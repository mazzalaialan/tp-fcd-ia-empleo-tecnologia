"""
Protocolo de curación del dataset (Fase I).

Cada función hace UNA sola cosa: recibe un DataFrame y devuelve uno nuevo
(nunca modifica el original). Las funciones `detectar_*` devuelven una máscara
booleana con los registros problemáticos; las de tratamiento los corrigen.

`limpiar_dataframe` encadena todo y devuelve, además del DataFrame limpio,
la bitácora con cada decisión y su justificación técnica.
"""

import numpy as np
import pandas as pd

from src.utils import (
    ORDEN_CATEGORIA_RIESGO,
    TRADUCCION_COLUMNAS,
    TRADUCCION_VALORES,
    UMBRALES_RIESGO,
    convertir_monto_a_float,
    registrar_paso,
)

TOLERANCIA_FACTOR_10 = 0.01  # margen relativo para detectar salarios cargados x10


# --- 1. Formato -----------------------------------------------------------------

def estandarizar_nombres_columnas(df):
    """Pasa los nombres de columnas a minúsculas y sin espacios en los extremos."""
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()
    return df


def eliminar_duplicados(df):
    """Elimina filas duplicadas exactas, conservando la primera aparición."""
    return df.drop_duplicates(keep="first")


def normalizar_texto_categorico(df, columna):
    """Quita espacios en los extremos y unifica mayúsculas (Formato Título)."""
    df = df.copy()
    df[columna] = df[columna].str.strip().str.title()
    return df


def convertir_columnas_monto(df, columnas):
    """Convierte columnas de montos con formato texto ("$1,234.5") a float."""
    df = df.copy()
    for columna in columnas:
        df[columna] = convertir_monto_a_float(df[columna])
    return df


def convertir_anio_a_entero(df):
    """Convierte el año ("2021" o "2021.0") a entero."""
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"]).astype(int)
    return df


# --- 2. Inconsistencias lógicas y de negocio ------------------------------------

def detectar_salarios_centinela(df):
    """Detecta salarios previos imposibles (<= 0), como el valor centinela -99999."""
    return df["salary_before_usd"] <= 0


def reemplazar_por_nulo(df, columna, mascara):
    """Reemplaza por NaN los valores de `columna` marcados en `mascara`."""
    df = df.copy()
    df.loc[mascara, columna] = np.nan
    return df


def calcular_salario_despues_esperado(df):
    """Salario posterior coherente con los datos base: antes * (1 + cambio%/100)."""
    return df["salary_before_usd"] * (1 + df["salary_change_percent"] / 100)


def detectar_salarios_inflados_x10(df):
    """
    Detecta salarios posteriores que son exactamente 10 veces el valor esperado
    (error típico de carga: un dígito / coma decimal corrida).
    """
    ratio = df["salary_after_usd"] / calcular_salario_despues_esperado(df)
    return (ratio - 10).abs() < 10 * TOLERANCIA_FACTOR_10


def corregir_salarios_inflados(df, mascara):
    """Divide por 10 los salarios posteriores marcados como inflados."""
    df = df.copy()
    df.loc[mascara, "salary_after_usd"] = df.loc[mascara, "salary_after_usd"] / 10
    return df


def detectar_contradiccion_salarial(df):
    """
    Detecta registros donde salario antes == después pero el % de cambio no es 0.
    Los tres campos (antes, después, cambio%) no pueden ser ciertos a la vez.
    """
    iguales = np.isclose(df["salary_before_usd"], df["salary_after_usd"])
    return iguales & (df["salary_change_percent"] != 0)


def eliminar_filas(df, mascara):
    """Elimina las filas marcadas en `mascara`."""
    return df[~mascara]


def recalcular_categoria_riesgo(df):
    """Recalcula Low/Medium/High a partir del % de riesgo con los umbrales 30/60."""
    df = df.copy()
    df["automation_risk_category"] = pd.cut(
        df["automation_risk_percent"], bins=UMBRALES_RIESGO,
        labels=["Low", "Medium", "High"], right=False,
    ).astype(str)
    return df


def recortar_a_rango(df, columna, minimo, maximo):
    """Acota los valores de una columna al rango [minimo, maximo]."""
    df = df.copy()
    df[columna] = df[columna].clip(lower=minimo, upper=maximo)
    return df


# --- 3. Recuperación de faltantes -----------------------------------------------

def recuperar_salario_antes(df):
    """Reconstruye salary_before faltante despejándolo de: después / (1 + cambio%/100)."""
    df = df.copy()
    faltante = df["salary_before_usd"].isna()
    recuperado = df["salary_after_usd"] / (1 + df["salary_change_percent"] / 100)
    df.loc[faltante, "salary_before_usd"] = recuperado[faltante].round(2)
    return df


