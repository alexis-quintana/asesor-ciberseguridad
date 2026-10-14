# Llena la columna casos_prueba de la matriz: python -m tests.trazabilidad_casos

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.validacion import cargar_casos, ejecutar

MATRIZ = Path(__file__).resolve().parent.parent / "docs" / "matriz_trazabilidad.csv"


def _abreviar(ids):
    numeros = sorted(int(i[1:]) for i in ids)
    tramos, inicio, previo = [], None, None
    for n in numeros:
        if inicio is None:
            inicio = previo = n
        elif n == previo + 1:
            previo = n
        else:
            tramos.append((inicio, previo))
            inicio = previo = n
    if inicio is not None:
        tramos.append((inicio, previo))
    return "; ".join(f"C{a:02d}" if a == b else f"C{a:02d}-C{b:02d}" for a, b in tramos)


def casos_por_regla():
    por_regla = {}
    for fila in cargar_casos():
        imp = json.loads(fila["impactos_json"]) if fila["impactos_json"] else None
        for regla in ejecutar(json.loads(fila["respuestas_json"]), imp)["disparadas"]:
            por_regla.setdefault(regla, []).append(fila["caso_id"])
    return por_regla


def main():
    with open(MATRIZ, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        campos, filas = lector.fieldnames, list(lector)
    por_regla = casos_por_regla()
    for fila in filas:
        previo = [p.strip() for p in fila["casos_prueba"].split(";") if p.strip().startswith("tests/")]
        casos = _abreviar(por_regla.get(fila["regla_id"], []))
        fila["casos_prueba"] = "; ".join([x for x in [casos] + previo if x])
    with open(MATRIZ, "w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=campos, lineterminator="\r\n")
        escritor.writeheader()
        escritor.writerows(filas)
    sin = [f["regla_id"] for f in filas if not f["casos_prueba"]]
    print(f"{len(filas) - len(sin)} de {len(filas)} reglas con casos de prueba; sin casos: {sin or 'ninguna'}")


if __name__ == "__main__":
    main()
