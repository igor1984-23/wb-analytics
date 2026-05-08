import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# Инициализация состояния
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "registered" not in st.session_state:
    st.session_state.registered = False
if "visitor_name" not in st.session_state:
    st.session_state.visitor_name = ""
if "visitor_tg" not in st.session_state:
    st.session_state.visitor_tg = ""
if "visitor_contact" not in st.session_state:
    st.session_state.visitor_contact = ""

st.set_page_config(page_title="Аналитик WB", page_icon="📊")

# ========== ФОРМА РЕГИСТРАЦИИ ==========
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
                # Отправляем на почту
                email_sent = send_registration_email(name, tg_username, contact)
                
                if email_sent:
                    st.success("✅ Спасибо! Данные отправлены. Теперь вы можете войти в сервис.")
                else:
                    st.warning("⚠️ Данные сохранены, но письмо не отправилось. Вход всё равно открыт.")
                
                st.session_state.visitor_name = name
                st.session_state.visitor_tg = tg_username
                st.session_state.visitor_contact = contact
                st.session_state.registered = True
                st.rerun()
            else:
                st.error("Пожалуйста, заполните все поля")
    
    st.markdown("---")
    st.caption("Ваши данные нужны только для обратной связи. Спам не рассылаем.")
    st.stop()

# ========== АВТОРИЗАЦИЯ ==========
if not st.session_state.authenticated:
    st.title("🔐 Вход в сервис")
    st.markdown(f"Добро пожаловать, **{st.session_state.visitor_name}**!")
    
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.visitor_name}**! Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров.")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

# ========== ФУНКЦИЯ РАСЧЁТА ==========
def calculate_unit_economy(df):
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
        
        result.append({
            "Артикул": sku,
            "Продано, шт": sales_count,
            "Выручка WB (брутто)": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Чистая выручка WB": net_revenue,
            "Убыточен?": "ДА" if net_revenue < 0 else "НЕТ"
        })
    
    return pd.DataFrame(result)

# Обработка загруженного файла
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        with st.spinner("Идёт расчёт..."):
            result_df = calculate_unit_economy(df)
        
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
