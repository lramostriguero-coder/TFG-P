"""
FASE 1 · PASO 7b — Estudio de relevancia de las variables exógenas.

Anteproyecto (Fase 1): "se incorporarán variables exógenas y se estudiará si
permite aportar información relevante para la predicción".

Se usan SOLO los días de ENTRENAMIENTO (2022-2023) sin los días incompletos,
para que la elección de variables no use información de validación ni de test.

Tres análisis, de más simple a más completo:
  1. Correlación de Spearman de cada variable con las llegadas (total y por área).
     Mide si cuando la variable sube, las llegadas suben o bajan (de −1 a 1).
  2. Diferencias de medias:
     - variables de sí/no → prueba de Mann-Whitney (¿hay diferencia real entre
       los días con y sin la característica?)
     - variables con varias categorías → prueba de Kruskal-Wallis.
     Un p-valor < 0,05 indica que la diferencia no se debe al azar.
  3. Modelo conjunto (regresión lineal): se añaden las variables una a una y se
     mira cuánto mejora la explicación (R² ajustado) y si cada variable sigue
     siendo significativa cuando las demás ya están. Sirve para detectar
     variables REDUNDANTES (que parecen importar solas, pero cuya información ya
     está en otra variable).
  Además se mide la colinealidad entre las temperaturas (correlación y VIF).

Uso:
    python tfg/fase1_paso7b_relevancia.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos" / "procesados"
INFORMES = RAIZ / "informes"

OBJETIVOS = {"llegadas": "Total", "llegadas_PED": "PED", "llegadas_GIN": "GIN", "llegadas_GEN": "GEN"}
VARIABLES = ["anio", "mes", "dia_mes", "dia_anio", "semana_anio", "dia_semana", "fin_de_semana",
             "festivo", "vacaciones_escolares", "dia_lectivo",
             "temp_max", "temp_min", "temp_media", "precipitacion", "humedad"]
EXOGENAS_MODELO = ["festivo", "vacaciones_escolares", "dia_lectivo", "temp_media", "log_precipitacion", "humedad"]


def cargar_entrenamiento() -> pd.DataFrame:
    d = pd.read_csv(PROCESADOS / "dataset_fase1.csv", parse_dates=["fecha"], index_col="fecha")
    t = d[(d["particion"] == "entrenamiento") & (~d["dato_incompleto"])].copy()
    t["log_precipitacion"] = np.log1p(t["precipitacion"])
    t["tipo_vac"] = t["tipo_vacaciones"].fillna("ninguna")
    return t


def correlaciones(t):
    filas = []
    for v in VARIABLES:
        fila = {"Variable": v}
        for y, nombre in OBJETIVOS.items():
            rho, p = stats.spearmanr(t[v], t[y])
            fila[f"Rho {nombre}"] = round(rho, 3)
            fila[f"p {nombre}"] = p
        filas.append(fila)
    return pd.DataFrame(filas)


def diferencias(t):
    filas = []
    for v in ["fin_de_semana", "festivo", "vacaciones_escolares", "dia_lectivo"]:
        con, sin = t.loc[t[v] == 1, "llegadas"], t.loc[t[v] == 0, "llegadas"]
        filas.append({"Variable": v, "Prueba": "Mann-Whitney", "Días con": len(con),
                      "Media con": round(con.mean(), 1), "Media sin": round(sin.mean(), 1),
                      "Diferencia": round(con.mean() - sin.mean(), 1), "p-valor": stats.mannwhitneyu(con, sin).pvalue})
    for v in ["dia_semana", "mes", "tipo_vac"]:
        grupos = [g["llegadas"].values for _, g in t.groupby(v)]
        medias = t.groupby(v)["llegadas"].mean().round(0).astype(int)
        if v == "dia_semana":
            medias.index = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        filas.append({"Variable": "tipo_vacaciones" if v == "tipo_vac" else v, "Prueba": "Kruskal-Wallis",
                      "Media con": None, "Media sin": None,
                      "Diferencia": int(medias.max() - medias.min()), "p-valor": stats.kruskal(*grupos).pvalue,
                      "Medias por grupo": ", ".join(f"{k}: {m}" for k, m in medias.items())})
    return pd.DataFrame(filas)


def modelo_incremental(t):
    pasos = [
        ("Día de la semana", "C(dia_semana)"),
        ("+ Mes (estacionalidad)", "C(dia_semana) + C(mes)"),
        ("+ Festivo", "C(dia_semana) + C(mes) + festivo"),
        ("+ Vacaciones escolares", "C(dia_semana) + C(mes) + festivo + vacaciones_escolares"),
        ("+ Tipo de vacaciones (en vez de sí/no)", "C(dia_semana) + C(mes) + festivo + C(tipo_vac)"),
        ("+ Día lectivo", "C(dia_semana) + C(mes) + festivo + vacaciones_escolares + dia_lectivo"),
        ("+ Temperatura media", "C(dia_semana) + C(mes) + festivo + vacaciones_escolares + temp_media"),
        ("+ Precipitación", "C(dia_semana) + C(mes) + festivo + vacaciones_escolares + temp_media + log_precipitacion"),
        ("+ Humedad", "C(dia_semana) + C(mes) + festivo + vacaciones_escolares + temp_media + log_precipitacion + humedad"),
    ]
    filas = []
    for nombre, f in pasos:
        m = smf.ols(f"llegadas ~ {f}", data=t).fit()
        filas.append({"Modelo": nombre, "R² ajustado": round(m.rsquared_adj, 3), "AIC": round(m.aic, 1)})
    return pd.DataFrame(filas)


def modelo_por_area(t):
    """Efecto de cada variable exógena controlando por día de la semana y mes."""
    filas = []
    f = " + ".join(["C(dia_semana)", "C(mes)"] + EXOGENAS_MODELO)
    for y, nombre in OBJETIVOS.items():
        m = smf.ols(f"{y} ~ {f}", data=t).fit()
        for v in EXOGENAS_MODELO:
            filas.append({"Área": nombre, "Variable": v, "Efecto (pacientes/día)": round(m.params[v], 2),
                          "p-valor": m.pvalues[v], "Significativa (p<0,05)": "Sí" if m.pvalues[v] < 0.05 else "No",
                          "R² ajustado del modelo": round(m.rsquared_adj, 3)})
    return pd.DataFrame(filas)


def colinealidad(t):
    cols = ["temp_max", "temp_min", "temp_media", "humedad", "precipitacion"]
    X = (t[cols] - t[cols].mean()) / t[cols].std()
    X["constante"] = 1
    vif = {c: round(variance_inflation_factor(X.values, i), 1) for i, c in enumerate(cols)}
    corr = t[cols].corr().round(2)
    corr["VIF"] = pd.Series(vif)
    return corr.reset_index().rename(columns={"index": "Variable"})


CONCLUSIONES = [
    ("dia_semana", "Mantener", "Es la variable que más explica (por sí sola, R² = 0,19). Los lunes hay ~80 llegadas más que los jueves."),
    ("mes / dia_anio", "Mantener (solo una de las dos)", "La estacionalidad es lo más importante tras el día de la semana (R² sube de 0,19 a 0,55). Mes, día del año y semana del año dicen lo mismo: basta con una."),
    ("semana_anio", "Redundante", "Misma información que el mes o el día del año."),
    ("dia_mes", "No relevante", "No tiene relación con las llegadas (rho = −0,03)."),
    ("anio", "Revisar en la Fase 2", "Recoge la tendencia: la demanda sube de 522 (2022) a 548 (2025) llegadas/día. Con solo 2 años de entrenamiento no se aprende bien; habrá que tratar la tendencia en el modelo."),
    ("fin_de_semana", "Redundante", "Su información ya está en el día de la semana."),
    ("festivo", "Mantener", "En el total no es significativo (p = 0,22), pero sí por áreas: PED +20 (p < 0,001) y GIN −6 (p < 0,001); los efectos se compensan. Necesaria para la predicción por áreas."),
    ("vacaciones_escolares / tipo_vacaciones", "Mantener", "Muy relevante (verano: ~70 llegadas menos). El tipo de vacaciones explica más que el simple sí/no. Sobre todo en Pediatría (rho = −0,51)."),
    ("dia_lectivo", "Redundante", "Sola parece importar, pero cuando ya están el día de la semana, los festivos y las vacaciones deja de ser significativa en todas las áreas (p ≥ 0,2)."),
    ("temp_media", "Mantener", "Significativa también controlando por el mes (p = 0,02 en el total; p = 0,002 en GEN)."),
    ("temp_max / temp_min", "Redundantes", "Correlación de 0,97-0,98 con la temperatura media (VIF > 50): repiten la misma información."),
    ("precipitacion", "Mantener", "Sola parece subir las llegadas (rho = 0,08) porque llueve más en invierno; controlando por el mes, los días de lluvia llegan MENOS pacientes (p < 0,001 en total, PED y GEN)."),
    ("humedad", "No relevante", "No es significativa en ninguna área cuando ya está la temperatura (p ≥ 0,23); está muy ligada a ella (r = −0,73)."),
]


def main():
    t = cargar_entrenamiento()
    tablas = {
        "Conclusiones": pd.DataFrame(CONCLUSIONES, columns=["Variable", "Decisión propuesta", "Motivo"]),
        "Correlaciones": correlaciones(t),
        "Diferencias de medias": diferencias(t),
        "Modelo conjunto": modelo_incremental(t),
        "Efecto por área": modelo_por_area(t),
        "Temperaturas (colinealidad)": colinealidad(t),
    }
    INFORMES.mkdir(exist_ok=True)
    guardar_excel(tablas, len(t), INFORMES / "fase1_paso7b_relevancia.xlsx")
    for nombre, df in tablas.items():
        print(f"\n== {nombre}\n{df.to_string(index=False)}")
    return tablas, len(t)


COMO_LEER = [
    ("Datos usados", "Solo los días de ENTRENAMIENTO (2022-2023) sin los 2 días incompletos: {n} días. Así la elección de variables no usa información de validación ni de test."),
    ("Correlación de Spearman (rho)", "Va de −1 a 1. Positiva: cuando la variable sube, las llegadas suben. Negativa: bajan. Cerca de 0: no hay relación. Mira cada variable por separado."),
    ("p-valor", "Probabilidad de ver esa relación por puro azar. Si p < 0,05 se considera que la relación es real (significativa)."),
    ("Mann-Whitney", "Compara las llegadas de los días CON y SIN una característica de sí/no (p. ej. festivo / no festivo)."),
    ("Kruskal-Wallis", "Igual, pero para variables con varios grupos (día de la semana, mes, tipo de vacaciones)."),
    ("Modelo conjunto (regresión lineal)", "Explica las llegadas con varias variables a la vez. Permite ver si una variable sigue aportando cuando las demás ya están: si deja de ser significativa, es REDUNDANTE."),
    ("R² ajustado", "Proporción de la variación de las llegadas que explica el modelo (de 0 a 1). Si al añadir una variable no sube, esa variable no aporta."),
    ("AIC", "Medida de calidad del modelo que penaliza añadir variables: cuanto más bajo, mejor."),
    ("Efecto (pacientes/día)", "Cuántas llegadas más (+) o menos (−) hay cuando la variable vale 1 (o por cada °C / unidad), con el día de la semana y el mes ya tenidos en cuenta. En Precipitacion se usa log(1 + mm), porque casi todos los días la lluvia es 0."),
    ("VIF", "Mide si una variable repite la información de otras. Por encima de 10 se considera que hay colinealidad (información duplicada)."),
]


def nombre_excel(texto):
    """Mismo formato de nombres que en el Excel de variables: primera letra en mayúscula y 'año'."""
    partes = []
    for p in str(texto).split(" / "):
        p = p.replace("anio", "año").replace("log_precipitacion", "precipitacion")
        partes.append(p[:1].upper() + p[1:])
    return " / ".join(partes)


def guardar_excel(tablas, n, ruta):
    tablas = {k: v.copy() for k, v in tablas.items()}
    for df in tablas.values():
        if "Variable" in df.columns:
            df["Variable"] = df["Variable"].map(nombre_excel)
    col = tablas["Temperaturas (colinealidad)"]
    col.columns = [nombre_excel(c) if c != "VIF" else c for c in col.columns]
    with pd.ExcelWriter(ruta, engine="xlsxwriter") as w:
        wb = w.book
        cab = wb.add_format({"bg_color": "#D9D9D9", "border": 1})
        celda = wb.add_format({"border": 1, "valign": "top"})
        texto = wb.add_format({"border": 1, "text_wrap": True, "valign": "top"})
        def hoja(df, nombre, anchos, envolver=()):
            ws = wb.add_worksheet(nombre)
            for j, c in enumerate(df.columns):
                ws.write(0, j, c[:1].upper() + c[1:], cab)
                ws.set_column(j, j, anchos.get(c, 13))
            for i, fila in enumerate(df.itertuples(index=False), 1):
                for j, v in enumerate(fila):
                    col = df.columns[j]
                    f = texto if col in envolver else celda
                    if v is None or (isinstance(v, float) and np.isnan(v)):
                        ws.write_blank(i, j, None, f)
                    elif isinstance(v, (int, float, np.integer, np.floating)):
                        fmt = wb.add_format({"border": 1, "num_format": "0.0000" if col.startswith("p") else "General"})
                        ws.write_number(i, j, float(v), fmt)
                    else:
                        ws.write(i, j, v, f)
            ws.freeze_panes(1, 1)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
        leer = pd.DataFrame([(a, b.format(n=n)) for a, b in COMO_LEER], columns=["Concepto", "Qué significa"])
        hoja(tablas["Conclusiones"], "Conclusiones", {"Variable": 36, "Decisión propuesta": 28, "Motivo": 110}, envolver=("Motivo",))
        hoja(leer, "Cómo leerlo", {"Concepto": 34, "Qué significa": 120}, envolver=("Qué significa",))
        hoja(tablas["Correlaciones"], "Correlaciones", {"Variable": 22})
        hoja(tablas["Diferencias de medias"], "Diferencias de medias", {"Variable": 22, "Prueba": 16, "Medias por grupo": 95})
        hoja(tablas["Modelo conjunto"], "Modelo conjunto", {"Modelo": 40})
        hoja(tablas["Efecto por área"], "Efecto por área", {"Variable": 22, "Efecto (pacientes/día)": 22, "Significativa (p<0,05)": 22, "R² ajustado del modelo": 22})
        hoja(tablas["Temperaturas (colinealidad)"], "Temperaturas (colinealidad)", {"Variable": 16})


if __name__ == "__main__":
    main()
