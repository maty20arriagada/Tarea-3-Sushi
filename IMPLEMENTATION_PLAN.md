# Plan de Implementación — HW03 Sushi Preference Dataset

> **v2 (2026-07-04).** Revisión mayor tras auditoría de datos. Ver §0 antes de leer el resto:
> dos bugs de datos corregidos y un problema de identificación que redefine la estrategia de modelos.

> **v3 (2026-07-06).** Reestructuración del informe final por decisión del usuario. **M6 (MNL
> sobre el Set B de 100 ítems) fue ELIMINADO del informe**, junto con los escenarios C
> (California roll) y D (Kinki), que dependían del Set B. El informe trabaja ahora 100% sobre
> el Set A con **dos escenarios** (A toro, B kappa). Los betas de los escenarios y el WTP se
> transfieren del baseline **MNL-atributos** del Set A (β_precio=+0,58), con el caveat de
> multicolinealidad (corr precio-grasa 0,82 → escenarios leídos cualitativamente). Los tres
> modelos protagonistas se **renumeraron en los entregables** (no en el código): antiguo M3→**M1**,
> M4b→**M2**, M5-LC3→**M3**; los baselines pasan a etiquetas descriptivas (MNL-atributos, MNL-ASC,
> MNL-explotado). El mapeo informe↔script está en el Apéndice B del informe y en
> `R_Studio/EXPLICACION_MODELOS_R.txt`. Las secciones §3–§10 de abajo describen el diseño
> original (con M6/Set B) y se conservan como referencia histórica.

---

## 0. Registro de correcciones (v1 → v2)

### 0.1 Bug crítico: ítems del Set A mal etiquetados (CORREGIDO)

El archivo `sushi3a.5000.10.order` usa numeración propia del Set A (definida en
`README-en.txt`), que **no coincide** con la numeración maestra de `sushi3.idata`
para los IDs 5–9. La versión anterior de `process_sushi_dataset.py` hacía el join
directo contra la tabla maestra, mislabeleando la mitad del choice set:

| Set A ID | Ítem real (README) | Lo que decía el CSV v1 | Master ID correcto |
|---|---|---|---|
| 0–4 | ebi, anago, maguro, ika, uni | ✓ (coincidían por casualidad) | 0–4 |
| 5 | **ikura** | tako ✗ | 6 |
| 6 | **tamago** | ikura ✗ | 7 |
| 7 | **toro** | tamago ✗ | 8 |
| 8 | **tekka_maki** | toro ✗ | 26 |
| 9 | **kappa_maki** | amaebi ✗ | 29 |

**Fix:** mapeo `SET_A_TO_MASTER` en `scripts/process_sushi_dataset.py`, columna nueva
`alt_id` (índice de alternativa 0–9) separada de `item_id` (ID maestro para joins con
`sushi_items.csv`), y check explícito del mapeo en `verify_sushi_dataset.py`.
La suite pasa **47/47** (la v1 pasaba 43/43 porque ningún check validaba nombres).

### 0.2 Bug: escala de oiliness invertida (CORREGIDO)

El README define `oiliness` con **0 = más grasoso** (`range[0-4] 0:heavy/oily`). El data
dictionary v1 decía lo contrario. Se recodificó en el procesamiento como `4 − raw`, de modo
que **mayor = más grasoso** (toro 3.45, kappa_maki 0.27). Todas las hipótesis sobre
β_oiliness de este plan usan la escala recodificada.

### 0.3 Problema de identificación: ASCs + atributos constantes por ítem

Los tres atributos continuos (`price_norm`, `oiliness`, `freq_sold`) son **constantes por
ítem**: los 5,000 usuarios ven exactamente los mismos valores. Con 10 alternativas hay a lo
más 9 parámetros identificables de variación "entre alternativas", y 9 ASCs ya los agotan.
La especificación v1 (9 ASCs + 3 betas genéricos) era **perfectamente colineal → no
estimable**. Esto no es un bug arreglable en los datos; es una propiedad del diseño, y la
sección §4 reorganiza los modelos para respetarla:

- Los betas de atributos y los ASCs completos **nunca** conviven en la misma especificación.
- M1 (solo atributos) está **anidado** en M2 (solo ASCs) → LR test limpio.
- Las interacciones atributo × demográfico **sí** son identificables junto a ASCs completos
  (varían entre individuos).
- Los escenarios de precio usan constantes calibradas + betas de M1/M6 (§6.0).

### 0.4 Otros cambios v1 → v2

