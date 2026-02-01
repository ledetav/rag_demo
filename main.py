import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from core.orchestrator import Orchestrator

ENABLE_AUTH = False  # False, чтобы отключить проверку
AUTH_SECRET_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc2ODM0MTk4M30.13hIyV-JuDJQq-WAH0aUywEa9Pln7pmcg6iar9zoAis"  # Должен совпадать с Auth Service
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="http://localhost:8001/token", auto_error=False)


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)):
    if not ENABLE_AUTH:
        return "Anonymous (Auth Disabled)"

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Could not validate credentials")

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Глобальный стейт ---
# Оркестратор тяжелый, инициализируем один раз
orchestrator: Optional[Orchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    logger.info("Server starting...")
    orchestrator = Orchestrator()
    yield
    logger.info("Server shutting down...")

app = FastAPI(title="Roleplay Engine API", lifespan=lifespan)

# --- CORS (Разрешаем запросы с React localhost:5173) ---
app.add_middleware(
    CORSMiddleware,
    # Для разработки можно *, в проде лучше конкретный домен
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DTO (Data Transfer Objects) ---


class UserPersonaDTO(BaseModel):
    name: str
    description: str
    relationship: str


class CreateSessionRequest(BaseModel):
    character_id: str
    profile_id: str
    user_persona: UserPersonaDTO
    scenario_id: Optional[str] = None


class ChatMessageRequest(BaseModel):
    session_id: str
    text: str


class RegenerateRequest(BaseModel):
    session_id: str


class EditMessageRequest(BaseModel):
    session_id: str
    msg_index: int
    new_text: str


class RewindRequest(BaseModel):
    session_id: str
    # Индекс сообщения, к которому откатываемся (оно останется последним)
    target_index: int

# --- ENDPOINTS: STATIC DATA ---


@app.get("/api/characters")
def get_characters():
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")
    return orchestrator.rag.cache["characters"]


@app.get("/api/scenarios")
def get_scenarios():
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")
    return orchestrator.rag.cache["scenarios"]


@app.get("/api/styles")
def get_styles():
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")
    return orchestrator.rag.cache["rule_profiles"]

# --- ENDPOINTS: SESSIONS ---


@app.get("/api/sessions")
def list_sessions(user: str = Depends(get_current_user_optional)):
    """Возвращает список сессий с метаданными (имена, дата)."""
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    sessions = []

    # Используем путь из RAG движка - он точно правильный (абсолютный)
    sessions_dir = orchestrator.rag.sessions_dir

    if sessions_dir.exists():
        # Сортируем по времени изменения (сначала новые)
        files = sorted(sessions_dir.glob("*.json"),
                       key=lambda f: f.stat().st_mtime, reverse=True)

        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Пытаемся достать красивые данные для отображения
                    meta = data.get("meta", {})
                    user_p = meta.get("user_persona", {})

                    # Если метаданных нет (старые сессии из консоли), ставим заглушки
                    session_info = {
                        "id": file.stem,
                        "character_id": meta.get("character_id", "Unknown"),
                        "user_name": user_p.get("name", "User"),
                        "msg_count": data.get("msg_count", 0),
                        "summary": data.get("summary", "")[:100] + "..." if data.get("summary") else "No summary yet."
                    }

                    # Пытаемся найти имя персонажа по ID для красоты
                    # (Используем кэш RAG)
                    char_id = meta.get("character_id")
                    if char_id:
                        char_obj = next(
                            (c for c in orchestrator.rag.cache["characters"] if c["id"] == char_id), None)
                        if char_obj:
                            session_info["character_name"] = char_obj["name"]
                        else:
                            session_info["character_name"] = char_id
                    else:
                        session_info["character_name"] = "AI"

                    sessions.append(session_info)
            except Exception as e:
                logger.error(f"Error reading session {file}: {e}")
                # Если файл битый, добавляем хотя бы ID
                sessions.append({"id": file.stem, "error": True})

    return sessions


@app.get("/api/sessions/{session_id}")
def load_session(session_id: str):
    """Возвращает полный стейт сессии (историю)."""
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")
    state = orchestrator.rag.get_session_state(session_id)

    # Преобразуем candidates в variants для фронтенда
    for msg in state.get("full_history", []):
        if "candidates" in msg and len(msg["candidates"]) > 1:
            msg["variants"] = msg["candidates"]
            msg["currentVariant"] = len(msg["candidates"]) - 1

    return state


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest, user: str = Depends(get_current_user_optional)):
    """Инициализирует новую игру."""
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    # Генерируем ID
    session_id = f"{req.user_persona.name}_{req.character_id}_{uuid.uuid4().hex[:8]}"

    # Формируем начальное состояние
    initial_state = {
        "summary": "",
        "buffer": [],
        "full_history": [],
        "msg_count": 0,
        # Сохраняем метаданные, чтобы не передавать их каждый раз в запросе чата
        "meta": {
            "character_id": req.character_id,
            "profile_id": req.profile_id,
            "user_persona": req.user_persona.model_dump(),
            "scenario_state": None
        }
    }

    if req.scenario_id:
        initial_state["meta"]["scenario_state"] = {
            "scenario_id": req.scenario_id,
            "current_step": 0,
            "fail_count": 0
        }

    # Сохраняем через RAGEngine (он просто пишет JSON)
    orchestrator.rag.save_session_state(session_id, initial_state)

    return {"session_id": session_id}

# --- ENDPOINTS: CHAT ---


@app.post("/api/chat/send")
async def send_message(req: ChatMessageRequest, x_gemini_api_key: Optional[str] = Header(None), user: str = Depends(get_current_user_optional)):
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    # 1. Загружаем состояние сессии
    state = orchestrator.rag.get_session_state(req.session_id)
    if not state or "meta" not in state:
        raise HTTPException(404, "Session not found or corrupted")

    meta = state["meta"]
    history = state.get("full_history", [])

    # 2. Генерируем ответ
    # ВАЖНО: Мы берем историю из файла, конвертируем её для оркестратора
    chat_hist_for_llm = [
        {"role": m["role"], "content": m["content"]} for m in history]

    result = await orchestrator.generate_response(
        text=req.text,
        sess_id=req.session_id,
        char_id=meta["character_id"],
        prof_id=meta["profile_id"],
        user_p=meta["user_persona"],
        scn_state=meta["scenario_state"],
        chat_hist=chat_hist_for_llm,
        api_key=x_gemini_api_key
    )

    # 3. Обновляем scenario_state в метаданных, если он изменился
    if result["scenario_state"]:
        # Перечитываем, т.к. generate_response уже обновил историю
        state = orchestrator.rag.get_session_state(req.session_id)
        state["meta"]["scenario_state"] = result["scenario_state"]
        orchestrator.rag.save_session_state(req.session_id, state)

    # Возвращаем ответ и, возможно, обновленное состояние истории для фронта
    state = orchestrator.rag.get_session_state(req.session_id)
    return {
        "response": result["response"],
        "prompt_debug": result.get("prompt", ""),
        "scenario_state": result["scenario_state"],
        "title": state.get("title")
    }


@app.post("/api/chat/regenerate")
async def regenerate(req: RegenerateRequest, x_gemini_api_key: Optional[str] = Header(None)):
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    state = orchestrator.rag.get_session_state(req.session_id)
    meta = state["meta"]

    new_text = await orchestrator.regenerate_last_message(
        sess_id=req.session_id,
        char_id=meta["character_id"],
        prof_id=meta["profile_id"],
        user_p=meta["user_persona"],
        scn_state=meta["scenario_state"],
        api_key=x_gemini_api_key
    )

    if not new_text:
        raise HTTPException(400, "Cannot regenerate")

    return {"response": new_text}

# --- ENDPOINTS: HISTORY ---


@app.post("/api/history/edit")
def edit_message(req: EditMessageRequest):
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    success = orchestrator.rag.edit_message(
        req.session_id, req.msg_index, req.new_text)
    if not success:
        raise HTTPException(400, "Edit failed")
    return {"status": "ok"}


@app.post("/api/history/rewind")
def rewind(req: RewindRequest):
    if not orchestrator:
        raise HTTPException(500, "Server not initialized")

    # Логика: удалить всё ПОСЛЕ target_index.
    # Значит, мы удаляем хвост, начиная с target_index + 1
    # Но в rag_engine у нас метод delete_message_tail(start_index), который удаляет ВКЛЮЧИТЕЛЬНО.
    # Значит, если мы хотим откатиться К сообщению 5 (чтобы оно осталось последним),
    # нам надо удалить начиная с 6.

    success = orchestrator.rag.delete_message_tail(
        req.session_id, req.target_index + 1)
    if not success:
        raise HTTPException(400, "Rewind failed")
    return {"status": "ok"}


# Запуск: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
