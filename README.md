<div align="center">

# ⚽ Alpha Football

**Manager de fútbol de escritorio con estética neón retro y clubes de parodia.**
Dirige un club de 8 países día a día: arma el once, negocia fichajes, responde a la prensa,
cuida las finanzas y cumple (o no) lo que te pide la directiva.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.6-2EA44F)
![Versión](https://img.shields.io/badge/versión-0.5.0.0-FFD700)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

<img src="docs/img/hub.png" alt="Hub de la carrera" width="820">

</div>

---

## Qué es

Alpha Football es un simulador de gestión futbolística hecho en **Python + Pygame**. Eres el DT:
eliges club en una de 16 ligas (1ª y 2ª división de 8 países), avanzas por un calendario con
fechas reales, juegas los partidos en vivo minuto a minuto y manejas todo lo que pasa fuera de la
cancha: mercado, contratos, vestuario, prensa, directiva y dinero. Los clubes y jugadores son
parodias (*Manchester Billete*, *Pool de Higado*, *FC Farcelona*, *Narconal*…).

## Capturas

| Dirección de equipo | Objetivos de la directiva |
|---|---|
| <img src="docs/img/direccion.png" alt="Dirección de equipo" width="400"> | <img src="docs/img/objetivos.png" alt="Objetivos" width="400"> |
| **Finanzas** | **Hub de la carrera** |
| <img src="docs/img/finanzas.png" alt="Finanzas" width="400"> | <img src="docs/img/hub.png" alt="Hub" width="400"> |

## Características

**Mundo y calendario**
- 8 países (Inglaterra, España, Italia, Brasil, Argentina, Colombia, Uruguay, Ecuador), cada uno con 1ª y 2ª división de 12 equipos, con ascensos y descensos.
- Calendario con fechas reales: avanzas día a día (**CONTINUAR** hasta el próximo evento o **+1 DÍA**). Europa juega de agosto a mayo y Sudamérica por año calendario, cada continente con su propio cierre de temporada.
- Champions (36 clubes) y Libertadores (32) intercaladas con la liga: fase de grupos o de liga, eliminatorias de ida y vuelta y penales. El campeón vigente entra a la edición siguiente.
- Copa Intercontinental en diciembre entre el campeón de la Libertadores y el de Europa.
- Las otras ligas y copas se juegan en paralelo y se siguen desde OTRAS LIGAS.

**Partido y táctica**
- Simulación minuto a minuto con narración, velocidad x1/x2/x5, cambios y dirección en vivo.
- 17 formaciones y 9 estilos de DT (Cruyffismo, Kloppismo, Choloismo, DeZerbismo…) con ventajas entre estilos; cada formación tiene tácticas afines que dan un pequeño bonus.
- Forma de los jugadores en 5 niveles (con racha *imparable*), moral, energía que se recupera por día, lesiones que duran días o meses, tarjetas y sanciones por competición.

**Mercado**
- Ventanas de fichajes por fechas; el último día de mercado se juega hora a hora.
- Negociación con contraofertas y respuestas en días, cláusulas, préstamos con el sueldo repartido, agentes libres reales y remates de clubes en quiebra.
- Liberar jugadores pagando su indemnización.
- La IA compra y vende con criterio: cuida su saldo, protege a sus figuras y no revende a quien acaba de llegar.
- Precios según edad, posición y lesión; ojeador, favoritos e historial de pases.

**Club y dinero**
- Finanzas con taquilla, patrocinios (marcas de parodia), venta de camisetas, salarios, tope salarial y quiebra. Ningún club arranca una temporada con más de $350M.
- Historial de transacciones con la fecha de cada movimiento.
- Cantera con canteranos que suben al primer equipo.

**Carrera del DT**
- Objetivos por secciones (liga, internacional, finanzas, marca y juveniles) con premios, multas, advertencias y despido.
- Calificación de DT que te sigue entre clubes y ofertas de otros banquillos; los clubes de la IA también cambian de técnico.
- Vestuario y moral, eventos con decisiones y 31 logros.

**Noticias y prensa**
- Sección NOTICIAS y feed en el hub: fichajes (ganga, pago generoso, traición y récord de traspaso), liberaciones, rumores, títulos al instante, Balón de Oro, Sudamericano del Año, equipo del año y récords.
- Desde una noticia se abre la ficha del jugador y se le puede seguir en favoritos.
- Ruedas de prensa con 8 tonos y preguntas según la situación real del partido (grupos, ida y vuelta, pelea por el título, descenso).
- Correo con acciones directas y resumen de fin de temporada.

**Calidad de vida**
- Todo se puede jugar con teclado; la tecla **H** abre la ayuda de cada pantalla.
- 5 ranuras de guardado con guardado atómico, checksum y copia de respaldo.
- Actualización automática: al abrir, el juego compara su versión con la de GitHub y se actualiza solo.
- Editor de base de datos (clubes, jugadores, DTs libres) y música propia, con aviso si no hay ninguna instalada.

## Instalación

Requisitos: **Python 3.10+** y **pygame** (en `requirements.txt`).

```bash
git clone https://github.com/dajaramilc/AlphaFootball.git
cd AlphaFootball
pip install -r requirements.txt
python main.py
```

Las versiones nuevas llegan solas: al abrir el juego aparece el aviso de actualización.

Música: copia tus pistas (`.mp3`, `.wav`, `.ogg`, `.m4a`) en la carpeta `music/` o impórtalas
desde YouTube en OPCIONES (necesita `yt-dlp`, que el juego intenta instalar solo, y `ffmpeg`
en el PATH).

## Controles

| Dónde | Tecla |
|---|---|
| Cualquier pantalla | **H** ayuda contextual · **ESC** volver |
| Hub | **J** jugar · **D** +1 día · **N** noticias · **← →** pestañas · **R** resultados · **M** correo · **O** opciones |
| Dirección de equipo | **flechas** mover · **Espacio** cambiar · **[ ]** formación · **- =** estilo · **, .** mentalidad · **A** auto |
| Finanzas | **T** historial de transacciones |
| Ficha de un jugador ajeno | **F** agregar o quitar de favoritos |

La barra al pie de cada pantalla muestra sus atajos.

## Estructura

```
main.py                 punto de entrada y máquina de estados de pantallas
VERSION                 versión instalada (la usa el actualizador)
alpha_football/
  engine.py             motor del partido
  calendario.py, dias.py, temporadas.py   calendario por fechas y temporadas por continente
  competiciones.py, intercontinental.py   copas internacionales
  directiva.py          objetivos, calificación de DT, despido
  finanzas.py           ingresos, gastos, camisetas, historial de transacciones, quiebra
  market.py, negociacion.py, prestamos.py, mercado_ia.py, dia_final.py   mercado
  noticias.py, noticias_gen.py, rumores.py   noticias
  prensa.py             ruedas de prensa
  logros.py, premios.py logros y premios individuales
  forma.py, desarrollo.py, vestuario.py   rendimiento y progreso de los jugadores
  actualizador.py       actualización automática desde GitHub
  save.py               guardado por ranuras
  data/                 ligas, clubes, jugadores y marcas de parodia
  ui/                   una pantalla por archivo (hub, partido, noticias, finanzas…)
tests/                  tests por versión (scripts ejecutables)
docs/superpowers/       especificaciones y planes de los cambios grandes
```

## Tests

Cada archivo de `tests/` es un script que se ejecuta solo (usa una ventana *dummy*, no abre nada).
Córrelos **de a un archivo**; lanzar toda la carpeta en un solo proceso de pytest se cuelga.

```bash
python tests/test_objetivos_secciones.py
# todos, uno detrás de otro:
for f in tests/test_*.py; do python "$f" || echo "FAIL $f"; done
```

En Windows con consola cp1252, usa `PYTHONIOENCODING=utf-8` para evitar errores al imprimir.

## Licencia

Uso personal / privado. No redistribuir sin autorización del autor.
