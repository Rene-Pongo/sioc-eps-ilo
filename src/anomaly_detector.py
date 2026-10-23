"""Motor de deteccion de anomalias operativas y comerciales para EPS Ilo.

Combina reglas de negocio SUNASS/DIGESA con un modelo no supervisado
``IsolationForest`` para identificar:

* Fugas fisicas nocturnas a partir del exceso sobre el Caudal Minimo
  Nocturno (CMN) de cada sector.
* Fraude comercial o subregistro por picos anomalos de Agua No Facturada
  (ANF) en horario diurno.
* Incumplimientos de cloro residual libre, turbiedad y presion normativa.
* Patrones estadisticamente atipicos en la telemetria.

El contrato de datos es obligatorio para las fases posteriores del monorepo:
el DataFrame retornado conserva todas las columnas originales y agrega
``is_night_window``, ``cmn_baseline_lps``, ``cmn_excess_lps``,
``physical_leak_alert``, ``commercial_fraud_alert``,
``quality_chlorine_alert``, ``pressure_norm_alert``, ``anomaly_score``,
``anomaly_type`` y ``severity``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .config import NORMATIVE_LIMITS

# ---------------------------------------------------------------------------
# Contratos y etiquetas de salida
# ---------------------------------------------------------------------------
TELEMETRY_REQUIRED_COLUMNS = [
    "timestamp",
    "sector_id",
    "sector_name",
    "caudal_lps",
    "presion_mca",
    "cloro_mg_l",
    "turbiedad_ntu",
    "continuidad_horas",
    "anf_pct",
]

ANOMALY_COLUMNS = [
    "is_night_window",
    "cmn_baseline_lps",
    "cmn_excess_lps",
    "physical_leak_alert",
    "commercial_fraud_alert",
    "quality_chlorine_alert",
    "pressure_norm_alert",
    "anomaly_score",
    "anomaly_type",
    "severity",
]

# Tipos de anomalia reportados en ``anomaly_type``.
TYPE_LEAK = "fuga_fisica"
TYPE_FRAUD = "fraude_comercial"
TYPE_CHLORINE = "cloro_bajo"
TYPE_TURBIDITY = "turbiedad_alta"
TYPE_PRESSURE = "presion_fuera_rango"
TYPE_STATISTICAL = "patron_atipico"
TYPE_NORMAL = "normal"

# Niveles de severidad ordenados de menor a mayor.
SEVERITY_ORDER = ["normal", "baja", "media", "alta", "critica"]
_SEVERITY_RANK = {level: rank for rank, level in enumerate(SEVERITY_ORDER)}

# Campos de alerta binaria que se resumen por sector.
ALERT_COLUMNS = [
    "physical_leak_alert",
    "commercial_fraud_alert",
    "quality_chlorine_alert",
    "pressure_norm_alert",
]

_SUMMARY_COLUMNS = [
    "sector_id",
    "sector_name",
    "registros",
    "alertas_totales",
    "alertas_porcentaje",
    "fugas_fisicas",
    "fraudes_comerciales",
    "alertas_cloro",
    "alertas_turbiedad",
    "alertas_presion",
    "alertas_estadisticas",
    "anf_promedio_pct",
    "score_promedio",
    "score_maximo",
    "severidad_maxima",
    "tipo_predominante",
]


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------
def _validate_input(df: pd.DataFrame, contamination: float) -> float:
    """Valida el DataFrame de entrada y el parametro ``contamination``."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df debe ser un pandas.DataFrame.")
    if df.empty:
        raise ValueError("df no puede estar vacio.")

    missing = [col for col in TELEMETRY_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "Faltan columnas obligatorias de telemetria: " + ", ".join(missing)
        )

    if isinstance(contamination, bool) or not isinstance(
        contamination, (int, float, np.integer, np.floating)
    ):
        raise TypeError("contamination debe ser un numero entre 0 y 0.5.")
    contamination = float(contamination)
    if not 0.0 < contamination <= 0.5:
        raise ValueError("contamination debe estar en el rango (0, 0.5].")
    return contamination


