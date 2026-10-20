"""
Análisis estadístico y exploratorio (Fase II) con Pandas y NumPy.

Todas las funciones reciben el DataFrame limpio (ya traducido al español)
y devuelven tablas (DataFrames) o diccionarios; ninguna grafica ni guarda.
"""

import numpy as np
import pandas as pd

from src.utils import resumen_estadistico

UMBRAL_CAMBIO_RELEVANTE = 5  # % de cambio salarial a partir del cual se considera ganancia/pérdida


def validar_contrato_analisis(df):
    """Verifica que los datos cumplan el contrato antes de analizarlos."""
    assert all(c == c.lower() for c in df.columns), "Columnas deben ser minúsculas"
    assert df.isnull().sum().sum() == 0, "No debe haber nulos"


def filtrar_sector(df, sector):
    """
    Devuelve solo los registros de una industria, con el índice reseteado.

    Parámetros:
    -----------
    df : pd.DataFrame
        Dataset limpio completo.
    sector : str
        Nombre de la industria en español (ej. "Tecnología").
    """
    sector_df = df[df["industria"] == sector].copy()
    sector_df["puesto"] = sector_df["puesto"].cat.remove_unused_categories()
    return sector_df.reset_index(drop=True)


# --- Distribución salarial y polarización ----------------------------------------

def calcular_gini(serie):
    """
    Coeficiente de Gini (0 = todos ganan lo mismo, 1 = máxima desigualdad).
    Fórmula sobre valores ordenados: G = sum((2i - n - 1) * x_i) / (n * sum(x)).
    """
    valores = np.sort(serie.to_numpy())
    n = len(valores)
    posiciones = np.arange(1, n + 1)
    return np.sum((2 * posiciones - n - 1) * valores) / (n * np.sum(valores))


def describir_distribucion_salarial(df):
    """
    Media, desvío y medidas de dispersión de los salarios pre y post IA.

    Retorna:
    --------
    pd.DataFrame
        Filas: estadísticos. Columnas: salario_antes_usd, salario_despues_usd, variacion_pct.
    """
    resultados = {}
    for columna in ["salario_antes_usd", "salario_despues_usd"]:
        serie = df[columna]
        medidas = resumen_estadistico(serie)
        medidas["percentil_10"] = serie.quantile(0.10)
        medidas["percentil_90"] = serie.quantile(0.90)
        medidas["ratio_p90_p10"] = medidas["percentil_90"] / medidas["percentil_10"]
        medidas["gini"] = calcular_gini(serie)
        resultados[columna] = medidas
    tabla = pd.DataFrame(resultados)
    tabla["variacion_pct"] = (tabla["salario_despues_usd"] / tabla["salario_antes_usd"] - 1) * 100
    return tabla.rename_axis("estadistico").reset_index()


def clasificar_cambio_salarial(df):
    """
    Cuenta qué proporción de trabajadores ganó, perdió o quedó estable
    (umbral de ±5% de cambio salarial). Si crecen ambos extremos a la vez,
    es una señal de polarización.
    """
    cambio = df["cambio_salarial_pct"]
    grupos = np.select(
        [cambio > UMBRAL_CAMBIO_RELEVANTE, cambio < -UMBRAL_CAMBIO_RELEVANTE],
        [f"Ganancia (> +{UMBRAL_CAMBIO_RELEVANTE}%)", f"Pérdida (< -{UMBRAL_CAMBIO_RELEVANTE}%)"],
        default="Estable (±5%)",
    )
    conteo = pd.Series(grupos, name="grupo").value_counts()
    return pd.DataFrame({"cantidad": conteo, "porcentaje": conteo / len(df) * 100}).reset_index()


def cambio_salarial_por_tramo(df, cantidad_tramos=4):
    """
    Cambio salarial promedio según el tramo (cuartil) del salario previo.
    Permite ver si la IA beneficia más a los que ya ganaban más.
    """
    tramos = pd.qcut(df["salario_antes_usd"], q=cantidad_tramos,
                     labels=[f"Q{i}" for i in range(1, cantidad_tramos + 1)])
    tabla = df.groupby(tramos, observed=True)["cambio_salarial_pct"].agg(["mean", "median", "std", "count"])
    return tabla.rename_axis("cuartil_salario_previo").reset_index()


