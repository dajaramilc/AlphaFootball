# 🎮 Alpha Football (v0.4)

¡Bienvenido a **Alpha Football**, el simulador definitivo de gestión futbolística (manager) de escritorio con estética neón retro y dosis de humor y parodia!

Este proyecto está desarrollado sobre **Pygame** y simula la experiencia completa de un director técnico de fútbol. Dirige charlas de vestuario, gestiona el mercado de fichajes con parodias hilarantes y compite en copas continentales e internacionales en paralelo con tu liga local.

---

## 🚀 Características Clave

1. **Sistema Multiliga y Base de Datos Parodiada**:
   - Juega en 5 ligas competitivas: **Liga BetPlay (Colombia)**, **LaLiga (España)**, **Premier League (Inglaterra)**, **Brasileirão (Brasil)** y **Liga Argentina**.
   - Base de datos totalmente parodiada y humorística con nombres legendarios como *Robert Abueloski*, *Kylian Mbappenal*, *Erling Gasoland*, *Boca Junias*, o *Palmeras de Sao Paulo*.
   - Atributos y ratings balanceados por el nivel real de cada liga local (con límites de OVR acordes a cada región).

2. **Motor de Simulación y Charlas Tácticas**:
   - Motor de partidos en vivo minuto a minuto con marcadores e incidencias realistas.
   - **Tácticas en el Medio Tiempo**: Detén la simulación a los 45' para motivar a tus jugadores, ajustar la agresividad táctica, "parquear el autobús" o mantener la estrategia. Tus decisiones afectan la probabilidad de éxito en la segunda mitad.
   - Efectos visuales dinámicos: flash en pantalla para celebrar goles y banners neón gigantes de los goleadores del encuentro.

3. **Copa Internacional Intercalada**:
   - Clasifica y disputa torneos de prestigio: **UEFA Champions League** (para clubes europeos) o la **Copa Libertadores** (para clubes sudamericanos).
   - Cronograma inteligente: las fechas internacionales se habilitan en paralelo mediante compuertas de progreso (*scheduling gates*) basadas en el desarrollo de la liga local.

4. **Mercado de Pases Activo con IA**:
   - Ventanas de transferencia restringidas (primeras 3 y últimas 3 jornadas de liga).
   - IA activa: los clubes rivales pueden realizar traspasos entre sí en segundo plano.
   - Aparición periódica de **Agentes Libres** e historial de fichajes detallado.

5. **Banda Sonora, Opciones y Música de YouTube**:
   - Sistema de sonido inteligente con reproducción asíncrona (shuffle) para evitar patrones repetitivos.
   - Control de volumen en la pantalla de **Opciones** (atajos de teclado `+`, `-`, `M` siguen activos en el juego).
   - **Importar música de YouTube**: pega una URL en Opciones (incluido **Ctrl+V** desde el portapapeles) y se descarga en segundo plano con `yt-dlp`.
   - **Aviso "Sonando ahora"**: al cambiar de canción aparece el nombre de la pista en la parte inferior unos segundos y luego desaparece solo.
   - Resiliencia integrada: si la conexión falla o no hay codecs, el sistema sigue corriendo en silencio de forma segura sin colgar el juego.

6. **Persistencia e Historial**:
   - Guardado automático al salir en formato JSON.
   - Recuperación resiliente en caso de corrupción de archivos utilizando un backup `.bak` automático.

7. **Partidos, Plantillas y Velocidad (Novedades v0.5)**:
   - **Plantillas más profundas**: cada club tiene 5 suplentes extra (un arquero de respaldo y relevos por línea), tanto en liga y copa como en carrera y amistosos.
   - **Amistosos entre ligas diferentes**: elige la liga del equipo local y, por separado, la del visitante; pueden ser de ligas distintas.
   - **Velocidad x2**: durante el partido, un botón `VEL x1/x2` duplica la rapidez de la simulación al instante.

---

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.10+
- **Biblioteca Gráfica**: Pygame
- **Gestión de Audio**: `pygame.mixer` + `yt-dlp` (descarga asíncrona opcional)
- **Persistencia**: JSON Serialización (Dataclasses) con control de esquema

---

## 📁 Estructura del Proyecto

La estructura del código fuente está optimizada para la modularidad y separación de responsabilidades:

```text
AlphaFootball/
│
├── main.py                     # Punto de entrada principal y máquina de estados del juego
├── musica.txt                  # Lista de reproducción configurable (URLs de YouTube)
├── context.md                  # Archivo de contexto técnico y desarrollo del proyecto
├── README.md                   # Esta guía general
├── .gitignore                  # Exclusiones de archivos del repositorio Git
│
├── music/                      # Carpeta de pistas de audio locales (.mp3 de fallback)
│
└── alpha_football/             # Paquete principal con submódulos de lógica y UI
    ├── __init__.py
    ├── models.py               # Contratos y dataclasses del juego (Jugador, Equipo, Liga, etc.)
    ├── engine.py               # Motor de simulación del partido y lógicas de probabilidad
    ├── events.py               # Eventos e incidencias aleatorias durante el torneo
    ├── market.py               # Algoritmo de fichajes e IA de equipos rivales
    ├── audio.py                # Reproductor asíncrona shuffle y widgets de control
    ├── save.py                 # Persistencia, guardados atómicos y backups ante fallos
    │
    ├── data/                   # Plantillas, ratings y base de datos inicial de las ligas
    │   ├── argentina.py
    │   ├── betplay.py
    │   ├── brasil.py
    │   ├── free_agents.py
    │   ├── internacional.py
    │   ├── laliga.py
    │   └── premier.py
    │
    ├── assets/                 # Gráficos de texto y recursos ascii art
    │   ├── ball.txt
    │   ├── logo.txt
    │   └── stadium.txt
    │
    └── ui/                     # Pantallas del juego (Pygame)
        ├── theme.py            # Paleta de colores neón y fuentes compartidas
        ├── menu.py             # Menú de inicio y selección de club
        ├── career_screen.py    # Pantalla de historial e hitos de campaña del DT
        ├── league_screen.py    # Tabla de posiciones y agenda de jornadas
        ├── match_screen.py     # Simulador visual en vivo y medio tiempo interactivo
        ├── market_screen.py    # Panel de transferencias y cartas de jugadores
        └── copa_screen.py      # Fase de grupos y llaves de copas internacionales
```

---

## 📥 Instalación y Ejecución

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/dajaramilc/AlphaFootball.git
   cd AlphaFootball
   ```

2. **Instalar dependencias**:
   Asegúrate de contar con Pygame instalado en tu entorno de Python:
   ```bash
   pip install pygame
   ```
   *(Opcional pero recomendado: instalar `yt-dlp` para descarga asíncrona de canciones configuradas).*

3. **Ejecutar el juego**:
   ```bash
   python main.py
   ```

---

## 🎮 Controles del Juego

- **Navegación**: Click izquierdo en los botones correspondientes de la pantalla.
- **Volumen**:
  - Tecla `+`: Subir el volumen (incrementos del 10%).
  - Tecla `-`: Bajar el volumen (decrementos del 10%).
  - Tecla `M`: Silenciar / Restaurar el audio (Mute).
- **Importar música (Opciones)**: clic en el campo de URL y `Ctrl+V` para pegar, o escribe y `Enter` para descargar.
- **Velocidad del partido**: botón `VEL x1 / x2` en el marcador para duplicar la rapidez de la simulación.
- **Salir**: Clic en la `X` de la ventana para guardar automáticamente tu progreso en la partida local.
