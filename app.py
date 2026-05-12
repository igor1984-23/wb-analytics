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
ADMIN_USERNAME = "gritzner"

BASE_URL = "https://wb-analytics-mqxvuxfayh5h5s3nqbq3ti.streamlit.app"

SMTP_SERVER = "smtp.mail.ru"
SMTP_PORT = 587
EMAIL_LOGIN = "wb_analitics@mail.ru"
EMAIL_PASSWORD = "cyoqc6SpdSIUzRkjp3He"
RECIPIENT_EMAIL = "wb_analitics@mail.ru"
# ================================

USERS_FILE = "users_data.csv"

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
        <p>Вы успешно зарегистрировались.</p>
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

def calculate_unit_economy(df, purchase_per_unit, acquirer_rate, tax_rate, tax_type, sku_ad_manual):
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
        return None, None
    
    for col in [amount_col, logistics_col, storage_col, penalties_col, other_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    result = []
    total_sales_count = 0
    total_sales_amount = 0
    total_net_revenue = 0
    total_purchase = 0
    total_ad_cost = 0
    total_acquirer = 0
    total_logistics = 0
    total_returns_amount = 0
    total_storage = 0
    total_penalties = 0
    
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
        
        acquirer_cost = sales_amount * (acquirer_rate / 100)
        ad_cost_for_sku = sku_ad_manual.get(sku, 0)
        
        final_profit = net_revenue - purchase_total - ad_cost_for_sku - acquirer_cost
        
        total_sales_count += sales_count
        total_sales_amount += sales_amount
        total_net_revenue += net_revenue
        total_purchase += purchase_total
        total_ad_cost += ad_cost_for_sku
        total_acquirer += acquirer_cost
        total_logistics += logistics_sum
        total_returns_amount += returns_amount
        total_storage += storage_sum
        total_penalties += penalties_sum
        
        drr_percent = (ad_cost_for_sku / sales_amount * 100) if sales_amount > 0 else 0
        return_rate = (returns_count / sales_count * 100) if sales_count > 0 else 0
        margin_percent = (final_profit / sales_amount * 100) if sales_amount > 0 else 0
        
        if final_profit >= 0:
            if margin_percent < 15:
                hint = f"✅ Товар прибыльный ({final_profit:.0f} ₽, маржа {margin_percent:.1f}%). Маржа низкая. Рекомендуем поднять цену на 10% или найти поставщика дешевле."
            else:
                hint = f"✅ Товар прибыльный ({final_profit:.0f} ₽, маржа {margin_percent:.1f}%). Можно увеличить закупку или протестировать повышение цены."
        else:
            reasons = []
            recommendations = []
            
            if ad_cost_for_sku > 0 and drr_percent > 30:
                reasons.append(f"реклама {ad_cost_for_sku:.0f} ₽ ({drr_percent:.1f}% от выручки)")
                recommendations.append("Отключите рекламу по этому SKU на неделю")
            
            if returns_count > 0 and return_rate > 20:
                reasons.append(f"возвраты: {returns_count} шт. ({return_rate:.1f}% от продаж)")
                recommendations.append("Проверьте качество товара, фото и описание")
            
            if logistics_sum > 0:
                reasons.append(f"логистика {logistics_sum:.0f} ₽")
                recommendations.append("Рассмотрите FBS или увеличьте цену")
            
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
            "Выручка WB": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Чистая выручка WB": net_revenue,
            "Закупка": purchase_total,
            "Реклама": ad_cost_for_sku,
            "Эквайринг": acquirer_cost,
            "Реальная прибыль": final_profit,
            "Убыточен?": "ДА" if final_profit < 0 else "НЕТ",
            "Комментарий": hint
        })
    
    # Итоговая сводка
    total_expenses = total_purchase + total_ad_cost + total_acquirer + total_logistics + abs(total_returns_amount) + total_storage + total_penalties
    profit_before_tax = total_net_revenue - total_expenses
    
    if tax_type == "УСН 6% (доходы)":
        tax = total_sales_amount * 0.06
    else:
        tax = profit_before_tax * (tax_rate / 100) if profit_before_tax > 0 else 0
    
    net_profit = profit_before_tax - tax
    
    summary = {
        "total_sales": total_sales_count,
        "total_revenue": total_sales_amount,
        "total_net_revenue": total_net_revenue,
        "total_purchase": total_purchase,
        "total_ad": total_ad_cost,
        "total_acquirer": total_acquirer,
        "total_logistics": total_logistics,
        "total_returns": abs(total_returns_amount),
        "total_storage": total_storage,
        "total_penalties": total_penalties,
        "profit_before_tax": profit_before_tax,
        "tax": tax,
        "net_profit": net_profit,
        "tax_type": tax_type,
        "tax_rate": tax_rate
    }
    
    return pd.DataFrame(result), summary

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
    
    else:
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

