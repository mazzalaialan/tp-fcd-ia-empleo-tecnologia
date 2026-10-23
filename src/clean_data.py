import numpy as np
import pandas as pd

from src.bitacora import registrar_paso

from src.utils import (
    ORDEN_CATEGORIA_RIESGO,
    TRADUCCION_COLUMNAS,
    TRADUCCION_VALORES,
    UMBRALES_RIESGO,
    convertir_monto_a_float,
)


# formato

def estandarizar_nombres_columnas(df):
    """paso los nombres de columnas a minúsculas y sin espacios en los extremos"""
    df = df.copy()
    df.columns = df.columns.str.lower().str.strip()
    return df


def eliminar_duplicados(df):
    """elimino las filas duplicadas exactas y conservo la primera aparición"""
    return df.drop_duplicates(keep="first")


def normalizar_texto_categorico(df, columna):
    """quito los espacios de los extremos y unifico las mayúsculas (formato título)"""
    df = df.copy()
    df[columna] = df[columna].str.strip().str.title()
    return df


def convertir_columnas_monto(df, columnas):
    """convierto las columnas de montos con formato texto ("$1,234.5") a float"""
    df = df.copy()
    for columna in columnas:
        df[columna] = convertir_monto_a_float(df[columna])
    return df


def convertir_anio_a_entero(df):
    """convierto el año ("2021" o "2021.0") a entero"""
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"]).astype(int)
    return df


# inconsistencias lógicas y de negocio

def calcular_salario_despues_esperado(df):
    """calculo el salario posterior coherente con los datos base: antes * (1 + cambio%/100)"""
    return df["salary_before_usd"] * (1 + df["salary_change_percent"] / 100)


def detectar_salarios_atipicos(df):
    """
    detecto los salarios posteriores por encima del límite superior de la regla del iqr (tukey):
    q3 + 1.5 * iqr.
    """
    salario = df["salary_after_usd"]

    # calculo el límite igual que en la auditoría; los nulos quedan como falso al comparar
    q1 = salario.quantile(0.25)
    q3 = salario.quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr
    return salario > limite_superior


def anular_salarios_atipicos(df, mascara):
    """dejo en nulo los salarios posteriores marcados, para recalcularlos después con la fórmula."""
    df = df.copy()
    df.loc[mascara, "salary_after_usd"] = np.nan
    return df


def detectar_contradiccion_salarial(df):
    """
    detecto los registros donde salario antes == después pero el % de cambio no es 0
    los tres campos (antes, después, cambio%) no pueden ser ciertos a la vez.
    """
    iguales = np.isclose(df["salary_before_usd"], df["salary_after_usd"])
    return iguales & (df["salary_change_percent"] != 0)


def eliminar_filas(df, mascara):
    """elimino las filas marcadas en `mascara`."""
    return df[~mascara]


def recalcular_categoria_riesgo(df):
    """recalculo low/medium/high a partir del % de riesgo con los umbrales 30/60"""
    df = df.copy()
    df["automation_risk_category"] = pd.cut(
        df["automation_risk_percent"], bins=UMBRALES_RIESGO,
        labels=["Low", "Medium", "High"], right=False,
    ).astype(str)
    return df


def recortar_a_rango(df, columna, minimo, maximo):
    """acoto los valores de una columna al rango [minimo, maximo]."""
    df = df.copy()
    df[columna] = df[columna].clip(lower=minimo, upper=maximo)
    return df


# recuperación de faltantes

def recuperar_salario_antes(df):
    """reconstruyo salary_before faltante despejándolo de: después / (1 + cambio%/100)"""
    df = df.copy()
    faltante = df["salary_before_usd"].isna()
    recuperado = df["salary_after_usd"] / (1 + df["salary_change_percent"] / 100)
    df.loc[faltante, "salary_before_usd"] = recuperado[faltante].round(2)
    return df


def recuperar_salario_despues(df):
    """reconstruyo salary_after faltante con: antes * (1 + cambio%/100)"""
    df = df.copy()
    faltante = df["salary_after_usd"].isna()
    df.loc[faltante, "salary_after_usd"] = calcular_salario_despues_esperado(df)[faltante].round(2)
    return df


