"""
FASE 1 · PASO 7 — Variables exógenas.

Anteproyecto (Fase 1): "Sobre esta serie se incorporarán variables exógenas
[...] tales como indicadores de calendario o fuentes de datos públicas externas.
La incorporación de estas variables requerirá, además, un proceso de búsqueda,
selección y validación de fuentes fiables, así como su correcta alineación
temporal con la serie de llegadas del hospital."

Se añaden a la serie diaria (una fila por día, 2022-2025) dos grupos de variables:

A) CALENDARIO
   Fuentes oficiales:
   - Festivos: decretos de fiestas laborales de la Comunidad de Madrid
     (2022, Decreto 2021; 2023, Decreto 101/2022; 2024, BOCM 28/09/2023;
     2025, Decreto 93/2024, BOCM 26/09/2024). Validados además con la
     librería `holidays` (Spain, subdiv='MD'): coinciden los 48 días.
   - Calendario escolar: notas oficiales de la Comunidad de Madrid para
     Infantil y Primaria de los cursos 2021-22 a 2025-26.
   No se incluyen las 2 fiestas locales de cada municipio, porque los
   pacientes vienen de muchos municipios distintos (Majadahonda, Las Rozas,
   Pozuelo, Boadilla...).

B) METEOROLOGÍA
   Fuente: Open-Meteo, API de datos históricos (reanálisis ERA5), punto de
   rejilla más cercano al hospital (40,457 N; 3,935 O; 741 m), zona de
   Majadahonda. Descargado el 26/10/2026 y comprobado con sumas de control.
   Fichero: datos/externos/meteo_open_meteo_2022_2025.csv

Uso:
    python tfg/fase1_paso7_variables_exogenas.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos" / "procesados"
EXTERNOS = RAIZ / "datos" / "externos"

# ---------------------------------------------------------------------------
# Festivos nacionales y autonómicos de la Comunidad de Madrid (decretos)
# ---------------------------------------------------------------------------
FESTIVOS = {
    # 2022 (1 de mayo cae en domingo y no se traslada; Navidad se traslada al 26)
    "2022-01-01": "Año Nuevo", "2022-01-06": "Epifanía", "2022-04-14": "Jueves Santo",
    "2022-04-15": "Viernes Santo", "2022-05-02": "Fiesta de la Comunidad de Madrid",
    "2022-07-25": "Santiago Apóstol", "2022-08-15": "Asunción", "2022-10-12": "Fiesta Nacional",
    "2022-11-01": "Todos los Santos", "2022-12-06": "Constitución", "2022-12-08": "Inmaculada",
    "2022-12-26": "Traslado de Navidad",
    # 2023
    "2023-01-06": "Epifanía", "2023-03-20": "Traslado de San José", "2023-04-06": "Jueves Santo",
    "2023-04-07": "Viernes Santo", "2023-05-01": "Fiesta del Trabajo",
    "2023-05-02": "Fiesta de la Comunidad de Madrid", "2023-08-15": "Asunción",
    "2023-10-12": "Fiesta Nacional", "2023-11-01": "Todos los Santos", "2023-12-06": "Constitución",
    "2023-12-08": "Inmaculada", "2023-12-25": "Navidad",
    # 2024
    "2024-01-01": "Año Nuevo", "2024-01-06": "Epifanía", "2024-03-28": "Jueves Santo",
    "2024-03-29": "Viernes Santo", "2024-05-01": "Fiesta del Trabajo",
    "2024-05-02": "Fiesta de la Comunidad de Madrid", "2024-07-25": "Santiago Apóstol",
    "2024-08-15": "Asunción", "2024-10-12": "Fiesta Nacional", "2024-11-01": "Todos los Santos",
    "2024-12-06": "Constitución", "2024-12-25": "Navidad",
    # 2025
    "2025-01-01": "Año Nuevo", "2025-01-06": "Epifanía", "2025-04-17": "Jueves Santo",
    "2025-04-18": "Viernes Santo", "2025-05-01": "Fiesta del Trabajo",
    "2025-05-02": "Fiesta de la Comunidad de Madrid", "2025-07-25": "Santiago Apóstol",
    "2025-08-15": "Asunción", "2025-11-01": "Todos los Santos", "2025-12-06": "Constitución",
    "2025-12-08": "Inmaculada", "2025-12-25": "Navidad",
}

# ---------------------------------------------------------------------------
# Calendario escolar de la Comunidad de Madrid (Infantil y Primaria)
# Periodos vacacionales: (desde, hasta), ambos incluidos.
# ---------------------------------------------------------------------------
VACACIONES = [
    ("2022-01-01", "2022-01-09", "Navidad"),       # curso 2021-22
    ("2022-04-08", "2022-04-18", "Semana Santa"),
    ("2022-06-25", "2022-09-06", "Verano"),        # fin 24/06/2022, inicio 07/09/2022
    ("2022-12-23", "2023-01-08", "Navidad"),       # curso 2022-23
    ("2023-03-31", "2023-04-10", "Semana Santa"),
    ("2023-06-23", "2023-09-05", "Verano"),        # fin 22/06/2023, inicio 06/09/2023
    ("2023-12-23", "2024-01-07", "Navidad"),       # curso 2023-24
    ("2024-03-23", "2024-03-31", "Semana Santa"),
    ("2024-06-22", "2024-09-08", "Verano"),        # fin 21/06/2024, inicio 09/09/2024
    ("2024-12-21", "2025-01-07", "Navidad"),       # curso 2024-25
    ("2025-04-11", "2025-04-21", "Semana Santa"),
    ("2025-06-21", "2025-09-07", "Verano"),        # fin 20/06/2025, inicio 08/09/2025
    ("2025-12-20", "2025-12-31", "Navidad"),       # curso 2025-26 (hasta el 07/01/2026)
]
# Días no lectivos sueltos (fuera de los periodos vacacionales y de los festivos)
NO_LECTIVOS = [
    "2022-02-25", "2022-02-28",                                       # curso 2021-22
    "2022-10-31", "2022-12-05", "2022-12-07", "2023-02-24", "2023-02-27",  # curso 2022-23
    "2023-10-13", "2023-12-07", "2024-02-22", "2024-02-23", "2024-03-22",
    "2024-04-01", "2024-05-03",                                       # curso 2023-24
    "2025-02-28", "2025-03-03",                                       # curso 2024-25
    "2025-10-13", "2025-11-03",                                       # curso 2025-26
]


def variables_calendario(fechas: pd.DatetimeIndex) -> pd.DataFrame:
    c = pd.DataFrame(index=fechas)
    c["anio"] = fechas.year
    c["mes"] = fechas.month
    c["dia_mes"] = fechas.day
    c["dia_anio"] = fechas.dayofyear
    c["semana_anio"] = fechas.isocalendar().week.astype(int).values
    c["dia_semana"] = fechas.dayofweek                    # 0 = lunes … 6 = domingo
    c["fin_de_semana"] = (c["dia_semana"] >= 5).astype(int)

    fest = pd.Series(FESTIVOS)
    fest.index = pd.to_datetime(fest.index)
    c["festivo"] = fechas.isin(fest.index).astype(int)
    c["nombre_festivo"] = fest.reindex(fechas).fillna("").values

    no_laborable = (c["fin_de_semana"] == 1) | (c["festivo"] == 1)
    laborable = ~no_laborable
    # Día laborable justo después de uno o varios días no laborables (p. ej. los lunes)
    c["primer_laborable"] = (laborable & no_laborable.shift(1, fill_value=True)).astype(int)
    # Víspera y día siguiente a un festivo
    c["vispera_festivo"] = c["festivo"].shift(-1, fill_value=0).astype(int)
    c["post_festivo"] = c["festivo"].shift(1, fill_value=0).astype(int)
    # Puente: laborable entre un festivo y un fin de semana (o entre dos no laborables)
    c["puente"] = (laborable & no_laborable.shift(1, fill_value=False)
                   & no_laborable.shift(-1, fill_value=False)).astype(int)
    c["nochebuena_nochevieja"] = (((c["mes"] == 12) & c["dia_mes"].isin([24, 31]))).astype(int)

    c["vacaciones_escolares"] = 0
    c["tipo_vacaciones"] = ""
    for desde, hasta, tipo in VACACIONES:
        m = (fechas >= desde) & (fechas <= hasta)
        c.loc[m, "vacaciones_escolares"] = 1
        c.loc[m, "tipo_vacaciones"] = tipo
    c["dia_lectivo"] = (laborable & (c["vacaciones_escolares"] == 0)
                        & ~fechas.isin(pd.to_datetime(NO_LECTIVOS))).astype(int)
    return c


def variables_meteo(fechas: pd.DatetimeIndex) -> pd.DataFrame:
    m = pd.read_csv(EXTERNOS / "meteo_open_meteo_2022_2025.csv", parse_dates=["fecha"]).set_index("fecha")
    m = m.reindex(fechas)
    assert m.notna().all().all(), "Faltan días en la meteorología"
    m["dia_lluvia"] = (m["precipitacion"] >= 1).astype(int)          # al menos 1 mm
    m["calor_extremo"] = (m["temp_max"] >= 36).astype(int)           # umbral de aviso por calor en Madrid
    m["helada"] = (m["temp_min"] < 0).astype(int)
    m["amplitud_termica"] = (m["temp_max"] - m["temp_min"]).round(1)
    return m


def main():
    serie = pd.read_csv(PROCESADOS / "serie_diaria.csv", parse_dates=["fecha"]).set_index("fecha")
    fechas = serie.index
    cal = variables_calendario(fechas)
    met = variables_meteo(fechas)
    datos = pd.concat([serie.drop(columns=["dia_semana"]), cal, met], axis=1)

    # Comprobaciones de alineación temporal: mismo calendario y sin huecos
    assert len(datos) == 1461 and datos.index.is_monotonic_increasing
    assert (datos.index.to_series().diff().dropna() == pd.Timedelta(days=1)).all()
    assert datos["festivo"].sum() == len(FESTIVOS)
    try:                                                              # validación cruzada opcional
        import holidays
        lib = {pd.Timestamp(d) for y in range(2022, 2026) for d in holidays.Spain(years=y, subdiv="MD")}
        assert lib == set(pd.to_datetime(list(FESTIVOS))), "Los festivos no coinciden con la librería"
    except ImportError:
        pass

    datos.to_csv(PROCESADOS / "dataset_fase1.csv")
    print(f"Guardado dataset_fase1.csv: {datos.shape[0]} días × {datos.shape[1]} columnas")
    return datos


if __name__ == "__main__":
    main()
