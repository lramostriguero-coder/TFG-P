"""
FASE 1 · PASO 1 — Ingesta y curación del dato crudo hospitalario.

Anteproyecto (Fase 1): "el punto de partida consistirá en la ingesta y curación
del dato crudo hospitalario, compuesto por episodios de urgencias y su
correspondiente codificación clínica (CIE) [...] Este proceso incluirá la
identificación y tratamiento de registros duplicados, incompletos o
inconsistentes, así como la homogeneización de los distintos campos
disponibles en un formato unificado."

Qué hace este script:
    1. Lee los volcados anuales de episodios y codificación (2022-2025) y los une.
    2. Convierte cada columna a su tipo (fechas, números, texto limpio).
    3. Trata DUPLICADOS (se eliminan).
    4. Marca registros INCOMPLETOS e INCONSISTENTES con columnas `flag_*`
       (no se borran: decidiremos qué hacer con ellos en pasos posteriores).
    5. HOMOGENEIZA campos: nivel de triaje 1-5, área asistencial (PED/GIN/GEN),
       ingreso sí/no, duración, diagnóstico principal y su capítulo CIE-10.
    6. Guarda dos ficheros limpios (.parquet) y un informe de calidad (.md).

Uso:
    python tfg/fase1_paso1_ingesta.py --origen "C:/PAULA/UNI/TFG/Datos_urgencias"

Los datos de salida se guardan en la carpeta `datos/` del repositorio, que está
excluida de git (.gitignore): contienen datos de pacientes y NO deben subirse.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from lectura_sql import leer_volcado

ANIOS = [2022, 2023, 2024, 2025]
RAIZ = Path(__file__).resolve().parent.parent

# Columnas que se descartan y por qué
COLUMNAS_DESCARTADAS = {
    "fuente": "vacía en el 100 % de los registros",
    "resp_final": "vacía en el 100 % de los registros",
    "resp_ing": "vacía en el 100 % de los registros",
    "fecha_ing": "vacía en el 100 % de los registros",
    "resp_acl": "identificador del profesional; no aporta a la predicción",
    "resp_alta": "identificador del profesional; no aporta a la predicción",
    "tipo_acto": "valor constante ('URGENCIAS')",
    "f_nacimiento": "dato personal redundante con `edad` (se verifica antes la coherencia)",
}

# Capítulos de la CIE-10-ES: (código inicial, código final, nombre corto).
# Se comparan los 3 primeros caracteres del código (p. ej. 'J18').
CAPITULOS_CIE10 = [
    ("A00", "B99", "Infecciosas y parasitarias"),
    ("C00", "D49", "Neoplasias"),
    ("D50", "D89", "Sangre y órganos hematopoyéticos"),
    ("E00", "E89", "Endocrinas, nutricionales y metabólicas"),
    ("F01", "F99", "Trastornos mentales"),
    ("G00", "G99", "Sistema nervioso"),
    ("H00", "H59", "Ojo"),
    ("H60", "H95", "Oído"),
    ("I00", "I99", "Aparato circulatorio"),
    ("J00", "J99", "Aparato respiratorio"),
    ("K00", "K95", "Aparato digestivo"),
    ("L00", "L99", "Piel y tejido subcutáneo"),
    ("M00", "M99", "Aparato musculoesquelético"),
    ("N00", "N99", "Aparato genitourinario"),
    ("O00", "O9A", "Embarazo, parto y puerperio"),
    ("P00", "P96", "Afecciones perinatales"),
    ("Q00", "Q99", "Malformaciones congénitas"),
    ("R00", "R99", "Síntomas y hallazgos anormales"),
    ("S00", "T88", "Traumatismos y envenenamientos"),
    ("U00", "U99", "Códigos especiales (COVID-19)"),
    ("V00", "Y99", "Causas externas"),
    ("Z00", "Z99", "Factores que influyen en el estado de salud"),
]


# ----------------------------------------------------------------------------
# 1. Lectura
# ----------------------------------------------------------------------------
def leer_anios(origen: Path, tabla: str) -> pd.DataFrame:
    partes = []
    for anio in ANIOS:
        ruta = origen / f"{tabla} ({anio}).sql"
        print(f"  leyendo {ruta.name} ...", flush=True)
        df = leer_volcado(ruta)
        df["anio_fichero"] = anio          # de qué fichero viene cada fila
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def limpiar_textos(df: pd.DataFrame) -> pd.DataFrame:
    """Quita espacios sobrantes y convierte los textos vacíos ('') en nulos."""
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip().replace("", np.nan)
    return df


def a_fecha(serie: pd.Series, informe: dict, nombre: str) -> pd.Series:
    """Convierte a fecha; lo que no sea una fecha válida (p. ej. '1900-01-00') pasa a nulo."""
    convertida = pd.to_datetime(serie, errors="coerce", format="%Y-%m-%d %H:%M:%S")
    invalidas = int((serie.notna() & convertida.isna()).sum())
    if invalidas:
        informe.setdefault("fechas_invalidas", {})[nombre] = invalidas
    return convertida


# ----------------------------------------------------------------------------
# 2. Episodios
# ----------------------------------------------------------------------------
def curar_episodios(ep: pd.DataFrame, informe: dict) -> pd.DataFrame:
    informe["ep_filas_leidas"] = len(ep)
    informe["ep_filas_por_fichero"] = ep.groupby("anio_fichero").size().to_dict()
    informe["ep_vacios_100"] = [c for c in ep.columns if ep[c].isna().all()]
    ep = limpiar_textos(ep)

    # --- Tipos ---
    for col in ["fecha_inicio", "fecha_fin", "fecha_triaje"]:
        ep[col] = a_fecha(ep[col], informe, col)
    ep["f_nacimiento"] = pd.to_datetime(ep["f_nacimiento"], errors="coerce")
    ep["edad"] = pd.to_numeric(ep["edad"], errors="coerce")
    for col in ["proceso", "nhc", "t_ini_tri", "t_ini_fin"]:
        ep[col] = pd.to_numeric(ep[col], errors="coerce").astype("Int64")

    # --- Duplicados ---
    # Un acto clínico identifica una visita. Si aparece dos veces (p. ej. en dos
    # ficheros anuales) nos quedamos con la versión del fichero más reciente.
    columnas_datos = [c for c in ep.columns if c != "anio_fichero"]
    informe["ep_duplicados_exactos"] = int(ep.duplicated(columnas_datos).sum())
    informe["ep_duplicados_acto"] = int(ep["acto_clinico"].duplicated().sum())
    ep = (ep.sort_values("anio_fichero")
            .drop_duplicates("acto_clinico", keep="last")
            .sort_values("fecha_inicio", kind="stable")
            .reset_index(drop=True))

    # --- Comprobación de coherencia de la edad antes de quitar f_nacimiento ---
    edad_calc = (ep["fecha_inicio"] - ep["f_nacimiento"]).dt.days / 365.25
    informe["ep_edad_incoherente"] = int(((edad_calc - ep["edad"]).abs() > 1).sum())

    # --- Campos homogeneizados ---
    ep["duracion_min"] = (ep["fecha_fin"] - ep["fecha_inicio"]).dt.total_seconds() / 60
    ep["es_ingreso"] = ep["motivo_alta"].eq("HOSPITALIZACION U")
    ep["area"] = np.select(
        [ep["edad"] < 16,
         ep["servicio"].isin(["Urgencias Ginecológicas", "Urgencias Obstétricas", "Obstetricia"])],
        ["PED", "GIN"], default="GEN")
    # El triaje aparece escrito de varias formas ('4 ESTANDAR - 120 min',
    # '4 ESTANDAR -120 m/PED 90 m', ...). Nos quedamos con el nivel 1-5
    # (1 = crítico, 5 = no urgente), que es lo que todas tienen en común.
    nivel = pd.to_numeric(ep["valor_triaje"].str[0], errors="coerce")
    nivel = nivel.where(nivel.between(1, 5))      # '0' aparece como "sin valor": no es un nivel real
    palabras = {"CRITICO": 1, "EMERGENCIA": 2, "URGENCIA": 3, "ESTANDAR": 4, "NO URGEN": 5}
    nivel_por_gravedad = pd.Series(np.nan, index=ep.index)
    for palabra, valor in reversed(list(palabras.items())):   # 'NO URGEN' antes que 'URGENCIA'
        pendiente = nivel_por_gravedad.isna() & ep["gravedad"].str.startswith(palabra, na=False)
        nivel_por_gravedad[pendiente] = valor
    ep["nivel_triaje"] = nivel.fillna(nivel_por_gravedad).astype("Int64")

    # --- Marcas de calidad (no se borra nada) ---
    ep["flag_sin_triaje"] = ep["nivel_triaje"].isna()
    ep["flag_triaje_incoherente"] = (ep["fecha_triaje"] < ep["fecha_inicio"]) | \
                                    (ep["fecha_triaje"] > ep["fecha_fin"])
    ep["flag_estancia_larga"] = ep["duracion_min"] > 72 * 60          # más de 72 h en urgencias
    ep["flag_fin_antes_inicio"] = ep["duracion_min"] < 0
    ep["flag_fuera_periodo"] = (ep["fecha_inicio"] < "2022-01-01") | (ep["fecha_inicio"] >= "2026-01-01")

    ep = ep.drop(columns=list(COLUMNAS_DESCARTADAS))
    informe["ep_filas_finales"] = len(ep)
    return ep


# ----------------------------------------------------------------------------
# 3. Codificación
# ----------------------------------------------------------------------------
def capitulo_cie10(codigo: pd.Series) -> pd.Series:
    tres = codigo.str[:3]
    resultado = pd.Series(pd.NA, index=codigo.index, dtype="string")
    for ini, fin, nombre in CAPITULOS_CIE10:
        resultado[(tres >= ini) & (tres <= fin)] = nombre
    return resultado


def curar_codificacion(cod: pd.DataFrame, ep: pd.DataFrame, informe: dict) -> pd.DataFrame:
    informe["cod_filas_leidas"] = len(cod)
    cod = limpiar_textos(cod)
    cod["orden"] = pd.to_numeric(cod["orden"]).astype(int)
    cod["fecha"] = a_fecha(cod["fecha"], informe, "codificacion.fecha")

    informe["cod_duplicados"] = int(cod.duplicated(["acto_clinico", "orden"]).sum())
    cod = cod.drop_duplicates(["acto_clinico", "orden"], keep="last")

    huerfanos = ~cod["acto_clinico"].isin(ep["acto_clinico"])
    informe["cod_huerfanos"] = int(huerfanos.sum())          # códigos sin episodio
    cod = cod[~huerfanos]

    # Los códigos con '/' (p. ej. '8000/1') son de morfología tumoral (CIE-O),
    # no diagnósticos CIE-10: se marcan para no usarlos como diagnóstico principal.
    cod["es_morfologia"] = cod["codigo"].str.contains("/", regex=False)
    cod["capitulo"] = capitulo_cie10(cod["codigo"]).where(~cod["es_morfologia"])
    informe["cod_filas_finales"] = len(cod)
    return cod.drop(columns="anio_fichero").reset_index(drop=True)


def anadir_diagnostico_principal(ep: pd.DataFrame, cod: pd.DataFrame, informe: dict) -> pd.DataFrame:
    """Diagnóstico principal = diagnóstico (tipo 'D') con menor `orden` de cada episodio.

    Normalmente es el de orden 1, pero en unos pocos miles de episodios el orden 1
    no existe o no es un diagnóstico, y el principal es el de orden 2.
    """
    dx = (cod[(cod["tipo"] == "D") & ~cod["es_morfologia"]]
          .sort_values(["acto_clinico", "orden"])
          .drop_duplicates("acto_clinico")
          [["acto_clinico", "codigo", "capitulo"]]
          .rename(columns={"codigo": "dx_principal", "capitulo": "dx_capitulo"}))
    ep = ep.merge(dx, on="acto_clinico", how="left")
    ep["flag_sin_diagnostico"] = ep["dx_principal"].isna()
    informe["ep_con_diagnostico"] = float(1 - ep["flag_sin_diagnostico"].mean())
    return ep


# ----------------------------------------------------------------------------
# 4. Informe
# ----------------------------------------------------------------------------
def escribir_informe(ep: pd.DataFrame, cod: pd.DataFrame, inf: dict, ruta: Path):
    n = len(ep)
    pct = lambda x: f"{x} ({100 * x / n:.2f} %)"
    flags = [c for c in ep.columns if c.startswith("flag_")]
    lineas = [
        "# Fase 1 · Paso 1 — Informe de calidad del dato crudo", "",
        "## Lectura", "",
        f"- Episodios leídos: **{inf['ep_filas_leidas']:,}** "
        f"({', '.join(f'{a}: {v:,}' for a, v in inf['ep_filas_por_fichero'].items())})",
        f"- Filas de codificación leídas: **{inf['cod_filas_leidas']:,}**", "",
        "## Duplicados", "",
        f"- Episodios duplicados (mismo `acto_clinico`): {inf['ep_duplicados_acto']} "
        f"(idénticos en todo: {inf['ep_duplicados_exactos']}) → eliminados",
        f"- Codificación duplicada (mismo episodio y `orden`): {inf['cod_duplicados']} → eliminados",
        f"- Códigos sin episodio asociado: {inf['cod_huerfanos']}", "",
        "## Datos inválidos e incoherentes (se marcan, no se borran)", "",
        "| Marca | Episodios | Significado |", "|---|---|---|",
    ]
    significado = {
        "flag_sin_triaje": "sin nivel de triaje registrado",
        "flag_triaje_incoherente": "triaje antes de la llegada o después de la salida",
        "flag_estancia_larga": "más de 72 h en urgencias",
        "flag_fin_antes_inicio": "fecha de salida anterior a la de llegada",
        "flag_fuera_periodo": "llegada fuera de 2022-2025",
        "flag_sin_diagnostico": "sin diagnóstico principal codificado",
    }
    for f in flags:
        lineas.append(f"| `{f}` | {pct(int(ep[f].sum()))} | {significado.get(f, '')} |")
    lineas += [
        "",
        f"- Fechas no válidas convertidas a nulo: {inf.get('fechas_invalidas', {})}",
        f"- Edades incoherentes con la fecha de nacimiento (>1 año): {inf['ep_edad_incoherente']}",
        "",
        "## Columnas descartadas", "",
        *[f"- `{c}`: {motivo}" for c, motivo in COLUMNAS_DESCARTADAS.items()],
        "",
        "## Resultado", "",
        f"- `episodios_limpios.parquet`: **{n:,}** episodios × {ep.shape[1]} columnas",
        f"- `codificacion_limpia.parquet`: **{len(cod):,}** filas",
        f"- Episodios con diagnóstico principal: {100 * inf['ep_con_diagnostico']:.1f} %",
        "",
        "### Reparto por área asistencial", "",
        ep["area"].value_counts().rename("episodios").to_frame().to_markdown(),
        "",
        "### Reparto por nivel de triaje (1 = crítico … 5 = no urgente)", "",
        ep["nivel_triaje"].value_counts(dropna=False).sort_index()
          .rename("episodios").to_frame().to_markdown(),
        "",
        "### Diagnóstico principal por capítulo CIE-10", "",
        ep["dx_capitulo"].value_counts(dropna=False)
          .rename("episodios").to_frame().to_markdown(),
    ]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


# ----------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--origen", default="C:/PAULA/UNI/TFG/Datos_urgencias",
                   help="carpeta con los volcados .sql")
    p.add_argument("--destino", default=str(RAIZ / "datos" / "procesados"),
                   help="carpeta donde guardar los datos limpios")
    args = p.parse_args()
    origen, destino = Path(args.origen), Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)
    informe = {}

    print("1/4 Episodios")
    ep = curar_episodios(leer_anios(origen, "episodios"), informe)
    print("2/4 Codificación")
    cod = curar_codificacion(leer_anios(origen, "codificacion"), ep, informe)
    print("3/4 Diagnóstico principal")
    ep = anadir_diagnostico_principal(ep, cod, informe)

    print("4/4 Guardando")
    ep.to_parquet(destino / "episodios_limpios.parquet", index=False)
    cod.to_parquet(destino / "codificacion_limpia.parquet", index=False)
    (RAIZ / "informes").mkdir(exist_ok=True)
    escribir_informe(ep, cod, informe, RAIZ / "informes" / "fase1_paso1_calidad.md")
    print(f"Listo: {len(ep):,} episodios y {len(cod):,} códigos en {destino}")


if __name__ == "__main__":
    main()
