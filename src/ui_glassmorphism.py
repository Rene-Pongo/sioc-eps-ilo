"""Motor visual "Luminance-Safe Glassmorphism" para el dashboard de EPS Ilo.

Implementa la arquitectura optica de tres capas descrita en
``PLAN_ARQUITECTURA.md``:

1. **Fondo dinamico**: una de las ocho fotografias HD del pool curado,
   seleccionada al azar en cada recarga de pagina (o con el boton
   "Cambiar Ambiente Visual"). Si no hay conexion se usa un gradiente CSS
   con color base ``#071120``.
2. **Velo atmosferico normalizador**: ``linear-gradient`` oscuro con
   ``backdrop-filter: blur(4px)`` que atenua las zonas claras de cualquier
   fotografia sin ocultar su estetica.
3. **Ventanas Smart Frosted Glass**: tarjetas, KPIs, tablas, controles y
   graficos sobre ``rgba(15, 23, 42, 0.70)`` con
   ``backdrop-filter: blur(22px) saturate(180%)``, borde especular y sombra
   profunda.

Legibilidad WCAG AAA (contraste > 10:1)
---------------------------------------
La peor condicion optica es una fotografia completamente blanca detras de
una tarjeta. La composicion del scrim (alpha 0.58 en su extremo claro) y del
tinte obsidiana (alpha 0.70) entrega un fondo efectivo cercano a ``#2C3242``
(luminancia relativa ~0.032). El texto principal ``#F8FAFC`` tiene
luminancia ~0.954, por lo que el contraste resulta:

    (0.954 + 0.05) / (0.032 + 0.05) ~= 12.2:1

y el texto secundario ``#E2E8F0`` ~= 10.3:1. Ambos superan el umbral AAA de
7:1 (y la meta interna de 10:1) incluso sobre fotografias claras. Sobre
fotografias oscuras el contraste aumenta porque el fondo compuesto se
aproxima al negro obsidiana.

Los acentos cian, esmeralda y ambar se reservan para bordes, indicadores y
valores de gran tamano; para texto pequeno sensible se usa la variante clara
``#FECACA`` del coral.
"""

from __future__ import annotations

import html
import secrets
from collections.abc import Sequence

import streamlit as st

from .config import BACKGROUND_IMAGES

# ---------------------------------------------------------------------------
# Paleta y constantes del sistema optico
# ---------------------------------------------------------------------------
TEXT_PRIMARY = "#F8FAFC"        # Blanco nieve puro
TEXT_SECONDARY = "#E2E8F0"      # Plata azulado luminoso
ACCENT_CYAN = "#38BDF8"         # Cian hidrico
ACCENT_EMERALD = "#34D399"      # Esmeralda
ACCENT_AMBER = "#FBBF24"        # Ambar
ACCENT_CORAL = "#F87171"        # Coral alerta
ACCENT_CYAN_TEXT = "#7DD3FC"    # Variante AAA para texto pequeno
ACCENT_CORAL_TEXT = "#FECACA"   # Variante AAA para texto pequeno

FALLBACK_GRADIENT = (
    "linear-gradient(135deg, #071120 0%, #0A192F 45%, #10263F 100%)"
)

ACCENT_COLORWAY = [
    ACCENT_CYAN,
    ACCENT_EMERALD,
    ACCENT_AMBER,
    ACCENT_CORAL,
    "#A78BFA",
    "#22D3EE",
]

_STATUS_ALIASES = {
    "ok": "ok",
    "optimo": "ok",
    "óptimo": "ok",
    "verde": "ok",
    "exito": "ok",
    "éxito": "ok",
    "success": "ok",
    "warn": "warn",
    "warning": "warn",
    "alerta": "warn",
    "amarillo": "warn",
    "critical": "critical",
    "critico": "critical",
    "crítico": "critical",
    "rojo": "critical",
    "danger": "critical",
    "error": "critical",
    "info": "info",
    "neutral": "info",
}

