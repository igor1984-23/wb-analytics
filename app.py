import streamlit as st
import pandas as pd
import io
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re

# ========== НАСТРОЙКИ ==========
VALID_PASSWORD = "secret123"
ADMIN_USERNAME = "admin"

# ВАША РЕАЛЬНАЯ ССЫЛКА
BASE_URL ="https://wb-analytics-mqxvuxfayhh5h5s3nqbq3ti.streamlit.app""

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# ================================

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
        <p><a href="{BASE_URL}">Перейти в сервис</a></p>
        """
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_LOGIN, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки welcome: {e}")
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
        print(f"Ошибка отправки admin: {e}")
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
        returns_count = len(returns)
        returns_amount = returns[amount_col].sum()
        
        logistics_sum = sku_data[logistics_col].sum()
        storage_sum = sku_data[storage_col].sum()
        penalties_sum = sku_data[penalties_col].sum()
        other_sum = sku_data[other_col].sum()
        
        total_wb_costs = logistics_sum + storage_sum + penalties_sum + other_sum
        net_revenue = sales_amount + returns_amount - total_wb_costs
        purchase_total = sales_count * purchase_per_unit
        final_profit = net_revenue - purchase_total - ad_cost_total
        
        # Расчёт процентов
        drr_percent = (ad_cost_total / sales_amount * 100) if sales_amount > 0 else 0
        return_rate = (returns_count / sales_count * 100) if sales_count > 0 else 0
        margin_percent = (final_profit / sales_amount * 100) if sales_amount > 0 else 0
        
        # Генерация умной рекомендации
        if final_profit >= 0:
            if margin_percent < 15:
                hint = f"✅ Товар прибыльный ({final_profit:.0f} ₽, маржа {margin_percent:.1f}%). Маржа низкая. Рекомендуем поднять цену на 10% или найти поставщика дешевле."
            else:
                hint = f"✅ Товар прибыльный ({final_profit:.0f} ₽, маржа {margin_percent:.1f}%). Можно увеличить закупку или протестировать повышение цены."
        else:
            reasons = []
            recommendations = []
            
            if ad_cost_total > 0 and drr_percent > 30:
                reasons.append(f"реклама {ad_cost_total:.0f} ₽ ({drr_percent:.1f}% от выручки)")
                recommendations.append("Отключите рекламу по этому SKU на неделю")
            
            if returns_count > 0 and return_rate > 20:
                reasons.append(f"возвраты: {returns_count} шт. ({return_rate:.1f}% от продаж)")
                recommendations.append("Проверьте качество товара, фото и описание")
            
            if logistics_sum > 0:
                reasons.append(f"логистика {logistics_sum:.0f} ₽")
                recommendations.append("Рассмотрите FBS (доставка со своего склада) или увеличьте цену")
            
            if purchase_total > 0 and margin_percent < -10:
                reasons.append(f"закупка {purchase_total:.0f} ₽")
                recommendations.append("Ищите поставщика дешевле или повышайте цену")
            
            if storage_sum > 0:
                reasons.append(f"хранение {storage_sum:.0f} ₽")
                recommendations.append("Уменьшите остатки, заказывайте меньшую партию")
            
            if not reasons:
                reasons.append("различные расходы")
                recommendations.append("Временно отключите товар и пересчитайте")
            
            reason_text = ", ".join(reasons)
            recommendation_text = " | ".join(recommendations[:2])
            
            hint = f"❌ Убыток: {final_profit:.0f} ₽. Причины: {reason_text}. 🔧 {recommendation_text}."
        
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

# ========== АВТОРИЗАЦИЯ ==========
if not st.session_state.authenticated:
    st.title("📊 Аналитик Wildberries")
    
    mode = st.radio("", ["🔐 Я новый пользователь", "👋 Я уже зарегистрирован"], horizontal=True)
    
    if mode == "🔐 Я новый пользователь":
        with st.form("register_form"):
            name = st.text_input("Имя *")
            username = st.text_input("Username (логин) *", help="Только латиница, цифры и _")
            email = st.text_input("Email *")
            phone = st.text_input("Телефон (необязательно)")
            submitted = st.form_submit_button("Зарегистрироваться", use_container_width=True)
            
            if submitted:
                if not name or not username or not email:
                    st.error("Заполните все обязательные поля")
                elif not re.match(r"^[a-zA-Z0-9_]+$", username):
                    st.error("Username: только латиница, цифры и _")
                elif not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                    st.error("Некорректный email")
                else:
                    ok, err = save_registration_to_csv(name, username, email, phone)
                    if ok:
                        send_welcome_email(email, username, name)
                        send_admin_notification(name, username, email, phone)
                        st.session_state.user_data = {
                            "name": name,
                            "username": username,
                            "email": email,
                            "phone": phone
                        }
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error(f"Ошибка: {err} уже используется")
    
    else:  # режим входа
        with st.form("login_form"):
            username = st.text_input("Username (логин)")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти", use_container_width=True)
            
            if submitted:
                if password == VALID_PASSWORD:
                    user = get_user_by_username(username)
                    if user:
                        st.session_state.user_data = user
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("❌ Неверный username")
                else:
                    st.error("❌ Неверный пароль")
    
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС (после входа) ==========
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user_data['name']}")
    st.markdown(f"🔑 {st.session_state.user_data['username']}")
    st.markdown(f"📧 {st.session_state.user_data['email']}")
    if st.session_state.user_data.get('phone'):
        st.markdown(f"📱 {st.session_state.user_data['phone']}")
    st.markdown("---")
    
    if st.button("🚪 Выйти", use_container_width=True):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    
    # Кнопка скачивания списка пользователей (только для админа)
    if st.session_state.user_data['username'] == ADMIN_USERNAME and os.path.exists(USERS_FILE):
        with open(USERS_FILE, "rb") as f:
            st.download_button(
                label="📥 Скачать список пользователей",
                data=f,
                file_name="users_data.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    st.markdown("---")
    
    with st.expander("💬 Обратная связь"):
        feedback_type = st.selectbox("Тип", ["💡 Идея", "🐛 Баг", "❓ Вопрос", "📝 Другое"])
        feedback_text = st.text_area("Сообщение", height=100)
        if st.button("📨 Отправить", use_container_width=True) and feedback_text.strip():
            send_feedback_email(
                st.session_state.user_data['name'],
                st.session_state.user_data['username'],
                st.session_state.user_data['email'],
                feedback_type,
                feedback_text
            )
            st.success("✅ Отправлено!")

# ========== ОСНОВНОЙ КОНТЕНТ ==========
st.title("📊 Аналитик Wildberries")
st.write(f"Здравствуйте, **{st.session_state.user_data['name']}**!")

st.subheader("💰 Введите дополнительные расходы")

col1, col2 = st.columns(2)
with col1:
    purchase_per_unit = st.number_input(
        "Закупка (себестоимость 1 единицы)",
        min_value=0.0,
        value=300.0,
        step=50.0,
        help="Сколько вы платите за одну штуку товара поставщику"
    )
with col2:
    ad_cost_total = st.number_input(
        "Реклама (общая сумма за период)",
        min_value=0.0,
        value=1000.0,
        step=500.0,
        help="Сколько вы потратили на рекламу за эту неделю"
    )

st.markdown("---")
st.write("Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров.")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Файл загружен, строк: {len(df)}")
        
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        if st.button("🧮 Рассчитать реальную прибыль", type="primary", use_container_width=True):
            with st.spinner("Идёт расчёт..."):
                result_df = calculate_unit_economy(df, purchase_per_unit, ad_cost_total)
            
            if result_df is not None and not result_df.empty:
                st.subheader("📈 Результат расчёта")
                
                # Отображаем каждый товар с рекомендацией
                for idx, row in result_df.iterrows():
                    if row["Убыточен?"] == "ДА":
                        st.markdown(f"🔴 **{row['Артикул']}**")
                        st.info(row["Комментарий"])
                    else:
                        st.markdown(f"🟢 **{row['Артикул']}**")
                        st.success(row["Комментарий"])
                    st.markdown("---")
                
                # Полная таблица под раскрывающимся блоком
                with st.expander("📋 Показать полную таблицу со всеми данными"):
                    def highlight_loss(row):
                        return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
                    st.dataframe(result_df.style.apply(highlight_loss, axis=1))
                
                # Кнопка скачать
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='Юнит-экономика', index=False)
                st.download_button(
                    label="📥 Скачать отчёт (Excel)",
                    data=output.getvalue(),
                    file_name="unit_economy_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("Не удалось выполнить расчёт. Проверьте структуру файла.")
    except Exception as e:
        st.error(f"Ошибка при обработке файла: {e}")

st.markdown("---")
st.caption("Аналитик WB — автоматический расчёт юнит-экономики по отчётам Wildberries")
