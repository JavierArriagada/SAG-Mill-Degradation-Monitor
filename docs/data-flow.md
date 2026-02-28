# Arquitectura de datos y flujo de procesamiento

Documentación exhaustiva de los dos pipelines de datos del sistema — el pipeline batch de inicialización y el pipeline de tiempo real — con énfasis en las decisiones de ingeniería de datos.

---

## 1. Visión general: dos pipelines

El sistema tiene una arquitectura de datos de **dos velocidades** (inspirada en Lambda Architecture):

```mermaid
graph TD
    subgraph BATCH["Pipeline Batch — una sola vez al arrancar"]
        direction LR
        B1["generate_history\n90 días × 24 h × 2 equipos\n= 4 320 lecturas/equipo"] --> B2["compute_health_summary\n× 4 320 veces por equipo"] --> B3["insert_readings\nBulk INSERT — executemany"] --> B4["derive_alerts\nstate machine sobre la lista"] --> B5["insert_alerts\nINSERT OR IGNORE"]
    end

    subgraph STREAM["Pipeline Tiempo Real — cada 30 segundos"]
        direction LR
        S1["dcc.Interval\ntrigger del navegador"] --> S2["generate_realtime_reading\npor equipo"] --> S3["compute_health_summary\n× 1 por equipo"] --> S4["insert_readings\n2 filas"] --> S5["query SQLite\nget_readings + get_latest"] --> S6["serve Plotly\nal navegador"]
    end

    BATCH -->|"SQLite con 8 640 filas\ncomo punto de partida"| STREAM
```

---

## 2. Pipeline Batch — Inicialización

### 2.1 Punto de entrada

`initialize_db()` en `store.py` es llamado una sola vez desde `app.py` al arrancar. Es **idempotente**: si la tabla ya tiene filas, no hace nada.

```python
# app.py
initialize_db()   # ← esta línea desencadena todo el pipeline batch
```

### 2.2 Paso 1 — `generate_history()`: generación vectorizada por equipo

```mermaid
flowchart TD
    SEED["rng = np.random.default_rng(seed=42)\nreproducible en cada arranque"] --> TIME

    TIME["Línea de tiempo:\nend_ts = ahora UTC (minutos truncados)\nstart_ts = end_ts − 90 días\ntimestamps = [start_ts + h×1h for h in range(2160)]"]

    TIME --> PLAN_SAG["_plan_events('SAG-01')\n1–3 DegradationEvents\nrng.integers + rng.choice"]
    TIME --> PLAN_BALL["_plan_events('BALL-01')\n1–3 DegradationEvents"]

    PLAN_SAG --> GEN_SAG
    PLAN_BALL --> GEN_BALL

    subgraph GEN_SAG["SAG-01: 2 160 lecturas"]
        SAG_LOOP["for h in range(2160):\n    _generate_sag_reading(h, timestamps[h], events, rng)"]
    end

    subgraph GEN_BALL["BALL-01: 2 160 lecturas"]
        BALL_LOOP["for h in range(2160):\n    _generate_ball_reading(h, timestamps[h], events, rng)"]
    end

    GEN_SAG & GEN_BALL --> OUT["dict[\n  'SAG-01': list[SensorReading] ×2160,\n  'BALL-01': list[SensorReading] ×2160\n]"]
```

**Decisión clave — loops Python vs NumPy vectorizado:**

El generador usa loops Python (`for h in range(2160)`) en lugar de operaciones vectorizadas de NumPy porque cada lectura depende de qué eventos de degradación están activos en `h`. La condición `_degradation_progress(h, event)` no es trivialmente vectorizable y mantener la claridad del modelo físico por hora era prioritario sobre la velocidad de generación (que ocurre una sola vez).

---

### 2.3 Paso 2 — `compute_health_summary(reading) × N`: el loop central

Este es el núcleo del pipeline batch. Por cada lectura generada, se calcula su Índice de Salud y se escribe de vuelta en el objeto:

