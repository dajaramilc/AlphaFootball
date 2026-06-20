# ALPHA FOOTBALL — Contexto de Proyecto (v0.8.7.5)
**Última actualización:** 2026-06-19
**Sesión actual:** v0.8.7.5 — 2 fixes pedidos por Diego: (1) VER ALINEACIÓN RIVAL en carrera abría DIRECCIÓN DE EQUIPO (modo edición) cuando el user jugaba de visitante, porque el handler fijaba siempre `team_equipo_objetivo = visitante` (que ES el user de visitante) → `view_mode` quedaba False; ahora elige el oponente real. (2) El historial mostraba "Fase de grupos" en vez de "No clasificado" tras un save/load porque los flags de clasificación a copa (`copa_user_en_copa` etc.) NO se persistían → ahora se guardan/restauran en el esquema del save.

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
| Persistencia | Guardado en JSON con esquema v5 (serialización limpia de Dataclasses; carga tolerante con saves v4) |
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
    engine.py                       ← Motor minuto a minuto + sinergia formación/táctica/familiaridad + penales por atributo
    formaciones.py                  ← (v0.7) Registro de 7 formaciones: cuotas, posiciones del campo, táctica preferida, mejor_once()
    desarrollo.py                   ← Desarrollo post-partido (OVR/valor), vallas invictas, actualiza familiaridad
    events.py                       ← Eventos caóticos de jornada (lluvia, peleas, directiva, etc.)
    market.py                       ← Mercado + mercado internacional, tope de fichaje (nivel club +5), plantilla 30, ofertas exterior
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
      match_screen.py               ← Simulador en vivo: velocidad x1/x2/x5, menú táctico (en vivo + medio tiempo), penales con selección de cobradores
      market_screen.py              ← Grid de transferibles + pestaña Internacional + factibilidad de fichaje
      copa_screen.py                ← Fase de grupos (tabla FIEL: autosimula rival y recalcula siempre) y bracket
      career_screen.py              ← Resumen histórico de campañas del manager
      prepartido_screen.py          ← (v0.7) Submenú al jugar: 1. jugar, 2. simular instantáneo, 3. dirección equipo
      ofertas_screen.py             ← (v0.7) Bandeja propia de ofertas recibidas (local + exterior) con aceptar/rechazar
      stats_screen.py               ← (v0.7) Tablas: goleadores, asistencias, vallas invictas, mejores notas
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

## Bitácora — v0.7 (paquete grande de UX + gameplay pedido por Diego)

**2026-06-18 — Implementado y verificado headless (`SDL_VIDEODRIVER=dummy`). Plan en `C:\Users\diego\.claude\plans\reflective-moseying-acorn.md`.**

