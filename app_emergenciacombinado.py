# -*- coding: utf-8 -*-
"""
Punto de entrada de PREDWEEM Balcarce.

La aplicación científica original se conserva en ``app_emergenciacombinado_core.py``. Antes de ejecutarla:

* ``build_private_core_source`` la prepara para el checkout privado (carga local de datos y modelos, agotamiento
  de la cohorte a los 110 días y panel del horizonte de pronóstico);
* ``parchear_visualizacion_intensidad_relativa`` ajusta la escala de su gráfico principal;
* se retiran de la página los elementos que reemplaza la alerta de flushes del final: mapa de riesgo, las pestañas
  (Monitor de decisión —con la dinámica principal, los mensajes de inicio y control y el indicador de tiempo
  térmico—, Precipitaciones y suelo, Análisis estratégico y Bio-calibración), la leyenda de versión, la sección
  "Datos del lote" (se usa el clima SIGA del repositorio y la cobertura de rastrojo por defecto, 10 %), la imagen de
  fondo (reemplazada por un fondo liso claro) y, en la barra lateral, los parámetros del motor (quedan en sus
  valores por defecto, incluido el decaimiento Weibull post-pico calibrado para Balcarce), sus avisos, el
  calibrador 2D y el botón del reporte del motor; la barra lateral conserva los parámetros de la ventana de control.

El motor sigue calculando como antes: su primer pico se usa como inicio estimado del reloj térmico hasta que se
informa la fecha de las primeras plántulas.

La alerta (``alerta_lolmu.py``) es la calibrada con 17 campañas de Bordenave, con dos ajustes propios de Balcarce,
donde la emergencia se concentra en un primer flush y después decae con fuerza:

1. la señal de calendario usa el calendario de Balcarce (pool 2014, 2025 y 2026; ``calendario_local.py``), que
   también dibuja la curva acumulada;
2. desde la fecha de las primeras plántulas, la probabilidad se multiplica por el agotamiento Weibull de la cohorte
   con la forma del motor de Balcarce (tau 3,57 días; beta 0,487) e intensidad atenuada 0,4 (la del motor, 0,95,
   suprimía los flushes siguientes al primero en 2025).
"""
from pathlib import Path

from private_runtime import build_private_core_source
from visualizacion_intensidad_relativa import parchear_visualizacion_intensidad_relativa

_CORE_APP = Path(__file__).with_name("app_emergenciacombinado_core.py")
_core_source = build_private_core_source(_CORE_APP)
_core_source = parchear_visualizacion_intensidad_relativa(_core_source)


def _reemplazar(origen: str, viejo: str, nuevo: str) -> str:
    if viejo not in origen:
        raise RuntimeError(f"No se encontró el bloque a reemplazar en el motor: {viejo[:70]!r}")
    return origen.replace(viejo, nuevo, 1)


def _cortar(origen: str, desde: str, hasta: str, nuevo: str) -> str:
    """Reemplaza el tramo [desde, hasta) del motor."""
    ini = origen.find(desde)
    fin = origen.find(hasta, ini) if ini >= 0 else -1
    if ini < 0 or fin < ini:
        raise RuntimeError(f"No se encontró el tramo a retirar del motor: {desde[:70]!r}")
    return origen[:ini] + nuevo + origen[fin:]


_FONDO_CSS = """<style>
.stApp { background: #f4f6f3; }
[data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] { background: transparent; }
[data-testid="stSidebar"] { background-color: #e8f3ea; border-right: 1px solid #cfe3d3; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #14532d !important; }
[data-testid="stCaptionContainer"], .stCaption { color: #4b5563 !important; }
h1, h2, h3, h4 { color: #1f2937; }
</style>"""

# mapa de riesgo del motor (el cálculo no cambia)
_core_source = _reemplazar(_core_source, "st.plotly_chart(go.Figure(data=go.Heatmap(", "_omitir_grafico(go.Figure(data=go.Heatmap(")
# la regla "header {visibility: hidden;}" ocultaba también el encabezado de los calendarios desplegables
_core_source = _reemplazar(_core_source, "    header {visibility: hidden;}", '    header[data-testid="stHeader"] {visibility: hidden;}')
# fondo liso claro en lugar de la imagen de plantas (mejor contraste)
_core_source = _reemplazar(_core_source, 'set_bg_hack(str(BASE / "fondo_predweem_v3.png"))', "st.markdown(_FONDO_CSS, unsafe_allow_html=True)")
# leyenda de versión del motor
_core_source = _reemplazar(
    _core_source,
    'st.caption("Balcarce · VISUAL V3 · ventana eficiente verde · exportación PNG de alta resolución")',
    "pass",
)

