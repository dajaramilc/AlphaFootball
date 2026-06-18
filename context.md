# ALPHA FOOTBALL — Contexto de Proyecto (v0.4)
**Última actualización:** 2026-06-18
**Sesión actual:** v0.5 — Se DESCARTA la migración a Tauri; se queda en Pygame y se optimiza la fluidez (Fase 0) + se arreglan Bug A y Bug B. Ver Bitácora.

---

## Identidad del Proyecto

**Alpha Football** es un simulador de gestión futbolística (manager) de escritorio desarrollado en **Pygame**. Permite al usuario iniciar una carrera en una de las 5 ligas disponibles, dirigir charlas de vestuario, gestionar el mercado de pases de jugadores en parodia humorística y competir en torneos internacionales (Copa Libertadores o UEFA Champions League) en simultáneo con el calendario local.

---

## Stack Técnico

| Componente | Detalle |
|---|---|
| Lenguaje | Python 3.10+ |
| Biblioteca Gráfica | Pygame (Interfaz gráfica de escritorio a 1280x720) |
| Gestión de Audio | `pygame.mixer` (reproducción shuffle) + `yt-dlp` (descarga de música asíncrona) |
| Persistencia | Guardado en JSON con esquema v4 (serialización limpia de Dataclasses) |
| Resiliencia | Mecanismos de recuperación y fallbacks locales en todos los módulos críticos |

---

## Estructura de Directorios del Proyecto

El prototipo monolítico original (`alpha_football.py`) fue refactorizado y dividido en submódulos modulares y legibles:

```
C:\Users\diego\Downloads\AlphaFootball 0.01\
  main.py                           ← Entrada principal del juego y máquina de estados
  musica.txt                        ← Lista de URLs de Youtube para la banda sonora
  context.md                        ← Este archivo de documentación
  saves/
    alpha_football_save.json        ← Archivo persistente de guardado (esquema v4)
  alpha_football/
    __init__.py
    models.py                       ← Dataclasses del contrato de datos (Jugador, Equipo, Liga, Copa)
    save.py                         ← Serialización y carga tolerante a fallos
    engine.py                       ← Motor de simulación minuto a minuto del partido
    events.py                       ← Eventos caóticos de jornada (lluvia, peleas, directiva, etc.)
    market.py                       ← Lógica del mercado de pases e IA de transferencias rivales
    audio.py                        ← Descarga asíncrona y reproductor shuffle sin patrones repetitivos
    data/                           ← Base de datos de equipos y plantillas parodiadas
      betplay.py                    ← Liga BetPlay (Colombia) - Máx OVR 76
      laliga.py                     ← LaLiga (España) - Máx OVR 85
      premier.py                    ← Premier League (Inglaterra) - Máx OVR 85
      brasil.py                     ← Brasileirão (Brasil) - Máx OVR 80
      argentina.py                  ← Liga Argentina (Argentina) - Máx OVR 80
      internacional.py              ← Pools de Copa (Champions y Libertadores)
      free_agents.py                ← Generador periódico de agentes libres
    ui/                             ← Pantallas gráficas e interfaces de Pygame
      theme.py                      ← Paleta de colores neón, fuentes y estilos comunes
      menu.py                       ← Menú principal, selector de liga y club
      league_screen.py              ← Tabla de posiciones neón, agenda y alertas
      match_screen.py               ← Simulador en vivo con flash de gol y charlas tácticas
      market_screen.py              ← Grid de transferibles con control de ventanas de fichaje
      copa_screen.py                ← Árbol visual y fase de grupos internacional con bloqueo por fecha
      career_screen.py              ← Resumen histórico de campañas del manager
```

---

## Estado Actual y Funcionalidades de v0.4

### 1. Sistema Multiliga y Base de Datos Parodiada
* **5 Ligas Disponibles**: Liga BetPlay (Colombia, 8 equipos), LaLiga (España, 6 equipos), Premier League (Inglaterra, 6 equipos), Brasileirão (Brasil, 6 equipos) y Liga Argentina (Argentina, 6 equipos).
* **Nombres Parodiados**: Clubes y jugadores reales están adaptados con nombres humorísticos reconocibles (por ejemplo, *Robert Abueloski, Kylian Mbappenal, Erling Gasoland, Boca Junias, Palmeras de Sao Paulo*).
* **Ratings Balanceados por Nivel de Liga**: Límite de OVR de 85 para Europa, 80 para Sudamérica (Brasil/Argentina) y 76 para BetPlay Colombia.

