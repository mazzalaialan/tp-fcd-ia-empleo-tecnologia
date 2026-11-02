"""
Fase II: análisis estadístico y exploratorio con pandas y numpy.
Las funciones reciben el df limpio (ya en español) y devuelven tablas o diccionarios; no grafican ni guardan.
"""

import numpy as np
import pandas as pd

from src.utils import resumen_estadistico

# a partir de este % de cambio salarial considero que el trabajador ganó o perdió
UMBRAL_CAMBIO_RELEVANTE = 5


def validar_contrato_analisis(df):
    """compruebo que el df cumpla lo que espera el análisis: columnas en minúscula y sin nulos"""
    assert all(c == c.lower() for c in df.columns), "Columnas deben ser minúsculas"
    assert df.isnull().sum().sum() == 0, "No debe haber nulos"


# parte 1: distribución salarial y polarización

def calcular_gini(serie):
    """coeficiente de gini (0 = todos ganan igual, 1 = máxima desigualdad): G = sum((2i - n - 1) * x_i) / (n * sum(x)) con los valores ordenados"""
    valores = np.sort(serie.to_numpy())
    n = len(valores)
    posiciones = np.arange(1, n + 1)
    return np.sum((2 * posiciones - n - 1) * valores) / (n * np.sum(valores))


def describir_distribucion_salarial(df):
    """media, desvío y otras medidas de dispersión de los salarios antes y después de la ia, con la variación entre ambos"""
    resultados = {}
    for columna in ["salario_antes_usd", "salario_despues_usd"]:
        serie = df[columna]

        # estadísticos base (utils) y los que agrego para ver si crece la dispersión
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
    """cuento cuántos trabajadores ganaron, perdieron o quedaron estables (umbral de ±5%); si crecen los dos extremos a la vez hay polarización"""
    cambio = df["cambio_salarial_pct"]
    grupos = np.select(
        [cambio > UMBRAL_CAMBIO_RELEVANTE, cambio < -UMBRAL_CAMBIO_RELEVANTE],
        [f"Ganancia (> +{UMBRAL_CAMBIO_RELEVANTE}%)", f"Pérdida (< -{UMBRAL_CAMBIO_RELEVANTE}%)"],
        default="Estable (±5%)",
    )
    conteo = pd.Series(grupos, name="grupo").value_counts()
    return pd.DataFrame({"cantidad": conteo, "porcentaje": conteo / len(df) * 100}).reset_index()


def cambio_salarial_por_tramo(df, cantidad_tramos=4):
    """cambio salarial promedio según el cuartil del salario previo, para ver si la ia favorece más a los que ya ganaban más"""
    tramos = pd.qcut(df["salario_antes_usd"], q=cantidad_tramos,
                     labels=[f"Q{i}" for i in range(1, cantidad_tramos + 1)])
    tabla = df.groupby(tramos, observed=True)["cambio_salarial_pct"].agg(["mean", "median", "std", "count"])
    return tabla.rename_axis("cuartil_salario_previo").reset_index()


# parte 2: vulnerabilidad por puesto

def ranking_riesgo_por_puesto(df):
    """ordeno los puestos de mayor a menor riesgo de automatización promedio, con puntaje de reemplazo, % en categoría alto y nivel educativo medio"""
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
    """devuelvo la lista con los puestos de mayor riesgo (3 por defecto)"""
    return ranking.head(cantidad)["puesto"].tolist()


def distribucion_educativa_por_puesto(df, puestos):
    """% de registros de cada puesto en cada nivel educativo (1 a 5), solo para los puestos que le paso (por ejemplo el top 3 de riesgo)"""
    subconjunto = df[df["puesto"].isin(puestos)]
    tabla = pd.crosstab(subconjunto["puesto"].astype(str), subconjunto["nivel_educativo_requerido"],
                        normalize="index") * 100
    return tabla.round(1).reset_index()


def riesgo_por_nivel_educativo(df):
    """riesgo de automatización medio para cada nivel educativo requerido"""
    tabla = df.groupby("nivel_educativo_requerido")["riesgo_automatizacion_pct"].agg(["mean", "median", "count"])
    return tabla.reset_index()


def correlacion_entre(df, columna_x, columna_y):
    """correlación de pearson (lineal) y de spearman (por rangos) entre dos columnas; spearman es pearson sobre los rangos, así no hace falta scipy"""
    x, y = df[columna_x], df[columna_y]
    return {
        "pearson": x.corr(y),
        "spearman": x.rank().corr(y.rank()),
    }


# parte 3: cambio salarial y resiliencia por puesto

def cambio_salarial_por_puesto(df):
    """cambio salarial por puesto: promedio de los cambios individuales y cambio del salario medio (antes vs después)"""
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
    """puntaje z: cuántos desvíos se aleja cada valor de la media"""
    return (serie - serie.mean()) / serie.std()


def indice_resiliencia_por_puesto(df):
    """índice de resiliencia por puesto: promedio de cuatro puntajes z (suman el cambio salarial y el crecimiento de la demanda de habilidades, restan el riesgo y la urgencia de recapacitación); un valor alto es un perfil que resiste mejor"""
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
    """promedios por año de riesgo, adopción de ia, disrupción y cambio salarial"""
    columnas = ["riesgo_automatizacion_pct", "nivel_adopcion_ia", "intensidad_disrupcion_ia", "cambio_salarial_pct"]
    return df.groupby("anio")[columnas].mean().reset_index()


# parte 4: inconsistencias de negocio

def verificar_inconsistencias_negocio(df):
    """vuelvo a chequear sobre el df limpio las reglas de negocio que estaban rotas en el crudo; todas las cantidades tienen que dar 0"""
    esperado = df["salario_antes_usd"] * (1 + df["cambio_salarial_pct"] / 100)

    # una regla por clave, con True en las filas que la violan
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


# función que junta todo el análisis (la llama main.py)

def calcular_estadisticas(df_sector):
    """corro el análisis de la fase 2 sobre el sector y devuelvo un diccionario con cada resultado, listo para guardar o graficar"""
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