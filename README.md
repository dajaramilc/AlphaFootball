# 🎮 Alpha Football (v0.8.7.4)

¡Bienvenido a **Alpha Football**, el simulador definitivo de gestión futbolística (manager) de escritorio con estética neón retro y dosis de humor y parodia!

Este proyecto está desarrollado sobre **Pygame** y simula la experiencia completa de un director técnico de fútbol. Dirige charlas de vestuario, gestiona el mercado de fichajes con parodias hilarantes y compite en copas continentales e internacionales en paralelo con tu liga local.

---

## 🚀 Características Clave

### 1. Sistema Multiliga y Base de Datos Parodiada
- **5 ligas competitivas**:
  - 🇨🇴 **Liga BetPlay Colombia** (8 equipos, OVR máx. 76)
  - 🇪🇸 **LaLiga EA Sports Parodia** (6 equipos, OVR máx. 85)
  - 🏴 Premier League Parodia (6 equipos, OVR máx. 85)
  - 🇧🇷 Brasileirão (6 equipos, OVR máx. 80)
  - 🇦🇷 Liga Profesional Argentina (6 equipos, OVR máx. 80)
- **Base de datos parodiada** con clubes como *Narconal*, *Real Madriz*, *FC Farcelona*, *Manchester Billete*, *Pool de Higado*, *Palmeras de Sao Paulo*, *Boca Grande*, *River Au*.
- **Plantillas de 20 jugadores** por club (v0.6): 11 titulares + 9 suplentes generados por línea.

### 2. Motor de Simulación y Táctica
- **Simulación minuto a minuto** con marcadores realistas (2-4 goles promedio).
- **Tácticas en el Medio Tiempo**: a los 45' podés elegir entre 4 charlas motivacionales (Motivación, Agresividad, Autobús, Mantener Esquema).
- **Cambios y táctica en vivo** (v0.6): pausa el partido para cambiar formación, táctica o hacer sustituciones (se anuncian en la transmisión).
- **Velocidad x1 / x2 / x5**: botón en el marcador para ajustar la rapidez al instante.
- **Sinergia formación + táctica + familiaridad** (v0.7): bonus de hasta +31% de goles cuando todo encaja.
- **Efectos visuales**: flash + banner neón "¡¡¡GOOOOL!!!" con el goleador estrella.
- **Solo titulares marcan goles** (v0.8.1): los defensas pueden cabecear en córner (8% de probabilidad); los porteros jamás atacan.

### 3. Copa Internacional Intercalada
- **Champions League** (ligas europeas) o **Copa Libertadores** (ligas sudamericanas) según el país.
- **Scheduling gates** que desbloquean las fechas internacionales según el progreso de la liga local.
- **Clasificación**: T1 = top 3 por OVR; T2+ = top 3 por puntos.
- **Copa en background** (v0.8.7.2): si no clasificás, la copa se simula sola a medida que avanzás en tu liga (mismos gates que la copa del user). Sin necesidad de tocar la pantalla de Copa.
- **Modo espectador "NO CLASIFICADO"** (v0.8.7.2): panel simple con botón "VER" para ojear el progreso en modo lectura.
- **Toast de campeón** (6s) cuando la copa termina en background.
- **Estadísticas de copa** (v0.8.6): goleadores, asistentes, vallas invictas y rendimiento del torneo.
- **Avance automático de jornada de copa** (v0.8.6): la copa salta de jornada al entrar a la pantalla, sin clics manuales.

### 4. Penales con Secuencia Ronda a Ronda (v0.8.7)
- En eliminatorias de copa del usuario que terminan 0-0:
  - Selector de 5 cobradores preseleccionados por atributo `penales`.
  - **Panel de resultado** con secuencia ronda a ronda (⚽/❌), nombres de cobradores, marcador acumulado.
  - Aviso de muerte súbita si hubo más de 5 rondas.

### 5. Mercado de Pases, Ofertas y Estadísticas
- **Ventanas de transferencia** restringidas (primeras 3 y últimas 3 jornadas).
- **Tope de fichajes por ventana** (v0.8.1): ahora sin límite rígido — solo tope por nivel del club + presupuesto + plantilla máxima (32).
- **Reset del log de fichajes** entre ventanas (v0.8.1).
- **Mercado internacional** (v0.7): pestaña para ojear talento de ligas más fuertes.
- **Bandeja de ofertas** (v0.7): ofertas locales y del exterior por jugadores destacados.
- **Filtros de precio / OVR** (v0.8.1): 12 pestañas (Todos, POR, DEF, MED, DEL, Colombia, España, Inglaterra, Brasil, Argentina, Libres, Internacional).
- **Pantalla de estadísticas**: goleadores, asistencias, vallas invictas, mejores notas (alcance: toda la liga o solo tu equipo).

