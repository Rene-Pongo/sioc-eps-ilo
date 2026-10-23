"""Pruebas unitarias del motor de telemetria hidraulica de EPS Ilo.

Valida el contrato de datos (14 columnas obligatorias), la coherencia fisica
y volumetrica de los registros, la reproducibilidad por semilla, la
inyeccion de eventos y la validacion de parametros publicos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import NORMATIVE_LIMITS, SECTORS
from src.telemetry_generator import (
    EVENT_FRAUD,
    EVENT_HIGH_TURBIDITY,
    EVENT_LEAK,
    EVENT_LOW_CHLORINE,
    EVENT_LOW_PRESSURE,
    TELEMETRY_COLUMNS,
    generate_telemetry_data,
)

DAYS = 30
SEED = 42


@pytest.fixture(scope="module")
def telemetry() -> pd.DataFrame:
    """Telemetria de 30 dias con eventos inyectados (dataset principal)."""
    return generate_telemetry_data(days=DAYS, seed=SEED, inject_anomalies=True)


@pytest.fixture(scope="module")
def telemetry_clean() -> pd.DataFrame:
    """Telemetria sin eventos inyectados, util para validar la linea base."""
    return generate_telemetry_data(days=DAYS, seed=SEED, inject_anomalies=False)


def test_contract_columns_and_order(telemetry: pd.DataFrame) -> None:
    """El DataFrame expone exactamente las 14 columnas del contrato."""
    assert list(telemetry.columns) == TELEMETRY_COLUMNS
    assert len(TELEMETRY_COLUMNS) == 14


def test_shape_three_sectors_hourly(telemetry: pd.DataFrame) -> None:
    """Se generan 24 registros horarios por dia para cada uno de los 3 sectores."""
    assert len(telemetry) == DAYS * 24 * len(SECTORS)
    assert sorted(telemetry["sector_id"].unique()) == sorted(SECTORS)


def test_sector_metadata_matches_config(telemetry: pd.DataFrame) -> None:
    """Cada sector conserva el nombre oficial y una fuente de abastecimiento."""
    observed = (
        telemetry[["sector_id", "sector_name"]]
        .drop_duplicates()
        .set_index("sector_id")["sector_name"]
        .to_dict()
    )
    expected = {sid: data["name"] for sid, data in SECTORS.items()}
    assert observed == expected
    assert telemetry["fuente_principal"].notna().all()
    assert (telemetry["fuente_principal"].astype(str).str.len() > 0).all()


def test_timestamp_is_hourly_and_sorted(telemetry: pd.DataFrame) -> None:
    """La serie es horaria, sin duplicados y ordenada por timestamp/sector."""
    assert pd.api.types.is_datetime64_any_dtype(telemetry["timestamp"])
    assert not telemetry.duplicated(subset=["timestamp", "sector_id"]).any()
    ordered = telemetry.sort_values(["timestamp", "sector_id"], kind="stable")
    pd.testing.assert_frame_equal(
        telemetry.reset_index(drop=True),
        ordered.reset_index(drop=True),
    )
    for _, group in telemetry.groupby("sector_id"):
        assert group["timestamp"].diff().dropna().eq(pd.Timedelta(hours=1)).all()


def test_no_missing_values_in_critical_columns(telemetry: pd.DataFrame) -> None:
    """Las variables operativas y del contrato no contienen nulos."""
    critical = [column for column in TELEMETRY_COLUMNS if column != "injected_event"]
    assert telemetry[critical].isna().sum().sum() == 0


def test_volume_identities(telemetry: pd.DataFrame) -> None:
    """Producido = caudal x 3.6; ANF = producido x anf_pct; facturado = resto."""
    expected_produced = (telemetry["caudal_lps"] * 3.6).round(3)
    expected_anf = (
        telemetry["volumen_producido_m3"] * telemetry["anf_pct"] / 100.0
    ).round(3)
    expected_billed = (
        telemetry["volumen_producido_m3"] - telemetry["anf_m3"]
    ).clip(lower=0.0).round(3)

    pd.testing.assert_series_equal(
        telemetry["volumen_producido_m3"],
        expected_produced,
        check_names=False,
    )
    pd.testing.assert_series_equal(
        telemetry["anf_m3"], expected_anf, check_names=False
    )
    pd.testing.assert_series_equal(
        telemetry["volumen_facturado_m3"],
        expected_billed,
        check_names=False,
    )


def test_volumes_are_non_negative(telemetry: pd.DataFrame) -> None:
    """Ningun volumen ni porcentaje de ANF puede ser negativo."""
    for column in (
        "volumen_producido_m3",
        "volumen_facturado_m3",
        "anf_m3",
        "anf_pct",
        "caudal_lps",
        "presion_mca",
        "cloro_mg_l",
        "turbiedad_ntu",
    ):
        assert (telemetry[column] >= 0.0).all(), column


def test_anf_never_exceeds_production(telemetry: pd.DataFrame) -> None:
    """El volumen facturado jamas supera el volumen producido."""
    assert (
        telemetry["volumen_facturado_m3"]
        <= telemetry["volumen_producido_m3"] + 1e-9
    ).all()
    assert telemetry["anf_pct"].between(0.0, 100.0).all()


def test_normative_physical_ranges(telemetry: pd.DataFrame) -> None:
    """Las magnitudes fisicas se mantienen en rangos operativos plausibles."""
    assert telemetry["presion_mca"].between(0.0, 60.0).all()
    assert telemetry["cloro_mg_l"].between(0.0, 5.0).all()
    assert telemetry["turbiedad_ntu"].between(0.0, 12.0).all()
    active = telemetry["caudal_lps"] > 0.0
    # En horas de servicio el cloro residual siempre es positivo.
    assert (telemetry.loc[active, "cloro_mg_l"] >= 0.05).all()
    assert (telemetry.loc[active, "turbiedad_ntu"] >= 0.15).all()


def test_out_of_service_hours_are_zero(telemetry_clean: pd.DataFrame) -> None:
    """Fuera de la ventana de continuidad no hay caudal, presion ni volumen."""
    inactive = telemetry_clean["caudal_lps"] == 0.0
    assert inactive.any()
    for column in (
        "presion_mca",
        "cloro_mg_l",
        "turbiedad_ntu",
        "volumen_producido_m3",
        "volumen_facturado_m3",
        "anf_m3",
    ):
        assert (telemetry_clean.loc[inactive, column] == 0.0).all(), column


def test_continuity_matches_service_hours(telemetry_clean: pd.DataFrame) -> None:
    """Las horas con caudal positivo coinciden con la continuidad declarada."""
    daily = telemetry_clean.assign(
        day=telemetry_clean["timestamp"].dt.normalize(),
        active=(telemetry_clean["caudal_lps"] > 0.0).astype(int),
    ).groupby(["sector_id", "day"], as_index=False).agg(
        active_hours=("active", "sum"),
        continuity=("continuidad_horas", "max"),
    )
    assert (daily["active_hours"] == daily["continuity"]).all()


def test_continuity_bounds_per_sector(telemetry: pd.DataFrame) -> None:
    """La continuidad diaria respeta el rango operativo de cada sector."""
    for sector_id, data in SECTORS.items():
        values = telemetry.loc[
            telemetry["sector_id"] == sector_id, "continuidad_horas"
        ]
        low, high = data["continuity_hours_range"]
        assert values.between(low, high).all()
        assert values.dtype.kind in "iu"


def test_reproducibility_same_seed() -> None:
    """La misma semilla produce exactamente el mismo dataset."""
    first = generate_telemetry_data(days=5, seed=7)
    second = generate_telemetry_data(days=5, seed=7)
    pd.testing.assert_frame_equal(first, second)


def test_different_seed_changes_data() -> None:
    """Semillas distintas generan series distintas."""
    first = generate_telemetry_data(days=5, seed=7)
    second = generate_telemetry_data(days=5, seed=8)
    assert not first["caudal_lps"].equals(second["caudal_lps"])


def test_no_events_when_injection_disabled(telemetry_clean: pd.DataFrame) -> None:
    """Con inject_anomalies=False la columna de eventos queda vacia."""
    assert telemetry_clean["injected_event"].isna().all()


def test_events_are_injected_and_labeled(telemetry: pd.DataFrame) -> None:
    """Se inyectan los cinco tipos de evento del catalogo operativo."""
    labels: set[str] = set()
    for value in telemetry["injected_event"].dropna():
        labels.update(str(value).split("|"))

    expected = {
        EVENT_LEAK,
        EVENT_FRAUD,
        EVENT_LOW_PRESSURE,
        EVENT_LOW_CHLORINE,
        EVENT_HIGH_TURBIDITY,
    }
    assert labels == expected
    assert telemetry["injected_event"].notna().sum() > 0


def test_days_parameter_controls_output() -> None:
    """La cantidad de filas escala linealmente con los dias solicitados."""
    one_day = generate_telemetry_data(days=1, seed=SEED)
    assert len(one_day) == 24 * len(SECTORS)
    assert one_day["timestamp"].dt.normalize().nunique() == 1


@pytest.mark.parametrize("days", [0, -1, 3651])
def test_invalid_days_raise_value_error(days: int) -> None:
    """Dias fuera del rango permitido lanzan ValueError."""
    with pytest.raises(ValueError):
        generate_telemetry_data(days=days)


@pytest.mark.parametrize("days", [True, 30.5, "30", None])
def test_invalid_days_type_raises_type_error(days: object) -> None:
    """Un tipo no entero para days lanza TypeError."""
    with pytest.raises(TypeError):
        generate_telemetry_data(days=days)  # type: ignore[arg-type]


def test_negative_seed_raises_value_error() -> None:
    """La semilla debe ser no negativa."""
    with pytest.raises(ValueError):
        generate_telemetry_data(days=1, seed=-5)


@pytest.mark.parametrize("seed", [True, 1.5, "42", None])
def test_invalid_seed_type_raises_type_error(seed: object) -> None:
    """Un tipo no entero para seed lanza TypeError."""
    with pytest.raises(TypeError):
        generate_telemetry_data(days=1, seed=seed)  # type: ignore[arg-type]


def test_numpy_integer_parameters_are_accepted() -> None:
    """Los enteros de numpy son aceptados como parametros validos."""
    frame = generate_telemetry_data(days=np.int64(1), seed=np.int64(0))
    assert len(frame) == 24 * len(SECTORS)
    assert frame["anf_pct"].max() <= 100.0


def test_normative_limits_are_consistent() -> None:
    """Los limites usados por el generador son coherentes entre si."""
    assert NORMATIVE_LIMITS["presion_min_mca"] < NORMATIVE_LIMITS["presion_max_mca"]
    assert NORMATIVE_LIMITS["cloro_min_mg_l"] < NORMATIVE_LIMITS["cloro_max_mg_l"]
    assert 0.0 < NORMATIVE_LIMITS["turbiedad_max_ntu"]
