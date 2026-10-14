# Sensibilidad de los puntajes (informe 4.5): python -m tests.sensibilidad_puntajes

from __future__ import annotations

import csv
import json
from pathlib import Path

from tests import oraculo

CASOS = Path(__file__).parent / "casos" / "casos_prueba.csv"

ALTERNATIVAS = (
    ("20 / 50 / 80", {"si": 20.0, "parcialmente": 50.0, "no": 80.0, "no_se": 80.0}),
    ("10 / 50 / 90", {"si": 10.0, "parcialmente": 50.0, "no": 90.0, "no_se": 90.0}),
    ("25 / 50 / 75", {"si": 25.0, "parcialmente": 50.0, "no": 75.0, "no_se": 75.0}),
    ("0 / 50 / 100", {"si": 0.0, "parcialmente": 50.0, "no": 100.0, "no_se": 100.0}),
    ("«Parcialmente» = 40", {"si": 16.5, "parcialmente": 40.0, "no": 83.5, "no_se": 83.5}),
    ("«Parcialmente» = 60", {"si": 16.5, "parcialmente": 60.0, "no": 83.5, "no_se": 83.5}),
)


def _resultados(puntajes, casos):
    original = dict(oraculo.PUNTAJE)
    oraculo.PUNTAJE.clear()
    oraculo.PUNTAJE.update(puntajes)
    try:
        salida = []
        for fila in casos:
            r = oraculo.esperado(json.loads(fila["respuestas_json"]))
            salida.append((tuple(sorted(r["niveles"].items())), r["global"], tuple(r["priorizadas"])))
        return salida
    finally:
        oraculo.PUNTAJE.clear()
        oraculo.PUNTAJE.update(original)


def main():
    with open(CASOS, encoding="utf-8-sig", newline="") as f:
        casos = list(csv.DictReader(f))
    base = _resultados(dict(oraculo.PUNTAJE), casos)
    print(f"Sensibilidad de los puntajes ({len(casos)} casos; base: "
          f"Sí {oraculo.PUNTAJE['si']} / Parcialmente {oraculo.PUNTAJE['parcialmente']} / "
          f"No {oraculo.PUNTAJE['no']})")
    print(f"{'Puntajes alternativos':<24}{'Nivel de área':>15}{'Riesgo global':>15}{'Lista priorizada':>18}")
    for nombre, puntajes in ALTERNATIVAS:
        alt = _resultados(puntajes, casos)
        niveles = sum(a[0] != b[0] for a, b in zip(base, alt))
        glob = sum(a[1] != b[1] for a, b in zip(base, alt))
        prio = sum(a[2] != b[2] for a, b in zip(base, alt))
        print(f"{nombre:<24}{niveles:>12} de {len(casos)}{glob:>12} de {len(casos)}{prio:>15} de {len(casos)}")


if __name__ == "__main__":
    main()
