from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict

from src.utils import COLUMNAS_TEXTO, convertir_monto_a_float

# orden de la categoria de riesgo, para poder usarla en la correlacion
ORDEN_RIESGO = {"Low": 0, "Medium": 1, "High": 2}

# considero predictora a una columna si su correlacion con la columna a imputar es al menos esta
UMBRAL_PREDICTORAS = 0.5

# considero calculable con una formula a una columna si el r2 de su ajuste llega a este valor
UMBRAL_RELACION_EXACTA = 0.9999

# ordeno el archivo asi:
# parte 1: tabla de hallazgos (nulos, formato, inconsistencias)
# parte 2: relaciones exactas entre columnas y nulos que se recuperan con ellas
# parte 3: comparacion de metodos de imputacion (media, regresion, knn) con r2
# parte 4: asimetria y outliers

# parte 1: tabla de hallazgos
# en cada funcion hallazgos_* armo una lista de filas para la tabla de auditoria:
# (categoria, problema, columna, cantidad, detalle)


def salarios_para_comparar(df):
    """devuelvo el salario antes, despues y el esperado segun el cambio % (copias temporales)"""
    # convierto los montos de texto a numero (no modifico el df)
    antes = convertir_monto_a_float(df["salary_before_usd"])
    despues = convertir_monto_a_float(df["salary_after_usd"])

    # salario posterior que deberia tener segun el cambio porcentual informado
    esperado = antes * (1 + df["salary_change_percent"] / 100)
    return antes, despues, esperado


def hallazgos_nulos(df):
    """cuento los nulos de cada columna que tenga al menos uno"""
    hallazgos = []

    # cantidad de nulos de cada columna
    nulos = df.isnull().sum()

    # me quedo solo con las columnas que tienen al menos un nulo
    con_nulos = nulos[nulos > 0]

    # una fila de la tabla por cada columna con nulos
    for columna, cantidad in con_nulos.items():
        porcentaje = cantidad / len(df)

        categoria = "Vacíos de datos"
        problema = "Valores nulos"
        detalle = f"{porcentaje:.1%} de la columna"
        hallazgos.append((categoria, problema, columna, cantidad, detalle))

    return hallazgos


def hallazgos_industria(df, industria):
    """cuento las filas de la industria escritas con espacios o mayusculas distintas y listo las variantes"""
    # filas cuya escritura no es exactamente la esperada, contadas por variante
    distintas = df.loc[df["industry"] != industria, "industry"].value_counts()

    # armo el texto con cada variante y cuantas veces aparece
    partes = []
    for texto, veces in distintas.items():
        partes.append(f"'{texto}' ({veces})")
    variantes = ", ".join(partes)

    categoria = "Errores de formato"
    problema = f"Escrituras distintas de '{industria}'"
    columna = "industry"
    cantidad = distintas.sum()
    detalle = "variantes: " + variantes
    return [(categoria, problema, columna, cantidad, detalle)]


def hallazgos_anio_decimal(df):
    """cuento los años escritos con decimal"""
    # leo year como texto, asi que busco el punto decimal, por ejemplo 2025.0
    con_decimal = df["year"].str.contains(r"\.")

    categoria = "Errores de formato"
    problema = "Año con decimal"
    columna = "year"
    cantidad = con_decimal.sum()
    detalle = "ej: 2025.0"
    return [(categoria, problema, columna, cantidad, detalle)]


