# Changelog

## [Ejercicio 03]
- Normalización de fechas `fecha_ingreso` y `fecha_egreso` al formato ISO `YYYY-MM-DD` e imputación de fechas inválidas con `1900-01-01`.
- Normalización de horas `hora_ingreso` y `hora_egreso` al formato 24hs e imputación de horas inválidas con `00:00`.
- Cálculo e incorporación de la columna `duracion_horas` entre fecha/hora de ingreso y egreso.
- Limpieza de cadenas, remoción de caracteres especiales y conversión a mayúsculas para las columnas `matricula` y `muelle`.

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
