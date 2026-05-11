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
import urllib.parse

# ========== НАСТРОЙКИ ДОСТУПА ==========
VALID_PASSWORD = "secret123"
ADMIN_USERNAME = "admin"
# =======================================

# ========== НАСТРОЙКИ ПОЧТЫ ==========
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# =======================================

# Файлы для хранения данных
USERS_FILE = "registered_users.csv"
VERIFICATION_TOKENS_FILE = "verification_tokens.csv"

# Базовый URL вашего сервиса (замените на свой)
BASE_URL = "https://wb-analytics-igor1984-23.streamlit.app"

def init_files():
    """Создаёт файлы, если их нет"""
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["Имя", "Username", "Email", "Телефон", "Дата_регистрации", "Статус"])
        df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    
    if not os.path.exists(VERIFICATION_TOKENS_FILE):
        df = pd.DataFrame(columns=["Email", "Token", "Создан"])
        df.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")

def generate_token(email):
    """Генерирует уникальный токен для верификации"""
    secret = "your_secret_key_here_change_me"
    data = f"{email}{datetime.now().timestamp()}{secret}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]

def save_verification_token(email, token):
    """Сохраняет токен верификации"""
    init_files()
    df = pd.read_csv(VERIFICATION_TOKENS_FILE, encoding="utf-8-sig")
    
    # Удаляем старые токены для этого email
    df = df[df["Email"] != email]
    
    new_row = pd.DataFrame([{
        "Email": email,
        "Token": token,
        "Создан": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")

def verify_token(token):
    """Проверяет токен и подтверждает email"""
    if not os.path.exists(VERIFICATION_TOKENS_FILE):
        return False
    
    df_tokens = pd.read_csv(VERIFICATION_TOKENS_FILE, encoding="utf-8-sig")
    
    # Ищем токен
    token_row = df_tokens[df_tokens["Token"] == token]
    if token_row.empty:
        return False
    
    email = token_row.iloc[0]["Email"]
    
    # Проверяем, что токен не старше 24 часов
    created = datetime.strptime(token_row.iloc[0]["Создан"], "%Y-%m-%d %H:%M:%S")
    if (datetime.now() - created).total_seconds() > 86400:  # 24 часа
        return False
    
    # Обновляем статус пользователя
    df_users = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    df_users.loc[df_users["Email"] == email, "Статус"] = "confirmed"
    df_users.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    
    # Удаляем использованный токен
    df_tokens = df_tokens[df_tokens["Token"] != token]
    df_tokens.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")
    
    return True

def is_email_confirmed(email):
    """Проверяет, подтверждён ли email"""
    if not os.path.exists(USERS_FILE):
        return False
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    user_rows = df[df["Email"] == email]
    if not user_rows.empty:
        return user_rows.iloc[0]["Статус"] == "confirmed"
    return False

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
        "Дата_регистрации": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Статус": "pending"
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    return True, None

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
            "phone": row["Телефон"],
            "status": row["Статус"]
        }
    return None

def send_verification_email(user_email, username, name, token):
    """Отправляет письмо со ссылкой для подтверждения"""
    try:
        verification_link = f"{BASE_URL}?verify={token}"
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = user_email
        msg['Subject'] = "Подтвердите регистрацию в Аналитик WB"
        
        body = f"""
        <h2>Здравствуйте, {name}!</h2>
        <p>Вы зарегистрировались в сервисе <strong>«Аналитик WB»</strong>.</p>
        <p>Для завершения регистрации <strong>подтвердите ваш email</strong>, перейдя по ссылке:</p>
        <p><a href="{verification_link}" style="background-color:#4CAF50; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">Подтвердить email</a></p>
        <p>или скопируйте ссылку в браузер: <br>{verification_link}</p>
        <p><strong>Ваши данные для входа после подтверждения:</strong></p>
        <ul>
            <li><strong>Username:</strong> {username}</li>
            <li><strong>Пароль:</strong> {VALID_PASSWORD}</li>
        </ul>
        <p>Ссылка действительна 24 часа.</p>
        <br>
        <p>С уважением,<br>Команда Аналитик WB</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки verification email: {e}")
        return False

def send_admin_notification(name, username, email, phone):
    """Отправляет уведомление администратору о новой регистрации"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"Новый тестировщик: {name}"
        
        body = f"""
        <h3>Новая регистрация в сервисе «Аналитик WB»</h3>
        <p><strong>Время:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Имя:</strong> {name}</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Телефон:</strong> {phone if phone else "не указан"}</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки admin email: {e}")
        return False

# ========== ОСТАЛЬНЫЕ ФУНКЦИИ ==========
# Функции calculate_unit_economy, send_feedback_email и другие остаются без изменений
# (здесь должен быть весь остальной код из предыдущей версии)

def calculate_unit_economy(df, purchase_per_unit, ad_cost_total):
    # ... (код функции остаётся без изменений)
    pass

def send_feedback_email(user_name, username, user_email, feedback_type, feedback_text):
    # ... (код функции остаётся без изменений)
    pass

# Инициализация состояния
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

# ========== ОБРАБОТКА ССЫЛКИ ПОДТВЕРЖДЕНИЯ ==========
query_params = st.query_params
if "verify" in query_params:
    token = query_params["verify"]
    if verify_token(token):
        st.title("✅ Email подтверждён!")
        st.markdown("Ваша почта успешно подтверждена. Теперь вы можете войти в сервис.")
        st.markdown(f"[👉 Перейти к входу]({BASE_URL})")
        st.stop()
    else:
        st.title("❌ Ошибка подтверждения")
        st.markdown("Ссылка недействительна или истекла. Попробуйте зарегистрироваться заново.")
        st.markdown(f"[👉 Вернуться к регистрации]({BASE_URL})")
        st.stop()

# ========== ВЫБОР РЕЖИМА ==========
if not st.session_state.authenticated:
    st.title("📊 Аналитик Wildberries")
    
    mode = st.radio(
        "У вас уже есть доступ?",
        ["🔐 Я новый пользователь", "👋 Я уже зарегистрирован"],
        horizontal=True
    )
    
    # ========== НОВЫЙ ПОЛЬЗОВАТЕЛЬ ==========
    if mode == "🔐 Я новый пользователь":
        st.markdown("### Добро пожаловать!")
        st.markdown("Заполните форму — на почту придёт ссылка для подтверждения.")
        
        st.markdown("---")
        
        with st.form("registration_form"):
            name = st.text_input("Ваше имя *")
            username = st.text_input("Придумайте username (логин) *", help="Только латиница, цифры, без пробелов")
            email = st.text_input("Ваш email *", help="На него придёт ссылка для подтверждения")
            phone = st.text_input("Телефон (необязательно)")
            
            submitted = st.form_submit_button("Зарегистрироваться")
            
            if submitted:
                errors = []
                if not name:
                    errors.append("Имя")
                if not username:
                    errors.append("Username")
                if not email:
                    errors.append("Email")
                elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                    errors.append("Некорректный email")
                if not re.match(r"^[a-zA-Z0-9_]+$", username):
                    st.error("Username может содержать только латиницу, цифры и нижнее подчёркивание")
                elif errors:
                    st.error(f"Заполните обязательные поля: {', '.join(errors)}")
                else:
                    success, conflict = save_registration_to_csv(name, username, email, phone)
                    if not success:
                        if conflict == "username":
                            st.error(f"Username '{username}' уже занят. Придумайте другой.")
                        elif conflict == "email":
                            st.error(f"Email '{email}' уже зарегистрирован. Войдите или используйте другой email.")
                    else:
                        # Генерируем токен и отправляем письмо
                        token = generate_token(email)
                        save_verification_token(email, token)
                        send_verification_email(email, username, name, token)
                        send_admin_notification(name, username, email, phone)
                        
                        st.success("✅ Регистрация почти завершена!")
                        st.info(f"На почту {email} отправлено письмо со ссылкой для подтверждения.\n\nПерейдите по ссылке в письме, чтобы активировать аккаунт.")
    
    # ========== ВХОД ДЛЯ ЗАРЕГИСТРИРОВАННЫХ ==========
    else:
        st.markdown("#### Введите данные для входа")
        
        username_input = st.text_input("Username (логин)")
        password_input = st.text_input("Пароль", type="password")
        
        if st.button("Войти"):
            if password_input == VALID_PASSWORD:
                user = get_user_by_username(username_input)
                if user:
                    if user["status"] == "confirmed":
                        st.session_state.user_data = user
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.warning("📧 Ваш email не подтверждён. Проверьте почту и перейдите по ссылке из письма.")
                else:
                    st.error("❌ Неверный username. Зарегистрируйтесь, если ещё не сделали этого.")
            else:
                st.error("Неверный пароль")
    
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС (после входа) ==========
# ... (основная часть остаётся без изменений) ...
st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.user_data['name']}**!")
# ... (весь остальной код интерфейса)
