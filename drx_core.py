"""Lectura XY y detección de máximos de difracción, sin dependencias de interfaz."""
import re
import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def read_xy(content, skip_rows=0, separator="Automático", decimal="."):
    """Lee exactamente dos columnas; conserva la primera fila numérica."""
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = content.decode("latin1")
    rows, ignored = [], []
    for number, raw in enumerate(content.splitlines(), 1):
        if number <= skip_rows:
            continue
        line = re.split(r"#|!|//", raw, maxsplit=1)[0].strip()
        if not line:
            continue
        if separator == "Automático":
            if ";" in line:
                parts = line.split(";")
            elif len(line.split()) == 2:
                parts = line.split()
            elif decimal == "." and "," in line:
                parts = line.split(",")
            else:
                parts = line.split()
        elif separator == "Espacios / tabulaciones":
            parts = line.split()
        else:
            parts = line.split({";": ";", ",": ",", "Tabulación": "\t"}[separator])
        try:
            if len(parts) != 2:
                raise ValueError
            values = [float(v.strip().replace(decimal, ".").replace("D", "E").replace("d", "e")) for v in parts]
            if not np.isfinite(values).all() or not 0 < values[0] < 180:
                raise ValueError
            rows.append(values)
        except ValueError:
            ignored.append(number)
    if len(rows) < 3:
        raise ValueError("Se requieren al menos tres pares válidos: 2θ (0 < grados < 180) e intensidad. Revise separador, decimal y encabezado.")
    df = pd.DataFrame(rows, columns=["x", "y"]).sort_values("x")
    duplicates = int(df.duplicated("x").sum())
    # Repeated angles are combined explicitly and reported to the user.
    df = df.groupby("x", as_index=False, sort=True)["y"].mean()
    if len(df) < 3:
        raise ValueError("Se requieren al menos tres ángulos distintos.")
    return df, ignored, duplicates


def normalize(y):
    y = np.asarray(y, dtype=float)
    span = np.ptp(y)
    return np.zeros_like(y) if span == 0 else (y - y.min()) / span * 100


def detect_peaks(x, y, prominence_percent=5.0, separation_deg=0.1, wavelength=1.5406):
    """Máximos muestreados; separación angular real, incluso en mallas irregulares."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if wavelength <= 0 or separation_deg < 0 or not 0 <= prominence_percent <= 100:
        raise ValueError("Parámetros de detección inválidos.")
    indices, properties = find_peaks(y, prominence=np.ptp(y) * prominence_percent / 100)
    # Prefer prominent peaks, then enforce actual angular separation.
    selected = []
    for j in np.argsort(-properties["prominences"], kind="stable"):
        i = indices[j]
        if all(abs(x[i] - x[k]) >= separation_deg for k, _ in selected):
            selected.append((i, properties["prominences"][j]))
    selected.sort()
    result = []
    for i, prominence in selected:
        result.append({
            "2θ (°)": x[i],
            "Intensidad original": y[i],
            "Prominencia original": prominence,
            "d (Å)": wavelength / (2 * np.sin(np.deg2rad(x[i] / 2))),
            "Longitud de onda (Å)": wavelength,
        })
    return pd.DataFrame(result, columns=["2θ (°)", "Intensidad original", "Prominencia original", "d (Å)", "Longitud de onda (Å)"])
