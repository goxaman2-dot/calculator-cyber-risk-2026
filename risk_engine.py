from __future__ import annotations

from itertools import combinations
from typing import Iterable

import numpy as np
import pandas as pd

from data_catalog import ASSETS, CONTROLS, SECTOR_PROFILES, THREATS, QUALITY_LEVELS


LAYER_LABELS = {
    "technical": "Технический слой",
    "org_legal": "Организационно-правовой слой",
    "economic_management": "Экономико-управленческий слой",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def asset_map(selected_asset_ids: Iterable[str]) -> dict[str, object]:
    selected = set(selected_asset_ids)
    return {asset.id: asset for asset in ASSETS if asset.id in selected}


def calculate_base_loss(
    monthly_revenue: float,
    critical_loss_threshold: float,
    downtime_hours: float,
    pdn_subjects: int,
    threat_default_loss_share: float,
    heavy_tail: float,
    asset_dependency: float,
) -> float:
    daily_revenue = monthly_revenue / 30.0
    downtime_loss = daily_revenue * max(downtime_hours, 1.0) / 8.0
    legal_scale = min(max(pdn_subjects / 1000.0, 0.0), 25.0) * 10000.0
    business_loss = monthly_revenue * threat_default_loss_share * asset_dependency
    tail_component = critical_loss_threshold * 0.05 * heavy_tail
    return max(10_000.0, business_loss + downtime_loss + legal_scale + tail_component)


def threat_vulnerability(
    threat_id: str,
    staff_with_access: int,
    has_remote_work: bool,
    has_contractors: bool,
    has_pdn: bool,
    online_share: float,
) -> float:
    v = 0.65
    if staff_with_access >= 5:
        v += 0.08
    if staff_with_access >= 15:
        v += 0.10
    if has_remote_work:
        v += 0.06
    if has_contractors:
        v += 0.07
    if has_pdn and threat_id in {"pdn_leak", "legal_gap_pdn", "insider_leak"}:
        v += 0.12
    if online_share >= 50 and threat_id in {"website_outage", "account_takeover", "phishing_email"}:
        v += 0.10
    return clamp(v, 0.25, 1.35)


def sector_asset_dependency(sector: str, asset_ids: list[str]) -> float:
    profile = SECTOR_PROFILES.get(sector, {})
    if not asset_ids:
        return 0.7
    values = [profile.get(asset_id, 0.65) for asset_id in asset_ids]
    return float(np.mean(values))


def active_controls_quality(selected_quality: dict[str, str]) -> dict[str, float]:
    qualities: dict[str, float] = {}
    for control in CONTROLS:
        level = selected_quality.get(control.id, "none")
        qualities[control.id] = QUALITY_LEVELS.get(level, ("", 0.0))[1]
    return qualities


def calculate_risk_table(
    sector: str,
    selected_asset_ids: list[str],
    monthly_revenue: float,
    critical_loss_threshold: float,
    tolerated_downtime_hours: float,
    staff_with_access: int,
    has_remote_work: bool,
    has_contractors: bool,
    has_pdn: bool,
    pdn_subjects: int,
    online_share: float,
    selected_quality: dict[str, str],
) -> pd.DataFrame:
    selected_assets = asset_map(selected_asset_ids)
    qualities = active_controls_quality(selected_quality)
    rows = []

    for threat in THREATS:
        relevant_asset_ids = [asset_id for asset_id in threat.asset_ids if asset_id in selected_assets]
        if not relevant_asset_ids:
            continue

        dep = sector_asset_dependency(sector, relevant_asset_ids)
        vulnerability = threat_vulnerability(
            threat.id,
            staff_with_access=staff_with_access,
            has_remote_work=has_remote_work,
            has_contractors=has_contractors,
            has_pdn=has_pdn,
            online_share=online_share,
        )
        likelihood = clamp(threat.base_likelihood * (0.75 + dep * 0.55), 0.01, 0.95)
        loss = calculate_base_loss(
            monthly_revenue=monthly_revenue,
            critical_loss_threshold=critical_loss_threshold,
            downtime_hours=tolerated_downtime_hours,
            pdn_subjects=pdn_subjects if has_pdn else 0,
            threat_default_loss_share=threat.default_loss_share,
            heavy_tail=threat.heavy_tail,
            asset_dependency=dep,
        )
        base_risk = likelihood * vulnerability * loss

        residual_multiplier = 1.0
        applied_controls = []
        preventive_costs = 0

        for control in CONTROLS:
            if threat.id not in control.affected_threats:
                continue
            q = qualities.get(control.id, 0.0)
            if q <= 0:
                continue

            # Мера может снижать вероятность, тяжесть ущерба и длительность простоя.
            # Эффекты действуют мультипликативно, чтобы не получать искусственное снижение риска больше 100%.
            combined_effect = 1.0 - (
                (1.0 - control.probability_reduction * q)
                * (1.0 - control.loss_reduction * q)
                * (1.0 - control.downtime_reduction * q * 0.45)
            )
            combined_effect = clamp(combined_effect, 0.0, 0.92)
            residual_multiplier *= 1.0 - combined_effect
            applied_controls.append(control.name)
            preventive_costs += int(control.annual_cost * q)

        residual_risk = base_risk * residual_multiplier
        risk_reduction = base_risk - residual_risk

        rows.append(
            {
                "id": threat.id,
                "Угроза / правовой разрыв": threat.name,
                "Слой": LAYER_LABELS[threat.layer],
                "Механизм": threat.mechanism,
                "Активы": ", ".join(relevant_asset_ids),
                "Вероятность": likelihood,
                "Уязвимость": vulnerability,
                "Оценка ущерба, руб.": loss,
                "Исходный риск, руб.": base_risk,
                "Остаточный риск, руб.": residual_risk,
                "Снижение риска, руб.": risk_reduction,
                "Остаточный риск, %": (residual_risk / base_risk * 100.0) if base_risk else 0.0,
                "Применённые меры": "; ".join(applied_controls) if applied_controls else "нет",
                "Учтённые защитные затраты, руб.": preventive_costs,
                "Тяжёлый хвост": threat.heavy_tail,
            }
        )

    return pd.DataFrame(rows)


def calculate_summary(risk_df: pd.DataFrame, critical_loss_threshold: float) -> dict[str, float]:
    if risk_df.empty:
        return {
            "base_risk": 0.0,
            "residual_risk": 0.0,
            "residual_percent": 0.0,
            "reduced_percent": 0.0,
            "critical_exceedance_proxy": 0.0,
        }

    base = float(risk_df["Исходный риск, руб."].sum())
    residual = float(risk_df["Остаточный риск, руб."].sum())
    residual_percent = residual / base * 100.0 if base else 0.0

    # Прокси tail-risk: чем выше сумма тяжёлых остаточных рисков относительно порога устойчивости,
    # тем выше вероятность критического сценария. Это не юридическая или актуарная гарантия,
    # а управленческий индекс для МСП.
    tail_weighted = float(
        (risk_df["Остаточный риск, руб."] * risk_df["Тяжёлый хвост"]).sum()
    )
    critical_proxy = 1.0 - np.exp(-tail_weighted / max(critical_loss_threshold, 1.0))
    critical_proxy = clamp(float(critical_proxy), 0.0, 0.95)

    return {
        "base_risk": base,
        "residual_risk": residual,
        "residual_percent": residual_percent,
        "reduced_percent": 100.0 - residual_percent,
        "critical_exceedance_proxy": critical_proxy * 100.0,
    }


def layer_summary(risk_df: pd.DataFrame) -> pd.DataFrame:
    if risk_df.empty:
        return pd.DataFrame(columns=["Слой", "Исходный риск, руб.", "Остаточный риск, руб.", "Остаточный риск, %"])
    grouped = (
        risk_df.groupby("Слой", as_index=False)[["Исходный риск, руб.", "Остаточный риск, руб."]]
        .sum()
    )
    grouped["Остаточный риск, %"] = grouped["Остаточный риск, руб."] / grouped["Исходный риск, руб."] * 100.0
    return grouped.sort_values("Остаточный риск, %", ascending=False)


def protection_costs(selected_quality: dict[str, str]) -> pd.DataFrame:
    rows = []
    for control in CONTROLS:
        level_id = selected_quality.get(control.id, "none")
        level_label, q = QUALITY_LEVELS.get(level_id, ("Мера отсутствует", 0.0))
        rows.append(
            {
                "Мера": control.name,
                "Слой": LAYER_LABELS[control.layer],
                "Тип затрат": control.cost_type,
                "Качество внедрения": level_label,
                "Коэффициент качества": q,
                "Базовые годовые затраты, руб.": control.annual_cost,
                "Учтённые годовые затраты, руб.": int(control.annual_cost * q),
            }
        )
    return pd.DataFrame(rows)


def marginal_control_effect(
    current_quality: dict[str, str],
    sector: str,
    selected_asset_ids: list[str],
    monthly_revenue: float,
    critical_loss_threshold: float,
    tolerated_downtime_hours: float,
    staff_with_access: int,
    has_remote_work: bool,
    has_contractors: bool,
    has_pdn: bool,
    pdn_subjects: int,
    online_share: float,
) -> pd.DataFrame:
    base_df = calculate_risk_table(
        sector,
        selected_asset_ids,
        monthly_revenue,
        critical_loss_threshold,
        tolerated_downtime_hours,
        staff_with_access,
        has_remote_work,
        has_contractors,
        has_pdn,
        pdn_subjects,
        online_share,
        current_quality,
    )
    base_summary = calculate_summary(base_df, critical_loss_threshold)
    base_residual = base_summary["residual_risk"]

    rows = []
    for control in CONTROLS:
        current_level = current_quality.get(control.id, "none")
        if current_level in {"working", "embedded"}:
            continue

        candidate_quality = dict(current_quality)
        candidate_quality[control.id] = "working"

        candidate_df = calculate_risk_table(
            sector,
            selected_asset_ids,
            monthly_revenue,
            critical_loss_threshold,
            tolerated_downtime_hours,
            staff_with_access,
            has_remote_work,
            has_contractors,
            has_pdn,
            pdn_subjects,
            online_share,
            candidate_quality,
        )
        candidate_summary = calculate_summary(candidate_df, critical_loss_threshold)
        delta = base_residual - candidate_summary["residual_risk"]

        current_q = QUALITY_LEVELS.get(current_level, ("", 0.0))[1]
        target_q = QUALITY_LEVELS["working"][1]
        additional_cost = max(0, int(control.annual_cost * (target_q - current_q)))

        rows.append(
            {
                "Мера": control.name,
                "Слой": LAYER_LABELS[control.layer],
                "Дополнительные защитные затраты, руб.": additional_cost,
                "Снижение остаточного риска, руб.": delta,
                "Снижение риска на 1 руб. затрат": delta / additional_cost if additional_cost else 0.0,
            }
        )

    return pd.DataFrame(rows).sort_values("Снижение риска на 1 руб. затрат", ascending=False)


def greedy_cost_plan(effect_df: pd.DataFrame, max_budget: int) -> pd.DataFrame:
    if effect_df.empty:
        return effect_df
    selected = []
    spent = 0
    for _, row in effect_df.iterrows():
        cost = int(row["Дополнительные защитные затраты, руб."])
        if cost <= 0:
            continue
        if spent + cost <= max_budget:
            selected.append(row)
            spent += cost
    if not selected:
        return pd.DataFrame(columns=effect_df.columns)
    return pd.DataFrame(selected)
