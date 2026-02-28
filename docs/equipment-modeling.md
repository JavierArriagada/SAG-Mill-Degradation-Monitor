# Modelado de equipos industriales para bases de datos robustas

Guía de ingeniería de datos usando el sistema SAG Monitor como caso de estudio concreto. El objetivo es entender los principios que permiten trasladar un equipo físico real a un modelo de datos que soporte monitoreo, análisis y mantenimiento predictivo.

---

## 1. El problema fundamental: de la física al dato

El modelado industrial parte de una premisa distinta al modelado de aplicaciones de negocio. En un sistema de ventas, los datos representan **transacciones** (discretas, intencionales, estructuradas). En un sistema industrial, los datos representan el **estado continuo de la realidad física** de una máquina.

```mermaid
graph TD
    subgraph REALIDAD["Realidad física"]
        F1["Eje girando a 15 RPM\nbajo carga de 2 200 t/h"]
        F2["Temperatura del lubricante\nsubiendo por fricción"]
        F3["Presión hidráulica\nmanteniéndose en 150 bar"]
    end

    subgraph PROBLEMA["Problema de modelado"]
        P1["¿Qué medir?\n¿A qué frecuencia?\n¿Con qué precisión?"]
        P2["¿Cómo saber si\nlo medido es normal?"]
        P3["¿Cómo detectar\nel inicio de una falla?"]
    end

    subgraph DATO["Modelo de datos"]
        D1["SensorReading\nvibration_mms = 1.8\nbearing_temp_c = 62.3\n..."]
        D2["EquipmentThresholds\nzone_a = 2.3\nzone_b = 4.5\n..."]
        D3["DegradationMode\nBEARING / LINER\n..."]
    end

    REALIDAD --> PROBLEMA --> DATO
```

**La pregunta más importante no es qué columnas crear, sino qué fenómeno físico representa cada columna.**

---

## 2. Las cuatro categorías de variables industriales

Todo equipo industrial emite datos que caen en cuatro categorías. Identificarlas correctamente define la estructura del esquema.

```mermaid
graph TD
    subgraph CAT1["Categoría 1: Variables de proceso\n¿Qué está haciendo el equipo?"]
        C1A["load_pct — nivel de llenado\n'¿cuánto material está procesando?'"]
        C1B["throughput_tph — toneladas/hora\n'¿cuánto está produciendo?'"]
    end

    subgraph CAT2["Categoría 2: Variables de máquina\n¿Cómo está la salud mecánica?"]
        C2A["vibration_mms — vibración RMS\n'¿hay algo desbalanceado o desgastado?'"]
        C2B["bearing_temp_c — temperatura cojinete\n'¿hay fricción excesiva?'"]
        C2C["hydraulic_pressure_bar — presión\n'¿el sistema de soporte funciona?'"]
    end

    subgraph CAT3["Categoría 3: Variables de energía\n¿Qué recursos consume?"]
        C3A["power_kw — potencia eléctrica\n'¿la eficiencia energética es normal?'"]
    end

    subgraph CAT4["Categoría 4: Variables de condición\n¿Cuánto tiempo le queda?"]
        C4A["liner_wear_pct — desgaste liner\n'¿cuánto del revestimiento protector queda?'"]
        C4B["seal_condition_pct — condición sellos\n'¿están previniendo fugas?'"]
    end

    CAT1 & CAT2 & CAT3 & CAT4 --> HS["HealthSummary\ncomposición de todas\nen un solo escalar HI"]
```

**Por qué importa esta clasificación:**
Las variables de proceso cambian rápido (carga fluctúa cada minuto). Las de máquina cambian lento (temperatura sube en horas). Las de condición cambian muy lento (desgaste en semanas). Esta diferencia de escala temporal determina frecuencia de muestreo, ventanas de análisis y umbrales.

---

## 3. El SAG Mill como caso de estudio: por qué cada variable

### 3.1 Mapa físico del equipo

