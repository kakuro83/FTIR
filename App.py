import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import io

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Visualizador FTIR", 
    layout="wide", 
    page_icon="📈"
)

# --- Estilos CSS personalizados para limpiar la interfaz ---
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1 {text-align: center; color: #2E4053;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Funciones Auxiliares ---

def detect_csv_format(uploaded_file):
    uploaded_file.seek(0)
    sample = uploaded_file.read(4096)
    if isinstance(sample, bytes):
        sample = sample.decode("latin1", errors="ignore")
    uploaded_file.seek(0)

    lines = [line for line in sample.splitlines() if line.strip()]
    header_line = lines[0] if lines else ""

    if ";" in header_line:
        return ";", ","
    if "\t" in header_line:
        return "\t", "."
    if "," in header_line:
        return ",", "."
    return ",", "."


def read_csv_flexible(uploaded_file, skip_rows):
    detected_sep, detected_decimal = detect_csv_format(uploaded_file)
    read_attempts = [
        {"sep": detected_sep, "engine": "python", "decimal": detected_decimal},
        {"sep": detected_sep, "engine": "python"},
        {"sep": None, "engine": "python"},
        {"sep": ";", "engine": "python", "decimal": ","},
        {"sep": ";", "engine": "python"},
        {"sep": "\t", "engine": "python"},
        {"sep": ",", "engine": "python", "decimal": ","},
    ]

    for params in read_attempts:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, skiprows=skip_rows, encoding="latin1", **params)
            df = df.dropna(axis=1, how="all")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue
    return None


def load_ftir_data(uploaded_file, skip_rows):
    """
    Carga el archivo CSV saltando filas de metadatos.
    Intenta detectar columnas automáticamente.
    """
    try:
        # Leemos el archivo
        # encoding='latin1' es común en equipos científicos antiguos/windows
        df = read_csv_flexible(uploaded_file, skip_rows)
        if df is None:
            return None
        
        # Limpieza básica de nombres de columnas
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Identificar columnas de Wavenumber y Transmittance por palabras clave
        wavenumber_col = next((c for c in df.columns if 'cm-1' in c or 'wave' in c or 'numero' in c or 'wavenumber' in c), None)
        transmittance_col = next((c for c in df.columns if '%t' in c or 'trans' in c or 'tra' in c), None)

        # Si falla la detección por nombre, usar índices 0 (X) y 1 (Y)
        if not wavenumber_col or not transmittance_col:
            if len(df.columns) >= 2:
                wavenumber_col = df.columns[0]
                transmittance_col = df.columns[1]
            else:
                return None

        # Asegurar que sean numéricos y eliminar filas vacías/texto
        for col in (wavenumber_col, transmittance_col):
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip().str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.dropna()
        
        # Renombrar para estandarizar el código interno
        df = df.rename(columns={wavenumber_col: 'x', transmittance_col: 'y'})
        
        # Ordenar por número de onda descendente (típico en visualización, pero pandas prefiere ascendente para procesar)
        return df.sort_values(by='x', ascending=False)
    except Exception as e:
        return None

def normalize_data(series):
    """Normaliza una serie entre 0 y 1 (Min-Max scaling)."""
    if series.max() == series.min():
        return series # Evitar división por cero
    return (series - series.min()) / (series.max() - series.min())

def find_ftir_peaks(x, y, prominence=0.01):
    """
    Encuentra picos en espectros FTIR. 
    Como FTIR es transmitancia (valles), invertimos los datos (-y) para buscar picos.
    """
    # Invertimos Y porque find_peaks busca máximos locales
    peaks, properties = find_peaks(-1*y, prominence=prominence)
    return x.iloc[peaks], y.iloc[peaks]

# --- Interfaz Principal ---

st.title("📈 Análisis y Gráficos de Espectros FTIR")