* **Modelos / esquema v5 (`models.py`):** `Jugador` +`penales` (con `__post_init__`: si es 0 se deriva de (técnica+mental)//2, cubre TODOS los sitios de creación) y +`porterias_cero`. `Equipo` +`nombre_corto` (property `corto`) y +`tactica_familiaridad: dict`. `EstadoJuego` +`dt_nombre`/`dt_nacionalidad`. `Alineacion.es_valida` flexible + `cumple_formacion`. `SCHEMA_VERSION=5` (carga sigue tolerante con v4).
* **Formaciones (`formaciones.py` NUEVO):** 7 formaciones (4-3-3, 4-4-2, 4-3-2-1, 5-4-1, 3-5-2, 3-4-1-2, 4-2-4) con cuotas, posiciones del campo y **táctica preferida**. Helpers `cuotas/posiciones/pref/lista_formaciones/mejor_once`.
* **Motor (`engine.py`):** 4ª táctica **anchelottismo** (equilibrada, NEUTRAL en el triángulo rock-paper-scissors). `synergy_equipo` = bonus si la táctica coincide con la preferida de la formación (+0.035) + familiaridad (hasta +0.05), acotado [0.97, 1.09] → **sinergia plena ≈ +31% goles** (calibrado: el umbral gaussiano amplifica mucho, por eso los bonos son pequeños). Se pliega en `simular_partido`/`simular_rango`. `actualizar_familiaridad` (sube al ganar/empatar, leve decay). `tanda_penales_jugadores` usa el atributo `penales` de los cobradores elegidos.
* **Desarrollo (`desarrollo.py`):** más peso a MED/DEL en goles/asistencias/nota; `porterias_cero` a los POR en valla invicta; llama a `actualizar_familiaridad` post-partido (sirve para partido en vivo Y simulación instantánea).
* **Pantalla de partido (`match_screen.py`):** velocidad **x1→x2→x5**; botón **TÁCTICA** en vivo (overlay `_menu_tactico`: formación/táctica/AUTO once + REANUDAR; al reanudar re-simula SOLO el tramo restante de la mitad); **medio tiempo** usa el mismo menú (reemplaza las 4 charlas fijas); **penales** en eliminatoria de copa del usuario → `_menu_penales` (preselecciona top-5 por `penales`) + `tanda_penales_jugadores`. `finalizar_jornada_liga` extraído y reutilizable. Nombres cortos en el marcador.
* **Submenú pre-partido (`prepartido_screen.py` NUEVO):** "JUGAR JORNADA" abre 1. jugar partido / 2. simular instantáneamente / 3. dirección equipo. `league_screen` enruta a él.
* **Dirección de equipo (`team_screen.py`):** cicladores de **formación** (7) y **táctica** (4); campo dibujado según la formación; AUTO ONCE y validación por cuotas; muestra preferida + % familiaridad.
* **Mercado (`market.py` / `market_screen.py`):** `PLANTILLA_MAXIMA=30` (+aviso "vende primero"); `nivel_club` (mejor XI) y `puede_fichar` (tope = nivel +5 → Once Caldas NO compra a un Mbappé; +dinero +30); pestaña **Internacional** (`pool_internacional`, ligas más fuertes por `FUERZA_LIGA`) que se puede ojear/ahorrar aunque no alcance; compra sin auto-reemplazo (respeta el tope 30).
* **Ofertas (`ofertas_screen.py` NUEVO + `market.crear_oferta_exterior`):** sección propia con todas las ofertas pendientes; **ofertas del exterior** (clubes de ligas más fuertes) por jugadores de buen rendimiento (monto valor×1.3–2.2). Botón **OFERTAS** con badge en el hub.
* **Estadísticas (`stats_screen.py` NUEVO):** goleadores / asistencias / vallas invictas / mejores notas; botón **ESTADÍSTICAS** en el hub.
* **Audio (`audio.py` / `main.py` / `options_screen.py`):** `cancion_actual()` da el **nombre real** (limpia "(Video Oficial)", lee ID3 con mutagen si está); **Mayús+S** cambia de pista al azar (global, suprimido en Opciones); en Opciones se puede **escribir el nombre** de la canción (`ytsearch1:` vía `descargar_por_nombre_async`). **FIX canciones cortadas:** `pygame.mixer.pre_init(44100,-16,2,4096)` antes de `pygame.init()` (el buffer por defecto de 512 hacía underrun y cortaba los MP3) + `start_music` idempotente (no reinicia la pista al volver al menú).
* **Copa (`copa_screen.py`):** **arreglado el bug reportado** — `recalcular_standings_copa` intentaba asignar `Standing.dg` (property de SOLO lectura) y crasheaba, por eso la tabla no reflejaba los partidos. Ahora: recalcula SIEMPRE al entrar + `_autosimular_rivales` (autosimula el partido rival-vs-rival de cada jornada ya jugada por el usuario) → tabla FIEL y completa. Mismo fix en la copia de `match_screen.py`. Nombres cortos en tabla/bracket; quitados los marcadores/equipos hardcodeados.
* **Inicio de carrera (`menu.py`):** nuevo paso `dt_setup` (nombre del DT + nacionalidad: lista sugerida + texto libre); al confirmar fija `estilo_dt='anchelottismo'` por defecto (cambiable). `anchelottismo` asignado a 10 clubes de juego equilibrado (Real Madriz, Junior, Santa Fe, Manchester Desunido, Chelsea, San Pablo, Fluminense, Talleres, Desindependiente, Inter/Milan/LDU en pools). `dt_nombre`/`dt_nacionalidad` persisten en los 3 guardados y se restauran al cargar.
* **Nombres cortos:** añadidos a los 6 `data/*.py` (ej. Nacional de Medellin→"Atl Nacional", Boca Amargo→"Boca", Nacionall de Montevideo→"Nacional URU", PSG, Bayerna, etc.).
* **Verificación headless:** `compileall` OK; render de las 11 pantallas sin crash; save/load roundtrip conserva todos los campos nuevos; A/B de sinergia (+31% a tope); tanda de penales respeta el atributo; copa: jugar 1 partido deja la tabla con PJ/PTS/DG correctos (autosim del rival); arranque de `main.py` sin errores. **Falta validar en vivo (`python main.py`, ventana real):** FPS, colocación de botones nuevos (TÁCTICA, OFERTAS/ESTADÍSTICAS en la barra, cicladores), look del menú táctico/penales y que los MP3 ahora suenen completos.
* **Estado: v0.7 COMPLETA según el plan.** Se mantiene en **v0.7** hasta nueva indicación de Diego.

### v0.7.1 — Ajustes pedidos por Diego tras probar en vivo (2026-06-18)

Todo verificado headless (`SDL_VIDEODRIVER=dummy`) + arranque real de `python main.py` sin crashes.

* **Audio — música cortada y selección:**
  * **Canciones completas:** `pygame.mixer.pre_init(44100,-16,2,4096)` antes de `pygame.init()` (el buffer por defecto de 512 hacía underrun y cortaba los MP3) + `start_music()` idempotente (no reinicia la pista al volver al menú).
  * **No re-crear pistas:** `audio._descargar_musica` usa un **manifiesto por URL** (`music/.descargas.json`): descarga cada URL de `musica.txt` una sola vez y lo recuerda → renombrar las pistas ya NO las vuelve a bajar como `pista_N`. Descarga con el **nombre real** del tema. Si ya hay audio en la carpeta y no hay manifiesto, lo siembra (no re-descarga lo existente).
  * **Buscar antes de descargar:** en Opciones, escribir un nombre hace **BUSCAR** (no descargar): `audio.buscar_canciones_async` (yt-dlp `ytsearchN`, sin descargar) muestra hasta 5 resultados clicables (título — canal — duración); se descarga SOLO el elegido. Las URLs siguen bajando directo.
* **Fichajes y economía (`market.py`):**
  * Margen ampliado: tope = nivel del club **+15** (antes +5) → se pueden fichar jugadores bastante mejores; el dinero pasa a ser el límite real.
  * **Valores realistas:** `calcular_valor` ahora es EXPONENCIAL anclada a la vida real (OVR85 ≈ €140M, 70 ≈ €17M, 60 ≈ €4M). Precios acordes.
  * **Presupuestos ×8** (`BUDGET_SCALE`, `escalar_presupuestos`, idempotente) al cargar ligas (`menu.load_league_teams`) y pools de copa, para que el mercado siga siendo jugable con los valores nuevos.
* **Ofertas (`market_screen.py` / `ofertas_screen.py` / `main.py`):** las ofertas **ya no aparecen como popup en el Mercado**; van solo a la sección **Ofertas** (incluida la "oferta de inicio"). Al llegar una oferta sale un **toast** arriba en pantalla (`main._dibujar_oferta_toast`, detecta crecimiento de `ofertas_recibidas`).
* **Simular instantáneamente (`prepartido_screen.py`):** muestra un overlay con **marcador + goleadores** (minuto + detalle) antes de continuar.
* **Estadísticas (`stats_screen.py`):** toggle de alcance **TODA LA LIGA** (predomina, por defecto) / **MI EQUIPO**.
* **Historial de partidos (`league_screen.py`):** panel **debajo de la tabla** con los últimos resultados del usuario (color por victoria/empate/derrota); la tabla se acortó para hacerle sitio.
* **Opciones en carrera (`prepartido_screen.py`):** opción **4. OPCIONES** en el menú de Jugar Partida (música/volumen) sin salir al menú principal (`options_return='prepartido_screen'`).
* **Cambios en vivo (`match_screen._menu_tactico`):** el menú TÁCTICA ahora muestra **TITULARES y BANCO**; tocar un titular y luego un suplente hace el **cambio**, que se **anuncia** en la transmisión ("CAMBIO: SALE X, ENTRA Y"). Sigue teniendo formación/táctica/AUTO ONCE/REANUDAR.

### PENDIENTES (acordados con Diego, para próximas sesiones)

1. **Más atributos por jugador + editables individualmente en modo editar.** Hoy `Jugador` tiene 5 (`ataque, defensa, fisico, tecnica, mental`) y el editor (`ui/edit_screen.py`) solo deja tocar el OVR, que se **copia igual** a los 5. Diego quiere añadir más atributos y que cada uno se pueda personalizar por separado en el editor. Tocará: ampliar el dataclass `Jugador` + su `from_dict`/`to_dict` (tolerante con saves viejos, subir `SCHEMA_VERSION`) + la UI de `edit_screen.py` (un input por atributo). Recalcular `overall` con los atributos nuevos.

### Notas / cosas a vigilar
* **403 de YouTube** al descargar música: es externo (yt-dlp desactualizado). Solución: `pip install -U yt-dlp`. El juego lo maneja fail-soft.
* Saves viejos (esquema v4) cargan con defaults tolerantes; los presupuestos escalados solo aplican a carreras NUEVAS (no se re-escala al cargar un save).
* Valores/economía (curva de valor, ×8 de presupuesto, margen +15, sinergia) son puntos de partida; ajustar si el balance se siente off al jugar.

---

## Bitácora — v0.8.1 (sesión 2026-06-19, paquete de bugs + features)

### Bugs corregidos

1. **Copa "no se pueden jugar partidos"** — `obtener_partido_copa_pendiente` (copa_screen.py) accedía a `estado['copa_grupo_partidos']` con corchetes directos y crasheaba con `KeyError` si la copa aún no estaba inicializada. Cambiado a `estado.get('copa_grupo_partidos') or []`. La detección de pendiente de Copa vuelve a funcionar y la pantalla de Copa se desbloquea.

2. **Jugadores del banco meten gol** — `engine.py`: nuevo helper `_once_titular(equipo)` que devuelve solo los 11 titulares (de `alineacion_activa.titulares`, con fallback a los 11 primeros no lesionados). Reemplaza el uso de `once_disponible` (que devolvía TODOS los no lesionados) en `simular_partido` y `simular_rango`. Además, en `procesar_minuto` se fuerza que el atacante venga de MED/DEL, y con **8% de probabilidad** se permite que sea un DEF (cabezazo en córner / balón parado). POR queda excluido del ataque normal. Verificado: 50 partidos simulados → POR=0%, MED+DEL≈97%, DEF≈3% (variación estadística sobre 8%).

3. **Historial de carrera en cero / "Desconocido"** — `resumen_temporada_screen.avanzar_nueva_temporada` guardaba con claves `posicion/puntos/pg/pe/pp`, pero `career_screen.py` leía `pos/pts/gf/gc/campeon_liga/libertadores`. Ninguna coincidía excepto `temporada`. Reescrito el guardado con TODAS las claves correctas + doble escritura (`pos`/`posicion`, `pts`/`puntos`) para tolerancia con saves viejos. `match_screen.py` y `prepartido_screen.py` ahora escriben `estado['copa_mejor_fase_temp']` cuando el usuario pierde/gana la copa, para que la columna "Copa Internac." del historial muestre "Cuartos / Semifinal / Finalista / Campeón" en vez de "-".

4. **Editor muestra OVR siempre en 70** — `Jugador.overall` es `@property` calculada, así que `asdict()` no la incluye. `models.py`: `Jugador.to_dict()` ahora añade `"overall": self.overall` explícitamente. `edit_screen.py`: fallback que recalcula el OVR desde los 5 atributos si el dict no lo trae (para `edited_db.json` viejos).

### Features nuevas

- **F1 — Sin límite 3 fichajes/ventana**: `market_screen.py` ya no bloquea al llegar a 3. El botón FICHAR depende solo de `_puede_fichar` (nivel del club + dinero + plantilla 32). El contador sigue ahí pero es informativo, no restrictivo.
- **F2 — Reset de `transfer_log` y `fichajes_realizados` al cambiar de ventana**: `market_screen.py` detecta la ventana actual (`T{n}_J1-3` o `T{n}_J{num-2}-{num}`); si difiere de `ultima_ventana_mercado_id`, limpia el log y resetea el contador. Verificado: ya no se acumula entre temporadas.
- **F3 — Máximo 5 cambios por partido** (solo del USUARIO): `match_screen.py` lleva `sim_subs_realizadas`, se muestra `Cambios: X / 5` en el menú táctico y al 6º intento se bloquea con mensaje en la transmisión. Se resetea al iniciar cada partido.
- **F4 — Cansancio y nota en menú táctico**: `match_screen.py` trackea `sim_minuto_por_jugador` (suma 1 por tick para cada titular en cancha) y `sim_nota_por_jugador` (base 6.0; +0.6 por gol del jugador). En el overlay del menú táctico, cada titular muestra: barra horizontal de cansancio (verde <50%, amarillo <80%, rojo ≥80% — `minutos/90 * 100`) y nota actual a la derecha. El motor ahora añade `jugador_id` al evento de gol, así que el tracking es real (no inferido).
- **F5 — Bono de fin de temporada**: `resumen_temporada_screen.avanzar_nueva_temporada` calcula bono por posición final en liga (€30M / €18M / €10M / €5M / €2M) + bono por copa (Campeón €15M, Finalista €8M, Semifinal €3M), acredita el total al `balance` del usuario y muestra banner verde con desglose en la pantalla de resumen. Se resetea `copa_mejor_fase_temp` para la nueva temporada.
- **F6 — Mercado con pestañas por país + filtros de precio/OVR**: `market_screen.py` ahora tiene 12 pestañas (Todos, POR, DEF, MED, DEL, Colombia, España, Inglaterra, Brasil, Argentina, Libres, Internacional). Las pestañas de país filtran por `equipo.tipo` (con fallback). Sobre el grid, barra compacta de filtros con 4 inputs numéricos (precio mín/máx, OVR mín/máx) + botón LIMPIAR; el filtrado se aplica antes de paginar.

### Verificación

- `compileall` 0 errores en todo el proyecto (`alpha_football/`, `alpha_football/data/`, `alpha_football/ui/`, `main.py`).
- Smoke headless: 50 partidos con 22 jugadores (11 titulares + 11 banco) confirman que solo titulares marcan y la tasa de DEF se acerca al 8% objetivo.
- Imports de los 22 módulos del juego OK.
- Sin cambios en `SCHEMA_VERSION` (las claves nuevas son retrocompatibles).

### Archivos modificados

`alpha_football/engine.py` · `alpha_football/models.py` · `alpha_football/ui/copa_screen.py` · `alpha_football/ui/match_screen.py` · `alpha_football/ui/market_screen.py` · `alpha_football/ui/prepartido_screen.py` · `alpha_football/ui/resumen_temporada_screen.py` · `alpha_football/ui/edit_screen.py`

## Bitácora — v0.8 (sesión 2026-06-19, paquete de correcciones críticas)

### Correcciones implementadas y verificadas con `compileall` ✅

1. **copa_screen.py — Bug crítico `draw_bracket_node` resuelto:** La función era llamada en 7 lugares del bracket visual pero nunca estaba definida, causando un `NameError` al entrar a la fase de eliminación directa. Se implementó la función completa: panel con `draw_panel`, borde dorado cuando participa el usuario, nombres truncados a 16 chars, marcador con color verde/rojo según avance del usuario, y `try-except` con fallback a rectángulo básico si falla el render. Todos los comentarios en español.

2. **league_screen.py — Historial de partidos ampliado:** El panel de historial pasó de mostrar solo 4 partidos con panel pequeño (`168px`) a mostrar **6 partidos** con panel más grande (`175px`). Se agregó un indicador de paginación `[X-Y de Z]` cuando hay más partidos que los visibles. El scroll con rueda funciona sobre el panel. Los botones ▲▼ están más claramente definidos.

3. **menu.py — Expansión de plantilla al cargar save:** Al cargar un slot de guardado con plantillas viejas (11 jugadores del esquema pre-v0.6), ahora se llama automáticamente a `expandir_liga(liga, 9)` para rellenar todos los equipos hasta 20 jugadores. Esto soluciona el problema de "solo veo 11 jugadores en plantilla" al cargar una partida guardada antigua.

4. **formaciones.py — Porteros solo juegan como porteros:** La función `mejor_once` ahora excluye a los jugadores de posición `POR` del relleno de campo (las últimas plazas del XI cuando faltan jugadores de alguna línea). Un portero solo se pone en posiciones de campo si no hay ningún portero disponible como último recurso.

### Estado actual
- **copa_screen**: funcional, bracket visual sin crashes ✅
- **league_screen**: historial de partidos con 6 visibles + scroll ✅
- **menu.py**: expansión de squad al cargar save ✅
- **formaciones.py**: porteros restringidos a su posición ✅
- **compileall**: 0 errores en todo el proyecto ✅

### 2026-06-18 — Renombre de ligas/equipos por Diego + verificación

* **Diego renombró** nombres de ligas y de equipos en los 6 `data/*.py` (BetPlay, LaLiga, Premier, Brasil, Argentina e internacional). Ej. actuales: BetPlay → Narconal / Pobres Vagos / ABerica de Cali / Junior daddy; LaLiga → Real Madriz / FC Farcelona; Premier → Manchester Billete / Pool de Higado; Brasil → Flamenguito / Palmeras de Sao Paulo; Argentina → Boca Grande / River Au.
* **Verificado que NO se rompió código** (real, no solo compile): `compileall` OK; las 5 ligas cargan vía `get_liga()`; los `tipo` de liga **no cambiaron** (betplay/laliga/premier/brasil/argentina) → motor, mercado y copa intactos; sin IDs de equipo duplicados; los `NOMBRES_CORTOS` de las 5 ligas siguen en sync; el save existente deserializa sin error.
* **Bug encontrado y corregido:** en `data/internacional.py` el equipo se renombró a "Paris Saint-Germain Sin Champions" pero la clave de `_NOMBRES_CORTOS_INTL` seguía como "Paris Saint Gayman" → quedaba sin `nombre_corto` (nombre largo se salía en el bracket de Champions). Clave corregida → ahora muestra "PSG".
* **README actualizado a v0.7:** nombres de liga/equipos actuales, bloque de features v0.6/v0.7 (formaciones/táctica/DT/penales, mercado internacional/ofertas/estadísticas) y árbol de estructura con los módulos y pantallas nuevas.
* **Pendiente nuevo registrado** (ver lista PENDIENTES, punto 3): más atributos por jugador y editables uno por uno en modo editar.

## Bitácora — v0.8.3 (sesión 2026-06-19, aislamiento + visor rival + hotfixes en vivo)

### Features nuevas
- **Aislamiento de partidas nuevas:** `menu.py:1053-1111` (confirmación del DT) ahora hace `estado.clear()` antes de sembrar los datos de la nueva carrera, y re-inicializa explícitamente TODAS las claves (`liga`, `mi_equipo`, `temporada`, `historial`, `transfer_log`, `ofertas_recibidas`, `mercado`, `copa_*`, `sim_*`, `now_playing_*`, etc.). Resuelve el bug donde ofertas, mercado y audio de una partida anterior (BetPlay) reaparecían al iniciar otra (Real Madriz).
- **Visor de alineación rival (F1):** nueva opción "VER ALINEACIÓN RIVAL" en `prepartido_screen`. Al pulsarla, `team_screen` entra en MODO VISOR (read-only): dibuja la mejor 11 del rival por posición (POR,DEF,MED,DEL) sobre el campo con la misma formación, y un botón "← VOLVER A MI ONCE" para regresar a editar el equipo del usuario. Implementado en `team_screen._render_team_view_mode` (línea 178).
- **Anti-shuffle en música (F2):** `audio.py` lleva `_HISTORIAL_CICLO` (set de las últimas 5 pistas) para que el shuffle no repita ni cicle; `next_track()` resetea el ciclo al cambio manual.

### Motor / Desarrollo
- **F3 — Bono POR/DEF en `desarrollo.py`:** porteros y defensas ahora reciben simétrico: base +0.04, portería a cero +0.20, ≤1 gol recibido +0.08, nota>7.5 +0.10, asistencia +0.20. Verificado con 15 partidos: 1 POR +1 OVR, 1 DEF +1 OVR.

### UI
- **Cicladores formación/táctica sin solape (Bug 3):** `team_screen.py` mueve los labels (`FORMACIÓN`/`TÁCTICA`) ARRIBA del box y el texto "Preferida..." más abajo (y=145) para que no choquen.
- **Lista de plantilla ordenada (Bug 4):** `jugadores_ordenados` reordena titulares primero, luego banco por posición (POR→DEF→MED→DEL) y OVR descendente. Hover/click ahora consistente.
- **Dots de OVR en prepartido (F4):** `_ovr_dots_render` dibuja 5 dots con OVR numérico del rival al lado del tuyo, con la diferencia centrada. Se ve en el panel pre-partido (y=90).

### Bugs corregidos
- **match_screen `simular_partidos_copa` (Bug 5):** el filtro `not p.get('jugado')` ahora aplica a TODOS los grupos, no solo a la jornada actual.
- **copa_screen autosim de rivales (Bug 6):** `_autosimular_rivales` y `encontrar_equipo_copa` endurecidos contra `None`/equipos faltantes.
- **Champions ficticios europeos (Bug 2):** los equipos del pool Champions ahora tienen nombres europeos parodiados (Ajax Legendario, Celtic Ancestral, etc.) en vez de clubes europeos reales.

### Hotfixes en vivo (post-primer-test)
1. **`menu.py:1054-1062` — KeyError `selected_liga_obj` al confirmar DT:** el bloque leía `estado['selected_liga_obj']` DESPUÉS de `estado.clear()` (siempre None → AttributeError → "alta del DT" fallaba y devolvía a menú). **Fix:** guardar `pending_equipo`, `selected_liga_obj` y `dt_nombre` a variables locales ANTES de `clear()`; el clear() solo se usa para borrar keys obsoletas, y los datos válidos se re-siembran desde las locales. Valida también que no sean None antes de continuar.
2. **`team_screen.py:332-342` — `Equipo.alineacion_activa` y `formaciones._Alineacion` no existen:** el código intentaba `team_objetivo.alineacion_activa` (Equipo no tiene ese attr) y caía al except, donde creaba `_F._Alineacion(...)` que tampoco existe en `formaciones.py`. **Fix:** reemplazar por `types.SimpleNamespace(formacion='4-4-2', titulares=[])` como stand-in ligero (solo necesitamos los atributos `formacion` y `titulares`).
3. **`team_screen.py:317-329` — `mouse_pos`/`click_pos` referenciados antes de definirse en el modo visor:** el early-return de `view_mode` saltaba la sección de eventos que define `mouse_pos`/`click_pos`. **Fix:** capturar mouse_pos y click_pos al inicio de `render()` (antes de cualquier early-return), y refrescarlos más adelante para el scroll/click del modo edición.
4. **`match_screen.py:1247` — `'NoneType' object has no attribute 'id'` (5× log spam):** `mi_equipo.id == local.id` reventaba cuando `mi_equipo` era None (caso patológico post-clear). **Fix:** envolver el bloque en `if mi_equipo is not None and local is not None:` para que el resumen de resultado solo se dibuje cuando ambos equipos están definidos.

### Verificación
- `compileall` 0 errores en los 3 archivos tocados (`menu.py`, `team_screen.py`, `match_screen.py`).
- Smoke headless: carrera nueva (LaLiga + Real Madriz + DT "Carlo Anchelotti") completa OK, modo visor del rival (FC Farcelona, 20 jug.) renderiza sin crash, match_screen con `mi_equipo=None` no rompe ni loguea spam.
- **Falta validar en vivo con `python main.py`:** confirmar que el flujo NUEVO → DT → liga ya no devuelve al menú y que "VER ALINEACIÓN RIVAL" dibuja correctamente al rival.

### Archivos modificados
- `alpha_football/ui/menu.py` (clear() + save-locales-before-clear)
- `alpha_football/ui/team_screen.py` (visor rival + mouse_pos fix)
- `alpha_football/ui/match_screen.py` (guard contra None)
- `alpha_football/audio.py` (F2 hist shuffle)
- `alpha_football/desarrollo.py` (F3 POR/DEF bonus)
- `alpha_football/ui/prepartido_screen.py` (F4 OVR dots + F1 botón rival)
- `alpha_football/ui/copa_screen.py` (Bug 5 + 6 + Champions ficticios)
- `alpha_football/data/internacional.py` (Champions ficticios)

## Bitácora — v0.8.3.4 (Diego en vivo, 2026-06-19, segundo test en vivo, fixes por claude)

### Bugs reportados por Diego tras la 2ª corrida en vivo (logs del 19/06/2026 02:42-02:48)

1. **Log spam masivo de `team_screen.py:580` — `UnboundLocalError: jugadores_ordenados referenced before assignment`** (cientos de logs en bucle). El bug: `jugadores_ordenados` se asigna en línea 596, pero se referencia en línea 580 dentro de un `if rect_lista.collidepoint(...)` que está ANTES de la asignación. Python detecta la asignación posterior y trata la variable como local en toda la función; si la asignación no se ejecuta (porque algo en medio lanza excepción o el flujo se va por otro camino), la referencia falla. **Fix aplicado:** inicializar `jugadores_ordenados = []` y `jugador_a_idx = {}` justo antes de la sección del hover (líneas ~575-577). Si la asignación posterior nunca corre, las refs al menos no rompen.

2. **Log spam en `copa_screen.py:1064` — `Error general en copa_screen.py: 'NoneType' object has no attribute 'upper'`** (decenas de logs en bucle). `copa_tipo` o `estado['copa_fase_actual']` es None cuando se entra a la pantalla de Copa sin copa inicializada o después de un clear. **Fix aplicado:** wrap con `try/except` que usa `str(copa_tipo or "COPA").upper()` y default `"Copa Internacional"` para `sub_desc`. Idem para `fase_actual.upper()` en línea 1324 y `action_to_return` en 1325.

3. **Log en `career_screen.py` — `UnboundLocalError: items_visibles referenced before assignment`** (ocurre 2×). `items_visibles = 11` se asigna dentro del bloque `else:` (cuando hay historial) pero se referencia en líneas 452, 513, 518 FUERA del if/else (en el manejo de scroll, que se ejecuta siempre). **Fix aplicado:** inicializar `items_visibles = 11` y `scroll = estado.get('career_scroll_offset', 0)` ANTES del `if not historial:` (línea ~399).

### Verificación
- `compileall` 0 errores en los 3 archivos modificados (`team_screen.py`, `career_screen.py`, `copa_screen.py`).
- **Falta validar en vivo con `python main.py`** que los 3 log-spam están cortados y el flujo NUEVO → DT → liga → DIRECCIÓN EQUIPO ya no genera errores en consola.

### Archivos modificados en v0.8.3.4
- `alpha_football/ui/team_screen.py` (init `jugadores_ordenados=[]` + `jugador_a_idx={}` antes del hover)
- `alpha_football/ui/career_screen.py` (init `items_visibles=11` + `scroll=0` antes del if/else de historial)
- `alpha_football/ui/copa_screen.py` (try/except en `.upper()` de `copa_tipo`, `copa_fase_actual`, `fase_actual`)

---

## Bitácora — v0.8.4 (sesión 2026-06-19, fixes reales por claude tras el 2º test en vivo)

Diego reportó (capturas + logs 02:42-02:48): (a) pantalla roja "ERROR: local variable 'jugadores..."
al entrar a DIRECCIÓN EQUIPO, (b) en mercado el dropdown "Por país" no muestra nada, (c) en una
**carrera nueva**, al ir a jugar partido te devuelve al menú principal. Los crashes de copa/career y
el del team_screen ya tenían band-aids de v0.8.3.4 en el working tree; esta sesión hizo los fixes de raíz.

1. **Nueva carrera → "JUGAR JORNADA" rebotaba al menú principal.** Causa: el alta de carrera
   (`menu.py` ~1090-1103) deja `estado['match_mode'] = None`. Luego `prepartido_screen`/`match_screen`
   hacían `estado.get('match_mode', 'liga')`, que devuelve **None** (la clave existe), no el default,
   y prepartido caía en `else: return "menu"`. Además `match_mode` NUNCA se asignaba `'liga'` (solo
   `'copa'` y `'amistoso'`). **Fix:** `league_screen.py` fija `estado['match_mode'] = 'liga'` al
   lanzar un partido de liga; y `prepartido_screen.py` (2 sitios) + `match_screen.py` usan
   `estado.get('match_mode') or 'liga'` (defensivo contra None).

2. **Mercado, filtro "Por país" mostraba lista vacía.** El dropdown se dibujaba bien; lo roto era el
   filtro: iteraba `estado['equipos']` (SOLO tu liga) y comparaba `eq.tipo`/`eq.liga_tipo` (atributos
   que `Equipo` no tiene; `tipo` es de `Liga`) con fallback a `estado['ligas']` (nunca poblado).
   **Fix (decisión de Diego = fichajes entre ligas):** nuevo helper resiliente
   `_cargar_equipos_por_tipo(tipo, estado)` en `market_screen.py` (lee `estado['ligas']` o cae a los
   módulos `data/{premier,laliga,betplay,brasil,argentina}.get_liga().equipos`). Al elegir un país
   distinto al de tu liga se cargan SUS equipos (cacheados por sesión en `estado['_market_ligas_cache']`,
   que se limpia al salir del mercado); con tu propio país o 'Todos' se usan los equipos persistentes.

3. **team_screen: hover sobre la plantilla.** v0.8.3.4 había puesto `jugadores_ordenados = []` antes
   del hover para cortar el `UnboundLocalError`, pero eso dejaba el hover leyendo una lista vacía.
   **Fix:** mover el cálculo de `jugadores_ordenados`/`jugador_a_idx` a ANTES del bloque de hover.

4. **copa `.upper()` sobre None y career `items_visibles`:** verificados; los guards de v0.8.3.4 ya
   los cubren. Sin cambios de código.

### Verificación
- `py_compile` OK en los 5 archivos. Imports OK bajo SDL dummy. Helper carga las 5 ligas (6-8 equipos,
  20 jugadores c/u). `None or 'liga' == 'liga'` confirmado.
- **Falta validación en vivo de Diego** (`python main.py`): nueva carrera → jugar (no rebota al menú);
  mercado "Por país" España/Inglaterra/etc. muestra jugadores y se puede fichar; hover de plantilla resalta bien.

### Archivos modificados en v0.8.4
- `alpha_football/ui/league_screen.py` (set `match_mode='liga'` al jugar jornada)
- `alpha_football/ui/prepartido_screen.py` (`get('match_mode') or 'liga'`, 2 sitios)
- `alpha_football/ui/match_screen.py` (`get('match_mode') or 'liga'`)
- `alpha_football/ui/market_screen.py` (helper `_cargar_equipos_por_tipo` + filtro país entre ligas + limpieza de cache al salir)
- `alpha_football/ui/team_screen.py` (cálculo de la lista ordenada movido antes del hover)

---

## Bitácora — v0.8.5 (sesión 2026-06-19, paquete grande post-3er test, por claude)

Diego corrió v0.8.4 y reportó 7 cosas. El run log (17.9k líneas) fue decisivo: miles de
`list index out of range` (autosim de copa), 143× KeyError `'cuartos'`, y 3×
`match_screen: // 'int' and 'NoneType'`.

1. **Partido EN VIVO rebotaba al menú de carrera.** `match_screen.py:803` hacía
   `MS_POR_MINUTO // estado['sim_velocidad_factor']`, pero la carrera nueva deja ese factor en
   None (el `setdefault` no reemplaza None) → crash → `main.py` recupera a league_screen. **Fix:**
   `factor = estado.get('sim_velocidad_factor') or 1`. Simular instantáneo funcionaba porque no
   entra a match_screen.

2. **Copa de carrera nueva rota.** (a) La copa mezcla equipos de varias ligas + 5 rellenos
   ficticios; `copa_grupos` guarda NOMBRES y `encontrar_equipo_copa` solo miraba la liga del user
   y los POOL → los demás caían a un `Equipo` mock SIN jugadores → `engine.simular_partido`
   indexaba plantilla vacía → IndexError en bucle. **Fix:** los rellenos ahora se crean CON
   plantilla (`_generar_jugadores_equipo`), se cachean TODOS los participantes por nombre en
   `estado['copa_equipos_obj']`, y `encontrar_equipo_copa` los consulta primero. Guard extra en
   `engine.simular_partido`/`simular_rango`: plantilla vacía → marcador por defecto (no crash).
   (b) `'cuartos'` KeyError: accesos directos a `copa_bracket['cuartos']` (render 1255, avanza
   833/835/1319) → ahora `.get` defensivo; y `estructura_ok` exige `copa_bracket` para reconstruir
   si falta.

3. **"SIMULAR OTROS PARTIDOS" eliminado.** Botón/acción quitados; nuevo helper
   `_autosimular_otros_grupo(estado, jornada)` simula SOLO los partidos rivales y sus resultados
   aparecen automáticamente. (Liga ya autosimulaba con `match_screen.simular_otros_partidos`.)

4. **Amistoso: dirección de equipo llevaba a la CARRERA + alineación de carrera.** `team_screen`
   usaba siempre `estado['mi_equipo']`/`estado['alineacion_activa']`. **Fix (aislamiento por
   contexto):** `estado['team_contexto']` ('amistoso' lo setea prepartido al entrar a dirección;
   'carrera' lo setean league_screen y career_screen). En amistoso, team_screen gestiona
   `estado['amis_local']` y su `alineacion_activa` propia (vuelve a prepartido). El match ya leía
   `local.alineacion_activa`, así que ahora todo el amistoso queda separado de la carrera.

5. **Modal de borrar slot parpadeaba.** `menu.py`: el mismo `click_pos` que abría el modal lo
   cerraba (el botón BORRAR queda fuera de `modal_rect`). **Fix:** `click_pos = None` al abrir.

6. **Música cortada (intermitente).** El buffer ya era correcto; el log mostró pistas de 3-4 min
   (completas) en este run. Endurecido `start_music` a idempotente real (`if IS_PLAYING: return`)
   para que SOLO el end-event avance la pista y no choque en el hueco entre pistas. Verificar en vivo.

7. **Jugadores con $0 en el mercado.** Las cards usan `calcular_precio` (≥50k), pero el modal de
   oferta de inicio mostraba `Valor: ${jug.valor}` crudo (=0 en equipos no recalculados).
   **Fix:** `getattr(jug,'valor',0) or calcular_valor(jug)` en `market_screen.py:805` (+ import de
   `calcular_valor`).

### Verificación hecha
- `py_compile` OK en los 10 archivos. Imports OK bajo SDL dummy.
- Smoke copa: init OK, los 16 equipos resuelven con ≥11 jugadores, autosim 21/24 (los 3 del user
  se excluyen), sin IndexError. Engine con plantilla vacía → 0-0 sin crash. `None or 1 == 1`.
- **Falta validación en vivo de Diego** (`python main.py`): ver la lista de verificación del plan.

### Archivos modificados en v0.8.5
- `alpha_football/ui/match_screen.py` (guard `// None`)
- `alpha_football/ui/copa_screen.py` (cache equipos + rellenos con plantilla + bracket defensivo + autosim sin botón)
- `alpha_football/engine.py` (guard plantilla vacía en simular_partido/simular_rango)
- `alpha_football/ui/prepartido_screen.py` (amistoso: btn_dir por amis_local + team_contexto)
- `alpha_football/ui/team_screen.py` (gestiona amis_local cuando team_contexto=='amistoso')
- `alpha_football/ui/league_screen.py` y `career_screen.py` (team_contexto='carrera' al ir a dirección)
- `alpha_football/ui/menu.py` (consumir clic al abrir el modal de borrado)
- `alpha_football/audio.py` (start_music idempotente real)
- `alpha_football/ui/market_screen.py` ($0 → fallback calcular_valor + import)

---

## Bitácora — v0.8.6 (sesión 2026-06-19, plan v0.8.6 — prepartido aislado, subs, copa auto + stats + fases finales)

Plan completo en `C:\Users\diego\.claude\plans\alpha-football-v0.8.6.md`. 5 tareas. Antigravity dejó las
tareas 2, 4 y 5 implementadas y un buen esqueleto de la 1 (sólo seteaba la bandera `team_modo_prepartido=True`).
Claude terminó las 2 que faltaban (Tarea 1 panel compacto en `team_screen` y Tarea 3 auto-jornada de copa),
validó todo con un smoke headless (23/23 OK) y empujó al repo.

### Tarea 1 — team_screen en modo prepartido (panel compacto sin HUB)

- **Causa:** `prepartido_screen.py:376` ya seteaba `estado['team_modo_prepartido'] = True` al pulsar
  DIRECCIÓN DE EQUIPO, pero nadie la leía en `team_screen.py`. El resultado: el HUB de carrera
  (8 botones: JUGAR/MERCADO/COPA/OFERTAS/ESTADISTICAS/HISTORIAL/GUARDAR Y SALIR) seguía apareciendo
  aunque el usuario estuviera eligiendo formación/táctica para el partido próximo.
- **Fix en `team_screen.py`:**
  - `modo_prepartido = bool(estado.get('team_modo_prepartido'))` al inicio de `render()`.
  - `ret_screen = "prepartido_screen" if (modo_prepartido or es_amistoso) else "league_screen"`.
  - Toda la barra lateral (8 botones + `menu_rect` + 3 franjas de color) y sus handlers de clic
    van gateados con `if not modo_prepartido:`.
  - Los cicladores `rect_f_*` y `rect_t_*` se REPOSICIONAN a la izquierda del panel compacto
    (los rects originales a 770,48/98 solo se usan en HUB normal). El handler de clics usa las
    mismas variables, así que sigue funcionando sin más cambios.
  - Nuevo panel compacto dibuja: nombre del club, mini-ayuda, **FORMACIÓN** y **TÁCTICA**
    bien visibles, **AUTO ONCE** (mismo `F.mejor_once`, sin contar subs porque es prepartido)
    y **VOLVER** (cancela y vuelve a prepartido). Header central cambia a "DIRECCIÓN DE EQUIPO".
  - Botones del sidebar (`btn_jugar`, `btn_mercado`, etc.) se inicializan a `None` y cada
    handler de clic tiene `not modo_prepartido and btn_X is not None and btn_X.collidepoint(...)`
    para no romper cuando están vacíos.
  - Compact panel tiene 2 botones propios: `btn_auto_pp` (AUTO ONCE sin contar subs) y
    `btn_volver_pp` (vuelve a prepartido, descartando cambios, y pop de las 2 banderas).
  - En todos los `return ret_screen` (CONFIRMAR, CANCELAR) se pop `team_modo_prepartido` cuando
    `modo_prepartido` para no dejar basura en el estado.

### Tarea 2 — AUTO ONCE / cambio de formación cuentan como cambios y respetan el tope 5

- **Causa:** en `match_screen._menu_tactico` el botón AUTO ONCE y el ciclador de formación
  hacían `alin.titulares = F.mejor_once(...)` sin tocar `sim_subs_realizadas`, así que el DT
  podía recomponer todo el equipo sin gastar cambios.
- **Fix:** helper `set(nuevos) - set(viejos)` para contar SOLO los que entran del banco.
  Si `subs_realizadas + entrantes > 5`: no aplicar y avisar por `sim_comentarios`. Si cabe:
  aplicar y sumar a `sim_subs_realizadas`. La misma lógica se aplica al ciclador de formación
  (cerraba el mismo hueco). El cambio manual titular↔banco (L646-665) ya tenía su propio
  guard con el tope 5.

### Tarea 3 — Avance automático de jornada en Copa

- **Causa:** tras jugar la jornada 1 de grupos había que pulsar "Jornada Sig." a mano para
  llegar a la 2.
- **Fix en `copa_screen.render` (justo después de `recalcular_standings_copa`):** se calcula
  la `objetivo` = menor jornada de {1,2,3} con partido del usuario no jugado y desbloqueada
  (`jornada_actual >= limites[j]`). Si existe y `copa_jornada_grupo != objetivo`, se actualiza.
  Si todas las jugables están jugadas, no se fuerza (deja navegar con Ant./Sig.).
- El bloque está dentro del `if copa_fase_actual == 'grupos':` para no interferir con la
  fase de eliminatorias.

### Tarea 4 — Panel de estadísticas de Copa (botón 📊 ESTADÍSTICAS arriba-derecha)

- **Reporte de desarrollo ampliado (`desarrollo.py`):** cada dict del `reporte` ahora incluye
  `posicion` e `id` (cambio aditivo, no rompe consumidores). Permite acumular por jugador sin
  colisiones de nombre y derivar porterías a cero.
- **Acumulador `registrar_stats_copa(estado, equipo_nombre, goles_contra, reporte)`:**
  `estado['copa_stats'][id] = {nombre, equipo, pos, goles, asist, porterias, suma_notas, pj}`.
  Suma goles/asist/nota del reporte; si `goles_contra == 0`, +1 portería a cero a los POR.
  Cada partido se simula una vez ⇒ sin doble conteo.
- **6 hooks de captura del reporte (ambos equipos en todos los partidos):**
  1. `_autosimular_otros_grupo` (rivales de grupos)
  2. `simular_partidos_ia_bracket` (rivales de eliminatorias)
  3. Rama `simular_resto_copa` en render
  4. `_autosimular_rivales` (rival-vs-rival del grupo del usuario; antes solo simulaba sin desarrollar)
  5. `prepartido._simular_instantaneo` (partido de copa simulado al instante)
  6. `match_screen` (partido de copa en vivo; ahora desarrolla AMBOS equipos y registra stats)
- **UI (`copa_screen.render`):** botón `📊 ESTADÍSTICAS` arriba-derecha (1040,20,200,40) que
  toggles `estado['copa_stats_abierto']`. Overlay con 4 secciones en grid 2×2 (top 8 c/u):
  **Goleadores** (por goles desc), **Asistentes** (por asist desc), **Porterías a cero**
  (porteros, por porterias desc) y **Rendimiento** (suma_notas/pj desc, con `pj ≥ 1`).
  Cada fila: nombre · equipo · valor. Botón CERRAR y clic fuera consume el clic (no dispara
  tabs/jugar). Las variables del overlay (`cerrar_rect`, `overlay_consumio_click`) viven en
  el mismo scope del `if estado.get('copa_stats_abierto'):` para que `cerrar_rect` esté
  definido al checkear el clic.

### Tarea 5 — Champions/Copa: cuartos/semis llaman a `avanzar_fase_bracket`

- **Causa raíz:** al ganar, `prepartido._simular_instantaneo` y `match_screen` (rama copa)
  SUBÍAN `copa_fase_actual` a mano (fases[idx+1]) sin llamar a `avanzar_fase_bracket`. Los
  otros partidos de la fase nunca se simulaban y la siguiente llave nunca se construía.
  Luego `_asegurar_bracket_normalizado` veía fase='semis' con placeholder y llamaba
  `avanzar_fase_bracket` con `fase_actual='semis'` que entraba por la rama semis→final
  equivocada.
- **Fix en los 2 finalizadores:** tras registrar goles/avanza del partido del usuario en
  `copa_bracket[fase]`, si `avanza == 'user'` y `fase_actual in ('cuartos','semis')`:
  `from alpha_football.ui.copa_screen import avanzar_fase_bracket; avanzar_fase_bracket(estado)`.
  Esa función ya simula los otros partidos de la fase, construye la siguiente llave y
  fija `copa_fase_actual`. Se ELIMINA el bump manual. Si `fase_actual == 'final'` se mantiene
  el camino a 'campeon' + `copa_mejor_fase_temp='Campeón'`. Eliminado: el flujo actual con
  `copa_mejor_fase_temp` tracking. `_asegurar_bracket_normalizado` queda como red de seguridad.

### Verificación hecha

- `python -m compileall -q alpha_football main.py` → 0 errores.
- **Smoke headless (`SDL_VIDEODRIVER=dummy`)** — 23/23 OK:
  - Imports limpios de las 4 pantallas + motor + formaciones.
  - **Tarea 2 (subs):** AUTO ONCE cuenta 1 cambio real (set-diff con 4-3-3 vs alineación inicial);
    AUTO ONCE sobre once ya óptimo = 0 cambios; cambio de formación con tope excedido = bloqueado.
  - **Tarea 3 (jornada auto):** 3 casos: autoposiciona a J2 cuando J1 jugada; no fuerza si todas
    jugadas; autoposiciona a J1 cuando es la menor pendiente.
  - **Tarea 1 (modo prepartido):** `team_screen.render` con `team_modo_prepartido=True` no crashea
    y dibuja el panel compacto; con el flag ausente (HUB) tampoco crashea.
  - **Tarea 5 (bracket):** `avanzar_fase_bracket(estado)` corre, deja `copa_fase_actual='semis'`
    y crea `copa_bracket['semis']`.
  - **Tarea 4 (stats):** `registrar_stats_copa` acumula goles/asist/notas/pj y otorga portería a
    cero SOLO a porteros con `goles_contra == 0`.
- **Falta validación en vivo de Diego** (`python main.py`):
  1. Carrera nueva → JUGAR JORNADA → DIRECCIÓN EQUIPO: panel compacto sin sidebar, cicladores
     visibles, AUTO ONCE + VOLVER. Volver regresa a prepartido.
  2. Copa: tras jugar J1, al volver a la pantalla el selector ya apunta a J2.
  3. Copa: ganar cuartos simula los otros 3 y arma semis (botón "JUGAR SEMIS" disponible);
     ganar semis arma la final.
  4. Copa: botón 📊 ESTADÍSTICAS muestra goleadores/asistentes/porterías/rendimiento del torneo.
  5. AUTO ONCE en partido en vivo: gastá cambios al entrar nuevos, no al reposicionar; respeta
     el tope 5 (al 6º intento se bloquea con un comentario en la transmisión).

### Archivos modificados en v0.8.6

**Por antigravity (en working tree al inicio):**
- `alpha_football/desarrollo.py` (+'posicion', +'id' en reporte)
- `alpha_football/ui/match_screen.py` (subs: AUTO ONCE + formación + manual con tope 5;
  juga desarrollo de AMBOS en copa + registra stats; finalizadores llaman avanzar_fase_bracket)
- `alpha_football/ui/copa_screen.py` (registrar_stats_copa, overlay con 4 secciones, botón
  📊 ESTADÍSTICAS, 4 hooks de captura del reporte, mejoras varias: cache de equipos, bracket
  defensivo, etc.)
- `alpha_football/ui/prepartido_screen.py` (set `team_modo_prepartido=True`, OVR dots,
  finalizador copa con avanzar_fase_bracket)

**Por claude (esta sesión, 2026-06-19):**
- `alpha_football/ui/team_screen.py` (Tarea 1: panel compacto modo_prepartido sin HUB, cicladores
  reposicionados, btn_auto_pp + btn_volver_pp, pop de banderas al salir)
- `alpha_football/ui/copa_screen.py` (Tarea 3: autoposicionamiento de jornada de copa en render)

---

## 🔴 ESTADO ACTUAL — Para que claude continue

**Versión:** v0.8.6 (recién aplicado por claude, pendiente validación en vivo de Diego)

**Última corrida:** Diego ejecutó `python main.py` 2026-06-19 02:42-02:48 (sobre v0.8.4, no v0.8.5 ni v0.8.6). En este momento
- v0.8.5 ya cubre los bugs críticos (partido en vivo, copa reparada, amistoso aislado, modal borrar slot).
- v0.8.6 completa el plan de prepartido (panel compacto), subs (AUTO ONCE), jornada auto de copa,
  stats de copa y fases finales.
- 23/23 tests del smoke headless pasan. Falta que Diego pruebe en vivo.

### Lo que falta (próximas sesiones)

1. **Validar en vivo v0.8.6** (`python main.py`): ver lista de los 5 puntos al final de la bitácora v0.8.6.
2. **PENDIENTE histórico de context.md** (sigue válido):
   - Más atributos por jugador y editables uno por uno en modo editar (ampliar `Jugador` dataclass, `from_dict`/`to_dict` tolerante, `edit_screen.py` con un input por atributo, recalcular `overall`).
3. **PENDIENTE menor:** revisar por qué `mi_equipo` puede ser None en `match_screen` post-clear (edge case en amistoso o al volver de un crash).
4. **PENDIENTE menor:** el editor `edit_screen.py` solo deja tocar el OVR (se copia a los 5 atributos). Decisión de diseño: ¿qué atributos quieres añadir?
5. **Decisión:** sigue en pie la pregunta de la sesión v0.5 sobre si migrar la UI a HTML/CSS (pywebview/Eel/Tauri). Diego descartó Tauri, sigue como decisión futura no implementada.

### Cómo está firmado cada cambio (autor)
- v0.4–v0.5: base original (Diego/Opus).
- v0.6: ajustes de UX (Diego/Opus).
- v0.7: paquete grande UX+gameplay (Diego/Opus).
- v0.7.1: ajustes post-test en vivo (Diego/Opus).
- v0.8: correcciones críticas (Diego/Opus).
- v0.8.1: bugs + features (Diego/Opus).
- v0.8.2: pendiente de documentar (este PR fue rápido).
- v0.8.3: aislamiento + visor rival + primer par de hotfixes en vivo (claude — plan + fixes 1, 2, 3, 4 de la bitácora).
- v0.8.3.4: 3 fixes de log-spam post-segundo-test-en-vivo (**claude**, esta sesión 2026-06-19 02:50-03:00).
- v0.8.4: fixes de raíz post-2º-test — match_mode de nueva carrera, filtro "Por país" entre ligas, hover de team_screen (**claude**, 2026-06-19 03:10-03:20).
- v0.8.5: paquete grande post-3er-test — partido en vivo (// None), copa reparada (plantillas + bracket defensivo + autosim sin botón), amistoso aislado, modal borrar slot, música idempotente, $0 en mercado (**claude**, 2026-06-19).
- v0.8.6: plan v0.8.6 — prepartido aislado (panel compacto sin HUB), subs (AUTO ONCE + formación con tope 5), jornada auto de copa, stats de copa con 6 hooks, fases finales (avanzar_fase_bracket) (**antigravity** dejó 2, 4, 5 + esqueleto de 1; **claude** terminó 1, 3 y validación 2026-06-19).

### Comandos rápidos para validar
```bash
cd "C:\Users\diego\Downloads\AlphaFootball"
python -m compileall -q alpha_football main.py
python main.py
```


## Bitácora — v0.8.7 (sesión 2026-06-19, plan v0.8.7)

Plan completo en `C:\Users\diego\.claude\plans\alpha-football-v0.8.7.md` (generado en vivo). 5 tareas, todas verificadas con smoke headless 6/6.

### Tarea 1 — Penales con secuencia ronda a ronda en `_render_resultado`
- **Causa:** `tanda_penales_jugadores` solo devolvía `(gana, "X-Y")`; el panel de resultado del prepartido solo mostraba goles del tiempo regular. La tanda quedaba enterrada en el título.
- **Fix en `engine.py`:** la firma ahora devuelve `(gana_local, marcador, secuencia)` donde `secuencia` es una lista de dicts con `ronda`, `local_mete`, `visitante_mete`, `cobrador_local`, `cobrador_visitante`. 5 rondas + muerte súbita + tope de seguridad a 30 rondas.
- **Fix en `prepartido_screen.py`:** `_simular_instantaneo` (rama copa bracket 0-0) desempaqueta los 3 valores, guarda `fase_data['penales_secuencia']` y `fase_data['penales_cobradores_l/v']`. `_render_resultado` agrega un panel lateral DERECHO (590px) con: lista de cobradores local+visitante, línea separadora azul, y SECUENCIA ronda a ronda con emojis (⚽/❌), nombres de cobradores y acumulado al final. Si hubo muerte súbita, se muestra el aviso. El botón CONTINUAR baja a y=670 para dejar sitio a los paneles.
- **Call-site `match_screen.py`:** actualizado para desempaquetar 3 valores y guardar `sim_penales_secuencia/cobradores_l/cobradores_v` (consumidos por la UI de finalizado).
- **Call-site `prepartido_screen._render_resultado`:** limpia los `sim_penales_*` al pulsar CONTINUAR.

### Tarea 2 — Formación y AUTO ONCE NO consumen cambios
- **Causa:** v0.8.6 (Tarea 2) hacía que el cycler de formación y AUTO ONCE cobraran subs reales (set-diff vs titulares), lo cual era demasiado restrictivo. Diego pidió: "solo cambiar un suplente por un titular debe consumir un cambio".
- **Fix en `match_screen._menu_tactico`:** cycler de formación (L597-614) y AUTO ONCE (L620-633) eliminan el set-diff y la lógica de cobro. Ahora:
  - Cycler formación: solo cambia `alin.formacion` y registra un comentario "sin consumir cambios".
  - AUTO ONCE: aplica `F.mejor_once(equipo.jugadores, alin.formacion)` y registra "sin consumir cambios".
  - Swap manual (titular→banco): SIGUE siendo la única vía que gasta 1 sub (tope 5).
- Header del overlay táctico: añade el recordatorio "(solo el swap manual titular↔banco cuenta)" al lado del contador "Cambios: X/5".

### Tarea 3 — Clasificación a copa (T1 = OVR top 3, T2+ = top 3 por puntos)
- **Causa:** la copa siempre incluía al user (`inicializar_copa_si_falta` agregaba `mi_equipo` a los 16). No había modo de fallar la clasificación.
- **Fix en `menu.py` (alta T1, L1104-1124):** se calcula `liga_ovr = sorted(liga_obj.equipos, key=ovr_promedio, reverse=True)[:3]`. Si `equipo.nombre in top3` → `copa_clasificado = True`; si no, `False`. Se guarda también `copa_clasificado_motivo` (texto legible: "OVR 70 (fuera del top 3)" etc.) y `copa_user_en_copa` (default True para saves viejos).
- **Fix en `resumen_temporada_screen.py` (entre 2b y 3, L134-160):** al cerrar la temporada se recalcula `copa_clasificado` por **puntos** de la liga (top 3). Se guarda la posición del user y el motivo, y se setea `copa_user_en_copa`. Esto se ejecuta ANTES de incrementar temporada, así la T2 ya arranca con el flag correcto.

### Tarea 4 — Modo espectador de copa + SIMULAR COPA ENTERA + toast de campeón
- **Causa:** cuando el user no clasifica, la copa quedaba inutilizable (botón visible pero sin partidos del user, o caía en estados raros).
- **Fix en `inicializar_copa_si_falta`:** si `copa_clasificado is False` o `copa_user_en_copa is False`, los 16 equipos se arman **sin** `mi_equipo`. Se setea `estado['copa_user_en_copa'] = False`.
- **Fix en `obtener_partido_copa_pendiente`:** si `copa_user_en_copa is False`, retorna `(None, None)` inmediatamente → no hay alerta de copa pendiente en `league_screen`.
- **Fix en `avanzar_fase_bracket` (3 ramas):** cuando el user no está en la copa, los branches de grupos→cuartos, cuartos→semis y semis→final ya NO marcan `copa_fase_actual = 'eliminado'` (porque el user no fue eliminado, simplemente no estaba). En su lugar avanzan a la siguiente fase para que la simulación automática pueda continuar.
- **Nuevo helper `_simular_featured_si_no_user(estado, fase)`:** simula el partido "featured" (`copa_bracket[fase]`) si el user no participa en él. Necesario porque `simular_partidos_ia_bracket` solo itera `copa_bracket_otros[fase]`, dejando sin simular el match del slot featured que se queda con un encuentro IA-vs-IA cuando no hay user.
- **Nuevo helper `simular_copa_entera_ia(estado)`:** orquesta la simulación completa: grupos (3 jornadas con `_autosimular_otros_grupo`) → cuartos (`_simular_featured_si_no_user` + `simular_partidos_ia_bracket`) → semis (idem) → final (idem). Al final, `copa_fase_actual = 'campeon'` y `copa_campeon = <ganador>`. Programa un toast de 6s con `copa_campeon_toast_until = pygame.time.get_ticks() + 6000`.
- **Overlay "MODO ESPECTADOR" en `copa_screen.render`:** cuando `copa_user_en_copa is False` y la copa no terminó, se dibuja un modal central (760×380) con título "MODO ESPECTADOR", motivo, explicación, y dos botones: "SIMULAR COPA ENTERA" (verde, grande) y "EXPLORAR COPA (sin simular)" (azul, más pequeño). El segundo setea `_spectator_dismissed = True` para esta sesión.
- **Toast de campeón:** se dibuja arriba a la derecha (450×60) durante 6s con "🏆 CAMPEÓN DE LA COPA" + nombre. Auto-hide vía `copa_campeon_toast_until`.
- **Click handling:** los clics en el overlay se consumen antes de pasar al resto de la UI. El botón SIMULAR dispara `simular_copa_entera_ia` y cambia a la pestaña "Fase Final". El botón EXPLORAR setea el flag dismissed.

### Tarea 5 — Fix del bug vivo: `avanzar_fase_bracket` con bracket placeholder
- **Causa:** cuando el estado de la copa estaba en una fase de eliminatorias y `copa_bracket[fase]` aún tenía la forma placeholder `{'m1':..., 'm2':...}`, `_asegurar_bracket_normalizado` llamaba a `avanzar_fase_bracket(estado)` que intentaba `s1['local']` sobre el placeholder → **KeyError: 'local'**. Cada frame, el bracket seguía siendo placeholder, así que se llamaba otra vez → bucle infinito de logs (el run de Diego generó 1M+ chars de spam).
- **Fix en `_asegurar_bracket_normalizado`:** ahora hace backtrack inteligente:
  - Si fase es `final` y `semis` es placeholder, retrocede a `cuartos` (o a `grupos` si `cuartos` también es placeholder).
  - Si fase es `semis` y `cuartos` es placeholder, retrocede a `grupos`.
  - Si fase es `cuartos`, retrocede a `grupos`.
  - Luego llama a `avanzar_fase_bracket` desde la fase correcta.
- **Anti-bloop:** `_asegurar_bracket_normalizado` ahora setea `_copa_bracket_normalizando = True` al inicio y lo limpia en `finally`. Si al inicio detecta la bandera, retorna inmediatamente (corta el bucle en el mismo frame).
- **Defensivo en `avanzar_fase_bracket` (ramas cuartos y semis):** si el bracket de la fase actual está en placeholder (sin clave 'local' a nivel raíz), log warning y return silencioso. Esto evita el KeyError incluso si `_asegurar_bracket_normalizado` no lo detectó.

### Verificación hecha
- `python -m compileall -q alpha_football main.py` → 0 errores.
- **Smoke headless (`SDL_VIDEODRIVER=dummy`)** — 6/6 OK:
  - **T1:** `tanda_penales_jugadores` con 5+5 jugadores devuelve `(gana, marcador, secuencia)` con 5+ rondas, cada una con `ronda/local_mete/visitante_mete/cobrador_local/cobrador_visitante`.
  - **T2:** formación cambia sin tocar `sim_subs_realizadas`; AUTO ONCE tampoco; swap manual sí lo incrementa.
  - **T3 (T1 OVR top 3):** liga con 6 equipos, mi_equipo con OVR 85 está en top 3, equipo con OVR 70 no.
  - **T3 (T2+ pts top 3):** liga con 6 equipos, user con 50pts está en top 3, equipo con 30pts no.
  - **T4:** copa con `copa_user_en_copa=False` se inicializa con 16 equipos SIN user; `obtener_partido_copa_pendiente` retorna `(None, None)`; `simular_copa_entera_ia` deja `copa_fase_actual='campeon'` y `copa_campeon='Real Madriz'`.
  - **T5:** inyectar `copa_bracket['semis']` en placeholder + `copa_fase_actual='semis'` y llamar `_asegurar_bracket_normalizado` 5 veces seguidas NO crashea y NO se queda en bucle.

### Lo que falta validar en vivo (Diego, `python main.py`)
1. Carrera nueva con equipo OVR top 3 → jugar la copa normal (las 5 features de v0.8.6 siguen funcionando).
2. Carrera nueva con equipo OVR #5/6 → entrar a COPA → ver overlay "MODO ESPECTADOR" → pulsar "SIMULAR COPA ENTERA" → ver cómo se llena el bracket y aparece el toast de campeón por 6s.
3. Simular instantáneamente un partido de copa bracket que quede 0-0 → ver el panel de PENALES con la secuencia ronda a ronda y los cobradores.
4. Partido en vivo: abrir menú TÁCTICA, cambiar formación 2 veces → ver contador "Cambios: 0/5". Pulsar AUTO ONCE → sigue 0/5. Swap manual → 1/5. Hasta 5/5, el 6º swap sigue bloqueado.
5. Tras llegar a la final y perder/ganar, avanzar de temporada → si quedé top 3 por puntos, `copa_clasificado=True` para T2; si no, modo espectador otra vez.
6. **Validar que el bug del bracket está cerrado:** en una carrera nueva, jugar hasta semis/final; la UI ya no debe hacer log spam ni quedarse pegada.

### Archivos modificados en v0.8.7
- `alpha_football/engine.py` — `tanda_penales_jugadores` devuelve secuencia
- `alpha_football/ui/copa_screen.py` — fix bracket placeholder + backtrack + anti-bucle + `_simular_featured_si_no_user` + `simular_copa_entera_ia` + overlay espectador + toast campeón + `inicializar_copa_si_falta` sin user + `obtener_partido_copa_pendiente` con short-circuit espectador + avanzar_fase_bracket ya no marca eliminado en modo espectador
- `alpha_football/ui/prepartido_screen.py` — captura secuencia en `_simular_instantaneo` + panel PENALES en `_render_resultado` + limpieza de sim_penales_* al continuar
- `alpha_football/ui/match_screen.py` — call-site tanda con 3 valores + `sim_penales_secuencia/cobradores_*` + formación y AUTO ONCE no gastan + recordatorio en header
- `alpha_football/ui/menu.py` — alta T1 calcula `copa_clasificado` por OVR top 3
- `alpha_football/ui/resumen_temporada_screen.py` — al cerrar temporada, `copa_clasificado` por puntos top 3

---

## Bitácora — v0.8.7.1 (sesión 2026-06-19, fix post-validación por Diego)

Diego reportó: en **HISTORIAL CARRERA → ESTADÍSTICAS GLOBALES** el contador "Copas Internacionales" salía en 0 aunque en el panel **HISTORIAL POR TEMPORADA** la fila T2 mostrase "Campeón".

### Causa raíz
`resumen_temporada_screen.py:65` guarda `mejor_fase = 'Campeón'` (con acento). Pero `career_screen.py:282` chequeaba `if 'campeon' in str(lib).lower() and 'sub' not in str(lib).lower():` (ASCII plano). En Python, `'campeon' in 'campeón'` devuelve **False** porque `ó ≠ o` → el contador `copas_won += 1` jamás se disparaba.

Misma comparación rota en L434 (`'campeon' in lib_txt.lower()` para colorear la fila). Como el chequeo fallaba, la fila mostraba el texto crudo (`"Campeón"`) — por eso parecía "funcionar" en lo visual.

### Fix en `alpha_football/ui/career_screen.py`
- Helper local `_norm_str(s)` al inicio de `render()` que reemplaza acentos (`á→a`, `é→e`, `í→i`, `ó→o`, `ú→u`, `ñ→n`) y aplica `.lower()`.
- Lógica del contador y de la fila reescritas para normalizar antes de comparar.
- Sin cambios en `SCHEMA_VERSION` (bug de UI/consumidor, no de datos).

### Verificación
Smoke headless (`SDL_VIDEODRIVER=dummy`) — 7/7 OK:
- historial con `{'libertadores':'Campeón'}` → `copas_won=1` (antes era 0).
- `{'libertadores':'Subcampeón'}` → `copas_won=0` y fila vira a `"Subcampeón 🥈"` dorado.
- Mixto T1 grupos + T2 campeón + T3 semifinal → 1 copa.
- Dos copas → 2.
- Regresión check: la lógica VIEJA con `'Campeón'` confirmado devuelve 0 (reproduce el bug).
- Fila: "Campeón" → "¡CAMPEÓN! 🌎" dorado, "Subcampeón" → "Subcampeón 🥈" dorado, "Fase de grupos" → blanco.

### Archivo modificado
- `alpha_football/ui/career_screen.py` — helper `_norm_str` + 2 sitios de comparación normalizados.

---

## Bitácora — v0.8.7.2 (sesión 2026-06-19, copa en background + info de slots)

Diego pidió:
1. Reemplazar MODO ESPECTADOR por un panel simple "NO CLASIFICADO" (sin "se simula en segundo plano mientras avanzás en tu liga").
2. Botón "VER" en vez de "VER RESULTADOS (opcional)".
3. Mostrar DT y presupuesto en los slots de Cargar/Guardar partida.

### Cambios

**1) `alpha_football/ui/copa_screen.py` — Copa en background + panel simplificado**

- **Nueva función `simular_copa_fondo(estado)`**: catch-up gradual que usa los MISMOS gates que la copa del user (J2 de liga = J1 de copa, 30% = J2, 50% = J3, 70% = cuartos, 85% = semis, 100% = final). Solo activa si `copa_user_en_copa is False`. Idempotente. Avanza grupos → cuartos → semis → final, setea `copa_campeon` y dispara el toast de 6s al final.
- **Nueva función `_get_cup_state_str(estado)`**: helper para mostrar la fase actual de la copa en el panel.
- **Reemplazo del overlay MODO ESPECTADOR (L1830-1886) → panel NO CLASIFICADO**:
  - Borde rojo (no dorado) + título "NO CLASIFICADO" en rojo
  - Subtítulo: "Tu equipo no participa en esta edición de la copa."
  - Motivo (de `copa_clasificado_motivo`)
  - Estado actual: "Copa en curso: ..." (usando `_get_cup_state_str`)
  - **Sin** el texto "se simula en segundo plano mientras avanzás en tu liga"
  - Botón único "VER" (centrado) → setea `_spectator_dismissed = True`
- **Click handler** (L1842-1860): solo maneja el botón "VER" (eliminados los handlers de SIMULAR COPA ENTERA y EXPLORAR COPA).

**2) `alpha_football/ui/match_screen.py` — Hook en `finalizar_jornada_liga`**

