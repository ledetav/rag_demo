import json
import shutil
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def load_json(name):
    path = DATA_DIR / name
    if not path.exists(): return []
    with open(path, 'r', encoding='utf-8') as f: return json.load(f)

def process_docs(data, doc_type):
    docs = []
    for item in data:
        content = ""
        meta = {}
        if doc_type == 'character':
            p = item.get("persona_data", {})
            content = f"Name: {item['name']}\nDesc: {item['description']}\nApp: {p.get('appearance')}\nPers: {p.get('personality')}"
            meta = {"id": item['id'], "name": item['name'], "type": "character"}
        elif doc_type == 'rule':
            content = item.get("text", "")
            meta = {"id": item['rule_id'], "category": item['category'], "type": "rule"}
        elif doc_type == 'scenario':
            content = f"Title: {item['title']}\nDesc: {item['description']}"
            meta = {"id": item['id'], "title": item['title'], "type": "scenario"}
        docs.append(Document(page_content=content, metadata=meta))
    return docs

def main():
    if CHROMA_DB_DIR.exists(): shutil.rmtree(CHROMA_DB_DIR)
    
    emb = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    # 1. Characters
    Chroma.from_documents(
        process_docs(load_json("characters.json"), 'character'), 
        emb, persist_directory=str(CHROMA_DB_DIR), collection_name="characters_collection"
    )
    # 2. Rules
    Chroma.from_documents(
        process_docs(load_json("rules.json"), 'rule'), 
        emb, persist_directory=str(CHROMA_DB_DIR), collection_name="rules_collection"
    )
    # 3. Scenarios
    Chroma.from_documents(
        process_docs(load_json("scenarios.json"), 'scenario'), 
        emb, persist_directory=str(CHROMA_DB_DIR), collection_name="scenarios_collection"
    )
    print("Database Initialized.")

if __name__ == "__main__":
    main()