### 2. Motor de Simulación y Charlas Tácticas (`engine.py`, `ui/match_screen.py`)
* Simulación minuto a minuto calibrada para marcadores realistas (2-4 goles en promedio).
* **Medio Tiempo Interactivo**: A los 45 minutos el partido se detiene y permite al DT elegir entre 4 opciones tácticas (*Charla Motivacional, Más Agresividad, Autobús Atrás, Mantener Esquema*) que alteran de forma lógica las probabilidades de la segunda mitad.
* **Animación de Gol**: Flash de pantalla intermitente y banner gigante de "¡¡¡GOOOOL!!!" mostrando el goleador estrella del club.
* **Normalización de Equipos**: El motor convierte de forma segura y dinámica objetos `models.Equipo` a `engine.Equipo` promediando los atributos de sus jugadores activos para calcular ataque, defensa y mediocampo.

### 3. Copa Internacional en Paralelo (`ui/copa_screen.py`, `ui/league_screen.py`)
* Si el club juega en Europa (Premier/LaLiga) compite en la **UEFA Champions League**. Si juega en Sudamérica (BetPlay/Brasil/Argentina), juega la **Copa Libertadores**.
* **Fechas Internacionales Simuladas**: Los partidos de copa se juegan intercalados con la temporada de liga a través de un sistema de puertas de progreso (*scheduling gates*):
  * **Copa Jornada 1**: Desbloqueada en la Jornada de Liga 2.
  * **Copa Jornada 2**: Desbloqueada en el 30% del progreso local.
  * **Copa Jornada 3**: Desbloqueada en el 50% del progreso local.
  * **Eliminatorias Directas (Octavos a Final)**: Desbloqueadas entre el 70% y el 100% del progreso de liga.
* **Alertas Gráficas**: En la pantalla de liga, si hay una fecha internacional desbloqueada y pendiente por jugar, parpadea un banner neón: `⚠️ Tienes Copa Jornada X pendiente. Ve a Copa.`.
* En la pantalla de Copa, las fases futuras muestran un texto de bloqueo: `"Bloqueado: Juega la Jornada X de Liga para desbloquear."`.

### 4. Mercado de Pases y Transferencias Rival (`market.py`, `ui/market_screen.py`)
* **Ventana de Pases Restringida**: Los fichajes solo están permitidos durante las **primeras 3** y las **últimas 3** jornadas de la temporada. Fuera de este rango, la pantalla de mercado se bloquea mostrando `"MERCADO CERRADO"`.
* **Traspasos entre Clubes de la IA**: Cada fecha hay 30% de probabilidad de que los clubes controlados por la IA intercambien jugadores entre sí (el equipo de mayor presupuesto ficha a la estrella de un club deficitario).
* **Agentes Libres**: Cada 2 jornadas se generan de 3 a 5 jugadores libres con ratings balanceados.
* **Límite de Fichajes**: Límite estricto de 3 transferencias por temporada para el usuario.

### 5. Sistema de Sonido, Playlist Shuffle y Control de Volumen (`audio.py`, `main.py`)
* Descarga e inicialización **asíncrona** en segundo plano de las URLs especificadas en `musica.txt` utilizando `yt-dlp`.
* **Reproducción en Shuffle Real**: El reproductor selecciona aleatoriamente la siguiente pista evitando patrones cíclicos y previniendo la repetición inmediata del tema anterior.
* **Widget Global de Volumen**: Un panel de control premium dibujado de manera global en la esquina superior derecha (`(1110, 20, 150, 80)`) visible en todas las pantallas. Muestra el estado del volumen (`VOL: X%` o `MUTED`), una barra de progreso elegante y tres mini botones:
  * `-` para bajar el volumen (decrementos de 10%).
  * `M` para silenciar (Mute) y restaurar el volumen al último nivel no nulo.
  * `+` para subir el volumen (incrementos de 10%).
