# 📋 Plan de Optimización y Nuevas Características — Alpha Football v0.5 (Pygame)

> **Cambio de rumbo (2026-06-17):** se DESCARTA la migración a Tauri/Rust. El juego se queda en **Python + Pygame** y se optimiza para que corra fluido. Motivo: la lentitud de la v0.4 no era de Python (un *manager* simula poco cómputo), sino del **renderizado** (fondo redibujado línea por línea, fuentes y texto sin cachear). Eso se arregla dentro de Pygame, sin reescribir a otro lenguaje ni aprender Rust (lo que justamente hizo fallar el plan anterior por la cascada de `st-1`).
>
> Este documento **conserva TODAS las features que pedía el plan de migración** (persistencia multislot, desarrollo de jugadores, ofertas de IA, simulación calibrada, partido amistoso, opciones + importador yt-dlp) y los **fixes de Bug A y Bug B**, reexpresados para Pygame.

---

## ✅ Estado de ejecución (2026-06-17)

Se dividió el trabajo: **el motor/mecánicas duras ya están hechas y verificadas headless por Diego/Opus**; lo que queda es **front-end y wiring**, listo para el orquestador.

### YA HECHO (motor + base) — NO re-ejecutar
| Pieza | Estado | Dónde |
|---|---|---|
| Fase 0 — caches de fuente/gradiente/texto + imports fuera del loop | ✅ hecho y verificado | `ui/theme.py`, `main.py` |
| Fase 1 — Bug A (`Optional`) y Bug B (colores) | ✅ hecho y verificado | `ui/copa_screen.py`, `ui/team_screen.py`, `ui/theme.py` |
| Fase 2 — **núcleo** de persistencia: escritura atómica + `.bak` + **magic + checksum** + **multislot** (slots, cabecera) | ✅ hecho y verificado | `save.py` (`guardar_en_slot`, `cargar_slot`, `leer_cabecera_slot`, `listar_slots`) |
| Fase 3 — **desarrollo de jugadores** (notas, progreso, +OVR, valor) | ✅ hecho y verificado | `desarrollo.py` + campos nuevos en `models.Jugador` |
| Fase 4 — **lógica** de ofertas recibidas de la IA (15%/jornada, monto, aceptar/rechazar) | ✅ hecho y verificado | `market.py` (`generar_ofertas_recibidas`, `aceptar_oferta`, `rechazar_oferta`, `ventana_mercado_abierta`) |
| Fase 5 — **motor** del partido (90 min, 2 mitades, multiplicadores de charla de medio tiempo `decision_mt`) | ✅ ya existía | `engine.py` (`simular_partido`) |

### ✅ TODAS LAS FASES COMPLETAS (2026-06-17, Diego/Opus)

Ya no queda nada para el orquestador: todas las features se implementaron y verificaron headless.

| Fase | Estado | Dónde |
|---|---|---|
| Fase 0 — fluidez + assets | ✅ | `ui/theme.py`, `main.py`. (Las imágenes —logo/estrellas— ya se cargan 1 vez y se cachean; el gradiente usa `convert()`.) |
| Fase 1 — Bug A / Bug B | ✅ | `ui/copa_screen.py`, `ui/team_screen.py`, `ui/theme.py` |
| Fase 2 — multislot (backend + UI) | ✅ | `save.py` (magic+checksum, slots) + selector **Cargar → slots** en `ui/menu.py` + autoguardado al slot activo en `main.py` |
| Fase 3 — desarrollo de jugadores | ✅ | `desarrollo.py` + wiring al final del partido en `ui/match_screen.py` (resumen +OVR/figura en pantalla) |
| Fase 4 — ofertas de la IA | ✅ | `market.py` (`crear_oferta_ui`) + generación al avanzar jornada en `match_screen` + **buzón** (aceptar/rechazar) en `ui/market_screen.py` |
| Fase 5 — partido en vivo + charla | ✅ | `engine.simular_rango` (mitades) + `ui/match_screen.py`: reloj 1 seg/min, charla al 45 que rellena `decision_mt` y la 2ª mitad se simula DE VERDAD con el motor |
| Fase 6 — Partido Amistoso | ✅ | `ui/menu.py` (pasos `amistoso_league`/`amistoso_teams`) + modo `amistoso` en `match_screen` (sin tocar liga/copa/carrera) |
| Fase 7 — Opciones + yt-dlp | ✅ | `ui/options_screen.py` (volumen + importador YouTube async + prefs), `audio.py` (`descargar_url_async`, `cargar/guardar_preferencias`); widget de volumen flotante retirado de `main.py` (atajos +/-/M siguen) |

