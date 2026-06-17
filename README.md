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

5. **Banda Sonora y Widget Global de Volumen**:
   - Sistema de sonido inteligente con reproducción asíncrona (shuffle) para evitar patrones repetitivos.
   - **Widget Global**: Ubicado permanentemente en la esquina superior derecha para subir, bajar o silenciar el sonido de forma táctil o mediante atajos de teclado (`+`, `-`, `M`).
   - Resiliencia integrada: si la conexión falla o no hay codecs, el sistema sigue corriendo en silencio de forma segura sin colgar el juego.

6. **Persistencia e Historial**:
   - Guardado automático al salir en formato JSON.
   - Recuperación resiliente en caso de corrupción de archivos utilizando un backup `.bak` automático.

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
  - Tecla `+` / Botón `+`: Subir el volumen (incrementos del 10%).
  - Tecla `-` / Botón `-`: Bajar el volumen (decrementos del 10%).
  - Tecla `M` / Botón `M`: Silenciar / Restaurar el audio (Mute).
- **Salir**: Clic en la `X` de la ventana para guardar automáticamente tu progreso en la partida local.
