import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re

# ========== НАСТРОЙКИ ДОСТУПА ==========
VALID_PASSWORD = "secret123"  # Единый пароль для всех
ADMIN_USERNAME = "admin"      # Ваш username для админ-доступа
# =======================================

# ========== НАСТРОЙКИ ПОЧТЫ ==========
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"  # Куда приходят уведомления о регистрациях
# =======================================

# Файл для хранения зарегистрированных пользователей
USERS_FILE = "registered_users.csv"

def init_users_file():
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["Имя", "Username", "Email", "Телефон", "Дата_регистрации"])
        df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")

def save_registration_to_csv(name, username, email, phone):
    init_users_file()
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    
    username = username.strip().lower()
    email = email.strip().lower()
    
    if username in df["Username"].values:
        return False, "username"  # Такой username уже существует
    if email in df["Email"].values:
        return False, "email"     # Такой email уже зарегистрирован
    
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
            "phone": row["Телефон"]
        }
    return None

def send_welcome_email(user_email, username, name):
    """Отправляет приветственное письмо пользователю после регистрации"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = user_email
        msg['Subject'] = "Добро пожаловать в Аналитик WB!"
        
        body = f"""
        <h2>Здравствуйте, {name}!</h2>
        <p>Вы успешно зарегистрировались в сервисе <strong>«Аналитик WB»</strong>.</p>
        <p><strong>Ваши данные для входа:</strong></p>
        <ul>
            <li><strong>Username (логин):</strong> {username}</li>
            <li><strong>Пароль:</strong> secret123</li>
        </ul>
        <p>🔗 <a href="https://wb-analytics-igor1984-23.streamlit.app">Перейти в сервис</a></p>
        <p>Сервис автоматически анализирует отчёты Wildberries и показывает убыточные товары.</p>
        <p>Если у вас возникнут вопросы или предложения — просто отправьте обратную связь в боковой панели сервиса или ответьте на это письмо.</p>
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
        print(f"Ошибка отправки welcome email: {e}")
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

def send_feedback_email(user_name, username, user_email, feedback_type, feedback_text):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"[ОС] {feedback_type}: {user_name}"
        
        body = f"""
        <h3>Обратная связь от пользователя</h3>
        <p><strong>Время:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Имя:</strong> {user_name}</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Email:</strong> {user_email}</p>
        <p><strong>Тип:</strong> {feedback_type}</p>
        <hr>
        <p><strong>Сообщение:</strong></p>
        <p>{feedback_text}</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки feedback: {e}")
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

# Инициализация состояния
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

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
        st.markdown("Заполните форму — на почту придут данные для входа.")
        
        st.markdown("---")
        
        with st.form("registration_form"):
            name = st.text_input("Ваше имя *")
            username = st.text_input("Придумайте username (логин) *", help="Только латиница, цифры, без пробелов. Например: ivan2026")
            email = st.text_input("Ваш email *", help="На него придут данные для входа")
            phone = st.text_input("Телефон (необязательно)")
            
            submitted = st.form_submit_button("Зарегистрироваться")
            
            if submitted:
                # Валидация
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
                        # Отправляем письма
                        send_welcome_email(email, username, name)
                        send_admin_notification(name, username, email, phone)
                        
                        st.success("✅ Регистрация успешна! Проверьте почту — там данные для входа.")
                        st.info(f"На почту {email} отправлено приветственное письмо с username и паролем.")
    
    # ========== ВХОД ДЛЯ ЗАРЕГИСТРИРОВАННЫХ ==========
    else:
        st.markdown("#### Введите данные для входа")
        
        username_input = st.text_input("Username (логин)")
        password_input = st.text_input("Пароль", type="password")
        
        if st.button("Войти"):
            if password_input == VALID_PASSWORD:
                user = get_user_by_username(username_input)
                if user:
                    st.session_state.user_data = user
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Неверный username. Зарегистрируйтесь, если ещё не сделали этого.")
            else:
                st.error("Неверный пароль")
    
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
# ... (основная часть остаётся без изменений) ...

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
    
    # Кнопка скачивания списка пользователей (только для админа)
    if st.session_state.user_data['username'] == ADMIN_USERNAME:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "rb") as f:
                st.download_button(
                    label="📥 Скачать список пользователей (CSV)",
                    data=f,
                    file_name="registered_users.csv",
                    mime="text/csv"
                )
    
    st.markdown("---")
    
    with st.expander("💬 Отправить обратную связь"):
        feedback_type = st.selectbox(
            "Тип обращения",
            ["💡 Идея", "🐛 Баг", "❓ Вопрос", "📝 Другое"]
        )
        feedback_text = st.text_area("Ваше сообщение", height=150)
        
        if st.button("📨 Отправить", type="primary"):
            if feedback_text.strip():
                with st.spinner("Отправка..."):
                    sent = send_feedback_email(
                        st.session_state.user_data["name"],
                        st.session_state.user_data["username"],
                        st.session_state.user_data["email"],
                        feedback_type,
                        feedback_text
                    )
                if sent:
                    st.success("✅ Спасибо! Ваше сообщение отправлено.")
                else:
                    st.error("❌ Ошибка отправки. Попробуйте позже.")
            else:
                st.error("Пожалуйста, напишите сообщение")

st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.user_data['name']}**!")

st.subheader("💰 Введите дополнительные расходы")

col1, col2 = st.columns(2)
with col1:
    purchase_per_unit = st.number_input(
        "Закупка (себестоимость 1 единицы)", 
        min_value=0.0, 
        value=300.0,
        step=50.0
    )
with col2:
    ad_cost_total = st.number_input(
        "Реклама (общая сумма за период)", 
        min_value=0.0, 
        value=1000.0,
        step=500.0
    )

st.markdown("---")
st.write("Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров.")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        if st.button("🧮 Рассчитать реальную прибыль", type="primary"):
            with st.spinner("Идёт расчёт..."):
                result_df = calculate_unit_economy(df, purchase_per_unit, ad_cost_total)
            
            if result_df is not None and not result_df.empty:
                st.subheader("📈 Результат расчёта")
                
                def highlight_loss(row):
                    return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
                
                st.dataframe(result_df.style.apply(highlight_loss, axis=1))
                
                st.subheader("🔴 Убыточные товары")
                loss_df = result_df[result_df['Убыточен?'] == 'ДА']
                if not loss_df.empty:
                    st.dataframe(loss_df)
                else:
                    st.info("✅ Убыточных товаров не найдено")
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='Юнит-экономика', index=False)
                st.download_button(
                    label="📥 Скачать отчёт (Excel)",
                    data=output.getvalue(),
                    file_name="unit_economy_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Не удалось выполнить расчёт. Проверьте структуру файла.")
    except Exception as e:
        st.error(f"Ошибка при обработке файла: {e}")

st.markdown("---")
st.caption("Автоматический расчёт юнит-экономики по отчётам WB")
