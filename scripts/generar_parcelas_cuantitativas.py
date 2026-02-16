#!/usr/bin/env python3
"""
Genera dataset a nivel de PARCELA (unidad experimental) para ANOVA y rendimiento.

Entradas:
  data/processed/biometria_con_calibre.csv
  data/raw/diseno_experimental.csv
  data/raw/rend_extra_muestra_coma.csv   <-- peso del resto de la parcela (EXCLUYE las 10 plantas)

Salida:
  data/processed/parcelas_cuantitativas.csv

Notas:
- Parcela = unidad experimental; planta = submuestra (10 plantas).
- DDS (días después de siembra) se integra como dds_cosecha usando MIN(DDS) por parcela,
  para representar precocidad (fecha efectiva de cosecha de la parcela).
- Rendimiento total usa cosecha observada: suma muestra (10) + peso_conto_gr.
- Rendimiento comercial: comercial de muestra + (peso_conto_gr * proporción comercial en peso de la muestra).
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BIO = ROOT / "data" / "processed" / "biometria_con_calibre.csv"
DIS = ROOT / "data" / "raw" / "diseno_experimental.csv"
REND = ROOT / "data" / "raw" / "rend_extra_muestra_coma.csv"
OUTDIR = ROOT / "data" / "processed"
OUT = OUTDIR / "parcelas_cuantitativas.csv"

UMBRAL_CALIBRE_COMERCIAL = 5  # calibre >= 5


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    bio = pd.read_csv(BIO)
    dis = pd.read_csv(DIS)
    rend = pd.read_csv(REND)

    # Validaciones mínimas
    for col in ["parcela", "peso_bulbo_gr", "calibre_com"]:
        if col not in bio.columns:
            raise KeyError(f"Falta columna '{col}' en biometria_con_calibre.csv")

    for col in ["parcela", "bloque", "tratamiento_codigo", "tratamiento_nombre",
                "area_parcela_surco_m2", "plantas_totales_parcela"]:
        if col not in dis.columns:
            raise KeyError(f"Falta columna '{col}' en diseno_experimental.csv")

    for col in ["parcela", "peso_conto_gr"]:
        if col not in rend.columns:
            raise KeyError(f"Falta columna '{col}' en rend_extra_muestra_coma.csv")

    # Normaliza tipos
    bio["parcela"] = to_num(bio["parcela"])
    dis["parcela"] = to_num(dis["parcela"])
    rend["parcela"] = to_num(rend["parcela"])

    peso = to_num(bio["peso_bulbo_gr"])
    calibre = to_num(bio["calibre_com"])
    is_com = (calibre >= UMBRAL_CALIBRE_COMERCIAL).fillna(False)

    # DDS (precocidad): usar MIN por parcela si existe
    dds_min = None
    if "DDS" in bio.columns:
        bio["DDS"] = to_num(bio["DDS"])
        dds_min = bio.groupby("parcela", as_index=False)["DDS"].min().rename(columns={"DDS": "dds_cosecha"})

    # --- Agregación por parcela (muestra de 10 plantas) ---
    aux = pd.DataFrame({
        "parcela": bio["parcela"],
        "peso_muestra_total_g": peso,
        "peso_muestra_com_g": peso.where(is_com, 0.0),
        "n_muestreo": 1,
        "n_com_muestreo": is_com.astype(int)
    })

    # Promedios de variables cuantitativas por parcela
    no_prom = {
        "cultivar", "entrada", "tratamiento", "cod_parcela", "num_planta",
        "calibre_com", "follaje_porte", "forma_longitudinal", "posicion_dientes_extrbulb",
        "forma_base", "distribución_dientes", "dientes_exteriores",
        "tallo_flora_curvatura", "tallo_floral_bulbillo"
    }

    cuant_cols = []
    for c in bio.columns:
        if c in no_prom or c in {"parcela", "DDS"}:
            continue
        s = to_num(bio[c])
        if s.notna().any():
            cuant_cols.append(c)

    cuant_df = bio[["parcela"]].copy()
    for c in cuant_cols:
        cuant_df[c] = to_num(bio[c])

    # Peso promedio por planta (útil como variable cuantitativa adicional)
    cuant_df["peso_bulbo_gr"] = peso

    # Groupby por parcela
    cuant_agg = {c: "mean" for c in cuant_cols}
    cuant_agg.update({"peso_bulbo_gr": "mean"})
    cuant_parcela = cuant_df.groupby("parcela", as_index=False).agg(cuant_agg)

    aux_sum = aux.groupby("parcela", as_index=False).agg({
        "peso_muestra_total_g": "sum",
        "peso_muestra_com_g": "sum",
        "n_muestreo": "sum",
        "n_com_muestreo": "sum"
    })

    # Une promedios + sumas
    base = cuant_parcela.merge(aux_sum, on="parcela", how="left")

    # Une diseño experimental (área, bloque, tratamiento, plantas)
    base = base.merge(
        dis[["parcela", "bloque", "tratamiento_codigo", "tratamiento_nombre",
             "area_parcela_surco_m2", "plantas_totales_parcela"]],
        on="parcela", how="left"
    )

    # Une el peso del resto de la parcela (sin las 10 plantas)
    base = base.merge(rend[["parcela", "peso_conto_gr"]], on="parcela", how="left")

    # Integra DDS (precocidad) si existe
    if dds_min is not None:
        base = base.merge(dds_min, on="parcela", how="left")

    # Validaciones clave
    if base["peso_conto_gr"].isna().any():
        miss = base.loc[base["peso_conto_gr"].isna(), "parcela"].head(10).tolist()
        raise ValueError(f"Hay parcelas sin 'peso_conto_gr' en rend_extra_muestra_coma.csv. Ejemplos: {miss}")

    area = to_num(base["area_parcela_surco_m2"])
    peso_conto = to_num(base["peso_conto_gr"])

    # --- Rendimiento total OBSERVADO ---
    base["peso_parcela_total_g_obs"] = base["peso_muestra_total_g"] + peso_conto
    base["rendimiento_total_tn_ha"] = (base["peso_parcela_total_g_obs"] / area) * 0.01

    # --- Rendimiento comercial (mixto) ---
    base["prop_comercial_peso_muestra"] = np.where(
        base["peso_muestra_total_g"] > 0,
        base["peso_muestra_com_g"] / base["peso_muestra_total_g"],
        np.nan
    )

    base["peso_parcela_comercial_g_est"] = base["peso_muestra_com_g"] + (
        peso_conto * base["prop_comercial_peso_muestra"]
    )
    base["rendimiento_comercial_tn_ha"] = (base["peso_parcela_comercial_g_est"] / area) * 0.01

    # Indicadores adicionales útiles
    base["prop_comercial_n_muestreo"] = base["n_com_muestreo"] / base["n_muestreo"]

    # Orden de columnas
    id_cols = [
        "parcela", "bloque", "tratamiento_codigo", "tratamiento_nombre",
        "area_parcela_surco_m2", "plantas_totales_parcela",
        "dds_cosecha" if "dds_cosecha" in base.columns else None,
        "n_muestreo", "n_com_muestreo", "prop_comercial_n_muestreo",
        "peso_conto_gr", "peso_muestra_total_g", "peso_muestra_com_g",
        "prop_comercial_peso_muestra",
        "peso_parcela_total_g_obs", "peso_parcela_comercial_g_est",
        "rendimiento_total_tn_ha", "rendimiento_comercial_tn_ha",
        "peso_bulbo_gr"
    ]
    id_cols = [c for c in id_cols if c is not None]

    rest = [c for c in base.columns if c not in id_cols]
    base = base[id_cols + rest]

    base.to_csv(OUT, index=False)
    print("=== PARCELAS CUANTITATIVAS GENERADO (DDS INTEGRADO) ===")
    print(f"Salida: {OUT}")
    print(f"Parcelas: {len(base)}")
    print(f"Umbral calibre comercial: >= {UMBRAL_CALIBRE_COMERCIAL}")
    print("Nota: Se asume que 'peso_conto_gr' NO incluye las 10 plantas muestreadas.")


if __name__ == "__main__":
    main()