```mermaid
graph TD
    subgraph MILL["Molino SAG — componentes físicos"]
        SHELL["Casco cilíndrico\n(gira a ~15 RPM)"]
        LINER["Revestimiento interior\n(liner)\nprotege el casco, facilita la molienda"]
        BEARING["Rodamientos de apoyo\n(trunnion bearings)\nsoportan todo el peso del molino"]
        HYD["Sistema hidráulico\nmantiene la presión\nen los rodamientos"]
        MOTOR["Motor eléctrico\n13 500 kW nominal"]
        CHARGE["Carga de molienda\nmineral + agua + bolas"]
        SEAL["Sellos de trunnion\nprevienen fugas"]
    end

    MOTOR -->|torque| SHELL
    HYD -->|presión| BEARING
    BEARING -->|soporta| SHELL
    LINER -->|recubre| SHELL
    CHARGE -->|dentro de| SHELL
    SEAL -->|cierra| BEARING
```

### 3.2 Por qué `vibration_mms` — La variable más importante

```mermaid
flowchart LR
    subgraph FISICA["Física del fenómeno"]
        VF1["Un rodamiento dañado\ncrea impactos periódicos\na frecuencia de defecto"]
        VF2["Un desalineamiento\ncrea vibración al doble\nde la frecuencia de giro 2×RPM"]
        VF3["Desequilibrio de masa\ncrea vibración a 1×RPM\n(frecuencia de giro)"]
    end

    subgraph MEDICION["Por qué mm/s RMS"]
        M1["RMS (Root Mean Square)\npromedio de energía\nno pico aislado"]
        M2["mm/s (velocidad)\ncorrelaciona mejor\ncon daño estructural\nque aceleración o desplazamiento"]
        M3["ISO 10816 estandariza\neste parámetro para\nmaquinaria giratoria"]
    end

    subgraph UMBRAL["Por qué 4 zonas y no 1"]
        U1["Zona A ≤ 2.3\nequipo nuevo: línea base"]
        U2["Zona B ≤ 4.5\naceptable: plan mantenimiento"]
        U3["Zona C ≤ 7.1\ninsatisfactorio: actuar pronto"]
        U4["Zona D > 7.1\npeligro: parada inminente"]
    end

    FISICA --> MEDICION --> UMBRAL
```

**Decisión de modelado:** la vibración necesita **4 umbrales** (no 1) porque el operador necesita saber no solo si hay problema, sino cuánto tiempo tiene para actuar. Esto se modela como `VibrationZones` con 3 valores numéricos que definen 4 regiones.

### 3.3 Por qué `bearing_temp_c` — El precursor de falla más confiable

```mermaid
flowchart TD
    CAUSA["Rodamiento dañado\no lubricación insuficiente"]
    EFECTO1["↑ fricción"]
    EFECTO2["↑ temperatura"]
    EFECTO3["↑ vibración\n(más tarde)"]
    FALLA["Falla catastrófica"]

    CAUSA --> EFECTO1 --> EFECTO2
    EFECTO2 --> EFECTO3 --> FALLA

    NOTE["Temperatura precede a la vibración\nen horas o días.\nEs el sensor de alerta temprana."]
```

**Decisión de modelado:** los umbrales de temperatura son **trilaterales** (warning / alert / critical), no zonas ISO. Cada nivel tiene una acción distinta asociada: cambiar lubricante, reducir carga, parar el equipo. El modelo usa un dict `{"warning": 72.0, "alert": 82.0, "critical": 92.0}` para máxima legibilidad.

### 3.4 Por qué `hydraulic_pressure_bar` — Variable bilateral

```mermaid
graph LR
    subgraph BAJO["Presión baja < 120 bar"]
        B1["Película de lubricante\ninsuficiente"]
        B2["Contacto metal-metal\nen rodamientos"]
        B3["→ FALLA por desgaste acelerado"]
    end

    subgraph NORMAL["Presión normal 120–180 bar"]
        N1["Film hidrostático\ncompleto"]
        N2["Sin contacto directo\nen cojinetes"]
    end

    subgraph ALTO["Presión alta > 195 bar"]
        A1["Sobrecarga de\nsello hidráulico"]
        A2["Riesgo de ruptura\nde líneas"]
        A3["→ FALLA por sobrepresión"]
    end

    BAJO -->|peligro| FALLA1([Falla])
    NORMAL -->|seguro| OK([OK])
    ALTO -->|peligro| FALLA2([Falla])
```

**Decisión de modelado crítica:** la presión hidráulica tiene **dos zonas de peligro** — presión alta Y presión baja son ambas problemáticas. Esto exige que `ThresholdBand` tenga un campo `lower_bound` además de los umbrales superiores. Modelar solo el umbral superior sería un error de dominio que dejaría fugas de presión sin detectar.

