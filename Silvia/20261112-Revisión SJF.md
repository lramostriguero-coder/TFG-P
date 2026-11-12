# Revisión SJF · 12/11/2026

Hay datos nuevos, de **enero a junio de 2026**. Esta revisión **sustituye el punto 1 (división del conjunto de datos)** de la revisión del 11/11/2026. El resto de esa revisión sigue igual.

---

## 1. Experimento 1: nueva división del conjunto de datos

La división sigue siendo **cronológica**.

| Partición | Periodo | Días | % (entrenamiento + validación) |
|---|---|---|---|
| Entrenamiento | 01/01/2022 – 30/06/2024 | 912 | 71 % |
| Validación | 01/07/2024 – 30/06/2025 | 365 | 29 % |
| Test | 01/07/2025 – 30/06/2026 | 365 | — |

- Entrenamiento y validación quedan en una proporción muy cercana a 70/30.
- La validación y el test no son años naturales, pero **cada uno abarca 12 meses seguidos**, así que recorren todas las estaciones una vez.
- Las predicciones del sistema actual del hospital (septiembre de 2024 a mayo de 2026) cubren casi todo el test, así que se puede comparar con ellas en ese periodo.
- El mínimo y el máximo de la normalización se calculan **solo con el entrenamiento**.
- Toda la Fase 2 (baselines, ARIMA/SARIMA/SARIMAX, árboles, redes) se hace con esta división. El test se usa **una sola vez**, al final.

---

## 2. Experimento 2: el mejor modelo, con más datos

Cuando termine la Fase 2 y se sepa cuál es el mejor modelo, se repite **solo ese modelo** con años completos:

| Partición | Periodo | Días | % (entrenamiento + validación) |
|---|---|---|---|
| Entrenamiento | 2022 – 2024 | 1.096 | 75 % |
| Validación | 2025 | 365 | 25 % |
| Test | 01/01/2026 – 30/06/2026 | 181 | — |

- Se usa la **misma familia de modelos** y se vuelven a buscar los mejores hiperparámetros **en la validación (2025)**, dentro del **mismo rango de búsqueda** que en el experimento 1. Es normal que los hiperparámetros salgan distintos, porque hay 6 meses más de datos.
- Los datos de 2026 **no se usan para entrenar ni para ajustar nada**.
- La normalización se vuelve a calcular con el entrenamiento de este experimento.

**Comparación entre los dos experimentos.** Se hace **sobre el mismo periodo**: enero–junio de 2026, que está en el test de los dos. Si se comparara el test de 12 meses del experimento 1 con el de 6 meses del experimento 2, las diferencias podrían deberse a la época del año y no al modelo.

La pregunta que se responde es: **¿entrenar con datos más recientes mejora la predicción?**

---

## 3. Días incompletos con los datos de 2026

Los días incompletos se siguen tratando como **dato faltante, sin imputación** (punto 2 de la revisión del 11/11/2026).

- **31/12/2025:** se marcó como incompleto porque faltaban los pacientes que salieron en 2026. Con el fichero de 2026 hay que comprobar si ya están y si el día se puede recuperar.
- **30/06/2026:** seguramente tenga el mismo problema (faltarán los pacientes que salieron en julio). Si es así, se trata como dato faltante.
- Hay que revisar el resto de 2026 igual que se revisaron 2022–2025, por si aparece algún otro día incompleto.

---

## 4. Incorporar 2026 a la Fase 1

- Pasar los datos de 2026 por los pasos de la Fase 1: ingesta y curación, serie diaria, variables exógenas y normalización.
- Añadir la meteorología de enero a junio de 2026 (misma fuente y mismo punto), los festivos de 2026 (fuentes oficiales) y el calendario escolar del curso 2025-26 hasta junio de 2026.
- Preparar el código para que se pueda pasar del experimento 1 al 2 cambiando solo un parámetro, sin tocar el código.
