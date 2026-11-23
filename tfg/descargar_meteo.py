"""
FASE 1 · PASO 7 (auxiliar) — Descarga de la meteorología diaria de Open-Meteo.

Fuente: Open-Meteo, API de datos históricos (https://archive-api.open-meteo.com),
reanálisis ERA5, configuración por defecto (`best_match`). Punto: 40,457 N;
3,935 O, zona de Majadahonda (el punto de rejilla más cercano al hospital).
Zona horaria Europe/Madrid, para que cada valor diario vaya de 00:00 a 23:59
hora local, igual que las llegadas.

Variables (una fila por día):
    temp_max, temp_min, temp_media  temperatura a 2 m (°C)
    precipitacion                    lluvia acumulada del día (mm)
    humedad                          humedad relativa media (%)

Es la meteorología OBSERVADA (reanálisis), no una previsión: en la Fase 2 solo
se puede usar la de los días hasta el día en que se hace la predicción.

Comprobación: los días de 2022-2025 coinciden exactamente con el fichero que se
descargó a mano el 26/10/2026 (`meteo_open_meteo_2022_2025.csv`, ya sustituido).

Uso:
    python tfg/descargar_meteo.py
"""
import json
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "externos" / "meteo_open_meteo_2022_2026.csv"
INICIO, FIN = "2022-01-01", "2026-06-30"

URL = ("https://archive-api.open-meteo.com/v1/archive"
       "?latitude=40.457&longitude=-3.935"
       f"&start_date={INICIO}&end_date={FIN}"
       "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
       "precipitation_sum,relative_humidity_2m_mean"
       "&timezone=Europe%2FMadrid")
NOMBRES = {"time": "fecha", "temperature_2m_max": "temp_max", "temperature_2m_min": "temp_min",
           "temperature_2m_mean": "temp_media", "precipitation_sum": "precipitacion",
           "relative_humidity_2m_mean": "humedad"}


def main():
    with urllib.request.urlopen(URL, timeout=120) as r:
        datos = json.load(r)
    meteo = pd.DataFrame(datos["daily"]).rename(columns=NOMBRES)
    meteo["fecha"] = pd.to_datetime(meteo["fecha"])

    # Comprobaciones: todos los días del periodo, sin huecos ni valores vacíos
    assert meteo["fecha"].tolist() == list(pd.date_range(INICIO, FIN, freq="D"))
    assert meteo.notna().all().all(), "Faltan valores en la meteorología"

    meteo.to_csv(SALIDA, index=False, date_format="%Y-%m-%d")
    print(f"Guardado {SALIDA.name}: {len(meteo)} días "
          f"(punto de rejilla {datos['latitude']:.3f}, {datos['longitude']:.3f}; {datos['elevation']:.0f} m)")


if __name__ == "__main__":
    main()
