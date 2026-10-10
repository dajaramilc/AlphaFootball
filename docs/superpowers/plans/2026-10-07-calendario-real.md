# Calendario real (v0.4.11.0, sub-proyecto C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Método elegido por Diego: NATIVO** → superpowers:executing-plans, en una sesión nueva con Sonnet 5.5. Sin commits: Diego da el OK final.

**Goal:** Cada partido del user tiene fecha real (Europa agosto–mayo, Sudamérica enero–diciembre), los choques se reprograman con aviso, la energía se recupera según los días de descanso y hay una pantalla CALENDARIO.

**Architecture:** Un módulo sin UI, `alpha_football/calendario.py`, calcula las fechas a partir de las ventanas de mercado (`market.ventanas_mercado`), así los cierres caen el 31 de agosto y el 31 de enero sin tocar la lógica por jornada. Las fechas base salen de una semilla y no se guardan; solo se guarda lo reprogramado en `datos_carrera['calendario']`. `energia.recuperar_todos` recibe los días de descanso y `match_screen.finalizar_jornada_liga` los reparte antes y después de la copa.

**Tech Stack:** Python 3.10 (`datetime`, `functools.lru_cache`), pygame. Tests = scripts ejecutables (`python tests/test_x.py`) con ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-06-calendario-mercado-actualizador-design.md` (sección C). Los sub-proyectos D, E y F tienen plan propio y van después.

## Global Constraints

- Versión: **0.4.11.0**. Comentarios nuevos: `# v0.4.11.0`. No reescribir comentarios `# v4.x` viejos.
- **Git: sin commits hasta que Diego lo pida.** Nunca atribuir a Claude ni a una IA en git.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor del cambio.
- Comentarios y textos del juego en español.
- Cada test corre con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` y termina en `N/N tests pasaron`. Hay tests que salen con código 0 aunque impriman `FAIL`: revisar siempre la salida.
- Temporada 1: **2026/27** en Europa (empieza en agosto de 2026) y **2027** en Sudamérica (empieza en enero de 2027). Cada temporada suma un año.
- Cierres de mercado: **31 de agosto** y **31 de enero**. Europa: inicio = agosto, invierno = enero. Sudamérica: inicio = enero, invierno = agosto.
- Liga: sábado 55%, domingo 40%, lunes 5%. Copa: martes 40%, miércoles 45%, jueves 15%. Mínimo **3 días** entre dos partidos del user.
- El orden de juego no cambia: la fecha `i` de copa se sigue jugando tras la jornada `fechas_jornada[i]`.
- `energia.recuperar_todos(estado)` sin días conserva la recuperación fija de hoy.
- No se toca nada de D (reloj del último día), E (auto-actualización) ni F (desfase entre continentes). `calendario.anio` ya lee `datos_carrera['mundo']['anio']` si existe, para que F lo use después.

### Desviaciones del spec decididas al planificar

1. **La tarjeta CALENDARIO va en DIRECCIÓN DE EQUIPO**, no en OFICINA: OFICINA ya tiene 8 tarjetas y su cuarta fila termina justo en la barra de atajos.
2. **La fecha va en el botón JUGAR** (arriba a la derecha) y en el pre-partido, no en la cabecera del hub: la cabecera no tiene lugar (`test_mercado_v440::test_franja_no_choca_y_render` ya mide el peor caso al límite).
3. **"Hoy" es el día de tu próximo partido** (el día en que estás parado antes de jugar); si no quedan partidos, el del último.

## Review Focus

1. **Liga sin ventana de invierno o muy corta** (2, 6, 14 jornadas) y **38 jornadas** → el calendario tiene exactamente `n` sábados crecientes, sin excepción (Task 1).
2. **Save viejo sin `datos_carrera['calendario']`**, o cambio de temporada, liga o club → el calendario se rearma solo y no arrastra lo reprogramado de antes (Task 1).
3. **Copa inexistente, fecha fuera de rango o user fuera de la copa** → `fecha_copa` devuelve `None` y la lista de partidos sale solo con la liga (Task 2).
4. **Choque sin solución** (ningún día libre cumple los 3 días) → no se mueve nada, no se manda correo y no entra en bucle (Task 3).
5. **Partido de copa del user pendiente tras la jornada** → el resto del descanso no se pierde: se aplica al cerrar ese partido, y si nunca se cierra, en la jornada siguiente (Task 4).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/calendario.py` (nuevo) | Sábados por jornada, cierres, fechas de liga y copa, partidos del user, reprogramación, descanso |
| `alpha_football/energia.py` | `recuperar(j, factor)` y `recuperar_todos(estado, dias)` |
| `alpha_football/ui/match_screen.py` | `finalizar_jornada_liga`: descanso antes y después de la copa, revisar choques; cierre del partido de copa en vivo |
| `alpha_football/ui/prepartido_screen.py` | cierre del partido de copa simulado; fecha en el pre-partido |
| `alpha_football/ui/league_screen.py` | fecha en el botón JUGAR, tarjeta CALENDARIO, primera revisión de choques |
| `alpha_football/ui/calendario_screen.py` (nuevo) | Pantalla del mes |
| `main.py`, `alpha_football/ui/atajos.py`, `alpha_football/ui/ayuda.py` | registro de la pantalla nueva |
| `tests/test_calendario.py` (nuevo) | tests de C |

Cabecera del archivo de test nuevo (copiar tal cual):

```python
"""v0.4.11.0: calendario real (fechas, copa, reprogramación, descanso) y pantalla CALENDARIO."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from datetime import date, timedelta
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
from alpha_football import calendario as CAL, correo as C, energia as E, competiciones as CP
from alpha_football.ui.league_screen import inicializar_calendario_liga


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _e(tipo='premier', idx=0):
    e = estado_carrera(tipo, idx)
    inicializar_calendario_liga(e['liga'])
    return e


def _jugar(e, jornada, gl=1, gv=0):
    """Marca como jugado el partido de liga del user de esa jornada (sin simular nada)."""
    mi = e['mi_equipo']
    p = next(p for p in e['liga'].calendario if p.jornada == jornada and mi.id in (p.local_id, p.visitante_id))
    p.jugado, p.goles_local, p.goles_visitante = True, gl, gv
    return p


def _con_copa(e, tipo='champions', fecha=0, local=True):
    """Copa mínima con un partido del user en la fecha dada. Devuelve fechas_jornada."""
    mi = e['mi_equipo'].nombre
    fj = [CP.jornada_de_fecha(i, CP.N_FECHAS[tipo], 22) for i in range(CP.N_FECHAS[tipo])]
    e['datos_carrera']['copas'] = {tipo: {
        'tipo': tipo, 'temporada': 1, 'clubes': [{'nombre': mi}, {'nombre': 'Rival Copa'}], 'num_jornadas': 22,
        'fechas_jornada': fj, 'campeon': None,
        'partidos': [{'id': f"{tipo}-{fecha}-0", 'fecha': fecha, 'fase': 'Fase de liga',
                      'local': mi if local else 'Rival Copa', 'visitante': 'Rival Copa' if local else mi,
                      'gl': 0, 'gv': 0, 'jugado': False}]}}
    return fj
```

Pie del archivo (copiar tal cual al final):

```python
if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
```

---

### Task 1: Sábados de cada jornada y fecha de liga

**Files:**
- Create: `alpha_football/calendario.py`
- Test: `tests/test_calendario.py` (nuevo)

**Interfaces:**
- Consumes: `market.ventanas_mercado(n) -> [(primera, última, nombre)]`, `paises.es_sudamerica(tipo) -> bool`.
- Produces: `calendario.sabados(n, cont, anio) -> tuple[date]`, `cierres(cont, anio) -> (date, date)`, `continente(estado) -> 'europa'|'sudamerica'`, `anio(estado) -> int`, `asegurar(estado) -> dict` (`{'clave': [...], 'mov': {}}`), `fecha_liga(estado, jornada) -> date`, `texto_fecha(d, con_anio=True) -> str`, constantes `ANIO_BASE`, `PLAN`, `DIAS_LIGA`, `DIAS_COPA`, `MIN_DIAS`.

- [ ] **Step 1: Crear el test** con la cabecera, el pie y estos casos:

