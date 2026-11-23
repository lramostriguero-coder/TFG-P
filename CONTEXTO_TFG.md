# Contexto del TFG — Predicción de la demanda diaria de urgencias

Resumen de todo lo trabajado hasta ahora (actualizado el 15/11/2026, tras las revisiones de la tutora del 11/11 y el 12/11 y la llegada de los datos de enero–junio de 2026), para retomar el trabajo con el código.

Las revisiones de la tutora se guardan en la carpeta `Silvia/`, con el nombre `AAAAMMDD-Revisión SJF.md`.

## 1. El proyecto

- **Título:** Predicción de la demanda diaria de urgencias hospitalarias mediante modelos de aprendizaje automático.
- **Alumna:** Paula Fernández Sánchez · **Tutora:** Silvia Jiménez Fernández · **Cotutor:** Alberto Palomo Alonso.
- **Objetivo:** predecir las llegadas diarias a urgencias con 1 a 7 días de antelación, con incertidumbre y desglose por áreas (Pediatría, Ginecología-Obstetricia y resto).
- **Documento de referencia:** `ANTEPROYECTO_borradoractpaula.pdf`.

### Reglas de trabajo

1. **El anteproyecto es el esqueleto.** Se pueden hacer cosas que no aparecen en él siempre que cada paso tenga **un motivo** (una pregunta concreta que responde), siga **un orden lógico** (de lo más sencillo a lo más complejo, y cada modelo se compara con el anterior) y quede **documentado** el porqué y el resultado. No se añaden variables, pruebas ni métodos «por si acaso», sin una pregunta detrás. (Revisión de la tutora, 11/11/2026; sustituye a «ceñirse al anteproyecto».)
2. **Ir paso a paso** y explicar cada cosa: qué se hace, por qué y con un ejemplo concreto con números reales.
3. **Entregables sencillos**, como si los hubiera hecho Paula: Excel con fórmulas visibles y formato simple.
4. Distinguir siempre lo que sale de **fuentes oficiales** de lo que es **criterio propio**.
5. **Los datos de pacientes nunca se suben a GitHub** (`datos/` está en `.gitignore`, salvo `datos/externos/`).

## 2. Datos

| Fichero | Qué contiene |
|---|---|
| `episodios (AAAA).sql` 2022–2025 | Un episodio de urgencias por fila. **778.472 episodios** |
| `codificacion (AAAA).sql` 2022–2025 | Códigos CIE-10 de cada episodio. **3.816.119 filas** |
| `sql_2026/sql_2026/episodios.sql` y `codificacion.sql` | Enero–junio de 2026 (llegaron el 12/11/2026). **98.727 episodios** (65 llegaron en diciembre de 2025 y salieron en 2026) y 477.583 códigos |
| `prd_unificado.sql` | Predicciones del **sistema actual del hospital** (una fila por día, sep-2024 a may-2026, 537 filas, faltan 81 días). No son llegadas reales: sirven para comparar en la Fase 2 |

- Carpeta local con los datos: `C:\PAULA\UNI\TFG\Datos_urgencias`.
- Son volcados de phpMyAdmin (`INSERT INTO ...`) y se leen sin base de datos con `tfg/lectura_sql.py` (episodios y codificación) y `tfg/cargar_sql.py` (prd_unificado).
- Indicación de la tutora: **el número real se obtiene contando los episodios por fecha** (`fecha_inicio`).
- Los ficheros parecen repartidos por **fecha de salida**: el de 2026 trae episodios que llegaron a finales de 2025. No hay episodios repetidos entre ficheros.
- En total: **877.199 episodios** y 4.293.702 códigos (01/01/2022–30/06/2026).

## 3. Fase 1 — Base de datos entrenable

### Paso 1 · Ingesta y curación — ✅ `tfg/fase1_paso1_ingesta.py`