def _night_mask(timestamps: pd.Series) -> pd.Series:
    """Marca las horas dentro de la ventana nocturna normativa."""
    start = int(NORMATIVE_LIMITS["night_window_start_hour"])
    end = int(NORMATIVE_LIMITS["night_window_end_hour"])
    hour = timestamps.dt.hour
    if start <= end:
        mask = (hour >= start) & (hour < end)
    else:
        mask = (hour >= start) | (hour < end)
    return mask.astype(bool)


def _baseline_by_sector(
    df: pd.DataFrame, active: pd.Series, night: pd.Series
) -> pd.Series:
    """Estima el CMN base de cada sector con el percentil 20 nocturno.

    Se usa un percentil bajo para que las fugas inyectadas (pocas horas al
    mes) no contaminen la linea base. Si un sector no tiene registros
    nocturnos activos se recurre a la mediana diurna y, en ultimo caso, se
    deja la base en cero.
    """
    night_active = df.loc[night & active]
    if not night_active.empty:
        baseline = night_active.groupby("sector_id")["caudal_lps"].quantile(0.20)
    else:
        baseline = pd.Series(dtype=float)

    day_active = df.loc[active]
    fallback = (
        day_active.groupby("sector_id")["caudal_lps"].median()
        if not day_active.empty
        else pd.Series(dtype=float)
    )

    baseline = baseline.reindex(df["sector_id"].unique())
    fallback = fallback.reindex(baseline.index)
    baseline = baseline.fillna(fallback).fillna(0.0)
    return baseline.clip(lower=0.0).round(2)


def _statistical_score(
    df: pd.DataFrame, active: pd.Series, contamination: float
) -> np.ndarray:
    """Calcula un score estadistico 0-1 con IsolationForest.

    El modelo se entrena solo con horas de servicio activo (caudal > 0) para
    no penalizar cortes programados de continuidad. Las horas sin servicio
    reciben score cero.
    """
    n_rows = len(df)
    scores = np.zeros(n_rows, dtype=float)
    active_positions = np.flatnonzero(active.to_numpy(dtype=bool))
    if active_positions.size < 10:
        return scores

    feature_frame = pd.DataFrame(
        {
            "caudal_lps": pd.to_numeric(df["caudal_lps"], errors="coerce"),
            "presion_mca": pd.to_numeric(df["presion_mca"], errors="coerce"),
            "cloro_mg_l": pd.to_numeric(df["cloro_mg_l"], errors="coerce"),
            "turbiedad_ntu": pd.to_numeric(df["turbiedad_ntu"], errors="coerce"),
            "anf_pct": pd.to_numeric(df["anf_pct"], errors="coerce"),
            "continuidad_horas": pd.to_numeric(
                df["continuidad_horas"], errors="coerce"
            ),
            "cmn_excess_lps": pd.to_numeric(
                df["cmn_excess_lps"], errors="coerce"
            ),
            "hour_sin": np.sin(2.0 * np.pi * df["timestamp"].dt.hour / 24.0),
            "hour_cos": np.cos(2.0 * np.pi * df["timestamp"].dt.hour / 24.0),
        }
    )

    # Imputacion defensiva por mediana para no romper el modelo con NaN.
    feature_frame = feature_frame.fillna(feature_frame.median(numeric_only=True))
    feature_frame = feature_frame.fillna(0.0)
    x_active = feature_frame.iloc[active_positions].to_numpy(dtype=float)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=1,
    )
    model.fit(x_active)

    # decision_function: menor valor = mas anomalo. Se invierte y se lleva a
    # un rango 0-1 mediante ranking porcentual robusto.
    raw_anomaly = -model.decision_function(x_active)
    ranked = pd.Series(raw_anomaly).rank(method="average", pct=True).to_numpy()
    scores[active_positions] = ranked
    return np.clip(scores, 0.0, 1.0)


