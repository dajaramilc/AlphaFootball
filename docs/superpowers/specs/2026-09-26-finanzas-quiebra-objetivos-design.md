# Finanzas, quiebra y objetivos — diseño (2026-09-26)

Aprobado por Diego en el chat. Va sobre v4.5.0 + préstamos + traspaso único por ventana.
Objetivo: que **quebrar sea posible** (para el user y, rara vez, para la IA), que la directiva
ponga **objetivos financieros** además del deportivo, que los objetivos deportivos sean **más
difíciles**, reorganizar la pantalla **OBJETIVOS** y que **otros clubes te llamen** durante la
temporada.

## Estado actual (para referencia)

- Ingresos del user por jornada (`finanzas.procesar_jornada`): patrocinio = 40% del presupuesto
  **medio de la liga** / n; taquilla (local) = 50% del medio / (n/2) × {1.2 V, 1.0 E, 0.85 D}.
- Sueldos: `SALARIO_PCT_VALOR = 0.05` del valor por año, cobrados por jornada.
- Quiebra: 3 jornadas seguidas en rojo → `vender_mejor` (80% del valor); cerrar la temporada en
  rojo → despido inmediato (`cierre_temporada` → `marcar_despido`).
- IA: no paga sueldos; `mercado_ia.ingresos_fin_temporada` le suma el 70% de su presupuesto base.
  Nunca quiebra.
- Medido: ingreso por temporada vs sueldos → Premier 126M vs 49-118M, Brasil 25M vs 7-11M,
  BetPlay 6.3M vs 5-8.5M. Más premios y un presupuesto inicial de 1-3 temporadas de sueldos.

## A. Economía más dura

- `SALARIO_PCT_VALOR`: 0.05 → **~0.08** (valor final calibrado, ver "Calibración").
- **Migración de saves:** al cargar una partida sin `datos_carrera['economia_v2']`, todos los
  salarios de todos los clubes se multiplican por `0.08 / 0.05` (redondeo a miles) y se marca la
  bandera. Las carreras nuevas ya nacen con el porcentaje nuevo (`contrato_inicial`).
- **Ingresos según el club:** en `procesar_jornada`, la base deja de ser `presupuesto_medio(liga)`
  y pasa a ser `presupuesto_base(equipo)` = `mercado_ia.presupuesto_realista(tipo, division,
  estrellas)` **sin azar** (punto medio de su banda). Mismas fracciones (40% / 50%).
- Nueva función `finanzas.ingresos_esperados(equipo, liga) -> int`: patrocinio + taquilla de una
  temporada con todos empates (base del tope salarial y de la IA).

## B. Quiebra del user

