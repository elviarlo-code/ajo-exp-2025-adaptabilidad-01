from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols


INPUT_PATH = Path("data/processed/parcelas_cuantitativas_sin_T5.csv")
RESULTS_DIR = Path("results")
DESCRIPTIVOS_PATH = RESULTS_DIR / "descriptivos_por_tratamiento.csv"
ANOVA_PATH = RESULTS_DIR / "anova_resultados.csv"

ID_COLUMNS = {
    "parcela",
    "bloque",
    "tratamiento_codigo",
    "tratamiento_nombre",
}


def identificar_variables_cuantitativas(df: pd.DataFrame) -> list[str]:
    columnas_numericas = df.select_dtypes(include="number").columns
    return [col for col in columnas_numericas if col not in ID_COLUMNS]


def generar_descriptivos(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    descriptivos = (
        df.groupby("tratamiento_nombre", dropna=False)[variables]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
    )

    descriptivos.columns = [
        "tratamiento_nombre"
        if col == "tratamiento_nombre"
        else f"{col[0]}_{col[1]}"
        for col in descriptivos.columns
    ]
    return descriptivos


def ejecutar_anova(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    resultados: list[dict[str, float | str | int]] = []

    for variable in variables:
        datos_variable = df[[variable, "tratamiento_nombre", "bloque"]].dropna()

        if datos_variable.empty:
            continue

        resumen_global = stats.describe(datos_variable[variable])

        modelo = ols(
            f"Q('{variable}') ~ C(tratamiento_nombre) + C(bloque)",
            data=datos_variable,
        ).fit()

        tabla_anova = sm.stats.anova_lm(modelo, typ=2)

        for efecto, fila in tabla_anova.iterrows():
            resultados.append(
                {
                    "variable": variable,
                    "efecto": efecto,
                    "df": fila.get("df"),
                    "sum_sq": fila.get("sum_sq"),
                    "mean_sq": fila.get("sum_sq") / fila.get("df") if fila.get("df") else None,
                    "F": fila.get("F"),
                    "p_valor": fila.get("PR(>F)"),
                    "n_obs_variable": resumen_global.nobs,
                }
            )

    return pd.DataFrame(resultados)


def main() -> None:
    df = pd.read_csv(INPUT_PATH)

    variables_cuantitativas = identificar_variables_cuantitativas(df)
    if not variables_cuantitativas:
        raise ValueError("No se encontraron variables cuantitativas para analizar.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    descriptivos = generar_descriptivos(df, variables_cuantitativas)
    descriptivos.to_csv(DESCRIPTIVOS_PATH, index=False)

    resultados_anova = ejecutar_anova(df, variables_cuantitativas)
    resultados_anova.to_csv(ANOVA_PATH, index=False)

    print(f"Variables analizadas: {len(variables_cuantitativas)}")
    print(f"Descriptivos guardados en: {DESCRIPTIVOS_PATH}")
    print(f"ANOVA guardado en: {ANOVA_PATH}")


if __name__ == "__main__":
    main()
