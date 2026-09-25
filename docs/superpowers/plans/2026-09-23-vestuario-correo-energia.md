# Vestuario, correo y energía (v3.1.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correo con acciones, moral con consecuencias, energía minuto a minuto con resistencia, lesiones/sanciones reales, personalidades, clásicos, pagos de cláusula de la IA y calificación de DT con segunda oportunidad.

**Architecture:** Cuatro módulos sin UI (`energia.py`, `correo.py`, `vestuario.py`, `data/clasicos.py`) + cambios en `directiva.py` y `mercado_ia.py`. Los hooks se enchufan en los dos cierres de partido del user (vivo en `match_screen`, instantáneo en `prepartido_screen`) y en el cierre de jornada (`finalizar_jornada_liga`). Una pantalla nueva (`correo_screen`).

**Tech Stack:** Python 3.10, Pygame 2.6 (tests con `SDL_VIDEODRIVER=dummy`), tests como scripts (`python tests/<archivo>.py`, sin pytest).

**Spec:** `docs/superpowers/specs/2026-09-23-vestuario-correo-energia-design.md`

## Global Constraints

- Sin commits (Diego prueba todo al final); cada "checkpoint" = correr la suite completa.
- Comentarios y textos de UI en español; versión en comentarios nuevos: `v3.1.0`.
- Todo hook en `try/except` con `logger.error(...)`; nunca romper el cierre de jornada.
- Saves viejos deben cargar: campos nuevos con defaults y derivación determinista.
- Moral: `factor = 1 + (moral − 70) × 0.004`. Energía: `factor = 1 − max(0, 60 − e)/600`; lesión `× (1 + max(0, 60 − e)/30)`.
- Gasto por minuto `0.40 × (1.5 − res/100)` (×1.10 si edad > 30). Recuperación `15 + 0.15 × res` (−3 si edad > 30).
- Bonus de resistencia por rasgo: pulmón de hierro +15, rústico +8, regateador −5.
- Personalidades: normal 70, lider 8, profesional 10, polemico 7, mercenario 5.
- Calif. DT inicial 50; cambios: superado +8, cumplido +4, fallado −8, liga +10, copa +12, descenso −12, despido −10, pedido +3/−4, clásico perdido −2.
- Cláusula IA: 10% por jornada con ventana abierta; negativa 40% (moral ≥ 70, comprador de menor media, no mercenario).
- Suite: `for f in tests/test_*.py; do python "$f" | tail -1; done` con `PYTHONIOENCODING=utf-8`.

## Review Focus

- Partido con jugador sin `id` repetido/ausente (ids random en saves viejos): `cerrar_partido` no debe romper ni gastar energía de quien no jugó → test en Task 1 con dos jugadores del mismo equipo e id distinto y uno sin minutos.
- Save viejo (v2.9) sin campos nuevos: carga con resistencia 1-99, personalidad válida, energía 100, rival asignado → test en Task 2 y Task 5.
- Amistoso: no debe gastar energía, ni moral, ni correo → test en Task 9.
- Plantilla corta: la IA no puede pagar una cláusula si te deja con menos de 18 jugadores → test en Task 8.
- Temporada que termina sin partidos para resolver un pedido (liga corta): el pedido vence como fallado en el cierre, no queda colgado → test en Task 7.

---

### Task 1: `energia.py` — resistencia, gasto, recuperación, lesiones y sanciones

**Files:**
- Create: `alpha_football/energia.py`
- Test: `tests/test_vestuario_v310.py` (crear con cabecera estándar)

**Interfaces:**
- Produces: `resistencia_inicial(fisico:int, edad:int, rasgo:str|None, semilla:str)->int`, `gasto_por_minuto(j)->float`,
  `energia_en_minuto(j, minutos:int)->float`, `energia_actual(j)->float`, `factor_energia(e:float)->float`,
  `factor_lesion(e:float)->float`, `factor_moral(m:float)->float`, `puntaje_once(j)->float`, `recuperacion(j)->float`,
  `recuperar(j)->None`, `recuperar_todos(estado)->None`, `cerrar_partido(equipo, minutos:dict[int,int], rng=None)->list[dict]`
  (incidencia = `{'tipo': 'lesion'|'sancion', 'jugador': j, 'partidos': n}`).

- [ ] **Step 1: Test file + failing tests**

```python
"""v3.1.0 (sub-proyecto 2): energía, moral, correo, personalidades, clásicos, cláusulas y DT."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import energia as E
from alpha_football.models import Jugador, Equipo, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division


def jug(pos='MED', ovr=70, edad=25, res=50, **kw):
    j = Jugador("Test", f"J{random.randint(0, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr, edad=edad,
                id=random.randint(10**6, 10**7), resistencia=res, **kw)
    return j


def test_gasto_y_recuperacion_por_resistencia():
    alto, medio, bajo = jug(res=90), jug(res=50), jug(res=30)
    assert abs(E.energia_en_minuto(alto, 90) - (100 - 0.40 * 0.6 * 90)) < 0.01      # ~78.4
    assert E.energia_en_minuto(alto, 90) > E.energia_en_minuto(medio, 90) > E.energia_en_minuto(bajo, 90)
    viejo = jug(res=50, edad=33)
    assert E.energia_en_minuto(viejo, 90) < E.energia_en_minuto(medio, 90)
    assert E.recuperacion(alto) == 15 + 0.15 * 90 and E.recuperacion(viejo) == 15 + 0.15 * 50 - 3
    medio.energia = 90; E.recuperar(medio); assert medio.energia == 100
    print("  test_gasto_y_recuperacion_por_resistencia: OK")


def test_factores_en_extremos():
    assert E.factor_energia(100) == 1.0 and E.factor_energia(60) == 1.0 and abs(E.factor_energia(0) - 0.9) < 1e-9
    assert E.factor_lesion(80) == 1.0 and E.factor_lesion(0) == 3.0
    assert E.factor_moral(70) == 1.0 and abs(E.factor_moral(40) - 0.88) < 1e-9 and abs(E.factor_moral(100) - 1.12) < 1e-9
    print("  test_factores_en_extremos: OK")


def test_resistencia_por_rasgo_y_edad():
    base = E.resistencia_inicial(70, 25, None, "x")
    assert E.resistencia_inicial(70, 25, 'pulmon_de_hierro', "x") == min(99, base + 15)
    assert E.resistencia_inicial(70, 25, 'rustico', "x") == min(99, base + 8)
    assert E.resistencia_inicial(70, 25, 'regateador', "x") == max(1, base - 5)
    assert E.resistencia_inicial(70, 34, None, "x") == max(1, base - 8)
    assert E.resistencia_inicial(70, 25, None, "x") == base                          # determinista
    assert all(1 <= E.resistencia_inicial(f, 38, None, str(f)) <= 99 for f in (1, 50, 99))
    print("  test_resistencia_por_rasgo_y_edad: OK")


def test_cerrar_partido_gasta_solo_minutos_jugados():
    eq = Equipo("Prueba FC", "X", 3.0, "cruyffismo", 1_000_000, [jug(), jug(), jug()])
    a, b, c = eq.jugadores
    c.lesion_partidos, c.partidos_sancion = 2, 1
    E.cerrar_partido(eq, {a.id: 90, b.id: 30}, rng=random.Random(99))
    assert abs(a.energia - E.energia_en_minuto(jug(), 90)) < 0.01 or a.lesion_partidos > 0
    assert b.energia > a.energia                                   # sustituido en el 30' gasta menos
    assert c.energia == 100 and c.lesion_partidos == 1 and c.partidos_sancion == 0   # no jugó: descuenta
    print("  test_cerrar_partido_gasta_solo_minutos_jugados: OK")


def test_lesiones_mas_probables_con_energia_baja():
    def tasa(energia):
        n = 0
        for s in range(4000):
            j = jug(); j.energia = energia
            eq = Equipo("T", "X", 3.0, "cruyffismo", 1, [j])
            n += any(i['tipo'] == 'lesion' for i in E.cerrar_partido(eq, {j.id: 90}, rng=random.Random(s)))
        return n / 4000
    fresca, vacia = tasa(100), tasa(0)
    assert 0.006 < fresca < 0.02 and vacia > 2 * fresca, (fresca, vacia)
    print("  test_lesiones_mas_probables_con_energia_baja: OK")


TESTS = [test_gasto_y_recuperacion_por_resistencia, test_factores_en_extremos, test_resistencia_por_rasgo_y_edad,
         test_cerrar_partido_gasta_solo_minutos_jugados, test_lesiones_mas_probables_con_energia_baja]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    sys.exit(1 if fail else 0)
```

- [ ] **Step 2: Run** `python tests/test_vestuario_v310.py` → FAIL (`No module named alpha_football.energia`).

- [ ] **Step 3: Implement `alpha_football/energia.py`**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Energía, resistencia, lesiones y sanciones (v3.1.0)
Sin UI y sin importar models (models importa de aquí los factores de rendimiento).
La energía (0-100) baja minuto a minuto según la resistencia y se recupera al cerrar cada
jornada de liga. Por debajo de 60 rinde menos y se lesiona más.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

GASTO_BASE = 0.40
UMBRAL = 60
BONUS_RASGO_RES = {'pulmon_de_hierro': 15, 'rustico': 8, 'regateador': -5}
PROB_LESION_90 = 0.012
PROB_ROJA_90 = 0.004
DURACION_LESION = (1, 2, 3, 4)
PESOS_LESION = (50, 25, 15, 10)


def _edad(j) -> int:
    return int(getattr(j, 'edad', 25) or 25)


def _res(j) -> int:
    return int(getattr(j, 'resistencia', 50) or 50)


def resistencia_inicial(fisico: int, edad: int, rasgo: Optional[str], semilla: str) -> int:
    azar = random.Random(f"res|{semilla}")
    r = int(fisico) + azar.randint(-8, 8)
    if int(edad) > 30:
        r -= 2 * (int(edad) - 30)
    r += BONUS_RASGO_RES.get(rasgo or '', 0)
    return max(1, min(99, r))


def gasto_por_minuto(j) -> float:
    g = GASTO_BASE * (1.5 - _res(j) / 100)
    return g * 1.10 if _edad(j) > 30 else g


def energia_en_minuto(j, minutos: int) -> float:
    return max(0.0, float(getattr(j, 'energia', 100.0)) - gasto_por_minuto(j) * max(0, int(minutos)))


