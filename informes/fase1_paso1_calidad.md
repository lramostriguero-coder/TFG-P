# Fase 1 · Paso 1 — Informe de calidad del dato crudo

## Lectura

- Episodios leídos: **877,199** (2022: 190,609, 2023: 191,041, 2024: 196,957, 2025: 199,865, 2026: 98,727)
- Filas de codificación leídas: **4,293,702**

## Duplicados

- Episodios duplicados (mismo `acto_clinico`): 0 (idénticos en todo: 0) → eliminados
- Codificación duplicada (mismo episodio, orden, tipo y código): 0 → eliminados
- Mismo episodio y `orden` pero códigos distintos: 1 → se conservan (no son duplicados)
- Códigos sin episodio asociado: 0

## Datos inválidos e incoherentes (se marcan, no se borran)

| Marca | Episodios | Significado |
|---|---|---|
| `flag_edad_invalida` | 2 (0.00 %) | fecha de nacimiento imposible (edad < 0 o > 120 años); edad vacía |
| `flag_sin_triaje` | 6919 (0.79 %) | sin nivel de triaje registrado |
| `flag_triaje_incoherente` | 1855 (0.21 %) | triaje antes de la llegada o después de la salida |
| `flag_estancia_larga` | 1240 (0.14 %) | más de 72 h en urgencias |
| `flag_fin_antes_inicio` | 0 (0.00 %) | fecha de salida anterior a la de llegada |
| `flag_fuera_periodo` | 60 (0.01 %) | llegada fuera del periodo 01/01/2022 - 30/06/2026 |
| `flag_sin_diagnostico` | 50194 (5.72 %) | sin diagnóstico principal codificado |

- Fechas no válidas convertidas a nulo: {'fecha_triaje': 344}
- Edades del fichero incoherentes con la fecha de nacimiento (>1 año): 0
- `edad` = años cumplidos el día de la llegada (entero). Episodios en los que no coincide con la parte entera de la edad decimal del fichero (por redondeo a 2 decimales): 3397

## Columnas descartadas

- `fuente`: vacía en el 100 % de los registros
- `resp_final`: vacía en el 100 % de los registros
- `resp_ing`: vacía en el 100 % de los registros
- `fecha_ing`: vacía en el 100 % de los registros
- `resp_acl`: identificador del profesional; no aporta a la predicción
- `resp_alta`: identificador del profesional; no aporta a la predicción
- `tipo_acto`: valor constante ('URGENCIAS')
- `f_nacimiento`: dato personal; solo se usa para calcular `edad` (años cumplidos el día de la llegada)

## Resultado

- `episodios_limpios.parquet`: **877,199** episodios × 35 columnas
- `codificacion_limpia.parquet`: **4,293,702** filas
- Episodios con diagnóstico principal: 94.3 %

### Reparto por área asistencial

| area   |   episodios |
|:-------|------------:|
| GEN    |      634866 |
| PED    |      175248 |
| GIN    |       67085 |

### Reparto por nivel de triaje (1 = crítico … 5 = no urgente)

| nivel_triaje   |   episodios |
|:---------------|------------:|
| 1              |        1279 |
| 2              |       51372 |
| 3              |      251548 |
| 4              |      546808 |
| 5              |       19273 |
| <NA>           |        6919 |

### Diagnóstico principal por capítulo CIE-10

| dx_capitulo                                 |   episodios |
|:--------------------------------------------|------------:|
| Traumatismos y envenenamientos              |      147520 |
| Síntomas y hallazgos anormales              |      126325 |
| Aparato respiratorio                        |       97846 |
| Aparato musculoesquelético                  |       70276 |
| Aparato digestivo                           |       52400 |
| <NA>                                        |       50194 |
| Ojo                                         |       49340 |
| Aparato genitourinario                      |       49167 |
| Embarazo, parto y puerperio                 |       44763 |
| Infecciosas y parasitarias                  |       38150 |
| Aparato circulatorio                        |       26339 |
| Oído                                        |       23003 |
| Trastornos mentales                         |       20734 |
| Piel y tejido subcutáneo                    |       20060 |
| Factores que influyen en el estado de salud |       19474 |
| Sistema nervioso                            |       15159 |
| Códigos especiales (COVID-19)               |        8874 |
| Endocrinas, nutricionales y metabólicas     |        4952 |
| Sangre y órganos hematopoyéticos            |        3600 |
| Afecciones perinatales                      |        3593 |
| Neoplasias                                  |        2724 |
| Causas externas                             |        2488 |
| Malformaciones congénitas                   |         218 |