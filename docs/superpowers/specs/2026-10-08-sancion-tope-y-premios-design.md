# v0.4.17.0 — Sanción por tope salarial, evaluación resumida y premios por fecha

**Fecha:** 2026-10-08 · **Estado:** diseño aprobado por Diego en chat, pendiente de revisión escrita.
**Sesiones:** la escribe y ejecuta `lol2`; `lol` trabaja a la vez en EJECUCION-PENDIENTES (0.4.14.1, E = 0.4.15.0, F = 0.4.16.0).

## Objetivo

1. Que pasarse del tope de masa salarial tenga una consecuencia de la **liga** (hoy solo cuenta como
   objetivo financiero fallado): no poder fichar, y con mala salud económica, multa y puntos.
2. Que la pantalla del veredicto diga **por qué** la directiva no está conforme.
3. Que el correo de evaluación de fin de temporada sea un resumen que cambia según el caso
   ("cumplió con todo menos con esto, y es muy importante").
4. Que el **Balón de Oro** se entregue en octubre (ya no en la pantalla de cambio de temporada) y que
   exista el **Jugador Sudamericano del Año**, que se entrega en enero. Los dos se anuncian en
   cualquier carrera.

Lo que NO cambia: la regla de despido (un objetivo principal fallado = advertencia; fallar otra vez
en la temporada siguiente = despido; una temporada limpia borra la advertencia) y la quiebra
(cerrar dos temporadas seguidas en rojo = despido).

## A. Sanción de la liga — módulo nuevo `alpha_football/sancion_liga.py`

### Regla

- Se decide al cerrar la temporada N, en `directiva.evaluar_temporada`, con los mismos datos del
  objetivo financiero: `masa_salarial(mi, estado) > obj['tope_salarial']`.
- **Siempre** (salud buena o mala): durante **toda la temporada N+1** el club no puede comprar
  jugadores, traer agentes libres ni pedir jugadores a préstamo. Sí puede vender, ceder a los suyos,
  renovar y subir juveniles. Lo que ya estaba firmado antes del cierre (compras diferidas y
  préstamos acordados) se respeta.
- **Salud mala** = `finanzas.factor_salud(saldo, base) < 1.0` (saldo negativo o menor al 25% de la
  base), con `saldo = mi.balance` al evaluar (ya con premio/multa de la directiva y la deuda del
  espaldarazo) y `base = finanzas.presupuesto_base(mi, liga.tipo, liga.division)` de la liga en que
  se jugó la temporada N. Además de lo anterior, **multa = 40% de esa base**.
- La multa se cobra en `finanzas.cierre_temporada`, justo después de
  `aplicar_presupuesto_temporada` (sobre el presupuesto nuevo):
  - si `mi.balance >= multa`: se descuenta;
  - si no alcanza: `mi.balance = 0` y **−6 puntos** en la tabla nueva (`mi.puntos -= 6`,
    `mi.sancion_puntos += 6`, igual que la quiebra, y se suman a los −6 de cerrar en rojo).
- La sanción es del **club**: si al DT lo despiden y cambia de club, no lo sigue.

### Datos

`datos_carrera['sancion_liga'] = {'club', 'temporada' (N+1), 'masa', 'tope', 'salud_mala', 'multa'
(0 con salud buena), 'multa_estado' (None | 'pagada' | 'impaga'), 'puntos' (0 | 6)}`. Una sola
sanción a la vez: registrar otra la reemplaza; una de otra temporada u otro club se ignora.

### API

