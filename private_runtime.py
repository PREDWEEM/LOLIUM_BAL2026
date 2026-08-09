# -*- coding: utf-8 -*-
"""Adaptador de despliegue privado para PREDWEEM Balcarce.

El motor científico se conserva en ``app_emergenciacombinado_core.py``. Antes
de ejecutarlo, este módulo sustituye únicamente dependencias públicas internas
por recursos locales, aplica la extinción fisiológica auditada de la cohorte,
mejora la visualización del horizonte meteorológico disponible y valida los
activos obligatorios del modelo.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


COHORT_EXHAUSTION_DAYS = 110
COHORT_REMAINING_THRESHOLD = 0.005

REQUIRED_PRIVATE_ASSETS = (
    "IW.npy",
    "LW.npy",
    "bias_IW.npy",
    "bias_out.npy",
    "modelo_clusters_k3.pkl",
    "meteo_daily.csv",
    "fondo_predweem_v3.png",
    "logo_predweem.svg",
)


class PrivateRuntimeError(RuntimeError):
    """Indica que la adaptación privada no puede aplicarse con seguridad."""


def _replace_once(
    source: str,
    pattern: str,
    replacement: str,
    description: str,
    *,
    flags: int = 0,
) -> str:
    updated, count = re.subn(
        pattern,
        lambda _match: replacement,
        source,
        count=1,
        flags=flags,
    )
    if count != 1:
        raise PrivateRuntimeError(
            f"No se pudo aplicar la adaptación privada: {description}. "
            "Revise si cambió app_emergenciacombinado_core.py."
        )
    return updated


def build_private_core_source(core_path: Path) -> str:
    """Devuelve el motor preparado para trabajar solo con archivos locales."""
    source = core_path.read_text(encoding="utf-8")

    source = _replace_once(
        source,
        r'set_bg_hack\("fondo_predweem_v3\.png"\)',
        'set_bg_hack(str(BASE / "fondo_predweem_v3.png"))',
        "carga local del fondo",
    )

    source = _replace_once(
        source,
        r"^def load_data\(file_uploader, default_name\):"
        r".*?(?=^def |\Z)",
        '''def load_data(file_uploader, default_name):
    """Carga un archivo aportado por el usuario o desde el checkout privado."""
    if file_uploader:
        suffix = Path(file_uploader.name).suffix.lower()
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(file_uploader)
        return pd.read_csv(file_uploader)

    local_candidates = (
        BASE / f"{default_name}.csv",
        BASE / f"{default_name}.xlsx",
        BASE / f"{default_name}.xls",
    )
    for candidate in local_candidates:
        if candidate.is_file():
            if candidate.suffix.lower() in {".xlsx", ".xls"}:
                return pd.read_excel(candidate)
            return pd.read_csv(candidate)

    st.warning(
        f"No se encontró un archivo local para '{default_name}'. "
        "Verifique que esté incluido en el checkout privado."
    )
    return None


''',
        "carga local de datos",
        flags=re.DOTALL | re.MULTILINE,
    )

    source = _replace_once(
        source,
        r'st\.sidebar\.image\("https://raw\.githubusercontent\.com/PREDWEEM/LOLIUM_BAL2026/main/logo\.png", width="stretch"\)',
        'st.sidebar.image(str(BASE / "logo_predweem.svg"), width="stretch")',
        "carga local del logotipo",
    )

    source = _replace_once(
        source,
        r'''    factor_base = np\.exp\(-np\.power\(dias_desde_pico / tau_dias, beta\)\)\n'''
        r'''    factor_base = np\.where\(pd\.to_datetime\(df\["Fecha"\]\) < fecha_pico, 1\.0, factor_base\)\n'''
        r'''    factor_aplicado = 1\.0 - intensidad \* \(1\.0 - factor_base\)\n\n'''
        r'''    df\["Dias_Desde_Primer_Pico"\] = dias_desde_pico\n'''
        r'''    df\["Factor_Decaimiento_Base"\] = factor_base\n'''
        r'''    df\["Factor_Decaimiento"\] = factor_aplicado''',
        f'''    factor_base = np.exp(-np.power(dias_desde_pico / tau_dias, beta))
    factor_base = np.where(pd.to_datetime(df["Fecha"]) < fecha_pico, 1.0, factor_base)
    factor_aplicado = 1.0 - intensidad * (1.0 - factor_base)

    # Extinción fisiológica específica de Balcarce. Una vez transcurridos
    # {COHORT_EXHAUSTION_DAYS} días desde el primer pico y cuando el remanente
    # Weibull es <= {COHORT_REMAINING_THRESHOLD:.3f}, la cohorte se considera
    # agotada y no puede ser reactivada por lluvias tardías.
    cohorte_agotada = (
        (dias_desde_pico >= {float(COHORT_EXHAUSTION_DAYS):.1f})
        & (factor_base <= {COHORT_REMAINING_THRESHOLD:.3f})
    )
    factor_aplicado = np.where(cohorte_agotada, 0.0, factor_aplicado)

    df["Dias_Desde_Primer_Pico"] = dias_desde_pico
    df["Factor_Decaimiento_Base"] = factor_base
    df["Cohorte_Agotada"] = cohorte_agotada
    df["Criterio_Agotamiento_Dias"] = {COHORT_EXHAUSTION_DAYS}
    df["Criterio_Remanente_Maximo"] = {COHORT_REMAINING_THRESHOLD:.3f}
    df["Factor_Decaimiento"] = factor_aplicado''',
        "extinción fisiológica de la cohorte",
    )

    source = _replace_once(
        source,
        r'''        with col_main:\n            fig_emer = go\.Figure\(\)\n''',
        '''        with col_main:
            fig_emer = go.Figure()

            # Delimita explícitamente el horizonte meteorológico que ya existe
            # en meteo_daily.csv. No agrega días ni extrapola el pronóstico.
            mascara_pronostico_graf = pd.Series(False, index=df.index)
            if "TIPODATO" in df.columns:
                mascara_pronostico_graf = (
                    df["TIPODATO"].astype(str).str.lower().eq("pronostico")
                )
            if not bool(mascara_pronostico_graf.any()):
                hoy_graf = pd.Timestamp.now().normalize()
                mascara_pronostico_graf = pd.to_datetime(df["Fecha"]) >= hoy_graf

            fecha_inicio_pronostico_graf = None
            fecha_fin_pronostico_graf = None
            if bool(mascara_pronostico_graf.any()):
                fecha_inicio_pronostico_graf = pd.Timestamp(
                    df.loc[mascara_pronostico_graf, "Fecha"].min()
                )
                fecha_fin_pronostico_graf = pd.Timestamp(
                    df.loc[mascara_pronostico_graf, "Fecha"].max()
                )
                fig_emer.add_vrect(
                    x0=fecha_inicio_pronostico_graf,
                    x1=fecha_fin_pronostico_graf + timedelta(days=1),
                    fillcolor="rgba(37, 99, 235, 0.055)",
                    layer="below",
                    line_width=0,
                )
                fig_emer.add_annotation(
                    x=fecha_fin_pronostico_graf,
                    xref="x",
                    y=0.985,
                    yref="paper",
                    text=(
                        "Fin del pronóstico disponible<br>"
                        + fecha_fin_pronostico_graf.strftime("%d-%m-%Y")
                    ),
                    showarrow=False,
                    xanchor="right",
                    yanchor="top",
                    bgcolor="rgba(239,246,255,0.96)",
                    bordercolor="rgba(37,99,235,0.35)",
                    borderwidth=1,
                    borderpad=4,
                    font=dict(size=11, color="#1E3A8A"),
                )
''',
        "delimitación visual del horizonte de pronóstico",
    )

    source = _replace_once(
        source,
        r'''            # Serie observada\.\n''',
        '''            # Tramo futuro superpuesto para distinguir visualmente el
            # pronóstico de la parte ya observada/provisional de la campaña.
            if bool(mascara_pronostico_graf.any()):
                fig_emer.add_trace(
                    go.Scatter(
                        x=df.loc[mascara_pronostico_graf, "Fecha"],
                        y=df.loc[mascara_pronostico_graf, "EMERREL_LOG"],
                        mode="lines+markers",
                        name="Pronóstico de emergencia disponible",
                        line=dict(color="#2563EB", width=3.0, dash="dash"),
                        marker=dict(size=5, color="#2563EB"),
                        hovertemplate=(
                            "<b>%{x|%d-%m-%Y}</b><br>"
                            "Pronóstico: %{y:.3f}<extra></extra>"
                        ),
                    )
                )

            # Serie observada.
''',
        "tramo visual del pronóstico de emergencia",
    )

    source = _replace_once(
        source,
        r'''            fig_emer\.update_xaxes\(\n                rangeslider_visible=False,\n                fixedrange=False,\n            \)''',
        '''            fig_emer.update_xaxes(
                range=[
                    pd.Timestamp(df["Fecha"].min()),
                    pd.Timestamp(df["Fecha"].max()) + timedelta(days=1),
                ],
                rangeslider_visible=False,
                fixedrange=False,
            )''',
        "extensión del eje X hasta la última fecha disponible",
    )

    source = _replace_once(
        source,
        r'''            if fecha_inicio_ventana:\n                st\.success\(''',
        '''            if bool(mascara_pronostico_graf.any()):
                df_pronostico_graf = df.loc[
                    mascara_pronostico_graf,
                    ["Fecha", "EMERREL", "EMERREL_LOG"],
                ].copy()
                df_pronostico_graf["Fecha"] = pd.to_datetime(
                    df_pronostico_graf["Fecha"], errors="coerce"
                )
                df_pronostico_graf = (
                    df_pronostico_graf.dropna(subset=["Fecha"])
                    .sort_values("Fecha")
                    .reset_index(drop=True)
                )

                if not df_pronostico_graf.empty:
                    inicio_zoom = pd.Timestamp(df_pronostico_graf["Fecha"].min())
                    fin_zoom = pd.Timestamp(df_pronostico_graf["Fecha"].max())
                    st.markdown(
                        "##### 🔭 Pronóstico de emergencia — horizonte completo"
                    )
                    st.caption(
                        f"Horizonte meteorológico vigente: "
                        f"{len(df_pronostico_graf)} días, "
                        f"del {inicio_zoom.strftime('%d-%m-%Y')} al "
                        f"{fin_zoom.strftime('%d-%m-%Y')}. "
                        "No se agregan ni extrapolan días."
                    )

                    fig_pronostico = go.Figure()
                    fig_pronostico.add_trace(
                        go.Scatter(
                            x=df_pronostico_graf["Fecha"],
                            y=df_pronostico_graf["EMERREL"],
                            mode="lines+markers+text",
                            name="EMERREL pronosticada",
                            text=[
                                f"{valor:.3f}"
                                for valor in df_pronostico_graf["EMERREL"]
                            ],
                            textposition="top center",
                            cliponaxis=False,
                            line=dict(color="#2563EB", width=3.0),
                            marker=dict(size=9, color="#2563EB"),
                            hovertemplate=(
                                "<b>%{x|%d-%m-%Y}</b><br>"
                                "EMERREL: %{y:.4f}<extra></extra>"
                            ),
                        )
                    )
                    fig_pronostico.update_layout(
                        title=dict(
                            text="Detalle diario del pronóstico de emergencia",
                            x=0.0,
                            xanchor="left",
                        ),
                        xaxis=dict(
                            title="Fecha",
                            tickmode="array",
                            tickvals=df_pronostico_graf["Fecha"],
                            ticktext=df_pronostico_graf["Fecha"].dt.strftime(
                                "%d-%m"
                            ),
                            range=[
                                inicio_zoom - timedelta(hours=12),
                                fin_zoom + timedelta(hours=12),
                            ],
                            showgrid=False,
                        ),
                        yaxis=dict(
                            title="EMERREL diaria",
                            rangemode="tozero",
                            showgrid=True,
                            gridcolor="rgba(148, 163, 184, 0.25)",
                        ),
                        height=360,
                        margin=dict(l=65, r=25, t=55, b=65),
                        hovermode="x unified",
                        showlegend=False,
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF",
                    )
                    st.plotly_chart(
                        fig_pronostico,
                        width="stretch",
                        key="balcarce_pronostico_emergencia_horizonte_completo",
                        config={"displaylogo": False, "responsive": True},
                    )

            if fecha_inicio_ventana:
                st.success(''',
        "panel diario del horizonte completo de pronóstico",
    )

    forbidden_reference = "raw.githubusercontent.com/PREDWEEM/LOLIUM_BAL2026"
    if forbidden_reference in source:
        raise PrivateRuntimeError(
            "Persisten referencias al repositorio público en el motor adaptado."
        )

    return source


def verify_private_checkout(base: Path) -> None:
    """Comprueba recursos, adaptación fisiológica, horizonte visual y sintaxis."""
    missing = [name for name in REQUIRED_PRIVATE_ASSETS if not (base / name).is_file()]
    if missing:
        raise PrivateRuntimeError(
            "Faltan recursos obligatorios: " + ", ".join(missing)
        )

    core_path = base / "app_emergenciacombinado_core.py"
    if not core_path.is_file():
        raise PrivateRuntimeError(
            "No se encontró app_emergenciacombinado_core.py en el checkout."
        )

    private_source = build_private_core_source(core_path)
    required_audit_fields = (
        'df["Cohorte_Agotada"]',
        'df["Criterio_Agotamiento_Dias"]',
        'df["Criterio_Remanente_Maximo"]',
        'name="Pronóstico de emergencia disponible"',
        'text=(\n                        "Fin del pronóstico disponible<br>"',
        'pd.Timestamp(df["Fecha"].max()) + timedelta(days=1)',
        'Pronóstico de emergencia — horizonte completo',
        'key="balcarce_pronostico_emergencia_horizonte_completo"',
    )
    missing_fields = [field for field in required_audit_fields if field not in private_source]
    if missing_fields:
        raise PrivateRuntimeError(
            "La adaptación privada quedó incompleta: "
            + ", ".join(missing_fields)
        )
    compile(private_source, str(core_path), "exec")


def main() -> int:
    base = Path(__file__).resolve().parent
    try:
        verify_private_checkout(base)
    except PrivateRuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "OK: Balcarce está preparado para despliegue privado con agotamiento "
        f"de cohorte a {COHORT_EXHAUSTION_DAYS} días, remanente máximo "
        f"{COHORT_REMAINING_THRESHOLD:.3f}, horizonte anual visible y panel "
        "diario independiente para todo el pronóstico disponible."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
