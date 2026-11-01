# Campañas de Balcarce: emergencia y clima

Son el **pool de Balcarce** (2014, 2025 y 2026, el mismo del gemelo digital `PREDWEEM/balca_digitaltween`) con que se validó
la alerta y se construye el calendario propio (`calendario_local.py`). La actualización automática no modifica estas carpetas.

| Campaña | Emergencia | Clima |
|---|---|---|
| 2014 | `emergencia_balcarce_2014.csv`: 31 muestreos semanales (10/03–06/10/2014), **porcentaje semanal del total anual** (`PORC_SEMANAL`; `PLM2` es la misma columna para el calendario), digitalizados de Diez de Ulzurrun (2015, XXII Congreso ALAM). Sin cero inicial. Procedencia en `procedencia_balcarce_2014.json`. | `clima_balcarce_2014.csv`: SIGA A872824; faltan los días 16–20/03/2014 y la lluvia del 15/03. |
| 2025 | `emergencia_balcarce_2025.csv`: curva diaria relativa procesada (`emererel2025 balcarce.xlsx` del clasificador de PREDWEEM), del 01/01 al 07/10/2025; no hay conteos originales. | `clima_balcarce_2025.csv`: SIGA A872824, 01/01–01/10/2025. |
| 2026 | `emergencia_balcarce_2026_original.xlsx` (planilla original, igual a `VALIDA (1).xlsx`) y `emergencia_balcarce_2026.csv`: 18 conteos del 12/03 (cero inicial) al 15/08/2026, 8280 plántulas/m², con fracción y acumulada. | `clima_balcarce_2026.csv`: copia de `meteo_daily.csv` al cierre (SIGA, 6 días provisionales ECMWF). |

`siga_balcarce_A872824_original.xls` es la planilla SIGA–INTA de la EEA Balcarce aportada por el autor (07/11/2006 – 31/10/2026);
`siga_balcarce_A872824_diario.csv` es su extracto (Fecha, TMAX, TMIN, Prec) usado para el clima 2025.

**Para sumar una campaña**, cree la carpeta `<año>/` con `emergencia_balcarce_<año>.csv` (al menos `Fecha` y `PLM2`) una vez
cerrada; el calendario la incorpora solo (la campaña en curso se excluye).

## Huellas SHA-256

| Archivo | SHA-256 |
|---|---|
| `2014/clima_balcarce_2014.csv` | `a961ada15046f4409c55650dffd65e85b400c3278ef44571755be98b2fa932cf` |
| `2014/emergencia_balcarce_2014.csv` | `75124adeff24e1e69a9c046146eb46129f17ff865593b9861ada1da79e832f9c` |
| `2014/procedencia_balcarce_2014.json` | `15523be67b1dd07bfe0a4a63de23f67fa2d637497a55778b4d1adf3817b5ce2a` |
| `2025/clima_balcarce_2025.csv` | `c2cf353015fbe8048da5b5100458c4e29f419bad1fb64d225908a884119ae83a` |
| `2025/emergencia_balcarce_2025.csv` | `fff0a2ac0c267a2c43af2357bb35b875ead3981ead901c757945aa601e2a02f7` |
| `2026/clima_balcarce_2026.csv` | `d2dc53815afb3ab113962c26375ab2ed38a5b91aa6af1df2c8859b54cc0018ee` |
| `2026/emergencia_balcarce_2026.csv` | `1ee1059117a08666a4463a6fcdfa56cb43273d25a6cead1d2824e98208509163` |
| `2026/emergencia_balcarce_2026_original.xlsx` | `f7aca3b3031eb3d16cdbb05302cc614debbb01675f8f67e755e86aaa97ffdf8d` |
| `siga_balcarce_A872824_diario.csv` | `c055cae526a991b50186713f7a752a40488ff4bc0676694355da973742f9907a` |
| `siga_balcarce_A872824_original.xls` | `4bad31bf66eb45fcfb56c8a08f9c8425864d126d36d250d522f8ed4445e51307` |
