from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from data_catalog import ASSETS, CONTROLS, QUALITY_LEVELS, SECTOR_PROFILES
from risk_engine import (
    calculate_risk_table,
    calculate_summary,
    greedy_cost_plan,
    layer_summary,
    marginal_control_effect,
    protection_costs,
)


st.set_page_config(
    page_title="Щит-МСП: калькулятор остаточного риска",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Щит-МСП")
st.subheader("Калькулятор остаточного информационного риска после защитных затрат")

st.markdown(
    """
Инструмент считает не «доходность» информационной безопасности, а **остаточный риск после
превентивных, правовых, обнаруживающих и восстановительных затрат**.  
ИБ здесь рассматривается как защитная функция бизнеса: она не создаёт самостоятельный актив,
а снижает вероятность и тяжесть неплановых потерь.
"""
)

with st.sidebar:
    st.header("1. Профиль МСП")

    sector = st.selectbox("Сфера деятельности", list(SECTOR_PROFILES.keys()), index=0)
    monthly_revenue = st.number_input(
        "Средняя месячная выручка, руб.",
        min_value=100_000,
        max_value=500_000_000,
        value=3_000_000,
        step=100_000,
    )
    online_share = st.slider("Доля онлайн-продаж / цифровых заявок, %", 0, 100, 35)
    tolerated_downtime_hours = st.slider("Допустимый простой, часов", 1, 120, 8)
    critical_loss_threshold = st.number_input(
        "Критический ущерб для устойчивости МСП, руб.",
        min_value=50_000,
        max_value=500_000_000,
        value=1_500_000,
        step=50_000,
    )

    st.header("2. Люди и данные")
    staff_with_access = st.slider("Сотрудников с доступом к данным / кабинетам", 1, 250, 8)
    has_remote_work = st.checkbox("Есть удалённый доступ", value=True)
    has_contractors = st.checkbox("Есть подрядчики с доступом к данным или сервисам", value=True)
    has_pdn = st.checkbox("Обрабатываются персональные данные", value=True)
    pdn_subjects = st.number_input(
        "Оценка числа субъектов ПДн",
        min_value=0,
        max_value=5_000_000,
        value=1200,
        step=100,
        disabled=not has_pdn,
    )

st.header("3. Карта активов")
default_assets = ["email", "website", "pos", "crm", "personal_data", "cloud", "bank", "employees"]
asset_options = {asset.name: asset.id for asset in ASSETS}
selected_asset_names = st.multiselect(
    "Выберите активы, значимые для бизнеса",
    options=list(asset_options.keys()),
    default=[asset.name for asset in ASSETS if asset.id in default_assets],
)
selected_asset_ids = [asset_options[name] for name in selected_asset_names]

with st.expander("Пояснение к карте активов", expanded=False):
    st.write(
        "Активы нужны, чтобы калькулятор считал риск не абстрактно, а через реальные точки выручки, данных, платежей и правового режима."
    )

st.header("4. Текущие меры и качество внедрения")

quality_options = {label: key for key, (label, _) in QUALITY_LEVELS.items()}
reverse_quality_options = {key: label for key, (label, _) in QUALITY_LEVELS.items()}

selected_quality: dict[str, str] = {}

controls_df_for_view = []
cols = st.columns(3)
for idx, control in enumerate(CONTROLS):
    with cols[idx % 3]:
        label = st.selectbox(
            control.name,
            options=list(quality_options.keys()),
            index=0,
            key=f"quality_{control.id}",
        )
        selected_quality[control.id] = quality_options[label]

st.divider()

risk_df = calculate_risk_table(
    sector=sector,
    selected_asset_ids=selected_asset_ids,
    monthly_revenue=float(monthly_revenue),
    critical_loss_threshold=float(critical_loss_threshold),
    tolerated_downtime_hours=float(tolerated_downtime_hours),
    staff_with_access=int(staff_with_access),
    has_remote_work=has_remote_work,
    has_contractors=has_contractors,
    has_pdn=has_pdn,
    pdn_subjects=int(pdn_subjects),
    online_share=float(online_share),
    selected_quality=selected_quality,
)

summary = calculate_summary(risk_df, float(critical_loss_threshold))
layers = layer_summary(risk_df)
costs_df = protection_costs(selected_quality)

st.header("5. Итоговый результат")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Исходный риск", f"{summary['base_risk']:,.0f} руб.".replace(",", " "))
m2.metric("Остаточный риск", f"{summary['residual_risk']:,.0f} руб.".replace(",", " "))
m3.metric("Остаточный риск", f"{summary['residual_percent']:.1f}%")
m4.metric("Индекс критического ущерба", f"{summary['critical_exceedance_proxy']:.1f}%")

st.caption(
    "Индекс критического ущерба — управленческий показатель вероятности тяжёлого сценария относительно заданного порога устойчивости. "
    "Он не является юридической или страховой гарантией."
)

if not layers.empty:
    st.subheader("Остаточный риск по трём слоям")
    layer_chart = (
        alt.Chart(layers)
        .mark_bar()
        .encode(
            x=alt.X("Остаточный риск, %:Q", title="Остаточный риск, %"),
            y=alt.Y("Слой:N", sort="-x", title="Слой"),
            tooltip=["Слой", "Исходный риск, руб.", "Остаточный риск, руб.", "Остаточный риск, %"],
        )
        .properties(height=180)
    )
    st.altair_chart(layer_chart, use_container_width=True)

st.subheader("Факторы остаточного риска")
if risk_df.empty:
    st.warning("Выберите хотя бы один актив, чтобы рассчитать риск.")
else:
    top_residual = risk_df.sort_values("Остаточный риск, руб.", ascending=False).head(10)
    chart = (
        alt.Chart(top_residual)
        .mark_bar()
        .encode(
            x=alt.X("Остаточный риск, руб.:Q", title="Остаточный риск, руб."),
            y=alt.Y("Угроза / правовой разрыв:N", sort="-x", title=None),
            tooltip=[
                "Угроза / правовой разрыв",
                "Слой",
                "Исходный риск, руб.",
                "Остаточный риск, руб.",
                "Остаточный риск, %",
                "Применённые меры",
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)

    st.dataframe(
        risk_df[
            [
                "Угроза / правовой разрыв",
                "Слой",
                "Вероятность",
                "Уязвимость",
                "Оценка ущерба, руб.",
                "Исходный риск, руб.",
                "Остаточный риск, руб.",
                "Остаточный риск, %",
                "Применённые меры",
            ]
        ].sort_values("Остаточный риск, руб.", ascending=False),
        use_container_width=True,
    )

st.header("6. Защитные затраты")
total_accounted_costs = int(costs_df["Учтённые годовые затраты, руб."].sum())
st.metric("Учтённые годовые защитные затраты", f"{total_accounted_costs:,.0f} руб.".replace(",", " "))

with st.expander("Структура защитных затрат", expanded=False):
    st.dataframe(costs_df, use_container_width=True)

st.header("7. Что усилить первым")
max_budget = st.number_input(
    "Предел дополнительных защитных затрат на ближайший период, руб.",
    min_value=0,
    max_value=50_000_000,
    value=150_000,
    step=10_000,
)

effect_df = marginal_control_effect(
    current_quality=selected_quality,
    sector=sector,
    selected_asset_ids=selected_asset_ids,
    monthly_revenue=float(monthly_revenue),
    critical_loss_threshold=float(critical_loss_threshold),
    tolerated_downtime_hours=float(tolerated_downtime_hours),
    staff_with_access=int(staff_with_access),
    has_remote_work=has_remote_work,
    has_contractors=has_contractors,
    has_pdn=has_pdn,
    pdn_subjects=int(pdn_subjects),
    online_share=float(online_share),
)

plan_df = greedy_cost_plan(effect_df, int(max_budget))

left, right = st.columns(2)
with left:
    st.subheader("Очередность мер")
    st.dataframe(effect_df.head(12), use_container_width=True)

with right:
    st.subheader("Портфель в пределах заданных затрат")
    if plan_df.empty:
        st.info("В заданный предел затрат не вошла ни одна дополнительная мера.")
    else:
        st.dataframe(plan_df, use_container_width=True)
        st.metric(
            "Сумма дополнительных затрат",
            f"{int(plan_df['Дополнительные защитные затраты, руб.'].sum()):,.0f} руб.".replace(",", " "),
        )
        st.metric(
            "Расчётное снижение остаточного риска",
            f"{float(plan_df['Снижение остаточного риска, руб.'].sum()):,.0f} руб.".replace(",", " "),
        )

st.header("8. Методологические ограничения")
st.markdown(
    """
1. Калькулятор не заменяет технический аудит, юридическое заключение или расследование инцидента.  
2. Итоговый процент — это нормированный индекс остаточного риска, а не абсолютная вероятность взлома.  
3. Штрафы и правовые последствия считаются как часть правового ущерба и стоимости несоблюдения режима информации.  
4. Защитные меры учитываются только через фактическое качество внедрения, а не через факт оплаты.  
5. Все коэффициенты в прототипе являются настраиваемыми и должны уточняться по данным конкретной отрасли, судебной практике, статистике инцидентов и экспертной проверке.
"""
)
