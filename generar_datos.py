"""
Genera datos simulados de "Heladerías Del Sur" (cadena ficticia con locales en 6 provincias).

Salida (carpeta data/):
- ventas_mensuales.csv : mes, provincia, local, categoria, kilos, tickets, facturacion
- sabores_mensuales.csv: mes, provincia, sabor, kilos

Incluye estacionalidad del hemisferio sur (pico en verano, piso en invierno) y
crecimiento de volumen 2025 vs 2024. Los precios suben mes a mes siguiendo la
inflación REAL: el IPC nacional del INDEC (data/ipc_indec.csv).

Uso:
    python generar_datos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(2025)
DATA = Path(__file__).parent / "data"

LOCALES = {
    "Córdoba": ["Nueva Córdoba", "Cerro de las Rosas", "General Paz", "Villa Carlos Paz"],
    "Buenos Aires": ["Mar del Plata", "La Plata", "Pilar"],
    "CABA": ["Palermo", "Belgrano", "Caballito"],
    "Santa Fe": ["Rosario Centro", "Santa Fe Capital"],
    "Mendoza": ["Mendoza Centro", "Godoy Cruz"],
    "Tucumán": ["San Miguel de Tucumán"],
}
# Volumen base mensual (kg) de un local "promedio" en cada provincia
ESCALA_PROV = {"Córdoba": 1.0, "Buenos Aires": 1.15, "CABA": 1.25, "Santa Fe": 0.95, "Mendoza": 0.9, "Tucumán": 1.05}
# Estacionalidad (ene..dic): verano fuerte, invierno flojo
ESTACION = np.array([1.55, 1.45, 1.15, 0.85, 0.6, 0.45, 0.5, 0.5, 0.7, 0.95, 1.2, 1.6])
# Locales con temporada turística propia
TURISTICOS = {"Villa Carlos Paz": [1.5, 1.4, 1.0, 0.8, 0.7, 0.6, 0.9, 0.7, 0.7, 0.8, 1.0, 1.3],
              "Mar del Plata": [1.9, 1.7, 1.0, 0.7, 0.5, 0.4, 0.6, 0.5, 0.6, 0.8, 1.0, 1.5]}
CATEGORIAS = {  # participación en kilos, precio por kg equivalente (ene 2024, ARS), kg por ticket
    "Helado por kilo": (0.62, 9000, 0.9),
    "Cucuruchos y vasitos": (0.22, 12500, 0.18),
    "Postres helados": (0.10, 11000, 0.6),
    "Palitos y bombones": (0.06, 14000, 0.15),
}
SABORES = {"Dulce de leche": 0.17, "Chocolate": 0.14, "Dulce de leche granizado": 0.10, "Frutilla a la crema": 0.09,
           "Sambayón": 0.06, "Limón": 0.07, "Menta granizada": 0.05, "Americana": 0.06, "Banana split": 0.05,
           "Tramontana": 0.06, "Chocolate amargo": 0.06, "Mascarpone con frutos rojos": 0.05}

MESES = pd.period_range("2024-01", "2025-12", freq="M")
# Índice de precios real (IPC INDEC), relativo a enero 2024: los precios base son de ese mes
ipc = pd.read_csv(DATA / "ipc_indec.csv", parse_dates=["indice_tiempo"])
ipc = ipc.set_index(ipc["indice_tiempo"].dt.to_period("M"))["ipc_nivel_general_nacional"]
faltan = [str(m) for m in MESES if m not in ipc.index]
if faltan:
    raise SystemExit(f"Al IPC le faltan meses: {faltan}")
INDICE_PRECIO = (ipc[MESES] / ipc[MESES[0]]).to_numpy()


def main() -> None:
    DATA.mkdir(exist_ok=True)
    ventas, sabores = [], []
    for t, mes in enumerate(MESES):
        crecimiento = 1.0 if mes.year == 2024 else 1.08  # +8% de volumen en 2025
        # Un local nuevo abre en julio 2024
        for prov, locales in LOCALES.items():
            kg_prov = 0.0
            for local in locales:
                if local == "Pilar" and mes < pd.Period("2024-07", "M"):
                    continue
                est = TURISTICOS.get(local, ESTACION)[mes.month - 1] if local in TURISTICOS else ESTACION[mes.month - 1]
                kg_local = 2600 * ESCALA_PROV[prov] * est * crecimiento * rng.normal(1, 0.06)
                if local == "Pilar" and mes < pd.Period("2025-01", "M"):
                    kg_local *= 0.7  # local nuevo, todavía ganando clientes
                for cat, (part, precio_base, kg_ticket) in CATEGORIAS.items():
                    kg = kg_local * part * rng.normal(1, 0.05)
                    precio = precio_base * INDICE_PRECIO[t] * rng.normal(1, 0.02)
                    ventas.append({"mes": str(mes), "provincia": prov, "local": local, "categoria": cat,
                                   "kilos": round(kg, 1), "tickets": int(kg / kg_ticket),
                                   "facturacion": round(kg * precio, 0)})
                kg_prov += kg_local * CATEGORIAS["Helado por kilo"][0]
            pesos = np.array(list(SABORES.values()))
            pesos = pesos * rng.normal(1, 0.08, len(pesos))
            if mes.month in (12, 1, 2):  # en verano suben los frutales y granizados
                for i, s in enumerate(SABORES):
                    if s in ("Limón", "Frutilla a la crema", "Menta granizada", "Mascarpone con frutos rojos"):
                        pesos[i] *= 1.35
            pesos = pesos / pesos.sum()
            for s, p in zip(SABORES, pesos):
                sabores.append({"mes": str(mes), "provincia": prov, "sabor": s, "kilos": round(kg_prov * p, 1)})

    pd.DataFrame(ventas).to_csv(DATA / "ventas_mensuales.csv", index=False)
    pd.DataFrame(sabores).to_csv(DATA / "sabores_mensuales.csv", index=False)
    print(f"{len(ventas)} filas de ventas y {len(sabores)} de sabores en {DATA}")


if __name__ == "__main__":
    main()