```python
def test_sabados_europa_22():
    s = CAL.sabados(22, 'europa', 2026)
    assert len(s) == 22 and all(d.weekday() == 5 for d in s)
    assert all(b > a for a, b in zip(s, s[1:]))
    assert s[0] == date(2026, 8, 15) and s[1] == date(2026, 8, 22)        # J1-J2 en agosto, antes del 31
    assert s[2] == date(2026, 9, 5) and s[9] == date(2026, 12, 19)        # J3-J10: septiembre a diciembre
    assert s[10] == date(2027, 1, 2) and s[11] == date(2027, 1, 23)       # J11-J12 en enero, antes del 31
    assert s[12] == date(2027, 2, 6) and s[21] == date(2027, 5, 29)       # J13-J22: febrero a mayo
    c1, c2 = CAL.cierres('europa', 2026)
    assert (c1, c2) == (date(2026, 8, 31), date(2027, 1, 31))
    assert s[1] + timedelta(days=2) < c1 < s[2] and s[11] + timedelta(days=2) < c2 < s[12]


def test_sabados_sudamerica_22():
    s = CAL.sabados(22, 'sudamerica', 2027)
    assert len(s) == 22 and all(d.weekday() == 5 for d in s)
    assert s[0] == date(2027, 1, 16) and s[1] == date(2027, 1, 23)        # J1-J2 en enero
    assert s[2] == date(2027, 2, 6) and s[9] == date(2027, 7, 17)         # J3-J10: febrero a julio
    assert s[10] == date(2027, 8, 7) and s[11] == date(2027, 8, 28)       # J11-J12 en agosto
    assert s[12] == date(2027, 9, 4) and s[21] == date(2027, 12, 11)      # J13-J22: septiembre a diciembre
    assert CAL.cierres('sudamerica', 2027) == (date(2027, 1, 31), date(2027, 8, 31))


def test_otros_largos_de_liga():
    for n in (38, 14, 6, 2, 1):
        for cont, anio in (('europa', 2026), ('sudamerica', 2027)):
            s = CAL.sabados(n, cont, anio)
            assert len(s) == n and all(d.weekday() == 5 for d in s), (n, cont)
            assert all(b > a for a, b in zip(s, s[1:])), (n, cont)
    s38 = CAL.sabados(38, 'europa', 2026)
    assert s38[0] >= date(2026, 8, 1) and s38[-1] <= date(2027, 6, 15)


def test_fecha_de_liga_es_fin_de_semana_y_estable():
    e = _e()
    fechas = [CAL.fecha_liga(e, j) for j in range(1, 23)]
    assert all(f.weekday() in (5, 6, 0) for f in fechas)                  # sábado, domingo o lunes
    assert fechas == [CAL.fecha_liga(e, j) for j in range(1, 23)]         # la semilla no cambia
    assert all(0 <= (f - b).days <= 2 for f, b in zip(fechas, CAL.sabados(22, 'europa', 2026)))
    assert CAL.fecha_liga(e, 0) == fechas[0] and CAL.fecha_liga(e, 99) == fechas[-1]   # fuera de rango: se acota
    assert CAL.texto_fecha(date(2026, 8, 15)) == "sáb 15 ago 2026"
    assert CAL.texto_fecha(date(2026, 8, 15), False) == "sáb 15 ago"


def test_anio_y_continente():
    e = _e()
    assert CAL.continente(e) == 'europa' and CAL.anio(e) == 2026
    e['temporada'] = 3
    assert CAL.anio(e) == 2028 and CAL.fecha_liga(e, 1).year == 2028
    sa = _e('betplay')
    assert CAL.continente(sa) == 'sudamerica' and CAL.anio(sa) == 2027 and CAL.fecha_liga(sa, 1).month == 1
    sa['datos_carrera']['mundo'] = {'anio': {'sudamerica': 2031}}         # lo que escribirá el sub-proyecto F
    assert CAL.anio(sa) == 2031
    assert CAL.continente({}) == 'europa'


def test_el_calendario_se_rearma_al_cambiar_de_temporada_o_club():
    e = _e()
    cal = CAL.asegurar(e)
    assert cal['mov'] == {} and cal['clave'][0] == 2026
    cal['mov']['liga:5'] = '2026-10-04'
    assert CAL.fecha_liga(e, 5) == date(2026, 10, 4)                      # lo reprogramado manda
    assert CAL.asegurar(e) is cal                                         # misma temporada: se conserva
    e['temporada'] = 2
    assert CAL.asegurar(e)['mov'] == {} and CAL.fecha_liga(e, 5).year == 2027
    e['mi_equipo'] = e['liga'].equipos[1]
    assert CAL.asegurar(e)['clave'][3] == str(e['liga'].equipos[1].id)
    viejo = _e(); viejo['datos_carrera']['calendario'] = "roto"           # save con el dato dañado
    assert CAL.asegurar(viejo)['mov'] == {}
    viejo['datos_carrera']['calendario']['mov']['liga:1'] = 'no-es-fecha'
    assert CAL.fecha_liga(viejo, 1).weekday() in (5, 6, 0)                # fecha inválida: se ignora
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: falla al importar (`cannot import name 'calendario'`).

- [ ] **Step 3: Crear `alpha_football/calendario.py`** con este contenido:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Calendario real (v0.4.11.0)
Fecha real de cada partido del user. La temporada va de agosto a mayo en Europa y de enero a
diciembre en Sudamérica, y se arma A PARTIR de las ventanas de mercado (market.ventanas_mercado):
las jornadas de cada ventana quedan antes del 31 de agosto / 31 de enero, que son los cierres.
- Liga: sábado, domingo o lunes. Copa: martes, miércoles o jueves entre dos jornadas.
- Las fechas base salen de una semilla (no cambian al guardar y cargar). Solo se guarda lo
  reprogramado: datos_carrera['calendario'] = {'clave': [...], 'mov': {clave del partido: 'AAAA-MM-DD'}}.
- Dos partidos tuyos necesitan MIN_DIAS entre sí: revisar_choques mueve uno y avisa por correo.
- El descanso (energía) es proporcional a los días entre partidos: descanso_tras_liga.
Sin UI.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

ANIO_BASE = {'europa': 2026, 'sudamerica': 2027}       # año en que empieza la temporada 1
# (mes, día, años a sumar al de inicio): cierre de la ventana de inicio, último sábado posible del
# tramo 2, primer día del tramo 3, cierre de la ventana de invierno y último sábado posible del tramo 4
PLAN = {
    'europa': {'cierre1': (8, 31, 0), 'fin2': (12, 21, 0), 'ini3': (1, 2, 1), 'cierre2': (1, 31, 1),
               'fin4': (5, 31, 1)},
    'sudamerica': {'cierre1': (1, 31, 0), 'fin2': (7, 20, 0), 'ini3': (8, 1, 0), 'cierre2': (8, 31, 0),
                   'fin4': (12, 13, 0)},
}
DIAS_LIGA = ((0, 55), (1, 40), (2, 5))       # días desde el sábado (sáb, dom, lun) y su peso
DIAS_COPA = ((3, 40), (4, 45), (5, 15))      # días desde el sábado anterior (mar, mié, jue) y su peso
MIN_DIAS = 3                                 # días mínimos entre dos partidos tuyos
DIAS_SEM = ('lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom')
MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
ETIQUETA_COPA = {'champions': 'UCL', 'libertadores': 'LIB'}


def texto_fecha(d: date, con_anio: bool = True) -> str:
    """'sáb 15 ago 2026' (o sin el año)."""
    t = f"{DIAS_SEM[d.weekday()]} {d.day} {MESES[d.month - 1]}"
    return f"{t} {d.year}" if con_anio else t


def _f(anio_inicio: int, t: tuple) -> date:
    return date(anio_inicio + t[2], t[0], t[1])


def _sabado_desde(d: date) -> date:
    """Primer sábado igual o posterior a d."""
    return d + timedelta(days=(5 - d.weekday()) % 7)


def _sabado_hasta(d: date) -> date:
    """Último sábado igual o anterior a d."""
    return d - timedelta(days=(d.weekday() - 5) % 7)


def _repartir(m: int, primero: date, ultimo: date) -> list:
    """m sábados repartidos parejo entre `primero` y `ultimo`; si no caben, el tramo se alarga."""
    if m <= 0:
        return []
    if m == 1:
        return [primero]
    huecos = max(m - 1, (ultimo - primero).days // 7)
    return [primero + timedelta(days=7 * int(i * huecos / (m - 1) + 0.5)) for i in range(m)]


def cierres(cont: str, anio_inicio: int) -> tuple:
    """(cierre de la ventana de inicio, cierre de la ventana de invierno)."""
    p = PLAN.get(cont, PLAN['europa'])
    return _f(anio_inicio, p['cierre1']), _f(anio_inicio, p['cierre2'])


@lru_cache(maxsize=64)
def sabados(n: int, cont: str, anio_inicio: int) -> tuple:
    """Sábado base de cada jornada (índice 0 = J1), anclado a los cierres de mercado."""
    from alpha_football.market import ventanas_mercado
    n = max(1, int(n))
    p = PLAN.get(cont, PLAN['europa'])
    vs = {v[2]: v for v in ventanas_mercado(n)}
    k1 = min(n, vs['inicio'][1])                              # última jornada de la ventana de inicio
    c1, c2 = cierres(cont, anio_inicio)
    m1 = max(0, k1 - 1)                                       # jornadas antes del primer cierre
    ult1 = _sabado_hasta(c1 - timedelta(days=3))              # su lunes también cae antes del cierre
    out = [ult1 - timedelta(days=7 * (m1 - 1 - i)) for i in range(m1)]
    tras1 = _sabado_desde(c1 + timedelta(days=1))
    if 'invierno' in vs:
        a, k2 = vs['invierno'][0], vs['invierno'][1]
        out += _repartir(a - k1, tras1, _sabado_hasta(_f(anio_inicio, p['fin2'])))
        out += _repartir(k2 - a, _sabado_desde(_f(anio_inicio, p['ini3'])), _sabado_hasta(c2 - timedelta(days=3)))
        out += _repartir(n - k2 + 1, _sabado_desde(c2 + timedelta(days=1)), _sabado_hasta(_f(anio_inicio, p['fin4'])))
    else:
        out += _repartir(n - m1, tras1, _sabado_hasta(_f(anio_inicio, p['fin4'])))
    for i in range(1, len(out)):                              # nunca dos jornadas el mismo fin de semana
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + timedelta(days=7)
    return tuple(out[:n])


@lru_cache(maxsize=4096)
def _dia(semilla: str, pesos: tuple) -> int:
    """Día sorteado con esa semilla: siempre el mismo para el mismo partido."""
    return random.Random(semilla).choices([d for d, _w in pesos], weights=[w for _d, w in pesos])[0]


# --- Estado ───────────────────────────────────────────────────────────────────

def continente(estado: dict) -> str:
    try:
        from alpha_football.paises import es_sudamerica
        return 'sudamerica' if es_sudamerica(getattr(estado.get('liga'), 'tipo', '') or '') else 'europa'
    except Exception:
        return 'europa'


def anio(estado: dict) -> int:
    """Año en que empieza la temporada del user (temporada 1: 2026/27 en Europa, 2027 en Sudamérica)."""
    cont = continente(estado)
    mundo = ((estado.get('datos_carrera') or {}).get('mundo') or {}).get('anio') or {}
    if mundo.get(cont):
        return int(mundo[cont])
    return ANIO_BASE[cont] + int(estado.get('temporada', 1) or 1) - 1


def _n(estado: dict) -> int:
    return max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))


def _sabs(estado: dict) -> tuple:
    return sabados(_n(estado), continente(estado), anio(estado))


def asegurar(estado: dict) -> dict:
    """El calendario guardado de esta temporada; al cambiar de temporada, liga o club se rearma."""
    dc = estado.setdefault('datos_carrera', {})
    clave = [anio(estado), continente(estado), _n(estado), str(getattr(estado.get('mi_equipo'), 'id', ''))]
    cal = dc.get('calendario')
    if not isinstance(cal, dict) or cal.get('clave') != clave:
        cal = dc['calendario'] = {'clave': clave, 'mov': {}}
        dc.pop('descanso_pendiente', None)
    if not isinstance(cal.get('mov'), dict):
        cal['mov'] = {}
    return cal


def _movido(estado: dict, clave: str) -> Optional[date]:
    txt = asegurar(estado)['mov'].get(clave)
    try:
        return date.fromisoformat(txt) if txt else None
    except Exception:
        return None


def fecha_liga(estado: dict, jornada: int) -> date:
    """Día en que el user juega esa jornada de liga."""
    j = max(1, min(_n(estado), int(jornada or 1)))
    movido = _movido(estado, f"liga:{j}")
    if movido:
        return movido
    a = anio(estado)
    club = str(getattr(estado.get('mi_equipo'), 'id', ''))
    return _sabs(estado)[j - 1] + timedelta(days=_dia(f"liga-{a}-{club}-{j}", DIAS_LIGA))
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `6/6 tests pasaron`.

---

### Task 2: Fechas de copa y partidos del user

**Files:**
- Modify: `alpha_football/calendario.py` (agregar al final)
- Test: `tests/test_calendario.py`

**Interfaces:**
- Consumes: `competiciones.copa(estado, tipo) -> Optional[dict]` (claves `fechas_jornada`, `partidos`, `campeon`), `competiciones.tipo_copa_user(estado) -> Optional[str]`; cada partido de copa es un dict con `fecha`, `local`, `visitante`, `gl`, `gv`, `jugado`.
- Produces: `fecha_copa(estado, tipo, i) -> Optional[date]`, `eventos_user(estado) -> list[dict]` (cada uno con `clave` (`'liga:<jornada>'` o `'copa:<tipo>:<fecha>'`), `tipo`, `num`, `fecha`, `jugado`, `local`, `rival`, `gf`, `gc`, `etiqueta`), `proximo_evento(estado) -> Optional[dict]`, `hoy(estado) -> date`, `texto_proximo(estado) -> str`.

- [ ] **Step 1: Tests** — agregar a `tests/test_calendario.py`:

```python
def test_fechas_de_copa_entre_jornadas_y_despues_del_cierre():
    e = _e(); fj = _con_copa(e)
    s = CAL.sabados(22, 'europa', 2026)
    c1, c2 = CAL.cierres('europa', 2026)
    for i, j in enumerate(fj[:-1]):
        f = CAL.fecha_copa(e, 'champions', i)
        assert f.weekday() in (1, 2, 3), (i, f)                           # martes, miércoles o jueves
        assert s[j - 1] < f < s[j], (i, j, f)                             # entre esa jornada y la siguiente
        for c in (c1, c2):
            if s[j - 1] < c < s[j]:
                assert f > c, (i, f, c)                                   # nunca antes del cierre de mercado
    assert CAL.fecha_copa(e, 'champions', len(fj) - 1) == s[-1] + timedelta(days=7)    # la final
    assert CAL.fecha_copa(e, 'champions', 0) == CAL.fecha_copa(e, 'champions', 0)      # estable