* **Atajos de Teclado Globales**: Teclas `-` y `+` para ajustar el volumen, y `M` para silenciar/desmutear rápidamente desde cualquier pantalla de forma directa.
* **Resiliencia ante Fallos**: Si no hay internet o falta FFmpeg, el sistema de audio continúa con las pistas locales o corre en silencio de forma segura sin colgar el videojuego, manteniendo el widget de volumen operativo en modo `MUTED` o seguro.

### 6. Persistencia y Autoguardado (`save.py`, `main.py`)
* Guardado automático del archivo `alpha_football_save.json` bajo el esquema v4 al detectar el evento de cierre (`QUIT`) de Pygame.
* Carga del archivo recuperando clubes, presupuestos, historial de fichajes y progreso del manager.

---

## Control de Diseño y Ajustes de UI
* **Evitar Solapamientos**: Los nombres de los equipos en la tabla de posiciones local se limitan a 22 caracteres, en el marcador en vivo a 20, y los nombres de jugadores en las cartas del mercado a 18 para garantizar que la tipografía neón nunca se sobreponga con las columnas numéricas de estadísticas.
* **Error de Oferta de Inicio Solucionado**: Se eliminó la llamada errónea de función en el getter property `mi_equipo.jugador_estrella` en el mercado.

---

## Cómo Ejecutar el Proyecto
Para iniciar el juego de forma unificada:
```bash
python main.py
```
*(Pygame debe estar instalado en el entorno. yt-dlp y FFmpeg son recomendados para la descarga de audio).*

---

## Bitácora — v0.5 (Pygame, optimización)

* **2026-06-17 — Cambio de rumbo: NO se migra a Tauri.** La lentitud no era de Python sino del renderizado. El plan completo (optimización + todas las features + bugs) está en [`migration_and_features_plan.md`](migration_and_features_plan.md) reescrito para Pygame.
* **2026-06-17 — Fase 0 (fluidez) aplicada y verificada (headless):**
  * `ui/theme.py`: **gradiente de fondo cacheado** (antes dibujaba **720 `draw.line` por frame** en cada pantalla → ahora 1 blit de una `Surface` cacheada por tamaño); **`get_font` memoizado** (`_FONT_CACHE`, antes creaba una `Font` nueva por cada texto por frame); **`draw_text` con cache de superficies** (`_TEXT_CACHE`, acotado a 2000) para no re-renderizar el mismo texto cada frame.
  * `main.py`: los **renderers de pantalla se importan una sola vez** (dispatch dict `PANTALLAS`) en vez de `from ... import` dentro del bucle en cada frame.
  * Pendiente de Fase 0: cargar el PNG de fondo (6.6 MB) una vez + `.convert()` y revisar `.convert()` de imágenes por pantalla.