Después del `simular_otros_partidos` y de avanzar la jornada de liga:
```python
try:
    from alpha_football.ui.copa_screen import simular_copa_fondo
    simular_copa_fondo(estado)
except Exception as e_bg:
    logger.error(f"Error al simular copa de fondo: {e_bg}")
```
Esto se ejecuta **una vez por jornada de liga** → la copa avanza gradualmente y de forma natural.

**3) `alpha_football/save.py` — DT en la cabecera del slot**

`_construir_meta` ahora incluye `"dt_nombre"`: `str(getattr(estado, "dt_nombre", "") or "—")`. Fallback "—" para saves viejos sin el campo (backwards compatible).

**4) `alpha_football/ui/menu.py` (L1169) — Slots de Cargar: DT + presupuesto**

Antes: 1 línea con equipo + temp + jor.
Ahora: 2 líneas:
- Línea 1 (dorado): "DT: Carlito  ·  Millonarios"
- Línea 2 (azul): "Temp 2  ·  Jor 7  ·  $50.0M"

**5) `alpha_football/ui/save_slots_screen.py` (L113-117) — Slots de Guardar: mismo formato**

Consistencia con Cargar: dos líneas con DT + temp/jor/presupuesto.

### Verificación
Smoke headless (`SDL_VIDEODRIVER=dummy`) — 12/12 OK:
- (1) `simular_copa_fondo` no hace nada si user está en la copa
- (2) No hace nada antes de J2 de liga
- (3) J2 de liga → J1 de grupos jugada
- (4) J5 de liga (30%) → J1+J2 de grupos jugadas
- (5) J7 de liga (50%) → J1+J2+J3 + avanza a cuartos
- (6) J10 (70%) → cuartos + avanza a semis
- (7) J12 (85%) → semis + avanza a final
- (8) J14 (100%) → final jugada, campeon=X, toast=7000 (6000ms de display)
- (9) No simula si copa ya terminó
- (10) Idempotente (2 llamadas misma jornada = mismo resultado)
- (11) `_construir_meta` con `dt_nombre="Carlo Anchelotti"` lo incluye en el dict
- (12) `_construir_meta` sin `dt_nombre` (saves viejos) devuelve "—"