# ========== БОКОВАЯ ПАНЕЛЬ ==========
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
    
    if st.session_state.user_data['username'] == ADMIN_USERNAME and os.path.exists(USERS_FILE):
        with open(USERS_FILE, "rb") as f:
            st.download_button("📥 Скачать список пользователей", data=f, file_name="users_data.csv", mime="text/csv", use_container_width=True)
    
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
    purchase_per_unit = st.number_input("Закупка (себестоимость 1 ед.)", min_value=0.0, value=300.0, step=50.0)

st.subheader("💳 Налоги и комиссии")

col3, col4, col5 = st.columns(3)
with col3:
    acquirer_rate = st.number_input("Эквайринг, %", min_value=0.0, value=1.5, step=0.1, help="Комиссия за приём платежей (обычно 1.5-2.5%)")
with col4:
    tax_type = st.selectbox("Система налогообложения", ["УСН 6% (доходы)", "УСН 15% (доходы-расходы)"])
with col5:
    tax_rate = 6.0 if tax_type == "УСН 6% (доходы)" else 15.0
    st.metric("Ставка налога", f"{tax_rate:.0f}%")

st.markdown("---")
st.write("Загрузите отчёт WB в формате Excel")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Файл загружен, строк: {len(df)}")
        
        # Определяем уникальные артикулы
        temp_df = df.copy()
        temp_df.columns = temp_df.columns.str.strip().str.lower()
        sku_col = None
        for col in temp_df.columns:
            if "артикул" in col or "sku" in col:
                sku_col = col
                break
        
        unique_skus = temp_df[sku_col].unique().tolist() if sku_col else []
        
        st.subheader("🎯 Реклама по каждому товару")
        st.info("Введите сумму рекламы для каждого товара. Если поле оставить пустым — реклама считается 0.")
        
        sku_ad_manual = {}
        for sku in unique_skus:
            ad_val = st.number_input(f"Реклама для {sku}", min_value=0.0, value=0.0, step=100.0, key=f"ad_{sku}")
            if ad_val > 0:
                sku_ad_manual[sku] = ad_val
        
        if st.button("🧮 Рассчитать реальную прибыль", type="primary", use_container_width=True):
            with st.spinner("Идёт расчёт..."):
                result_df, summary = calculate_unit_economy(df, purchase_per_unit, acquirer_rate, tax_rate, tax_type, sku_ad_manual)
            
            if result_df is not None and not result_df.empty:
                # Итоговая сводка
                st.subheader("📊 Итоговая сводка")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("📦 Продано, шт", f"{summary['total_sales']:,}".replace(",", " "))
                    st.metric("💰 Выручка брутто", f"{summary['total_revenue']:,.0f} ₽".replace(",", " "))
                with col_b:
                    total_expenses_fmt = summary['total_purchase'] + summary['total_ad'] + summary['total_acquirer'] + summary['total_logistics'] + summary['total_returns'] + summary['total_storage'] + summary['total_penalties']
                    st.metric("📦 Расходы всего", f"{total_expenses_fmt:,.0f} ₽".replace(",", " "))
                    st.metric("💰 Закупка", f"{summary['total_purchase']:,.0f} ₽".replace(",", " "))
                    st.metric("📢 Реклама", f"{summary['total_ad']:,.0f} ₽".replace(",", " "))
                with col_c:
                    st.metric("🚚 Логистика", f"{summary['total_logistics']:,.0f} ₽".replace(",", " "))
                    st.metric("🔄 Возвраты", f"{summary['total_returns']:,.0f} ₽".replace(",", " "))
                
                st.markdown("---")
                
                col_d, col_e, col_f = st.columns(3)
                with col_d:
                    st.metric("💰 Прибыль до налогов", f"{summary['profit_before_tax']:,.0f} ₽".replace(",", " "))
                with col_e:
                    st.metric("📊 Налог", f"{summary['tax']:,.0f} ₽".replace(",", " "))
                with col_f:
                    st.metric("✅ Чистая прибыль", f"{summary['net_profit']:,.0f} ₽".replace(",", " "))
                
                st.markdown("---")
                st.subheader("📈 Результат по каждому товару")
                
                for idx, row in result_df.iterrows():
                    if row["Убыточен?"] == "ДА":
                        st.markdown(f"🔴 **{row['Артикул']}**")
                        st.info(row["Комментарий"])
                    else:
                        st.markdown(f"🟢 **{row['Артикул']}**")
                        st.success(row["Комментарий"])
                    st.markdown("---")
                
                with st.expander("📋 Показать полную таблицу"):
                    def highlight_loss(row):
                        return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
                    st.dataframe(result_df.style.apply(highlight_loss, axis=1))
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    result_df.to_excel(writer, sheet_name='Юнит-экономика', index=False)
                st.download_button("📥 Скачать отчёт (Excel)", data=output.getvalue(), file_name="unit_economy_result.xlsx")
    except Exception as e:
        st.error(f"Ошибка: {e}")

st.caption("Аналитик WB — автоматический расчёт юнит-экономики по отчётам Wildberries")
