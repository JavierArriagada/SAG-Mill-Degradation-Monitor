# Modelo de datos — Contexto, abstracciones y decisiones de diseño

Este documento explica **por qué** el sistema está modelado como está, no solo **qué** contiene cada clase. Cada decisión de modelado tiene raíces en el dominio del problema: el monitoreo de condición de maquinaria giratoria pesada.

---

## 1. El problema de dominio

Un molino SAG o de Bolas es una máquina de miles de toneladas que gira continuamente. Su falla no es instantánea: la degradación sigue una curva característica de semanas o meses. El sistema debe:

1. **Capturar** el estado del equipo a través de múltiples sensores cada hora.
2. **Calcular** qué tan sano está el equipo en ese instante.
3. **Detectar** cuando una variable se sale de los rangos seguros.
4. **Predecir** cuánto tiempo queda antes de que el estado sea crítico.

Esto define exactamente tres objetos de dominio principales:

```mermaid
graph LR
    SENSOR["SensorReading<br>'lo que midió el sensor'"]
    HEALTH["HealthSummary<br>'lo que calculó el análisis'"]
    ALERT["Alert<br>'lo que salió de rango'"]

    SENSOR -->|compute_health_summary| HEALTH
    SENSOR -->|derive_alerts| ALERT
```

Todo lo demás en el sistema es configuración, utilidades, o infraestructura para servir a estos tres.

---

## 2. Mapa completo de abstracciones

```mermaid
classDiagram
    direction TB

    class SensorReading {
        <<Pydantic BaseModel>>
        +str equipment_id
        +datetime timestamp
        +float vibration_mms       [0–50]
        +float bearing_temp_c      [0–200]
        +float hydraulic_pressure_bar [0–300]
        +float power_kw            [0–25000]
        +float load_pct            [0–100]
        +float liner_wear_pct      [0–100]  opcional
        +float seal_condition_pct  [0–100]  opcional
        +float throughput_tph      [0–6000]
        +float health_index        [0–100]
        +DegradationMode degradation_mode
    }

    class HealthSummary {
        <<Pydantic BaseModel>>
        +str equipment_id
        +datetime timestamp
        +float health_index        [0–100]
        +float vibration_score     [0–100]
        +float thermal_score       [0–100]
        +float pressure_score      [0–100]
        +float power_score         [0–100]
        +float predicted_rul_days  nullable
        +int active_alerts
        +DegradationMode degradation_mode
    }

    class Alert {
        <<Pydantic BaseModel>>
        +str id  UUID
        +datetime timestamp
        +str equipment_id
        +AlertSeverity severity
        +AlertCategory category
        +str variable
        +float value
        +float threshold
        +str message
        +bool acknowledged
    }

    class DegradationMode {
        <<Enum str>>
        NORMAL
        BEARING
        LINER
        HYDRAULIC
        MISALIGNMENT
    }

    class DegradationStage {
        <<Enum str>>
        HEALTHY
        INCIPIENT
        MODERATE
        SEVERE
        CRITICAL
    }

    class AlertSeverity {
        <<Enum str>>
        INFO
        WARNING
        ALERT
        CRITICAL
    }

    class AlertCategory {
        <<Enum str>>
        VIBRATION
        TEMPERATURE
        PRESSURE
        POWER
        DEGRADATION
        HEALTH
    }

    class EquipmentThresholds {
        <<frozen dataclass>>
        +VibrationZones vibration
        +dict bearing_temp_c
        +dict hydraulic_pressure_bar
        +dict power_kw
        +dict load_pct
    }

    class VibrationZones {
        <<frozen dataclass>>
        +float zone_a
        +float zone_b
        +float zone_c
    }

    class ThresholdBand {
        <<frozen dataclass>>
        +str variable
        +float warning   nullable
        +float alert     nullable
        +float critical  nullable
        +float lower_bound nullable
    }

    class Settings {
        <<dataclass>>
        +bool DEBUG
        +int PORT
        +str HOST
        +str DATABASE_URL
        +int UPDATE_INTERVAL_MS
        +int SIMULATION_SEED
        +int HISTORY_DAYS
        +str DEFAULT_LANG
        +int ALERT_RETENTION_DAYS
    }

    SensorReading --> DegradationMode
    HealthSummary --> DegradationMode
    Alert --> AlertSeverity
    Alert --> AlertCategory
    EquipmentThresholds *-- VibrationZones
    SensorReading ..> HealthSummary : compute_health_summary()
    SensorReading ..> Alert : derive_alerts()
    EquipmentThresholds ..> ThresholdBand : get_static_thresholds()
```

