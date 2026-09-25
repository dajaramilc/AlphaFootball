# Sub-proyectos 3 a 6 — decisiones de diseño e implementación

**Fecha:** 2026-09-23 · **Versiones:** v2.6.0 (3) · v2.7.0 (4) · v2.8.0 (5) · v2.9.0 (6)

Diego pidió "hagamos el resto y pruebo al final": no hubo spec/plan aprobado por separado para
cada uno. Antes de empezar contestó 4 decisiones (despido → elige club nuevo; quiebra → ventas
forzadas + despido; fichar → oferta al club + contrato; transferible → atrae ofertas). El resto
lo decidió Claude y queda anotado aquí. Todo con TDD (salvo `negociacion.py`, ver abajo).

## 3 · Dirección de equipo — Plantilla (v2.6.0)

- `ui/plantilla_screen.py` (tarjeta PLANTILLA en DIRECCIÓN). Lista ordenable (posición, media,
  edad, valor, contrato), ficha a la derecha con atributos, estadísticas, contrato y botones
  PONER/QUITAR TRANSFERIBLE (T) y RENOVAR CONTRATO (R). Verde = titular; LES/SAN/T marcas.
- `Jugador.transferible`. Marcarlo baja 5 de moral. Con al menos un transferible la chance de
  oferta de la IA por jornada (ventana abierta) sube de 15% a 45% y el 75% va por un
  transferible (medido: 57 → 206 ofertas en 400 jornadas, 79% por el transferible).
- La tarjeta FORMACIÓN sigue llevando directo a la pantalla de formación.

## 4 · Negociaciones (v2.7.0)

- `alpha_football/negociacion.py`: pool = jugadores de las 10 ligas vivas + agentes libres (sin
  el pool internacional viejo, que duplicaba clubes con parodias). Filtros: nombre (sin tildes),
  posición, liga, edad mín/máx, media mín, potencial mín, precio máx (o "≤ presupuesto").
- `ui/buscador_screen.py` (NEGOCIAR): sin buscar muestra los 40 mejores; tras BUSCAR aparece
  ORDENAR (media, potencial, edad, precio; clic de nuevo invierte). Los atajos de volumen de
  main.py se suprimen en el buscador (se escribe el nombre). La lista se recalcula al volver.
- Historial: `datos_carrera['historial_pases']` (se guarda con la partida, tope 500). Lo llenan el
  mercado de la IA, tus fichajes, tus ventas, las ventas forzadas y los fines de contrato.
  `ui/historial_pases_screen.py` con pestañas GENERAL / PROPIO.
- Ojeador: `recomendar_fichajes` busca jugadores que superan en 2+ la media del titular más flojo
  de su posición (mejor 4-3-3), que puedes pagar y fichar; prioriza posiciones distintas y
  mejora por dólar (los jóvenes con potencial suman). Se fijan una vez por ventana
  (`datos_carrera['ojeador']`, clave temporada + inicio/cierre).
- Nota: `negociacion.py` (parte del buscador) se escribió antes que sus tests; los tests se
  escribieron después cubriendo cada función.

## 5 · Oficina + Objetivos (v2.8.0)

- `alpha_football/directiva.py`. Objetivo por temporada según el ranking de tu plantilla por media
  (+1 puesto de margen): "Clasificar a la copa (top N)", "Terminar entre los X primeros",
  "No descender", "No terminar último"; "Ser campeón" solo con 8+ de media sobre el 2º; en 2ª,
  "Ascender (top 2)". Medido en 1000 temporadas: se cumple el 72% (antes, sin margen, 23-61%).
- Confianza 0-100 (empieza en 70): victoria de liga +3, derrota −3; cumplir +8, superar +15.
- Al cerrar: superado +30% del presupuesto con que empezaste, cumplido +15%, fallado −20%.
  Fallar con confianza ≥ 70 = advertencia (queda en 40); con < 70 = despido.
- Despido (`ui/despido_screen.py`): 3 clubes de menor nivel de las 10 ligas (uno de tu país si
  hay). `cambiar_de_club` mueve liga, equipo, alineación, objetivo y confianza; sin copa esa
  temporada. Orden de pantallas al cerrar: despido → ascensos/descensos → hub.
- `ui/objetivos_screen.py` (tarjeta OBJETIVOS en OFICINA) + línea de objetivo en "Tu club".

## 6 · Finanzas + contratos (v2.9.0)

- `alpha_football/finanzas.py`. Contrato: salario anual = 5% del valor (mín. $20K), años según
  edad (≤23: 3-5, ≤29: 2-4, ≤31: 1-3, 32+: 1-2), cláusula = 2× valor. Se asignan una vez a toda
  la partida (saves viejos incluidos, flag `contratos_v290`).
- Por jornada de liga del user: patrocinio = 40% del presupuesto medio de su liga / jornadas;
  taquilla (de local) = 50% / (jornadas/2) × 1.2 si gana, 0.85 si pierde; salarios = masa/jornadas.
  Medido en una temporada sin fichar: Premier +4M, BetPlay −1.9M (lo cubren los premios de fin
  de temporada), Brasil +14M. La IA no paga salarios (sigue con su economía de v2.3.7).
- Quiebra: con saldo < 0 no puedes fichar; 3 jornadas seguidas en rojo → la directiva vende al
  más valioso al club más rico al 80%; cerrar la temporada en rojo → despido.
- Fin de temporada: contratos −1 año; los tuyos que llegan a 0 se van libres (a la lista de
  agentes libres); la IA renueva sola 1-3 años. Si la plantilla queda < 15 se completa.
- Fichar (`ui/negociacion_screen.py`): 1) oferta al club: acepta si llega al precio (+25% si es
  una de sus 3 figuras) o si pagas la cláusula; si no, contraoferta. 2) contrato: salario anual,
  años (1-5; 32+ solo hasta 2) y cláusula ×1.5/×2/×3 (más cláusula = pide más). Pide +20% sobre
  su salario para cambiar de club, +10% para renovar. Agentes libres: solo el paso 2.
  El mercado viejo (market_screen, fichaje directo) quedó sin acceso desde el hub.
- Columna FINANZAS: RESUMEN (`ui/finanzas_screen.py`: saldo, libro de la temporada, proyección,
  contratos que vencen) y CONTRATOS (plantilla ordenada por contrato, con RENOVAR).
- Vender/quitar un jugador reindexa la alineación (`finanzas.quitar_de_plantilla`), también en
  ofertas aceptadas (antes los índices de titulares quedaban corridos).

## Tests

`test_plantilla_v260` (5), `test_negociaciones_v270` (6), `test_directiva_v280` (7),
`test_finanzas_v290` (9), `test_integracion_v290` (3 temporadas completas sin errores en el log
+ guardar/cargar conserva todo lo nuevo). Suite completa: 19 scripts OK.

## v2.9.1 — arreglos de la revisión final

Crítico: aceptar una oferta vieja duplicaba al jugador y cobraba dos veces. Importantes: el
despido se esquivaba cerrando el juego (ahora persiste y el hub lo exige), el recorte del
historial borraba los pases propios, cambiar de club dejaba alineación y avisos del anterior, y
(re-graduado de menor a importante) la plantilla podía quedar sin portero y los reemplazos se
iban libres al cierre. Todos con test RED→GREEN en `tests/test_revision_v291.py`.
Menores diferidos: ver "Lo que falta" en context.md.
