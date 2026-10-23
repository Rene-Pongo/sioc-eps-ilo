"""Dashboard ejecutivo Streamlit del SIOC de EPS Ilo S.A.

Integra la telemetria hidraulica, el motor de deteccion de anomalias, la
valorizacion economica SUNASS y el simulador de inversion en una interfaz
"Luminance-Safe Glassmorphism" de tres capas, con cambio aleatorio de fondo
al recargar la pagina y un boton interactivo en la barra lateral.

Ejecucion local::

    streamlit run app/dashboard.py
"""

from __future__ import annotations

import html as html_lib
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Permitir "streamlit run app/dashboard.py" desde la raiz del monorepo.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.anomaly_detector import detect_anomalies, summarize_anomalies_by_sector
from src.config import (
    CITY,
    NORMATIVE_LIMITS,
    PTAPS,
    SECTORS,
    SOURCES,
    TARIFF_STRUCTURE,
)
from src.economic_evaluator import (
    evaluate_economic_impact,
    simulate_anf_reduction_roi,
)
from src.report_generator import generate_executive_docx_report
from src.telemetry_generator import generate_telemetry_data
from src.ui_glassmorphism import (
    ACCENT_AMBER,
    ACCENT_CORAL,
    ACCENT_CORAL_TEXT,
    ACCENT_CYAN,
    ACCENT_EMERALD,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    apply_transparent_plotly_theme,
    get_background_index,
    get_random_background,
    inject_glassmorphism_css,
    render_glass_footer,
    render_glass_hero,
    render_glass_kpi_card,
    render_glass_note,
    render_glass_section_title,
)

# ---------------------------------------------------------------------------
# Configuracion general
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SIOC EPS Ilo | Control de ANF",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

SECTOR_COLORS = {
    "SEC-01": ACCENT_CYAN,
    "SEC-02": ACCENT_EMERALD,
    "SEC-03": ACCENT_AMBER,
}
NAME_COLOR_MAP = {
    SECTORS[sid]["name"]: color for sid, color in SECTOR_COLORS.items()
}
SEMAFORO_STATUS = {"VERDE": "ok", "AMARILLO": "warn", "ROJO": "critical"}
SEMAFORO_LABEL = {
    "VERDE": "Dentro de la meta SUNASS",
    "AMARILLO": "Sobre la meta de 28%",
    "ROJO": "Sobre el umbral crítico de 35%",
}
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------
def _fmt_int(value: float | int) -> str:
    """Formatea un numero entero con separador de miles."""
    return f"{int(round(float(value))):,}".replace(",", " ")


def _fmt_money(value: float | int) -> str:
    """Formatea un monto en soles."""
    return f"S/ {float(value):,.0f}".replace(",", " ")


def _fmt_pct(value: float | int, decimals: int = 1) -> str:
    """Formatea un porcentaje."""
    return f"{float(value):.{decimals}f}%"



# ---------------------------------------------------------------------------
# Estado de sesion y fondo aleatorio
# ---------------------------------------------------------------------------
def _init_session() -> None:
    """Inicializa el fondo aleatorio una vez por sesion de navegador."""
    if "sioc_bg_url" not in st.session_state:
        st.session_state["sioc_bg_url"] = get_random_background()


def _rotate_background() -> None:
    """Selecciona una imagen distinta de las ocho disponibles."""
    current = st.session_state.get("sioc_bg_url")
    st.session_state["sioc_bg_url"] = get_random_background(exclude=current)