def test_copa_que_no_existe_o_fecha_fuera_de_rango():
    e = _e()
    assert CAL.fecha_copa(e, 'champions', 0) is None                      # sin copas
    _con_copa(e)
    assert CAL.fecha_copa(e, 'champions', 99) is None and CAL.fecha_copa(e, 'champions', -1) is None
    assert CAL.fecha_copa(e, 'libertadores', 0) is None
    e['datos_carrera']['copas']['champions']['fechas_jornada'] = None
    assert CAL.fecha_copa(e, 'champions', 0) is None


def test_partidos_del_user_en_orden():
    e = _e(); _con_copa(e, fecha=0)                                       # la fecha 0 se juega tras la J2
    evs = CAL.eventos_user(e)
    assert [x['clave'] for x in evs[:4]] == ['liga:1', 'liga:2', 'copa:champions:0', 'liga:3']
    assert all(b['fecha'] >= a['fecha'] for a, b in zip(evs, evs[1:]))
    assert len([x for x in evs if x['tipo'] == 'liga']) == 22
    copa = evs[2]
    assert copa['etiqueta'] == 'UCL' and copa['rival'] == 'Rival Copa' and copa['local'] and not copa['jugado']
    assert CAL.proximo_evento(e)['clave'] == 'liga:1' and CAL.hoy(e) == CAL.fecha_liga(e, 1)
    assert CAL.texto_proximo(e) == CAL.texto_fecha(CAL.fecha_liga(e, 1))
    _jugar(e, 1, 2, 1)
    assert CAL.proximo_evento(e)['clave'] == 'liga:2'
    ev1 = CAL.eventos_user(e)[0]
    assert ev1['jugado'] and {ev1['gf'], ev1['gc']} == {2, 1} and ev1['rival'] != '?'