# sección "Datos del lote": clima SIGA del repositorio, sin conteos del formato anterior, cobertura por defecto (10 %)
_core_source = _cortar(
    _core_source,
    'with st.expander("📂 1. Datos del Lote", expanded=True):',
    "# Carga de datos antes de construir el optimizador del sidebar",
    "archivo_meteo = None\narchivo_campo = None\ncobertura_pct = 10\nke_val, mod_termico = parametros_superficie(cobertura_pct)\n\n",
)
_core_source = _reemplazar(_core_source, 'df_campo_raw = load_data(archivo_campo, "BALCARCE_campo")', "df_campo_raw = None")

# barra lateral: solo la ventana de control; los parámetros del motor quedan en sus valores por defecto
_core_source = _cortar(
    _core_source,
    'st.sidebar.markdown("## ⚙️ 2. Fisiología y Logística")',
    "# ---------------------------------------------------------\n# 6. MOTOR DE CÁLCULO",
    '''st.sidebar.markdown("## ⚙️ Ventana de control")
st.sidebar.caption("Tiempo térmico sobre la temperatura media del aire y objetivos de la ventana post-emergente.")
col_t1, col_t2 = st.sidebar.columns(2)
with col_t1: t_base_val = st.number_input("T Base", value=2.0, step=0.5)
with col_t2: t_opt_max = st.number_input("T Óptima Max", value=20.0, step=1.0)
t_critica = st.sidebar.slider("T Crítica (Stop)", 26.0, 42.0, 30.0)
st.sidebar.markdown("**Objetivos (°Cd)**")
dga_optimo = st.sidebar.number_input("TT Control Post-emergente (°Cd)", value=600, step=10)
dga_critico = st.sidebar.number_input("Límite Ventana (°Cd)", value=800, step=10)

# parámetros del motor PREDWEEM en sus valores por defecto (controles retirados de la página)
umbral_er = 0.0001
umbral_termoinhibicion = 24.0
umbral_choque_hidrico = 45.0
activar_decaimiento = True
intensidad_decaimiento = float(DECAY_INTENSITY_FIT)
tau_decaimiento = float(DECAY_TAU_DAYS_FIT)
beta_decaimiento = float(DECAY_BETA_FIT)
intensidad_decaimiento_aplicada = intensidad_decaimiento
residualidad = 0
w_max_val = 10.0
exponente_kr = 0.0

''',
)

# pestañas del motor (incluyen la dinámica principal, los mensajes de inicio y control y el indicador térmico)
_core_source = _cortar(_core_source, "    tab1, tab2, tab3, tab4 = st.tabs(", "    output = io.BytesIO()", "")
# botón lateral del reporte del motor: la descarga final reúne los resultados de la alerta
_core_source = _reemplazar(_core_source, 'st.sidebar.download_button("📥 Descargar Reporte Completo"', '_omitir_grafico("📥 Descargar Reporte Completo"')


def _omitir_grafico(*_args, **_kwargs):
    """No dibuja el elemento (se conservan la figura y todos los cálculos del motor)."""
    return None


exec(
    compile(_core_source, str(_CORE_APP), "exec"),
    globals(),
)

# forma del agotamiento del motor de Balcarce; intensidad atenuada para la alerta (validación 2014, 2025 y 2026)
AGOTAMIENTO_BALCARCE = dict(
    tau=float(globals().get("DECAY_TAU_DAYS_FIT", 3.5656)),
    beta=float(globals().get("DECAY_BETA_FIT", 0.48684)),
    intensidad=0.4,
)

NOTA_BALCARCE = (
    "**Ajustes de Balcarce.** En Balcarce la emergencia se concentra más que en Bordenave (mitad de la campaña hacia el "
    "15/03 y 90 % entre fines de marzo y principios de mayo; en 2026, el 76 % emergió entre el 12 y el 20/03). Por eso la "
    "alerta de Bordenave se adapta en dos puntos: (1) la señal de calendario y la curva acumulada usan el calendario de "
    "Balcarce (pool 2014, 2025 y 2026 del gemelo digital, sin la campaña en curso; `data/campanias/`); (2) desde la fecha de "
    "las primeras plántulas, la probabilidad se multiplica por el agotamiento de la cohorte con la forma Weibull del motor "
    "de Balcarce (τ 3,57 días, β 0,487) e intensidad 0,4: a los 7 días queda el 70 %, a los 30 días el 62 %.\n\n"
    "**Validación en Balcarce** (2014, 2025 y 2026 con clima SIGA de la EEA Balcarce, cada campaña con el calendario de las "
    "otras; 82 intervalos semanales, 10 con gran flujo). Con la fecha de primeras plántulas: AUC 0,96; 9 de 10 grandes flujos en "
    "*Alerta* y 6 falsas alarmas (8 % de las semanas sin gran flujo). La alerta de Bordenave sin ajustes: AUC 0,94, 9 de 10 y 19 "
    "falsas alarmas (seguía alertando después del primer gran flujo). Con la intensidad del motor (0,95) no había falsas "
    "alarmas, pero solo detectaba 4 de 10: en 2025 los grandes flujos siguieron cinco semanas después del primero.\n\n"
    "**Límites en Balcarce.** Tres campañas; la intensidad 0,4 se eligió con ellas. 2025 es una curva procesada (sin conteos "
    "originales) y en 2014 faltan datos de clima del 15 al 21/03. El clima operativo es SIGA–INTA Balcarce."
)

