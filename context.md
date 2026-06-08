# ALPHA FOOTBALL — Context de Proyecto
**Última actualización:** 2026-06-07
**Sesión actual:** v0.3 — persistencia entre temporadas implementada

---

## Identidad del Proyecto

**Alpha Football** es un prototipo de manager de fútbol jugable en consola, ambientado en la Liga BetPlay de Colombia. El objetivo es validar si las mecánicas centrales (atributos de jugadores, rasgos, estilos tácticos tipo piedra-papel-tijera, eventos caóticos, Copa Libertadores) son divertidas en una sesión de juego. Si el prototipo engancha, la siguiente fase sería implementarlo en Godot como juego completo.

**Filosofía:** un archivo `.py` solo, sin dependencias externas obligatorias, corriendo en cualquier terminal con Python 3.10+. Colorama es opcional (colores si está, texto plano si no).

---

## Stack Técnico

| Item | Detalle |
|---|---|
| Lenguaje | Python 3.10+ |
| Librerías | Solo estándar (`random`, `os`, `sys`, `time`, `dataclasses`, `typing`) |
| Dependencia opcional | `colorama` para colores en consola |
| Compatibilidad | Windows, Linux, Mac |
| Encoding | UTF-8 forzado en Windows (`sys.stdout.reconfigure`) con detección de soporte emoji |
| Archivo único | `alpha_football.py` — 1419 líneas en v0.3 |

---

## Ubicación del Archivo

```
C:\Users\diego\Downloads\AlphaFootball 0.01\
  alpha_football.py     ← juego principal (v0.3)
  context.md            ← este archivo
  AlphaFootball_Plan_Maestro_v0.01.docx  ← visión original
```

**Cómo ejecutar:**
```bash
python "C:\Users\diego\Downloads\AlphaFootball 0.01\alpha_football.py"
```

---

## Estado Actual — v0.3

### Lo que está implementado y funciona

#### Liga BetPlay
- 8 equipos reales de la Liga BetPlay Colombia con sus plantillas de jugadores reales
- Round-robin completo de 7 jornadas (cada equipo juega contra los otros 7)
- Tabla de posiciones con PJ/G/E/P/GF/GC/DG/PTS, actualizada jornada a jornada
- Fixture generado por algoritmo de rotación estándar

#### Equipos y jugadores
- **8 equipos reales:** Atlético Nacional, Millonarios FC, América de Cali, Junior FC, Deportivo Cali, Independiente Santa Fe, Deportes Tolima, Once Caldas
- **Plantillas reales** hardcodeadas en `PLANTILLAS_REALES`: Kevin Mier, Falcao, Bacca, Teófilo Gutiérrez, Anderson Plata, Hugo Rodallega, etc.
- **Ratings balanceados para el fútbol colombiano:** tope ~73-75 OVR (antes llegaban a 85+)
  - Fórmula: `base = int(40 + estrellas * 5)`, `hi = min(base + 20, 76)`
  - Nacional/Millonarios (4.0⭐): rango 60-76 → OVR promedio ~68-72
  - Once Caldas (2.5⭐): rango 52-72 → OVR promedio ~62
- **5 atributos por jugador:** ATAQUE, DEFENSA, FÍSICO, TÉCNICA, MENTAL
- **Rasgos opcionales** (30% de probabilidad): regateador (+15% ATK), rústico (+20% DEF), líder (+8% DEF), pulmón_de_hierro (+5% ATK)
- **Moral** (0-100, empieza en 70): afecta `poder_ataque_efectivo` y `poder_defensa_efectivo` via `(moral/70)`

#### Motor de simulación de partido
- Simula 90 minutos. Probabilidad de evento de ataque por minuto: `PROB_ATAQUE = 0.13`
- La posesión se calcula como promedio de (TÉCNICA + MENTAL)/2 del equipo
- **Resolución de choque:**
  ```
  poder = ataque_efectivo * bono_estilo
  diff = poder - defensa_efectiva + gauss(0, 12)
  si diff > 38 → GOL
  si diff > 15 → TIRO (fallido)
  sino         → DEFENSA
  ```
- Resultado esperado: 2-4 goles por partido (realista para fútbol)
- Narrativa minuto a minuto: velocidad 1 segundo/minuto, con `time.sleep(1.0)`
- Cada 10 minutos sin evento imprime un mensaje "tranquilo" (no spam)
- Narrativa activable/desactivable por partido

#### Estilos tácticos — piedra-papel-tijera
- **haramball** vence a cruyffismo (+15% poder de ataque)
- **cruyffismo** vence a flickismo (+15%)
- **flickismo** vence a haramball (+15%)
- El derrotado baja a ×0.87 en su poder de ataque

