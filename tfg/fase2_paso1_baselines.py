"""
FASE 2 · PASO 1 — Baselines: persistencia y naïve estacional semanal.

Revisión de la tutora (11/11/2026): antes de cualquier modelo, dos predicciones
muy sencillas que marcan la "nota mínima" que hay que superar.

Cómo se predice (igual para todos los modelos de la Fase 2):
    Al final del día t, con las llegadas conocidas hasta t, se predicen los días
    t+1 ... t+7 (horizonte h = 1 ... 7).

Los dos baselines:
    1. Persistencia ("mañana = hoy"):            ŷ(t+h) = y(t)
       Para cualquier horizonte se repite el último dato conocido.
    2. Naïve estacional semanal ("mismo día de la semana anterior"):
                                                 ŷ(t+h) = y(t+h−7)
       Como h ≤ 7, el día t+h−7 es como muy tarde el día t: ya se conoce.
       Con h = 7 coincide con la persistencia (t+7−7 = t).

Evaluación (experimento 1):
    - Se puntúan los días OBJETIVO de la validación (01/07/2024–30/06/2025).
      El día de origen t puede caer en el entrenamiento (p. ej. para predecir el
      01/07/2024 a 7 días se usa el 24/06/2024): es un dato que ya se conocía.
    - Días en blanco (NaN, sin imputar): si el objetivo está en blanco no se
      puntúa; si la entrada que hace falta está en blanco, no hay predicción y
      se descarta esa muestra. Se cuenta cuántas se descartan.
    - Métricas, sobre las llegadas reales (sin normalizar), por horizonte:
        MAE  = media de |real − predicción|           (en pacientes/día)
        RMSE = raíz de la media de (real − predicción)² (castiga más los fallos grandes)
        MAPE = media de |real − predicción| / real × 100 (en %)

Incertidumbre (intervalo de predicción del 90 %, empírico):
    Con los errores (real − predicción) del ENTRENAMIENTO de cada baseline y
    horizonte se calculan los percentiles 5 y 95. El intervalo de un día es
        [predicción + P5 ; predicción + P95]
    En validación se mide la COBERTURA (% de días cuyo valor real cae dentro;
    lo ideal es ≈ 90 %) y la ANCHURA media del intervalo (cuanto más estrecho,
    más útil, siempre que cubra).

Desglose por áreas:
    Lo mismo para llegadas_PED, llegadas_GIN y llegadas_GEN.

Salidas:
    informes/fase2_paso1_baselines.csv   métricas por serie, baseline y horizonte
    informes/fase2_paso1_baselines.png   MAE por horizonte

Uso:
    python tfg/fase2_paso1_baselines.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SERIE = RAIZ / "datos" / "procesados" / "serie_diaria.csv"
INFORMES = RAIZ / "informes"

PARTICION_EVALUADA = "validacion"
HORIZONTES = range(1, 8)
SERIES = ["llegadas", "llegadas_PED", "llegadas_GIN", "llegadas_GEN"]
NIVEL = (5, 95)   # percentiles del intervalo del 90 %


def predecir(y: pd.Series, h: int, baseline: str) -> pd.Series:
    """Predicción de cada día (índice = día objetivo) hecha h días antes.

    `y` tiene un índice diario continuo. shift(k) trae el valor de k días antes.
    """
    if baseline == "persistencia":
        return y.shift(h)          # y(t) con t = objetivo − h
    if baseline == "naive_semanal":
        return y.shift(7)          # y(objetivo − 7), para cualquier h ≤ 7
    raise ValueError(baseline)


def metricas(real: pd.Series, pred: pd.Series) -> dict:
    error = real - pred
    return {
        "MAE": error.abs().mean(),
        "RMSE": np.sqrt((error ** 2).mean()),
        "MAPE_%": (error.abs() / real).mean() * 100,
    }


def main() -> None:
    serie = pd.read_csv(SERIE, parse_dates=["fecha"]).set_index("fecha").asfreq("D")
    evaluados = serie["particion"] == PARTICION_EVALUADA
    entreno = serie["particion"] == "entrenamiento"

    filas = []
    for col in SERIES:
        y = serie[col]
        for baseline in ["persistencia", "naive_semanal"]:
            for h in HORIZONTES:
                pred = predecir(y, h, baseline)
                err_ent = (y - pred)[entreno].dropna()
                p5, p95 = np.percentile(err_ent, NIVEL)
                real = y[evaluados]
                p = pred[evaluados]
                objetivo_en_blanco = real.isna()
                entrada_en_blanco = p.isna() & ~objetivo_en_blanco
                v = ~objetivo_en_blanco & ~entrada_en_blanco
                dentro = (real[v] >= p[v] + p5) & (real[v] <= p[v] + p95)
                filas.append({
                    "serie": col,
                    "baseline": baseline,
                    "horizonte": h,
                    "dias_puntuados": int(v.sum()),
                    "descartados_objetivo_en_blanco": int(objetivo_en_blanco.sum()),
                    "descartados_entrada_en_blanco": int(entrada_en_blanco.sum()),
                    **metricas(real[v], p[v]),
                    "P5_error_entreno": p5,
                    "P95_error_entreno": p95,
                    "cobertura_90_%": dentro.mean() * 100,
                    "anchura_intervalo": p95 - p5,
                })
    y = serie["llegadas"]

    res = pd.DataFrame(filas)
    INFORMES.mkdir(exist_ok=True)
    res.round(2).to_csv(INFORMES / "fase2_paso1_baselines.csv", index=False)

    print(f"Partición evaluada: {PARTICION_EVALUADA} "
          f"({serie.index[evaluados].min().date()} – {serie.index[evaluados].max().date()})\n")
    print(res.round(2).to_string(index=False))

    # Ejemplo con números reales: el primer día de validación.
    dia = serie.index[evaluados][0]
    print(f"\nEjemplo, día objetivo {dia.date()} ({y[dia]:.0f} llegadas reales):")
    for h in (1, 7):
        origen = dia - pd.Timedelta(days=h)
        sem = dia - pd.Timedelta(days=7)
        print(f"  h={h}: origen {origen.date()} · persistencia = y({origen.date()}) = {y[origen]:.0f}"
              f" · naïve semanal = y({sem.date()}) = {y[sem]:.0f}")

    grafica(res[res["serie"] == "llegadas"])


def grafica(res: pd.DataFrame) -> None:
    colores = {"persistencia": "#2a78d6", "naive_semanal": "#eb6834"}
    nombres = {"persistencia": "Persistencia (mañana = hoy)",
               "naive_semanal": "Naïve semanal (mismo día semana anterior)"}
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for b, d in res.groupby("baseline"):
        ax.plot(d["horizonte"], d["MAE"], color=colores[b], lw=2,
                marker="o", ms=7, label=nombres[b])
        ultimo = d.iloc[-1]
        ax.annotate(f"{ultimo['MAE']:.0f}", (ultimo["horizonte"], ultimo["MAE"]),
                    xytext=(8, 0), textcoords="offset points", va="center",
                    color="#333333", fontsize=9)
    ax.set_xticks(list(HORIZONTES))
    ax.set_xlabel("Horizonte (días de antelación)")
    ax.set_ylabel("MAE (pacientes/día)")
    ax.set_ylim(bottom=0)
    ax.set_title("Baselines · error medio absoluto en validación (07/2024–06/2025)",
                 loc="left", fontsize=11)
    ax.grid(axis="y", color="#e5e5e5", lw=0.8)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(INFORMES / "fase2_paso1_baselines.png", dpi=150)


if __name__ == "__main__":
    main()