- **HCM eliminado del alcance.** Los indicadores propuestos (I1–I3) se construían desde el
  ítem elegido → endógenos respecto de la variable dependiente. La pauta exige 2 modelos;
  tenemos 5–6 sin el HCM. Si sobrara tiempo, la única versión válida usaría los scores del
  Set B como indicadores (no el choice), y no es prioridad.
- **Ranking explotado (rank-ordered logit)** entra como herramienta central para NL y MXL
  (§4.5, §4.6): usa ranks 1–3 en vez de solo rank 1, triplica las pseudo-observaciones y
  aporta la información de sustitución que identifica los λ y las varianzas aleatorias.
- Nidos redefinidos con los ítems correctos (§4.5): ahora existe un nido `akami` coherente
  (maguro, toro, tekka_maki).
- Escenarios redefinidos con ítems que sí están en cada choice set y con el modelo que
  alimenta cada uno declarado (§6).
- `apollo_config.R` corregido: 10 nombres para 10 códigos (v1 asignaba 11 nombres a 10).
- Tablas de escenarios 14–17 ahora definidas (§8).
- Entregables de la pauta agregados al cronograma (§9): link a carpeta compartida;
  la redacción del reporte es de los autores (la pauta prohíbe redactarlo con IA generativa).

---

## 1. Contexto

### 1.1 ¿Qué tenemos hasta ahora?

| Recurso | Estado | Ubicación |
|---|---|---|
| Sushi raw data (Kamishima 2003) | Procesado | `Data/sushi_raw/` |
| `sushi_items.csv` (100 items) | Regenerado v2 (oiliness recodificada) | `Data/` |
| `sushi_users.csv` (5,000 users) | Verificado | `Data/` |
| `sushi3a_choice_long.csv` (50K rows) | **Regenerado v2 (mapeo corregido, + `alt_id`)** | `Data/` |
| `sushi3b_choice_long.csv` (50K rows) | Regenerado (sin cambios de fondo) | `Data/` |
| `sushi3b_consideration_long.csv` (50K rows) | Regenerado | `Data/` |
| `sushi3b_score_long.csv` (500K rows) | Regenerado | `Data/` |
| `data_dictionary.txt` | Actualizado v2 | `Data/` |
| `process_sushi_dataset.py`, `verify_sushi_dataset.py` | Instalados y corregidos | `scripts/` |
| Verificación **47/47 checks pass** | Completado 2026-07-04 | `scripts/verify_sushi_dataset.py` |
| HW03 pauta | En mano | `HW03 - Understanding Consumer Behavior.txt` |

### 1.2 Proyecto de referencia

El proyecto Olist (`Tarea 2 Olist/`) sirve como plantilla de estructura (config central,
scripts numerados, Apollo en R). **Ojo:** sus especificaciones de utilidad no son
trasplantables — en Olist los atributos variaban dentro del choice set; aquí no (§0.3).

### 1.3 Fenómeno de estudio

**Elección de sushi en consumidores japoneses.** 5,000 consumidores reales rankearon 10
tipos de sushi del más al menos preferido. El dataset incluye atributos reales de mercado
(precio normalizado, nivel de grasa, frecuencia de venta) y demografía (edad, género,
región, migración). Existen diferencias culturales documentadas entre el este y el oeste de
Japón en preferencias alimentarias (el propio README del dataset las describe) — ese es el
hilo conductor del análisis de heterogeneidad.

Shares observados (rank 1, Set A corregido): toro 34.3%, uni 14.9%, anago 11.0%,
ikura 10.9%, ebi 9.2%, maguro 8.1%, ika 4.6%, tamago 4.1%, tekka_maki 2.3%, kappa_maki 0.7%.

---

## 2. Estructura del proyecto

```
Tarea 3 Sushi/
├── Data/                                    # Ya existe (regenerada v2)
├── scripts/
│   ├── process_sushi_dataset.py             # ✔ instalado y corregido
│   ├── verify_sushi_dataset.py              # ✔ instalado y ampliado (47 checks)
│   ├── config.py                            # Central: paths, alternativas, nests, SEED
│   ├── 01_eda_visualizations.py             # Figuras + tablas resumen
│   ├── 02_estimate_models.py                # M1, M2, M3, M6 (scipy, gradiente analítico)
│   ├── 03_exploded_models.py                # M4 NL y M5 MXL sobre ranking explotado
│   ├── 04_scenario_analysis.py              # 4 escenarios what-if
│   └── run_all.py                           # Reproducción completa
├── R_Studio/
│   ├── apollo_config.R
│   ├── apollo_data_prep.R                   # Long → wide (incluye explosión de ranks)
│   ├── 01_apollo_mnl.R                      # M1 + M2 + M3 (validación cruzada Python)
│   ├── 02_apollo_nested_logit.R             # M4 NL
│   ├── 03_apollo_mixed_logit.R              # M5 MXL
│   └── README.md
├── outputs/
│   ├── figures/                             # PNG 150 dpi
│   └── tables/                              # CSV model results
├── requirements.txt
└── README.md
```