### Archivos modificados
- `alpha_football/ui/copa_screen.py` — `simular_copa_fondo` + `_get_cup_state_str` + overlay NO CLASIFICADO + click handler
- `alpha_football/ui/match_screen.py` — hook en `finalizar_jornada_liga`
- `alpha_football/save.py` — `dt_nombre` en `_construir_meta`
- `alpha_football/ui/menu.py` — slots de Cargar con DT + presupuesto
- `alpha_football/ui/save_slots_screen.py` — slots de Guardar con DT + presupuesto

---

## Bitácora — v0.8.7.3 (sesión 2026-06-19, fix "Campeón" en historial)

Diego reportó: en el **HISTORIAL POR TEMPORADA** aparecía "Campeón" en la columna "Copa Internac." de una temporada en la que NO clasificó a la copa.

### Causa raíz
v0.8.7.2 agregó `simular_copa_fondo` que avanza la copa en background cuando el user no clasificó. Al finalizar la temporada, `simular_copa_fondo` deja `copa_fase_actual='campeon'` y `copa_campeon=<otro equipo>`.

Pero `resumen_temporada_screen.py:60-70` derivaba `mejor_fase` SOLO desde `copa_fase_actual`:
```python
fase_actual = estado.get('copa_fase_actual', 'grupos')
if fase_actual == 'campeon':
    mejor_fase = 'Campeón'   # <-- BUG: aunque el user no haya jugado
```

