# Trabajo Práctico: Impacto de la IA en el Empleo (2020-2026)

## Sector Asignado: Tecnología (Technology)

### 1\. Introducción Académica

El avance de la Inteligencia Artificial no es solo un fenómeno técnico, sino una fuerza socioeconómica que está redefiniendo la naturaleza del trabajo. En los próximos años, diversos sectores experimentarán cambios sin precedentes en sus estructuras salariales, demandas de habilidades y estabilidad laboral. Este Trabajo Práctico propone analizar estas tendencias con rigor científico y pensamiento crítico.

### 2\. Ficha del Proyecto: Grupo 1

* **Sector**: Tecnología.  
* **Objetivo General**: Evaluar la dinámica salarial y los roles críticos dentro del ecosistema tecnológico, determinando el grado de vulnerabilidad de los perfiles técnicos frente a la automatización.

### 3\. Fase I: Diagnóstico y Saneamiento (Caja Negra)

Ustedes trabajarán con la fuente de datos `ai_job_replacement_dirty.csv`. **Advertencia**: La fuente posee anomalías estructuradas.

- **Auditoría de Calidad**: Realicen un reporte inicial sobre el estado de la información. Deben identificar inconsistencias lógicas, errores de formato y vacíos de datos sin guía externa.  
- **Protocolo de Curación**: Implementen y documenten un proceso sistemático de limpieza. Cada decisión (casteo de tipos, manejo de nulos, eliminación de duplicados) debe estar técnicamente justificada en su bitácora.  
- **Normalización**: Traduzcan y estandaricen los campos para asegurar una lectura fluida en español.

### 4\. Fase II: Análisis Estadístico y Exploratorio (EDA)

Utilizando las librerías Pandas y NumPy, resuelvan las siguientes problemáticas:

- **Distribución Salarial**: Calculen la media y desviación estándar de los salarios pre y post IA. ¿Se observa una polarización en el sector?  
- **Grado de Vulnerabilidad**: Identifiquen los 3 roles con mayor riesgo de reemplazo y analicen su relación con el nivel educativo.  
- **Inconsistencias de Negocio**: Identifiquen y traten registros que presenten contradicciones (ej: cambios salariales que no coinciden con los datos base).

### 5\. Fase III: Visualización y Comunicación

Diseñen las siguientes piezas utilizando Matplotlib:

- **Histograma de Riesgo**: Distribución del riesgo de automatización en tecnología, incluyendo líneas de tendencia (media/mediana).  
- **Gráfico Comparativo**: Gráfico de barras que muestre el cambio porcentual salarial por puesto de trabajo.  
- **Gráfico de Dispersión**: Relación entre la urgencia de re-capacitación y la intensidad de disrupción.

### 6\. Fase IV: Reflexión Crítica (Anti-LLM)

*Responda basándose estrictamente en los hallazgos de su procesamiento de datos:*

- ¿Qué perfil tecnológico parece ser más "resiliente" según los datos analizados?  
- Si tuviera que asesorar a un gremio de trabajadores tecnológicos basándose en este dataset, ¿qué 3 recomendaciones estratégicas daría para los próximos 3 años?

### 7\. Requerimientos de Entrega y Defensa

1. **Informe Profesional**: PDF o Markdown con resumen ejecutivo, bitácora de saneamiento e interpretación de resultados.  
2. **Código Fuente**: Script o Notebook estructurado, comentado y reproducible.  
3. **Defensa Oral**: Justificación técnica de la limpieza e interpretación de las visualizaciones ante el curso.

&nbsp;