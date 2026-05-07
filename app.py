import streamlit as st
import pandas as pd
import io

# ========== НАСТРОЙКИ ДОСТУПА (меняй здесь) ==========
VALID_USERNAME = "analitik"
VALID_PASSWORD = "secret123"
# ====================================================

# Инициализация состояния авторизации
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Функция расчета юнит-экономики
def calculate_unit_economy(df):
    # Нормализуем названия колонок (убираем пробелы, приводим к нижнему регистру)
    df.columns = df.columns.str.strip().str.lower()
    
    # Определяем нужные колонки (поиск по ключевым словам)
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
        if "перечислению" in col or "к перечислению" in col:
            amount_col = col
        if "логистик" in col:
            logistics_col = col
        if "хранен" in col:
            storage_col = col
        if "штраф" in col:
            penalties_col = col
        if "прочие" in col or "удержан" in col:
            other_col = col
    
    # Если не нашли все колонки — показываем ошибку
    if not all([sku_col, doc_type_col, amount_col, logistics_col, storage_col, penalties_col, other_col]):
        st.error(f"Не найдены нужные колонки. Найдено: SKU={sku_col}, Тип={doc_type_col}, Сумма={amount_col}, Логистика={logistics_col}, Хранение={storage_col}, Штрафы={penalties_col}, Прочие={other_col}")
        return None
    
    # Преобразуем числовые колонки
    for col in [amount_col, logistics_col, storage_col, penalties_col, other_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Группируем по артикулу и типу документа
    result = []
    
    for sku in df[sku_col].unique():
        sku_data = df[df[sku_col] == sku]
        
        # Продажи
        sales = sku_data[sku_data[doc_type_col].str.contains("продажа", case=False, na=False)]
        sales_count = len(sales)
        sales_amount = sales[amount_col].sum()
        
        # Возвраты
        returns = sku_data[sku_data[doc_type_col].str.contains("возврат", case=False, na=False)]
        returns_amount = returns[amount_col].sum()
        
        # Расходы
        logistics_sum = sku_data[logistics_col].sum()
        storage_sum = sku_data[storage_col].sum()
        penalties_sum = sku_data[penalties_col].sum()
        other_sum = sku_data[other_col].sum()
        
        total_wb_costs = logistics_sum + storage_sum + penalties_sum + other_sum
        
        # Чистая выручка WB
        net_revenue = sales_amount + returns_amount - total_wb_costs
        
        result.append({
            "Артикул": sku,
            "Продано, шт": sales_count,
            "Выручка WB (брутто)": sales_amount,
            "Возвраты": returns_amount,
            "Расходы WB": total_wb_costs,
            "Чистая выручка WB": net_revenue,
            "Убыточен?" : "ДА" if net_revenue < 0 else "НЕТ"
        })
    
    return pd.DataFrame(result)

# ========== ИНТЕРФЕЙС ==========
st.set_page_config(page_title="Аналитик WB", page_icon="📊")

# Страница авторизации
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

# Основной интерфейс (показывается только после авторизации)
st.title("📊 Аналитик Wildberries")
st.write("Загрузите отчёт WB в формате Excel — получите анализ убыточных товаров")

uploaded_file = st.file_uploader("Выберите файл", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success(f"Файл загружен, строк: {len(df)}")
        
        # Показываем первые 5 строк загруженного файла
        with st.expander("📄 Предпросмотр загруженных данных"):
            st.dataframe(df.head())
        
        # Рассчитываем юнит-экономику
        with st.spinner("Идёт расчёт..."):
            result_df = calculate_unit_economy(df)
        
        if result_df is not None and not result_df.empty:
            st.subheader("📈 Результат расчёта")
            
            # Подсвечиваем убытки
            def highlight_loss(row):
                return ['background-color: #ffcccc' if row['Убыточен?'] == 'ДА' else '' for _ in row]
            
            st.dataframe(result_df.style.apply(highlight_loss, axis=1))
            
            # Фильтр по убыточным
            st.subheader("🔴 Убыточные товары")
            loss_df = result_df[result_df['Убыточен?'] == 'ДА']
            if not loss_df.empty:
                st.dataframe(loss_df)
            else:
                st.info("Убыточных товаров не найдено")
            
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
