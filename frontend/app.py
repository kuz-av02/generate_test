import requests
import streamlit as st
import time
import pandas as pd

from auth import show_auth_page
from db_client import (
    init_db, get_db_session, save_generation,
    get_user_generations, get_generation_by_id,
    get_all_versions
)
from inference_client import generate_quiz, generate_quiz_from_file, generate_quiz_regenerate
from logger_config import setup_logger

# Инициализация логгера
logger = setup_logger(__name__)
init_db()


def get_available_models():
    """Запрашивает у бэкенда список доступных моделей"""
    logger.debug("Запрос списка доступных моделей")
    try:
        response = requests.get("http://backend:8000/models", timeout=5)
        if response.status_code == 200:
            models = response.json()["models"]
            logger.info(f"Получены модели: {models}")
            return models
        else:
            logger.warning(f"Ошибка получения моделей: {response.status_code}")
            return [{"id": "local", "name": "Локальная", "available": True}]
    except Exception as e:
        logger.error(f"Ошибка соединения с бэкендом: {e}")
        return [{"id": "local", "name": "Локальная (нет связи с бэкендом)", "available": True}]


def generate_quiz_with_model(topic: str, num_questions: int, model: str):
    """Отправляет запрос на генерацию с указанием модели"""
    logger.info(
        f"Пользователь {st.session_state.get('username', 'unknown')} запросил генерацию: topic='{topic}', num_questions={num_questions}, model={model}")
    start_time = time.time()

    try:
        response = requests.post(
            "http://backend:8000/generate",
            json={"topic": topic, "num_questions": num_questions, "model": model},
            timeout=60.0
        )
        elapsed = time.time() - start_time
        logger.debug(f"Ответ от бэкенда за {elapsed:.2f}с, статус: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"Успешная генерация, request_id: {response.json().get('request_id', 'unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"Ошибка генерации: HTTP {response.status_code}, ответ: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Исключение при генерации: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    logger.debug("Пользователь не аутентифицирован, показываем страницу входа")
    show_auth_page()
    st.stop()

# Логируем вход пользователя
# logger.info(f"Пользователь {st.session_state['username']} (id: {st.session_state['user_id']}) вошёл в систему")

st.set_page_config(page_title="Генератор тестов", page_icon="📝", layout="wide")

st.sidebar.title(f"👤 {st.session_state['username']}")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Меню",
    ["✨ Генерация теста", "📁 Генерация из файла", "📜 История генераций", "ℹ️ О сервисе"]
)

# logger.debug(f"Пользователь {st.session_state['username']} перешёл в раздел: {menu}")

if st.sidebar.button("🚪 Выйти"):
    logger.info(f"Пользователь {st.session_state['username']} вышел из системы")
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = None
    st.session_state["username"] = None
    st.rerun()


if menu == "✨ Генерация теста":
    st.title("✨ Генерация теста")
    st.markdown("Создайте новый тест на любую тему")

    # Получаем доступные модели
    available_models = get_available_models()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # ИЗМЕНЕНИЕ: используем text_area вместо text_input для многострочного ввода
        topic = st.text_area(
            "📚 Тема теста",
            placeholder="Например: Python основы, История России, Искусственный интеллект...",
            height=68,
            # max_chars=1000,
            key="topic_text",
            help="Введите тему теста. Поддерживается многострочный ввод."
        )

    with col2:
        num_questions = st.selectbox("🔢 Количество вопросов", options=[5, 10, 15, 20], index=0)

    with col3:
        # Выбор модели
        model_options = {m["id"]: m["name"] for m in available_models if m["available"]}
        if model_options:
            selected_model = st.selectbox(
                "🤖 Модель ИИ",
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x]
            )
        else:
            st.error("❌ Нет доступных моделей")
            selected_model = "local"

    # Показываем статус Gemini, если недоступна
    gemini_available = any(m["id"] == "gemini" and m["available"] for m in available_models)
    # if not gemini_available:
    #     st.info("ℹ️ Gemini API недоступна. Используется локальная модель (заглушка).")

    generate_button = st.button("🚀 Сгенерировать тест", type="primary", use_container_width=True)

    if generate_button and topic:
        logger.info(f"Нажата кнопка генерации теста. Тема: {topic[:100]}...")
        with st.spinner(f"🔄 Генерируем тест через {model_options[selected_model]}... (до 30 секунд)"):
            result = generate_quiz_with_model(topic, num_questions, selected_model)

            if result["success"]:
                quiz_data = result["data"]
                quiz_text = quiz_data["quiz_text"]
                model_used = quiz_data.get("used_model", selected_model)
                request_id = quiz_data.get("request_id", "unknown")

                session = get_db_session()
                try:
                    generation_id = save_generation(
                        session=session,
                        user_id=st.session_state["user_id"],
                        topic=topic,
                        num_questions=num_questions,
                        quiz_text=quiz_text,
                        model_used=model_used
                    )
                    session.commit()
                    st.session_state["last_generation_id"] = generation_id
                    logger.info(f"Тест сохранён в БД: generation_id={generation_id}, request_id={request_id}")
                finally:
                    session.close()

                st.success(f"✅ Тест успешно сгенерирован! (Модель: {model_used})")
                st.markdown("---")
                st.markdown("### 📋 Сгенерированный тест")
                st.text_area("Текст теста", quiz_text, height=400)
            else:
                logger.error(f"Ошибка генерации: {result['error']}")
                st.error(f"❌ Ошибка генерации: {result['error']}")

    elif generate_button and not topic:
        logger.warning("Попытка генерации с пустой темой")
        st.warning("⚠️ Пожалуйста, введите тему теста")

elif menu == "📜 История генераций":
    st.title("📜 История ваших тестов")

    generations = get_user_generations(st.session_state["user_id"])

    if not generations:
        st.info("📭 У вас пока нет сгенерированных тестов.")
    else:
        # Группируем по parent_id (если parent_id None, используем id)
        latest_versions = {}

        for gen in generations:
            # Определяем корневой ID (если parent_id None, то это корневой тест)
            root_id = gen.parent_id if gen.parent_id else gen.id

            # Если для этого root_id еще нет записи или текущая версия новее
            if root_id not in latest_versions or gen.version > latest_versions[root_id].version:
                latest_versions[root_id] = gen

        # Формируем данные для таблицы только из последних версий
        history_data = []
        for gen in latest_versions.values():
            model_name = "Gemini" if gen.model_used == "gemini" else "Локальная"
            if gen.model_used and "gemini" in gen.model_used:
                model_name = "Gemini"

            history_data.append({
                "ID": gen.id,
                "Тема": gen.topic[:50] + ("..." if len(gen.topic) > 50 else ""),
                "Вопросов": gen.num_questions,
                "Версия": gen.version,
                "Модель": model_name,
                "Дата": gen.created_at.strftime("%Y-%m-%d %H:%M")
            })

        st.dataframe(pd.DataFrame(history_data), use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Просмотр и перегенерация")

        # Получаем доступные модели
        available_models = get_available_models()
        model_options = {m["id"]: m["name"] for m in available_models if m["available"]}

        # Четыре колонки: выбор ID, выбор версии, выбор модели, кнопка
        col_select, col_version, col_model, col_button = st.columns([2, 2, 2, 1])

        with col_select:
            selected_id = st.selectbox(
                "📋 Выберите тест",
                options=[g.id for g in generations],
                format_func=lambda x: f"#{x} - {next(g.topic[:40] for g in generations if g.id == x)}..."
            )

        if selected_id:
            selected_gen = get_generation_by_id(selected_id)

            # Получаем все версии для выбранного теста
            versions = get_all_versions(selected_id)
            version_options = {
                v.id: f"Версия {v.version} ({'Gemini' if v.model_used == 'gemini' else 'Local'}) - {v.created_at.strftime('%d.%m.%Y %H:%M')}"
                for v in versions
            }

            with col_version:
                selected_version_id = st.selectbox(
                    "📚 Версия для перегенерации",
                    options=list(version_options.keys()),
                    format_func=lambda x: version_options[x],
                    key="version_for_regenerate"
                )

            with col_model:
                reg_model = st.selectbox(
                    "🤖 Новая модель",
                    options=list(model_options.keys()),
                    format_func=lambda x: model_options.get(x, x),
                    key="regenerate_model_select"
                )

            with col_button:
                st.write("")
                st.write("")
                regenerate_clicked = st.button("🔄 Перегенерировать", type="primary", use_container_width=True)

            # Если нажата кнопка перегенерации
            if regenerate_clicked and selected_version_id:
                # Получаем выбранную версию для перегенерации
                source_version = get_generation_by_id(selected_version_id)

                with st.spinner(
                        f"🔄 Генерируем новую версию через {model_options.get(reg_model, reg_model)} на основе версии {source_version.version}..."):
                    result = generate_quiz_regenerate(
                        topic=source_version.topic,
                        num_questions=source_version.num_questions,
                        old_quiz_text=source_version.quiz_text,
                        model=reg_model
                    )

                    if result["success"]:
                        new_quiz = result["data"]["quiz_text"]
                        model_used = result["data"].get("used_model", reg_model)

                        root_id = source_version.parent_id if source_version.parent_id else source_version.id
                        session = get_db_session()
                        try:
                            new_id = save_generation(
                                session=session,
                                user_id=st.session_state["user_id"],
                                topic=source_version.topic,
                                num_questions=source_version.num_questions,
                                quiz_text=new_quiz,
                                parent_id=root_id,
                                model_used=model_used
                            )
                            session.commit()
                            st.success(f"✅ Создана новая версия! ID: {new_id}")
                            st.rerun()
                        finally:
                            session.close()
                    else:
                        st.error(f"❌ Ошибка: {result['error']}")

            # Показываем информацию о выбранном тесте
            st.markdown("---")

            # Показываем выбранную версию (для просмотра)
            if selected_version_id:
                display_version = get_generation_by_id(selected_version_id)
                if display_version:
                    st.markdown(f"### 📄 Тема: {display_version.topic}")

                    col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
                    with col_meta1:
                        model_display = "Gemini" if display_version.model_used == "gemini" else "Локальная"
                        st.caption(f"🤖 Модель: {model_display}")
                    with col_meta2:
                        st.caption(f"📊 Вопросов: {display_version.num_questions}")
                    with col_meta3:
                        st.caption(f"📌 Версия: {display_version.version}")
                    with col_meta4:
                        st.caption(f"📅 Дата: {display_version.created_at.strftime('%d.%m.%Y %H:%M')}")

                    st.text_area("📋 Текст теста", display_version.quiz_text, height=300, key="display_quiz_text")

                # Показываем все версии с указанием модели
                versions = get_all_versions(selected_id)
                if len(versions) > 1:
                    st.markdown("### 📚 История версий")

                    # Выпадающий список для выбора версии
                    version_options = {
                        v.id: f"Версия {v.version} ({'Gemini' if v.model_used == 'gemini' else 'Локальная'}) - {v.created_at.strftime('%d.%m.%Y %H:%M')}"
                        for v in versions
                    }

                    selected_version_id = st.selectbox(
                        "Выберите версию для просмотра",
                        options=list(version_options.keys()),
                        format_func=lambda x: version_options[x],
                        key="version_selector"
                    )

                    # Показываем выбранную версию
                    if selected_version_id:
                        selected_version = get_generation_by_id(selected_version_id)
                        if selected_version:
                            st.text_area("Текст версии 1:", selected_version.quiz_text, height=300,
                                         key="version_text")

elif menu == "📁 Генерация из файла":
    st.title("📁 Генерация теста из файла")
    st.markdown("Загрузите файл (TXT, PDF, DOCX, CSV), и ИИ создаст тест на основе его содержимого")

    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=['txt', 'pdf', 'docx', 'csv'],
        help="Поддерживаются файлы: .txt, .pdf, .docx, .csv"
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        num_questions = st.selectbox("🔢 Количество вопросов", options=[5, 10, 15, 20], index=0)

    with col2:
        available_models = get_available_models()
        model_options = {m["id"]: m["name"] for m in available_models if m["available"]}
        if model_options:
            selected_model = st.selectbox(
                "🤖 Модель ИИ",
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x]
            )

    if uploaded_file and st.button("🚀 Сгенерировать тест", type="primary"):
        with st.spinner(
                f"🔄 Анализируем файл и генерируем {num_questions} вопросов через {model_options[selected_model]}..."):

            result = generate_quiz_from_file(uploaded_file, num_questions, selected_model)

            if result["success"]:
                quiz_data = result["data"]
                quiz_text = quiz_data["quiz_text"]
                model_used = quiz_data.get("used_model", selected_model)

                # Формируем тему из имени файла (без расширения)
                file_name = uploaded_file.name
                file_name_without_ext = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
                topic_display = f"{file_name}"

                session = get_db_session()
                try:
                    generation_id = save_generation(
                        session=session,
                        user_id=st.session_state["user_id"],
                        topic=topic_display,  # Сохраняем с префиксом "Из файла:"
                        num_questions=num_questions,
                        quiz_text=quiz_text,
                        model_used=model_used
                    )
                    session.commit()
                    st.session_state["last_generation_id"] = generation_id
                    logger.info(f"Тест из файла сохранён в БД: generation_id={generation_id}")
                finally:
                    session.close()

                st.success(f"✅ Тест успешно сгенерирован из файла {uploaded_file.name}! (Модель: {model_used})")
                st.markdown("---")
                st.markdown("### 📋 Сгенерированный тест")
                st.text_area("Текст теста", quiz_text, height=400)
            else:
                st.error(f"❌ Ошибка генерации: {result['error']}")

else:
    st.title("ℹ️ О сервисе")
    st.markdown("""
    ### Генератор учебных тестов на основе ИИ

    **Возможности:**
    - 🎓 Генерация тестов на любую тему
    - 👤 Регистрация и хранение личной истории
    - 🔄 Перегенерация тестов с сохранением версий

    **Технологии:**
    - Frontend: Streamlit
    - Backend: FastAPI + Google Gemini AI
    - База данных: PostgreSQL
    """)

