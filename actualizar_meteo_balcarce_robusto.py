# -*- coding: utf-8 -*-
"""Actualizador meteorológico robusto PREDWEEM — Balcarce.

Reutiliza el lector SIGA del actualizador histórico y añade:
- ECMWF IFS histórico provisional para cada fecha vencida sin SIGA;
- ECMWF IFS ENS emparejado por miembro, sin completar nulos con cero;
- P50 coherente para TMAX, TMIN, TMEDIA y Prec;
- validación diaria y escritura atómica.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import actualizar_meteo_balcarce as base

MIN_MIEMBROS = 30
FRACCION_MINIMA = 0.80
HORAS_DIA = 24
URL_HIST = "https://archive-api.open-meteo.com/v1/archive"
MODELO_HIST = "ecmwf_ifs"

COLUMNAS = [
    "Fecha", "TMAX", "TMIN", "Prec", "TMEDIA",
    "TMAX_Media_Ens", "TMIN_Media_Ens", "TMEDIA_Media_Ens", "Prec_Media_Ens",
    "TMAX_P10", "TMAX_P50", "TMAX_P90", "TMIN_P10", "TMIN_P50", "TMIN_P90",
    "TMEDIA_P10", "TMEDIA_P50", "TMEDIA_P90", "Prec_P10", "Prec_P50", "Prec_P90",
    "Prob_Prec_ge_1mm", "Prob_Prec_ge_5mm", "Prob_Prec_ge_10mm", "Prob_Prec_ge_30mm",
    "GD_Tb2", "Fuente", "TipoDato", "CalidadDato", "N_miembros",
    "Latitud_grilla", "Longitud_grilla", "Elevacion_grilla_m", "Emision_UTC",
]
base.COLUMNAS_COMPLETAS = COLUMNAS


def columnas(df: pd.DataFrame) -> pd.DataFrame:
    salida = df.copy()
    for c in COLUMNAS:
        if c not in salida.columns:
            salida[c] = np.nan
    return salida[COLUMNAS]


def fechas_faltantes(obs: pd.DataFrame, inicio: date, fin: date) -> list[date]:
    esperadas = pd.date_range(inicio, fin, freq="D")
    presentes = pd.DatetimeIndex(pd.to_datetime(obs["Fecha"], errors="coerce").dropna()).normalize()
    return [x.date() for x in esperadas.difference(presentes)]


def rangos(fechas: list[date]) -> list[tuple[date, date]]:
    if not fechas:
        return []
    ordenadas = sorted(set(fechas)); salida = []; inicio = anterior = ordenadas[0]
    for actual in ordenadas[1:]:
        if actual == anterior + timedelta(days=1):
            anterior = actual
        else:
            salida.append((inicio, anterior)); inicio = anterior = actual
    salida.append((inicio, anterior))
    return salida


def params_hist(inicio: date, fin: date) -> dict[str, Any]:
    return {
        "latitude": base.LATITUD, "longitude": base.LONGITUD,
        "start_date": inicio.isoformat(), "end_date": fin.isoformat(),
        "models": MODELO_HIST, "timezone": base.ZONA_HORARIA,
        "temperature_unit": "celsius", "precipitation_unit": "mm",
        "cell_selection": "land",
    }


def normalizar_provisional(df: pd.DataFrame, payload: dict[str, Any], inicio: date, fin: date) -> pd.DataFrame:
    s = df.copy(); s["Fecha"] = pd.to_datetime(s["Fecha"], errors="coerce").dt.normalize()
    for c in ("TMAX", "TMIN", "TMEDIA", "Prec"):
        s[c] = pd.to_numeric(s[c], errors="coerce")
    s = s.loc[s["Fecha"].notna() & (s["Fecha"].dt.date >= inicio) & (s["Fecha"].dt.date <= fin)].copy()
    faltan = pd.date_range(inicio, fin).difference(pd.DatetimeIndex(s["Fecha"]))
    if len(faltan) or s[["TMAX", "TMIN", "TMEDIA", "Prec"]].isna().any().any():
        raise ValueError("ECMWF histórico devolvió fechas o valores incompletos.")
    if (s["TMAX"] < s["TMIN"]).any() or (s["Prec"] < 0).any():
        raise ValueError("ECMWF histórico devolvió valores físicamente inválidos.")
    for v in ("TMAX", "TMIN", "TMEDIA", "Prec"):
        s[f"{v}_P50"] = s[v]
    s["GD_Tb2"] = np.maximum(0.0, s["TMEDIA"] - base.TBASE)
    s["Fuente"] = "ECMWF_IFS_HISTORICO"; s["TipoDato"] = "Provisional"
    s["CalidadDato"] = "Provisional_hasta_reemplazo_SIGA"; s["N_miembros"] = 1
    s["Latitud_grilla"] = payload.get("latitude", np.nan)
    s["Longitud_grilla"] = payload.get("longitude", np.nan)
    s["Elevacion_grilla_m"] = payload.get("elevation", np.nan)
    s["Emision_UTC"] = base.fecha_utc_iso(); s["Fecha"] = s["Fecha"].dt.strftime("%Y-%m-%d")
    return columnas(s)


def provisional_diario(inicio: date, fin: date) -> pd.DataFrame:
    p = {**params_hist(inicio, fin), "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"}
    datos = base.solicitar_con_reintentos("GET", URL_HIST, params=p).json(); d = datos.get("daily", {})
    if {"time", "temperature_2m_max", "temperature_2m_min", "precipitation_sum"}.difference(d):
        raise ValueError("Faltan variables diarias en ECMWF histórico.")
    tmax = pd.to_numeric(pd.Series(d["temperature_2m_max"]), errors="coerce")
    tmin = pd.to_numeric(pd.Series(d["temperature_2m_min"]), errors="coerce")
    tmedia = pd.to_numeric(pd.Series(d.get("temperature_2m_mean", (tmax+tmin)/2)), errors="coerce")
    prec = pd.to_numeric(pd.Series(d["precipitation_sum"]), errors="coerce")
    return normalizar_provisional(pd.DataFrame({"Fecha": d["time"], "TMAX": tmax, "TMIN": tmin, "TMEDIA": tmedia, "Prec": prec}), datos, inicio, fin)


def provisional_horario(inicio: date, fin: date) -> pd.DataFrame:
    p = {**params_hist(inicio, fin), "hourly": "temperature_2m,precipitation"}
    datos = base.solicitar_con_reintentos("GET", URL_HIST, params=p).json(); h = datos.get("hourly", {})
    if {"time", "temperature_2m", "precipitation"}.difference(h):
        raise ValueError("Faltan variables horarias en ECMWF histórico.")
    x = pd.DataFrame({"Hora": pd.to_datetime(h["time"], errors="coerce"), "Temp": pd.to_numeric(pd.Series(h["temperature_2m"]), errors="coerce"), "Prec_h": pd.to_numeric(pd.Series(h["precipitation"]), errors="coerce")}).dropna(subset=["Hora"])
    x["Fecha"] = x["Hora"].dt.normalize()
    d = x.groupby("Fecha", as_index=False).agg(TMAX=("Temp","max"), TMIN=("Temp","min"), TMEDIA=("Temp","mean"), Prec=("Prec_h","sum"), HT=("Temp","count"), HP=("Prec_h","count"))
    d = d.loc[(d["HT"] == HORAS_DIA) & (d["HP"] == HORAS_DIA)].drop(columns=["HT","HP"])
    return normalizar_provisional(d, datos, inicio, fin)


def cargar_provisional(inicio: date, fin: date) -> pd.DataFrame:
    print(f"🧩 ECMWF provisional: {inicio} a {fin}")
    try:
        return provisional_diario(inicio, fin)
    except Exception as error:
        print(f"⚠️ Reintento horario: {error}")
        return provisional_horario(inicio, fin)


def mapear(hourly: dict[str, Any], variable: str) -> dict[str, str]:
    patron = re.compile(rf"^{re.escape(variable)}(?:_member(\d+))?$"); out = {}
    for clave, valor in hourly.items():
        m = patron.match(clave)
        if m and isinstance(valor, list):
            out["control" if m.group(1) is None else f"member{int(m.group(1)):03d}"] = clave
    return out


def procesar_ens(datos: dict[str, Any]) -> pd.DataFrame:
    h = datos.get("hourly", {}); tiempos = pd.Series(pd.to_datetime(h.get("time", []), errors="coerce"))
    if tiempos.empty or tiempos.isna().any():
        raise ValueError("ECMWF ENS no contiene fechas horarias válidas.")
    tm, pm = mapear(h, "temperature_2m"), mapear(h, "precipitation")
    comunes = sorted(set(tm).intersection(pm)); requeridos = max(MIN_MIEMBROS, math.ceil(len(comunes)*FRACCION_MINIMA))
    if len(comunes) < requeridos:
        raise ValueError(f"Solo hay {len(comunes)} miembros emparejados; se requieren {requeridos}.")
    diarios = []
    for ident in comunes:
        temp = pd.to_numeric(pd.Series(h[tm[ident]]), errors="coerce"); prec = pd.to_numeric(pd.Series(h[pm[ident]]), errors="coerce")
        if len(temp) != len(tiempos) or len(prec) != len(tiempos):
            continue
        x = pd.DataFrame({"Hora": tiempos, "Temp": temp, "Prec_h": prec}); x["Fecha"] = x["Hora"].dt.normalize()
        d = x.groupby("Fecha", as_index=False).agg(TMAX=("Temp","max"), TMIN=("Temp","min"), TMEDIA=("Temp","mean"), Prec=("Prec_h","sum"), HT=("Temp","count"), HP=("Prec_h","count"))
        ok = (d["HT"] == HORAS_DIA) & (d["HP"] == HORAS_DIA) & d[["TMAX","TMIN","TMEDIA","Prec"]].notna().all(axis=1) & (d["TMAX"] >= d["TMIN"]) & (d["Prec"] >= 0)
        d = d.loc[ok, ["Fecha","TMAX","TMIN","TMEDIA","Prec"]]; d["miembro"] = ident; diarios.append(d)
    todos = pd.concat(diarios, ignore_index=True) if diarios else pd.DataFrame()
    if todos.empty:
        raise ValueError("Ningún miembro produjo días válidos.")
    registros = []
    for fecha, g in todos.groupby("Fecha"):
        n = g["miembro"].nunique()
        if n < requeridos:
            raise ValueError(f"{pd.Timestamp(fecha).date()}: {n} miembros válidos; se requieren {requeridos}.")
        series = {v: g[v] for v in ("TMAX","TMIN","TMEDIA","Prec")}; p50 = {v: float(s.quantile(.5)) for v,s in series.items()}
        r = {"Fecha": pd.Timestamp(fecha).strftime("%Y-%m-%d"), **p50}
        for v,s in series.items():
            r[f"{v}_Media_Ens"] = float(s.mean()); r[f"{v}_P10"] = float(s.quantile(.1)); r[f"{v}_P50"] = p50[v]; r[f"{v}_P90"] = float(s.quantile(.9))
        r.update({"Prob_Prec_ge_1mm": float((series["Prec"]>=1).mean()*100), "Prob_Prec_ge_5mm": float((series["Prec"]>=5).mean()*100), "Prob_Prec_ge_10mm": float((series["Prec"]>=10).mean()*100), "Prob_Prec_ge_30mm": float((series["Prec"]>=30).mean()*100), "GD_Tb2": max(0,p50["TMEDIA"]-base.TBASE), "Fuente": "ECMWF_IFS_ENS_025", "TipoDato": "Pronostico", "CalidadDato": "Mediana_ensamble_P50", "N_miembros": int(n), "Latitud_grilla": datos.get("latitude",np.nan), "Longitud_grilla": datos.get("longitude",np.nan), "Elevacion_grilla_m": datos.get("elevation",np.nan), "Emision_UTC": base.fecha_utc_iso()})
        registros.append(r)
    return columnas(pd.DataFrame(registros)).sort_values("Fecha").reset_index(drop=True)


def cargar_ens() -> pd.DataFrame:
    datos = base.consultar_ecmwf_ens(); pron = procesar_ens(datos)
    base.DIRECTORIO_PRONOSTICOS.mkdir(parents=True, exist_ok=True)
    marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base.escribir_csv_atomico(pron, base.DIRECTORIO_PRONOSTICOS / f"ecmwf_ifs_ens_025_balcarce_{marca}.csv")
    return pron


def huecos(df: pd.DataFrame, inicio: date, fin: date) -> list[str]:
    esperadas = pd.date_range(inicio, fin); presentes = pd.DatetimeIndex(pd.to_datetime(df["Fecha"], errors="coerce").dropna()).normalize()
    return list(esperadas.difference(presentes).strftime("%Y-%m-%d"))


def validar(df: pd.DataFrame, fin: date) -> None:
    f = pd.to_datetime(df["Fecha"], errors="coerce"); c = df[["TMAX","TMIN","TMEDIA","Prec"]].apply(pd.to_numeric, errors="coerce")
    if df.empty or f.isna().any() or f.duplicated().any() or c.isna().any().any() or (c["TMAX"]<c["TMIN"]).any() or (c["Prec"]<0).any() or huecos(df, base.CAMPANIA_START, fin):
        raise ValueError("La serie meteorológica final no es válida y continua.")
    pron = df["TipoDato"].astype(str).eq("Pronostico")
    for a,b in (("TMAX","TMAX_P50"),("TMIN","TMIN_P50"),("TMEDIA","TMEDIA_P50"),("Prec","Prec_P50")):
        if not np.allclose(pd.to_numeric(df.loc[pron,a]), pd.to_numeric(df.loc[pron,b]), atol=1e-9):
            raise ValueError(f"{a} no coincide con {b}.")
    if (pd.to_numeric(df.loc[pron,"N_miembros"], errors="coerce") < MIN_MIEMBROS).any():
        raise ValueError("El pronóstico tiene menos de 30 miembros válidos.")


def ejecutar() -> pd.DataFrame:
    hoy = base.hoy_argentina(); ayer = hoy - timedelta(days=1)
    obs, estado_siga = base.obtener_siga_dataframe(base.CAMPANIA_START, ayer)
    faltantes = fechas_faltantes(obs, base.CAMPANIA_START, ayer); rs = rangos(faltantes)
    bloques = [cargar_provisional(i,f) for i,f in rs]
    prov = columnas(pd.concat(bloques, ignore_index=True)) if bloques else pd.DataFrame(columns=COLUMNAS)
    pron = cargar_ens(); pron = pron.loc[pd.to_datetime(pron["Fecha"]).dt.date >= hoy].copy()
    todo = columnas(pd.concat([obs,prov,pron], ignore_index=True)); todo["Fecha_dt"] = pd.to_datetime(todo["Fecha"], errors="coerce")
    todo["_p"] = todo["TipoDato"].map({"Observado":0,"Provisional":1,"Pronostico":2}).fillna(9)
    todo = todo.dropna(subset=["Fecha_dt"]).sort_values(["Fecha_dt","_p"]).drop_duplicates("Fecha_dt", keep="first").sort_values("Fecha_dt")
    fin = pd.to_datetime(pron["Fecha"]).max().date(); todo = todo.loc[(todo["Fecha_dt"].dt.date >= base.CAMPANIA_START) & (todo["Fecha_dt"].dt.date <= fin)]
    todo["Fecha"] = todo["Fecha_dt"].dt.strftime("%Y-%m-%d"); todo = columnas(todo.drop(columns=["Fecha_dt","_p"])).reset_index(drop=True)
    validar(todo, fin); base.escribir_csv_atomico(todo, base.ARCHIVO_MAESTRO_DEFAULT)
    estado = {"ejecucion_utc": base.fecha_utc_iso(), "sitio":"Balcarce", "latitud":base.LATITUD, "longitud":base.LONGITUD, "estacion_siga":"A872824", "estado_siga":estado_siga, "ultima_observacion_siga":str(obs["Fecha"].max()), "huecos_siga":[x.isoformat() for x in faltantes], "rangos_provisionales":[{"inicio":i.isoformat(),"fin":f.isoformat()} for i,f in rs], "fuente_provisional":"ECMWF_IFS_HISTORICO" if len(prov) else None, "filas_provisionales":len(prov), "fuente_pronostico":"ECMWF_IFS_ENS_025", "estadistico_operativo":"P50", "inicio_pronostico":str(pron["Fecha"].min()), "fin_pronostico":str(pron["Fecha"].max()), "miembros_validos_min":int(pd.to_numeric(pron["N_miembros"]).min()), "huecos_finales":huecos(todo,base.CAMPANIA_START,fin)}
    base.ARCHIVO_ESTADO.parent.mkdir(parents=True, exist_ok=True); base.ARCHIVO_ESTADO.write_text(json.dumps(estado,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"✅ SIGA={len(obs)}; provisionales={len(prov)}; pronóstico={len(pron)}")
    return todo


if __name__ == "__main__":
    try:
        ejecutar()
    except Exception as error:
        print(f"❌ Error: {error}. No se reemplazó meteo_daily.csv.", file=sys.stderr)
        raise SystemExit(1)