# --- Vulnerabilidad por puesto ----------------------------------------------------

def ranking_riesgo_por_puesto(df):
    """
    Ordena los puestos de mayor a menor riesgo de automatización promedio.

    Retorna:
    --------
    pd.DataFrame
        Riesgo medio, puntaje de reemplazo medio, % de registros en categoría "Alto"
        y nivel educativo medio por puesto.
    """
    agrupado = df.groupby("puesto", observed=True)
    tabla = pd.DataFrame({
        "riesgo_medio_pct": agrupado["riesgo_automatizacion_pct"].mean(),
        "puntaje_reemplazo_medio": agrupado["puntaje_reemplazo_ia"].mean(),
        "pct_riesgo_alto": agrupado["categoria_riesgo"].apply(lambda s: (s == "Alto").mean() * 100),
        "nivel_educativo_medio": agrupado["nivel_educativo_requerido"].mean(),
        "registros": agrupado.size(),
    })
    return tabla.sort_values("riesgo_medio_pct", ascending=False).reset_index()


def obtener_top_puestos_riesgo(ranking, cantidad=3):
    """Devuelve la lista con los `cantidad` puestos de mayor riesgo."""
    return ranking.head(cantidad)["puesto"].tolist()


def distribucion_educativa_por_puesto(df, puestos):
    """
    Tabla cruzada: % de registros de cada puesto en cada nivel educativo (1 a 5).

    Parámetros:
    -----------
    df : pd.DataFrame
        Datos del sector.
    puestos : list[str]
        Puestos a incluir (ej. el top 3 de riesgo).
    """
    subconjunto = df[df["puesto"].isin(puestos)]
    tabla = pd.crosstab(subconjunto["puesto"].astype(str), subconjunto["nivel_educativo_requerido"],
                        normalize="index") * 100
    return tabla.round(1).reset_index()


def riesgo_por_nivel_educativo(df):
    """Riesgo de automatización medio para cada nivel educativo requerido."""
    tabla = df.groupby("nivel_educativo_requerido")["riesgo_automatizacion_pct"].agg(["mean", "median", "count"])
    return tabla.reset_index()


def correlacion_entre(df, columna_x, columna_y):
    """
    Correlación de Pearson (lineal) y de Spearman (monótona) entre dos columnas.
    Spearman se calcula como Pearson sobre los rangos, sin depender de scipy.
    """
    x, y = df[columna_x], df[columna_y]
    return {
        "pearson": x.corr(y),
        "spearman": x.rank().corr(y.rank()),
    }


# --- Cambio salarial y resiliencia por puesto ------------------------------------

def cambio_salarial_por_puesto(df):
    """
    Cambio salarial porcentual por puesto: promedio de los cambios individuales
    y cambio del salario medio del puesto (antes vs después).
    """
    agrupado = df.groupby("puesto", observed=True)
    tabla = pd.DataFrame({
        "cambio_medio_pct": agrupado["cambio_salarial_pct"].mean(),
        "cambio_mediano_pct": agrupado["cambio_salarial_pct"].median(),
        "salario_medio_antes": agrupado["salario_antes_usd"].mean(),
        "salario_medio_despues": agrupado["salario_despues_usd"].mean(),
    })
    tabla["cambio_salario_medio_pct"] = (tabla["salario_medio_despues"] / tabla["salario_medio_antes"] - 1) * 100
    return tabla.sort_values("cambio_medio_pct", ascending=False).reset_index()


def estandarizar_z(serie):
    """Puntaje z: cuántos desvíos se aleja cada valor de la media."""
    return (serie - serie.mean()) / serie.std()