_STATUS_LABELS = {
    "ok": "ÓPTIMO",
    "warn": "ALERTA",
    "critical": "CRÍTICO",
    "info": "INFO",
}


# ---------------------------------------------------------------------------
# Fondo aleatorio y utilidades CSS
# ---------------------------------------------------------------------------
def get_random_background(exclude: str | None = None) -> str:
    """Selecciona al azar una de las ocho imagenes HD del pool curado.

    Parameters
    ----------
    exclude:
        URL que no debe repetirse (util para el boton de cambio de ambiente).

    Returns
    -------
    str
        URL de Unsplash de la imagen elegida o :data:`FALLBACK_GRADIENT` si el
        pool estuviera vacio.
    """
    pool = [url for url in BACKGROUND_IMAGES if url != exclude]
    if not pool:
        pool = list(BACKGROUND_IMAGES)
    if not pool:
        return FALLBACK_GRADIENT
    return secrets.choice(pool)


def get_background_index(bg_url: str) -> int | None:
    """Retorna la posicion 1-based de la imagen en el pool (o ``None``)."""
    try:
        return BACKGROUND_IMAGES.index(bg_url) + 1
    except ValueError:
        return None


def _sanitize_url(url: str) -> str:
    """Normaliza una URL para inyectarla con seguridad dentro de ``url()``."""
    cleaned = str(url or "").strip().replace('"', "%22").replace("'", "%27")
    cleaned = cleaned.replace("\n", "").replace("\r", "")
    cleaned = cleaned.replace("\\", "").replace(";", "")
    return cleaned


def _css_background(value: str) -> str:
    """Convierte una URL o gradiente en un valor CSS seguro para Layer 1."""
    value = (value or "").strip()
    if value.startswith(("http://", "https://")):
        return f'url("{_sanitize_url(value)}")'
    if value.startswith(("linear-gradient", "radial-gradient")):
        return value
    return FALLBACK_GRADIENT


def _normalize_status(status: str) -> str:
    """Mapea alias de estado a las cuatro variantes visuales soportadas."""
    return _STATUS_ALIASES.get(str(status or "").strip().lower(), "info")