(Se elimina `04_apollo_hybrid_choice.R` — ver §0.4.)

---

## 3. Especificaciones de datos

### 3.1 Dataset principal — `sushi3a_choice_long.csv` (Set A)

| Propiedad | Valor |
|---|---|
| Universo de alternativas | 10, fijo para todos los usuarios |
| Alternativas (`alt_id` / master `item_id`) | ebi (0/0), anago (1/1), maguro (2/2), ika (3/3), uni (4/4), ikura (5/6), tamago (6/7), toro (7/8), tekka_maki (8/26), kappa_maki (9/29) |
| Ocasiones de elección | 5,000 (una por usuario) |
| Filas | 50,000 |
| Variable de elección | `chosen=1` si rank=1; columna `rank` (1–10) disponible para explosión |
| Atributos continuos (constantes por ítem, §0.3) | `price_norm` [1.02–4.49], `oiliness` recodificada [0.27–3.45], `freq_sold` [0.76–0.92] |
| Atributos categóricos | `style` (maki/other), `major_group`, `minor_group` — colineales con ASCs; útiles solo para definir nidos e interacciones |
| Características del decisor | `gender`, `age_group` (0–5), `childhood_region`, `current_region`, `eastwest_childhood`, `eastwest_current`, `moved`, `time_taken_sec` |
| Rol | Dataset principal: modelos M1–M5, escenarios A–C |

**Advertencia de identificación (§0.3):** cualquier especificación sobre Set A debe elegir
entre betas de atributos (M1) o ASCs completos (M2/M3); jamás ambos.

### 3.2 Dataset secundario — `sushi3b_choice_long.csv` (Set B)

| Propiedad | Valor |
|---|---|
| Universo | 100 ítems; cada choice set = 1 elegido + 9 muestreados uniforme (McFadden 1978, SEED=42) |
| Ocasiones / filas | 5,000 / 50,000 |
| Rol | M6 (MNL de atributos con choice sets variables): validación externa de los betas de M1 y vehículo de los escenarios C y D. El muestreo uniforme satisface la uniform conditioning property → MNL consistente sin corrección |

### 3.3 Datasets auxiliares

- `sushi3b_consideration_long.csv`: los 10 ítems que cada usuario realmente rankeó del
  universo de 100 → estadística descriptiva de qué entra al consideration set (EDA §5).
- `sushi3b_score_long.csv`: ratings 0–4 → validación descriptiva de preferencias; no entra
  a los modelos.

---

## 4. Modelos a estimar

### 4.0 Estrategia de identificación

Cadena de modelos anidados sobre Set A, con LR tests en cada eslabón:

```
M1 (3 betas de atributos)  ⊂  M2 (9 ASCs)  ⊂  M3 (9 ASCs + interacciones demográficas)
```

- M1 responde: ¿cuánto de la preferencia explican precio, grasa y disponibilidad?
- M2 es el benchmark saturado en shares (ajuste perfecto de shares agregados por construcción).
- LR M1 vs M2 cuantifica lo que los 3 atributos **no** capturan (calidad no observada,
  prestigio del ítem, etc.).
- M3 agrega heterogeneidad observada: las interacciones sí son identificables porque varían
  entre individuos.

M4 (NL) y M5 (MXL) explotan el ranking (ranks 1–3) para identificar sustitución y
heterogeneidad no observada. M6 replica M1 en Set B como validación externa.

### 4.1 M1 — MNL de atributos (Set A, sin ASCs)

```
U_nj = β_price · price_j + β_oil · oiliness_j + β_freq · freq_sold_j + ε_nj      (3 parámetros)
```

- Estimación: scipy BFGS con gradiente analítico (Python) + Apollo (R, validación cruzada).
- **WTP (delta method):** `WTP_oil = −β_oil/β_price`, `WTP_freq = −β_freq/β_price`.
  Precio normalizado → WTP en unidades relativas de precio, no JPY (limitación declarada).
