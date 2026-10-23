import pandas as pd
from src.bitacora import registrar_paso


def cargar_industria(ruta, industria):
    """
    cargo del dataset crudo y filtro por la indstria de interes
    """

    # leo dataset
    df_crudo = pd.read_csv(ruta, dtype={"year": "string"})
    
    # normalizo (pero no guardo) ya que hay variantes de la industria de interes
    normalizada = df_crudo["industry"].str.strip().str.title()
    
    # aplico mascara boleana 
    mascara = normalizada == industria
    
    # filtro y conservo copia del nuevo df 
    df_industria = df_crudo[mascara].copy()
    
    registrar_paso(f"Se incluyeron filas con variantes de '{industria}'", (df_industria["industry"] != industria).sum(),
                   "Espacios, minúsculas y mayúsculas distintas: sin normalizar se habrían perdido esas filas.")
    
    return df_industria