def energia_actual(j) -> float:
    vivo = getattr(j, 'energia_vivo', None)
    return float(getattr(j, 'energia', 100.0)) if vivo is None else float(vivo)


def factor_energia(e: float) -> float:
    return 1.0 - max(0.0, UMBRAL - float(e)) / 600.0


def factor_lesion(e: float) -> float:
    return 1.0 + max(0.0, UMBRAL - float(e)) / 30.0


def factor_moral(m: float) -> float:
    return 1.0 + (float(m) - 70.0) * 0.004


def puntaje_once(j) -> float:
    """Media ajustada por cansancio para que la IA rote (−0.3 por punto de energía bajo 70)."""
    return float(getattr(j, 'overall', 60)) - max(0.0, 70.0 - float(getattr(j, 'energia', 100.0))) * 0.3


def recuperacion(j) -> float:
    r = 15 + 0.15 * _res(j)
    return r - 3 if _edad(j) > 30 else r


def recuperar(j) -> None:
    j.energia = min(100.0, float(getattr(j, 'energia', 100.0)) + recuperacion(j))


def recuperar_todos(estado: dict) -> None:
    """Cierre de jornada de liga: recuperan todos los clubes de las 10 ligas y los de la copa."""
    equipos = []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            equipos += list(getattr(liga, 'equipos', []) or [])
    equipos += list((estado.get('copa_equipos_obj') or {}).values())
    vistos = set()
    for eq in equipos:
        if id(eq) in vistos:
            continue
        vistos.add(id(eq))
        for j in getattr(eq, 'jugadores', []) or []:
            recuperar(j)


def cerrar_partido(equipo, minutos: dict, rng: Optional[random.Random] = None) -> list:
    """
    Cierre físico de un partido de `equipo`. `minutos` = {jugador.id: minutos jugados}.
    Gasta energía de los que jugaron, descuenta 1 a lesionados/sancionados que no jugaron
    y sortea lesiones y rojas. Retorna las incidencias nuevas.
    """
    azar = rng or random.Random()
    incidencias = []
    for j in list(getattr(equipo, 'jugadores', []) or []):
        try:
            j.energia_vivo = None
            m = int(minutos.get(getattr(j, 'id', None), 0) or 0)
            if m <= 0:
                if j.lesion_partidos > 0:
                    j.lesion_partidos -= 1
                if j.partidos_sancion > 0:
                    j.partidos_sancion -= 1
                continue
            antes = float(getattr(j, 'energia', 100.0))
            j.energia = energia_en_minuto(j, m)
            media = (antes + j.energia) / 2
            if azar.random() < PROB_LESION_90 * m / 90 * factor_lesion(media):
                j.lesion_partidos = azar.choices(DURACION_LESION, weights=PESOS_LESION)[0]
                incidencias.append({'tipo': 'lesion', 'jugador': j, 'partidos': j.lesion_partidos})
            elif azar.random() < PROB_ROJA_90 * m / 90:
                j.partidos_sancion = 2 if azar.random() < 0.2 else 1
                incidencias.append({'tipo': 'sancion', 'jugador': j, 'partidos': j.partidos_sancion})
        except Exception as e:
            logger.error(f"cerrar_partido: error con {getattr(j, 'apellido', '?')}: {e}")
    return incidencias
```

- [ ] **Step 4: Run** → los tests de energía fallan solo por `Jugador(... resistencia=...)` (se agrega en Task 2). Continuar con Task 2 y correr ambos juntos.

---

### Task 2: `models.py` — campos nuevos, derivación y factores de rendimiento

**Files:**
- Modify: `alpha_football/models.py` (Jugador: campos tras `clausula`, `__post_init__`, `to_dict`, `from_dict`, `poder_*`; Equipo: `rival`, `from_dict`)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `energia.resistencia_inicial`, `energia.factor_moral/factor_energia/energia_actual`, `vestuario.personalidad_inicial(rasgo, semilla)->str` (se crea aquí en un `vestuario.py` mínimo; Task 6 lo amplía).
- Produces: `Jugador.resistencia:int`, `energia:float`, `personalidad:str`, `pide_salir:bool`, `jornadas_moral_baja:int`, `notas_recientes:list[float]`, `energia_vivo:Optional[float]` (transitorio, no se guarda); `Equipo.rival:str`.

- [ ] **Step 1: Failing tests** (agregar a `TESTS`)

```python
def test_jugador_nuevo_y_save_viejo():
    j = Jugador("Ana", "Pulmón", "MED", 70, 70, 70, 70, 70, rasgo='pulmon_de_hierro', id=1234)
    assert 1 <= j.resistencia <= 99 and j.energia == 100 and j.personalidad in (
        'normal', 'lider', 'profesional', 'polemico', 'mercenario')
    viejo = {k: v for k, v in j.to_dict().items()
             if k not in ('resistencia', 'energia', 'personalidad', 'pide_salir', 'jornadas_moral_baja', 'notas_recientes')}
    k = Jugador.from_dict(viejo)
    assert k.resistencia == j.resistencia and k.personalidad == j.personalidad and k.energia == 100
    assert 'energia_vivo' not in j.to_dict()
    lider = Jugador("L", "Der", "DEF", 70, 70, 70, 70, 70, rasgo='lider', id=5)
    assert lider.personalidad == 'lider'
    j.energia, j.notas_recientes, j.pide_salir = 42.5, [6.0, 7.1], True
    r = Jugador.from_dict(j.to_dict())
    assert r.energia == 42.5 and r.notas_recientes == [6.0, 7.1] and r.pide_salir
    eq = Equipo("A", "X", 3.0, "cruyffismo", 1, [], rival="B")
    assert Equipo.from_dict(eq.to_dict()).rival == "B" and Equipo.from_dict({'nombre': 'Z'}).rival == ""
    print("  test_jugador_nuevo_y_save_viejo: OK")


def test_rendimiento_por_moral_y_energia():
    j = jug(ovr=70)
    base = j.poder_ataque_efectivo()
    j.moral = 40; assert abs(j.poder_ataque_efectivo() / base - 0.88) < 0.01
    j.moral = 70; j.energia = 0; assert abs(j.poder_ataque_efectivo() / base - 0.90) < 0.01
    j.energia_vivo = 100; assert abs(j.poder_defensa_efectivo() / jug(ovr=70).poder_defensa_efectivo() - 1) < 0.01
    print("  test_rendimiento_por_moral_y_energia: OK")
```

- [ ] **Step 2: Run** → FAIL (`unexpected keyword 'resistencia'`).

- [ ] **Step 3: Implement**

`alpha_football/vestuario.py` (mínimo; Task 6 agrega el resto debajo):

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Vestuario (v3.1.0)
Moral por jornada, personalidades, pide-salir, clásicos y cierre de partido del user.
Sin UI. No importa models a nivel de módulo (models importa personalidad_inicial de aquí).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

PERSONALIDADES = ('normal', 'lider', 'profesional', 'polemico', 'mercenario')
PESOS_PERSONALIDAD = (70, 8, 10, 7, 5)


def personalidad_inicial(rasgo: Optional[str], semilla: str) -> str:
    if rasgo == 'lider':
        return 'lider'
    return random.Random(f"per|{semilla}").choices(PERSONALIDADES, weights=PESOS_PERSONALIDAD)[0]
```

En `models.py` (arriba, tras los imports): `from alpha_football import energia as _E`.

Jugador — campos nuevos tras `clausula: int = 0`:

```python
    # v3.1.0: vestuario y físico. resistencia/personalidad vacíos = derivar (saves viejos).
    resistencia: int = 0
    energia: float = 100.0
    personalidad: str = ""
    pide_salir: bool = False
    jornadas_moral_baja: int = 0
    notas_recientes: list = field(default_factory=list)
    energia_vivo: Optional[float] = None       # transitorio: energía en el tramo que se simula
```

Al final de `__post_init__` (dentro de un `try` propio):

```python
        try:
            semilla = f"{self.id}|{self.nombre}|{self.apellido}"
            if not self.resistencia:
                self.resistencia = _E.resistencia_inicial(self.fisico, self.edad, self.rasgo, semilla)
            if not self.personalidad:
                from alpha_football.vestuario import personalidad_inicial
                self.personalidad = personalidad_inicial(self.rasgo, semilla)
        except Exception:
            self.resistencia = self.resistencia or 50
            self.personalidad = self.personalidad or 'normal'
```

`poder_ataque_efectivo` / `poder_defensa_efectivo`: reemplazar `* (self.moral / 70.0)` por
`* _E.factor_moral(self.moral) * _E.factor_energia(_E.energia_actual(self))`.

`to_dict`: tras `d = asdict(self)` agregar `d.pop("energia_vivo", None)`.

`from_dict`: en el `cls(...)` agregar

```python
                resistencia=int(datos.get("resistencia", 0) or 0),
                energia=float(datos.get("energia", 100.0) if datos.get("energia") is not None else 100.0),
                personalidad=str(datos.get("personalidad", "") or ""),
                pide_salir=bool(datos.get("pide_salir", False)),
                jornadas_moral_baja=int(datos.get("jornadas_moral_baja", 0) or 0),
                notas_recientes=[float(x) for x in (datos.get("notas_recientes") or [])][-5:],
```

Equipo — campo tras `division: int = 1`: `rival: str = ""  # v3.1.0: nombre del club clásico`; en `from_dict`: `rival=str(datos.get("rival", "") or ""),`.

- [ ] **Step 4: Run** `python tests/test_vestuario_v310.py` → 7/7 (Tasks 1-2). Correr `tests/test_mentalidad_v250.py` (calibración de goles) → 10/10.

---

### Task 3: Motor — energía por tramo, cierre físico de partidos de la IA, IA que rota

**Files:**
- Modify: `alpha_football/engine.py` (`_simular_minutos`, `simular_partido`, `simular_rango`, `_once_titular`)
- Modify: `alpha_football/formaciones.py:127` (`mejor_once` acepta `puntaje`)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `energia.energia_en_minuto`, `energia.cerrar_partido`, `energia.puntaje_once`.
- Produces: `simular_partido(..., aplicar_fisico: bool = True)`; `simular_rango(..., minutos_previos: Optional[dict] = None)` con claves `id(jugador)` → minutos ya jugados; `mejor_once(jugadores, formacion, puntaje=None)`.

- [ ] **Step 1: Failing tests**

