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

## 5. Qué se puede hacer fuera del anteproyecto: orden lógico

El anteproyecto es un esqueleto. **Se pueden hacer cosas que no aparecen en él**, siempre que:

- cada paso tenga **un motivo** (una pregunta concreta que responde);
- siga **un orden lógico**: de lo más sencillo a lo más complejo, y cada modelo se compara con el anterior;
- quede **documentado** el porqué y el resultado.

Lo que no se hace es añadir variables, pruebas o métodos "por si acaso", sin una pregunta detrás.

Esto sustituye a la regla 1 de `CONTEXTO_TFG.md` ("ceñirse al anteproyecto"), que hay que actualizar.

**Orden de la Fase 2:**

1. **Baselines**: persistencia (mañana = hoy) y naïve estacional semanal (mismo día de la semana anterior). Son la nota mínima que hay que superar.
2. **ARIMA → SARIMA → SARIMAX**, con el estudio de días anteriores del punto 6.
3. **Estudio de relevancia de exógenas** (punto 3), empezando en SARIMAX.
4. **Ensembles de árboles** (árbol de decisión, XGBoost).
5. **Redes neuronales**: tradicionales y profundas.

En cada familia se usan las mismas particiones, las mismas métricas, los horizontes de 1 a 7 días y se compara con los baselines.

---

## 6. ARIMA, SARIMA y SARIMAX: qué días anteriores usar

**Objetivo:** que se vea, y se analice, que **la elección de los días anteriores que usa el modelo cambia la predicción**.

Configuraciones que hay que probar, como mínimo:

- el día anterior;
- los 3 días anteriores;
- los 7 días anteriores (la semana anterior);
- los 14 días anteriores;
- el mismo día de la semana (lunes, martes…) de la semana anterior;
- el mismo día de la semana de las dos semanas anteriores;
- la semana anterior + el mismo día de la semana del año anterior;
- … y las combinaciones que vayan saliendo del análisis.

**Lo que tiene que pensar y decidir Paula** (dejando escrito el razonamiento):

- Cómo se traduce cada configuración a cada modelo (ARIMA, SARIMA o SARIMAX) y a sus parámetros.
- Qué significa exactamente "el mismo día de la semana del año anterior" y cómo se calcula.
- Qué consecuencias tiene cada configuración sobre los datos disponibles para entrenar.
- Cómo afectan a cada configuración los 3 días en blanco del punto 1.

**Qué hay que analizar:**

- El error en validación **para cada horizonte** (1 a 7 días), comparado con los baselines.
- **Qué días ayudan y a qué horizonte.**
- Si añadir más días mejora la predicción o solo complica el modelo.
- Una tabla resumen y una gráfica de error por horizonte, con una conclusión escrita.