```mermaid
graph TD
    subgraph MAL["❌ Modelado incorrecto"]
        M1["threshold: float\n¿solo el límite superior?\n¿y la presión baja?"]
    end

    subgraph BIEN["✓ Modelado correcto"]
        B2["ThresholdBand:\n  lower_bound: 120  ← baja presión\n  warning:     180  ← alta presión\n  alert:       195  ← crítica alta\n  critical:    None ← no aplica"]
    end
```

### 3.5 Por qué `power_kw` — El KPI de eficiencia

```mermaid
graph TD
    subgraph NORMAL2["Potencia nominal"]
        N2["13 500 kW ±5%\nel motor trabaja en su punto\nde máxima eficiencia"]
    end

    subgraph ALTO2["Potencia alta > 15 000 kW"]
        A2["Molino sobrecargado\no liner desgastado\n(mayor resistencia interna)"]
    end

    subgraph BAJO2["Potencia baja < 8 000 kW"]
        B2["Molino sub-cargado\no problema en alimentación\nproducción en riesgo"]
    end

    NORMAL2 --> OK2([Eficiencia óptima])
    ALTO2 --> OVER([Sobrecarga o desgaste])
    BAJO2 --> UNDER([Sub-producción])
```

**Decisión de modelado:** la potencia también es bilateral. El punto de referencia no es un umbral, sino el **nominal** del equipo (13 500 kW). El modelo define `{"min", "nominal", "max"}` en lugar de solo umbrales de alarma. El `nominal` se usa para calcular `_power_score()` centrando la función alrededor de ±5% del nominal.

### 3.6 Por qué `load_pct` tiene 4 niveles y no 2

```mermaid
graph LR
    subgraph CARGA["% de llenado del molino"]
        L0["< 20%\nbolas golpean directamente\nel liner → daño"]
        L1["20–35%\npor debajo del óptimo\nproducción reducida"]
        L2["35–45%\nZONA ÓPTIMA\nmolienda eficiente"]
        L3["45–55%\nsobrecargado\naumento potencia y temperatura"]
        L4["> 55%\natasco\nparada de emergencia"]
    end

    L0 -->|min| L1 -->|opt_low| L2 -->|opt_high| L3 -->|max| L4
```

**Decisión de modelado:** `{"min", "opt_low", "opt_high", "max"}` porque el operador tiene cuatro acciones distintas: ajustar alimentación (min/opt_low), operar normalmente (opt_low/opt_high), reducir carga (opt_high/max), parar (>max). Un solo umbral binario perdería toda esta información.

### 3.7 Por qué `liner_wear_pct` y `seal_condition_pct` son opcionales

```mermaid
graph TD
    subgraph SAG_ONLY["Solo en Molino SAG — por qué"]
        L1["liner_wear_pct\nel SAG tiene un revestimiento\nde acero Mn que se desgasta\nen 6–18 meses\nEl Molino de Bolas tiene liner\npero más simple, sin sensor dedicado"]
        S1["seal_condition_pct\nel SAG tiene sellos de trunnion\ncon sensor de monitoreo\nnecesarios por el tamaño\nde los rodamientos de apoyo"]
    end

    subgraph BALL_NO["No en Molino de Bolas — por qué"]
        B1["Tamaño menor\nlos sellos son más simples\nno justifican sensor dedicado"]
        B2["El liner del Ball Mill\nse reemplaza por mantenimiento\nno requiere seguimiento continuo"]
    end
```

**Decisión de esquema resultante:** campo `NULL`-able en la misma tabla, no tabla separada. El costo de `NULL` en dos columnas es mínimo. El costo de una tabla separada `sag_specific_readings` + JOIN en cada query es significativo para un dashboard en tiempo real.

---

## 4. El concepto de "ventana operativa nominal"

El insight más importante del modelado industrial: cada variable no tiene solo un umbral — tiene una **ventana de operación normal** con topografía propia.

