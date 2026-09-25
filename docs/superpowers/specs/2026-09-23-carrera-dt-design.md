# Sub-proyecto 7 — Carrera del DT (7a · 7c · 7b)

**Fecha:** 2026-09-23 · **Versiones:** v3.2.0 (7a) · v3.3.0 (7c) · v3.4.0 (7b)
**Aprobado por Diego (chat 2026-09-23):** dividir en 7a/7b/7c, sueldo = patrimonio personal,
espaldarazo = solo meta más alta (conserva la segunda oportunidad), objetivo internacional solo si
estás clasificado, clubes que van mal echan a su DT y buscan otro (también entre la IA, menos
seguido), DTs reales con nombre parodia editables, 5 estilos nuevos con la tabla de Diego y las
contradicciones resueltas según sus textos.

**Orden de implementación:** 7a → 7c → 7b (los DTs de 7b ya nacen con los 9 estilos).
Después siguen los sub-proyectos 3 → 4 → 5 → 6 y al final el 8 (ayuda con la tecla H).

---

## 7a · Carrera del DT (v3.2.0)

### Módulo `alpha_football/carrera_dt.py`
Estado en `datos_carrera` (se guarda con la partida):
- `contrato_dt = {'club': nombre, 'sueldo': int anual, 'desde': temporada, 'hasta': temporada}`
  (`hasta` = última temporada incluida).
- `patrimonio_dt: int` (suma de sueldos cobrados + indemnizaciones).
- `renovacion_dt = {'temporada': t, 'estado': 'ofrecida'|'aceptada'|'rechazada'|'negada'}`.

Funciones:
- `ofertas_contrato(estado, equipo, renovacion=False) -> list[dict]`: 3 variantes
  `{'anios', 'sueldo'}`. Base = max($100K, 4% del `balance` del club) × (0.8 + calif_dt/250).
  1 año ×1.25 · 2 años ×1.0 · 3 años ×0.85. En renovación la base ×1.10.
- `firmar(estado, equipo, oferta)`: escribe `contrato_dt` (`hasta = temporada + anios - 1`).
- `pagar_jornada(estado)`: suma `sueldo / num_jornadas` al patrimonio (jornada de liga del user,
  mismo punto que `revisar_pedido` en `match_screen.finalizar_jornada_liga`).
- `indemnizacion(estado, temporada_fin)`: 50% × sueldo × temporadas que faltaban
  (`hasta − temporada_fin`, mín. 0). Se paga al patrimonio al ser despedido (no al renunciar).
- `revisar_renovacion(estado)`: a mitad de temporada, si `hasta == temporada` y aún no se trató:
  calif ≥ 60 → correo 'directiva' "Oferta de renovación" con acción `contrato_dt_screen`
  (modo renovación); calif < 60 → correo "La directiva no renovará tu contrato" (estado 'negada').
- `contrato_vencido(estado, temporada_fin) -> bool`: `hasta <= temporada_fin` sin renovación
  aceptada.
- `asegurar_contrato(estado)`: saves viejos sin contrato → contrato de 2 años con la variante
  media, sin pantalla (flag implícito: existe `contrato_dt`).

### Pantalla `ui/contrato_dt_screen.py` (estilo FIFA)
Tres modos en `estado['contrato_modo']`:
- **'alta'**: tras crear la carrera (menu devuelve `contrato_dt_screen` en vez de `league_screen`)
  y tras cambiar de club (despido, fin de contrato, oferta aceptada). 3 tarjetas (años, sueldo
  anual, total del contrato), ←/→ + Enter o clic para FIRMAR. Sin cancelar. Luego → `league_screen`.
- **'renovacion'**: desde el correo. Las 3 tarjetas + RECHAZAR. Rechazar = el contrato vence al
  final de temporada.
- **'ver'**: tarjeta **MI CONTRATO** en OFICINA: club, sueldo, hasta qué temporada, patrimonio,
  estado de la renovación, historial de clubes (`clubes_dirigidos`). Solo VOLVER.

### Correo de rendimiento + veredicto (fin de temporada)
- `directiva.evaluar_temporada` añade `info['veredicto']` ∈ `felicitacion` (superado, campeón de
  liga o de copa) · `neutro` (cumplido) · `regano` (fallado con segunda oportunidad) · `despido`,
  y envía el correo 'directiva' "Evaluación de la temporada N" (texto con liga, copa, premio o
  multa, calificación y confianza). La advertencia deja de ir en un correo aparte (queda en este).
- Si el contrato vence sin renovar y no hubo despido: `veredicto = 'fin_contrato'` y se deja
  pendiente la elección de club (reusa `despido_pendiente` con motivo "Terminó tu contrato" y sin
  indemnización).
