import os
import requests
import logging
import time
from typing import Dict, Any
from logger_config import setup_logger
logger = setup_logger(__name__)

INFERENCE_URL = os.getenv("INFERENCE_URL", "http://backend:8000")


def generate_quiz(topic: str, num_questions: int) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{INFERENCE_URL}/generate",
            json={"topic": topic, "num_questions": num_questions},
            timeout=60.0
        )
        print(f"📤 Отправка запроса: num_questions={num_questions}")

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_quiz_from_file(file, num_questions: int, model: str) -> Dict[str, Any]:
    """Отправляет запрос на генерацию теста из файла"""
    try:
        logger.info(f"generate_quiz_from_file вызван: model={model}, num_questions={num_questions}")
        response = requests.post(
            f"{INFERENCE_URL}/generate-from-file",
            files={"file": file},
            data={"num_questions": num_questions, "model": model},
            timeout=90.0
        )

        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_quiz_regenerate(topic: str, num_questions: int, old_quiz_text: str, model: str) -> Dict[str, Any]:
    """Отправляет запрос на перегенерацию теста с исключением старых вопросов"""
    logger.info(f"Запрос перегенерации: topic='{topic}', num_questions={num_questions}, model={model}")
    start_time = time.time()

    try:
        response = requests.post(
            f"{INFERENCE_URL}/regenerate",
            json={
                "topic": topic,
                "num_questions": num_questions,
                "old_quiz_text": old_quiz_text,
                "model": model
            },
            timeout=90.0
        )
        elapsed = time.time() - start_time
        logger.debug(f"Ответ от бэкенда за {elapsed:.2f}с, статус: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"Успешная перегенерация")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"Ошибка перегенерации: HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Исключение при перегенерации: {e}", exc_info=True)
        return {"success": False, "error": str(e)}