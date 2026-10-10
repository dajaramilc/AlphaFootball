# Último día de fichajes: las 20 horas (G3) — diseño (v0.4.14.0)

**Fecha:** 2026-10-07
**Estado:** diseño aprobado en conversación (2026-10-07), pendiente de revisión del spec escrito
**Depende de:** G1 (reloj y agenda) y G2 (`temporada.py`, mercado por fecha). Orden: G1 → G2 → G3.
**Reemplaza:** la sección D del spec `2026-10-06-calendario-mercado-actualizador-design.md`. Las
horas y sus costos (D2) son los que Diego ya aprobó; cambia el **disparador** (D1) y la integración (D3),
que ahora usan fechas en vez de jornadas.

## Objetivo

Que el último día de cada ventana (31 de agosto y 31 de enero) tenga un reloj de **20 horas**: el user
decide qué cerrar antes de que se acabe el mercado. Con el reloj por días de G1, ese día es el día en que
CONTINUAR siempre se detiene.

## Decisiones de Diego (2026-10-06 y 2026-10-07)

- El último día de fichajes es una fecha del calendario: **31 de agosto y 31 de enero**, con 20 horas.
- Costos y reglas del reloj por horas: la tabla D2 (abajo), aprobada en el spec del 2026-10-06.
- Sin partidos esos días (el calendario de C nunca pone un partido tuyo en un cierre).
- Lo acordado con el mercado cerrado se concreta el primer día de la ventana siguiente.

## Supuestos míos (corregir si no es así)

- Las horas corren **solo en el último día**; los demás días de la ventana pasan por días (G1), sin horas.
- Si pasas de largo (no hay forma de saltarse el cierre): el día 31 se puede terminar con 0 horas o con
  CERRAR MERCADO; **ni +1 DÍA ni CONTINUAR avanzan ese día** mientras queden horas.
- Un save cargado en el último día arranca con 20 horas si el día aún no se había abierto.
- Los clubes de la IA hacen su ronda de cierre cuando el mercado se cierra (con 0 horas o CERRAR MERCADO).

## Fuera de alcance

- Horas en otros días, cierre del mercado a otra hora, mercado de la IA por horas.
- Desfase entre continentes (F).

## 1. Cuándo

Cuando el reloj de G1 llega a un **cierre** (`temporada.ultimo_dia(estado)`: 31 de agosto o 31 de enero)
y quedan horas por vivir, empieza el último día. Estado en
`datos_carrera['calendario']['dia_final'] = {'fecha': 'AAAA-MM-DD', 'horas': 20, 'pendientes': []}`
(dentro del bloque de C, que se rearma solo al cambiar de temporada, liga o club). Al terminar,
`horas = 0` y el mercado queda cerrado para el resto del día; `temporada.ventana_abierta` lo respeta.

## 2. El reloj

| Acción | Horas |
|---|---|
| AVANZAR 1 HORA | 1 |
| Fichaje inscrito (compra, agente libre o préstamo que llega) | 3 |
| Venta o cesión concretada | 2 |
| "Lo analizamos" (club, jugador o préstamo) | responde a las 3 horas |

- Negociar, ofertar y contraofertar no gastan horas; solo lo que se concreta.
- Con menos horas de las que cuesta, el trato no llega a inscribirse hoy: queda **acordado para la
  próxima ventana**, igual que con el mercado cerrado (`traspasos_pendientes`).
- Un "lo analizamos" pedido con menos de 3 horas se responde en el momento: "no hay tiempo".
- Cada hora que pasa: llegan las respuestas que vencen y puede entrar una oferta por un jugador tuyo
  (10% por hora; 25% si tienes transferibles o alguien que pide salir). Mismas ofertas y correos que G1
  (se crean con `dias._entregar_oferta`).
- A las 0 horas, o con CERRAR MERCADO (pide confirmación): se retiran las ofertas sin responder, los
  análisis pendientes se caen con un correo, la IA hace su ronda de cierre y aparece el cartel MERCADO
  CERRADO. Recién entonces el reloj puede pasar al día siguiente.

## 3. Datos y módulo

