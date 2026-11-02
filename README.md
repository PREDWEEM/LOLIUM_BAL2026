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

### Fin de carga de cada campaña

La última fecha meteorológica de cada campaña es el **1 de octubre, inclusive** (en 2026, el 1/10/2026).
El pronóstico de siete días se recorta al alcanzar ese límite, tanto en la
serie operativa como en los nuevos archivos de pronóstico. Desde el 2 de
octubre no se consulta el ensamble; las actualizaciones de SIGA y del puente
provisional quedan limitadas al 1 de octubre, permitiendo incorporar la
observación de ese día cuando se publique y reemplazar datos provisionales.
La validación admite una serie cerrada sin pronóstico y rechaza fechas
posteriores al cierre. Los archivos históricos existentes se conservan.

## Alerta de flushes

La página muestra la **alerta de flushes** de *Lolium multiflorum*: la probabilidad de que en los próximos 7 días emerja
≥ 5 % de la campaña, con dos niveles (*Atención* desde 15 %, *Alerta* desde 25 %), la emergencia acumulada esperada y la
ventana de control post-emergente (600–800 °Cd desde el inicio). El modelo (`alerta_lolmu.py`, `alerta_lolmu_params.json`,
`visualizacion_alerta_lolmu.py`) es el calibrado con 17 campañas de Bordenave, con dos ajustes propios de Balcarce, donde la
emergencia se concentra más:

1. **Calendario de Balcarce** (`calendario_local.py`, pool 2014, 2025 y 2026 en `data/campanias/`, sin la campaña en curso)
   en la señal de calendario y en la curva acumulada.
2. **Agotamiento de la cohorte**: desde la fecha de las primeras plántulas, la probabilidad se multiplica por
   `1 − 0,4·(1 − exp[−(t/3,57)^0,487])` (forma Weibull del motor de Balcarce, intensidad atenuada 0,4).

**Validación** (2014, 2025 y 2026 con clima SIGA de la EEA Balcarce; 82 intervalos semanales, 10 con flush; cada campaña con el
calendario de las otras):

| Configuración (con primeras plántulas) | AUC | Flushes en *Alerta* | Falsas alarmas |
|---|---|---|---|
| Alerta de Bordenave sin ajustes | 0,94 | 9/10 | 19/72 |
| Calendario de Balcarce | 0,94 | 9/10 | 10/72 |
| **Calendario de Balcarce + agotamiento 0,4 (implementada)** | **0,96** | **9/10** | **6/72** |
| Calendario de Balcarce + agotamiento del motor (0,95) | 0,97 | 4/10 | 0/72 |

Con la intensidad del motor (0,95) la alerta no anticipaba los flushes que siguen al primero (en 2025 continuaron cinco
semanas). Límites: tres campañas, con las que también se eligió la intensidad; 2025 es una curva procesada; en 2014 faltan
datos de clima del 15 al 21/03.

La barra lateral conserva solo los parámetros que usa la alerta (temperaturas base, óptima y crítica, y objetivos 600 y
800 °Cd); los del motor PREDWEEM quedan en sus valores por defecto (cobertura 10 %, Wmax 10 mm, decaimiento post-pico
calibrado).

## Campaña vigente y actualización automática

La campaña meteorológica va del **1 de enero al 1 de octubre** de cada año (`_campania_vigente()` en
`actualizar_meteo_balcarce.py`; las variables `CAMPANIA_INICIO` y `CAMPANIA_FIN` la fijan a mano). Después del 1 de octubre la
serie queda cerrada; el **1 de enero siguiente** la carga se reinicia sola: mientras SIGA no publica días del año, el puente
provisional ECMWF los cubre. La caché SIGA se limita a la campaña vigente.

## Aviso de emergencia tardía (ventana de siembra)

Del 1 de mayo al 31 de agosto, debajo de la alerta de flushes, la app muestra la **probabilidad de emergencia tardía**:
que en los próximos 7 días emerja al menos 2 % de la campaña, con aviso desde 20 %. En esa época los flushes de ≥ 5 %
son raros, pero pocas plantas por semana importan para decidir la fecha de siembra. Es la misma alerta recalibrada por
nivel de información (`tardia` en `alerta_lolmu_params.json`); también aparece en el gráfico (línea punteada violeta) y
en la descarga en Excel.

| Información | AUC Bordenave (17 campañas, 196 semanas, 50 con ≥ 2 %) | Detectadas con el aviso | Semanas marcadas |
|---|---|---|---|
| Solo clima | 0,69 | 72 % | 52 % |
| + primeras plántulas | 0,78 | 82 % | 49 % |
| + conteos semanales | 0,84 | 74 % | 39 % |

Cada campaña se predijo con el ajuste sin ella. En las otras siete localidades (115 intervalos de mayo a agosto, 12 con
≥ 2 % por semana) la AUC fue 0,89 con primeras plántulas y 0,91 con conteos, con 92 % y 83 % de detección; allí la
probabilidad tiende a ser alta (19 % en promedio contra 10 % observado), por lo que hay más falsas alarmas.

## Condiciones de uso

No se concede licencia de uso por el solo hecho de acceder al repositorio. Cualquier utilización académica, técnica, institucional o comercial que exceda la visualización del contenido requiere autorización previa y escrita del titular de los derechos correspondientes.

Las solicitudes de autorización deben canalizarse mediante los medios de contacto del titular del repositorio PREDWEEM.

## Limitación de responsabilidad

PREDWEEM es una herramienta de soporte para decisiones y no sustituye el diagnóstico profesional, el monitoreo a campo ni la evaluación agronómica específica de cada lote. Las decisiones de manejo deben ser adoptadas por profesionales responsables considerando las condiciones locales y la normativa aplicable.

## Autoría

**PREDWEEM by Guillermo R. Chantre**
