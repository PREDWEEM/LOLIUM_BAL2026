# Preparación para repositorio privado

Este repositorio fue acondicionado para ejecutarse desde un checkout privado sin depender de archivos servidos desde `raw.githubusercontent.com`.

## Configuración de Streamlit

- Repositorio: `PREDWEEM/LOLIUM_BAL2026`
- Rama: `main`
- Archivo principal: `app_emergenciacombinado.py`

Antes de cambiar la visibilidad, autorice Streamlit Community Cloud para acceder a los repositorios privados de la cuenta `PREDWEEM`.

## Recursos obligatorios

La aplicación necesita en la raíz del checkout:

- `app_emergenciacombinado.py`
- `app_emergenciacombinado_core.py`
- `private_runtime.py`
- `IW.npy`
- `LW.npy`
- `bias_IW.npy`
- `bias_out.npy`
- `modelo_clusters_k3.pkl`
- `meteo_daily.csv`
- `fondo_predweem_v3.png`
- `logo_predweem.svg`

Los datos de validación de campo son opcionales y pueden cargarse desde la interfaz.

## Verificación previa

1. Ejecutar el workflow **Verificar despliegue privado**.
2. Confirmar que todos los pasos terminen correctamente.
3. Ejecutar manualmente **Actualizar SIGA Balcarce y ECMWF ENS**.
4. Verificar que el workflow pueda actualizar `meteo_daily.csv` o informar que no hay cambios.
5. Confirmar que la aplicación Streamlit cargue datos, modelos, fondo y logotipo.

## Cambio de visibilidad

En GitHub:

1. Abrir **Settings**.
2. Ingresar en **General**.
3. Buscar **Danger Zone**.
4. Seleccionar **Change repository visibility**.
5. Cambiar de `Public` a `Private`.

## Verificación posterior

Después de privatizar:

1. Reiniciar o redeployar la aplicación en Streamlit.
2. Ejecutar nuevamente los dos workflows.
3. Confirmar que la actualización meteorológica pueda hacer commit y push sobre `main`.
4. Revisar los logs de Streamlit ante cualquier archivo faltante.

## Seguridad

- No guardar claves, tokens o credenciales dentro del código.
- Utilizar GitHub Secrets o Streamlit Secrets.
- Mantener los pesos, parámetros y datos reservados dentro del repositorio privado.
- Conservar `mis-apps` como portal público, sin alojar allí el motor científico.