def _anomaly_types(
    leak: np.ndarray,
    fraud: np.ndarray,
    chlorine: np.ndarray,
    turbidity: np.ndarray,
    pressure: np.ndarray,
    statistical: np.ndarray,
) -> np.ndarray:
    """Asigna un tipo primario de anomalia por prioridad operativa."""
    conditions = [
        leak,
        fraud,
        chlorine,
        turbidity,
        pressure,
        statistical,
    ]
    choices = [
        TYPE_LEAK,
        TYPE_FRAUD,
        TYPE_CHLORINE,
        TYPE_TURBIDITY,
        TYPE_PRESSURE,
        TYPE_STATISTICAL,
    ]
    return np.select(conditions, choices, default=TYPE_NORMAL)


def _severities(
    leak: np.ndarray,
    fraud: np.ndarray,
    chlorine: np.ndarray,
    turbidity: np.ndarray,
    pressure: np.ndarray,
    baseline: np.ndarray,
    excess: np.ndarray,
    anf_pct: np.ndarray,
    chlorine_values: np.ndarray,
    turbidity_values: np.ndarray,
    pressure_values: np.ndarray,
    statistical: np.ndarray,
) -> np.ndarray:
    """Clasifica la severidad operativa de cada registro."""
    pressure_min = float(NORMATIVE_LIMITS["presion_min_mca"])
    pressure_max = float(NORMATIVE_LIMITS["presion_max_mca"])

    with np.errstate(divide="ignore", invalid="ignore"):
        excess_ratio = np.where(baseline > 0, excess / baseline, 0.0)

    critical_pressure = pressure & (
        (pressure_values < 0.5 * pressure_min)
        | (pressure_values > pressure_max + 5.0)
    )

    conditions = [
        leak & (excess_ratio >= 0.60),
        leak,
        fraud & (anf_pct >= 50.0),
        fraud,
        chlorine & (chlorine_values < 0.20),
        chlorine,
        turbidity & (turbidity_values > 7.0),
        turbidity,
        critical_pressure,
        pressure,
        statistical >= 0.95,
        statistical >= 0.85,
    ]
    choices = [
        "critica",
        "alta",
        "critica",
        "alta",
        "critica",
        "alta",
        "critica",
        "alta",
        "critica",
        "alta",
        "media",
        "baja",
    ]
    return np.select(conditions, choices, default="normal")