**Verificación:** `py_compile` de todos los módulos + tests headless (driver `dummy`): desarrollo, ofertas+buzón, persistencia+checksum, `decision_mt` afecta el motor (goles 0.70→5.13), y render-smoke de match/market/options/menu/amistoso sin crash. **Pendiente único: validar FPS y el look en vivo** ejecutando `python main.py` con ventana real.

> Los specs detallados de cada fase siguen abajo como referencia (las fórmulas y números no cambian).

---

## Fase 0 — Rendimiento y fluidez (prioridad máxima)

Diagnóstico por lectura del código (no hubo que correr profiler para ver los anti-patrones):

| # | Problema | Archivo | Arreglo |
|---|----------|---------|---------|
| 1 | `draw_gradient_bg` dibuja **720 `pygame.draw.line` por frame** (una por fila), en cada pantalla | `ui/theme.py:76` | Renderizar el gradiente **una sola vez** a una `Surface` cacheada y `blit`earla. 720 draws → 1 blit. |
| 2 | `get_font()` crea una `Font` nueva en **cada llamada** (caro en SDL_ttf), y se llama por cada texto de cada frame | `ui/theme.py:29` | **Memoizar** por tamaño en un dict `_FONT_CACHE`. |
| 3 | El texto se **re-renderiza cada frame** (con sombra = 2 renders por texto), sin cache | `ui/theme.py:190` (`draw_text`) | Cache LRU de superficies por `(texto, size, color, shadow)`. |
| 4 | Imports `from alpha_football... import` **dentro del bucle principal** y del widget de volumen, cada frame | `main.py:394-413, 253-254` | Subir los imports a nivel de módulo / dispatch dict una sola vez. |
| 5 | PNG de fondo de **6.6 MB** (`assets/Plantilla pantalla principal.png`) potencialmente cargado/escalado por frame | `ui/menu.py` (verificar) | Cargar **una vez**, `.convert()`/`.convert_alpha()`, cachear la versión escalada. |
| 6 | Superficies de imágenes sin `convert()` (blit lento por conversión de formato en cada blit) | varios `ui/*` | `.convert()`/`.convert_alpha()` al cargar cualquier imagen. |

**Criterio de aceptación Fase 0:** el juego mantiene 60 FPS estables navegando entre menú/liga/equipo/mercado/copa; el uso de CPU baja notablemente respecto a v0.4. Verificación: `python -m py_compile` de todos los módulos + arranque manual sin caídas de framerate.

> Estado: el cacheo de fuentes/gradiente/texto y el hoist de imports + fixes de bugs se aplican en esta sesión (ver bitácora de `context.md`). Los puntos 5–6 (assets) quedan para revisar por pantalla.

---

## Fase 1 — Bugs críticos de la v0.4 (arreglar en Python, NO reescribir)

### Bug A — `NameError: Optional` en la pantalla de Copa
* **Ubicación:** `ui/copa_screen.py:166` — `obtener_partido_copa_pendiente(estado: dict) -> tuple[Optional[str], Optional[dict]]`.
* **Causa:** usa `Optional` en la anotación pero el módulo **no importa** `from typing import Optional` (ni tiene `from __future__ import annotations`). La anotación se evalúa al definir la función → `NameError` al importar el módulo → la Copa crashea.
* **Fix:** añadir `from typing import Optional` (y los demás nombres de `typing` que se usen) al inicio de `copa_screen.py`.

### Bug B — `NameError` de colores en Dirección de Equipo
* **Ubicación:** `ui/team_screen.py` líneas 345, 370, 373, 376, 411, 413, 572.
* **Causa:** usa `VERDE_CAMPO`, `VERDE_CAMPO2`, `BLANCO`, `AMARILLO`, `GRIS_CLAR` que **no están definidas ni importadas** de `theme.py`.
* **Fix:** definir esas constantes **centralizadas en `theme.py`** e importarlas en `team_screen.py` (y agregarlas al bloque de *fallback* local del `except`). Equivalente Pygame de "centralizar la paleta".

---

## Fase 2 — Persistencia multislot (5 slots)