def recuperar_salario_despues(df):
    """Reconstruye salary_after faltante con: antes * (1 + cambio%/100)."""
    df = df.copy()
    faltante = df["salary_after_usd"].isna()
    df.loc[faltante, "salary_after_usd"] = calcular_salario_despues_esperado(df)[faltante].round(2)
    return df


def recuperar_riesgo_automatizacion(df):
    """
    Reconstruye automation_risk_percent faltante usando la identidad verificada
    en el 100% de los registros completos:
        skill_transition_pressure = (skill_gap_index + automation_risk_percent) / 2
    """
    df = df.copy()
    faltante = df["automation_risk_percent"].isna()
    recuperado = 2 * df["skill_transition_pressure"] - df["skill_gap_index"]
    df.loc[faltante, "automation_risk_percent"] = recuperado[faltante].round(2)
    return df


def imputar_nulos(df, columna, valor):
    """Rellena los nulos de una columna con un valor fijo."""
    df = df.copy()
    df[columna] = df[columna].fillna(valor)
    return df


# --- 4. Normalización al español ------------------------------------------------

def traducir_columnas(df):
    """Renombra las columnas al español (minúsculas, sin tildes ni espacios)."""
    return df.rename(columns=TRADUCCION_COLUMNAS)


def traducir_valores_categoricos(df):
    """Traduce al español los valores de puesto, industria, país y categoría de riesgo."""
    df = df.copy()
    for columna, traduccion in TRADUCCION_VALORES.items():
        df[columna] = df[columna].map(traduccion)
    return df


def asignar_tipos(df):
    """
    Aplica el contrato de tipos: categóricos como `category`, la categoría de
    riesgo como categórica ordenada, numéricos como float y enteros donde corresponde.
    """
    df = df.copy()
    for columna in ["puesto", "industria", "pais"]:
        df[columna] = df[columna].astype("category")
    df["categoria_riesgo"] = pd.Categorical(df["categoria_riesgo"], categories=ORDEN_CATEGORIA_RIESGO, ordered=True)
    enteros = ["id_registro", "anio", "nivel_educativo_requerido"]
    flotantes = df.select_dtypes("number").columns.difference(enteros)
    df[enteros] = df[enteros].astype(int)
    df[flotantes] = df[flotantes].astype(float)
    return df.reset_index(drop=True)


# --- Etapas que agrupan los pasos -----------------------------------------------

def etapa_formato(df, bitacora):
    """Etapa 1: duplicados, texto, montos y año. Devuelve (df, bitacora)."""
    df = estandarizar_nombres_columnas(df)
    cantidad = df.duplicated().sum()
    df = eliminar_duplicados(df)
    bitacora = registrar_paso(bitacora, "Eliminar duplicados exactos", cantidad,
                              "Registros idénticos (incluido job_id) inflan conteos y sesgan medias.")
    cambios = (df["industry"].dropna() != df["industry"].dropna().str.strip().str.title()).sum()
    df = normalizar_texto_categorico(df, "industry")
    bitacora = registrar_paso(bitacora, "Normalizar escritura de 'industry'", cambios,
                              "Variantes como ' Technology ', 'TECHNOLOGY' o 'technology' son la misma categoría.")
    cantidad = df["salary_before_usd"].astype(str).str.contains(r"\$").sum() + \
        df["salary_after_usd"].astype(str).str.contains(r"\$").sum()
    df = convertir_columnas_monto(df, ["salary_before_usd", "salary_after_usd"])
    bitacora = registrar_paso(bitacora, "Castear salarios a float", cantidad,
                              "Montos guardados como texto ('$32,820.29') impiden operar numéricamente.")
    cantidad = df["year"].str.contains(r"\.").sum()
    df = convertir_anio_a_entero(df)
    bitacora = registrar_paso(bitacora, "Castear año a entero", cantidad,
                              "El año es una variable discreta; '2021.0' y '2021' deben ser el mismo valor.")
    return df, bitacora


def etapa_inconsistencias(df, bitacora):
    """Etapa 2: centinelas, salarios x10, contradicciones y rangos. Devuelve (df, bitacora)."""
    mascara = detectar_salarios_centinela(df)
    df = reemplazar_por_nulo(df, "salary_before_usd", mascara)
    bitacora = registrar_paso(bitacora, "Salario previo centinela (-99999) -> nulo", mascara.sum(),
                              "Un salario negativo es imposible; se trata como faltante y se recupera luego por fórmula.")
    mascara = detectar_salarios_inflados_x10(df)
    df = corregir_salarios_inflados(df, mascara)
    bitacora = registrar_paso(bitacora, "Corregir salario posterior inflado x10", mascara.sum(),
                              "El valor es exactamente 10 veces el esperado según salario previo y % de cambio: error de carga.")
    mascara = detectar_contradiccion_salarial(df)
    df = eliminar_filas(df, mascara)
    bitacora = registrar_paso(bitacora, "Eliminar contradicción salarial (antes = después con cambio != 0)", mascara.sum(),
                              "No se puede saber qué campo es el verdadero; además el índice de volatilidad tampoco coincide.")
    cantidad = (df["ai_replacement_score"] > 100).sum()
    df = recortar_a_rango(df, "ai_replacement_score", 0, 100)
    bitacora = registrar_paso(bitacora, "Acotar ai_replacement_score a [0, 100]", cantidad,
                              "Es un puntaje en escala 0-100 (igual que el riesgo); valores > 100 son ruido fuera de escala.")
    return df, bitacora


