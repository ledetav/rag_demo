import asyncio
import json
from pathlib import Path
from core.orchestrator import Orchestrator

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def load_json(name):
    try:
        with open(DATA_DIR / name, 'r', encoding='utf-8') as f: return json.load(f)
    except: return []

def multiline(p):
    print(f"\n📝 {p} (END to finish):")
    lines = []
    while True:
        try:
            l = input()
            if l.strip().upper() == 'END': break
            lines.append(l)
        except: break
    return "\n".join(lines).strip()

def select(items, key, p):
    print(f"\n👉 {p}:")
    for i, it in enumerate(items, 1):
        print(f"{i}. {it.get(key) or it.get('name') or it.get('title')}")
    while True:
        try:
            idx = int(input("Choice: ")) - 1
            if 0 <= idx < len(items): return items[idx]
        except: pass

async def main():
    orch = Orchestrator()
    print("\n--- NEW GAME ---")
    
    char = select(load_json("characters.json"), 'name', "Character")
    prof = select(load_json("rule_profiles.json"), 'description', "Style")
    
    uname = input("\nYour Name: ")
    udesc = multiline("Describe Yourself")
    
    mode = input("\nMode (1=Scenario, 2=Sandbox): ")
    scn_state = None
    rel = ""
    
    if mode == "1":
        scens = [s for s in load_json("scenarios.json") if char['id'] in s.get('compatible_character_ids', [])]
        if scens:
            scn = select(scens, 'title', "Scenario")
            role = select(scn['user_role_options'], 'name', "Role")
            rel = role.get('description', '')
            scn_state = {"scenario_id": scn['id'], "current_step": 0, "fail_count": 0}
        else:
            print("No scenarios. Sandbox mode.")
            
    if not rel: rel = multiline("Relationship")
    
    user_p = {"name": uname, "description": udesc, "relationship": rel}
    sess_id = f"console_{uname}_{char['name']}"
    hist = []

    print(f"\n🚀 START ({sess_id})")
    while True:
        txt = multiline("You")
        if txt.lower() in ['exit', 'quit']: break
        
        print("\n⏳ Thinking...")
        res = await orch.generate_response(
            txt, sess_id, char['id'], prof['profile_id'], user_p, scn_state, hist
        )
        
        print(f"\n📋 PROMPT:\n{'-'*80}\n{res['prompt']}\n{'-'*80}")
        print(f"\n🤖 {char['name']}:\n{res['response']}")
        
        hist.append({"role": "user", "content": txt})
        hist.append({"role": "ai", "content": res['response']})
        if res['scenario_state']: scn_state = res['scenario_state']

if __name__ == "__main__":
    asyncio.run(main())