def hallazgos_numeros_como_texto(df):
    """detecto los valores que no se pueden leer como numero en las columnas que deberian ser numericas"""
    hallazgos = []

    # dejo afuera las columnas que son texto de verdad
    numericas = df.drop(columns=COLUMNAS_TEXTO)

    # convierto a numero (con errors="coerce" lo que no se puede queda nulo) y marco verdadero donde habia un valor
    # que ahora es nulo, por ejemplo "$61,170.45"
    convertido = numericas.apply(pd.to_numeric, errors="coerce")
    no_numero = numericas.notna() & convertido.isna()

    # cantidad de valores problematicos por columna, solo las que tienen alguno
    cantidades = no_numero.sum()
    con_problema = cantidades[cantidades > 0]

    # una fila de la tabla por cada columna afectada
    for columna, cantidad in con_problema.items():
        # tomo el primer valor que no se pudo convertir como ejemplo
        ejemplo = numericas.loc[no_numero[columna], columna].iloc[0]

        # cuento que tipo de python tiene cada valor de la columna; un float es un vacio (nulo)
        tipos = numericas[columna].apply(type).value_counts().to_dict()

        categoria = "Errores de formato"
        problema = "Número guardado como texto"
        detalle = f"ej: {ejemplo}; tipos: {tipos}"
        hallazgos.append((categoria, problema, columna, cantidad, detalle))

    return hallazgos


def hallazgos_duplicados(df):
    """cuento las filas repetidas"""
    categoria = "Inconsistencias lógicas"
    problema = "Filas duplicadas"
    columna = "todas"
    cantidad = df.duplicated().sum()
    detalle = ""
    return [(categoria, problema, columna, cantidad, detalle)]


def hallazgos_puntaje(df):
    """cuento los puntajes fuera de la escala de 0 a 100"""
    fuera_de_escala = df["ai_replacement_score"] > 100

    categoria = "Inconsistencias lógicas"
    problema = "Puntaje fuera de 0-100"
    columna = "ai_replacement_score"
    cantidad = fuera_de_escala.sum()
    detalle = ""
    return [(categoria, problema, columna, cantidad, detalle)]


def hallazgos_relaciones(df):
    """cuento las filas donde no se cumple cada relacion exacta entre columnas (tolerancia del 1%)"""
    hallazgos = []

    # valores que deberian tener las columnas segun cada formula
    _, despues, esperado = salarios_para_comparar(df)

    # calculo la presion esperada como el promedio entre la brecha de habilidades y el riesgo
    presion_esperada = (df["skill_gap_index"] + df["automation_risk_percent"]) / 2

    # columna (formula escrita, valor real, valor calculado con la formula)
    relaciones = {
        "salary_after_usd": ("salary_after = salary_before * (1 + salary_change/100)", despues, esperado),
        "skill_transition_pressure": ("pressure = (skill_gap + automation_risk) / 2",
                                      df["skill_transition_pressure"], presion_esperada),
    }

    for columna, (formula, real, calculado) in relaciones.items():
        # solo comparo las filas donde existen los dos valores
        evaluadas = real.notna() & calculado.notna()

        # tolero una diferencia de hasta el 1% del valor calculado, por los redondeos
        cumplen = ((real - calculado).abs() <= 0.01 * calculado.abs())[evaluadas]

        categoria = "Inconsistencias lógicas"
        problema = "No cumple la relación"
        cantidad = (~cumplen).sum()
        detalle = f"{formula}; cumplen {cumplen.sum()} de {evaluadas.sum()}"
        hallazgos.append((categoria, problema, columna, cantidad, detalle))

    return hallazgos


def ids_en_texto(df, mascara):
    """devuelvo los job_id de las filas marcadas, como texto (muestro hasta 10)"""
    ids = df.loc[mascara, "job_id"].tolist()
    texto = "job_id: " + ", ".join(str(i) for i in ids[:10])

    # si hay mas de 10, aviso cuantos quedan sin mostrar
    if len(ids) > 10:
        texto += f" (y {len(ids) - 10} mas)"
    return texto


