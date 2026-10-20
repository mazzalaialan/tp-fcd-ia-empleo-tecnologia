"""
Carga y validación del dataset crudo.

Incluye la Auditoría de Calidad (Fase I): un diagnóstico del estado de los
datos ANTES de tocarlos, para justificar cada decisión de limpieza.
"""

import pandas as pd

from src.utils import convertir_monto_a_float

COLUMNAS_ESPERADAS = [
    "job_id", "job_role", "industry", "country", "year",
    "automation_risk_percent", "ai_replacement_score", "skill_gap_index",
    "salary_before_usd", "salary_after_usd", "salary_change_percent",
    "skill_demand_growth_percent", "remote_feasibility_score",
    "ai_adoption_level", "education_requirement_level",
    "automation_risk_category", "skill_transition_pressure",
    "wage_volatility_index", "reskilling_urgency_score", "ai_disruption_intensity",
]

COLUMNAS_SALARIO = ["salary_before_usd", "salary_after_usd"]
COLUMNAS_SCORE_0_100 = [
    "automation_risk_percent", "ai_replacement_score", "skill_gap_index",
    "remote_feasibility_score", "ai_adoption_level",
]


def cargar_dataset(ruta):
    """
    Lee el CSV crudo y valida que tenga las columnas del diccionario.

    Parámetros:
    -----------
    ruta : str o Path
        Ruta al archivo CSV.

    Retorna:
    --------
    pd.DataFrame
        Datos tal cual vienen en el archivo (sin limpiar).
    """
    # "year" se lee como texto para poder auditar su formato original ("2021" vs "2021.0").
    df = pd.read_csv(ruta, dtype={"year": "string"})
    validar_columnas_esperadas(df)
    return df


def validar_columnas_esperadas(df):
    """
    Verifica que el DataFrame tenga exactamente las columnas del diccionario.

    Parámetros:
    -----------
    df : pd.DataFrame
        Datos recién cargados.

    Lanza:
    ------
    ValueError
        Si faltan columnas o aparecen columnas desconocidas.
    """
    faltantes = set(COLUMNAS_ESPERADAS) - set(df.columns)
    sobrantes = set(df.columns) - set(COLUMNAS_ESPERADAS)
    if faltantes or sobrantes:
        raise ValueError(f"Columnas faltantes: {faltantes} | sobrantes: {sobrantes}")


# --- Auditoría de calidad ------------------------------------------------------

def contar_nulos_por_columna(df):
    """Devuelve una Serie con la cantidad de nulos de cada columna (solo las que tienen)."""
    nulos = df.isnull().sum()
    return nulos[nulos > 0]


def contar_variantes_texto(df, columna):
    """
    Analiza las escrituras distintas de una columna de texto.

    Retorna:
    --------
    tuple[int, int, int]
        (variantes_originales, categorias_reales, filas_mal_escritas)
        Una fila está "mal escrita" si difiere de su versión sin espacios
        extremos y en Formato Título (ej. " Technology " o "TECHNOLOGY").
    """
    valores = df[columna].dropna()
    normalizados = valores.str.strip().str.title()
    filas_mal_escritas = int((valores != normalizados).sum())
    return valores.nunique(), normalizados.nunique(), filas_mal_escritas


def contar_montos_con_formato_texto(df, columna):
    """Cuenta los montos escritos como texto (ej. "$32,820.29") que no son números directos."""
    valores = df[columna].dropna().astype(str)
    return int(valores.str.contains(r"[\$,]", regex=True).sum())


def contar_anios_con_decimales(df):
    """Cuenta los años guardados con formato decimal (ej. "2021.0")."""
    return int(df["year"].astype(str).str.contains(r"\.", regex=True).sum())


def contar_fuera_de_rango(serie, minimo, maximo):
    """Cuenta los valores de una Serie numérica fuera del rango [minimo, maximo]."""
    return int(((serie < minimo) | (serie > maximo)).sum())


def contar_salarios_inconsistentes(df):
    """
    Cuenta registros donde el salario posterior NO coincide con
    salario_antes * (1 + cambio%/100), con tolerancia de 1 punto porcentual.
    """
    antes = convertir_monto_a_float(df["salary_before_usd"])
    despues = convertir_monto_a_float(df["salary_after_usd"])
    cambio_calculado = (despues - antes) / antes * 100
    diferencia = (cambio_calculado - df["salary_change_percent"]).abs()
    return int((diferencia > 1).sum())


def auditar_calidad(df):
    """
    Genera el reporte inicial de calidad del dataset crudo.

    Parámetros:
    -----------
    df : pd.DataFrame
        Dataset crudo (salida de cargar_dataset).

    Retorna:
    --------
    pd.DataFrame
        Una fila por hallazgo: tipo de problema, columna afectada y cantidad.
    """
    hallazgos = [("Filas duplicadas exactas", "todas", int(df.duplicated().sum()))]
    for columna, cantidad in contar_nulos_por_columna(df).items():
        hallazgos.append(("Valores nulos", columna, int(cantidad)))
    originales, categorias, mal_escritas = contar_variantes_texto(df, "industry")
    hallazgos.append((f"Escrituras inconsistentes ({originales} variantes para {categorias} categorías)",
                      "industry", mal_escritas))
    for columna in COLUMNAS_SALARIO:
        hallazgos.append(("Monto con formato texto ($ y comas)", columna,
                          contar_montos_con_formato_texto(df, columna)))
        hallazgos.append(("Salario negativo o cero (valor centinela)", columna,
                          contar_fuera_de_rango(convertir_monto_a_float(df[columna]), 1, float("inf"))))
    hallazgos.append(("Año con formato decimal", "year", contar_anios_con_decimales(df)))
    for columna in COLUMNAS_SCORE_0_100:
        hallazgos.append(("Score fuera del rango 0-100", columna, contar_fuera_de_rango(df[columna], 0, 100)))
    hallazgos.append(("Salario posterior no coincide con el % de cambio", "salary_after_usd",
                      contar_salarios_inconsistentes(df)))
    reporte = pd.DataFrame(hallazgos, columns=["problema", "columna", "cantidad"])
    return reporte[reporte["cantidad"] > 0].reset_index(drop=True)