Módulo nuevo `alpha_football/dia_final.py` (sin UI):

- `activo(estado) -> bool`, `horas(estado) -> int`, `abrir(estado)` (crea el estado con 20 horas),
  `gastar(estado, horas, motivo) -> bool` (False si no alcanza), `avanzar_hora(estado) -> dict` (resumen
  de lo que llegó), `cerrar(estado) -> dict` (retira ofertas, cae los análisis, ronda de la IA, cartel).
- `pendientes`: lo que espera respuesta, cada uno con la hora de respuesta (`{'tipo', 'clave', 'hora'}`).
- `dias.avanzar_dia` / `continuar`: si `dia_final.activo` con horas > 0, no avanzan y devuelven
  `{'dias': 0, 'ultimo_dia': True}`; `continuar` se detiene al llegar al cierre.

## 4. Integración

- `traspasos_pendientes.mercado_abierto(estado)` es la única pregunta "¿puedo operar ya?": además de
  `temporada.ventana_abierta`, mira que el último día no esté cerrado. Los llamados directos que deciden
  por el user (contraofertas, negociación, salidas, ojeador, G2) pasan a usarla.
- `contraofertas` y `prestamos`: los análisis guardan la hora de respuesta cuando hay reloj de horas.
- **Hub:** en INICIO la tarjeta JUGAR se reemplaza por el panel del día (fecha, horas, AVANZAR 1 HORA,
  CERRAR MERCADO); la franja de mercado dice "ÚLTIMO DÍA · quedan 14 h". Cartel al empezar el día
  ("tienes 20 horas") y al terminar. El cartel de cierre de G2 ya no existe: este lo reemplaza.
- Los jugadores y clubes que dependen de una respuesta tardía (préstamos, contraofertas) la reciben con
  su correo habitual (`correo.enviar`) cuando llega la hora.

## 5. Compatibilidad con saves

- Campo nuevo con valor por defecto: `datos_carrera['calendario']['dia_final']` (ausente = sin día final).
- Un save cargado el 31 de agosto o el 31 de enero con el mercado todavía abierto arranca con 20 horas.
- Un save cargado con el día final cerrado conserva el cierre (`horas == 0`).

## 6. Tests

Archivo nuevo `tests/test_dia_final.py`:

- el día final se abre solo al llegar el reloj al 31 de agosto / 31 de enero y arranca con 20 horas;
- `+1 DÍA` y `CONTINUAR` no pasan el día mientras haya horas; CONTINUAR se detiene al llegar;
- costos: fichaje 3, venta 2, hora 1; con menos horas el trato queda acordado para la próxima ventana;
- "lo analizamos": responde a las 3 horas; con menos horas se responde "no hay tiempo";
- ofertas por hora (10% / 25%) con frecuencia estadística; las respuestas vencen en su hora;
- cierre a 0 horas y con CERRAR MERCADO: retira ofertas, cae análisis con correo, ronda de la IA, cartel;
- después del cierre el reloj pasa al día siguiente y `temporada.ventana_abierta` queda cerrada;
- save cargado en el último día, con día cerrado y con día final inexistente;
- hub: panel del día, franja "ÚLTIMO DÍA · quedan N h" y cartel sin errores en el log.

Se ajustan los tests que dan por hecho que se puede jugar o avanzar el 31 sin cerrar el mercado.
Suite completa con `PYTHONIOENCODING=utf-8`, revisando los logs.

## 7. Riesgos

- **Muchos flujos de mercado** consultan "¿abierto?": por eso `traspasos_pendientes.mercado_abierto` es
  la única puerta y el plan la cablea antes que el panel.
- **Reloj de horas dentro del reloj de días:** la regla "el día no avanza con horas" vive en
  `dias.avanzar_dia`, con un test que cubre `+1 DÍA`, `CONTINUAR` y `hasta_el_partido`.
- **Respuestas pendientes al guardar:** `pendientes` es JSON puro (sin objetos) y se rehidrata al abrir.

## Versión

0.4.14.0: comentarios `# v0.4.14.0` y bitácora en `context.md`; título y badge se deciden al cerrar el
paquete (siguen en 0.4.10.0).
