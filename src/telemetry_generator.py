"""Motor de generacion de telemetria hidraulica para EPS Ilo S.A.

Genera un DataFrame horario y reproducible con las variables operativas de
los tres sectores hidraulicos de Ilo: caudal, presion, cloro residual libre,
turbiedad, continuidad, volumenes producidos/facturados y Agua No Facturada
(ANF).

El contrato de columnas es obligatorio para todas las fases del proyecto:

    timestamp, sector_id, sector_name, fuente_principal, caudal_lps,
    presion_mca, cloro_mg_l, turbiedad_ntu, continuidad_horas,
    volumen_producido_m3, volumen_facturado_m3, anf_m3, anf_pct,
    injected_event

La columna ``injected_event`` documenta los eventos simulados incorporados
al dataset (fuga fisica, fraude comercial, baja presion, cloro bajo o
turbiedad alta). En filas normales su valor es ``None``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import (
    HOURLY_DEMAND_PROFILE,
    NORMATIVE_LIMITS,
    SECTORS,
    SOURCES,
    TELEMETRY_DEFAULT_DAYS,
    TELEMETRY_DEFAULT_SEED,
)

# Contrato de datos: orden obligatorio de columnas del DataFrame.
TELEMETRY_COLUMNS = [
    "timestamp",
    "sector_id",
    "sector_name",
    "fuente_principal",
    "caudal_lps",
    "presion_mca",
    "cloro_mg_l",
    "turbiedad_ntu",
    "continuidad_horas",
    "volumen_producido_m3",
    "volumen_facturado_m3",
    "anf_m3",
    "anf_pct",
    "injected_event",
]

# Etiquetas de eventos inyectados (usadas por el detector de anomalias).
EVENT_LEAK = "fuga_fisica"
EVENT_FRAUD = "fraude_comercial"
EVENT_LOW_PRESSURE = "baja_presion"
EVENT_LOW_CHLORINE = "cloro_bajo"
EVENT_HIGH_TURBIDITY = "turbiedad_alta"

_HOURS_PER_DAY = 24


def _validate_parameters(days: int, seed: int) -> tuple[int, int]:
    """Valida y normaliza los parametros publicos del generador."""
    if isinstance(days, bool) or not isinstance(days, (int, np.integer)):
        raise TypeError("days debe ser un entero mayor o igual a 1.")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("seed debe ser un entero.")

    days = int(days)
    seed = int(seed)

    if days < 1:
        raise ValueError("days debe ser mayor o igual a 1.")
    if days > 3650:
        raise ValueError("days no debe superar 3650 dias.")
    if seed < 0:
        raise ValueError("seed debe ser mayor o igual a 0.")

    return days, seed


def _build_sector_frame(
    sector_id: str,
    sector: dict,
    dates: list[pd.Timestamp],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Construye la telemetria base (sin eventos) de un sector.

    Se modela un registro por hora. La continuidad diaria define la ventana
    de servicio; fuera de ella el caudal, la presion y los volumenes son
    cero, pero se conserva el valor de continuidad del dia.
    """
    source_name = SOURCES[sector["source_id"]]["name"]
    continuity_min, continuity_max = sector["continuity_hours_range"]

    daily_continuity = rng.integers(
        continuity_min, continuity_max + 1, size=len(dates)
    )
    daily_start_hour = np.array(
        [rng.integers(0, _HOURS_PER_DAY - int(c) + 1) for c in daily_continuity]
    )
    daily_anf = np.clip(
        rng.normal(sector["base_anf_pct"], 1.8, size=len(dates)),
        8.0,
        55.0,
    )

    records: list[dict] = []

    for day_index, day in enumerate(dates):
        continuity = int(daily_continuity[day_index])
        start_hour = int(daily_start_hour[day_index])
        end_hour = start_hour + continuity
        day_anf = float(daily_anf[day_index])

        for hour in range(_HOURS_PER_DAY):
            timestamp = day + pd.Timedelta(hours=hour)
            in_service = start_hour <= hour < end_hour
            demand_factor = HOURLY_DEMAND_PROFILE[hour]

            if in_service:
                flow = (
                    sector["base_demand_lps"]
                    * demand_factor
                    * float(rng.normal(1.0, 0.035))
                )
                flow = max(flow, 0.0)

                pressure = (
                    sector["base_pressure_mca"]
                    - sector["pressure_drop_coef"] * (demand_factor - 0.60)
                    + float(rng.normal(0.0, 1.30))
                )
                pressure = float(
                    np.clip(
                        pressure,
                        0.0,
                        NORMATIVE_LIMITS["presion_max_mca"] + 5.0,
                    )
                )

                chlorine = (
                    sector["base_chlorine_mg_l"]
                    + float(rng.normal(0.0, 0.07))
                    - 0.02 * (demand_factor - 1.0)
                )
                chlorine = float(
                    np.clip(
                        chlorine,
                        0.05,
                        NORMATIVE_LIMITS["cloro_max_mg_l"],
                    )
                )

                turbidity = float(
                    rng.lognormal(
                        mean=float(np.log(sector["base_turbidity_ntu"])),
                        sigma=0.22,
                    )
                )
                turbidity = float(np.clip(turbidity, 0.15, 12.0))

                anf_pct = float(
                    np.clip(
                        day_anf + float(rng.normal(0.0, 1.0)),
                        5.0,
                        60.0,
                    )
                )
            else:
                flow = 0.0
                pressure = 0.0
                chlorine = 0.0
                turbidity = 0.0
                anf_pct = 0.0

            records.append(
                {
                    "timestamp": timestamp,
                    "sector_id": sector_id,
                    "sector_name": sector["name"],
                    "fuente_principal": source_name,
                    "caudal_lps": flow,
                    "presion_mca": pressure,
                    "cloro_mg_l": chlorine,
                    "turbiedad_ntu": turbidity,
                    "continuidad_horas": continuity,
                    "anf_pct": anf_pct,
                    "injected_event": None,
                }
            )

    return pd.DataFrame.from_records(records)