#### Decisión de medio tiempo
- Se pausa a los 45 minutos (en narrativa Y en modo rápido)
- Muestra el marcador parcial y permite elegir:
  1. Cerrar el partido → DEF +20%, ATK -10%
  2. Buscar el gol → ATK +25%, DEF -15%
  3. Cambiar estilo → gira la rueda táctica aleatoriamente
  4. Mantener el esquema → sin cambios
- Los multiplicadores se aplican solo en la segunda mitad

#### Copa Libertadores
- Se activa cuando el usuario termina en el TOP 2 de la liga
- **Bracket completo:**
  - Fase de grupos: tu equipo + otro colombiano (el 2° clasificado) + 2 rivales sorteados del pool (Nacional URU, Boca, Palmeiras, Ind. del Valle)
  - Los otros 2 del pool van a Octavos y Cuartos
  - Semifinal: River Plate o Flamengo (sorteado)
  - Final: el que no salió en semis (siempre River vs Flamengo para la final si llegas)
- Cada partido tiene decisión de MT
- Empates en eliminatorias van a penales (probabilidad basada en moral del equipo)
- **Ratings internacionales mucho más altos:**
  - Ind. del Valle: nivel 2.5 → rango 73-87 OVR
  - Nacional URU: nivel 2.8 → rango 75-89 OVR
  - Boca/Palmeiras: nivel 4.2 → rango 83-95 OVR
  - River/Flamengo: nivel 5.0 → rango 88-95 OVR
- Hay una brecha real de dificultad entre liga colombiana y Libertadores

#### Mercado de pases
- Se abre antes de la Copa Libertadores (si clasificas)
- También disponible en pre-temporada (temporada 2+)
- **Oferta entrante:** un club rival hace oferta aleatoria por tu estrella (×1.05-1.35 del precio base)
- **Mercado de compras:** muestra top 15 jugadores disponibles de otros equipos, ordenados por OVR, con precio visible e indicador "SIN FONDOS"
- Hasta 3 fichajes por ventana
- El jugador se mueve realmente de plantilla a plantilla
- Fórmula de precio: `(ovr - 45)² × 3500`
  - OVR 70 = $1.875M, OVR 75 = $2.8M, OVR 65 = $1.2M
- Si compras a alguien y ya tienes 2 en su posición, el de menor OVR vuelve al club de origen

#### Eventos caóticos
- 25% de probabilidad tras cada jornada
- 5 eventos posibles:
  1. Escándalo (jugador de fiesta) → multar o perdonar (afecta moral)
  2. Oferta árabe por tu estrella → aceptar (plata) o rechazar
  3. Pelea en camerino → mediar (60% de éxito) o castigar
  4. Lesión → jugador fuera 3 partidos
  5. Hincha en cancha → solo flavor text, sin consecuencias

#### Persistencia entre temporadas ✅ (implementado en v0.3)
- **El mismo `Equipo` objeto persiste** — mismos jugadores, mismo balance, mismo historial de fichajes
- Pre-temporada automática al inicio de cada temporada:
  - Lesiones se resetean a 0 (recuperación)
  - Moral sube +10 a todos (vacaciones)
  - Equipos rivales se auto-rellenan si quedaron con menos de 11 jugadores
- **Premio de liga** al final de cada temporada: 1°=$500K, 2°=$350K, 3°=$200K, resto=$100K
- **Balance acumulado** entre temporadas
- **Historial de carrera** visible al inicio de cada temporada: columnas Temporada / Posición / Pts / GF / GC / Campeón de Liga / Copa Libertadores
- Menú de pre-temporada (T2+): ir al mercado, cambiar estilo, ver plantilla, o arrancar directamente
- Al salir, muestra resumen completo de toda la carrera del DT

#### Clasificación a Libertadores en tabla
- Las 2 primeras posiciones aparecen con badge "LIBERTADORES" en la tabla de posiciones desde jornada 1

---

## Arquitectura del Código

### Dataclasses principales
```python
@dataclass class Jugador:
    nombre, apellido, posicion
    ataque, defensa, fisico, tecnica, mental  # ints 40-76 (colombianos)
    moral: int = 70
    rasgo: Optional[str] = None
    lesion_partidos: int = 0
    # props: overall, nombre_completo
    # methods: poder_ataque_efectivo(mult), poder_defensa_efectivo(mult)

@dataclass class Equipo:
    nombre, ciudad, estrellas, estilo_dt, balance
    jugadores: list[Jugador]
    # props: once_disponible
    # methods: promedio_ataque/defensa/tecnica_mental, jugador_estrella, ovr_promedio, tick_lesiones

@dataclass class Resultado:
    equipo_local, equipo_visitante, goles_local, goles_visitante

@dataclass class Standing:
    equipo, pj, g, e, p, gf, gc, pts
    # prop: dg (diferencia de goles)
```