* **2026-06-17 — Bug A arreglado:** `ui/copa_screen.py` ahora importa `from typing import Optional` (la anotación de `obtener_partido_copa_pendiente` crasheaba el import de la pantalla de Copa con `NameError`).
* **2026-06-17 — Bug B arreglado:** las constantes `BLANCO`, `AMARILLO`, `GRIS_CLAR`, `VERDE_CAMPO`, `VERDE_CAMPO2` se definen ahora en `ui/theme.py` y se importan en `ui/team_screen.py` (con fallback local en el `except`).
* **Verificación:** `py_compile` de los 4 archivos OK; import real de `copa_screen`/`team_screen`/`theme` OK (Bug A/B cerrados); test headless confirmó que fuente, gradiente y texto se cachean. **Falta validar en vivo el FPS** ejecutando `python main.py` con ventana real.
* **2026-06-17 — Mecánicas de MOTOR hechas por Diego/Opus (verificadas headless):**
  * **Fase 3 — Desarrollo de jugadores:** nuevo `alpha_football/desarrollo.py` (`desarrollar_plantilla_post_partido`): nota del partido 4.0–10.0, `promedio_nota`, reparto de goles/asistencias entre MED/DEL, `progreso_desarrollo` (POR/DEF: clean sheet +0.10, nota>7.5 +0.05; MED/DEL: gol +0.20, asist +0.10, nota>7.5 +0.10), al llegar a 1.0 → +1 OVR en 3 atributos al azar, y recálculo de `valor`. Campos nuevos en `models.Jugador`: `asistencias, partidos_jugados, promedio_nota, progreso_desarrollo, valor, edad` (con defaults; `from_dict` tolerante).
  * **Fase 4 — Ofertas recibidas (IA compradora):** en `market.py`: `ventana_mercado_abierta` (jornadas 1–3 y últimas 3), `generar_ofertas_recibidas` (15%/jornada, monto = valor × Random(0.95,1.5), se guardan en `estado.mercado_ofertas`), `aceptar_oferta`/`rechazar_oferta`. (`calcular_valor` con OVR²×1000×factor_edad ya existía.)
  * **Fase 2 — Persistencia robusta:** `save.py` ya tenía escritura atómica + `.bak`; se añadió **magic + checksum SHA-256** (detecta corrupción/manipulación → carga al `.bak`) y **multislot**: `ruta_slot`, `guardar_en_slot` (con cabecera: nombre_partida, fecha, equipo, temporada, jornada, presupuesto), `cargar_slot`, `leer_cabecera_slot`, `listar_slots`.
  * **Fase 5 — Motor del partido:** ya existía en `engine.py` (`simular_partido` con `decision_mt` aplicando multiplicadores de la charla de medio tiempo a la 2ª mitad). Solo falta la pantalla en vivo (front).
  * **Verificación:** `py_compile` de los 4 módulos OK; test headless OK (Fase3: 11 jugaron, 3 goles repartidos, valores y notas; Fase4: oferta generada + aceptar traspasa y cobra; Fase2: slot+cabecera+listado y el **checksum detectó una manipulación** de `temporada`).
* **Reparto del trabajo (en el plan):** el motor queda hecho; **al orquestador van solo front-end/wiring** — UI de slots, wiring del desarrollo post-partido, buzón de ofertas, reloj en vivo + charla de medio tiempo (rellena `decision_mt`), Partido Amistoso, y Opciones + yt-dlp. Ver tabla "Estado de ejecución" en [`migration_and_features_plan.md`](migration_and_features_plan.md) con los puntos de integración exactos.
* **Siguiente:** entregar las tareas de front/wiring al orquestador (Constela) con el plan actualizado; validar el FPS en vivo con `python main.py`.
* **2026-06-17 — TODAS las features restantes implementadas por Diego/Opus (verificadas headless):**
  * **Fase 5 (partido en vivo + charla de medio tiempo):** `engine.simular_rango(local,vis,min_ini,min_fin,mult)` simula por mitades; `ui/match_screen.py` reescrito: reloj **1 seg/min** (`MS_POR_MINUTO=1000`), simula la 1ª mitad al entrar, pausa al 45, la charla (4 opciones → `CHARLAS_MT`) rellena `decision_mt` y la **2ª mitad se simula con el motor** usando esos multiplicadores (verificado: atacar fuerte sube goles 0.70→5.13). Al finalizar aplica el **desarrollo (Fase 3)** y muestra resumen (subió OVR / figura).
  * **Fase 4 (ofertas IA):** `market.crear_oferta_ui` (objetos runtime); al avanzar jornada en `match_screen` se genera (15% en ventana abierta) y se guarda en `estado['ofertas_recibidas']`; **buzón** con aceptar/rechazar en `ui/market_screen.py` (traspasa + cobra + reemplazo).
  * **Fase 7 (Opciones + música):** nueva `ui/options_screen.py` (control de volumen + barra, importador de URL de YouTube con `audio.descargar_url_async` async/fail-soft, estado de descarga, persistencia de prefs). `audio.py`: `descargar_url_async`, `estado_descarga`, `cargar/guardar_preferencias` (`preferencias.json`). **Se retiró el widget de volumen flotante** de `main.py` (atajos +/-/M se conservan; se suprimen en Opciones para poder escribir la URL).
  * **Fase 2 (multislot UI):** menú **Cargar Partida → selector de 5 slots** (`save.listar_slots` con cabecera; `save.cargar_slot`), y `main.py` autoguarda al **slot activo** al salir (primer slot libre si no hay uno asignado). Backend (atómico + magic + checksum) ya estaba.
  * **Fase 6 (Partido Amistoso):** `ui/menu.py` con pasos `amistoso_league`/`amistoso_teams` (elegir liga y los 2 equipos) + modo `amistoso` en `match_screen` (vuelve al menú, **sin** tocar liga/copa/carrera ni aplicar desarrollo).
  * **Fase 0:** las imágenes (logo, estrellas) ya se cargan una vez y se cachean en `estado`; el gradiente usa `convert()`. No hay loads por frame.
  * **Verificación:** `py_compile` de todos los módulos + smokes headless (driver `dummy`) de opciones (captura texto), load_slots, amistoso (simula 15 eventos), buzón, y los caches. **Falta solo validar FPS/look en vivo con `python main.py`.**