- Une los ficheros de 2022–2025 y el de enero–junio de 2026, de episodios y de codificación.
- **Duplicados:** no hay episodios duplicados. Se corrigió un error del script que borraba un registro de codificación que no era duplicado (mismo episodio y orden, códigos distintos: se conserva).
- **Incompletos e incoherentes:** se **marcan** con columnas `flag_*`, no se borran (~6,4 % de los episodios). **Todos se cuentan como llegadas** (tutora, 11/11/2026): son personas que llegaron a urgencias, aunque no se sepa si se fueron sin triaje o si no se guardó el resultado. Las marcas solo documentan la calidad del dato:
  `flag_sin_triaje` (6.919), `flag_triaje_incoherente` (1.855), `flag_estancia_larga` >72 h (1.240), `flag_fuera_periodo` (60: llegada antes de 2022), `flag_sin_diagnostico` (50.194), `flag_fin_antes_inicio` (0), `flag_edad_invalida` (2: fecha de nacimiento imposible, edad vacía). Cifras con 2026 incluido.
- **Homogeneización:**
  - Tipos: fechas como fechas, números como números; vacíos unificados; fechas imposibles (`1900-01-00`) → vacías.
  - `nivel_triaje`: 1 a 5 (había más de 10 formas de escribirlo).
  - `edad`: **años cumplidos el día de la llegada** (número entero), calculados con `f_nacimiento` y `fecha_inicio`. La edad del fichero era decimal y estaba redondeada a 2 decimales (a quien le faltaba 1 día para cumplir 16 le salía 16,00). Así un mismo paciente tiene la edad que tenía en cada episodio. Corregido el 04/11/2026: 30 episodios pasaron a PED (28 de GEN y 2 de GIN); las llegadas totales y los parámetros de normalización no cambian.
  - `area`: **PED** si edad < 16; **GIN** si servicio es Urgencias Ginecológicas, Urgencias Obstétricas u Obstetricia; **GEN** el resto. **La edad tiene prioridad sobre el servicio:** una paciente de menos de 16 años atendida en Ginecología u Obstetricia cuenta como PED. Este corte queda **fijado para este trabajo**, sin consultarlo al hospital (tutora, 11/11/2026).
  - `es_ingreso`: sí si `motivo_alta = "HOSPITALIZACION U"`.
  - `dx_capitulo`: capítulo CIE-10 del diagnóstico principal (22 grupos).
  - `duracion_min`: tiempo en urgencias.
- Columnas descartadas: `fuente`, `resp_final`, `resp_ing`, `fecha_ing` (vacías), `resp_acl`, `resp_alta` (profesional), `tipo_acto` (constante), `f_nacimiento` (dato personal; solo se usa para calcular `edad`).
- Salida: `datos/procesados/episodios_limpios.parquet`, `codificacion_limpia.parquet` e informe `informes/fase1_paso1_calidad.md`.

### Paso 2 · Serie diaria continua — ✅ `tfg/fase1_paso2_serie_diaria.py`

- **1.642 días** (01/01/2022–30/06/2026), sin huecos en el calendario. Los 4 días incompletos se quedan, con los conteos **en blanco** (ver abajo).
- Columnas: `llegadas` (lo que se predice), `llegadas_PED`, `llegadas_GIN`, `llegadas_GEN` (suman `llegadas`), `salidas` (solo referencia), `particion`.
- **División del conjunto de datos: dos experimentos** (tutora, 12/11/2026; sustituye a la división A/B del 11/11/2026). Siempre **cronológica**. Se elige con el parámetro `EXPERIMENTO` del paso 2; para cambiarlo basta con cambiar esa línea y volver a ejecutar los pasos 2, 7 y 8.