```python
# store.py — initialize_db()
for equipment_id, reading_list in history.items():     # 2 equipos
    for reading in reading_list:                       # 2 160 lecturas
        summary = compute_health_summary(reading)      # ← función pura
        reading.health_index = summary.health_index    # ← mutación del objeto
    insert_readings(reading_list)                      # ← bulk después del loop
```

```mermaid
sequenceDiagram
    participant INIT as initialize_db()
    participant HIST as generate_history()
    participant HI as compute_health_summary()
    participant STORE as insert_readings()

    INIT->>HIST: generate_history(seed=42, days=90)
    HIST-->>INIT: dict{SAG-01: [SR×2160], BALL-01: [SR×2160]}

    loop Para cada equipment_id (2 equipos)
        loop Para cada reading en reading_list (2 160 veces)
            INIT->>HI: compute_health_summary(reading)
            HI-->>INIT: HealthSummary{health_index=87.3, ...}
            INIT->>INIT: reading.health_index = 87.3
            Note over INIT: Mutación del objeto Pydantic
        end
        INIT->>STORE: insert_readings(reading_list)
        Note over STORE: executemany — una sola transacción
    end
```

**Por qué se muta `reading.health_index` en lugar de guardar el `HealthSummary`:**

`HealthSummary` tiene 8 campos calculados (scores parciales, RUL, etc.). Para el pipeline histórico solo interesa `health_index` — los scores parciales y el RUL no se guardan en BD para las lecturas históricas. Persistir un `HealthSummary` completo requeriría una segunda tabla o columnas adicionales, aumentando el costo de almacenamiento y queries sin beneficio operacional.

La denormalización de `health_index` en `SensorReading` es una **decisión de ingeniería de datos deliberada**: el patrón de acceso dominante es "dame la serie temporal de health_index junto a vibration_mms" — un JOIN sería costoso para cada render del dashboard.

**Conteo de llamadas totales en startup:**

```
2 equipos × 2 160 lecturas = 4 320 llamadas a compute_health_summary()
```

`compute_health_summary()` es una función pura (sin side effects, sin I/O, sin estado). Esto la hace segura para llamar 4 320 veces sin riesgo de efectos acumulados.

---

### 2.4 Paso 3 — `insert_readings()`: escritura bulk

```mermaid
flowchart TD
    INPUT["reading_list: list[SensorReading]\n2 160 objetos Pydantic"] --> UNPACK

    UNPACK["List comprehension → list of tuples\nrows = [\n  (r.timestamp.isoformat(),\n   r.equipment_id,\n   r.vibration_mms,\n   ...\n   r.degradation_mode.value,\n   r.health_index)\n  for r in readings\n]"]

    UNPACK --> LOCK["with _lock, conn:\n    conn.executemany(INSERT, rows)"]

    LOCK --> COMMIT["Transacción atómica\n2 160 filas en un solo commit"]
```

**Por qué `executemany` y no un loop de `execute`:**

`executemany` envía todas las filas en una sola transacción. Un loop de `execute` haría un commit por fila → 2 160 transacciones separadas → ~100× más lento para SQLite. Con `executemany`, el costo es prácticamente el de una sola transacción.

**Por qué `.isoformat()` y no pasar el `datetime` directamente:**

SQLite no tiene tipo `DATETIME`. El driver `sqlite3` de Python puede hacer la conversión automáticamente si se activa `detect_types`, pero esto tiene un costo de parsing en cada lectura. Se prefiere texto ISO 8601 explícito: es ordenable lexicográficamente (`ORDER BY timestamp ASC` sin conversión), universalmente legible, y el código de lectura hace la conversión una sola vez (`pd.to_datetime(df["timestamp"], utc=True)`).

---

### 2.5 Paso 4 — `derive_alerts()`: máquina de estados sobre la lista completa