def _dominant_type(types: pd.Series) -> str:
    """Retorna el tipo de anomalia mas frecuente, ignorando filas normales."""
    anomalies = types[types != TYPE_NORMAL]
    if anomalies.empty:
        return TYPE_NORMAL
    counts = anomalies.value_counts()
    return str(counts.index[0])


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------
def detect_anomalies(
    df: pd.DataFrame, contamination: float = 0.05
) -> pd.DataFrame:
    """Detecta anomalias hidraulicas, comerciales y de calidad.

    Parameters
    ----------
    df:
        Telemetria con el contrato de columnas de
        :func:`src.telemetry_generator.generate_telemetry_data`.
    contamination:
        Proporcion esperada de outliers para ``IsolationForest`` (0, 0.5].

    Returns
    -------
    pandas.DataFrame
        Copia del DataFrame de entrada con las diez columnas adicionales del
        contrato de deteccion, sin modificar el objeto original.
    """
    contamination = _validate_input(df, contamination)
    flagged = df.copy()
    flagged["timestamp"] = pd.to_datetime(flagged["timestamp"])

    # 1. Ventana nocturna y caudal minimo nocturno (CMN).
    night = _night_mask(flagged["timestamp"])
    active = pd.to_numeric(flagged["caudal_lps"], errors="coerce").fillna(0.0) > 0.0
    flagged["is_night_window"] = night.to_numpy(dtype=bool)

    baseline_map = _baseline_by_sector(flagged, active, night)
    baseline = (
        flagged["sector_id"].map(baseline_map).fillna(0.0).to_numpy(dtype=float)
    )
    flagged["cmn_baseline_lps"] = baseline

    caudal = pd.to_numeric(flagged["caudal_lps"], errors="coerce").fillna(0.0)
    excess = np.where(night & active, np.maximum(caudal - baseline, 0.0), 0.0)
    flagged["cmn_excess_lps"] = np.round(excess, 2)

    # 2. Reglas de negocio.
    leak_threshold = np.maximum(0.30 * baseline, 5.0)
    physical_leak = (
        night.to_numpy(dtype=bool)
        & active.to_numpy(dtype=bool)
        & (excess >= leak_threshold)
    )

    anf_pct = pd.to_numeric(flagged["anf_pct"], errors="coerce").fillna(0.0)
    sector_median = anf_pct.groupby(flagged["sector_id"]).transform("median")
    q25 = anf_pct.groupby(flagged["sector_id"]).transform(lambda s: s.quantile(0.25))
    q75 = anf_pct.groupby(flagged["sector_id"]).transform(lambda s: s.quantile(0.75))
    fraud_threshold = sector_median + np.maximum(8.0, 2.5 * (q75 - q25))
    commercial_fraud = (
        active.to_numpy(dtype=bool)
        & ~night.to_numpy(dtype=bool)
        & ~physical_leak
        & (anf_pct.to_numpy(dtype=float) >= fraud_threshold.to_numpy(dtype=float))
    )

    chlorine_values = (
        pd.to_numeric(flagged["cloro_mg_l"], errors="coerce").fillna(0.0).to_numpy()
    )
    turbidity_values = (
        pd.to_numeric(flagged["turbiedad_ntu"], errors="coerce")
        .fillna(0.0)
        .to_numpy()
    )
    pressure_values = (
        pd.to_numeric(flagged["presion_mca"], errors="coerce").fillna(0.0).to_numpy()
    )
    active_values = active.to_numpy(dtype=bool)

    chlorine_alert = active_values & (
        chlorine_values < float(NORMATIVE_LIMITS["cloro_min_mg_l"])
    )
    turbidity_alert = active_values & (
        turbidity_values > float(NORMATIVE_LIMITS["turbiedad_max_ntu"])
    )
    pressure_alert = active_values & (
        (pressure_values < float(NORMATIVE_LIMITS["presion_min_mca"]))
        | (pressure_values > float(NORMATIVE_LIMITS["presion_max_mca"]))
    )

    flagged["physical_leak_alert"] = physical_leak
    flagged["commercial_fraud_alert"] = commercial_fraud
    flagged["quality_chlorine_alert"] = chlorine_alert
    flagged["pressure_norm_alert"] = pressure_alert

    # 3. Score estadistico + refuerzo de reglas.
    statistical = _statistical_score(flagged, active, contamination)
    rule_strength = np.zeros(len(flagged), dtype=float)
    rule_strength = np.where(pressure_alert, 0.80, rule_strength)
    rule_strength = np.where(turbidity_alert, 0.82, rule_strength)
    rule_strength = np.where(chlorine_alert, 0.88, rule_strength)
    rule_strength = np.where(commercial_fraud, 0.92, rule_strength)
    rule_strength = np.where(physical_leak, 0.97, rule_strength)

    anomaly_score = 0.55 * statistical + 0.45 * rule_strength
    flagged["anomaly_score"] = np.round(np.clip(anomaly_score, 0.0, 1.0), 4)

    flagged["anomaly_type"] = _anomaly_types(
        physical_leak,
        commercial_fraud,
        chlorine_alert,
        turbidity_alert,
        pressure_alert,
        statistical >= 0.95,
    )
    flagged["severity"] = _severities(
        physical_leak,
        commercial_fraud,
        chlorine_alert,
        turbidity_alert,
        pressure_alert,
        baseline,
        excess,
        anf_pct.to_numpy(dtype=float),
        chlorine_values,
        turbidity_values,
        pressure_values,
        statistical,
    )

    # Asegurar tipos nativos y orden estable de columnas nuevas.
    flagged["is_night_window"] = flagged["is_night_window"].astype(bool)
    for column in ALERT_COLUMNS:
        flagged[column] = flagged[column].astype(bool)

    return flagged