```mermaid
graph TD
    subgraph VENTANA["Estructura de la ventana operativa"]
        V1["lower_danger\nvalor tan bajo que indica falla\no ausencia de la variable"]
        V2["lower_warning\nlímite inferior de operación\naceptable"]
        V3["optimal_low\nlímite inferior de la zona\nóptima de eficiencia"]
        V4["nominal\npunto de diseño\neficiencia máxima"]
        V5["optimal_high\nlímite superior de la zona\nóptima"]
        V6["upper_warning\nempieza la zona de riesgo"]
        V7["upper_danger\nzona crítica, actuar de inmediato"]

        V1 --> V2 --> V3 --> V4 --> V5 --> V6 --> V7
    end

    subgraph TIPOS["Tipos de ventana por variable"]
        T1["Unilateral superior\nvibration_mms\nsolo límites por arriba"]
        T2["Unilateral superior con warning\nbearing_temp_c\nwarning/alert/critical arriba"]
        T3["Bilateral completa\nhydraulic_pressure_bar, power_kw\nlímites arriba Y abajo"]
        T4["Bilateral con óptimo central\nload_pct\nmin/opt_low/opt_high/max"]
    end
```

**Regla de modelado:** siempre preguntar para cada variable: ¿puede ser peligrosamente baja? Si sí → necesita `lower_bound`. ¿Tiene una zona óptima distinta de "cualquier valor normal"? Si sí → necesita `opt_low` y `opt_high`.

---

## 5. Modos de degradación: taxonomía de fallas como dato

Uno de los errores más comunes en el modelado industrial es tratar las fallas como eventos binarios (ok/falla). La realidad es que una máquina tiene **modos de falla** distintos, cada uno con su firma de datos propia.

```mermaid
graph TD
    subgraph FISICA2["Física de cada modo de falla"]
        BEARING2["Falla de rodamiento\nProgresión Weibull:\n  t < 0.3: incipiente, difícil detectar\n  0.3–0.65: vib↑ + temp↑ clara\n  0.65–1.0: runaway exponencial\nFirma: vibration↑↑ + bearing_temp↑↑"]

        LINER2["Desgaste de liner\nProgresión lineal + cuadrática:\n  power_factor = 1 + 0.10t + 0.08t²\nFirma: power_kw↑ + load_pct más ruidoso\n     + liner_wear_pct↑"]

        HYDRAULIC2["Degradación hidráulica\nCaída + varianza creciente:\n  drop = base × (0.12t + 0.06t²)\n  noise ∝ (1 + 4t)\nFirma: pressure↓ + varianza↑↑"]

        MISALIGN2["Desalineamiento de eje\nArmónico de doble frecuencia:\n  vib_f = 1 + 1.2t + 2.5t²\nFirma: vibration↑↑ sin aumento de temp"]
    end

    BEARING2 & LINER2 & HYDRAULIC2 & MISALIGN2 --> DM["DegradationMode\nEnumeración str\nalmacenable directamente en SQLite"]
```

**Por qué modelar el modo de degradación como columna y no solo detectarlo:**

```mermaid
graph LR
    subgraph SIN["Sin DegradationMode en esquema"]
        S1["Solo se sabe que algo está mal\nNo se puede entrenar un clasificador\nNo hay histórico de qué modo ocurrió\nNo se puede comparar duración por modo"]
    end

    subgraph CON["Con DegradationMode como columna"]
        C1["Se puede preguntar:\n'¿cuántos eventos bearing en 90 días?'\n'¿cuánto duró cada evento liner?'\n'¿qué variables varían más en hydraulic?'"]
        C1B["Base para ML supervisado:\nX = [vib, temp, pressure, power]\ny = degradation_mode"]
    end

    SIN -->|decisión| CON
```

---

## 6. Diseño de esquema: decisiones por tipo de flota

### 6.1 Flota homogénea — mismos sensores en todos los equipos

```mermaid
erDiagram
    EQUIPMENT {
        str id PK "SAG-01, BALL-01"
        str type "SAG | BALL"
        str name
        float nominal_throughput_tph
    }

    READINGS {
        int id PK AUTOINCREMENT
        str equipment_id FK
        datetime timestamp
        float vibration_mms
        float bearing_temp_c
        float hydraulic_pressure_bar
        float power_kw
        float load_pct
        float throughput_tph
        float health_index
        str degradation_mode
    }

    EQUIPMENT ||--o{ READINGS : "tiene muchas"
```

Cuando todos los equipos tienen exactamente las mismas variables: **una sola tabla con `equipment_id`**. La clave compuesta `(equipment_id, timestamp)` es el índice natural.

### 6.2 Flota heterogénea — algunos equipos tienen variables adicionales

Este es el caso exacto del SAG Monitor: SAG-01 tiene `liner_wear_pct` y `seal_condition_pct`, BALL-01 no.

