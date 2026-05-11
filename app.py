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

# ВАША РЕАЛЬНАЯ ССЫЛКА (исправлено)
BASE_URL = "https://wb-analytics-mqxvuxfayh5h5s3nqbq3ti.streamlit.app"

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# ================================

USERS_FILE = "registered_users.csv"
VERIFICATION_TOKENS_FILE = "verification_tokens.csv"

def init_files():
    """Создаёт файлы с нужной структурой"""
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["Имя", "Username", "Email", "Телефон", "Дата_регистрации", "Статус"])
        df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    else:
        # Проверяем, есть ли колонка Статус
        df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
        if "Статус" not in df.columns:
            df["Статус"] = "confirmed"  # Для старых пользователей
            df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    
    if not os.path.exists(VERIFICATION_TOKENS_FILE):
        df = pd.DataFrame(columns=["Email", "Token", "Создан"])
        df.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")

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
            "phone": str(row["Телефон"]) if pd.notna(row["Телефон"]) else "",
            "status": row["Статус"] if "Статус" in df.columns else "confirmed"
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
        "Дата_регистрации": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Статус": "pending"
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    return True, None

def generate_token(email):
    secret = "your_secret_key_change_me_123"
    data = f"{email}{datetime.now().timestamp()}{secret}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]

def save_verification_token(email, token):
    init_files()
    df = pd.read_csv(VERIFICATION_TOKENS_FILE, encoding="utf-8-sig")
    df = df[df["Email"] != email]
    new_row = pd.DataFrame([{"Email": email, "Token": token, "Создан": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")

def verify_token(token):
    if not os.path.exists(VERIFICATION_TOKENS_FILE):
        return False
    df_tokens = pd.read_csv(VERIFICATION_TOKENS_FILE, encoding="utf-8-sig")
    token_row = df_tokens[df_tokens["Token"] == token]
    if token_row.empty:
        return False
    email = token_row.iloc[0]["Email"]
    created = datetime.strptime(token_row.iloc[0]["Создан"], "%Y-%m-%d %H:%M:%S")
    if (datetime.now() - created).total_seconds() > 86400:
        return False
    df_users = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    df_users.loc[df_users["Email"] == email, "Статус"] = "confirmed"
    df_users.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    df_tokens = df_tokens[df_tokens["Token"] != token]
    df_tokens.to_csv(VERIFICATION_TOKENS_FILE, index=False, encoding="utf-8-sig")
    return True

def send_verification_email(user_email, username, name, token):
    try:
        verification_link = f"{BASE_URL}?verify={token}"
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = user_email
        msg['Subject'] = "Подтвердите регистрацию в Аналитик WB"
        body = f"""
        <h2>Здравствуйте, {name}!</h2>
        <p>Для завершения регистрации подтвердите email:</p>
        <p><a href="{verification_link}">Подтвердить email</a></p>
        <p>Username: {username}<br>Пароль: {VALID_PASSWORD}</p>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

def send_admin_notification(name, username, email, phone):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"Новый тестировщик: {name}"
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
        result.append({
            "Артикул": sku,
            "Продано, шт": sales_count,
            "Выручка WB (брутто)": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Чистая выручка WB": net_revenue,
            "Закупка (всего)": purchase_total,
            "Реклама (всего)": ad_cost_total,
            "Реальная прибыль": final_profit,
            "Убыточен?": "ДА" if final_profit < 0 else "НЕТ"
        })
    return pd.DataFrame(result)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
init_files()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

# ========== ПОДТВЕРЖДЕНИЕ ПО ССЫЛКЕ ==========
query_params = st.query_params
if "verify" in query_params:
    token = query_params["verify"]
    if verify_token(token):
        st.title("✅ Email подтверждён!")
        st.markdown("Теперь вы можете войти в сервис.")
        st.markdown(f"[👉 Перейти к входу]({BASE_URL})")
    else:
        st.title("❌ Ошибка")
        st.markdown("Ссылка недействительна или истекла.")
        st.markdown(f"[👉 Вернуться]({BASE_URL})")
    st.stop()

# ========== ВЫБОР РЕЖИМА ==========
if not st.session_state.authenticated:
    st.title("📊 Аналитик Wildberries")
    mode = st.radio("У вас уже есть доступ?", ["🔐 Я новый пользователь", "👋 Я уже зарегистрирован"], horizontal=True)
    
    if mode == "🔐 Я новый пользователь":
        st.markdown("### Добро пожаловать!")
        with st.form("registration_form"):
            name = st.text_input("Ваше имя *")
            username = st.text_input("Придумайте username (логин) *")
            email = st.text_input("Ваш email *")
            phone = st.text_input("Телефон (необязательно)")
            submitted = st.form_submit_button("Зарегистрироваться")
            if submitted:
                if not name or not username or not email:
                    st.error("Заполните обязательные поля")
                elif not re.match(r"^[a-zA-Z0-9_]+$", username):
                    st.error("Username: только латиница, цифры и _")
                elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                    st.error("Некорректный email")
                else:
                    success, conflict = save_registration_to_csv(name, username, email, phone)
                    if not success:
                        if conflict == "username":
                            st.error(f"Username '{username}' уже занят")
                        else:
                            st.error(f"Email '{email}' уже зарегистрирован")
                    else:
                        token = generate_token(email)
                        save_verification_token(email, token)
                        send_verification_email(email, username, name, token)
                        send_admin_notification(name, username, email, phone)
                        st.success("✅ Проверьте почту! На указанный email отправлена ссылка для подтверждения.")
    
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
                        st.warning("Email не подтверждён. Проверьте почту.")
                else:
                    st.error("Неверный username")
            else:
                st.error("Неверный пароль")
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_data['name']}")
    st.markdown(f"🔑 {st.session_state.user_data['username']}")
    st.markdown(f"📧 {st.session_state.user_data['email']}")
    if st.session_state.user_data.get('phone'):
        st.markdown(f"📱 {st.session_state.user_data['phone']}")
    st.markdown("---")
    if st.button("🚪 Выйти"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    st.markdown("---")
    if st.session_state.user_data['username'] == ADMIN_USERNAME and os.path.exists(USERS_FILE):
        with open(USERS_FILE, "rb") as f:
            st.download_button("📥 Скачать список пользователей", data=f, file_name="registered_users.csv", mime="text/csv")
    st.markdown("---")
    with st.expander("💬 Отправить обратную связь"):
        feedback_type = st.selectbox("Тип", ["💡 Идея", "🐛 Баг", "❓ Вопрос", "📝 Другое"])
        feedback_text = st.text_area("Сообщение", height=150)
        if st.button("📨 Отправить") and feedback_text.strip():
            send_feedback_email(st.session_state.user_data['name'], st.session_state.user_data['username'], st.session_state.user_data['email'], feedback_type, feedback_text)
            st.success("✅ Отправлено!")

st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.user_data['name']}**!")

st.subheader("💰 Введите расходы")
col1, col2 = st.columns(2)
with col1:
    purchase_per_unit = st.number_input("Закупка (себестоимость 1 ед.)", min_value=0.0, value=300.0, step=50.0)
with col2:
    ad_cost_total = st.number_input("Реклама (общая сумма)", min_value=0.0, value=1000.0, step=500.0)

uploaded_file = st.file_uploader("Загрузите отчёт WB (Excel)", type=["xlsx", "xls"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        if st.button("🧮 Рассчитать"):
            result_df = calculate_unit_economy(df, purchase_per_unit, ad_cost_total)
            if result_df is not None:
                def highlight_loss(row):
                    return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
                st.dataframe(result_df.style.apply(highlight_loss, axis=1))
                loss_df = result_df[result_df['Убыточен?'] == 'ДА']
                if not loss_df.empty:
                    st.subheader("🔴 Убыточные товары")
                    st.dataframe(loss_df)
                else:
                    st.info("✅ Убыточных товаров не найдено")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='Анализ', index=False)
                st.download_button("📥 Скачать отчёт", data=output.getvalue(), file_name="unit_economy.xlsx")
    except Exception as e:
        st.error(f"Ошибка: {e}")

st.caption("Аналитик WB — автоматический расчёт юнит-экономики")
