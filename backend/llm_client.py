import os
import requests
import json
import google.generativeai as genai
import threading
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta

from logger_config import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class LLMClient:
    def __init__(self):
        """Инициализация при создании объекта (один раз при старте)"""
        self.gemini_available = False
        self.ollama_available = True  # Считаем, что Ollama всегда доступна
        self.current_model = "ollama"  # По умолчанию используем Ollama
        self.ollama_model_name = "llama3.2:3b"  # Модель по умолчанию

        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

        # Кэширование проверок (чтобы не проверять слишком часто)
        self._last_gemini_check = None
        self._last_ollama_check = None
        self._check_interval = timedelta(seconds=30)

        self._check_gemini_availability()
        self._check_ollama_availability()

        self._stop_monitoring = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_models, daemon=True)
        self._monitor_thread.start()

        logger.info("✅ LLM клиент инициализирован.")
        logger.info(f"   Ollama: {self.ollama_host} (модель: {self.ollama_model_name})")
        logger.info(f"   Gemini доступна: {self.gemini_available}")
        logger.info(f"📱 Текущая модель: {self.current_model}")

    def _monitor_models(self):
        """Фоновый поток для периодической проверки моделей"""
        while not self._stop_monitoring.is_set():
            time.sleep(30)
            self._check_ollama_availability(force=True)
            self._check_gemini_availability(force=True)
            if self.ollama_available or self.gemini_available:
                logger.debug("🔍 Фоновая проверка моделей завершена")

    def __del__(self):
        """Остановка фонового потока при уничтожении объекта"""
        if hasattr(self, '_stop_monitoring'):
            self._stop_monitoring.set()

    def _is_cache_valid(self, last_check: datetime) -> bool:
        """Проверяет, устарел ли кэш"""
        if last_check is None:
            return False
        return datetime.now() - last_check < self._check_interval

    def _check_ollama_availability(self, force: bool = False):
        """Проверяет доступность локального Ollama и получает список моделей"""
        if not force and self._is_cache_valid(self._last_ollama_check):
            return
        self._last_ollama_check = datetime.now()

        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.ollama_models = [m["name"] for m in data.get("models", [])]
                self.ollama_available = len(self.ollama_models) > 0
                if self.ollama_available:
                    logger.info(f"✅ Ollama доступна, модели: {self.ollama_models}")
                else:
                    logger.warning("⚠️ Ollama запущена, но модели не загружены. Первый запрос загрузит модель.")
                    self.ollama_available = True  # Всё равно считаем доступной
                    # Добавляем дефолтную модель, которую будем использовать
                    self.ollama_models = ["llama3.2:3b"]
        except Exception as e:
            logger.warning(f"⚠️ Ollama не доступна: {e}")
            self.ollama_available = False

    def _check_gemini_availability(self, force: bool = False):
        """Проверяет доступность Gemini API при старте"""
        if not force and self._is_cache_valid(self._last_gemini_check):
            return

        self._last_gemini_check = datetime.now()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            logger.error("❌ GEMINI_API_KEY не найден в переменных окружения")
            self.gemini_available = False
            return

        try:
            genai.configure(api_key=api_key)
            models = genai.list_models()
            models_list = list(genai.list_models())
            logger.info(f"Найдено моделей Gemini: {len(models_list)}")
            for model in models_list:
                logger.debug(f"  - {model.name}")

            self.gemini_model = None
            for model in models:
                if self.gemini_model_name in model.name and 'generateContent' in model.supported_generation_methods:
                    self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
                    self.gemini_available = True
                    logger.info(f"✅ Gemini API доступна, модель: {model.name}")
                    return
            logger.warning("❌ Не найдена подходящая модель Gemini")
        except Exception as e:
            logger.error(f"❌ Gemini API недоступна: {e}")
            self.gemini_available = False

    def _generate_with_ollama(self, prompt: str, model_name: str = "llama3.2:3b") -> str:
        """Использует локальную модель через Ollama"""
        try:
            logger.info(f"🔄 Отправляю запрос к Ollama ({model_name})...")

            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2000
                    }
                },
                timeout=120.0
            )

            if response.status_code == 200:
                result = response.json()
                logger.info("✅ Ответ от Ollama получен")
                return result.get("response", "")
            else:
                logger.error(f"❌ Ошибка Ollama: {response.status_code}, {response.text}")
                return self._generate_with_fallback(prompt)
        except requests.exceptions.ConnectionError:
            logger.error("❌ Не удалось подключиться к Ollama")
            return self._generate_with_fallback(prompt)
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове Ollama: {e}")
            return self._generate_with_fallback(prompt)

    def switch_model(self, model_name: str):
        """Переключает модель"""
        if model_name == "gemini" and self.gemini_available:
            self.current_model = "gemini"
            logger.info("🔄 Переключено на Gemini")
            return True
        elif model_name == "ollama" or model_name.startswith("ollama:"):
            self.current_model = "ollama"
            # Если указана конкретная модель ollama
            if model_name.startswith("ollama:"):
                self.ollama_model_name = model_name.replace("ollama:", "")
            logger.info(f"🔄 Переключено на Ollama (модель: {self.ollama_model_name})")
            return True
        else:
            logger.warning(f"❌ Модель {model_name} недоступна")
            return False

    def get_available_models(self):
        """Возвращает список доступных моделей для UI"""
        models = [
            {"id": "ollama", "name": f"Ollama ({self.ollama_model_name})", "available": True}
        ]

        if self.gemini_available:
            models.append({"id": "gemini", "name": "Gemini (API)", "available": True})

        return models

    def generate(self, prompt: str) -> str:
        logger.info(f"Пришел запрос на генерацию: {prompt}")
        """Генерация текста с выбранной моделью"""
        if self.current_model == "gemini":
            res = self._generate_with_gemini(prompt)
            logger.info(f"Ответ генерации Gemini: {res}")
            return res
        else:
            res = self._generate_with_ollama(prompt)
            logger.info(f"Ответ генерации Ollama: {prompt}")
            return res

    def _generate_with_gemini(self, prompt: str) -> str:
        """Использует Gemini API"""
        try:
            logger.info("🔄 Отправляю запрос к Gemini API...")
            response = self.gemini_model.generate_content(prompt)
            logger.info("✅ Ответ от Gemini получен")
            return response.text
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове Gemini: {e}")
            logger.info("🔄 Переключаюсь на Ollama как fallback")
            return self._generate_with_ollama(prompt)

    def _generate_with_fallback(self, prompt: str) -> str:
        """
        Абсолютный fallback на случай, если Ollama недоступна.
        Возвращает простой шаблон ответа.
        """
        logger.warning("🔄 Использую fallback генерацию")

        # Извлекаем тему из промпта
        topic = "учебной теме"
        if "тему \"" in prompt:
            topic = prompt.split("тему \"")[1].split("\"")[0]
        elif "тема: " in prompt.lower():
            # Альтернативный парсинг
            lines = prompt.lower().split('\n')
            for line in lines:
                if 'тема:' in line or 'topic:' in line:
                    topic = line.split(':')[-1].strip()
                    break

        return f"""Вопрос 1: Что такое {topic}?
A) Первый вариант ответа
B) Второй вариант ответа (правильный)
C) Третий вариант ответа
D) Четвёртый вариант ответа
Правильный ответ: B

Вопрос 2: Какое из следующих утверждений верно о {topic}?
A) Неверное утверждение 1
B) Неверное утверждение 2
C) Верное утверждение
D) Неверное утверждение 3
Правильный ответ: C

Вопрос 3: Какой подход наиболее эффективен для изучения {topic}?
A) Подход A
B) Подход B
C) Подход C (правильный)
D) Подход D
Правильный ответ: C"""