def hallazgos_salarios_puntuales(df):
    """detecto dos errores concretos del salario posterior: fuera del limite del iqr e igual al anterior"""
    antes, despues, _ = salarios_para_comparar(df)

    # calculo el limite superior de la regla del iqr sobre el salario posterior, igual que en la limpieza
    q1 = despues.quantile(0.25)
    q3 = despues.quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr
    es_atipico = despues > limite_superior

    # busco salarios antes y despues iguales (diferencia menor a un centavo) con un cambio % distinto de 0
    son_iguales = ((antes - despues).abs() < 0.01) & (df["salary_change_percent"] != 0)

    categoria = "Inconsistencias lógicas"
    columna = "salary_after_usd"
    problema_atipico = "Salario posterior fuera del límite del IQR"
    problema_iguales = "Salario antes = después con cambio % distinto de 0"
    detalle_atipico = ids_en_texto(df, es_atipico) + f"; límite superior: {limite_superior:,.2f}"
    detalle_iguales = ids_en_texto(df, son_iguales)
    return [(categoria, problema_atipico, columna, es_atipico.sum(), detalle_atipico),
            (categoria, problema_iguales, columna, son_iguales.sum(), detalle_iguales)]


def auditar_calidad(df, industria):
    """armo la tabla con todos los problemas encontrados en los datos crudos"""
    # junto los hallazgos de cada revision, una por linea
    hallazgos = []
    hallazgos += hallazgos_nulos(df)
    hallazgos += hallazgos_industria(df, industria)
    hallazgos += hallazgos_anio_decimal(df)
    hallazgos += hallazgos_numeros_como_texto(df)
    hallazgos += hallazgos_duplicados(df)
    hallazgos += hallazgos_puntaje(df)
    hallazgos += hallazgos_relaciones(df)
    hallazgos += hallazgos_salarios_puntuales(df)

    columnas = ["categoria", "problema", "columna", "cantidad", "detalle"]
    return pd.DataFrame(hallazgos, columns=columnas)


def tabla_numerica(df):
    """devuelvo las columnas numericas del df (sin el identificador), con las que estaban como texto ya convertidas"""
    # paso a numero las columnas que se leyeron como texto
    antes, despues, _ = salarios_para_comparar(df)
    anio = pd.to_numeric(df["year"])
    riesgo = df["automation_risk_category"].map(ORDEN_RIESGO)

    # tomo las que ya son numericas, descarto el identificador y agrego las convertidas con assign
    numericas = df.select_dtypes("number").drop(columns=["job_id"])
    numericas = numericas.assign(salary_before_usd=antes, salary_after_usd=despues,
                                 year=anio, automation_risk_category=riesgo)
    return numericas


def matriz_correlacion(df):
    """armo la matriz de correlacion de las columnas numericas (convierto antes salarios, año y riesgo)"""
    numericas = tabla_numerica(df)
    correlacion = numericas.corr().round(2)
    return correlacion


# parte 2: relaciones exactas entre columnas y nulos que se recuperan con ellas (no modifico el df)


def buscar_relaciones_exactas(df):
    """
    busco columnas que se puedan calcular con una formula a partir de otras dos (r2 casi 1)
    la formula que guardo es objetivo = coef_1 * explicadora_1 + coef_2 * explicadora_2 + constante
    """
    numericas = tabla_numerica(df)

    # dejo afuera la categoria de riesgo porque es solo un orden (0, 1, 2) y no una cantidad que entre en una formula
    columnas = numericas.columns.drop("automation_risk_category")

    relaciones = []
    for objetivo in columnas:
        # pruebo cada par de las demas columnas como posibles explicadoras del objetivo
        for x1, x2 in combinations(columnas.drop(objetivo), 2):
            # uso solo las filas donde estan las tres columnas
            completas = numericas[[objetivo, x1, x2]].dropna()
            x = completas[[x1, x2]].to_numpy()
            y = completas[objetivo].to_numpy()

            # ajusto objetivo = a * x1 + b * x2 + c y mido que tan bien calza con el r2 de la clase
            modelo = LinearRegression()
            modelo.fit(x, y)
            r2 = r2_score(y, modelo.predict(x))

            # si el ajuste es casi perfecto, guardo los coeficientes de la formula (sumo 0.0 para no mostrar -0.0)
            if r2 >= UMBRAL_RELACION_EXACTA:
                coef_1 = round(modelo.coef_[0], 2) + 0.0
                coef_2 = round(modelo.coef_[1], 2) + 0.0
                constante = round(modelo.intercept_, 2) + 0.0
                relaciones.append((objetivo, x1, x2, coef_1, coef_2, constante, round(r2, 6), len(completas)))

    columnas_tabla = ["objetivo", "explicadora_1", "explicadora_2", "coef_1", "coef_2", "constante", "r2", "filas"]
    return pd.DataFrame(relaciones, columns=columnas_tabla)


