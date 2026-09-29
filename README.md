# Port Log — Sprint 2

## Sprint actual
Sprint 2

## Objetivo
Procesar imágenes de matrículas del Puerto Fluvial de Rosario: organizar el dataset de fotos, agrupar por placa, preprocesar, reconocer texto con OCR y medir el desempeño contra el dataset limpio de Sprint 1.

## Introducción y contexto
En Sprint 1 se depuraron los movimientos portuarios y se generaron los CSV de trabajo (`raw`, `interim` y el resumen). En este sprint el equipo trabaja sobre las imágenes asociadas a esos movimientos: descarga y organización de fotos, agrupación por matrícula, pipeline de preprocesamiento (escala de grises, ecualización, blur, Canny), reconocimiento con EasyOCR y métricas de acierto.

## Entorno de ejecución

El trabajo práctico fue desarrollado y validado en **Google Colab**.

[**Abrir notebook en Google Colab**](https://colab.research.google.com/drive/1iCnkIsHzdEI-PWeNtrIE2MUJAZQt4K77)