```mermaid
flowchart TD
    INPUT["reading_list: list[SensorReading]\nordenada cronológicamente"] --> LOOP

    LOOP["for reading in readings:\n    checks = [(variable, value, warn, alert), ...]"]

    LOOP --> CHECK{"valor > alert_thresh?"}
    CHECK -- Sí --> CRIT["severity = CRITICAL"]
    CHECK -- No --> CHECK2{"valor > warn_thresh?"}
    CHECK2 -- Sí --> WARN["severity = WARNING"]
    CHECK2 -- No --> CLEAR["in_alert[key] = False\nno emite nada"]

    CRIT & WARN --> DEDUP{"in_alert[key]\n== True?"}
    DEDUP -- No --> EMIT["Emite Alert\nuuid4() como id\nin_alert[key] = True"]
    DEDUP -- Sí --> SKIP["Silencio\n(ya se avisó)"]

    EMIT --> OUT["list[Alert]\n~decenas a centenares\ndependiendo de eventos embebidos"]
```

**El estado `in_alert` es crítico:** sin él, cada lectura anómala generaría una alerta, produciendo miles de alertas por evento de degradación. La máquina de estados garantiza que se emite exactamente **una alerta por cruce de umbral**, independientemente de cuántas lecturas consecutivas superen el umbral.

---

## 3. Pipeline de Tiempo Real — cada 30 segundos

### 3.1 Trigger: `dcc.Interval`

Dash tiene un componente `dcc.Interval` que dispara un evento en el navegador cada `UPDATE_INTERVAL_MS` (30 000 ms por defecto). Este evento activa callbacks en el servidor Python vía WebSocket:

```mermaid
sequenceDiagram
    participant BROWSER as Navegador
    participant WS as WebSocket (Dash)
    participant CB as Callback Python
    participant SIM as generate_realtime_reading()
    participant HI as compute_health_summary()
    participant DB as SQLite
    participant UI as Plotly figures

    loop Cada 30 segundos
        BROWSER->>WS: n_intervals += 1
        WS->>CB: trigger equipment callback

        loop Para cada equipment_id ["SAG-01", "BALL-01"]
            CB->>SIM: generate_realtime_reading(equipment_id)
            Note over SIM: seed = int(now.timestamp()) % 10_000<br/>seed distinto cada vez → variación realista
            SIM-->>CB: SensorReading (un objeto)

            CB->>HI: compute_health_summary(reading)
            HI-->>CB: HealthSummary

            CB->>DB: insert_readings([reading])
            CB->>DB: check_thresholds() → insert_alerts() si aplica
        end

        CB->>DB: get_readings(equipment_id, hours=window)
        DB-->>CB: DataFrame con últimas N horas
        CB->>DB: get_latest(equipment_id)
        DB-->>CB: dict con fila más reciente
        CB-->>UI: Figuras Plotly actualizadas
    end
```

### 3.2 `generate_realtime_reading()` — diseño de la semilla

```python
def generate_realtime_reading(equipment_id: str) -> SensorReading:
    seed = int(datetime.now(tz=timezone.utc).timestamp()) % 10_000
    rng = np.random.default_rng(seed)
    ts = datetime.now(tz=timezone.utc).replace(second=0, microsecond=0)
    ...
```

```mermaid
flowchart TD
    NOW["datetime.now(UTC)\nts = ahora con segundos=0"] --> SEED

    SEED["seed = int(now.timestamp()) % 10_000\n~cambia cada segundo\ngarantiza variación entre llamadas"] --> RNG

    RNG["rng = np.random.default_rng(seed)\nnueva semilla → nueva secuencia\nde números aleatorios"] --> GEN

    GEN["_generate_sag_reading(h=0, ts, events=[], rng)\no _generate_ball_reading(...)"]

    GEN --> SR["SensorReading\ncon ruido fresco sobre baseline\nsin eventos de degradación activos"]
```

**Decisión clave — `events=[]` en tiempo real:**

Las lecturas en tiempo real siempre se generan sin eventos de degradación activos (`events=[]`). Esto refleja la intención del sistema: el dashboard muestra el estado **actual** de la planta, que en la demo siempre es operación normal. Los eventos de degradación viven solo en el historial (los 90 días) para dar contexto a las páginas de tendencias y alertas.

**Decisión clave — `% 10_000`:**

