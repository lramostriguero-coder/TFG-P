# TFG · Fase 1: construcción de la base de datos entrenable

Fecha: 04/11/2026 · Versión editable: [documento en Claude](https://claude.ai/artifact/JT7AE7TU8PNLBws2Cmt87Z)

## Introducción

La Fase 1 está terminada: a partir de los datos crudos del hospital se ha construido una serie diaria de **1.458 días** (2022–2025), con variables de calendario y meteorología, normalizada y dividida en entrenamiento, validación y test.

El TFG, *Predicción de la demanda diaria de urgencias hospitalarias mediante modelos de aprendizaje automático* (alumna: Paula Fernández Sánchez; tutora: Silvia Jiménez Fernández; cotutor: Alberto Palomo Alonso), busca predecir las llegadas diarias a urgencias con 1 a 7 días de antelación. Este documento explica, paso a paso, qué se ha hecho en la Fase 1 y por qué.

Reglas de trabajo seguidas:

- **Ceñirse al anteproyecto**: no se añaden variables, pruebas ni métodos que no aparezcan en él. Lo que el anteproyecto no fija se consulta antes.
- **Separar fuentes oficiales de criterio propio**, y dejar escrita cada decisión.
- **Los datos de pacientes nunca se suben a GitHub.**

## Datos de partida

Se trabaja solo con los ficheros entregados por el hospital: no va a llegar ningún dato más. Son volcados de phpMyAdmin (sentencias `INSERT INTO`) que se leen con Python sin instalar una base de datos.

| Fichero | Qué contiene | Tamaño |
| --- | --- | --- |
| `episodios (2022–2025).sql` | Un episodio de urgencias por fila: llegada, salida, edad, servicio, triaje, alta… | 778.472 episodios |
| `codificacion (2022–2025).sql` | Códigos CIE-10 de cada episodio | 3.816.119 filas |
| `prd_unificado.sql` | Predicciones del sistema actual del hospital, una fila por día (sep-2024 a may-2026) | 537 días |

Por indicación de la tutora, **el número real de llegadas se obtiene contando los episodios por su fecha de llegada** (`fecha_inicio`). Las predicciones de `prd_unificado.sql` no son llegadas reales: se usarán en la Fase 2 para comparar con el sistema actual.

## Paso 1 · Ingesta y curación del dato crudo

Se unen los 4 años de episodios y de codificación, se revisan duplicados y errores, y se unifica el formato de cada campo. Los registros con problemas **se marcan, no se borran**. Script: `tfg/fase1_paso1_ingesta.py`.

1. **Duplicados.** No hay episodios repetidos ni códigos repetidos. Había un caso con el mismo episodio y orden pero códigos distintos: no es un duplicado y se conserva (al principio el script lo borraba por error; se corrigió).
2. **Marcas de calidad.** Cada problema se señala con una columna `flag_*` (unos 6,4 % de los episodios tienen alguna):

| Marca | Episodios | Qué significa |
| --- | --- | --- |
| `flag_sin_diagnostico` | 42.850 | Sin diagnóstico principal codificado |
| `flag_sin_triaje` | 6.112 | Sin nivel de triaje |
| `flag_triaje_incoherente` | 1.143 | Triaje antes de la llegada o después de la salida |
| `flag_estancia_larga` | 1.064 | Más de 72 h en urgencias |
| `flag_fuera_periodo` | 60 | Llegada fuera de 2022–2025 |
| `flag_edad_invalida` | 1 | Fecha de nacimiento imposible (01/01/1800); edad vacía |
| `flag_fin_antes_inicio` | 0 | Salida anterior a la llegada |

3. **Homogeneización de campos.**
   - Tipos: fechas como fechas y números como números; los vacíos (`NULL`, `""`, espacios) se unifican, y las fechas imposibles (`1900-01-00`, 344 casos) quedan vacías.
   - `nivel_triaje`: de 1 (crítico) a 5 (no urgente). Había más de 10 formas de escribirlo; si falta, se deduce de la columna `gravedad`.
   - `es_ingreso`: sí cuando `motivo_alta` es «HOSPITALIZACION U».
   - `dx_capitulo`: capítulo CIE-10 del diagnóstico principal (22 grupos).
   - `duracion_min`: minutos en urgencias (salida − llegada).
4. **Edad.** Es la que tenía el paciente **el día de esa llegada**, en años cumplidos (número entero), calculada con la fecha de nacimiento y la de llegada. Un mismo paciente tiene, por tanto, edades distintas en cada episodio: por ejemplo, 15 años en septiembre de 2022, 16 en noviembre de 2022 y 19 en octubre de 2025. El fichero traía una edad decimal redondeada (a quien le faltaba un día para cumplir 16 le salía 16,00); al corregirlo, 30 episodios pasaron a Pediatría.
5. **Área asistencial** (`area`):
   - **PED** si el paciente tiene menos de 16 años ese día.
   - Si no, **GIN** si el servicio es Urgencias Ginecológicas, Urgencias Obstétricas u Obstetricia.
   - El resto, **GEN**.
6. **Columnas descartadas:** `fuente`, `resp_final`, `resp_ing` y `fecha_ing` (vacías), `resp_acl` y `resp_alta` (identifican al profesional), `tipo_acto` (siempre «URGENCIAS») y `f_nacimiento` (dato personal, solo se usa para calcular la edad).

Resultado: 778.472 episodios limpios (157.165 PED, 58.704 GIN y 562.603 GEN) y el informe `informes/fase1_paso1_calidad.md`.

## Paso 2 · Serie diaria y particiones

Se cuentan los episodios de cada día por su fecha de llegada, en total y por área, y cada día se asigna a una partición cronológica. Script: `tfg/fase1_paso2_serie_diaria.py`.

- **Columnas:** `llegadas` (lo que se va a predecir), `llegadas_PED`, `llegadas_GIN` y `llegadas_GEN` (suman `llegadas`), `salidas` (solo como referencia) y `particion`.
- **Calendario completo:** se construyen los 1.461 días del 01/01/2022 al 31/12/2025, incluso si un día no tuviera episodios.

| Partición | Periodo | Días | Llegadas/día (media) | Mínimo | Máximo |
| --- | --- | --- | --- | --- | --- |
| Entrenamiento | 2022–2023 | 728 | 523,7 | 364 | 735 |
| Validación | 2024 | 366 | 538,1 | 385 | 687 |
| Test | 2025 | 364 | 547,9 | 417 | 723 |

El modelo aprende con entrenamiento, la configuración se elige en validación y test se usa **una sola vez**, al final.

### Días incompletos eliminados

Al revisar las salidas por hora aparecieron 3 días con registros perdidos. **Por decisión de la tutora, se eliminan de la serie**, que queda con 1.458 días:

| Día | Partición | Llegadas registradas | Problema |
| --- | --- | --- | --- |
| 14/04/2023 | Entrenamiento | 174 | Casi no hay salidas en todo el día (90 de unas 500) |
| 16/06/2023 | Entrenamiento | 248 | Ninguna salida de 14:00 a 23:59 |
| 31/12/2025 | Test | 366 | Faltan los pacientes que salieron en 2026 (no hay fichero de 2026) |

![Llegadas diarias a urgencias 2022–2025 con las particiones y los 3 días incompletos eliminados](../informes/fase1_paso2_serie_diaria.png)

Llegadas por día de 2022 a 2025, con la media móvil de 28 días en negro; en rojo, los 3 días incompletos que se han eliminado.

Dos consecuencias que conviene recoger en la memoria:

- El anteproyecto pide una serie «sin discontinuidades en el calendario»; ahora tiene 3 huecos de un día, por decisión de la tutora.
- En la Fase 2, los valores de días anteriores (el día de antes, el mismo día de la semana anterior) se buscarán **por fecha**, no por la fila de arriba, para no saltarse un hueco.

## Paso 7 · Variables exógenas

A cada día se le añaden variables de calendario y de meteorología, todas de fuentes oficiales o públicas y alineadas día a día con la serie. Script: `tfg/fase1_paso7_variables_exogenas.py`.

| Variable | Qué indica | Fuente |
| --- | --- | --- |
| `anio`, `mes`, `dia_mes`, `dia_anio`, `semana_anio` | Posición del día en el calendario | Calendario |
| `dia_semana`, `fin_de_semana` | Día de la semana (0 = lunes … 6 = domingo); 1 si es sábado o domingo | Calendario |
| `festivo`, `nombre_festivo` | 1 si es festivo nacional o de la Comunidad de Madrid (48 días en 2022–2025) | Decretos de fiestas laborales de la Comunidad de Madrid (BOCM); comprobados con la librería `holidays` |
| `vacaciones_escolares`, `tipo_vacaciones`, `dia_lectivo` | Navidad, Semana Santa o verano escolar; 1 si hay colegio | Calendarios escolares de la Comunidad de Madrid (Infantil y Primaria), cursos 2021-22 a 2025-26; el 2025-26 por la Orden 1476/2025 (BOCM 13/05/2025) |
| `temp_max`, `temp_min`, `temp_media` | Temperatura del día (°C) | Open-Meteo, reanálisis ERA5, punto más cercano al hospital (zona de Majadahonda) |
| `precipitacion` | Lluvia del día (mm) | Open-Meteo |
| `humedad` | Humedad relativa media (%) | Open-Meteo |

No se incluyen las fiestas locales, porque los pacientes vienen de muchos municipios distintos. También se quitaron, por no estar en el anteproyecto, variables de criterio propio (puentes, vísperas, post-festivos, Nochebuena y Nochevieja, calor extremo) y pruebas estadísticas de relevancia. **La selección de variables se hará en la Fase 2**, comparando en validación modelos con distintos conjuntos.

## Paso 8 · Normalización

Las variables continuas se normalizan con **min-max**, con el mínimo y el máximo calculados **solo con los 728 días de entrenamiento**. Script: `tfg/fase1_paso8_normalizacion.py`.

```
valor normalizado = (valor − mínimo de entrenamiento) / (máximo de entrenamiento − mínimo de entrenamiento)
```

Por qué se normaliza: las variables tienen escalas muy distintas (unas 500 llegadas, unos 20 °C, de 0 a 80 mm de lluvia), y muchos modelos aprenden peor si unas pesan más solo por tener números más grandes.

| Variable | Mínimo | Máximo |
| --- | --- | --- |
| Llegadas | 364 | 735 |
| Llegadas PED | 37 | 213 |
| Llegadas GIN | 16 | 68 |
| Llegadas GEN | 280 | 542 |
| Temperatura máxima (°C) | 5,5 | 40,6 |
| Temperatura mínima (°C) | −5,5 | 25,4 |
| Temperatura media (°C) | 0,6 | 33,3 |
| Precipitación (mm) | 0 | 77,5 |
| Humedad (%) | 17 | 97 |

Ejemplo, 01/01/2022: (521 − 364) / (735 − 364) = **0,423**.

- **Sin fuga de datos:** validación y test no intervienen en el cálculo del mínimo y el máximo. Sí se les aplica la misma fórmula con esos valores, para que el modelo reciba los datos en la escala con la que aprendió. Por eso algún día de 2024 o 2025 queda un poco fuera de 0–1 (por ejemplo, Pediatría −0,125 o Ginecología 1,058 en test).
- **Variables cíclicas** (`dia_semana`, `mes`, `dia_anio`): se pasan a seno y coseno, con periodos 7, 12 y 365,25, para que el domingo quede junto al lunes y diciembre junto a enero.
- **Variables binarias** (`fin_de_semana`, `festivo`, `vacaciones_escolares`, `dia_lectivo`): se dejan como 0/1.
- Los parámetros se guardan para deshacer la normalización de las predicciones y volver a pacientes por día.

Al principio se usó la estandarización, (x − media) / desviación; se cambió a min-max por indicación de Paula.

## Entregables y dónde están

El código está en GitHub; los datos de pacientes y los Excel solo en el equipo de Paula.

| Entregable | Dónde | Contenido |
| --- | --- | --- |
| Código | [GitHub · TFG-P](https://github.com/lramostriguero-coder/TFG-P), rama `main` | Scripts de los pasos 1, 2, 7 y 8, informe de calidad, gráfica de la serie y `CONTEXTO_TFG.md` |
| Datos procesados | `datos/procesados/` (no se sube) | `episodios_limpios.parquet`, `serie_diaria.csv`, `dataset_fase1.csv`, `dataset_fase1_normalizado.csv`, `parametros_normalizacion.csv` |
| Excel de episodios | `C:\PAULA\UNI\TFG\Datos_urgencias\FASE1` | `episodios_limpios_2022` a `2025`.xlsx: episodios limpios con edad en años cumplidos y marcas de calidad |
| Excel de la serie | Misma carpeta | `datos_urgencias_fase1.xlsx`: unificación de campos, errores detectados, serie diaria y resumen |
| Excel de variables | Misma carpeta | `variables_exogenas_y_normalizadas_fase1.xlsx`: leyenda, variables exógenas, parámetros y normalización con fórmulas `MIN`/`MAX` visibles |

Los Excel coinciden con Python (diferencias menores de 0,0001 por redondeo) y no tienen errores de fórmula. Hay copias de seguridad de los Excel anteriores en `FASE1\copia_antes_eliminar_incompletos` y `FASE1\copia_antes_edad_entera`.

Para repetir todo el proceso (Python 3.12):

```
pip install -r requirements.txt
python tfg/fase1_paso1_ingesta.py --origen "C:/PAULA/UNI/TFG/Datos_urgencias"
python tfg/fase1_paso2_serie_diaria.py
python tfg/fase1_paso7_variables_exogenas.py
python tfg/fase1_paso8_normalizacion.py
```

## Decisiones tomadas y siguientes pasos

| Decisión | Quién la tomó | Por qué |
| --- | --- | --- |
| Las llegadas se cuentan por `fecha_inicio` | Tutora | Es el número real de pacientes que llegan cada día |
| Los registros con problemas se marcan, no se borran | Criterio del trabajo | No perder información y poder decidir después qué hacer con ellos |
| Se eliminan los 3 días incompletos | Tutora | Tienen registros perdidos y distorsionarían el entrenamiento y la evaluación |
| Edad en años cumplidos el día de cada llegada | Paula | El estudio debe usar la edad real del paciente en cada episodio |
| Normalización min-max con mínimo y máximo de entrenamiento | Paula | El anteproyecto pide normalizar sin fijar el método; el mínimo y el máximo de entrenamiento evitan la fuga de datos |
| Sin variables ni pruebas que no estén en el anteproyecto | Criterio del trabajo | Ceñirse a lo aprobado; la selección de variables va en la Fase 2 |

Siguientes pasos, según el anteproyecto:

- [ ] Explicar en la memoria los 3 huecos de la serie y por qué se eliminaron esos días.
- [ ] Fase 2 · Modelos de referencia: persistencia (repetir el día anterior) y naïve estacional semanal (repetir el mismo día de la semana anterior), buscando esos días por fecha.
- [ ] Fase 2 · ARIMA y SARIMAX con estacionalidad semanal y regresores de calendario.
- [ ] Fase 2 · Ensembles de árboles (árboles de decisión, XGBoost) y redes neuronales (tradicionales y Transformers).
- [ ] Fase 2 · Predicción de 1 a 7 días con incertidumbre, desglosada por áreas, comparada con el sistema actual del hospital, y una interfaz para probar los modelos.
