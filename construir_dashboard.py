"""
Construye dashboard.html: un único archivo con los datos embebidos, que se abre
en cualquier navegador (sin internet) y se puede publicar gratis en GitHub Pages.

Además calcula la facturación SIN INFLACIÓN con dos índices reales del INDEC:
    facturacion_real = facturacion * IPC(último mes) / IPC(mes de la venta)
- IPC nivel general: poder de compra general de lo facturado.
- IPC alimentos y bebidas no alcohólicas: vara más cercana al rubro.
Esto mide poder de compra de la facturación, no rentabilidad: para márgenes harían falta los costos.

Uso:
    python construir_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).parent
MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Índices disponibles para ajustar por inflación (archivos descargados de datos.gob.ar)
DEFLACTORES = {
    "general": {"archivo": "ipc_indec.csv", "nombre": "IPC nivel general",
                "serie": "148.3_INIVELNAL_DICI_M_26"},
    "alimentos": {"archivo": "ipc_alimentos_indec.csv", "nombre": "IPC alimentos y bebidas",
                  "serie": "146.3_IALIMENNAL_DICI_M_45"},
}


def cargar_indice(archivo: str) -> pd.Series:
    ipc = pd.read_csv(RAIZ / "data" / archivo, parse_dates=["indice_tiempo"])
    return ipc.set_index(ipc["indice_tiempo"].dt.strftime("%Y-%m")).iloc[:, -1]


def main() -> None:
    ventas = pd.read_csv(RAIZ / "data" / "ventas_mensuales.csv")
    sabores = pd.read_csv(RAIZ / "data" / "sabores_mensuales.csv")

    # Controles antes de publicar
    assert ventas[["kilos", "facturacion", "tickets"]].ge(0).all().all(), "hay valores negativos"
    assert ventas["mes"].str.match(r"^\d{4}-\d{2}$").all(), "formato de mes inválido"

    base = ventas["mes"].max()   # pesos constantes del último mes con ventas
    meses = sorted(ventas["mes"].unique())
    previo = (pd.Period(meses[0], "M") - 1).strftime("%Y-%m")
    inflacion, meta = {}, {}
    for clave, d in DEFLACTORES.items():
        if not (RAIZ / "data" / d["archivo"]).exists():
            print(f"Aviso: falta data/{d['archivo']}; se omite el ajuste por {d['nombre']}")
            continue
        ipc = cargar_indice(d["archivo"])
        faltan = sorted(set(meses) - set(ipc.index))
        assert not faltan, f"a {d['archivo']} le faltan meses: {faltan}"
        ventas[f"facturacion_real_{clave}"] = (ventas["facturacion"] * ipc[base] / ventas["mes"].map(ipc)).round(0)
        serie = ipc.loc[[previo] + meses] if previo in ipc.index else ipc.loc[meses]
        inflacion[clave] = {m: round(v * 100, 4) for m, v in serie.pct_change().dropna().items()}
        meta[clave] = {"nombre": d["nombre"], "serie": d["serie"]}
    assert "general" in meta, "el IPC nivel general es obligatorio"

    anio, mes = base.split("-")
    base_texto = f"{MESES_ES[int(mes) - 1]} {anio}"

    html = (RAIZ / "plantilla.html").read_text(encoding="utf-8")
    reemplazos = {
        "__VENTAS__": ventas.to_dict("records"),
        "__SABORES__": sabores.to_dict("records"),
        "__INFLACION__": inflacion,
        "__DEFLACTORES__": meta,
        "__BASE_REAL__": base_texto,
    }
    for marcador, valor in reemplazos.items():
        assert marcador in html, f"falta {marcador} en la plantilla"
        html = html.replace(marcador, json.dumps(valor, ensure_ascii=False, separators=(",", ":")))

    salida = RAIZ / "dashboard.html"
    salida.write_text(html, encoding="utf-8")
    print(f"Dashboard generado: {salida} ({salida.stat().st_size / 1024:.0f} KB) · pesos constantes de {base_texto} · "
          f"índices: {', '.join(m['nombre'] for m in meta.values())}")


if __name__ == "__main__":
    main()
