"""
FASE 1 · PASO 2 — Serie diaria de episodios (el "número real").

Anteproyecto (Fase 1): "se realizará una agregación temporal de dichos episodios
hasta obtener una serie diaria continua [...] garantizando que no existan
discontinuidades en el calendario".

Qué hace este script:
    1. Cuenta los episodios de cada día según su FECHA DE LLEGADA (`fecha_inicio`):
       total y desglose por área (PED, GIN, GEN). También cuenta las salidas
       (`fecha_fin`) como referencia.
    2. Garantiza un calendario continuo: los 1.461 días de 2022-2025, aunque un
       día no tuviera ningún episodio.
    3. Marca los días con registros perdidos (`dato_incompleto`), que NO deben
       usarse tal cual para entrenar ni para evaluar.
    4. Asigna a cada día su partición cronológica:
           entrenamiento  2022-01-01 → 2023-12-31   (el modelo aprende aquí)
           validación     2024-01-01 → 2024-12-31   (elegimos configuraciones aquí)
           test           2025-01-01 → 2025-12-31   (evaluación final, una sola vez)
    5. Guarda `datos/procesados/serie_diaria.csv` y una gráfica en `informes/`.

Uso:
    python tfg/fase1_paso2_serie_diaria.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos" / "procesados"
INFORMES = RAIZ / "informes"

INICIO, FIN = "2022-01-01", "2025-12-31"

PARTICIONES = [                      # (nombre, desde, hasta) — ambos incluidos
    ("entrenamiento", "2022-01-01", "2023-12-31"),
    ("validacion",    "2024-01-01", "2024-12-31"),
    ("test",          "2025-01-01", "2025-12-31"),
]

# Días con episodios perdidos, detectados al revisar las salidas por hora
# (ver informe del paso 1 y la explicación en la conversación):
DIAS_INCOMPLETOS = {
    "2023-04-14": "casi no hay salidas registradas en todo el día (90 de ~500)",
    "2023-06-16": "no hay ninguna salida registrada de 14:00 a 23:59",
    "2025-12-31": "faltan los pacientes que salieron en 2026 (no hay fichero de 2026)",
}


def construir_serie(ep: pd.DataFrame) -> pd.DataFrame:
    calendario = pd.date_range(INICIO, FIN, freq="D")       # todos los días, sin huecos
    dia_llegada = ep["fecha_inicio"].dt.normalize()

    serie = pd.DataFrame(index=calendario)
    serie.index.name = "fecha"
    serie["llegadas"] = dia_llegada.value_counts().reindex(calendario, fill_value=0)
    for area in ["PED", "GIN", "GEN"]:
        serie[f"llegadas_{area}"] = (dia_llegada[ep["area"] == area]
                                     .value_counts().reindex(calendario, fill_value=0))
    serie["salidas"] = (ep["fecha_fin"].dt.normalize()
                        .value_counts().reindex(calendario, fill_value=0))

    serie["dia_semana"] = serie.index.dayofweek             # 0 = lunes … 6 = domingo
    serie["dato_incompleto"] = serie.index.strftime("%Y-%m-%d").isin(DIAS_INCOMPLETOS)
    serie["particion"] = ""
    for nombre, desde, hasta in PARTICIONES:
        serie.loc[desde:hasta, "particion"] = nombre

    # Comprobaciones: el calendario es continuo y las áreas suman el total
    assert len(serie) == (pd.Timestamp(FIN) - pd.Timestamp(INICIO)).days + 1
    assert (serie[["llegadas_PED", "llegadas_GIN", "llegadas_GEN"]].sum(axis=1)
            == serie["llegadas"]).all()
    assert (serie["particion"] != "").all()
    return serie


def grafica(serie: pd.DataFrame, ruta: Path):
    azul, rojo, gris = "#2a78d6", "#e34948", "#52514e"
    fig, ax = plt.subplots(figsize=(13, 4.8), dpi=150)
    fondo = {"entrenamiento": "#f1f0ec", "validacion": "#e6e5df", "test": "#d9d8d0"}
    titulos = {"entrenamiento": "Entrenamiento (2022–2023)",
               "validacion": "Validación (2024)", "test": "Test (2025)"}
    for nombre, desde, hasta in PARTICIONES:
        ax.axvspan(pd.Timestamp(desde), pd.Timestamp(hasta) + pd.Timedelta(days=1),
                   color=fondo[nombre], zorder=0, lw=0)
        ax.text(pd.Timestamp(desde) + pd.Timedelta(days=8), 790, titulos[nombre],
                fontsize=10, color=gris, va="top")

    ax.plot(serie.index, serie["llegadas"], color=azul, lw=0.8, zorder=2)
    media = serie["llegadas"].where(~serie["dato_incompleto"]).rolling(28, center=True, min_periods=20).mean()
    ax.plot(serie.index, media, color="#0b0b0b", lw=1.6, zorder=3)
    ax.text(pd.Timestamp("2022-02-10"), 610, "media móvil 28 días", fontsize=8.5, color="#0b0b0b")

    malos = serie[serie["dato_incompleto"]]
    ax.scatter(malos.index, malos["llegadas"], s=40, color=rojo, zorder=4,
               edgecolor="white", linewidth=1.5)
    for fecha, fila in malos.iterrows():
        ax.annotate(f"{fecha:%d/%m/%Y}\n{fila['llegadas']} (incompleto)",
                    (fecha, fila["llegadas"]), xytext=(8, -4), textcoords="offset points",
                    fontsize=8, color=gris, va="top")

    ax.set_ylim(100, 800)
    ax.set_xlim(pd.Timestamp(INICIO), pd.Timestamp(FIN) + pd.Timedelta(days=1))
    ax.set_ylabel("Llegadas por día", color=gris)
    ax.set_title("Llegadas diarias a urgencias (conteo de episodios por fecha de llegada)",
                 loc="left", fontsize=12)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%Y"))
    ax.grid(axis="y", color="#e2e1dc", lw=0.6)
    for lado in ["top", "right"]:
        ax.spines[lado].set_visible(False)
    ax.tick_params(colors=gris, labelsize=8.5)
    fig.tight_layout()
    fig.savefig(ruta)
    plt.close(fig)


def resumen(serie: pd.DataFrame) -> str:
    validos = serie[~serie["dato_incompleto"]]
    tabla = (validos.groupby("particion", sort=False)
             .agg(dias=("llegadas", "size"), media=("llegadas", "mean"),
                  minimo=("llegadas", "min"), maximo=("llegadas", "max"))
             .round(1))
    return tabla.to_string()


def main():
    ep = pd.read_parquet(PROCESADOS / "episodios_limpios.parquet",
                         columns=["fecha_inicio", "fecha_fin", "area"])
    serie = construir_serie(ep)
    serie.to_csv(PROCESADOS / "serie_diaria.csv")
    INFORMES.mkdir(exist_ok=True)
    grafica(serie, INFORMES / "fase1_paso2_serie_diaria.png")
    print(resumen(serie))
    print(f"\nGuardado: {PROCESADOS / 'serie_diaria.csv'} ({len(serie)} días)")


if __name__ == "__main__":
    main()
