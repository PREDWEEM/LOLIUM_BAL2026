import requests
import pandas as pd
import sys
import os

# Coordenadas específicas de BALCARCE, Provincia de Buenos Aires
LAT = -37.7664
LON = -58.2999
ARCHIVO_CSV = 'meteo_daily.csv'

def actualizar_pronostico():
    url = "https://api.open-meteo.com/v1/forecast"
    
    # ESTRATEGIA DE REANÁLISIS DE TIEMPO REAL:
    # Captura los últimos 7 días (datos corregidos/asimilados) y los próximos 7 días de pronóstico.
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "America/Argentina/Buenos_Aires",
        "past_days": 7,
        "forecast_days": 7
    }
    
    print("Consultando a Open-Meteo para Balcarce (Ventana Híbrida: -7d a +7d)...")
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"Error en la API: {response.text}")
            sys.exit(1)
    except Exception as e:
        print(f"Error de conexión con la API: {e}")
        sys.exit(1)
        
    data = response.json()
    
    # DataFrame con el bloque temporal de 14 días móviles para Balcarce
    df_nuevo = pd.DataFrame({
        'Fecha': data['daily']['time'],
        'TMAX': data['daily']['temperature_2m_max'],
        'TMIN': data['daily']['temperature_2m_min'],
        'Prec': data['daily']['precipitation_sum']
    })
    
    # Forzar el parseo a datetime para evitar inconsistencias de tipo string al concatenar
    df_nuevo['Fecha'] = pd.to_datetime(df_nuevo['Fecha'])
    
    if df_nuevo.isnull().values.any():
        print("ADVERTENCIA: Datos incompletos detectados para Balcarce. Aplicando forward-fill temporal.")
        df_nuevo = df_nuevo.ffill()

    # Integración consistente con el archivo histórico local
    if os.path.exists(ARCHIVO_CSV):
        print(f"Leyendo historial desde {ARCHIVO_CSV}...")
        df_historico = pd.read_csv(ARCHIVO_CSV)
        df_historico['Fecha'] = pd.to_datetime(df_historico['Fecha'])
        
        # Combinamos la base histórica con el nuevo set de datos de la API
        df_final = pd.concat([df_historico, df_nuevo], ignore_index=True)
        
        # PROCESO DE DEPURACIÓN CRÍTICO:
        # 'keep=last' elimina las estimaciones de pronóstico antiguo y las reemplaza por
        # los registros consolidados mediante reanálisis a corto plazo una vez transcurrido el tiempo.
        df_final = df_final.drop_duplicates(subset=['Fecha'], keep='last')
        df_final = df_final.sort_values(by='Fecha').reset_index(drop=True)
    else:
        print(f"No se encontró {ARCHIVO_CSV}, inicializando nuevo registro para Balcarce...")
        df_final = df_nuevo

    # Persistencia en disco con formato ISO estricto (YYYY-MM-DD)
    df_final['Fecha'] = df_final['Fecha'].dt.strftime('%Y-%m-%d')
    df_final.to_csv(ARCHIVO_CSV, index=False)
    
    print("Base meteorológica de Balcarce actualizada y purgada. Últimos 10 registros:")
    print(df_final.tail(10))

if __name__ == "__main__":
    actualizar_pronostico()