- `estado['veredicto_pendiente'] = {'correo_id', 'tipo', ...}`.
- Pantalla nueva `ui/veredicto_screen.py`, dos pasos:
  1. El correo abierto (remitente, asunto, cuerpo). Enter →
  2. Veredicto a pantalla completa: FELICITACIÓN (dorado) / TEMPORADA CUMPLIDA (neutro, azul) /
     REGAÑO (naranja) / DESPEDIDO (rojo) / FIN DE CONTRATO (gris), con premio/multa, Δ calificación
     y confianza. Enter → siguiente.
- Orden al cerrar: resumen → **veredicto** → despido (si aplica) → **contrato (alta)** si cambiaste
  de club → ascensos/descensos → hub.

### Espaldarazo financiero
- En OBJETIVOS, botón **PEDIR ESPALDARAZO** (una vez por temporada, solo hasta la mitad de la
  liga): +15% / +30% / +50% del `presupuesto_ref` a cambio de subir la meta 1 / 2 / 3 puestos
  (`pos_max` baja; no por debajo de 1; si ya es 1, no se ofrece esa opción).
- La directiva se niega si calif < 40 (mensaje en pantalla).
- Se guarda en `objetivo['espaldarazo'] = {'pct', 'puestos'}`; el texto del objetivo se regenera;
  el dinero entra a `balance` y al libro de finanzas en la clave nueva `'directiva'`.
- Premio/multa de fin de temporada siguen calculados sobre el `presupuesto_ref` original.
  La segunda oportunidad se conserva.

### Objetivo internacional
- `directiva.definir_objetivo_copa(estado)` → `dc['objetivo_copa']` solo si
  `copa_user_en_copa`; si no, None y OBJETIVOS muestra "Sin competición internacional: no hay meta".
- Meta por ranking de OVR entre los equipos de la copa (r de n): r = 1 con 8+ de media sobre el
  2º → "Ser campeón"; r ≤ n/4 → "Llegar a la final" (Finalista); r ≤ n/2 → "Llegar a semifinales";
  si no → "Llegar a cuartos".
- Orden de fases (`copa_mejor_fase_temp`): Fase de grupos < Cuartos < Semifinal < Finalista < Campeón.
- Al cerrar: superado +6 / cumplido +3 / fallado −4 de calificación. Sin dinero y sin despido.
  Va en el correo de rendimiento y en el historial de objetivos.

---

## 7c · Estilos de juego: de 4 a 9 (v3.3.0)

### Motor (`engine.py`)
- `ESTILOS_DT` = haramball, cruyffismo, flickismo, anchelottismo, kloppismo, artetismo,
  choloismo, dezerbismo, fullbackismo. `NOMBRE_ESTILO` (para mostrar) y `DESC_ESTILO` (una línea).
- `ESTILO_VENTAJA: dict[str, set[str]]` con la matriz de abajo; `bono_estilo` igual que hoy
  (+10% al ganador, −9% al perdedor, 1.0 si es neutro; bajado de +15%/−13% en v3.9.0). Anchelottismo siempre 1.0.
- Kloppismo: gasto de energía ×1.3 (`energia.py`), su contrapartida.

### Matriz (gana a → pierde contra)
| Estilo | Gana a | Pierde contra |
|---|---|---|
| Cruyffismo | Flickismo, Artetismo | Haramball, Choloismo, Fullbackismo |
| Flickismo | Haramball, Artetismo | Cruyffismo, DeZerbismo |
| Haramball | Cruyffismo, DeZerbismo, Kloppismo | Flickismo, Artetismo, Fullbackismo |
| Kloppismo | Choloismo, Fullbackismo | Haramball, DeZerbismo |
| Artetismo | Haramball, Choloismo, DeZerbismo | Flickismo, Cruyffismo |
| Choloismo | Cruyffismo, DeZerbismo, Fullbackismo | Kloppismo, Artetismo |
| DeZerbismo | Flickismo, Kloppismo, Fullbackismo | Haramball, Choloismo, Artetismo |
| Fullbackismo | Cruyffismo, Haramball | Kloppismo, DeZerbismo, Choloismo |
| Anchelottismo | — | — |

El resto de los pares es neutro (20 relaciones gana/pierde). Contradicciones de la tabla original
resueltas con los textos de Diego: Fullback>Cruyff, Cholo>Fullback, Haramball>Klopp,
Arteta>DeZerbi. Equilibrados a neutro por pedido de Diego: Arteta–Cruyff, Fullback–Haramball.
Neutros no mencionados: Klopp–Arteta, Flick–Cholo.
**v3.9.0 (pedido de Diego):** Cruyff > Arteta, Fullback > Haramball, Klopp–Cruyff y Flick–Fullback neutros → nadie con más de ±1 entre victorias y derrotas.

