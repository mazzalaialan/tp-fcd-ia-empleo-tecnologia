"""
Visualización (Fase III) con Matplotlib.

Cada función genera UN gráfico y lo guarda como PNG. `generar_reporte`
las llama a todas y devuelve las rutas de los archivos creados.
"""

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: permite correr el pipeline en cualquier máquina
import matplotlib.pyplot as plt
import numpy as np

from src.utils import CARPETA_FIGURAS, SECTOR_ASIGNADO

# Paleta validada (colorblind-safe) y tintas de texto.
AZUL = "#2a78d6"
NARANJA = "#eb6834"
ROJO = "#e34948"
TINTA_PRINCIPAL = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRILLA = "#e4e3df"
FONDO = "#fcfcfb"


def configurar_estilo():
    """Aplica un estilo sobrio y uniforme a todos los gráficos."""
    plt.rcParams.update({
        "figure.facecolor": FONDO, "axes.facecolor": FONDO,
        "axes.edgecolor": GRILLA, "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlecolor": TINTA_PRINCIPAL,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": GRILLA, "grid.linewidth": 0.8,
        "xtick.color": TINTA_SECUNDARIA, "ytick.color": TINTA_SECUNDARIA,
        "font.size": 10, "legend.frameon": False, "savefig.dpi": 150,
    })