def nulos_recuperables_por_formula(df):
    """cuento cuantos nulos de cada columna puedo recuperar exactos con una formula (sin estadistica)"""
    antes, despues, _ = salarios_para_comparar(df)
    cambio = df["salary_change_percent"]
    riesgo = df["automation_risk_percent"]
    presion = df["skill_transition_pressure"]
    brecha = df["skill_gap_index"]

    # nulos de cada columna
    nulos_despues = despues.isna().sum()
    nulos_antes = antes.isna().sum()
    nulos_riesgo = riesgo.isna().sum()

    # de esos, cuento los que tienen en la misma fila los datos que pide la formula
    recuperables_despues = (despues.isna() & antes.notna() & cambio.notna()).sum()
    recuperables_antes = (antes.isna() & despues.notna() & cambio.notna()).sum()
    recuperables_riesgo = (riesgo.isna() & presion.notna() & brecha.notna()).sum()

    # despejo el riesgo de pressure = (skill_gap + riesgo) / 2
    formula_despues = "after = before * (1 + cambio/100)"
    formula_antes = "before = after / (1 + cambio/100)"
    formula_riesgo = "riesgo = 2 * pressure - skill_gap"

    filas = [("salary_after_usd", nulos_despues, recuperables_despues, formula_despues),
             ("salary_before_usd", nulos_antes, recuperables_antes, formula_antes),
             ("automation_risk_percent", nulos_riesgo, recuperables_riesgo, formula_riesgo)]
    columnas = ["columna", "nulos", "recuperables_por_formula", "formula"]

    tabla = pd.DataFrame(filas, columns=columnas)
    tabla["quedan_para_estadistica"] = tabla["nulos"] - tabla["recuperables_por_formula"]
    return tabla


# parte 3: comparacion de metodos de imputacion, con las herramientas de la clase de regresion lineal