# Alerta de flushes (independiente del motor científico; no modifica sus resultados)
if "df_meteo_raw" in globals() and isinstance(df_meteo_raw, pd.DataFrame) and not df_meteo_raw.empty:
    st.divider()
    try:
        from calendario_local import construir_calendario
        import importlib

        import alerta_lolmu as _alerta_lolmu
        import visualizacion_alerta_lolmu as _vis_alerta

        # Streamlit conserva en memoria los módulos ya importados entre ejecuciones: tras una actualización del
        # repositorio, recargarlos evita usar una versión vieja
        importlib.reload(_alerta_lolmu)
        importlib.reload(_vis_alerta)
        mostrar_alerta_lolmu = _vis_alerta.mostrar_alerta_lolmu

        # calendario de Balcarce, sin la campaña en curso (su total todavía no se conoce)
        _anio_campania = int(pd.to_datetime(df_meteo_raw["Fecha"], errors="coerce").max().year)
        _calendario_local = construir_calendario(excluir=(_anio_campania,))
        _idx_pico = globals().get("idx_primer_pico")
        _inicio_predicho = (
            df.loc[_idx_pico, "Fecha"]
            if _idx_pico is not None and "df" in globals() and isinstance(df, pd.DataFrame) and _idx_pico in df.index
            else globals().get("fecha_inicio_ventana")
        )
        _resultados_alerta = mostrar_alerta_lolmu(
            df_meteo_raw,
            inicio_predicho=_inicio_predicho,
            t_base=float(globals().get("t_base_val", 2.0)),
            t_opt=float(globals().get("t_opt_max", 20.0)),
            t_crit=float(globals().get("t_critica", 30.0)),
            tt_control=float(globals().get("dga_optimo", 600.0)),
            tt_limite=float(globals().get("dga_critico", 800.0)),
            tope_hasta_ultimo_cero=True,  # semanas ya cerradas por un conteo posterior en cero: probabilidad 0
            curva_desde_ultimo_cero=True,  # la curva acumulada arranca a mitad de camino entre el último cero y el primer conteo con plántulas
            localidad="Balcarce",
            nota_sitio=NOTA_BALCARCE,
            calendario_local=_calendario_local,
            calendario_en_alerta=True,
            agotamiento=AGOTAMIENTO_BALCARCE,
        )
    except Exception as _error_alerta:  # noqa: BLE001
        st.warning(f"No se pudo calcular la alerta: {_error_alerta}")


def _escribir_hoja(writer, dataframe, nombre):
    """Escribe una hoja y aplica un formato básico de lectura."""
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return
    dataframe.to_excel(writer, sheet_name=nombre, index=False)
    hoja = writer.sheets[nombre]
    ultima_columna = max(0, len(dataframe.columns) - 1)
    hoja.freeze_panes(1, 0)
    hoja.autofilter(0, 0, len(dataframe), ultima_columna)
    hoja.set_column(0, ultima_columna, 18)


# Descarga final: los resultados que muestra la app (alerta, emergencia acumulada y ventana de control)
_resultados_alerta = globals().get("_resultados_alerta")
if isinstance(_resultados_alerta, dict) and _resultados_alerta:
    reporte_excel_final = io.BytesIO()
    with pd.ExcelWriter(reporte_excel_final, engine="xlsxwriter", datetime_format="dd/mm/yyyy", date_format="dd/mm/yyyy") as writer:
        for _hoja, _tabla in _resultados_alerta.items():
            _escribir_hoja(writer, _tabla, _hoja)
    reporte_excel_final.seek(0)
    _emision = _resultados_alerta["Resumen"].set_index("Indicador")["Valor"].get("Fecha de emisión", "")

    st.divider()
    st.subheader("📥 Descarga de resultados")
    st.caption(
        "Excel con los resultados que muestra la app para la fecha de emisión elegida: resumen (nivel y probabilidad de "
        "gran flujo, inicio y ventana de control 600–800 °Cd, emergencia acumulada esperada), alerta semanal, emergencia "
        "acumulada con su rango, tiempo térmico diario desde el inicio, conteos usados, clima, parámetros y validación."
    )
    st.download_button(
        label="📊 Descargar resultados en Excel",
        data=reporte_excel_final.getvalue(),
        file_name=f"PREDWEEM_Lolium_Balcarce_alerta_{str(_emision).replace('/', '-') or 'resultados'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key="descarga_excel_resultados_final_balcarce",
    )
