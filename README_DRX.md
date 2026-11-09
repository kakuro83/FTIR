# DRX — Visualizador y analizador de difractogramas

Aplicación Python/Streamlit adaptada del visualizador FTIR de este repositorio.

## Ejecutar

Desde la carpeta del repositorio, con Python 3.11 o posterior:

```bash
python -m pip install -r requirements_drx.txt
python -m streamlit run DRX.py
```

En Streamlit Community Cloud, seleccione el repositorio `kakuro83/FTIR`, rama `main` y archivo principal `DRX.py`. El requirements.txt de la raíz también contiene las dependencias necesarias.

## Entrada XY

Dos columnas: **2θ en grados** e **intensidad**, sin requerir encabezado.
Los valores de 2θ deben estar entre 0 y 180 grados (extremos excluidos).
Se admiten espacios, tabulaciones, punto y coma y coma como separadores.
Para coma decimal, elija esa opción y use espacios, tabulaciones o punto y coma como separador.
No use separadores de miles. Se admite notación científica E y D.

```text
# 2theta intensidad
10.00 120
10.02 125
10.04 118
```

Se conserva la primera fila numérica, se ordenan los ángulos y se promedian intensidades de ángulos repetidos con aviso.
Las líneas no válidas o encabezados se informan; comentarios con #, ! y // se omiten.
Los metadatos que sean exactamente dos números pueden parecer datos: use “Filas iniciales a omitir”.
Se exigen tres ángulos distintos; archivos con columnas adicionales deben convertirse a dos columnas.

## Funciones

- Carga múltiple, etiquetas, colores, estilos, orden y rango angular.
- Superposición o apilado (orden 1 arriba); separación relativa a la amplitud máxima.
- Normalización min-max 0–100 por serie dentro del rango seleccionado. Las señales constantes quedan en cero.
- Detección de máximos con prominencia relativa a la amplitud original y separación en grados, incluso con espaciado irregular.
- Distancia interplanar por ley de Bragg: d = λ / [2 sen(θ)], n = 1.
- Longitud de onda ajustable; valor inicial 1.5406 Å (Cu Kα1).
- Gráficos PNG a 300 dpi, SVG y PDF; tabla de picos CSV y datos XY en ZIP.

La tabla conserva intensidades y prominencias originales, sin normalización ni desplazamiento.
El ZIP contiene datos del rango seleccionado con la normalización elegida, sin offset, y un índice de archivos.
Los picos son máximos muestreados, sin ajuste de perfiles: no equivalen a identificación de fases.
No se aplica corrección de fondo, suavizado, refinamiento Rietveld ni cálculo de tamaño de cristalito.
Los extremos del rango no se detectan como picos; revise los parámetros y la radiación antes de interpretar.

## Pruebas

```bash
python -m unittest test_drx.py -v
```

La aplicación FTIR original sigue en `App.py`.
