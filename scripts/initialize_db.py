import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

load_dotenv()

# Определяем корневую директорию проекта (на 2 уровня выше скрипта)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# Настройки модели эмбеддингов
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_json_data(filename: str) -> List[Dict[str, Any]]:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        print(f"Файл {filename} не найден в {DATA_DIR}. Пропуск.")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Ошибка чтения JSON {filename}: {e}")
        return []


def process_characters(data: List[Dict]) -> List[Document]:
    documents = []
    for char in data:
        # Формируем текст, который будет векторизован (semantic content)
        # Мы объединяем описание, личность и стиль речи для лучшего поиска
        persona = char.get("persona_data", {})
        page_content = (
            f"Character Name: {char.get('name')}\n"
            # f"Tagline: {char.get('tagline')}\n"
            # f"Description: {char.get('description')}\n"
            # f"Tags: {', '.join(char.get('tags', []))}\n"
            f"Appearance: {persona.get('appearance', '')}\n"
            f"Personality: {persona.get('personality', '')}\n"
            f"Inner World: {persona.get('inner_world', '')}"
        )

        metadata = {
            "id": char.get("id"),
            "name": char.get("name"),
            "type": "character"
        }
        
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


def process_rules(data: List[Dict]) -> List[Document]:
    documents = []
    for rule in data:
        # Для правил контентом является сам текст правила
        page_content = rule.get("text", "")
        
        metadata = {
            "id": rule.get("rule_id"),
            "category": rule.get("category"),
            "type": "rule"
        }
        
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


def process_scenarios(data: List[Dict]) -> List[Document]:
    documents = []
    for scn in data:
        page_content = (
            f"Scenario Title: {scn.get('title')}\n"
            f"Description: {scn.get('description')}\n"
        )
        
        # Добавляем сюжетные точки в контент для лучшего поиска контекста
        plot_points = scn.get("plot_points", [])
        plot_text = "\n".join([f"- {p['title']}: {p.get('goal', '')}" for p in plot_points])
        page_content += f"Plot Outline:\n{plot_text}"

        metadata = {
            "id": scn.get("id"),
            "title": scn.get("title"),
            "type": "scenario"
        }
        
        documents.append(Document(page_content=page_content, metadata=metadata))
    return documents


def initialize_vector_db():
    print(f"Начинаем инициализацию базы данных в: {CHROMA_DB_DIR}")

    # Очистка старой базы данных (если нужно полное пересоздание)
    if CHROMA_DB_DIR.exists():
        print("Удаление существующей базы данных...")
        shutil.rmtree(CHROMA_DB_DIR)
    
    # Инициализация модели эмбеддингов
    print(f"Загрузка модели эмбеддингов ({EMBEDDING_MODEL_NAME})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # Загрузка и процессинг данных
    chars_data = load_json_data("characters.json")
    rules_data = load_json_data("rules.json")
    scenarios_data = load_json_data("scenarios.json")

    char_docs = process_characters(chars_data)
    rule_docs = process_rules(rules_data)
    scenario_docs = process_scenarios(scenarios_data)

    """ Создание коллекций в ChromaDB
    Создаем отдельные коллекции для разных типов данных, чтобы
    Оркестратор мог обращаться к конкретному "Контуру" """
    
    if char_docs:
        print(f"Индексация персонажей ({len(char_docs)} шт.)...")
        Chroma.from_documents(
            documents=char_docs,
            embedding=embeddings,
            persist_directory=str(CHROMA_DB_DIR),
            collection_name="characters_collection"
        )

    if rule_docs:
        print(f"Индексация правил ({len(rule_docs)} шт.)...")
        Chroma.from_documents(
            documents=rule_docs,
            embedding=embeddings,
            persist_directory=str(CHROMA_DB_DIR),
            collection_name="rules_collection"
        )

    if scenario_docs:
        print(f"Индексация сценариев ({len(scenario_docs)} шт.)...")
        Chroma.from_documents(
            documents=scenario_docs,
            embedding=embeddings,
            persist_directory=str(CHROMA_DB_DIR),
            collection_name="scenarios_collection"
        )
    
    """ rule_profiles.json не векторизуется, так как это конфигурационные
    файлы, связывающие ID. Их приложение будет читать напрямую как JSON. """

    print("База данных успешно инициализирована!")
    print(f"Файлы сохранены в: {CHROMA_DB_DIR}")


if __name__ == "__main__":
    initialize_vector_db()