# Contexto del TFG — Predicción de la demanda diaria de urgencias

Resumen de todo lo trabajado hasta ahora (29/10/2026), para retomar el trabajo con el código.

## 1. El proyecto

- **Título:** Predicción de la demanda diaria de urgencias hospitalarias mediante modelos de aprendizaje automático.
- **Alumna:** Paula Fernández Sánchez · **Tutora:** Silvia Jiménez Fernández · **Cotutor:** Alberto Palomo Alonso.
- **Objetivo:** predecir las llegadas diarias a urgencias con 1 a 7 días de antelación, con incertidumbre y desglose por áreas (Pediatría, Ginecología-Obstetricia y resto).
- **Documento de referencia:** `ANTEPROYECTO_borradoractpaula.pdf`.

### Reglas de trabajo

1. **Ceñirse al anteproyecto.** No añadir variables, pruebas estadísticas ni métodos que no aparezcan en él. Si hace falta una decisión que el anteproyecto no fija, se explica y se consulta antes.
2. **Ir paso a paso** y explicar cada cosa: qué se hace, por qué y con un ejemplo concreto con números reales.
3. **Entregables sencillos**, como si los hubiera hecho Paula: Excel con fórmulas visibles y formato simple.
4. Distinguir siempre lo que sale de **fuentes oficiales** de lo que es **criterio propio**.
5. **Los datos de pacientes nunca se suben a GitHub** (`datos/` está en `.gitignore`, salvo `datos/externos/`).

## 2. Datos

| Fichero | Qué contiene |
|---|---|
| `episodios (AAAA).sql` 2022–2025 | Un episodio de urgencias por fila. **778.472 episodios** |
| `codificacion (AAAA).sql` 2022–2025 | Códigos CIE-10 de cada episodio. **3.816.119 filas** |
| `prd_unificado.sql` | Predicciones del **sistema actual del hospital** (una fila por día, sep-2024 a may-2026, 537 filas, faltan 81 días). No son llegadas reales: sirven para comparar en la Fase 2 |

- Carpeta local con los datos: `C:\PAULA\UNI\TFG\Datos_urgencias`.
- Son volcados de phpMyAdmin (`INSERT INTO ...`) y se leen sin base de datos con `tfg/lectura_sql.py` (episodios y codificación) y `tfg/cargar_sql.py` (prd_unificado).
- Indicación de la tutora: **el número real se obtiene contando los episodios por fecha** (`fecha_inicio`).
- No va a llegar ningún dato más: se trabaja solo con lo que hay.

## 3. Fase 1 — Base de datos entrenable

### Paso 1 · Ingesta y curación — ✅ `tfg/fase1_paso1_ingesta.py`

- Une los 4 años de episodios y de codificación.
- **Duplicados:** no hay episodios duplicados. Se corrigió un error del script que borraba un registro de codificación que no era duplicado (mismo episodio y orden, códigos distintos: se conserva).
- **Incompletos e incoherentes:** se **marcan** con columnas `flag_*`, no se borran (~6,4 % de los episodios):
  `flag_sin_triaje` (6.112), `flag_triaje_incoherente` (1.143), `flag_estancia_larga` >72 h (1.064), `flag_fuera_periodo` (60), `flag_sin_diagnostico` (42.850), `flag_fin_antes_inicio` (0).
- **Homogeneización:**
  - Tipos: fechas como fechas, números como números; vacíos unificados; fechas imposibles (`1900-01-00`) → vacías.
  - `nivel_triaje`: 1 a 5 (había más de 10 formas de escribirlo).
  - `area`: **PED** si edad < 16; **GIN** si servicio es Urgencias Ginecológicas, Urgencias Obstétricas u Obstetricia; **GEN** el resto.
  - `es_ingreso`: sí si `motivo_alta = "HOSPITALIZACION U"`.
  - `dx_capitulo`: capítulo CIE-10 del diagnóstico principal (22 grupos).
  - `duracion_min`: tiempo en urgencias.
- Columnas descartadas: `fuente`, `resp_final`, `resp_ing`, `fecha_ing` (vacías), `resp_acl`, `resp_alta` (profesional), `tipo_acto` (constante), `f_nacimiento` (redundante con `edad`).
- Salida: `datos/procesados/episodios_limpios.parquet`, `codificacion_limpia.parquet` e informe `informes/fase1_paso1_calidad.md`.

### Paso 2 · Serie diaria continua — ✅ `tfg/fase1_paso2_serie_diaria.py`

- **1.461 días** (01/01/2022–31/12/2025), sin huecos.
- Columnas: `llegadas` (lo que se predice), `llegadas_PED`, `llegadas_GIN`, `llegadas_GEN` (suman `llegadas`), `salidas` (solo referencia), `dato_incompleto`, `particion`.
- **Particiones cronológicas:** entrenamiento 2022–2023 · validación 2024 · test 2025.
- Salida: `datos/procesados/serie_diaria.csv` y `informes/fase1_paso2_serie_diaria.png`.

### Días incompletos — ⏳ PENDIENTE