- Hipótesis: `β_price` ambiguo en agregado (toro es caro Y el favorito — el precio del sushi
  señala calidad; el signo "de libro" puede no aparecer sin controlar por grasa);
  `β_oil > 0` (los shares altos son de ítems grasos); `β_freq` ambiguo.
- **Advertencia (hallazgo EDA):** dentro del Set A, corr(price, oiliness) = **0.82** —
  multicolinealidad severa con solo 10 ítems. Los SEs de M1 saldrán inflados y el WTP será
  inestable; reportar la matriz de correlación junto a M1 y apoyarse en M6 (Set B, 100
  ítems, correlación menor) para los WTP definitivos.

### 4.2 M2 — MNL de ASCs (Set A, benchmark saturado)

```
U_nj = ASC_j + ε_nj      (9 parámetros; ASC_ebi = 0, referencia)
```

- Reproduce exactamente los shares observados; LL(M2) es la cota superior de cualquier
  modelo sin variación individual.
- **LR test M1 vs M2** (df = 6): ¿bastan los 3 atributos para explicar los shares?
- Auxiliar descriptivo: regresión OLS de los 9 ASCs sobre los atributos de los ítems
  (n=10 — solo ilustrativo, para el reporte, no inferencia).

### 4.3 M3 — MNL con ASCs + interacciones demográficas (Set A) — **candidato a preferido**

```
U_nj = ASC_j + β_price_west · price_j · west_n
             + β_oil_age    · oiliness_j · age_n
             + β_oil_west   · oiliness_j · west_n        (9 + 3 parámetros)
```

- `west_n = eastwest_current` (0/1); `age_n = age_group` (0–5, entra lineal; robustez con
  dummy `age_group ≥ 3`).
- **Interpretación correcta:** los efectos "promedio" de los atributos viven dentro de los
  ASCs; cada β de interacción mide la **desviación** de un segmento respecto del promedio.
  No existe β_price principal en este modelo (§0.3) — no usarlo para simular precios.
- Hipótesis: `β_oil_west < 0` (oeste de Japón prefiere sabores más ligeros — README del
  dataset); `β_oil_age > 0` (mayores prefieren toro/anago); `β_price_west < 0`
  (frugalidad relativa del oeste — exploratoria).
- LR test M2 vs M3 (df = 3) justifica la heterogeneidad.

### 4.4 M1r — Variante restringida de M3

Eliminar interacciones con |z| < 1.96 y re-estimar; LR test de parsimonia contra M3.

### 4.5 M4 — Nested Logit sobre ranking explotado (Set A)