def etapa_faltantes(df, bitacora):
    """Etapa 3: recuperación e imputación de nulos. Devuelve (df, bitacora)."""
    cantidad = (df["salary_before_usd"].isna() & df["salary_after_usd"].notna()).sum()
    df = recuperar_salario_antes(df)
    bitacora = registrar_paso(bitacora, "Recuperar salario previo por fórmula", cantidad,
                              "salary_change_percent es completo: antes = después / (1 + cambio%/100). Valor exacto, no estimado.")
    cantidad = (df["salary_after_usd"].isna() & df["salary_before_usd"].notna()).sum()
    df = recuperar_salario_despues(df)
    bitacora = registrar_paso(bitacora, "Recuperar salario posterior por fórmula", cantidad,
                              "después = antes * (1 + cambio%/100). Valor exacto, no estimado.")
    mascara = df["salary_before_usd"].isna() | df["salary_after_usd"].isna()
    df = eliminar_filas(df, mascara)
    bitacora = registrar_paso(bitacora, "Eliminar registros sin ningún salario", mascara.sum(),
                              "Sin ninguno de los dos salarios no hay base para reconstruirlos; imputar la media inventaría datos.")
    cantidad = df["automation_risk_percent"].isna().sum()
    df = recuperar_riesgo_automatizacion(df)
    bitacora = registrar_paso(bitacora, "Recuperar riesgo de automatización por fórmula", cantidad,
                              "Identidad verificada en el 100% de filas completas: presión = (brecha + riesgo) / 2.")
    categoria_anterior = df["automation_risk_category"]
    df = recalcular_categoria_riesgo(df)
    bitacora = registrar_paso(bitacora, "Recalcular categoría de riesgo (umbrales 30/60)",
                              (categoria_anterior != df["automation_risk_category"]).sum(),
                              "Garantiza coherencia entre el % de riesgo y su categoría Low/Medium/High.")
    cantidad = df["industry"].isna().sum()
    df = imputar_nulos(df, "industry", "Unknown")
    bitacora = registrar_paso(bitacora, "Imputar industria faltante como 'Sin dato'", cantidad,
                              "No es deducible de otras columnas; se conserva el registro para análisis globales y se excluye del sector.")
    return df, bitacora


def etapa_normalizacion(df, bitacora):
    """Etapa 4: traducción al español y contrato de tipos. Devuelve (df, bitacora)."""
    df = traducir_columnas(df)
    df = traducir_valores_categoricos(df)
    df = asignar_tipos(df)
    bitacora = registrar_paso(bitacora, "Traducir al español y asignar tipos", len(df),
                              "Lectura fluida en español; categóricos como 'category', numéricos como float, índice reseteado.")
    return df, bitacora


def validar_contrato(df):
    """
    Verifica el contrato del equipo antes de pasar los datos al análisis.

    Lanza:
    ------
    AssertionError
        Si alguna regla del contrato no se cumple.
    """
    assert all(c == c.lower() and " " not in c for c in df.columns), "Columnas deben ser minúsculas y sin espacios"
    assert df.isnull().sum().sum() == 0, "No debe haber nulos"
    assert not df["id_registro"].duplicated().any(), "id_registro debe ser único"
    assert df.index.equals(pd.RangeIndex(len(df))), "El índice debe estar reseteado"
    esperado = df["salario_antes_usd"] * (1 + df["cambio_salarial_pct"] / 100)
    assert np.allclose(df["salario_despues_usd"], esperado, rtol=0.001), "Salarios incoherentes con el % de cambio"


def limpiar_dataframe(df):
    """
    Ejecuta el protocolo de curación completo.

    Parámetros:
    -----------
    df : pd.DataFrame
        Dataset crudo (salida de cargar_dataset).

    Retorna:
    --------
    tuple[pd.DataFrame, pd.DataFrame]
        (dataset limpio y validado, bitácora de saneamiento)
    """
    bitacora = []
    df, bitacora = etapa_formato(df, bitacora)
    df, bitacora = etapa_inconsistencias(df, bitacora)
    df, bitacora = etapa_faltantes(df, bitacora)
    df, bitacora = etapa_normalizacion(df, bitacora)
    validar_contrato(df)
    return df, pd.DataFrame(bitacora)
