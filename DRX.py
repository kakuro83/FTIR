"""Ejecutar: python -m streamlit run DRX.py"""
import io
import zipfile
import hashlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from drx_core import read_xy, normalize, detect_peaks


def main():
    st.set_page_config(page_title="Visualizador DRX", page_icon="📈", layout="wide")
    st.title("📈 Análisis y gráficos de difracción de rayos X")
    st.caption("Archivos XY · 2θ (grados) e intensidad · Comparación de difractogramas")
    with st.sidebar:
        st.header("1. Carga de archivos")
        files = st.file_uploader("Archivos XY o TXT", type=["xy", "txt"], accept_multiple_files=True)
        skip = st.number_input("Filas iniciales a omitir", min_value=0, value=0, step=1)
        separator = st.selectbox("Separador", ["Automático", "Espacios / tabulaciones", "Tabulación", ";", ","])
        decimal = st.selectbox("Símbolo decimal", [".", ","])
        st.caption("Dos columnas: 2θ e intensidad. Encabezados no numéricos se omiten y se informa su número.")
        st.header("3. Opciones de gráfico")
        crop = st.checkbox("Limitar rango de 2θ")
        c1, c2 = st.columns(2)
        xmin = c1.number_input("Mínimo (°)", min_value=0.0, max_value=180.0, value=5.0)
        xmax = c2.number_input("Máximo (°)", min_value=0.0, max_value=180.0, value=90.0)
        normalized = st.checkbox("Normalizar intensidad (0–100)", value=False)
        stacked = st.checkbox("Modo apilado", value=False)
        spacing = st.number_input("Separación (fracción de amplitud máxima)", min_value=0.0, value=1.1, step=0.1)
        st.caption("En apilado, orden 1 aparece arriba. El desplazamiento no cambia los datos exportados.")
        st.subheader("Detección de picos")
        prominence = st.slider("Prominencia mínima (% de amplitud)", 0.1, 100.0, 5.0, 0.1)
        separation = st.number_input("Separación mínima entre picos (°)", min_value=0.0, value=0.1, step=0.05, format="%.3f")
        wavelength = st.number_input("Longitud de onda (Å)", min_value=0.0001, value=1.5406, step=0.0001, format="%.4f", help="Valor inicial: Cu Kα1. Ajuste según la radiación de su equipo.")
        marks = st.checkbox("Marcar picos", value=True)
        annotations = st.checkbox("Etiquetar posiciones 2θ", value=False)
        st.subheader("Estética")
        axis_size = st.slider("Tamaño de fuente de ejes", 8, 22, 12)
        legend_size = st.slider("Tamaño de leyenda", 6, 18, 10)
        legend = st.selectbox("Posición de leyenda", ["best", "upper right", "upper left", "lower right", "none"])
        yticks = st.checkbox("Mostrar valores del eje Y", value=True)
        width = st.slider("Ancho de figura (pulgadas)", 6, 16, 10)
        height = st.slider("Alto de figura (pulgadas)", 4, 12, 6)
    if not files:
        st.info("Suba uno o varios archivos .xy desde el panel izquierdo.")
        st.code("# 2theta  intensidad\n10.00  120\n10.02  125\n10.04  118", language="text")
        st.write("Personalice etiquetas, colores y orden; descargue la figura, la tabla de picos y los datos del rango seleccionado.")
        return
    if separator == "," and decimal == ",":
        st.error("La coma no puede ser simultáneamente separador y símbolo decimal.")
        return
    if crop and xmin >= xmax:
        st.error("El máximo de 2θ debe ser mayor que el mínimo.")
        return
    st.header("2. Configuración de series")
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    series = []
    for i, file in enumerate(files):
        data = file.getvalue()
        key = hashlib.sha256(file.name.encode() + data).hexdigest()[:16] + str(i)
        try:
            df, ignored, duplicates = read_xy(data, skip, separator, decimal)
        except ValueError as exc:
            st.error(f"{file.name}: {exc}")
            continue
        if ignored:
            st.warning(f"{file.name}: {len(ignored)} líneas no válidas o de encabezado omitidas. Primeras líneas: {ignored[:10]}.")
        if duplicates:
            st.warning(f"{file.name}: {duplicates} ángulos repetidos; sus intensidades se promediaron.")
        if crop:
            df = df.loc[df.x.between(xmin, xmax)].copy()
        if len(df) < 3:
            st.warning(f"{file.name}: menos de tres puntos en el rango seleccionado.")
            continue
        with st.expander(file.name, expanded=(i == 0)):
            c0, c1, c2, c3 = st.columns([1, 3, 2, 2])
            order = c0.number_input("Orden", min_value=1, value=i + 1, step=1, key="order"+key)
            label = c1.text_input("Etiqueta", file.name.rsplit(".", 1)[0], key="label"+key)
            color = c2.color_picker("Color", palette[i % len(palette)], key="color"+key)
            style = c3.selectbox("Estilo de línea", ["-", "--", "-.", ":"], key="style"+key)
            st.caption(f"{len(df)} puntos · 2θ: {df.x.min():.4f}–{df.x.max():.4f}°")
        y = normalize(df.y) if normalized else df.y.to_numpy()
        peaks = detect_peaks(df.x, df.y, prominence, separation, wavelength)
        series.append(dict(df=df, y=y, peaks=peaks, order=order, label=label, color=color, style=style, filename=file.name))
    if not series:
        return
    series.sort(key=lambda item: item["order"])
    amplitude = max(float(np.ptp(item["y"])) for item in series) or 1.0
    fig, ax = plt.subplots(figsize=(width, height))
    tables = []
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, item in enumerate(series):
            df, y, peaks = item["df"], item["y"], item["peaks"]
            offset = (len(series)-1-idx) * spacing * amplitude if stacked else 0
            ax.plot(df.x, y + offset, label=item["label"], color=item["color"], linestyle=item["style"], linewidth=1.2)
            if not peaks.empty:
                py = np.interp(peaks["2θ (°)"], df.x, y) + offset
                if marks:
                    ax.scatter(peaks["2θ (°)"], py, marker="v", s=18, color=item["color"])
                if annotations:
                    for px, peak_y in zip(peaks["2θ (°)"], py):
                        ax.annotate(f"{px:.2f}", (px, peak_y), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=8, rotation=90)
                table = peaks.copy()
                table.insert(0, "Serie", item["label"])
                table.insert(1, "Archivo", item["filename"])
                tables.append(table)
            export = pd.DataFrame({"2theta_deg": df.x, "intensity": y})
            zf.writestr(f"{idx+1:02d}_datos.xy", export.to_csv(index=False, header=False, sep="\t", float_format="%.10g"))
        zf.writestr("LEEME.txt", "Datos sin offset; columnas: 2theta (grados), intensidad.\nNormalización min-max 0–100: " + str(normalized) + "\nOrden de archivos:\n" + "\n".join(f"{i+1:02d}_datos.xy: {s['filename']} | {s['label']}" for i, s in enumerate(series)))
    ax.set_xlabel("2θ (°)", fontsize=axis_size)
    ylabel = "Intensidad normalizada (u.a., 0–100)" if normalized else "Intensidad (unidades del archivo)"
    ax.set_ylabel(ylabel + (" + desplazamiento" if stacked else ""), fontsize=axis_size)
    if crop:
        ax.set_xlim(xmin, xmax)
    ax.tick_params(labelsize=axis_size)
    if not yticks:
        ax.set_yticks([])
    ax.spines[["top", "right"]].set_visible(False)
    if legend != "none":
        ax.legend(loc=legend, fontsize=legend_size, frameon=False)
    fig.tight_layout()
    st.pyplot(fig)
    st.subheader("Exportar resultados")
    columns = st.columns(3)
    for col, fmt, mime in zip(columns, ["png", "svg", "pdf"], ["image/png", "image/svg+xml", "application/pdf"]):
        buffer = io.BytesIO()
        fig.savefig(buffer, format=fmt, dpi=300, bbox_inches="tight")
        col.download_button(f"Gráfico {fmt.upper()}", buffer.getvalue(), f"drx_plot.{fmt}", mime)
    plt.close(fig)
    st.download_button("Datos XY del rango seleccionado (ZIP)", archive.getvalue(), "drx_datos.zip", "application/zip")
    if tables:
        table = pd.concat(tables, ignore_index=True)
        st.dataframe(table, hide_index=True)
        st.download_button("Tabla de picos (CSV)", table.to_csv(index=False).encode("utf-8-sig"), "picos_drx.csv", "text/csv")
    else:
        st.info("No se detectaron picos con estos parámetros.")
    st.caption("Los picos corresponden a máximos muestreados de los datos originales del rango seleccionado. d = λ/[2 sen(θ)], orden n = 1. La normalización es min-max por serie y rango; no corrige el fondo. No identifica fases ni estima tamaño de cristalito.")


if __name__ == "__main__":
    main()