def recuperar_riesgo_automatizacion(df):
    """
    reconstruyo automation_risk_percent faltante usando la identidad verificada
    en el 100% de los registros completos:
        skill_transition_pressure = (skill_gap_index + automation_risk_percent) / 2
    """
    df = df.copy()
    faltante = df["automation_risk_percent"].isna()
    recuperado = 2 * df["skill_transition_pressure"] - df["skill_gap_index"]
    df.loc[faltante, "automation_risk_percent"] = recuperado[faltante].round(2)
    return df


def imputar_nulos(df, columna, valor):
    """relleno los nulos de una columna con un valor fijo."""
    df = df.copy()
    df[columna] = df[columna].fillna(valor)
    return df


# normalización al español

def traducir_columnas(df):
    """renombro las columnas al español (minúsculas, sin tildes ni espacios)"""
    return df.rename(columns=TRADUCCION_COLUMNAS)


def traducir_valores_categoricos(df):
    """traduzco al español los valores de puesto, industria, país y categoría de riesgo"""
    df = df.copy()
    for columna, traduccion in TRADUCCION_VALORES.items():
        df[columna] = df[columna].map(traduccion)
    return df


def asignar_tipos(df):
    """
    aplico el contrato de tipos: categóricos como `category`, la categoría de
    riesgo como categórica ordenada, numéricos como float y enteros donde corresponde
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


# etapas que agrupan los pasos

def etapa_formato(df):
    """etapa 1: elimino duplicados, normalizo el texto y convierto montos y año"""
    df = estandarizar_nombres_columnas(df)

    # elimino los duplicados primero, así el conteo coincide con el de la auditoría
    cantidad = df.duplicated().sum()
    df = eliminar_duplicados(df)
    registrar_paso("Eliminar duplicados exactos", cantidad,
                   "Registros idénticos (incluido job_id) inflan conteos y sesgan medias.")

    cambios = (df["industry"].dropna() != df["industry"].dropna().str.strip().str.title()).sum()
    df = normalizar_texto_categorico(df, "industry")
    registrar_paso("Normalizar escritura de 'industry'", cambios,
                   "Variantes como ' Technology ', 'TECHNOLOGY' o 'technology' son la misma categoría.")

    # cuento los montos con "$" en las dos columnas antes de convertirlos
    cantidad = df["salary_before_usd"].astype(str).str.contains(r"\$").sum() + \
        df["salary_after_usd"].astype(str).str.contains(r"\$").sum()
    df = convertir_columnas_monto(df, ["salary_before_usd", "salary_after_usd"])
    registrar_paso("Castear salarios a float", cantidad,
                   "Montos guardados como texto ('$32,820.29') impiden operar numéricamente.")

    cantidad = df["year"].str.contains(r"\.").sum()
    df = convertir_anio_a_entero(df)
    registrar_paso("Castear año a entero", cantidad,
                   "El año es una variable discreta; '2021.0' y '2021' deben ser el mismo valor.")
    return df


def etapa_inconsistencias(df):
    """etapa 2: anulo salarios atípicos, elimino contradicciones y acoto rangos"""
    # no corrijo el valor a mano: lo dejo nulo y lo recupero con la fórmula en la etapa de faltantes,
    # que es el mismo criterio que uso con el resto de los salarios
    mascara = detectar_salarios_atipicos(df)
    df = anular_salarios_atipicos(df, mascara)
    registrar_paso("Anular salario posterior atípico (se recalcula por fórmula)", mascara.sum(),
                   "Supera el límite superior de la regla del IQR y resulta unas 10 veces el esperado según salario "
                   "previo y % de cambio: error de carga. Se anula y se recupera con la fórmula, como los demás salarios.")

    # elimino estas filas porque el % de cambio vale 5.0 en todas y wage_volatility_index, que en el resto del
    # dataset coincide con |cambio|, no coincide: no sé cuál de los campos es el verdadero
    mascara = detectar_contradiccion_salarial(df)
    df = eliminar_filas(df, mascara)
    registrar_paso("Eliminar contradicción salarial (antes = después con cambio != 0)", mascara.sum(),
                   "No se puede saber qué campo es el verdadero; además el índice de volatilidad tampoco coincide.")

    cantidad = (df["ai_replacement_score"] > 100).sum()
    df = recortar_a_rango(df, "ai_replacement_score", 0, 100)
    registrar_paso("Acotar ai_replacement_score a [0, 100]", cantidad,
                   "Es un puntaje en escala 0-100 (igual que el riesgo); valores > 100 son ruido fuera de escala.")
    return df


def etapa_faltantes(df):
    """etapa 3: recupero los nulos con fórmulas y imputo los que quedan"""
    # primero uso las fórmulas, porque son exactas y no dependen de ningún supuesto estadístico
    cantidad = (df["salary_before_usd"].isna() & df["salary_after_usd"].notna()).sum()
    df = recuperar_salario_antes(df)
    registrar_paso("Recuperar salario previo por fórmula", cantidad,
                   "salary_change_percent es completo: antes = después / (1 + cambio%/100). Valor exacto, no estimado.")

    cantidad = (df["salary_after_usd"].isna() & df["salary_before_usd"].notna()).sum()
    df = recuperar_salario_despues(df)
    registrar_paso("Recuperar salario posterior por fórmula", cantidad,
                   "después = antes * (1 + cambio%/100). Valor exacto, no estimado. Incluye el salario anulado por atípico.")

    # los salarios previos que siguen vacíos son de filas sin ningún salario, así que la fórmula no sirve;
    # imputo la media porque ninguna otra columna predice el salario mejor que la media
    cantidad = df["salary_before_usd"].isna().sum()
    media = round(df["salary_before_usd"].mean(), 2)
    df = imputar_nulos(df, "salary_before_usd", media)
    registrar_paso("Imputar salario previo con la media (registros sin ningún salario)", cantidad,
                   "Sin ningún salario la fórmula no aplica. La regresión lineal con las demás columnas tiene un R² de "
                   "predicción cercano a 0 y no mejora a la media; se imputa la media de la columna.")

    # con el salario previo ya imputado, el posterior vuelve a salir de la fórmula
    cantidad = df["salary_after_usd"].isna().sum()
    df = recuperar_salario_despues(df)
    registrar_paso("Recuperar salario posterior por fórmula sobre el salario imputado", cantidad,
                   "después = antes * (1 + cambio%/100) con el salario previo estimado; mantiene la coherencia con el % de cambio.")

    cantidad = df["automation_risk_percent"].isna().sum()
    df = recuperar_riesgo_automatizacion(df)
    registrar_paso("Recuperar riesgo de automatización por fórmula", cantidad,
                   "Identidad verificada en el 100% de filas completas: presión = (brecha + riesgo) / 2.")

    categoria_anterior = df["automation_risk_category"]
    df = recalcular_categoria_riesgo(df)
    registrar_paso("Recalcular categoría de riesgo (umbrales 30/60)",
                   (categoria_anterior != df["automation_risk_category"]).sum(),
                   "Garantiza coherencia entre el % de riesgo y su categoría Low/Medium/High.")
    return df


def etapa_normalizacion(df):
    """etapa 4: traduzco al español y asigno los tipos"""
    df = traducir_columnas(df)
    df = traducir_valores_categoricos(df)
    df = asignar_tipos(df)

    registrar_paso("Traducir al español y asignar tipos", len(df),
                   "Lectura fluida en español; categóricos como 'category', numéricos como float, índice reseteado.")
    return df


def verificar_dataset_limpio(df):
    """
    verifico que el dataset esté limpio y se pueda seguir trabajando con el después
    """

    assert all(c == c.lower() and " " not in c for c in df.columns), "Columnas deben ser minúsculas y sin espacios"
    assert df.isnull().sum().sum() == 0, "No debe haber nulos"
    assert not df["id_registro"].duplicated().any(), "id_registro debe ser único"
    assert df.index.equals(pd.RangeIndex(len(df))), "El índice debe estar reseteado"
    esperado = df["salario_antes_usd"] * (1 + df["cambio_salarial_pct"] / 100)
    assert np.allclose(df["salario_despues_usd"], esperado, rtol=0.001), "Salarios incoherentes con el % de cambio"


def limpiar_dataframe(df):
    """
    ejecuto cada etapa en orden y devuelvo el dataset limpio y validado
    cada paso queda anotado en la bitácora.
    """
    df = etapa_formato(df)
    df = etapa_inconsistencias(df)
    df = etapa_faltantes(df)
    df = etapa_normalizacion(df)
    verificar_dataset_limpio(df)
    return df