_CSS_TEMPLATE = """
/* =====================================================================
   SIOC EPS Ilo - Luminance-Safe Glassmorphism (3 capas)
   Capa 1: fondo dinamico | Capa 2: scrim | Capa 3: ventanas de cristal
   ===================================================================== */

:root {
    --sioc-text: #F8FAFC;
    --sioc-muted: #E2E8F0;
    --sioc-cyan: #38BDF8;
    --sioc-cyan-text: #7DD3FC;
    --sioc-emerald: #34D399;
    --sioc-amber: #FBBF24;
    --sioc-coral: #F87171;
    --sioc-coral-text: #FECACA;
    --sioc-base: #071120;
    --sioc-glass: rgba(15, 23, 42, 0.70);
    --sioc-glass-blur: blur(22px) saturate(180%);
    --sioc-radius: 16px;
}

/* ----------------------------- Capa 1 ------------------------------- */
html, body, [data-testid="stApp"] {
    background-color: var(--sioc-base);
}

[data-testid="stAppViewContainer"] {
    background-color: var(--sioc-base);
    background-image: __BG_IMAGE__;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}

/* ----------------------------- Capa 2 ------------------------------- */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background: linear-gradient(
        135deg,
        rgba(6, 12, 26, 0.58) 0%,
        rgba(10, 25, 47, 0.72) 100%
    );
    -webkit-backdrop-filter: blur(4px);
    backdrop-filter: blur(4px);
}

[data-testid="stMain"],
[data-testid="stSidebar"] {
    position: relative;
    z-index: 1;
}

/* El header conserva su posicion nativa; solo se eleva sobre el scrim. */
[data-testid="stHeader"] {
    background: transparent;
    z-index: 3;
}

[data-testid="stAppViewBlockContainer"] {
    padding-top: 2.1rem;
    padding-bottom: 2.5rem;
    max-width: 1520px;
}

/* ----------------------------- Capa 3 ------------------------------- */
.sioc-glass-panel,
.sioc-glass-card,
.sioc-glass-note,
[data-testid="stMetric"],
[data-testid="stPlotlyChart"],
[data-testid="stDataFrame"],
[data-testid="stTable"],
[data-testid="stExpander"],
[data-testid="stForm"],
[data-testid="stAlert"] {
    background: var(--sioc-glass);
    -webkit-backdrop-filter: var(--sioc-glass-blur);
    backdrop-filter: var(--sioc-glass-blur);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-top: 1px solid rgba(255, 255, 255, 0.38);
    border-radius: var(--sioc-radius);
    box-shadow:
        0 12px 36px 0 rgba(0, 0, 0, 0.50),
        inset 0 1px 1px 0 rgba(255, 255, 255, 0.16);
}

[data-testid="stPlotlyChart"],
[data-testid="stDataFrame"],
[data-testid="stTable"],
[data-testid="stExpander"],
[data-testid="stForm"] {
    padding: 0.85rem;
    overflow: hidden;
}

[data-testid="stMetric"] {
    padding: 1.1rem 1.25rem;
}

/* --------------------------- Tipografia ----------------------------- */
[data-testid="stAppViewContainer"] h1,
[data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3,
[data-testid="stAppViewContainer"] h4,
[data-testid="stAppViewContainer"] h5,
[data-testid="stAppViewContainer"] h6 {
    color: var(--sioc-text);
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.75);
    letter-spacing: -0.01em;
}

.stMarkdown p,
.stMarkdown li,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stCaptionContainer"] p {
    color: var(--sioc-muted);
}

[data-testid="stMarkdownContainer"] strong {
    color: var(--sioc-text);
}

/* Los encabezados de seccion tambien viven en una ventana de cristal para
   que ninguna letra quede directamente sobre la fotografia. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > h2,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > h3,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] > h4 {
    background: var(--sioc-glass);
    -webkit-backdrop-filter: var(--sioc-glass-blur);
    backdrop-filter: var(--sioc-glass-blur);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-top: 1px solid rgba(255, 255, 255, 0.38);
    border-radius: 12px;
    box-shadow:
        0 10px 28px 0 rgba(0, 0, 0, 0.42),
        inset 0 1px 1px 0 rgba(255, 255, 255, 0.16);
    padding: 0.55rem 0.95rem;
    margin: 1.15rem 0 0.75rem 0;
}

/* Los caption del area principal se presentan como pildora de cristal. */
[data-testid="stMain"] [data-testid="stCaptionContainer"] {
    display: inline-block;
    padding: 0.38rem 0.68rem;
    border-radius: 10px;
    background: rgba(15, 23, 42, 0.74);
    -webkit-backdrop-filter: blur(22px) saturate(180%);
    backdrop-filter: blur(22px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.18);
}

a {
    color: var(--sioc-cyan-text) !important;
    text-decoration: underline;
}

/* ------------------------------- Hero ------------------------------- */
.sioc-hero {
    padding: 1.65rem 1.85rem;
    margin-bottom: 1.1rem;
    position: relative;
    overflow: hidden;
}

.sioc-hero::after {
    content: "";
    position: absolute;
    inset: -40% 45% 55% -10%;
    background: radial-gradient(
        circle at 30% 40%,
        rgba(56, 189, 248, 0.20),
        transparent 62%
    );
    pointer-events: none;
}

.sioc-eyebrow {
    display: inline-block;
    color: var(--sioc-cyan-text);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}

.sioc-hero h1 {
    margin: 0 0 0.45rem 0;
    font-size: clamp(1.65rem, 3vw, 2.35rem);
    font-weight: 800;
    line-height: 1.15;
    color: var(--sioc-text);
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.75);
}

.sioc-hero p {
    margin: 0;
    max-width: 96ch;
    color: var(--sioc-muted);
    font-size: 0.98rem;
    line-height: 1.55;
}

.sioc-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1.05rem;
}

.sioc-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.34rem 0.72rem;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.22);
    background: rgba(2, 6, 23, 0.42);
    color: var(--sioc-text);
    font-size: 0.76rem;
    font-weight: 650;
    letter-spacing: 0.01em;
    white-space: nowrap;
}

/* ---------------------------- Tarjetas KPI -------------------------- */
.sioc-glass-card.sioc-kpi {
    position: relative;
    min-height: 142px;
    padding: 1.25rem;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 0.45rem;
    transition: transform 180ms ease, box-shadow 180ms ease;
}

.sioc-glass-card.sioc-kpi::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    background: var(--sioc-accent, #38BDF8);
    opacity: 0.95;
}

.sioc-glass-card.sioc-kpi:hover {
    transform: translateY(-2px);
    box-shadow:
        0 18px 44px 0 rgba(0, 0, 0, 0.58),
        inset 0 1px 1px 0 rgba(255, 255, 255, 0.20);
}

.sioc-kpi.is-ok { --sioc-accent: #34D399; }
.sioc-kpi.is-warn { --sioc-accent: #FBBF24; }
.sioc-kpi.is-critical { --sioc-accent: #F87171; }
.sioc-kpi.is-info { --sioc-accent: #38BDF8; }

.sioc-kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.sioc-kpi-title {
    color: var(--sioc-muted);
    font-size: 0.74rem;
    font-weight: 800;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

.sioc-kpi-value {
    color: var(--sioc-text);
    font-size: clamp(1.65rem, 2.5vw, 2.15rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.75);
    overflow-wrap: anywhere;
}

.sioc-kpi-delta {
    color: var(--sioc-muted);
    font-size: 0.82rem;
    font-weight: 600;
    line-height: 1.35;
}

.sioc-kpi-pill {
    flex: 0 0 auto;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    border: 1px solid currentColor;
}

.sioc-kpi.is-ok .sioc-kpi-pill {
    color: #A7F3D0;
    background: rgba(52, 211, 153, 0.16);
}

.sioc-kpi.is-warn .sioc-kpi-pill {
    color: #FDE68A;
    background: rgba(251, 191, 36, 0.16);
}

.sioc-kpi.is-critical .sioc-kpi-pill {
    color: var(--sioc-coral-text);
    background: rgba(248, 113, 113, 0.18);
}

.sioc-kpi.is-info .sioc-kpi-pill {
    color: #BAE6FD;
    background: rgba(56, 189, 248, 0.16);
}

/* ------------------------- Notas y pie de pagina -------------------- */
.sioc-glass-note {
    padding: 1rem 1.2rem;
    margin: 0.35rem 0 0.6rem 0;
    color: var(--sioc-muted);
    font-size: 0.92rem;
    line-height: 1.6;
}

.sioc-glass-note strong {
    color: var(--sioc-text);
}

.sioc-glass-note .sioc-note-accent {
    color: var(--sioc-cyan-text);
    font-weight: 700;
}

.sioc-section {
    padding: 0.72rem 1.05rem;
    margin: 1.2rem 0 0.75rem 0;
}

.sioc-section h3 {
    margin: 0;
    color: var(--sioc-text);
    font-size: 1.08rem;
    font-weight: 800;
    letter-spacing: -0.01em;
    text-shadow: 0 2px 6px rgba(0, 0, 0, 0.75);
}

.sioc-section p {
    margin: 0.18rem 0 0 0;
    color: var(--sioc-muted);
    font-size: 0.82rem;
    line-height: 1.45;
}

.sioc-footer {
    margin-top: 1.4rem;
    padding: 1rem 1.25rem;
    color: var(--sioc-muted);
    font-size: 0.78rem;
    text-align: center;
    line-height: 1.55;
}

.sioc-footer strong {
    color: var(--sioc-text);
}

/* --------------------------- Sidebar glass -------------------------- */
[data-testid="stSidebar"] {
    background: rgba(6, 12, 26, 0.74) !important;
    -webkit-backdrop-filter: blur(22px) saturate(180%);
    backdrop-filter: blur(22px) saturate(180%);
    border-right: 1px solid rgba(255, 255, 255, 0.16);
    box-shadow: 12px 0 36px 0 rgba(0, 0, 0, 0.42);
}

[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
    background: transparent !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--sioc-text);
}

.sioc-sidebar-brand {
    padding: 0.9rem 1rem;
    margin-bottom: 0.85rem;
    border-radius: 14px;
    border: 1px solid rgba(56, 189, 248, 0.32);
    background: linear-gradient(
        135deg,
        rgba(56, 189, 248, 0.16),
        rgba(52, 211, 153, 0.10)
    );
}

.sioc-sidebar-brand .sioc-brand-title {
    color: var(--sioc-text);
    font-size: 1rem;
    font-weight: 800;
    letter-spacing: 0.02em;
}

.sioc-sidebar-brand .sioc-brand-sub {
    color: var(--sioc-muted);
    font-size: 0.74rem;
    line-height: 1.4;
    margin-top: 0.2rem;
}

/* ----------------------------- Controles ---------------------------- */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] label {
    color: var(--sioc-text) !important;
    font-weight: 650;
    font-size: 0.82rem;
}

.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div,
.stDateInput input {
    background: rgba(15, 23, 42, 0.78) !important;
    color: var(--sioc-text) !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 10px !important;
}

[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {
    background: rgba(10, 25, 47, 0.96) !important;
    color: var(--sioc-text) !important;
}

[data-baseweb="popover"] li {
    color: var(--sioc-text) !important;
}

/* Slider */
[data-testid="stSlider"] [role="slider"] {
    background: var(--sioc-cyan) !important;
    border-color: var(--sioc-text) !important;
    box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.22) !important;
}

/* Botones */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    width: 100%;
    min-height: 2.65rem;
    padding: 0.55rem 1rem;
    border-radius: 12px;
    border: 1px solid rgba(56, 189, 248, 0.55);
    background: linear-gradient(
        135deg,
        rgba(56, 189, 248, 0.26),
        rgba(52, 211, 153, 0.18)
    );
    color: var(--sioc-text);
    font-weight: 750;
    letter-spacing: 0.01em;
    box-shadow:
        0 8px 24px 0 rgba(0, 0, 0, 0.38),
        inset 0 1px 1px 0 rgba(255, 255, 255, 0.18);
    transition: transform 160ms ease, border-color 160ms ease,
        box-shadow 160ms ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(56, 189, 248, 0.95);
    color: var(--sioc-text);
    box-shadow:
        0 12px 28px 0 rgba(0, 0, 0, 0.46),
        0 0 0 3px rgba(56, 189, 248, 0.16);
}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 2px solid var(--sioc-cyan);
    outline-offset: 2px;
}

/* ------------------------------- Tabs ------------------------------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
    padding: 0.38rem;
    margin-bottom: 0.35rem;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    background: rgba(15, 23, 42, 0.58);
    -webkit-backdrop-filter: blur(22px) saturate(180%);
    backdrop-filter: blur(22px) saturate(180%);
    box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.40);
    overflow-x: auto;
}

.stTabs [data-baseweb="tab"] {
    height: 2.45rem;
    padding: 0 0.95rem;
    border-radius: 10px;
    color: var(--sioc-muted);
    font-weight: 650;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--sioc-text);
    background: rgba(56, 189, 248, 0.10);
}

.stTabs [aria-selected="true"] {
    color: var(--sioc-text) !important;
    background: linear-gradient(
        135deg,
        rgba(56, 189, 248, 0.26),
        rgba(52, 211, 153, 0.16)
    ) !important;
    border: 1px solid rgba(56, 189, 248, 0.38);
}

.stTabs [data-baseweb="tab-highlight"] {
    background-color: transparent;
}

/* ------------------------- Tablas y expanders ----------------------- */
[data-testid="stDataFrame"] * {
    font-size: 0.84rem;
}

[data-testid="stExpander"] summary {
    color: var(--sioc-text);
    font-weight: 700;
}

[data-testid="stAlert"] {
    color: var(--sioc-text);
}

[data-testid="stAlert"] p {
    color: var(--sioc-text);
}

/* --------------------------- Accesibilidad -------------------------- */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition: none !important;
        animation: none !important;
        scroll-behavior: auto !important;
    }
}

*:focus-visible {
    outline: 2px solid var(--sioc-cyan);
    outline-offset: 2px;
}

/* Navegadores sin backdrop-filter: fondo opaco que conserva el contraste */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
    .sioc-glass-panel,
    .sioc-glass-card,
    .sioc-glass-note,
    .sioc-footer,
    [data-testid="stMetric"],
    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    [data-testid="stExpander"],
    [data-testid="stForm"],
    [data-testid="stAlert"] {
        background: rgba(15, 23, 42, 0.94);
    }
    [data-testid="stSidebar"] {
        background: rgba(6, 12, 26, 0.96) !important;
    }
}

/* --------------------------- Responsive ----------------------------- */
@media (max-width: 900px) {
    [data-testid="stAppViewBlockContainer"] {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .sioc-hero {
        padding: 1.25rem;
    }
    .sioc-glass-card.sioc-kpi {
        min-height: 128px;
    }
}
"""


