# Competiciones reales y Balón de Oro (sub-proyecto 6, v3.8.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Champions con fase de liga suiza de 36 (playoff, llaves ida/vuelta, final única) y Libertadores con 8 grupos de 4 + llaves, ambas simuladas cada temporada; pantalla de copa nueva; tabla LIGA/COPA en el hub; COPAS en OTRAS LIGAS; objetivo de copa y Balón de Oro con la fórmula nueva.

**Architecture:** Motor puro y serializable `alpha_football/competiciones.py` (estado en `datos_carrera['copas'][tipo]`); `ui/copa_screen.py` se reescribe como vista del motor y conserva los nombres de funciones que usan otros módulos (fachada), para que `match_screen`, `prepartido_screen`, `league_screen`, `resumen_temporada_screen`, `menu` y `directiva` migren sin romperse. Las claves viejas `estado['copa_*']` se eliminan (una por una, con grep).

**Tech Stack:** Python 3.10+, Pygame; tests con runner propio.

**Spec:** `docs/superpowers/specs/2026-09-23-competiciones-design.md` · **Depende de:** sub-proyecto 5 terminado (8 países, ligas de 12, `data/internacional.RELLENO_CHAMPIONS` / `RELLENO_LIBERTADORES`, `paises.py`).

## Global Constraints
- Comentarios `# v3.8.0: ...`; sin commits; suite completa en verde tras cada tarea.
- Cupos: Champions premier 5 · laliga 5 · seriea 5 + 21 relleno = 36; Libertadores brasil 7 · argentina 6 · betplay 5 · uruguay 5 · ecuador 5 + 4 relleno = 32.
- Fechas: Champions 17 (8 liga + 2 playoff + 2 octavos + 2 cuartos + 2 semis + 1 final); Libertadores 13 (6 + 2 + 2 + 2 + 1). Fecha i de N tras la jornada `ceil((i+1)·(J−1)/N)` con J = `num_jornadas` de la liga del user.
- Empates en llaves: global; si persiste, penales. Sin gol de visitante.
- Balón de Oro: goles×4 + asistencias×2 + max(0, nota−6)×10 + liga 15 + copa 20 + (POR) vallas×1.5, × peso (Europa 1.0; brasil, argentina 0.85; resto 0.75; 2ª 0.6); mínimo 50% de la liga jugada.

## Review Focus
- El user eliminado a mitad de copa → la copa sigue simulándose en segundo plano hasta el campeón, y JUGAR ya no ofrece partidos de copa. Test en Task 2 (`test_user_eliminado_sigue_copa`).
- Save viejo con `estado['copa_bracket']` a mitad de temporada → al cargar se regenera con el motor nuevo sin excepción y las fechas pasadas quedan jugadas. Test en Task 3 (`test_save_viejo_regenera_copa`).
- User clasificado cuya liga tiene 10 jornadas (save viejo) → el mapeo de fechas usa esas 10 y la final cae antes del final de liga. Test en Task 1 (`test_fechas_monotonicas`).
- Sorteo imposible sin repetir país (p. ej. 7 brasileños en 8 grupos con otros 5 de otro país) → se relaja la regla, nunca cuelga. Test en Task 1 (`test_sorteo_nunca_cuelga`).
- Partido de copa del user jugado en vivo y luego "simular copa entera" → no se duplica ni se pisa su resultado. Test en Task 2 (`test_resultado_user_no_se_pisa`).

## Reparto
Subagente Motor: Tasks 1-2. Subagente Integración: Tasks 3-4 (después del Motor).

---