def test_sin_liga_o_temporada_terminada():
    assert CAL.eventos_user({}) == [] and CAL.proximo_evento({}) is None and CAL.texto_proximo({}) == ''
    e = _e()
    for j in range(1, 23):
        _jugar(e, j)
    assert CAL.proximo_evento(e) is None and CAL.hoy(e) == CAL.fecha_liga(e, 22)
    vacio = estado_carrera()                                              # liga sin calendario armado
    vacio['liga'].calendario = []
    assert CAL.eventos_user(vacio) == [] and CAL.hoy(vacio) == CAL.sabados(22, 'europa', 2026)[0]
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'fecha_copa'`).

- [ ] **Step 3: Implementar** — agregar al final de `alpha_football/calendario.py`:

```python
# --- Copa ─────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1024)
def _copa_base(n: int, cont: str, anio_inicio: int, tipo: str, i: int, fj: tuple) -> date:
    """Día base de la fecha i de una copa: entre la jornada fj[i] y la siguiente."""
    sabs = sabados(n, cont, anio_inicio)
    j = max(1, min(n, fj[i]))
    if j >= n:                                        # la final: el sábado siguiente a la última jornada
        return sabs[-1] + timedelta(days=7)
    s1, s2 = sabs[j - 1], sabs[j]
    semanas = list(range(max(1, (s2 - s1).days // 7)))        # semana w: su martes es s1 + 3 + 7w
    for c in cierres(cont, anio_inicio):
        if s1 < c < s2:                               # hueco de un cierre de mercado: la copa va después
            semanas = [w for w in semanas if s1 + timedelta(days=3 + 7 * w) > c] or semanas[-1:]
    orden = sum(1 for x in fj[:i] if x == fj[i])      # otra fecha en el mismo hueco: una semana después
    w = semanas[min(len(semanas) - 1, (len(semanas) - 1) // 2 + orden)]
    return s1 + timedelta(days=7 * w + _dia(f"copa-{anio_inicio}-{tipo}-{i}", DIAS_COPA))


def fecha_copa(estado: dict, tipo: str, i: int) -> Optional[date]:
    """Día de la fecha `i` de esa copa (None si la copa o la fecha no existen)."""
    try:
        from alpha_football import competiciones as CP
        c = CP.copa(estado, tipo)
        fj = tuple(int(x) for x in ((c or {}).get('fechas_jornada') or ()))
        i = int(i)
        if not c or not 0 <= i < len(fj):
            return None
        return (_movido(estado, f"copa:{tipo}:{i}")
                or _copa_base(_n(estado), continente(estado), anio(estado), tipo, i, fj))
    except Exception as e:
        logger.error(f"No se pudo calcular la fecha {i} de la copa {tipo}: {e}")
        return None


# --- Partidos del user ────────────────────────────────────────────────────────

def eventos_user(estado: dict) -> list:
    """Tus partidos de liga y de copa ordenados por fecha."""
    out: list = []
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return out
    try:
        nombres = {e.id: e.nombre for e in liga.equipos}
        for p in getattr(liga, 'calendario', None) or []:
            if mi.id not in (p.local_id, p.visitante_id):
                continue
            loc = p.local_id == mi.id
            gf, gc = (p.goles_local, p.goles_visitante) if loc else (p.goles_visitante, p.goles_local)
            out.append({'clave': f"liga:{int(p.jornada)}", 'tipo': 'liga', 'num': int(p.jornada),
                        'fecha': fecha_liga(estado, p.jornada), 'jugado': bool(p.jugado), 'local': loc,
                        'rival': nombres.get(p.visitante_id if loc else p.local_id, '?'),
                        'gf': gf if p.jugado else None, 'gc': gc if p.jugado else None,
                        'etiqueta': f"J{int(p.jornada)}"})
    except Exception as e:
        logger.error(f"calendario: no se pudieron leer los partidos de liga: {e}")
    try:
        from alpha_football import competiciones as CP
        t = CP.tipo_copa_user(estado)
        c = CP.copa(estado, t) if t else None
        for p in (c or {}).get('partidos') or []:
            if mi.nombre not in (p.get('local'), p.get('visitante')):
                continue
            num = int(p.get('fecha', 0) or 0)
            f = fecha_copa(estado, t, num)
            if f is None:
                continue
            loc, jugado = p.get('local') == mi.nombre, bool(p.get('jugado'))
            gf, gc = (p.get('gl'), p.get('gv')) if loc else (p.get('gv'), p.get('gl'))
            out.append({'clave': f"copa:{t}:{num}", 'tipo': 'copa', 'num': num, 'fecha': f, 'jugado': jugado,
                        'local': loc, 'rival': p.get('visitante') if loc else p.get('local'),
                        'gf': gf if jugado else None, 'gc': gc if jugado else None,
                        'etiqueta': ETIQUETA_COPA.get(t, 'COPA')})
    except Exception as e:
        logger.error(f"calendario: no se pudieron leer los partidos de copa: {e}")
    out.sort(key=lambda x: (x['fecha'], x['tipo'] != 'liga'))
    return out


def proximo_evento(estado: dict) -> Optional[dict]:
    return next((e for e in eventos_user(estado) if not e['jugado']), None)


def hoy(estado: dict) -> date:
    """El día en que estás parado: el de tu próximo partido (o el del último si ya no quedan)."""
    evs = eventos_user(estado)
    prox = next((e for e in evs if not e['jugado']), None)
    if prox is not None:
        return prox['fecha']
    return evs[-1]['fecha'] if evs else _sabs(estado)[0]


def texto_proximo(estado: dict) -> str:
    """Fecha de tu próximo partido ('' si no hay)."""
    try:
        ev = proximo_evento(estado)
        return texto_fecha(ev['fecha']) if ev else ''
    except Exception as e:
        logger.error(f"calendario: no se pudo leer el próximo partido: {e}")
        return ''
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `10/10 tests pasaron`.

---

### Task 3: Reprogramación de choques

**Files:**
- Modify: `alpha_football/calendario.py` (agregar al final)
- Modify: `alpha_football/ui/match_screen.py` (final de `finalizar_jornada_liga`)
- Modify: `alpha_football/ui/league_screen.py` (en `render`, justo antes del comentario `# --- Eventos ---`)
- Test: `tests/test_calendario.py`

**Interfaces:**
- Consumes: `eventos_user`, `asegurar`, `texto_fecha`; `correo.enviar(estado, remitente, asunto, cuerpo, accion)`, `correo.accion(pantalla, texto)`.
- Produces: `revisar_choques(estado, max_eventos=3) -> list[dict]` (cada cambio: `clave`, `de`, `a`); marca `datos_carrera['calendario']['revisado']`.

- [ ] **Step 1: Tests** — agregar:

```python
def _reprogramados(e):
    return [m for m in C.bandeja(e) if m['asunto'].startswith("Partido reprogramado")]


def test_choque_mueve_la_liga_dentro_del_fin_de_semana():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['copa:champions:0'] = '2026-09-03'                         # jueves
    cal['mov']['liga:3'] = '2026-09-05'                                   # sábado: a 2 días
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['liga:3']
    assert cambios[0]['de'] == date(2026, 9, 5) and cambios[0]['a'] == date(2026, 9, 6)
    assert CAL.fecha_liga(e, 3) == date(2026, 9, 6)                       # pasa al domingo
    m = _reprogramados(e)[0]
    assert m['accion']['pantalla'] == 'calendario_screen' and "dom 6 sep" in m['cuerpo']
    assert CAL.revisar_choques(e) == [] and len(_reprogramados(e)) == 1   # ya no hay choque


def test_choque_lunes_martes_adelanta_la_liga():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1)
    cal = CAL.asegurar(e)
    cal['mov']['liga:1'] = '2026-08-15'
    cal['mov']['liga:2'] = '2026-08-24'                                   # lunes
    cal['mov']['copa:champions:0'] = '2026-08-25'                         # martes
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['liga:2'] and CAL.fecha_liga(e, 2) == date(2026, 8, 22)


def test_si_la_liga_no_puede_moverse_se_mueve_la_copa():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['copa:champions:0'] = '2026-09-03'                         # jueves
    cal['mov']['liga:3'] = '2026-09-05'                                   # sábado
    cal['mov']['liga:4'] = '2026-09-08'                                   # martes: el domingo y el lunes no sirven
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['copa:champions:0']
    assert CAL.fecha_copa(e, 'champions', 0) == date(2026, 9, 2)          # miércoles


def test_choque_sin_solucion_no_mueve_nada():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['liga:2'] = '2026-08-31'                                   # ya jugado, pegado al de copa
    cal['mov']['copa:champions:0'] = '2026-09-03'
    cal['mov']['liga:3'] = '2026-09-04'                                   # viernes: a 1 día
    cal['mov']['liga:4'] = '2026-09-07'
    antes = dict(cal['mov'])
    assert CAL.revisar_choques(e) == [] and cal['mov'] == antes and _reprogramados(e) == []


def test_solo_mira_los_proximos_partidos():
    e = _e(); _con_copa(e, fecha=0)
    cal = CAL.asegurar(e)
    cal['mov']['liga:9'] = '2026-11-21'
    cal['mov']['liga:10'] = '2026-11-22'                                  # choque lejano: todavía no se mira
    assert CAL.revisar_choques(e) == []
    assert CAL.revisar_choques({}) == []                                  # sin partida: nada
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'revisar_choques'`).

- [ ] **Step 3: Implementar** — agregar al final de `alpha_football/calendario.py`:

```python
# --- Reprogramación ───────────────────────────────────────────────────────────

def _opciones(ev: dict) -> list:
    """Otros días posibles para ese partido (liga: su fin de semana; copa: martes a jueves de su
    semana), del más cercano al más lejano."""
    f = ev['fecha']
    if ev['tipo'] == 'liga':
        base = f - timedelta(days=(f.weekday() - 5) % 7)          # su sábado
    else:
        base = f - timedelta(days=(f.weekday() - 1) % 7)          # su martes
    dias = [base + timedelta(days=k) for k in (0, 1, 2)]
    return sorted((d for d in dias if d != f), key=lambda d: abs((d - f).days))


def _cabe(evs: list, k: int, nueva: date) -> bool:
    """¿El partido k puede pasar a `nueva` sin quedar a menos de MIN_DIAS de sus vecinos?"""
    antes = evs[k - 1]['fecha'] if k > 0 else None
    despues = evs[k + 1]['fecha'] if k + 1 < len(evs) else None
    return ((antes is None or (nueva - antes).days >= MIN_DIAS)
            and (despues is None or (despues - nueva).days >= MIN_DIAS))


def _avisar_cambio(estado: dict, ev: dict, nueva: date, otro: dict) -> None:
    try:
        from alpha_football import correo as C
        que = f"la jornada {ev['num']} de liga" if ev['tipo'] == 'liga' else "el partido de copa"
        C.enviar(estado, 'club', f"Partido reprogramado: {ev['etiqueta']} contra {ev['rival']}",
                 f"Para respetar los {MIN_DIAS} días de descanso entre partidos, {que} contra {ev['rival']} "
                 f"pasa del {texto_fecha(ev['fecha'], False)} al {texto_fecha(nueva, False)}. Quedaba demasiado "
                 f"cerca de {otro['etiqueta']} contra {otro['rival']} ({texto_fecha(otro['fecha'], False)}).",
                 C.accion('calendario_screen', "VER CALENDARIO"))
    except Exception as e:
        logger.error(f"No se pudo avisar el partido reprogramado: {e}")


def revisar_choques(estado: dict, max_eventos: int = 3) -> list:
    """Mira tus próximos partidos: si dos quedan a menos de MIN_DIAS, mueve uno y avisa por correo.
    Orden: el de liga dentro de su fin de semana, el de copa entre martes y jueves, el de liga al
    fin de semana siguiente. Devuelve los cambios hechos ([{'clave', 'de', 'a'}])."""
    cambios: list = []
    try:
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return cambios
        cal = asegurar(estado)
        for _vuelta in range(6):                                  # cada vuelta arregla un choque
            evs = eventos_user(estado)
            pend = [k for k, e in enumerate(evs) if not e['jugado']][:max_eventos]
            a = next((k for k in pend[:-1] if (evs[k + 1]['fecha'] - evs[k]['fecha']).days < MIN_DIAS), None)
            if a is None:
                break
            b = a + 1
            intentos = [(k, d) for k in (a, b) if evs[k]['tipo'] == 'liga' for d in _opciones(evs[k])]
            intentos += [(k, d) for k in (a, b) if evs[k]['tipo'] == 'copa' for d in _opciones(evs[k])]
            intentos += [(k, evs[k]['fecha'] + timedelta(days=7)) for k in (b, a) if evs[k]['tipo'] == 'liga']
            hecho = next(((k, d) for k, d in intentos if _cabe(evs, k, d)), None)
            if hecho is None:
                logger.info(f"calendario: choque sin solución entre {evs[a]['clave']} y {evs[b]['clave']}")
                break
            k, nueva = hecho
            cal['mov'][evs[k]['clave']] = nueva.isoformat()
            cambios.append({'clave': evs[k]['clave'], 'de': evs[k]['fecha'], 'a': nueva})
            _avisar_cambio(estado, evs[k], nueva, evs[b] if k == a else evs[a])
    except Exception as e:
        logger.error(f"calendario: error revisando los choques: {e}", exc_info=True)
    return cambios
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `15/15 tests pasaron`.

- [ ] **Step 5: Enganches** — dos lugares.

En `alpha_football/ui/match_screen.py`, dentro de `finalizar_jornada_liga`, después del último bloque `try/except` (el de patrocinios, `_patro.revisar_jornada(estado)`) y antes del `except Exception as e:` que cierra la función:

```python
        try:  # v0.4.11.0: partidos demasiado pegados → se reprograma uno y se avisa
            from alpha_football import calendario as _cal_ch
            _cal_ch.revisar_choques(estado)
        except Exception as e_cal:
            logger.error(f"Error revisando el calendario: {e_cal}")
```

En `alpha_football/ui/league_screen.py`, en `render`, inmediatamente antes del comentario `# --- Eventos ---`:

```python
        try:  # v0.4.11.0: la primera vez que se ve el calendario de la temporada, revisa los choques
            from alpha_football import calendario as _cal
            _c = _cal.asegurar(estado)
            if not _c.get('revisado'):
                _c['revisado'] = True
                _cal.revisar_choques(estado)
        except Exception as e_cal:
            logger.error(f"Error preparando el calendario: {e_cal}")
```

- [ ] **Step 6: Test del enganche** — agregar y correr:

```python
def test_el_hub_revisa_los_choques_una_sola_vez():
    from alpha_football.ui import league_screen as L
    e = _e(); _con_copa(e, fecha=0)
    e['datos_carrera']['aviso_mercado_visto'] = [1, 1]
    pygame.event.clear(); L.render(screen, e)
    assert CAL.asegurar(e).get('revisado') is True
```

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `16/16 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py; PYTHONIOENCODING=utf-8 python tests/test_teclado_v420.py`
Expected: ambos en `N/N tests pasaron`.

---

### Task 4: Descanso y energía según los días

**Files:**
- Modify: `alpha_football/calendario.py` (agregar al final)
- Modify: `alpha_football/energia.py:83-103` (`recuperar`, `recuperar_todos`)
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga` y el cierre del partido de copa en vivo)
- Modify: `alpha_football/ui/prepartido_screen.py` (cierre del partido de copa simulado)
- Modify: `tests/test_vestuario_v310.py:399` (recuperación esperada)
- Test: `tests/test_calendario.py`

**Interfaces:**
- Produces: `calendario.dias_por_jornada(estado) -> float`, `descanso_tras_liga(estado, jornada) -> (float, float)`, `aplicar_descanso_pendiente(estado) -> float`, `tras_partido_copa_user(estado) -> None`; `energia.recuperar(j, factor=1.0)`, `energia.recuperar_todos(estado, dias=None)`; `datos_carrera['descanso_pendiente']`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_descanso_reparte_los_dias_del_hueco():
    e = _e()
    total = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days
    assert CAL.descanso_tras_liga(e, 1) == (float(total), 0.0)            # sin copa en el hueco
    _con_copa(e, fecha=0)                                                  # fecha 0: tras la J2
    d1, d2 = CAL.descanso_tras_liga(e, 2)
    assert d1 == (CAL.fecha_copa(e, 'champions', 0) - CAL.fecha_liga(e, 2)).days > 0
    assert d1 + d2 == (CAL.fecha_liga(e, 3) - CAL.fecha_liga(e, 2)).days and d2 > 0
    assert CAL.descanso_tras_liga(e, 1) == (float(total), 0.0)            # esa copa no cae en el hueco de la J1
    assert CAL.descanso_tras_liga(e, 22) == (7.0, 0.0)                    # tras la última jornada
    e['datos_carrera']['copas']['champions']['campeon'] = 'Alguien'       # copa terminada: no cuenta
    assert CAL.descanso_tras_liga(e, 2)[1] == 0.0
    assert abs(CAL.dias_por_jornada(e) - 287 / 21) < 1e-9


def test_recuperacion_proporcional_a_los_dias():
    e = _e(); j = e['mi_equipo'].jugadores[0]
    ref = CAL.dias_por_jornada(e)
    j.energia = 10; E.recuperar_todos(e)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-9                 # sin días: la de siempre
    j.energia = 10; E.recuperar_todos(e, ref)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-6
    j.energia = 10; E.recuperar_todos(e, ref / 2)
    assert abs(j.energia - 10 - E.recuperacion(j) / 2) < 1e-6
    j.energia = 10; E.recuperar_todos(e, 0); assert j.energia == 10
    j.energia = 10; E.recuperar_todos(e, -5); assert j.energia == 10      # días negativos: nada
    j.energia = 95; E.recuperar_todos(e, 60); assert j.energia == 100     # tope
    j.energia = 50; E.recuperar(j, 0.5)
    assert abs(j.energia - 50 - E.recuperacion(j) / 2) < 1e-9


def test_descanso_pendiente_se_aplica_tras_la_copa():
    e = _e(); j = e['mi_equipo'].jugadores[0]
    CAL.asegurar(e)
    e['datos_carrera']['descanso_pendiente'] = CAL.dias_por_jornada(e)
    j.energia = 10
    CAL.tras_partido_copa_user(e)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-6
    assert 'descanso_pendiente' not in e['datos_carrera']
    assert CAL.aplicar_descanso_pendiente(e) == 0                         # no se aplica dos veces
    assert CAL.aplicar_descanso_pendiente({}) == 0


def test_la_jornada_recupera_segun_los_dias_de_descanso():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    for j in mi.jugadores:
        j.energia = 10.0
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    factor = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days / CAL.dias_por_jornada(e)
    bien = [j for j in mi.jugadores if abs(j.energia - min(100.0, 10 + E.recuperacion(j) * factor)) < 1e-6]
    assert len(bien) >= len(mi.jugadores) - 2, (len(bien), len(mi.jugadores))
    assert 'descanso_pendiente' not in e['datos_carrera']                 # sin copa pendiente: todo aplicado
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'descanso_tras_liga'`, `recuperar_todos() takes 1 positional argument`).

- [ ] **Step 3: `calendario.py`** — agregar al final:

```python
# --- Descanso ─────────────────────────────────────────────────────────────────

def dias_por_jornada(estado: dict) -> float:
    """Días que hay en promedio entre dos jornadas: con esos días se recupera lo de una jornada."""
    s = _sabs(estado)
    return max(1.0, (s[-1] - s[0]).days / max(1, len(s) - 1))


def descanso_tras_liga(estado: dict, jornada: int) -> tuple:
    """(días hasta el próximo partido de cualquier competición, días que quedan después hasta la
    jornada siguiente). Sin copa en ese hueco: (todos los días, 0)."""
    jornada = int(jornada)
    if jornada >= _n(estado):
        return 7.0, 0.0
    f0 = fecha_liga(estado, jornada)
    total = max(1, (fecha_liga(estado, jornada + 1) - f0).days)
    antes = None
    try:
        from alpha_football import competiciones as CP
        for t in ('champions', 'libertadores'):
            c = CP.copa(estado, t)
            if not c or c.get('campeon'):
                continue
            for i, x in enumerate(c.get('fechas_jornada') or []):
                if int(x) != jornada:
                    continue
                f = fecha_copa(estado, t, i)
                d = (f - f0).days if f else 0
                if 0 < d < total:
                    antes = d if antes is None else min(antes, d)
    except Exception as e:
        logger.error(f"calendario: no se pudo leer la copa para el descanso: {e}")
    if antes is None:
        return float(total), 0.0
    return float(antes), float(total - antes)


def aplicar_descanso_pendiente(estado: dict) -> float:
    """Aplica (una sola vez) el descanso que quedó esperando a tu partido de copa. Devuelve los días."""
    dias = float((estado.get('datos_carrera') or {}).pop('descanso_pendiente', 0) or 0)
    if dias > 0:
        from alpha_football.energia import recuperar_todos
        recuperar_todos(estado, dias)
    return dias


def tras_partido_copa_user(estado: dict) -> None:
    """Al cerrar tu partido de copa: el resto del descanso hasta la jornada siguiente y los choques."""
    try:
        aplicar_descanso_pendiente(estado)
        revisar_choques(estado)
    except Exception as e:
        logger.error(f"calendario: error tras el partido de copa: {e}")
```

- [ ] **Step 4: `energia.py`** — reemplazar `recuperar` y el encabezado de `recuperar_todos`:

```python
def recuperar(j, factor: float = 1.0) -> None:
    """v0.4.11.0: `factor` = parte de una jornada de descanso (días / días por jornada)."""
    j.energia = min(100.0, float(getattr(j, 'energia', 100.0)) + recuperacion(j) * factor)


def recuperar_todos(estado: dict, dias: Optional[float] = None) -> None:
    """Recuperan todos los clubes de las ligas y los de la copa. v0.4.11.0: con `dias` la
    recuperación es proporcional a los días de descanso (calendario.py); sin `dias`, la fija de siempre."""
    factor = 1.0
    if dias is not None:
        try:
            from alpha_football.calendario import dias_por_jornada
            factor = max(0.0, float(dias)) / dias_por_jornada(estado)
        except Exception as e:
            logger.error(f"No se pudo calcular el descanso por días: {e}")
            factor = 1.0
```

El resto del cuerpo de `recuperar_todos` no cambia, salvo la última línea del bucle: `recuperar(j)` → `recuperar(j, factor)`. Si `energia.py` no tiene `logger`, agregar arriba `import logging` y `logger = logging.getLogger(__name__)`.

- [ ] **Step 5: `finalizar_jornada_liga`** (`alpha_football/ui/match_screen.py`) — tres cambios.

(a) Inmediatamente antes del comentario `# v3.8.0: las dos copas juegan sus fechas vencidas tras la jornada` (el bloque de `simular_copa_fondo`):

```python
        # v0.4.11.0: descanso según el calendario. Primero los días hasta el próximo partido de
        # cualquier competición; el resto, después de la copa (más abajo).
        descanso = None
        try:
            from alpha_football import calendario as _cal_d
            from alpha_football.energia import recuperar_todos as _recuperar_dias
            _cal_d.aplicar_descanso_pendiente(estado)      # por si quedó de una fecha de copa sin cerrar
            descanso = _cal_d.descanso_tras_liga(estado, int(getattr(partido, 'jornada', 0) or 1))
            _recuperar_dias(estado, descanso[0])
        except Exception as e_desc:
            logger.error(f"Error calculando el descanso de la jornada: {e_desc}")
            descanso = None
```

(b) En el bloque `# v3.1.0: recuperación física de todos...`, reemplazar:

```python
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado)
```

por:

```python
            from alpha_football.energia import recuperar_todos
            if descanso is None:
                recuperar_todos(estado)                    # sin calendario: la recuperación fija de siempre
            elif descanso[1] > 0:                          # v0.4.11.0: lo que queda tras la fecha de copa
                from alpha_football import competiciones as _CP_d
                if _CP_d.partido_pendiente_user(estado):   # tu partido de copa va antes: se aplica al cerrarlo
                    estado.setdefault('datos_carrera', {})['descanso_pendiente'] = descanso[1]
                else:
                    recuperar_todos(estado, descanso[1])
```

(c) Nada más: el enganche de `revisar_choques` ya quedó en el Task 3.

- [ ] **Step 6: Cierre de tu partido de copa** — dos lugares, siempre DESPUÉS del gasto de energía del partido.

En `alpha_football/ui/match_screen.py` (cierre del partido en vivo), dentro de `if match_mode == 'copa':`, después de la línea `registrar_resultado_copa(estado, goles_l, goles_v, pen_user)`:

```python
                    from alpha_football import calendario as _cal_copa      # v0.4.11.0
                    _cal_copa.tras_partido_copa_user(estado)
```

En `alpha_football/ui/prepartido_screen.py` (simulación instantánea), en la rama `elif match_mode == 'copa':`, después del bloque `try/except` de `post_partido_user` (el que termina en `logger.error(f"Error de vestuario en sim instantánea de copa: {e_ves}")`):

```python
            try:  # v0.4.11.0: resto del descanso hasta la jornada siguiente y choques del calendario
                from alpha_football import calendario as _cal_copa
                _cal_copa.tras_partido_copa_user(estado)
            except Exception as e_cal:
                logger.error(f"Error con el calendario tras la copa: {e_cal}")
```

- [ ] **Step 7: Test viejo que esperaba la recuperación fija** — en `tests/test_vestuario_v310.py`, en el test que tiene la línea `esperado = [min(100.0, max(0.0, 100 - E.gasto_por_minuto(j) * m) + E.recuperacion(j)) for m in (100, 90)]`, agregar antes del `for j in gastaron:`:

```python
    from alpha_football import calendario as CAL          # v0.4.11.0: la recuperación depende de los días de descanso
    _jugada = e['liga'].jornada_actual - 1
    _factor = sum(CAL.descanso_tras_liga(e, _jugada)) / CAL.dias_por_jornada(e)
```

y cambiar esa línea por:

```python
        esperado = [min(100.0, max(0.0, 100 - E.gasto_por_minuto(j) * m) + E.recuperacion(j) * _factor) for m in (100, 90)]
```

La línea siguiente del test (`assert all(j.energia == 100 for j in mi.jugadores if j.id not in once_ids)`) sigue valiendo: partían de 100.

- [ ] **Step 8: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `20/20 tests pasaron`.
Run (uno por uno): `test_vestuario_v310.py`, `test_stamina_puntos.py`, `test_motor_v400.py`, `test_copa_v430.py`, `test_competiciones_v380.py`, `test_integracion_v290.py`.
Expected: todos en `N/N tests pasaron` (o su línea final de OK). Un test que compare la energía tras una jornada con `recuperacion(j)` entera se ajusta igual que el del Step 7.

---

### Task 5: La fecha en el botón JUGAR y en el pre-partido

**Files:**
- Modify: `alpha_football/ui/league_screen.py` (bloque que dibuja `R_JUGAR`, tras `draw_text(screen, l1, ...)`)
- Modify: `alpha_football/ui/prepartido_screen.py` (tras el título `"PREPARAR PARTIDO"`)
- Test: `tests/test_calendario.py`

**Interfaces:**
- Consumes: `calendario.texto_proximo(estado) -> str`.

- [ ] **Step 1: Test** — agregar:

```python
def test_hub_y_prepartido_dibujan_la_fecha_sin_errores():
    import logging
    from alpha_football.ui import league_screen as L

    class _Errores(logging.Handler):
        def __init__(self):
            super().__init__(level=logging.ERROR); self.vistos = []
        def emit(self, record):
            self.vistos.append(record.getMessage())
    h = _Errores(); logging.getLogger().addHandler(h)
    try:
        e = _e(); _con_copa(e, fecha=0)
        e['datos_carrera']['aviso_mercado_visto'] = [1, 1]
        pygame.event.clear(); L.render(screen, e)
        pygame.event.clear(); L.render(screen, e)
    finally:
        logging.getLogger().removeHandler(h)
    assert not [m for m in h.vistos if 'fecha' in m.lower() or 'calendario' in m.lower()], h.vistos
    assert CAL.texto_proximo(e).startswith(('sáb', 'dom', 'lun'))
```

- [ ] **Step 2: Hub** — en `alpha_football/ui/league_screen.py`, en el bloque que dibuja el botón JUGAR, después de:

```python
        draw_text(screen, l1, (R_JUGAR.x + 20, R_JUGAR.y + 10), size='lg',
                  color='verde' if habilitado else 'blanco')
```

agregar:

```python
        try:   # v0.4.11.0: fecha del partido, arriba a la derecha del botón
            from alpha_football import calendario as _cal_j
            _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
            if _txt_fecha:
                _w_fecha = get_font('sm').size(_txt_fecha)[0]
                draw_text(screen, _txt_fecha, (R_JUGAR.right - 20 - _w_fecha, R_JUGAR.y + 16), size='sm', color='dorado')
        except Exception as e_fecha:
            logger.error(f"Error al dibujar la fecha del partido: {e_fecha}")
```

(`get_font` ya está importado en ese módulo; si no lo estuviera, agregarlo al `from alpha_football.ui.theme import ...` de arriba.)

- [ ] **Step 3: Pre-partido** — en `alpha_football/ui/prepartido_screen.py`, después de las dos líneas que dibujan `"PREPARAR PARTIDO"`:

```python
        if match_mode != 'amistoso':      # v0.4.11.0: fecha real del partido que se va a jugar
            try:
                from alpha_football import calendario as _cal_p
                _txt_fecha = _cal_p.texto_proximo(estado)
                if _txt_fecha:
                    draw_text(screen, _txt_fecha, (SCREEN_W // 2 - get_font('sm').size(_txt_fecha)[0] // 2, 50),
                              size='sm', color='azul')
            except Exception as e_fecha:
                logger.error(f"Error al dibujar la fecha en el pre-partido: {e_fecha}")
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `21/21 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py; PYTHONIOENCODING=utf-8 python tests/test_presentacion_v410.py; PYTHONIOENCODING=utf-8 python tests/test_ux_v360.py`
Expected: los tres en `N/N tests pasaron`.

---

### Task 6: Pantalla CALENDARIO

**Files:**
- Create: `alpha_football/ui/calendario_screen.py`
- Modify: `alpha_football/ui/league_screen.py:352-356` (`TARJETAS['direccion']`)
- Modify: `main.py` (`MODULOS_PANTALLA`, junto a `'cantera_screen'`)
- Modify: `alpha_football/ui/atajos.py` (junto a `'cantera_screen'`)
- Modify: `alpha_football/ui/ayuda.py` (texto corto junto a `'cantera_screen'`, función `_ayuda_calendario` y registro en `AYUDA`)
- Modify: `tests/test_hub_v240.py:172` (tarjetas esperadas de `'direccion'`)
- Test: `tests/test_calendario.py`

**Interfaces:**
- Consumes: `calendario.eventos_user`, `hoy`, `cierres`, `continente`, `anio`, `texto_fecha`.
- Produces: `calendario_screen.render(screen, estado) -> Optional[str]`, `celdas_mes(anio, mes) -> list[date]` (42 días), `eventos_por_dia(estado) -> dict`, `limites(estado) -> ((año, mes), (año, mes))`, `rect_celda(i)`, `_rects()`, `R_GRILLA`; `estado['cal_mes'] = [año, mes]`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_cuadricula_del_mes():
    from alpha_football.ui import calendario_screen as KS
    c = KS.celdas_mes(2026, 8)
    assert len(c) == 42 and c[0].weekday() == 0 and c[0] <= date(2026, 8, 1) and c[-1] >= date(2026, 8, 31)
    assert [(b - a).days for a, b in zip(c, c[1:])] == [1] * 41
    assert KS.rect_celda(41).bottom <= KS.R_GRILLA.bottom and KS.rect_celda(6).right <= KS.R_GRILLA.right
    assert KS.R_GRILLA.bottom <= 696                                       # no pisa la barra de atajos


def test_pantalla_calendario_navega_y_vuelve():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    por_dia = KS.eventos_por_dia(e)
    assert por_dia[CAL.fecha_liga(e, 1)][0]['clave'] == 'liga:1'
    assert KS.limites(e) == ((2026, 8), (2027, 5))                         # del primer partido al último
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [2026, 8]                                       # abre en el mes de tu próximo partido
    key(pygame.K_RIGHT); KS.render(screen, e); assert e['cal_mes'] == [2026, 9]
    key(pygame.K_LEFT); KS.render(screen, e); key(pygame.K_LEFT); KS.render(screen, e)
    assert e['cal_mes'] == [2026, 8]                                       # no retrocede antes del primer partido
    for _ in range(14):
        key(pygame.K_RIGHT); KS.render(screen, e)
    assert e['cal_mes'] == [2027, 5]                                       # ni pasa del último
    key(pygame.K_ESCAPE); assert KS.render(screen, e) == 'league_screen' and 'cal_mes' not in e
    assert KS.render(screen, {}) == 'league_screen'                        # sin partida: vuelve


def test_la_pantalla_esta_registrada():
    import main
    from alpha_football.ui import league_screen as L, ayuda
    assert any(t[2] == 'calendario_screen' for t in L.TARJETAS['direccion'])
    assert len(L.TARJETAS['oficina']) == 8                                 # OFICINA no cambia: está llena
    assert main.MODULOS_PANTALLA['calendario_screen'] == 'alpha_football.ui.calendario_screen'
    assert 'calendario_screen' in ayuda.AYUDA and ayuda.AYUDA['calendario_screen']({})
```

- [ ] **Step 2: Correr y ver que falla** (`cannot import name 'calendario_screen'`).

- [ ] **Step 3: Crear `alpha_football/ui/calendario_screen.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Calendario (Pygame)
v0.4.11.0: mes en cuadrícula con tus partidos de liga y copa, los cierres de mercado y el día en
que estás parado (el de tu próximo partido). ← → cambia de mes, ESC vuelve.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

MESES_LARGO = ('ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE',
               'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE')
DIAS_CABECERA = ('LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM')
R_GRILLA = pygame.Rect(16, 110, 1248, 586)       # termina en y=696 (barra de atajos)
CABECERA_H = 28
COLS, FILAS = 7, 6


def _rects() -> dict:
    return {'volver': pygame.Rect(1116, 12, 148, 40),
            'prev': pygame.Rect(16, 62, 44, 36), 'next': pygame.Rect(68, 62, 44, 36)}


def rect_celda(i: int) -> pygame.Rect:
    w = R_GRILLA.width // COLS
    h = (R_GRILLA.height - CABECERA_H) // FILAS
    return pygame.Rect(R_GRILLA.x + (i % COLS) * w, R_GRILLA.y + CABECERA_H + (i // COLS) * h, w - 4, h - 4)


def celdas_mes(anio: int, mes: int) -> list:
    """Los 42 días (6 semanas de lunes a domingo) de la cuadrícula de ese mes."""
    primero = date(anio, mes, 1)
    inicio = primero - timedelta(days=primero.weekday())
    return [inicio + timedelta(days=k) for k in range(COLS * FILAS)]


def eventos_por_dia(estado: dict) -> dict:
    out: dict = {}
    for ev in CAL.eventos_user(estado):
        out.setdefault(ev['fecha'], []).append(ev)
    return out


def limites(estado: dict) -> tuple:
    """((año, mes) del primer partido o cierre, (año, mes) del último)."""
    fechas = [ev['fecha'] for ev in CAL.eventos_user(estado)]
    fechas += list(CAL.cierres(CAL.continente(estado), CAL.anio(estado)))
    return (min(fechas).year, min(fechas).month), (max(fechas).year, max(fechas).month)


def _mover(estado: dict, paso: int) -> None:
    a, m = estado['cal_mes']
    m += paso
    if m < 1:
        a, m = a - 1, 12
    elif m > 12:
        a, m = a + 1, 1
    lo, hi = limites(estado)
    if lo <= (a, m) <= hi:
        estado['cal_mes'] = [a, m]


def _texto_evento(ev: dict) -> tuple:
    """(línea 1, línea 2, color) de un partido dentro de su celda."""
    l1 = f"{ev['etiqueta']} {'vs' if ev['local'] else 'en'} {str(ev['rival'])[:13]}"
    if ev['jugado']:
        gf, gc = int(ev['gf'] or 0), int(ev['gc'] or 0)
        return l1, f"{gf}-{gc}", 'verde' if gf > gc else 'rojo' if gf < gc else 'blanco'
    return l1, "LOCAL" if ev['local'] else "VISITANTE", 'dorado' if ev['tipo'] == 'copa' else 'azul'


def _salir(estado: dict) -> str:
    estado.pop('cal_mes', None)
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return 'league_screen'
        hoy = CAL.hoy(estado)
        if not estado.get('cal_mes'):
            estado['cal_mes'] = [hoy.year, hoy.month]
        r = _rects()
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return _salir(estado)
                if ev.key == pygame.K_LEFT:
                    _mover(estado, -1)
                elif ev.key == pygame.K_RIGHT:
                    _mover(estado, 1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if r['volver'].collidepoint(ev.pos):
                    return _salir(estado)
                if r['prev'].collidepoint(ev.pos):
                    _mover(estado, -1)
                elif r['next'].collidepoint(ev.pos):
                    _mover(estado, 1)

        a, m = estado['cal_mes']
        draw_gradient_bg(screen)
        draw_text(screen, "CALENDARIO", (16, 14), size='lg', color='dorado')
        draw_button(screen, r['prev'], "<", r['prev'].collidepoint(mouse_pos))
        draw_button(screen, r['next'], ">", r['next'].collidepoint(mouse_pos))
        draw_button(screen, r['volver'], "VOLVER", r['volver'].collidepoint(mouse_pos))
        draw_text(screen, f"{MESES_LARGO[m - 1]} {a}", (128, 68), size='md', color='blanco')
        draw_text(screen, f"Próximo partido: {CAL.texto_fecha(hoy)}", (520, 70), size='sm', color='azul')

        por_dia = eventos_por_dia(estado)
        dias_cierre = set(CAL.cierres(CAL.continente(estado), CAL.anio(estado)))
        ancho = R_GRILLA.width // COLS
        for c, nombre in enumerate(DIAS_CABECERA):
            draw_text(screen, nombre, (R_GRILLA.x + c * ancho + 8, R_GRILLA.y + 4), size='sm', color='azul', shadow=False)
        for i, d in enumerate(celdas_mes(a, m)):
            rc = rect_celda(i)
            del_mes = d.month == m
            pygame.draw.rect(screen, (20, 26, 46) if del_mes else (14, 18, 32), rc, border_radius=6)
            if d == hoy:
                pygame.draw.rect(screen, COLORS['dorado'], rc, width=2, border_radius=6)
            draw_text(screen, str(d.day), (rc.x + 6, rc.y + 4), size='sm',
                      color='blanco' if del_mes else 'azul', shadow=False)
            y = rc.y + 26
            if d in dias_cierre:
                draw_text(screen, "CIERRE MERCADO", (rc.x + 6, y), size='sm', color='rojo', shadow=False)
                y += 20
            for ev in por_dia.get(d, [])[:1 if d in dias_cierre else 2]:
                l1, l2, col = _texto_evento(ev)
                draw_text(screen, l1, (rc.x + 6, y), size='sm', color=col, shadow=False)
                draw_text(screen, l2, (rc.x + 6, y + 20), size='sm', color='blanco', shadow=False)
                y += 40
        return None
    except Exception as e:
        logger.error(f"Error en calendario_screen: {e}", exc_info=True)
        return 'league_screen'
```

- [ ] **Step 4: Registrar la pantalla** — cuatro lugares.

`alpha_football/ui/league_screen.py`, en `TARJETAS['direccion']`, después de la tarjeta CANTERA:

```python
        ("CALENDARIO", "Tus partidos de liga y copa, día por día", 'calendario_screen'),   # v0.4.11.0
```

`main.py`, en `MODULOS_PANTALLA`, después de la línea de `'cantera_screen'`:

```python
    'calendario_screen': 'alpha_football.ui.calendario_screen',        # v0.4.11.0
```

`alpha_football/ui/atajos.py`, en el mismo diccionario donde está `'cantera_screen'`, después de esa línea:

```python
    'calendario_screen': "← → Mes · O Opciones · H Ayuda · ESC Volver",   # v0.4.11.0
```

`alpha_football/ui/ayuda.py`: en el diccionario de textos cortos donde está `'cantera_screen': "Juveniles del club: ..."`, después de esa línea:

```python
    'calendario_screen': "Tus partidos de liga y copa con su fecha real. Dos partidos necesitan 3 días entre sí: si chocan, se reprograma uno.",   # v0.4.11.0
```

después de la función `_ayuda_cantera`:

```python
# ---------------------------------------------------------------- calendario (v0.4.11.0)
def _ayuda_calendario(estado: dict) -> list:
    from alpha_football.ui import calendario_screen as KS
    r = KS._rects()
    return [
        (KS.R_GRILLA, "Mes", "Tus partidos de liga (J) y de copa, día por día. En dorado, el día de tu próximo partido; en rojo, el cierre del mercado."),
        (r['prev'], "Mes anterior", "También con la flecha izquierda."),
        (r['next'], "Mes siguiente", "También con la flecha derecha."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]
```

y junto a `AYUDA['cantera_screen'] = _ayuda_cantera`:

```python
AYUDA['calendario_screen'] = _ayuda_calendario
```

- [ ] **Step 5: Test del hub** — en `tests/test_hub_v240.py`, en el diccionario de tarjetas esperadas (línea ~172), agregar `'calendario_screen'` al final de la lista de `'direccion'`.

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `24/24 tests pasaron`.
Run (uno por uno): `test_hub_v240.py`, `test_ayuda_v390.py`, `test_ux_v360.py`, `test_teclado_v420.py`.
Expected: todos en `N/N tests pasaron`. Si alguno recorre todas las pantallas y pide algo más para la nueva (por ejemplo, que la ayuda de la pestaña DIRECCIÓN nombre cada tarjeta), se agrega lo que pida siguiendo lo que ya hay para `cantera_screen`.

---

### Task 7: Cierre de C

**Files:**
- Modify: `context.md` (bitácora y pendientes; fecha del encabezado)

- [ ] **Step 1: Suite completa, una sola vez y un archivo a la vez.** Lanzarla con la opción de segundo plano de la herramienta (no con `nohup`), escribiendo el resumen en una carpeta temporal fuera del repo:

```bash
cd "C:/Users/diego/Downloads/AlphaFootball" && mkdir -p "$TEMP/af_suite_c" && : > "$TEMP/af_suite_c/resumen.txt" && for f in tests/test_*.py; do
  b=$(basename "$f" .py); PYTHONIOENCODING=utf-8 timeout 1200 python "$f" > "$TEMP/af_suite_c/$b.log" 2>&1; rc=$?
  echo "$b rc=$rc FAIL=$(grep -c 'FAIL' "$TEMP/af_suite_c/$b.log") · $(tail -1 "$TEMP/af_suite_c/$b.log" | cut -c1-80)" >> "$TEMP/af_suite_c/resumen.txt"
done; echo TERMINADO >> "$TEMP/af_suite_c/resumen.txt"
```

Expected: cada línea con `rc=0` y `FAIL=0`. Lo que no cumpla se arregla: si el test daba por hecha la recuperación fija por jornada o la lista de tarjetas, se ajusta el test; si no, es un bug del cambio.

- [ ] **Step 2: Comprobación sin pantalla** — con `SDL_VIDEODRIVER=dummy`, sobre un estado de carrera con el calendario de liga armado, renderizar un cuadro de `league_screen`, `calendario_screen` y `prepartido_screen` y confirmar que no hay excepciones ni líneas `ERROR` en el log. Probar también una liga sudamericana (`estado_carrera('betplay')`): la pantalla abre en enero de 2027.

- [ ] **Step 3: `context.md`** — agregar la bitácora "2026-10-07 — Calendario real (v0.4.11.0, sub-proyecto C, sin commit)" con: el módulo y sus funciones, las tres desviaciones del spec (tarjeta en DIRECCIÓN, fecha en JUGAR, "hoy" = próximo partido), el reparto del descanso y el test viejo ajustado. Actualizar la fecha del encabezado y dejar como pendientes D, E, F y la prueba a mano: fecha en JUGAR y en el pre-partido, pantalla CALENDARIO (← →), un correo "Partido reprogramado" y la energía tras una semana con copa.