### Flujo de datos en simulación de partido
```
simular_partido(local, visitante, narrativa, velocidad, decision_mt)
  └─ loop de minutos 1-90, dividido en 2 mitades
       └─ _procesar_minuto(minuto, local, visitante, jl, jv, gl, gv, narrativa, atk_l, def_l, atk_v, def_v)
            └─ resolver_choque(atk_efectivo, def_efectiva, estilo_atk, estilo_def)
                 └─ bono_estilo(ea, ed) → 1.15 / 0.87 / 1.0
```

### Funciones clave
| Función | Responsabilidad |
|---|---|
| `generar_equipo_real(nombre, ciudad, estrellas)` | Crea equipo con nombres reales de `PLANTILLAS_REALES`, atributos generados por rango |
| `generar_rival_int(nombre, ciudad, nivel)` | Crea equipo internacional con `rango_int` (stats más altos) |
| `calcular_precio(jugador)` | `(ovr-45)² × 3500` |
| `mercado_de_pases(mi_equipo, liga)` | Ventana de transferencias interactiva |
| `copa_libertadores(mi_equipo, otro_col, narrativa)` | Bracket completo, retorna string con resultado |
| `_partido_copa(mi_equipo, rival, fase, narrativa)` | Partido individual de copa (con MT y penales) |
| `_pretemporada(equipos, mi_equipo)` | Reset lesiones/moral, rellena rivales |
| `main()` | Flujo completo con `while True` persistente |

---

## Constantes Importantes

```python
PROB_ATAQUE   = 0.13     # prob de ataque por equipo por minuto
UMBRAL_GOL    = 38       # diff > 38 → gol
UMBRAL_TIRO   = 15       # diff > 15 → tiro fallido
CUPOS_LIBERTADORES = 2   # top 2 clasifican

# Fórmulas de rango de atributos
rango_co(estrellas)  → base = int(40 + estrellas*5), hi = min(base+20, 76)
rango_int(nivel)     → base = int(60 + nivel*6),     hi = min(base+20, 95)

# Pool Libertadores
POOL_GRUPOS = [Nacional(2.8), Boca(4.2), Palmeiras(4.2), Ind.Valle(2.5)]
SEMIS_FIJOS = [River(5.0), Flamengo(5.0)]
```

---

## Pendientes / Roadmap

### 🔴 Bugs conocidos / cosas incompletas

1. **Modo rápido sin narrativa también hace decision_medio_tiempo** — está bien implementado pero el UX es raro: el usuario pide "sin narrativa" y de repente aparece la pantalla de MT. Habría que avisarle antes: "Aunque no haya narrativa, igual tomas decisiones en el descanso." O hacerlo opcional.

2. **Los equipos rivales no compran jugadores entre sí** — el mercado solo opera para el usuario. Los rivales nunca se refuerzan activamente (solo se les rellenan los huecos con jugadores generados). Esto hace que el nivel de la liga se degrade lentamente conforme el usuario compra a sus mejores jugadores.

3. **Penales muy 50/50** — la probabilidad base es 50% ± diferencia de moral × 0.3%. Con morales similares es casi una moneda al aire. Podría mejorar con más factores (OVR del portero, rasgos, etc.).

4. **`_nombres_usados` no se limpia entre temporadas** — En v0.3 se eliminó el `_nombres_usados.clear()` para preservar jugadores. Pero si se juegan muchas temporadas y se generan muchos suplentes/rivales internacionales, el pool de nombres generados puede agotarse y empezar a repetir. Impacto bajo pero existe.

5. **El "otro colombiano" en Libertadores puede ser el equipo del usuario** si hay un bug de empate en puntos — raro pero posible. Habría que añadir `if otro != mi_equipo`.

6. **No hay desempate por head-to-head** en la tabla de posiciones — se usa solo PTS → DG → GF. En el fútbol real se desempata por el enfrentamiento directo primero.

---

### 🟡 Mejoras de gameplay pendientes (prioridad media)

7. **Desarrollo de jugadores entre temporadas** — Los jugadores no mejoran ni empeoran con el tiempo. Un delantero joven de OVR 62 debería ir creciendo. Propuesta simple: al final de cada temporada, los jugadores menores de cierto umbral tienen 40% de probabilidad de subir 1-2 puntos en su atributo principal.