def _build_css(bg_url: str) -> str:
    """Compone la hoja de estilos con la imagen de fondo seleccionada."""
    return _CSS_TEMPLATE.replace("__BG_IMAGE__", _css_background(bg_url))


def inject_glassmorphism_css(bg_url: str) -> None:
    """Inyecta la arquitectura optica de tres capas en la app Streamlit.

    Parameters
    ----------
    bg_url:
        URL de la imagen elegida por :func:`get_random_background`. Si no es
        una URL valida se aplica el gradiente CSS de respaldo.
    """
    st.markdown(f"<style>{_build_css(bg_url)}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Componentes de interfaz
# ---------------------------------------------------------------------------
def render_glass_kpi_card(
    title: str,
    value: str,
    delta: str,
    status: str,
) -> None:
    """Dibuja una tarjeta KPI de cristal esmerilado.

    Parameters
    ----------
    title:
        Etiqueta superior de la metrica.
    value:
        Valor principal (se muestra en blanco nieve, gran tamano).
    delta:
        Texto contextual o variacion.
    status:
        ``ok``, ``warn``, ``critical`` o ``info`` (se aceptan alias en
        espanol como ``verde``, ``amarillo`` o ``rojo``).
    """
    normalized = _normalize_status(status)
    label = _STATUS_LABELS[normalized]
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_delta = html.escape(str(delta))
    st.markdown(
        f"""
<section class="sioc-glass-card sioc-kpi is-{normalized}"
         role="group"
         aria-label="{safe_title}: {safe_value}. {safe_delta}">
    <div class="sioc-kpi-top">
        <span class="sioc-kpi-title">{safe_title}</span>
        <span class="sioc-kpi-pill">{label}</span>
    </div>
    <div class="sioc-kpi-value">{safe_value}</div>
    <div class="sioc-kpi-delta">{safe_delta}</div>
</section>
""",
        unsafe_allow_html=True,
    )


def render_glass_hero(
    eyebrow: str,
    title: str,
    subtitle: str,
    chips: Sequence[str] | None = None,
) -> None:
    """Dibuja el encabezado principal tipo ventana de cristal."""
    chips_html = "".join(
        f'<span class="sioc-chip">{html.escape(str(chip))}</span>'
        for chip in (chips or [])
    )
    st.markdown(
        f"""
<header class="sioc-glass-panel sioc-hero">
    <span class="sioc-eyebrow">{html.escape(str(eyebrow))}</span>
    <h1>{html.escape(str(title))}</h1>
    <p>{html.escape(str(subtitle))}</p>
    <div class="sioc-chip-row">{chips_html}</div>
</header>
""",
        unsafe_allow_html=True,
    )


def render_glass_note(body_html: str) -> None:
    """Dibuja una nota informativa sobre una ventana de cristal.

    El contenido se interpreta como HTML controlado por la aplicacion (no
    debe incluir datos externos sin escapar).
    """
    st.markdown(
        f'<div class="sioc-glass-note" role="note">{body_html}</div>',
        unsafe_allow_html=True,
    )


def render_glass_section_title(title: str, subtitle: str | None = None) -> None:
    """Dibuja un titulo de seccion con su propia ventana de cristal.

    Garantiza que ninguna letra quede directamente sobre la fotografia,
    independientemente de la estructura interna de Streamlit.
    """
    subtitle_html = (
        f"<p>{html.escape(str(subtitle))}</p>" if subtitle else ""
    )
    st.markdown(
        f"""
<section class="sioc-glass-panel sioc-section">
    <h3>{html.escape(str(title))}</h3>
    {subtitle_html}
</section>
""",
        unsafe_allow_html=True,
    )


def render_glass_footer(body_html: str) -> None:
    """Dibuja el pie de pagina institucional sobre cristal."""
    st.markdown(
        f'<footer class="sioc-footer">{body_html}</footer>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tema transparente de Plotly
# ---------------------------------------------------------------------------
def apply_transparent_plotly_theme(fig):
    """Aplica fondo transparente y tipografia clara a una figura Plotly.

    ``paper_bgcolor`` y ``plot_bgcolor`` quedan en ``rgba(0,0,0,0)`` para que
    el blur de la ventana de cristal se vea a traves del grafico. Los ejes,
    leyendas, hover y barra de herramientas usan la paleta luminosa del
    sistema. Retorna la misma figura para permitir encadenamiento.
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": TEXT_PRIMARY,
            "family": "Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
            "size": 13,
        },
        title={
            "font": {"color": TEXT_PRIMARY, "size": 17},
            "x": 0.01,
            "xanchor": "left",
        },
        legend={
            "bgcolor": "rgba(15, 23, 42, 0.62)",
            "bordercolor": "rgba(255, 255, 255, 0.20)",
            "borderwidth": 1,
            "font": {"color": TEXT_SECONDARY, "size": 12},
            "title": {"font": {"color": TEXT_SECONDARY}},
        },
        hoverlabel={
            "bgcolor": "rgba(2, 6, 23, 0.94)",
            "bordercolor": ACCENT_CYAN,
            "font": {"color": TEXT_PRIMARY, "size": 12},
        },
        margin={"l": 56, "r": 28, "t": 58, "b": 48},
        colorway=ACCENT_COLORWAY,
        modebar={
            "bgcolor": "rgba(0,0,0,0)",
            "color": TEXT_SECONDARY,
            "activecolor": ACCENT_CYAN,
        },
    )

    cartesian_axes = [
        axis_name
        for axis_name in fig.layout
        if axis_name.startswith("xaxis") or axis_name.startswith("yaxis")
    ]
    if cartesian_axes:
        fig.update_xaxes(
            gridcolor="rgba(226, 232, 240, 0.14)",
            zerolinecolor="rgba(226, 232, 240, 0.18)",
            linecolor="rgba(226, 232, 240, 0.28)",
            tickfont={"color": TEXT_SECONDARY, "size": 11},
            title_font={"color": TEXT_SECONDARY, "size": 12},
        )
        fig.update_yaxes(
            gridcolor="rgba(226, 232, 240, 0.14)",
            zerolinecolor="rgba(226, 232, 240, 0.18)",
            linecolor="rgba(226, 232, 240, 0.28)",
            tickfont={"color": TEXT_SECONDARY, "size": 11},
            title_font={"color": TEXT_SECONDARY, "size": 12},
        )

    return fig
