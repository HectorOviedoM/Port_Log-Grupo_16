# Conclusión — Port Log, Integración de los tres sprints

## Alcance y problema que resuelve

El sistema desarrollado integra un pipeline de procesamiento de datos portuarios que abarca la limpieza y transformación de registros, su vinculación con evidencias fotográficas, el almacenamiento relacional, la consulta de información operativa y la recuperación de buques mediante similitud visual. De esta manera, permite explorar cómo combinar datos tabulares e imágenes para analizar infracciones, consultar antecedentes y facilitar la identificación de embarcaciones.

Los resultados obtenidos muestran la utilidad potencial de integrar ambas fuentes. En el Sprint 1, de los 1500 movimientos originales se conservaron 447 registros infractores para el análisis. En el Sprint 2, se logró asociar evidencia visual a 431 de esas infracciones, alcanzando una cobertura del 96,42 % según el criterio de coincidencia utilizado. Sin embargo, estos resultados deben interpretarse dentro de las características del dataset y de las limitaciones de los procedimientos de limpieza y matching implementados.

## Aporte de la base vectorial frente al OCR

El OCR permite extraer texto de las imágenes y contrastar las matrículas reconocidas con los registros tabulares. Su efectividad depende de la calidad de las capturas, la legibilidad de los caracteres y la correcta normalización de las matrículas.

La búsqueda vectorial mediante embeddings de OpenCLIP incorpora una estrategia complementaria: permite recuperar imágenes visualmente similares sin depender exclusivamente de una lectura textual correcta. Esto puede resultar útil cuando la matrícula no es legible o cuando se necesita localizar un buque a partir de una fotografía general.

No obstante, la similitud visual no garantiza la identidad de una embarcación. Por este motivo, tanto el OCR como la búsqueda vectorial deberían considerarse herramientas de asistencia para la identificación y verificación, en lugar de mecanismos infalibles. Una mejora concreta sería conservar una medida numérica de confianza para cada resultado y establecer umbrales que determinen cuándo aceptar una coincidencia como suficientemente confiable y cuándo derivarla a revisión humana. La búsqueda vectorial podría utilizarse para proponer candidatos y reducir el trabajo manual, sin reemplazar la validación de los casos dudosos.

## Principales limitaciones

Una de las principales limitaciones del sistema es su dependencia de la calidad y consistencia de los datos de entrada. Aunque los datos originales y los normalizados se mantienen separados, algunas inconsistencias de etapas anteriores no fueron corregidas completamente y se propagaron hacia las etapas posteriores. Por ejemplo, las diferencias en la normalización de matrículas pueden hacer que una misma embarcación quede representada mediante valores distintos, afectando las relaciones y las consultas.

Esto también evidencia una dificultad de modelado: antes de definir las entidades y sus relaciones es necesario comprender con mayor precisión qué representa cada identificador y cuáles son las reglas del dominio. En particular, la relación entre `buque_id` y `matricula` requiere una definición clara para determinar cómo identificar una embarcación de manera estable y cómo resolver posibles discrepancias entre los registros.

Por otra parte, los resultados del OCR y de la búsqueda vectorial dependen de la calidad de las imágenes y de los criterios de coincidencia utilizados. Los porcentajes obtenidos sobre el conjunto disponible no garantizan el mismo desempeño ante nuevas capturas o condiciones operativas diferentes. Asimismo, la incorporación de SQLAlchemy, DVC, Supabase y ChromaDB permite trabajar con distintas tecnologías de persistencia y recuperación, pero su utilidad debe evaluarse en función de las necesidades concretas del sistema y de la complejidad que introduce cada componente.

## Propuesta para una implementación real

Para llevar el sistema a un entorno operativo en el Puerto de Rosario, el primer paso sería profundizar el relevamiento del dominio portuario junto con las personas responsables de los procesos. Esto permitiría definir con precisión las entidades, sus identificadores, las relaciones entre movimientos y embarcaciones, y las reglas que deben cumplirse al registrar o corregir información. A partir de ese conocimiento, se podría revisar el modelo de datos y establecer restricciones de integridad y validaciones consistentes desde el ingreso.

También reforzaría el proceso de normalización para garantizar que una misma entidad se represente de manera uniforme en todas las etapas, manteniendo los valores originales y la trazabilidad de las correcciones. Las imputaciones y los datos dudosos deberían quedar identificados explícitamente para evitar que se interpreten como observaciones verificadas.

En cuanto a la identificación visual, mantendría el OCR y la búsqueda vectorial como mecanismos complementarios de asistencia. El sistema podría calcular y conservar medidas de confianza, recuperar candidatos y derivar los casos que no superen determinados umbrales a una instancia de revisión humana. Para establecer esos umbrales sería necesario evaluar ambos mecanismos con datos representativos y medir sus errores, en lugar de asumir que los resultados obtenidos durante el desarrollo se mantendrán en producción.

Finalmente, revisaría las decisiones de arquitectura a partir de los requisitos reales del proyecto, priorizando un modelo de dominio explícito, reglas de negocio centralizadas y una implementación mantenible. Esto podría incluir el uso de un lenguaje de tipado estático fuerte y la reducción de abstracciones o código repetitivo que no aporten valor, siempre que esas decisiones resulten adecuadas para el equipo y el contexto de operación.

En conclusión, los tres sprints permitieron integrar técnicas de limpieza de datos, procesamiento de imágenes, almacenamiento relacional y búsqueda vectorial en una solución que aborda un problema concreto. El trabajo también mostró que la viabilidad técnica de integrar estas herramientas no garantiza, por sí sola, la confiabilidad de los resultados. Para avanzar hacia una implementación real, sería necesario profundizar el conocimiento del dominio, consolidar las reglas de identificación de las entidades y validar los mecanismos de asistencia visual con datos representativos. Sobre esa base, las tecnologías utilizadas podrían formar parte de una solución más consistente, mantenible y adecuada para las necesidades operativas del puerto.