| Experimento | Entrenamiento | Validación | Test |
|---|---|---|---|
| **1** (el que está puesto; toda la Fase 2) | 01/01/2022–30/06/2024 · 912 días (71 %) | 01/07/2024–30/06/2025 · 365 días (29 %) | 01/07/2025–30/06/2026 · 365 días |
| **2** (solo el mejor modelo, al final) | 2022–2024 · 1.096 días (75 %) | 2025 · 365 días (25 %) | 01/01/2026–30/06/2026 · 181 días |

  - En el experimento 1, validación y test no son años naturales, pero cada uno abarca **12 meses seguidos**: recorren todas las estaciones. Las predicciones del hospital (sep-2024 a may-2026) cubren casi todo el test.
  - En el experimento 2 se usa la **misma familia de modelos** y se vuelven a buscar los hiperparámetros en su validación (2025), nunca mirando el test del experimento 1. Los datos de 2026 no se usan para entrenar ni ajustar nada.
  - **Los dos experimentos se comparan sobre enero–junio de 2026** (está en el test de los dos). Pregunta: ¿entrenar con datos más recientes mejora la predicción?
  - El test se usa **una sola vez**, al final.
- Salida: `datos/procesados/serie_diaria.csv` y `informes/fase1_paso2_serie_diaria.png`.

### Días incompletos — ✅ dato faltante, sin imputación (tutora, 11/11/2026)

| Día | Problema |
|---|---|
| 14/04/2023 | Casi no hay salidas en todo el día (90 de ~500) |
| 16/06/2023 | Ninguna salida de 14:00 a 23:59 |
| 24/05/2024 | 408 llegadas (lo normal ese mes, unas 565), bajas durante todo el día y sin un corte horario. Las salidas cuadran con las llegadas, pero el número no es creíble: se marca por decisión de Paula (23/11/2026) |
| 30/06/2026 | Faltan los pacientes que salieron en julio de 2026 (no hay fichero): de 21:00 a 23:59 solo hay 8 llegadas (lo normal, unas 70) |

El número de llegadas de esos días **no es un dato real**. Son **valores faltantes** (*missing values*, `NaN`) y se tratan **sin imputación**:

- Los 4 días se quedan en la serie, pero `llegadas`, `llegadas_PED`, `llegadas_GIN`, `llegadas_GEN` y `salidas` van **en blanco** (`NaN`). No se rellenan con ningún valor (ni el día anterior, ni la semana anterior, ni medias).
- El calendario y la meteorología de esos días **sí están rellenos**, porque son correctos.
- Con el experimento 1 quedan 3 días en blanco en entrenamiento (2023 y 2024) y 1 en test (30/06/2026): entrenamiento tiene 909 días con dato, validación 365 y test 364.
- **El 31/12/2025 se ha recuperado** (15/11/2026): estaba incompleto porque faltaban los pacientes que salieron en 2026, y el fichero de 2026 trae 61. Ahora tiene 427 llegadas y la misma proporción salidas/llegadas que el 31/12/2024 (1,12). El 30/12/2025 y el 23/12/2025 ganan 3 y 1 (estancias largas); se cuentan como completos, igual que se hizo con el resto de días.
- El resto de 2026 se revisó igual que 2022–2025 (salidas por hora y caídas de llegadas) y no hay más días incompletos.
- **24/05/2024:** a diferencia de los otros, no tiene un corte horario: las llegadas son bajas durante todo el día. Se marca como dato faltante por decisión de Paula (23/11/2026); conviene comentárselo a la tutora.
- La gráfica del paso 2 muestra en rojo lo que se llegó a registrar esos días, para documentarlo.
- (Hasta el 11/11/2026 se borraban las filas y la serie tenía 1.458 días; se cambió porque el anteproyecto pide una serie sin discontinuidades.)

Consecuencias para la Fase 2 (lo gestiona el modelo):
- Al **entrenar**, esos días no se usan como objetivo; al **evaluar**, no se puntúan.
- Si un día en blanco hace falta como entrada (por ejemplo, el retardo «día anterior»), esa entrada queda en blanco. SARIMAX (filtro de Kalman) y XGBoost lo admiten; en los modelos que no, se descarta esa muestra y se indica cuántas se han descartado.

### Paso 7 · Variables exógenas — ✅ `tfg/fase1_paso7_variables_exogenas.py`