def indice_resiliencia_por_puesto(df):
    """
    Índice de resiliencia = promedio de puntajes z de cuatro indicadores:
      + cambio salarial medio, + crecimiento de demanda de habilidades,
      - riesgo de automatización, - urgencia de recapacitación.
    Un valor alto indica un perfil que resiste mejor el impacto de la IA.
    """
    agrupado = df.groupby("puesto", observed=True)
    tabla = pd.DataFrame({
        "riesgo_medio_pct": agrupado["riesgo_automatizacion_pct"].mean(),
        "cambio_salarial_medio_pct": agrupado["cambio_salarial_pct"].mean(),
        "crecimiento_demanda_medio_pct": agrupado["crecimiento_demanda_habilidades_pct"].mean(),
        "urgencia_recapacitacion_media": agrupado["urgencia_recapacitacion"].mean(),
    })
    tabla["indice_resiliencia"] = (
        estandarizar_z(tabla["cambio_salarial_medio_pct"])
        + estandarizar_z(tabla["crecimiento_demanda_medio_pct"])
        - estandarizar_z(tabla["riesgo_medio_pct"])
        - estandarizar_z(tabla["urgencia_recapacitacion_media"])
    ) / 4
    return tabla.sort_values("indice_resiliencia", ascending=False).reset_index()


def evolucion_anual(df):
    """Promedios por año de riesgo, adopción de IA, disrupción y cambio salarial."""
    columnas = ["riesgo_automatizacion_pct", "nivel_adopcion_ia", "intensidad_disrupcion_ia", "cambio_salarial_pct"]
    return df.groupby("anio")[columnas].mean().reset_index()


# --- Inconsistencias de negocio ---------------------------------------------------

def verificar_inconsistencias_negocio(df):
    """
    Re-chequea sobre el dataset limpio las reglas de negocio que estaban rotas
    en el crudo. Todas las cantidades deberían ser 0.

    Retorna:
    --------
    pd.DataFrame
        Una fila por regla con la cantidad de registros que la violan.
    """
    esperado = df["salario_antes_usd"] * (1 + df["cambio_salarial_pct"] / 100)
    reglas = {
        "Salario posterior != antes * (1 + cambio%)": ~np.isclose(df["salario_despues_usd"], esperado, rtol=0.001),
        "Salario antes = después con cambio != 0": np.isclose(df["salario_antes_usd"], df["salario_despues_usd"])
        & (df["cambio_salarial_pct"] != 0),
        "Salario <= 0": (df["salario_antes_usd"] <= 0) | (df["salario_despues_usd"] <= 0),
        "Puntaje de reemplazo fuera de 0-100": ~df["puntaje_reemplazo_ia"].between(0, 100),
        "Categoría de riesgo incoherente con el %": ~df["categoria_riesgo"].astype(str).eq(
            pd.cut(df["riesgo_automatizacion_pct"], [0, 30, 60, 100.01], right=False,
                   labels=["Bajo", "Medio", "Alto"]).astype(str)),
    }
    return pd.DataFrame({"regla": list(reglas), "registros_que_la_violan": [int(m.sum()) for m in reglas.values()]})


# --- Función integradora ----------------------------------------------------------

def calcular_estadisticas(df_sector):
    """
    Ejecuta todo el análisis de la Fase II sobre los datos del sector.

    Retorna:
    --------
    dict[str, pd.DataFrame | dict | list]
        Cada clave es un resultado listo para guardar o graficar.
    """
    validar_contrato_analisis(df_sector)
    ranking = ranking_riesgo_por_puesto(df_sector)
    top_puestos = obtener_top_puestos_riesgo(ranking)
    return {
        "distribucion_salarial": describir_distribucion_salarial(df_sector),
        "clasificacion_cambio_salarial": clasificar_cambio_salarial(df_sector),
        "cambio_por_cuartil_salarial": cambio_salarial_por_tramo(df_sector),
        "ranking_riesgo_puestos": ranking,
        "top_puestos_riesgo": top_puestos,
        "educacion_top_puestos": distribucion_educativa_por_puesto(df_sector, top_puestos),
        "riesgo_por_nivel_educativo": riesgo_por_nivel_educativo(df_sector),
        "corr_riesgo_educacion": correlacion_entre(df_sector, "nivel_educativo_requerido", "riesgo_automatizacion_pct"),
        "corr_urgencia_disrupcion": correlacion_entre(df_sector, "intensidad_disrupcion_ia", "urgencia_recapacitacion"),
        "cambio_salarial_puestos": cambio_salarial_por_puesto(df_sector),
        "resiliencia_puestos": indice_resiliencia_por_puesto(df_sector),
        "evolucion_anual": evolucion_anual(df_sector),
        "inconsistencias_negocio": verificar_inconsistencias_negocio(df_sector),
    }
