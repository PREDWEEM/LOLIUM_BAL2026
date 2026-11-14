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

**Inicio de la curva.** Cuando se informa la fecha de las primeras plántulas (o hay un primer conteo con plántulas), la curva
del calendario de Balcarce vale 0 antes de esa fecha, arranca ese día en la fracción típica ya emergida al ver las primeras
plantas (~18 %) y desde ahí sigue el calendario reescalado. Error medio de la curva desde las primeras plántulas: 9,7 puntos,
contra 6,9 con el calendario por fecha; se prefirió que la curva no suba antes del inicio informado.

## Señal de lluvia (actualización de noviembre de 2026)

La señal de lluvia usa ahora el **modelo de pulsos ajustado con las 17 campañas de *Lolium multiflorum* de Bordenave**.
El tamaño de cada pulso depende del agua que entró al suelo, de cuán seco estaba y de la época del año (máximo para
lluvias de fines de mayo); la mitad de la respuesta emerge dentro de 114 °Cd de tiempo térmico de suelo y el 90 %
dentro de 252 °Cd. Con el nuevo núcleo se reajustaron los modelos logísticos, los percentiles de referencia y la
recalibración de flujos tardíos (`alerta_lolmu_params.json`). El balance de agua y la temperatura de suelo no cambian.

Validación con cada campaña de Bordenave predicha con el ajuste sin ella (incluido el núcleo de lluvia): AUC 0,77 solo
con clima, 0,83 con primeras plántulas y 0,87 con conteos. En las ocho localidades de validación, sin reajustar: 0,89,
0,92 y 0,93 (calendario solo, 0,89). En Balcarce: 0,91, 0,93 y 0,95 (antes 0,95, 0,96 y 0,97); las tablas de
validación de este sitio que figuran más arriba corresponden a la versión anterior.

## Aviso de flujos tardíos

Del 1 de mayo al 30 de junio la app muestra además la **probabilidad de flujos tardíos**: que en los próximos 7 días
emerja al menos 2 % de la campaña. El aviso se da desde 20 %; sin datos del lote, desde 25 % (`tardia.umbral_tramos`).
En esa época los grandes flujos (≥ 5 %) son raros, pero pocas plantas por semana importan para decidir la fecha de siembra.
Es la misma alerta recalibrada por nivel de información (`tardia` en `alerta_lolmu_params.json`). Aparece en un recuadro
debajo de la alerta y en la descarga en Excel.

| Información | AUC Bordenave (17 campañas, 130 semanas de mayo–junio, 42 con ≥ 2 %) | Detectadas con el aviso | Semanas marcadas |
|---|---|---|---|
| Solo clima (aviso desde 25 %) | 0,57 | 67 % | 68 % |
| + primeras plántulas | 0,79 | 90 % | 62 % |
| + conteos semanales | 0,87 | 86 % | 51 % |

Cada campaña se predijo con el ajuste sin ella. Sin datos del lote el aviso casi no distingue semanas: conviene cargar la
fecha de primeras plántulas. En otras seis localidades (58 intervalos de mayo–junio, 10 con ≥ 2 % por semana) la AUC fue
0,85 con primeras plántulas y 0,89 con conteos, con 90 % de detección; allí la probabilidad tiende a ser alta (30 % contra
17 % observado).

**Del 1 de julio al 1 de octubre no se muestra probabilidad** (`tardia.recorrida`): en Bordenave (80 semanas, 11 con
flujo tardío) no distinguió las semanas con emergencia (AUC 0,41–0,50), y bajar el umbral solo marcaba más semanas al
azar. En su lugar, la app recomienda **recorrer los lotes cada 2 semanas**, sobre todo donde suele haber emergencia
invernal (sudoeste bonaerense), antes de definir la fecha de siembra o un control.

En las apps con dos o más campañas propias (Bordenave, Tres Arroyos, Balcarce, San Pedro y Pergamino), el recuadro de
flujos tardíos muestra además cuánto emergió **después de la fecha de emisión en cada campaña del sitio**. Si en esas
campañas, en mediana, emergió menos de 3 % de la campaña desde esa fecha, el aviso se presenta como «Flujo tardío posible
según el modelo; en <sitio> la emergencia suele cortarse antes»: la recalibración de tardíos se ajustó con Bordenave, donde
la emergencia se extiende hasta el invierno, y en sitios donde se corta antes avisa de más (en Balcarce, en mayo de 2014,
2025 y 2026, avisó 8 semanas y hubo 2 flujos tardíos). La probabilidad se sigue mostrando.

## Residual a la siembra (guía de riesgo)

Debajo de la alerta, un recuadro siempre visible muestra, para la **fecha de siembra prevista** (1/05–31/07; si no se
carga, el 1/06 como referencia), el riesgo de nacimientos en la **ventana de acción del residual: de 10 días antes a 45 días
después de la siembra**, el período de acción promedio de un herbicida residual. Tiene tres tarjetas: riesgo, nacimientos en
la ventana (mediana de las campañas, en plantas/m² y en % de la campaña) y recomendación. Se calcula con las 3 campañas de Balcarce (`residual` en `alerta_lolmu_params.json`). Las plantas/m² usan la densidad de cada campaña con conteos; las campañas que solo
tienen la curva relativa usan la densidad de referencia del sitio (8280 pl/m² por campaña, mediana de las
campañas con conteos):

