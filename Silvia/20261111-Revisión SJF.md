# Revisión SJF · 11/11/2026

Revisión de la Fase 1 (base de datos entrenable) antes de empezar la Fase 2.
En general, los pasos son adecuados y siguen el orden del anteproyecto. Abajo están los puntos que hay que cambiar o dejar escritos como decisión.

---

## 1. Días incompletos: se tratan como dato faltante, sin imputación

**Qué pasa.** Los días 14/04/2023, 16/06/2023 y 31/12/2025 se dejó de registrar información a mitad del día. El número de llegadas de esos días **no es un dato real** y usarlo sería conceptualmente incorrecto.

**Cómo se llama.** Son **valores faltantes** (*missing values*, `NaN`). Lo que acordamos es tratarlos **sin imputación**: no se rellenan con ningún valor estimado.

**Qué se ha hecho hasta ahora y por qué hay que cambiarlo.** En el paso 2 se **borran las filas** de esos días, así que la serie tiene 1.458 días con 3 huecos en el calendario. El anteproyecto pide una serie continua, sin discontinuidades.

**Decisión:**

- La serie mantiene **los 1.461 días** (01/01/2022–31/12/2025), sin huecos en el calendario.
- Los 3 días se quedan en la tabla, pero `llegadas`, `llegadas_PED`, `llegadas_GIN`, `llegadas_GEN` y `salidas` van **en blanco** (`NaN`).
- **No se imputan**: ni con el día anterior, ni con el mismo día de la semana anterior, ni con el del año anterior, ni con medias. Rellenarlos sería meter ruido inventado.
- Las variables de calendario y de meteorología de esos días **sí se rellenan**, porque son correctas.
- Que **lo gestione el modelo**:
  - Al **entrenar**, esos días no se usan como objetivo (no hay valor real que aprender).
  - Al **evaluar**, esos días no se puntúan (no hay valor real con el que comparar).
  - Si un día faltante se necesita como entrada (por ejemplo, el retardo "día anterior"), esa entrada queda en blanco. Los modelos que admiten `NaN` (SARIMAX con filtro de Kalman, XGBoost) lo gestionan solos. En los que no lo admiten, se descarta esa muestra y se indica cuántas se han descartado.
- La normalización del paso 8 ya ignora los `NaN` al calcular el mínimo y el máximo; solo hay que comprobarlo.

**Qué tiene que hacer Paula:** cambiar el paso 2 para que guarde los 1.461 días con `NaN` en lugar de borrar las filas. Adaptar las comprobaciones de los pasos 7 y 8. Actualizar `CONTEXTO_TFG.md`, `docs/FASE1_explicacion.md` y los Excel.

---

## 2. Meteorología: no usar el tiempo real del día que se predice

**Situación actual.** Todavía no hay ningún modelo. En `dataset_fase1.csv` cada día lleva la meteorología **observada** de ese mismo día (reanálisis ERA5 de Open-Meteo). **No es una previsión del tiempo**: es lo que realmente pasó.

**El riesgo.** Si en la Fase 2 un modelo predice las llegadas del día *t* usando la temperatura o la lluvia reales del día *t* (o de *t+1 … t+7*), está usando información que **no se conoce** en el momento de hacer la predicción. Los resultados saldrían mejores de lo que serían en la realidad.

**Decisión:**

- Se fija el **momento de la predicción**: al final del día *t*, con los datos disponibles hasta el día *t*, se predicen los días *t+1 … t+7*.
- Como entrada solo se puede usar la meteorología **observada hasta el día *t*** (el día actual y los anteriores), nunca la de los días que se predicen.
- Las variables de calendario de los días que se predicen sí se pueden usar, porque se conocen de antemano (festivos, fin de semana, vacaciones escolares).
- Si más adelante se quiere usar la **previsión** del tiempo para los días *t+1 … t+7*, habría que conseguir previsiones históricas reales (las que se emitieron cada día). Está **pendiente de ver** si hay una fuente fiable que cubra 2022–2025.

---

## 3. Estudio de relevancia de las variables exógenas

El anteproyecto dice que "se estudiará si [las variables exógenas] permiten aportar información relevante para la predicción". Así que sí hay que hacerlo, en la Fase 2.

**Decisión: se hace comparando los resultados del modelo con y sin exógenas** (en inglés, *estudio de ablación*):

- Mismo modelo, mismas particiones y mismas métricas. Lo único que cambia es el conjunto de variables de entrada.
- La comparación se hace en **validación (2024)**. El test (2025) se usa una sola vez, al final.
- Se compara por **grupos**, no variable a variable, para no multiplicar las combinaciones:
  1. sin exógenas (solo la propia serie de llegadas);
  2. \+ calendario;
  3. \+ meteorología;
  4. \+ calendario + meteorología.
- Se mira el resultado **para cada horizonte** (1 a 7 días). Un grupo puede ayudar a 1 día y no a 7.
- Una variable o grupo se considera relevante si mejora de forma consistente (en varios horizontes y en varios modelos), no por una mejora muy pequeña en un único caso.

---

## 4. Decisiones sobre los episodios y las áreas

- **Los episodios marcados se cuentan como llegadas.** Episodios sin triaje, con triaje incoherente, con estancia de más de 72 h o sin diagnóstico: todos son personas que llegaron a urgencias. No sabemos si se fueron sin hacer el triaje o si no se guardó el resultado, pero en cualquier caso **llegaron**. Las marcas `flag_*` se mantienen solo para documentar la calidad del dato.
- **Corte de Pediatría:** **menos de 16 años → PED**; **16 años o más → GEN** (o GIN si corresponde). La edad es la de los años cumplidos el día de la llegada. Este criterio queda **fijado para este trabajo**, sin consultarlo al hospital.
- **Prioridad de la edad sobre el servicio.** Una paciente de menos de 16 años atendida en Ginecología u Obstetricia cuenta como **PED**.

---

## 5. Otros detalles menores

- La numeración de los pasos de la Fase 1 (1, 2, 7 y 8) confunde porque no hay pasos 3 a 6. Hay que renumerarlos o explicar por qué se saltan.
- `requirements.txt` solo pone versiones mínimas (`>=`). Conviene fijar las versiones exactas con las que se ha trabajado, para que los resultados se puedan reproducir.
