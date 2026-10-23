# ESPECIFICACIÓN TÉCNICA Y ARQUITECTURA MAESTRA: sioc-eps-ilo
Proyecto: Sistema Integrado de Operaciones, Control de Agua No Facturada (ANF) e Inteligencia Comercial — Caso Operativo EPS Ilo S.A.
Arquitectura: Monorepo Modular en Python 3.11+ (5 Sub-Proyectos Integrados) + Doble Despliegue Web (Streamlit Cloud & GitHub Pages).

---

## 1. REGLAS ESTRICTAS DE GIT Y AUTORÍA
- Autor obligatorio: Todos los commits DEBEN ejecutarse bajo el usuario Rene-Pongo.
- Verificación previa: Ejecutar siempre git config user.name "Rene-Pongo" antes del primer commit.
- Formato de mensajes (Conventional Commits en español):
  - Fase 1: feat(hydraulics): implementar configuracion normativa y motor de telemetria de Ilo
  - Fase 2: feat(analytics): agregar motor IA de deteccion de ANF y evaluador economico SUNASS
  - Fase 3: feat(streamlit-glass): construir dashboard con efecto blur adaptativo y reportes docx
  - Fase 4: feat(web-portal): desarrollar portal ejecutivo glassmorphism para GitHub Pages
  - Fase 5: docs(release): agregar suite de pruebas unitarias y documentacion ejecutiva

---

## 2. CONTEXTO TÉCNICO Y OPERATIVO REAL DE EPS ILO S.A.
El sistema modela las fuentes de captación, plantas de tratamiento y sectores hidráulicos reales de la provincia de Ilo (Moquegua):

### 2.1 Fuentes de Abastecimiento y Plantas (PTAP)
- Fuentes de Agua Cruda:
  1. Línea de Conducción Pasto Grande (Aporte superficial estratégico, alta sensibilidad a turbiedad estacional).
  2. Galerías Filtrantes del Río Osmore (Agua subterránea subálvea de alta calidad filtrada naturalmente).
- Plantas de Tratamiento de Agua Potable (PTAP):
  1. PTAP Cata Catas (Abastece principalmente Cercado de Ilo y Pacocha).
  2. PTAP Pampa Inalámbrica (Abastece el macro-sector de Pampa Inalámbrica).

### 2.2 Sectores Hidráulicos Monitoreados
1. SEC-01: Pampa Inalámbrica
   - Características: Alta densidad poblacional y crecimiento urbano en cota alta.
   - Problemática modelada: Retos de continuidad horaria (18–22 h/día), presiones bajas en zonas altas y riesgo de conexiones clandestinas en expansiones urbanas.
   - Coordenadas centrales: lat: -17.6534, lon: -71.3185
2. SEC-02: Cercado de Ilo
   - Características: Red antigua (tuberías con décadas de antigüedad en transición a PVC/HDPE).
   - Problemática modelada: Alto riesgo de fugas físicas invisibles en red matriz, roturas nocturnas por sobrepresión y subregistro por micromedidores antiguos.
   - Coordenadas centrales: lat: -17.6458, lon: -71.3442
3. SEC-03: Pacocha / Ciudad Nueva
   - Características: Consumo mixto (residencial consolidado, comercial e industrial/pesquero).
   - Problemática modelada: Monitoreo estricto de macromedición, control de cloro residual libre en cola de red y facturación de alto valor económico.
   - Coordenadas centrales: lat: -17.6251, lon: -71.3395

### 2.3 Parámetros Normativos (SUNASS / DIGESA)
- Presión de servicio normativa: Mínima 10 m.c.a. | Máxima 50 m.c.a.
- Cloro residual libre (DIGESA): Mínimo obligatorio >= 0.5 mg/L en cualquier punto de la red.
- Turbiedad máxima permitida: <= 5.0 NTU.
- Meta referencial de ANF (Agua No Facturada): Alerta amarilla > 28%, Alerta crítica roja > 35%.
- Estructura Tarifaria Referencial (S/ por m3):
  - Social: S/ 1.65 | Doméstico: S/ 2.85 | Comercial: S/ 6.40 | Industrial: S/ 9.20 | Estatal: S/ 4.10
  - Tarifa Media Ponderada: S/ 3.85 / m3 | Costo Variable de Producción: S/ 1.20 / m3.

---