→ El historial de T2 se guardaba con `libertadores='Campeón'` aunque el user NO participó en esa copa.

### Fix en `alpha_football/ui/resumen_temporada_screen.py`
- **2 sitios** (L60-70 en `avanzar_nueva_temporada` y L292-300 en `render`) ahora chequean `copa_user_en_copa` ANTES de derivar `mejor_fase`:
  ```python
  if not estado.get('copa_user_en_copa', True):
      mejor_fase = 'No clasificado'
  else:
      # ...existing fallback logic
  ```
- Sin cambios en `SCHEMA_VERSION` (es solo cambio de UI/datos del historial).
- El bono de copa se mantiene en 0 automáticamente porque `tabla_copa_b.get('No clasificado', 0) == 0` (la clave no existe en el dict).
- `career_screen.py` ya maneja "No clasificado" correctamente: el contador `copas_won` solo cuenta los que tengan "Campeón" en su texto normalizado.

### Verificación
Smoke headless (`SDL_VIDEODRIVER=dummy`) — 11/11 OK:
- (1) User NO clasificado + `copa_fase_actual='campeon'` (background sim terminó) → `mejor_fase='No clasificado'` ✓ (era "Campeón" antes, ahora "No clasificado")
- (2) User SÍ clasificado + ganó → "Campeón" ✓
- (3) User SÍ clasificado + semis → "Semifinal" ✓
- (4) User SÍ clasificado + eliminado → "Fase de grupos" ✓
- (5) User SÍ clasificado + cup en mid-flight → "Fase de grupos" ✓
- (6) User NO clasificado + cup en cuartos → "No clasificado" ✓
- (7) Historial mixto T1 Campeón + T2 No clasificado → `copas_won=1` ✓
- (8) Display de "No clasificado" en career_screen → texto blanco sin highlight ✓
- (9) T1 No clasificado + T2 Campeón → `copas_won=1` ✓
- (10) Ambas No clasificado → `copas_won=0` ✓
- (11) Bono de copa para "No clasificado" → €0 ✓

