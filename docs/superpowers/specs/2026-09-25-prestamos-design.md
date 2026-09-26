# Préstamos de jugadores — diseño (2026-09-25)

Aprobado por Diego en el chat (opción 1: negociación como un fichaje; ofertas de préstamo de la IA
con contraoferta). Va sobre v4.4.0 + traspasos pendientes + mercado de invierno (ventanas
J1-3, J n/2..n/2+2, J n-2..n).

## Objetivo

Poder **pedir a préstamo** jugadores de otros clubes y **ceder** los propios, por **6 meses o 1 año**,
repartiendo el sueldo en porcentajes. El jugador juega y progresa en el club donde está y al
terminar vuelve a su dueño. Las idas y vueltas solo ocurren con el mercado abierto.

## Datos

- **`Jugador.prestamo`** (campo nuevo, persistido en `to_dict`/`from_dict`, `None` por defecto):
  `{'dueno': nombre del club dueño, 'club': nombre del club donde juega, 'pct_dueno': 0-100,
  'vuelve': [temporada, jornada], 'id': id del préstamo}`. Solo existe mientras el jugador está
  cedido (en el club que lo recibió).
- **`datos_carrera['prestamos_pendientes']`**: préstamos acordados que esperan la ventana para
  empezar o para terminar (misma idea que `traspasos_pendientes`): `{'tipo': 'inicio'|'fin', ...}`.
- **`datos_carrera['lista_prestamo']`**: nombres de tus jugadores ofrecidos a préstamo.
- Duración → regreso: **6 meses** = la siguiente ventana (inicio → invierno, invierno → cierre,
  cierre → invierno de la temporada siguiente); **1 año** = la misma ventana de la temporada
  siguiente. `market.ventanas_mercado` da las ventanas; el préstamo vuelve el primer día de esa
  ventana.

## Módulo nuevo `alpha_football/prestamos.py` (sin UI)

- `duracion_a_regreso(estado, meses) -> [temporada, jornada]`.
- `pedir(estado, jugador, club, meses, pct_user)` → evalúa con el club (ver reglas), devuelve
  `('acepta'|'analiza'|'rechaza', mensaje)`; `'analiza'` queda en `datos_carrera['analisis_prestamos']`
  y responde por correo en la jornada siguiente (50/50, como las compras).
- `aceptar_jugador(estado, jugador, club, meses, pct_user)` → el jugador acepta si tu club no es
  mucho peor que el suyo (media del once ≥ la suya − 6) o si va a ser titular en tu once.
- `iniciar(estado, jugador, dueno, destino, meses, pct_dueno)` → con mercado abierto mueve al
  jugador y le pone `prestamo`; con mercado cerrado lo deja en `prestamos_pendientes` ('inicio').
  Correo al acordar (con la jornada en que se va / llega) y al concretarse.
- `terminar(estado, jugador)` → vuelve a su dueño (inmediato con mercado abierto; si no, queda
  pendiente 'fin' para la próxima ventana). Correo al volver.
- `revisar_jornada(estado)` → al cerrar cada jornada del user: ejecuta pendientes si el mercado
  abrió, devuelve a los que cumplieron (`vuelve` ≤ jornada actual), genera **ofertas de préstamo**
  de la IA por los de tu lista (con mercado abierto, 30% por jugador y jornada) y resuelve las
  contraofertas en análisis.
- `ofertas de préstamo`: van a `estado['ofertas_recibidas']` con `'prestamo': {'meses', 'pct_ellos'}`.
  Aceptar = `iniciar`; contraoferta = pedir que paguen más % (tope oculto como en ventas; dentro =
  acepta, hasta +15 puntos = "lo analizamos", más = se retira).

### Reglas del club que presta

- No presta a sus **3 mejores** (por media): "Es pieza clave, no se presta".
- % mínimo que exige que pagues: 30% si el jugador no está en su mejor once; 60% si es titular.
  Ofrecer el mínimo o más → acepta. Ofrecer menos pero a 20 puntos o menos del mínimo →
  "lo analizamos". Ofrecer todavía menos → rechaza y dice el mínimo.
- Nunca con el clásico (misma regla que las compras).

## Sueldo

