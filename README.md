# Impacto de la IA en el Empleo (2020-2026) — Sector Tecnología

Trabajo Práctico de **Fundamentos para la Ciencia de Datos** — Grupo 1.

El proyecto audita, limpia y analiza el dataset `ai_job_replacement_dirty.csv` para evaluar la
dinámica salarial y la vulnerabilidad de los puestos del sector **Tecnología** frente a la automatización.
Todo el proceso corre de punta a punta con un solo comando y es reproducible.

## Estructura del proyecto

```
mi_proyecto/
│
├── data/
│   ├── raw/                     # Dataset original (no se modifica nunca)
│   │   └── ai_job_replacement_dirty.csv
│   └── processed/               # Dataset limpio generado por el pipeline
│       └── ai_job_replacement_limpio.csv
│
├── src/                         # Código fuente
│   ├── load_data.py             # Carga, validación de columnas y auditoría de calidad
│   ├── clean_data.py            # Protocolo de curación + bitácora + validación del contrato
│   ├── analysis.py              # Estadísticas descriptivas, rankings, correlaciones
│   ├── visualization.py         # Gráficos con Matplotlib
│   └── utils.py                 # Rutas, traducciones y funciones auxiliares reutilizables
│
├── outputs/                     # Generado por main.py
│   ├── tablas/                  # Auditoría, bitácora y resultados del análisis (CSV)
│   └── figuras/                 # Gráficos (PNG)
│
├── docs/
│   ├── consigna_grupo_1.md                          # Enunciado del TP
│   ├── diccionario_variables_ai_job_replacement.pdf # Diccionario de variables
│   └── informe_tp.md                                # Informe final
│
├── main.py                      # Orquestador: une todo
├── requirements.txt             # Dependencias
└── README.md
```

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## Ejecución

Desde la carpeta raíz del proyecto:

```bash
python main.py
```

El pipeline:

1. **Carga** `data/raw/ai_job_replacement_dirty.csv`, valida las columnas y genera la auditoría de calidad.
2. **Limpia** los datos (duplicados, formatos, nulos, inconsistencias, traducción al español) y registra cada decisión en la bitácora.
3. **Valida el contrato** (sin nulos, columnas en minúsculas, salarios coherentes, índice reseteado) y guarda el dataset limpio en `data/processed/`.
4. **Analiza** el sector Tecnología y guarda las tablas en `outputs/tablas/`.
5. **Grafica** y guarda los PNG en `outputs/figuras/`.

## Contrato de datos entre módulos

Lo que `clean_data.py` garantiza y `analysis.py` verifica antes de trabajar:

- Columnas en español, minúsculas, sin espacios ni tildes (`salario_antes_usd`, `riesgo_automatizacion_pct`, ...).
- Categóricos (`puesto`, `industria`, `pais`) como `category`; `categoria_riesgo` como categórica ordenada (Bajo < Medio < Alto).
- Numéricos como `float`; `id_registro`, `anio` y `nivel_educativo_requerido` como enteros.
- Sin nulos. Índice reseteado.
- `salario_despues_usd = salario_antes_usd * (1 + cambio_salarial_pct / 100)` en todas las filas.

## Resultados

El informe con resumen ejecutivo, bitácora de saneamiento, interpretación de resultados y reflexión crítica
está en [docs/informe_tp.md](docs/informe_tp.md).

## Integrantes y responsabilidades

| Integrante | Fase | Módulos |
|---|---|---|
| _(completar)_ | 1. Entendimiento | README.md |
| _(completar)_ | 2. Carga y limpieza | `load_data.py`, `clean_data.py` |
| _(completar)_ | 3. Análisis | `analysis.py` |
| _(completar)_ | 4. Visualización | `visualization.py` |
| _(completar)_ | 5. Integración | `main.py`, `utils.py` |
| _(completar)_ | 6. Documentación | `docs/informe_tp.md` |