8. **Edad/retiro de jugadores** — No existe concepto de edad. Sería bueno que jugadores "veteranos" como Falcao o Bacca se retiren eventualmente y haya que reemplazarlos.

9. **Rivalidades entre clubes** — Nacional vs Millonarios, América vs Cali — deberían tener un multiplicador de intensidad en el partido (moral extra, más eventos).

10. **Sistema de descenso/ascenso** — Actualmente todos los 8 equipos permanecen en la liga para siempre. Un equipo que termine último podría descender y ser reemplazado por uno generado nuevo.

11. **Más eventos caóticos** — Solo hay 5. El catálogo debería tener al menos 10-12 para evitar la repetición:
    - Lluvia torrencial en el partido (FÍSICO +20% ambos equipos ese partido)
    - Directiva mete la mano (te imponen un fichaje malo)
    - Jugador pide salir (si no lo vendes en 2 jornadas, su moral baja a 20)
    - Árbitro escandaloso (se anulan 2 goles al azar en la narrativa)
    - Hincha famoso en el palco (moral de todo el equipo +5)
    - Periodista te ataca (moral DT, flavor text)

12. **Clasificación a Copa Colombia / Sudamericana** — Actualmente solo existe Libertadores. Los puestos 3-5 podrían clasificar a la Sudamericana (bracket más corto, rivales de nivel medio).

13. **Estadísticas individuales de jugadores** — Goles anotados, asistencias, tarjetas amarillas/rojas acumuladas por temporada. Permitiría mostrar un "pichichi" al final de temporada y enriquecer el mercado.

14. **Jugadores con nombre + stats reales de famosos** — Actualmente los stats de los jugadores reales son generados aleatoriamente dentro del rango del club. Falcao podría tener stats hardcodeados más altos que el resto en Millonarios.

---

### 🟢 Mejoras de UX/presentación pendientes (prioridad baja)

15. **Guardar/cargar partida** — El único "NO" del spec original. Pero si el juego engancha, los usuarios van a querer guardar su carrera. Implementación sugerida: serializar `mi_equipo`, `equipos`, `historial`, `temporada` a JSON con `json.dump` usando `dataclasses.asdict`.

16. **Pantalla de "Club" mejorada** — Mostrar no solo la plantilla sino también el balance, estilo, estrellas, historial del club en la sesión actual.

17. **Animación de gol más dramática** — Actualmente es texto plano verde. Con colorama se podría hacer una animación de 3-4 líneas que simule el marcador electrónico del estadio.

18. **Velocidad ajustable de narrativa** — Actualmente hardcodeado a 1s/minuto. Podría exponerse como opción al inicio: "¿Velocidad de partido? [1] Lenta (1s) [2] Normal (0.5s) [3] Rápida (0.1s)".

19. **Logo ASCII mejorado** — El actual es funcional pero básico. Se puede hacer uno más elaborado con bordes dobles y colores.

20. **Sonido (beep)** — En Windows se puede hacer `import winsound; winsound.Beep(880, 200)` en los goles. Crossplatform con `os.system('echo \a')`. Flavor pequeño pero impactante.

---

### 🔵 Pendientes de arquitectura (si el proyecto escala)

21. **Separar en módulos** — Cuando el archivo supere ~2000 líneas, separar en:
    - `models.py` — Jugador, Equipo, Resultado, Standing
    - `engine.py` — simulación de partido
    - `display.py` — toda la presentación
    - `events.py` — eventos caóticos
    - `market.py` — mercado de pases
    - `copa.py` — Copa Libertadores
    - `main.py` — orquestación

22. **Tests unitarios para el motor** — `resolver_choque` y `_procesar_minuto` son deterministas si se fija la semilla. Con `random.seed(42)` se pueden escribir tests que validen que el número promedio de goles está en rango.

23. **Config file** — `config.json` para exponer `PROB_ATAQUE`, `UMBRAL_GOL`, velocidad de narrativa, etc. sin tocar el código.

---

## Decisiones de Diseño Tomadas (y por qué)

| Decisión | Razón |
|---|---|
| Solo 8 equipos (no 20) | Prototipo de una tarde — fixture de 7 jornadas es jugable en ~1h |
| Sin save/load | Scope del prototipo. La persistencia entre sesiones no es el objetivo ahora |
| OVR máx 76 para colombianos | Realismo — es raro ver un jugador con 80+ en la liga colombiana |
| Narrativa 1s/minuto | El usuario pidió explícitamente esto. Es lento pero dramático |
| Mercado de pases solo en eventos específicos | Evita que el usuario refuerce sin límite — la ventana pre-Libertadores es el incentivo de clasificar |
| Penales en empates de copa | Más drama que alargar 30 minutos extra que serían aburridos |
| Historial de carrera | El usuario pidió persistencia — el historial hace que cada temporada importe |