### Task 1: Motor — sorteos, fechas, tablas y llaves
**Files:** Create `alpha_football/competiciones.py`. Test: `tests/test_competiciones_v380.py` (cabecera como `test_directiva_v280.py`).
**Produces:**
```python
FASES = {'champions': ['Fase de liga', 'Playoff', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón'],
         'libertadores': ['Fase de grupos', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']}
N_FECHAS = {'champions': 17, 'libertadores': 13}
def jornada_de_fecha(i: int, n_fechas: int, num_jornadas: int) -> int
def sorteo_fase_liga(clubes: list[dict], rng) -> list[dict]      # clubes: {'nombre','ovr','pais'}; devuelve 144 partidos {'fecha','local','visitante'}
def sorteo_grupos(clubes: list[dict], rng) -> list[list[str]]    # 8 grupos de 4 nombres
def partidos_grupos(grupos) -> list[dict]                        # 96 partidos, fechas 0..5
def tabla(nombres: list[str], partidos: list[dict]) -> list[dict] # [{'nombre','pj','g','e','p','gf','gc','pts'}] ordenada
def resolver_llave(ida: dict, vuelta: dict | None, rng, fuerza: dict) -> str   # ganador (penales si hace falta; guarda 'penales' en el partido decisivo)
def cruces_playoff(tabla36) -> list[tuple[str, str]]             # (mejor, peor): 9v24 ... 16v17
def cruces_octavos_champions(tabla36, ganadores_playoff: dict) -> list[tuple[str, str]]
def cruces_octavos_libertadores(grupos_tablas: list[list[dict]]) -> list[tuple[str, str]]
```
- [ ] **Tests:**
```python
import random, math
from alpha_football import competiciones as CP

def _clubes(n, paises):
    return [{'nombre': f"C{i}", 'ovr': 90 - i // 2, 'pais': paises[i % len(paises)]} for i in range(n)]

def test_fechas_monotonicas():
    for n in (17, 13):
        for J in (22, 10):
            js = [CP.jornada_de_fecha(i, n, J) for i in range(n)]
            assert js == sorted(js) and js[0] >= 1 and js[-1] == J - 1, (n, J, js)

def test_sorteo_fase_liga():
    for seed in range(10):
        cl = _clubes(36, ['ING', 'ESP', 'ITA', 'ALE', 'FRA', 'POR', 'NED', 'BEL'])
        ps = CP.sorteo_fase_liga(cl, random.Random(seed))
        assert len(ps) == 144 and sorted({p['fecha'] for p in ps}) == list(range(8))
        bombo = {c['nombre']: i // 9 for i, c in enumerate(sorted(cl, key=lambda c: -c['ovr']))}
        pais = {c['nombre']: c['pais'] for c in cl}
        for c in cl:
            n = c['nombre']
            mios = [p for p in ps if n in (p['local'], p['visitante'])]
            assert len(mios) == 8 and sum(p['local'] == n for p in mios) == 4
            rivales = [p['visitante'] if p['local'] == n else p['local'] for p in mios]
            assert len(set(rivales)) == 8
            assert sorted(bombo[r] for r in rivales) == [0, 0, 1, 1, 2, 2, 3, 3]
            assert all(pais[r] != pais[n] for r in rivales)
            assert sorted(p['fecha'] for p in mios) == list(range(8))        # uno por fecha

def test_sorteo_grupos():
    cl = _clubes(32, ['BRA'] * 7 + ['ARG'] * 6 + ['COL'] * 5 + ['URU'] * 5 + ['ECU'] * 5 + ['CHI', 'PAR', 'PER', 'BOL'])
    g = CP.sorteo_grupos(cl, random.Random(3))
    assert len(g) == 8 and all(len(x) == 4 for x in g)
    assert sorted(n for x in g for n in x) == sorted(c['nombre'] for c in cl)
    ps = CP.partidos_grupos(g)
    assert len(ps) == 96 and sorted({p['fecha'] for p in ps}) == list(range(6))

def test_sorteo_nunca_cuelga():
    cl = _clubes(32, ['BRA'])                          # todos del mismo país: debe relajar la regla
    assert len(CP.sorteo_grupos(cl, random.Random(1))) == 8
    assert len(CP.sorteo_fase_liga(_clubes(36, ['ING']), random.Random(1))) == 144

def test_tabla_y_cruces():
    nombres = [f"C{i}" for i in range(36)]
    ps = [{'local': nombres[i], 'visitante': nombres[35 - i], 'gl': 2, 'gv': 0, 'jugado': True} for i in range(18)]
    t = CP.tabla(nombres, ps)
    assert t[0]['pts'] == 3 and t[-1]['pts'] == 0 and len(t) == 36
    orden = [f"T{i}" for i in range(36)]
    tab = [{'nombre': n} for n in orden]
    assert CP.cruces_playoff(tab)[0] == ('T8', 'T23') and CP.cruces_playoff(tab)[-1] == ('T15', 'T16')
    gan = {('T8', 'T23'): 'T8'}
    octv = CP.cruces_octavos_champions(tab, {p: p[0] for p in CP.cruces_playoff(tab)})
    assert len(octv) == 8 and octv[0][0] == 'T0' and octv[0][1] == 'T15'

def test_llave_global_y_penales():
    ida = {'local': 'A', 'visitante': 'B', 'gl': 1, 'gv': 0, 'jugado': True}
    vuelta = {'local': 'B', 'visitante': 'A', 'gl': 1, 'gv': 0, 'jugado': True}
    g = CP.resolver_llave(ida, vuelta, random.Random(1), {'A': 80, 'B': 80})
    assert g in ('A', 'B') and 'penales' in vuelta
    vuelta2 = {'local': 'B', 'visitante': 'A', 'gl': 0, 'gv': 0, 'jugado': True}
    assert CP.resolver_llave(ida, vuelta2, random.Random(1), {}) == 'A'
    final = {'local': 'A', 'visitante': 'B', 'gl': 2, 'gv': 2, 'jugado': True}
    assert CP.resolver_llave(final, None, random.Random(2), {}) in ('A', 'B') and 'penales' in final
```
(`test_tabla_y_cruces`: `cruces_playoff` recibe la tabla ordenada; el test usa nombres `T0..T35` como posiciones 1-36, así 9º = `T8`, 24º = `T23`. Octavos: 1º vs ganador del cruce 16-17 → `('T0', 'T15')` cuando el mejor gana.)
- [ ] **Implementación (núcleo):**
```python
def jornada_de_fecha(i, n_fechas, num_jornadas):
    """v3.8.0: fecha i (0-based) tras la jornada ceil((i+1)(J-1)/N); la final queda tras la J-1."""
    return max(1, math.ceil((i + 1) * (num_jornadas - 1) / n_fechas))


def _bombos(clubes, n_bombos):
    orden = sorted(clubes, key=lambda c: -c['ovr'])
    t = len(orden) // n_bombos
    return [orden[k * t:(k + 1) * t] for k in range(n_bombos)]


def _emparejar_fase_liga(bombos, rng, mismo_pais_ok):
    """Aristas dirigidas (local, visitante): por cada par de bombos (i<=j) un 'desplazamiento' aleatorio."""
    partidos = []
    perms = [rng.sample(b, len(b)) for b in bombos]
    for i in range(4):
        for j in range(i, 4):
            if i == j:
                s = rng.randrange(1, 9)
                while s in (0,) or (2 * s) % 9 == 0:
                    s = rng.randrange(1, 9)
                for a in range(9):
                    partidos.append((perms[i][a], perms[i][(a + s) % 9]))   # cada uno 1 L y 1 V dentro del bombo
            else:
                s1, s2 = rng.sample(range(9), 2)
                for a in range(9):
                    partidos.append((perms[i][a], perms[j][(a + s1) % 9]))
                    partidos.append((perms[j][(a + s2) % 9], perms[i][a]))
    if not mismo_pais_ok and any(l['pais'] == v['pais'] for l, v in partidos):
        return None
    if len({frozenset((l['nombre'], v['nombre'])) for l, v in partidos}) != len(partidos):
        return None                                  # un mismo cruce dos veces
    return partidos


def _repartir_fechas(partidos, n_fechas, rng, intentos=400):
    """Cada club juega una vez por fecha: extrae emparejamientos perfectos sucesivos (backtracking)."""
    nombres = sorted({x for p in partidos for x in p})
    for _ in range(intentos):
        restantes = list(partidos); fechas = []
        ok = True
        for f in range(n_fechas):
            m = _matching_perfecto(nombres, restantes, rng)
            if m is None:
                ok = False; break
            fechas.append(m)
            restantes = [p for p in restantes if p not in m]
        if ok:
            return [{'fecha': f, 'local': l, 'visitante': v} for f, m in enumerate(fechas) for l, v in m]
    return None


def _matching_perfecto(nombres, aristas, rng, limite=20000):
    ady = {n: [] for n in nombres}
    for a in aristas:
        ady[a[0]].append(a); ady[a[1]].append(a)
    for n in ady:
        rng.shuffle(ady[n])
    usados, elegido, pasos = set(), [], [0]

    def bt():
        pasos[0] += 1
        if pasos[0] > limite:
            return False
        libres = [n for n in nombres if n not in usados]
        if not libres:
            return True
        n = min(libres, key=lambda x: sum(1 for a in ady[x] if a[0] not in usados and a[1] not in usados))
        for a in ady[n]:
            if a[0] in usados or a[1] in usados:
                continue
            usados.update(a); elegido.append(a)
            if bt():
                return True
            usados.difference_update(a); elegido.pop()
        return False
    return list(elegido) if bt() else None


def sorteo_fase_liga(clubes, rng):
    bombos = _bombos(clubes, 4)
    for relajar in (False, True):
        for _ in range(300):
            aristas = _emparejar_fase_liga(bombos, rng, mismo_pais_ok=relajar)
            if aristas is None:
                continue
            pares = [(l['nombre'], v['nombre']) for l, v in aristas]
            fechas = _repartir_fechas(pares, 8, rng, intentos=20)
            if fechas:
                return fechas
    raise RuntimeError("sorteo_fase_liga: no se pudo sortear")
```
(Si en la práctica `_repartir_fechas` falla seguido, cambiar a Misra-Gries/Kempe para colorear aristas con Δ=8 colores; el test con 10 semillas lo detecta. `sorteo_grupos`: bombos de 8, 1 por bombo en cada grupo, asignación aleatoria con reintentos que evita repetir país; si 500 intentos fallan, sin la regla. `partidos_grupos` reutiliza `ui.league_screen.generar_fixture` (4 equipos → 6 fechas). `tabla`: 3/1/0, orden pts, dif, gf, nombre. `resolver_llave`: global = goles de A en ambos; si empate → `penales(fuerza_a, fuerza_b, rng)` (5 + muerte súbita, prob. de gol 0.75 ± (fuerza−75)/200) y guarda `{'a': x, 'b': y}` en el partido decisivo.)
- [ ] Verde + suite.