with st.sidebar:
    st.header("1. Carga de Archivos")
    uploaded_files = st.file_uploader(
        "Sube archivos CSV (Equipo FTIR/ATR)", 
        type=['csv', 'txt'], 
        accept_multiple_files=True
    )
    
    st.caption("Ajuste de lectura de archivo:")
    skip_rows = st.number_input("Filas de encabezado a saltar", min_value=0, value=1, step=1, help="Número de líneas de texto antes de que empiecen los datos numéricos en el CSV.")

    st.header("3. Opciones de Gráfico")
    
    # Rango del Eje X
    st.subheader("Rango (Número de Onda)")
    col_r1, col_r2 = st.columns(2)
    x_max_limit = col_r1.number_input("Máx (cm⁻¹)", value=4000)
    x_min_limit = col_r2.number_input("Mín (cm⁻¹)", value=400)
    invalid_range = x_max_limit <= x_min_limit
    if invalid_range:
        st.error("El valor máximo debe ser mayor que el mínimo para graficar el espectro.")
    
    st.divider()
    
    # Opciones de Normalización y Visualización
    normalize_option = st.checkbox("Normalizar Espectros (0-1)", value=False, help="Ajusta la escala de todos los espectros de 0 a 1 para comparar formas.")
    
    stack_mode = st.checkbox("Modo Apilado (Offset)", value=False, help="Graficar uno encima del otro para evitar superposición.")
    offset_value = 0.0
    if stack_mode:
        offset_value = st.slider("Separación vertical", 0.0, 1.5, 0.5, step=0.1)

    st.divider()
    
    # Estética
    st.subheader("Estética")
    font_size_axis = st.slider("Tamaño Fuente Ejes", 8, 20, 12)
    font_size_legend = st.slider("Tamaño Fuente Leyenda", 6, 16, 9)
    legend_options = {
        "Automática (dentro)": "best",
        "Arriba a la derecha (dentro)": "upper right",
        "Arriba a la izquierda (dentro)": "upper left",
        "Abajo a la derecha (dentro)": "lower right",
        "Derecha (fuera)": "outside_right",
        "Debajo (fuera)": "outside_bottom",
        "Sin leyenda": "none",
    }
    legend_label = st.selectbox("Posición Leyenda", list(legend_options), index=0)
    loc_legend = legend_options[legend_label]
    legend_columns = 1
    if loc_legend == "outside_bottom":
        legend_columns = st.number_input("Columnas de la leyenda", min_value=1, max_value=6, value=3, step=1)

# --- Procesamiento y Configuración Individual ---

