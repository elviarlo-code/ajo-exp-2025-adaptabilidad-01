from __future__ import annotations

from pathlib import Path
import string
import unicodedata

import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import MultiComparison


INPUT_PATH = Path("data/processed/parcelas_cuantitativas_sin_T5.csv")
RESULTS_DIR = Path("results")

ANOVA_OUTPUT = RESULTS_DIR / "anova_resumen_general.csv"
TUKEY_OUTPUT = RESULTS_DIR / "tukey_comparaciones_todas.csv"
PAPER_OUTPUT = RESULTS_DIR / "tabla_variables_significativas_tukey_para_paper.csv"
FINAL_OUTPUT = RESULTS_DIR / "tabla_final_medias_sd_letras_tukey.csv"
CSV_ENCODING = "utf-8-sig"

CULTIVAR_ORDER = [
    "AJO CANETANO",
    "AJO CHINO",
    "AJO KIYAN",
    "INIA 104 BLANCO",
    "INIA 105 DONAJUS",
]

ID_COLUMNS = {
    "parcela",
    "bloque",
    "bloue",
    "tratamiento_codigo",
    "tratamiento_nombre",
    "tratamiento",
    "cultivar",
    "cultivares",
}


def normalize_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return "".join(ch.lower() for ch in text if ch.isalnum())


def find_column(columns: list[str], candidates: list[str]) -> str:
    normalized_map = {normalize_name(col): col for col in columns}

    for candidate in candidates:
        key = normalize_name(candidate)
        if key in normalized_map:
            return normalized_map[key]

    for candidate in candidates:
        key = normalize_name(candidate)
        for normalized_col, original_col in normalized_map.items():
            if key in normalized_col or normalized_col in key:
                return original_col

    raise KeyError(f"No se encontró una columna compatible con: {candidates}")


def prepare_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    tratamiento_col = find_column(
        list(df.columns),
        ["tratamiento_nombre", "tratamiento", "cultivar", "cultivares"],
    )
    bloque_col = find_column(list(df.columns), ["bloque", "bloue", "block"])

    df = df.copy()
    df[tratamiento_col] = df[tratamiento_col].astype(str).str.strip()
    df[bloque_col] = df[bloque_col].astype(str).str.strip()

    return df, tratamiento_col, bloque_col


def identify_quantitative_variables(df: pd.DataFrame, tratamiento_col: str, bloque_col: str) -> list[str]:
    excluded = ID_COLUMNS | {tratamiento_col, bloque_col}
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    variables = []

    for col in numeric_columns:
        if col in excluded:
            continue
        if df[col].dropna().nunique() <= 1:
            continue
        variables.append(col)

    return variables


def bron_kerbosch(
    r: set[str],
    p: set[str],
    x: set[str],
    neighbors: dict[str, set[str]],
    cliques: list[set[str]],
) -> None:
    if not p and not x:
        cliques.append(set(r))
        return

    for v in list(p):
        bron_kerbosch(r | {v}, p & neighbors[v], x & neighbors[v], neighbors, cliques)
        p.remove(v)
        x.add(v)


