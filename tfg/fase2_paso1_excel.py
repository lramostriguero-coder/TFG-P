"""
FASE 2 · PASO 1 — Excel de los baselines con las fórmulas visibles.

Genera `baselines_fase2.xlsx` (en la carpeta de los datos, porque contiene las
llegadas diarias). Todo lo calcula Excel con fórmulas, para poder revisarlo a mano:

    Leyenda        qué hay en cada hoja
    Total          llegadas totales, las 8 predicciones (persistencia h=1..7 y naïve
                   semanal), su error, |error|, error² y |error|/real
    Areas          naïve semanal para PED, GIN y GEN con las mismas columnas
    Metricas       MAE, RMSE, MAPE en validación + intervalo del 90 % (P5 y P95 del
                   error en entrenamiento), cobertura y anchura

Días en blanco: si el real o la entrada están vacíos, la fila queda vacía y
AVERAGEIFS / PERCENTILE no la cuentan (Excel no la toma como 0).

Uso:
    python tfg/fase2_paso1_excel.py --destino "C:/PAULA/UNI/TFG/Datos_urgencias/FASE2"
"""
import argparse
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter as L

RAIZ = Path(__file__).resolve().parents[1]
SERIE = RAIZ / "datos" / "procesados" / "serie_diaria.csv"
NEGRITA = Font(bold=True)
CABECERA = PatternFill("solid", fgColor="DDEBF7")
N = 5  # columnas por predicción: pred, error, |error|, error², |error|/real


def bloque(ws, fila_cab, col0, nombre, col_real, desfase, n_filas):
    """Escribe las 5 columnas de una predicción ŷ(r) = real(r − desfase)."""
    c = [L(col0 + i) for i in range(N)]
    for i, t in enumerate(["pred", "error", "|error|", "error²", "|error|/real"]):
        ws.cell(fila_cab, col0 + i, f"{nombre} · {t}")
    for r in range(fila_cab + 1, fila_cab + 1 + n_filas):
        if r - desfase <= fila_cab:
            continue
        ws[f"{c[0]}{r}"] = f'=IF({col_real}{r - desfase}="","",{col_real}{r - desfase})'
        ws[f"{c[1]}{r}"] = f'=IF(OR({col_real}{r}="",{c[0]}{r}=""),"",{col_real}{r}-{c[0]}{r})'
        ws[f"{c[2]}{r}"] = f'=IF({c[1]}{r}="","",ABS({c[1]}{r}))'
        ws[f"{c[3]}{r}"] = f'=IF({c[1]}{r}="","",{c[1]}{r}^2)'
        ws[f"{c[4]}{r}"] = f'=IF({c[1]}{r}="","",{c[2]}{r}/{col_real}{r})'
    return c