### Task 2: Temporada de copa — clasificados, avance por jornada, API del user
**Files:** Modify `alpha_football/competiciones.py`. Test: `tests/test_competiciones_v380.py`.
**Produces:**
```python
def clasificados(estado, tipo) -> list[dict]          # 36 / 32 {'nombre','ovr','pais','liga'} (cupos + relleno)
def iniciar_temporada(estado, rng=None) -> None       # crea datos_carrera['copas'] para las 2 copas de la temporada
def copa(estado, tipo) -> dict | None
def tipo_copa_user(estado) -> str | None              # 'champions'/'libertadores' si el user clasificó
def avanzar(estado, rng=None) -> None                 # tras cada jornada de liga del user: juega todas las fechas vencidas (salvo el partido del user)
def partido_pendiente_user(estado) -> dict | None     # el partido del user de la próxima fecha vencida
def registrar_resultado_user(estado, partido_id, gl, gv, penales=None) -> None
def fase_user(estado) -> str                          # etiqueta de FASES (mejor fase alcanzada)
def linea_estado_user(estado) -> str                  # "Champions · Octavos (ida) vs X" / "eliminado en Cuartos" / "campeón"
def simular_todo(estado, rng=None) -> None            # termina ambas copas (fin de temporada)
def campeon(estado, tipo) -> str | None
def equipo_por_nombre(estado, nombre)                 # Equipo de las 16 ligas o del pool internacional
```
Estado por copa: `{'tipo','temporada','clubes': [...], 'fechas_jornada': [int]*N, 'partidos': [...], 'grupos'?, 'llaves': [{'fase','a','b','ida','vuelta','ganador'}], 'fase_actual', 'campeon', 'mejor_fase': {nombre: fase}}`; `partidos[i]['id']` único (`f"{tipo}-{fecha}-{k}"`).
- [ ] **Tests:**
```python
def _estado_con_copas():
    e = estado_carrera()
    CP.iniciar_temporada(e, random.Random(5))
    return e

def test_clasificados_cupos():
    e = estado_carrera()
    ch, li = CP.clasificados(e, 'champions'), CP.clasificados(e, 'libertadores')
    assert len(ch) == 36 and len(li) == 32
    assert len({c['nombre'] for c in ch + li}) == 68
    from collections import Counter
    cnt = Counter(c['liga'] for c in ch)
    assert cnt['premier'] == cnt['laliga'] == cnt['seriea'] == 5
    cnt2 = Counter(c['liga'] for c in li)
    assert (cnt2['brasil'], cnt2['argentina'], cnt2['betplay'], cnt2['uruguay'], cnt2['ecuador']) == (7, 6, 5, 5, 5)

def test_temporada_completa_ambas_copas():
    e = _estado_con_copas(); liga = e['liga']
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        pend = CP.partido_pendiente_user(e)
        while pend:
            CP.registrar_resultado_user(e, pend['id'], 1, 0)
            pend = CP.partido_pendiente_user(e)
        CP.avanzar(e, random.Random(j))
    CP.simular_todo(e, random.Random(99))
    for t in ('champions', 'libertadores'):
        c = CP.copa(e, t)
        assert c['campeon'] and all(p['jugado'] for p in c['partidos']), t
        assert len([p for p in c['partidos'] if p.get('fase') == 'Final']) == 1

def test_user_eliminado_sigue_copa():
    e = _estado_con_copas(); t = CP.tipo_copa_user(e)
    if t is None: return
    c = CP.copa(e, t); mi = e['mi_equipo'].nombre
    liga = e['liga']
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        pend = CP.partido_pendiente_user(e)
        while pend:
            CP.registrar_resultado_user(e, pend['id'], 0, 5 if pend['local'] == mi else 0) if pend['local'] == mi \
                else CP.registrar_resultado_user(e, pend['id'], 5, 0)
            pend = CP.partido_pendiente_user(e)
        CP.avanzar(e, random.Random(j))
    assert CP.partido_pendiente_user(e) is None and CP.copa(e, t)['campeon'] != mi

def test_resultado_user_no_se_pisa():
    e = _estado_con_copas(); t = CP.tipo_copa_user(e)
    if t is None: return
    e['liga'].jornada_actual = e['liga'].num_jornadas
    p = CP.partido_pendiente_user(e)
    CP.registrar_resultado_user(e, p['id'], 3, 3)
    CP.simular_todo(e, random.Random(1))
    q = next(x for x in CP.copa(e, t)['partidos'] if x['id'] == p['id'])
    assert (q['gl'], q['gv']) == (3, 3)

def test_linea_estado_y_fase():
    e = _estado_con_copas()
    assert isinstance(CP.linea_estado_user(e), str)
    if CP.tipo_copa_user(e): assert CP.fase_user(e) in CP.FASES[CP.tipo_copa_user(e)]
```
(En `estado_carrera` forzar que el user clasifique: tomar la liga premier y el club de mayor media; T1 = top por media. Si no clasifica, los tests que dependen del user retornan temprano; añadir un test que fuerce `tipo_copa_user(e) == 'champions'` con el club más fuerte de la premier.)
- [ ] **Reglas de `avanzar`:** para cada copa, cada fecha `i` con `fechas_jornada[i] <= liga_user.jornada_actual - 1`... usar exactamente: la fecha i está **vencida** cuando `liga.jornada_actual > fechas_jornada[i]` (se juega después de esa jornada). Se simulan los partidos no jugados de fechas vencidas salvo el del user, que queda pendiente para JUGAR; la siguiente fase se sortea/arma cuando la anterior está completa (incluido el partido del user). Si el user tiene un partido pendiente de una fecha vencida, las fases siguientes esperan. `simular_todo` juega todo lo que quede (incluido el del user si nunca lo jugó).
- [ ] Simulación de partidos IA: usar la misma función del motor que `simular_otros_partidos` (buscar en `engine.py`/`match_screen.py`), con los `Equipo` resueltos por `equipo_por_nombre`; registrar goles/asistencias de copa en `datos_carrera['copas'][tipo]['stats']` (`{jugador: {'club','goles','asist'}}`).
- [ ] Verde + suite.