def guardar_figura(figura, nombre_archivo, carpeta=CARPETA_FIGURAS):
    """Guarda la figura como PNG, la cierra para liberar memoria y devuelve la ruta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo
    figura.savefig(ruta, bbox_inches="tight")
    plt.close(figura)
    return ruta


def graficar_histograma_riesgo(df):
    """
    Histograma del riesgo de automatización con líneas verticales de media y mediana.

    Parámetros:
    -----------
    df : pd.DataFrame
        Datos del sector (columna riesgo_automatizacion_pct).

    Retorna:
    --------
    Path
        Ruta del PNG generado.
    """
    riesgo = df["riesgo_automatizacion_pct"]
    figura, ejes = plt.subplots(figsize=(9, 5))
    ejes.hist(riesgo, bins=np.arange(0, 101, 5), color=AZUL, edgecolor=FONDO, linewidth=2, alpha=0.9)
    ejes.axvline(riesgo.mean(), color=NARANJA, linewidth=2, label=f"Media: {riesgo.mean():.1f}%")
    ejes.axvline(riesgo.median(), color=TINTA_PRINCIPAL, linewidth=2, linestyle="--",
                 label=f"Mediana: {riesgo.median():.1f}%")
    for umbral in (30, 60):
        ejes.axvline(umbral, color=TINTA_SECUNDARIA, linewidth=0.8, linestyle=":")
    ejes.text(15, ejes.get_ylim()[1] * 0.97, "Bajo", ha="center", color=TINTA_SECUNDARIA)
    ejes.text(37, ejes.get_ylim()[1] * 0.97, "Medio", ha="center", color=TINTA_SECUNDARIA)
    ejes.text(80, ejes.get_ylim()[1] * 0.97, "Alto", ha="center", color=TINTA_SECUNDARIA)
    ejes.set(title=f"Distribución del riesgo de automatización — {SECTOR_ASIGNADO} (n={len(df):,})",
             xlabel="Riesgo de automatización (%)", ylabel="Cantidad de registros", xlim=(0, 100))
    ejes.grid(axis="x", visible=False)
    ejes.legend(loc="upper right", bbox_to_anchor=(1, 0.9))
    return guardar_figura(figura, "01_histograma_riesgo.png")


def graficar_cambio_salarial_por_puesto(tabla_cambios):
    """
    Barras horizontales con el cambio salarial porcentual medio de cada puesto.
    Azul = aumento, rojo = caída.

    Parámetros:
    -----------
    tabla_cambios : pd.DataFrame
        Salida de analysis.cambio_salarial_por_puesto.
    """
    tabla = tabla_cambios.sort_values("cambio_medio_pct")
    colores = [AZUL if valor >= 0 else ROJO for valor in tabla["cambio_medio_pct"]]
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    barras = ejes.barh(tabla["puesto"].astype(str), tabla["cambio_medio_pct"], color=colores, height=0.6)
    ejes.bar_label(barras, labels=[f"{v:+.2f}%" for v in tabla["cambio_medio_pct"]],
                   padding=4, color=TINTA_PRINCIPAL, fontsize=9)
    ejes.axvline(0, color=TINTA_SECUNDARIA, linewidth=1)
    limite = tabla["cambio_medio_pct"].abs().max() * 1.35
    ejes.set(title=f"Cambio salarial medio por puesto — {SECTOR_ASIGNADO}",
             xlabel="Cambio salarial promedio (%)", xlim=(-limite, limite))
    ejes.grid(axis="y", visible=False)
    return guardar_figura(figura, "02_cambio_salarial_por_puesto.png")


def graficar_dispersion_urgencia_disrupcion(df, correlacion):
    """
    Dispersión entre intensidad de disrupción por IA (x) y urgencia de
    re-capacitación (y), con recta de tendencia por mínimos cuadrados.

    Parámetros:
    -----------
    df : pd.DataFrame
        Datos del sector.
    correlacion : dict
        Salida de analysis.correlacion_entre (claves 'pearson' y 'spearman').
    """
    x = df["intensidad_disrupcion_ia"]
    y = df["urgencia_recapacitacion"]
    pendiente, ordenada = np.polyfit(x, y, deg=1)
    x_linea = np.linspace(x.min(), x.max(), 100)
    figura, ejes = plt.subplots(figsize=(9, 5.5))
    ejes.scatter(x, y, s=14, color=AZUL, alpha=0.45, edgecolors="none", label="Registros")
    ejes.plot(x_linea, pendiente * x_linea + ordenada, color=NARANJA, linewidth=2,
              label=f"Tendencia lineal (pendiente {pendiente:.2f})")
    ejes.text(0.98, 0.04, f"r de Pearson = {correlacion['pearson']:.2f}\nρ de Spearman = {correlacion['spearman']:.2f}",
              transform=ejes.transAxes, ha="right", va="bottom", color=TINTA_PRINCIPAL)
    ejes.set(title=f"Urgencia de re-capacitación vs. intensidad de disrupción — {SECTOR_ASIGNADO}",
             xlabel="Intensidad de disrupción por IA", ylabel="Urgencia de re-capacitación")
    ejes.legend(loc="upper left")
    return guardar_figura(figura, "03_dispersion_urgencia_disrupcion.png")


def graficar_salarios_pre_post(df):
    """
    Gráfico complementario: histogramas superpuestos del salario antes y después
    de la IA, para evaluar visualmente la polarización.
    """
    salarios = df[["salario_antes_usd", "salario_despues_usd"]]
    bins = np.linspace(salarios.min().min(), salarios.max().max(), 30)
    figura, ejes = plt.subplots(figsize=(9, 5))
    ejes.hist(df["salario_antes_usd"] / 1000, bins=bins / 1000, color=AZUL, alpha=0.55,
              label="Antes de la IA", edgecolor=FONDO)
    ejes.hist(df["salario_despues_usd"] / 1000, bins=bins / 1000, histtype="step", color=NARANJA,
              linewidth=2, label="Después de la IA")
    ejes.set(title=f"Salarios antes y después del impacto de la IA — {SECTOR_ASIGNADO}",
             xlabel="Salario anual (miles de USD)", ylabel="Cantidad de registros")
    ejes.grid(axis="x", visible=False)
    ejes.legend()
    return guardar_figura(figura, "04_salarios_pre_post.png")


def generar_reporte(df_sector, resultados):
    """
    Genera todas las piezas gráficas de la Fase III.

    Parámetros:
    -----------
    df_sector : pd.DataFrame
        Datos limpios del sector asignado.
    resultados : dict
        Salida de analysis.calcular_estadisticas.

    Retorna:
    --------
    list[Path]
        Rutas de los gráficos guardados.
    """
    configurar_estilo()
    return [
        graficar_histograma_riesgo(df_sector),
        graficar_cambio_salarial_por_puesto(resultados["cambio_salarial_puestos"]),
        graficar_dispersion_urgencia_disrupcion(df_sector, resultados["corr_urgencia_disrupcion"]),
        graficar_salarios_pre_post(df_sector),
    ]
