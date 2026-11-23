"""
FASE 1 · PASO 2 — Serie diaria de episodios (el "número real").

Anteproyecto (Fase 1): "se realizará una agregación temporal de dichos episodios
hasta obtener una serie diaria continua [...] garantizando que no existan
discontinuidades en el calendario".

Qué hace este script:
    1. Cuenta los episodios de cada día según su FECHA DE LLEGADA (`fecha_inicio`):
       total y desglose por área (PED, GIN, GEN). También cuenta las salidas
       (`fecha_fin`) como referencia.
    2. Garantiza un calendario continuo: los 1.642 días del 01/01/2022 al
       30/06/2026, aunque un día no tuviera ningún episodio.
    3. Los días con registros perdidos o dudosos (14/04/2023, 16/06/2023,
       24/05/2024 y 30/06/2026)
       se tratan como DATO FALTANTE, sin imputación (revisión de la tutora,
       11/11/2026): se quedan en la serie, pero `llegadas`, `llegadas_PED`,
       `llegadas_GIN`, `llegadas_GEN` y `salidas` van en blanco (NaN). No se
       rellenan con ningún valor estimado. La serie no tiene huecos en el
       calendario. La gráfica muestra en rojo lo que se llegó a registrar esos
       días, para documentarlo. El 31/12/2025 ya no está incompleto: con el
       fichero de 2026 aparecen los pacientes que salieron en 2026.
    4. Asigna a cada día su partición cronológica. El experimento se elige con
       el parámetro EXPERIMENTO (revisión de la tutora, 12/11/2026):
           1  entrenamiento 01/2022-06/2024 · validación 07/2024-06/2025 · test 07/2025-06/2026
           2  entrenamiento 2022-2024 · validación 2025 · test 01/2026-06/2026
       El experimento 1 es el de toda la Fase 2; el 2 se hace solo con el mejor
       modelo, y los dos se comparan sobre enero-junio de 2026.
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

INICIO, FIN = "2022-01-01", "2026-06-30"

# Experimento (revisión de la tutora, 12/11/2026). Para cambiar de experimento
# basta con cambiar esta línea y volver a ejecutar los pasos 2, 7 y 8.
EXPERIMENTO = 1

EXPERIMENTOS = {                     # (nombre, desde, hasta) — ambos incluidos
    1: [("entrenamiento", "2022-01-01", "2024-06-30"),     # 912 días (71 %)
        ("validacion",    "2024-07-01", "2025-06-30"),     # 365 días (29 %)
        ("test",          "2025-07-01", "2026-06-30")],    # 365 días
    2: [("entrenamiento", "2022-01-01", "2024-12-31"),     # 1.096 días (75 %)
        ("validacion",    "2025-01-01", "2025-12-31"),     # 365 días (25 %)
        ("test",          "2026-01-01", "2026-06-30")],    # 181 días
}
PARTICIONES = EXPERIMENTOS[EXPERIMENTO]

# Columnas que se cuentan con los episodios: en los días incompletos van en blanco
CONTEOS = ["llegadas", "llegadas_PED", "llegadas_GIN", "llegadas_GEN", "salidas"]

# Días con episodios perdidos, detectados al revisar las salidas por hora
# (ver informe del paso 1). Decisión de la tutora: dato faltante (NaN), sin imputar.
DIAS_INCOMPLETOS = {
    "2023-04-14": "casi no hay salidas registradas en todo el día (90 de ~500)",
    "2023-06-16": "no hay ninguna salida registrada de 14:00 a 23:59",
    "2024-05-24": "408 llegadas (lo normal ese mes, unas 565), bajas durante todo el día "
                  "y sin un corte horario; se marca por decisión de Paula (23/11/2026)",
    "2026-06-30": "faltan los pacientes que salieron en julio de 2026 (no hay fichero): "
                  "de 21:00 a 23:59 solo hay 8 llegadas",
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

    # Comprobaciones: el calendario es continuo, las áreas suman el total y
    # todos los días tienen partición
    assert len(serie) == (pd.Timestamp(FIN) - pd.Timestamp(INICIO)).days + 1
    assert (serie[["llegadas_PED", "llegadas_GIN", "llegadas_GEN"]].sum(axis=1)
            == serie["llegadas"]).all()
    assert (serie["particion"] != "").all()
    return serie


def dejar_en_blanco(serie: pd.DataFrame) -> pd.DataFrame:
    """Días incompletos: los conteos pasan a NaN (dato faltante, sin imputación)."""
    final = serie.drop(columns="dato_incompleto").astype({c: "float" for c in CONTEOS})
    final.loc[serie["dato_incompleto"], CONTEOS] = float("nan")

    # Comprobaciones: siguen todos los días, solo esos días están en blanco
    # y el resto de días no ha cambiado
    assert final.index.equals(serie.index)
    en_blanco = final[CONTEOS].isna()
    assert (en_blanco.all(axis=1) == serie["dato_incompleto"]).all()
    assert (en_blanco.any(axis=1) == serie["dato_incompleto"]).all()
    assert final.loc[~serie["dato_incompleto"], CONTEOS].equals(
        serie.loc[~serie["dato_incompleto"], CONTEOS].astype(float))
    return final


def periodo(desde: str, hasta: str) -> str:
    """'2022-01-01', '2024-06-30' → '01/2022–06/2024'."""
    return f"{desde[5:7]}/{desde[:4]}–{hasta[5:7]}/{hasta[:4]}"


def grafica(serie: pd.DataFrame, ruta: Path):
    azul, rojo, gris = "#2a78d6", "#e34948", "#52514e"
    fig, ax = plt.subplots(figsize=(13, 4.8), dpi=150)
    fondo = {"entrenamiento": "#f1f0ec", "validacion": "#e6e5df", "test": "#d9d8d0"}
    etiqueta = {"entrenamiento": "Entrenamiento", "validacion": "Validación", "test": "Test"}
    for nombre, desde, hasta in PARTICIONES:
        if pd.Timestamp(desde) > pd.Timestamp(FIN):          # partición todavía sin datos
            continue
        titulo = f"{etiqueta[nombre]} ({periodo(desde, hasta)})"
        ax.axvspan(pd.Timestamp(desde), pd.Timestamp(hasta) + pd.Timedelta(days=1),
                   color=fondo[nombre], zorder=0, lw=0)
        ax.text(pd.Timestamp(desde) + pd.Timedelta(days=8), 790, titulo,
                fontsize=10, color=gris, va="top")

    validas = serie["llegadas"].where(~serie["dato_incompleto"])    # los días en blanco cortan la línea
    ax.plot(serie.index, validas, color=azul, lw=0.8, zorder=2)
    media = validas.rolling(28, center=True, min_periods=20).mean()
    ax.plot(serie.index, media, color="#0b0b0b", lw=1.6, zorder=3)
    ax.text(pd.Timestamp("2022-02-10"), 610, "media móvil 28 días", fontsize=8.5, color="#0b0b0b")

    malos = serie[serie["dato_incompleto"]]
    ax.scatter(malos.index, malos["llegadas"], s=40, color=rojo, zorder=4,
               edgecolor="white", linewidth=1.5)
    for fecha, fila in malos.iterrows():
        al_final = fecha > pd.Timestamp(FIN) - pd.Timedelta(days=90)   # texto a la izquierda del punto
        ax.annotate(f"{fecha:%d/%m/%Y}\n{fila['llegadas']} (incompleto, sin dato)",
                    (fecha, fila["llegadas"]), xytext=(-8 if al_final else 8, -4),
                    textcoords="offset points", ha="right" if al_final else "left",
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
    INFORMES.mkdir(exist_ok=True)
    grafica(serie, INFORMES / "fase1_paso2_serie_diaria.png")
    print(resumen(serie))

    # Los días incompletos se quedan, con los conteos en blanco (sin imputar)
    final = dejar_en_blanco(serie)
    final.to_csv(PROCESADOS / "serie_diaria.csv")
    print(f"\nExperimento {EXPERIMENTO}: " + " · ".join(f"{n} {periodo(d, h)}" for n, d, h in PARTICIONES))
    print(f"Días en blanco (NaN, sin imputar): {', '.join(DIAS_INCOMPLETOS)}")
    print(f"Guardado: {PROCESADOS / 'serie_diaria.csv'} ({len(final)} días)")


if __name__ == "__main__":
    main()
