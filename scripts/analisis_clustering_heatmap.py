from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, fcluster, leaves_list, linkage
from scipy.spatial.distance import pdist, squareform

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

    required_cols = {"tratamiento_nombre", "bloque"}
    faltantes = required_cols - set(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el dataset: {sorted(faltantes)}")

    return df


def seleccionar_variables_cuantitativas(
    df: pd.DataFrame,
) -> tuple[list[str], dict[str, list[str]]]:
    excluidas = {
        "identificacion": [col for col in df.columns if col in ID_COLUMNS],
        "vacias": [],
        "sin_varianza": [],
        "no_numericas": [],
    }

    candidatas = [col for col in df.columns if col not in ID_COLUMNS]
    variables_finales: list[str] = []

    for col in candidatas:
        serie = pd.to_numeric(df[col], errors="coerce")

        if serie.isna().all():
            excluidas["vacias"].append(col)
            continue

        if serie.dropna().empty:
            excluidas["no_numericas"].append(col)
            continue

        if np.isclose(serie.dropna().var(ddof=0), 0.0):
            excluidas["sin_varianza"].append(col)
            continue

        variables_finales.append(col)

    if not variables_finales:
        raise ValueError("No quedaron variables cuantitativas útiles para el análisis de clustering.")

    return variables_finales, excluidas


def agregar_por_cultivar(df: pd.DataFrame, variables: list[str]) -> pd.DataFrame:
    base = df[["tratamiento_nombre", *variables]].copy()

    for col in variables:
        base[col] = pd.to_numeric(base[col], errors="coerce")

    matriz = base.groupby("tratamiento_nombre", as_index=False, dropna=False)[variables].mean()
    matriz = matriz.dropna(axis=1, how="all")

    var_cols = [c for c in matriz.columns if c != "tratamiento_nombre"]
    var_validas = [c for c in var_cols if not np.isclose(matriz[c].dropna().var(ddof=0), 0.0)]

    if not var_validas:
        raise ValueError("No hay variación entre cultivares tras promediar variables.")

    return matriz[["tratamiento_nombre", *var_validas]]


def estandarizar_matriz(matriz_cultivares: pd.DataFrame) -> pd.DataFrame:
    variables = [c for c in matriz_cultivares.columns if c != "tratamiento_nombre"]
    X = matriz_cultivares[variables].copy()

    if X.isna().any().any():
        X = X.fillna(X.mean())

    medias = X.mean(axis=0)
    desv = X.std(axis=0, ddof=0).replace(0, np.nan)
    X_std = (X - medias) / desv

    if X_std.isna().any().any():
        X_std = X_std.fillna(0.0)

    X_std.insert(0, "tratamiento_nombre", matriz_cultivares["tratamiento_nombre"].values)
    return X_std


def clustering_jerarquico(matriz_std: pd.DataFrame) -> dict[str, object]:
    variables = [c for c in matriz_std.columns if c != "tratamiento_nombre"]
    X = matriz_std[variables].to_numpy()

    if X.shape[0] < 2:
        raise ValueError("Se requieren al menos 2 cultivares para clustering jerárquico.")

    Z = linkage(X, method="ward", metric="euclidean")

    dist_condensada = pdist(X, metric="euclidean")
    dist_matrix = squareform(dist_condensada)

    cultivares = matriz_std["tratamiento_nombre"].tolist()
    dist_df = pd.DataFrame(dist_matrix, index=cultivares, columns=cultivares)

    orden_indices = leaves_list(Z)
    orden_cultivares = [cultivares[idx] for idx in orden_indices]

    grupos = {}
    for k in [2, 3, 4]:
        if len(cultivares) >= k:
            etiquetas = fcluster(Z, t=k, criterion="maxclust")
            grupos[k] = pd.DataFrame(
                {
                    "tratamiento_nombre": cultivares,
                    "grupo": etiquetas,
                }
            ).sort_values(["grupo", "tratamiento_nombre"]).reset_index(drop=True)

    return {
        "linkage": Z,
        "distancias": dist_df,
        "orden_cultivares": orden_cultivares,
        "grupos": grupos,
    }


def _pares_mas_cercanos(distancias: pd.DataFrame, n: int = 3) -> list[tuple[str, str, float]]:
    pares: list[tuple[str, str, float]] = []
    cultivares = distancias.index.tolist()

    for i in range(len(cultivares)):
        for j in range(i + 1, len(cultivares)):
            a = cultivares[i]
            b = cultivares[j]
            pares.append((a, b, float(distancias.loc[a, b])))

    return sorted(pares, key=lambda x: x[2])[:n]


def _descripcion_grupos(
    grupos_df: pd.DataFrame,
    matriz_std: pd.DataFrame,
    umbral: float = 0.5,
) -> list[str]:
    descripciones: list[str] = []
    if grupos_df.empty:
        return descripciones

    indexada = matriz_std.set_index("tratamiento_nombre")
    variables = indexada.columns.tolist()

    for grupo in sorted(grupos_df["grupo"].unique()):
        miembros = grupos_df.loc[grupos_df["grupo"] == grupo, "tratamiento_nombre"].tolist()
        sub = indexada.loc[miembros, variables]
        perfil = sub.mean(axis=0)

        altas = perfil[perfil >= umbral].sort_values(ascending=False).index.tolist()
        bajas = perfil[perfil <= -umbral].sort_values(ascending=True).index.tolist()

        altas_txt = ", ".join(altas[:5]) if altas else "sin variables marcadamente altas"
        bajas_txt = ", ".join(bajas[:5]) if bajas else "sin variables marcadamente bajas"

        descripciones.append(
            f"- Grupo {grupo} ({len(miembros)} cultivares: {', '.join(miembros)}): "
            f"altas -> {altas_txt}; bajas -> {bajas_txt}."
        )

    return descripciones


def exportar_resultados(
    matriz_base: pd.DataFrame,
    matriz_std: pd.DataFrame,
    clustering: dict[str, object],
) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    matriz_base.to_csv(RESULTS_DIR / "clustering_matriz_base_cultivares.csv", index=False)
    matriz_std.to_csv(RESULTS_DIR / "clustering_matriz_estandarizada.csv", index=False)

    orden_df = pd.DataFrame(
        {
            "orden": np.arange(1, len(clustering["orden_cultivares"]) + 1),
            "tratamiento_nombre": clustering["orden_cultivares"],
        }
    )
    orden_df.to_csv(RESULTS_DIR / "clustering_orden_cultivares.csv", index=False)

    clustering["distancias"].to_csv(RESULTS_DIR / "clustering_distancias.csv", index=True)

    for k, grupos_df in clustering["grupos"].items():
        grupos_df.to_csv(RESULTS_DIR / f"clustering_grupos_k{k}.csv", index=False)

    pares = _pares_mas_cercanos(clustering["distancias"], n=3)
    pares_txt = "\n".join(
        [f"  - {a} ↔ {b}: distancia euclidiana = {d:.3f}" for a, b, d in pares]
    )

    lineas = [
        "Resumen automático de clustering jerárquico (medias por cultivar)",
        "=" * 66,
        f"Número de cultivares analizados: {matriz_base['tratamiento_nombre'].nunique()}",
        "Variables incluidas en el análisis:",
        "  - " + "\n  - ".join([c for c in matriz_base.columns if c != "tratamiento_nombre"]),
        "",
        "Métrica de distancia: euclidiana",
        "Método de enlace: Ward",
        "",
        "Orden final de agrupamiento de cultivares:",
        "  - " + "\n  - ".join(clustering["orden_cultivares"]),
        "",
        "Cultivares más cercanos entre sí (menor distancia):",
        pares_txt if pares_txt else "  - No disponible",
        "",
        "Descripción automática de perfiles por grupo (matriz estandarizada):",
    ]

    if clustering["grupos"]:
        for k in sorted(clustering["grupos"].keys()):
            lineas.append(f"\nCorte en k={k} grupos:")
            lineas.extend(_descripcion_grupos(clustering["grupos"][k], matriz_std))
    else:
        lineas.append("No se pudieron generar cortes de grupos (insuficientes cultivares).")

    salida = RESULTS_DIR / "clustering_resumen.txt"
    salida.write_text("\n".join(lineas), encoding="utf-8")
    return salida


def generar_figuras(matriz_std: pd.DataFrame, linkage_matrix: np.ndarray) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    cultivares = matriz_std["tratamiento_nombre"].tolist()
    variables = [c for c in matriz_std.columns if c != "tratamiento_nombre"]
    X = matriz_std.set_index("tratamiento_nombre")[variables]

    fig, ax = plt.subplots(figsize=(11, 7))
    dendrogram(
        linkage_matrix,
        labels=cultivares,
        leaf_rotation=45,
        leaf_font_size=10,
        ax=ax,
    )
    ax.set_title("Dendrograma jerárquico de cultivares de ajo")
    ax.set_xlabel("Cultivares")
    ax.set_ylabel("Distancia (Ward)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "dendrograma_cultivares.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(
        X,
        cmap="vlag",
        center=0,
        linewidths=0.4,
        linecolor="white",
        cbar_kws={"label": "Valor estandarizado (z-score)"},
        ax=ax,
    )
    ax.set_title("Heatmap de perfiles agronómicos estandarizados por cultivar")
    ax.set_xlabel("Variables agronómicas")
    ax.set_ylabel("Cultivares")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "heatmap_cultivares.png", dpi=300)
    plt.close(fig)

    cluster_grid = sns.clustermap(
        X,
        method="ward",
        metric="euclidean",
        cmap="vlag",
        center=0,
        linewidths=0.3,
        figsize=(12, 9),
        cbar_kws={"label": "Valor estandarizado (z-score)"},
    )
    cluster_grid.ax_heatmap.set_title("Clustermap de cultivares y variables agronómicas", pad=18)
    cluster_grid.ax_heatmap.set_xlabel("Variables agronómicas")
    cluster_grid.ax_heatmap.set_ylabel("Cultivares")
    plt.setp(cluster_grid.ax_heatmap.get_xticklabels(), rotation=45, ha="right")
    cluster_grid.savefig(FIGURES_DIR / "clustermap_cultivares.png", dpi=300)
    plt.close(cluster_grid.fig)


def main() -> None:
    print("[INFO] Iniciando clustering jerárquico + heatmap por cultivar...")

    df = cargar_datos(INPUT_PATH)
    variables, excluidas = seleccionar_variables_cuantitativas(df)
    matriz_base = agregar_por_cultivar(df, variables)
    matriz_std = estandarizar_matriz(matriz_base)
    clustering = clustering_jerarquico(matriz_std)

    variables_finales = [c for c in matriz_base.columns if c != "tratamiento_nombre"]

    print(f"[INFO] Variables candidatas: {len(variables)}")
    print(
        "[INFO] Variables excluidas -> "
        f"vacías: {len(excluidas['vacias'])}, "
        f"sin varianza: {len(excluidas['sin_varianza'])}, "
        f"no numéricas: {len(excluidas['no_numericas'])}."
    )
    print(f"[INFO] Variables que entraron al análisis: {variables_finales}")
    print(f"[INFO] Número de cultivares analizados: {matriz_base.shape[0]}")

    resumen_path = exportar_resultados(matriz_base, matriz_std, clustering)
    generar_figuras(matriz_std, clustering["linkage"])

    print(f"[INFO] Resultados guardados en: {RESULTS_DIR.resolve()}")
    print(f"[INFO] Figuras guardadas en: {FIGURES_DIR.resolve()}")
    print(f"[INFO] Resumen guardado en: {resumen_path.resolve()}")


if __name__ == "__main__":
    main()