### Archivos modificados
- `alpha_football/ui/resumen_temporada_screen.py` — 2 sitios con guard `copa_user_en_copa` antes de derivar `mejor_fase`
- `context.md` — bitácora v0.8.7.3

### Lo que queda (validación en vivo)
1. Carrera con equipo OVR #5/6 → jugar toda la T1 sin clasificar → al cerrar T1, HISTORIAL POR TEMPORADA debe mostrar **"No clasificado"** en T1.
2. T2 avanzar a T2 → repetir → "No clasificado" en T2 también.
3. Si T3 sí clasifica y gana → T3 muestra "Campeón" + contador "Copas Internacionales: 1".
4. Verificar que el bono de fin de temporada NO incluye bono de copa cuando T1 fue "No clasificado".

---

## 🔴 ESTADO ACTUAL — Para que claude continue

**Versión:** v0.8.7.3 (recién aplicado por claude, pendiente validación en vivo de Diego)

**Última corrida:** Diego ejecutó `python main.py` 2026-06-19 02:42-02:48 (sobre v0.8.4, no v0.8.5 ni v0.8.6 ni v0.8.7). En este momento:
- v0.8.5 cubre los bugs críticos (partido en vivo, copa reparada, amistoso aislado, modal borrar slot).
- v0.8.6 completa el plan de prepartido (panel compacto), subs (AUTO ONCE), jornada auto de copa, stats de copa y fases finales.
- v0.8.7 completa los 3 pedidos de Diego (penales con secuencia + subs solo manual + clasificación a copa con modo espectador) y arregla el bug vivo del bracket.
- v0.8.7.1 cierra el bug del contador "Copas Internacionales" en `career_screen` (chequeaba `'campeon'` ASCII contra `'Campeón'` con acento).
- **v0.8.7.2** reemplaza MODO ESPECTADOR por NO CLASIFICADO + VER, agrega copa en background (`simular_copa_fondo`), y DT/presupuesto en slots de Cargar/Guardar.
- **v0.8.7.3** corrige el bug "Campeón" en historial cuando el user no clasificó: `resumen_temporada_screen` ahora chequea `copa_user_en_copa` antes de derivar `mejor_fase` (la sim de background dejaba `copa_fase_actual='campeon'` aunque el user no jugó).
- 11/11 tests del smoke headless pasan. Falta que Diego pruebe en vivo (4 puntos arriba).

