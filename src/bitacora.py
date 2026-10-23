"""Bitácora de saneamiento: cada módulo registra sus pasos con registrar_paso()."""

import pandas as pd

entradas = []


def registrar_paso(paso, filas_afectadas, justificacion):
    # agrego una entrada a la bitacora"
    entradas.append({"paso": paso, "filas_afectadas": int(filas_afectadas), "justificacion": justificacion})


def obtener_bitacora():
    "devuelvo la bitacora como df"
    return pd.DataFrame(entradas)


def reiniciar_bitacora():
    # vacio la bitácora (evita duplicados si el pipeline corre dos veces) 
    entradas.clear()