---

## 3. `SensorReading` — El objeto central

### Por qué Pydantic v2

`SensorReading` usa `Pydantic BaseModel` porque es el punto de entrada de datos del mundo exterior. Los sensores pueden enviar valores fuera de rango, `NaN`, o tipos incorrectos. Pydantic valida en el borde del sistema:

```mermaid
flowchart LR
    RAW["Dato crudo del sensor<br>o del simulador"] -->|Pydantic valida| SR["SensorReading<br>✓ vibration ∈ [0, 50]<br>✓ temp ∈ [0, 200]<br>✓ power ∈ [0, 25000]"]
    SR -->|ya validado| SISTEMA["Resto del sistema<br>no necesita re-validar"]
```

Los objetos internos (como `ThresholdBand` o `EquipmentThresholds`) **no** usan Pydantic porque no provienen de fuentes externas y no necesitan validación en tiempo de ejecución.

### Por qué `health_index` vive en `SensorReading`

En teoría, el HI es un dato analítico derivado, no un dato sensorial. Pero se incluyó en `SensorReading` por una razón pragmática: el esquema SQLite tiene una sola tabla `readings`, y el HI debe ser consultable junto a las variables sensoriales en la misma fila para las series temporales del dashboard.

```mermaid
graph TD
    PURE["Diseño 'puro':<br>Dos tablas separadas<br>readings | health_summaries<br>JOIN en cada query"]
    PRAGMA["Decisión adoptada:<br>Una tabla con health_index<br>una query simple<br>sin JOIN"]

    PURE -->|demasiado JOIN para<br>un dashboard en tiempo real| PRAGMA
```

Es una **desnormalización intencional** justificada por el patrón de acceso dominante: siempre se necesitan ambos datos juntos.

### Por qué `liner_wear_pct` y `seal_condition_pct` son opcionales

Solo el Molino SAG (`SAG-01`) tiene sensores de desgaste de liner y condición de sellos. El Molino de Bolas no los tiene. En lugar de crear dos clases separadas `SAGReading` y `BallReading`, se optó por **una sola clase con campos opcionales**:

```mermaid
graph LR
    subgraph SR["SensorReading (una sola clase)"]
        COMMON["Campos comunes<br>vibration, temp, pressure<br>power, load, throughput"]
        SAG_ONLY["Opcionales (solo SAG-01)<br>liner_wear_pct<br>seal_condition_pct"]
    end

    SAG01["SAG-01"] --> COMMON & SAG_ONLY
    BALL01["BALL-01"] --> COMMON
    SAG_ONLY -->|None en BALL-01| NULL[null / None]
```

Razón: los equipos comparten el 80% de las variables. Mantener una jerarquía de herencia solo para dos campos opcionales añadiría complejidad sin beneficio.

---

## 4. `HealthSummary` — Resultado analítico

### Por qué existe separado de `SensorReading`

`HealthSummary` es el resultado de aplicar el motor analítico sobre un `SensorReading`. Separarlo en un objeto distinto sigue el principio de **separación de responsabilidades**:

```mermaid
graph LR
    SR["SensorReading<br>'qué midió el equipo'"]
    HS["HealthSummary<br>'qué interpreta el sistema'"]
    ANALYTIC["compute_health_summary()<br>motoranalítico"]

    SR --> ANALYTIC --> HS
```

`SensorReading` es **inmutable en el tiempo** (es el registro histórico del sensor). `HealthSummary` podría recalcularse si el algoritmo cambia — no es el estado del equipo, sino la interpretación del sistema de ese estado.

### Por qué `predicted_rul_days` es `Optional[float]`

El RUL (`Remaining Useful Life`) solo tiene sentido cuando la tendencia del HI es decreciente. Si el equipo está estable o mejorando, no tiene sentido hablar de "días hasta la falla". El `None` no es un dato faltante — es un valor semánticamente significativo: "tendencia positiva, no aplica RUL".

