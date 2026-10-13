"""
Ingesta del volcado prd_unificado.sql.

Lee las sentencias INSERT del fichero .sql (exportado de MariaDB con phpMyAdmin)
sin necesidad de instalar una base de datos, y devuelve una lista de filas
con las columnas JSON ya convertidas a diccionarios de Python.
"""
import json
from pathlib import Path

COLUMNAS = ["fecha", "afl", "pet", "ing", "enf", "afl_hora"]


def _leer_tuplas(texto: str):
    """Recorre el texto carácter a carácter y extrae cada tupla (v1, v2, ...).

    Respeta las comillas simples y los escapes con barra invertida de MySQL,
    para no confundir las comas de dentro del JSON con separadores de columna.
    """
    i, n = 0, len(texto)
    while i < n:
        if texto[i] != "(":
            i += 1
            continue
        i += 1
        valores, actual, en_cadena = [], [], False
        while i < n:
            c = texto[i]
            if en_cadena:
                if c == "\\":                      # escape: \" \' \\ \n ...
                    sig = texto[i + 1]
                    actual.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(sig, sig))
                    i += 2
                    continue
                if c == "'":
                    if texto[i + 1] == "'":        # '' = comilla literal
                        actual.append("'")
                        i += 2
                        continue
                    en_cadena = False
                else:
                    actual.append(c)
            else:
                if c == "'":
                    en_cadena = True
                    actual = []
                elif c == ",":
                    valores.append("".join(actual).strip())
                    actual = []
                elif c == ")":
                    valores.append("".join(actual).strip())
                    i += 1
                    break
                elif not c.isspace():
                    actual.append(c)               # valores sin comillas (NULL, números)
            i += 1
        yield valores


def cargar(ruta="prd_unificado.sql"):
    texto = Path(ruta).read_text(encoding="utf-8")
    filas = []
    for bloque in texto.split("INSERT INTO `prd_unificado`")[1:]:
        cuerpo = bloque.split("VALUES", 1)[1]
        cuerpo = cuerpo.split(";\n", 1)[0]
        for vals in _leer_tuplas(cuerpo):
            if len(vals) != len(COLUMNAS):
                raise ValueError(f"Fila con {len(vals)} columnas: {vals[:1]}")
            fila = {"fecha": vals[0]}
            for col, v in zip(COLUMNAS[1:], vals[1:]):
                fila[col] = None if v in ("NULL", "") else json.loads(v)
            filas.append(fila)
    return filas


if __name__ == "__main__":
    filas = cargar()
    print(f"{len(filas)} filas leídas: {filas[0]['fecha']} -> {filas[-1]['fecha']}")
