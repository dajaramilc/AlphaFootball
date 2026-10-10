# La temporada por fechas (G2): mercado, ritmos y fin de temporada — diseño (v0.4.13.0)

**Fecha:** 2026-10-07
**Estado:** diseño aprobado en conversación (2026-10-07), pendiente de revisión del spec escrito
**Depende de:** C (calendario real, `calendario.py`) y G1 (reloj y agenda, `dias.py`). Orden: G1 → G2 → G3.
**Absorbe:** la parte "ventanas por fecha" que el spec de C/D daba por hecha (`2026-10-06-calendario-mercado-actualizador-design.md`, secciones B3 y D3). Las 20 horas del último día son G3.

## Objetivo

Que la temporada se cuente por **fechas** y no por partidos: el mercado abre y cierra en días del
calendario (hoy "la ventana de inicio" son las jornadas 1 a 3 aunque la J3 caiga el 5 de septiembre,
después del cierre del 31 de agosto), los ritmos de mitad de temporada y el fin de temporada se
disparan por fecha, y el hub muestra la fecha y la fase como lo principal.

## Decisiones de Diego (2026-10-07)

- **Mercado por fecha:** las jornadas ya no deciden cuándo está abierto el mercado.
- **Calendario realista** (tabla de abajo): ventana larga de verano en Europa y a mitad de año en
  Sudamérica; cierres 31 de agosto y 31 de enero.
- **Pasan a fechas:** los ritmos de mitad de temporada (cantera, préstamos, renovaciones, directiva,
  patrocinios, ojeador), el fin de temporada y el hub con la fecha primero.
- **Mercado vivo por días:** ofertas y fichajes de la IA caen en días de la ventana (en G1 ya lo
  eligió: *Jugadores* y *Mercado*).
- **Las 20 horas del último día** (D) son otro sub-proyecto, G3, con el diseño que ya aprobó.

## Supuestos míos (corregir si no es así)

- Sin reloj (tests y saves viejos), "hoy" es el día del partido que vas a jugar (`calendario.fecha_liga`
  de la jornada actual): todo funciona sin abrir el hub.
- La **mitad de temporada** es el primer día de la ventana de invierno (1 de enero en Europa, 1 de
  julio en Sudamérica). La J11 europea cae el 2 de enero: queda en la segunda mitad.
