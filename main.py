"""
Orquestador del pipeline: Impacto de la IA en el Empleo — Sector Tecnología (Grupo 1).

No hace el trabajo pesado: llama a las funciones de cada módulo en orden
y guarda los resultados. Ejecutar con:  python main.py
"""

import pandas as pd

from src.analysis import calcular_estadisticas, filtrar_sector
from src.clean_data import limpiar_dataframe
from src.load_data import auditar_calidad, cargar_dataset
from src.utils import (
    RUTA_DATOS_CRUDOS,
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


def imprimir_resumen(df_crudo, df_limpio, df_sector, resultados):
    """Muestra por consola los números clave del pipeline."""
    print(f"Registros crudos: {len(df_crudo):,} | limpios: {len(df_limpio):,} | sector {SECTOR_ASIGNADO}: {len(df_sector):,}")
    print(f"Top 3 puestos con mayor riesgo: {', '.join(resultados['top_puestos_riesgo'])}")
    print("\nDistribución salarial:\n", resultados["distribucion_salarial"].round(2).to_string(index=False))
    print("\nResiliencia por puesto:\n", resultados["resiliencia_puestos"].round(2).to_string(index=False))


def main():
    # 1. Carga y auditoría de calidad del dato crudo
    df_crudo = cargar_dataset(RUTA_DATOS_CRUDOS)
    guardar_tabla(auditar_calidad(df_crudo), "00_auditoria_calidad.csv")

    # 2. Limpieza (con bitácora de decisiones)
    df_limpio, bitacora = limpiar_dataframe(df_crudo)
    guardar_tabla(bitacora, "00_bitacora_saneamiento.csv")
    RUTA_DATOS_LIMPIOS.parent.mkdir(parents=True, exist_ok=True)
    df_limpio.to_csv(RUTA_DATOS_LIMPIOS, index=False, encoding="utf-8-sig")

    # 3. Análisis del sector asignado
    df_sector = filtrar_sector(df_limpio, SECTOR_ASIGNADO)
    resultados = calcular_estadisticas(df_sector)
    guardar_resultados(resultados)

    # 4. Visualización
    generar_reporte(df_sector, resultados)

    imprimir_resumen(df_crudo, df_limpio, df_sector, resultados)
    print("\n✅ Pipeline completado exitosamente. Resultados en outputs/ y data/processed/.")


if __name__ == "__main__":
    main()