---

## Sesiones Anteriores — Bitácora

### Sesión 1 — Creación del prototipo base (v0.1)
- Creó el archivo desde cero en `C:\Users\diego\alpha_football.py`
- Equipos ficticios colombianos (Verdolaga FC, Tiburones del Caribe, etc.)
- Motor de simulación básico con narrativa
- 5 eventos caóticos
- Tabla de posiciones
- **Problema:** logo ASCII deteriorado, velocidad de narrativa muy rápida (0.05s), demasiados goles

### Sesión 2 — Mejoras principales (v0.2)
- Logo ASCII limpio con box
- Velocidad 1s/minuto
- Decisión de medio tiempo
- Algoritmo de goles balanceado (PROB_ATAQUE=0.13, UMBRAL_GOL=38)
- Clasificación a Libertadores (solo visual/cosmético en v0.2)
- Movido a `C:\Users\diego\Downloads\AlphaFootball 0.01\`
- **Descubrimiento:** la Libertadores era cosmética — el usuario preguntó "¿contra quién jugamos?" y se detectó que no había implementación real

### Sesión 3 — Libertadores real + mercado + nombres reales (v0.3)
- Copa Libertadores con bracket completo (grupos → octavos → cuartos → semis → final)
- Mercado de pases funcional (compra/venta real entre equipos)
- Plantillas reales por equipo (Kevin Mier, Falcao, Bacca, etc.)
- Ratings balanceados para fútbol colombiano (tope 76 OVR)
- Equipos reales Liga BetPlay
- Persistencia entre temporadas con `while True` en main()
- Historial de carrera
- Pre-temporada con menú de opciones
- Premio de liga al final de cada temporada

---

## Notas para la Próxima Sesión

- El archivo tiene **1419 líneas** — cualquier cambio grande debería hacerse con `Edit` (reemplazo parcial), NO con `Write` completo a menos que sea un refactor total
- El juego **corre bien en Windows** con Python 3.10+ — verificado con `python alpha_football.py` (sale en EOFError porque no hay stdin interactivo en el test, pero eso es normal)
- Si colorama no está instalado, el juego corre igual en texto plano — no hay que instalarlo obligatoriamente
- El **contexto más importante** para próximas sesiones es leer los pendientes del punto "Mejoras de gameplay" (#7 al #14) — ahí está el corazón de lo que falta para que el prototipo sea verdaderamente validable
- El siguiente feature más impactante sería probablemente **#13 (estadísticas individuales)** + **#14 (stats hardcodeados para estrellas reales)** porque hacen que los jugadores se sientan únicos, no intercambiables
- La pregunta que el prototipo debe responder: **¿Las mecánicas (atributos + rasgos + estilos + eventos caóticos + Libertadores) son divertidas en una tarde de juego?** Si sí → Godot. Si no → hay que iterar en el prototipo antes de invertir meses de desarrollo

---

## Fragmentos de Código Útiles para Referencia Rápida

### Agregar un nuevo evento caótico
```python
# En la función evento_caotico(), agregar elif evento == 6: (y aumentar random.randint(1, 6))
elif evento == 6:
    # tu evento aquí
    pass
```

### Agregar stats hardcodeados a un jugador famoso
```python
# En PLANTILLAS_REALES, los jugadores usan generar_jugador_pos() que es aleatorio.
# Para hardcodear stats, habría que modificar generar_equipo_real() para detectar nombres especiales:
STATS_ESPECIALES = {
    ("Radamel", "Falcao"): {"ataque": 74, "defensa": 35, "fisico": 72, "tecnica": 73, "mental": 70},
    ("Carlos", "Bacca"):   {"ataque": 71, "defensa": 32, "fisico": 68, "tecnica": 65, "mental": 67},
}
# Y en generar_equipo_real(), antes de hacer _attrs(), chequear si el nombre está en STATS_ESPECIALES
```

### Serializar para save/load (cuando se implemente)
```python
import json, dataclasses
def guardar_partida(mi_equipo, equipos, historial, temporada, dt_nombre, filepath):
    data = {
        "dt_nombre": dt_nombre,
        "temporada": temporada,
        "historial": historial,
        "mi_equipo_nombre": mi_equipo.nombre,
        "equipos": [dataclasses.asdict(e) for e in equipos],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

---

*Este archivo no se commitea (va en .gitignore si existe). No contiene secretos.*
