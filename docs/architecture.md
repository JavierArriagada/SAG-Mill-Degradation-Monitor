# Arquitectura del sistema

---

## 1. Visión general — Capas del sistema

El sistema está organizado en cuatro capas horizontales. Cada capa depende solo de las que están por debajo de ella.

```mermaid
graph TD
    subgraph PRES["Presentación  (Dash / Plotly)"]
        P1[Overview]
        P2[Equipment]
        P3[Alerts]
        P4[Trends]
    end

    subgraph CB["Callbacks  (lógica reactiva)"]
        C1[navigation.py]
        C2[equipment.py]
        C3[alerts.py]
        C4[trends.py]
    end

    subgraph AN["Analítica"]
        A1[health_index.py]
        A2[anomaly.py]
        A3[thresholds.py]
    end

    subgraph DATA["Datos"]
        D1[simulator.py]
        D2[store.py  — SQLite]
        D3[models.py  — Pydantic v2]
        D4[degradation.py]
    end

    subgraph CFG["Configuración"]
        F1[settings.py  — env vars]
        F2[equipment.py  — umbrales ISO]
        F3[alerts.py  — severidades]
    end

    PRES --> CB --> AN --> DATA --> CFG
```

---

## 2. Flujo de datos completo

Desde la generación del dato en el simulador hasta su visualización en el navegador.

```mermaid
sequenceDiagram
    participant BOOT as app.py (startup)
    participant SIM as simulator.py
    participant STORE as store.py (SQLite)
    participant ANAL as analytics/
    participant DASH as Dash callbacks
    participant UI as Navegador

    BOOT->>SIM: generate_history(seed=42, days=90)
    SIM-->>BOOT: dict[equipment_id → list[SensorReading]]
    BOOT->>ANAL: compute_health_summary(reading) × N
    ANAL-->>BOOT: list[HealthSummary]
    BOOT->>STORE: insert_readings() + insert_alerts()
    STORE-->>BOOT: OK

    loop Cada 30 segundos (dcc.Interval)
        DASH->>SIM: generate_realtime_reading(equipment_id)
        SIM-->>DASH: SensorReading
        DASH->>ANAL: compute_health_summary(reading)
        ANAL-->>DASH: HealthSummary
        DASH->>STORE: insert_reading() + check_thresholds()
        STORE-->>DASH: latest data
        DASH-->>UI: figuras Plotly actualizadas
    end
```

---

## 3. Modelo de dominio

Modelos Pydantic v2 que representan todas las entidades del sistema.

```mermaid
classDiagram
    class SensorReading {
        +str equipment_id
        +datetime timestamp
        +float vibration_mms
        +float bearing_temp_c
        +float hydraulic_pressure_bar
        +float power_kw
        +float load_pct
        +float liner_wear_pct
        +float seal_condition_pct
        +float throughput_tph
        +float health_index
        +DegradationMode degradation_mode
    }

    class HealthSummary {
        +str equipment_id
        +datetime timestamp
        +float health_index
        +float vibration_score
        +float thermal_score
        +float pressure_score
        +float power_score
        +float predicted_rul_days
        +int active_alerts
        +DegradationMode degradation_mode
    }

    class Alert {
        +str id
        +datetime timestamp
        +str equipment_id
        +str severity
        +str category
        +str variable
        +float value
        +float threshold
        +str message
        +bool acknowledged
    }

    class DegradationMode {
        <<enumeration>>
        NORMAL
        BEARING
        LINER
        HYDRAULIC
        MISALIGNMENT
    }

    SensorReading --> DegradationMode
    HealthSummary --> DegradationMode
    SensorReading ..> HealthSummary : compute_health_summary()
    SensorReading ..> Alert : derive_alerts()
```

---

## 4. Estructura de módulos