El módulo 10 000 garantiza que la semilla sea un número manejable (evita problemas con semillas muy grandes en algunos backends de NumPy) y que cambie en cada llamada al callback (que ocurre cada 30 segundos, y el timestamp en segundos cambia siempre).

---

### 3.3 Patrón de lectura: separación write path / read path

```mermaid
graph LR
    subgraph WRITE["Write Path"]
        direction TB
        WR1["insert_readings([reading])\n1 fila → executemany\ntransacción atómica"]
        WR2["insert_alerts(alerts)\nINSERT OR IGNORE"]
    end

    subgraph READ["Read Path"]
        direction TB
        RD1["get_readings(eq_id, hours=N)\nSELECT * WHERE eq+ts\nORDER BY timestamp ASC\n→ DataFrame"]
        RD2["get_latest(eq_id)\nSELECT * ORDER BY ts DESC LIMIT 1\n→ dict (fila más reciente para KPIs)"]
        RD3["get_alerts(eq_id, severity, days)\nSELECT * con filtros dinámicos\n→ DataFrame"]
    end

    CALLBACK[Dash callback] --> WRITE
    CALLBACK --> READ
    WRITE --> DB[(SQLite)]
    READ --> DB
```

**Por qué `get_latest` retorna `dict` y no `DataFrame`:**

`get_latest` se usa para KPIs instantáneos (ej. "temperatura actual: 71.2°C"). Crear un DataFrame de una sola fila tiene overhead de pandas (metadata, dtypes, indexing). Un `dict` es suficiente y más eficiente para acceso por nombre de columna (`row["bearing_temp_c"]`).

**Por qué `get_readings` siempre retorna `DataFrame`:**

Todas las visualizaciones de series temporales en Plotly esperan DataFrames con columna `timestamp`. La conversión `pd.to_datetime(df["timestamp"], utc=True)` se hace una sola vez en el store, no en cada callback. Delegar la conversión al store centraliza la lógica de parsing.

---

## 4. Arquitectura de datos — Vista de ingeniero de datos

### 4.1 Flujo end-to-end

```mermaid
graph TD
    subgraph SOURCES["Fuentes de datos"]
        SIM_HIST["Simulador histórico\nnp.random.default_rng(42)\ndeterminista y reproducible"]
        SIM_RT["Simulador tiempo real\nnp.random.default_rng(timestamp)\nestocástico controlado"]
    end

    subgraph MODELS["Modelos de dominio (Pydantic)"]
        SR["SensorReading\nvalidación de rangos físicos\npunto de verdad del sensor"]
        HS["HealthSummary\nobjeto efímero\nno persiste a BD"]
        AL["Alert\npersiste con UUID\nINSERT OR IGNORE"]
    end

    subgraph TRANSFORMS["Transformaciones"]
        T1["compute_health_summary\nfunción pura\nSensorReading → HealthSummary"]
        T2["derive_alerts\nstateful\nlist[SensorReading] → list[Alert]"]
        T3["annotate_anomalies\nZ-score rodante\nDataFrame → DataFrame+zscore"]
    end

    subgraph STORE["Almacenamiento"]
        DB[(SQLite\nreadings + alerts\n2 tablas, 2 índices)]
    end

    subgraph SERVE["Serving layer"]
        DF1["get_readings → DataFrame\npara series temporales"]
        DF2["get_latest → dict\npara KPIs instantáneos"]
        DF3["get_alerts → DataFrame\npara tabla de alertas"]
    end

    subgraph UI["Presentación"]
        PLOTLY["Figuras Plotly\ncada 30s"]
    end

    SIM_HIST & SIM_RT --> SR
    SR --> T1 --> HS
    SR --> T2 --> AL
    HS -->|health_index| SR
    SR & AL --> DB
    DB --> DF1 & DF2 & DF3
    DF1 --> T3 --> PLOTLY
    DF2 & DF3 --> PLOTLY
```

### 4.2 Inmutabilidad vs. mutación — la única excepción

El diseño favorece la inmutabilidad. La **única mutación explícita** del sistema ocurre en el pipeline batch:

```python
reading.health_index = summary.health_index
```

Esta mutación es aceptable porque:
1. Ocurre antes de que el objeto llegue a la BD — no hay copia "limpia" que proteger.
2. Es más eficiente que crear 4 320 nuevos objetos `SensorReading` solo para actualizar un campo.
3. El scope es local al loop de `initialize_db()` — no escapa a otros módulos.

Pydantic v2 por defecto permite mutación (`model_config = ConfigDict(frozen=False)`). Si en el futuro se quiere inmutabilidad total, se puede usar `frozen=True` y reemplazar la mutación por `reading = reading.model_copy(update={"health_index": summary.health_index})`.

### 4.3 Cardinalidades en estado de steady-state

```mermaid
graph LR
    subgraph VOLUME["Volumen de datos"]
        RD["readings\n90 días × 24h × 2 equipos\n= 4 320 filas iniciales\n+2 filas cada 30s"]
        AL["alerts\n~50–200 filas\ndependiendo de eventos embebidos\nretención: 30 días"]
    end

    subgraph QUERIES["Queries por callback (cada 30s)"]
        Q1["get_readings: 1 SELECT por pestaña activa"]
        Q2["get_latest: 1 SELECT por equipo"]
        Q3["get_alerts: 1 SELECT por equstaña de alertas"]
    end

    subgraph INDEXES["Índices SQLite"]
        I1["idx_readings_eq_ts\n(equipment_id, timestamp)\ncubre el WHERE dominante"]
        I2["idx_alerts_eq_ts\n(equipment_id, timestamp)\ncubre los filtros de alertas"]
    end
```

Después de un año de operación continua (si la instancia no se reinicia):

```
readings = 4 320 (histórico) + (365 × 24 × 2) × 2 = 4 320 + 35 040 ≈ 39 360 filas
```

SQLite maneja cómodamente este volumen. El índice compuesto `(equipment_id, timestamp)` garantiza que todos los queries de series temporales sean O(log n) independientemente del volumen total.

### 4.4 Consistencia de datos — garantías del diseño

```mermaid
graph TD
    subgraph G1["Garantía 1: Atomicidad de escritura"]
        A1["insert_readings usa\nwith _lock, conn:\n    executemany(...)\n→ todas las filas o ninguna"]
    end

    subgraph G2["Garantía 2: Idempotencia de alertas"]
        A2["insert_alerts usa INSERT OR IGNORE\nUUID como PK\n→ re-insertar el mismo alert es no-op"]
    end

    subgraph G3["Garantía 3: Reproducibilidad del histórico"]
        A3["generate_history(seed=42)\nsiempre produce la misma historia\n→ cada reinicio es determinista"]
    end

    subgraph G4["Garantía 4: Thread safety"]
        A4["threading.Lock() a nivel de módulo\ncheck_same_thread=False\n→ Dash multi-thread seguro"]
    end
```

### 4.5 Limitaciones de diseño conocidas

```mermaid
graph TD
    subgraph L1["Limitación 1: SQLite es efímero en App Platform"]
        LL1["Cada reinicio del container\nllama initialize_db() de nuevo\nlos datos en tiempo real se pierden\nsolución: migrar a PostgreSQL"]
    end

    subgraph L2["Limitación 2: No hay ventana deslizante en BD"]
        LL2["readings crece indefinidamente\nno hay LIMIT o TTL de filas antiguas\nsolución: agregar vacuumjob periódico\no particionamiento por mes"]
    end

    subgraph L3["Limitación 3: health_index desnormalizado"]
        LL3["Si cambia el algoritmo HI,\nlas filas históricas tienen el HI antiguo\nsolución: recalcular con force_reseed=True\no versionar el algoritmo"]
    end

    subgraph L4["Limitación 4: derive_alerts es O(n×m)"]
        LL4["n = lecturas, m = variables por lectura\nen 90 días: 2160 × 3 = 6480 evaluaciones\naceptable en startup, no en streaming continuo"]
    end
```