- Lo que **cuenta partidos de verdad** sigue por jornada: los pedidos de la directiva ("suma N puntos
  en las próximas 5 jornadas"), lesiones y sanciones (partidos), forma, los despidos de DT de la IA,
  y las fechas de copa (`fechas_jornada`).
- Una liga de 38 jornadas usa las mismas fechas de ventana (ya no dependen de `num_jornadas`).
- Las ligas de la IA siguen jugando su jornada cuando juegas la tuya.

## Fuera de alcance

- Las 20 horas del último día y su reloj por horas (G3).
- Desfase entre continentes y cierre del otro continente (F).
- Auto-actualización (E).

## 1. El calendario

| | Europa | Sudamérica |
|---|---|---|
| Temporada | 1 jul → 30 jun | 1 ene → 31 dic |
| Ventana de inicio | 1 jul – **31 ago** | 1 ene – **31 ene** |
| Mitad de temporada = ventana de invierno | 1 – **31 ene** | 1 jul – **31 ago** |
| Primera jornada / última | ~15 ago / ~29 may (copa: final ~5 jun) | ~16 ene / ~11 dic (copa: final ~18 dic) |
| Fin de temporada | 30 jun | 31 dic |

- Cierres y jornadas ya salen de C (`calendario.PLAN`, `sabados`): C no cambia, salvo que
  `market.ventanas_mercado(n)` queda **solo** para anclar las jornadas del calendario.
- G1 arrancaba el reloj el 1 de agosto en Europa: G2 lo cambia al **1 de julio** (`dias.INICIO_TEMPORADA`).
  La temporada siguiente nace el día después del fin (1 de julio / 1 de enero).

## 2. `temporada.py`: un solo sitio que sabe en qué fase estamos

Módulo nuevo `alpha_football/temporada.py` (sin UI), todo a partir de la fecha de hoy:

- `fecha(estado) -> date`: el reloj (`dias.hoy`) si existe; si no, la fecha de la jornada actual.
- `ventanas(estado) -> {'inicio': (abre, cierra), 'invierno': (abre, cierra)}`, `ventana_actual(estado)
  -> 'inicio' | 'invierno' | None`, `ventana_abierta(estado)`, `ultimo_dia(estado)` (hoy es un cierre),
  `dias_para_cierre(estado)`, `proxima_apertura(estado) -> date`.
- `inicio(estado)`, `mitad(estado)`, `fin(estado)`, `segunda_mitad(estado)`, `es_fin(estado)`.
- `texto_fase(estado)`: "Mercado abierto · cierra en 19 días", "Primera mitad", "Segunda mitad",
  "Temporada terminada · fin 30 jun".

`market.ventana_mercado_abierta`, `ventana_actual`, `clave_ventana_traspaso` y `proxima_apertura`
conservan su nombre y reciben `estado` como parámetro opcional: con `estado` leen `temporada.py`; sin
él conservan la lógica por jornada (compatibilidad). Los llamados que deciden por el user o por la IA
pasan `estado` (son unos 26, en 10 archivos). `ventana_actual` devuelve `(primera, última, nombre)`:
los que solo necesitan el nombre usan `temporada.ventana_actual(estado)`.

## 3. Ritmos por fecha, fuente por fuente

| Fuente | Hoy (por jornada) | G2 (por fecha) |
|---|---|---|
| Mercado abierto (user, IA, contraofertas, negociación, salidas, ojeador) | jornadas 1–3 y n/2…n/2+2 | `temporada.ventana_abierta` |
| Traspasos y préstamos acordados con el mercado cerrado | se concretan al abrir la ventana (jornada) | se concretan el **primer día** de la ventana (se agenda al abrir) |
| Regreso de un préstamo (`prestamos._regreso`) | `vuelve: [temporada, jornada]` | `vuelve: [temporada, 'AAAA-MM-DD']` (primer día de la ventana que corresponde); un `vuelve` viejo con jornada se traduce a la fecha de apertura de esa ventana |
| `negociacion._clave_ventana` y recomendaciones del ojeador (3 por ventana) | por jornada | por ventana (`ventana_actual` o la próxima) |
| Informes de cantera (`cantera._hito`, `proximo_informe`) | 'inicio' hasta la jornada n/2, 'mitad' desde ahí | 'inicio' en la primera mitad, 'mitad' desde `temporada.mitad` |
| "Quiere renovar" (`salidas.revisar_renovaciones`) | jornada > n/2 | `temporada.segunda_mitad` |
| Directiva: aviso de tope salarial, espaldarazo ("hasta la mitad") y pedidos de inicio y mitad (`directiva`) | jornada n/2 | `temporada.segunda_mitad` / primer día de la mitad. Los pedidos "en las próximas N jornadas" siguen contando partidos |
| Patrocinios: ofertas de invierno y retiro al cerrar (`patrocinios.revisar_jornada`) | al abrir y cerrar la ventana por jornada | al abrir la ventana de invierno y al cerrarla (agenda) |
| Cartel de apertura del mercado y franja del hub (`aviso_mercado`) | jornada de apertura; "cierra en N jornadas" | primer día de la ventana; "cierra en N días". El cartel de cierre pasa a G3 |
| Ofertas por tus jugadores (G1: `dias.programar_ofertas`) | una tirada por hueco si la ventana (jornada) está abierta | una tirada por hueco sobre los días libres que caen dentro de la ventana; los huecos largos (p. ej. 1 jul → J1) tiran una vez por cada 14 días. Mismas probabilidades |
| Fichajes de la IA (`mercado_ia.ronda_fichajes_ia`, modo ventana) | una ronda al cerrar cada jornada con el mercado abierto | tres rondas por ventana en días sorteados de la ventana (agenda), más la ronda de cierre del último día (G3). `en_inicio` sale de `ventana_actual` |
| Despidos de DT de la IA (`entrenadores`, jornada > n/3), pedidos de N jornadas, lesiones, sanciones | por jornada | **sin cambio** (cuentan partidos) |
| Copas (`fechas_jornada`) | por jornada | **sin cambio** (C ya les da fecha) |

## 4. Fin de temporada por fecha

- La temporada termina el **30 de junio** (Europa) o el **31 de diciembre** (Sudamérica): ese día vencen
  los contratos, se cierra el año y aparece AVANZAR TEMPORADA. Ya no al jugar la última jornada.
- Después de tu último partido (liga y final de copa), CONTINUAR corre los días hasta esa fecha;
  `dias.es_dia_de_continuar` deja de depender de que haya un partido pendiente.
- Si por reprogramaciones quedara un partido tuyo pendiente al llegar la fecha, la temporada termina el
  día siguiente a ese partido.
- `league_screen._info_partido.esta_finalizada` pasa a `ultima jornada jugada y temporada.es_fin`.
- La temporada siguiente nace el día después (1 de julio / 1 de enero): `resumen_temporada_screen`
  reinicia el calendario (C) y el reloj (G1) como hoy; las ventanas de inicio abren ese mismo día.

## 5. El hub: la fecha primero

- Tarjeta JUGAR: línea 1 la acción (JUGAR / CONTINUAR / AVANZAR TEMPORADA); línea 2 **la fecha de hoy y
  la fase** (dorado): "Mié 12 ago 2026 · Mercado abierto, cierra en 19 días"; línea 3 el próximo
  partido ("J3 vs Everton · sáb 5 sep (en 24 días)"). La fecha de arriba a la derecha (C y G1) pasa a
  esa línea.
- Cabecera: `fecha corta · J5/22` (la jornada, chica); franja de mercado: "MERCADO ABIERTO · cierra en
  19 días" (por fecha; con la regla actual de ancho de `test_mercado_v440`).
- Pantalla CALENDARIO: marca los días de ventana abierta (franja verde) además de los cierres.

## 6. Compatibilidad con saves

- Un save en la J3 europea o la J13 (antes "mercado abierto" por jornada) carga con el mercado cerrado
  si su fecha ya pasó el cierre; lo acordado se concreta el primer día de la próxima ventana.
- `vuelve` de préstamos viejos y ventanas guardadas por jornada (`ventana_traspaso` con clave
  `T-verano` / `T-invierno`) se leen sin cambio de formato; solo `vuelve` cambia (ver tabla).
- El reloj de un save de G1 que nació el 1 de agosto sigue valiendo: no se recalcula.

## 7. Tests

Archivo nuevo `tests/test_temporada.py`:

- ventanas y fechas de cada continente (cierres, mitad, fin) y `temporada.fecha` con y sin reloj;
- el mercado está cerrado en la J3 europea (5 sep) y en la J13 (6 feb) aunque la jornada "toque";
  abierto en la J1, J2, J11 y J12;
- `proxima_apertura`, `ultimo_dia`, `dias_para_cierre`, `texto_fase`;
- ritmos: informe de cantera, "quiere renovar", aviso de tope y espaldarazo cambian en la fecha de
  mitad; los pedidos de N jornadas no;
- ofertas agendadas dentro de la ventana, huecos largos con más tiradas, frecuencia equivalente;
- traspasos y préstamos acordados se concretan el primer día de la ventana; `vuelve` viejo se traduce;
- fin de temporada: CONTINUAR corre hasta el 30 jun / 31 dic, AVANZAR TEMPORADA aparece ese día,
  los contratos vencen ese día, la temporada nueva nace al día siguiente;
- hub: líneas de JUGAR con fecha y fase, cabecera y franja por fecha.

Se ajustan los tests que dan por hecho la ventana por jornada (`test_ventana_traspaso`,
`test_invierno_hitos`, `test_mercado_v350`, `test_mercado_v440`, `test_negociaciones_v270`,
`test_prestamos*`, `test_patrocinios`, `test_cantera`, `test_ajustes_v0411`, `test_presupuesto_ventanas`,
hub y teclado) y los de G1 que dan por hecho el 1 de agosto. Suite completa con
`PYTHONIOENCODING=utf-8`, revisando los logs.

## 8. Riesgos

- **Muchos puntos de contacto** (~50 usos de ventanas y de "mitad"): el plan los migra por fuente, con
  el parámetro opcional `estado` para no romper llamados sin partida.
- **Huecos largos antes de la J1** (1 jul → 15 ago): se cubren con tiradas proporcionales y rondas de
  la IA por días; sin eso el mercado de verano quedaría mudo.
- **Fin de temporada con partidos movidos:** la regla "al día siguiente del último partido".

## Versión

0.4.13.0: comentarios `# v0.4.13.0` y bitácora en `context.md`; título y badge se deciden al cerrar el
paquete (siguen en 0.4.10.0).