### Una sola lista en todo el juego
`match_screen._TACTICAS_MENU`, `team_screen.TACTICAS` y `edit_screen.ESTILOS_TACTICOS` importan
`engine.ESTILOS_DT`; los menús se re-maquetan para 9 opciones (2 columnas o lista con scroll) con
la descripción corta. Estilos viejos del editor se mapean al cargar (`Equipo.from_dict`):
guardiolismo→cruyffismo, simeonismo→choloismo, mourinhismo→haramball, bielsismo→kloppismo,
cualquier otro desconocido→anchelottismo.

---

## 7b · DTs reales y mercado de entrenadores (v3.4.0)

### Datos
- `data/entrenadores.py`: `DT_REALES = {nombre_parodia_club: (nombre_parodia_dt, estilo)}` para las
  1ª de los 5 países y los internacionales (DTs reales 2025-26, parodia obvia; p. ej. Guardiola →
  "Pep Guardiolo"). 2ª división y DTs libres: nombres generados (nombre + apellido por país, semilla
  fija). ~20 DTs libres al empezar.
- `alpha_football/entrenadores.py` (lógica). Estado en `datos_carrera['dts'] = {'por_club':
  {equipo_id: dt}, 'libres': [dt], 'historial': [...]}` con
  `dt = {'id', 'nombre', 'estilo', 'calif', 'hasta'}`. Calif inicial = 50 + (estrellas − 3)·10.
- El `estilo_dt` del club = el estilo de su DT (se sincroniza al asignar). Tu club no tiene DT de
  la IA (el DT eres tú).
- Editor: el panel de equipo gana el campo **DT** (nombre) junto al dropdown de estilo; se guarda
  en la base custom (`dt_nombre`) y pisa al de `DT_REALES`.

### Despidos entre clubes (IA)
- Tras cada jornada de liga del user, para cada club IA de las 10 ligas: si ya pasó 1/3 de la
  temporada y está 3+ puestos por debajo de lo esperado (ranking por OVR) en la mitad de abajo,
  lo echa con 8% por jornada. Máximo 1 despido por liga por temporada (menos seguido que al user).
- Al cierre: el club que terminó 3+ puestos bajo lo esperado echa con 50%.
- Reemplazo: el mejor DT libre por calif (el despedido pasa a libres con calif −10). Se anota en
  `dts['historial']` y sale en el historial de noticias (correo 'club' "Cambio de DT en X") solo si
  es de tu liga.

### Ofertas para ti
- Cuando un club IA echa a su DT a mitad de temporada y su OVR entra en tu banda (calif ≥ 70: hasta
  tu OVR + 10; ≥ 55: hasta + 5; si no: ≤ tu OVR), con 60% te escribe primero: correo 'club'
  "El [club] te quiere como DT" con acción `ofertas_dt_screen`. La oferta dura 3 jornadas; el club
  juega con un interino (DT libre generado, estilo anchelottismo).
- `ui/ofertas_dt_screen.py` (tarjeta **OFERTAS DT** en OFICINA, con badge): club, liga, OVR,
  puesto actual, jornadas que quedan, ACEPTAR / RECHAZAR.
- Aceptar = cambio inmediato: `directiva.cambiar_de_club` + `contrato_dt_screen` modo 'alta'
  (sin indemnización: renunciaste). Tu club viejo contrata al mejor DT libre.
- Rechazar / vencer = el club contrata al mejor DT libre.

### Dónde se ve
Prepartido e info del rival: "DT: Pep Guardiolo · Cruyffismo". OTRAS LIGAS: DT de cada club.

---

## Pruebas (TDD)
- `tests/test_carrera_dt_v320.py`: variantes y montos del contrato, pago por jornada, indemnización,
  renovación (calif ≥ 60 / < 60), fin de contrato → elección de club, veredicto por caso,
  espaldarazo (montos, meta, negativa con calif < 40, una vez por temporada), objetivo de copa
  (solo si clasificado, metas por ranking, evaluación por fase), saves viejos.
- `tests/test_estilos_v330.py`: matriz simétrica (si A gana a B, B pierde contra A), anchelottismo
  neutro, conteo de la tabla, gasto ×1.3 de kloppismo, mapeo de estilos viejos, listas de UI =
  `ESTILOS_DT`.
- `tests/test_dts_v340.py`: todo club IA tiene DT y su estilo coincide, persistencia en save,
  despido IA (umbral, tope por liga), reemplazo desde libres, oferta al user (banda, 3 jornadas),
  aceptar → cambio de club + contrato, override del editor.
- Toda la suite existente sigue en verde.
