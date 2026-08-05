# -*- coding: utf-8 -*-
"""Adaptador de despliegue privado para PREDWEEM Balcarce.

El motor científico se conserva en ``app_emergenciacombinado_core.py``. Antes
de ejecutarlo, este módulo sustituye únicamente dependencias públicas internas
por recursos locales, aplica la extinción fisiológica auditada de la cohorte y
valida los activos obligatorios del modelo.
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

    forbidden_reference = "raw.githubusercontent.com/PREDWEEM/LOLIUM_BAL2026"
    if forbidden_reference in source:
        raise PrivateRuntimeError(
            "Persisten referencias al repositorio público en el motor adaptado."
        )

    return source


def verify_private_checkout(base: Path) -> None:
    """Comprueba recursos, adaptación fisiológica y sintaxis sin ejecutar Streamlit."""
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
    )
    missing_fields = [field for field in required_audit_fields if field not in private_source]
    if missing_fields:
        raise PrivateRuntimeError(
            "La adaptación de agotamiento quedó incompleta: "
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
        f"de cohorte a {COHORT_EXHAUSTION_DAYS} días y remanente máximo "
        f"{COHORT_REMAINING_THRESHOLD:.3f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