```mermaid
flowchart TD
    TREND{¿Pendiente del HI<br>en últimas 48h?}
    TREND -- "slope < 0<br>(degradándose)" --> RUL["predicted_rul_days = X días"]
    TREND -- "slope ≥ 0<br>(estable o mejorando)" --> NONE["predicted_rul_days = None"]
```

---

## 5. `Alert` — Evento de umbral cruzado

### Decisión de deduplicación

Una alerta no es "cada lectura que supera el umbral" — eso generaría cientos de alertas por minuto y haría el sistema inutilizable. Una alerta es **el cruce del umbral**: el momento en que la variable pasa de normal a anormal.

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Alerting : valor > umbral<br>✉ emite Alert
    Alerting --> Normal : valor ≤ umbral<br>clear flag
    Alerting --> Alerting : valor > umbral<br>(silencio — ya alertado)
```

Esto se implementa con un diccionario de estado `in_alert: dict[str, bool]` por variable+equipo. La clave de decisión fue: **el operador recibe UNA alerta por evento**, no una por lectura.

### Por qué `id` es UUID string y no autoincrement

Los `Alert.id` se generan con `uuid.uuid4()` en el simulador, antes de insertarlos. Esto permite:

1. Crear alertas en memoria y asignarles ID sin necesidad de una inserción previa en BD.
2. Usar `INSERT OR IGNORE` en SQLite para idempotencia — el mismo alert no se duplica aunque se llame dos veces.
3. La columna en SQLite es `TEXT PRIMARY KEY`, que aprovecha exactamente esa garantía.

En contraste, `readings` usa `INTEGER PRIMARY KEY AUTOINCREMENT` porque las lecturas siempre se insertan en secuencia y la BD es la fuente de verdad del ID.

---

## 6. Enumeraciones — Por qué `str, Enum`

Todas las enumeraciones heredan de `(str, Enum)`, no de `Enum` puro:

```python
class DegradationMode(str, Enum):
    BEARING = "bearing"
```

Esto tiene tres consecuencias directas:

```mermaid
graph TD
    subgraph STRENUM["str, Enum"]
        A["Serializable directo a JSON<br>bearing, liner, hydraulic"]
        B["Almacenable en SQLite sin mapping<br>DEFAULT 'normal' en schema"]
        C["Comparable con strings<br>mode == 'bearing' funciona"]
    end

    subgraph ENUMPURO["Enum puro"]
        D["Requiere .value para serializar"]
        E["Requiere conversión para SQLite"]
        F["Solo comparable con DegradationMode.BEARING"]
    end
```

### `DegradationMode` — Estados de la máquina

```mermaid
graph TD
    NRM["NORMAL<br>estado de operación sano"]
    BEA["BEARING<br>degradación de rodamiento<br>ISO 13381 modo 1"]
    LIN["LINER<br>desgaste de revestimiento<br>solo SAG-01"]
    HYD["HYDRAULIC<br>degradación del sistema hidráulico<br>solo SAG-01"]
    MIS["MISALIGNMENT<br>desalineamiento del eje<br>solo BALL-01"]

    NRM -->|inicio de evento| BEA & LIN & HYD & MIS
    BEA & LIN & HYD & MIS -->|fin del evento| NRM
```

Solo puede estar activo **un modo a la vez** por equipo (el simulador tiene un `break` explícito para garantizarlo).

### `DegradationStage` — Progreso dentro de un modo

```mermaid
graph LR
    H["HEALTHY<br>t < 0.20"] --> I["INCIPIENT<br>0.20–0.40<br>difícil de detectar"] --> M["MODERATE<br>0.40–0.60<br>tendencia clara"] --> S["SEVERE<br>0.60–0.80<br>escalada rápida"] --> C["CRITICAL<br>t ≥ 0.80<br>runaway exponencial"]