### Task 3: Integración — fachada en copa_screen, estado viejo fuera, objetivos, premios y Balón de Oro
**Files:** Modify `alpha_football/ui/copa_screen.py` (funciones públicas usadas por otros: `cupos_copa`, `sincronizar_copa_user`, `simular_copa_fondo`, `rival_copa_pendiente`, `preparar_partido_copa`, `linea_copa_user`, `guardar_ranking_copas`, `registrar_stats_copa`, `avanzar_fase_bracket`), `alpha_football/ui/league_screen.py`, `alpha_football/ui/match_screen.py`, `alpha_football/ui/prepartido_screen.py`, `alpha_football/ui/resumen_temporada_screen.py`, `alpha_football/ui/menu.py`, `alpha_football/directiva.py` (`FASES_COPA`, `meta_copa`, `definir_objetivo_copa`, `evaluar_objetivo_copa`), `alpha_football/premios.py`, tests viejos de copa (`tests/test_copa_integridad.py`, `test_hub_v240.py`, `test_ui_v235.py`, `test_v236.py`). Test: `tests/test_competiciones_v380.py`.
- [ ] **Paso 1 — inventario:** `grep -rn "copa_" alpha_football main.py --include=*.py | grep "estado\["` y `grep -rn "from alpha_football.ui.copa_screen import" alpha_football main.py tests`. Anotar cada uso en el informe; cada uno pasa a usar `competiciones`. Claves que quedan (derivadas del motor, por compatibilidad de pantallas): `copa_user_en_copa`, `copa_clasificado`, `copa_clasificado_motivo`, `copa_mejor_fase_temp` (= `fase_user`), `copa_campeon`. El resto (`copa_bracket*`, `copa_grupos*`, `copa_fase_actual`, `copa_jornada_grupo`, `copa_grupo_partidos`, `copa_tipo`…) desaparece.
- [ ] **Paso 2 — tests:**
```python
def test_directiva_meta_copa_nueva():
    from alpha_football import directiva as D
    assert D.meta_copa(1, 36, ventaja=9) == 'Campeón'
    assert D.meta_copa(4, 36) == 'Finalista' and D.meta_copa(8, 36) == 'Semifinal'
    assert D.meta_copa(16, 36) == 'Cuartos' and D.meta_copa(30, 36) == 'Octavos'
    assert D.FASES_COPA[-1] == 'Campeón' and 'Octavos' in D.FASES_COPA

def test_balon_de_oro_formula():
    from alpha_football import premios as PR
    class J: pass
    j = J(); j.goles, j.asistencias, j.promedio_nota, j.posicion, j.porterias_cero, j.overall = 10, 5, 7.5, 'DEL', 0, 85
    assert PR.puntaje_jugador(j, 1.0, True, False) == 10 * 4 + 5 * 2 + 15 + 15
    assert PR.puntaje_jugador(j, 1.0, False, True) == 10 * 4 + 5 * 2 + 15 + 20

def test_save_viejo_regenera_copa():
    e = estado_carrera()
    e['copa_bracket'] = {'cuartos': [{'a': 'X', 'b': 'Y'}]}; e['copa_fase_actual'] = 'cuartos'
    e['liga'].jornada_actual = 8
    from alpha_football.ui.copa_screen import sincronizar_copa_user
    sincronizar_copa_user(e)
    assert 'copa_bracket' not in e and CP.copa(e, 'champions')
    c = CP.copa(e, 'champions')
    vencidas = [i for i, j in enumerate(c['fechas_jornada']) if e['liga'].jornada_actual > j]
    assert all(p['jugado'] for p in c['partidos'] if p['fecha'] in vencidas and e['mi_equipo'].nombre not in (p['local'], p['visitante']))

def test_jugar_lleva_a_copa_cuando_toca():
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    if not CP.tipo_copa_user(e): return
    e['liga'].jornada_actual = CP.copa(e, CP.tipo_copa_user(e))['fechas_jornada'][0] + 1
    from alpha_football.ui.copa_screen import rival_copa_pendiente
    assert rival_copa_pendiente(e)[0] is not None
```
- [ ] **Paso 3 — implementar:** `premios.puntaje_jugador` con la fórmula del spec (goles/asistencias de copa sumados desde `datos_carrera['copas'][t]['stats']` en `calcular_balon_de_oro`; `PESO_LIGA_1A` desde `paises`); `directiva.FASES_COPA = ['Fase de liga', 'Playoff', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']` con `evaluar_objetivo_copa` usando el orden de `competiciones.FASES[tipo]` (Fase de grupos ≡ Fase de liga); `meta_copa`: r = 1 y ventaja ≥ 8 → Campeón, r ≤ n/8 → Finalista, r ≤ n/4 → Semifinal, r ≤ n/2 → Cuartos, si no → Octavos. `definir_objetivo_copa` toma los clubes de `competiciones.copa(...)['clubes']`. Premios en dinero por fase: Champions liga 2M, playoff +1M, octavos +3M, cuartos +5M, semis +8M, final +12M, campeón +20M; Libertadores la mitad (registrar en `finanzas` clave `'premios'`). Hooks: `match_screen.finalizar_jornada_liga` → `competiciones.avanzar(estado)`; fin de temporada → `simular_todo` + `iniciar_temporada` de la siguiente (tras la clasificación por `copa_ranking`).
- [ ] Verde + suite (los tests viejos de copa se adaptan al motor nuevo: mismas intenciones, API nueva; anotar cada cambio).

