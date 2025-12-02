import os
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from core.rag_engine import RAGEngine
from core.director import Director
from core.summary_engine import SummaryEngine
from core.prompt_builder import PromptBuilder

load_dotenv()

class Orchestrator:
    def __init__(self):
        print("🎹 Orch Init...")

        self.default_key = os.getenv("GEMINI_API_KEY")
        self.rag = RAGEngine()
        self.builder = PromptBuilder()
        self.director = Director(self.default_key or "")
        self.summarizer = SummaryEngine(self.default_key or "")

    async def generate_response(
        self, text: str, sess_id: str, char_id: str, prof_id: str, 
        user_p: Dict, scn_state: Optional[Dict] = None, chat_hist: Optional[List] = None, 
        api_key: Optional[str] = None
    ) -> Dict:
        
        # Определяем, какой ключ использовать
        key_to_use = api_key if api_key else self.default_key
        if not key_to_use:
            return {"response": "[SYSTEM ERROR: Gemini API Key is missing. Please enter it in settings.]", "scenario_state": scn_state}

        # Создаем инстанс LLM под конкретный запрос
        main_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=1.15, google_api_key=key_to_use)

        # 1. Data Fetch
        char = self.rag.get_character_data_raw(char_id)
        rules = self.rag.get_rules_raw(prof_id)
        
        # 2. Director
        scn_data = None
        guide = ""
        new_scn = scn_state.copy() if scn_state else None

        if new_scn and new_scn.get('scenario_id'):
            scn_data = self.rag.get_scenario_data_raw(new_scn['scenario_id'])
            if scn_data:
                pts = scn_data.get('plot_points', [])
                idx = new_scn.get('current_step', 0)
                if idx < len(pts):
                    goal = pts[idx].get('goal')
                    scn_data['current_plot_point'] = goal
                    
                    last_ai = chat_hist[-1]['content'] if chat_hist and chat_hist[-1]['role'] == 'ai' else ""
                    if await self.director.check_progress(f"AI: {last_ai}\nUser: {text}", goal, api_key=key_to_use):
                        new_scn['current_step'] += 1
                        new_scn['fail_count'] = 0
                    else:
                        new_scn['fail_count'] = new_scn.get('fail_count', 0) + 1
                        if new_scn['fail_count'] >= 3:
                            guide = f"Plot stagnating. Force advancement towards: '{goal}'."

        # 3. Context
        sess = self.rag.get_session_state(sess_id)
        mems = self.rag.get_relevant_history(sess_id, text)
        sys_txt = self.builder.build(char, user_p, rules, scn_data or {}, sess.get("summary") or "", guide)

        # 4. Messages
        msgs: List[BaseMessage] = [SystemMessage(content=sys_txt)]
        if mems: msgs.append(SystemMessage(content=f"### MEMORY ###\n{mems}"))
        if chat_hist:
            for m in chat_hist[-6:]:
                if m["role"] == "user":
                    msgs.append(HumanMessage(content=m["content"]))
                else:
                    msgs.append(AIMessage(content=m["content"]))
        msgs.append(HumanMessage(content=text))

        # 5. Generate
        try:
            resp = await main_llm.ainvoke(msgs)
            ai_text = str(resp.content)
        except Exception as e:
            ai_text = f"[Error: {e}]"

        # 6. Store
        vid = self.rag.store_interaction(sess_id, text, ai_text)
        upd_state = self.rag.append_to_buffer(sess_id, text, ai_text, vid or "")
        
        if len(upd_state["buffer"]) >= 6:
            new_sum = await self.summarizer.update(sess.get("summary") or "", upd_state["buffer"], api_key=key_to_use)
            self.rag.update_session_summary(sess_id, new_sum)

        return {"response": ai_text, "scenario_state": new_scn, "prompt": sys_txt}

    async def regenerate_last_message(self, sess_id: str, char_id: str, prof_id: str, user_p: Dict, scn_state: Optional[Dict], api_key: Optional[str] = None):
        """Регенерация последнего ответа ИИ."""
        key_to_use = api_key if api_key else self.default_key
        if not key_to_use:
            return None

        main_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=1.15, google_api_key=key_to_use)

        sess = self.rag.get_session_state(sess_id)
        hist = sess["full_history"]
        if not hist or hist[-1]["role"] != "ai": return None
        
        # Получаем контекст БЕЗ последнего сообщения
        # User message, которое триггернуло ответ
        last_user_idx = len(hist) - 2
        last_user_txt = hist[last_user_idx]["content"]
        
        char = self.rag.get_character_data_raw(char_id)
        rules = self.rag.get_rules_raw(prof_id)
        scn_data = self.rag.get_scenario_data_raw(scn_state['scenario_id']) if scn_state else None
        
        sys_txt = self.builder.build(char, user_p, rules, scn_data or {}, sess.get("summary") or "", "")
        
        msgs: List[BaseMessage] = [SystemMessage(content=sys_txt)]
        # История до последнего хода
        short_hist = hist[-6:-1] 
        for m in short_hist:
             cls = HumanMessage if m["role"] == "user" else AIMessage
             msgs.append(cls(content=m["content"]))
        
        # Вызов
        resp = await main_llm.ainvoke(msgs)
        new_text = str(resp.content)
        
        # Сохранение как кандидата
        last_idx = len(hist) - 1
        self.rag.add_candidate_response(sess_id, last_idx, new_text)
        
        return new_text