# ---------------------------------------------------------------------------
# Pipeline de datos (cacheado)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=900)
def _load_pipeline(days: int, seed: int, contamination: float):
    """Ejecuta telemetria, deteccion de anomalias y valorizacion economica."""
    telemetry = generate_telemetry_data(
        days=int(days), seed=int(seed), inject_anomalies=True
    )
    flagged = detect_anomalies(telemetry, contamination=float(contamination))
    anomalies_summary = summarize_anomalies_by_sector(flagged)
    economic_summary = evaluate_economic_impact(flagged)
    return flagged, anomalies_summary, economic_summary


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
def _render_sidebar_header() -> None:
    """Marca institucional y boton de cambio de ambiente visual."""
    with st.sidebar:
        st.markdown(
            """
<div class="sioc-sidebar-brand">
    <div class="sioc-brand-title">💧 SIOC · EPS Ilo S.A.</div>
    <div class="sioc-brand-sub">
        Control de Agua No Facturada<br>
        Ilo · Moquegua · Perú
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        if st.button(
            "🎨 Cambiar Ambiente Visual",
            use_container_width=True,
            help="Selecciona otra de las 8 fotografías HD del pool curado.",
        ):
            _rotate_background()
            st.rerun()

        index = get_background_index(st.session_state.get("sioc_bg_url", ""))
        if index is not None:
            st.caption(f"Ambiente visual {index}/8 · selección aleatoria")
        else:
            st.caption("Ambiente visual: gradiente de respaldo (sin conexión)")


def _render_sidebar_controls() -> tuple[int, int, float, float, float]:
    """Dibuja los controles y retorna sus valores."""
    with st.sidebar:
        st.markdown("### ⚙️ Parámetros de simulación")
        days = st.slider(
            "Ventana de análisis (días)",
            min_value=7,
            max_value=90,
            value=30,
            step=1,
            help="Periodo de telemetría horaria a analizar.",
        )
        seed = st.number_input(
            "Semilla de telemetría",
            min_value=1,
            max_value=9999,
            value=42,
            step=1,
            help="Cambia la semilla para explorar escenarios reproducibles.",
        )
        contamination = st.slider(
            "Sensibilidad IA (contaminación)",
            min_value=0.01,
            max_value=0.15,
            value=0.05,
            step=0.01,
            format="%.2f",
            help="Proporción esperada de outliers del modelo Isolation Forest.",
        )

        st.markdown("### 💰 Simulador de inversión")
        reduction = st.slider(
            "Reducción objetivo de ANF (%)",
            min_value=5,
            max_value=80,
            value=30,
            step=5,
            help="Porcentaje del ANF actual que se busca recuperar.",
        )
        investment = st.number_input(
            "Inversión del plan (S/)",
            min_value=5_000,
            max_value=500_000,
            value=45_000,
            step=5_000,
            help="Inversión inicial en sectorización, medidores y fugas.",
        )

        with st.expander("ℹ️ Metodología"):
            st.markdown(
                f"""
- **Telemetría:** {len(SECTORS)} sectores con perfil horario real de Ilo.
- **Detección:** reglas SUNASS/DIGESA + `IsolationForest`.
- **Valorización:** tarifa media S/ {TARIFF_STRUCTURE['tarifa_media_ponderada']:.2f}/m³.
- **Calidad:** cloro ≥ {NORMATIVE_LIMITS['cloro_min_mg_l']:.1f} mg/L y turbiedad ≤ {NORMATIVE_LIMITS['turbiedad_max_ntu']:.1f} NTU.
- **Fondo:** 8 imágenes HD aleatorias al recargar.
"""
            )
    return int(days), int(seed), float(contamination), float(reduction), float(investment)


# ---------------------------------------------------------------------------
# Preparacion de graficos
# ---------------------------------------------------------------------------
def _daily_frame(flagged: pd.DataFrame) -> pd.DataFrame:
    """Agrega la telemetria a nivel diario y sector."""
    daily = (
        flagged.assign(fecha=flagged["timestamp"].dt.date)
        .groupby(
            ["fecha", "sector_id", "sector_name"], as_index=False, sort=True
        )
        .agg(
            anf_pct=("anf_pct", "mean"),
            presion_mca=("presion_mca", "mean"),
            cloro_mg_l=("cloro_mg_l", "mean"),
        )
    )
    return daily


def _sector_stats(flagged: pd.DataFrame) -> pd.DataFrame:
    """Calcula estadisticas operativas por sector en horas de servicio."""
    active = flagged[flagged["caudal_lps"] > 0]
    rows = []
    for sector_id, meta in SECTORS.items():
        group = active[active["sector_id"] == sector_id]
        all_group = flagged[flagged["sector_id"] == sector_id]
        rows.append(
            {
                "sector_id": sector_id,
                "sector_name": meta["name"],
                "lat": meta["lat"],
                "lon": meta["lon"],
                "anf_pct": float(group["anf_pct"].mean()) if not group.empty else 0.0,
                "presion_mca": (
                    float(group["presion_mca"].mean()) if not group.empty else 0.0
                ),
                "cloro_mg_l": (
                    float(group["cloro_mg_l"].mean()) if not group.empty else 0.0
                ),
                "turbiedad_ntu": (
                    float(group["turbiedad_ntu"].mean()) if not group.empty else 0.0
                ),
                "alertas": int((all_group["anomaly_type"] != "normal").sum()),
                "continuidad": (
                    float(group["continuidad_horas"].mean()) if not group.empty else 0.0
                ),
            }
        )
    return pd.DataFrame(rows)


def _build_anf_figure(daily: pd.DataFrame) -> go.Figure:
    """Curva diaria de ANF con umbrales SUNASS."""
    fig = px.line(
        daily,
        x="fecha",
        y="anf_pct",
        color="sector_name",
        markers=True,
        color_discrete_map=NAME_COLOR_MAP,
        labels={
            "fecha": "Fecha",
            "anf_pct": "ANF (%)",
            "sector_name": "Sector",
        },
        title="Evolución diaria del ANF por sector",
    )
    fig.update_traces(line={"width": 2.6}, marker={"size": 5})
    fig.add_hline(
        y=float(NORMATIVE_LIMITS["anf_alerta_amarilla_pct"]),
        line_dash="dot",
        line_color=ACCENT_AMBER,
        annotation_text="Alerta 28%",
        annotation_font_color=ACCENT_AMBER,
        annotation_position="top left",
    )
    fig.add_hline(
        y=float(NORMATIVE_LIMITS["anf_alerta_critica_pct"]),
        line_dash="dot",
        line_color=ACCENT_CORAL,
        annotation_text="Crítico 35%",
        annotation_font_color=ACCENT_CORAL_TEXT,
        annotation_position="bottom left",
    )
    fig.update_layout(hovermode="x unified", legend_title_text="Sector")
    return apply_transparent_plotly_theme(fig)


def _build_volume_figure(sector_breakdown: pd.DataFrame) -> go.Figure:
    """Barras agrupadas de volumen producido versus facturado."""
    long_frame = sector_breakdown.melt(
        id_vars=["sector_name"],
        value_vars=["volumen_producido_m3", "volumen_facturado_m3"],
        var_name="Serie",
        value_name="m3",
    )
    long_frame["Serie"] = long_frame["Serie"].map(
        {
            "volumen_producido_m3": "Producido",
            "volumen_facturado_m3": "Facturado",
        }
    )
    fig = px.bar(
        long_frame,
        x="sector_name",
        y="m3",
        color="Serie",
        barmode="group",
        color_discrete_map={
            "Producido": ACCENT_CYAN,
            "Facturado": ACCENT_EMERALD,
        },
        labels={"sector_name": "", "m3": "Volumen (m³)", "Serie": "Serie"},
        title="Balance hídrico por sector",
    )
    fig.update_traces(marker_line_width=0, opacity=0.92)
    fig.update_layout(legend_title_text="")
    return apply_transparent_plotly_theme(fig)


def _build_quality_figure(flagged: pd.DataFrame) -> go.Figure:
    """Cloro residual promedio por sector con umbral DIGESA."""
    active = flagged[flagged["caudal_lps"] > 0]
    quality = (
        active.groupby(["sector_id", "sector_name"], as_index=False)
        .agg(
            cloro_prom=("cloro_mg_l", "mean"),
            cloro_min=("cloro_mg_l", "min"),
            turbiedad_max=("turbiedad_ntu", "max"),
        )
        .sort_values("sector_name")
    )
    fig = px.bar(
        quality,
        x="sector_name",
        y="cloro_prom",
        color="sector_name",
        color_discrete_map=NAME_COLOR_MAP,
        text_auto=".2f",
        labels={"sector_name": "", "cloro_prom": "Cloro (mg/L)"},
        title="Cloro residual promedio por sector",
    )
    fig.update_traces(marker_line_width=0, textposition="outside")
    fig.add_hline(
        y=float(NORMATIVE_LIMITS["cloro_min_mg_l"]),
        line_dash="dash",
        line_color=ACCENT_CORAL,
        annotation_text="Mínimo DIGESA 0.5 mg/L",
        annotation_font_color=ACCENT_CORAL_TEXT,
        annotation_position="top left",
    )
    fig.update_layout(showlegend=False)
    return apply_transparent_plotly_theme(fig)


def _build_pressure_figure(flagged: pd.DataFrame) -> go.Figure:
    """Distribucion de presion de servicio con limites normativos."""
    active = flagged[flagged["caudal_lps"] > 0]
    fig = px.histogram(
        active,
        x="presion_mca",
        color="sector_name",
        color_discrete_map=NAME_COLOR_MAP,
        nbins=40,
        opacity=0.72,
        barmode="overlay",
        labels={"presion_mca": "Presión (m.c.a.)", "sector_name": "Sector"},
        title="Distribución de presión de servicio",
    )
    fig.update_traces(marker_line_width=0)
    fig.add_vline(
        x=float(NORMATIVE_LIMITS["presion_min_mca"]),
        line_dash="dash",
        line_color=ACCENT_AMBER,
        annotation_text="Mín. 10",
        annotation_font_color=ACCENT_AMBER,
    )
    fig.add_vline(
        x=float(NORMATIVE_LIMITS["presion_max_mca"]),
        line_dash="dash",
        line_color=ACCENT_CORAL,
        annotation_text="Máx. 50",
        annotation_font_color=ACCENT_CORAL_TEXT,
    )
    fig.update_layout(legend_title_text="Sector", bargap=0.04)
    return apply_transparent_plotly_theme(fig)


def _build_alerts_figure(anomalies_summary: pd.DataFrame) -> go.Figure:
    """Conteo apilado de alertas por tipo y sector."""
    columns = {
        "fugas_fisicas": "Fugas físicas",
        "fraudes_comerciales": "Fraude comercial",
        "alertas_cloro": "Cloro bajo",
        "alertas_turbiedad": "Turbiedad",
        "alertas_presion": "Presión",
        "alertas_estadisticas": "Patrón atípico",
    }
    present = {key: label for key, label in columns.items() if key in anomalies_summary}
    if not present or anomalies_summary.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Sin alertas para el periodo seleccionado",
            showarrow=False,
            font={"color": TEXT_SECONDARY, "size": 14},
        )
        return apply_transparent_plotly_theme(fig)

    long_frame = anomalies_summary.melt(
        id_vars=["sector_name"],
        value_vars=list(present),
        var_name="Tipo",
        value_name="Alertas",
    )
    long_frame["Tipo"] = long_frame["Tipo"].map(present)
    fig = px.bar(
        long_frame,
        x="Alertas",
        y="sector_name",
        color="Tipo",
        orientation="h",
        barmode="stack",
        color_discrete_sequence=[
            ACCENT_CORAL,
            ACCENT_AMBER,
            ACCENT_CYAN,
            "#A78BFA",
            ACCENT_EMERALD,
            "#22D3EE",
        ],
        labels={"sector_name": "", "Alertas": "N.º de alertas", "Tipo": "Tipo"},
        title="Alertas detectadas por tipo y sector",
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(legend_title_text="", yaxis={"categoryorder": "total ascending"})
    return apply_transparent_plotly_theme(fig)


def _build_roi_figure(roi: dict, investment: float) -> go.Figure:
    """Flujo de ahorro acumulado frente a la inversion inicial."""
    monthly_saving = float(roi.get("ahorro_mensual_soles", 0.0))
    months = list(range(0, 13))
    cumulative = [monthly_saving * month for month in months]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=cumulative,
            mode="lines+markers",
            name="Ahorro acumulado",
            line={"color": ACCENT_EMERALD, "width": 3},
            marker={"size": 7, "color": ACCENT_EMERALD},
            fill="tozeroy",
            fillcolor="rgba(52, 211, 153, 0.12)",
            hovertemplate="Mes %{x}: S/ %{y:,.0f}<extra></extra>",
        )
    )
    fig.add_hline(
        y=float(investment),
        line_dash="dash",
        line_color=ACCENT_CORAL,
        annotation_text=f"Inversión S/ {float(investment):,.0f}",
        annotation_font_color=ACCENT_CORAL_TEXT,
        annotation_position="top right",
    )
    fig.update_layout(
        title="Ahorro acumulado a 12 meses vs. inversión",
        xaxis_title="Meses",
        yaxis_title="Soles (S/)",
        showlegend=False,
    )
    return apply_transparent_plotly_theme(fig)


def _build_sector_map(stats: pd.DataFrame) -> go.Figure:
    """Mapa interactivo de Ilo con la intensidad de ANF por sector."""
    colorscale = [
        [0.0, ACCENT_EMERALD],
        [0.5, ACCENT_AMBER],
        [1.0, ACCENT_CORAL],
    ]
    marker = {
        "size": 30,
        "color": stats["anf_pct"].tolist(),
        "colorscale": colorscale,
        "cmin": max(15.0, float(stats["anf_pct"].min()) - 3.0),
        "cmax": min(60.0, float(stats["anf_pct"].max()) + 3.0),
        "showscale": True,
        "opacity": 0.94,
        "colorbar": {
            "title": {
                "text": "ANF %",
                "font": {"color": TEXT_SECONDARY, "size": 12},
            },
            "tickfont": {"color": TEXT_SECONDARY, "size": 11},
            "bgcolor": "rgba(15, 23, 42, 0.62)",
            "bordercolor": "rgba(255, 255, 255, 0.22)",
            "borderwidth": 1,
            "thickness": 14,
        },
    }
    hovertext = [
        (
            f"<b>{row.sector_name}</b><br>"
            f"ANF promedio: {row.anf_pct:.1f}%<br>"
            f"Presión media: {row.presion_mca:.1f} m.c.a.<br>"
            f"Cloro medio: {row.cloro_mg_l:.2f} mg/L<br>"
            f"Continuidad: {row.continuidad:.1f} h/día<br>"
            f"Alertas: {int(row.alertas)}"
        )
        for row in stats.itertuples()
    ]

    if hasattr(go, "Scattermap"):
        trace = go.Scattermap(
            lat=stats["lat"],
            lon=stats["lon"],
            mode="markers+text",
            marker=marker,
            text=stats["sector_name"],
            textposition="top center",
            textfont={"color": TEXT_PRIMARY, "size": 13},
            hovertext=hovertext,
            hoverinfo="text",
            name="Sectores",
        )
        fig = go.Figure(trace)
        fig.update_layout(
            map={
                "style": "open-street-map",
                "center": {"lat": CITY["lat"], "lon": CITY["lon"]},
                "zoom": 12.2,
            },
            height=520,
        )
    else:  # Compatibilidad con plotly < 5.24
        trace = go.Scattermapbox(
            lat=stats["lat"],
            lon=stats["lon"],
            mode="markers+text",
            marker=marker,
            text=stats["sector_name"],
            textposition="top center",
            textfont={"color": TEXT_PRIMARY, "size": 13},
            hovertext=hovertext,
            hoverinfo="text",
            name="Sectores",
        )
        fig = go.Figure(trace)
        fig.update_layout(
            mapbox={
                "style": "open-street-map",
                "center": {"lat": CITY["lat"], "lon": CITY["lon"]},
                "zoom": 12.2,
            },
            height=520,
        )

    fig.update_layout(title="Mapa operativo de sectores hidráulicos de Ilo")
    return apply_transparent_plotly_theme(fig)


# ---------------------------------------------------------------------------
# Tablas de presentacion
# ---------------------------------------------------------------------------
def _sector_table(sector_breakdown: pd.DataFrame) -> pd.DataFrame:
    """Prepara el desagregado sectorial para visualizacion."""
    rows = []
    for _, row in sector_breakdown.iterrows():
        rows.append(
            {
                "Sector": row.get("sector_name", "—"),
                "Producido (m³)": _fmt_int(row.get("volumen_producido_m3", 0)),
                "Facturado (m³)": _fmt_int(row.get("volumen_facturado_m3", 0)),
                "ANF (m³)": _fmt_int(row.get("anf_m3", 0)),
                "ANF %": _fmt_pct(row.get("anf_pct", 0)),
                "Pérdida física (m³)": _fmt_int(row.get("perdida_fisica_m3", 0)),
                "Pérdida comercial (m³)": _fmt_int(
                    row.get("perdida_comercial_m3", 0)
                ),
                "Pérdida económica": _fmt_money(
                    row.get("perdida_economica_soles", 0)
                ),
                "Semáforo": row.get("semaforo_sunass", "—"),
            }
        )
    return pd.DataFrame(rows)


def _alerts_table(anomalies_summary: pd.DataFrame) -> pd.DataFrame:
    """Prepara el resumen de alertas para visualizacion."""
    rows = []
    for _, row in anomalies_summary.iterrows():
        rows.append(
            {
                "Sector": row.get("sector_name", "—"),
                "Registros": _fmt_int(row.get("registros", 0)),
                "Alertas": _fmt_int(row.get("alertas_totales", 0)),
                "% Alertas": _fmt_pct(row.get("alertas_porcentaje", 0), 2),
                "Fugas": _fmt_int(row.get("fugas_fisicas", 0)),
                "Fraudes": _fmt_int(row.get("fraudes_comerciales", 0)),
                "Cloro": _fmt_int(row.get("alertas_cloro", 0)),
                "Presión": _fmt_int(row.get("alertas_presion", 0)),
                "ANF prom.": _fmt_pct(row.get("anf_promedio_pct", 0)),
                "Severidad": str(row.get("severidad_maxima", "—")).upper(),
            }
        )
    return pd.DataFrame(rows)


def _top_anomalies_table(flagged: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    """Selecciona las alertas de mayor score para revision operativa."""
    columns = [
        "timestamp",
        "sector_name",
        "anomaly_type",
        "severity",
        "anomaly_score",
        "caudal_lps",
        "presion_mca",
        "cloro_mg_l",
        "anf_pct",
    ]
    available = [column for column in columns if column in flagged.columns]
    top = (
        flagged[flagged["anomaly_type"] != "normal"]
        .sort_values(["anomaly_score", "timestamp"], ascending=[False, False])
        .head(limit)
        .loc[:, available]
        .copy()
    )
    if top.empty:
        return top
    top["timestamp"] = pd.to_datetime(top["timestamp"]).dt.strftime(
        "%d/%m/%Y %H:%M"
    )
    top = top.rename(
        columns={
            "timestamp": "Fecha/hora",
            "sector_name": "Sector",
            "anomaly_type": "Tipo de anomalía",
            "severity": "Severidad",
            "anomaly_score": "Score IA",
            "caudal_lps": "Caudal (L/s)",
            "presion_mca": "Presión (m.c.a.)",
            "cloro_mg_l": "Cloro (mg/L)",
            "anf_pct": "ANF %",
        }
    )
    if "Score IA" in top.columns:
        top["Score IA"] = top["Score IA"].map(lambda value: f"{float(value):.3f}")
    for column in ("Caudal (L/s)", "Presión (m.c.a.)", "Cloro (mg/L)", "ANF %"):
        if column in top.columns:
            top[column] = top[column].map(
                lambda value: f"{float(value):,.2f}".replace(",", " ")
            )
    return top


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------
def _render_kpis(economic_summary: dict, flagged: pd.DataFrame) -> None:
    """Fila de tarjetas KPI de cristal."""
    semaforo = str(economic_summary["semaforo_sunass"])
    status = SEMAFORO_STATUS.get(semaforo, "info")
    critical_alerts = int((flagged["severity"] == "critica").sum())
    high_alerts = int((flagged["severity"] == "alta").sum())
    total_alerts = int((flagged["anomaly_type"] != "normal").sum())

    columns = st.columns(4, gap="medium")
    with columns[0]:
        render_glass_kpi_card(
            "ANF del periodo",
            _fmt_pct(economic_summary["anf_porcentaje"]),
            f"{_fmt_int(economic_summary['anf_total_m3'])} m³ no facturados",
            status,
        )
    with columns[1]:
        render_glass_kpi_card(
            "Pérdida económica",
            _fmt_money(economic_summary["perdida_economica_soles"]),
            (
                f"Costo energía/químicos: "
                f"{_fmt_money(economic_summary['costo_energia_quimicos_perdido_soles'])}"
            ),
            status,
        )
    with columns[2]:
        render_glass_kpi_card(
            "Volumen facturado",
            f"{_fmt_int(economic_summary['volumen_facturado_total_m3'])} m³",
            f"Producido: {_fmt_int(economic_summary['volumen_producido_total_m3'])} m³",
            "info",
        )
    with columns[3]:
        render_glass_kpi_card(
            "Alertas detectadas",
            _fmt_int(total_alerts),
            f"Críticas: {_fmt_int(critical_alerts)} · Altas: {_fmt_int(high_alerts)}",
            "critical" if critical_alerts else ("warn" if total_alerts else "ok"),
        )


def _render_operations_tab(
    flagged: pd.DataFrame,
    daily: pd.DataFrame,
    economic_summary: dict,
) -> None:
    """Pestana de operacion hidraulica y calidad del agua."""
    render_glass_note(
        "<strong>Lectura del panel:</strong> las curvas diarias de ANF se "
        "comparan contra las metas SUNASS de "
        f"<span class='sioc-note-accent'>28% (alerta)</span> y "
        f"<span class='sioc-note-accent'>35% (crítico)</span>. Los volúmenes y "
        "la calidad se calculan solo sobre horas con servicio activo."
    )

    st.plotly_chart(
        _build_anf_figure(daily),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

    left, right = st.columns(2, gap="medium")
    with left:
        st.plotly_chart(
            _build_volume_figure(economic_summary["sector_breakdown"]),
            use_container_width=True,
            config=PLOTLY_CONFIG,
        )
    with right:
        st.plotly_chart(
            _build_quality_figure(flagged),
            use_container_width=True,
            config=PLOTLY_CONFIG,
        )

    st.plotly_chart(
        _build_pressure_figure(flagged),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

    render_glass_section_title("Balance y valorización por sector")
    st.dataframe(
        _sector_table(economic_summary["sector_breakdown"]),
        use_container_width=True,
        hide_index=True,
    )


def _render_alerts_tab(
    flagged: pd.DataFrame,
    anomalies_summary: pd.DataFrame,
) -> None:
    """Pestana del motor IA de anomalias."""
    render_glass_note(
        "<strong>Motor IA:</strong> las reglas normativas SUNASS/DIGESA se "
        "combinan con <em>Isolation Forest</em> para priorizar fugas "
        "nocturnas, fraude comercial, incumplimientos de cloro, turbiedad y "
        "presión. El score IA va de 0 a 1 y la severidad resume el riesgo "
        "operativo."
    )

    st.plotly_chart(
        _build_alerts_figure(anomalies_summary),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

    render_glass_section_title("Resumen de alertas por sector")
    if anomalies_summary.empty:
        st.info("No se registraron alertas en el periodo seleccionado.")
    else:
        st.dataframe(
            _alerts_table(anomalies_summary),
            use_container_width=True,
            hide_index=True,
        )

    render_glass_section_title("Alertas priorizadas por score IA")
    top = _top_anomalies_table(flagged)
    if top.empty:
        st.success("No se detectaron eventos anómalos con los parámetros actuales.")
    else:
        st.dataframe(top, use_container_width=True, hide_index=True)


def _render_map_tab(stats: pd.DataFrame) -> None:
    """Pestana del mapa interactivo y contexto de los sectores."""
    render_glass_note(
        f"<strong>Ilo, {CITY['region']}:</strong> los tres sectores hidráulicos "
        "monitoreados se ubican sobre la costa de la provincia de Ilo. El color "
        "del marcador representa el ANF promedio y el tamaño es fijo para "
        "mantener la legibilidad. El mapa usa OpenStreetMap y requiere conexión "
        "a internet; si no está disponible, las tablas siguientes conservan la "
        "información operativa."
    )
    st.plotly_chart(
        _build_sector_map(stats),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

    render_glass_section_title("Contexto operativo por sector")
    columns = st.columns(3, gap="medium")
    for column, row in zip(columns, stats.itertuples(), strict=False):
        sector = SECTORS[row.sector_id]
        source_name = SOURCES[sector["source_id"]]["name"]
        ptap_name = PTAPS[sector["ptap_id"]]["name"]
        with column:
            render_glass_note(
                f"<strong>{sector['name']}</strong><br>"
                f"<span class='sioc-note-accent'>{sector['zone']}</span><br><br>"
                f"ANF promedio: <strong>{row.anf_pct:.1f}%</strong><br>"
                f"Presión media: <strong>{row.presion_mca:.1f} m.c.a.</strong><br>"
                f"Cloro medio: <strong>{row.cloro_mg_l:.2f} mg/L</strong><br>"
                f"Continuidad: <strong>{row.continuidad:.1f} h/día</strong><br>"
                f"Alertas: <strong>{int(row.alertas)}</strong><br><br>"
                f"Fuente: {html_lib.escape(source_name)}<br>"
                f"PTAP: {html_lib.escape(ptap_name)}<br><br>"
                f"<em>{html_lib.escape(sector['description'])}</em>"
            )


def _render_roi_tab(
    economic_summary: dict,
    roi: dict,
    investment: float,
    reduction: float,
    days: int,
) -> None:
    """Pestana del simulador What-If y retorno de inversion."""
    monthly_anf = float(economic_summary["anf_total_m3"]) * 30.0 / max(days, 1)
    render_glass_note(
        "<strong>Simulador What-If:</strong> el ANF mensual equivalente se "
        f"estima en <strong>{_fmt_int(monthly_anf)} m³</strong> a partir de la "
        f"ventana de {days} días. Con una reducción objetivo de "
        f"<strong>{reduction:.0f}%</strong> y una inversión de "
        f"<strong>{_fmt_money(investment)}</strong>, el modelo calcula el "
        "ahorro valorizado a la tarifa media SUNASS y el VAN descontado a una "
        "tasa anual referencial del 12%."
    )

    columns = st.columns(4, gap="medium")
    with columns[0]:
        render_glass_kpi_card(
            "Volumen recuperado",
            f"{_fmt_int(roi['m3_recuperados_mes'])} m³",
            "por mes",
            "ok",
        )
    with columns[1]:
        render_glass_kpi_card(
            "Ahorro mensual",
            _fmt_money(roi["ahorro_mensual_soles"]),
            f"Anual: {_fmt_money(roi['ahorro_anual_soles'])}",
            "ok",
        )
    with columns[2]:
        payback = float(roi["payback_meses"])
        render_glass_kpi_card(
            "Payback",
            (
                f"{payback:.1f} meses"
                if payback != float("inf")
                else "No recuperable"
            ),
            "Periodo de recuperación",
            "ok" if payback <= 18 else "warn",
        )
    with columns[3]:
        render_glass_kpi_card(
            "VAN 12 meses",
            _fmt_money(roi["van_12_meses_soles"]),
            f"ROI: {_fmt_pct(roi['roi_porcentaje'])}",
            "ok" if float(roi["van_12_meses_soles"]) > 0 else "critical",
        )

    st.plotly_chart(
        _build_roi_figure(roi, investment),
        use_container_width=True,
        config=PLOTLY_CONFIG,
    )

    verdict = (
        "El plan es económicamente viable: el VAN a 12 meses es positivo y el "
        "ahorro anual supera la inversión inicial."
        if float(roi["van_12_meses_soles"]) > 0
        else (
            "Con los parámetros actuales el plan no recupera la inversión en "
            "12 meses. Amplía el objetivo de reducción o reduce el costo de "
            "intervención."
        )
    )
    render_glass_note(
        f"<strong>Veredicto:</strong> {html_lib.escape(verdict)}"
    )


def _render_report_tab(
    economic_summary: dict,
    anomalies_summary: pd.DataFrame,
    roi: dict,
    report_bytes: bytes | None,
    report_error: str | None,
) -> None:
    """Pestana de descarga del Reporte Ejecutivo Word."""
    render_glass_note(
        "<strong>Reporte Ejecutivo Word:</strong> el documento consolida el "
        "resumen ejecutivo, el semáforo SUNASS, el balance hídrico por sector, "
        "las alertas del motor IA y la simulación de inversión. Se genera en "
        "memoria, con el autor y la fecha de emisión, listo para descargar."
    )

    if report_error:
        st.error(f"No fue posible generar el reporte: {report_error}")
    elif report_bytes is not None:
        file_name = f"Reporte_Ejecutivo_ANF_EPS_Ilo_{datetime.now():%Y%m%d}.docx"
        st.download_button(
            label="⬇️ Descargar Reporte Ejecutivo (.docx)",
            data=report_bytes,
            file_name=file_name,
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            use_container_width=True,
        )
        st.caption(
            f"Archivo: {file_name} · {len(report_bytes) / 1024:.1f} KB · "
            "Formato Word editable"
        )

    render_glass_section_title("Contenido del informe")
    render_glass_note(
        "<strong>1.</strong> Resumen ejecutivo y KPIs del ANF.<br>"
        "<strong>2.</strong> Semáforo normativo SUNASS con lectura operativa.<br>"
        "<strong>3.</strong> Balance hídrico y valorización por sector.<br>"
        "<strong>4.</strong> Alertas operativas y comerciales del motor IA.<br>"
        "<strong>5.</strong> Simulación de inversión, payback, VAN y ROI.<br>"
        "<strong>6.</strong> Conclusiones y recomendaciones priorizadas."
    )

    render_glass_section_title("Cifras clave del reporte")
    preview = pd.DataFrame(
        [
            {
                "Indicador": "Volumen producido",
                "Valor": f"{_fmt_int(economic_summary['volumen_producido_total_m3'])} m³",
            },
            {
                "Indicador": "Volumen facturado",
                "Valor": f"{_fmt_int(economic_summary['volumen_facturado_total_m3'])} m³",
            },
            {
                "Indicador": "ANF total",
                "Valor": f"{_fmt_int(economic_summary['anf_total_m3'])} m³",
            },
            {
                "Indicador": "ANF porcentual",
                "Valor": _fmt_pct(economic_summary["anf_porcentaje"]),
            },
            {
                "Indicador": "Pérdida económica",
                "Valor": _fmt_money(economic_summary["perdida_economica_soles"]),
            },
            {
                "Indicador": "Semáforo SUNASS",
                "Valor": str(economic_summary["semaforo_sunass"]),
            },
            {
                "Indicador": "Alertas detectadas",
                "Valor": _fmt_int(
                    anomalies_summary["alertas_totales"].sum()
                    if "alertas_totales" in anomalies_summary
                    else 0
                ),
            },
            {
                "Indicador": "ROI del plan",
                "Valor": _fmt_pct(roi["roi_porcentaje"]),
            },
        ]
    )
    st.dataframe(preview, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Aplicacion principal
# ---------------------------------------------------------------------------
def main() -> None:
    """Punto de entrada del dashboard."""
    _init_session()
    inject_glassmorphism_css(st.session_state["sioc_bg_url"])

    _render_sidebar_header()
    days, seed, contamination, reduction, investment = _render_sidebar_controls()

    with st.spinner("Generando telemetría y ejecutando el motor de análisis..."):
        try:
            flagged, anomalies_summary, economic_summary = _load_pipeline(
                days, seed, contamination
            )
        except Exception as exc:  # pragma: no cover - proteccion de UI
            st.error(f"No fue posible generar la telemetría: {exc}")
            st.stop()

    monthly_anf = float(economic_summary["anf_total_m3"]) * 30.0 / max(days, 1)
    roi = simulate_anf_reduction_roi(
        current_anf_m3=monthly_anf,
        reduction_target_pct=reduction,
        investment_soles=investment,
    )

    report_bytes: bytes | None = None
    report_error: str | None = None
    try:
        report_bytes = generate_executive_docx_report(
            economic_summary, anomalies_summary, roi
        )
    except Exception as exc:  # pragma: no cover - proteccion de UI
        report_error = str(exc)

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📄 Reporte ejecutivo")
        if report_bytes is not None:
            st.download_button(
                label="⬇️ Descargar Reporte (.docx)",
                data=report_bytes,
                file_name=(
                    f"Reporte_Ejecutivo_ANF_EPS_Ilo_{datetime.now():%Y%m%d}.docx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
                use_container_width=True,
            )
        else:
            st.caption("Reporte no disponible.")
        st.caption(
            "Datos simulados con fines de planificación · "
            "SIOC EPS Ilo S.A."
        )

    period = (
        f"{flagged['timestamp'].min():%d/%m/%Y} — "
        f"{flagged['timestamp'].max():%d/%m/%Y}"
    )
    semaforo = str(economic_summary["semaforo_sunass"])

    render_glass_hero(
        eyebrow=f"{CITY['eps']} · {CITY['region']} · Perú",
        title="Centro de Control de Agua No Facturada",
        subtitle=(
            "Telemetría hidráulica, detección de fugas y fraude con IA, "
            "valorización económica SUNASS y simulación de inversiones para "
            "Pampa Inalámbrica, Cercado de Ilo y Pacocha / Ciudad Nueva."
        ),
        chips=[
            f"📅 {period}",
            f"🧪 {_fmt_int(len(flagged))} registros horarios",
            "🏘️ 3 sectores hidráulicos",
            f"🚱 ANF {_fmt_pct(economic_summary['anf_porcentaje'])}",
            f"⚖️ SUNASS {semaforo}",
        ],
    )

    _render_kpis(economic_summary, flagged)
    st.markdown("")

    daily = _daily_frame(flagged)
    stats = _sector_stats(flagged)

    tabs = st.tabs(
        [
            "📊 Operación",
            "🚨 Alertas IA",
            "🗺️ Mapa de Ilo",
            "💰 Simulador ROI",
            "📄 Reporte",
        ]
    )
    with tabs[0]:
        _render_operations_tab(flagged, daily, economic_summary)
    with tabs[1]:
        _render_alerts_tab(flagged, anomalies_summary)
    with tabs[2]:
        _render_map_tab(stats)
    with tabs[3]:
        _render_roi_tab(
            economic_summary, roi, investment, reduction, days
        )
    with tabs[4]:
        _render_report_tab(
            economic_summary,
            anomalies_summary,
            roi,
            report_bytes,
            report_error,
        )

    render_glass_footer(
        "<strong>SIOC · EPS Ilo S.A.</strong> · Sistema Integrado de "
        "Operaciones, Control de ANF e Inteligencia Comercial<br>"
        "Motor visual Luminance-Safe Glassmorphism de 3 capas · "
        "contraste WCAG AAA sobre fondos claros y oscuros · "
        f"actualizado {datetime.now():%d/%m/%Y %H:%M}"
    )


if __name__ == "__main__":
    main()