if uploaded_files:
    st.header("2. Configuración de Series")
    st.caption("Marque Mostrar en el gráfico para elegir las series del gráfico y las exportaciones. Al ocultarlas se conservan sus ajustes.")
    
    plot_data = [] # Lista para guardar los dataframes procesados
    
    # Iterar sobre los archivos subidos
    for i, file in enumerate(uploaded_files):
        # Cargar datos
        df = load_ftir_data(file, skip_rows)
        
        if df is not None and not df.empty:
            # Filtrar por rango seleccionado para optimizar
            if invalid_range:
                st.warning("Ajusta el rango del eje X antes de procesar los archivos.")
                break
            mask = (df['x'] <= x_max_limit) & (df['x'] >= x_min_limit)
            df_filtered = df[mask].copy()
            
            if df_filtered.empty:
                st.warning(f"El archivo {file.name} no tiene datos en el rango seleccionado.")
                continue

            if normalize_option:
                df_filtered['y'] = normalize_data(df_filtered['y'])
            
            # --- Panel de Configuración por Archivo (Expanders) ---
            with st.expander(f"🖍️ {file.name}", expanded=(i==0)):
                show_series = st.checkbox("Mostrar en el gráfico", value=True, key=f"show_{i}")
                # Se añaden 4 columnas para incluir el campo de Orden
                c0, c1, c2, c3 = st.columns([1, 2, 2, 2])
                
                # NUEVO: Campo de Orden
                order = c0.number_input(
                    "Orden", 
                    min_value=1, 
                    value=i + 1, 
                    step=1, 
                    key=f"ord_{i}",
                    help="Define el orden de graficado y leyenda (1 es el primero en la parte superior del apilado)."
                )

                default_name = file.name.rsplit('.', 1)[0]
                label = c1.text_input(f"Etiqueta", value=default_name, key=f"lbl_{i}")
                
                # Paleta de colores rotativa por defecto
                default_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
                color = c2.color_picker(f"Color", value=default_colors[i % len(default_colors)], key=f"clr_{i}")
                
                linestyle = c3.selectbox(f"Estilo Línea", ["-", "--", "-.", ":"], key=f"lst_{i}")
            
            if not show_series:
                continue
            plot_data.append({
                "df": df_filtered,
                "label": label,
                "color": color,
                "linestyle": linestyle,
                "filename": file.name,
                "order": order # Guardar el orden definido por el usuario
            })
        else:
            st.error(f"⚠️ Error leyendo {file.name}. Verifica que sea un CSV válido y ajusta las 'Filas a saltar' en el menú lateral.")

    if not plot_data and not invalid_range:
        st.info("No hay series seleccionadas con datos en el rango. Active Mostrar en el gráfico en al menos un archivo.")

    # --- Generación del Gráfico ---
    if plot_data:
        st.write("---")

        # NUEVO: Ordenar la lista de datos según el campo 'order'
        plot_data.sort(key=lambda x: x['order'])
        
        # Crear figura Matplotlib
        # Ajustamos figsize para que sea panorámico
        fig, ax = plt.subplots(figsize=(10, 6))
        
        all_peaks_data = []

        # Graficar cada serie
        for idx, item in enumerate(plot_data):
            y_plot = item['df']['y'].values
            x_plot = item['df']['x'].values
            
            # Aplicar Offset para modo apilado
            # NOTA: idx ahora representa la posición en el *orden deseado*
            current_offset = idx * offset_value if stack_mode else 0
            y_final = y_plot + current_offset
            
            ax.plot(
                x_plot, 
                y_final, 
                label=item['label'], 
                color=item['color'], 
                linestyle=item['linestyle'],
                linewidth=1.2
            )
            
            # --- Detección de Bandas ---
            # Prominence dinámico: si está normalizado, buscamos picos más pequeños (0.02), si no, más grandes (1.0)
            prom = 0.02 if normalize_option else 0.5
            peaks_x, peaks_y = find_ftir_peaks(item['df']['x'], item['df']['y'], prominence=prom)
            
            transmittance_label = "Transmitancia Normalizada" if normalize_option else "Transmitancia Original"
            for px, py in zip(peaks_x, peaks_y):
                all_peaks_data.append({
                    "Serie": item['label'],
                    "Número de Onda (cm⁻¹)": round(px, 2),
                    transmittance_label: round(py, 4),
                    "Archivo Origen": item['filename']
                })

        # --- Estética Limpia (Clean Look) ---
        ax.set_xlim(x_max_limit, x_min_limit) # Eje X Invertido (Mayor a menor)
        
        ax.set_xlabel("Número de Onda ($cm^{-1}$)", fontsize=font_size_axis)
        ax.set_ylabel("Transmitancia (u.a.)", fontsize=font_size_axis)
        
        # Quitar números del eje Y
        ax.set_yticks([]) 
        
        # Tamaño texto eje X
        ax.tick_params(axis='x', labelsize=font_size_axis)
        
        # Bordes: Quitar superior y derecho
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        # Mantener izquierdo y inferior
        ax.spines['left'].set_visible(True)
        ax.spines['bottom'].set_visible(True)

        # Leyenda limpia
        if loc_legend == "outside_right":
            ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5),
                      borderaxespad=0, fontsize=font_size_legend, frameon=False)
        elif loc_legend == "outside_bottom":
            ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18),
                      ncol=min(legend_columns, len(plot_data)),
                      borderaxespad=0, fontsize=font_size_legend, frameon=False)
        elif loc_legend != "none":
            ax.legend(loc=loc_legend, fontsize=font_size_legend, frameon=False)
        fig.tight_layout()
        
        # Mostrar en Streamlit
        st.pyplot(fig)

        # --- Área de Descargas ---
        st.subheader("📥 Exportar Resultados")
        col_d1, col_d2 = st.columns(2)

        # 1. Descargar PNG
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
        img_buffer.seek(0)
        col_d1.download_button(
            label="📷 Descargar Gráfico (PNG)",
            data=img_buffer,
            file_name="ftir_plot.png",
            mime="image/png",
            use_container_width=True
        )

        # 2. Descargar Bandas
        if all_peaks_data:
            df_peaks = pd.DataFrame(all_peaks_data)
            csv_peaks = df_peaks.to_csv(index=False).encode('utf-8')
            col_d2.download_button(
                label="📄 Descargar Tabla de Bandas (CSV)",
                data=csv_peaks,
                file_name="bandas_ftir.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            with st.expander("Ver tabla de bandas detectadas"):
                st.dataframe(df_peaks)

else:
    # Mensaje de bienvenida/instrucción
    st.info("👈 Utiliza el panel izquierdo para subir tus archivos CSV o TXT de espectroscopia.")
    st.markdown("""
    ### Instrucciones:
    1. **Sube** tus archivos CSV generados por el equipo FTIR.
    2. Ajusta el parámetro **"Filas a saltar"** si tus archivos tienen texto al principio.
    3. Usa las opciones de **Personalización** para cambiar colores, nombres y **el orden de graficado**.
    4. Descarga la imagen final o la tabla de bandas.
    """)
