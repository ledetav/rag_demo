from typing import List, Dict

class PromptBuilder:
    def build(self, ai_persona: Dict, user_persona: Dict, rules: List[Dict], 
              scenario: Dict, summary: str = "", guidance: str = "") -> str:
        
        # Вспомогательная функция для извлечения текста правил по категории
        def get_rules_text(category_name: str) -> str:
            # Ищем правила, у которых 'category' совпадает с запрошенной
            relevant_rules = [r['text'] for r in rules if r.get('category') == category_name]
            return "\n".join(relevant_rules)

        # --- 1. CORE DIRECTIVES ---
        prompt = "[CORE DIRECTIVE: ATMOSPHERE & STYLE]\n"
        prompt += get_rules_text('core') + "\n\n"
        
        # --- 2. PROHIBITIONS (Anti-Mirror) ---
        prompt += "[MANDATORY PROHIBITIONS]\n"
        prompt += get_rules_text('anti_mirror') + "\n\n"
        
        # --- 3. FORMATTING (Language & Perspective) --- 
        # Добавили этот блок, чтобы подхватывать язык и лицо
        lang_rules = get_rules_text('language')
        persp_rules = get_rules_text('perspective')
        
        if lang_rules or persp_rules:
            prompt += "[FORMATTING & LANGUAGE]\n"
            if lang_rules: prompt += lang_rules + "\n"
            if persp_rules: prompt += persp_rules + "\n"
            prompt += "\n"

        # --- 4. QUALITY ASSURANCE ---
        prompt += "[QUALITY RULES]\n"
        prompt += get_rules_text('quality_assurance') + "\n\n"
        
        # --- 5. AI PERSONA ---
        # Описание приходит из RAGEngine уже собранным
        prompt += "[PART 1: AI's PERSONA]\n"
        prompt += f"AI Character Name: {ai_persona.get('name')}\n"
        
        # --- 6. USER PERSONA ---
        prompt += "[PART 2: USER's PERSONA]\n"
        prompt += f"User Character Name: {user_persona.get('name')}\n"
        prompt += f"Appearance & Personality: {user_persona.get('description')}\n"
        # Если есть отношения, добавляем
        if user_persona.get('relationship'):
            prompt += f"Relationship with AI's Character: {user_persona.get('relationship')}\n"
        prompt += "\n"
        
        # --- 7. SCENARIO (Optional) ---
        if scenario:
            prompt += "[PART 3: SCENARIO]\n"
            prompt += f"Title: {scenario.get('title')}\n"
            prompt += f"Hook: {scenario.get('description')}\n"
            if cp := scenario.get('current_plot_point'):
                prompt += f"Current Objective: {cp}\n"
            prompt += "\n"
            
        # --- 8. HISTORY & CONTEXT ---
        if summary:
            prompt += f"[STORY SUMMARY]\n{summary}\n\n"
        
        if guidance:
            prompt += f"[DIRECTOR NOTE]\n!!! {guidance} !!!\n\n"
            
        return prompt