```

`DegradationStage` no se almacena en BD. Es una abstracción del simulador (`classify_stage(t)`) que describe en qué parte de la curva de vida está el evento de degradación, y determina qué modelo físico aplicar.

---

## 7. Configuración — Tres niveles de abstracción

El sistema usa tres tipos de objetos de configuración con propósito distinto:

```mermaid
graph TD
    subgraph RUNTIME["Runtime — cambia por entorno"]
        SETT["Settings dataclass<br>lee de variables de entorno<br>DEBUG, PORT, DATABASE_URL..."]
    end

    subgraph DOMAIN["Dominio — constante en producción"]
        EQT["EquipmentThresholds frozen dataclass<br>valores ISO 10816 por equipo<br>SAG_THRESHOLDS, BALL_THRESHOLDS"]
        VZ["VibrationZones frozen dataclass<br>zone_a, zone_b, zone_c<br>en mm/s RMS"]
    end

    subgraph UI["Presentación — constante en runtime"]
        ASV["AlertSeverity enum<br>INFO / WARNING / ALERT / CRITICAL"]
        ACA["AlertCategory enum<br>VIBRATION / TEMPERATURE / PRESSURE..."]
        CLR["SEVERITY_COLORS dict<br>hex colors por severidad"]
    end
```

### Por qué `EquipmentThresholds` es un `frozen dataclass` y no Pydantic

Los umbrales del equipo son constantes de ingeniería derivadas de la ISO 10816. No provienen de una fuente externa en runtime — están definidos en el código. Pydantic añadiría overhead de validación innecesario para datos que nunca cambian.

`frozen=True` garantiza que ninguna parte del sistema pueda modificar accidentalmente los umbrales:

```python
@dataclass(frozen=True)
class VibrationZones:
    zone_a: float  # modificar esto lanzaría FrozenInstanceError
```

### Por qué `Settings` es un `dataclass` simple (no Pydantic, no frozen)

`Settings` lee de variables de entorno con `os.getenv`. Las conversiones de tipo (`int(os.getenv(...))`) ya fallan explícitamente si el valor es inválido. No necesita la maquinaria de validación de Pydantic. Y `frozen=False` porque se instancia una vez como singleton `settings = Settings()`.

---

## 8. `ThresholdBand` — Objeto de valor para visualización

```mermaid
classDiagram
    class ThresholdBand {
        <<frozen dataclass — value object>>
        +str variable
        +float warning   nullable
        +float alert     nullable
        +float critical  nullable
        +float lower_bound nullable
    }

    note for ThresholdBand "No es una entidad de dominio.<br>Es un objeto de valor descartable<br>que encapsula los límites de una<br>variable para usarlos en gráficos<br>y en la función evaluate_current_value()"
```

`ThresholdBand` existe porque distintas variables tienen estructuras de umbral diferentes:

```mermaid
graph TD
    subgraph VIB["Vibración (unilateral)"]
        V1["zone_a → warning"]
        V2["zone_b → alert"]
        V3["zone_c → critical"]
        V4["no tiene lower_bound"]
    end

    subgraph PRES["Presión hidráulica (bilateral)"]
        P1["max → warning"]
        P2["critical_high → alert"]
        P3["min → lower_bound<br>⚠ presión baja también es peligrosa"]
    end

    subgraph POW["Potencia (bilateral)"]
        W1["nominal×1.05 → warning<br>sobrepotencia"]
        W2["max → alert"]
        W3["min → lower_bound<br>baja potencia = anomalía"]
    end
```

Un único objeto `ThresholdBand` con campos opcionales unifica estas estructuras distintas, permitiendo que `evaluate_current_value()` y el renderizado de gráficos usen la misma interfaz.

---

## 9. Modelos físicos de degradación

```mermaid
graph TD
    subgraph BEARING["Rodamiento — Weibull"]
        B1["t < 0.30: incipiente<br>vib_f = 1 + 0.6·(t/0.3)²<br>cuadrático suave"]
        B2["0.30 ≤ t < 0.65: moderado<br>vib_f = 1.6 + 1.8·tn<br>lineal ascendente"]
        B3["t ≥ 0.65: severo/crítico<br>vib_f = 3.4 + 6·tn^1.8<br>exponencial runaway"]
        B1 --> B2 --> B3
    end

    subgraph LINER["Liner — Desgaste gradual"]
        L1["power_factor = 1 + 0.10·t + 0.08·t²<br>potencia crece con el desgaste"]
        L2["load_noise_scale = 1 + 3·t<br>carga más ruidosa = inestabilidad"]
        L1 & L2
    end

    subgraph HYDRAULIC["Hidráulico — Caída + ruido"]
        H1["drop = pressure × (0.12·t + 0.06·t²)<br>caída de presión progresiva"]
        H2["noise_scale = 4 × (1 + 4·t)<br>fugas → alta varianza"]
        H1 & H2
    end

    subgraph MISALIGN["Desalineamiento — 2X armónico"]
        M1["vib_f = 1 + 1.2·t + 2.5·t²<br>cuadrático — firma de doble frecuencia"]
    end
