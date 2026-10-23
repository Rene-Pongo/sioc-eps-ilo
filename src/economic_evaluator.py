"""Evaluador economico del Agua No Facturada (ANF) para EPS Ilo S.A.

Valoriza las perdidas fisicas y comerciales detectadas por el motor de
anomalias usando la estructura tarifaria referencial SUNASS, determina el
semaforo normativo de ANF y simula el retorno de inversion (ROI) de planes
de reduccion de perdidas.

Contrato de datos:

* :func:`evaluate_economic_impact` retorna un diccionario con las metricas
  globales, el semaforo SUNASS y un ``sector_breakdown`` (DataFrame).
* :func:`simulate_anf_reduction_roi` retorna las metricas mensuales/anuales,
  el payback, el VAN a 12 meses y el ROI porcentual.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import NORMATIVE_LIMITS, TARIFF_STRUCTURE

# Columnas minimas requeridas para valorizar el impacto economico.
REQUIRED_COLUMNS = [
    "sector_id",
    "sector_name",
    "volumen_producido_m3",
    "volumen_facturado_m3",
    "anf_m3",
    "anf_pct",
]

# Tasa de descuento anual referencial para el VAN (12%).
ANNUAL_DISCOUNT_RATE = 0.12
# Tasa mensual equivalente compuesta.
MONTHLY_DISCOUNT_RATE = (1.0 + ANNUAL_DISCOUNT_RATE) ** (1.0 / 12.0) - 1.0

SEMAFORO_VERDE = "VERDE"
SEMAFORO_AMARILLO = "AMARILLO"
SEMAFORO_ROJO = "ROJO"

SECTOR_BREAKDOWN_COLUMNS = [
    "sector_id",
    "sector_name",
    "volumen_producido_m3",
    "volumen_facturado_m3",
    "anf_m3",
    "anf_pct",
    "perdida_fisica_m3",
    "perdida_comercial_m3",
    "perdida_economica_soles",
    "costo_energia_quimicos_soles",
    "alertas_fugas",
    "alertas_fraudes",
    "semaforo_sunass",
]


def _require_columns(df: pd.DataFrame) -> None:
    """Valida el contrato minimo del DataFrame de entrada."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df_flagged debe ser un pandas.DataFrame.")
    if df.empty:
        raise ValueError("df_flagged no puede estar vacio.")

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas obligatorias para la evaluacion economica: "
            + ", ".join(missing)
        )


def _semaforo(anf_pct: float) -> str:
    """Clasifica el ANF segun las metas referenciales SUNASS."""
    if anf_pct > float(NORMATIVE_LIMITS["anf_alerta_critica_pct"]):
        return SEMAFORO_ROJO
    if anf_pct > float(NORMATIVE_LIMITS["anf_alerta_amarilla_pct"]):
        return SEMAFORO_AMARILLO
    return SEMAFORO_VERDE


def _safe_ratio(part: float, total: float) -> float:
    """Division protegida para porcentajes."""
    if total <= 0.0:
        return 0.0
    return float(part) / float(total) * 100.0