### 6. Carrera del DT y Estadísticas Globales
- **Identidad del DT** (v0.7): nombre + nacionalidad al alta de carrera.
- **Historial por temporada** (v0.8.1): posición, puntos, GF/GC, liga campeona, fase de copa alcanzada.
- **Bono de fin de temporada** (v0.8.1): variable por país + continente (€30M-€150M por liga, €5M-€75M por copa).
- **"No clasificado" en historial** (v0.8.7.3): cuando el user no clasifica a la copa, el panel muestra "No clasificado" en vez de "Campeón" (bug del background sim).
- **Contador de Copas Internacionales** con fix de acentos (v0.8.7.1): chequea `'Campeón'` con acento, no `'campeon'` ASCII.

### 7. Plantillas, Amistosos y Velocidad (v0.6)
- **Plantillas más profundas**: 20 jugadores por club (suplentes generados por línea).
- **Amistosos entre ligas diferentes**: podés enfrentar un equipo local de LaLiga contra uno visitante de BetPlay, por ejemplo.
- **Velocidad x1 → x2 → x5**: botón en el marcador.

### 8. Táctica Profunda (v0.7)
- **7 formaciones**: 4-3-3, 4-4-2, 4-3-2-1, 5-4-1, 3-5-2, 3-4-1-2, 4-2-4.
- **4 estilos tácticos**: anchelottismo, cruyffismo, flickismo, haramball (con triángulo rock-paper-scissors + opción neutra).
- **AUTO ONCE sin consumir cambios** (v0.8.7): el cycler de formación y AUTO ONCE son gratis; solo el swap titular↔banco manual cuenta (tope 5 cambios por partido).
- **Cansancio y nota en menú táctico** (v0.8.1): cada titular muestra barra de cansancio y nota actual.
- **Desarrollo post-partido** (v0.7): los jugadores suben OVR cuando acumulan suficiente progreso (goles, asist, porterías a cero, nota > 7.5).

### 9. Persistencia Multislot con Cabecera Rica
- **5 slots de guardado** con cabecera que muestra: DT, equipo, temporada, jornada y **presupuesto**.
- **Guardado atómico + checksum SHA-256** (v0.5): detecta corrupción/manipulación → carga al `.bak`.
- **Carga tolerante con saves v4**.

### 10. Banda Sonora, Opciones y Música de YouTube
- **Sistema de sonido inteligente** con reproducción asíncrona (shuffle) y `_HISTORIAL_CICLO` (v0.8.6) para evitar patrones repetitivos.
- **Idempotencia de `start_music`** (v0.8.5): el end-event del mixer es el único que avanza la pista.
- **Control de volumen** en pantalla de Opciones (atajos `+`, `-`, `M` siguen activos).
- **Importar música de YouTube**: pegá una URL (soporte Ctrl+V desde portapapeles) o escribí el nombre (búsqueda con `ytsearch1:`).
- **Aviso "Sonando ahora"**: nombre de la pista actual en la parte inferior durante 6s al cambiar de canción.
- **Resiliencia**: si no hay internet o falta FFmpeg, el juego corre en silencio sin colgarse.

### 11. Dirección de Equipo + Visor Rival (v0.8.3/v0.8.7.4)
- **Panel de campo** con formación, táctica, sustituciones y once inicial.
- **Visor de alineación rival** (v0.8.3): desde el prepartido, botón "VER ALINEACIÓN RIVAL" muestra el mejor 11 del oponente en modo lectura.
- **AUTO ONCE** genera la mejor alineación por posición respetando la formación.
- **Persistencia entre modos**: amistoso no contamina los datos de la carrera (aislamiento total por `team_contexto`).

---

## 🛠️ Stack Tecnológico

| Componente | Detalle |
|---|---|
| Lenguaje | Python 3.10+ |
| Biblioteca Gráfica | Pygame (1280×720) |
| Gestión de Audio | `pygame.mixer` + `yt-dlp` (descarga asíncrona) |
| Persistencia | JSON con esquema v5 (Dataclasses serializadas limpiamente; carga tolerante con v4) |
| Resiliencia | Mecanismos de recuperación y fallbacks locales en todos los módulos críticos |

