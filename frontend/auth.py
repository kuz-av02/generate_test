import streamlit as st
from db_client import authenticate_user, create_user, get_user_by_username


def show_auth_page():
    st.set_page_config(
        page_title="Генератор тестов",
        page_icon="📝",
        layout="wide"
    )

    st.title("📝 Генератор учебных тестов")
    st.markdown("---")

    tab1, tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Имя пользователя")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")

            if submitted:
                if not username or not password:
                    st.error("Заполните все поля")
                else:
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user_id"] = user.id
                        st.session_state["username"] = user.username
                        st.rerun()
                    else:
                        st.error("Неверное имя пользователя или пароль")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Имя пользователя")
            new_email = st.text_input("Email")
            new_password = st.text_input("Пароль", type="password")
            confirm_password = st.text_input("Подтвердите пароль", type="password")
            submitted = st.form_submit_button("Зарегистрироваться")

            if submitted:
                if not all([new_username, new_email, new_password]):
                    st.error("Заполните все поля")
                elif new_password != confirm_password:
                    st.error("Пароли не совпадают")
                elif get_user_by_username(new_username):
                    st.error("Пользователь с таким именем уже существует")
                else:
                    create_user(new_username, new_email, new_password)
                    st.success("Регистрация успешна! Теперь войдите.")  