| Día | Problema |
|---|---|
| 14/04/2023 | Casi no hay salidas en todo el día (90 de ~500) |
| 16/06/2023 | Ninguna salida de 14:00 a 23:59 |
| 31/12/2025 | Faltan los pacientes que salieron en 2026 (no hay fichero de 2026) |

Están marcados con `dato_incompleto = Sí`. **Falta decidir cómo tratarlos: espera a que la tutora apruebe un método.** Es lo único que falta para cerrar la Fase 1.

### Paso 7 · Variables exógenas — ✅ `tfg/fase1_paso7_variables_exogenas.py`

**Calendario** (fuentes oficiales):
- `anio`, `mes`, `dia_mes`, `dia_anio`, `semana_anio`, `dia_semana` (0 = lunes … 6 = domingo), `fin_de_semana`.
- `festivo` y `nombre_festivo`: decretos de fiestas laborales de la Comunidad de Madrid 2022–2025 (48 días, validados también con la librería `holidays`). No se incluyen las fiestas locales.
- `vacaciones_escolares`, `tipo_vacaciones` y `dia_lectivo`: calendarios escolares oficiales de Infantil y Primaria de la Comunidad de Madrid, cursos 2021-22 a 2025-26 (el 2025-26 confirmado con la Orden 1476/2025, BOCM 13/05/2025).

**Meteorología:** Open-Meteo (reanálisis ERA5), punto más cercano al hospital (zona de Majadahonda). Fichero `datos/externos/meteo_open_meteo_2022_2025.csv` con `temp_max`, `temp_min`, `temp_media`, `precipitacion`, `humedad`.

**Eliminado por no estar en el anteproyecto:** puentes, vísperas y post-festivos, Nochebuena/Nochevieja, calor extremo, logaritmo de la lluvia, pruebas de Mann-Whitney, VIF y el estudio de relevancia de variables. **La selección de variables se hace en la Fase 2**, comparando en validación modelos con distintos conjuntos de variables.

Salida: `datos/procesados/dataset_fase1.csv`.

### Paso 8 · Normalización — ✅ `tfg/fase1_paso8_normalizacion.py`

- **Continuas** (llegadas y desgloses, temperaturas, precipitación, humedad): `(x − media) / desviación` (estandarización). Columnas `…_normalizada`.
- **Media y desviación solo con entrenamiento** y sin días incompletos (728 días), para evitar fuga de datos. Desviación típica muestral (`DESVEST.M`).
  - Ejemplo: llegadas media 523,698 y desviación 61,280 → 01/01/2022: (521 − 523,698) / 61,280 = −0,044.
  - Precipitación sin logaritmo: media 1,424 mm, desviación 4,991 mm.
- **Cíclicas** (`dia_semana`, `mes`, `dia_anio`): seno y coseno con periodo 7, 12 y 365,25. Decidido mantenerlas. **La elección del método de normalización conviene confirmarla con la tutora.**
- **Binarias** (`fin_de_semana`, `festivo`, `vacaciones_escolares`, `dia_lectivo`): se dejan igual.
- Salida: `datos/procesados/dataset_fase1_normalizado.csv` y `parametros_normalizacion.csv` (para desnormalizar las predicciones con `desnormalizar()`).

### Excel de la Fase 1

En la carpeta local hay un Excel con las hojas de serie diaria, resumen, variables exógenas, parámetros de normalización y normalización, con las fórmulas visibles. Si se modifica, cerrarlo antes en Excel para no perder cambios.

## 4. Fase 2 — Modelos de predicción (siguiente)

Según el anteproyecto:

1. **Baselines:** persistencia y naïve estacional semanal (la nota mínima a superar).
2. **Estadísticos:** ARIMA y SARIMAX, con estacionalidad semanal y regresores de calendario.
3. **Ensembles de árboles** (árboles de decisión, XGBoost).
4. **Redes neuronales:** tradicionales y profundas (Transformers).

- Horizonte de **1 a 7 días**, con **incertidumbre** de cada predicción.
- Todos con las mismas particiones: entrenar con 2022–2023, elegir configuración en 2024 (tamaño de ventana, variables de entrada) y evaluar **una sola vez** en 2025.
- Comparar con el **sistema actual del hospital** (`prd_unificado.sql`) y estudiar métricas de comparación.
- Predicción desagregada por áreas (PED, GIN, GEN).
- **Interfaz** para probar los modelos y visualizar resultados.
- Medios: Python 3.12, entrenamiento en CPU.

## 5. Cómo ejecutar

```bash
pip install -r requirements.txt
python tfg/fase1_paso1_ingesta.py --origen "C:/PAULA/UNI/TFG/Datos_urgencias"
python tfg/fase1_paso2_serie_diaria.py
python tfg/fase1_paso7_variables_exogenas.py
python tfg/fase1_paso8_normalizacion.py
```

Los resultados se guardan en `datos/procesados/` (no se suben a GitHub).

## 6. Pendientes

- [ ] Método para los 3 días incompletos (espera a la tutora).
- [ ] Confirmar con la tutora el método de normalización.
- [ ] Unir la rama `fase1-paso1-ingesta` a `main` (pull request).
- [ ] Empezar la Fase 2 por los baselines.
