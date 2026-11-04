"""
Lectura de volcados .sql exportados con phpMyAdmin (MariaDB/MySQL).

Permite leer los ficheros `episodios (AAAA).sql` y `codificacion (AAAA).sql`
directamente en un DataFrame de pandas, sin tener que instalar una base de datos.

Cómo es un volcado de phpMyAdmin:
    INSERT INTO `tabla` (`col1`, `col2`, ...) VALUES
    ('valor', 123, NULL, ...),
    ('valor', 456, 'texto con \\'comilla\\'', ...);

Cada fila va en su propia línea, empieza por "(" y termina por "),"
(o por ");" si es la última fila de ese bloque INSERT). Los textos van entre
comillas simples y los caracteres especiales se escapan con una barra invertida.
"""
import csv
import re
from pathlib import Path

import pandas as pd


def leer_volcado(ruta: str | Path) -> pd.DataFrame:
    """Devuelve todas las filas de los INSERT del fichero como un DataFrame.

    Todos los valores se leen como texto (str) o None si eran NULL; la
    conversión a fechas y números se hace después, en la fase de limpieza,
    para poder detectar y contar los valores que no se pueden convertir.
    """
    columnas = None
    filas = []
    with open(ruta, encoding="utf-8") as f:
        for num_linea, linea in enumerate(f, start=1):
            if linea.startswith("INSERT INTO"):
                # Nombres de columna: lo que va entre comillas invertidas antes de VALUES
                cabecera = linea.split("VALUES")[0]
                nuevas = re.findall(r"`(\w+)`", cabecera)[1:]   # [0] es el nombre de la tabla
                if columnas is not None and nuevas != columnas:
                    raise ValueError(f"{ruta}: las columnas cambian en la línea {num_linea}")
                columnas = nuevas
                continue
            if not linea.startswith("("):
                continue                                   # comentarios, CREATE TABLE, etc.

            cuerpo = linea.rstrip("\r\n")
            cuerpo = cuerpo[1:-2] if cuerpo.endswith(("),", ");")) else cuerpo[1:-1]
            # El módulo csv sabe separar por comas respetando las comillas
            # simples y los escapes con barra invertida.
            valores = next(csv.reader([cuerpo], quotechar="'", escapechar="\\",
                                      skipinitialspace=True))
            if len(valores) != len(columnas):
                raise ValueError(f"{ruta}: la línea {num_linea} tiene {len(valores)} "
                                 f"valores y se esperaban {len(columnas)}")
            filas.append([None if v == "NULL" else v for v in valores])

    return pd.DataFrame(filas, columns=columnas)