### Cómo está firmado cada cambio (autor)
- v0.4–v0.5: base original (Diego/Opus).
- v0.6: ajustes de UX (Diego/Opus).
- v0.7: paquete grande UX+gameplay (Diego/Opus).
- v0.7.1: ajustes post-test en vivo (Diego/Opus).
- v0.8: correcciones críticas (Diego/Opus).
- v0.8.1: bugs + features (Diego/Opus).
- v0.8.2: pendiente de documentar.
- v0.8.3: aislamiento + visor rival + primer par de hotfixes en vivo (claude).
- v0.8.3.4: 3 fixes de log-spam post-segundo-test-en-vivo (claude).
- v0.8.4: fixes de raíz post-2º-test (claude).
- v0.8.5: paquete grande post-3er-test (claude).
- v0.8.6: plan v0.8.6 (antigravity + claude).
- v0.8.7: plan v0.8.7 — penales con secuencia, subs solo manual, clasificación a copa, modo espectador, fix bracket (claude, 2026-06-19 15:35-15:42).
- v0.8.7.1: fix contador "Copas Internacionales" (acento ó ≠ o) en `career_screen` (claude, 2026-06-19).
- **v0.8.7.2: copa en background (NO CLASIFICADO + VER), DT/presupuesto en slots, hook en finalizar_jornada_liga (claude, 2026-06-19).**
- **v0.8.7.3: fix "Campeón" en historial cuando user no clasificó. `resumen_temporada_screen.py` chequea `copa_user_en_copa` antes de derivar `mejor_fase` de `copa_fase_actual` (la sim de background deja `copa_fase_actual='campeon'` aunque el user no jugó) (claude, 2026-06-19).**
- **v0.8.7.4: 3 fixes consolidados — (A) VER ALINEACIÓN RIVAL en carrera ahora setea `team_contexto` + guard defensivo en `team_screen.py` para que NUNCA devuelva "menu" en view_mode; (B) ventaja OVR invertida cuando user es visitante (diff desde la perspectiva del user); (C) badge dorado "CHAMPIONS"/"LIBERTADORES" para top 3 en tabla de posiciones (claude, 2026-06-19).**

---

## Bitácora — v0.8.7.4 (sesión 2026-06-19, 3 fixes consolidados)

Diego reportó 3 bugs en vivo:
1. **VER ALINEACIÓN RIVAL** en prepartido de modo carrera llevaba al menú principal en vez de mostrar la alineación del rival.
2. **Ventaja OVR invertida** en el cartel del prepartido cuando el user era visitante (ej: OVR 83 vs rival 80 mostraba "-3 en contra").
3. Faltaban **labels de clasificados a copa** en la tabla de posiciones (verde en los que pasan a Champions/Libertadores).

### Cambios

**1) `alpha_football/ui/prepartido_screen.py` — VER ALINEACIÓN RIVAL + OVR visitante**

- **Fix VER ALINEACIÓN RIVAL** (L484-487): el handler del botón ahora también setea `team_contexto = 'amistoso'/'carrera'` (igual que el botón DIRECCIÓN DE EQUIPO). Sin esto, team_screen recibía un estado ambiguo y la línea 334 podía devolver "menu" si `liga`/`mi_equipo` estaban stale.
- **Fix OVR visitante** (L425-435): el cálculo de la diferencia ahora detecta si el user es local o visitante (`user_is_local = mi_equipo.id == local.id`) y calcula `diff = ovr_user - ovr_rival` desde la perspectiva del user. Antes siempre hacía `ovr_l - ovr_v` (rival - user cuando el user es visitante), mostrando el signo invertido.

**2) `alpha_football/ui/team_screen.py` — Guard defensivo para view_mode**

- **L334-336**: cuando `mi_equipo` o `liga` están stale y estamos en `view_mode` (viendo al rival), ahora se devuelve "prepartido_screen" o "league_screen" en vez de "menu". El usuario explícitamente pidió ver al rival, así que NUNCA debe rebotar al menú.