def sin_outliers(df, columna):
    """me quedo con las filas donde la columna esta dentro de los limites de tukey (regla del iqr)"""
    q1 = df[columna].quantile(0.25)
    q3 = df[columna].quantile(0.75)
    iqr = q3 - q1

    dentro = df[columna].between(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return df[dentro]


def r2_de_regresion(x, y):
    """devuelvo el r2 de ajuste, el r2 de prediccion (press con leave-one-out) y el error tipico de la regresion y de la media"""
    modelo = LinearRegression()
    modelo.fit(x, y)

    # r2 de ajuste: mido que tan bien se adapta el modelo a los mismos datos con los que lo entrene
    r2 = r2_score(y, modelo.predict(x))

    # r2 de prediccion: predigo cada fila con un modelo entrenado con todas las demas (leave-one-out)
    predicciones = cross_val_predict(modelo, x, y, cv=LeaveOneOut())

    # calculo press como la suma de los errores al cuadrado de esas predicciones y sst como la variacion total de la columna
    press = np.sum((y - predicciones) ** 2)
    sst = np.sum((y - np.mean(y)) ** 2)
    r2_prediccion = 1 - press / sst

    # calculo el error tipico por fila, en las unidades de la columna, como la raiz del error cuadratico medio
    # de la regresion (press) y de la media (sst, que es lo que se equivoca quien siempre predice la media)
    error_regresion = np.sqrt(press / len(y))
    error_media = np.sqrt(sst / len(y))
    return r2, r2_prediccion, error_regresion, error_media


def comparar_imputacion(df):
    """para cada columna con nulos calculo el r2 y el error tipico de la regresion, y el desvio de la columna imputada con media, regresion y knn"""
    numericas = tabla_numerica(df)

    # correlacion de cada columna con todas las demas, para elegir las predictoras
    correlaciones = numericas.corr()
    columnas_con_nulos = numericas.columns[numericas.isnull().any()]

    filas = []
    for objetivo in columnas_con_nulos:
        # me quedo con las columnas cuya correlacion con el objetivo es al menos el umbral; saco la categoria
        # de riesgo porque se deriva del porcentaje (uso errors="ignore" para evitar el error si ya no esta)
        r = correlaciones[objetivo].drop([objetivo, "automation_risk_category"], errors="ignore")
        predictoras = list(r[r.abs() >= UMBRAL_PREDICTORAS].index)
        original = numericas[objetivo]

        # metodo a: media
        con_media = original.fillna(original.mean())

        fila = {"columna": objetivo, "nulos": int(original.isna().sum()),
                "predictoras": ", ".join(predictoras), "desvio_original": round(original.std(), 2),
                "desvio_media": round(con_media.std(), 2)}

        # necesito al menos una predictora para la regresion y el knn
        if predictoras:
            # uso solo las filas completas y saco los outliers del objetivo, como hizo el profe con fare
            completas = numericas[[objetivo] + predictoras].dropna()
            completas = sin_outliers(completas, objetivo)
            x = completas[predictoras].to_numpy()
            y = completas[objetivo].to_numpy()

            # metodo b: regresion lineal; solo puedo predecir los nulos que tienen todas sus predictoras
            modelo = LinearRegression()
            modelo.fit(x, y)
            se_puede_predecir = original.isna() & numericas[predictoras].notna().all(axis=1)
            con_regresion = original.copy()

            # uso to_numpy porque entrene el modelo con arrays y no con tablas
            con_regresion[se_puede_predecir] = modelo.predict(numericas.loc[se_puede_predecir, predictoras].to_numpy())

            # metodo c: vecino mas cercano (k=5), como el knnimputer de la clase; no escalo las columnas, como en la clase
            imputado = KNNImputer(n_neighbors=5).fit_transform(numericas[[objetivo] + predictoras])

            # tomo la primera columna del resultado, que es el objetivo ya completado
            con_knn = pd.Series(imputado[:, 0], index=numericas.index)

            # r2 de la regresion (ajuste y prediccion) y error tipico por fila de la regresion y de la media
            r2, r2_prediccion, error_regresion, error_media = r2_de_regresion(x, y)
            fila["r2_ajuste"] = round(r2, 3)
            fila["r2_prediccion"] = round(r2_prediccion, 3)
            fila["error_media"] = round(error_media, 2)
            fila["error_regresion"] = round(error_regresion, 2)
            fila["desvio_regresion"] = round(con_regresion.std(), 2)
            fila["desvio_knn"] = round(con_knn.std(), 2)
        filas.append(fila)

    columnas = ["columna", "nulos", "predictoras", "r2_ajuste", "r2_prediccion", "desvio_original",
                "error_media", "error_regresion", "desvio_media", "desvio_regresion", "desvio_knn"]
    return pd.DataFrame(filas, columns=columnas)


def error_tipico(real, predicho):
    """calculo la raiz del error cuadratico medio entre los valores reales y los predichos"""
    diferencia = np.asarray(real) - np.asarray(predicho)
    return np.sqrt(np.mean(diferencia ** 2))


def comparar_salarios_sin_el_otro(df):
    """comparo media, regresion y knn para predecir cada salario sin usar el otro, como en las filas sin ningun salario"""
    numericas = tabla_numerica(df)

    # en las filas sin ningun salario faltan los dos, asi que ninguno puede ser predictora
    # tampoco uso la categoria de riesgo porque se deriva del porcentaje de riesgo
    salarios = ["salary_before_usd", "salary_after_usd"]
    predictoras = [c for c in numericas.columns if c not in salarios + ["automation_risk_category"]]

    filas = []
    for objetivo in salarios:
        # me quedo con las filas que tienen todos los datos, para poder comparar contra el valor real
        # y saco los outliers del salario, igual que en comparar_imputacion
        completas = numericas[[objetivo] + predictoras].dropna()
        completas = sin_outliers(completas, objetivo)
        x = completas[predictoras].to_numpy()
        y = completas[objetivo].to_numpy()

        # r2 de ajuste y de prediccion de la regresion, como en la clase (el resto de lo que devuelve no lo uso)
        r2, r2_prediccion, _, _ = r2_de_regresion(x, y)

        # separo el 20% de las filas como prueba y dejo el 80% restante para entrenar
        # random_state fijo para que el sorteo sea siempre el mismo
        prueba = completas.sample(frac=0.2, random_state=0)
        entrenamiento = completas.drop(prueba.index)
        real = prueba[objetivo]

        # metodo a: predigo la media del entrenamiento para todas las filas de prueba
        error_media = error_tipico(real, entrenamiento[objetivo].mean())

        # metodo b: ajusto una regresion lineal con el entrenamiento y predigo las filas de prueba
        modelo = LinearRegression()
        modelo.fit(entrenamiento[predictoras].to_numpy(), entrenamiento[objetivo].to_numpy())
        error_regresion = error_tipico(real, modelo.predict(prueba[predictoras].to_numpy()))

        # metodo c: escondo el salario de las filas de prueba y dejo que el knn lo complete
        # con las 5 filas mas parecidas (k=5)
        escondido = completas.copy()
        escondido.loc[prueba.index, objetivo] = np.nan
        imputado = KNNImputer(n_neighbors=5).fit_transform(escondido)

        # la primera columna del resultado es el salario ya completado; tomo solo las filas de prueba
        con_knn = pd.Series(imputado[:, 0], index=completas.index)
        error_knn = error_tipico(real, con_knn[prueba.index])

        # una fila de la tabla por salario, con los r2 y el error de cada metodo
        filas.append((objetivo, len(completas), round(r2, 3), round(r2_prediccion, 3),
                      round(error_media, 2), round(error_regresion, 2), round(error_knn, 2)))

    columnas = ["columna", "filas", "r2_ajuste", "r2_prediccion", "error_media", "error_regresion", "error_knn"]
    return pd.DataFrame(filas, columns=columnas)


# parte 4: asimetria y outliers


def asimetria_y_outliers(df):
    """para cada columna numerica calculo la asimetria, hacia donde esta la cola y cuantos outliers hay por la regla del iqr"""
    numericas = tabla_numerica(df)

    # calculo los limites de la regla del iqr: considero outlier lo que queda fuera de [q1 - 1.5 * iqr, q3 + 1.5 * iqr]
    q1 = numericas.quantile(0.25)
    q3 = numericas.quantile(0.75)
    iqr = q3 - q1
    limite_bajo = q1 - 1.5 * iqr
    limite_alto = q3 + 1.5 * iqr

    # con skew positivo marco cola derecha y con negativo cola izquierda; cuento los valores fuera de cada limite
    asimetria = numericas.skew()
    outliers_bajos = (numericas < limite_bajo).sum()
    outliers_altos = (numericas > limite_alto).sum()

    # marco la cola segun el signo de la asimetria (entre -0.5 y 0.5 la considero simetrica)
    cola = pd.Series("simétrica", index=numericas.columns)
    cola[asimetria >= 0.5] = "cola derecha"
    cola[asimetria <= -0.5] = "cola izquierda"

    tabla = pd.DataFrame({"asimetria": asimetria.round(2), "cola": cola,
                          "outliers_bajos": outliers_bajos, "outliers_altos": outliers_altos})
    return tabla