---

## 📁 Estructura del Proyecto

```text
AlphaFootball/
│
├── main.py                       # Punto de entrada y máquina de estados
├── musica.txt                    # Lista de URLs de YouTube para la banda sonora
├── context.md                    # Bitácora técnica y de desarrollo (v0.4 → v0.8.7.4)
├── README.md                     # Esta guía
├── .gitignore
│
├── music/                        # Pistas de audio locales (fallback)
│
└── alpha_football/
    ├── __init__.py
    ├── models.py                 # Dataclasses: Jugador, Equipo, Liga, Copa, EstadoJuego
    ├── engine.py                 # Motor minuto a minuto, sinergia, penales por atributo
    ├── formaciones.py            # 7 formaciones (cuotas, posiciones, táctica preferida)
    ├── desarrollo.py             # Desarrollo post-partido (OVR/valor/notas/porterías)
    ├── plantilla.py              # Expansión de plantillas hasta 20 jugadores
    ├── events.py                 # Eventos caóticos de jornada
    ├── market.py                 # Mercado + internacional + tope por nivel de club
    ├── audio.py                  # Reproductor shuffle asíncrono + importador yt-dlp
    ├── save.py                   # Multislot, cabecera rica, checksum SHA-256, .bak
    │
    ├── data/                     # DB parodiada de las 5 ligas + pools de copa
    │   ├── argentina.py
    │   ├── betplay.py
    │   ├── brasil.py
    │   ├── free_agents.py
    │   ├── internacional.py
    │   ├── laliga.py
    │   └── premier.py
    │
    ├── assets/                   # ASCII art: ball, logo, stadium
    │   ├── ball.txt
    │   ├── logo.txt
    │   └── stadium.txt
    │
    └── ui/                       # Pantallas Pygame
        ├── theme.py              # Paleta neón, fuentes, gradiente cacheado
        ├── menu.py               # Menú principal, alta de DT, selector de liga/club
        ├── career_screen.py      # Historial de campañas, estadísticas globales del DT
        ├── league_screen.py      # Tabla de posiciones (con badges de clasificados),
        │                         # agenda, historial de partidos
        ├── prepartido_screen.py  # Submenú: jugar / simular / dirección / opciones
        ├── team_screen.py        # Dirección de equipo + visor de rival
        ├── match_screen.py       # Simulador en vivo: velocidad, táctica/cambios, penales
        ├── market_screen.py      # Transferencias (local + internacional)
        ├── ofertas_screen.py     # Bandeja de ofertas recibidas
        ├── stats_screen.py       # Estadísticas de liga (goleadores, asist, vallas)
        ├── options_screen.py     # Volumen + importador de música
        ├── save_slots_screen.py  # Selector de slots con cabecera rica
        ├── edit_screen.py        # Editor de equipos y jugadores
        ├── copa_screen.py        # Copa internacional (grupos + bracket + modo espectador)
        └── resumen_temporada_screen.py  # Resumen de fin de temporada + avanzar a T2
```

---

