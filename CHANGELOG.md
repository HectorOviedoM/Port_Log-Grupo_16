# Changelog

## [Ejercicio 01] Correcciones y validación
- Se agrego la logica para que el notebook persista los archivos de output en el repositorio remoto, anteriormente se creaban las carpetas y persistian a nivel local pero no estaban incluidos en el repositorio

- 
## [Ejercicio 04] Correcciones y validación
- Implementación de los promedios real y con tolerancia, conteos por muelle en orden alfabético y por tipo de carga de mayor a menor.
- Ranking de matrículas con índice desde 1 y copia del DataFrame recibido para preservar los datos externos.
- Cuatro invocaciones nuevas en celdas separadas, ejecutadas con resultados guardados.

## [Ejercicio 03] Correcciones y trazabilidad
- Corrección de `normalizar_hora`: uso de `strftime` sobre el Timestamp individual.
- Incorporación de `hora_ingreso_imputada` y `hora_egreso_imputada` antes de reemplazar horas inválidas, conservadas en el CSV limpio.
- Conservación de los criterios de limpieza y de los resultados de los ejercicios 06 y 07; las limitaciones por imputación siguen documentadas.


## [Ejercicio 07]
- Conclusión basada en los resultados del dataset limpio y del diagnóstico del original, exportada a `port_log/reports/conclusion.md`.
- Distinción entre registros excluidos por limpieza/IQR y movimientos excluidos por no presentar infracción.
- Análisis de concentración por turnos, muelles y tipos de carga; limitaciones de las horas imputadas y de la duración promedio.
- Reflexión sobre la migración y propuesta de validaciones y trazabilidad en la captura de datos.

## [Ejercicio 06]
- Porcentajes de infracciones con alguna fecha u hora de ingreso egreso inválida, contando cada registro una sola vez.
- Recuperación de la validez original de las horas para no confundir la imputación `00:00` con una medianoche válida.
- Tipo de carga y origen más frecuentes, con tratamiento de empates, y duración promedio sin convertir ausentes en cero.
- Celdas ejecutadas sobre el resultado de la limpieza existente, sin modificar los ejercicios 01 a 05.



## [Ejercicio 05]
- Top 10 matrículas más reincidentes en barras verticales ordenadas de mayor a menor. Exportado a `port_log/data/interim/plots/top_infractores.jpg`.
- Total de infracciones por turno del día (Madrugada / Mañana / Tarde / Noche) en gráfico de torta. Exportado a `port_log/data/interim/plots/turnos.jpg`.
- Total de infracciones por mes en barras horizontales ordenadas de mayor a menor, excluyendo las fechas inválidas (`1900-01-01`). Exportado a `port_log/data/interim/plots/meses.jpg`.
- Histograma del exceso de velocidad real con curva de densidad (KDE) superpuesta. Exportado a `port_log/data/interim/plots/distribucion_exceso.jpg`.
- Exceso de velocidad promedio por muelle en barras horizontales ordenadas de mayor a menor. Exportado a `port_log/data/interim/plots/exceso_por_muelle.jpg`.
- Comparación de infracciones con fecha válida vs inválida (`1900-01-01`) en barras simples. Exportado a `port_log/data/interim/plots/fechas_invalidas.jpg`.
- Todos los gráficos con título, etiquetas en los ejes y leyenda cuando corresponde.

## [Ejercicio 04]
- Armado de clase PortAnalyzer para hacer operaciones de analisis sin mutar el dataset.
- Asume ya fueron eliminaron los movimientos no-infractores del dataset 

## [Ejercicio 03]
- Normalización de fechas `fecha_ingreso` y `fecha_egreso` al formato ISO `YYYY-MM-DD` e imputación de fechas inválidas con `1900-01-01`.
- Normalización de horas `hora_ingreso` y `hora_egreso` al formato 24hs e imputación de horas inválidas con `00:00`.
- Cálculo e incorporación de la columna `duracion_horas` entre fecha/hora de ingreso y egreso.
- Limpieza de cadenas, remoción de caracteres especiales y conversión a mayúsculas para las columnas `matricula` y `muelle`.
- Eliminación de valores nulos en las columnas críticas del dataset.
- Conversión de tonelaje_declarado y velocidad_ingreso a valores numéricos.
- Detección y eliminación de valores atípicos mediante el método del rango intercuartílico (IQR).
- Cálculo de la columna exceso_velocidad_real respecto al límite de velocidad del muelle.
- Cálculo de la columna exceso_velocidad aplicando una tolerancia del 5%.
- Conservación de los movimientos que superan el límite de velocidad con tolerancia.
- Guardado del dataset limpio en port_log/data/interim/port_movements.csv.
- Exportación del resumen estadístico en port_log/reports/summary_sprint1.csv.


## [Ejercicio 02]
- Inspección inicial de datos con head() e info().
- Identificación de columnas que requieren conversión de datos.
- Conteo e informe de valores nulos y porcentaje de completitud por columna.

## [Ejercicio 02]
- Descarga del dataset raw desde la URL oficial hacia `port_log/data/raw/port_movements.csv`
- Función `descargar_dataset_raw` con pandas (`read_csv` / `to_csv`) y type hints
- Visualización de las primeras y últimas 5 filas en una sola salida con `pd.concat`

## [Ejercicio 01]
- Inicialización del trabajo sobre la rama `Sprint_1`
- Creación de la estructura de carpetas `port_log` (`data/raw`, `data/interim/plots`, `data/processed`, `reports`)
- Celdas de verificación de la estructura en el notebook
