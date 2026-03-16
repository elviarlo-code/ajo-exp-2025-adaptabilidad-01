#!/usr/bin/env python3
"""Filtra un CSV eliminando un tratamiento específico.

Uso típico:
    python scripts/limpiar_tratamiento.py \
        --input data/processed/parcelas_cuantitativas.csv \
        --output data/processed/parcelas_cuantitativas_sin_T5.csv \
        --tratamiento T5
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def normalizar_tratamiento(valor: str) -> str:
    valor = valor.strip().upper()
    if not valor:
        return valor
    if valor.startswith("T"):
        return valor
    if valor.isdigit():
        return f"T{valor}"
    return valor


def filtrar_csv(input_path: Path, output_path: Path, tratamiento_objetivo: str) -> tuple[int, int]:
    with input_path.open("r", newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        if reader.fieldnames is None:
            raise ValueError("El archivo de entrada no contiene encabezados.")
        if "tratamiento_codigo" not in reader.fieldnames:
            raise ValueError("No se encontró la columna 'tratamiento_codigo' en el CSV.")

        rows = list(reader)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(rows)
    descartadas = 0

    with output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in rows:
            codigo = normalizar_tratamiento(row.get("tratamiento_codigo", ""))
            if codigo == tratamiento_objetivo:
                descartadas += 1
                continue
            writer.writerow(row)

    return total, descartadas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Elimina filas de un CSV según el tratamiento en la columna tratamiento_codigo."
    )
    parser.add_argument(
        "--input",
        default="data/processed/parcelas_cuantitativas.csv",
        help="Ruta del CSV de entrada.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/parcelas_cuantitativas_sin_T5.csv",
        help="Ruta del CSV de salida.",
    )
    parser.add_argument(
        "--tratamiento",
        default="T5",
        help="Tratamiento a eliminar (acepta formatos como T5 o 5).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {input_path}")

    tratamiento_objetivo = normalizar_tratamiento(args.tratamiento)
    total, descartadas = filtrar_csv(input_path, output_path, tratamiento_objetivo)

    print(f"Archivo de entrada: {input_path}")
    print(f"Archivo de salida: {output_path}")
    print(f"Tratamiento eliminado: {tratamiento_objetivo}")
    print(f"Filas totales: {total}")
    print(f"Filas eliminadas: {descartadas}")
    print(f"Filas finales: {total - descartadas}")


if __name__ == "__main__":
    main()
