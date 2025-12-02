import json
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class RAGEngine:
    def __init__(self):
        print("RAG Engine Init...")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
        
        # Коллекция векторов истории (Память диалога)
        self.history_collection = Chroma(
            persist_directory=str(CHROMA_DB_DIR),
            embedding_function=self.embeddings,
            collection_name="history_collection"
        )
        
        # Кэш статических данных (чтобы не читать файлы каждый раз)
        self.cache = {
            "characters": self._load_json("characters.json"),
            "rules": self._load_json("rules.json"),
            "scenarios": self._load_json("scenarios.json"),
            "rule_profiles": self._load_json("rule_profiles.json")
        }
        
        # Маппинг профилей правил
        self.profile_map = {p["profile_id"]: p["rule_ids"] for p in self.cache["rule_profiles"]}

        # Папка сессий
        self.sessions_dir = DATA_DIR / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _load_json(self, filename: str) -> List[Dict]:
        path = DATA_DIR / filename
        if not path.exists(): return []
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except: return []

    # ============================
    # 1. STATIC DATA ACCESS
    # ============================
    def get_character_data_raw(self, char_id: str) -> Dict:
        c = next((x for x in self.cache["characters"] if x["id"] == char_id), None)
        if not c: return {}
        
        # Сборка полного описания для LLM
        desc = [c.get("description", "")]
        p = c.get("persona_data", {})
        for k, v in p.items():
            if v: desc.append(f"\n{k.replace('_', ' ').title()}:\n{v}")
            
        return {"name": c["name"], "description_full": "\n".join(desc)}

    def get_rules_raw(self, profile_id: str) -> List[Dict]:
        ids = self.profile_map.get(profile_id, [])
        return [r for r in self.cache["rules"] if r["rule_id"] in ids]

    def get_scenario_data_raw(self, scenario_id: str) -> Dict:
        return next((s for s in self.cache["scenarios"] if s["id"] == scenario_id), {})

    # ============================
    # 2. VECTOR MEMORY (CHROMA)
    # ============================
    def store_interaction(self, session_id: str, user_text: str, ai_text: str) -> Optional[str]:
        """Сохраняет пару сообщений в вектор и ВОЗВРАЩАЕТ ID документа."""
        if not session_id: return None
        doc_id = str(uuid.uuid4())
        content = f"User: {user_text}\nAI: {ai_text}"
        
        doc = Document(
            page_content=content,
            metadata={"session_id": session_id, "type": "interaction", "timestamp": str(uuid.uuid4())}
        )
        try:
            self.history_collection.add_documents([doc], ids=[doc_id])
            return doc_id
        except Exception as e:
            print(f"Vector Store Error: {e}")
            return None

    def get_relevant_history(self, session_id: str, query: str, k: int = 3) -> str:
        if not session_id: return ""
        try:
            results = self.history_collection.similarity_search(query, k=k, filter={"session_id": session_id})
            return "\n".join([f"Memory {i+1}: {d.page_content.replace(chr(10), ' ')}" for i, d in enumerate(results)])
        except: return ""

    def delete_vectors(self, vector_ids: List[str]):
        """Удаляет список векторов по ID."""
        valid_ids = [v for v in vector_ids if v]
        if valid_ids:
            try:
                self.history_collection.delete(ids=valid_ids)
                print(f"🗑️ Deleted {len(valid_ids)} vectors.")
            except Exception as e:
                print(f"Vector delete error: {e}")

    # ============================
    # 3. SESSION MANAGEMENT (JSON)
    # ============================
    def get_session_state(self, session_id: str) -> Dict:
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "full_history" not in data: data["full_history"] = []
                    return data
            except: pass
        return {"summary": "", "buffer": [], "full_history": [], "msg_count": 0}

    def save_session_state(self, session_id: str, state: Dict):
        path = self.sessions_dir / f"{session_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def append_to_buffer(self, session_id: str, user_text: str, ai_text: str, vector_id: Optional[str] = None):
        """Добавляет ход в JSON историю."""
        state = self.get_session_state(session_id)
        current_sum = state.get("summary", "")
        
        # Обновляем буфер для саммаризатора
        state["buffer"].extend([f"User: {user_text}", f"AI: {ai_text}"])
        state["msg_count"] += 1
        
        idx = len(state["full_history"])
        
        # User Message
        state["full_history"].append({
            "index": idx, "role": "user", "content": user_text, 
            "summary_snapshot": current_sum, "vector_id": None
        })
        
        # AI Message (хранит ID вектора)
        state["full_history"].append({
            "index": idx + 1, "role": "ai", "content": ai_text, 
            "summary_snapshot": current_sum, "vector_id": vector_id,
            "candidates": [ai_text] # Для свайпов
        })
        
        self.save_session_state(session_id, state)
        return state

    def update_session_summary(self, session_id: str, new_summary: str):
        state = self.get_session_state(session_id)
        state["summary"] = new_summary
        state["buffer"] = []
        self.save_session_state(session_id, state)

    # ============================
    # 4. ADVANCED EDITING & SWIPING
    # ============================
    
    def delete_message_tail(self, session_id: str, start_index: int):
        """Удаляет сообщение по индексу и ВСЕ последующие (Rewind)."""
        state = self.get_session_state(session_id)
        history = state["full_history"]
        
        if start_index < 0 or start_index >= len(history): return False
        
        # Вектора на удаление
        removed_items = history[start_index:]
        vec_ids = [m["vector_id"] for m in removed_items if m.get("vector_id")]
        self.delete_vectors(vec_ids)
        
        # Обрезаем JSON
        new_hist = history[:start_index]
        state["full_history"] = new_hist
        
        # Восстанавливаем состояние
        if new_hist:
            last = new_hist[-1]
            state["summary"] = last.get("summary_snapshot", "")
            # Восстанавливаем буфер
            r_buf = []
            snap = last.get("summary_snapshot", "")
            for m in reversed(new_hist):
                if m.get("summary_snapshot") == snap:
                    role = "User" if m["role"] == "user" else "AI"
                    r_buf.insert(0, f"{role}: {m['content']}")
                else: break
            state["buffer"] = r_buf
        else:
            state["summary"] = ""
            state["buffer"] = []
            
        self.save_session_state(session_id, state)
        return True

    def edit_message(self, session_id: str, index: int, new_text: str):
        """Редактирует сообщение и обновляет его вектор."""
        state = self.get_session_state(session_id)
        hist = state["full_history"]
        if index < 0 or index >= len(hist): return False
        
        msg = hist[index]
        msg["content"] = new_text
        if "candidates" in msg: msg["candidates"].append(new_text)
        
        # Обновляем вектор (удаляем старый, создаем новый)
        old_vid = msg.get("vector_id")
        if old_vid: self.delete_vectors([old_vid])
        
        # Если это AI, создаем новый вектор пары (User+AI)
        if msg["role"] == "ai" and index > 0:
            prev_user = hist[index-1]["content"]
            new_vid = self.store_interaction(session_id, prev_user, new_text)
            msg["vector_id"] = new_vid
            
        self.save_session_state(session_id, state)
        return True

    def add_candidate_response(self, session_id: str, index: int, new_text: str):
        """Добавляет вариант ответа (свайп)."""
        state = self.get_session_state(session_id)
        hist = state["full_history"]
        msg = hist[index]
        
        if msg["role"] != "ai": return False
        
        if "candidates" not in msg: msg["candidates"] = [msg["content"]]
        msg["candidates"].append(new_text)
        msg["content"] = new_text # Делаем активным
        
        # Обновляем вектор
        if old_vid := msg.get("vector_id"): self.delete_vectors([old_vid])
        
        prev_user = hist[index-1]["content"]
        new_vid = self.store_interaction(session_id, prev_user, new_text)
        msg["vector_id"] = new_vid
        
        self.save_session_state(session_id, state)
        return True

    def fork_session(self, src_id: str, new_id: str, up_to_index: int) -> bool:
        """Создает ветку чата, дублируя JSON и вектора."""
        src_state = self.get_session_state(src_id)
        hist = src_state.get("full_history", [])
        if not hist: return False
        
        new_hist = hist[:up_to_index + 1]
        
        # 1. Дублируем вектора
        old_vec_ids = [m["vector_id"] for m in new_hist if m.get("vector_id")]
        id_map = {}
        
        if old_vec_ids:
            try:
                # Получаем данные
                existing = self.history_collection.get(ids=old_vec_ids)
                new_docs, new_ids = [], []
                
                # Итерируемся и создаем копии с новым session_id
                cnt = len(existing['ids'])
                for i in range(cnt):
                    old_id = existing['ids'][i]
                    # Создаем новые
                    new_vid = str(uuid.uuid4())
                    meta = existing['metadatas'][i].copy()
                    meta['session_id'] = new_id
                    
                    new_docs.append(Document(page_content=existing['documents'][i], metadata=meta))
                    new_ids.append(new_vid)
                    id_map[old_id] = new_vid
                
                if new_docs:
                    self.history_collection.add_documents(new_docs, ids=new_ids)
            except Exception as e: print(f"Fork Error: {e}")

        # 2. Создаем новый JSON
        new_state = {
            "summary": new_hist[-1].get("summary_snapshot", ""),
            "buffer": [], # Буфер восстановим ниже
            "full_history": [],
            "msg_count": 0
        }
        
        # Обновляем vector_id в истории
        final_hist = []
        for item in new_hist:
            itm = item.copy()
            if ov := itm.get("vector_id"):
                if ov in id_map: itm["vector_id"] = id_map[ov]
            final_hist.append(itm)
        new_state["full_history"] = final_hist
        
        # Восстановление буфера
        r_buf = []
        snap = new_hist[-1].get("summary_snapshot", "")
        for m in reversed(new_hist):
            if m.get("summary_snapshot") == snap:
                role = "User" if m["role"] == "user" else "AI"
                r_buf.insert(0, f"{role}: {m['content']}")
            else: break
        new_state["buffer"] = r_buf
        
        self.save_session_state(new_id, new_state)
        return True