def _event_mask(
    df: pd.DataFrame,
    sector_id: str,
    event_day: pd.Timestamp,
    start_hour: int,
    duration_hours: int,
    only_active: bool = False,
) -> pd.Series:
    """Construye la mascara booleana de una ventana horaria de evento."""
    end_hour = start_hour + duration_hours
    mask = (
        (df["sector_id"] == sector_id)
        & (df["timestamp"].dt.normalize() == event_day)
        & (df["timestamp"].dt.hour >= start_hour)
        & (df["timestamp"].dt.hour < end_hour)
    )
    if only_active:
        mask &= df["caudal_lps"] > 0.0
    return mask


def _set_event(
    df: pd.DataFrame,
    mask: pd.Series,
    event_label: str,
    **column_values: object,
) -> None:
    """Aplica un evento sobre las filas de la mascara y registra su etiqueta."""
    if not bool(mask.any()):
        return

    for column, value in column_values.items():
        if callable(value):
            df.loc[mask, column] = value(df.loc[mask, column])
        else:
            df.loc[mask, column] = value

    previous = df.loc[mask, "injected_event"]
    df.loc[mask, "injected_event"] = [
        event_label if prev is None or pd.isna(prev) else f"{prev}|{event_label}"
        for prev in previous
    ]


def _inject_events(
    df: pd.DataFrame,
    dates: list[pd.Timestamp],
    rng: np.random.Generator,
) -> None:
    """Inyecta eventos operativos realistas y reproducibles por sector."""
    n_days = len(dates)

    def random_day() -> pd.Timestamp:
        return dates[int(rng.integers(0, n_days))]

    def random_hours(start_min: int, start_max: int, duration_min: int, duration_max: int) -> tuple[int, int]:
        start = int(rng.integers(start_min, start_max + 1))
        duration = int(rng.integers(duration_min, duration_max + 1))
        return start, duration

    # ------------------------------------------------------------------
    # Fugas fisicas nocturnas: el caudal se eleva sobre el CMN mientras el
    # volumen facturado no acompana, elevando el ANF del sector.
    # ------------------------------------------------------------------
    leaks = {"SEC-01": 2, "SEC-02": 2, "SEC-03": 1}
    for sector_id, n_events in leaks.items():
        base_flow = SECTORS[sector_id]["base_demand_lps"]
        for _ in range(n_events):
            day = random_day()
            start_hour, duration = random_hours(0, 3, 2, 4)
            mask = _event_mask(df, sector_id, day, start_hour, duration)
            if not bool(mask.any()):
                continue

            leak_multiplier = float(rng.uniform(1.45, 1.85))
            leak_floor = base_flow * float(rng.uniform(0.45, 0.60))

            df.loc[mask, "caudal_lps"] = np.maximum(
                df.loc[mask, "caudal_lps"] * leak_multiplier,
                leak_floor,
            )
            df.loc[mask, "presion_mca"] = np.maximum(
                df.loc[mask, "presion_mca"] - float(rng.uniform(1.0, 2.5)),
                1.0,
            )
            _set_event(
                df,
                mask,
                EVENT_LEAK,
                anf_pct=lambda values: np.minimum(
                    values + float(rng.uniform(6.0, 10.0)),
                    85.0,
                ),
            )

    # ------------------------------------------------------------------
    # Fraude comercial: subregistro de volumen facturado en horario diurno.
    # ------------------------------------------------------------------
    frauds = {"SEC-01": 1, "SEC-02": 1, "SEC-03": 2}
    for sector_id, n_events in frauds.items():
        for _ in range(n_events):
            day = random_day()
            start_hour, duration = random_hours(10, 14, 4, 7)
            mask = _event_mask(
                df, sector_id, day, start_hour, duration, only_active=True
            )
            if not bool(mask.any()):
                continue

            extra_anf = float(rng.uniform(18.0, 30.0))
            _set_event(
                df,
                mask,
                EVENT_FRAUD,
                anf_pct=lambda values: np.minimum(values + extra_anf, 88.0),
            )

    # ------------------------------------------------------------------
    # Baja presion en cota alta de Pampa Inalambrica durante el pico.
    # ------------------------------------------------------------------
    day = random_day()
    start_hour, duration = random_hours(17, 19, 2, 4)
    mask = _event_mask(
        df, "SEC-01", day, start_hour, duration, only_active=True
    )
    low_pressure = float(rng.uniform(6.2, 9.4))
    _set_event(
        df,
        mask,
        EVENT_LOW_PRESSURE,
        presion_mca=low_pressure,
    )

    # ------------------------------------------------------------------
    # Cloro residual bajo en la cola de red de Pacocha / Ciudad Nueva.
    # ------------------------------------------------------------------
    day = random_day()
    start_hour, duration = random_hours(14, 17, 3, 5)
    mask = _event_mask(
        df, "SEC-03", day, start_hour, duration, only_active=True
    )
    low_chlorine = float(rng.uniform(0.18, 0.42))
    _set_event(
        df,
        mask,
        EVENT_LOW_CHLORINE,
        cloro_mg_l=low_chlorine,
    )

    # ------------------------------------------------------------------
    # Turbiedad alta por evento estacional en la conduccion Pasto Grande.
    # ------------------------------------------------------------------
    day = random_day()
    start_hour, duration = random_hours(7, 11, 5, 8)
    mask = _event_mask(
        df, "SEC-01", day, start_hour, duration, only_active=True
    )
    high_turbidity = float(rng.uniform(5.6, 9.2))
    _set_event(
        df,
        mask,
        EVENT_HIGH_TURBIDITY,
        turbiedad_ntu=high_turbidity,
    )


