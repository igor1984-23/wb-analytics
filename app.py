def calculate_unit_economy(df, purchase_per_unit, ad_cost_total, acquirer_rate, tax_rate, tax_type):
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
    
    # ========== РАСПРЕДЕЛЕНИЕ РЕКЛАМЫ ПО ТОВАРАМ ==========
    # Сначала собираем выручку по каждому товару
    sku_revenue = {}
    for sku in df[sku_col].unique():
        sku_data = df[df[sku_col] == sku]
        sales = sku_data[sku_data[doc_type_col].str.contains("продажа", case=False, na=False)]
        sales_amount = sales[amount_col].sum()
        sku_revenue[sku] = sales_amount
    
    total_revenue = sum(sku_revenue.values())
    
    # Распределяем рекламу пропорционально выручке
    sku_ad_cost = {}
    if total_revenue > 0 and ad_cost_total > 0:
        for sku, revenue in sku_revenue.items():
            sku_ad_cost[sku] = ad_cost_total * (revenue / total_revenue)
    else:
        for sku in sku_revenue.keys():
            sku_ad_cost[sku] = 0
    # ======================================================
    
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
        
        # ЭКВАЙРИНГ
        acquirer_cost = sales_amount * (acquirer_rate / 100)
        
        # РЕКЛАМА (индивидуально для каждого товара)
        ad_cost_for_sku = sku_ad_cost.get(sku, 0)
        
        final_profit = net_revenue - purchase_total - ad_cost_for_sku - acquirer_cost
        
        # Накопление для сводки
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
        
        # Расчёт процентов
        drr_percent = (ad_cost_for_sku / sales_amount * 100) if sales_amount > 0 else 0
        return_rate = (returns_count / sales_count * 100) if sales_count > 0 else 0
        margin_percent = (final_profit / sales_amount * 100) if sales_amount > 0 else 0
        
        # Генерация рекомендации
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
            "Реклама (всего)": ad_cost_for_sku,
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