def evaluate_economic_impact(df_flagged: pd.DataFrame) -> dict:
    """Valoriza el impacto economico global y por sector del ANF.

    La perdida comercial se estima con el volumen ANF de las filas con
    ``commercial_fraud_alert``; el resto del ANF se atribuye a perdida
    fisica (fugas y submedicion de red). Asi, ambas componentes suman
    exactamente el ANF total.

    Parameters
    ----------
    df_flagged:
        DataFrame retornado por :func:`src.anomaly_detector.detect_anomalies`.

    Returns
    -------
    dict
        Metricas globales y ``sector_breakdown`` (DataFrame por sector).
    """
    _require_columns(df_flagged)
    working = df_flagged.copy()

    for column in (
        "volumen_producido_m3",
        "volumen_facturado_m3",
        "anf_m3",
        "anf_pct",
    ):
        working[column] = pd.to_numeric(working[column], errors="coerce").fillna(0.0)

    # Columnas de alerta opcionales: si no existen se asume ausencia de evento.
    for column in ("physical_leak_alert", "commercial_fraud_alert"):
        if column not in working.columns:
            working[column] = False
        working[column] = working[column].fillna(False).astype(bool)

    # La perdida comercial solo cuenta filas de fraude que no sean fuga.
    fraud_only = working["commercial_fraud_alert"] & ~working["physical_leak_alert"]
    working["_anf_comercial"] = np.where(fraud_only, working["anf_m3"], 0.0)

    working["_alertas_fugas"] = working["physical_leak_alert"].astype(int)
    working["_alertas_fraudes"] = working["commercial_fraud_alert"].astype(int)

    grouped = (
        working.groupby(["sector_id", "sector_name"], as_index=False, sort=True)
        .agg(
            volumen_producido_m3=("volumen_producido_m3", "sum"),
            volumen_facturado_m3=("volumen_facturado_m3", "sum"),
            anf_m3=("anf_m3", "sum"),
            anf_comercial_m3=("_anf_comercial", "sum"),
            alertas_fugas=("_alertas_fugas", "sum"),
            alertas_fraudes=("_alertas_fraudes", "sum"),
        )
        .reset_index(drop=True)
    )

    # El ANF no atribuido a fraude se considera perdida fisica.
    grouped["perdida_comercial_m3"] = grouped["anf_comercial_m3"].clip(lower=0.0)
    grouped["perdida_fisica_m3"] = (
        grouped["anf_m3"] - grouped["perdida_comercial_m3"]
    ).clip(lower=0.0)
    grouped["anf_pct"] = [
        _safe_ratio(anf, producido)
        for anf, producido in zip(
            grouped["anf_m3"], grouped["volumen_producido_m3"], strict=False
        )
    ]

    tarifa_media = float(TARIFF_STRUCTURE["tarifa_media_ponderada"])
    costo_variable = float(TARIFF_STRUCTURE["costo_variable_produccion"])
    grouped["perdida_economica_soles"] = grouped["anf_m3"] * tarifa_media
    grouped["costo_energia_quimicos_soles"] = grouped["anf_m3"] * costo_variable
    grouped["semaforo_sunass"] = grouped["anf_pct"].map(_semaforo)

    numeric_columns = [
        "volumen_producido_m3",
        "volumen_facturado_m3",
        "anf_m3",
        "anf_pct",
        "perdida_fisica_m3",
        "perdida_comercial_m3",
        "perdida_economica_soles",
        "costo_energia_quimicos_soles",
    ]
    grouped[numeric_columns] = grouped[numeric_columns].round(3)
    grouped = grouped.loc[:, SECTOR_BREAKDOWN_COLUMNS]

    producido_total = float(working["volumen_producido_m3"].sum())
    facturado_total = float(working["volumen_facturado_m3"].sum())
    anf_total = float(working["anf_m3"].sum())
    comercial_total = float(grouped["perdida_comercial_m3"].sum())
    fisica_total = max(anf_total - comercial_total, 0.0)
    anf_porcentaje = _safe_ratio(anf_total, producido_total)

    return {
        "volumen_producido_total_m3": round(producido_total, 3),
        "volumen_facturado_total_m3": round(facturado_total, 3),
        "anf_total_m3": round(anf_total, 3),
        "anf_porcentaje": round(anf_porcentaje, 2),
        "perdida_fisica_m3": round(fisica_total, 3),
        "perdida_comercial_m3": round(comercial_total, 3),
        "perdida_economica_soles": round(anf_total * tarifa_media, 2),
        "costo_energia_quimicos_perdido_soles": round(
            anf_total * costo_variable, 2
        ),
        "semaforo_sunass": _semaforo(anf_porcentaje),
        "sector_breakdown": grouped,
    }


def simulate_anf_reduction_roi(
    current_anf_m3: float,
    reduction_target_pct: float,
    investment_soles: float = 45000.0,
) -> dict:
    """Simula el ROI de un plan de reduccion de ANF.

    Parameters
    ----------
    current_anf_m3:
        Volumen mensual actual de ANF en metros cubicos.
    reduction_target_pct:
        Porcentaje de reduccion objetivo sobre el ANF actual (0-100).
    investment_soles:
        Inversion inicial del plan en soles (por defecto S/ 45,000).

    Returns
    -------
    dict
        ``m3_recuperados_mes``, ``ahorro_mensual_soles``,
        ``ahorro_anual_soles``, ``payback_meses``,
        ``van_12_meses_soles`` y ``roi_porcentaje``.
    """
    for name, value in (
        ("current_anf_m3", current_anf_m3),
        ("reduction_target_pct", reduction_target_pct),
        ("investment_soles", investment_soles),
    ):
        if isinstance(value, bool) or not isinstance(
            value, (int, float, np.integer, np.floating)
        ):
            raise TypeError(f"{name} debe ser un numero.")
        if not np.isfinite(float(value)):
            raise ValueError(f"{name} debe ser un numero finito.")

    current_anf_m3 = float(current_anf_m3)
    reduction_target_pct = float(reduction_target_pct)
    investment_soles = float(investment_soles)

    if current_anf_m3 < 0.0:
        raise ValueError("current_anf_m3 no puede ser negativo.")
    if not 0.0 <= reduction_target_pct <= 100.0:
        raise ValueError("reduction_target_pct debe estar entre 0 y 100.")
    if investment_soles <= 0.0:
        raise ValueError("investment_soles debe ser mayor que cero.")

    tarifa_media = float(TARIFF_STRUCTURE["tarifa_media_ponderada"])
    m3_recuperados_mes = current_anf_m3 * reduction_target_pct / 100.0
    ahorro_mensual = m3_recuperados_mes * tarifa_media
    ahorro_anual = ahorro_mensual * 12.0

    if ahorro_mensual > 0.0:
        payback_meses = investment_soles / ahorro_mensual
        van_12_meses = (
            sum(
                ahorro_mensual / ((1.0 + MONTHLY_DISCOUNT_RATE) ** month)
                for month in range(1, 13)
            )
            - investment_soles
        )
        roi_porcentaje = (ahorro_anual - investment_soles) / investment_soles * 100.0
    else:
        payback_meses = float("inf")
        van_12_meses = -investment_soles
        roi_porcentaje = -100.0

    return {
        "m3_recuperados_mes": round(m3_recuperados_mes, 3),
        "ahorro_mensual_soles": round(ahorro_mensual, 2),
        "ahorro_anual_soles": round(ahorro_anual, 2),
        "payback_meses": round(payback_meses, 2)
        if np.isfinite(payback_meses)
        else float("inf"),
        "van_12_meses_soles": round(van_12_meses, 2),
        "roi_porcentaje": round(roi_porcentaje, 2),
    }
