# Sub-proyecto 2 (v3.1.0) — Correo, moral, energía, personalidades, clásicos y calificación de DT

**Fecha:** 2026-09-23 · Aprobado por Diego en chat (diseño A–E + ajustes de cláusulas, energía en vivo, resistencia y rasgos).
Sub-proyectos siguientes que dependen de este: 3 (mercado: contraofertas por correo, rivalidad = solo cláusula,
mercenario en mercado), 4 (nota en vivo en formación), 5 (editor: rival de cada club y resistencia editables).

## Objetivo

Que el vestuario tenga consecuencias: la moral cambia por razones visibles y afecta rendimiento y desarrollo, la
energía obliga a rotar y a pensar los cambios, los jugadores tienen personalidad, los clásicos importan, y todo lo
que pasa llega a una bandeja de correo con enlaces a la pantalla donde se actúa. El DT tiene una calificación que
lo sigue entre clubes y una segunda oportunidad antes del despido.

## Módulos nuevos

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/correo.py` | Modelo del mensaje, `enviar(estado, ...)`, no leídos, marcar leído, tope 200. Sin UI. |
| `alpha_football/vestuario.py` | Moral por jornada, personalidades, pide-salir, clásicos, pedidos de la directiva. Sin UI. |
| `alpha_football/energia.py` | Resistencia (generación/migración), gasto por minuto, recuperación por jornada, factores de rendimiento y lesión. Sin UI. |
| `alpha_football/data/clasicos.py` | Pares de clásicos reales por liga (por identidad de club, como `_IDENTIDAD_CLUB`). |
| `alpha_football/ui/correo_screen.py` | Bandeja: lista (no leídos en negrita) + mensaje + botón de acción. Teclado ↑↓/Enter/Esc. |

Módulos existentes que se tocan: `models.py` (campos nuevos), `engine.py` (moral reequilibrada, energía por tramo,
lesiones), `desarrollo.py` (+15% y potencial), `directiva.py` (calificación DT, segunda oportunidad, catastrófico),
`match_screen.py` / `prepartido_screen.py` (cierre de jornada, energía en vivo), `mercado_ia.py` (cláusulas),
`league_screen.py` (tarjeta CORREO, alerta, calificación en cabecera), `team_screen.py`, `plantilla_screen.py`,
`objetivos_screen.py`, `save.py` / `menu.py` (migración de saves).

## Datos

- `Jugador`: `resistencia: int` (1-99), `energia: float = 100`, `personalidad: str = 'normal'`,
  `pide_salir: bool = False`, `jornadas_moral_baja: int = 0`, `notas_recientes: list[float]` (últimas 5).
  `moral` ya existe (0-100, base 70).
- `Equipo`: `rival: str` (nombre del club clásico; '' si no tiene).
- `datos_carrera`: `correo` (lista), `calif_dt` (0-100, inicial 50), `pedido_directiva` (dict o None),
  `advertencia_dt` (bool: ya fallaste un objetivo la temporada anterior).
- Todo con `to_dict`/`from_dict` tolerante: un save viejo carga con resistencia derivada, energía 100,
  personalidad asignada, rival por la lista de clásicos. La migración es determinista (semilla = id del jugador).

## A. Correo

- Mensaje: `{id, temporada, jornada, remitente, asunto, cuerpo, leido, accion}`; `remitente` ∈ directiva,
  jugador, cuerpo médico, club; `accion` = `{'texto': 'VER OFERTAS', 'pantalla': 'ofertas_screen', ...}` o None.
- Tarjeta **CORREO** primera en OFICINA con contador de no leídos; alerta "N correos nuevos" en Inicio.
- Llegan en este sub-proyecto:
  - Lesión (≥1 partido) o suspensión de un jugador tuyo → Dirección de equipo (`team_screen`).
  - Oferta recibida por un jugador tuyo → Ofertas.
  - **Cláusula pagada** por un club de la IA → Historial de pases.
  - Directiva: felicitación (clásico ganado, racha de 3 victorias, título), advertencia (racha de 3 derrotas,
    confianza < 40, objetivo fallado = segunda oportunidad), pedido nuevo y su resultado.
  - Jugador: queja (moral < 40 por primera vez en la racha) y "quiero irme" → Plantilla.
- La infraestructura acepta cualquier pantalla destino; el sub-proyecto 3 agrega contraofertas/respuestas.

## A2. Cláusulas pagadas por la IA

- Con la ventana de mercado abierta, cada jornada 10% de chance de un pago de cláusula.
- Candidatos: jugadores del user con `clausula > 0` que caben en el `balance` de algún club de la IA de 1ª
  división (cualquiera de las 10 ligas, 1ª). Peso = `ovr / (clausula en millones)` (cláusula barata para su
  nivel pesa más) × 1.5 si el club comprador tiene mayor media que el tuyo.
- El jugador puede negarse (40%) si su moral ≥ 70 y el comprador tiene menor media que tu club; el
  mercenario nunca se niega. Si se niega: correo "X rechazó irse a Y" y +5 moral.
- Si se va: el club comprador paga la cláusula (balance −, tu balance +), el jugador se mueve de plantilla, se
  quita de tu alineación, se registra en historial de pases y en finanzas (`registrar(... 'ventas' ...)`).

## B. Moral

- **Rendimiento:** el factor actual `moral / 70` (moral 40 = 57%) se reemplaza en `models.py` y `engine.py` por
  `1 + (moral − 70) × 0.004` (moral 40 = 0.88, 100 = 1.12).
- **Cambios por jornada** (tras cada partido de liga o copa del user; los clubes de la IA no llevan moral):
  - Jugó: nota ≥ 7 → +3; nota < 5.5 → −3.
  - Resultado del equipo: victoria +2, derrota −2, a todo el plantel.
  - Clásico: derrota −6 extra, victoria +5 extra, a todo el plantel.
  - Top 5 del plantel por media, disponible, no jugó: −3.
  - Sueldo < 60% del salario de mercado para su media (función de `finanzas`): −2.
  - Forma: promedio de las últimas 5 notas < 5.5 → −2.
  - Deriva: ±1 hacia 70 si no hubo otro cambio.
  - Límites 0-100.
- **Desarrollo:** moral ≥ 75 y forma ≥ 6.5 → el progreso de desarrollo de ese partido ×1.15. Al cierre de
  temporada, los ≤ 24 años con moral ≥ 75 y promedio de temporada ≥ 6.5 tienen 40% de +1 y 15% de +2 de potencial.
- **Pide salir:** `jornadas_moral_baja` cuenta jornadas seguidas con moral ≤ 30 (4 si es polémico, 6 el resto;
  el líder nunca). Al llegar: `pide_salir = True` y correo. Mientras pide salir cuenta como transferible para la
  generación de ofertas. Se apaga si su moral vuelve a ≥ 50 o si se vende.

## C. Energía y resistencia

- **Resistencia** (1-99, no cuenta para la media): al generar o migrar = `fisico ± 8` (azar determinista) −
  `2 × (edad − 30)` si edad > 30, + bonus de rasgo: pulmón de hierro +15, rústico +8, regateador −5; límites 1-99.
- **Gasto en vivo:** por minuto jugado `0.40 × (1.5 − resistencia / 100)` (res. 90 ≈ 22 en 90', 50 ≈ 36,
  30 ≈ 43), ×1.10 si edad > 30. Se gasta solo por los minutos que estuvo en cancha: el sustituido guarda la
  energía que tenía al salir; el que entra gasta desde su minuto de ingreso. La simulación instantánea y los
  partidos de la IA usan la misma cuenta con 90' para los titulares.
- **Rendimiento:** en cada tramo simulado cada jugador usa su energía al inicio del tramo:
  factor = `1 − max(0, 60 − energía) / 600` (energía 0 = −10%).
- **Lesión:** probabilidad base × `1 + max(0, 60 − energía) / 30` (energía 0 = ×3).
- **Recuperación:** al cerrar cada jornada de liga del user, TODOS los clubes (10 ligas + equipos de la copa)
  recuperan `15 + 0.15 × resistencia` (−3 si edad > 30), tope 100. Jugar copa y liga entre dos cierres
  acumula cansancio (congestión real).
- **Lesiones y sanciones (hallazgo: hoy NO existen; el campo está pero nada lo activa desde v0.8.9):** al cerrar
  cada partido, por jugador que jugó: lesión con prob. `0.012 × minutos/90 × factor_lesión` (1-4 partidos,
  pesos 50/25/15/10) y roja con prob. `0.004 × minutos/90` (1 partido, 20% 2). Los lesionados/sancionados
  que NO jugaron ese partido descuentan 1 (cuenta por partido del club). Vale para todos los clubes.
- **IA:** el once de la IA ordena por `overall × factor_energía`, así rota sola.
- **UI:** barra de energía en formación (team_screen), plantilla y ficha; aviso en prepartido de titulares con
  energía < 60; energía en vivo junto a cada jugador en el partido.

## D. Personalidades y clásicos

- `personalidad` ∈ normal (70%), lider (8%), profesional (10%), polemico (7%), mercenario (5%), asignada al
  generar/migrar (determinista). Un rasgo de juego `lider` pasa a personalidad `lider` (su bonus defensivo se
  conserva).
- **Líder** (titular en el partido): la pérdida de moral del plantel por derrota/clásico se reduce a la mitad.
  Nunca pide salir.
- **Profesional:** −3 por no jugar y −2 por sueldo se aplican a la mitad.
- **Polémico:** con moral < 40 resta 1 de moral a 3 compañeros al azar por jornada. Pide salir a las 4 jornadas.
- **Mercenario:** el efecto del sueldo es doble (−4). Nunca se niega a un pago de cláusula. (Efectos de mercado:
  sub-proyecto 3.)
- **Clásicos:** `data/clasicos.py` con pares reales por liga (identidad del club real → parodia), p. ej.
  Real Madrid–Barcelona, Boca–River, Nacional–Medellín, Flamengo–Fluminense, Man United–Man City. Al cargar,
  cada club recibe `rival` con el nombre del club de su liga que corresponde (vacío si no está). Un partido es
  clásico si `local.rival == visitante.nombre` o viceversa. Editable en el editor (sub-proyecto 5).
- Efectos del clásico ahora: moral (B), confianza de la directiva ±6, calificación DT −2 si pierdes, correo de
  felicitación si ganas. Marca "CLÁSICO" en prepartido.

## E. Calificación de DT y segunda oportunidad

- `calif_dt` 0-100 (inicial 50), sigue al DT si cambia de club. Visible en OBJETIVOS y cabecera del hub.
- Cambios: objetivo superado +8 / cumplido +4 / fallado −8; título de liga +10; título de copa +12;
  descenso −12; despido −10; pedido cumplido +3 / fallado −4; clásico perdido −2.
- **Pedidos de la directiva:** uno por mitad de temporada (se crea al cerrar la J1 y al cerrar la jornada `num_jornadas // 2`), elegido entre
  los que aplican: ganar el próximo clásico (si hay uno en la mitad), sumar 8 puntos en las próximas 5 jornadas, dar 3 partidos a un sub-21 en las próximas 5 jornadas.
  Correo al crearlo y al resolverlo. Cumplido: +3 calif, +5 confianza. Fallado: −4 y −5.
