"""Pruebas unitarias del motor de deteccion de anomalias de EPS Ilo.

Verifica el contrato de columnas, las reglas de negocio SUNASS/DIGESA
(fugas nocturnas, fraude comercial, cloro, turbiedad y presion), el score
estadistico, las severidades y el resumen sectorial.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.anomaly_detector import (
    ANOMALY_COLUMNS,
    SEVERITY_ORDER,
    TYPE_CHLORINE,
    TYPE_FRAUD,
    TYPE_LEAK,
    TYPE_NORMAL,
    TYPE_PRESSURE,
    TYPE_STATISTICAL,
    TYPE_TURBIDITY,
    detect_anomalies,
    summarize_anomalies_by_sector,
)
from src.config import NORMATIVE_LIMITS, SECTORS
from src.telemetry_generator import (
    EVENT_FRAUD,
    EVENT_HIGH_TURBIDITY,
    EVENT_LEAK,
    EVENT_LOW_CHLORINE,
    EVENT_LOW_PRESSURE,
    generate_telemetry_data,
)

DAYS = 30
SEED = 42
ALLOWED_TYPES = {
    TYPE_NORMAL,
    TYPE_LEAK,
    TYPE_FRAUD,
    TYPE_CHLORINE,
    TYPE_TURBIDITY,
    TYPE_PRESSURE,
    TYPE_STATISTICAL,
}


@pytest.fixture(scope="module")
def telemetry() -> pd.DataFrame:
    """Telemetria base de 30 dias con eventos inyectados."""
    return generate_telemetry_data(days=DAYS, seed=SEED, inject_anomalies=True)


@pytest.fixture(scope="module")
def flagged(telemetry: pd.DataFrame) -> pd.DataFrame:
    """Dataset con las diez columnas de deteccion calculadas."""
    return detect_anomalies(telemetry, contamination=0.05)


def _rows_with_event(df: pd.DataFrame, event: str) -> pd.DataFrame:
    """Filas cuyo ``injected_event`` contiene la etiqueta indicada."""
    mask = df["injected_event"].astype(str).str.contains(event, regex=False)
    return df.loc[mask]


def test_contract_adds_all_columns(flagged: pd.DataFrame) -> None:
    """Se agregan exactamente las diez columnas del contrato de deteccion."""
    for column in ANOMALY_COLUMNS:
        assert column in flagged.columns, column
    assert list(flagged.columns[-len(ANOMALY_COLUMNS):]) == ANOMALY_COLUMNS


def test_contract_preserves_original_columns(
    telemetry: pd.DataFrame, flagged: pd.DataFrame
) -> None:
    """Todas las columnas originales se conservan sin alterar su contenido."""
    assert len(flagged) == len(telemetry)
    assert set(telemetry.columns).issubset(flagged.columns)
    for column in telemetry.columns:
        pd.testing.assert_series_equal(
            flagged[column], telemetry[column], check_names=False
        )


def test_input_dataframe_is_not_mutated(
    telemetry: pd.DataFrame, flagged: pd.DataFrame
) -> None:
    """detect_anomalies trabaja sobre una copia defensiva."""
    assert "anomaly_type" not in telemetry.columns
    assert "anomaly_score" not in telemetry.columns
    assert "physical_leak_alert" not in telemetry.columns


def test_night_window_matches_normative_hours(flagged: pd.DataFrame) -> None:
    """La ventana nocturna cubre las horas configuradas (00:00-04:59)."""
    start = int(NORMATIVE_LIMITS["night_window_start_hour"])
    end = int(NORMATIVE_LIMITS["night_window_end_hour"])
    expected = (flagged["timestamp"].dt.hour >= start) & (
        flagged["timestamp"].dt.hour < end
    )
    assert flagged["is_night_window"].dtype == bool
    pd.testing.assert_series_equal(
        flagged["is_night_window"], expected, check_names=False
    )


def test_cmn_baseline_is_constant_and_non_negative(flagged: pd.DataFrame) -> None:
    """Cada sector tiene una linea base CMN unica y no negativa."""
    baselines = flagged.groupby("sector_id")["cmn_baseline_lps"].nunique()
    assert (baselines == 1).all()
    assert (flagged["cmn_baseline_lps"] >= 0.0).all()
    assert set(flagged["sector_id"]) == set(SECTORS)


def test_cmn_excess_only_exists_at_night(flagged: pd.DataFrame) -> None:
    """El exceso sobre el CMN solo se calcula en horas nocturnas activas."""
    daytime = ~flagged["is_night_window"]
    assert np.allclose(flagged.loc[daytime, "cmn_excess_lps"], 0.0)

    night_active = flagged["is_night_window"] & (flagged["caudal_lps"] > 0.0)
    expected = np.maximum(
        flagged.loc[night_active, "caudal_lps"]
        - flagged.loc[night_active, "cmn_baseline_lps"],
        0.0,
    )
    assert np.allclose(
        flagged.loc[night_active, "cmn_excess_lps"],
        expected.round(2),
        atol=0.01,
    )
    assert (flagged["cmn_excess_lps"] >= 0.0).all()


def test_physical_leaks_are_detected(flagged: pd.DataFrame) -> None:
    """Al menos el 90% de las fugas inyectadas activa la alerta fisica."""
    leaks = _rows_with_event(flagged, EVENT_LEAK)
    assert not leaks.empty
    detected = leaks["physical_leak_alert"].mean()
    assert detected >= 0.90
    assert (leaks["anomaly_type"] == TYPE_LEAK).mean() >= 0.90


def test_commercial_fraud_is_detected(flagged: pd.DataFrame) -> None:
    """Todo fraude comercial inyectado activa su alerta y su tipo primario."""
    frauds = _rows_with_event(flagged, EVENT_FRAUD)
    assert not frauds.empty
    assert frauds["commercial_fraud_alert"].all()
    assert (frauds["anomaly_type"] == TYPE_FRAUD).all()


def test_low_chlorine_is_detected(flagged: pd.DataFrame) -> None:
    """El cloro inyectado bajo 0.5 mg/L activa la alerta de calidad."""
    rows = _rows_with_event(flagged, EVENT_LOW_CHLORINE)
    assert not rows.empty
    assert rows["quality_chlorine_alert"].all()
    assert (rows["anomaly_type"] == TYPE_CHLORINE).all()


def test_high_turbidity_is_detected(flagged: pd.DataFrame) -> None:
    """La turbiedad inyectada sobre 5 NTU se clasifica como turbiedad alta."""
    rows = _rows_with_event(flagged, EVENT_HIGH_TURBIDITY)
    assert not rows.empty
    assert rows["turbiedad_ntu"].gt(
        NORMATIVE_LIMITS["turbiedad_max_ntu"]
    ).all()
    assert (rows["anomaly_type"] == TYPE_TURBIDITY).all()


def test_low_pressure_is_detected(flagged: pd.DataFrame) -> None:
    """La baja presion inyectada en cota alta activa la alerta normativa."""
    rows = _rows_with_event(flagged, EVENT_LOW_PRESSURE)
    assert not rows.empty
    assert rows["pressure_norm_alert"].all()
    assert (rows["anomaly_type"] == TYPE_PRESSURE).all()


def test_pressure_rule_respects_normative_range(flagged: pd.DataFrame) -> None:
    """Toda alerta de presion esta efectivamente fuera del rango normativo."""
    alerts = flagged["pressure_norm_alert"]
    low = NORMATIVE_LIMITS["presion_min_mca"]
    high = NORMATIVE_LIMITS["presion_max_mca"]
    values = flagged.loc[alerts, "presion_mca"]
    assert ((values < low) | (values > high)).all()


def test_chlorine_rule_respects_normative_limit(flagged: pd.DataFrame) -> None:
    """Toda alerta de cloro queda por debajo del minimo DIGESA."""
    alerts = flagged["quality_chlorine_alert"]
    values = flagged.loc[alerts, "cloro_mg_l"]
    assert (values < NORMATIVE_LIMITS["cloro_min_mg_l"]).all()


def test_alert_columns_are_boolean(flagged: pd.DataFrame) -> None:
    """Las cuatro banderas de alerta son booleanas y sin nulos."""
    for column in (
        "physical_leak_alert",
        "commercial_fraud_alert",
        "quality_chlorine_alert",
        "pressure_norm_alert",
    ):
        assert flagged[column].dtype == bool, column
        assert not flagged[column].isna().any(), column


def test_anomaly_score_is_normalized(flagged: pd.DataFrame) -> None:
    """El score de anomalia esta acotado entre 0 y 1."""
    assert flagged["anomaly_score"].between(0.0, 1.0).all()
    assert flagged["anomaly_score"].notna().all()


def test_anomaly_types_and_severities_are_valid(flagged: pd.DataFrame) -> None:
    """Tipos y severidades pertenecen al catalogo oficial."""
    assert set(flagged["anomaly_type"].unique()).issubset(ALLOWED_TYPES)
    assert set(flagged["severity"].unique()).issubset(set(SEVERITY_ORDER))
    assert (flagged["anomaly_type"] != TYPE_NORMAL).sum() > 0


def test_rule_alerts_have_higher_scores(flagged: pd.DataFrame) -> None:
    """Las filas con regla de negocio disparada pesan mas en el score."""
    rule_alert = flagged[
        [
            "physical_leak_alert",
            "commercial_fraud_alert",
            "quality_chlorine_alert",
            "pressure_norm_alert",
        ]
    ].any(axis=1)
    assert flagged.loc[rule_alert, "anomaly_score"].mean() > flagged.loc[
        ~rule_alert, "anomaly_score"
    ].mean()


def test_statistical_detector_finds_atypical_rows(flagged: pd.DataFrame) -> None:
    """IsolationForest aporta al menos una fila de patron atipico."""
    assert (flagged["anomaly_type"] == TYPE_STATISTICAL).sum() > 0


def test_summary_one_row_per_sector(flagged: pd.DataFrame) -> None:
    """El resumen sectorial devuelve exactamente una fila por sector."""
    summary = summarize_anomalies_by_sector(flagged)
    assert len(summary) == len(SECTORS)
    assert list(summary["sector_id"]) == sorted(SECTORS)
    assert summary["sector_id"].is_unique
    assert summary["registros"].sum() == len(flagged)


def test_summary_counts_match_flagged_data(flagged: pd.DataFrame) -> None:
    """Los conteos del resumen coinciden con las banderas del DataFrame."""
    summary = summarize_anomalies_by_sector(flagged).set_index("sector_id")
    for sector_id, group in flagged.groupby("sector_id"):
        row = summary.loc[sector_id]
        assert row["registros"] == len(group)
        assert row["alertas_totales"] == int(
            (group["anomaly_type"] != TYPE_NORMAL).sum()
        )
        assert row["fugas_fisicas"] == int(group["physical_leak_alert"].sum())
        assert row["fraudes_comerciales"] == int(
            group["commercial_fraud_alert"].sum()
        )
        assert row["alertas_cloro"] == int(
            (group["anomaly_type"] == TYPE_CHLORINE).sum()
        )
        assert row["alertas_turbiedad"] == int(
            (group["anomaly_type"] == TYPE_TURBIDITY).sum()
        )
        assert row["alertas_presion"] == int(
            (group["anomaly_type"] == TYPE_PRESSURE).sum()
        )
        assert row["alertas_estadisticas"] == int(
            (group["anomaly_type"] == TYPE_STATISTICAL).sum()
        )


def test_summary_percentages_and_scores(flagged: pd.DataFrame) -> None:
    """Porcentajes y scores del resumen estan en rango y bien calculados."""
    summary = summarize_anomalies_by_sector(flagged)
    assert summary["alertas_porcentaje"].between(0.0, 100.0).all()
    assert summary["score_promedio"].between(0.0, 1.0).all()
    assert summary["score_maximo"].between(0.0, 1.0).all()
    assert (summary["score_maximo"] >= summary["score_promedio"]).all()

    expected_pct = (
        summary["alertas_totales"] / summary["registros"] * 100.0
    ).round(2)
    assert np.allclose(summary["alertas_porcentaje"], expected_pct, atol=0.01)


def test_summary_returns_expected_columns(flagged: pd.DataFrame) -> None:
    """El resumen respeta el esquema declarado."""
    summary = summarize_anomalies_by_sector(flagged)
    assert list(summary.columns) == [
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


def test_summary_empty_dataframe_returns_schema() -> None:
    """Un DataFrame vacio retorna un resumen vacio con columnas."""
    empty = summarize_anomalies_by_sector(pd.DataFrame())
    assert empty.empty
    assert "sector_id" in empty.columns
    assert "severidad_maxima" in empty.columns


def test_summary_requires_detection_columns(flagged: pd.DataFrame) -> None:
    """El resumen exige que el DataFrame provenga de detect_anomalies."""
    with pytest.raises(ValueError):
        summarize_anomalies_by_sector(flagged.drop(columns=["anomaly_type"]))


def test_summary_rejects_non_dataframe() -> None:
    """El resumen valida el tipo de entrada."""
    with pytest.raises(TypeError):
        summarize_anomalies_by_sector([1, 2, 3])  # type: ignore[arg-type]


def test_detect_rejects_non_dataframe() -> None:
    """detect_anomalies exige un pandas.DataFrame."""
    with pytest.raises(TypeError):
        detect_anomalies({"sector_id": ["SEC-01"]})  # type: ignore[arg-type]


def test_detect_rejects_empty_dataframe() -> None:
    """detect_anomalies rechaza DataFrames sin registros."""
    with pytest.raises(ValueError):
        detect_anomalies(pd.DataFrame())


def test_detect_rejects_missing_columns(telemetry: pd.DataFrame) -> None:
    """detect_anomalies exige el contrato minimo de telemetria."""
    with pytest.raises(ValueError):
        detect_anomalies(telemetry.drop(columns=["anf_pct"]))


@pytest.mark.parametrize("contamination", [0.0, -0.1, 0.51, 1.0])
def test_detect_rejects_invalid_contamination(
    telemetry: pd.DataFrame, contamination: float
) -> None:
    """contamination debe pertenecer al intervalo (0, 0.5]."""
    with pytest.raises(ValueError):
        detect_anomalies(telemetry, contamination=contamination)


@pytest.mark.parametrize("contamination", [True, "0.05", None])
def test_detect_rejects_invalid_contamination_type(
    telemetry: pd.DataFrame, contamination: object
) -> None:
    """contamination debe ser numerico."""
    with pytest.raises(TypeError):
        detect_anomalies(telemetry, contamination=contamination)  # type: ignore[arg-type]


def test_detect_accepts_boundary_contamination(telemetry: pd.DataFrame) -> None:
    """El limite superior 0.5 es valido."""
    result = detect_anomalies(telemetry, contamination=0.5)
    assert len(result) == len(telemetry)
    assert result["anomaly_score"].between(0.0, 1.0).all()
