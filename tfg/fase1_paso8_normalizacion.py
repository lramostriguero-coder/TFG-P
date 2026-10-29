"""
FASE 1 · PASO 8 — Normalización de las variables.

Anteproyecto (Fase 1): "la aplicación de métodos de normalización".

Por qué se normaliza: las variables tienen escalas muy distintas (llegadas
~500, temperatura ~20, lluvia ~0-80 mm, humedad ~20-100 %). Muchos modelos
(redes neuronales, ARIMAX con regresores...) aprenden peor si unas variables
"pesan" más solo por tener números más grandes. Normalizar las pone en una
escala comparable.

Reglas que se aplican:
  1. Variables continuas → normalización min-max:
         valor normalizado = (valor − mínimo) / (máximo − mínimo)
     Queda entre 0 (el mínimo) y 1 (el máximo).
  2. Variables cíclicas (día de la semana, mes, día del año) → seno y coseno,
     para que el modelo sepa que el domingo va justo antes del lunes y
     diciembre justo antes de enero. Quedan entre −1 y 1.
  3. Variables binarias (0/1: festivo, vacaciones…) → se dejan igual.

MUY IMPORTANTE: el mínimo y el máximo se calculan SOLO con los días de
ENTRENAMIENTO (2022-2023); los días incompletos ya se eliminaron en el paso 2.
Después se aplican esos mismos valores a validación y test. Si se usaran los
datos de 2024-2025 para calcularlos, el modelo "vería" información del futuro
(fuga de datos). Por eso, en validación y test algún día puede quedar un poco
por debajo de 0 o por encima de 1, si supera los valores de entrenamiento.

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
LOGARITMO = []          # sin transformaciones extra: el anteproyecto solo pide normalizar
CICLICAS = {"dia_semana": 7, "mes": 12, "dia_anio": 365.25}
BINARIAS = ["fin_de_semana", "festivo", "vacaciones_escolares", "dia_lectivo"]


def ajustar(datos: pd.DataFrame) -> pd.DataFrame:
    """Calcula el mínimo y el máximo de cada variable continua con el entrenamiento."""
    entr = datos[datos["particion"] == "entrenamiento"]
    filas = []
    for col in CONTINUAS:
        x = np.log1p(entr[col]) if col in LOGARITMO else entr[col]
        filas.append({"variable": col, "transformacion": "log(1+x) y min-max" if col in LOGARITMO else "min-max",
                      "minimo": x.min(), "maximo": x.max(), "dias_usados": len(x)})
    return pd.DataFrame(filas).set_index("variable")


def transformar(datos: pd.DataFrame, params: pd.DataFrame) -> pd.DataFrame:
    out = datos[["particion"]].copy()
    for col in CONTINUAS:
        x = np.log1p(datos[col]) if col in LOGARITMO else datos[col]
        mn, mx = params.loc[col, "minimo"], params.loc[col, "maximo"]
        out[f"{col}_normalizada"] = ((x - mn) / (mx - mn)).round(4)
    for col, periodo in CICLICAS.items():
        valor = datos[col] - (1 if col in ("mes", "dia_anio") else 0)       # empezar en 0
        out[f"{col}_sin"] = np.sin(2 * np.pi * valor / periodo).round(4)
        out[f"{col}_cos"] = np.cos(2 * np.pi * valor / periodo).round(4)
    for col in BINARIAS:
        out[col] = datos[col].astype(int)
    return out


def desnormalizar(z, variable: str, params: pd.DataFrame):
    """Convierte una predicción normalizada de vuelta a su escala original."""
    mn, mx = params.loc[variable, "minimo"], params.loc[variable, "maximo"]
    x = np.asarray(z) * (mx - mn) + mn
    return np.expm1(x) if variable in LOGARITMO else x


def main():
    datos = pd.read_csv(PROCESADOS / "dataset_fase1.csv", parse_dates=["fecha"], index_col="fecha")
    params = ajustar(datos)
    norm = transformar(datos, params)

    # Comprobaciones: en entrenamiento cada variable va exactamente de 0 a 1,
    # y desnormalizar devuelve los valores originales.
    entr = norm[norm["particion"] == "entrenamiento"]
    for col in CONTINUAS:
        assert entr[f"{col}_normalizada"].min() == 0 and entr[f"{col}_normalizada"].max() == 1, col
        tol = 1e-4 * (params.loc[col, "maximo"] - params.loc[col, "minimo"]) + 1e-9    # por el redondeo a 4 decimales
        assert np.allclose(desnormalizar(norm[f"{col}_normalizada"], col, params), datos[col], atol=tol), col

    params.round(6).to_csv(PROCESADOS / "parametros_normalizacion.csv")
    norm.to_csv(PROCESADOS / "dataset_fase1_normalizado.csv")
    print(params.round(3).to_string())
    print(f"\nGuardado dataset_fase1_normalizado.csv: {norm.shape[0]} días × {norm.shape[1]} columnas")


if __name__ == "__main__":
    main()