def compact_letter_display(
    treatment_means: pd.Series,
    nonsignificant_pairs: set[frozenset[str]],
) -> dict[str, str]:
    treatments = treatment_means.sort_values(ascending=False).index.tolist()
    neighbors = {t: set() for t in treatments}

    for pair in nonsignificant_pairs:
        a, b = tuple(pair)
        neighbors[a].add(b)
        neighbors[b].add(a)

    cliques: list[set[str]] = []
    bron_kerbosch(set(), set(treatments), set(), neighbors, cliques)
    cliques = [clique for clique in cliques if clique]
    cliques.sort(
        key=lambda clique: (
            -max(treatment_means[t] for t in clique),
            -len(clique),
            ",".join(sorted(clique)),
        )
    )

    labels = {}
    alphabet = list(string.ascii_lowercase)
    for idx, clique in enumerate(cliques):
        if idx < len(alphabet):
            labels[idx] = alphabet[idx]
        else:
            first = alphabet[(idx // len(alphabet)) - 1]
            second = alphabet[idx % len(alphabet)]
            labels[idx] = first + second

    treatment_letters = {t: [] for t in treatments}
    for idx, clique in enumerate(cliques):
        for treatment in treatments:
            if treatment in clique:
                treatment_letters[treatment].append(labels[idx])

    return {treatment: "".join(letters) for treatment, letters in treatment_letters.items()}


def run_anova_and_tukey(
    df: pd.DataFrame,
    tratamiento_col: str,
    bloque_col: str,
    variables: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    anova_rows: list[dict[str, object]] = []
    tukey_rows: list[dict[str, object]] = []
    paper_rows: list[dict[str, object]] = []

    ordered_treatments = [t for t in CULTIVAR_ORDER if t in set(df[tratamiento_col].dropna())]
    remaining_treatments = sorted(set(df[tratamiento_col].dropna()) - set(ordered_treatments))
    treatment_order = ordered_treatments + remaining_treatments

    for variable in variables:
        data = df[[variable, tratamiento_col, bloque_col]].dropna().copy()
        if data.empty or data[variable].nunique() <= 1:
            continue

        model = ols(
            f"Q('{variable}') ~ C(Q('{tratamiento_col}')) + C(Q('{bloque_col}'))",
            data=data,
        ).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)

        treatment_effect = next(
            idx for idx in anova_table.index if "C(Q('" in idx and tratamiento_col in idx
        )
        block_effect = next(idx for idx in anova_table.index if "C(Q('" in idx and bloque_col in idx)

        treatment_p = float(anova_table.loc[treatment_effect, "PR(>F)"])
        block_p = float(anova_table.loc[block_effect, "PR(>F)"])
        treatment_f = float(anova_table.loc[treatment_effect, "F"])
        block_f = float(anova_table.loc[block_effect, "F"])

        summary = (
            data.groupby(tratamiento_col, dropna=False)[variable]
            .agg(["mean", "std", "count"])
            .reindex(treatment_order)
            .reset_index()
        )
        summary["std"] = summary["std"].fillna(0.0)

        anova_rows.append(
            {
                "variable": variable,
                "n_obs": int(len(data)),
                "gl_tratamiento": float(anova_table.loc[treatment_effect, "df"]),
                "F_tratamiento": treatment_f,
                "p_tratamiento": treatment_p,
                "significativo_tratamiento_p_lt_0_05": treatment_p < 0.05,
                "gl_bloque": float(anova_table.loc[block_effect, "df"]),
                "F_bloque": block_f,
                "p_bloque": block_p,
                "significativo_bloque_p_lt_0_05": block_p < 0.05,
            }
        )

        letters = {t: "" for t in summary[tratamiento_col].dropna().tolist()}

        if treatment_p < 0.05:
            mc = MultiComparison(data[variable], data[tratamiento_col])
            tukey = mc.tukeyhsd(alpha=0.05)
            tukey_table = pd.DataFrame(
                tukey._results_table.data[1:],
                columns=tukey._results_table.data[0],
            )

            nonsignificant_pairs: set[frozenset[str]] = set()
            for _, row in tukey_table.iterrows():
                group1 = str(row["group1"])
                group2 = str(row["group2"])
                reject = bool(row["reject"])
                pair = frozenset({group1, group2})
                if not reject:
                    nonsignificant_pairs.add(pair)

                tukey_rows.append(
                    {
                        "variable": variable,
                        "group1": group1,
                        "group2": group2,
                        "meandiff": float(row["meandiff"]),
                        "p_adj": float(row["p-adj"]),
                        "lower": float(row["lower"]),
                        "upper": float(row["upper"]),
                        "reject": reject,
                    }
                )

            means = summary.set_index(tratamiento_col)["mean"]
            letters = compact_letter_display(means, nonsignificant_pairs)

        for _, row in summary.iterrows():
            treatment = row[tratamiento_col]
            mean_value = float(row["mean"])
            sd_value = float(row["std"])
            letter_value = letters.get(treatment, "")
            paper_rows.append(
                {
                    "variable": variable,
                    "tratamiento_nombre": treatment,
                    "media": mean_value,
                    "desviacion_estandar": sd_value,
                    "n": int(row["count"]),
                    "letras_tukey": letter_value,
                    "media_sd_letras": f"{mean_value:.2f} \u00B1 {sd_value:.2f} {letter_value}".strip(),
                }
            )

    anova_df = pd.DataFrame(anova_rows).sort_values(["significativo_tratamiento_p_lt_0_05", "p_tratamiento"], ascending=[False, True])
    tukey_df = pd.DataFrame(tukey_rows)
    paper_df = pd.DataFrame(paper_rows)

    return anova_df, tukey_df, paper_df


def build_final_table(anova_df: pd.DataFrame, paper_df: pd.DataFrame) -> pd.DataFrame:
    significant_vars = anova_df.loc[
        anova_df["significativo_tratamiento_p_lt_0_05"], "variable"
    ].tolist()

    paper_significant = paper_df[paper_df["variable"].isin(significant_vars)].copy()
    if paper_significant.empty:
        return pd.DataFrame(columns=["variable"] + CULTIVAR_ORDER)

    final_table = (
        paper_significant.pivot(
            index="variable",
            columns="tratamiento_nombre",
            values="media_sd_letras",
        )
        .reindex(columns=CULTIVAR_ORDER)
        .reset_index()
    )
    return final_table


def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    df, tratamiento_col, bloque_col = prepare_dataframe(df)
    variables = identify_quantitative_variables(df, tratamiento_col, bloque_col)

    if not variables:
        raise ValueError("No se identificaron variables cuantitativas analizables.")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    anova_df, tukey_df, paper_df = run_anova_and_tukey(df, tratamiento_col, bloque_col, variables)

    paper_significant = paper_df[
        paper_df["variable"].isin(
            anova_df.loc[anova_df["significativo_tratamiento_p_lt_0_05"], "variable"]
        )
    ].copy()

    final_table = build_final_table(anova_df, paper_df)

    anova_df.to_csv(ANOVA_OUTPUT, index=False, encoding=CSV_ENCODING)
    tukey_df.to_csv(TUKEY_OUTPUT, index=False, encoding=CSV_ENCODING)
    paper_significant.to_csv(PAPER_OUTPUT, index=False, encoding=CSV_ENCODING)
    final_table.to_csv(FINAL_OUTPUT, index=False, encoding=CSV_ENCODING)

    print(f"Columna de tratamiento usada: {tratamiento_col}")
    print(f"Columna de bloque usada: {bloque_col}")
    print(f"Variables analizadas: {len(variables)}")
    print(f"Variables significativas (tratamiento): {int(anova_df['significativo_tratamiento_p_lt_0_05'].sum())}")
    print(f"ANOVA: {ANOVA_OUTPUT}")
    print(f"Tukey: {TUKEY_OUTPUT}")
    print(f"Tabla paper: {PAPER_OUTPUT}")
    print(f"Tabla final: {FINAL_OUTPUT}")


if __name__ == "__main__":
    main()
