from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

INPUT_PATH = Path("data/processed/parcelas_cuantitativas_sin_T5.csv")
RESULTS_DIR = Path("results")
FIGURES_DIR = Path("figures")

ID_COLUMNS = {
    "parcela",
    "bloque",
    "tratamiento_codigo",
    "tratamiento_nombre",
}


def cargar_datos(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("El archivo de entrada no contiene registros.")

    if "tratamiento_nombre" not in df.columns:
        raise ValueError("La columna 'tratamiento_nombre' es obligatoria para este análisis.")

    return df


def seleccionar_variables_pca(df: pd.DataFrame) -> tuple[list[str], dict[str, list[str]]]:
    excluidas = {
        "identificacion": [],
        "vacias": [],
        "sin_varianza": [],
        "no_numericas": [],
    }

    candidatas = [col for col in df.columns if col not in ID_COLUMNS]
    excluidas["identificacion"] = [col for col in df.columns if col in ID_COLUMNS]

    variables_finales: list[str] = []

    for col in candidatas:
        serie = pd.to_numeric(df[col], errors="coerce")

        if serie.isna().all():
            excluidas["vacias"].append(col)
            continue

        no_na = serie.dropna()
        if no_na.empty:
            excluidas["no_numericas"].append(col)
            continue

        if np.isclose(no_na.var(ddof=0), 0.0):
            excluidas["sin_varianza"].append(col)
            continue

        variables_finales.append(col)

    if not variables_finales:
        raise ValueError("No quedaron variables útiles para PCA tras el filtrado.")

    return variables_finales, excluidas


def agregar_por_cultivar(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    base = df[["tratamiento_nombre", *variables]].copy()
    for col in variables:
        base[col] = pd.to_numeric(base[col], errors="coerce")

    matriz = base.groupby("tratamiento_nombre", dropna=False, as_index=False)[variables].mean()
    matriz = matriz.dropna(axis=1, how="all")

    var_cols = [c for c in matriz.columns if c != "tratamiento_nombre"]
    var_cols_validas = [
        c for c in var_cols if not np.isclose(matriz[c].dropna().var(ddof=0), 0.0)
    ]

    if not var_cols_validas:
        raise ValueError("No hay variables con variación entre cultivares para ejecutar PCA.")

    matriz = matriz[["tratamiento_nombre", *var_cols_validas]]
    return matriz


def ejecutar_pca(matriz_cultivares: pd.DataFrame) -> dict[str, pd.DataFrame | PCA]:
    variables = [c for c in matriz_cultivares.columns if c != "tratamiento_nombre"]
    X = matriz_cultivares[variables].copy()

    if X.isna().any().any():
        X = X.fillna(X.mean())

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_componentes = min(2, X_scaled.shape[0], X_scaled.shape[1])
    if n_componentes < 2:
        raise ValueError(
            "No fue posible calcular dos componentes principales. "
            "Se requieren al menos 2 cultivares y 2 variables con variación."
        )

    pca = PCA(n_components=n_componentes)
    scores = pca.fit_transform(X_scaled)

    varianza = pd.DataFrame(
        {
            "componente": [f"PC{i + 1}" for i in range(n_componentes)],
            "varianza_explicada": pca.explained_variance_ratio_,
            "varianza_explicada_pct": pca.explained_variance_ratio_ * 100,
            "varianza_acumulada_pct": np.cumsum(pca.explained_variance_ratio_) * 100,
        }
    )

    coordenadas = pd.DataFrame(scores, columns=[f"PC{i + 1}" for i in range(n_componentes)])
    coordenadas.insert(0, "tratamiento_nombre", matriz_cultivares["tratamiento_nombre"].values)

    cargas = pd.DataFrame(
        pca.components_.T,
        index=variables,
        columns=[f"PC{i + 1}" for i in range(n_componentes)],
    ).reset_index(names="variable")

    contribucion = cargas.copy()
    for pc in [f"PC{i + 1}" for i in range(n_componentes)]:
        contribucion[f"contrib_{pc}_pct"] = (
            (contribucion[pc] ** 2) / (contribucion[pc] ** 2).sum()
        ) * 100

    return {
        "pca": pca,
        "varianza": varianza,
        "coordenadas": coordenadas,
        "cargas": cargas,
        "contribucion": contribucion,
        "variables": pd.DataFrame({"variable": variables}),
    }


def guardar_resultados(resultados: dict[str, pd.DataFrame | PCA], matriz_cultivares: pd.DataFrame) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    resultados["varianza"].to_csv(RESULTS_DIR / "pca_varianza_explicada.csv", index=False)
    resultados["coordenadas"].to_csv(RESULTS_DIR / "pca_coordenadas_cultivares.csv", index=False)
    resultados["cargas"].to_csv(RESULTS_DIR / "pca_cargas_variables.csv", index=False)
    resultados["contribucion"].to_csv(
        RESULTS_DIR / "pca_contribucion_variables.csv", index=False
    )
    matriz_cultivares.to_csv(RESULTS_DIR / "pca_matriz_base_cultivares.csv", index=False)


def _configurar_ejes(varianza: pd.DataFrame) -> tuple[str, str]:
    x_lab = f"PC1 ({varianza.loc[0, 'varianza_explicada_pct']:.2f}%)"
    y_lab = f"PC2 ({varianza.loc[1, 'varianza_explicada_pct']:.2f}%)"
    return x_lab, y_lab


def graficar_scatter(coordenadas: pd.DataFrame, varianza: pd.DataFrame) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(coordenadas["PC1"], coordenadas["PC2"], s=90, alpha=0.85)

    for _, fila in coordenadas.iterrows():
        ax.annotate(
            fila["tratamiento_nombre"],
            (fila["PC1"], fila["PC2"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
        )

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    x_lab, y_lab = _configurar_ejes(varianza)
    ax.set_xlabel(x_lab)
    ax.set_ylabel(y_lab)
    ax.set_title("PCA de cultivares de ajo (medias por cultivar)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pca_scatter_cultivares.png", dpi=300)
    plt.close(fig)


def graficar_biplot(
    coordenadas: pd.DataFrame,
    cargas: pd.DataFrame,
    contribucion: pd.DataFrame,
    varianza: pd.DataFrame,
    top_n: int = 8,
) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.scatter(coordenadas["PC1"], coordenadas["PC2"], s=80, alpha=0.75, label="Cultivares")

    for _, fila in coordenadas.iterrows():
        ax.annotate(
            fila["tratamiento_nombre"],
            (fila["PC1"], fila["PC2"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=9,
        )

    escala = 0.85 * max(
        coordenadas["PC1"].abs().max(),
        coordenadas["PC2"].abs().max(),
    )

    top_variables = contribucion.assign(
        prioridad=lambda d: d["contrib_PC1_pct"] + d["contrib_PC2_pct"]
    ).nlargest(top_n, "prioridad")

    cargas_map = cargas.set_index("variable")

    for _, fila in top_variables.iterrows():
        var = fila["variable"]
        x = cargas_map.loc[var, "PC1"] * escala
        y = cargas_map.loc[var, "PC2"] * escala
        ax.arrow(0, 0, x, y, color="crimson", alpha=0.7, head_width=0.04 * escala)
        ax.text(x * 1.08, y * 1.08, var, color="crimson", fontsize=9)

    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    x_lab, y_lab = _configurar_ejes(varianza)
    ax.set_xlabel(x_lab)
    ax.set_ylabel(y_lab)
    ax.set_title("Biplot PCA de cultivares y variables")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "pca_biplot_cultivares.png", dpi=300)
    plt.close(fig)


def _top_variables(cargas: pd.DataFrame, pc: str, n: int = 5) -> pd.DataFrame:
    return cargas.assign(abs_carga=lambda d: d[pc].abs()).nlargest(n, "abs_carga")


def exportar_resumen(varianza: pd.DataFrame, cargas: pd.DataFrame) -> Path:
    top_pc1 = _top_variables(cargas, "PC1", n=5)
    top_pc2 = _top_variables(cargas, "PC2", n=5)

    def formatear_top(df_top: pd.DataFrame, pc: str) -> str:
        return ", ".join(
            [f"{fila['variable']} ({fila[pc]:+.3f})" for _, fila in df_top.iterrows()]
        )

    texto = [
        "Resumen automático del PCA (medias por cultivar)",
        "=" * 58,
        f"Varianza explicada por PC1: {varianza.loc[0, 'varianza_explicada_pct']:.2f}%",
        f"Varianza explicada por PC2: {varianza.loc[1, 'varianza_explicada_pct']:.2f}%",
        "",
        f"Variables con mayor contribución (|carga|) en PC1: {formatear_top(top_pc1, 'PC1')}",
        f"Variables con mayor contribución (|carga|) en PC2: {formatear_top(top_pc2, 'PC2')}",
        "",
        "Interpretación agronómica sugerida:",
        (
            "- PC1 resume un gradiente multivariado dominado por las variables con mayores "
            "cargas absolutas en dicho componente, útil para diferenciar cultivares según "
            "rasgos de crecimiento/rendimiento asociados a esas variables."
        ),
        (
            "- PC2 captura un patrón complementario e independiente de PC1, destacando "
            "la variación en los rasgos con mayor peso en este eje; esto ayuda a distinguir "
            "cultivares con perfiles agronómicos contrastantes."
        ),
        "",
        "Nota: el signo (+/-) de la carga indica dirección de asociación dentro de cada componente.",
    ]

    salida = RESULTS_DIR / "pca_resumen.txt"
    salida.write_text("\n".join(texto), encoding="utf-8")
    return salida


def main() -> None:
    print("[INFO] Iniciando análisis multivariado (PCA) de cultivares de ajo...")

    df = cargar_datos(INPUT_PATH)
    variables_pca, excluidas = seleccionar_variables_pca(df)
    matriz_cultivares = agregar_por_cultivar(df, variables_pca)

    print(f"[INFO] Variables candidatas al PCA: {len(variables_pca)}")
    print(
        "[INFO] Variables excluidas -> "
        f"vacías: {len(excluidas['vacias'])}, "
        f"sin varianza: {len(excluidas['sin_varianza'])}, "
        f"no numéricas: {len(excluidas['no_numericas'])}."
    )

    variables_finales = [c for c in matriz_cultivares.columns if c != "tratamiento_nombre"]
    print(f"[INFO] Variables que entraron al PCA: {variables_finales}")
    print(f"[INFO] Número de cultivares analizados: {matriz_cultivares.shape[0]}")

    resultados = ejecutar_pca(matriz_cultivares)
    guardar_resultados(resultados, matriz_cultivares)
    graficar_scatter(resultados["coordenadas"], resultados["varianza"])
    graficar_biplot(
        resultados["coordenadas"],
        resultados["cargas"],
        resultados["contribucion"],
        resultados["varianza"],
    )
    resumen_path = exportar_resumen(resultados["varianza"], resultados["cargas"])

    print(f"[INFO] Resultados guardados en: {RESULTS_DIR.resolve()}")
    print(f"[INFO] Figuras guardadas en: {FIGURES_DIR.resolve()}")
    print(f"[INFO] Resumen automático guardado en: {resumen_path.resolve()}")


if __name__ == "__main__":
    main()
