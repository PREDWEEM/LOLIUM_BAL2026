import pandas as pd
import requests

# Coordenadas de Balcarce, provincia de Buenos Aires
lat = -37.7664
lon = -58.2999

# Rango de fechas de tu archivo original
start_date = "2026-01-01"
end_date = "2026-03-30"

# URL de la API de Open-Meteo para datos históricos diarios
url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=America%2FArgentina%2FBuenos_Aires"

print("Obteniendo datos meteorológicos para Balcarce...")
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    daily = data['daily']
    
    # Construcción del DataFrame con las columnas idénticas a tu archivo
    df_balcarce = pd.DataFrame({
        'Fecha': daily['time'],
        'TMAX': daily['temperature_2m_max'],
        'TMIN': daily['temperature_2m_min'],
        'Prec': daily['precipitation_sum']
    })
    
    # Rellenar posibles datos nulos (si la API tiene algún bache reciente) con 0 para lluvia o interpolando temperaturas
    df_balcarce['Prec'] = df_balcarce['Prec'].fillna(0)
    df_balcarce['TMAX'] = df_balcarce['TMAX'].interpolate()
    df_balcarce['TMIN'] = df_balcarce['TMIN'].interpolate()
    
    # Exportar el archivo final
    nombre_archivo = 'meteo_daily_balcarce_real.csv'
    df_balcarce.to_csv(nombre_archivo, index=False)
    
    print(f"¡Archivo '{nombre_archivo}' generado con éxito!")
    print(df_balcarce.head())
else:
    print(f"Error al consultar la API. Código de estado: {response.status_code}")