```mermaid
graph LR
    subgraph root["/ (raíz)"]
        APP[app.py]
    end

    subgraph config["config/"]
        CFG_S[settings.py]
        CFG_E[equipment.py]
        CFG_A[alerts.py]
    end

    subgraph src_data["src/data/"]
        MOD[models.py]
        SIM[simulator.py]
        DEG[degradation.py]
        STO[store.py]
    end

    subgraph src_ana["src/analytics/"]
        HI[health_index.py]
        ANO[anomaly.py]
        THR[thresholds.py]
    end

    subgraph src_lay["src/layout/"]
        NAV[navbar.py]
        SID[sidebar.py]
        MAIN[main.py]
        KPI[components/kpi_card.py]
        GAU[components/health_gauge.py]
        BAD[components/alert_badge.py]
    end

    subgraph src_pg["src/pages/"]
        OV[overview.py]
        EQ[equipment.py]
        AL[alerts.py]
        TR[trends.py]
    end

    subgraph src_cb["src/callbacks/"]
        CB_N[navigation.py]
        CB_E[equipment.py]
        CB_A[alerts.py]
        CB_T[trends.py]
    end

    subgraph src_i18["src/i18n/"]
        TRANS[translator.py]
        ES[locales/es.json]
        EN[locales/en.json]
    end

    APP --> config & src_data & src_ana & src_lay & src_cb
    src_cb --> src_pg & src_ana & src_data
    src_pg --> src_lay
    src_ana --> config & src_data
    SIM --> DEG & MOD & config
    STO --> MOD
```

---

## 5. Arranque de la aplicación

Secuencia exacta que ocurre cuando `app.py` se ejecuta o gunicorn lo importa.

```mermaid
flowchart TD
    A([Inicio: gunicorn / python app.py]) --> B[initialize_db]
    B --> C{¿Tabla vacía?}
    C -- Sí --> D[generate_history<br>seed=42, days=90]
    D --> E[derive_alerts<br>por equipo]
    E --> F[insert_readings + insert_alerts]
    F --> G[Dash app creada<br>tema DARKLY]
    C -- No --> G
    G --> H[create_layout]
    H --> I[register callbacks<br>navigation / equipment<br>alerts / trends]
    I --> J([Servidor listo en :8050 / :8080])
```

---

## 6. Arquitectura de despliegue

```mermaid
graph TD
    DEV[Developer<br>máquina local] -->|git push main| GH[GitHub<br>repositorio]

    subgraph CI["GitHub Actions CI"]
        Q[quality<br>ruff + mypy]
        T[test<br>pytest + coverage]
        D[docker build]
        DEP[deploy<br>doctl]
        Q --> T --> D --> DEP
    end

    GH --> CI

    subgraph DO["DigitalOcean App Platform"]
        BUILD[Build container<br>pip install]
        APP[gunicorn<br>app:server]
        DB[(SQLite<br>local)]
        BUILD --> APP --> DB
    end

    DEP -->|doctl apps create-deployment| DO

    USER[Usuario final<br>navegador] -->|HTTPS| APP
```

---

## 7. Equipos y variables sensoriales

```mermaid
graph LR
    subgraph SAG01["SAG-01 — Molino SAG  (2 200 t/h)"]
        S1[vibration_mms]
        S2[bearing_temp_c]
        S3[hydraulic_pressure_bar]
        S4[power_kw]
        S5[load_pct]
        S6[liner_wear_pct]
        S7[seal_condition_pct]
        DMODES_SAG["Modos: bearing · liner · hydraulic"]
    end

    subgraph BALL01["BALL-01 — Molino de Bolas  (1 800 t/h)"]
        B1[vibration_mms]
        B2[bearing_temp_c]
        B3[hydraulic_pressure_bar]
        B4[power_kw]
        B5[load_pct]
        DMODES_BALL["Modos: bearing · misalignment"]
    end

    SAG01 & BALL01 --> HI_ENGINE[Health Index Engine]
    HI_ENGINE --> DASHBOARD[Dashboard]
```