**3) `alpha_football/ui/league_screen.py` — Badge de clasificados a copa en la tabla**

- **L373**: nuevo `_badge_text` = `'CHAMPIONS'` si liga es europea (`premier`/`laliga`), `'LIBERTADORES'` si no.
- **L378-380**: el color verde de "clasificado" se aplica ahora al **top 3** (antes era top 2, leftover de cuando clasificaban 2).
- **L398+**: pill/badge dorado (255,215,0) con texto en color BG (oscuro) dibujado al lado del nombre del equipo para los top 3. Indica que ese equipo clasifica a la copa internacional.

### Verificación

Smoke headless (`SDL_VIDEODRIVER=dummy`) — 17/17 OK:
- **Fix A** (4 tests): handler setea `team_contexto`, `team_equipo_objetivo` queda al rival, regresión de DIRECCIÓN sigue OK.
- **Fix B** (5 tests): 4 combinaciones de local/visitante + iguales. Antes el caso (3) mostraba "-3 en contra" cuando debía ser "+3 a tu favor".
- **Fix C** (7 tests): los 5 tipos de liga + fallback + colores top 3 verde / medio blanco / último rojo.
- **E2E** (1 test): simulación del flow completo VER ALINEACIÓN RIVAL → no dispara early return.

### Archivos modificados
- `alpha_football/ui/prepartido_screen.py` — handler VER ALINEACIÓN RIVAL + OVR visitante
- `alpha_football/ui/team_screen.py` — guard defensivo para view_mode
- `alpha_football/ui/league_screen.py` — badge dorado top 3 + top 3 verde

### Lo que queda (validación en vivo)
1. Carrera → jugar partido → click "VER ALINEACIÓN RIVAL" → debe mostrar la alineación del rival (NO rebotar al menú).
2. Partido como visitante (OVR user 83 vs rival 80) → cartel debe mostrar "+3 a tu favor" (antes mostraba "-3 en contra").
3. Liga Premier o LaLiga → tabla de posiciones → top 3 debe mostrar badge dorado "CHAMPIONS".
4. Liga BetPlay, Brasil o Argentina → tabla de posiciones → top 3 debe mostrar badge dorado "LIBERTADORES".
5. Top 3 → nombre en VERDE; 4° en adelante → blanco; último → rojo.

---

## Bitácora — v0.8.7.5 (sesión 2026-06-19, 2 fixes pedidos por Diego)

Diego reportó 2 bugs en vivo:
1. **VER ALINEACIÓN RIVAL** (solo en modo carrera, no amistoso) abría la pantalla DIRECCIÓN TÁCTICA DE EQUIPO (modo edición del propio once) en vez del visor de la alineación rival.
2. En el **HISTORIAL CARRERA**, una temporada en la que el user NO clasificó a la copa aparecía como "Fase de grupos" en vez de "No clasificado".

### Causa raíz

**Bug 1** — `prepartido_screen.py`: el handler de "VER ALINEACIÓN RIVAL" fijaba siempre `estado['team_equipo_objetivo'] = visitante`. En liga/copa el user juega de local o de visitante según el fixture; cuando jugaba de **visitante**, ese `visitante` ES su propio equipo, así que en `team_screen` `view_mode = (team_objetivo is not mi_equipo)` daba **False** → caía al modo edición. En amistoso no pasaba porque el user siempre es `amis_local`.

**Bug 2** — persistencia: `resumen_temporada_screen.py` ya mostraba "No clasificado" cuando `copa_user_en_copa` era False, PERO ese flag (junto con `copa_clasificado`, `copa_clasificado_motivo`, `copa_mejor_fase_temp`) **no se guardaba en el save ni se restauraba al cargar**. Como el juego autoguarda al inicio de cada temporada ("T{n} J1"), al recargar el flag desaparecía y `estado.get('copa_user_en_copa', True)` caía al default `True` → el historial derivaba "Fase de grupos".

### Cambios

**1) `alpha_football/ui/prepartido_screen.py`** — handler "VER ALINEACIÓN RIVAL" (L490+): calcula el equipo que el user controla (`amis_local` en amistoso, `mi_equipo` en carrera) y elige como objetivo el OTRO equipo (`local if user_es_visitante else visitante`). Así funciona juegue de local o de visitante.

**2) Persistencia de flags de clasificación a copa** (4 archivos):
- `alpha_football/models.py` — `EstadoJuego`: 4 campos nuevos (`copa_clasificado`, `copa_user_en_copa`, `copa_clasificado_motivo`, `copa_mejor_fase_temp`) + serialización en `to_dict`/`from_dict`.
- `main.py`, `alpha_football/ui/save_slots_screen.py`, `alpha_football/ui/resumen_temporada_screen.py` — los 3 dicts de guardado incluyen los 4 campos. (El autosave de fin de temporada NO tenía campos de copa; ahora persiste la clasificación de la NUEVA temporada recién calculada.)
- `alpha_football/ui/menu.py` (carga): restaura los flags **solo si el save los trae** (no None); saves viejos quedan con la clave ausente → consumidores caen al default True (clasificado), sin romper partidas existentes.

### Verificación
- Sintaxis OK en los 5 archivos (`ast.parse`).
- Lógica de selección de rival: 3 escenarios (user local, user visitante, amistoso) devuelven el rival correcto.
- Roundtrip save→load: `copa_user_en_copa=False` se conserva; save viejo sin la clave → None (default True).

### Archivos modificados
- `alpha_football/ui/prepartido_screen.py` — selección de rival real en VER ALINEACIÓN RIVAL
- `alpha_football/models.py` — 4 campos nuevos + to_dict/from_dict
- `main.py`, `alpha_football/ui/save_slots_screen.py`, `alpha_football/ui/resumen_temporada_screen.py` — dicts de guardado
- `alpha_football/ui/menu.py` — restauración en carga
- `context.md` — bitácora v0.8.7.5

### Lo que queda (validación en vivo)
1. Carrera, jornada como **visitante** → click "VER ALINEACIÓN RIVAL" → debe mostrar el VISOR del rival (no DIRECCIÓN DE EQUIPO).
2. Carrera sin clasificar a copa → guardar/salir → cargar → terminar la temporada → HISTORIAL debe mostrar "No clasificado".

---

## 🔴 ESTADO ACTUAL — Para que claude continue

**Versión:** v0.8.7.5 (recién aplicado por claude, pendiente validación en vivo de Diego)

**Última corrida:** Diego ejecutó `python main.py` 2026-06-19 02:42-02:48 (sobre v0.8.4, no v0.8.5 ni v0.8.6 ni v0.8.7). En este momento:
- v0.8.5 cubre los bugs críticos (partido en vivo, copa reparada, amistoso aislado, modal borrar slot).
- v0.8.6 completa el plan de prepartido (panel compacto), subs (AUTO ONCE), jornada auto de copa, stats de copa y fases finales.
- v0.8.7 completa los 3 pedidos de Diego (penales con secuencia + subs solo manual + clasificación a copa con modo espectador) y arregla el bug vivo del bracket.
- v0.8.7.1 cierra el bug del contador "Copas Internacionales" en `career_screen` (chequeaba `'campeon'` ASCII contra `'Campeón'` con acento).
- v0.8.7.2 reemplaza MODO ESPECTADOR por NO CLASIFICADO + VER, agrega copa en background (`simular_copa_fondo`), y DT/presupuesto en slots de Cargar/Guardar.
- v0.8.7.3 corrige el bug "Campeón" en historial cuando el user no clasificó: `resumen_temporada_screen` ahora chequea `copa_user_en_copa` antes de derivar `mejor_fase`.
- v0.8.7.4 consolida 3 fixes: VER ALINEACIÓN RIVAL en carrera, OVR visitante invertido, badge clasificados copa.
- **v0.8.7.5** arregla 2 bugs: (1) VER ALINEACIÓN RIVAL abría DIRECCIÓN DE EQUIPO cuando el user jugaba de visitante (handler ahora elige el oponente real); (2) historial mostraba "Fase de grupos" en vez de "No clasificado" tras save/load porque los flags de clasificación a copa no se persistían (ahora se guardan/restauran).
- Smoke headless previo (17/17) sigue válido + verificación puntual de v0.8.7.5 (rival real, roundtrip save/load). Falta que Diego pruebe en vivo.

### Cómo está firmado cada cambio (autor)
- v0.4–v0.5: base original (Diego/Opus).
- v0.6: ajustes de UX (Diego/Opus).
- v0.7: paquete grande UX+gameplay (Diego/Opus).
- v0.7.1: ajustes post-test en vivo (Diego/Opus).
- v0.8: correcciones críticas (Diego/Opus).
- v0.8.1: bugs + features (Diego/Opus).
- v0.8.2: pendiente de documentar.
- v0.8.3: aislamiento + visor rival + primer par de hotfixes en vivo (claude).
- v0.8.3.4: 3 fixes de log-spam post-segundo-test-en-vivo (claude).
- v0.8.4: fixes de raíz post-2º-test (claude).
- v0.8.5: paquete grande post-3er-test (claude).
- v0.8.6: plan v0.8.6 (antigravity + claude).
- v0.8.7: plan v0.8.7 — penales con secuencia, subs solo manual, clasificación a copa, modo espectador, fix bracket (claude, 2026-06-19 15:35-15:42).
- v0.8.7.1: fix contador "Copas Internacionales" (acento ó ≠ o) en `career_screen` (claude, 2026-06-19).
- v0.8.7.2: copa en background (NO CLASIFICADO + VER), DT/presupuesto en slots, hook en finalizar_jornada_liga (claude, 2026-06-19).
- v0.8.7.3: fix "Campeón" en historial cuando user no clasificó (claude, 2026-06-19).
- v0.8.7.4: VER ALINEACIÓN RIVAL fix + OVR visitante fix + badge clasificados copa (claude, 2026-06-19).
- **v0.8.7.5: VER ALINEACIÓN RIVAL elige el oponente real (user de visitante) + persistencia de flags de clasificación a copa en el save (fix "Fase de grupos" → "No clasificado" tras load) (claude, 2026-06-19).**

### Lo que falta (próximas sesiones)

1. **Validar en vivo v0.8.7.4** (`python main.py`): ver lista de los 5 puntos al final de la bitácora v0.8.7.4 (VER ALINEACIÓN RIVAL, OVR visitante, badge clasificados).
2. **PENDIENTE histórico de context.md** (sigue válido):
   - Más atributos por jugador y editables uno por uno en modo editar (ampliar `Jugador` dataclass, `from_dict`/`to_dict` tolerante, `edit_screen.py` con un input por atributo, recalcular `overall`).
3. **PENDIENTE menor:** revisar por qué `mi_equipo` puede ser None en `match_screen` post-clear.
4. **PENDIENTE menor:** el editor `edit_screen.py` solo deja tocar el OVR (se copia a los 5 atributos). Decisión de diseño: ¿qué atributos quieres añadir?
5. **Decisión:** sigue en pie la pregunta de la sesión v0.5 sobre si migrar la UI a HTML/CSS (pywebview/Eel/Tauri). Diego descartó Tauri, sigue como decisión futura no implementada.
2. **PENDIENTE histórico de context.md** (sigue válido):
   - Más atributos por jugador y editables uno por uno en modo editar (ampliar `Jugador` dataclass, `from_dict`/`to_dict` tolerante, `edit_screen.py` con un input por atributo, recalcular `overall`).
3. **PENDIENTE menor:** revisar por qué `mi_equipo` puede ser None en `match_screen` post-clear.
4. **PENDIENTE menor:** el editor `edit_screen.py` solo deja tocar el OVR (se copia a los 5 atributos). Decisión de diseño: ¿qué atributos quieres añadir?
5. **Decisión:** sigue en pie la pregunta de la sesión v0.5 sobre si migrar la UI a HTML/CSS (pywebview/Eel/Tauri). Diego descartó Tauri, sigue como decisión futura no implementada.