* **Ubicación:** carpeta `./saves/` junto al ejecutable; archivos `slot_1.json` … `slot_5.json`.
* **Cabecera de visualización** (primer nivel del JSON): `nombre_partida`, `fecha_guardado` (ISO), `equipo_nombre`, `temporada`, `jornada`, `presupuesto`, y `estado` (el `EstadoJuego` completo).
* **Guardado atómico** (en `save.py`): escribir `slot_X.json.tmp` → respaldar el actual a `slot_X.json.bak` → `os.replace(tmp, slot_X.json)`.
* **Validación de integridad al cargar** (cierra el riesgo de saves corruptos): cabecera con **magic string + versión de esquema + checksum** del bloque `estado`; si no valida, devolver error tipado y NO cargar (en vez de crashear).
* **UI:** menú "Cargar Partida" lista los slots leyendo solo la cabecera (slot vacío → `"[Slot Libre]"`); menú de carrera con "Guardar Partida" → modal de `nombre_partida` + selección de slot 1–5.

---

## Fase 3 — Desarrollo dinámico de jugadores (post-partido)

Al terminar cada partido, para los jugadores con minutos (en `engine.py`):
1. **Nota del partido:** entre `4.0` y `10.0`.
2. **Promedio:** `promedio_nota = (promedio_nota*(pj-1) + nota_partido) / pj`.
3. **Progreso oculto (`progreso_desarrollo`, float):**
   * POR/DEF: clean sheet → `+0.10`; nota `>7.5` → `+0.05`.
   * MED/DEL: cada gol → `+0.20`; cada asistencia → `+0.10`; nota `>7.5` → `+0.10`.
   * Al llegar a `≥1.0`: OVR `+1` (sumar `+1` a 3 de los 5 atributos base al azar) y restar `1.0` al progreso.
4. **Valor de mercado:** `valor_base = OVR² × 1000 × factor_edad`.

---

## Fase 4 — Ofertas recibidas (IA de fichajes)

* **Disparador:** en jornadas con mercado abierto (jornadas 1–3 y últimas 3 de liga), **15% por jornada** de recibir una oferta de la IA por un jugador propio.
* **Monto:** `monto_oferta = valor_jugador × Random(0.95, 1.5)`.
* **Buzón:** panel en el menú de transferencias con las ofertas activas: *jugador, valor real, equipo oferente, monto, botón Aceptar, botón Rechazar*. (en `market.py` + `ui/market_screen.py`/career).

---

## Fase 5 — Simulación de partido calibrada

* **Reloj:** 1 tick por segundo real (1000 ms) = 1 minuto de juego.
* **Duración:** partido de **90 segundos** reales.
* **Medio tiempo táctico:** al minuto 45 (segundo 45 real) se **pausa** y se muestra la pantalla de vestuario para elegir la charla táctica, que altera variables ofensivas/defensivas del 2º tiempo. (en `ui/match_screen.py` + `engine.py`).

---

## Fase 6 — Modo PARTIDO AMISTOSO (nuevo)

* Pantalla de selección rápida de rival (local o internacional) para jugar un amistoso suelto.
* **No** impacta el calendario de liga ni de copa ni la persistencia de la carrera.

---

## Fase 7 — Opciones + importador de música (yt-dlp)

* **Widget de volumen centralizado:** quitar el panel flotante de volumen de todas las pantallas (hoy vive en `main.py`) y moverlo al menú **Opciones**. Atajos `+`/`-`/`M` se mantienen.
* **Importador YouTube (Python, sin Rust):** caja de texto para una URL; al confirmar, lanzar `yt-dlp` en un **hilo aparte** (`threading`/`subprocess`) para no bloquear la UI:
  ```bash
  yt-dlp -x --audio-format mp3 --audio-quality 0 -o "./music/%(title)s.%(ext)s" <URL>
  ```
  * Si falla: log detallado + mensaje amigable en pantalla, sin crashear (silencio funcional).
  * Si tiene éxito: actualizar la lista de pistas; el reproductor (`audio.py`) suena sin interrupción.
* **Persistencia de preferencias:** volumen, música activada/desactivada, liga por defecto.

---

## Guía para el orquestador (paralelización)

* **Fase 0 y Fase 1** son ortogonales y seguras de correr primero (tocan `theme.py`, `copa_screen.py`, `team_screen.py`, `main.py`).
* `theme.py` es **archivo caliente** (lo importan casi todas las pantallas): no paralelizar dos subtareas que lo editen — secuenciar con `depends_on`.
* Fases 2–7 dependen de un `theme.py` estable (Fase 0) pero entre sí son mayormente independientes (datos/persistencia/mercado/partido/opciones) → pueden ir en paralelo respetando los archivos que toca cada una.