**Calendario** (fuentes oficiales):
- `anio`, `mes`, `dia_mes`, `dia_anio`, `semana_anio`, `dia_semana` (0 = lunes … 6 = domingo), `fin_de_semana`.
- `festivo` y `nombre_festivo`: decretos de fiestas laborales de la Comunidad de Madrid 2022–2026 (54 días hasta el 30/06/2026; los de 2026 del Decreto 75/2025, BOCM núm. 229 de 25/09/2025). Validados también con la librería `holidays`. No se incluyen las fiestas locales.
- `vacaciones_escolares`, `tipo_vacaciones` y `dia_lectivo`: calendarios escolares oficiales de Infantil y Primaria de la Comunidad de Madrid, cursos 2021-22 a 2025-26. El 2025-26, con la Orden 1476/2025 (BOCM núm. 113, 13/05/2025) y el «Cuadro síntesis informativo» de la Consejería de Educación: Navidad del 20/12/2025 al 06/01/2026, Semana Santa del 28/03 al 05/04/2026, no lectivos 07/01, 27/03 y 06/04/2026, último día lectivo 19/06/2026.

**Meteorología:** Open-Meteo (reanálisis ERA5), punto más cercano al hospital (zona de Majadahonda). Fichero `datos/externos/meteo_open_meteo_2022_2026.csv` (01/01/2022–30/06/2026) con `temp_max`, `temp_min`, `temp_media`, `precipitacion`, `humedad`, generado con `tfg/descargar_meteo.py`. Los días de 2022–2025 coinciden exactamente con la descarga original del 26/10/2026.

**Meteorología: no usar el tiempo real de los días que se predicen** (tutora, 11/11/2026). La meteorología del fichero es la **observada** (reanálisis), no una previsión. Se predice al final del día *t*, con los datos hasta *t*, para los días *t+1 … t+7*; como entrada solo se usa la meteorología **hasta el día *t***. Las variables de calendario de los días que se predicen sí se pueden usar, porque se conocen de antemano. **Previsiones del tiempo: no se usan** (revisado el 23/11/2026). Open-Meteo guarda previsiones antiguas de dos formas: la *Historical Forecast API* (desde 2021-2022) une las primeras horas de cada ejecución del modelo, así que es casi lo observado y no una previsión a varios días; la *Previous Runs API* sí da la previsión hecha 1 a 7 días antes (`temperature_2m_previous_day1 … day7`), pero solo desde enero de 2024 para la mayoría de modelos. No cubre el entrenamiento (2022–06/2024), así que no se puede entrenar con ella. Se queda la meteorología observada hasta el día *t*.

**Quitado en la Fase 1 por no tener una pregunta detrás:** puentes, vísperas y post-festivos, Nochebuena/Nochevieja, calor extremo, logaritmo de la lluvia, pruebas de Mann-Whitney y VIF. La relevancia de las variables exógenas **sí se estudia, en la Fase 2**, comparando el modelo con y sin exógenas (ver sección 4).

Salida: `datos/procesados/dataset_fase1.csv`.

### Paso 8 · Normalización — ✅ `tfg/fase1_paso8_normalizacion.py`

- **Continuas** (llegadas y desgloses, temperaturas, precipitación, humedad): **min-max**, `(x − mínimo) / (máximo − mínimo)`. Columnas `…_normalizada`. (Antes era estandarización `(x − media) / desviación`; se cambió el 29/10/2026 por indicación de Paula.)
- **Mínimo y máximo solo con el entrenamiento del experimento elegido** (experimento 1: 01/2022–06/2024, 909 días con llegadas y 912 con meteorología), para evitar fuga de datos. Los días en blanco no cuentan y siguen en blanco después de normalizar. En entrenamiento todo va de 0 a 1; en validación y test algún día se sale un poco (p. ej. `llegadas_PED` −0,125 en validación y `llegadas_GIN` 1,058 en test).
  - Ejemplo: llegadas mínimo 364 y máximo 735 → 01/01/2022: (521 − 364) / (735 − 364) = 0,423.
  - Temperatura mínima: de −5,5 a 25,4 °C (los días bajo cero quedan en 0 o cerca). Precipitación: de 0 a 77,5 mm, sin logaritmo. Humedad: de 17 a 98 %. (Con el experimento 2, la temperatura mínima llega a 25,6 °C.)
  - `parametros_normalizacion.csv` guarda también las fechas del entrenamiento usado (`entrenamiento_desde`, `entrenamiento_hasta`).