## 3. ARQUITECTURA VISUAL OBLIGATORIA: MOTOR "LUMINANCE-SAFE GLASSMORPHISM" + FONDOS ALEATORIOS
Tanto la aplicación en Streamlit (src/ui_glassmorphism.py + app/dashboard.py) como el Portal Web Ejecutivo (docs/index.html + docs/styles.css + docs/app.js) DEBEN implementar esta arquitectura óptica de 3 capas para garantizar que las letras se lean con perfección absoluta incluso cuando la imagen aleatoria de atrás sea muy oscura o muy clara:

### 3.1 Pool Curado de 8 Imágenes HD para Cambio Aleatorio al Recargar
En cada recarga de página (y mediante un botón interactivo "Cambiar Ambiente Visual"), el fondo selecciona aleatoriamente una de estas 8 fotografías HD verificadas de Unsplash (con fallback a gradiente CSS si no hay conexión):
1. [https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1920&q=80) (Océano profundo y ondas hídricas)
2. [https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80) (Cuenca hidrológica y neblina de montaña)
3. [https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80) (Costa del Pacífico al amanecer)
4. [https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=80) (Red global de telemetría nocturna)
5. [https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1920&q=80) (Geometría natural y recursos hídricos)
6. [https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80) (Cordillera y reserva hídrica altoandina)
7. [https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1920&q=80) (Dinámica de fluidos y mar abierto)
8. [https://images.unsplash.com/photo-1439066615861-d1af74d74000?auto=format&fit=crop&w=1920&q=80](https://images.unsplash.com/photo-1439066615861-d1af74d74000?auto=format&fit=crop&w=1920&q=80) (Espejo de agua de reservorio natural)

### 3.2 Solución Óptica de 3 Capas para Legibilidad Garantizada (WCAG AAA > 10:1)
- Capa 1 (Fondo Dinámico):
  - background-size: cover; background-position: center center; background-attachment: fixed;
  - Fallback CSS: background-color: #071120;
- Capa 2 (Velo Atmosférico Normalizador / Scrim Global):
  - Un recubrimiento fijo sobre la imagen con linear-gradient(135deg, rgba(6, 12, 26, 0.58) 0%, rgba(10, 25, 47, 0.72) 100%) y backdrop-filter: blur(4px). Esto atenúa zonas blancas deslumbrantes de cualquier fotografía sin ocultar su estética ni sus colores.
- Capa 3 (Ventanas y Tarjetas "Smart Frosted Glass"):
  - Todo el texto, KPIs, tablas, controles del sidebar y gráficos van dentro de contenedores con cristal esmerilado calibrado:
    - background: rgba(15, 23, 42, 0.70); (Tinte obsidiana translúcido que asegura que el texto blanco resalte si la foto de atrás es muy clara, y que la ventana tenga cuerpo propio si la foto de atrás es muy oscura).
    - backdrop-filter: blur(22px) saturate(180%); -webkit-backdrop-filter: blur(22px) saturate(180%);
    - border: 1px solid rgba(255, 255, 255, 0.20); border-top: 1px solid rgba(255, 255, 255, 0.38); (Borde especular luminoso que dibuja nítidamente la ventana sobre fondos negros).
    - box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.50), inset 0 1px 1px 0 rgba(255, 255, 255, 0.16);
    - border-radius: 16px; padding: 1.25rem;
