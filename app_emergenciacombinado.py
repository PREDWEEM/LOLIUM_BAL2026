# -*- coding: utf-8 -*-
"""
PREDWEEM Lolium — Balcarce.

La página muestra la alerta de grandes flujos de Lolium del paquete ``lolium-comun`` (probabilidad de gran flujo en
los próximos 7 días, qué hacer esta semana, ventana del graminicida de barbecho, residual a la siembra y flujos tardíos)
con el clima diario del repositorio (``meteo_daily.csv``).

El motor PREDWEEM anterior (red neuronal y balance hídrico, ``app_emergenciacombinado_core.py`` y sus modelos) ya no se
ejecuta: su inicio estimado de la emergencia erró 12–14 días en promedio y no mejoraba la alerta. Sus archivos quedan
en el repositorio solo como referencia.
"""
import importlib
from pathlib import Path

import pandas as pd
import streamlit as st

# Control de acceso (ingreso con Google y usuarios aprobados). Inactivo hasta configurar los secretos [acceso] y [auth].
from acceso_predweem import mostrar_sesion, requerir_acceso
from lolium_comun import pagina

BASE = Path(__file__).resolve().parent

requerir_acceso("Balcarce")
pagina.encabezado("🌾 PREDWEEM LOLIUM — BALCARCE (BA) lat=-37.7664 lon=-58.2999", "PREDWEEM BALCARCE")
parametros = pagina.barra_lateral(BASE, "Balcarce")
meteo = pagina.cargar_meteo(BASE, "https://raw.githubusercontent.com/PREDWEEM/LOLIUM_BAL2026/main/meteo_daily.csv")

NOTA_BALCARCE = (
    "**Ajustes de Balcarce.** En Balcarce la emergencia se concentra más que en el calendario de referencia regional (mitad de la campaña hacia el "
    "15/03 y 90 % entre fines de marzo y principios de mayo; en 2026, el 76 % emergió entre el 12 y el 20/03). Por eso la "
    "alerta general se adapta en dos puntos: (1) la señal de calendario y la curva acumulada usan el calendario de "
    "Balcarce (pool 2014, 2025 y 2026 del gemelo digital, sin la campaña en curso; `data/campanias/`); (2) desde la fecha de "
    "las primeras plántulas, la probabilidad se multiplica por el agotamiento de la cohorte con la forma Weibull del motor "
    "de Balcarce (τ 3,57 días, β 0,487) e intensidad 0,4: a los 7 días queda el 70 %, a los 30 días el 62 %.\n\n"
    "**Validación en Balcarce** (2014, 2025 y 2026 con clima SIGA de la EEA Balcarce, cada campaña con el calendario de las "
    "otras; 82 intervalos semanales, 10 con gran flujo). Con la fecha de primeras plántulas: AUC 0,96; 9 de 10 grandes flujos en "
    "*Alerta* y 6 falsas alarmas (8 % de las semanas sin gran flujo). La alerta general sin ajustes: AUC 0,94, 9 de 10 y 19 "
    "falsas alarmas (seguía alertando después del primer gran flujo). Con la intensidad del motor (0,95) no había falsas "
    "alarmas, pero solo detectaba 4 de 10: en 2025 los grandes flujos siguieron cinco semanas después del primero.\n\n"
    "**Límites en Balcarce.** Tres campañas; la intensidad 0,4 se eligió con ellas. 2025 es una curva procesada (sin conteos "
    "originales) y en 2014 faltan datos de clima del 15 al 21/03. El clima operativo es SIGA–INTA Balcarce."
)

from calendario_local import construir_calendario

# calendario propio del sitio, sin la campaña en curso (su total todavía no se conoce)
_anio_campania = int(pd.to_datetime(meteo["Fecha"], errors="coerce").max().year) if meteo is not None else None
_calendario_local = construir_calendario(excluir=(_anio_campania,)) if _anio_campania else None

# forma del agotamiento de la cohorte calibrada en Balcarce (tau 3,57 días; beta 0,487); intensidad atenuada para
# la alerta (validación 2014, 2025 y 2026)
AGOTAMIENTO_BALCARCE = dict(tau=3.5656, beta=0.48684, intensidad=0.4)

_resultados_alerta = None
if meteo is not None and not meteo.empty:
    try:
        import alerta_lolmu as _alerta_lolmu
        import visualizacion_alerta_lolmu as _vis_alerta

        # Streamlit conserva en memoria los módulos ya importados entre ejecuciones: tras una actualización del
        # repositorio, recargarlos evita usar una versión vieja
        importlib.reload(_alerta_lolmu)
        importlib.reload(_vis_alerta)
        _resultados_alerta = _vis_alerta.mostrar_alerta_lolmu(
            meteo,
            **parametros,
    tope_hasta_ultimo_cero=True,  # semanas ya cerradas por un conteo posterior en cero: probabilidad 0
    curva_desde_ultimo_cero=True,  # la curva acumulada arranca a mitad de camino entre el último cero y el primer conteo con plántulas
    curva_desde_primeras=True,  # con primeras plántulas, la curva del calendario propio arranca ese día
    localidad="Balcarce",
    nota_sitio=NOTA_BALCARCE,
    calendario_local=_calendario_local,
    calendario_en_alerta=True,
    agotamiento=AGOTAMIENTO_BALCARCE,
        )
    except Exception as _error_alerta:  # noqa: BLE001
        st.warning(f"No se pudo calcular la alerta: {_error_alerta}")

pagina.descarga_excel(_resultados_alerta, "Balcarce", "descarga_excel_resultados_final_balcarce")
mostrar_sesion()