**Datos:** explosión de ranks 1–3 (rank-ordered logit, Beggs–Cardell–Hausman 1981): cada
usuario aporta 3 pseudo-elecciones con choice sets decrecientes (10, 9 y 8 alternativas).
Esto aporta la información de sustitución observada ("qué elijo cuando mi favorito no
está") que identifica los λ con datos reales y no solo forma funcional.

**Utilidad:** ASCs (como M2). **Nidos** (por ingrediente principal, con los ítems correctos):

| Nest | Ítems (alt code Apollo) | Lógica |
|---|---|---|
| **akami** | maguro (3), toro (8), tekka_maki (9) | Atún en tres formatos — sustitución fuerte esperada |
| **seafood_other** | ebi (1), anago (2), ika (4), uni (5), ikura (6) | Otros productos del mar |
| **non_seafood** | tamago (7), kappa_maki (10) | Huevo y vegetal — opciones "de descanso" |

- λ_k estimados libres; test t H0: λ_k = 1 por nido; LR test global M4 vs M2-explotado.
- Hipótesis: λ_akami claramente < 1 (si toro no está, la segunda opción es maguro).
- Caveat a declarar: la explosión asume IIA entre etapas del ranking y coeficientes
  estables entre etapas (test de robustez: comparar M2 con ranks 1–3 vs solo rank 1).

### 4.6 M5 — Mixed Logit sobre ranking explotado (Set A) — *opcional, si el tiempo alcanza*

- Especificación tipo M1 (atributos, sin ASCs) con `β_oil_n ~ N(μ, σ²)`;
  panel: `indivID = user_id` sobre las 3 pseudo-elecciones → σ identificado por la
  consistencia intra-persona.
- 500 Halton draws; boundary LR test H0: σ = 0 con distribución ½χ²(0)+½χ²(1)
  (valor crítico 5% = 2.71).
- Variante log-normal en −β_price solo si M1/M6 arrojan β_price < 0 estable.

### 4.7 M6 — MNL de atributos (Set B, sampled)

Misma especificación que M1 sobre `sushi3b_choice_long.csv` (choice sets variables dentro
del universo de 100 ítems, mucha más variación de atributos: precio [1.0–4.5], oiliness
completo). Roles:

1. Validación externa de los betas de M1 (¿mismos signos y magnitudes comparables?).
2. Modelo base de los escenarios C y D (ítems fuera del Set A).
3. Aquí sí se pueden agregar `style` (maki dummy) y `major_group` como regresores — con
   100 ítems y sin ASCs no hay colinealidad.

---

## 5. EDA — `01_eda_visualizations.py`

### 5.1 Figuras

| # | Archivo | Contenido |
|---|---|---|
| fig01 | `choice_shares_setA.png` | Bar chart: share de rank-1 por ítem (Set A) |
| fig02 | `item_attribute_map.png` | Scatter precio × oiliness, tamaño = share, etiquetas por ítem (reemplaza los boxplots v1 — los atributos son constantes por ítem, un boxplot degenera a un punto) |
| fig03 | `rank_distribution.png` | Distribución de ranks 1–10 por ítem (heatmap ítem × rank) |
| fig04 | `attribute_correlation.png` | Heatmap 3×3 con los 10 ítems del Set A + versión con los 100 ítems |
| fig05 | `choice_by_region_heatmap.png` | Región actual × sushi preferido (shares por fila) |
| fig06 | `choice_by_age_gender.png` | Shares por grupo etario y género |
| fig07 | `eastwest_preferences.png` | Este vs oeste: diferencia en share por ítem (diverging bars) |
| fig08 | `oiliness_by_eastwest.png` | Oiliness promedio del ítem elegido, este vs oeste, por edad |
| fig09 | `setB_chosen_vs_sampled.png` | Set B: atributos de elegidos vs muestreados |
| fig10 | `price_sensitivity_region.png` | Share de ítems caros (> mediana de precio) por región |
| fig11 | `substitution_dendrogram.png` | Clustering jerárquico de ítems por correlación de ranks entre usuarios — evidencia empírica previa para los nidos de M4 |

### 5.2 Tablas resumen

| # | Archivo | Contenido |
|---|---|---|
| 01 | `choice_shares.csv` | Shares Set A: count, %, acumulado |
| 02 | `attribute_summary.csv` | Atributos por ítem (una fila por ítem — sin SD intra-ítem) |
| 03 | `user_demographics.csv` | Distribución de gender, age, region, eastwest, moved |
| 04 | `rank_summary.csv` | Rank promedio y mediano por ítem, total y por este/oeste |
| 05 | `region_crosstab.csv` | Contingencia región × sushi preferido (+ test χ²) |

---

## 6. Escenarios — `04_scenario_analysis.py`

### 6.0 Motor de simulación (aplica a todos los escenarios)

Los escenarios de precio requieren un β_price y los ASCs a la vez, que ninguna
especificación estima junta (§0.3). Se usa el enfoque estándar de **calibración de
constantes** (Train, cap. de forecasting):

```
V_j = C_j + β·X_j    con β tomado de M1 (Set A) o M6 (Set B, escenarios C/D)
     y C_j calibrado tal que el escenario base reproduce los shares observados
```

- Para efectos por segmento se agregan las interacciones de M3.
- Outputs siempre: shares base vs contrafactual, Δ en puntos porcentuales, y elasticidades
  (propia y cruzadas) cuando la intervención es de precio.
- Caveat IIA a declarar: con MNL calibrado, la sustitución es proporcional a shares;
  el escenario A se re-simula también con M4 (NL) para contrastar.

### Escenario A — "Toro escasea" (shock de oferta)

| Parámetro | Valor |
|---|---|
| Intervención | `price_norm` de toro +40% |
| Justificación | Sobrepesca de atún rojo — cuotas de pesca en Japón |
| Modelo | Motor §6.0 con β de M1 → contraste con M4 (NL) |
| Hipótesis | Con NL, la demanda migra dentro del nido akami (maguro, tekka_maki) más que proporcionalmente; con MNL calibrado, proporcional a shares. La diferencia entre ambos ES el hallazgo |
| Output | Tabla 14: shares base/MNL/NL, elasticidades propias y cruzadas |

### Escenario B — "Promoción saludable" (salud pública)

| Parámetro | Valor |
|---|---|
| Intervención | kappa_maki −30% precio + campaña que sube su `freq_sold` al p75 |
| Justificación | Campaña gubernamental de alimentación ligera |
| Modelo | Motor §6.0 con β de M1; heterogeneidad por edad/región vía interacciones de M3 |
| Hipótesis | Efecto absoluto pequeño (share base 0.7%) — el hallazgo honesto es que precio no basta para mover un ítem impopular; discutir qué sí (disponibilidad, hábito) |
| Output | Tabla 15: Δ shares total y por segmento (edad × este/oeste) |

### Escenario C — "Entrada de sushi occidental" (competencia)

| Parámetro | Valor |
|---|---|
| Intervención | Nuevo ítem `california_roll`: price=1.5, oiliness=2.0, style=maki |
| Justificación | Cadena americana entra al mercado japonés |
| Modelo | **M6 (Set B)** — al predecir con atributos (sin ASC del ítem nuevo), el modelo de atributos es el único honesto. Supuesto declarado: la "calidad no observada" del ítem nuevo = promedio de los maki existentes; análisis de sensibilidad con ±0.5 en esa constante |
| Hipótesis | Share modesto; canibalización proporcional (IIA) — declarar que la afirmación "canibaliza principalmente maki" requiere el supuesto de nidos, no sale del MNL |
| Output | Tabla 16: share predicho del entrante (rango según sensibilidad), canibalización por ítem |

### Escenario D — "Campaña regional Kinki" (política cultural)

| Parámetro | Valor |
|---|---|
| Intervención | −20% `price_norm` en ítems tradicionales de Kansai — `battera`, `saba`, `tai`, `hamo` (verificados presentes en `sushi_items.csv`) — para usuarios con `current_region = Kinki` |
| Justificación | Preservación de patrimonio culinario regional |
| Modelo | **M6 (Set B)** — estos ítems no están en Set A |
| Hipótesis | Incremento de share concentrado en consumidores Kinki; spillover ~0 en otras regiones (la intervención es segmentada) |
| Output | Tabla 17: Δ share por región, costo-efectividad relativa (Δshare / %descuento) |

---

## 7. Apollo R — Especificaciones

### 7.1 `apollo_config.R` (corregido)

```r
# === Sushi Set A — Apollo Configuration ===
# alt code = alt_id + 1 (Apollo requiere códigos 1-based)
SUSHI_ITEMS_A <- c("ebi", "anago", "maguro", "ika", "uni",
                   "ikura", "tamago", "toro", "tekka_maki", "kappa_maki")  # 10 nombres
ALT_CODES <- setNames(1:10, SUSHI_ITEMS_A)
REF_ALT   <- "ebi"

NEST_MAP <- list(
  akami         = c(3, 8, 9),          # maguro, toro, tekka_maki
  seafood_other = c(1, 2, 4, 5, 6),    # ebi, anago, ika, uni, ikura
  non_seafood   = c(7, 10)             # tamago, kappa_maki
)

APOLLO_CTRL_FIRSTCHOICE <- list(modelName = "SUSHI_A", indivID = "user_id",
                                panelData = FALSE, seed = 42,
                                nCores = max(1, parallel::detectCores() - 1))
# Para modelos sobre ranking explotado (M4, M5): 3 pseudo-obs por usuario
APOLLO_CTRL_EXPLODED    <- modifyList(APOLLO_CTRL_FIRSTCHOICE,
                                      list(modelName = "SUSHI_A_EXP", panelData = TRUE))
N_DRAWS_MXL <- 500
EXPLODE_DEPTH <- 3   # ranks 1-3
```

### 7.2 `apollo_data_prep.R`

- Lee `sushi3a_choice_long.csv`; usa `alt_id` como índice de alternativa.
- Pivot a wide (una fila por pseudo-elección): `price_1..price_10`, `oil_1..oil_10`, etc.
- Genera la versión explotada (ranks 1–3) con columna `availability`: en la etapa k,
  los ítems con rank < k tienen avail = 0.
- Estandarización z-score de atributos **pooled sobre los 10 ítems** (documentar media/SD
  usadas para poder des-estandarizar los WTP).

### 7.3 Scripts de modelos

| Script | Modelos | Notas |
|---|---|---|
| `01_apollo_mnl.R` | M1, M2, M3 | Primera elección; validación cruzada de los resultados Python (mismos LL y betas ±1e-4) |
| `02_apollo_nested_logit.R` | M4 | Ranking explotado; λ libres; t-test λ=1 y LR vs M2 explotado |
| `03_apollo_mixed_logit.R` | M5 (opcional) | Explotado, panelData=TRUE, 500 Halton |

---

## 8. Tablas de resultados

| # | Archivo | Contenido |
|---|---|---|
| 09 | `mnl_attributes_results.csv` | M1: coef, SE, z, p, IC 95% |
| 09b | `mnl_asc_results.csv` | M2: ASCs + LR test M1 vs M2 |
| 10 | `wtp_results.csv` | WTP de M1 y M6 (delta method), en unidades de precio normalizado |
| 11 | `interactions_results.csv` | M3: interacciones + LR M2 vs M3 + variante restringida (M1r) |
| 12 | `nested_logit_results.csv` | M4: λ_k, SE, t-test λ=1, LR test |
| 12b | `mixed_logit_results.csv` | M5 (si se estima): μ, σ, boundary LR |
| 13 | `model_comparison.csv` | LL, ρ², ρ²_adj, AIC, BIC, K, N para M1/M2/M3/M4/(M5)/M6 — nota al pie: M4/M5 usan datos explotados, sus LL no son comparables directos con M1–M3 |
| 14 | `scenario_A_toro.csv` | Shares base/MNL/NL + elasticidades |
| 15 | `scenario_B_kappa.csv` | Δ shares total y por segmento |
| 16 | `scenario_C_entry.csv` | Share entrante (con sensibilidad) + canibalización |
| 17 | `scenario_D_kinki.csv` | Δ share por región |

---

## 9. Cronograma de implementación

### Fase 0 — Datos (COMPLETADA 2026-07-04)

| Paso | Estado |
|---|---|
| Corregir mapeo Set A + recodificar oiliness en `process_sushi_dataset.py` | ✔ |
| Regenerar los 6 CSVs + data dictionary | ✔ |
| `verify_sushi_dataset.py` ampliado — 47/47 checks | ✔ |

### Fase 1 — EDA

| Paso | Comando | Output |
|---|---|---|
| 1 | `python scripts/01_eda_visualizations.py` | 11 figuras + 5 tablas |

### Fase 2 — Modelos (COMPLETADA 2026-07-04, Python + Apollo ejecutados)

| Paso | Comando | Output | Estado |
|---|---|---|---|
| 2 | `python scripts/02_estimate_models.py` | M1, M2, M3, M6 → tablas 09–11, 13 | ✔ |
| 3 | `python scripts/03_exploded_models.py` | M4/M4b → tablas 12, rank_stability | ✔ |
| 4 | `R_Studio/01_apollo_mnl.R` | Validación cruzada M1–M3 | ✔ ejecutado — paridad LL ≤ 0.004 |
| 5 | `R_Studio/02_apollo_nested_logit.R` | Validación M2exp + M4b | ✔ ejecutado — paridad ≤ 0.01 (M4 libre solo en Python: frontera λ→0 revienta BGW) |
| 5b | `R_Studio/03_apollo_latent_class.R` + `04_lc_postprocess.R` | **M5-LC clases latentes** → latent_class_{results,selection,profiles}.csv | ✔ ejecutado — LC3 mejor por BIC (LL −28513.7); clases: gourmet premium 33.7% / gusto ligero 31.3% / fanático del atún 34.9% |

**Resultados clave (referencia para el reporte):**

- Cadena LR: M1 (LL −9850.7) → M2 (−9755.1) → M3 (−9733.2); ambos tests rechazan
  (p < 1e-8). Los 3 atributos explican R² = 0.95 de los ASCs (OLS descriptivo).
  **M3 = modelo preferido** para insights de comportamiento.
- `b_oil_x_age = +0.089 (z = 5.2)`: los mayores eligen más graso — hipótesis confirmada.
  Las interacciones con West son individualmente débiles pero **conjuntamente**
  significativas (LR = 15.6, df = 2, p = 4e-4) — multicolinealidad price↔oiliness.
- **β_price > 0 confirmado** (M1 +0.58, M6 +0.25): precio como señal de calidad, el WTP
  no es interpretable monetariamente (advertencia escrita en `wtp_results.csv`).
- M4 NL: LR vs MNL = 668.7 (p ≈ 0) — IIA rechazada. λ_akami = 0.33, λ_seafood = 0.34,
  λ_non_seafood → 0 (nido degenerado; variante M4b con λ = 1 pierde por BIC, se reportan
  ambas). Sustitución dentro del nido atún confirmada → clave para el Escenario A.
- Rank-stability: deriva de ASCs de hasta 6 SEs entre rank-1 y ranks 1–3 (maguro y
  tekka_maki son "segunda opción segura"; uni polariza). Declarar como limitación de la
  explosión y como evidencia de heterogeneidad (motiva M5 si se estima).
- Sensibilidad sin los 4 autores del dataset: Δcoef máx = 0.003 — irrelevante.

### Fase 3 — Escenarios

| Paso | Comando | Output |
|---|---|---|
| 6 | `python scripts/04_scenario_analysis.py` | Escenarios A y B (tablas + figuras). C y D eliminados con M6 (v3) |

### Fase 4 — Entregables (v3, 2026-07-06; pendiente revisión final del autor)

| Paso | Output | Estado |
|---|---|---|
| 7 | `outputs/report.pdf` (20 págs, español, portada Tarea 1 con logo DII) | ✔ v3: M6 y escenarios C/D eliminados; 3 modelos renumerados M1/M2/M3; layout arreglado (sin overfull); WTP y escenarios re-basados en MNL-atributos; Apéndice B con mapeo informe↔script. **La prosa interpretativa debe ser revisada y hecha propia por el autor: la pauta prohíbe redactar el texto del informe con IA generativa** |
| 8 | **Link a carpeta compartida** con datos y scripts | ⚠ PENDIENTE — placeholder visible en informe (Linkografía) y presentación (slide final); reemplazar antes de entregar |
| 9 | `outputs/presentation.pdf` (11 slides, inglés, executive pitch) | ✔ v3: renumerado M1/M2/M3, slide de Escenario B en vez de C, λ del NL corregidos, co-autor añadido; mismo pendiente de link |

---

## 10. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Atributos constantes por ítem → tentación de "meter ASCs y betas juntos" en algún script | Media | §0.3 y §4.0 lo prohíben por diseño; `02_estimate_models.py` valida rango de la matriz de diseño antes de optimizar |
| β_price > 0 en M1 (precio como señal de calidad: toro caro y favorito) | **Alta** | No es un error: discutirlo como confounding calidad-precio. M6 (Set B, 100 ítems) y el control por oiliness ayudan a separarlo; si persiste, los WTP se reportan con la advertencia correspondiente |
| corr(price, oiliness) = 0.82 en Set A (verificado en EDA) → SEs inflados en M1, WTP inestable | **Alta** | Reportar correlaciones junto a M1; WTP definitivos desde M6 (Set B); robustez de M1 quitando un atributo a la vez |
| Explosión de ranks asume estabilidad de preferencias entre etapas | Media | Robustez: re-estimar M2 con ranks 1–3 vs solo rank 1 y comparar betas |
| λ de nido `non_seafood` (2 ítems, shares 0.7% y 4.1%) inestable | Media | Aceptable si converge; si no, colapsar a 2 nidos (akami vs resto) |
| WTP en unidades de precio normalizado, no JPY | Baja | Interpretación relativa declarada en el reporte (trade-off entre atributos) |
| Usuarios 323, 617, 1431, 4667 son los autores del dataset | Baja | Análisis de sensibilidad excluyéndolos |
| SEED=42 en el muestreo del Set B | Media | Robustez de M6 con seed alternativo (una corrida) |
| Sobre-alcance: 6 modelos + 4 escenarios para una presentación de 8 min | Media | M5 marcado opcional; presentación usa solo M3 + M4 + 2 escenarios estrella |

---

## 11. Referencias

- Kamishima, T. (2003). "Nantonac Collaborative Filtering: Recommendation Based on Order Responses." *KDD2003*, pp. 583-588.
- Train, K. (2009). *Discrete Choice Methods with Simulation.* Cambridge University Press. Caps. 3 (MNL, forecasting y calibración de constantes), 4 (NL), 6 (MXL).
- Beggs, S., Cardell, S. & Hausman, J. (1981). "Assessing the potential demand for electric cars." *Journal of Econometrics*, 17(1), 1-19. (Rank-ordered logit.)
- McFadden, D. (1978). "Modelling the choice of residential location." *Spatial Interaction Theory and Planning Models*, pp. 75-96. (Sampling of alternatives.)
- Hess, S. & Palma, D. (2019). "Apollo: A flexible, powerful and customisable freeware package for choice model estimation." *Journal of Choice Modelling*, 32, 100170.