```mermaid
graph TD
    subgraph OPCION1["Opción A: columnas NULL-able (elegida)"]
        A1["Una tabla readings\ncolumnas opcionales para SAG:\n  liner_wear_pct REAL (NULL para BALL)\n  seal_condition_pct REAL (NULL para BALL)\nPro: una sola query\nCon: columnas NULL en 50% de filas"]
    end

    subgraph OPCION2["Opción B: tabla de extensión"]
        B1["Tabla readings (común)\nTabla sag_readings (extensión)\nPro: schema limpio\nCon: JOIN obligatorio siempre\n     complejidad en queries"]
    end

    subgraph OPCION3["Opción C: tabla por tipo de equipo"]
        C1["Tabla sag_readings\nTabla ball_readings\nPro: schema perfectamente limpio\nCon: imposible query de flota\n     duplicación de lógica"]
    end

    subgraph CRITERIO["Criterio de decisión"]
        D1["¿Cuántas columnas exclusivas?\n¿Con qué frecuencia se hacen queries\nde flota completa vs equipo individual?"]
    end

    CRITERIO --> OPCION1
    OPCION1 --> ELEGIDA["✓ Elegida:\n≤ 5 columnas opcionales\nqueries siempre por equipo_id\nNULL overhead mínimo en SQLite"]
```

### 6.3 Flota muy heterogénea — muchos tipos distintos

Para flotas con docenas de tipos de equipo muy distintos:

```mermaid
graph TD
    subgraph EAV["Opción EAV (Entity-Attribute-Value)"]
        E1["Tabla: readings\n  equipment_id, timestamp, variable_name, value\nPro: schema flexible, ilimitado\nCon: imposible de indexar bien\n     queries complejas\n     pérdida de tipos de dato"]
    end

    subgraph HYBRID["Opción híbrida recomendada para IoT industrial"]
        H1["Tabla: readings_common\n  equipment_id, timestamp\n  vibration, temp, power (siempre presentes)"]
        H2["Tabla: readings_extended  (JSONB)\n  equipment_id, timestamp\n  extra_data: {'liner_wear': 45.2, 'seal': 89.1}"]
        H1 --> H2
    end

    subgraph TIMESERIES["Opción base de datos de series temporales"]
        T1["TimescaleDB / InfluxDB / QuestDB\nmodelado nativo por tags + fields\n  tags: equipment_id, type\n  fields: variable_name=value\nPro: queries temporales muy optimizadas\nCon: herramienta adicional en stack"]
    end
```

**Regla:** SQLite + columnas NULL funciona bien hasta ~10 variables opcionales. Para flotas con >10 tipos de equipo distintos con >10 variables únicas por tipo, considerar TimescaleDB o JSONB.

---

## 7. Modelado de umbrales: configuración vs. datos

Un error frecuente es mezclar umbrales de configuración con datos operacionales. Son cosas distintas con ciclos de vida distintos.

```mermaid
graph TD
    subgraph CONFIG["Umbrales como configuración"]
        C1["Cambian raramente\n(después de calibración o revisión ISO)\nSon constantes de ingeniería\nNo tienen historial temporal\nNo necesitan timestamps"]
        C2["En código: frozen dataclass\nEquipmentThresholds\nVibrationZones"]
        C3["En BD de producción:\ntabla equipment_config\ncon version_effective_date"]
    end

    subgraph DYNAMIC["Umbrales dinámicos como datos"]
        D1["Se recalculan con cada nuevo lote\nde datos históricos\nDependen de la historia del equipo\nCambian con el ciclo de vida"]
        D2["compute_dynamic_thresholds(series)\nμ ± k×σ sobre primeras 168h\nse guardan como ThresholdBand"]
    end

    subgraph BEST["Práctica recomendada"]
        B1["Umbral estático ISO → en código\ncomo constante inmutable"]
        B2["Umbral dinámico → calculado en runtime\n sobre ventana de baseline\nno persiste a BD (es derivado)"]
    end

    CONFIG & DYNAMIC --> BEST
```

---

## 8. El esquema de eventos (alertas) vs. lecturas continuas

La distinción fundamental que define si el sistema es útil operacionalmente:

