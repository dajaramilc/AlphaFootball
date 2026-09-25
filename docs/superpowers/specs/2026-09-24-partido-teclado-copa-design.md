# Sub-proyectos 9-12 — Motor del partido, presentación, teclado/correo, copa (v4.0.0 → v4.3.0)

**Fecha:** 2026-09-24 · **Aprobado por Diego en chat** · Orden: A → B → C → D (B depende de A; C y D son independientes).

## Pedido original (resumen)
1. Al simular: ver quién marcó, se lesionó, recibió tarjeta, los cambios y en qué minuto.
2. Antes de continuar: calificaciones del partido y posición en tabla / clasificación de copa.
3. Todo el juego usable sin mouse (menú inicial, cada pantalla y overlay).
4. Lesión, expulsión/amarilla y gol pesan más: pausan un momento con aviso (en vivo) y afectan el partido.
5. Tecla directa al correo. 6. Opciones desde teclado; GUARDAR (solo carrera) dentro de Opciones.
7. Sobre de correo arriba a la derecha en INICIO con el número de no leídos en rojo.
8. Calificaciones que suben/bajan más fácil; más variedad y más eventos; los eventos afectan la nota.
9. Historial de partidos de INICIO con los de copa. 10. Correo con el % del premio de copa por fase.
11. Correo al cumplir un objetivo. 12. Balón de Oro: se mantiene el porcentaje, pero sobre liga + copa.

## Bug detectado (se corrige en A)
`desarrollo.desarrollar_plantilla_post_partido` re-sortea goleadores/asistentes y la nota es azar +
resultado: lo que se ve en la transmisión no coincide con las estadísticas.

---

## A · Motor del partido (v4.0.0) — `engine.py`, `desarrollo.py`, `energia.py`

### Eventos nuevos (dicts en `Resultado.eventos`, mismo formato que hoy: minuto, tipo, equipo_id, detalle, jugador_id)
| tipo | frecuencia objetivo (por partido, ambos equipos) | efecto |
|---|---|---|
| `amarilla` | ~3.5 | nota −0.3; 2ª amarilla ⇒ evento `roja` (motivo "doble amarilla") |
| `roja` | ~0.15 directas | sale del once; su equipo ×0.85 en ataque y defensa por cada expulsado; nota −1.5; `partidos_sancion` 1 (20%: 2) |
| `lesion` | ~0.25 | sale; `lesion_partidos` con la tabla de `energia.py`; la probabilidad usa `factor_lesion(energía)`; nota se congela |
| `cambio` | IA 3-5 entre 60'-80' (cansancio/lesión) | `detalle` "Entra X por Y", `jugador_id` = entra, `sale_id` = sale; máx 5 por equipo |
| `penal` | ~0.25 | resultado `gol` (cuenta como gol, `detalle` de penal) o `penal_fallado` (nota −0.6) |
| `atajada` | derivada de los tiros | portero +0.4 |
| `ocasion` | ocasión clara / palo | atacante −0.2 (ya existe `tiro`: se enriquece la narrativa) |
| `falta` | narrativa de falta peligrosa | sin efecto de nota salvo que acabe en tarjeta |

- Los eventos de `gol` llevan `asistente_id` (el motor lo elige: MED/DEL compañero, 70%).
- Los equipos del user se reemplazan en **simulación instantánea** automáticamente (mismo algoritmo que la IA); en **vivo** lo decide el user (sub-proyecto B).