- **Jornadas en rojo** (`procesar_jornada`):
  - `JORNADAS_ROJO_VENTA`: 3 → **4**.
  - 1ª jornada en rojo: correo de la directiva "Saldo negativo" con lo que falta para volver a
    positivo y el aviso de la venta forzada.
  - Jornadas 2 y 3: correo con la cuenta regresiva ("en N jornadas la directiva venderá a tu mejor
    jugador").
  - 4ª: `vender_mejor` (igual que hoy) + correo explicando la venta.
  - Volver a positivo resetea el contador (correo "Saldo recuperado" solo si había aviso).
- **Cierre de temporada en rojo** (`cierre_temporada`), reemplaza el despido inmediato:
  - `datos_carrera['temporadas_en_rojo']` += 1 (se pone en 0 si cierra en positivo).
  - 1ª temporada en rojo: correo de advertencia + **−6 puntos** (`PUNTOS_QUIEBRA`) al empezar la
    temporada siguiente (se aplican en la liga nueva tras el reset de la tabla) + correo al
    aplicarse.
  - 2ª temporada **seguida** en rojo: `marcar_despido` ("Quiebra: dos temporadas en números rojos").
- El −6 se guarda en `datos_carrera['sancion_puntos_pendiente']` hasta que la liga nueva exista.

## C. Quiebra de la IA (rara)

- `mercado_ia.ingresos_fin_temporada` pasa a: `balance += ingresos_esperados(eq) − masa_salarial(eq)`
  (la IA cobra y paga una vez por temporada, al empezarla). Se mantiene el tope de fichajes por
  fracción del saldo, así que la IA casi nunca queda en rojo.
- Tras cobrar/pagar, un club de la IA con `balance < 0` **quiebra**:
  - **Remate:** vende sus 2-3 mejores (no a préstamo, no traspasados en esta ventana) al **60% del
    valor** a clubes de 1ª de la IA que puedan pagar (misma lógica que `vender_salidas_forzadas`).
    Esos jugadores quedan marcados `remate=True` hasta el final de la ventana siguiente: el
    buscador del user los muestra con precio de remate (60% del valor) si aún no se vendieron.
  - **Sin fichajes:** `eq.sin_fichajes_hasta = temporada` → `ronda_fichajes_ia` lo salta como
    comprador toda la temporada.
  - **Resta de puntos:** −6 (`PUNTOS_QUIEBRA`) al empezar la temporada.
  - **Noticia por correo** (remitente nuevo `'prensa'` → "Prensa"): "Quiebra en <club>" con la
    lista de jugadores rematados (nombre, posición, media, precio y club comprador) y un botón al
    buscador.
- **Calibración:** que quiebren ~1 club por temporada en todo el mundo (medido en simulación de
  varias temporadas). Si sale más, se agrega un colchón (p. ej. la IA solo quiebra si el rojo
  supera el 10% de sus ingresos).
- Campos nuevos en `Equipo` persistidos: `sin_fichajes_hasta: int = 0`. En `Jugador`:
  `remate: bool = False`.

## D. Objetivos financieros

Se agregan al objetivo de la temporada (`directiva.definir_objetivo`), guardados en el mismo dict:

- **Tope de masa salarial:** `tope_salarial = TOPE_SALARIAL_PCT (0.70) × ingresos_esperados(mi)`.
  - Se evalúa **al cierre** con la masa salarial de ese momento.
  - Correo de aviso (una vez por mitad de temporada) si la masa supera el tope durante la temporada.
- **Saldo mínimo al cierre:** `saldo_minimo = SALDO_MIN_PCT (0.10) × presupuesto_ref`.
- **Evaluación** (`evaluar_temporada`): la temporada se considera **fallada** si falla el deportivo
  **o** cualquiera de los dos financieros (un solo fallo por temporada: primero advertencia,
  reincidir = despido, igual que hoy). El premio/multa de la directiva sigue dependiendo solo del
  resultado deportivo. El correo de evaluación y el historial dicen qué objetivo se falló.
- Los financieros se evalúan **después** de descontar el espaldarazo (ver F).

## E. Objetivos deportivos más difíciles

- `MARGEN_OBJETIVO`: 1 → **0** (la meta es el ranking por media).
- `VENTAJA_PARA_TITULO`: 8 → **5**.
- El test que mide el % de cumplimiento se actualiza al nuevo rango (~50-60%).

## F. Espaldarazo financiero

- Mismo flujo que hoy (una vez por temporada, hasta la mitad, calif ≥ 40, sube la meta 1-3 puestos)
  pero ahora es **deuda**: `obj['espaldarazo']['deuda'] = monto`.
- **Al cierre de la temporada**, antes de evaluar los objetivos financieros y el rojo, la deuda se
  descuenta: primero del premio de la directiva y el bono de fin de temporada; lo que falte, del
  saldo (puede dejarlo en rojo). Se registra en el libro como `'directiva'` negativo.
- Textos: "PEDIR ESPALDARAZO FINANCIERO"; el overlay y el correo dicen que se devuelve al cierre.
- Finanzas y Objetivos muestran "Deuda con la directiva: $X (se descuenta al cierre)".

## G. Pantalla OBJETIVOS reorganizada (`ui/objetivos_screen.py`)

- **Panel izquierdo — OBJETIVOS DE LA TEMPORADA:**
  - Deportivo: meta en grande + "Vas Xº de N" + botón **?** al lado de la meta.
  - **?** (clic o tecla `?`/`I`) abre un overlay con las reglas: si lo superas / cumples / fallas
    (montos), descenso o 4+ puestos por debajo = despido directo, ranking de la plantilla al
    empezar. ESC o clic fuera cierra.
  - Internacional: una línea (igual que hoy).
  - **Masa salarial:** barra actual / tope (verde < 85% del tope, amarillo 85-100%, rojo > tope) con
    el texto "$X / $Y".
  - **Saldo:** barra saldo actual / saldo mínimo al cierre (mismos colores, invertidos) y la deuda
    del espaldarazo si hay.
  - Botón **PEDIR ESPALDARAZO FINANCIERO**.
- **Panel derecho — DIRECTIVA:**
  - Barra de confianza (igual que hoy).
  - **Barra de calificación de DT** (0-100, mismos colores) sin las líneas de "+3/−3…".
  - Pedido activo.
  - Oferta de club vigente (si hay) con botón VER OFERTA.
- **Abajo:** historial (igual que hoy, con qué objetivo se falló).
- Los rects nuevos se exponen como constantes y se agregan a la ayuda (H).

## H. Ofertas de clubes durante la temporada

- Módulo nuevo `alpha_football/ofertas_dt.py` (sin UI):
  - Al cerrar cada jornada de liga (no en las 3 últimas), sorteo con probabilidad tal que salgan
    **1-2 ofertas por temporada** (máx. 2; nunca con otra oferta vigente).
  - Probabilidad y nivel según la calificación de DT:
    - calif ≥ 70: clubes **mejores** que el tuyo (ovr del club +0..+8).
    - 40-69: clubes **parecidos** (±4).
    - < 40: probabilidad muy baja y clubes **peores**.
  - Candidatos: los clubes de las ligas vivas (1ª y 2ª) menos el tuyo, filtrados por la banda de
    nivel de tu calificación (se reutiliza la lógica de `opciones_de_club` con estas bandas). Si
    la banda queda vacía, esa jornada no hay oferta.
  - La oferta se guarda en `datos_carrera['oferta_dt'] = {club, liga, temporada, vence}` con plazo
    de **2 jornadas**; correo de la directiva del otro club con botón **VER OFERTA**.
- **Pantalla/overlay VER OFERTA:** club, liga, media, objetivo que te pondrían y presupuesto;
  ACEPTAR / RECHAZAR.
  - **Aceptar:** `directiva.cambiar_de_club(estado, nuevo)` (ya hace liga, equipo, once, copa y
    objetivo nuevo) a mitad de temporada; el historial registra la temporada en el club viejo como
    "se fue" (sin evaluación de objetivo) y la calificación no cambia.
  - **Rechazar / vencer:** se borra la oferta (correo corto si vence).

## Calibración

Script de simulación (en `tests/`, marcado lento o con pocas temporadas) que mide:
- Un club del user que ficha agresivo (gasta el 90% del saldo en cada ventana) quiebra en 1-2
  temporadas; uno prudente no quiebra en 5.
- Quiebras de la IA por temporada en todo el mundo ≈ 1.
Los valores `SALARIO_PCT_VALOR`, `PUNTOS_QUIEBRA`, `TOPE_SALARIAL_PCT` y `SALDO_MIN_PCT` son
constantes al principio de sus módulos.

## Tests

- Economía: sueldos nuevos, migración una sola vez, ingresos por club.
- Quiebra user: correos en jornadas 1-3 en rojo, venta en la 4ª, reset al volver a positivo;
  temporada en rojo → −6 y advertencia; dos seguidas → despido.
- Quiebra IA: remate 2-3 al 60%, sin fichajes, −6, correo de prensa con la lista.
- Objetivos: financieros al cierre (fallo por tope o por saldo = temporada fallada), margen 0 y
  ventaja 5.
- Espaldarazo: deuda descontada al cierre (del premio y luego del saldo).
- Ofertas DT: máximo 2 por temporada, nivel según calif, aceptar cambia de club, vencer las borra.
- UI: overlay "?", barras, botón VER OFERTA (smoke con `SDL_VIDEODRIVER=dummy`).
