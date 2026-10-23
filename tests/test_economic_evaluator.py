"""Pruebas unitarias del evaluador economico SUNASS de EPS Ilo.

Valida la valorizacion del Agua No Facturada (ANF), la separacion entre
perdida fisica y comercial, el semaforo normativo y el simulador What-If
de retorno de inversion (ROI, payback y VAN a 12 meses).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.anomaly_detector import detect_anomalies
from src.config import NORMATIVE_LIMITS, TARIFF_STRUCTURE
from src.economic_evaluator import (
    ANNUAL_DISCOUNT_RATE,
    SEMAFORO_AMARILLO,
    SEMAFORO_ROJO,
    SEMAFORO_VERDE,
    evaluate_economic_impact,
    simulate_anf_reduction_roi,
)
from src.telemetry_generator import generate_telemetry_data

DAYS = 30
SEED = 42
TARIFA_MEDIA = float(TARIFF_STRUCTURE["tarifa_media_ponderada"])
COSTO_VARIABLE = float(TARIFF_STRUCTURE["costo_variable_produccion"])


def _single_sector_frame(
    produced: float,
    anf: float,
    *,
    fraud: bool = False,
    leak: bool = False,
    sector_id: str = "SEC-01",
) -> pd.DataFrame:
    """Construye una fila sintetica para probar el semaforo y la atribucion."""
    billed = produced - anf
    return pd.DataFrame(
        {
            "sector_id": [sector_id],
            "sector_name": ["Pampa Inalambrica"],
            "volumen_producido_m3": [produced],
            "volumen_facturado_m3": [billed],
            "anf_m3": [anf],
            "anf_pct": [anf / produced * 100.0 if produced else 0.0],
            "physical_leak_alert": [leak],
            "commercial_fraud_alert": [fraud],
        }
    )


@pytest.fixture(scope="module")
def flagged() -> pd.DataFrame:
    """Telemetria de 30 dias procesada por el detector de anomalias."""
    telemetry = generate_telemetry_data(days=DAYS, seed=SEED)
    return detect_anomalies(telemetry, contamination=0.05)


@pytest.fixture(scope="module")
def economic(flagged: pd.DataFrame) -> dict:
    """Evaluacion economica del dataset principal."""
    return evaluate_economic_impact(flagged)


def test_result_contract_keys(economic: dict) -> None:
    """El resultado expone todas las metricas del contrato."""
    expected = {
        "volumen_producido_total_m3",
        "volumen_facturado_total_m3",
        "anf_total_m3",
        "anf_porcentaje",
        "perdida_fisica_m3",
        "perdida_comercial_m3",
        "perdida_economica_soles",
        "costo_energia_quimicos_perdido_soles",
        "semaforo_sunass",
        "sector_breakdown",
    }
    assert expected.issubset(economic.keys())
    assert isinstance(economic["sector_breakdown"], pd.DataFrame)


def test_global_totals_match_telemetry(
    flagged: pd.DataFrame, economic: dict
) -> None:
    """Los totales globales coinciden con la suma de la telemetria."""
    assert economic["volumen_producido_total_m3"] == pytest.approx(
        flagged["volumen_producido_m3"].sum(), abs=0.01
    )
    assert economic["volumen_facturado_total_m3"] == pytest.approx(
        flagged["volumen_facturado_m3"].sum(), abs=0.01
    )
    assert economic["anf_total_m3"] == pytest.approx(
        flagged["anf_m3"].sum(), abs=0.01
    )


def test_global_anf_percentage(economic: dict) -> None:
    """El porcentaje global de ANF se calcula sobre el volumen producido."""
    expected = (
        economic["anf_total_m3"]
        / economic["volumen_producido_total_m3"]
        * 100.0
    )
    assert economic["anf_porcentaje"] == pytest.approx(expected, abs=0.01)
    assert 0.0 <= economic["anf_porcentaje"] <= 100.0


def test_loss_components_sum_to_anf(economic: dict) -> None:
    """Perdida fisica + perdida comercial reconstruyen el ANF total."""
    total = economic["perdida_fisica_m3"] + economic["perdida_comercial_m3"]
    assert total == pytest.approx(economic["anf_total_m3"], abs=0.01)
    assert economic["perdida_fisica_m3"] >= 0.0
    assert economic["perdida_comercial_m3"] >= 0.0


def test_economic_valuation_uses_tariff(economic: dict) -> None:
    """La valorizacion usa la tarifa media y el costo variable oficiales."""
    expected_loss = economic["anf_total_m3"] * TARIFA_MEDIA
    expected_cost = economic["anf_total_m3"] * COSTO_VARIABLE
    assert economic["perdida_economica_soles"] == pytest.approx(
        expected_loss, abs=0.01
    )
    assert economic["costo_energia_quimicos_perdido_soles"] == pytest.approx(
        expected_cost, abs=0.01
    )
    assert (
        economic["perdida_economica_soles"]
        > economic["costo_energia_quimicos_perdido_soles"]
    )


def test_sector_breakdown_contract(economic: dict) -> None:
    """El desagregado sectorial respeta columnas y una fila por sector."""
    breakdown = economic["sector_breakdown"]
    assert list(breakdown.columns) == [
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
    assert len(breakdown) == 3
    assert list(breakdown["sector_id"]) == sorted(breakdown["sector_id"])
    assert breakdown["sector_id"].is_unique


def test_sector_breakdown_totals(
    flagged: pd.DataFrame, economic: dict
) -> None:
    """Los subtotales sectoriales cuadran con la telemetria de cada sector."""
    breakdown = economic["sector_breakdown"].set_index("sector_id")
    for sector_id, group in flagged.groupby("sector_id"):
        row = breakdown.loc[sector_id]
        assert row["volumen_producido_m3"] == pytest.approx(
            group["volumen_producido_m3"].sum(), abs=0.01
        )
        assert row["volumen_facturado_m3"] == pytest.approx(
            group["volumen_facturado_m3"].sum(), abs=0.01
        )
        assert row["anf_m3"] == pytest.approx(
            group["anf_m3"].sum(), abs=0.01
        )
        assert row["alertas_fugas"] == int(
            group["physical_leak_alert"].sum()
        )
        assert row["alertas_fraudes"] == int(
            group["commercial_fraud_alert"].sum()
        )


def test_sector_percentages_and_valuation(economic: dict) -> None:
    """Cada sector calcula su ANF % y su valorizacion correctamente."""
    breakdown = economic["sector_breakdown"]
    expected_pct = (
        breakdown["anf_m3"] / breakdown["volumen_producido_m3"] * 100.0
    ).round(3)
    assert np.allclose(breakdown["anf_pct"], expected_pct, atol=0.01)
    assert np.allclose(
        breakdown["perdida_economica_soles"],
        (breakdown["anf_m3"] * TARIFA_MEDIA).round(3),
        atol=0.01,
    )
    assert np.allclose(
        breakdown["costo_energia_quimicos_soles"],
        (breakdown["anf_m3"] * COSTO_VARIABLE).round(3),
        atol=0.01,
    )


def test_semaforo_global_is_consistent(economic: dict) -> None:
    """El semaforo global sigue los umbrales SUNASS configurados."""
    pct = economic["anf_porcentaje"]
    critical = float(NORMATIVE_LIMITS["anf_alerta_critica_pct"])
    warning = float(NORMATIVE_LIMITS["anf_alerta_amarilla_pct"])
    if pct > critical:
        assert economic["semaforo_sunass"] == SEMAFORO_ROJO
    elif pct > warning:
        assert economic["semaforo_sunass"] == SEMAFORO_AMARILLO
    else:
        assert economic["semaforo_sunass"] == SEMAFORO_VERDE


@pytest.mark.parametrize(
    ("produced", "anf", "expected"),
    [
        (1000.0, 200.0, SEMAFORO_VERDE),
        (1000.0, 279.9, SEMAFORO_VERDE),
        (1000.0, 281.0, SEMAFORO_AMARILLO),
        (1000.0, 349.9, SEMAFORO_AMARILLO),
        (1000.0, 351.0, SEMAFORO_ROJO),
        (1000.0, 500.0, SEMAFORO_ROJO),
    ],
)
def test_semaforo_thresholds(
    produced: float, anf: float, expected: str
) -> None:
    """Se prueban valores a ambos lados de los umbrales 28% y 35%."""
    result = evaluate_economic_impact(_single_sector_frame(produced, anf))
    assert result["semaforo_sunass"] == expected
    assert result["sector_breakdown"].loc[0, "semaforo_sunass"] == expected


def test_fraud_loss_is_attributed_to_commercial() -> None:
    """El ANF de filas con fraude se atribuye a perdida comercial."""
    frame = pd.concat(
        [
            _single_sector_frame(1000.0, 100.0, fraud=True),
            _single_sector_frame(1000.0, 200.0),
        ],
        ignore_index=True,
    )
    result = evaluate_economic_impact(frame)
    assert result["perdida_comercial_m3"] == pytest.approx(100.0, abs=0.01)
    assert result["perdida_fisica_m3"] == pytest.approx(200.0, abs=0.01)
    assert result["anf_total_m3"] == pytest.approx(300.0, abs=0.01)


def test_fraud_and_leak_together_remain_physical() -> None:
    """Si una fila es fuga y fraude a la vez, prevalece la perdida fisica."""
    frame = _single_sector_frame(1000.0, 150.0, fraud=True, leak=True)
    result = evaluate_economic_impact(frame)
    assert result["perdida_comercial_m3"] == pytest.approx(0.0, abs=0.01)
    assert result["perdida_fisica_m3"] == pytest.approx(150.0, abs=0.01)


def test_missing_alert_columns_are_optional() -> None:
    """Sin banderas de alerta, todo el ANF se asume perdida fisica."""
    frame = _single_sector_frame(1000.0, 300.0).drop(
        columns=["physical_leak_alert", "commercial_fraud_alert"]
    )
    result = evaluate_economic_impact(frame)
    assert result["perdida_comercial_m3"] == pytest.approx(0.0, abs=0.01)
    assert result["perdida_fisica_m3"] == pytest.approx(300.0, abs=0.01)


def test_evaluation_does_not_mutate_input(flagged: pd.DataFrame) -> None:
    """evaluate_economic_impact opera sobre una copia defensiva."""
    original = flagged.copy(deep=True)
    evaluate_economic_impact(flagged)
    pd.testing.assert_frame_equal(flagged, original)


def test_evaluate_rejects_non_dataframe() -> None:
    """La evaluacion valida el tipo de entrada."""
    with pytest.raises(TypeError):
        evaluate_economic_impact({"anf_m3": [10.0]})  # type: ignore[arg-type]


def test_evaluate_rejects_empty_dataframe() -> None:
    """La evaluacion rechaza DataFrames vacios."""
    with pytest.raises(ValueError):
        evaluate_economic_impact(pd.DataFrame())


def test_evaluate_rejects_missing_columns(flagged: pd.DataFrame) -> None:
    """La evaluacion exige el contrato minimo de columnas."""
    with pytest.raises(ValueError):
        evaluate_economic_impact(flagged.drop(columns=["anf_m3"]))


def test_roi_contract_and_math() -> None:
    """El simulador ROI aplica la formula tarifaria y financiera declarada."""
    current_anf = 1000.0
    target = 20.0
    investment = 45000.0
    result = simulate_anf_reduction_roi(current_anf, target, investment)

    recovered = current_anf * target / 100.0
    monthly = recovered * TARIFA_MEDIA
    annual = monthly * 12.0
    monthly_rate = (1.0 + ANNUAL_DISCOUNT_RATE) ** (1.0 / 12.0) - 1.0
    van = (
        sum(monthly / ((1.0 + monthly_rate) ** month) for month in range(1, 13))
        - investment
    )

    assert set(result) == {
        "m3_recuperados_mes",
        "ahorro_mensual_soles",
        "ahorro_anual_soles",
        "payback_meses",
        "van_12_meses_soles",
        "roi_porcentaje",
    }
    assert result["m3_recuperados_mes"] == pytest.approx(recovered)
    assert result["ahorro_mensual_soles"] == pytest.approx(monthly, abs=0.01)
    assert result["ahorro_anual_soles"] == pytest.approx(annual, abs=0.01)
    assert result["payback_meses"] == pytest.approx(
        investment / monthly, abs=0.01
    )
    assert result["van_12_meses_soles"] == pytest.approx(van, abs=0.01)
    assert result["roi_porcentaje"] == pytest.approx(
        (annual - investment) / investment * 100.0, abs=0.01
    )


def test_roi_payback_recovers_investment() -> None:
    """El payback, aplicado al ahorro mensual, recupera la inversion."""
    result = simulate_anf_reduction_roi(800.0, 30.0, 30000.0)
    assert (
        result["payback_meses"] * result["ahorro_mensual_soles"]
        == pytest.approx(30000.0, rel=1e-4)
    )


def test_roi_zero_reduction_has_no_return() -> None:
    """Sin reduccion objetivo no hay ahorro ni recuperacion de capital."""
    result = simulate_anf_reduction_roi(1000.0, 0.0, 45000.0)
    assert result["m3_recuperados_mes"] == 0.0
    assert result["ahorro_mensual_soles"] == 0.0
    assert result["ahorro_anual_soles"] == 0.0
    assert result["payback_meses"] == float("inf")
    assert result["van_12_meses_soles"] == -45000.0
    assert result["roi_porcentaje"] == -100.0


def test_roi_full_reduction() -> None:
    """Una reduccion del 100% recupera todo el ANF simulado."""
    result = simulate_anf_reduction_roi(500.0, 100.0, 10000.0)
    assert result["m3_recuperados_mes"] == pytest.approx(500.0)
    assert result["ahorro_mensual_soles"] == pytest.approx(
        500.0 * TARIFA_MEDIA, abs=0.01
    )


@pytest.mark.parametrize(
    ("current_anf", "target", "investment"),
    [
        (-1.0, 20.0, 45000.0),
        (1000.0, -0.1, 45000.0),
        (1000.0, 100.1, 45000.0),
        (1000.0, 20.0, 0.0),
        (1000.0, 20.0, -500.0),
    ],
)
def test_roi_rejects_out_of_range_values(
    current_anf: float, target: float, investment: float
) -> None:
    """Los parametros del ROI deben estar en rangos validos."""
    with pytest.raises(ValueError):
        simulate_anf_reduction_roi(current_anf, target, investment)


@pytest.mark.parametrize(
    ("current_anf", "target", "investment"),
    [
        (True, 20.0, 45000.0),
        (1000.0, "20", 45000.0),
        (1000.0, 20.0, None),
    ],
)
def test_roi_rejects_non_numeric_types(
    current_anf: object, target: object, investment: object
) -> None:
    """Los parametros del ROI deben ser numericos."""
    with pytest.raises(TypeError):
        simulate_anf_reduction_roi(  # type: ignore[arg-type]
            current_anf, target, investment
        )


def test_roi_rejects_non_finite_values() -> None:
    """Los parametros del ROI deben ser finitos."""
    with pytest.raises(ValueError):
        simulate_anf_reduction_roi(float("nan"), 20.0)
    with pytest.raises(ValueError):
        simulate_anf_reduction_roi(1000.0, float("inf"))


def test_roi_zero_anf_edge_case() -> None:
    """Con ANF actual igual a cero el plan no genera ahorro."""
    result = simulate_anf_reduction_roi(0.0, 50.0, 45000.0)
    assert result["m3_recuperados_mes"] == 0.0
    assert result["payback_meses"] == float("inf")
    assert result["roi_porcentaje"] == -100.0


def test_roi_accepts_numpy_scalars() -> None:
    """El simulador acepta escalares de numpy."""
    result = simulate_anf_reduction_roi(
        np.float64(1000.0), np.int64(20), np.float64(45000.0)
    )
    assert result["m3_recuperados_mes"] == pytest.approx(200.0)
    assert np.isfinite(result["van_12_meses_soles"])