```

El parámetro `t ∈ [0, 1]` es el **progreso normalizado** dentro del evento de degradación. Ningún modelo físico conoce el tiempo absoluto, solo qué fracción del evento ha transcurrido. Esto hace los modelos independientes de la escala temporal.

---

## 10. Esquema de base de datos

```mermaid
erDiagram
    READINGS {
        INTEGER id PK "AUTOINCREMENT"
        TEXT    timestamp   "ISO 8601 UTC"
        TEXT    equipment_id "SAG-01 | BALL-01"
        REAL    vibration_mms
        REAL    bearing_temp_c
        REAL    hydraulic_pressure_bar
        REAL    power_kw
        REAL    load_pct
        REAL    liner_wear_pct  "NULL para BALL-01"
        REAL    seal_condition_pct "NULL para BALL-01"
        REAL    throughput_tph
        TEXT    degradation_mode "DEFAULT normal"
        REAL    health_index "DEFAULT 100.0"
    }

    ALERTS {
        TEXT    id PK "UUID v4"
        TEXT    timestamp "ISO 8601 UTC"
        TEXT    equipment_id
        TEXT    severity "info|warning|alert|critical"
        TEXT    category "vibration|temperature|..."
        TEXT    variable "nombre de la columna"
        REAL    value "valor en el momento del cruce"
        REAL    threshold "umbral cruzado"
        TEXT    message "mensaje legible"
        INTEGER acknowledged "0|1"
    }

    READINGS ||--o{ ALERTS : "equipment_id + timestamp"
```

### Decisiones del esquema

**`timestamp` como `TEXT`** (ISO 8601) en lugar de `INTEGER` (epoch): SQLite no tiene tipo nativo `DATETIME`. ISO 8601 es ordenable lexicográficamente, lo que permite hacer `ORDER BY timestamp ASC` sin conversión. El código convierte a `pd.Timestamp` al leer.

**Índice compuesto `(equipment_id, timestamp)`** en ambas tablas: el patrón de acceso dominante es siempre "últimas N horas de un equipo específico". El índice compuesto con este orden satisface ese query directamente.

**`INSERT OR IGNORE` para alertas**: las alertas tienen ID UUID generado antes de insertar. Si se llama `initialize_db()` dos veces (reinicio del container), el `OR IGNORE` evita duplicados sin necesidad de verificar primero.

---

## 11. Thread safety en el store

Dash ejecuta callbacks en múltiples hilos concurrentes. El store usa dos mecanismos complementarios:

```mermaid
sequenceDiagram
    participant CB1 as Callback thread 1
    participant CB2 as Callback thread 2
    participant LOCK as threading.Lock
    participant DB as SQLite connection

    CB1->>LOCK: acquire()
    CB2->>LOCK: acquire() — bloqueado
    CB1->>DB: SELECT * FROM readings WHERE ...
    DB-->>CB1: DataFrame
    CB1->>LOCK: release()
    LOCK-->>CB2: adquirido
    CB2->>DB: INSERT INTO readings ...
    DB-->>CB2: OK
    CB2->>LOCK: release()
```

- `check_same_thread=False` en `sqlite3.connect()`: permite que múltiples hilos usen la misma conexión.
- `threading.Lock()` a nivel de módulo: garantiza que solo un hilo ejecuta una operación de BD a la vez.

La conexión es un **singleton de módulo** (`_DB`), creada una vez y reutilizada en todos los callbacks. Crear una conexión por callback sería costoso e innecesario para SQLite.
