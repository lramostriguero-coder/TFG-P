# Fase 1 · Paso 1 — Informe de calidad del dato crudo

## Lectura

- Episodios leídos: **778,472** (2022: 190,609, 2023: 191,041, 2024: 196,957, 2025: 199,865)
- Filas de codificación leídas: **3,816,119**

## Duplicados

- Episodios duplicados (mismo `acto_clinico`): 0 (idénticos en todo: 0) → eliminados
- Codificación duplicada (mismo episodio y `orden`): 1 → eliminados
- Códigos sin episodio asociado: 0

## Datos inválidos e incoherentes (se marcan, no se borran)

| Marca | Episodios | Significado |
|---|---|---|
| `flag_sin_triaje` | 6112 (0.79 %) | sin nivel de triaje registrado |
| `flag_triaje_incoherente` | 1143 (0.15 %) | triaje antes de la llegada o después de la salida |
| `flag_estancia_larga` | 1064 (0.14 %) | más de 72 h en urgencias |
| `flag_fin_antes_inicio` | 0 (0.00 %) | fecha de salida anterior a la de llegada |
| `flag_fuera_periodo` | 60 (0.01 %) | llegada fuera de 2022-2025 |
| `flag_sin_diagnostico` | 42850 (5.50 %) | sin diagnóstico principal codificado |

- Fechas no válidas convertidas a nulo: {'fecha_triaje': 344}
- Edades incoherentes con la fecha de nacimiento (>1 año): 0

## Columnas descartadas

- `fuente`: vacía en el 100 % de los registros
- `resp_final`: vacía en el 100 % de los registros
- `resp_ing`: vacía en el 100 % de los registros
- `fecha_ing`: vacía en el 100 % de los registros
- `resp_acl`: identificador del profesional; no aporta a la predicción
- `resp_alta`: identificador del profesional; no aporta a la predicción
- `tipo_acto`: valor constante ('URGENCIAS')
- `f_nacimiento`: dato personal redundante con `edad` (se verifica antes la coherencia)

## Resultado

- `episodios_limpios.parquet`: **778,472** episodios × 34 columnas
- `codificacion_limpia.parquet`: **3,816,118** filas
- Episodios con diagnóstico principal: 94.5 %

### Reparto por área asistencial

| area   |   episodios |
|:-------|------------:|
| GEN    |      562631 |
| PED    |      157135 |
| GIN    |       58706 |

### Reparto por nivel de triaje (1 = crítico … 5 = no urgente)

| nivel_triaje   |   episodios |
|:---------------|------------:|
| 1              |        1173 |
| 2              |       45422 |
| 3              |      223663 |
| 4              |      485048 |
| 5              |       17054 |
| <NA>           |        6112 |

### Diagnóstico principal por capítulo CIE-10

| dx_capitulo                                 |   episodios |
|:--------------------------------------------|------------:|
| Traumatismos y envenenamientos              |      130592 |
| Síntomas y hallazgos anormales              |      110243 |
| Aparato respiratorio                        |       89574 |
| Aparato musculoesquelético                  |       61930 |
| Aparato digestivo                           |       46702 |
| Aparato genitourinario                      |       44022 |
| Ojo                                         |       43555 |
| <NA>                                        |       42850 |
| Embarazo, parto y puerperio                 |       38820 |
| Infecciosas y parasitarias                  |       34390 |
| Aparato circulatorio                        |       23645 |
| Oído                                        |       20851 |
| Trastornos mentales                         |       18351 |
| Piel y tejido subcutáneo                    |       17896 |
| Factores que influyen en el estado de salud |       17140 |
| Sistema nervioso                            |       13381 |
| Códigos especiales (COVID-19)               |        8850 |
| Endocrinas, nutricionales y metabólicas     |        4492 |
| Sangre y órganos hematopoyéticos            |        3232 |
| Afecciones perinatales                      |        3144 |
| Neoplasias                                  |        2471 |
| Causas externas                             |        2158 |
| Malformaciones congénitas                   |         183 |