- Constantes: `MULTA_PCT_BASE = 0.40`, `PUNTOS_MULTA = 6`.
- `registrar(estado, masa, tope, temporada_fin) -> dict`: calcula salud y multa y guarda la sanción.
- `activa(estado) -> Optional[dict]`: la sanción si es del club actual y de `estado['temporada']`.
- `motivo_bloqueo(estado) -> Optional[str]`: texto único del bloqueo ("Sanción de la liga: tu club no
  puede fichar, traer agentes libres ni pedir préstamos esta temporada.") o None.
- `texto(sancion) -> str`: frase para el correo y el veredicto (menciona la multa si la hay).
- `cobrar_multa(estado) -> Optional[dict]`: cobra una sola vez (`multa_estado` pasa a 'pagada' o
  'impaga'), anota lo cobrado como negativo en el libro de la temporada nueva bajo `'premios'` (donde
  ya van el premio y la multa de la directiva) y envía un correo de la directiva "Sanción de la
  liga" con el resultado (no lo envía si hay despido pendiente).

### Puntos de bloqueo (sin cambiar firmas; `traspasos_pendientes.puede_concretar` no se toca)

| Función | Con sanción activa |
|---|---|
| `negociacion.iniciar_negociacion` (modos `fichaje` y `prestamo`) | abre la pantalla con `neg['msg'] = (motivo, 'rojo')` |
| `negociacion.evaluar_compra` | `('rechaza', motivo, 0)` |
| `negociacion.reanudar_compra` | `estado['correo_aviso'] = motivo`, devuelve None |
| `negociacion.fichar` (respaldo: compras, libres y contratos "en análisis") | `(False, motivo)` |
| `prestamos.evaluar_pedido` | `('rechaza', motivo)` |
| `prestamos.cerrar_pedido` | `(False, motivo)` |

Al implementar se verifica que la ejecución de lo ya acordado (`traspasos_pendientes.ejecutar`,
`prestamos._ejecutar_pendientes`) no pasa por estos puntos; si pasara, se exceptúa lo acordado antes
del cierre.

## B. Evaluación de fin de temporada — `directiva.py`

### `evaluar_temporada`

- Si la masa pasa el tope, llama a `sancion_liga.registrar(...)` y guarda una copia en
  `info['sancion']`.
- Agrega `info['motivos']`: lista de frases de los objetivos **principales** fallados (ver abajo).
- No cambia premios, calificación, confianza, advertencia ni despido.

### `motivos_fallo(info) -> list` (nueva, pura)

Una frase por objetivo principal fallado: liga (`"Terminaste 9º; la meta era: Terminar entre los 6
primeros"`) y cada fallo financiero (las frases que ya arma `fallos_financieros`, con mayúscula
inicial). Tolera `info` de saves viejos (claves ausentes → lista vacía).

### `texto_evaluacion(info)` — correo resumido y variable

Principales = liga, tope salarial, saldo mínimo. Secundarios = copa, marca, juveniles.

| Caso | Primera frase |
|---|---|
| Nada fallado, liga superada | "Temporada sobresaliente: superó el objetivo de liga y cumplió con todo lo demás." |
| Nada fallado | "Cumplió con todo lo que le pedimos esta temporada." |
| Un principal fallado | "Cumplió con todo menos con X, y eso es muy importante para nosotros." |
| Dos o más principales | "No cumplió con lo más importante: X e Y." |
| Solo secundarios | "Cumplió con lo importante. Nos quedó pendiente X (solo afecta su calificación)." |
| Principales + secundarios | frase del principal + "También quedó pendiente X." |
| Despido | "Prescindimos de sus servicios: no cumplió con X." |
| Fin de contrato | "Su contrato ha finalizado y no continuará en el club." + resumen de arriba |

Después, en este orden y solo si aplican:
1. Advertencia (veredicto `regano`): "Es su advertencia: si la próxima temporada vuelve a fallar un
   objetivo principal, prescindiremos de sus servicios."
2. Sanción de la liga (`sancion_liga.texto`).
3. Detalle compacto en una línea, con palabras (la fuente no garantiza ✓/✗):
   `Liga: superado · Finanzas: fallado · Copa: cumplido · Marca: cumplido · Juveniles: fallado`.
4. Premio o multa de la directiva, deuda del espaldarazo, calificación, confianza, indemnización.

## C. Pantalla del veredicto — `ui/veredicto_screen.py`

En el paso 2, con tipo `regano` o `despido`, debajo del título se listan en rojo hasta 3 motivos
(`info['motivos']` o `directiva.motivos_fallo(info)` en saves viejos). Con cualquier tipo, si
`info['sancion']` existe, una línea con la sanción de la liga. Las líneas de posición, premio y
calificación bajan lo necesario para no encimarse.

## D. Premios por fecha — `premios.py`

### Premios

| Clave | Nombre | Candidatos | Gala | Palmarés |
|---|---|---|---|---|
| `balon_oro` | Balón de Oro | las 10 ligas (como hoy) | último lunes de octubre | `datos_carrera['balon_oro']` |
| `sudamericano` | Jugador Sudamericano del Año | quienes juegan en las ligas de `paises.SUDAMERICA` (1ª y 2ª), con sus datos de Libertadores | 15 de enero | `datos_carrera['sudamericano']` |

El Sudamericano usa la misma fórmula (`calcular_balon_de_oro`) con las ligas filtradas, solo el
campeón de la Libertadores y solo las estadísticas de esa copa.

### Flujo

- **Cierre** — `premios.cerrar_temporada(estado, primeras, segundas, temporada, campeones_copas)`:
  una sola llamada que reemplaza el bloque actual del Balón en
  `resumen_temporada_screen.avanzar_nueva_temporada` (mismo lugar, sin reordenar). Primero entrega
  lo que siguiera pendiente (respaldo, sin gala) y luego calcula los dos premios y los deja en
  `datos_carrera['premios_pendientes'] = [{'premio', 'fecha_entrega', 'datos'}]`.
  Ya no escribe `estado['balon_oro_ultimo']` ni agrega al palmarés.
- **Fecha** — `fecha_entrega(estado, premio)`: la primera ocurrencia de la gala en o después de
  `temporada.inicio(estado)` de la temporada nueva (el año sale de `calendario.anio`, compatible
  con F). Europa: Balón en octubre del mismo año y Sudamericano el enero siguiente. Sudamérica:
  Sudamericano a los 15 días del cierre y Balón en octubre, 10 meses después (decisión de Diego:
  octubre para todos).
- **Entrega** — `premios.revisar_jornada(estado, rng=None)`: idempotente y sin UI. Entrega cada
  pendiente con `fecha_entrega <= temporada.fecha(estado)`: lo agrega a su palmarés, envía un correo
  de **Prensa** con ganador y podio, y si el ganador o alguien del podio juega en el club del user
  lo agrega a `datos_carrera['gala_premio_pendiente']` (lista) y deja `estado['_parar_avance'] = True`
  (gancho de `lol` en `dias.continuar`).
  Se llama cada día desde `dias.revisar_dia` (se agrega a la tupla `pasos`) y, para partidas sin
  reloj, después de cada partido en `match_screen` junto a `patrocinios.revisar_jornada`.

### Pantallas

- **Nueva `ui/gala_balon_screen.py`**: una gala por vez (la primera de la lista): nombre del premio y
  temporada, fecha de la gala, ganador en grande, 2º y 3º; los de tu club en verde. Enter/clic saca
  la gala de la lista; si quedan más, sigue; si no, vuelve a `league_screen`. Tolera que hayan
  pasado días desde la entrega y datos incompletos (sale sola al hub).
- **`ui/league_screen.render`**: un `if` justo después del `try` de `restaurar_despido`: con galas
  pendientes devuelve `'gala_balon_screen'`.
- **`main.py`**: la pantalla en `MODULOS_PANTALLA` y en `SIN_ATAJOS_GLOBALES`.
- **`ui/promo_releg_screen.py`**: se quita la caja del Balón (y la clave `'balon'` de `rects_promo`);
  el resto de la pantalla no se mueve. En `ui/ayuda.py` se quita su entrada.
- **`ui/career_screen.py`**: la caja del palmarés muestra dos listas, BALÓN DE ORO y SUDAMERICANO
  DEL AÑO, con los 3 últimos de cada una (hoy: 6 del Balón).

## Reparto con la sesión `lol`

Archivos de `lol` que se tocan, solo en lo acordado por mensaje: la tupla `pasos` de
`dias.revisar_dia`; una entrada en `ayuda._ayuda_promo`; dos entradas en `main.py`; un `if` en
`league_screen.render`; el bloque del Balón en `avanzar_nueva_temporada`. `lol` no toca
`evaluar_temporada`, `texto_evaluacion`, `cierre_temporada` ni `procesar_jornada`; sí cambia
`presupuesto_temporada` (de su dict solo se puede leer `base`, `saldo`, `salud`, `deuda`, `total`;
esta versión no lo lee). No se tocan `VERSION`, el título de la ventana ni el README. Sin commits,
stash ni reset: Diego da el OK al final.

## Pruebas

- `tests/test_sancion_liga_v0417.py`: registro con salud buena y mala; `activa` por club y
  temporada; cada punto de bloqueo; multa pagada e impaga (saldo 0 y −6 puntos); una sola cobranza;
  variantes de `texto_evaluacion` (los 8 casos) y `motivos_fallo`.
- `tests/test_premios_v0417.py`: fechas de gala en Europa y Sudamérica; `cerrar_temporada` deja los
  dos pendientes y no toca el palmarés; `revisar_jornada` entrega una sola vez, envía el correo y
  marca la gala solo si hay alguien del club en el podio; respaldo al cerrar otra temporada;
  candidatos del Sudamericano solo de ligas sudamericanas.
- Se ajustan `tests/test_v236.py` y `tests/test_competiciones_v380.py` (leían el palmarés justo
  después del cierre) y `tests/test_objetivos_secciones.py` si cambia el texto que comprueba.
- Suite completa al terminar; un rojo en algo de `lol` a medio hacer se avisa, no se "arregla".
