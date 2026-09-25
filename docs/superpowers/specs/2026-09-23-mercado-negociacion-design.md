# Sub-proyecto 3 — Mercado y negociación (v3.5.0)

**Fecha:** 2026-09-23 · **Aprobado por Diego (chat):** contraofertas en ventas y "lo analizamos" también en
compras; valores exactos = montos completos en pantalla + cifra tecleable; rivalidad en ambos sentidos
(salvo moral < 40); contrato por vencer = −25% solo en el último año; más ofertas del exterior; ficha del
jugador ofrecido.

## 1. Contraofertas por tus jugadores (ventas)
- Cada oferta recibida (`estado['ofertas_recibidas']`, dicts `{jugador, comprador, monto, exterior?}`) gana
  un **tope oculto** `of['tope']` = monto × U(1.10, 1.35); si no es del exterior, además ≤ max(monto,
  balance del comprador). Se asigna la primera vez que se contraoferta.
- Una sola contraoferta por oferta (`of['contra']`). Debe superar el monto actual.
  - pedido ≤ tope → **aceptada**: la venta se cierra al instante al precio pedido.
  - pedido ≤ tope × 1.30 → **"lo analizamos"**: `of['contra'] = {'pedido', 'estado': 'analizando',
    'jornada'}`; en la siguiente jornada de liga del user: 50% se cierra la venta al pedido (correo
    "X acepta tu contraoferta"), 50% retiran la oferta (correo "X se retira").
  - más → **rechazada**: la oferta se retira.
- La venta (hoy `ui/ofertas_screen._aceptar`) pasa a lógica testeable `contraofertas.vender(estado, of)`.

## 2. "Lo analizamos" en tus compras
- `negociacion.evaluar_compra(estado, jugador, club, monto)` → `('acepta'|'analiza'|'rechaza', msg, contra)`:
  cláusula pagada → acepta; clásico (ver 6) → rechaza pidiendo la cláusula; ≥ mínimo del club → acepta;
  ≥ 85% del mínimo → analiza; si no → rechaza con contraoferta = mínimo (como hoy).
- Analiza: se guarda en `datos_carrera['analisis_compras']` (`{jugador_id, club_id, club, jugador, monto,
  jornada, temporada}`, uno por jugador). En la siguiente jornada: 50% acepta → correo con acción
  "NEGOCIAR CONTRATO" (`accion['compra'] = {jugador_id, club_id, monto, temporada}`), 50% rechaza (correo
  con lo que pide).
- El acuerdo vale mientras la ventana esté abierta, sea la misma temporada y el jugador siga en el club;
  el correo lleva a `negociacion_screen` en la etapa del contrato con el monto pactado.

## 3. Valores exactos
- `negociacion.dinero_exacto(v) -> "$12,345,000"` en ofertas, negociación (monto, salario, cláusula,
  mensajes) y ficha del jugador.
- En `negociacion_screen` (etapa club) y en la contraoferta de `ofertas_screen` el monto se teclea:
  dígito = monto·10 + d, Backspace = monto // 10 (`ui/entrada_monto.editar_valor`), además de los botones.

## 4. Ficha del jugador ofrecido
- `ui/ficha_jugador.dibujar_ficha(screen, rect, jugador, estado_txt="") -> int` (sacada de
  `plantilla_screen._dibujar_ficha`, sin los botones de plantilla). La usan PLANTILLA y OFERTAS.
- OFERTAS: lista de ofertas a la izquierda (seleccionable con clic o ↑/↓), ficha del jugador de la oferta
  seleccionada a la derecha, botones ACEPTAR (A) / RECHAZAR (R) / CONTRAOFERTAR (C).

## 5. Más ofertas del exterior
- `crear_oferta_exterior`: probabilidad por jornada 12% → **25%**; candidatos = los que rinden bien
  (como hoy) **+ tus 3 mejores por media**.

## 6. Rivalidades (clásico, `data/clasicos.es_clasico`)
- Comprar al clásico: solo pagando la cláusula ("Es tu clásico: solo por la cláusula de $X").
- El clásico no hace ofertas normales por tus jugadores (`crear_oferta_ui` lo excluye como comprador);
  sí puede pagar la cláusula (`pago_clausulas`, sin cambios).
- Excepción en ambos sentidos: jugador con moral < 40 → se negocia normal.

## 7. Contrato por vencer
- `market.factor_contrato(j)` = 0.75 si `contrato_anios == 1`, si no 1.0. Aplica a
  `negociacion.precio_fichaje` (y por lo tanto al mínimo del club) y a los montos de `crear_oferta_ui` y
  `crear_oferta_exterior`. La cláusula no cambia.

## Pruebas
`tests/test_mercado_v350.py` (TDD): formato exacto, factor de contrato, tope, las tres respuestas a la
contraoferta y su resolución 50/50 por correo, una sola contraoferta, rivalidad en ventas y compras (y la
excepción por moral), análisis de compras → correo → reanudar negociación (y acuerdo inválido fuera de
ventana), ofertas del exterior (25% y top 3), descuento en ofertas de la IA, pantallas (ficha, teclear
monto, flujo de contraoferta, acción del correo). Toda la suite sigue en verde.
