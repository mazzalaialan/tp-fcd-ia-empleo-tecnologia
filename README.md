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
│   └── processed/               # Dataset limpio generado por el pipeline (no se sube a git)
│       └── ai_job_replacement_limpio.csv
│
├── src/                         # Código fuente
│   ├── load_data.py             # Carga y filtro del sector Tecnología
│   ├── audit.py                 # Auditoría de calidad: solo diagnostica, no modifica los datos
│   ├── clean_data.py            # Protocolo de curación + verificación del dataset limpio
│   ├── bitacora.py              # Bitácora compartida: cada paso de limpieza queda registrado
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

En Windows, sin activar el entorno virtual: `venv\Scripts\python.exe main.py`

El pipeline:

1. **Carga** el CSV crudo y se queda con los registros de Tecnología.
2. **Audita** la calidad de los datos y guarda las tablas en `outputs/tablas/`. No modifica nada.
3. **Limpia** los datos y registra cada decisión en la bitácora.
4. **Verifica** el dataset limpio y lo guarda en `data/processed/`.
5. **Analiza** el sector y guarda las tablas en `outputs/tablas/`.
6. **Grafica** y guarda los PNG en `outputs/figuras/`.

`data/processed/` está en `.gitignore`: el CSV limpio no se sube al repositorio. Cada integrante lo genera al ejecutar `main.py`.

## Resultados

La auditoría, la bitácora de saneamiento con la justificación de cada decisión, el análisis y la reflexión crítica
están en el [informe](docs/informe_tp.md).

## Integrantes y responsabilidades

| Integrante | Fase | Módulos |
|---|---|---|
| _(completar)_ | 1. Entendimiento | README.md |
| _Santiago Vega_ | 2. Carga, auditoría y limpieza | `load_data.py`, `audit.py`, `clean_data.py`, `bitacora.py` |
| _(completar)_ | 3. Análisis | `analysis.py` |
| _(completar)_ | 4. Visualización | `visualization.py` |
| _(completar)_ | 5. Integración | `main.py`, `utils.py` |
| _(completar)_ | 6. Documentación | `docs/informe_tp.md` |
