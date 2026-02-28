# Motor analítico

Documentación de los tres algoritmos centrales del sistema: Índice de Salud (HI), Vida Útil Remanente (RUL) y detección de anomalías por Z-score.

---

## 1. Índice de Salud (HI)

### Definición

El HI es un escalar ∈ [0, 100] que resume el estado de un equipo en un instante dado. 100 = condición perfecta, 0 = falla inminente. Sigue el marco de ISO 13381 para monitoreo de condición y pronóstico.

### Fórmula

```
HI = 0.30 · S_vib  +  0.25 · S_temp  +  0.20 · S_pres  +  0.25 · S_pow
```

### Pipeline de cálculo

```mermaid
flowchart TD
    SR([SensorReading]) --> VIB[_vibration_score<br>vibration_mms]
    SR --> TMP[_thermal_score<br>bearing_temp_c]
    SR --> PRS[_pressure_score<br>hydraulic_pressure_bar]
    SR --> PWR[_power_score<br>power_kw]

    VIB -->|× 0.30| SUM
    TMP -->|× 0.25| SUM
    PRS -->|× 0.20| SUM
    PWR -->|× 0.25| SUM

    SUM[Suma ponderada] --> CLIP[clip 0–100]
    CLIP --> HS([HealthSummary<br>health_index = HI])
```

---

### Sub-índice de vibración — ISO 10816

```mermaid
flowchart TD
    V([vibration_mms]) --> ZA{≤ zone_a?}
    ZA -- Sí --> RA["100 − (vib/zone_a)×15<br>Rango: 85–100"]
    ZA -- No --> ZB{≤ zone_b?}
    ZB -- Sí --> RB["85 − t×20<br>Rango: 65–85"]
    ZB -- No --> ZC{≤ zone_c?}
    ZC -- Sí --> RC["65 − t×35<br>Rango: 30–65"]
    ZC -- No --> RD["30 − t×30<br>Rango: 0–30"]

    RA & RB & RC & RD --> SVIB([S_vib ∈ 0–100])
```

**Zonas ISO 10816 por equipo:**

| Zona | SAG-01 (mm/s) | BALL-01 (mm/s) | Score aprox. |
|---|---|---|---|
| A — Óptimo | ≤ 2.3 | ≤ 1.8 | 85–100 |
| B — Aceptable | ≤ 4.5 | ≤ 3.5 | 65–85 |
| C — Insatisfactorio | ≤ 7.1 | ≤ 5.6 | 30–65 |
| D — Peligro | > 7.1 | > 5.6 | 0–30 |

---

### Sub-índice térmico

```mermaid
flowchart TD
    T([bearing_temp_c]) --> TW{≤ warning?}
    TW -- Sí --> RT["100 − t×15<br>Rango: 85–100<br>baseline=20°C"]
    TW -- No --> TA{≤ alert?}
    TA -- Sí --> RA2["85 − t×35<br>Rango: 50–85"]
    TA -- No --> TC{≤ critical?}
    TC -- Sí --> RC2["50 − t×40<br>Rango: 10–50"]
    TC -- No --> RD2["max(0, 10 − excess×2)<br>Rango: 0–10"]

    RT & RA2 & RC2 & RD2 --> STEMP([S_temp ∈ 0–100])
```

**Umbrales por equipo:**

| Nivel | SAG-01 (°C) | BALL-01 (°C) |
|---|---|---|
| Warning | 72 | 68 |
| Alert | 82 | 78 |
| Critical | 92 | 88 |

---

### Sub-índice de presión hidráulica

```mermaid
flowchart TD
    P([hydraulic_pressure_bar]) --> PIN{p_min ≤ P ≤ p_max?}
    PIN -- Sí --> ROK["100 − t×10<br>penaliza dist. del punto medio"]
    PIN -- No --> PLOW{P < p_min?}
    PLOW -- Sí --> RLOW["max(0, 90 − drop×150)<br>baja presión"]
    PLOW -- No --> PHIGH{P ≤ critical_high?}
    PHIGH -- Sí --> RHIGH["90 − t×60<br>sobrepresión"]
    PHIGH -- No --> RCRIT["0<br>crítico"]

    ROK & RLOW & RHIGH & RCRIT --> SPRES([S_pres ∈ 0–100])
```

