"""
Orquestador del pipeline: Impacto de la IA en el Empleo — Sector Tecnología (Grupo 1).

No hace el trabajo pesado: llama a las funciones de cada módulo en orden
y guarda los resultados. Ejecutar con:  python main.py
"""

import pandas as pd

from src.analysis import calcular_estadisticas, filtrar_sector
from src.clean_data import limpiar_dataframe
from src.load_data import cargar_industria
from src.audit import auditar_calidad, nulos_recuperables_por_formula, buscar_relaciones_exactas, comparar_imputacion, asimetria_y_outliers, matriz_correlacion
from src.bitacora import reiniciar_bitacora, obtener_bitacora

from src.utils import (
    RUTA_DATOS_CRUDOS,
    INDUSTRIA,
    RUTA_DATOS_LIMPIOS,
    SECTOR_ASIGNADO,
    guardar_tabla,
)

from src.visualization import generar_reporte


def guardar_resultados(resultados):
    """Guarda en outputs/tablas cada resultado del análisis que sea un DataFrame o dict."""
    for nombre, valor in resultados.items():
        if isinstance(valor, dict):
            valor = pd.DataFrame([valor])
        if isinstance(valor, pd.DataFrame):
            guardar_tabla(valor.round(4), f"{nombre}.csv")

""" Descomentar esta funcion cuando haga falta!
def imprimir_resumen(df_industria, df_limpio, df_industria, resultados):
    Muestra por consola los números clave del pipeline.
    print(f"Registros crudos: {len(df_industria):,} | limpios: {len(df_limpio):,} | sector {SECTOR_ASIGNADO}: {len(df_industria):,}")
    print(f"Top 3 puestos con mayor riesgo: {', '.join(resultados['top_puestos_riesgo'])}")
    print("\nDistribución salarial:\n", resultados["distribucion_salarial"].round(2).to_string(index=False))
    print("\nResiliencia por puesto:\n", resultados["resiliencia_puestos"].round(2).to_string(index=False))
"""

# S auditamos y guardamos la informacion relevante en csv
def guardar_auditoria(df_industria):
    """Calcula las tablas de la auditoría, muestra la principal por consola y las guarda en outputs/tablas."""
    # calculo cada tabla, en el orden de las partes de audit.py
    hallazgos = auditar_calidad(df_industria, INDUSTRIA)
    relaciones = buscar_relaciones_exactas(df_industria)
    recuperables = nulos_recuperables_por_formula(df_industria)
    comparacion = comparar_imputacion(df_industria)
    outliers = asimetria_y_outliers(df_industria).reset_index(names="columna")
    correlacion = matriz_correlacion(df_industria).rename_axis("columna").reset_index()

    # muestro por consola la tabla principal
    print(hallazgos.to_string(index=False))

    # guardo cada tabla con su numero
    guardar_tabla(hallazgos, "00_auditoria_calidad.csv")
    guardar_tabla(recuperables, "01_nulos_recuperables.csv")
    guardar_tabla(comparacion, "02_comparacion_imputacion.csv")
    guardar_tabla(outliers, "03_asimetria_outliers.csv")
    guardar_tabla(correlacion, "04_matriz_correlacion.csv")
    guardar_tabla(relaciones, "05_relaciones_exactas.csv")


def main():
    # limpio la bitacora al ejecutar(obligarorio)
    reiniciar_bitacora()
    

    # FASE I
    # cargo y filtro el dataset
    df_industria = cargar_industria(RUTA_DATOS_CRUDOS, INDUSTRIA)
    # audito los datos disponibles y guardo resultados en archivos csv 
    guardar_auditoria(df_industria)
    
    # limpiamos el dataset teniendo en cuenta las conclusiones de la auditación
    df_limpio = limpiar_dataframe(df_industria)
    
    # garantizo que la carpeta destino exista
    RUTA_DATOS_LIMPIOS.parent.mkdir(parents=True, exist_ok=True)
    # guardamos el csv en data/processed/
    df_limpio.to_csv(RUTA_DATOS_LIMPIOS, index=False, encoding="utf-8-sig")
    
    #guardo la informacion de la bitacora hasta el momento(mover al final de fase 3, cuando ya haya sido revisada)
    guardar_tabla(obtener_bitacora(), "00_bitacora_saneamiento.csv")

    # 3. Análisis del sector asignado
    df_industria = filtrar_sector(df_limpio, SECTOR_ASIGNADO)
    resultados = calcular_estadisticas(df_industria)
    guardar_resultados(resultados)

    # 4. Visualización
    generar_reporte(df_industria, resultados)

    #imprimir_resumen(df_industria, df_limpio, df_industria, resultados)
    print("\n✅ Pipeline completado exitosamente. Resultados en outputs/ y data/processed/.")


if __name__ == "__main__":
    main()