- Tipografía y Gráficos Transparentes:
  - Títulos y valores principales: Blanco nieve puro (#F8FAFC) con text-shadow: 0 2px 6px rgba(0, 0, 0, 0.75).
  - Subtítulos y etiquetas: Plata azulado luminoso (#E2E8F0).
  - Acentos semánticos: Cian Hídrico (#38BDF8), Esmeralda (#34D399), Ámbar (#FBBF24), Coral Alerta (#F87171).
  - Todos los gráficos de Plotly y Chart.js DEBEN tener paper_bgcolor="rgba(0,0,0,0)" y plot_bgcolor="rgba(0,0,0,0)" con fuentes en color #F8FAFC, para que el efecto blur de la ventana se vea a través del gráfico.

---

## 4. ESTRUCTURA DEL MONOREPO Y CONTRATOS DE MÓDULOS

    sioc-eps-ilo/
    ├── README.md
    ├── PLAN_ARQUITECTURA.md
    ├── requirements.txt
    ├── .gitignore
    ├── src/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── telemetry_generator.py
    │   ├── anomaly_detector.py
    │   ├── economic_evaluator.py
    │   ├── report_generator.py
    │   └── ui_glassmorphism.py
    ├── app/
    │   └── dashboard.py
    ├── docs/
    │   ├── index.html
    │   ├── styles.css
    │   └── app.js
    └── tests/
        ├── test_telemetry.py
        ├── test_anomaly_detector.py
        └── test_economic_evaluator.py

### Contratos de Datos entre Módulos (Obligatorios para compatibilidad entre fases)
1. src/config.py:
   - Exporta diccionarios/constantes: SECTORS, SOURCES, PTAPS, NORMATIVE_LIMITS, TARIFF_STRUCTURE, BACKGROUND_IMAGES.
2. src/telemetry_generator.py:
   - Función principal: generate_telemetry_data(days: int = 30, seed: int = 42, inject_anomalies: bool = True) -> pd.DataFrame
   - Columnas obligatorias del DataFrame retornado:
     ["timestamp", "sector_id", "sector_name", "fuente_principal", "caudal_lps", "presion_mca", "cloro_mg_l", "turbiedad_ntu", "continuidad_horas", "volumen_producido_m3", "volumen_facturado_m3", "anf_m3", "anf_pct", "injected_event"]
3. src/anomaly_detector.py:
   - Función principal: detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame
   - Añade al DataFrame las columnas:
     ["is_night_window", "cmn_baseline_lps", "cmn_excess_lps", "physical_leak_alert", "commercial_fraud_alert", "quality_chlorine_alert", "pressure_norm_alert", "anomaly_score", "anomaly_type", "severity"]
   - Función resumen: summarize_anomalies_by_sector(df_flagged: pd.DataFrame) -> pd.DataFrame
4. src/economic_evaluator.py:
   - Función de balance y valorización: evaluate_economic_impact(df_flagged: pd.DataFrame) -> dict
     Retorna métricas globales y por sector: volumen_producido_total_m3, volumen_facturado_total_m3, anf_total_m3, anf_porcentaje, perdida_fisica_m3, perdida_comercial_m3, perdida_economica_soles, costo_energia_quimicos_perdido_soles, semaforo_sunass, sector_breakdown (DataFrame).
   - Función simulador What-If / ROI: simulate_anf_reduction_roi(current_anf_m3: float, reduction_target_pct: float, investment_soles: float = 45000.0) -> dict
     Retorna: m3_recuperados_mes, ahorro_mensual_soles, ahorro_anual_soles, payback_meses, van_12_meses_soles, roi_porcentaje.
5. src/report_generator.py:
   - Función principal: generate_executive_docx_report(economic_summary: dict, anomalies_summary: pd.DataFrame, roi_simulation: dict) -> bytes
   - Retorna el archivo Word (.docx) en memoria (io.BytesIO().getvalue()) listo para st.download_button.
6. src/ui_glassmorphism.py:
   - Funciones: inject_glassmorphism_css(bg_url: str) -> None, get_random_background() -> str, render_glass_kpi_card(title: str, value: str, delta: str, status: str) -> None, apply_transparent_plotly_theme(fig) -> fig.

---

## 5. PLAN DE CONSTRUCCIÓN EN 5 FASES SECUENCIALES (MODO BUILD)
- Fase 1 (Cimientos y Motor Hidráulico): Crear requirements.txt, .gitignore, src/__init__.py, src/config.py y src/telemetry_generator.py. Instalar dependencias en .venv, verificar generación de datos y hacer commit como Rene-Pongo.
- Fase 2 (Inteligencia Operativa IA y Evaluación Económica SUNASS): Crear src/anomaly_detector.py y src/economic_evaluator.py. Validar cálculos y hacer commit como Rene-Pongo.
- Fase 3 (Motor Visual Blur, Reportes Word y Dashboard Streamlit): Crear src/ui_glassmorphism.py, src/report_generator.py y app/dashboard.py (con cambio de fondo aleatorio al recargar + botón en sidebar, tarjetas glass, mapa de Ilo, curvas Plotly transparentes, simulador ROI y descarga .docx). Hacer commit como Rene-Pongo.
- Fase 4 (Portal Web Ejecutivo en GitHub Pages): Crear docs/index.html, docs/styles.css y docs/app.js con arquitectura Glassmorphism de 3 capas, fondo aleatorio en cada recarga (window.onload), botón "Cambiar Escenario Visual", mapa interactivo de Ilo con Leaflet, gráficos Chart.js transparentes y calculadora ANF en vivo. Hacer commit como Rene-Pongo.
- Fase 5 (Suite de Pruebas Pytest y README Ejecutivo): Crear pruebas unitarias en tests/, asegurar 100% pass en pytest y redactar README.md profesional con diagramas Mermaid y enfoque directo para EPS Ilo. Hacer commit final como Rene-Pongo.