**Rangos operativos:**

| Límite | SAG-01 (bar) | BALL-01 (bar) |
|---|---|---|
| Mínimo | 120 | 80 |
| Máximo | 180 | 140 |
| Crítico alto | 195 | 155 |

---

### Sub-índice de potencia

```mermaid
flowchart TD
    W([power_kw]) --> WLO{W < p_min?}
    WLO -- Sí --> RLO["max(0, 80 − t×120)<br>bajo consumo"]
    WLO -- No --> WNO{W ≤ nominal×1.05?}
    WNO -- Sí --> RNO["100<br>zona nominal"]
    WNO -- No --> WMX{W ≤ p_max?}
    WMX -- Sí --> RMX["100 − t×25<br>sobre nominal"]
    WMX -- No --> ROV["max(0, 75 − excess×150)<br>sobre máximo"]

    RLO & RNO & RMX & ROV --> SPOW([S_pow ∈ 0–100])
```

**Potencias nominales:**

| Parámetro | SAG-01 (kW) | BALL-01 (kW) |
|---|---|---|
| Mínimo | 8 000 | 3 000 |
| Nominal | 13 500 | 6 500 |
| Máximo | 15 000 | 7 500 |

---

## 2. Vida Útil Remanente (RUL)

### Definición

Estimación en días hasta que el HI alcanza el umbral crítico de 20. Se calcula mediante extrapolación lineal de la tendencia reciente del HI.

### Algoritmo

```mermaid
flowchart TD
    HS([Serie HI histórica]) --> WIN["Ventana últimas 48 h<br>(o toda la serie si es menor)"]
    WIN --> FIT["Regresión lineal<br>coeffs = polyfit(x, y, 1)<br>slope = coeff[0]"]
    FIT --> CHK{slope ≥ 0?}
    CHK -- Sí --> STABLE([Retorna None<br>'tendencia estable o mejorando'])
    CHK -- No --> CURR[current_hi = último valor]
    CURR --> CRIT{current_hi ≤ 20?}
    CRIT -- Sí --> ZERO([Retorna 0.0<br>'ya en zona crítica'])
    CRIT -- No --> CALC["hours = (current_hi − 20) / |slope|<br>rul_days = hours / 24"]
    CALC --> ROUND([Retorna rul_days redondeado a 1 decimal])
```

### Parámetros

| Parámetro | Valor | Descripción |
|---|---|---|
| `window_hours` | 48 | Horas de historia usadas para la regresión |
| `critical_threshold` | 20 | HI mínimo antes de considerar falla |
| `min_points` | 4 | Mínimo de puntos para calcular (evita ruido) |

### Interpretación

```mermaid
graph LR
    subgraph HI["HI a lo largo del tiempo"]
        H100["100 (nuevo)"] -->|degradación| H80["80"] -->|degradación| H50["50"] -->|degradación| H20["20 ← crítico"] -->|falla| H0["0"]
    end

    H50 -->|extrapolación lineal| RUL["RUL = X días<br>hasta HI=20"]
```

---

## 3. Detección de anomalías

### Definición

Z-score rodante por variable para identificar lecturas estadísticamente inusuales sin depender de umbrales fijos. Complementa el sistema de alertas basado en umbrales ISO.

### Fórmula

```
z(t) = (x(t) − μ_ventana(t)) / σ_ventana(t)

anomalía si |z(t)| > 2.5
```

### Pipeline

```mermaid
flowchart TD
    SER([Serie temporal<br>por variable]) --> ROLL["rolling window = 24 h<br>min_periods = 4"]
    ROLL --> MEAN["μ_t = media rodante"]
    ROLL --> STD["σ_t = desviación estándar rodante<br>(0 → NaN para evitar división)"]
    MEAN & STD --> ZSCORE["z_t = (x_t − μ_t) / σ_t"]
    ZSCORE --> MASK{"|z_t| > 2.5?"}
    MASK -- Sí --> ANO([anomaly = True])
    MASK -- No --> NORM([anomaly = False])
    ANO & NORM --> OUT["DataFrame con columnas:<br>{variable}_zscore<br>{variable}_anomaly"]
```

