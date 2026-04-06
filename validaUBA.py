# -*- coding: utf-8 -*-
# ===============================================================
# 🌾 PREDWEEM INTEGRAL vK4.9.8 — MULTILOCALIDAD 2026
# Actualización:
# - CORRECCIÓN DE KEYERROR: Mapeo robusto de columnas (TMÍN, TMAX, Prec).
# - SELECCIÓN DE LOCALIDAD: Umbrales dinámicos (Sur: 24°C | Norte: 18°C).
# - ADAPTACIÓN AUTOMÁTICA: Lee archivos de Lucas Royo sin errores.
# - UNIFICACIÓN MECANÍSTICA 100%
# ===============================================================

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pickle
import io
from datetime import timedelta
from pathlib import Path
from scipy.signal import find_peaks

# ---------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO
# ---------------------------------------------------------
st.set_page_config(
    page_title="PREDWEEM MULTILOCALIDAD vK4.9.8",
    layout="wide",
    page_icon="🌾"
)

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] {
        background-color: #dcfce7;
        border-right: 1px solid #bbf7d0;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p {
        color: #166534 !important;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .bio-alert {
        padding: 10px;
        border-radius: 5px;
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fca5a5;
        margin-bottom: 10px;
        font-size: 0.9em;
    }
    .metric-header { color: #1e293b; font-weight: bold; margin-bottom: -10px; }
</style>
""", unsafe_allow_html=True)

BASE = Path(__file__).parent if "__file__" in globals() else Path.cwd()

# ---------------------------------------------------------
# 2. LÓGICA TÉCNICA (ANN + BIO + SEÑALES + BHS)
# ---------------------------------------------------------
def calculate_tt_scalar(t, t_base, t_opt, t_crit):
    if t <= t_base: return 0.0
    elif t <= t_opt: return t - t_base
    elif t < t_crit:
        factor = (t_crit - t) / (t_crit - t_opt)
        return (t - t_base) * factor
    else: return 0.0

def calcular_et0_hargreaves(jday, tmax, tmin, latitud=-37.75):
    lat_rad = np.radians(latitud)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * jday)
    dec = 0.409 * np.sin(2 * np.pi / 365 * jday - 1.39)
    ws = np.arccos(-np.tan(lat_rad) * np.tan(dec))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(lat_rad) * np.sin(dec) + np.cos(lat_rad) * np.cos(dec) * np.sin(ws))
    ra_mm = ra / 2.45
    tmean = (tmax + tmin) / 2.0
    trange = np.maximum(tmax - tmin, 0)
    return np.maximum(0.0023 * ra_mm * (tmean + 17.8) * np.sqrt(trange), 0)

def balance_hidrico_superficial(prec, et0, w_max=20.0, ke_suelo_max=0.4):
    n = len(prec)
    w = np.zeros(n)
    w[0] = w_max / 2.0 
    for i in range(1, n):
        kr = w[i-1] / w_max 
        ke_dinamico = ke_suelo_max * kr
        evaporacion_real = et0[i] * ke_dinamico
        w[i] = max(0.0, min(w_max, w[i-1] + prec[i] - evaporacion_real))
    return w

class PracticalANNModel:
    def __init__(self, IW, bIW, LW, bLW):
        self.IW, self.bIW, self.LW, self.bLW = IW, bIW, LW, bLW
        self.input_min = np.array([1, 0, -7, 0])
        self.input_max = np.array([300, 41, 25.5, 84])
    def normalize(self, X): return 2 * (X - self.input_min) / (self.input_max - self.input_min) - 1
    def predict(self, Xreal):
        Xn = self.normalize(Xreal)
        z1 = Xn @ self.IW + self.bIW
        a1 = np.tanh(z1)
        z2 = (a1 @ self.LW.T).flatten() + self.bLW
        emerrel = (np.tanh(z2) + 1) / 2
        return emerrel, np.cumsum(emerrel)

@st.cache_resource
def load_models():
    try:
        ann = PracticalANNModel(np.load(BASE/"IW.npy"), np.load(BASE/"bias_IW.npy"), np.load(BASE/"LW.npy"), np.load(BASE/"bias_out.npy"))
        with open(BASE/"modelo_clusters_k3.pkl", "rb") as f: k3 = pickle.load(f)
        return ann, k3
    except: return None, None

def load_data_robust(file_uploader):
    if not file_uploader: return None
    df = pd.read_excel(file_uploader) if file_uploader.name.endswith((".xlsx", ".xls")) else pd.read_csv(file_uploader)
    
    # Buscar cabecera si el archivo tiene filas vacías al inicio (Formato Royo)
    if not any(x in df.columns.str.lower() for x in ['fecha', 'date', 'tmax']):
        for i, row in df.iterrows():
            if str(row.iloc[0]).strip().lower() in ['fecha', 'fecha / hora', 'date']:
                df.columns = row.values
                df = df.iloc[i+1:].reset_index(drop=True)
                break
    return df

# ---------------------------------------------------------
# 3. INTERFAZ Y SIDEBAR
# ---------------------------------------------------------
modelo_ann, cluster_model = load_models()

st.sidebar.image("https://raw.githubusercontent.com/PREDWEEM/LOLIUM_BAL2026/main/logo.png", use_container_width=True)

st.sidebar.markdown("## 📍 1. Localización")
localidad = st.sidebar.selectbox("Seleccione Localidad", 
    ["Balcarce / Azul / T. Arroyos", "Bordenave", "Pergamino / Buenos Aires"])

# Ajuste automático del umbral según zona
default_umbral_termo = 18.0 if "Pergamino" in localidad else 24.0

st.sidebar.markdown("## 📂 2. Carga de Datos")
archivo_meteo = st.sidebar.file_uploader("Subir Clima", type=["xlsx", "csv"])
archivo_campo = st.sidebar.file_uploader("Subir Campo (Opcional)", type=["xlsx", "csv"])

df_meteo_raw = load_data_robust(archivo_meteo)
df_campo_raw = load_data_robust(archivo_campo)

st.sidebar.divider()
st.sidebar.markdown("## ⚙️ 3. Fisiología")
umbral_termoinhibicion = st.sidebar.number_input("Umbral Termoinhibición (°C)", value=default_umbral_termo, step=0.5)
umbral_er = st.sidebar.slider("Umbral Alerta Temprana", 0.05, 0.80, 0.30)
umbral_choque_hidrico = st.sidebar.slider("Choque Hídrico 3d (mm)", 20, 100, 45)

# ---------------------------------------------------------
# 4. MOTOR DE CÁLCULO (ROBUSTEZ DE COLUMNAS)
# ---------------------------------------------------------
if df_meteo_raw is not None and modelo_ann is not None:
    df = df_meteo_raw.copy()
    
    # MAPEO ROBUSTO (Cubre tmax, tmín, Prec, sum, etc.)
    df.columns = [str(c).upper().strip() for c in df.columns]
    mapeo = {
        'FECHA / HORA': 'Fecha', 'FECHA': 'Fecha', 'DATE': 'Fecha',
        'TMAX': 'TMAX', 'MÁX': 'TMAX', 'MAX': 'TMAX',
        'TMÍN': 'TMIN', 'TMIN': 'TMIN', 'MÍN': 'TMIN', 'MIN': 'TMIN',
        'SUM': 'Prec', 'PREC': 'Prec', 'LLUVIA': 'Prec'
    }
    df = df.rename(columns=mapeo)

    # Rescate de Prec si viene como Unnamed/NaN por celdas combinadas
    if 'Prec' not in df.columns:
        for c in df.columns:
            if c not in ['Fecha', 'TMAX', 'TMIN', 'PROMEDIO'] and ('NAN' in c or 'UNNAMED' in c):
                df = df.rename(columns={c: 'Prec'})
                break

    # Limpieza final
    for col in ["TMAX", "TMIN", "Prec"]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
    
    # DROPNA SEGURO (El KeyError se soluciona aquí)
    df = df.dropna(subset=["Fecha", "TMAX", "TMIN", "Prec"]).sort_values("Fecha").reset_index(drop=True)
    df["Julian_days"] = df["Fecha"].dt.dayofyear

    # Cálculos Mecanísticos
    df["Tmedia_aire"] = (df["TMAX"] + df["TMIN"]) / 2
    df["TMAX_suelo"] = df["Tmedia_aire"] + ((df["TMAX"] - df["TMIN"]) / 2 * 0.9)
    df["TMIN_suelo"] = df["Tmedia_aire"] - ((df["TMAX"] - df["TMIN"]) / 2 * 0.9)

    # Predicción ANN
    X = df[["Julian_days", "TMAX_suelo", "TMIN_suelo", "Prec"]].to_numpy(float)
    df["EMERREL"], _ = modelo_ann.predict(X)

    # Balance Hídrico y Escudo Térmico
    df["ET0"] = calcular_et0_hargreaves(df["Julian_days"], df["TMAX"], df["TMIN"])
    df["W_superficial"] = balance_hidrico_superficial(df["Prec"].values, df["ET0"].values, w_max=20.0)
    df["Hydric_Factor"] = 1 / (1 + np.exp(-10 * ((df["W_superficial"]/20.0) - 0.3)))
    df["EMERREL"] *= df["Hydric_Factor"]
    
    # Bloqueo por Termoinhibición (Escudo 10d)
    df["Tmedia_10d"] = df["Tmedia_aire"].rolling(window=10, min_periods=1).mean()
    df.loc[df["Tmedia_10d"] >= umbral_termoinhibicion, "EMERREL"] = 0.0

    # Visualización (Simplificada para Tab 1)
    st.title(f"🌾 PREDWEEM - {localidad}")
    
    # Mapa de Riesgo
    colorscale = [[0, "green"], [0.29, "green"], [0.3, "red"], [1, "red"]]
    fig_risk = go.Figure(go.Heatmap(z=[df["EMERREL"]], x=df["Fecha"], colorscale=colorscale, zmin=0, zmax=1, showscale=False))
    fig_risk.update_layout(height=120, margin=dict(t=30, b=0, l=10, r=10))
    st.plotly_chart(fig_risk, use_container_width=True)

    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=df["Fecha"], y=df["EMERREL"], name="Tasa Diaria", line=dict(color="green")))
    fig_main.add_hline(y=umbral_er, line_dash="dash", line_color="orange")
    
    # Mostrar datos de campo si existen
    if df_campo_raw is not None:
        df_c = df_campo_raw.copy()
        c_reps = [c for c in df_c.columns if "REP" in str(c).upper()]
        if c_reps:
            df_c['PLM2'] = df_c[c_reps].apply(pd.to_numeric, errors='coerce').mean(axis=1)
            df_c['Fecha'] = pd.to_datetime(df_c.iloc[:,0], errors='coerce')
            fig_main.add_trace(go.Scatter(x=df_c['Fecha'], y=df_c['PLM2']/df_c['PLM2'].max(), mode='markers+lines', name='Campo (Normalizado)', marker=dict(color='red')))

    st.plotly_chart(fig_main, use_container_width=True)

    # Exportación
    output = io.BytesIO()
    df.to_excel(output, index=False)
    st.sidebar.download_button("📥 Descargar Reporte", output.getvalue(), "PREDWEEM_Reporte.xlsx")

else:
    st.info("👋 Cargue su archivo de clima para iniciar la simulación.")