- **Segunda oportunidad:** fallar el objetivo de la temporada da una advertencia (correo) y deja
  `advertencia_dt = True`. Despido solo si: fallas con la advertencia vigente (dos temporadas seguidas), o es
  **catastrófico** (descender, terminar ≥ 4 puestos por debajo de la meta, o quiebra). Cumplir apaga la
  advertencia. Reemplaza la regla actual basada en confianza ≥ 70.
- `opciones_de_club` escala el nivel de los clubes ofrecidos con `calif_dt`: ≥ 70 clubes de media similar a la
  tuya, 40-69 algo menor (actual), < 40 bastante menor.

## Manejo de errores

Como el resto del proyecto: cada hook de jornada en su `try/except` con `logger.error`, sin romper el cierre de
jornada. Valores ausentes en saves viejos toman defaults. Ningún hook corre dos veces por partido (la guarda de
v3.0.0 en `finalizar_jornada_liga` lo asegura para liga; la copa usa su propio punto de cierre).

## Pruebas (`tests/test_vestuario_v310.py`)

- Moral: cada regla por separado (nota, resultado, clásico, top 5 sin jugar, sueldo, forma, deriva, límites),
  líder amortigua, profesional a la mitad, polémico contagia, pide salir a las 6/4 jornadas y se apaga.
- Energía: gasto por minutos jugados (sustituido gasta menos), resistencia alta gasta menos y recupera más,
  factores de rendimiento y lesión en los extremos, IA rota con energía baja, rasgos modifican resistencia.
- Correo: enviar/no leídos/tope 200/roundtrip de guardado; lesión y oferta generan correo con acción.
- Cláusulas: frecuencia ≈ 10% por jornada con ventana abierta (medida), negativa del jugador, dinero y plantillas
  consistentes, mercenario nunca se niega.
- DT: segunda oportunidad, despido por reincidencia y por catastrófico, calificación sube/baja, pedidos se
  resuelven.
- Migración: un save v2.9 carga con resistencia, personalidad, rival y energía válidos.
- Balance: con la moral reequilibrada, goles promedio por partido en IA vs IA siguen en el rango de
  `test_mentalidad_v250` (sin regresión).