```mermaid
graph TD
    subgraph LECTURAS["Tabla readings — datos continuos"]
        R1["Una fila por lectura\nsiempre, independientemente del estado\nFreuencia alta (1/hora)\nVolumen alto (4320 filas/equipo/90días)\nPregunta que responde:\n'¿Cómo estaba el equipo en el instante T?'"]
    end

    subgraph ALERTAS["Tabla alerts — eventos de cruce"]
        A1["Una fila por CRUCE de umbral\nNo por lectura\nFrecuencia baja (decenas por evento)\nVolumen bajo (~200 alertas en 90 días)\nPregunta que responde:\n'¿Cuándo cruzó el umbral X por primera vez?'"]
    end

    subgraph ESTADO["Por qué separarlos"]
        E1["Si alerts fuera una columna boolean en readings:\n  90 días × 24h × 2 equipos = 4320 filas\n  con 99% de valores false\n  queries de alertas escanearían toda la tabla"]
        E2["Con tabla separada:\n  solo se guardan los eventos relevantes\n  índice perfecto sobre la tabla pequeña"]
    end
```

**Cardinalidad típica:**

| Tabla | Filas en 90 días | Ratio |
|---|---|---|
| `readings` | 4 320 por equipo | 1 fila/hora |
| `alerts` | ~50–200 total | ~1 por evento de degradación |

---

## 9. `DegradationStage` — Modelar el progreso, no solo el estado

En sistemas de mantenimiento predictivo el valor está en saber **qué tan avanzada** está la degradación, no solo si está presente.

```mermaid
graph LR
    subgraph ESTADOS["DegradationStage"]
        HEALTHY3["HEALTHY\nt < 0.20\nnada inusual"]
        INCIPIENT3["INCIPIENT\nt 0.20–0.40\ndetectable solo con análisis\nno activa alertas ISO"]
        MODERATE3["MODERATE\nt 0.40–0.60\ntendencia clara\nactiva warning"]
        SEVERE3["SEVERE\nt 0.60–0.80\nescalada rápida\nactiva alert/critical"]
        CRITICAL3["CRITICAL\nt ≥ 0.80\nrunaway exponencial\nparada requerida"]

        HEALTHY3 --> INCIPIENT3 --> MODERATE3 --> SEVERE3 --> CRITICAL3
    end

    subgraph VALOR["Por qué modelarlo como dato"]
        V1["Con solo HEALTHY/FALLA:\n  se detecta cuando ya es tarde\n  el técnico llega en zona D"]
        V2["Con 5 etapas:\n  se detecta en INCIPIENT\n  se planifica mantenimiento en MODERATE\n  se ejecuta antes de SEVERE"]
    end

    ESTADOS --> VALOR
```

**Nota:** `DegradationStage` en este sistema es interno al simulador (`classify_stage(t)`). En un sistema con datos reales, se puede calcular a partir del HI:

| HI | DegradationStage |
|---|---|
| 80–100 | HEALTHY |
| 60–80 | INCIPIENT |
| 40–60 | MODERATE |
| 20–40 | SEVERE |
| 0–20 | CRITICAL |

---

## 10. Variables derivadas vs. variables primarias

No todas las columnas del esquema son lecturas directas de sensores. Algunas son derivadas.

```mermaid
graph TD
    subgraph PRIMARIAS["Variables primarias — medición directa"]
        P1["vibration_mms\n← acelerómetro + integración"]
        P2["bearing_temp_c\n← termopar o termistor"]
        P3["hydraulic_pressure_bar\n← transductor de presión"]
        P4["power_kw\n← vatímetro en tablero eléctrico"]
        P5["load_pct\n← sensor de nivel acústico o de peso"]
    end

    subgraph DERIVADAS["Variables derivadas — calculadas"]
        D1["throughput_tph\n← función de load_pct + RPM\n¿guardarla? Sí: es el KPI productivo"]
        D2["health_index\n← algoritmo sobre 4 variables\n¿guardarla? Sí: desnormalización\nintencional para queries"]
        D3["liner_wear_pct\n← modelo de desgaste acumulado\no sensor ultrasonido periódico\n¿guardarla? Sí: cambia lento, costosa de recalcular"]
    end

    subgraph EFIMERAS["Variables efímeras — no persistir"]
        E1["vibration_score\n← sub-índice del HI\nno tiene valor independiente\nse recalcula gratis desde vib_mms"]
        E2["thermal_score, pressure_score\nidem"]
        E3["predicted_rul_days\n← extrapolación lineal\nfunciona de la serie de HI\nno tiene sentido almacenar como columna"]
    end
```