def main(destino: Path) -> None:
    s = pd.read_csv(SERIE, parse_dates=["fecha"])
    n = len(s)
    ult = n + 1
    ent = s.index[s["particion"] == "entrenamiento"]
    ent_ini, ent_fin = ent.min() + 2, ent.max() + 2   # filas de Excel (cabecera en 1)

    wb = Workbook()
    ley = wb.active
    ley.title = "Leyenda"
    for fila in [
        ["Fase 2 · Paso 1 — Baselines (experimento 1)"],
        [],
        ["Persistencia h", "ŷ(t+h) = y(t): la predicción del día de la fila es la llegada de h filas más arriba"],
        ["Naïve semanal", "ŷ(t+h) = y(t+h−7): la llegada de 7 filas más arriba (igual para h = 1…7)"],
        ["error", "real − predicción"],
        ["MAE", "media de |error| en validación (pacientes/día)"],
        ["RMSE", "raíz de la media de error² en validación"],
        ["MAPE", "media de |error|/real en validación"],
        ["Intervalo 90 %", "[pred + P5 ; pred + P95], P5 y P95 = percentiles del error en ENTRENAMIENTO "
                           f"(filas {ent_ini}–{ent_fin} de las hojas Total y Areas)"],
        ["Cobertura", "% de días de validación con el real dentro del intervalo (ideal ≈ 90 %)"],
        ["Días en blanco", "14/04/2023, 16/06/2023, 24/05/2024 y 30/06/2026: sin dato, no se puntúan"],
    ]:
        ley.append(fila)
    ley["A1"].font = NEGRITA
    ley.column_dimensions["A"].width = 18
    ley.column_dimensions["B"].width = 110

    def hoja_base(nombre, columnas):
        ws = wb.create_sheet(nombre)
        ws.append(["fecha", "particion"] + columnas)
        for _, f in s.iterrows():
            ws.append([f["fecha"].date(), f["particion"]] +
                      [None if pd.isna(f[c]) else int(f[c]) for c in columnas])
        for r in range(2, ult + 1):
            ws[f"A{r}"].number_format = "dd/mm/yyyy"
        ws.freeze_panes = "C2"
        return ws

    # --- Total ---
    tot = hoja_base("Total", ["llegadas"])
    metodos = {}
    col = 4
    for h in range(1, 8):
        metodos[f"Persistencia h={h}"] = ("Total", bloque(tot, 1, col, f"Pers h={h}", "C", h, n))
        col += N
    metodos["Naïve semanal (h=1…7)"] = ("Total", bloque(tot, 1, col, "Naïve sem", "C", 7, n))

    # --- Áreas ---
    ar = hoja_base("Areas", ["llegadas_PED", "llegadas_GIN", "llegadas_GEN"])
    col = 6
    for area, cr in [("PED", "C"), ("GIN", "D"), ("GEN", "E")]:
        metodos[f"Naïve semanal {area}"] = ("Areas", bloque(ar, 1, col, f"Naïve {area}", cr, 7, n))
        col += N

    for ws in (tot, ar):
        for c in range(1, ws.max_column + 1):
            ws.cell(1, c).font = NEGRITA
            ws.cell(1, c).fill = CABECERA
            ws.column_dimensions[L(c)].width = 13

    # --- Métricas ---
    m = wb.create_sheet("Metricas")
    cab = ["Predicción", "Días puntuados", "MAE", "RMSE", "MAPE", "P5 error (entr.)",
           "P95 error (entr.)", "Anchura intervalo", "Cobertura 90 %"]
    m.append(cab)
    for i, (nombre, (hoja, c)) in enumerate(metodos.items(), start=2):
        part = f"{hoja}!$B$2:$B${ult}"
        rng = lambda k: f"{hoja}!${c[k]}$2:${c[k]}${ult}"
        val = f'{part},"validacion"'
        m.append([
            nombre,
            f'=COUNTIFS({val},{rng(1)},">=-1E9")',
            f'=AVERAGEIFS({rng(2)},{val})',
            f'=SQRT(AVERAGEIFS({rng(3)},{val}))',
            f'=AVERAGEIFS({rng(4)},{val})',
            f'=PERCENTILE({hoja}!{c[1]}{ent_ini}:{c[1]}{ent_fin},0.05)',
            f'=PERCENTILE({hoja}!{c[1]}{ent_ini}:{c[1]}{ent_fin},0.95)',
            f"=G{i}-F{i}",
            f'=COUNTIFS({val},{rng(1)},">="&F{i},{rng(1)},"<="&G{i})/B{i}',
        ])
        for k, fmt in zip("CDEFGH", ["0.00"] * 6):
            m[f"{k}{i}"].number_format = fmt
        m[f"E{i}"].number_format = "0.00%"
        m[f"I{i}"].number_format = "0.0%"
    for c in range(1, len(cab) + 1):
        m.cell(1, c).font = NEGRITA
        m.cell(1, c).fill = CABECERA
        m.column_dimensions[L(c)].width = 17
    m.column_dimensions["A"].width = 24
    wb.move_sheet("Metricas", offset=-2)

    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / "baselines_fase2.xlsx"
    wb.save(salida)
    print(f"Guardado: {salida}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", default="C:/PAULA/UNI/TFG/Datos_urgencias/FASE2")
    main(Path(ap.parse_args().destino))