```python
def _liga(tipo='premier'):
    return load_league_teams(tipo)


def test_equipo_cansado_rinde_menos():
    from alpha_football import engine
    liga = _liga()
    a, b = liga.equipos[0], liga.equipos[1]
    def goles(energia_a, n=1500):                      # diferencia de gol de `a` (ataque y defensa)
        tot = 0
        for _ in range(n):
            for j in a.jugadores: j.energia = energia_a
            for j in b.jugadores: j.energia = 100
            r = engine.simular_partido(a, b, aplicar_fisico=False)
            tot += r.goles_local - r.goles_visitante
        return tot / n
    fresco, vacio = goles(100), goles(0)
    assert vacio < fresco, (fresco, vacio)
    print("  test_equipo_cansado_rinde_menos: OK")


def test_simular_partido_gasta_energia_de_los_titulares():
    from alpha_football import engine
    liga = _liga()
    a, b = liga.equipos[0], liga.equipos[1]
    for j in a.jugadores + b.jugadores: j.energia = 100
    once = engine._once_titular(a)
    engine.simular_partido(a, b)
    assert all(j.energia < 100 or j.lesion_partidos for j in once)
    assert all(j.energia == 100 for j in a.jugadores if j not in once)
    assert all(getattr(j, 'energia_vivo', None) is None for j in a.jugadores)
    for j in a.jugadores: j.energia = 100
    engine.simular_partido(a, b, aplicar_fisico=False)
    assert all(j.energia == 100 for j in a.jugadores)
    print("  test_simular_partido_gasta_energia_de_los_titulares: OK")


def test_ia_rota_al_cansado():
    from alpha_football import engine
    eq = _liga().equipos[0]
    eq.alineacion_activa = None
    once = engine._once_titular(eq)
    estrella = max((j for j in once if j.posicion != 'POR'), key=lambda j: j.overall)
    estrella.energia = 5
    assert estrella not in engine._once_titular(eq)
    print("  test_ia_rota_al_cansado: OK")
```

- [ ] **Step 2: Run** → FAIL (`unexpected keyword 'aplicar_fisico'`).

- [ ] **Step 3: Implement**

`formaciones.mejor_once(jugadores, formacion, puntaje=None)`: definir `_p = puntaje or (lambda j: getattr(j, "overall", 60))` y usar `_p(j)` en lugar de `getattr(j, "overall", 60)` en `por_pos[p].append(...)` y en `restantes`.

`engine._once_titular`, rama IA: `from alpha_football.energia import puntaje_once` y
`once = [no_lesionados[i] for i in mejor_once(no_lesionados, "4-3-3", puntaje=puntaje_once)]`.

`engine._simular_minutos(..., previas, minutos_previos=None)`: al inicio

```python
    # v3.1.0: cada jugador juega el tramo con la energía que tiene al empezarlo.
    from alpha_football.energia import energia_en_minuto
    primer = minutos[0] if len(minutos) else 1
    for j in list(jl) + list(jv):
        prev = (minutos_previos or {}).get(id(j), primer - 1)
        j.energia_vivo = energia_en_minuto(j, prev)
```

`simular_partido`: agregar keyword-only `aplicar_fisico: bool = True` (junto a `ment_v`). Antes del `return`:

```python
    for j in list(jl) + list(jv):
        j.energia_vivo = None
    if aplicar_fisico:   # v3.1.0: partidos de la IA (el user cierra su parte en vestuario)
        from alpha_football.energia import cerrar_partido
        cerrar_partido(local, {j.id: 90 for j in jl})
        cerrar_partido(visitante, {j.id: 90 for j in jv})
```

`simular_rango(..., ment_v="ia", minutos_previos: Optional[dict] = None)`: pasar `minutos_previos` a `_simular_minutos` y antes del `return` limpiar `j.energia_vivo = None` de `jl + jv`.

- [ ] **Step 4: Run** `tests/test_vestuario_v310.py` → 10/10; `tests/test_mentalidad_v250.py` → 10/10; `tests/test_hub_v240.py` → 16/16.

---

### Task 4: `correo.py`

**Files:**
- Create: `alpha_football/correo.py`
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Produces: `enviar(estado, remitente:str, asunto:str, cuerpo:str, accion:dict|None=None)->dict`, `accion(pantalla:str, texto:str)->dict`, `bandeja(estado)->list`, `no_leidos(estado)->int`, `marcar_leido(estado, msg_id:int)->None`, `MAX_CORREOS=200`. Mensaje: `{id, temporada, jornada, remitente, asunto, cuerpo, leido, accion}`; lo más nuevo primero.

- [ ] **Step 1: Failing test**

```python
def test_correo_basico_y_guardado():
    import json
    from alpha_football import correo as C
    e = {'temporada': 2, 'datos_carrera': {}}
    m = C.enviar(e, 'medico', "Lesión de X", "3 partidos", C.accion('team_screen', 'VER DIRECCIÓN'))
    assert m['id'] == 1 and not m['leido'] and C.no_leidos(e) == 1 and C.bandeja(e)[0] is m
    C.marcar_leido(e, 1); assert C.no_leidos(e) == 0
    for i in range(250): C.enviar(e, 'club', f"m{i}", "")
    assert len(C.bandeja(e)) == C.MAX_CORREOS and C.bandeja(e)[0]['asunto'] == 'm249'
    assert json.loads(json.dumps(e['datos_carrera']))['correo'][0]['asunto'] == 'm249'
    print("  test_correo_basico_y_guardado: OK")
```

- [ ] **Step 2: Run** → FAIL (no module).

- [ ] **Step 3: Implement**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo de la oficina (v3.1.0)
Mensajes de la directiva, los jugadores, el cuerpo médico y otros clubes. Se guardan con la
partida en datos_carrera['correo'] (lo más nuevo primero, tope MAX_CORREOS). Cada mensaje
puede traer una acción: la pantalla a la que lleva su botón.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_CORREOS = 200
REMITENTES = {'directiva': "Directiva", 'jugador': "Jugador", 'medico': "Cuerpo médico", 'club': "Club"}


def bandeja(estado: dict) -> list:
    return estado.setdefault('datos_carrera', {}).setdefault('correo', [])


def accion(pantalla: str, texto: str) -> dict:
    return {'pantalla': pantalla, 'texto': texto}


def enviar(estado: dict, remitente: str, asunto: str, cuerpo: str, accion: Optional[dict] = None) -> dict:
    lista = bandeja(estado)
    liga = estado.get('liga')
    msg = {'id': max((int(m.get('id', 0)) for m in lista), default=0) + 1,
           'temporada': int(estado.get('temporada', 1) or 1),
           'jornada': int(getattr(liga, 'jornada_actual', 1) or 1),
           'remitente': remitente, 'asunto': str(asunto)[:80], 'cuerpo': str(cuerpo),
           'leido': False, 'accion': accion}
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def no_leidos(estado: dict) -> int:
    return sum(1 for m in bandeja(estado) if not m.get('leido'))


def marcar_leido(estado: dict, msg_id: int) -> None:
    for m in bandeja(estado):
        if m.get('id') == msg_id:
            m['leido'] = True
```

- [ ] **Step 4: Run** → 11/11.

---

### Task 5: Clásicos

**Files:**
- Create: `alpha_football/data/clasicos.py`
- Modify: `alpha_football/ui/menu.py` (`_ligas_por_division`, antes del `return`)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Produces: `CLASICOS: list[tuple[str, str]]`, `asignar_rivales(equipos:list)->None` (solo llena `rival` vacío), `es_clasico(a, b)->bool`.

- [ ] **Step 1: Failing test**

```python
def test_clasicos_reales():
    from alpha_football.data.clasicos import es_clasico
    liga = load_league_teams('laliga')
    primeras, segunda = _ligas_por_division(liga, {}, {})
    por_nombre = {e.nombre: e for l in list(primeras.values()) + list(segunda.values()) for e in l.equipos}
    assert por_nombre['Real Vadrid'].rival == 'FC Farcelona' and por_nombre['FC Farcelona'].rival == 'Real Vadrid'
    assert es_clasico(por_nombre['Patetico de Madriz'], por_nombre['Real Vadrid'])
    assert es_clasico(por_nombre['Boca Grande'], por_nombre['River Au'])
    assert not es_clasico(por_nombre['Real Vadrid'], por_nombre['Real Suciedad'])
    por_nombre['Real Vadrid'].rival = 'Gordona'                  # editado a mano: no se pisa
    from alpha_football.data.clasicos import asignar_rivales
    asignar_rivales(list(por_nombre.values()))
    assert por_nombre['Real Vadrid'].rival == 'Gordona'
    print("  test_clasicos_reales: OK")
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `data/clasicos.py`**

```python
# -*- coding: utf-8 -*-
"""
v3.1.0: clásicos reales por liga. Cada par = (fragmento del nombre del club, fragmento del rival),
en minúsculas, para reconocer las parodias. El primer par que menciona a un club define su rival;
un partido es clásico si CUALQUIERA de los dos tiene al otro de rival. Editable en el editor.
"""
from __future__ import annotations

CLASICOS = [
    ('real vadrid', 'farcelona'), ('patetico', 'real vadrid'), ('flaco de bilbao', 'suciedad'),
    ('gordona', 'farcelona'),
    ('desunido', 'billete'), ('higado', 'desunido'), ('pechofrio', 'spurs'), ('chelsea', 'pechofrio'),
    ('flamenguito', 'flumando'), ('palmerinha', 'don pablo'), ('botaagua', 'flamenguito'),
    ('boca grande', 'river au'), ('desindependiente', 'corriendo'), ('san lorenzont', 'boca grande'),
    ('talleres', 'belgrano'),
    ('pobres vagos', 'chanda fe'), ('aberica', 'deportivo casi'), ('narconal', 'junior daddy'),
]


def _buscar(equipos: list, fragmento: str):
    return next((e for e in equipos if fragmento in str(getattr(e, 'nombre', '')).lower()), None)


def asignar_rivales(equipos: list) -> None:
    for eq in equipos:
        if getattr(eq, 'rival', ''):
            continue
        nombre = str(getattr(eq, 'nombre', '')).lower()
        for a, b in CLASICOS:
            otro = b if a in nombre else a if b in nombre else None
            rival = _buscar(equipos, otro) if otro else None
            if rival is not None and rival is not eq:
                eq.rival = rival.nombre
                break


def es_clasico(a, b) -> bool:
    ra, rb = getattr(a, 'rival', ''), getattr(b, 'rival', '')
    return bool((ra and ra == getattr(b, 'nombre', None)) or (rb and rb == getattr(a, 'nombre', None)))
```

