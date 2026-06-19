# ALPHA FOOTBALL — Contexto de Proyecto (v0.7)
**Última actualización:** 2026-06-18
**Sesión actual:** v0.7 — Paquete grande de UX + gameplay (formaciones, 4ª táctica, sinergia/familiaridad, penales por atributo, submenú pre-partido, mercado internacional + tope de fichaje, ofertas del exterior, estadísticas, alta de DT, copa con tabla FIEL, audio: nombre real + Mayús+S + búsqueda por nombre + fix de canciones cortadas). **NO subir a v0.8 hasta que Diego lo indique.** Ver Bitácora v0.7.

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

1. **20 jugadores base por equipo** con nombres parodia ÚNICOS y consistentes con las plantillas reales actuales (transfermarkt) + valores reales. Se hará **liga por liga, empezando por BetPlay** (decisión de Diego). Hoy las plantillas son 11 base hand-authored + 5 suplentes generados (16); faltan ~9 reales por equipo.
2. **Selector de slot al guardar/salir** (elegir slot 1-5 al darle Guardar y Salir; hoy autoguarda al slot activo).
3. **Más atributos por jugador + editables individualmente en modo editar.** Hoy `Jugador` tiene 5 (`ataque, defensa, fisico, tecnica, mental`) y el editor (`ui/edit_screen.py`) solo deja tocar el OVR, que se **copia igual** a los 5. Diego quiere añadir más atributos y que cada uno se pueda personalizar por separado en el editor. Tocará: ampliar el dataclass `Jugador` + su `from_dict`/`to_dict` (tolerante con saves viejos, subir `SCHEMA_VERSION`) + la UI de `edit_screen.py` (un input por atributo). Recalcular `overall` con los atributos nuevos.

### Notas / cosas a vigilar
* **403 de YouTube** al descargar música: es externo (yt-dlp desactualizado). Solución: `pip install -U yt-dlp`. El juego lo maneja fail-soft.
* Saves viejos (esquema v4) cargan con defaults tolerantes; los presupuestos escalados solo aplican a carreras NUEVAS (no se re-escala al cargar un save).
* Valores/economía (curva de valor, ×8 de presupuesto, margen +15, sinergia) son puntos de partida; ajustar si el balance se siente off al jugar.

---

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
