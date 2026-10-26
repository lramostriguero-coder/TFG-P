"""
FASE 1 · PASO 8 — Normalización de las variables.

Anteproyecto (Fase 1): "la aplicación de métodos de normalización".

Por qué se normaliza: las variables tienen escalas muy distintas (llegadas
~500, temperatura ~20, lluvia ~0-80 mm, humedad ~20-100 %). Muchos modelos
(redes neuronales, ARIMAX con regresores...) aprenden peor si unas variables
"pesan" más solo por tener números más grandes. Normalizar las pone en una
escala comparable.

Reglas que se aplican:
  1. Variables continuas → valor normalizado = (x − media) / desviación típica.
     La lluvia es muy asimétrica (casi siempre 0), así que antes se aplica
     log(1 + x).
  2. Variables cíclicas (día de la semana, mes, día del año) → seno y coseno,
     para que el modelo sepa que el domingo va justo antes del lunes y
     diciembre justo antes de enero. Quedan entre −1 y 1.
  3. Variables binarias (0/1: festivo, vacaciones…) → se dejan igual.

MUY IMPORTANTE: la media y la desviación se calculan SOLO con los días de
ENTRENAMIENTO (2022-2023) y sin los días incompletos. Después se aplican esos
mismos valores a validación y test. Si se usaran los datos de 2024-2025 para
calcularlas, el modelo "vería" información del futuro (fuga de datos).

Los parámetros se guardan en `parametros_normalizacion.csv` para poder
deshacer la normalización de las predicciones (volver a "pacientes/día").

Uso:
    python tfg/fase1_paso8_normalizacion.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PROCESADOS = RAIZ / "datos" / "procesados"

CONTINUAS = ["llegadas", "llegadas_PED", "llegadas_GIN", "llegadas_GEN",
             "temp_max", "temp_min", "temp_media", "precipitacion", "humedad"]
LOGARITMO = ["precipitacion"]
CICLICAS = {"dia_semana": 7, "mes": 12, "dia_anio": 365.25}
BINARIAS = ["fin_de_semana", "festivo", "vacaciones_escolares", "dia_lectivo"]


def ajustar(datos: pd.DataFrame) -> pd.DataFrame:
    """Calcula media y desviación de cada variable continua con el entrenamiento."""
    entr = datos[(datos["particion"] == "entrenamiento") & (~datos["dato_incompleto"])]
    filas = []
    for col in CONTINUAS:
        x = np.log1p(entr[col]) if col in LOGARITMO else entr[col]
        filas.append({"variable": col, "transformacion": "log(1+x) y z" if col in LOGARITMO else "z",
                      "media": x.mean(), "desviacion": x.std(), "dias_usados": len(x)})
    return pd.DataFrame(filas).set_index("variable")


def transformar(datos: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    out = datos[["particion", "dato_incompleto"]].copy()
    for col in CONTINUAS:
        x = np.log1p(datos[col]) if col in LOGARITMO else datos[col]
        out[f"{col}_normalizada"] = ((x - params.loc[col, "media"]) / params.loc[col, "desviacion"]).round(4)
    for col, periodo in CICLICAS.items():
        valor = datos[col] - (1 if col in ("mes", "dia_anio") else 0)       # empezar en 0
        out[f"{col}_sin"] = np.sin(2 * np.pi * valor / periodo).round(4)
        out[f"{col}_cos"] = np.cos(2 * np.pi * valor / periodo).round(4)
    for col in BINARIAS:
        out[col] = datos[col].astype(int)
    return out


def desnormalizar(z, variable: str, params: pd.DataFrame):
    """Convierte una predicción normalizada de vuelta a su escala original."""
    x = np.asarray(z) * params.loc[variable, "desviacion"] + params.loc[variable, "media"]
    return np.expm1(x) if variable in LOGARITMO else x


def main():
    datos = pd.read_csv(PROCESADOS / "dataset_fase1.csv", parse_dates=["fecha"], index_col="fecha")
    params = ajustar(datos)
    norm = transformar(datos, params)

    # Comprobaciones: en entrenamiento cada variable z tiene media 0 y desviación 1,
    # y desnormalizar devuelve exactamente los valores originales.
    entr = norm[(norm["particion"] == "entrenamiento") & (~norm["dato_incompleto"])]
    for col in CONTINUAS:
        assert abs(entr[f"{col}_normalizada"].mean()) < 1e-3 and abs(entr[f"{col}_normalizada"].std() - 1) < 1e-3, col
        assert np.allclose(desnormalizar(norm[f"{col}_normalizada"], col, params), datos[col], atol=0.01), col

    params.round(6).to_csv(PROCESADOS / "parametros_normalizacion.csv")
    norm.to_csv(PROCESADOS / "dataset_fase1_normalizado.csv")
    print(params.round(3).to_string())
    print(f"\nGuardado dataset_fase1_normalizado.csv: {norm.shape[0]} días × {norm.shape[1]} columnas")


if __name__ == "__main__":
    main()
