"""Configuracion normativa y operativa de EPS Ilo S.A.

Este modulo centraliza los parametros reales modelados para la provincia de
Ilo (Moquegua): sectores hidraulicos, fuentes de captacion, plantas de
tratamiento, limites normativos SUNASS/DIGESA, estructura tarifaria y el pool
de imagenes de fondo del motor visual "Luminance-Safe Glassmorphism".

Todas las fases del proyecto importan estas constantes, por lo que sus
nombres y valores no deben modificarse sin actualizar el contrato de datos
definido en PLAN_ARQUITECTURA.md.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Sectores hidraulicos monitoreados
# ---------------------------------------------------------------------------
# Coordenadas centrales, demanda base, presion de operacion y problematica
# modelada segun el contexto operativo real de EPS Ilo S.A.
SECTORS = {
    "SEC-01": {
        "name": "Pampa Inalambrica",
        "lat": -17.6534,
        "lon": -71.3185,
        "zone": "Cota alta - crecimiento urbano",
        "population": 28500,
        "connections": 7100,
        "base_demand_lps": 58.0,
        "base_pressure_mca": 24.0,
        "pressure_drop_coef": 11.0,
        "base_chlorine_mg_l": 0.82,
        "base_turbidity_ntu": 1.85,
        "base_anf_pct": 30.5,
        "continuity_hours_range": (18, 22),
        "source_id": "SRC-PASTO-GRANDE",
        "ptap_id": "PTAP-PAMPA-INALSAMBRICA",
        "description": (
            "Alta densidad poblacional y crecimiento urbano en cota alta. "
            "Retos de continuidad horaria (18-22 h/dia), presiones bajas en "
            "zonas altas y riesgo de conexiones clandestinas en expansiones "
            "urbanas."
        ),
    },
    "SEC-02": {
        "name": "Cercado de Ilo",
        "lat": -17.6458,
        "lon": -71.3442,
        "zone": "Red antigua en transicion a PVC/HDPE",
        "population": 24200,
        "connections": 6400,
        "base_demand_lps": 46.0,
        "base_pressure_mca": 32.0,
        "pressure_drop_coef": 7.0,
        "base_chlorine_mg_l": 0.74,
        "base_turbidity_ntu": 1.40,
        "base_anf_pct": 34.0,
        "continuity_hours_range": (20, 24),
        "source_id": "SRC-PASTO-GRANDE",
        "ptap_id": "PTAP-CATA-CATAS",
        "description": (
            "Red antigua con tuberias de decadas de antiguedad en transicion "
            "a PVC/HDPE. Alto riesgo de fugas fisicas invisibles en red "
            "matriz, roturas nocturnas por sobrepresion y subregistro por "
            "micromedidores antiguos."
        ),
    },
    "SEC-03": {
        "name": "Pacocha / Ciudad Nueva",
        "lat": -17.6251,
        "lon": -71.3395,
        "zone": "Consumo mixto residencial, comercial e industrial",
        "population": 21800,
        "connections": 5200,
        "base_demand_lps": 52.0,
        "base_pressure_mca": 30.0,
        "pressure_drop_coef": 6.0,
        "base_chlorine_mg_l": 0.62,
        "base_turbidity_ntu": 1.10,
        "base_anf_pct": 26.5,
        "continuity_hours_range": (21, 24),
        "source_id": "SRC-OSMORE",
        "ptap_id": "PTAP-CATA-CATAS",
        "description": (
            "Consumo mixto (residencial consolidado, comercial e "
            "industrial/pesquero). Monitoreo estricto de macromedicion, "
            "control de cloro residual libre en cola de red y facturacion de "
            "alto valor economico."
        ),
    },
}

# ---------------------------------------------------------------------------
# 2. Fuentes de abastecimiento de agua cruda
# ---------------------------------------------------------------------------
SOURCES = {
    "SRC-PASTO-GRANDE": {
        "name": "Linea de Conduccion Pasto Grande",
        "type": "Superficial",
        "description": (
            "Aporte superficial estrategico, alta sensibilidad a turbiedad "
            "estacional."
        ),
        "design_flow_lps": 180.0,
    },
    "SRC-OSMORE": {
        "name": "Galerias Filtrantes del Rio Osmore",
        "type": "Subterranea subalvea",
        "description": (
            "Agua subterranea subalvea de alta calidad filtrada naturalmente."
        ),
        "design_flow_lps": 120.0,
    },
}

# ---------------------------------------------------------------------------
# 3. Plantas de Tratamiento de Agua Potable (PTAP)
# ---------------------------------------------------------------------------
PTAPS = {
    "PTAP-CATA-CATAS": {
        "name": "PTAP Cata Catas",
        "served_sectors": ["SEC-02", "SEC-03"],
        "source_ids": ["SRC-PASTO-GRANDE", "SRC-OSMORE"],
        "design_flow_lps": 170.0,
        "description": "Abastece principalmente Cercado de Ilo y Pacocha.",
    },
    "PTAP-PAMPA-INALSAMBRICA": {
        "name": "PTAP Pampa Inalambrica",
        "served_sectors": ["SEC-01"],
        "source_ids": ["SRC-PASTO-GRANDE"],
        "design_flow_lps": 95.0,
        "description": "Abastece el macro-sector de Pampa Inalambrica.",
    },
}

# ---------------------------------------------------------------------------
# 4. Parametros normativos SUNASS / DIGESA
# ---------------------------------------------------------------------------
NORMATIVE_LIMITS = {
    # Presion de servicio (m.c.a.)
    "presion_min_mca": 10.0,
    "presion_max_mca": 50.0,
    # Cloro residual libre (mg/L) - DIGESA
    "cloro_min_mg_l": 0.5,
    "cloro_max_mg_l": 5.0,
    # Turbiedad maxima permitida (NTU)
    "turbiedad_max_ntu": 5.0,
    # Meta referencial de Agua No Facturada (ANF)
    "anf_alerta_amarilla_pct": 28.0,
    "anf_alerta_critica_pct": 35.0,
    # Ventana nocturna operativa para caudal minimo nocturno (CMN)
    "night_window_start_hour": 0,
    "night_window_end_hour": 5,
    # Continuidad del servicio (horas/dia)
    "continuidad_min_horas": 18.0,
    "continuidad_max_horas": 24.0,
}

# ---------------------------------------------------------------------------
# 5. Estructura tarifaria referencial (S/ por m3)
# ---------------------------------------------------------------------------
TARIFF_STRUCTURE = {
    "social": 1.65,
    "domestico": 2.85,
    "comercial": 6.40,
    "industrial": 9.20,
    "estatal": 4.10,
    "tarifa_media_ponderada": 3.85,
    "costo_variable_produccion": 1.20,
}

# ---------------------------------------------------------------------------
# 6. Pool curado de imagenes HD para el fondo aleatorio
# ---------------------------------------------------------------------------
BACKGROUND_IMAGES = [
    "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1920&q=80",
    "https://images.unsplash.com/photo-1439066615861-d1af74d74000?auto=format&fit=crop&w=1920&q=80",
]

# ---------------------------------------------------------------------------
# 7. Parametros generales del motor de telemetria
# ---------------------------------------------------------------------------
TELEMETRY_DEFAULT_DAYS = 30
TELEMETRY_DEFAULT_SEED = 42

# Perfil horario adimensional de demanda (0 = madrugada, 19 = pico vespertino)
HOURLY_DEMAND_PROFILE = (
    0.52, 0.48, 0.45, 0.44, 0.47, 0.58,
    0.78, 1.00, 1.12, 1.18, 1.15, 1.10,
    1.05, 1.00, 0.96, 0.94, 0.98, 1.08,
    1.22, 1.30, 1.20, 1.02, 0.82, 0.66,
)

CITY = {
    "name": "Ilo",
    "region": "Moquegua",
    "country": "Peru",
    "lat": -17.6394,
    "lon": -71.3375,
    "eps": "EPS Ilo S.A.",
}
