"""
Funciones auxiliares y constantes compartidas por todos los módulos.

Acá vive todo lo que se reutiliza en más de un lugar: rutas del proyecto,
diccionarios de traducción, conversión de montos y guardado de archivos.
"""

from pathlib import Path

import pandas as pd

# --- Rutas del proyecto -------------------------------------------------------
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DATOS_CRUDOS = RAIZ_PROYECTO / "data" / "raw" / "ai_job_replacement_dirty.csv"
RUTA_DATOS_LIMPIOS = RAIZ_PROYECTO / "data" / "processed" / "ai_job_replacement_limpio.csv"
CARPETA_TABLAS = RAIZ_PROYECTO / "outputs" / "tablas"
CARPETA_FIGURAS = RAIZ_PROYECTO / "outputs" / "figuras"

# Sector asignado al Grupo 1 (valor ya traducido al español).
SECTOR_ASIGNADO = "Tecnología"

# --- Normalización al español -------------------------------------------------
# Columnas: minúsculas, sin espacios y sin tildes (contrato del equipo).
TRADUCCION_COLUMNAS = {
    "job_id": "id_registro",
    "job_role": "puesto",
    "industry": "industria",
    "country": "pais",
    "year": "anio",
    "automation_risk_percent": "riesgo_automatizacion_pct",
    "ai_replacement_score": "puntaje_reemplazo_ia",
    "skill_gap_index": "indice_brecha_habilidades",
    "salary_before_usd": "salario_antes_usd",
    "salary_after_usd": "salario_despues_usd",
    "salary_change_percent": "cambio_salarial_pct",
    "skill_demand_growth_percent": "crecimiento_demanda_habilidades_pct",
    "remote_feasibility_score": "factibilidad_remota",
    "ai_adoption_level": "nivel_adopcion_ia",
    "education_requirement_level": "nivel_educativo_requerido",
    "automation_risk_category": "categoria_riesgo",
    "skill_transition_pressure": "presion_reconversion",
    "wage_volatility_index": "indice_volatilidad_salarial",
    "reskilling_urgency_score": "urgencia_recapacitacion",
    "ai_disruption_intensity": "intensidad_disrupcion_ia",
}

TRADUCCION_VALORES = {
    "puesto": {
        "Accountant": "Contador/a",
        "Customer Support Rep": "Atención al Cliente",
        "Data Analyst": "Analista de Datos",
        "Financial Analyst": "Analista Financiero/a",
        "HR Manager": "Gerente de RR.HH.",
        "Marketing Specialist": "Especialista en Marketing",
        "Mechanical Engineer": "Ingeniero/a Mecánico/a",
        "Software Engineer": "Ingeniero/a de Software",
        "Teacher": "Docente",
        "Truck Driver": "Camionero/a",
    },
    "industria": {
        "Education": "Educación",
        "Energy": "Energía",
        "Finance": "Finanzas",
        "Healthcare": "Salud",
        "Manufacturing": "Manufactura",
        "Retail": "Comercio Minorista",
        "Technology": "Tecnología",
        "Transportation": "Transporte",
        "Unknown": "Sin dato",
    },
    "pais": {
        "Australia": "Australia",
        "Brazil": "Brasil",
        "Canada": "Canadá",
        "Germany": "Alemania",
        "India": "India",
        "Japan": "Japón",
        "Singapore": "Singapur",
        "UK": "Reino Unido",
        "USA": "Estados Unidos",
    },
    "categoria_riesgo": {"Low": "Bajo", "Medium": "Medio", "High": "Alto"},
}

ORDEN_CATEGORIA_RIESGO = ["Bajo", "Medio", "Alto"]

# Umbrales de la categoría de riesgo inferidos del propio dataset
# (Low: [0, 30), Medium: [30, 60), High: [60, 100]).
UMBRALES_RIESGO = [0, 30, 60, 100.01]


def convertir_monto_a_float(serie):
    """
    Convierte una Serie de montos con formato de texto a números.

    Acepta valores como "$32,820.29", "32820.29" o vacíos.

    Parámetros:
    -----------
    serie : pd.Series
        Columna con montos (texto o números mezclados).

    Retorna:
    --------
    pd.Series
        Serie float; lo que no se pueda convertir queda como NaN.
    """
    texto_limpio = serie.astype("string").str.replace(r"[\$,\s]", "", regex=True)
    return pd.to_numeric(texto_limpio, errors="coerce")


def resumen_estadistico(serie):
    """
    Devuelve las medidas descriptivas básicas de una Serie numérica.

    Parámetros:
    -----------
    serie : pd.Series
        Columna numérica.

    Retorna:
    --------
    dict
        media, desvío, mediana, mínimo, máximo y coeficiente de variación (%).
    """
    media = serie.mean()
    desvio = serie.std()
    return {
        "media": media,
        "desvio": desvio,
        "mediana": serie.median(),
        "minimo": serie.min(),
        "maximo": serie.max(),
        "coef_variacion_pct": desvio / media * 100,
    }


def registrar_paso(bitacora, paso, filas_afectadas, justificacion):
    """
    Agrega una entrada a la bitácora de saneamiento (sin modificar el original).

    Parámetros:
    -----------
    bitacora : list[dict]
        Bitácora acumulada hasta el momento.
    paso : str
        Nombre corto del paso de limpieza.
    filas_afectadas : int
        Cantidad de registros modificados o eliminados.
    justificacion : str
        Motivo técnico de la decisión.

    Retorna:
    --------
    list[dict]
        Nueva bitácora con la entrada agregada.
    """
    entrada = {"paso": paso, "filas_afectadas": int(filas_afectadas), "justificacion": justificacion}
    return bitacora + [entrada]


def guardar_tabla(df, nombre_archivo, carpeta=CARPETA_TABLAS):
    """
    Guarda un DataFrame como CSV (UTF-8 con BOM para que Excel respete las tildes).

    Parámetros:
    -----------
    df : pd.DataFrame
        Tabla a guardar.
    nombre_archivo : str
        Nombre del archivo, por ejemplo "auditoria.csv".
    carpeta : Path
        Carpeta destino (se crea si no existe).

    Retorna:
    --------
    Path
        Ruta completa del archivo guardado.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    return ruta