def _calculate_volumes(df: pd.DataFrame) -> None:
    """Calcula volumenes y ANF a partir del caudal y el porcentaje de perdida."""
    # 1 l/s durante 1 hora equivale a 3.6 m3.
    df["caudal_lps"] = df["caudal_lps"].round(2)
    df["anf_pct"] = df["anf_pct"].round(2)
    df["volumen_producido_m3"] = (df["caudal_lps"] * 3.6).round(3)
    df["anf_m3"] = (
        df["volumen_producido_m3"] * df["anf_pct"] / 100.0
    ).round(3)
    df["volumen_facturado_m3"] = (
        df["volumen_producido_m3"] - df["anf_m3"]
    ).clip(lower=0.0).round(3)


def generate_telemetry_data(
    days: int = TELEMETRY_DEFAULT_DAYS,
    seed: int = TELEMETRY_DEFAULT_SEED,
    inject_anomalies: bool = True,
) -> pd.DataFrame:
    """Genera telemetria horaria de los sectores hidraulicos de Ilo.

    Parameters
    ----------
    days:
        Cantidad de dias completos a generar (por defecto 30).
    seed:
        Semilla del generador aleatorio para resultados reproducibles.
    inject_anomalies:
        Si es ``True``, incorpora eventos operativos simulados (fugas,
        fraude comercial, baja presion, cloro bajo y turbiedad alta).

    Returns
    -------
    pandas.DataFrame
        DataFrame con las 14 columnas del contrato de datos, ordenado por
        ``timestamp`` y ``sector_id``.
    """
    days, seed = _validate_parameters(days, seed)
    rng = np.random.default_rng(seed)

    # Periodo de dias completos que termina ayer.
    last_day = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
    first_day = last_day - pd.Timedelta(days=days - 1)
    dates = [first_day + pd.Timedelta(days=i) for i in range(days)]

    sector_frames = [
        _build_sector_frame(sector_id, sector, dates, rng)
        for sector_id, sector in SECTORS.items()
    ]
    df = pd.concat(sector_frames, ignore_index=True)

    if inject_anomalies:
        _inject_events(df, dates, rng)

    _calculate_volumes(df)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["continuidad_horas"] = df["continuidad_horas"].astype(int)
    df["injected_event"] = df["injected_event"].astype(object)

    df = (
        df.sort_values(["timestamp", "sector_id"], kind="stable")
        .reset_index(drop=True)
        .loc[:, TELEMETRY_COLUMNS]
    )

    return df