`menu._ligas_por_division`, antes de `return primeras, segunda`:

```python
    try:  # v3.1.0: clásicos (saves viejos y carreras nuevas; no pisa los editados)
        from alpha_football.data.clasicos import asignar_rivales
        asignar_rivales([e for l in list(primeras.values()) + list(segunda.values())
                         if l is not None for e in l.equipos])
    except Exception as e_cl:
        logger.error(f"No se pudieron asignar los clásicos: {e_cl}")
```

- [ ] **Step 4: Run** → 12/12.

---

### Task 6: `vestuario.py` — moral, personalidades, pide-salir, desarrollo y cierre de temporada

**Files:**
- Modify: `alpha_football/vestuario.py`, `alpha_football/finanzas.py` (nuevo `salario_mercado`), `alpha_football/desarrollo.py:127-173`
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `finanzas.salario_mercado(j)->int` (= `max(SALARIO_MIN, int(_valor(j) * SALARIO_PCT_VALOR))`, refactor de `contrato_inicial` para usarla).
- Produces: `forma(j)->float`, `actualizar_moral(equipo, reporte:list, gf:int, gc:int, es_clasico:bool, jugaron_ids:set, rng=None)->dict` (`{'quejas': [j], 'pide_salir': [j]}`), `cierre_temporada(estado, rng=None)->list[str]` (bonus de potencial).

- [ ] **Step 1: Failing tests**

```python
def _plantel(n=16, **kw):
    js = [jug(ovr=60 + i, **kw) for i in range(n)]
    for j in js: j.salario = 10**9            # sueldo alto: sin efecto de contrato
    return Equipo("Prueba FC", "X", 3.0, "cruyffismo", 1, js)


def _rep(js, nota):
    return [{'id': j.id, 'nota': nota} for j in js]


def test_moral_reglas():
    from alpha_football import vestuario as V
    eq = _plantel(); js = eq.jugadores
    for j in js: j.personalidad, j.moral = 'normal', 70
    once = js[-11:]; ids = {j.id for j in once}
    V.actualizar_moral(eq, _rep(once, 7.5), 2, 0, False, ids)
    assert all(j.moral == 75 for j in once)                   # +3 nota, +2 victoria
    assert all(j.moral == 72 for j in js[:5])                 # +2 victoria (no son top 5)
    for j in js: j.moral = 70
    top = sorted(js, key=lambda j: -j.overall)[0]
    V.actualizar_moral(eq, _rep([j for j in once if j is not top], 6.0), 0, 0, False, ids - {top.id})
    assert top.moral == 67                                     # top 5 sin jugar
    for j in js: j.moral = 70
    V.actualizar_moral(eq, _rep(once, 6.0), 0, 1, True, ids)
    assert all(j.moral == 62 for j in once)                   # −2 derrota −6 clásico
    for j in js: j.moral, j.personalidad = 70, 'normal'
    once[0].personalidad = 'lider'
    V.actualizar_moral(eq, _rep(once, 6.0), 0, 1, True, ids)
    assert all(j.moral == 66 for j in once)                   # líder: pérdida a la mitad
    j0 = js[0]; j0.moral, j0.salario, j0.personalidad = 70, 1, 'mercenario'
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 66                                      # sueldo bajo ×2
    j0.moral, j0.notas_recientes = 80, [5.0] * 5
    j0.salario = 10**9
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 78                                      # mala forma
    j0.notas_recientes, j0.moral = [], 80
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 79                                      # deriva a 70
    print("  test_moral_reglas: OK")


def test_pide_salir_y_polemico():
    from alpha_football import vestuario as V
    eq = _plantel(); js = eq.jugadores
    for j in js: j.personalidad, j.moral = 'profesional', 70
    a, b = js[0], js[1]
    a.personalidad, b.personalidad = 'normal', 'polemico'
    salen = []
    for _ in range(6):
        a.moral = b.moral = 20
        salen += V.actualizar_moral(eq, [], 0, 0, False, set(), rng=random.Random(1))['pide_salir']
    assert b in salen and a in salen and salen.index(b) < salen.index(a)   # polémico a las 4, normal a las 6
    assert any(j.moral < 70 for j in js[2:])                            # el polémico contagia
    a.moral = 55
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert not a.pide_salir
    print("  test_pide_salir_y_polemico: OK")


def test_desarrollo_mas_rapido_con_buena_moral():
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    attrs = ('ataque', 'defensa', 'fisico', 'tecnica', 'mental')
    def progreso(moral):
        eq = _liga().equipos[0]
        for j in eq.jugadores:
            j.moral, j.notas_recientes, j.progreso_desarrollo, j.potencial = moral, [7.0] * 5, 0.0, 99
        antes = sum(getattr(j, a) for j in eq.jugadores for a in attrs)
        desarrollar_plantilla_post_partido(eq, 3, 0, rng=random.Random(4))
        subidas = sum(getattr(j, a) for j in eq.jugadores for a in attrs) - antes
        return sum(j.progreso_desarrollo for j in eq.jugadores) + subidas / 3   # 1.0 de progreso = +3 atributos
    assert progreso(80) > progreso(70) * 1.10
    eq = _liga().equipos[0]
    desarrollar_plantilla_post_partido(eq, 1, 0, rng=random.Random(4))
    assert all(len(j.notas_recientes) <= 5 for j in eq.jugadores)
    print("  test_desarrollo_mas_rapido_con_buena_moral: OK")


def test_cierre_temporada_potencial():
    from alpha_football import vestuario as V
    eq = _plantel(); mi = eq
    for j in eq.jugadores: j.edad, j.moral, j.promedio_nota, j.partidos_jugados, j.potencial = 21, 80, 7.0, 10, 80
    V.cierre_temporada({'mi_equipo': mi}, rng=random.Random(2))
    subieron = [j for j in eq.jugadores if j.potencial > 80]
    assert 0 < len(subieron) < len(eq.jugadores) and all(j.potencial <= 82 for j in eq.jugadores)
    print("  test_cierre_temporada_potencial: OK")
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement**

`finanzas.py`:

```python
def salario_mercado(j) -> int:
    """v3.1.0: lo que 'merece' cobrar según su valor (base de contratos y de la moral)."""
    return max(SALARIO_MIN, int(_valor(j) * SALARIO_PCT_VALOR))
```

y en `contrato_inicial` usar `salario_mercado(j)` en el `return`.

`desarrollo.py` en el loop de `desarrollar_plantilla_post_partido`, justo después de calcular `nota` (línea ~129):

```python
        j.notas_recientes = (list(getattr(j, "notas_recientes", []) or []) + [nota])[-5:]
```

y justo antes de `j.progreso_desarrollo += inc * _factor_progreso_edad(edad_j)`:

```python
        # v3.1.0: con buena moral y buena forma progresa un 15% más rápido.
        try:
            from alpha_football.vestuario import forma
            if int(getattr(j, "moral", 70)) >= 75 and forma(j) >= 6.5:
                inc *= 1.15
        except Exception:
            pass
```

`vestuario.py` (agregar):

```python
UMBRAL_PIDE_SALIR = {'polemico': 4}
JORNADAS_PIDE_SALIR = 6


def forma(j) -> float:
    notas = list(getattr(j, 'notas_recientes', []) or [])
    return sum(notas) / len(notas) if notas else 6.5


def _mitad(delta: int) -> int:
    return int(delta / 2)


