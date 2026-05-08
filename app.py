import streamlit as st
import pandas as pd
import io
import gspread
from google.oauth2.service_account import Credentials

# ========== НАСТРОЙКИ ДОСТУПА ==========
VALID_USERNAME = "analitik"
VALID_PASSWORD = "secret123"
# =======================================

# ========== НАСТРОЙКИ GOOGLE SHEETS (для сбора регистраций) ==========
# ШАГ 1: Создайте сервисный аккаунт в Google Cloud
# ШАГ 2: Поделитесь таблицей с email сервисного аккаунта
# ШАГ 3: Сохраните JSON-ключ как секрет в Streamlit Cloud
# ======================================================================

def save_registration_to_gsheet(name, tg_username, contact):
    """Сохраняет данные регистрации в Google Sheets"""
    try:
        # Загружаем credentials из секретов Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Открываем таблицу по ID (ID берём из секретов)
        sheet = client.open_by_key(st.secrets["sheet_id"]).sheet1
        
        # Добавляем строку
        sheet.append_row([pd.Timestamp.now(), name, tg_username, contact, "active"])
        return True
    except Exception as e:
        print(f"Ошибка сохранения в Google Sheets: {e}")
        return False

# Инициализация состояния
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "registered" not in st.session_state:
    st.session_state.registered = False
if "name" not in st.session_state:
    st.session_state.name = ""
if "tg_username" not in st.session_state:
    st.session_state.tg_username = ""
if "contact" not in st.session_state:
    st.session_state.contact = ""

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

# ========== ФОРМА РЕГИСТРАЦИИ (первый экран) ==========
if not st.session_state.registered:
    st.title("📊 Аналитик Wildberries")
    st.markdown("### Добро пожаловать!")
    st.markdown("Сервис автоматически анализирует отчёты WB и показывает убыточные товары.")
    
    st.markdown("---")
    st.markdown("#### Пожалуйста, представьтесь для получения доступа")
    
    with st.form("registration_form"):
        name = st.text_input("Ваше имя")
        tg_username = st.text_input("Telegram username (или @ник)")
        contact = st.text_input("Email или телефон")
        
        submitted = st.form_submit_button("Получить доступ")
        
        if submitted:
            if name and tg_username and contact:
                # Сохраняем данные в сессию
                st.session_state.name = name
                st.session_state.tg_username = tg_username
                st.session_state.contact = contact
                
                # Сохраняем в Google Sheets
                # save_registration_to_gsheet(name, tg_username, contact)  # Раскомментировать после настройки
                
                st.session_state.registered = True
                st.success("Спасибо! Теперь вы можете войти в сервис.")
                st.rerun()
            else:
                st.error("Пожалуйста, заполните все поля")
    
    st.markdown("---")
    st.caption("Ваши данные нужны только для обратной связи. Спам мы не рассылаем.")
    st.stop()

# ========== АВТОРИЗАЦИЯ (второй экран) ==========
if not st.session_state.authenticated:
    st.title("🔐 Вход в сервис")
    st.markdown(f"Добро пожаловать, **{st.session_state.name}**!")
    
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС (после авторизации) ==========
st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.name}**! Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров.")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        # ... (весь остальной код расчёта остаётся без изменений)
        # Ваша функция calculate_unit_economy и всё остальное
        
    except Exception as e:
        st.error(f"Ошибка при обработке файла: {e}")

st.markdown("---")
st.caption("Автоматический расчёт юнит-экономики по отчётам WB")