| Siembra | Nacimientos de −10 a +45 días (mediana) | Riesgo para el residual | Campañas del sitio |
|---|---|---|---|
| 1/05 | 467 pl/m² (5,6 %) | Muy alto | 2014: 1292 pl/m² · 2025: 467 pl/m² · 2026: 44 pl/m² |
| 15/05 | 225 pl/m² (2,7 %) | Muy alto | 2014: 723 pl/m² · 2025: 225 pl/m² · 2026: 48 pl/m² |
| 1/06 | 37 pl/m² (0,4 %) | Alto | 2014: 244 pl/m² · 2025: 0 pl/m² · 2026: 37 pl/m² |
| 15/06 | 27 pl/m² (0,3 %) | Alto | 2014: 149 pl/m² · 2025: 0 pl/m² · 2026: 27 pl/m² |
| 1/07 | 17 pl/m² (0,2 %) | Medio | 2014: 174 pl/m² · 2025: 0 pl/m² · 2026: 17 pl/m² |

El nivel de riesgo surge de las plantas/m² que nacieron en la ventana en una campaña típica (mediana). Se usan plantas
y no el % de la campaña porque en sitios con mucha densidad una fracción chica son muchas plantas (en San Pedro, 0,8 % de
la campaña fueron 29–42 pl/m²):

| Riesgo | Nacimientos en la ventana | Recomendación |
|---|---|---|
| 🔴 Muy alto | ≥ 50 pl/m² | Usar residual |
| 🟠 Alto | 20–50 pl/m² | Residual recomendado |
| 🟡 Medio | 5–20 pl/m² | Según infestación: residual si el lote tiene alta infestación o antecedentes de raigrás |
| 🟢 Bajo | < 5 pl/m² | Residual solo en lotes muy infestados |

Sin otro dato, las densidades son las registradas en los ensayos del sitio. El usuario puede indicar la **infestación de raigrás de su lote** (opcional): baja (unas 200 pl/m² en toda la campaña), media (unas 1.000) o alta (unas 4.000). Con ese dato las plantas/m² se calculan con la densidad del lote y, como la infestación ya está considerada, las recomendaciones de los niveles medio y bajo pasan a «residual opcional» y «no hace falta residual».

Debajo de las tarjetas se indica el valor de cada campaña del sitio y qué proporción de las campañas cayó en cada nivel. Es
un **riesgo histórico, no una predicción de la campaña**: ni la fecha de primeras plántulas ni el clima anticiparon cuánta
emergencia queda después de la siembra.

En el gráfico, la segunda fila del **semáforo semanal** («Residual (siembra)») muestra, para cada semana del 1/05 al
31/07, el riesgo para el residual si se siembra el primer día de esa semana: rojo, alto o muy alto (≥ 20 pl/m²); amarillo, medio
(5–20 pl/m²); verde, bajo (< 5 pl/m²), con la infestación del lote si se indicó. Con fecha de siembra cargada, las semanas empiezan ese día, así la celda
de la siembra coincide con el recuadro del residual. La fecha de siembra prevista se marca
con una línea verde y una flecha con cartel.

## Condiciones de uso

No se concede licencia de uso por el solo hecho de acceder al repositorio. Cualquier utilización académica, técnica, institucional o comercial que exceda la visualización del contenido requiere autorización previa y escrita del titular de los derechos correspondientes.

Las solicitudes de autorización deben canalizarse mediante los medios de contacto del titular del repositorio PREDWEEM.

## Limitación de responsabilidad

PREDWEEM es una herramienta de soporte para decisiones y no sustituye el diagnóstico profesional, el monitoreo a campo ni la evaluación agronómica específica de cada lote. Las decisiones de manejo deben ser adoptadas por profesionales responsables considerando las condiciones locales y la normativa aplicable.

## Autoría

**PREDWEEM by Guillermo R. Chantre**

## Módulo común (LOLIUM-COMUN)

La alerta, su visualización y el control de acceso son comunes a las 8 apps de Lolium y están en el paquete
[PREDWEEM/LOLIUM-COMUN](https://github.com/PREDWEEM/LOLIUM-COMUN), fijado por versión en `requirements.txt`
(`lolium-comun @ git+https://github.com/PREDWEEM/LOLIUM-COMUN@<commit>  # v1.3.1`). En esta app, `alerta_lolmu.py`,
`visualizacion_alerta_lolmu.py` y `acceso_predweem.py` son archivos puente que cargan ese paquete con los parámetros de este
sitio (`alerta_lolmu_params.json`), que siguen acá. Los cambios a la alerta se hacen en LOLIUM-COMUN y llegan a la app al
actualizar la versión en `requirements.txt`.