### Detección de períodos

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Anomaly : |z| > 2.5
    Anomaly --> Normal : |z| ≤ 2.5
    Anomaly --> Anomaly : |z| > 2.5<br>(acumula peak_z)

    Normal : anomaly = False
    Anomaly : anomaly = True<br>track peak_zscore

    Normal --> [*]
```

La función `get_anomaly_periods()` extrae períodos discretos con `start`, `end` y `peak_zscore` — usados para sombrear regiones en los gráficos de tendencias.

### Parámetros

| Parámetro | Valor | Descripción |
|---|---|---|
| `window` | 24 | Tamaño de ventana rodante en observaciones (horas) |
| `min_periods` | 4 | Mínimo de obs. para calcular μ y σ |
| `threshold` | 2.5 | Umbral de Z-score para declarar anomalía |

---

## 4. Simulador de datos

El simulador genera historia reproducible con eventos de degradación realistas.

### Arquitectura del simulador

```mermaid
flowchart TD
    SEED["SIMULATION_SEED = 42<br>np.random.default_rng(seed)"] --> PLAN

    PLAN["_plan_events<br>1–3 eventos por equipo<br>dentro del historial"] --> EVENTS

    subgraph EVENTS["DegradationEvents"]
        EV1["bearing<br>start_hour: aleatorio<br>duration: 48–240 h<br>severity: 0.4–0.95"]
        EV2["liner / hydraulic<br>(solo SAG-01)"]
        EV3["misalignment<br>(solo BALL-01)"]
    end

    EVENTS --> GEN["Genera N=days×24 lecturas<br>por equipo"]

    subgraph MODES["Funciones de degradación"]
        BD["bearing_degradation(t)<br>vib ↑, temp ↑"]
        LD["liner_degradation(t)<br>pow ↑, load ↑, wear ↑"]
        HD["hydraulic_degradation(t)<br>pres fluctúa"]
        MD["misalignment_degradation(t)<br>vib ↑ patrón cíclico"]
    end

    GEN --> MODES --> OUT["list[SensorReading]<br>con health_index calculado"]
```

### Parámetros del simulador

| Parámetro | Valor | Descripción |
|---|---|---|
| `SIMULATION_SEED` | 42 | Semilla para reproducibilidad |
| `HISTORY_DAYS` | 90 | Días de historia a generar |
| Eventos por equipo | 1–3 | Degradaciones embebidas en el historial |
| Duración evento | 48–240 h | 2–10 días de degradación continua |
| Severidad pico | 0.4–0.95 | Qué tan grave llega el evento |
| Noise σ (vibración) | 0.15 mm/s SAG | Ruido gaussiano sobre baseline |

---

## 5. Sistema de alertas

```mermaid
flowchart TD
    RD([SensorReading]) --> CHK{"Para cada variable:<br>vibration_mms<br>bearing_temp_c<br>hydraulic_pressure_bar"}

    CHK --> CMP1{valor > alert_thresh?}
    CMP1 -- Sí --> CRIT["severity = CRITICAL<br>🔴"]
    CMP1 -- No --> CMP2{valor > warn_thresh?}
    CMP2 -- Sí --> WARN["severity = WARNING<br>🟡"]
    CMP2 -- No --> CLEAR[Sin alerta<br>clear in_alert flag]

    CRIT & WARN --> DEDUP{¿ya en alerta<br>para esta variable?}
    DEDUP -- No --> EMIT["emit Alert<br>(deduplica: una por cruce)"]
    DEDUP -- Sí --> SKIP[Skip]

    EMIT --> DB[(SQLite<br>alerts)]
```

**Severidades disponibles:**

| Severidad | Color | Umbral |
|---|---|---|
| `info` | #58a6ff azul | Informativo |
| `warning` | #e8a020 amarillo | zone_b / temp warning |
| `alert` | #f0883e naranja | zone_c / temp alert |
| `critical` | #da3633 rojo | zone_d / temp critical |