- `finanzas.masa_salarial(mi)` cuenta el sueldo de cada jugador de tu plantilla × el % que te
  toca (`100 − pct_dueno` si lo tienes a préstamo; 100 si es tuyo) **más** el % que pagas de tus
  cedidos (`pct_dueno` de los que están en otros clubes). La IA no paga sueldos (sin cambios).

## Durante el préstamo

- El jugador está en la plantilla del club que lo recibió: juega, suma minutos, nota y desarrollo
  como cualquiera de ese club (no hace falta código de desarrollo nuevo).
- **Protecciones:**
  - La IA no lo compra, no lo vende, no lo libera (`_liberar_sobrantes`) ni paga su cláusula.
  - No recibe ofertas de traspaso.
  - Tú no lo puedes vender, renovar ni poner transferible si lo tienes a préstamo.
  - A los tuyos cedidos no les llegan ofertas de traspaso mientras están fuera.
- **Contratos al cerrar la temporada:** el contrato sigue siendo del dueño. Si vence durante la
  cesión, al cerrar la temporada vuelve y queda libre (si el dueño es el user: se va libre como hoy).
  El club que lo tiene a préstamo no lo libera por contrato.
- **Retiro:** si se retira estando cedido, se borra el préstamo (correo si te afecta).
- **Despido o cambio de club del DT:** los préstamos siguen con el club (dueño y destino por nombre).

## UI

- **NEGOCIAR / FAVORITOS**: en la ficha, botón **PEDIR PRÉSTAMO** junto a NEGOCIAR →
  `negociacion_screen` en modo `'prestamo'`: etapa club (duración 6 M / 1 AÑO, % que pagas de 10 en 10,
  OFERTAR) y etapa jugador (ACEPTAR/rechazo con motivo). Mensajes como en el fichaje.
- **PLANTILLA**: botón **LISTA DE PRÉSTAMO** (alterna; tecla P). En la ficha: "A PRÉSTAMO · vuelve
  J11 T2" o "EN LISTA DE PRÉSTAMO".
- **PLANTILLA > CONTRATOS** (`plantilla_orden = 'contrato'`): sección **PRÉSTAMOS** con los que tienes
  a préstamo y los **CEDIDOS** (están en otros clubes), con club, % de sueldo y regreso; botón
  **CONCLUIR PRÉSTAMO** para el elegido.
- **OFERTAS**: las de préstamo se marcan "PRÉSTAMO · 6 meses · pagan 50%"; ACEPTAR / RECHAZAR /
  CONTRAOFERTAR (pides % más alto); en análisis se ocultan ACEPTAR/RECHAZAR.
- Ayuda (H) y barra de atajos de las pantallas tocadas.

## Correos

Acuerdo (con la jornada en que se va o llega), llegada/salida al abrirse el mercado, regreso al
terminar, concluido antes de tiempo, respuesta del análisis, oferta de préstamo recibida.

## Guardar / cargar

`Jugador.prestamo` viaja con el jugador; `prestamos_pendientes`, `lista_prestamo` y
`analisis_prestamos` están en `datos_carrera`. Saves viejos: `prestamo = None`.

## Tests (`tests/test_prestamos.py`)

1. Pedir con mercado abierto: acepta el club y el jugador → llega ya, `prestamo` puesto.
2. Pedir a uno de los 3 mejores → rechazo; % bajo → análisis → correo en la jornada siguiente.
3. Pedir con mercado cerrado → llega el primer día de la próxima ventana.
4. Sueldo: la masa salarial cuenta solo tu % (entrantes y cedidos).
5. Ceder: en lista → llega oferta con mercado abierto; aceptar → se va; contraoferta y análisis.
6. Regreso a los 6 meses / 1 año en la ventana correcta (incluye cambio de temporada).
7. CONCLUIR PRÉSTAMO: inmediato con mercado abierto, pendiente si está cerrado.
8. Protecciones: la IA no lo vende/libera, no hay ofertas de traspaso por él, no se renueva.
9. Contrato vencido durante la cesión → vuelve y queda libre.
10. Guardar/cargar a mitad de un préstamo.

## Fuera de alcance

Cuota de préstamo, opción de compra, préstamos entre clubes de la IA.