def summarize_anomalies_by_sector(df_flagged: pd.DataFrame) -> pd.DataFrame:
    """Resume las alertas detectadas por sector hidraulico.

    Parameters
    ----------
    df_flagged:
        DataFrame retornado por :func:`detect_anomalies`.

    Returns
    -------
    pandas.DataFrame
        Una fila por sector con conteos de alertas, ANF promedio, scores y el
        tipo/severidad predominante. Si no hay filas, retorna un DataFrame
        vacio con el esquema esperado.
    """
    if not isinstance(df_flagged, pd.DataFrame):
        raise TypeError("df_flagged debe ser un pandas.DataFrame.")
    if df_flagged.empty:
        return pd.DataFrame(columns=_SUMMARY_COLUMNS)

    if "anomaly_type" not in df_flagged.columns:
        raise ValueError(
            "df_flagged debe provenir de detect_anomalies (falta anomaly_type)."
        )

    working = df_flagged.copy()
    for column in ALERT_COLUMNS:
        if column not in working.columns:
            working[column] = False
        working[column] = working[column].fillna(False).astype(bool)

    if "severity" not in working.columns:
        working["severity"] = "normal"
    working["severity"] = working["severity"].fillna("normal")
    if "anomaly_score" not in working.columns:
        working["anomaly_score"] = 0.0
    working["anomaly_score"] = (
        pd.to_numeric(working["anomaly_score"], errors="coerce").fillna(0.0)
    )
    if "anf_pct" not in working.columns:
        working["anf_pct"] = 0.0
    working["anf_pct"] = pd.to_numeric(working["anf_pct"], errors="coerce").fillna(0.0)

    working["_is_alert"] = working["anomaly_type"] != TYPE_NORMAL
    working["_severity_rank"] = (
        working["severity"].map(_SEVERITY_RANK).fillna(0).astype(int)
    )

    rows: list[dict] = []
    for (sector_id, sector_name), group in working.groupby(
        ["sector_id", "sector_name"], sort=True
    ):
        total = int(len(group))
        alerts = int(group["_is_alert"].sum())
        max_rank = int(group["_severity_rank"].max())
        rows.append(
            {
                "sector_id": sector_id,
                "sector_name": sector_name,
                "registros": total,
                "alertas_totales": alerts,
                "alertas_porcentaje": round(100.0 * alerts / total, 2)
                if total
                else 0.0,
                "fugas_fisicas": int(group["physical_leak_alert"].sum()),
                "fraudes_comerciales": int(
                    group["commercial_fraud_alert"].sum()
                ),
                "alertas_cloro": int(
                    (group["anomaly_type"] == TYPE_CHLORINE).sum()
                ),
                "alertas_turbiedad": int(
                    (group["anomaly_type"] == TYPE_TURBIDITY).sum()
                ),
                "alertas_presion": int(
                    (group["anomaly_type"] == TYPE_PRESSURE).sum()
                ),
                "alertas_estadisticas": int(
                    (group["anomaly_type"] == TYPE_STATISTICAL).sum()
                ),
                "anf_promedio_pct": round(float(group["anf_pct"].mean()), 2),
                "score_promedio": round(float(group["anomaly_score"].mean()), 4),
                "score_maximo": round(float(group["anomaly_score"].max()), 4),
                "severidad_maxima": SEVERITY_ORDER[max_rank],
                "tipo_predominante": _dominant_type(group["anomaly_type"]),
            }
        )

    summary = pd.DataFrame.from_records(rows, columns=_SUMMARY_COLUMNS)
    return summary.sort_values("sector_id", kind="stable").reset_index(drop=True)