- **Cíclicas** (`dia_semana`, `mes`, `dia_anio`): seno y coseno con periodo 7, 12 y 365,25. Decidido mantenerlas.
- **Binarias** (`fin_de_semana`, `festivo`, `vacaciones_escolares`, `dia_lectivo`): se dejan igual.
- Salida: `datos/procesados/dataset_fase1_normalizado.csv` y `parametros_normalizacion.csv` (para desnormalizar las predicciones con `desnormalizar()`).

### Excel de la Fase 1

En `C:\PAULA\UNI\TFG\Datos_urgencias\FASE1` hay dos Excel con las fórmulas visibles: `datos_urgencias_fase1.xlsx` (unificación, errores, serie diaria y resumen) y `variables_exogenas_y_normalizadas_fase1.xlsx` (leyenda, variables exógenas, datos de entrenamiento, parámetros de normalización, normalización, festivos y calendario escolar). Actualizados el 15/11/2026: **1.642 días** (hasta el 30/06/2026), los días incompletos con llegadas y salidas en blanco (columna «Nota»; el 24/05/2024 añadido el 23/11/2026), partición del experimento 1 (fórmula con las fechas de corte), «Datos entrenamiento» con 01/2022–06/2024, festivos de 2026 y calendario escolar hasta junio de 2026. Las fórmulas que leen las llegadas devuelven vacío en los días en blanco, para que Excel no los tome como 0. Coinciden con Python (diferencias < 0,0001 por el redondeo) y no tienen errores de fórmula. Copias previas en `FASE1\copia_antes_datos_2026\` y `FASE1\copia_antes_revision_20261111\`. Para el experimento 2 hay que cambiar las fechas de la fórmula de partición y el rango de «Datos entrenamiento». Si se modifica, cerrarlo antes en Excel para no perder cambios.

## 4. Fase 2 — Modelos de predicción (siguiente)

Orden de trabajo (revisiones de la tutora, 11/11/2026 y 12/11/2026):

1. **Baselines:** persistencia (mañana = hoy) y naïve estacional semanal (mismo día de la semana anterior). Son la nota mínima que hay que superar.
2. **ARIMA → SARIMA → SARIMAX**, con el estudio de qué días anteriores usar (abajo). Indicación de la tutora: **empezar por ARIMA**, primero entender el algoritmo (la teoría), después aplicarlo y luego ir mejorando los resultados.
3. **Estudio de relevancia de las exógenas**, empezando en SARIMAX (abajo).
4. **Ensembles de árboles** (árbol de decisión, XGBoost).
5. **Redes neuronales:** tradicionales y profundas (Transformers).

- Horizonte de **1 a 7 días**, con **incertidumbre** de cada predicción.
- Todos con las mismas particiones (**experimento 1**: entrenar con 01/2022–06/2024, elegir configuración en 07/2024–06/2025), las mismas métricas y comparados con los baselines. El test (07/2025–06/2026) se usa **una sola vez**, al final.
- Al final, el **experimento 2** solo con el mejor modelo, y comparación de los dos experimentos sobre enero–junio de 2026.

**Estudio de relevancia de las exógenas** (estudio de ablación): mismo modelo, mismas particiones y mismas métricas, cambiando solo las variables de entrada. Se compara en validación y por grupos: (1) sin exógenas, (2) + calendario, (3) + meteorología, (4) + calendario + meteorología. Se mira cada horizonte (1 a 7 días). Un grupo es relevante si mejora de forma consistente (varios horizontes y varios modelos), no por una mejora pequeña en un caso.

**ARIMA, SARIMA y SARIMAX: qué días anteriores usar.** Objetivo: mostrar y analizar que la elección de los días anteriores cambia la predicción. Paula decide, dejando escrito el razonamiento: qué configuraciones probar y por qué, cómo se traduce cada una a los parámetros de cada modelo, qué consecuencias tiene sobre los datos disponibles para entrenar y cómo le afectan los días en blanco. Se analiza el error en validación por horizonte frente a los baselines, qué días ayudan y a qué horizonte, y si añadir más días mejora o solo complica el modelo, con una tabla resumen, una gráfica de error por horizonte y una conclusión escrita.
- Comparar con el **sistema actual del hospital** (`prd_unificado.sql`) y estudiar métricas de comparación.
- Predicción desagregada por áreas (PED, GIN, GEN).
- **Interfaz** para probar los modelos y visualizar resultados.
- Medios: Python 3.12, entrenamiento en CPU.

## 5. Cómo ejecutar

```bash
python -m venv .venv          # una sola vez; luego usar .venv\Scripts\python.exe
pip install -r requirements.txt
python tfg/fase1_paso1_ingesta.py --origen "C:/PAULA/UNI/TFG/Datos_urgencias"
python tfg/descargar_meteo.py          # solo si hay que volver a descargar la meteorología
python tfg/fase1_paso2_serie_diaria.py
python tfg/fase1_paso7_variables_exogenas.py
python tfg/fase1_paso8_normalizacion.py
```

Los resultados se guardan en `datos/procesados/` (no se suben a GitHub).

## 6. Pendientes

- [x] Método para los 3 días incompletos: eliminarlos (tutora).
- [x] Volver a ejecutar los pasos 1, 2, 7 y 8 sin esos 3 días (29/10/2026): 1.458 días.
- [x] `datos_urgencias_fase1.xlsx` sin esos 3 días ni la columna Incompleto (copia previa en `FASE1\copia_antes_eliminar_incompletos\`).
- [x] `variables_exogenas_y_normalizadas_fase1.xlsx` sin esos 3 días ni la columna Dato_incompleto, y con normalización min-max (`MIN`/`MAX` de «Datos entrenamiento»). Coincide con Python (diferencias < 0,0001 por el redondeo).
- [x] Normalización min-max en el paso 8.
- [x] Unir la rama `fase1-paso1-ingesta` a `main` (lramostriguero-coder/TFG-P#1, 04/11/2026).
- [x] Revisión de la tutora del 11/11/2026 (`Silvia/20261111-Revisión SJF.md`): 3 días incompletos en blanco (`NaN`) en lugar de borrados, 1.461 días, división A/B con el parámetro `DIVISION` (puesta la A).
- [x] Los dos Excel de la Fase 1 con 1.461 días, los 3 días en blanco y la división A (11/11/2026).
- [x] Revisión de la tutora del 12/11/2026 (`Silvia/20261112-Revisión SJF.md`): datos de enero–junio de 2026 en la Fase 1 (1.642 días), días incompletos revisados (se recupera el 31/12/2025; el 30/06/2026 en blanco), festivos y calendario escolar de 2026, meteorología hasta junio de 2026 y parámetro `EXPERIMENTO` 1/2 (puesto el 1). Excel actualizados (15/11/2026).
- [x] 24/05/2024 marcado como dato faltante (llegadas bajas todo el día, sin corte horario), por decisión de Paula (23/11/2026). Excel actualizados (copia previa en `FASE1\copia_antes_marcar_20240524\`).
- [ ] Comentar a la tutora que se ha marcado el 24/05/2024.
- [x] Previsiones meteorológicas históricas: no hay para todo el entrenamiento (Open-Meteo *Previous Runs* empieza en enero de 2024). Se usa la meteorología observada hasta el día *t* (23/11/2026).
- [ ] Fase 2: teoría de ARIMA, baselines y ARIMA con el experimento 1.
