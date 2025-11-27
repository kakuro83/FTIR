📉 Visualizador y Analizador de Espectros FTIR

Aplicación web desarrollada en Python y Streamlit para graficar, procesar y analizar espectros de Infrarrojo por Transformada de Fourier (FTIR), específicamente diseñada para manejar datos exportados en CSV (modo ATR/Transmitancia).

✨ Características

Carga de Archivos: Soporte para múltiples archivos CSV simultáneos.

Limpieza de Datos: Detección automática de columnas y salto de metadatos (headers).

Visualización Científica:

Eje X invertido (Número de onda).

Eje Y limpio (Transmitancia sin etiquetas numéricas).

Gráficos sin cuadrícula (estilo publicación).

Modos de Gráfico:

Superpuesto (Comparación directa).

Apilado/Offset (Para visualizar múltiples espectros sin solapamiento).

Análisis: Detección automática de bandas (picos) y exportación de tablas.

Normalización: Opción para escalar datos de 0 a 1 (útil para ATR).

Exportación: Descarga de gráficos en PNG de alta resolución (300 DPI).

🚀 Cómo ejecutar localmente

Clona este repositorio.

Instala las dependencias:

pip install -r requirements.txt


Ejecuta la aplicación:

streamlit run streamlit_app.py


☁️ Despliegue

Esta aplicación está lista para ser desplegada en Streamlit Community Cloud:

Sube estos archivos a un repositorio de GitHub.

Conecta tu cuenta de GitHub en share.streamlit.io.

Selecciona el repositorio y el archivo principal streamlit_app.py.