## 📥 Instalación y Ejecución

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/dajaramilc/AlphaFootball.git
   cd AlphaFootball
   ```

2. **Instalar dependencias**:
   ```bash
   pip install pygame
   ```
   *(Opcional pero recomendado para descarga de música):* `pip install yt-dlp` y `ffmpeg` en PATH.

3. **Ejecutar el juego**:
   ```bash
   python main.py
   ```

---

## 🎮 Controles del Juego

| Acción | Control |
|---|---|
| Navegación | Click izquierdo en los botones |
| Subir volumen | Tecla `+` (incrementos de 10%) |
| Bajar volumen | Tecla `-` (decrementos de 10%) |
| Silenciar / Restaurar | Tecla `M` |
| Cambiar canción | `Shift+S` o `Ctrl+S` |
| Importar música (Opciones) | Clic en campo de URL + `Ctrl+V` o escribir nombre + `Enter` |
| Velocidad del partido | Botón `VEL x1 / x2 / x5` en el marcador |
| Salir | Clic en la `X` de la ventana (guarda automático en slot activo) |

---

## 📝 Resumen de Versiones

### v0.4 — Base original (Diego/Opus)
- Sistema multiliga, motor de simulación, copa intercalada, mercado, persistencia.

### v0.5 — Optimización + features (Diego/Opus)
- Multislot, desarrollo, ofertas, simulación calibrada, amistosos, opciones.

### v0.6 — UX + gameplay (Diego/Opus)
- Amistosos entre ligas, velocidad x2, +5 jugadores por equipo, Ctrl+V, "sonando ahora".

### v0.7 — Paquete grande (Diego/Opus)
- Formaciones (7), táctica (4 estilos), DT (alta con nombre + nacionalidad), penales, mercado internacional, ofertas, estadísticas.

### v0.8 — Estabilización y features de gameplay
- **v0.8.1**: bugs críticos + features (cansaço + nota en menú táctico, +5 jugadores en todos los equipos, ofertas como popup en mercado, bono de fin de temporada, mercado sin límite rígido con reset por ventana, filtros precio/OVR, 12 pestañas).
- **v0.8.3**: aislamiento de partidas nuevas, visor de rival desde prepartido.
- **v0.8.3.4**: 3 fixes de log-spam post-segundo-test-en-vivo.
- **v0.8.4**: fixes de raíz — match_mode de nueva carrera, filtro "Por país" entre ligas, hover de team_screen.
- **v0.8.5**: paquete grande — partido en vivo (`// None`), copa reparada (plantillas + bracket defensivo + autosim sin botón), amistoso aislado, modal borrar slot, música idempotente, $0 en mercado con fallback `calcular_valor`.
- **v0.8.6**: prepartido aislado (panel compacto sin HUB), subs con tope 5, jornada auto de copa, stats de copa, fases finales (`avanzar_fase_bracket`).
- **v0.8.7**: penales con secuencia ronda a ronda, formación + AUTO ONCE NO consumen cambios (solo swap titular↔banco cuenta), clasificación a copa (T1 = top 3 OVR, T2+ = top 3 pts), modo espectador con `SIMULAR COPA ENTERA`, fix de bracket placeholder con backtrack + anti-bucle.
- **v0.8.7.1**: fix contador "Copas Internacionales" en `career_screen` — chequeaba `'campeon'` ASCII contra `'Campeón'` con acento.
- **v0.8.7.2**: copa en background (NO CLASIFICADO + VER), DT/presupuesto en slots de Cargar/Guardar.
- **v0.8.7.3**: fix "Campeón" en historial cuando el user no clasificó (chequeo `copa_user_en_copa` antes de derivar `mejor_fase`).
- **v0.8.7.4** (actual): 3 fixes consolidados — VER ALINEACIÓN RIVAL en carrera ahora setea `team_contexto` + guard defensivo en `team_screen`; ventaja OVR invertida cuando user es visitante (diff desde la perspectiva del user); badge dorado "CHAMPIONS"/"LIBERTADORES" para top 3 en tabla de posiciones.

---

## 🧪 Verificación

Cada versión incluye smoke tests headless (`SDL_VIDEODRIVER=dummy`) que validan la lógica sin necesidad de ejecutar el juego completo. Los tests verifican:
- Lógica de motor y desarrollo
- Integridad de saves y cabeceras
- Flujo de fixtures y brackets
- Modo espectador y copa en background
- Cálculos de ventaja OVR y badges de clasificados

Para correr los tests:
```bash
python -m compileall -q alpha_football main.py
```

---

## 📂 Cómo está firmado cada cambio (autor)

| Autor | Versiones |
|---|---|
| **Diego / Opus** | v0.4, v0.5, v0.6, v0.7, v0.7.1, v0.8, v0.8.1 |
| **antigravity + claude** | v0.8.6 (antigravity implementó 2, 4, 5 + esqueleto de 1; claude terminó 1, 3) |
| **claude** | v0.8.3, v0.8.3.4, v0.8.4, v0.8.5, v0.8.7, v0.8.7.1, v0.8.7.2, v0.8.7.3, v0.8.7.4 |

---

## 📋 Pendientes Actuales

1. **Validación en vivo de v0.8.7.4** por Diego (`python main.py`).
2. **Más atributos por jugador**: ampliar `Jugador` dataclass y `edit_screen.py` con un input por atributo.
3. **Migración a UI HTML/CSS** (decisión futura, no implementada).

---

## 📄 Licencia

Uso personal / privado. No redistribuir sin autorización del autor.