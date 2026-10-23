/* ============================================================================
   SIOC · EPS Ilo S.A. — Portal Ejecutivo de Agua No Facturada
   ----------------------------------------------------------------------------
   - Motor visual de 3 capas: fondo aleatorio (8 imágenes HD) + scrim + glass.
   - Fondo distinto en cada recarga y botón "Cambiar Escenario Visual".
   - Mapa interactivo Leaflet de los 3 sectores hidráulicos de Ilo.
   - Gráficos Chart.js con lienzo transparente (paper/plot 0,0,0,0).
   - Calculadora interactiva de ROI / ANF valorizada a tarifa media SUNASS.

   Los datos de referencia provienen del pipeline del monorepo
   (src/telemetry_generator.py -> anomaly_detector.py -> economic_evaluator.py)
   con ventana de 30 días, semilla 42 y contaminación 0.05.
   ========================================================================== */

(function () {
    "use strict";

    /* ---------------------------------------------------------------------
       Datos de referencia (snapshot del pipeline, incrustado para que el
       portal funcione como sitio estático en GitHub Pages sin backend).
       --------------------------------------------------------------------- */
    const SIOC_DATA = {"meta":{"days":30,"seed":42,"generated_at":"2026-10-22 23:00","period_start":"2026-09-23","period_end":"2026-10-22","records":2160,"city":{"name":"Ilo","region":"Moquegua","country":"Peru","lat":-17.6394,"lon":-71.3375,"eps":"EPS Ilo S.A."},"eps":"EPS Ilo S.A."},"normative":{"presion_min_mca":10.0,"presion_max_mca":50.0,"cloro_min_mg_l":0.5,"cloro_max_mg_l":5.0,"turbiedad_max_ntu":5.0,"anf_alerta_amarilla_pct":28.0,"anf_alerta_critica_pct":35.0,"night_window_start_hour":0,"night_window_end_hour":5,"continuidad_min_horas":18.0,"continuidad_max_horas":24.0},"tariffs":{"social":1.65,"domestico":2.85,"comercial":6.4,"industrial":9.2,"estatal":4.1,"tarifa_media_ponderada":3.85,"costo_variable_produccion":1.2},"sectors":{"SEC-01":{"name":"Pampa Inalambrica","lat":-17.6534,"lon":-71.3185,"zone":"Cota alta - crecimiento urbano","population":28500,"connections":7100,"base_demand_lps":58.0,"base_pressure_mca":24.0,"pressure_drop_coef":11.0,"base_chlorine_mg_l":0.82,"base_turbidity_ntu":1.85,"base_anf_pct":30.5,"continuity_hours_range":[18,22],"source_id":"SRC-PASTO-GRANDE","ptap_id":"PTAP-PAMPA-INALSAMBRICA","description":"Alta densidad poblacional y crecimiento urbano en cota alta. Retos de continuidad horaria (18-22 h/dia), presiones bajas en zonas altas y riesgo de conexiones clandestinas en expansiones urbanas."},"SEC-02":{"name":"Cercado de Ilo","lat":-17.6458,"lon":-71.3442,"zone":"Red antigua en transicion a PVC/HDPE","population":24200,"connections":6400,"base_demand_lps":46.0,"base_pressure_mca":32.0,"pressure_drop_coef":7.0,"base_chlorine_mg_l":0.74,"base_turbidity_ntu":1.4,"base_anf_pct":34.0,"continuity_hours_range":[20,24],"source_id":"SRC-PASTO-GRANDE","ptap_id":"PTAP-CATA-CATAS","description":"Red antigua con tuberias de decadas de antiguedad en transicion a PVC/HDPE. Alto riesgo de fugas fisicas invisibles en red matriz, roturas nocturnas por sobrepresion y subregistro por micromedidores antiguos."},"SEC-03":{"name":"Pacocha / Ciudad Nueva","lat":-17.6251,"lon":-71.3395,"zone":"Consumo mixto residencial, comercial e industrial","population":21800,"connections":5200,"base_demand_lps":52.0,"base_pressure_mca":30.0,"pressure_drop_coef":6.0,"base_chlorine_mg_l":0.62,"base_turbidity_ntu":1.1,"base_anf_pct":26.5,"continuity_hours_range":[21,24],"source_id":"SRC-OSMORE","ptap_id":"PTAP-CATA-CATAS","description":"Consumo mixto (residencial consolidado, comercial e industrial/pesquero). Monitoreo estricto de macromedicion, control de cloro residual libre en cola de red y facturacion de alto valor economico."}},"sources":{"SRC-PASTO-GRANDE":{"name":"Linea de Conduccion Pasto Grande","type":"Superficial","description":"Aporte superficial estrategico, alta sensibilidad a turbiedad estacional.","design_flow_lps":180.0},"SRC-OSMORE":{"name":"Galerias Filtrantes del Rio Osmore","type":"Subterranea subalvea","description":"Agua subterranea subalvea de alta calidad filtrada naturalmente.","design_flow_lps":120.0}},"ptaps":{"PTAP-CATA-CATAS":{"name":"PTAP Cata Catas","served_sectors":["SEC-02","SEC-03"],"source_ids":["SRC-PASTO-GRANDE","SRC-OSMORE"],"design_flow_lps":170.0,"description":"Abastece principalmente Cercado de Ilo y Pacocha."},"PTAP-PAMPA-INALSAMBRICA":{"name":"PTAP Pampa Inalambrica","served_sectors":["SEC-01"],"source_ids":["SRC-PASTO-GRANDE"],"design_flow_lps":95.0,"description":"Abastece el macro-sector de Pampa Inalambrica."}},"backgrounds":["https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1920&q=80","https://images.unsplash.com/photo-1439066615861-d1af74d74000?auto=format&fit=crop&w=1920&q=80"],"economic":{"volumen_producido_total_m3":337512.888,"volumen_facturado_total_m3":233980.657,"anf_total_m3":103532.231,"anf_porcentaje":30.68,"perdida_fisica_m3":101251.084,"perdida_comercial_m3":2281.147,"perdida_economica_soles":398599.09,"costo_energia_quimicos_perdido_soles":124238.68,"semaforo_sunass":"AMARILLO"},"sector_breakdown":[{"sector_id":"SEC-01","sector_name":"Pampa Inalambrica","volumen_producido_m3":119554.272,"volumen_facturado_m3":82596.093,"anf_m3":36958.179,"anf_pct":30.913,"perdida_fisica_m3":36315.226,"perdida_comercial_m3":642.953,"perdida_economica_soles":142288.989,"costo_energia_quimicos_soles":44349.815,"alertas_fugas":4,"alertas_fraudes":6,"semaforo_sunass":"AMARILLO"},{"sector_id":"SEC-02","sector_name":"Cercado de Ilo","volumen_producido_m3":101006.1,"volumen_facturado_m3":65746.522,"anf_m3":35259.578,"anf_pct":34.908,"perdida_fisica_m3":34642.262,"perdida_comercial_m3":617.316,"perdida_economica_soles":135749.375,"costo_energia_quimicos_soles":42311.494,"alertas_fugas":6,"alertas_fraudes":6,"semaforo_sunass":"AMARILLO"},{"sector_id":"SEC-03","sector_name":"Pacocha / Ciudad Nueva","volumen_producido_m3":116952.516,"volumen_facturado_m3":85638.042,"anf_m3":31314.474,"anf_pct":26.775,"perdida_fisica_m3":30293.596,"perdida_comercial_m3":1020.878,"perdida_economica_soles":120560.725,"costo_energia_quimicos_soles":37577.369,"alertas_fugas":3,"alertas_fraudes":10,"semaforo_sunass":"VERDE"}],"anomalies":[{"sector_id":"SEC-01","sector_name":"Pampa Inalambrica","registros":720,"alertas_totales":54,"alertas_porcentaje":7.5,"fugas_fisicas":4,"fraudes_comerciales":6,"alertas_cloro":0,"alertas_turbiedad":8,"alertas_presion":3,"alertas_estadisticas":33,"anf_promedio_pct":26.06,"score_promedio":0.3063,"score_maximo":0.9862,"severidad_maxima":"critica","tipo_predominante":"patron_atipico"},{"sector_id":"SEC-02","sector_name":"Cercado de Ilo","registros":720,"alertas_totales":35,"alertas_porcentaje":4.86,"fugas_fisicas":6,"fraudes_comerciales":6,"alertas_cloro":0,"alertas_turbiedad":0,"alertas_presion":0,"alertas_estadisticas":23,"anf_promedio_pct":32.31,"score_promedio":0.2144,"score_maximo":0.9859,"severidad_maxima":"critica","tipo_predominante":"patron_atipico"},{"sector_id":"SEC-03","sector_name":"Pacocha / Ciudad Nueva","registros":720,"alertas_totales":55,"alertas_porcentaje":7.64,"fugas_fisicas":3,"fraudes_comerciales":10,"alertas_cloro":26,"alertas_turbiedad":0,"alertas_presion":0,"alertas_estadisticas":16,"anf_promedio_pct":25.44,"score_promedio":0.2683,"score_maximo":0.9865,"severidad_maxima":"critica","tipo_predominante":"cloro_bajo"}],"sector_stats":{"SEC-01":{"anf_pct":30.91,"presion_mca":20.19,"cloro_mg_l":0.822,"turbiedad_ntu":1.95,"continuidad_horas":20.31,"alertas":54},"SEC-02":{"anf_pct":34.88,"presion_mca":29.83,"cloro_mg_l":0.743,"turbiedad_ntu":1.45,"continuidad_horas":22.33,"alertas":35},"SEC-03":{"anf_pct":26.74,"presion_mca":28.03,"cloro_mg_l":0.617,"turbiedad_ntu":1.14,"continuidad_horas":22.89,"alertas":55}},"daily":{"SEC-01":{"labels":["2026-09-23","2026-09-24","2026-09-25","2026-09-26","2026-09-27","2026-09-28","2026-09-29","2026-09-30","2026-10-01","2026-10-02","2026-10-03","2026-10-04","2026-10-05","2026-10-06","2026-10-07","2026-10-08","2026-10-09","2026-10-10","2026-10-11","2026-10-12","2026-10-13","2026-10-14","2026-10-15","2026-10-16","2026-10-17","2026-10-18","2026-10-19","2026-10-20","2026-10-21","2026-10-22"],"anf":[25.55,26.95,26.18,24.66,26.34,29.68,22.58,25.13,22.48,23.7,26.39,28.74,25.74,27.07,26.76,26.86,26.92,23.09,33.49,25.33,26.04,24.95,20.99,27.32,26.29,25.77,25.0,30.4,24.23,27.06],"presion":[14.64,17.91,16.61,16.92,16.55,18.91,14.63,17.74,16.29,14.72,17.36,18.6,17.31,18.26,17.95,17.39,16.11,14.51,18.5,16.67,17.04,15.99,15.46,18.92,17.79,18.43,16.51,19.3,17.28,16.41]},"SEC-02":{"labels":["2026-09-23","2026-09-24","2026-09-25","2026-09-26","2026-09-27","2026-09-28","2026-09-29","2026-09-30","2026-10-01","2026-10-02","2026-10-03","2026-10-04","2026-10-05","2026-10-06","2026-10-07","2026-10-08","2026-10-09","2026-10-10","2026-10-11","2026-10-12","2026-10-13","2026-10-14","2026-10-15","2026-10-16","2026-10-17","2026-10-18","2026-10-19","2026-10-20","2026-10-21","2026-10-22"],"anf":[35.02,41.51,30.0,35.29,32.69,33.17,27.16,33.5,32.39,32.71,31.26,31.41,28.72,26.44,30.16,36.72,33.42,32.82,32.19,32.71,27.6,31.68,31.82,34.58,34.41,29.51,36.97,31.64,34.72,27.21],"presion":[30.22,28.14,26.15,29.82,28.52,29.02,24.38,28.48,27.34,30.0,27.15,28.7,25.9,24.55,24.67,29.57,28.26,25.96,28.8,25.2,24.72,27.17,28.79,30.58,28.84,26.19,30.05,27.18,30.03,24.74]},"SEC-03":{"labels":["2026-09-23","2026-09-24","2026-09-25","2026-09-26","2026-09-27","2026-09-28","2026-09-29","2026-09-30","2026-10-01","2026-10-02","2026-10-03","2026-10-04","2026-10-05","2026-10-06","2026-10-07","2026-10-08","2026-10-09","2026-10-10","2026-10-11","2026-10-12","2026-10-13","2026-10-14","2026-10-15","2026-10-16","2026-10-17","2026-10-18","2026-10-19","2026-10-20","2026-10-21","2026-10-22"],"anf":[24.12,27.28,24.36,20.01,22.84,24.56,24.96,25.69,31.55,25.84,25.4,26.02,31.65,25.66,28.26,25.77,23.89,28.55,22.23,25.8,24.04,27.78,28.2,23.67,28.94,24.4,22.64,22.56,22.83,23.66],"presion":[25.58,27.55,25.74,24.26,26.58,28.24,28.15,26.73,28.19,25.58,25.39,25.72,25.88,27.19,27.71,25.76,24.55,28.49,27.86,28.71,25.09,27.03,26.69,28.57,27.89,28.0,25.96,24.33,24.04,28.53]}},"monthly_anf_m3":103532.23,"roi_default":{"m3_recuperados_mes":31059.669,"ahorro_mensual_soles":119579.73,"ahorro_anual_soles":1434956.72,"payback_meses":0.38,"van_12_meses_soles":1305236.4,"roi_porcentaje":3088.79},"top_alerts":[{"timestamp":"2026-09-23 03:00","sector_id":"SEC-03","sector_name":"Pacocha / Ciudad Nueva","anomaly_type":"fuga_fisica","severity":"critica","score":0.987,"caudal_lps":39.61,"presion_mca":31.07,"cloro_mg_l":0.433,"anf_pct":34.22},{"timestamp":"2026-09-24 03:00","sector_id":"SEC-01","sector_name":"Pampa Inalambrica","anomaly_type":"fuga_fisica","severity":"critica","score":0.986,"caudal_lps":43.44,"presion_mca":25.24,"cloro_mg_l":0.858,"anf_pct":38.53},{"timestamp":"2026-10-08 02:00","sector_id":"SEC-02","sector_name":"Cercado de Ilo","anomaly_type":"fuga_fisica","severity":"alta","score":0.986,"caudal_lps":29.78,"presion_mca":32.66,"cloro_mg_l":0.619,"anf_pct":42.22},{"timestamp":"2026-09-23 04:00","sector_id":"SEC-03","sector_name":"Pacocha / Ciudad Nueva","anomaly_type":"fuga_fisica","severity":"critica","score":0.986,"caudal_lps":40.74,"presion_mca":28.36,"cloro_mg_l":0.622,"anf_pct":34.28},{"timestamp":"2026-09-26 03:00","sector_id":"SEC-01","sector_name":"Pampa Inalambrica","anomaly_type":"fuga_fisica","severity":"critica","score":0.985,"caudal_lps":41.13,"presion_mca":23.26,"cloro_mg_l":0.774,"anf_pct":35.92},{"timestamp":"2026-09-24 04:00","sector_id":"SEC-01","sector_name":"Pampa Inalambrica","anomaly_type":"fuga_fisica","severity":"critica","score":0.985,"caudal_lps":46.82,"presion_mca":24.28,"cloro_mg_l":0.799,"anf_pct":37.3},{"timestamp":"2026-09-26 02:00","sector_id":"SEC-01","sector_name":"Pampa Inalambrica","anomaly_type":"fuga_fisica","severity":"alta","score":0.985,"caudal_lps":39.78,"presion_mca":24.61,"cloro_mg_l":0.901,"anf_pct":34.95},{"timestamp":"2026-09-23 02:00","sector_id":"SEC-03","sector_name":"Pacocha / Ciudad Nueva","anomaly_type":"fuga_fisica","severity":"critica","score":0.984,"caudal_lps":41.47,"presion_mca":29.7,"cloro_mg_l":0.705,"anf_pct":34.18},{"timestamp":"2026-10-08 01:00","sector_id":"SEC-02","sector_name":"Cercado de Ilo","anomaly_type":"fuga_fisica","severity":"critica","score":0.984,"caudal_lps":33.69,"presion_mca":30.02,"cloro_mg_l":0.803,"anf_pct":43.71},{"timestamp":"2026-09-24 02:00","sector_id":"SEC-02","sector_name":"Cercado de Ilo","anomaly_type":"fuga_fisica","severity":"alta","score":0.984,"caudal_lps":29.91,"presion_mca":32.54,"cloro_mg_l":0.699,"anf_pct":42.49}]};

    /* ---------------------------------------------------------------------
       Constantes de presentación
       --------------------------------------------------------------------- */
    const SECTOR_ORDER = ["SEC-01", "SEC-02", "SEC-03"];

    const SECTOR_DISPLAY = {
        "SEC-01": "Pampa Inalámbrica",
        "SEC-02": "Cercado de Ilo",
        "SEC-03": "Pacocha / Ciudad Nueva"
    };

    const SECTOR_COLORS = {
        "SEC-01": "#38BDF8",
        "SEC-02": "#34D399",
        "SEC-03": "#FBBF24"
    };

    const ANOMALY_LABELS = {
        fuga_fisica: "Fuga física",
        fraude_comercial: "Fraude comercial",
        cloro_bajo: "Cloro bajo",
        turbiedad_alta: "Turbiedad alta",
        presion_fuera_rango: "Presión fuera de rango",
        patron_atipico: "Patrón atípico",
        normal: "Normal"
    };

    const SEVERITY_META = {
        critica: { label: "Crítica", className: "is-critical" },
        alta: { label: "Alta", className: "is-alta" },
        media: { label: "Media", className: "is-media" },
        baja: { label: "Baja", className: "is-baja" },
        normal: { label: "Normal", className: "is-baja" }
    };

    const STATUS_META = {
        ok: { label: "ÓPTIMO" },
        warn: { label: "ALERTA" },
        critical: { label: "CRÍTICO" },
        info: { label: "INFO" }
    };

    const FALLBACK_GRADIENT =
        "linear-gradient(135deg, #071120 0%, #0A192F 45%, #10263F 100%)";

    const ANNUAL_DISCOUNT_RATE = 0.12;
    const MONTHLY_DISCOUNT_RATE =
        Math.pow(1 + ANNUAL_DISCOUNT_RATE, 1 / 12) - 1;

    const COLORS = {
        text: "#F8FAFC",
        muted: "#E2E8F0",
        cyan: "#38BDF8",
        emerald: "#34D399",
        amber: "#FBBF24",
        coral: "#F87171",
        violet: "#A78BFA",
        aqua: "#22D3EE",
        grid: "rgba(226, 232, 240, 0.10)",
        axis: "rgba(226, 232, 240, 0.22)"
    };

    const CHART_IDS = [
        "chart-anf",
        "chart-balance",
        "chart-chlorine",
        "chart-alerts",
        "chart-roi"
    ];

    const state = {
        booted: false,
        bgInitialized: false,
        bgIndex: null,
        usingA: true,
        charts: {},
        map: null,
        roi: null
    };

    /* ---------------------------------------------------------------------
       Utilidades de formato y DOM
       --------------------------------------------------------------------- */
    function fmtNumber(value, decimals) {
        const places = Number.isInteger(decimals) ? decimals : 0;
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
            return "—";
        }
        const fixed = Math.abs(numeric).toFixed(places);
        const parts = fixed.split(".");
        const grouped = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        const sign = numeric < 0 ? "-" : "";
        return sign + grouped + (parts[1] ? "," + parts[1] : "");
    }

    function fmtInt(value) {
        return fmtNumber(value, 0);
    }

    function fmtPct(value, decimals) {
        return fmtNumber(value, Number.isInteger(decimals) ? decimals : 1) + "%";
    }

    function fmtMoney(value) {
        return "S/ " + fmtNumber(value, 0);
    }

    function fmtShortDate(isoDate) {
        const parts = String(isoDate).split("-");
        return parts.length === 3 ? parts[2] + "/" + parts[1] : String(isoDate);
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>"']/g, function (character) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[character];
        });
    }

    function withAlpha(hexColor, alpha) {
        const clean = String(hexColor).replace("#", "");
        if (clean.length !== 6) {
            return "rgba(56, 189, 248, " + alpha + ")";
        }
        const r = parseInt(clean.slice(0, 2), 16);
        const g = parseInt(clean.slice(2, 4), 16);
        const b = parseInt(clean.slice(4, 6), 16);
        return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")";
    }

    function statusFromAnf(anfPct) {
        const value = Number(anfPct) || 0;
        if (value > SIOC_DATA.normative.anf_alerta_critica_pct) {
            return "critical";
        }
        if (value > SIOC_DATA.normative.anf_alerta_amarilla_pct) {
            return "warn";
        }
        return "ok";
    }

    function statusFromSemaforo(semaforo) {
        if (semaforo === "ROJO") {
            return "critical";
        }
        if (semaforo === "AMARILLO") {
            return "warn";
        }
        return "ok";
    }

    function anfColor(anfPct) {
        const status = statusFromAnf(anfPct);
        if (status === "critical") {
            return COLORS.coral;
        }
        if (status === "warn") {
            return COLORS.amber;
        }
        return COLORS.emerald;
    }

    function safe(label, task) {
        try {
            task();
        } catch (error) {
            // Un fallo aislado (CDN, gráfico, mapa) no debe tumbar el portal.
            console.error("[SIOC] " + label, error);
        }
    }

    function sectorRow(sectorId) {
        return (SIOC_DATA.sector_breakdown || []).find(function (row) {
            return row.sector_id === sectorId;
        });
    }

    function anomalyRow(sectorId) {
        return (SIOC_DATA.anomalies || []).find(function (row) {
            return row.sector_id === sectorId;
        });
    }

    function sectorStat(sectorId) {
        return (SIOC_DATA.sector_stats || {})[sectorId] || {};
    }

    function sectorMeta(sectorId) {
        return (SIOC_DATA.sectors || {})[sectorId] || {};
    }

    /* ---------------------------------------------------------------------
       CAPA 1 + 2: fondo aleatorio con crossfade y fallback
       --------------------------------------------------------------------- */
    function pickBackgroundIndex(excludeIndex) {
        const pool = Array.isArray(SIOC_DATA.backgrounds)
            ? SIOC_DATA.backgrounds
            : [];
        if (!pool.length) {
            return -1;
        }
        if (pool.length === 1) {
            return 0;
        }
        let index = excludeIndex;
        let guard = 0;
        while (index === excludeIndex && guard < 20) {
            index = Math.floor(Math.random() * pool.length);
            guard += 1;
        }
        return index === excludeIndex ? (excludeIndex + 1) % pool.length : index;
    }

    function updateBackgroundIndicator(index) {
        const badge = document.getElementById("bg-indicator");
        if (!badge) {
            return;
        }
        if (index === null || index < 0) {
            badge.textContent = "Ambiente visual: gradiente de respaldo";
        } else {
            badge.textContent =
                "Ambiente visual " + (index + 1) + "/" + SIOC_DATA.backgrounds.length;
        }
    }

    function applyRandomBackground() {
        const pool = Array.isArray(SIOC_DATA.backgrounds)
            ? SIOC_DATA.backgrounds
            : [];
        const layerA = document.getElementById("bg-a");
        const layerB = document.getElementById("bg-b");
        if (!pool.length || !layerA || !layerB) {
            updateBackgroundIndicator(-1);
            state.bgInitialized = true;
            return;
        }

        const index = pickBackgroundIndex(state.bgIndex);
        const url = pool[index];
        const incoming = state.usingA ? layerB : layerA;
        const current = state.usingA ? layerA : layerB;
        let finished = false;

        function finalize(loaded) {
            if (finished) {
                return;
            }
            finished = true;
            incoming.style.backgroundImage = loaded
                ? 'url("' + url.replace(/"/g, "%22") + '")'
                : FALLBACK_GRADIENT;
            incoming.classList.add("is-active");
            current.classList.remove("is-active");
            state.usingA = !state.usingA;
            state.bgIndex = index;
            state.bgInitialized = true;
            updateBackgroundIndicator(loaded ? index : -1);
        }

        const preloader = new Image();
        preloader.onload = function () {
            finalize(true);
        };
        preloader.onerror = function () {
            finalize(false);
        };
        preloader.src = url;

        // Si Unsplash no responde, el gradiente de respaldo entra en 8 s.
        window.setTimeout(function () {
            finalize(false);
        }, 8000);
    }

    function bindBackgroundButton() {
        const button = document.getElementById("bg-button");
        if (!button) {
            return;
        }
        button.addEventListener("click", function () {
            applyRandomBackground();
        });
    }

    /* ---------------------------------------------------------------------
       Cabecera dinámica y KPIs
       --------------------------------------------------------------------- */
    function renderHeaderMeta() {
        const economic = SIOC_DATA.economic;
        const meta = SIOC_DATA.meta;
        const status = statusFromSemaforo(economic.semaforo_sunass);

        function setChipText(id, text) {
            const chip = document.getElementById(id);
            if (!chip) {
                return;
            }
            const target = chip.querySelector(".chip__text") || chip;
            target.textContent = text;
        }

        setChipText(
            "chip-period",
            "Periodo " + fmtShortDate(meta.period_start) +
            " — " + fmtShortDate(meta.period_end)
        );
        setChipText(
            "chip-records",
            fmtInt(meta.records) + " registros horarios"
        );
        setChipText(
            "chip-anf",
            "ANF " + fmtPct(economic.anf_porcentaje)
        );
        setChipText(
            "chip-sunass",
            "SUNASS " + economic.semaforo_sunass
        );

        const anfChip = document.getElementById("chip-anf");
        if (anfChip) {
            anfChip.classList.remove("is-warn", "is-ok", "is-critical");
            anfChip.classList.add(status === "ok" ? "is-ok" : "is-warn");
        }

        const sunassChip = document.getElementById("chip-sunass");
        if (sunassChip) {
            sunassChip.classList.remove("is-warn", "is-ok", "is-critical");
            sunassChip.classList.add(status === "ok" ? "is-ok" : "is-warn");
        }

        const kpiMeta = document.getElementById("kpi-period-meta");
        if (kpiMeta) {
            kpiMeta.textContent =
                meta.days + " días · " + fmtInt(meta.records) + " registros";
        }

        const footer = document.getElementById("footer-updated");
        if (footer) {
            footer.textContent =
                "Datos simulados con fines de planificación · Periodo " +
                fmtShortDate(meta.period_start) + " — " + fmtShortDate(meta.period_end) +
                " · Semilla " + meta.seed;
        }
    }

    function renderKpis() {
        const container = document.getElementById("kpi-grid");
        if (!container) {
            return;
        }
        const economic = SIOC_DATA.economic;
        const status = statusFromSemaforo(economic.semaforo_sunass);
        const alertsTotal = (SIOC_DATA.anomalies || []).reduce(function (total, row) {
            return total + (Number(row.alertas_totales) || 0);
        }, 0);
        const leaks = (SIOC_DATA.anomalies || []).reduce(function (total, row) {
            return total + (Number(row.fugas_fisicas) || 0);
        }, 0);
        const frauds = (SIOC_DATA.anomalies || []).reduce(function (total, row) {
            return total + (Number(row.fraudes_comerciales) || 0);
        }, 0);

        const cards = [
            {
                label: "ANF del periodo",
                value: fmtPct(economic.anf_porcentaje),
                delta: fmtInt(economic.anf_total_m3) + " m³ no facturados",
                status: status
            },
            {
                label: "Pérdida económica",
                value: fmtMoney(economic.perdida_economica_soles),
                delta:
                    "Costo energía/químicos: " +
                    fmtMoney(economic.costo_energia_quimicos_perdido_soles),
                status: status
            },
            {
                label: "Volumen facturado",
                value: fmtInt(economic.volumen_facturado_total_m3) + " m³",
                delta: "Producido: " + fmtInt(economic.volumen_producido_total_m3) + " m³",
                status: "info"
            },
            {
                label: "Alertas detectadas",
                value: fmtInt(alertsTotal),
                delta: "Fugas: " + fmtInt(leaks) + " · Fraudes: " + fmtInt(frauds),
                status: alertsTotal > 0 ? "critical" : "ok"
            }
        ];

        container.innerHTML = cards.map(function (card) {
            const meta = STATUS_META[card.status] || STATUS_META.info;
            return (
                '<article class="glass kpi is-' + card.status + '">' +
                    '<div class="kpi__top">' +
                        '<span class="kpi__label">' + escapeHtml(card.label) + "</span>" +
                        '<span class="kpi__pill">' + meta.label + "</span>" +
                    "</div>" +
                    '<div class="kpi__value">' + escapeHtml(card.value) + "</div>" +
                    '<p class="kpi__delta">' + escapeHtml(card.delta) + "</p>" +
                "</article>"
            );
        }).join("");
    }

    function renderSectorTable() {
        const body = document.getElementById("sector-table-body");
        if (!body) {
            return;
        }
        body.innerHTML = SECTOR_ORDER.map(function (sectorId) {
            const row = sectorRow(sectorId);
            if (!row) {
                return "";
            }
            const semaforo = String(row.semaforo_sunass || "VERDE");
            const badgeClass = statusFromSemaforo(semaforo);
            return (
                "<tr>" +
                    '<td class="sector-cell">' + escapeHtml(SECTOR_DISPLAY[sectorId]) + "</td>" +
                    '<td class="num">' + fmtInt(row.volumen_producido_m3) + "</td>" +
                    '<td class="num">' + fmtInt(row.volumen_facturado_m3) + "</td>" +
                    '<td class="num">' + fmtInt(row.anf_m3) + "</td>" +
                    '<td class="num">' + fmtPct(row.anf_pct) + "</td>" +
                    '<td class="num">' + fmtInt(row.perdida_fisica_m3) + " m³</td>" +
                    '<td class="num">' + fmtInt(row.perdida_comercial_m3) + " m³</td>" +
                    '<td class="num">' + fmtMoney(row.perdida_economica_soles) + "</td>" +
                    '<td><span class="badge ' + badgeClass + '">' +
                        escapeHtml(semaforo) + "</span></td>" +
                "</tr>"
            );
        }).join("");
    }

    function renderSectorCards() {
        const container = document.getElementById("sector-grid");
        if (!container) {
            return;
        }
        container.innerHTML = SECTOR_ORDER.map(function (sectorId) {
            const meta = sectorMeta(sectorId);
            const stats = sectorStat(sectorId);
            const economic = sectorRow(sectorId) || {};
            const semaforo = String(economic.semaforo_sunass || "VERDE");
            const badgeClass = statusFromSemaforo(semaforo);
            const source = (SIOC_DATA.sources || {})[meta.source_id] || {};
            const ptap = (SIOC_DATA.ptaps || {})[meta.ptap_id] || {};

            const metrics = [
                ["ANF promedio", fmtPct(stats.anf_pct)],
                ["Presión media", fmtNumber(stats.presion_mca, 1) + " m.c.a."],
                ["Cloro medio", fmtNumber(stats.cloro_mg_l, 2) + " mg/L"],
                ["Turbiedad", fmtNumber(stats.turbiedad_ntu, 2) + " NTU"],
                ["Continuidad", fmtNumber(stats.continuidad_horas, 1) + " h/día"],
                ["Alertas", fmtInt(stats.alertas)]
            ];

            return (
                '<article class="glass sector-card">' +
                    '<div class="sector-card__head">' +
                        "<div>" +
                            "<h3>" + escapeHtml(SECTOR_DISPLAY[sectorId]) + "</h3>" +
                            '<p class="sector-card__zone">' + escapeHtml(meta.zone) + "</p>" +
                        "</div>" +
                        '<span class="badge ' + badgeClass + '">' +
                            escapeHtml(semaforo) + "</span>" +
                    "</div>" +
                    '<div class="sector-card__metrics">' +
                        metrics.map(function (metric) {
                            return (
                                '<div class="sector-card__metric">' +
                                    "<span>" + escapeHtml(metric[0]) + "</span>" +
                                    "<strong>" + escapeHtml(metric[1]) + "</strong>" +
                                "</div>"
                            );
                        }).join("") +
                    "</div>" +
                    '<p class="sector-card__meta">' +
                        "Fuente: <strong>" + escapeHtml(source.name || "—") + "</strong><br>" +
                        "PTAP: <strong>" + escapeHtml(ptap.name || "—") + "</strong>" +
                    "</p>" +
                    '<p class="sector-card__desc">' + escapeHtml(meta.description) + "</p>" +
                "</article>"
            );
        }).join("");
    }

    function renderAlertsTable() {
        const body = document.getElementById("alerts-table-body");
        if (!body) {
            return;
        }
        const top = SIOC_DATA.top_alerts || [];
        if (!top.length) {
            body.innerHTML =
                '<tr><td colspan="9" class="muted">Sin alertas en el periodo.</td></tr>';
            return;
        }
        body.innerHTML = top.map(function (alert) {
            const severity = SEVERITY_META[String(alert.severity)] || {
                label: String(alert.severity || "—"),
                className: "is-media"
            };
            const typeLabel = ANOMALY_LABELS[alert.anomaly_type] || alert.anomaly_type;
            return (
                "<tr>" +
                    "<td>" + escapeHtml(alert.timestamp) + "</td>" +
                    '<td class="sector-cell">' +
                        escapeHtml(SECTOR_DISPLAY[alert.sector_id] || alert.sector_name) +
                    "</td>" +
                    "<td>" + escapeHtml(typeLabel) + "</td>" +
                    '<td><span class="alert-badge ' + severity.className + '">' +
                        escapeHtml(severity.label) + "</span></td>" +
                    '<td class="num">' + fmtNumber(alert.score, 3) + "</td>" +
                    '<td class="num">' + fmtNumber(alert.caudal_lps, 1) + "</td>" +
                    '<td class="num">' + fmtNumber(alert.presion_mca, 1) + "</td>" +
                    '<td class="num">' + fmtNumber(alert.cloro_mg_l, 2) + "</td>" +
                    '<td class="num">' + fmtPct(alert.anf_pct) + "</td>" +
                "</tr>"
            );
        }).join("");
    }

    function renderAlertsMeta() {
        const meta = document.getElementById("alerts-meta");
        if (!meta) {
            return;
        }
        const total = (SIOC_DATA.anomalies || []).reduce(function (sum, row) {
            return sum + (Number(row.alertas_totales) || 0);
        }, 0);
        meta.textContent =
            fmtInt(total) + " alertas · " + SIOC_DATA.meta.days + " días";
    }

    /* ---------------------------------------------------------------------
       Chart.js — todos los lienzos son transparentes
       --------------------------------------------------------------------- */
    function showChartFallback(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !canvas.parentElement) {
            return;
        }
        const wrapper = canvas.parentElement;
        const fallback = document.createElement("div");
        fallback.className = "chart-fallback";
        fallback.textContent =
            "No se pudo cargar la librería de gráficos. Verifica la conexión a internet " +
            "y recarga la página; las tablas conservan las cifras del periodo.";
        wrapper.innerHTML = "";
        wrapper.appendChild(fallback);
    }

    function configureChartDefaults() {
        Chart.defaults.color = COLORS.muted;
        Chart.defaults.font.family =
            '"Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
        Chart.defaults.font.size = 12;
        Chart.defaults.borderColor = COLORS.grid;
        Chart.defaults.animation.duration = 700;
    }

    function tooltipConfig() {
        return {
            backgroundColor: "rgba(2, 6, 23, 0.94)",
            borderColor: "rgba(56, 189, 248, 0.55)",
            borderWidth: 1,
            titleColor: COLORS.text,
            bodyColor: COLORS.muted,
            padding: 10,
            cornerRadius: 8,
            boxPadding: 4
        };
    }

    function legendConfig() {
        return {
            labels: {
                color: COLORS.muted,
                usePointStyle: true,
                pointStyle: "circle",
                boxWidth: 8,
                boxHeight: 8,
                padding: 14,
                font: { size: 11, weight: "600" }
            }
        };
    }

    function axisConfig(options) {
        const settings = options || {};
        return {
            grid: {
                color: settings.gridColor || COLORS.grid,
                drawBorder: false,
                display: settings.showGrid !== false
            },
            border: { color: COLORS.axis },
            ticks: {
                color: COLORS.muted,
                font: { size: 11 },
                maxRotation: 0,
                autoSkip: true,
                maxTicksLimit: settings.maxTicks || 10,
                precision: settings.precision,
                callback: settings.tickCallback
            },
            title: {
                display: Boolean(settings.title),
                text: settings.title || "",
                color: COLORS.muted,
                font: { size: 11, weight: "600" }
            },
            beginAtZero: Boolean(settings.beginAtZero),
            suggestedMin: settings.suggestedMin,
            suggestedMax: settings.suggestedMax,
            stacked: Boolean(settings.stacked)
        };
    }

    function buildAnfChart() {
        const canvas = document.getElementById("chart-anf");
        if (!canvas) {
            return;
        }
        const daily = SIOC_DATA.daily || {};
        const firstSector = SECTOR_ORDER[0];
        const labels = ((daily[firstSector] || {}).labels || []).map(fmtShortDate);

        const datasets = SECTOR_ORDER.map(function (sectorId) {
            const color = SECTOR_COLORS[sectorId];
            return {
                label: SECTOR_DISPLAY[sectorId],
                data: ((daily[sectorId] || {}).anf || []),
                borderColor: color,
                backgroundColor: withAlpha(color, 0.12),
                borderWidth: 2.4,
                tension: 0.32,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointBackgroundColor: color,
                pointBorderColor: COLORS.text,
                pointBorderWidth: 1,
                fill: false,
                order: 2
            };
        });

        datasets.push({
            label: "Alerta 28%",
            data: labels.map(function () {
                return SIOC_DATA.normative.anf_alerta_amarilla_pct;
            }),
            borderColor: COLORS.amber,
            borderDash: [6, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 1
        });

        datasets.push({
            label: "Crítico 35%",
            data: labels.map(function () {
                return SIOC_DATA.normative.anf_alerta_critica_pct;
            }),
            borderColor: COLORS.coral,
            borderDash: [2, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0,
            order: 1
        });

        state.charts.anf = new Chart(canvas.getContext("2d"), {
            type: "line",
            data: { labels: labels, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: legendConfig(),
                    tooltip: Object.assign(tooltipConfig(), {
                        callbacks: {
                            label: function (context) {
                                return (
                                    context.dataset.label + ": " +
                                    fmtNumber(context.parsed.y, 1) + "%"
                                );
                            }
                        }
                    })
                },
                scales: {
                    x: axisConfig({ maxTicks: 10, gridColor: "rgba(226, 232, 240, 0.06)" }),
                    y: axisConfig({
                        suggestedMin: 15,
                        suggestedMax: 45,
                        maxTicks: 7,
                        tickCallback: function (value) {
                            return fmtNumber(value, 0) + "%";
                        }
                    })
                }
            }
        });
    }

    function buildBalanceChart() {
        const canvas = document.getElementById("chart-balance");
        if (!canvas) {
            return;
        }
        const rows = SECTOR_ORDER.map(function (sectorId) {
            return sectorRow(sectorId) || {};
        });

        state.charts.balance = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: SECTOR_ORDER.map(function (sectorId) {
                    return SECTOR_DISPLAY[sectorId];
                }),
                datasets: [
                    {
                        label: "Producido",
                        data: rows.map(function (row) {
                            return row.volumen_producido_m3;
                        }),
                        backgroundColor: withAlpha(COLORS.cyan, 0.72),
                        borderColor: COLORS.cyan,
                        borderWidth: 1,
                        borderRadius: 6,
                        maxBarThickness: 42
                    },
                    {
                        label: "Facturado",
                        data: rows.map(function (row) {
                            return row.volumen_facturado_m3;
                        }),
                        backgroundColor: withAlpha(COLORS.emerald, 0.72),
                        borderColor: COLORS.emerald,
                        borderWidth: 1,
                        borderRadius: 6,
                        maxBarThickness: 42
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: legendConfig(),
                    tooltip: Object.assign(tooltipConfig(), {
                        callbacks: {
                            label: function (context) {
                                return (
                                    context.dataset.label + ": " +
                                    fmtInt(context.parsed.y) + " m³"
                                );
                            }
                        }
                    })
                },
                scales: {
                    x: axisConfig({ showGrid: false }),
                    y: axisConfig({
                        beginAtZero: true,
                        maxTicks: 6,
                        tickCallback: function (value) {
                            return fmtInt(value / 1000) + "k";
                        }
                    })
                }
            }
        });
    }

    function buildChlorineChart() {
        const canvas = document.getElementById("chart-chlorine");
        if (!canvas) {
            return;
        }
        const labels = SECTOR_ORDER.map(function (sectorId) {
            return SECTOR_DISPLAY[sectorId];
        });
        const values = SECTOR_ORDER.map(function (sectorId) {
            return Number(sectorStat(sectorId).cloro_mg_l) || 0;
        });
        const colors = SECTOR_ORDER.map(function (sectorId) {
            return SECTOR_COLORS[sectorId];
        });
        const minimum = SIOC_DATA.normative.cloro_min_mg_l;

        state.charts.chlorine = new Chart(canvas.getContext("2d"), {
            data: {
                labels: labels,
                datasets: [
                    {
                        type: "bar",
                        label: "Cloro promedio",
                        data: values,
                        backgroundColor: colors.map(function (color) {
                            return withAlpha(color, 0.72);
                        }),
                        borderColor: colors,
                        borderWidth: 1,
                        borderRadius: 6,
                        maxBarThickness: 46
                    },
                    {
                        type: "line",
                        label: "Mínimo DIGESA " + fmtNumber(minimum, 1) + " mg/L",
                        data: labels.map(function () {
                            return minimum;
                        }),
                        borderColor: COLORS.coral,
                        borderDash: [6, 4],
                        borderWidth: 1.6,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: legendConfig(),
                    tooltip: Object.assign(tooltipConfig(), {
                        callbacks: {
                            label: function (context) {
                                return (
                                    context.dataset.label + ": " +
                                    fmtNumber(context.parsed.y, 2) + " mg/L"
                                );
                            }
                        }
                    })
                },
                scales: {
                    x: axisConfig({ showGrid: false }),
                    y: axisConfig({
                        beginAtZero: true,
                        suggestedMax: 1,
                        maxTicks: 6
                    })
                }
            }
        });
    }

    function buildAlertsChart() {
        const canvas = document.getElementById("chart-alerts");
        if (!canvas) {
            return;
        }
        const series = [
            { label: "Fugas físicas", key: "fugas_fisicas", color: COLORS.coral },
            { label: "Fraude comercial", key: "fraudes_comerciales", color: COLORS.amber },
            { label: "Cloro bajo", key: "alertas_cloro", color: COLORS.cyan },
            { label: "Turbiedad", key: "alertas_turbiedad", color: COLORS.violet },
            { label: "Presión", key: "alertas_presion", color: COLORS.emerald },
            { label: "Patrón atípico", key: "alertas_estadisticas", color: COLORS.aqua }
        ];

        const datasets = series.map(function (item) {
            return {
                label: item.label,
                data: SECTOR_ORDER.map(function (sectorId) {
                    const row = anomalyRow(sectorId) || {};
                    return Number(row[item.key]) || 0;
                }),
                backgroundColor: withAlpha(item.color, 0.78),
                borderColor: item.color,
                borderWidth: 1,
                borderRadius: 4,
                maxBarThickness: 26
            };
        });

        state.charts.alerts = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: SECTOR_ORDER.map(function (sectorId) {
                    return SECTOR_DISPLAY[sectorId];
                }),
                datasets: datasets
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: legendConfig(),
                    tooltip: Object.assign(tooltipConfig(), {
                        callbacks: {
                            label: function (context) {
                                return (
                                    context.dataset.label + ": " +
                                    fmtInt(context.parsed.x) + " alertas"
                                );
                            }
                        }
                    })
                },
                scales: {
                    x: axisConfig({
                        beginAtZero: true,
                        precision: 0,
                        stacked: true,
                        maxTicks: 8
                    }),
                    y: axisConfig({ showGrid: false, stacked: true })
                }
            }
        });
    }

    function buildRoiChart() {
        const canvas = document.getElementById("chart-roi");
        if (!canvas) {
            return;
        }
        const investment = Number(
            (document.getElementById("roi-investment") || {}).value
        ) || 45000;
        const months = Array.from({ length: 13 }, function (_, index) {
            return index;
        });

        state.charts.roi = new Chart(canvas.getContext("2d"), {
            type: "line",
            data: {
                labels: months.map(function (month) {
                    return String(month);
                }),
                datasets: [
                    {
                        label: "Ahorro acumulado",
                        data: months.map(function () {
                            return 0;
                        }),
                        borderColor: COLORS.emerald,
                        backgroundColor: withAlpha(COLORS.emerald, 0.14),
                        borderWidth: 2.8,
                        tension: 0.28,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: COLORS.emerald,
                        pointBorderColor: COLORS.text,
                        pointBorderWidth: 1,
                        fill: "origin"
                    },
                    {
                        label: "Inversión inicial",
                        data: months.map(function () {
                            return investment;
                        }),
                        borderColor: COLORS.coral,
                        borderDash: [7, 5],
                        borderWidth: 1.6,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: legendConfig(),
                    tooltip: Object.assign(tooltipConfig(), {
                        callbacks: {
                            label: function (context) {
                                return (
                                    context.dataset.label + ": " +
                                    fmtMoney(context.parsed.y)
                                );
                            }
                        }
                    })
                },
                scales: {
                    x: axisConfig({
                        title: "Meses",
                        showGrid: false,
                        maxTicks: 13,
                        maxTicksLimit: 13
                    }),
                    y: axisConfig({
                        beginAtZero: true,
                        maxTicks: 6,
                        tickCallback: function (value) {
                            if (Math.abs(value) >= 1000) {
                                return "S/ " + fmtInt(value / 1000) + "k";
                            }
                            return "S/ " + fmtInt(value);
                        }
                    })
                }
            }
        });
    }

    function initCharts() {
        if (typeof Chart === "undefined") {
            CHART_IDS.forEach(showChartFallback);
            return;
        }
        configureChartDefaults();
        safe("gráfico ANF", buildAnfChart);
        safe("gráfico balance", buildBalanceChart);
        safe("gráfico cloro", buildChlorineChart);
        safe("gráfico alertas", buildAlertsChart);
        safe("gráfico ROI", buildRoiChart);
    }

    /* ---------------------------------------------------------------------
       Mapa Leaflet de los sectores de Ilo
       --------------------------------------------------------------------- */
    function buildMapPopup(sectorId) {
        const meta = sectorMeta(sectorId);
        const stats = sectorStat(sectorId);
        const economic = sectorRow(sectorId) || {};
        const source = (SIOC_DATA.sources || {})[meta.source_id] || {};
        const ptap = (SIOC_DATA.ptaps || {})[meta.ptap_id] || {};
        const semaforo = String(economic.semaforo_sunass || "VERDE");

        return (
            '<div class="map-popup">' +
                "<h4>" + escapeHtml(SECTOR_DISPLAY[sectorId]) + "</h4>" +
                '<p class="map-popup__zone">' + escapeHtml(meta.zone) + "</p>" +
                "<dl>" +
                    "<dt>ANF promedio</dt><dd>" + fmtPct(stats.anf_pct) + "</dd>" +
                    "<dt>Presión media</dt><dd>" + fmtNumber(stats.presion_mca, 1) + " m.c.a.</dd>" +
                    "<dt>Cloro medio</dt><dd>" + fmtNumber(stats.cloro_mg_l, 2) + " mg/L</dd>" +
                    "<dt>Continuidad</dt><dd>" + fmtNumber(stats.continuidad_horas, 1) + " h/día</dd>" +
                    "<dt>Alertas IA</dt><dd>" + fmtInt(stats.alertas) + "</dd>" +
                    "<dt>Semáforo</dt><dd>" + escapeHtml(semaforo) + "</dd>" +
                    "<dt>Fuente</dt><dd>" + escapeHtml(source.name || "—") + "</dd>" +
                    "<dt>PTAP</dt><dd>" + escapeHtml(ptap.name || "—") + "</dd>" +
                "</dl>" +
                '<a class="map-popup__link" href="#simulador">Simular reducción de ANF →</a>' +
            "</div>"
        );
    }

    function buildMapLegend() {
        return (
            "<strong>ANF por sector</strong>" +
            '<div class="map-legend__item"><span class="map-legend__dot" style="background:' +
                COLORS.emerald + '"></span>≤ ' +
                fmtPct(SIOC_DATA.normative.anf_alerta_amarilla_pct, 0) + " · meta</div>" +
            '<div class="map-legend__item"><span class="map-legend__dot" style="background:' +
                COLORS.amber + '"></span>> ' +
                fmtPct(SIOC_DATA.normative.anf_alerta_amarilla_pct, 0) + " · alerta</div>" +
            '<div class="map-legend__item"><span class="map-legend__dot" style="background:' +
                COLORS.coral + '"></span>> ' +
                fmtPct(SIOC_DATA.normative.anf_alerta_critica_pct, 0) + " · crítica</div>"
        );
    }

    function initMap() {
        const mapElement = document.getElementById("map");
        const mapShell = document.getElementById("map-shell");
        if (!mapElement) {
            return;
        }

        if (typeof L === "undefined") {
            mapElement.innerHTML =
                '<div class="map-fallback"><strong>Mapa no disponible sin conexión.</strong><br>' +
                "No se pudo cargar Leaflet. Las tarjetas de los sectores que aparecen " +
                "debajo conservan la información operativa del periodo.</div>";
            if (mapShell) {
                mapShell.classList.add("is-offline");
            }
            return;
        }

        const city = SIOC_DATA.meta.city;
        const map = L.map(mapElement, {
            center: [city.lat, city.lon],
            zoom: 13,
            minZoom: 10,
            maxZoom: 16,
            scrollWheelZoom: false,
            zoomControl: true
        });
        state.map = map;

        L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            {
                maxZoom: 16,
                attribution:
                    'Tiles &copy; <a href="https://www.esri.com/" ' +
                    'target="_blank" rel="noopener noreferrer">Esri</a> · ' +
                    'HERE · Garmin · &copy; ' +
                    '<a href="https://www.openstreetmap.org/copyright" ' +
                    'target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'
            }
        ).addTo(map);

        L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            {
                maxZoom: 16,
                pane: "overlayPane",
                opacity: 0.9
            }
        ).addTo(map);

        const bounds = [];
        const permanentTooltips = window.matchMedia("(min-width: 721px)").matches;

        SECTOR_ORDER.forEach(function (sectorId) {
            const meta = sectorMeta(sectorId);
            const stats = sectorStat(sectorId);
            if (!meta.lat || !meta.lon) {
                return;
            }
            const color = anfColor(stats.anf_pct);
            const point = [meta.lat, meta.lon];
            bounds.push(point);

            const marker = L.circleMarker(point, {
                radius: 15,
                color: COLORS.text,
                weight: 2,
                opacity: 0.95,
                fillColor: color,
                fillOpacity: 0.88
            }).addTo(map);

            marker.bindPopup(buildMapPopup(sectorId), {
                maxWidth: 310,
                autoPanPadding: [24, 24]
            });

            marker.bindTooltip(SECTOR_DISPLAY[sectorId], {
                permanent: permanentTooltips,
                direction: "top",
                offset: [0, -12],
                className: "sector-tooltip"
            });

            marker.on("mouseover", function () {
                marker.setStyle({ radius: 18, weight: 3 });
            });
            marker.on("mouseout", function () {
                marker.setStyle({ radius: 15, weight: 2 });
            });
        });

        if (bounds.length) {
            map.fitBounds(L.latLngBounds(bounds), {
                padding: [60, 60],
                maxZoom: 13
            });
        }

        const legend = L.control({ position: "topright" });
        legend.onAdd = function () {
            const div = L.DomUtil.create("div", "map-legend");
            div.innerHTML = buildMapLegend();
            L.DomEvent.disableClickPropagation(div);
            L.DomEvent.disableScrollPropagation(div);
            return div;
        };
        legend.addTo(map);

        // El mapa vive dentro de tarjetas glass: recalcular tras el layout.
        window.setTimeout(function () {
            map.invalidateSize();
        }, 300);

        let resizeTimer = null;
        window.addEventListener("resize", function () {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(function () {
                map.invalidateSize();
            }, 180);
        });
    }

    /* ---------------------------------------------------------------------
       Calculadora de ROI / ANF
       --------------------------------------------------------------------- */
    function computeRoi(anfM3, reductionPct, investment) {
        const rate = Number(SIOC_DATA.tariffs.tarifa_media_ponderada);
        const recovered = anfM3 * (reductionPct / 100);
        const monthlySaving = recovered * rate;
        const annualSaving = monthlySaving * 12;
        const payback = monthlySaving > 0 ? investment / monthlySaving : Infinity;

        let van = -investment;
        for (let month = 1; month <= 12; month += 1) {
            van += monthlySaving / Math.pow(1 + MONTHLY_DISCOUNT_RATE, month);
        }

        const roi = investment > 0 ? ((annualSaving - investment) / investment) * 100 : 0;
        const residualPct =
            Number(SIOC_DATA.economic.anf_porcentaje) *
            (1 - reductionPct / 100);

        return {
            anfM3: anfM3,
            reductionPct: reductionPct,
            investment: investment,
            recovered: recovered,
            monthlySaving: monthlySaving,
            annualSaving: annualSaving,
            payback: payback,
            van: van,
            roi: roi,
            residualPct: residualPct
        };
    }

    function renderRoiTiles(roi) {
        const container = document.getElementById("roi-grid");
        if (!container) {
            return;
        }
        const paybackLabel = Number.isFinite(roi.payback)
            ? fmtNumber(roi.payback, 1) + " meses"
            : "No recuperable";
        const paybackStatus = Number.isFinite(roi.payback)
            ? roi.payback <= 18
                ? "ok"
                : "warn"
            : "critical";

        const tiles = [
            {
                label: "Volumen recuperado",
                value: fmtInt(roi.recovered) + " m³",
                delta: "por mes",
                status: "ok"
            },
            {
                label: "Ahorro mensual",
                value: fmtMoney(roi.monthlySaving),
                delta: "Anual: " + fmtMoney(roi.annualSaving),
                status: "ok"
            },
            {
                label: "Payback",
                value: paybackLabel,
                delta: "Periodo de recuperación",
                status: paybackStatus
            },
            {
                label: "VAN 12 meses",
                value: fmtMoney(roi.van),
                delta: "ROI: " + fmtPct(roi.roi),
                status: roi.van > 0 ? "ok" : "critical"
            }
        ];

        container.innerHTML = tiles.map(function (tile) {
            return (
                '<article class="glass roi-tile is-' + tile.status + '">' +
                    '<span class="roi-tile__label">' + escapeHtml(tile.label) + "</span>" +
                    '<span class="roi-tile__value">' + escapeHtml(tile.value) + "</span>" +
                    '<span class="roi-tile__delta">' + escapeHtml(tile.delta) + "</span>" +
                "</article>"
            );
        }).join("");
    }

    function renderRoiVerdict(roi) {
        const box = document.getElementById("roi-verdict");
        const text = document.getElementById("roi-verdict-text");
        if (!text) {
            return;
        }

        const residualStatus = statusFromAnf(roi.residualPct);
        const residualLabel = { ok: "VERDE", warn: "AMARILLO", critical: "ROJO" }[
            residualStatus
        ];
        const updatedThisPeriod = roi.reductionPct > 0
            ? "Con la reducción de " + fmtNumber(roi.reductionPct, 0) + "%, " +
              "el ANF estimado pasaría de " +
              fmtPct(SIOC_DATA.economic.anf_porcentaje) + " a " +
              fmtPct(roi.residualPct) + ", en semáforo SUNASS " + residualLabel + "."
            : "Sin reducción, el ANF se mantiene en " +
              fmtPct(SIOC_DATA.economic.anf_porcentaje) + " (semáforo " +
              SIOC_DATA.economic.semaforo_sunass + ").";

        let status = "critical";
        let icon = "×";
        let conclusion;

        if (roi.van > 0 && Number.isFinite(roi.payback) && roi.payback <= 12) {
            status = "ok";
            icon = "✓";
            conclusion =
                "El plan es económicamente viable: recupera la inversión en " +
                fmtNumber(roi.payback, 1) + " meses y el VAN a 12 meses es " +
                fmtMoney(roi.van) + ". " + updatedThisPeriod;
        } else if (roi.van > 0) {
            status = "warn";
            icon = "!";
            conclusion =
                "El plan crea valor (VAN " + fmtMoney(roi.van) +
                "), aunque la recuperación toma " + fmtNumber(roi.payback, 1) +
                " meses. " + updatedThisPeriod;
        } else {
            conclusion =
                "Con los parámetros actuales el plan no recupera la inversión en " +
                "12 meses (VAN " + fmtMoney(roi.van) +
                "). Amplía la reducción objetivo o reduce el costo de intervención. " +
                updatedThisPeriod;
        }

        text.innerHTML =
            "<strong>Veredicto:</strong> " + escapeHtml(conclusion);

        if (box) {
            box.classList.remove("is-ok", "is-warn", "is-critical");
            box.classList.add("is-" + status);
            const iconElement = box.querySelector(".verdict__icon");
            if (iconElement) {
                iconElement.textContent = icon;
            }
        }
    }

    function updateRoiChart(roi) {
        const chart = state.charts.roi;
        if (!chart) {
            return;
        }
        const cumulative = Array.from({ length: 13 }, function (_, month) {
            return roi.monthlySaving * month;
        });
        chart.data.datasets[0].data = cumulative;
        chart.data.datasets[1].data = cumulative.map(function () {
            return roi.investment;
        });
        chart.update();
    }

    function readRoiInputs() {
        const anfInput = document.getElementById("roi-anf");
        const reductionInput = document.getElementById("roi-reduction");
        const investmentInput = document.getElementById("roi-investment");

        const anf = Math.max(0, Number(anfInput && anfInput.value) || 0);
        const reduction = Math.min(
            80,
            Math.max(5, Number(reductionInput && reductionInput.value) || 5)
        );
        const investment = Math.max(
            5000,
            Number(investmentInput && investmentInput.value) || 45000
        );

        return { anf: anf, reduction: reduction, investment: investment };
    }

    function updateCalculator() {
        const inputs = readRoiInputs();
        const reductionOut = document.getElementById("roi-reduction-out");
        const investmentOut = document.getElementById("roi-investment-out");
        if (reductionOut) {
            reductionOut.textContent = fmtNumber(inputs.reduction, 0) + "%";
        }
        if (investmentOut) {
            investmentOut.textContent = fmtMoney(inputs.investment);
        }

        const roi = computeRoi(inputs.anf, inputs.reduction, inputs.investment);
        state.roi = roi;
        renderRoiTiles(roi);
        renderRoiVerdict(roi);
        updateRoiChart(roi);
    }

    function bindCalculator() {
        const form = document.getElementById("roi-form");
        const anfInput = document.getElementById("roi-anf");
        const reductionInput = document.getElementById("roi-reduction");
        const investmentInput = document.getElementById("roi-investment");

        if (!anfInput || !reductionInput || !investmentInput) {
            return;
        }

        if (form) {
            form.addEventListener("submit", function (event) {
                event.preventDefault();
            });
        }

        [anfInput, reductionInput, investmentInput].forEach(function (input) {
            input.addEventListener("input", updateCalculator);
            input.addEventListener("change", updateCalculator);
        });

        anfInput.addEventListener("blur", function () {
            const value = Math.min(
                1000000,
                Math.max(0, Number(anfInput.value) || 0)
            );
            anfInput.value = String(Math.round(value));
            updateCalculator();
        });
    }

    /* ---------------------------------------------------------------------
       Arranque
       --------------------------------------------------------------------- */
    function boot() {
        if (state.booted) {
            return;
        }
        state.booted = true;

        safe("cabecera", renderHeaderMeta);
        safe("KPIs", renderKpis);
        safe("tabla sectorial", renderSectorTable);
        safe("tarjetas sectoriales", renderSectorCards);
        safe("tabla de alertas", renderAlertsTable);
        safe("metadatos de alertas", renderAlertsMeta);
        safe("mapa", initMap);
        safe("gráficos", initCharts);
        safe("calculadora", bindCalculator);
        safe("cálculo inicial", updateCalculator);
        safe("botón de fondo", bindBackgroundButton);

        applyRandomBackground();
    }

    document.addEventListener("DOMContentLoaded", boot);

    // Fondo aleatorio en cada recarga (window.onload), con respaldo si algún
    // recurso externo demora la carga de la página.
    window.onload = function () {
        if (!state.booted) {
            boot();
        } else if (!state.bgInitialized) {
            applyRandomBackground();
        }
    };
})();
