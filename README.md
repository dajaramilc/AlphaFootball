# 🎮 Alpha Football (v0.7)

¡Bienvenido a **Alpha Football**, el simulador definitivo de gestión futbolística (manager) de escritorio con estética neón retro y dosis de humor y parodia!

Este proyecto está desarrollado sobre **Pygame** y simula la experiencia completa de un director técnico de fútbol. Dirige charlas de vestuario, gestiona el mercado de fichajes con parodias hilarantes y compite en copas continentales e internacionales en paralelo con tu liga local.

---

## 🚀 Características Clave

1. **Sistema Multiliga y Base de Datos Parodiada**:
   - Juega en 5 ligas competitivas: **Liga BetPlay Colombia**, **LaLiga EA Sports Parodia**, **Premier League Parodia**, **Brasileirão Brasil** y **Liga Profesional Argentina**.
   - Base de datos totalmente parodiada y humorística con clubes como *Narconal*, *Real Madriz*, *FC Farcelona*, *Manchester Billete*, *Pool de Higado*, *Palmeras de Sao Paulo* o *Boca Grande*.
   - Atributos y ratings balanceados por el nivel real de cada liga local (límites de OVR: 85 Europa, 80 Sudamérica, 76 BetPlay).

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

7. **Partidos, Plantillas y Velocidad (v0.5–v0.6)**:
   - **Plantillas más profundas**: cada club se rellena hasta 20 jugadores (suplentes generados por línea), tanto en liga y copa como en carrera y amistosos.
   - **Amistosos entre ligas diferentes**: elige la liga del equipo local y, por separado, la del visitante; pueden ser de ligas distintas.
   - **Velocidad x1/x2/x5**: durante el partido un botón duplica/quintuplica la rapidez de la simulación al instante.

8. **Táctica Profunda, DT y Penales (v0.7)**:
   - **7 formaciones** (4-3-3, 4-4-2, 5-4-1, 3-5-2, etc.) y **4 estilos tácticos** con sistema de sinergia (la táctica que encaja con la formación + la familiaridad acumulada potencian al equipo).
   - **Cambios y táctica en vivo**: pausa el partido para cambiar formación, estilo, hacer sustituciones (se anuncian en la transmisión) o repartir la charla de medio tiempo.
   - **Identidad del DT**: al iniciar carrera eliges nombre y nacionalidad del entrenador.
   - **Penales por atributo**: en eliminatorias eliges a tus cobradores y su atributo `penales` decide la tanda.

9. **Mercado Avanzado, Ofertas y Estadísticas (v0.7)**:
   - **Mercado internacional**: pestaña para ojear/fichar talento de ligas más fuertes, con tope de fichaje por nivel de club y plantilla máxima de 30.
   - **Bandeja de ofertas**: recibe ofertas locales y del exterior por tus jugadores destacados, con aceptar/rechazar.
   - **Pantalla de estadísticas**: goleadores, asistencias, vallas invictas y mejores notas (toda la liga o solo tu equipo).

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
    ├── engine.py               # Motor de simulación del partido, sinergia táctica y penales
    ├── formaciones.py          # Registro de 7 formaciones (cuotas, posiciones, táctica preferida)
    ├── desarrollo.py           # Desarrollo post-partido de jugadores (OVR/valor/notas)
    ├── plantilla.py            # Expansión de plantillas hasta 20 jugadores (suplentes)
    ├── events.py               # Eventos e incidencias aleatorias durante el torneo
    ├── market.py               # Algoritmo de fichajes, mercado internacional e IA rival
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
        ├── menu.py             # Menú de inicio, alta de DT y selección de club
        ├── career_screen.py    # Pantalla de historial e hitos de campaña del DT
        ├── league_screen.py    # Tabla de posiciones, agenda e historial de partidos
        ├── prepartido_screen.py# Submenú al jugar: jugar / simular / dirección / opciones
        ├── team_screen.py      # Dirección de equipo: formación, táctica y once
        ├── match_screen.py     # Simulador en vivo: velocidad, táctica/cambios y penales
        ├── market_screen.py    # Panel de transferencias (local e internacional)
        ├── ofertas_screen.py   # Bandeja de ofertas recibidas (local y del exterior)
        ├── stats_screen.py     # Estadísticas: goleadores, asistencias, vallas invictas
        ├── options_screen.py   # Opciones de audio e importador de música
        ├── save_slots_screen.py# Selector de slots de guardado
        ├── edit_screen.py      # Editor de equipos y jugadores
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
