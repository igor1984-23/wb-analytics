import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
import hashlib

# ========== НАСТРОЙКИ ==========
VALID_PASSWORD = "secret123"
ADMIN_USERNAME = "admin"

# ВАША РЕАЛЬНАЯ ССЫЛКА
BASE_URL = "https://wb-analytics-mqxvuxfayh5h5s3nqbq3ti.streamlit.app"

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# ================================

# Единое имя файла (без пробелов, без проблем)
USERS_FILE = "users_data.csv"

# Удаляем старые проблемные файлы
for old_file in ["registered users.csv", "Registered users.csv", "registered_users.csv", "Registered_users.csv"]:
    if os.path.exists(old_file):
        os.remove(old_file)

def init_files():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["Имя", "Username", "Email", "Телефон", "Дата_регистрации"])
        df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")

def get_user_by_username(username):
    username = username.strip().lower()
    if not os.path.exists(USERS_FILE):
        return None
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    user_rows = df[df["Username"] == username]
    if not user_rows.empty:
        row = user_rows.iloc[0]
        return {
            "name": row["Имя"],
            "username": row["Username"],
            "email": row["Email"],
            "phone": str(row["Телефон"]) if pd.notna(row["Телефон"]) else ""
        }
    return None

def save_registration_to_csv(name, username, email, phone):
    init_files()
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    
    username = username.strip().lower()
    email = email.strip().lower()
    
    if username in df["Username"].values:
        return False, "username"
    if email in df["Email"].values:
        return False, "email"
    
    new_row = pd.DataFrame([{
        "Имя": name,
        "Username": username,
        "Email": email,
        "Телефон": phone,
        "Дата_регистрации": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    return True, None

def send_welcome_email(user_email, username, name):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = user_email
        msg['Subject'] = "Добро пожаловать в Аналитик WB"
        body = f"""
        <h2>Здравствуйте, {name}!</h2>
        <p>Вы успешно зарегистрировались в сервисе.</p>
        <p><strong>Ваши данные для входа:</strong></p>
        <ul>
            <li><strong>Username:</strong> {username}</li>
            <li><strong>Пароль:</strong> {VALID_PASSWORD}</li>
        </ul>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def send_admin_notification(name, username, email, phone):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"Новый пользователь: {name}"
        body = f"<p>Имя: {name}<br>Username: {username}<br>Email: {email}<br>Телефон: {phone}</p>"
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def send_feedback_email(user_name, username, user_email, feedback_type, feedback_text):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"[ОС] {feedback_type}: {user_name}"
        body = f"<p>Имя: {user_name}<br>Username: {username}<br>Email: {user_email}<br>Тип: {feedback_type}<br>Сообщение: {feedback_text}</p>"
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def calculate_unit_economy(df, purchase_per_unit, ad_cost_total):
    df.columns = df.columns.str.strip().str.lower()
    sku_col = None
    doc_type_col = None
    amount_col = None
    logistics_col = None
    storage_col = None
    penalties_col = None
    other_col = None
    
    for col in df.columns:
        if "артикул" in col or "sku" in col:
            sku_col = col
        if "тип документа" in col or "тип" in col:
            doc_type_col = col
        if "перечислению" in col:
            amount_col = col
        if "логистик" in col:
            logistics_col = col
        if "хранен" in col:
            storage_col = col
        if "штраф" in col:
            penalties_col = col
        if "прочие" in col or "удержан" in col:
            other_col = col
    
    if not all([sku_col, doc_type_col, amount_col, logistics_col, storage_col, penalties_col, other_col]):
        st.error("Не найдены нужные колонки")
        return None
    
    for col in [amount_col, logistics_col, storage_col, penalties_col, other_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    result = []
    for sku in df[sku_col].unique():
        sku_data = df[df[sku_col] == sku]
        sales = sku_data[sku_data[doc_type_col].str.contains("продажа", case=False, na=False)]
        sales_count = len(sales)
        sales_amount = sales[amount_col].sum()
        returns = sku_data[sku_data[doc_type_col].str.contains("возврат", case=False, na=False)]
        returns_amount = returns[amount_col].sum()
        logistics_sum = sku_data[logistics_col].sum()
        storage_sum = sku_data[storage_col].sum()
        penalties_sum = sku_data[penalties_col].sum()
        other_sum = sku_data[other_col].sum()
        total_wb_costs = logistics_sum + storage_sum + penalties_sum + other_sum
        net_revenue = sales_amount + returns_amount - total_wb_costs
        purchase_total = sales_count * purchase_per_unit
        final_profit = net_revenue - purchase_total - ad_cost_total
        
        if final_profit >= 0:
            hint = f"✅ Товар прибыльный. Реальная прибыль: {final_profit:.0f} ₽"
        else:
            hint = f"❌ Убыток: {final_profit:.0f} ₽. Проверьте расходы."
        
        result.append({
            "Артикул": sku,
            "Продано, шт": sales_count,
            "Выручка WB": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Закупка": purchase_total,
            "Реклама": ad_cost_total,
            "Реальная прибыль": final_profit,
            "Убыточен?": "ДА" if final_profit < 0 else "НЕТ",
            "Комментарий": hint
        })
    
    return pd.DataFrame(result)

# ========== ЗАПУСК ==========
init_files()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

if not st.session_state.authenticated:
    st.title("📊 Аналитик Wildberries")
    mode = st.radio("", ["🔐 Я новый пользователь", "👋 Я уже зарегистрирован"], horizontal=True)
    
    if mode == "🔐 Я новый пользователь":
        with st.form("reg"):
            name = st.text_input("Имя")
            username = st.text_input("Username (логин)")
            email = st.text_input("Email")
            phone = st.text_input("Телефон (необязательно)")
            if st.form_submit_button("Зарегистрироваться"):
                if name and username and email:
                    ok, err = save_registration_to_csv(name, username, email, phone)
                    if ok:
                        send_welcome_email(email, username, name)
                        send_admin_notification(name, username, email, phone)
                        st.session_state.user_data = {"name": name, "username": username, "email": email, "phone": phone}
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error(f"Ошибка: {err} уже используется")
                else:
                    st.error("Заполните имя, username и email")
    else:
        username = st.text_input("Username")
        password = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            if password == VALID_PASSWORD:
                user = get_user_by_username(username)
                if user:
                    st.session_state.user_data = user
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Неверный username")
            else:
                st.error("Неверный пароль")
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
with st.sidebar:
    st.markdown(f"### {st.session_state.user_data['name']}")
    st.markdown(f"@{st.session_state.user_data['username']}")
    st.markdown(f"{st.session_state.user_data['email']}")
    if st.button("Выйти"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    with st.expander("Обратная связь"):
        t = st.selectbox("Тип", ["Идея", "Баг", "Вопрос"])
        txt = st.text_area("Сообщение")
        if st.button("Отправить") and txt:
            send_feedback_email(st.session_state.user_data['name'], st.session_state.user_data['username'], st.session_state.user_data['email'], t, txt)
            st.success("Отправлено!")

st.title("Аналитик WB")
st.write(f"Здравствуйте, {st.session_state.user_data['name']}!")

purchase = st.number_input("Закупка (1 ед.)", value=300.0)
ad = st.number_input("Реклама (всего)", value=1000.0)
file = st.file_uploader("Отчёт WB", type=["xlsx", "xls"])

if file:
    df = pd.read_excel(file)
    if st.button("Рассчитать"):
        res = calculate_unit_economy(df, purchase, ad)
        if res is not None:
            for _, row in res.iterrows():
                if row["Убыточен?"] == "ДА":
                    st.markdown(f"🔴 **{row['Артикул']}**: {row['Комментарий']}")
                else:
                    st.markdown(f"🟢 **{row['Артикул']}**: {row['Комментарий']}")
            out = io.BytesIO()
            res.to_excel(out, index=False)
            st.download_button("Скачать Excel", out.getvalue(), "report.xlsx")
