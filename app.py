import streamlit as st
import pandas as pd
import io

# ========== НАСТРОЙКИ ДОСТУПА ==========
VALID_USERNAME = "analitik"
VALID_PASSWORD = "secret123"
# =======================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Функция расчёта (принимает словари расходов по каждому артикулу)
def calculate_unit_economy(df, purchase_dict, ad_dict):
    df.columns = df.columns.str.strip().str.lower()
    
    # Поиск колонок
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
        st.error(f"Не найдены колонки. SKU={sku_col}, Тип={doc_type_col}, Сумма={amount_col}")
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
        
        # Берём расходы конкретно для этого артикула (если ввели)
        purchase_total = sales_count * purchase_dict.get(sku, 0.0)
        ad_total = ad_dict.get(sku, 0.0)
        final_profit = net_revenue - purchase_total - ad_total
        
        result.append({
            "Артикул": sku,
            "Продано, шт": sales_count,
            "Выручка WB (брутто)": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Чистая выручка WB": net_revenue,
            "Закупка (всего)": purchase_total,
            "Реклама (всего)": ad_total,
            "Реальная прибыль": final_profit,
            "Убыточен?": "ДА" if final_profit < 0 else "НЕТ"
        })
    
    return pd.DataFrame(result)

# ========== ИНТЕРФЕЙС ==========
st.set_page_config(page_title="Аналитик WB", page_icon="📊")

if not st.session_state.authenticated:
    st.title("🔐 Вход в систему")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    
    if st.button("Войти"):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

st.title("📊 Аналитик Wildberries")
st.write("Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        # Определяем уникальные артикулы
        # Нормализуем названия колонок для поиска колонки с артикулами
        temp_df = df.copy()
        temp_df.columns = temp_df.columns.str.strip().str.lower()
        sku_col = None
        for col in temp_df.columns:
            if "артикул" in col or "sku" in col:
                sku_col = col
                break
        
        if sku_col is None:
            st.error("Не удалось найти колонку с артикулами")
            st.stop()
        
        unique_skus = temp_df[sku_col].unique().tolist()
        
        st.subheader("💰 Введите расходы по каждому товару")
        st.info("Заполните только нужные поля. Если поле оставить пустым — расход будет считаться как 0.")
        
        purchase_dict = {}
        ad_dict = {}
        
        # Создаём таблицу для ввода данных по каждому артикулу
        for sku in unique_skus:
            with st.container():
                st.markdown(f"**{sku}**")
                col1, col2 = st.columns(2)
                with col1:
                    purchase_val = st.number_input(
                        f"Закупка (себест. 1 ед.) — {sku}",
                        min_value=0.0,
                        value=0.0,
                        step=50.0,
                        key=f"purchase_{sku}",
                        help=f"Сколько вы платите за одну штуку {sku}"
                    )
                    if purchase_val > 0:
                        purchase_dict[sku] = purchase_val
                
                with col2:
                    ad_val = st.number_input(
                        f"Реклама (общая за период) — {sku}",
                        min_value=0.0,
                        value=0.0,
                        step=200.0,
                        key=f"ad_{sku}",
                        help=f"Сколько потрачено на рекламу {sku} за эту неделю"
                    )
                    if ad_val > 0:
                        ad_dict[sku] = ad_val
        
        # Кнопка запуска расчёта
        if st.button("🧮 Рассчитать реальную прибыль", type="primary"):
            with st.spinner("Идёт расчёт..."):
                result_df = calculate_unit_economy(df, purchase_dict, ad_dict)
            
            if result_df is not None and not result_df.empty:
                st.subheader("📈 Результат расчёта")
                
                # Подсветка убытков
                def highlight_loss(row):
                    return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
                
                st.dataframe(result_df.style.apply(highlight_loss, axis=1))
                
                st.subheader("🔴 Убыточные товары")
                loss_df = result_df[result_df['Убыточен?'] == 'ДА']
                if not loss_df.empty:
                    st.dataframe(loss_df)
                else:
                    st.info("✅ Убыточных товаров не найдено")
                
                # Кнопка скачать
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
