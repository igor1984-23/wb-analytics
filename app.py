import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import hashlib

# ========== НАСТРОЙКИ ДОСТУПА ==========
VALID_USERNAME = "analitik"
VALID_PASSWORD = "secret123"
# =======================================

# ========== НАСТРОЙКИ ПОЧТЫ ==========
SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# =======================================

# Файл для хранения зарегистрированных пользователей
USERS_FILE = "registered_users.csv"

def init_users_file():
    """Создаёт файл пользователей, если его нет"""
    if not os.path.exists(USERS_FILE):
        df = pd.DataFrame(columns=["Имя", "Telegram", "Контакт", "Дата_регистрации"])
        df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")

def is_user_registered(tg_username):
    """Проверяет, зарегистрирован ли пользователь"""
    if not os.path.exists(USERS_FILE):
        return False
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    return tg_username in df["Telegram"].values

def save_registration_to_csv(name, tg_username, contact):
    """Сохраняет регистрацию в CSV-файл"""
    init_users_file()
    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
    
    # Проверяем, нет ли уже такого пользователя
    if tg_username in df["Telegram"].values:
        return True
    
    new_row = pd.DataFrame([{
        "Имя": name,
        "Telegram": tg_username,
        "Контакт": contact,
        "Дата_регистрации": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(USERS_FILE, index=False, encoding="utf-8-sig")
    return True

def send_registration_email(name, tg_username, contact):
    """Отправляет данные регистрации на почту"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"Новый тестировщик: {name}"
        
        body = f"""
        <h3>Новая регистрация в сервисе «Аналитик WB»</h3>
        <p><strong>Время:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Имя:</strong> {name}</p>
        <p><strong>Telegram:</strong> {tg_username}</p>
        <p><strong>Контакт:</strong> {contact}</p>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False

def send_feedback_email(user_name, user_tg, user_contact, feedback_type, feedback_text):
    """Отправляет обратную связь на почту"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_LOGIN
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"[ОС] {feedback_type}: {user_name}"
        
        body = f"""
        <h3>Обратная связь от пользователя</h3>
        <p><strong>Время:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Имя:</strong> {user_name}</p>
        <p><strong>Telegram:</strong> {user_tg}</p>
        <p><strong>Контакт:</strong> {user_contact}</p>
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

# ========== ФУНКЦИЯ РАСЧЁТА ==========
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

# ========== ВЫБОР РЕЖИМА (НОВЫЙ / ВЕРНУЛСЯ) ==========
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
                    # Сохраняем в CSV
                    save_registration_to_csv(name, tg_username, contact)
                    # Отправляем на почту
                    send_registration_email(name, tg_username, contact)
                    
                    st.session_state.user_data = {
                        "name": name,
                        "tg": tg_username,
                        "contact": contact
                    }
                    st.success("✅ Спасибо! Теперь войдите в сервис.")
                    st.rerun()
                else:
                    st.error("Пожалуйста, заполните все поля")
    
    # ========== ВЕРНУВШИЙСЯ ПОЛЬЗОВАТЕЛЬ ==========
    else:
        st.markdown("#### Введите ваши данные для входа")
        
        tg_input = st.text_input("Telegram username (или @ник)")
        password_input = st.text_input("Пароль сервиса", type="password")
        
        if st.button("Войти"):
            if password_input == VALID_PASSWORD:
                if is_user_registered(tg_input):
                    # Загружаем данные пользователя из CSV
                    df = pd.read_csv(USERS_FILE, encoding="utf-8-sig")
                    user_row = df[df["Telegram"] == tg_input].iloc[0]
                    st.session_state.user_data = {
                        "name": user_row["Имя"],
                        "tg": tg_input,
                        "contact": user_row["Контакт"]
                    }
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Вы не зарегистрированы. Пожалуйста, выберите «Я новый пользователь»")
            else:
                st.error("Неверный пароль")
    
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС (после входа) ==========
# Боковая панель
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_data['name']}")
    st.markdown(f"📱 {st.session_state.user_data['tg']}")
    st.markdown(f"📧 {st.session_state.user_data['contact']}")
    st.markdown("---")
    
    # Кнопка выхода
    if st.button("🚪 Выйти"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    
    # Форма обратной связи
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
                        st.session_state.user_data["tg"],
                        st.session_state.user_data["contact"],
                        feedback_type,
                        feedback_text
                    )
                if sent:
                    st.success("✅ Спасибо! Ваше сообщение отправлено.")
                else:
                    st.error("❌ Ошибка отправки. Попробуйте позже.")
            else:
                st.error("Пожалуйста, напишите сообщение")

# ========== ОСНОВНОЙ КОНТЕНТ ==========
st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.user_data['name']}**!")

# Ручной ввод расходов
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