def actualizar_moral(equipo, reporte: list, gf: int, gc: int, es_clasico: bool, jugaron_ids: set,
                     rng: Optional[random.Random] = None) -> dict:
    """Moral del plantel del user tras un partido (liga o copa). Ver spec §B y §D."""
    azar = rng or random.Random()
    from alpha_football.finanzas import salario_mercado
    js = list(getattr(equipo, 'jugadores', []) or [])
    notas = {r.get('id'): float(r.get('nota', 6.0)) for r in reporte or []}
    gano, perdio = gf > gc, gf < gc
    d_equipo = (2 if gano else -2 if perdio else 0) + ((5 if gano else -6 if perdio else 0) if es_clasico else 0)
    hay_lider = any(j.personalidad == 'lider' and j.id in jugaron_ids for j in js)
    if d_equipo < 0 and hay_lider:
        d_equipo = _mitad(d_equipo)
    top5 = {id(j) for j in sorted(js, key=lambda x: -x.overall)[:5]}
    salida = {'quejas': [], 'pide_salir': []}
    for j in js:
        antes = int(j.moral)
        prof = j.personalidad == 'profesional'
        d = d_equipo
        if j.id in notas:
            d += 3 if notas[j.id] >= 7 else -3 if notas[j.id] < 5.5 else 0
        if id(j) in top5 and j.id not in jugaron_ids and j.disponible:
            d += -1 if prof else -3
        if int(getattr(j, 'salario', 0) or 0) and j.salario < 0.6 * salario_mercado(j):
            d += -1 if prof else -4 if j.personalidad == 'mercenario' else -2
        if len(getattr(j, 'notas_recientes', []) or []) >= 3 and forma(j) < 5.5:
            d -= 2
        if d == 0 and antes != 70:
            d = 1 if antes < 70 else -1
        j.moral = max(0, min(100, antes + d))
        if antes >= 40 > j.moral:
            salida['quejas'].append(j)
    for j in js:                                    # el polémico descontento contagia
        if j.personalidad == 'polemico' and j.moral < 40:
            otros = [o for o in js if o is not j]
            for o in azar.sample(otros, min(3, len(otros))):
                o.moral = max(0, o.moral - 1)
    for j in js:
        j.jornadas_moral_baja = j.jornadas_moral_baja + 1 if j.moral <= 30 else 0
        if j.pide_salir and j.moral >= 50:
            j.pide_salir = False
        umbral = UMBRAL_PIDE_SALIR.get(j.personalidad, JORNADAS_PIDE_SALIR)
        if (not j.pide_salir and j.personalidad != 'lider' and j.jornadas_moral_baja >= umbral):
            j.pide_salir = True
            salida['pide_salir'].append(j)
    return salida


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Jóvenes (≤24) con moral ≥75 y promedio ≥6.5: 40% +1 / 15% +2 de potencial."""
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    textos = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if (int(j.edad) <= 24 and int(j.moral) >= 75 and float(j.promedio_nota) >= 6.5
                and int(j.partidos_jugados) > 0 and int(j.potencial) > 0):
            r = azar.random()
            inc = 2 if r < 0.15 else 1 if r < 0.55 else 0
            if inc:
                j.potencial = min(99, j.potencial + inc)
                textos.append(f"{j.nombre} {j.apellido} +{inc} de potencial")
    return textos
```

- [ ] **Step 4: Run** → 16/16. Correr `tests/test_potencial.py`, `tests/test_desarrollo_pasivo.py`, `tests/test_finanzas_v290.py` → sin regresiones.

---

### Task 7: Directiva — calificación de DT, segunda oportunidad, catastrófico y pedidos

**Files:**
- Modify: `alpha_football/directiva.py`
- Modify: `tests/test_directiva_v280.py:72-100` (nueva regla de despido)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `correo.enviar/accion`.
- Produces: `CALIF_INICIAL=50`, `calif_dt(estado)->int`, `ajustar_calif(estado, delta:int)->int`, `es_catastrofico(estado, posicion:int, pos_max:int)->bool`, `revisar_pedido(estado, rng=None)->None`, `resolver_pedido(estado, cumplido:bool)->None`, `pedido_activo(estado)->dict|None`. Pedido: `{'temporada','tipo': 'clasico'|'puntos'|'sub21','texto','hasta','puntos_ini','pj_ini':{str(id):pj},'resuelto','cumplido','creado_en':[temporada, jugadas]}`.

- [ ] **Step 1: Update `tests/test_directiva_v280.py::test_evaluar_temporada`** (reemplazar el bloque desde `# fallado con confianza alta`):

```python
    # fallado sin advertencia previa: segunda oportunidad (advertencia, multa, confianza 40)
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=2)
    bal = e['mi_equipo'].balance
    r = D.evaluar_temporada(e, 4)
    assert r['resultado'] == 'fallado' and not r['despido'] and D.confianza(e) == 40
    assert e['datos_carrera']['advertencia_dt'] is True
    assert e['mi_equipo'].balance == bal - int(obj['presupuesto_ref'] * 0.20)
    # fallar con la advertencia vigente: despido con 3 opciones de menor nivel
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=2)
    r = D.evaluar_temporada(e, 4)
    assert r['despido'] and e['despido_pendiente']
```

Y en `test_cambiar_de_club` agregar `assert not e['datos_carrera'].get('advertencia_dt')`.

- [ ] **Step 2: Failing tests nuevos en `test_vestuario_v310.py`**

```python
def _estado(tipo='premier', idx=0):
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    inicializar_calendario_liga(liga)
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def test_catastrofico_despide_sin_segunda_oportunidad():
    from alpha_football import directiva as D, correo as C
    e = _estado()
    D.definir_objetivo(e).update(pos_max=2)
    r = D.evaluar_temporada(e, len(e['liga'].equipos))          # último = desciende
    assert r['despido'] and D.calif_dt(e) == 50 - 8 - 12 - 10
    e2 = _estado()
    D.definir_objetivo(e2).update(pos_max=1)
    r2 = D.evaluar_temporada(e2, 3)                             # 2 debajo: advertencia
    assert not r2['despido'] and any('advertencia' in m['asunto'].lower() for m in C.bandeja(e2))
    e3 = _estado(); D.definir_objetivo(e3).update(pos_max=3)
    D.evaluar_temporada(e3, 1)
    assert D.calif_dt(e3) == 50 + 8 + 10
    print("  test_catastrofico_despide_sin_segunda_oportunidad: OK")


def test_calif_escala_opciones_de_club():
    from alpha_football import directiva as D
    e = _estado()
    ovr = e['mi_equipo'].ovr_promedio
    e['datos_carrera']['calif_dt'] = 90
    alto = D.opciones_de_club(e)
    e['datos_carrera']['calif_dt'] = 10
    bajo = D.opciones_de_club(e)
    assert sum(o.ovr_promedio for o in alto) > sum(o.ovr_promedio for o in bajo)
    assert all(o.ovr_promedio >= ovr - 12 for o in alto)
    print("  test_calif_escala_opciones_de_club: OK")


def test_pedidos_de_la_directiva():
    from alpha_football import directiva as D
    e = _estado(); liga, mi = e['liga'], e['mi_equipo']
    def jugar_jornada(pts):
        p = next(p for p in liga.calendario if not p.jugado and mi.id in (p.local_id, p.visitante_id))
        p.jugado = True; mi.puntos += pts
        liga.jornada_actual = min(liga.num_jornadas, liga.jornada_actual + 1)
        D.revisar_pedido(e, rng=random.Random(3))
    jugar_jornada(3)
    p = D.pedido_activo(e)
    assert p and p['tipo'] in ('clasico', 'puntos', 'sub21')
    p.update(tipo='puntos', hasta=6, puntos_ini=mi.puntos)       # forzar el de puntos
    for pts in (3, 3, 0, 0, 3):
        jugar_jornada(pts)
    assert p['resuelto'] and p['cumplido'] and D.calif_dt(e) == 53
    # vencido sin resolver al cierre de la temporada = fallado
    e2 = _estado()
    e2['datos_carrera']['pedido'] = {'temporada': 1, 'tipo': 'clasico', 'texto': 'x', 'hasta': 99,
                                     'resuelto': False, 'creado_en': [1, 1]}
    D.cerrar_pedido_temporada(e2)
    assert e2['datos_carrera']['pedido']['resuelto'] and not e2['datos_carrera']['pedido']['cumplido']
    print("  test_pedidos_de_la_directiva: OK")
```

(Agrega `cerrar_pedido_temporada(estado)->None` a Produces: resuelve como fallado un pedido abierto; se llama en el cierre de temporada, Task 9.)

- [ ] **Step 3: Run** ambos archivos → FAIL.

- [ ] **Step 4: Implement en `directiva.py`**

Constantes: borrar `CONFIANZA_PERDON`; agregar

```python
CALIF_INICIAL = 50
CALIF = {'superado': 8, 'cumplido': 4, 'fallado': -8, 'liga': 10, 'copa': 12, 'descenso': -12,
         'despido': -10, 'pedido_ok': 3, 'pedido_mal': -4, 'clasico_perdido': -2}
PUESTOS_CATASTROFE = 4
PUNTOS_PEDIDO = 8
JORNADAS_PEDIDO = 5
```

Funciones:

```python
def calif_dt(estado: dict) -> int:
    return int(_dc(estado).get('calif_dt', CALIF_INICIAL))


def ajustar_calif(estado: dict, delta: int) -> int:
    _dc(estado)['calif_dt'] = max(0, min(100, calif_dt(estado) + int(delta)))
    return calif_dt(estado)


def _desciende(estado: dict, posicion: int) -> bool:
    liga = estado.get('liga')
    return getattr(liga, 'division', 1) == 1 and posicion >= len(getattr(liga, 'equipos', []) or []) - 1


def es_catastrofico(estado: dict, posicion: int, pos_max: int) -> bool:
    return _desciende(estado, posicion) or posicion - pos_max >= PUESTOS_CATASTROFE
```

`evaluar_temporada` — reemplazar el bloque `despido = False ... else: dc['confianza'] = ...` por:

```python
    from alpha_football import correo as C
    despido = False
    ajustar_calif(estado, CALIF[resultado])
    if posicion == 1:
        ajustar_calif(estado, CALIF['liga'])
    if estado.get('copa_mejor_fase_temp') == 'Campeón':
        ajustar_calif(estado, CALIF['copa'])
    if _desciende(estado, posicion):
        ajustar_calif(estado, CALIF['descenso'])
    if resultado == 'fallado':
        if es_catastrofico(estado, posicion, pos_max) or dc.get('advertencia_dt'):
            despido = True
            ajustar_calif(estado, CALIF['despido'])
        else:
            dc['advertencia_dt'] = True
            dc['confianza'] = CONFIANZA_TRAS_AVISO
            C.enviar(estado, 'directiva', "Advertencia: no cumpliste el objetivo",
                     f"Terminaste {posicion}º y te pedimos {obj.get('texto', 'el objetivo')}. "
                     "Te damos una segunda oportunidad: si vuelves a fallar, te despedimos.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
    else:
        dc['advertencia_dt'] = False
        dc['confianza'] = min(100, confianza(estado) + (15 if resultado == 'superado' else 8))
```

`actualizar_confianza`: al final, aviso por correo cuando cae bajo 40 (una vez por caída):

```python
    dc = _dc(estado)
    if dc['confianza'] < 40 and not dc.get('aviso_confianza'):
        dc['aviso_confianza'] = True
        from alpha_football import correo as C
        C.enviar(estado, 'directiva', "La directiva está preocupada",
                 f"La confianza cayó a {dc['confianza']}. Necesitamos resultados ya.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
    elif dc['confianza'] >= 40:
        dc['aviso_confianza'] = False
```

`opciones_de_club`: reemplazar el loop de márgenes por bandas según calificación:

```python
    c = calif_dt(estado)
    if c >= 70:
        bandas = [(ovr - 6, ovr + 3), (ovr - 12, ovr + 3), (-999, ovr + 3)]
    elif c >= 40:
        bandas = [(ovr - 12, ovr - 2), (ovr - 20, ovr - 2), (-999, ovr - 2)]
    else:
        bandas = [(ovr - 25, ovr - 8), (ovr - 35, ovr - 8), (-999, ovr - 2)]
    for lo, hi in bandas:
        banda = [(eq, t) for eq, t in todos if lo <= eq.ovr_promedio < hi]
        if len(banda) >= n:
            break
```

(mantener el fallback `if len(banda) < n:` existente).

`cambiar_de_club`: junto a `dc.pop('objetivo', None)` agregar `dc['advertencia_dt'] = False` y `dc.pop('pedido', None)`.

Pedidos:

```python
def pedido_activo(estado: dict) -> Optional[dict]:
    p = _dc(estado).get('pedido')
    return p if isinstance(p, dict) and not p.get('resuelto') else None


def _jugadas(liga, mi) -> int:
    return sum(1 for p in getattr(liga, 'calendario', []) or []
               if p.jugado and mi.id in (p.local_id, p.visitante_id))


def resolver_pedido(estado: dict, cumplido: bool) -> None:
    p = pedido_activo(estado)
    if not p:
        return
    from alpha_football import correo as C
    p['resuelto'], p['cumplido'] = True, bool(cumplido)
    ajustar_calif(estado, CALIF['pedido_ok'] if cumplido else CALIF['pedido_mal'])
    dc = _dc(estado)
    dc['confianza'] = max(0, min(100, confianza(estado) + (5 if cumplido else -5)))
    C.enviar(estado, 'directiva', ("Pedido cumplido: " if cumplido else "Pedido fallado: ") + p['texto'],
             "La directiva toma nota." + (" Bien hecho." if cumplido else " Esto baja tu calificación."),
             C.accion('objetivos_screen', "VER OBJETIVOS"))


def _crear_pedido(estado: dict, jugadas: int, azar: random.Random) -> None:
    liga, mi = estado['liga'], estado['mi_equipo']
    mitad = liga.num_jornadas // 2
    fin_mitad = mitad if jugadas < mitad else liga.num_jornadas
    opciones = []
    rival = getattr(mi, 'rival', '')
    riv = next((e for e in liga.equipos if e.nombre == rival), None)
    if riv is not None and any(not p.jugado and p.jornada <= fin_mitad and {p.local_id, p.visitante_id} == {mi.id, riv.id}
                               for p in liga.calendario):
        opciones.append(('clasico', f"Ganar el clásico contra {riv.nombre}", fin_mitad))
    if liga.num_jornadas - jugadas >= JORNADAS_PEDIDO:
        opciones.append(('puntos', f"Sumar {PUNTOS_PEDIDO} puntos en las próximas {JORNADAS_PEDIDO} jornadas",
                         jugadas + JORNADAS_PEDIDO))
        if any(int(j.edad) <= 21 for j in mi.jugadores):
            opciones.append(('sub21', f"Dar 3 partidos a un sub-21 en las próximas {JORNADAS_PEDIDO} jornadas",
                             jugadas + JORNADAS_PEDIDO))
    if not opciones:
        return
    tipo, texto, hasta = azar.choice(opciones)
    _dc(estado)['pedido'] = {
        'temporada': int(estado.get('temporada', 1) or 1), 'tipo': tipo, 'texto': texto, 'hasta': hasta,
        'puntos_ini': int(mi.puntos), 'pj_ini': {str(j.id): int(j.partidos_jugados) for j in mi.jugadores},
        'resuelto': False, 'cumplido': False, 'creado_en': [int(estado.get('temporada', 1) or 1), jugadas]}
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', f"Pedido de la directiva: {texto}",
             "Cumplirlo sube tu calificación de DT; fallarlo la baja.", C.accion('objetivos_screen', "VER OBJETIVOS"))


def revisar_pedido(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga: resuelve el pedido vencido y crea el de cada mitad."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return
        jugadas = _jugadas(liga, mi)
        p = pedido_activo(estado)
        if p and jugadas >= int(p.get('hasta', 99)):
            if p['tipo'] == 'puntos':
                resolver_pedido(estado, mi.puntos - int(p.get('puntos_ini', 0)) >= PUNTOS_PEDIDO)
            elif p['tipo'] == 'sub21':
                ini = p.get('pj_ini') or {}
                resolver_pedido(estado, any(int(j.edad) <= 21 and j.partidos_jugados - int(ini.get(str(j.id), j.partidos_jugados)) >= 3
                                            for j in mi.jugadores))
            else:
                resolver_pedido(estado, False)
        actual = _dc(estado).get('pedido') or {}
        clave = [int(estado.get('temporada', 1) or 1), jugadas]
        if jugadas in (1, liga.num_jornadas // 2) and actual.get('creado_en') != clave and not pedido_activo(estado):
            _crear_pedido(estado, jugadas, rng or random.Random())
    except Exception as e:
        logger.error(f"Error al revisar el pedido de la directiva: {e}")


def cerrar_pedido_temporada(estado: dict) -> None:
    if pedido_activo(estado):
        resolver_pedido(estado, False)
```

- [ ] **Step 5: Run** `tests/test_directiva_v280.py` → 7/7; `tests/test_vestuario_v310.py` → 19/19.

---

### Task 8: Pago de cláusulas por la IA

**Files:**
- Modify: `alpha_football/mercado_ia.py` (nueva `pago_clausulas`)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `finanzas.quitar_de_plantilla`, `finanzas.registrar`, `finanzas.PLANTILLA_MINIMA`, `negociacion.registrar_pase`, `market.registrar_region_jugador`, `correo`.
- Produces: `pago_clausulas(estado, rng=None, prob=0.10)->dict|None` (`{'jugador', 'comprador', 'monto', 'rechazo': bool}`).

- [ ] **Step 1: Failing test**

```python
def test_pago_de_clausulas():
    from alpha_football import mercado_ia as M, correo as C
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores: j.clausula = 0
    barato = max(mi.jugadores, key=lambda j: j.overall)
    barato.clausula, barato.personalidad, barato.moral = 1_000_000, 'mercenario', 90
    ok = []
    for s in range(400):
        h = M.pago_clausulas(e, rng=random.Random(s))
        if h:
            assert h['jugador'] is barato and not h['rechazo']
            assert barato not in mi.jugadores and barato in h['comprador'].jugadores
            ok.append(h)
            h['comprador'].jugadores.remove(barato); mi.jugadores.append(barato)   # volver a probar
    assert 0.06 < len(ok) / 400 < 0.14, len(ok)
    assert any('cláusula' in m['asunto'].lower() for m in C.bandeja(e))
    assert any(h.get('propio') and h['monto'] == 1_000_000 for h in e['datos_carrera']['historial_pases'])
    # plantilla corta: nadie paga
    e2 = _estado(); mi2 = e2['mi_equipo']
    mi2.jugadores[:] = mi2.jugadores[:18]
    for j in mi2.jugadores: j.clausula = 1
    assert all(M.pago_clausulas(e2, rng=random.Random(s), prob=1.0) is None for s in range(20))
    print("  test_pago_de_clausulas: OK")
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement en `mercado_ia.py`**

```python
PROB_CLAUSULA = 0.10          # v3.1.0: por jornada con la ventana abierta
PROB_NEGATIVA = 0.40


def pago_clausulas(estado: dict, rng: Optional[random.Random] = None, prob: float = PROB_CLAUSULA) -> Optional[dict]:
    """Un club de 1ª de la IA paga la cláusula de un jugador del user (el user no puede negarse)."""
    try:
        from alpha_football import correo as C
        from alpha_football.finanzas import quitar_de_plantilla, registrar, PLANTILLA_MINIMA
        azar = rng or random.Random()
        mi = estado.get('mi_equipo')
        if mi is None or azar.random() > prob or len(mi.jugadores) <= PLANTILLA_MINIMA:
            return None
        compradores = [(eq, tipo) for tipo, liga in (estado.get('primera_division') or {}).items()
                       if liga is not None for eq in liga.equipos if eq is not mi and eq.id != mi.id]
        cands = []
        for j in mi.jugadores:
            c = int(getattr(j, 'clausula', 0) or 0)
            ricos = [(eq, t) for eq, t in compradores if c > 0 and eq.balance >= c]
            if ricos:
                cands.append((j, c, ricos))
        if not cands:
            return None
        j, c, ricos = azar.choices(cands, weights=[j.overall / max(0.1, c / 1_000_000) for j, c, _ in cands])[0]
        comprador, tipo_c = azar.choices(ricos, weights=[1.5 if eq.ovr_promedio > mi.ovr_promedio else 1.0
                                                         for eq, _ in ricos])[0]
        if (j.personalidad != 'mercenario' and j.moral >= 70 and comprador.ovr_promedio < mi.ovr_promedio
                and azar.random() < PROB_NEGATIVA):
            j.moral = min(100, j.moral + 5)
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} rechazó irse a {comprador.nombre}",
                     f"{comprador.nombre} pagó su cláusula (${c:,}) pero él prefiere quedarse.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
            return {'jugador': j, 'comprador': comprador, 'monto': c, 'rechazo': True}
        from alpha_football.market import registrar_region_jugador
        from alpha_football.negociacion import registrar_pase
        comprador.balance -= c
        mi.balance += c
        quitar_de_plantilla(mi, j)
        comprador.jugadores.append(j)
        comprador.alineacion_activa = None
        j.transferible = j.pide_salir = False
        registrar_region_jugador(j, tipo_c)
        registrar_pase(estado, j, mi.nombre, comprador.nombre, c, True)
        registrar(estado, 'ventas', c)
        C.enviar(estado, 'club', f"{comprador.nombre} pagó la cláusula de {j.nombre} {j.apellido}",
                 f"Se va por ${c:,}. El dinero ya está en tu presupuesto.",
                 C.accion('historial_pases_screen', "VER HISTORIAL"))
        return {'jugador': j, 'comprador': comprador, 'monto': c, 'rechazo': False}
    except Exception as e:
        logger.error(f"Error en el pago de cláusulas de la IA: {e}")
        return None
```

- [ ] **Step 4: Run** → 20/20.

---

### Task 9: Integración — cierres de partido y de jornada

**Files:**
- Modify: `alpha_football/vestuario.py` (nueva `post_partido_user`)
- Modify: `alpha_football/ui/prepartido_screen.py` (`_simular_instantaneo`)
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga`, las 4 llamadas a `simular_rango`, bloque `sim_desarrollo_done`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py` (`avanzar_nueva_temporada`, junto a `evaluar_temporada`)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: `vestuario.post_partido_user(estado, user_eq, rival, gf:int, gc:int, reporte:list, minutos:dict[int,int], rng=None)->list` (incidencias del user); `match_screen._minutos_previos(estado, user_eq, user_alin)->dict`.

- [ ] **Step 1: Failing tests**

```python
def test_simulacion_instantanea_aplica_vestuario():
    from alpha_football.ui import prepartido_screen
    from alpha_football import correo as C
    e = _estado(); liga, mi = e['liga'], e['mi_equipo']
    liga.jornada_actual = 1
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    e['partido_actual'], e['match_mode'] = p, 'liga'
    local = next(x for x in liga.equipos if x.id == p.local_id)
    visit = next(x for x in liga.equipos if x.id == p.visitante_id)
    for j in mi.jugadores: j.energia = 100
    once_ids = {mi.jugadores[i].id for i in mi.alineacion_activa.titulares}
    prepartido_screen._simular_instantaneo(e, local, visit)
    gastaron = [j for j in mi.jugadores if j.id in once_ids]
    assert all(j.energia < 100 or j.lesion_partidos for j in gastaron)   # gastó y luego recuperó (< 100)
    assert all(j.energia == 100 for j in mi.jugadores if j.id not in once_ids)
    assert len(e['datos_carrera'].get('racha', [])) == 1          # el hook de vestuario corrió una vez
    print("  test_simulacion_instantanea_aplica_vestuario: OK")


def test_amistoso_sin_consecuencias():
    from alpha_football.ui import prepartido_screen
    e = _estado(); a, b = e['liga'].equipos[0], e['liga'].equipos[1]
    e['match_mode'], e['amis_local'], e['amis_visitante'] = 'amistoso', a, b
    for j in a.jugadores + b.jugadores: j.energia, j.moral = 100, 70
    prepartido_screen._simular_instantaneo(e, a, b)
    assert all(j.energia == 100 and j.moral == 70 for j in a.jugadores + b.jugadores)
    assert not (e['datos_carrera'].get('correo'))
    print("  test_amistoso_sin_consecuencias: OK")


def test_lesion_del_user_llega_al_correo():
    from alpha_football import vestuario as V, correo as C, energia as Ener
    e = _estado(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    orig = Ener.PROB_LESION_90
    Ener.PROB_LESION_90 = 1.0
    try:
        V.post_partido_user(e, mi, rival, 1, 0, [], {mi.jugadores[0].id: 90}, rng=random.Random(1))
    finally:
        Ener.PROB_LESION_90 = orig
    assert mi.jugadores[0].lesion_partidos > 0
    assert any(x['remitente'] == 'medico' and x['accion']['pantalla'] == 'team_screen' for x in C.bandeja(e))
    print("  test_lesion_del_user_llega_al_correo: OK")
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `vestuario.post_partido_user`**

```python
def post_partido_user(estado: dict, user_eq, rival, gf: int, gc: int, reporte: list, minutos: dict,
                      rng: Optional[random.Random] = None) -> list:
    """
    Cierre del partido del user (liga o copa, vivo o instantáneo): físico de ambos equipos,
    lesiones/sanciones por correo, moral, clásico y rachas. Nunca en amistosos.
    """
    from alpha_football import energia as E, correo as C, directiva as D
    from alpha_football.data.clasicos import es_clasico
    from alpha_football.engine import _once_titular
    azar = rng or random.Random()
    incid = []
    try:
        incid = E.cerrar_partido(user_eq, minutos, rng=azar)
        E.cerrar_partido(rival, {j.id: 90 for j in _once_titular(rival)}, rng=azar)
        for inc in incid:
            j = inc['jugador']
            if inc['tipo'] == 'lesion':
                C.enviar(estado, 'medico', f"Lesión: {j.nombre} {j.apellido}",
                         f"Estará fuera {inc['partidos']} partido(s).", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
            else:
                C.enviar(estado, 'club', f"Suspensión: {j.nombre} {j.apellido}",
                         f"Expulsado: se pierde {inc['partidos']} partido(s).", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
        clasico = es_clasico(user_eq, rival)
        jugaron = {jid for jid, m in minutos.items() if int(m or 0) > 0}
        res = actualizar_moral(user_eq, reporte, gf, gc, clasico, jugaron, rng=azar)
        for j in res['quejas']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} está molesto",
                     f"Su moral bajó a {j.moral}. Minutos, contrato o forma: algo no le gusta.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        for j in res['pide_salir']:
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} quiere irse",
                     "Lleva semanas descontento y pide salir. Atraerá ofertas como un transferible.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
        dc = estado.setdefault('datos_carrera', {})
        if clasico:
            dc['confianza'] = max(0, min(100, D.confianza(estado) + (6 if gf > gc else -6 if gf < gc else 0)))
            if gf > gc:
                C.enviar(estado, 'directiva', f"¡Ganaste el clásico a {rival.nombre}!", "La afición y la directiva lo celebran.")
            elif gf < gc:
                D.ajustar_calif(estado, D.CALIF['clasico_perdido'])
            p = D.pedido_activo(estado)
            if p and p.get('tipo') == 'clasico' and rival.nombre in p.get('texto', ''):
                D.resolver_pedido(estado, gf > gc)
        racha = (list(dc.get('racha', [])) + ['G' if gf > gc else 'P' if gf < gc else 'E'])[-3:]
        dc['racha'] = racha
        if racha == ['G'] * 3:
            C.enviar(estado, 'directiva', "Tres victorias seguidas", "La directiva felicita al cuerpo técnico.")
            dc['racha'] = []
        elif racha == ['P'] * 3:
            C.enviar(estado, 'directiva', "Advertencia: tres derrotas seguidas", "Esperamos una reacción inmediata.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
            dc['racha'] = []
    except Exception as e:
        logger.error(f"Error en el cierre de vestuario del partido: {e}")
    return incid
```

- [ ] **Step 4: Enchufar en `prepartido_screen._simular_instantaneo`**
  - Llamada al motor: `res = simular_partido(local, visitante, aplicar_fisico=False, **_ments(local, visitante, user_eq))`.
  - Justo después: `minutos_user = {j.id: 90 for j in _once_titular(user_eq)}` (import `from alpha_football.engine import _once_titular`) — calcular **antes** de cualquier cierre.
  - Rama liga: mover `user_is_local = (mi_equipo.id == local.id)` fuera del `try` de desarrollo (hoy vive adentro), capturar `rep = desarrollar_plantilla_post_partido(mi_equipo, gf, gc)` (hoy se descarta) y, antes de `finalizar_jornada_liga(...)`:
    ```python
            try:  # v3.1.0: físico, moral, correo del partido del user
                from alpha_football.vestuario import post_partido_user
                post_partido_user(estado, mi_equipo, visitante if user_is_local else local, gf, gc, rep or [], minutos_user)
            except Exception as e_ves:
                logger.error(f"Error de vestuario en sim instantánea de liga: {e_ves}")
    ```
    (declarar `rep = []` antes del `try` de desarrollo).
  - Rama copa: tras el desarrollo de ambos, con `user_is_local = mi_equipo.id == local.id`:
    ```python
            try:
                from alpha_football.vestuario import post_partido_user
                post_partido_user(estado, mi_equipo, visitante if user_is_local else local,
                                  gl if user_is_local else gv, gv if user_is_local else gl,
                                  (rep_l if user_is_local else rep_v) or [], minutos_user)
            except Exception as e_ves:
                logger.error(f"Error de vestuario en sim instantánea de copa: {e_ves}")
    ```
    (declarar `rep_l = rep_v = []` antes del `try`).
  - Amistoso: sin hook (el `aplicar_fisico=False` ya evita el gasto).

- [ ] **Step 5: Enchufar en `match_screen`**
  - Helper nuevo (junto a `_ments`):
    ```python
    def _minutos_previos(estado: dict, user_eq: Any, user_alin: Any) -> dict:
        """v3.1.0: {id(jugador): minutos ya jugados} de los titulares actuales del user."""
        mins = estado.get('sim_minuto_por_jugador') or {}
        js = list(getattr(user_eq, 'jugadores', []) or [])
        return {id(js[i]): int(mins.get(js[i].id, 0)) for i in (getattr(user_alin, 'titulares', []) or [])
                if 0 <= i < len(js)}
    ```
  - En las 4 llamadas a `simular_rango(...)` (líneas ~566, ~731, ~1171, ~1190/~1203) agregar
    `minutos_previos=_minutos_previos(estado, user_eq, user_alin)` (en `_cambiar_mentalidad_en_vivo` usar su `user_eq` y `getattr(user_eq, 'alineacion_activa', None)`).
  - Bloque `sim_desarrollo_done`, tras `estado['sim_desarrollo'] = ...` (solo liga/copa, ya excluye amistoso):
    ```python
                        try:  # v3.1.0: físico, moral y correo del partido del user
                            from alpha_football.vestuario import post_partido_user
                            post_partido_user(estado, mi_equipo, visitante if user_is_local else local,
                                              goles_l if user_is_local else goles_v,
                                              goles_v if user_is_local else goles_l,
                                              estado['sim_desarrollo'] or [],
                                              dict(estado.get('sim_minuto_por_jugador') or {}))
                        except Exception as e_ves:
                            logger.error(f"Error de vestuario tras el partido en vivo: {e_ves}")
    ```
  - `finalizar_jornada_liga`: al final del `try` principal (tras las ofertas):
    ```python
        try:  # v3.1.0: recuperación física de todos, pedidos de la directiva y cláusulas
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado)
            from alpha_football.directiva import revisar_pedido
            revisar_pedido(estado)
            from alpha_football import market as _mk2
            if _mk2.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
                from alpha_football.mercado_ia import pago_clausulas
                pago_clausulas(estado)
        except Exception as e_v31:
            logger.error(f"Error en el cierre de jornada v3.1.0: {e_v31}")
    ```
    y en los dos `append` de ofertas, correo:
    ```python
                    from alpha_football import correo as C
                    jo = oferta_ia['jugador']
                    C.enviar(estado, 'club', f"Oferta por {jo.nombre} {jo.apellido}",
                             f"{oferta_ia['comprador'].nombre} ofrece ${int(oferta_ia['monto']):,}.",
                             C.accion('ofertas_screen', "VER OFERTAS"))
    ```
    (igual para `oferta_ext`, asunto "Oferta del exterior por ...").
  - Pide salir cuenta como transferible: en `market.crear_oferta_ui`, la lista `transferibles` usa
    `getattr(j, "transferible", False) or getattr(j, "pide_salir", False)`.
- [ ] **Step 6: Cierre de temporada** en `resumen_temporada_screen.avanzar_nueva_temporada`, justo **antes** del `try` de `evaluar_temporada`:
    ```python
            try:  # v3.1.0: pedido abierto = fallado; bonus de potencial por moral
                from alpha_football.directiva import cerrar_pedido_temporada
                cerrar_pedido_temporada(estado)
                from alpha_football.vestuario import cierre_temporada as _cierre_vestuario
                _cierre_vestuario(estado)
            except Exception as e_v31:
                logger.error(f"Error en el cierre de temporada v3.1.0: {e_v31}")
    ```
- [ ] **Step 7: Run** `tests/test_vestuario_v310.py` → 23/23; suite completa sin regresiones (en especial `test_hub_v240`, `test_mentalidad_v250`, `test_integridad_v300`, `test_finanzas_v290`, `test_integracion_v290`).

---

### Task 10: UI — correo, energía, personalidad, calificación, clásico

**Files:**
- Create: `alpha_football/ui/correo_screen.py`
- Modify: `alpha_football/ui/league_screen.py` (`TARJETAS['oficina']`, `_alertas_inicio`, panel TU CLUB), `main.py` (registrar pantalla), `alpha_football/ui/team_screen.py` (`_dibujar_tarjeta`, ficha), `alpha_football/ui/plantilla_screen.py` (`_dibujar_ficha`), `alpha_football/ui/prepartido_screen.py` (aviso cansados + CLÁSICO), `alpha_football/ui/objetivos_screen.py` (calificación, advertencia, pedido)
- Test: `tests/test_vestuario_v310.py`

**Interfaces:**
- Consumes: `correo.*`, `directiva.calif_dt/pedido_activo`, `energia.energia_en_minuto/energia_actual`, `clasicos.es_clasico`, `league_screen._abrir`.
- Produces: `correo_screen.render(screen, estado)->Optional[str]`, `correo_screen._rect_accion()->pygame.Rect`, `correo_screen._rect_fila(i)->pygame.Rect`.

- [ ] **Step 1: Failing test**

```python
def test_pantallas_v310():
    from alpha_football.ui import correo_screen, league_screen, team_screen, plantilla_screen, objetivos_screen
    from alpha_football import correo as C
    assert league_screen.TARJETAS['oficina'][0][2] == 'correo_screen'
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    assert "'correo_screen': correo_render" in src
    e = _estado()
    C.enviar(e, 'medico', "Lesión: X", "2 partidos", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
    pygame.event.clear()
    assert correo_screen.render(screen, e) is None and C.no_leidos(e) == 0     # abrir = leído (el 1º)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=correo_screen._rect_accion().center))
    assert correo_screen.render(screen, e) == 'team_screen' and e['team_contexto'] == 'carrera'
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
    assert correo_screen.render(screen, e) == 'league_screen'
    C.enviar(e, 'club', "Oferta", "")
    assert any('correo' in t.lower() for t, _c in league_screen._alertas_inicio(e, e['mi_equipo']))
    for mod in (plantilla_screen, objetivos_screen):
        pygame.event.clear(); assert mod.render(screen, e) is None
    print("  test_pantallas_v310: OK")
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement `ui/correo_screen.py`**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo (v3.1.0). OFICINA > CORREO.
Lista a la izquierda (no leídos en dorado), mensaje a la derecha y botón de acción que lleva a
la pantalla donde se resuelve. Teclado: ↑/↓ elegir, Enter = acción, Esc = volver.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    COLORS = {'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import correo as C

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 76, 560, 628)
R_MSG = pygame.Rect(588, 76, 676, 628)
ALTO_FILA = 44
FILAS = (R_LISTA.height - 16) // ALTO_FILA


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(R_LISTA.x + 8, R_LISTA.y + 8 + i * ALTO_FILA, R_LISTA.width - 16, ALTO_FILA - 4)


def _rect_accion() -> pygame.Rect:
    return pygame.Rect(R_MSG.x + 20, R_MSG.bottom - 70, 360, 50)


def _envolver(texto: str, ancho_px: int, size: str = 'sm') -> list:
    fuente, lineas, linea = get_font(size), [], ""
    for palabra in str(texto).split():
        prueba = (linea + " " + palabra).strip()
        if fuente.size(prueba)[0] > ancho_px and linea:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    return lineas + ([linea] if linea else [])


def _ir(estado: dict, msg: dict) -> Optional[str]:
    acc = msg.get('accion') or {}
    if not acc.get('pantalla'):
        return None
    from alpha_football.ui.league_screen import _abrir
    return _abrir(estado, acc['pantalla'])


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mensajes = C.bandeja(estado)
        sel = max(0, min(int(estado.get('correo_sel', 0) or 0), len(mensajes) - 1))
        mouse_pos = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key == pygame.K_DOWN:
                    sel = min(len(mensajes) - 1, sel + 1)
                elif ev.key == pygame.K_UP:
                    sel = max(0, sel - 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and mensajes:
                    destino = _ir(estado, mensajes[sel])
                    if destino:
                        return destino
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
        inicio = max(0, sel - FILAS + 1)
        if click:
            if _volver().collidepoint(click):
                return 'league_screen'
            for i in range(min(FILAS, len(mensajes) - inicio)):
                if _rect_fila(i).collidepoint(click):
                    sel = inicio + i
            if mensajes and _rect_accion().collidepoint(click):
                destino = _ir(estado, mensajes[sel])
                if destino:
                    return destino
        estado['correo_sel'] = sel
        if mensajes:
            C.marcar_leido(estado, mensajes[sel]['id'])

        draw_gradient_bg(screen)
        draw_text(screen, "CORREO", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{len(mensajes)} mensajes  ·  {C.no_leidos(estado)} sin leer  ·  ↑/↓ elegir · Enter acción · Esc volver",
                  (16, 48), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        draw_panel(screen, R_LISTA)
        draw_panel(screen, R_MSG)
        if not mensajes:
            draw_text(screen, "No tienes mensajes.", (R_LISTA.x + 20, R_LISTA.y + 20), size='sm', color='blanco')
            return None
        for i, m in enumerate(mensajes[inicio:inicio + FILAS]):
            r = _rect_fila(i)
            if inicio + i == sel:
                pygame.draw.rect(screen, (40, 60, 95), r, border_radius=6)
            col = 'dorado' if not m.get('leido') else 'blanco'
            draw_text(screen, f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  T{m['temporada']} J{m['jornada']}",
                      (r.x + 8, r.y + 2), size='sm', color='azul', shadow=False)
            draw_text(screen, m['asunto'][:52], (r.x + 8, r.y + 20), size='sm', color=col, shadow=False)
        m = mensajes[sel]
        x, y = R_MSG.x + 20, R_MSG.y + 16
        draw_text(screen, C.REMITENTES.get(m['remitente'], m['remitente']), (x, y), size='sm', color='azul')
        for k, linea in enumerate(_envolver(m['asunto'], R_MSG.width - 40, 'md')[:2]):
            draw_text(screen, linea, (x, y + 26 + k * 30), size='md', color='dorado')
        for k, linea in enumerate(_envolver(m['cuerpo'], R_MSG.width - 40)[:14]):
            draw_text(screen, linea, (x, y + 100 + k * 26), size='sm', color='blanco')
        acc = m.get('accion') or {}
        if acc.get('pantalla'):
            draw_button(screen, _rect_accion(), acc.get('texto', 'IR'), _rect_accion().collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en correo_screen: {e}", exc_info=True)
        return 'league_screen'
```

- [ ] **Step 4: Resto de la UI**
  - `league_screen.TARJETAS['oficina']`: insertar primero `("CORREO", "Mensajes de la directiva, jugadores y clubes", 'correo_screen')`. En `_render_tarjetas`, para `destino == 'correo_screen'` con no leídos, subtítulo `f"{n} sin leer"` en dorado (usar `correo.no_leidos`).
  - `_alertas_inicio`: antes del recorte `avisos = avisos[:2 if n else 3]`, si `no_leidos > 0` insertar al principio `(f"{k} correo{'s' if k != 1 else ''} sin leer (OFICINA > CORREO)", 'dorado')`.
  - Panel TU CLUB: agregar tras la línea de OVR/Presupuesto `draw_text(screen, f"Calificación DT {calif_dt(estado)}/100", (cx0, cy0 + 112), size='sm', color='azul')` (ajustar la `y` de la línea de objetivo que sigue si se superpone; verificar con captura).
  - `main.py`: junto a los imports de `objetivos_screen`: `from alpha_football.ui.correo_screen import render as correo_render` y en el mapa `'correo_screen': correo_render,`.
  - `team_screen._dibujar_tarjeta(..., energia=None)`: bajo la línea de moral, barra de energía de `rect.width − 16` px, alto 5, en `rect.y + rect.height − 9`: verde ≥ 60, dorado ≥ 30, rojo < 30; `energia` por defecto `E.energia_actual(j)`. En las llamadas del modo partido (hay `sim_minuto_por_jugador` en `estado`), pasar `E.energia_en_minuto(j, estado['sim_minuto_por_jugador'].get(j.id, 0))`. En la ficha (`("Moral", ...)` ~línea 530) agregar filas `("Resistencia", j.resistencia)`, `("Energía", int(E.energia_actual(j)))` y el texto `Personalidad: <nombre>`.
  - `plantilla_screen._dibujar_ficha`: línea `f"Energía {int(j.energia)}  ·  Resistencia {j.resistencia}  ·  {PERSONALIDAD_TXT[j.personalidad]}"` y, si `j.pide_salir`, `"PIDE SALIR"` en rojo. `PERSONALIDAD_TXT = {'normal': "Normal", 'lider': "Líder", 'profesional': "Profesional", 'polemico': "Polémico", 'mercenario': "Mercenario"}` en `vestuario.py`.
  - `prepartido_screen.render`: bajo el cartel, si `es_clasico(local, visitante)` → `"CLÁSICO"` en rojo centrado; si hay titulares del user con energía < 60 → `f"{n} titulares cansados (energía < 60): {apellidos[:3]}"` en dorado.
  - `objetivos_screen`: reemplazar la 3ª línea de `lineas` por `("Si fallas: −20% y " + ("TE ECHAN (ya tenías advertencia)" if dc.get('advertencia_dt') else "advertencia (segunda oportunidad)") + "; descender o quedar 4+ puestos abajo = despido", 'rojo')`. Quitar la marca blanca de `CONFIANZA_PERDON`. En el panel de confianza, agregar `Calificación DT: {calif}/100` (lg) y el pedido activo: `Pedido: {texto} (hasta J{hasta})` o `"Sin pedido activo"`.
- [ ] **Step 5: Capturas** con un script de scratchpad (como `shots_fin.py`) para `correo_screen`, `league_screen` (Inicio y OFICINA), `team_screen`, `plantilla_screen`, `objetivos_screen` y `prepartido_screen`; revisar que no haya superposiciones.
- [ ] **Step 6: Run** suite completa → todo verde. Actualizar `context.md` (bitácora v3.1.0, fecha).

---

## Self-review (hecho)

- Cobertura del spec: A correo (T4, T9, T10), A2 cláusulas (T8), B moral (T2, T6, T9), C energía/resistencia/lesiones (T1-T3, T9, T10), D personalidades/clásicos (T2, T5, T6), E calificación/pedidos/segunda oportunidad (T7, T9, T10), migración (T2, T5), balance (T2 step 4, T3 step 4).
- Nombres consistentes: `post_partido_user`, `actualizar_moral`, `cerrar_partido`, `recuperar_todos`, `revisar_pedido`, `cerrar_pedido_temporada`, `pago_clausulas`, `calif_dt`, `ajustar_calif`, `es_clasico`, `asignar_rivales`.