* **Estado: el juego v0.5 en Pygame queda COMPLETO según el plan** (optimización + bugs + multislot + desarrollo + ofertas + simulación calibrada + amistoso + opciones/yt-dlp). El plan `migration_and_features_plan.md` marca todas las fases ✅.

## Bitácora — v0.6 (mejoras de UX pedidas por Diego)

* **2026-06-18 — 6 mejoras (verificadas headless con `SDL_VIDEODRIVER=dummy`):**
  * **Pegar URL de YouTube (Ctrl+V):** `ui/options_screen.py` ahora maneja `Ctrl+V` en el campo de URL con nuevo helper `_leer_portapapeles()` (Tkinter como opción principal — fiable en Windows y en la stdlib — y `pygame.scrap` como fallback). El placeholder indica "(Ctrl+V)".
  * **Velocidad x2:** `ui/match_screen.py` usa `estado['sim_velocidad_factor']` (1 o 2, persistente) → `sim_speed = MS_POR_MINUTO // factor`. Botón `VEL x1/x2` dibujado en el marcador (`rect_velocidad`) que alterna al instante.
  * **+5 jugadores por equipo (TODOS los equipos):** nuevo módulo `alpha_football/plantilla.py` (`expandir_plantilla` / `expandir_liga`, idempotente con flag `_plantilla_expandida`). Se engancha en `menu.load_league_teams` (cubre liga/carrera/amistoso) y al final de `data/internacional.py` (cubre Copa). Suplentes generados (1 POR + relevos por línea), nivel un poco por debajo del once base. Plantillas: 11 → 16. Las partidas guardadas conservan su plantilla (no se re-expanden).
  * **Amistosos entre ligas diferentes:** `ui/menu.py` ahora usa `estado['amis_phase']` ('local'→'visitante'). Se elige liga+equipo del local y luego liga+equipo del visitante por separado (pueden ser ligas distintas). Botón "OTRA LIGA" para cambiar de liga sin perder el equipo ya elegido. Comparación por `equipo.id` para no permitir el mismo club contra sí mismo.
  * **Aviso "Sonando ahora":** `audio.py` registra `_CURRENT_TRACK_NAME` + bandera `_TRACK_CHANGED` al cambiar de pista (`cancion_actual()`, `hay_cancion_nueva()`). `main.py` (`_dibujar_now_playing`) muestra un panel abajo con el nombre de la canción durante 6 s y se oculta solo.
  * **Editar la UI de forma breve (Pygame):** `ui/theme.py` tiene un bloque "EDITA AQUÍ" con `FONT_SIZES` central (usado por `get_font`) junto a `COLORS`: cambiar colores/tamaños en un solo lugar afecta todas las pantallas. **Pendiente/decisión de Diego:** preguntó si la UI se puede hacer en HTML/CSS — eso es una migración completa a web (pywebview/Eel/Tauri), justo lo que se descartó en v0.5; queda como decisión futura, no implementada.
  * **Verificación:** `py_compile` de los 8 archivos OK; smoke headless: las 5 ligas con 16 jug/equipo (idempotente), pools de Copa a 16, API de audio presente, helper de pegado presente, `FONT_SIZES` central, e import de `match_screen`/`main` OK. **Falta validar en vivo con `python main.py` (ventana real):** look del botón VEL, toast de canción y el `Ctrl+V` real.
