# PREDWEEM — Lolium Balcarce 2026

Repositorio correspondiente a la implementación de **PREDWEEM** para la predicción de la emergencia y la dinámica fenológica de *Lolium multiflorum* en Balcarce, provincia de Buenos Aires, Argentina.

> **Propiedad intelectual**  
> Copyright © 2026 Guillermo R. Chantre / PREDWEEM.  
> Todos los derechos reservados.
>
> Este repositorio constituye software propietario. Su disponibilidad pública no concede autorización para utilizar, copiar, modificar, redistribuir, sublicenciar, realizar ingeniería inversa ni explotar comercialmente el código, los modelos, los parámetros, los pesos neuronales, la documentación o los datos incluidos.
>
> Consulte el aviso completo en [COPYRIGHT.md](COPYRIGHT.md).

## Finalidad

PREDWEEM es una herramienta de apoyo a la toma de decisiones agronómicas basada en la integración de datos meteorológicos, modelos predictivos y filtros ecofisiológicos para anticipar los flujos de emergencia de raigrás anual.

La implementación de este repositorio está orientada a **Balcarce** y debe utilizarse considerando el dominio geográfico, climático y agronómico para el cual fue configurada, así como su estado específico de validación.

## Preparación para repositorio privado

La aplicación fue acondicionada para ejecutarse desde un checkout privado:

- los datos, modelos y recursos visuales se cargan localmente;
- no se depende de archivos públicos servidos desde `raw.githubusercontent.com`;
- la ausencia de pesos o modelos reales detiene la aplicación;
- GitHub Actions puede continuar actualizando `meteo_daily.csv` dentro del repositorio privado;
- Streamlit Community Cloud debe estar autorizado para acceder a repositorios privados de `PREDWEEM`.

Configuración de Streamlit:

- repositorio: `PREDWEEM/LOLIUM_BAL2026`;
- rama: `main`;
- archivo principal: `app_emergenciacombinado.py`.

El procedimiento completo se encuentra en [PRIVATE_REPOSITORY.md](PRIVATE_REPOSITORY.md).

## Automatización meteorológica

El workflow **Actualizar SIGA Balcarce y ECMWF ENS** conserva SIGA–INTA, estación `A872824`, como fuente observada prioritaria. Cada fecha vencida sin una observación SIGA válida se cubre temporalmente con ECMWF IFS histórico y queda identificada como `Provisional_hasta_reemplazo_SIGA`. Cuando SIGA publica posteriormente esa fecha, la observación reemplaza automáticamente el valor provisional.

Desde la fecha actual se usa ECMWF IFS ENS 0,25°. Las variables operativas `TMAX`, `TMIN`, `TMEDIA` y `Prec` corresponden al percentil 50 del ensamble. Las medias se conservan en columnas separadas para auditoría.

La precipitación ausente no se transforma en cero. Temperatura y precipitación se emparejan por identificador de miembro; cada miembro debe aportar 24 valores horarios válidos por día. El proceso exige al menos 30 miembros válidos y el 80 % de los miembros emparejados disponibles.

Antes de guardar `meteo_daily.csv`, GitHub Actions comprueba continuidad diaria, ausencia de nulos, coherencia física, prioridad de SIGA, correspondencia de las filas provisionales con los huecos observados y uso consistente de P50.

El workflow **Verificar despliegue privado** valida el checkout, pero ignora los commits que solo actualizan `meteo_daily.csv` o `data/**`, reduciendo el consumo de minutos de GitHub Actions.

## Condiciones de uso

No se concede licencia de uso por el solo hecho de acceder al repositorio. Cualquier utilización académica, técnica, institucional o comercial que exceda la visualización del contenido requiere autorización previa y escrita del titular de los derechos correspondientes.

Las solicitudes de autorización deben canalizarse mediante los medios de contacto del titular del repositorio PREDWEEM.

## Limitación de responsabilidad

PREDWEEM es una herramienta de soporte para decisiones y no sustituye el diagnóstico profesional, el monitoreo a campo ni la evaluación agronómica específica de cada lote. Las decisiones de manejo deben ser adoptadas por profesionales responsables considerando las condiciones locales y la normativa aplicable.

## Autoría

**PREDWEEM by Guillermo R. Chantre**