**Regla de persistencia:** guardar una variable derivada si:
1. Su cálculo es costoso (O(n) sobre historia)
2. Es un KPI que se consulta frecuentemente junto a datos primarios
3. Su valor puede cambiar si cambia el algoritmo (en ese caso, recalcular con `force_reseed=True`)

No guardar si: se recalcula en O(1) a partir de datos ya persistidos.

---

## 11. Generalización: plantilla para cualquier equipo industrial

### 11.1 Proceso de modelado en 6 pasos

```mermaid
flowchart TD
    S1["Paso 1: Diagrama físico del equipo\n¿Cuáles son los subsistemas?\n¿Cómo interactúan?\n¿Dónde ocurren las fallas?"]
    S2["Paso 2: Taxonomía de modos de falla\nPara cada subsistema:\n¿Qué puede fallar?\n¿Con qué signature de datos?"]
    S3["Paso 3: Selección de variables\nUna por subsistema crítico\n¿Primaria o derivada?\n¿Unilateral o bilateral?"]
    S4["Paso 4: Definición de ventanas operativas\nPor variable: min, opt_low, nominal\nopt_high, max, critical_high\n¿Fuente: ISO? ¿Fabricante? ¿Histórico?"]
    S5["Paso 5: Diseño del esquema\n¿Flota homogénea o heterogénea?\n¿Frecuencia de muestreo?\n¿Retención de datos?"]
    S6["Paso 6: Diseño del pipeline de eventos\n¿Qué es un 'evento'?\n¿Cómo deduplicar?\n¿Qué acciones dispara?"]

    S1 --> S2 --> S3 --> S4 --> S5 --> S6
```

### 11.2 Plantilla de esquema para cualquier equipo rotativo

```mermaid
erDiagram
    EQUIPMENT_TYPES {
        str type_id PK "SAG, BALL, PUMP, COMPRESSOR"
        str name
        str iso_standard "ISO 10816, ISO 13381, ..."
        json threshold_template "umbrales por defecto del tipo"
    }

    EQUIPMENT {
        str id PK "SAG-01, PUMP-03"
        str type_id FK
        str location
        float nominal_throughput
        datetime commissioned_date
        json custom_thresholds "overrides del template"
    }

    READINGS {
        int id PK
        str equipment_id FK
        datetime timestamp
        float vibration_mms
        float bearing_temp_c
        float power_kw
        float health_index
        str degradation_mode
        json extra_variables "para variables específicas del tipo"
    }

    FAILURE_MODES {
        str id PK "bearing, liner, hydraulic"
        str equipment_type_id FK
        str name
        str primary_indicator "variable más afectada"
        str progression_model "weibull, linear, exponential"
    }

    ALERTS {
        str id PK "UUID"
        str equipment_id FK
        datetime timestamp
        str severity
        str failure_mode_id FK
        str variable
        float value
        float threshold
        bool acknowledged
    }

    EQUIPMENT_TYPES ||--o{ EQUIPMENT : "instancias de"
    EQUIPMENT ||--o{ READINGS : "genera"
    EQUIPMENT_TYPES ||--o{ FAILURE_MODES : "puede tener"
    EQUIPMENT ||--o{ ALERTS : "genera"
    FAILURE_MODES ||--o{ ALERTS : "clasifica"
```

### 11.3 Aplicar la plantilla a otros equipos

| Equipo | Vibración | Temperatura | Presión | Potencia | Variable específica |
|---|---|---|---|---|---|
| SAG Mill (este proyecto) | vibration_mms | bearing_temp_c | hydraulic_pressure_bar | power_kw | liner_wear_pct, seal_condition_pct |
| Bomba centrífuga | vibration_mms | bearing_temp_c | discharge_pressure_bar | power_kw | flow_rate_m3h, suction_pressure_bar |
| Compresor de tornillo | vibration_mms | outlet_temp_c | discharge_pressure_bar | power_kw | oil_pressure_bar, intercooler_temp_c |
| Ventilador industrial | vibration_mms | bearing_temp_c | — | power_kw | blade_angle_deg, airflow_m3s |
| Correa transportadora | — | drive_temp_c | — | power_kw | belt_tension_n, tracking_offset_mm |

La estructura del esquema es la misma. Solo cambian los valores de los umbrales y las columnas `extra_variables` o los campos opcionales.
