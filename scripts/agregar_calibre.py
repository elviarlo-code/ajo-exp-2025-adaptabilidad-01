#!/usr/bin/env python3
"""
Pipeline de clasificación de calibre comercial para ajo.

Lee:
  data/raw/biometria_coma.csv
  data/raw/calibre_mercosur_coma.csv

Genera:
  data/processed/biometria_con_calibre.csv

Regla:
- Usa floor(ancho_bulbo_mm) para clasificar por mm entero.
- Si falta dato -> FUERA_RANGO
"""

from pathlib import Path
import pandas as pd
import numpy as np


# =========================
# RUTAS DEL PROYECTO
# =========================

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

BIOMETRIA = RAW / "biometria_coma.csv"
CALIBRES = RAW / "calibre_mercosur_coma.csv"

OUT = PROCESSED / "biometria_con_calibre.csv"


# =========================

def main():

    PROCESSED.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(BIOMETRIA)
    calib = pd.read_csv(CALIBRES).sort_values("valor_menor_mm")

    # convertir ancho a numérico
    ancho = pd.to_numeric(df["ancho_bulbo_mm"], errors="coerce")

    # regla comercial: usar mm entero hacia abajo
    ancho_clasif = np.floor(ancho)

    conditions = []
    choices = []

    for _, r in calib.iterrows():
        lo = float(r["valor_menor_mm"])
        hi = float(r["valor_mayor_mm"])
        conditions.append((ancho_clasif >= lo) & (ancho_clasif <= hi))
        choices.append(str(r["calibre"]))

    df["calibre_com"] = np.select(conditions, choices, default="FUERA_RANGO")

    # guardar valor usado para clasificar (auditoría científica)
    df["ancho_bulbo_mm_clasif"] = ancho_clasif

    df.to_csv(OUT, index=False)

    total = len(df)
    fuera = (df["calibre_com"] == "FUERA_RANGO").sum()

    print("=== CALIBRADO COMPLETADO ===")
    print(f"Archivo generado: {OUT}")
    print(f"Filas totales: {total}")
    print(f"FUERA_RANGO: {fuera}")


if __name__ == "__main__":
    main()