### Task 4: UI — pantalla de copa, tabla LIGA/COPA en el hub, COPAS en OTRAS LIGAS
**Files:** Modify `alpha_football/ui/copa_screen.py` (render reescrito), `alpha_football/ui/league_screen.py` (panel de tabla con pestañas LIGA/COPA; línea "Copa: eliminado en X"), `alpha_football/ui/otras_ligas_screen.py` (pestaña COPAS). Test: `tests/test_competiciones_v380.py`.
**Produces:** en copa_screen `PESTANAS = ['liga_grupos', 'llaves', 'partidos', 'estadisticas']`, `rect_pestana(clave)`, `R_SELECTOR_COPA`; en league_screen `rect_tab_tabla('liga'|'copa')`, `estado['hub_tabla_tab']`; en otras_ligas `rect_tab_copas()`.
- [ ] **Tests:**
```python
def test_copa_screen_pestanas():
    from alpha_football.ui import copa_screen as S
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    for clave in S.PESTANAS:
        click(S.rect_pestana(clave).center); assert S.render(screen, e) is None
    click(S.R_SELECTOR_COPA.center); S.render(screen, e)

def test_hub_tabla_copa():
    from alpha_football.ui import league_screen as L
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5)); e['hub_tab'] = 'inicio'
    click(L.rect_tab_tabla('copa').center); L.render(screen, e)
    assert e['hub_tabla_tab'] == 'copa'

def test_otras_ligas_copas():
    from alpha_football.ui import otras_ligas_screen as O
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    click(O.rect_tab_copas().center); assert O.render(screen, e) is None
```
- [ ] Vistas: FASE DE LIGA = tabla de 36 en 2 columnas de 18 con franjas (verde 1-8, azul 9-24, gris 25-36) y tu club resaltado; GRUPOS = 8 mini-tablas 4×2; LLAVES = columnas playoff/octavos/cuartos/semis/final con "global X-Y" y "(pen. a-b)"; PARTIDOS = fecha seleccionable con ←/→; ESTADÍSTICAS = top 10 goleadores/asistidores de la copa. Selector CHAMPIONS/LIBERTADORES. Todo por debajo de y = 696.
- [ ] Capturas headless de cada pestaña (con una temporada simulada a medias) para revisar solapes. Verde + suite.