### Nota por jugador (en el motor)
- Base 6.0; +1.0 gol, +0.5 asistencia, +0.4 atajada, +0.5 valla invicta (DEF/POR que jugaron ≥ 60'),
  −0.2 ocasión fallada, −0.3 amarilla, −1.5 roja, −0.6 penal fallado, −0.3 al defensor batido en un gol recibido.
  +0.1 al defensor por cada corte (`defensa`), para que los defensores también suban por lo que hacen.
- Resultado: +0.5 victoria / 0 empate / −0.4 derrota. Ruido pequeño ±0.3. Rango [3.0, 10.0], 1 decimal.
- `Resultado` gana: `notas: {jugador_id: nota}`, `minutos: {jugador_id: min jugados}`,
  `goles_jug`, `asist_jug`, `incidencias` (lesiones/sanciones nuevas).
- `simular_rango` (vivo por tramos) acepta y devuelve el estado del partido (expulsados, lesionados,
  cambios usados, notas acumuladas) para que persista entre tramos y re-simulaciones por mentalidad.

### Una sola fuente de verdad
- `desarrollar_plantilla_post_partido` acepta `stats_partido` (goles/asist/notas/minutos reales) y lo usa;
  sin él (llamadas viejas), conserva el comportamiento actual.
- `energia.cerrar_partido` deja de sortear lesión/roja cuando recibe las incidencias del partido (sigue
  gastando energía y descontando sanciones/lesiones de quien no jugó).
- Balance: la media de goles por partido no debe cambiar más de ±0.2 respecto a hoy (test estadístico).

## B · Presentación del partido (v4.1.0) — `match_screen.py`, `prepartido_screen.py`

- **Pausas en vivo:** gol ~2.5 s (el flash actual pasa a pausa), roja/lesión ~2 s, amarilla ~1 s, con un
  aviso grande (ícono dibujado, jugador, equipo). Enter/Espacio lo salta. La pausa respeta la velocidad x1/x2/x5.
- **Lesión del user en vivo:** abre el selector de cambio (↑/↓ + Enter, también con clic); si no quedan
  cambios, sigue con 10. Expulsión: aviso y el equipo sigue con 10.
- **Simulación instantánea:** línea de tiempo con minuto + ícono dibujado (gol, amarilla, roja, lesión,
  cambio, penal fallado) + jugador; local a la izquierda, visitante a la derecha; con scroll (↑/↓) si no cabe.
- **Pantalla post-partido** (vivo y simulado, liga/copa/amistoso) antes de CONTINUAR, pestañas ←/→:
  - CALIFICACIONES: ambos equipos (titulares + los que entraron), nota coloreada, goles/asist/tarjetas, figura.
  - TABLA: liga → tabla con tu fila resaltada y flecha ↑/↓ vs. la fecha anterior; copa → tabla del grupo /
    fase liga o "Pasas a X" / "Eliminado"; amistoso → sin pestaña TABLA.
  - Enter = CONTINUAR (misma navegación de salida que hoy).

## C · Teclado y correo (v4.2.0)

- **Menú inicial:** ↑/↓ + Enter con foco visible en todos los botones; ESC = salir (ya existe el diálogo).
- **Auditoría de pantallas y overlays:** cada botón alcanzable por teclado (↑/↓ o Tab mueve el foco,
  Enter activa, ESC cierra/vuelve). Se actualiza `ui/atajos.py` y la ayuda H donde cambie algo.
- **Teclas globales en carrera** (no con texto activo, no en partido en vivo): **M** = correo, **O** = opciones
  (desde opciones, ESC vuelve a la pantalla de origen).
- **GUARDAR dentro de Opciones** (solo en carrera); se quita el botón de donde está hoy.
- **Sobre de correo** arriba a la derecha en INICIO del hub: ícono dibujado con círculo rojo y número de no
  leídos (oculto si 0; "9+" si > 9); clic abre el correo.

## D · Copa, objetivos, historial, Balón de Oro (v4.3.0)

- **Correo por fase de copa** al cobrar el premio (`cobrar_premios_copa`): "Premio por alcanzar {fase}: $X
  ({p}% del premio total; acumulado {q}%)", total = suma de la tabla de premios de la copa.
- **Correo de objetivo cumplido:** copa → en el momento en que alcanzas la fase meta; liga → cuando la meta
  queda asegurada matemáticamente (ningún rival puede empujarte fuera con los puntos que quedan). Uno por
  objetivo y temporada.
- **Historial de INICIO:** incluye los partidos de copa del user con etiqueta (UCL/LIB), orden cronológico.
- **Balón de Oro:** `min_pj = max(3, int((jornadas de liga + partidos de copa de su equipo) × 0.5))` y los PJ
  del jugador cuentan liga + copa (se agrega el conteo de partidos de copa por jugador).

## Pruebas
Un archivo de tests por sub-proyecto (`test_motor_v400.py`, `test_presentacion_v410.py`,
`test_teclado_v420.py`, `test_copa_v430.py`), con `PYTHONIOENCODING=utf-8`; suite completa en verde al final.
Saves viejos siguen cargando (campos nuevos con defaults).
