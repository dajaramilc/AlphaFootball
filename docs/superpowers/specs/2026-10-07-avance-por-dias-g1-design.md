# Avance por días (G1): reloj, agenda y botones — diseño (v0.4.12.0)

**Fecha:** 2026-10-07
**Estado:** diseño aprobado en conversación (2026-10-07), pendiente de revisión del spec escrito
**Depende de:** el sub-proyecto C (calendario real, v0.4.11.0): fechas de liga y copa, `calendario.eventos_user`, `revisar_choques`.

## Objetivo

Que el juego avance por **días** y no de partido en partido: el user puede detener el día en el que
quiere hacer una acción, y los correos y ofertas que no dependen de un partido llegan en días
sueltos entre partidos. Lo que sí depende de un partido sigue llegando el día del partido.

## Decisiones de Diego (2026-10-07)

- **Avance:** botón **AVANZAR DÍA** (un día) y botón **CONTINUAR**, que corre los días hasta que pase
  algo (correo, oferta, evento, día de partido) y se detiene solo. Elegida la opción "día a día +
  continuar con pausa automática".
- **Qué cae en días sueltos (G1):** *Jugadores* (ofertas por tus jugadores, "pide salir", "quiere
  renovar", eventos de vestuario).
- **Qué cae en días sueltos (G2, aparte):** *Mercado* (fichajes de la IA, traspasos y préstamos
  acordados, cláusulas, ventanas por fecha; absorbe el sub-proyecto D).
- **Se queda al cerrar el partido:** *Club y directiva* (ofertas de banquillo, patrocinios, cantera,
  pedidos y avisos de la directiva, sueldo del DT) y todo lo ligado al partido (resultado, lesiones,
  sanciones, vestuario del partido, finanzas, confianza).
- **Enfoque:** agenda pre-sorteada (no dados diarios), para no cambiar el balance ya calibrado.
- **Partido en dos sub-proyectos:** G1 (este) y G2 (mercado por fecha). Cada uno con su spec y plan.

## Supuestos míos (corregir si no es así)

- La temporada arranca el **1 de agosto** (Europa) o el **1 de enero** (Sudamérica): unas dos semanas
  antes de la J1, para que existan días sin partido desde el principio.
- Los partidos **siempre los juegas tú**: ni CONTINUAR ni AVANZAR DÍA pasan por encima del día de tu
  próximo partido.
- Los efectos de las otras ligas (jornada de los demás clubes, copa de fondo) siguen ocurriendo al
  cerrar tu partido, como hoy.
- Los jugadores lesionados y sancionados siguen contando **partidos**, no días.

## Fuera de alcance

- Mercado por fecha, último día de fichajes, fichajes de la IA y traspasos acordados por día (G2/D).
- Clubes de la IA que cambian de DT, patrocinios y cantera por día (siguen al cerrar el partido).
- Animación del paso de los días: CONTINUAR corre los días de golpe y muestra un resumen.
- Calendario distinto por país, fases de la temporada, desfase entre continentes (F).

## 1. El reloj

`datos_carrera['dia'] = 'AAAA-MM-DD'` es "hoy". Módulo nuevo `alpha_football/dias.py` (sin UI):

- `hoy(estado)` lee el reloj. Si no existe (save viejo o temporada nueva), lo crea: en temporada nueva,
  el 1 de agosto / 1 de enero del año de la temporada (`calendario.anio`); en un save a mitad de
  temporada, el día de tu próximo partido (como `calendario.hoy` de C). `calendario.hoy` pasa a
  delegar en `dias.hoy`.
- El reloj **solo avanza**, y nunca más allá del día de tu próximo partido (`calendario.proximo_evento`).
  Si te mueven el partido (`revisar_choques`) a una fecha anterior al reloj, el reloj no retrocede y
  el partido se juega ese mismo día.
- Al terminar la liga (sin partidos pendientes) no hay días que correr: sigue AVANZAR TEMPORADA. La
  temporada siguiente reinicia el reloj.
- Cambiar de club (despido, oferta de DT) conserva el reloj y vacía la agenda.

## 2. Botones del hub

En el bloque de JUGAR de `league_screen`:

| Situación | Botón grande | Botón chico |
|---|---|---|
| Hoy hay partido tuyo | **JUGAR** (igual que hoy) | — |
| No hay partido hoy | **CONTINUAR** (+ fecha y "próximo: <partido> en N días") | **+1 DÍA** (tecla `D`) |
| Liga terminada | **AVANZAR TEMPORADA** (igual que hoy) | — |

- `dias.avanzar_dia(estado) -> dict` mueve el reloj un día, recupera energía del día, entrega lo que
  caiga ese día en la agenda y devuelve un resumen (`{'dias': 1, 'correos': n, 'ofertas': n, 'eventos': n}`).
- `dias.continuar(estado) -> dict` repite `avanzar_dia` hasta el primer día en que la agenda entrega
  algo o llega el día del próximo partido. Si hoy ya hay algo pendiente, avanza al menos un día.
- Tras CONTINUAR / +1 DÍA, una línea de aviso en el hub: "Pasaron 3 días: 1 oferta, 1 correo".
- Todas las acciones del hub (formación, plantilla, negociaciones, notificaciones…) están disponibles
  cualquier día: "detener el día" es no avanzar más. Atajos (`atajos.py`) y ayuda (`ayuda.py`) se
  actualizan.
- La fecha del botón JUGAR (C) pasa a mostrar "hoy"; el pre-partido sigue mostrando la del partido.

## 3. La agenda

`datos_carrera['agenda']` = lista de `{'fecha': 'AAAA-MM-DD', 'tipo': str, 'datos': dict}`. Es
serializable (ids y nombres, no objetos) y se guarda con la partida.

**Cuándo se sortea:** una vez por hueco, al cerrar cada partido (en `finalizar_jornada_liga`, donde
hoy corren esos sorteos) y al arrancar la temporada (hueco previo a la J1). Los días posibles son
desde el día siguiente al reloj hasta el día anterior al próximo partido. Nada cae el día del
partido. La fecha sale de una semilla (temporada + club + jornada + tipo): reproducible.

**Fuente por fuente:**

| Fuente | Hoy (al cerrar la jornada) | G1 |
|---|---|---|
| Oferta local por un jugador (`market.crear_oferta_ui`, `PROB_OFERTA_POR_JORNADA`) | sorteo y oferta en el acto | el sorteo se hace al cerrar; la oferta se crea el día sorteado (con prob. 1.0 y la ventana de mercado revisada ese día) |
| Oferta del exterior (`market.crear_oferta_exterior`, prob. 0.25) | ídem | ídem |
| Evento de vestuario (`eventos.sortear`) | sorteo y evento en el acto | el sorteo se hace al cerrar; el evento aparece el día sorteado. Si queda sin decidir, se resuelve por defecto al cerrar el partido siguiente, como hoy |
| "Quiere renovar" (`salidas.revisar_renovaciones`) | aviso en el acto | se decide al cerrar; el aviso (correo y marca `renovacion_avisada`) llega el día sorteado |
| "Pide salir", descontento y escalada (`salidas.revisar_descontento`, `subir_escalon`) | al cerrar | se evalúa al cerrar (depende de minutos y resultados); el correo llega el día sorteado. Las ofertas garantizadas siguen el mismo camino que la oferta local |
| Curados, promesas, pendientes, resultado, lesiones, sanciones, finanzas, confianza | al cerrar | sin cambio |
| Club y directiva (ofertas de DT, patrocinios, cantera, pedido, tope salarial, sueldo del DT) | al cerrar | sin cambio |
| Mercado de la IA, traspasos y préstamos acordados, cláusulas, aviso de mercado | al cerrar | sin cambio (G2) |

**Entrega:** `dias.entregar(estado, fecha)` recorre la agenda y ejecuta lo que vence ese día. Cada
`tipo` tiene su función de entrega; un tipo desconocido se descarta con un log (no rompe el save). Una
entrega que falla se registra y se descarta: nunca bloquea el avance del reloj.

**Equivalencia con hoy:** la probabilidad por hueco es la misma que la probabilidad por jornada de
hoy (una tirada por hueco), así que la frecuencia total de ofertas, eventos y avisos no cambia; solo
cambia el día en que se ven.

**Mecanismo de diferido:** el plan decide cómo diferir lo que hoy se crea dentro de las funciones de
cierre (p. ej. separar "decidir" de "enviar" en `salidas` y `eventos`, o encolar el correo ya
preparado). El criterio es no duplicar la lógica de cada fuente.

## 4. Energía diaria

Con el reloj activo, cada día que pasa recupera `recuperacion(j) / calendario.dias_por_jornada` (la
proporción que ya usa C). Al llegar a un partido el total acumulado es el que daba el reparto de C
(`descanso_tras_liga`), así que el balance anual no cambia. Por eso, con reloj activo:

- `finalizar_jornada_liga` **no** recupera energía (lo hace cada día).
- `descanso_tras_liga`, `aplicar_descanso_pendiente` y `descanso_pendiente` quedan como respaldo
  para partidas sin reloj (tests, saves viejos antes de abrir el hub).

## 5. Compatibilidad con saves

- Campos nuevos con valor por defecto: `datos_carrera['dia']`, `['agenda']` (vacía).
- Save a mitad de temporada: el reloj se crea en el día del próximo partido; sin días intermedios
  que correr hasta entonces; la agenda arranca vacía y se sortea al cerrar el siguiente partido.
- Un save con el hub ya renderizado en C (calendario con `revisado`) no necesita migración.

## 6. Tests

Archivo nuevo `tests/test_dias.py`:

- el reloj nace en 1 ago / 1 ene, no retrocede y nunca pasa del próximo partido;
- `avanzar_dia` y `continuar` (se detienen en el primer evento y en el día del partido; no pasan
  por encima del partido; con la liga terminada no hacen nada);
- la agenda es determinista (misma semilla, mismas fechas), no cae el día del partido y los días
  posibles respetan el hueco (hueco de 3 días y de 13);
- equivalencia de frecuencias: con muchas semillas, ofertas/eventos por hueco ≈ probabilidad de hoy;
- cada fuente se entrega el día sorteado (oferta local, exterior, evento, renovar, pide salir);
- una oferta agendada no se entrega si ese día la ventana de mercado ya cerró;
- la energía acumulada hasta el partido coincide con `descanso_tras_liga` de C;
- save viejo (sin `dia` ni `agenda`) carga y funciona; agenda corrupta se descarta;
- hub: botones por situación, teclado (`D`, Enter) y línea de resumen sin errores en el log.

Se ajustan los tests que dan por hecho que las ofertas, eventos o avisos de renovación se crean al
cerrar la jornada (`test_eventos`, `test_renovacion_aviso`, `test_ofertas*`, `test_salidas*`, hub y
teclado) y los que dan por hecho la recuperación de energía en el cierre (`test_vestuario_v310`,
`test_calendario`). La suite completa se corre con `PYTHONIOENCODING=utf-8` revisando los logs (hay
tests que salen con 0 aunque impriman FAIL).

## 7. Riesgos

- **Muchos sitios leen `jornada_actual`** (72 usos): G1 no lo toca; el reloj se apoya en el
  calendario de C y en el próximo partido.
- **Diferir sin duplicar:** separar "decidir" de "enviar" en cuatro fuentes (ofertas, eventos,
  renovar, pide salir) es la parte más delicada; el plan la divide en una tarea por fuente.
- **Partidos reprogramados** (C) con el reloj adelantado: cubiertos por la regla "el reloj no
  retrocede".

## Versión

0.4.12.0: `VERSION`, título de la ventana, badge del README, comentarios `# v0.4.12.0` y bitácora en
`context.md`.
