from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class Director:
    def __init__(self, default_api_key: str):
        self.default_api_key = default_api_key

    async def check_progress(self, history_text: str, goal: str, api_key: Optional[str] = None) -> bool:
        if not goal: return False
        
        # Если ключ пришел от юзера - используем его, иначе дефолтный из .env
        key_to_use = api_key if api_key else self.default_api_key
        
        # Создаем "одноразовый" экземпляр модели с нужным ключом
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0, google_api_key=key_to_use)
        
        prompt = (
            f"Goal: \"{goal}\"\nChat:\n{history_text}\n"
            "Did they make significant progress towards the goal? YES or NO."
        )
        try:
            res = await llm.ainvoke([HumanMessage(content=prompt)])
            return "YES" in str(res.content).strip().upper()
        except: return False