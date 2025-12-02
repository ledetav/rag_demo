from typing import List, Dict, Optional

class PromptBuilder:
    def build(self, ai: Dict, user: Dict, rules: List[Dict], scn: Optional[Dict], summary: Optional[str], guide: str) -> str:
        
        def get_rules(cat): return "\n".join([r['text'] for r in rules if r.get('category') == cat])

        p = "[CORE DIRECTIVE]\n" + get_rules('core') + "\n\n"
        p += "[PROHIBITIONS]\n" + get_rules('anti_mirror') + "\n\n"
        p += "[QUALITY]\n" + get_rules('quality_assurance') + "\n\n"
        
        p += f"[AI PERSONA]\nName: {ai.get('name')}\n{ai.get('description_full')}\n\n"
        p += f"[USER PERSONA]\nName: {user.get('name')}\nDesc: {user.get('description')}\nRel: {user.get('relationship')}\n\n"
        
        if scn:
            p += f"[SCENARIO]\nTitle: {scn.get('title')}\nHook: {scn.get('description')}\n"
            if cp := scn.get('current_plot_point'): p += f"Objective: {cp}\n"
            
        if summary: p += f"\n[STORY SUMMARY]\n{summary}\n\n"
        if guide: p += f"\n[DIRECTOR NOTE]\n!!! {guide} !!!\n"
        
        return p