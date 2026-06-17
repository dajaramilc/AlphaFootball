# ALPHA FOOTBALL — Contexto de Proyecto (v0.4)
**Última actualización:** 2026-06-08
**Sesión actual:** v0.4 — Refactor completo a UI de Escritorio (Pygame) e Integración de Copas y Mercado

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
