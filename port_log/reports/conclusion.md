# Conclusión — Port Log, Sprint 1

## Calidad del dataset heredado

El archivo original contiene 1500 movimientos y el dataset limpio
conserva 447 registros infractores. Quedaron fuera del conjunto
final 1053 registros (70.20% del original).
Este porcentaje no equivale a un porcentaje de datos erróneos: la limpieza y
el criterio IQR excluyeron 313 registros
(20.87% del original), mientras que
otros 740 registros
(49.33%) fueron excluidos por no
superar el límite de velocidad con la tolerancia del 5%. Los valores atípicos
excluidos por IQR son candidatos estadísticos, no errores comprobados por sí solos.

Las incidencias comprobadas en el original, ordenadas por frecuencia, son:
Algún valor nulo: 332 (22.13%); Alguna hora inválida o ausente: 231 (15.40%); Matrícula inutilizable después de normalizar: 91 (6.07%); Alguna fecha inválida o ausente: 90 (6.00%).
Estas categorías se superponen: una misma fila puede presentar más de un problema.
Los nulos por columna se distribuyen así:
velocidad_ingreso: 82 (5.47%); tonelaje_declarado: 69 (4.60%); radar_id: 65 (4.33%); estado_despacho: 58 (3.87%); matricula: 56 (3.73%); hora_egreso: 34 (2.27%).
También fue necesario unificar los formatos de fecha y hora y normalizar las
matrículas y los muelles. La normalización de texto no implica necesariamente
que el registro deba descartarse.

Entre las infracciones conservadas, el 4.92% tiene
alguna fecha de ingreso o egreso inválida y el 14.99%
tenía alguna hora inválida antes de la imputación. Cada registro se cuenta una
sola vez en cada porcentaje. Una fecha imputada a 1900-01-01 no es una fecha
real y una hora 00:00 no prueba por sí sola un error: puede representar una
medianoche válida. Por eso, la calidad de las horas se recuperó del archivo
original para los mismos movimientos que permanecen en el dataset limpio.

## Patrones de infracción

La distribución por turno, calculada sobre las horas normalizadas del dataset
limpio y consistente con el ejercicio 05, es:
Tarde: 124 (27.74%); Madrugada: 123 (27.52%); Noche: 103 (23.04%); Mañana: 97 (21.70%).
Sin embargo, 26 infracciones tienen la hora de
ingreso imputada a 00:00 y quedan asignadas artificialmente a Madrugada.
Como control, al considerar solo los 421 registros con
hora de ingreso originalmente válida, la distribución es:
Tarde: 124 (29.45%); Noche: 103 (24.47%); Mañana: 97 (23.04%); Madrugada: 97 (23.04%).

Los tres muelles con más registros infractores son:
MUELLE-B: 75 (16.78%); MUELLE-C: 75 (16.78%); MUELLE-D: 74 (16.55%).
Los tres tipos de carga más frecuentes entre las infracciones son:
TRIGO: 69 (15.44%); CONTENEDORES: 68 (15.21%); HARINA: 59 (13.20%).
Hay 0 infracciones sin muelle informado y
0 sin tipo de carga informado; los
porcentajes anteriores usan todas las infracciones como denominador.
Estas concentraciones describen cantidades dentro del conjunto de infractores,
no tasas de riesgo: para comparar propensión a infringir haría falta conocer
el total de movimientos de cada turno, muelle y tipo de carga antes de filtrar.
Tampoco representan cantidades de buques únicos, ya que un buque puede aparecer
en más de un movimiento.

La estadía promedio es 98.30 horas, calculada sobre
400 duraciones disponibles y excluyendo
47 valores ausentes. De las
duraciones utilizadas, 59 incluyen alguna hora
imputada; por ello el promedio debe interpretarse con esa limitación y no como
una medición completamente verificada de los tiempos de estadía.

## Impacto de migrar sin limpieza

Incorporar directamente el archivo heredado podría asociar movimientos a
matrículas incorrectas, fragmentar un mismo muelle en distintas categorías y
producir estadísticas temporales y duraciones engañosas. Los nulos y los
valores extremos también afectarían las comparaciones de tonelaje y velocidad.
Las imputaciones deben quedar señaladas explícitamente para que el nuevo
sistema no interprete datos sustituidos como observaciones reales. Además,
el dataset final de este sprint contiene solo infracciones: no debe utilizarse
como reemplazo del registro completo de operaciones del puerto.

## Propuesta de mejora

Implementar en el punto de captura un formulario con fechas ISO y horas de
24 horas validadas, matrícula obligatoria con formato definido y un catálogo
único de muelles y tipos de carga. El egreso debe ser posterior al ingreso y
los campos numéricos deben pasar controles de rango definidos con el área
operativa. Los límites de velocidad deben obtenerse del catálogo de muelles.
Los registros que fallen una validación deben ir a una bandeja de revisión,
conservando el valor original, la causa del rechazo y un identificador de
movimiento único. Mantener indicadores separados de dato faltante, inválido
e imputado permitirá corregir errores sin confundirlos con ceros o medianoches
válidas y dejará un historial auditable de la migración.
