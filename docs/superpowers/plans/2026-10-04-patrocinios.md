# Patrocinios (v4.9.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el patrocinio plano por hasta 3 contratos con marcas parodia (camiseta, manga, estadio), con fijo, bono, objetivo, años, ofertas al vencer, negociación, prima, rescisión y reputación comercial; y que el patrocinio pese más en los ingresos.

**Architecture:** Módulo nuevo de lógica pura `alpha_football/patrocinios.py` con el estado en `datos_carrera['patrocinios']` (dicts JSON). `finanzas.procesar_jornada` cobra los contratos en vez de la fórmula. El ciclo de temporada tiene tres enganches porque los datos están disponibles en momentos distintos: evaluación de objetivos (con la tabla final aún intacta), cláusula de división (tras el swap de ascensos) y vencimiento + ofertas (en el cierre financiero). Pantalla nueva `ui/patrocinios_screen.py` en la pestaña Finanzas.

**Tech Stack:** Python 3, pygame, tests como scripts (`python tests/test_x.py`, lista `TESTS`).

**Spec:** `docs/superpowers/specs/2026-10-04-patrocinios-design.md`

**Bloques de código:** cada bloque va precedido de `<!-- bloque: ID -->`. Los pasos dicen a qué archivo va cada bloque (crear o añadir al final).

## Global Constraints

- `PATROCINIO_FRAC = 0.55`, `TAQUILLA_FRAC = 0.35` (suma 0.90: `ingresos_esperados` no cambia).
- Espacios y pesos: camiseta 0.50, manga 0.30, estadio 0.20.
- Perfiles (fijo, bono, dificultad): conservadora (1.00, 0.10, fácil), equilibrada (0.90, 0.25, media), ambiciosa (0.75, 0.50, difícil).
- Reputación 0–100, inicial 50: cumple +6, falla −5, título (1ª) +8, ascenso +8, descenso −10, quiebra −15, rescisión −8. Multiplicador de ofertas: 0 → ×0.80, 50 → ×1.00, 100 → ×1.30.
- Renovación: +10% a +20% de fijo, solo con `cumplido_ultima is True`. Ofertas nuevas: 2 por espacio, ±5%.
- Sin interesados: reputación < 15 → cada marca nueva 50% de no presentarse.
- Negociar: nivel 1 = +10% (60%), nivel 2 = +20% (30%); ±0.3 puntos por punto de reputación sobre/bajo 50; acotado a 5%–90%; una vez por oferta.
- Prima: 30% de un año al contado, fijo ×0.88. Rescisión: multa 50% del fijo restante.
- Cláusulas: descenso ×0.60, ascenso ×1.30 (fijo y bono). Invierno: ofertas ×0.85.
- La IA no tiene contratos. `ingresos_esperados` y el tope salarial no dependen de los contratos.
- Un fallo en patrocinios nunca deja al club sin cobrar la jornada: `procesar_jornada` cae a la fórmula.
- Git: commits solo si Diego lo pide; nunca atribución a IA. Edit parcial en archivos existentes.

## Review Focus

1. **Dos espacios vacíos con ofertas del mismo rubro:** firmar la segunda debe rechazarse por exclusividad (Task 2: `test_firmar_exclusividad`).
2. **Doble evaluación del cierre** (el resumen de temporada puede re-ejecutarse): el bono no se paga dos veces (Task 3: `test_evaluar_temporada_bonos_y_reputacion`).
3. **Objetivo de copa en una temporada sin copa:** ni bono ni castigo, y no habilita renovación (Task 1: `test_objetivos_cumple_y_progreso`; Task 3).
4. **Rescindir sin saldo para la multa:** se rechaza y el contrato sigue (Task 2: `test_rescindir`).
5. **Estado corrupto, de otro club o partida vieja:** se regenera con 3 contratos, sin excepción (Task 1: `test_contratos_iniciales`).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/patrocinios.py` (crear) | Estado, marcas, contratos, objetivos, cobro, ofertas, acciones, ciclo de temporada, correos. |
| `alpha_football/finanzas.py` (modificar) | Fracciones; `procesar_jornada` cobra contratos; `cierre_temporada` llama al vencimiento. |
| `alpha_football/correo.py` (modificar) | Remitente y firma `'patrocinador'`. |
| `alpha_football/ui/resumen_temporada_screen.py` (modificar) | Enganches de evaluación y de división. |
| `alpha_football/ui/match_screen.py` (modificar) | Enganche de jornada (ventanas). |
| `alpha_football/ui/patrocinios_screen.py` (crear) | Pantalla. |
| `alpha_football/ui/league_screen.py`, `main.py`, `ui/ayuda.py`, `ui/atajos.py`, `ui/finanzas_screen.py` (modificar) | Tarjeta, registro, ayuda, atajos, estimado por jornada. |
| `tests/test_patrocinios.py` (crear) | Tests de la feature. |
| `tests/test_finanzas_v460.py`, `tests/test_hub_v240.py` (modificar) | Expectativas que cambian. |

---

### Task 1: Núcleo — estado, contratos iniciales, objetivos y cobro

**Files:**
- Create: `alpha_football/patrocinios.py` (bloque `T1-impl`)
- Create: `tests/test_patrocinios.py` (bloque `T1-test`)
- Modify: `alpha_football/finanzas.py:32-33` y `:293`
- Modify: `tests/test_finanzas_v460.py:37`

**Interfaces:**
- Consumes: `finanzas.base_ingresos(equipo, tipo, division)`, `finanzas.PATROCINIO_FRAC`, `market.nivel_club`, `ui.postpartido.posicion_liga(liga, equipo_id)`, `directiva._indice_fase_copa(fase)`, `competiciones.tipo_copa_user(estado)`.
- Produces: `patrocinios.datos(estado) -> dict`, `valor_referencia(estado, espacio) -> int`, `crear_objetivo(estado, dificultad, rng, tipo=None) -> dict`, `cumple(estado, contrato, posicion=None) -> bool|None`, `progreso(estado, contrato) -> float`, `cobro_jornada(estado) -> int`, `ingreso_anual(estado) -> int`, `mult_reputacion(rep) -> float`, `_crear_contrato(estado, marca, espacio, rng, anios, mult=1.0, fijo=None) -> dict`, `_rep(p, delta)`, `_m(v) -> str`, constantes `ESPACIOS`, `NOMBRE_ESPACIO`, `PERFILES`, `MARCAS`.

- [ ] **Step 1: Crear `tests/test_patrocinios.py` con el bloque `T1-test`**

<!-- bloque: T1-test -->
```python
"""Patrocinios v4.9.0: contratos, objetivos, ofertas, acciones, ciclo de temporada, pantalla."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(49)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, patrocinios as P, finanzas as F, correo as C
from alpha_football.models import Partido
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _base(e):
    liga = e['liga']
    return F.base_ingresos(e['mi_equipo'], liga.tipo, liga.division)


def _obj(tipo, meta):
    return {'tipo': tipo, 'meta': meta, 'texto': f"{tipo} {meta}"}


def test_fracciones_y_ingresos_esperados():
    e = estado_carrera(); liga = e['liga']; base = _base(e)
    assert F.PATROCINIO_FRAC == 0.55 and F.TAQUILLA_FRAC == 0.35
    esperados = F.ingresos_esperados(e['mi_equipo'], liga.tipo, liga.division)
    assert esperados == int(base * 0.55) + int(base * 0.35)
    assert abs(esperados - int(base * 0.90)) <= 1                      # el total no cambió
    print("  test_fracciones_y_ingresos_esperados: OK")


def test_contratos_iniciales():
    e = estado_carrera(); p = P.datos(e)
    cs = p['contratos']
    assert set(cs) == {'camiseta', 'manga', 'estadio'} and all(cs.values())
    assert len({c['rubro'] for c in cs.values()}) == 3 and p['reputacion'] == 50
    for espacio, c in cs.items():
        f_fijo, f_bono, _d = P.PERFILES[c['perfil']]
        ref = P.valor_referencia(e, espacio)
        assert 1 <= c['anios'] <= 3 and c['espacio'] == espacio
        assert c['fijo'] == int(ref * f_fijo) and c['bono'] == int(ref * f_bono)
        assert c['objetivo']['texto'] and c['cumplido_ultima'] is None
    total_ref = sum(P.valor_referencia(e, esp) for esp, _w in P.ESPACIOS)
    assert abs(total_ref - int(_base(e) * F.PATROCINIO_FRAC)) <= 3     # referencia = patrocinio de fórmula
    assert P.datos(e) is p                                             # estable entre llamadas
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))    # ida y vuelta como el guardado
    assert P.datos(e)['contratos'] == cs
    for basura in ("x", {'club': e['mi_equipo'].nombre}, {'club': e['mi_equipo'].nombre, 'contratos': {'camiseta': 3}}):
        e['datos_carrera']['patrocinios'] = basura                     # corrupto → se regenera
        assert all(P.datos(e)['contratos'].values())
    e['mi_equipo'] = e['liga'].equipos[1]                              # cambio de club
    p2 = P.datos(e)
    assert p2['club'] == e['mi_equipo'].nombre and p2['reputacion'] == 50 and all(p2['contratos'].values())
    print("  test_contratos_iniciales: OK")


def test_cobro_jornada():
    e = estado_carrera(); mi = e['mi_equipo']; n = e['liga'].num_jornadas
    cs = P.datos(e)['contratos']
    assert P.cobro_jornada(e) == sum(c['fijo'] // n for c in cs.values())
    assert P.ingreso_anual(e) == sum(c['fijo'] for c in cs.values())
    bal = mi.balance
    mov = F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert mov['patrocinio'] == P.cobro_jornada(e) and mi.balance == bal + mov['patrocinio'] - mov['salarios']
    assert F.libro(e)['patrocinio'] == mov['patrocinio']
    cs['manga'] = cs['estadio'] = None
    assert P.cobro_jornada(e) == cs['camiseta']['fijo'] // n
    cs['camiseta'] = None                                              # sin patrocinadores no se cobra
    assert P.cobro_jornada(e) == 0 and F.procesar_jornada(e, False, 0, 0)['patrocinio'] == 0
    print("  test_cobro_jornada: OK")


def test_objetivos_cumple_y_progreso():
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']
    c = lambda tipo, meta: {'objetivo': _obj(tipo, meta)}
    assert P.cumple(e, c('posicion', 4), posicion=4) is True and P.cumple(e, c('posicion', 4), posicion=5) is False
    mi.gf = 30
    assert P.cumple(e, c('goles', 30)) is True and P.cumple(e, c('goles', 31)) is False
    assert abs(P.progreso(e, c('goles', 60)) - 0.5) < 1e-9
    rival = liga.equipos[1] if liga.equipos[0] is mi else liga.equipos[0]
    liga.calendario = [Partido(local_id=mi.id, visitante_id=rival.id, jornada=1, goles_local=2, goles_visitante=0, jugado=True),
                       Partido(local_id=mi.id, visitante_id=rival.id, jornada=3, goles_local=1, goles_visitante=1, jugado=True),
                       Partido(local_id=rival.id, visitante_id=mi.id, jornada=2, goles_local=0, goles_visitante=3, jugado=True)]
    assert P.cumple(e, c('local', 1)) is True and P.cumple(e, c('local', 2)) is False   # solo cuenta ganar de local
    for j in mi.jugadores:
        j.edad, j.partidos_jugados = 25, 9
    mi.jugadores[0].edad, mi.jugadores[1].edad = 19, 20
    assert P.cumple(e, c('u21', 18)) is True and P.cumple(e, c('u21', 19)) is False
    e['copa_mejor_fase_temp'] = None                                   # temporada sin copa: no aplica
    assert P.cumple(e, c('copa', 'Octavos')) is None and P.progreso(e, c('copa', 'Octavos')) == 0.0
    e['copa_mejor_fase_temp'] = 'Cuartos'
    assert P.cumple(e, c('copa', 'Octavos')) is True and P.cumple(e, c('copa', 'Semifinal')) is False
    for tipo, meta in (('posicion', 3), ('goles', 40), ('local', 6), ('u21', 20), ('copa', 'Semifinal')):
        assert 0.0 <= P.progreso(e, c(tipo, meta)) <= 1.0
    print("  test_objetivos_cumple_y_progreso: OK")


def test_crear_objetivo_dificultad():
    e = estado_carrera(); rng = random.Random(2)
    for tipo in ('goles', 'local', 'u21'):
        metas = [P.crear_objetivo(e, d, rng, tipo=tipo)['meta'] for d in (0, 1, 2)]
        assert metas == sorted(metas) and metas[0] < metas[2], (tipo, metas)
    pos = [P.crear_objetivo(e, d, rng, tipo='posicion')['meta'] for d in (0, 1, 2)]
    assert pos[0] >= pos[1] >= pos[2] >= 1                              # más difícil = puesto más alto
    assert all(P.crear_objetivo(e, 1, rng)['tipo'] != 'copa' for _ in range(40))   # sin copa no se ofrece
    assert P.mult_reputacion(0) == 0.80 and P.mult_reputacion(50) == 1.00 and abs(P.mult_reputacion(100) - 1.30) < 1e-9
    print("  test_crear_objetivo_dificultad: OK")


TESTS = [test_fracciones_y_ingresos_esperados, test_contratos_iniciales, test_cobro_jornada,
         test_objetivos_cumple_y_progreso, test_crear_objetivo_dificultad]
# --- TESTS-FIN ---

if __name__ == '__main__':
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

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py`
Expected: FAIL con `ImportError: cannot import name 'patrocinios'`.

- [ ] **Step 3: Crear `alpha_football/patrocinios.py` con el bloque `T1-impl`**

<!-- bloque: T1-impl -->
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Patrocinios (v4.9.0)
Hasta 3 contratos (camiseta, manga, estadio) con marcas parodia: fijo por jornada, bono por
objetivo, años de contrato. Al vencer llegan ofertas (renovación si cumpliste). Reputación
comercial 0–100 que mejora o empeora las ofertas. Estado en datos_carrera['patrocinios'].
Los clubes de la IA no tienen contratos: siguen con el ingreso de fórmula.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

ESPACIOS = (('camiseta', 0.50), ('manga', 0.30), ('estadio', 0.20))
NOMBRE_ESPACIO = {'camiseta': "Camiseta", 'manga': "Manga", 'estadio': "Estadio"}
# perfil: (fijo × referencia, bono × referencia, dificultad del objetivo 0 fácil / 1 media / 2 difícil)
PERFILES = {'conservadora': (1.00, 0.10, 0), 'equilibrada': (0.90, 0.25, 1), 'ambiciosa': (0.75, 0.50, 2)}
MARCAS = [   # (marca parodia, rubro, perfil)
    ("Fly Emirados", "aerolínea", 'ambiciosa'), ("Qatar Airguais", "aerolínea", 'equilibrada'),
    ("Etihat", "aerolínea", 'conservadora'), ("Turquish Erlains", "aerolínea", 'equilibrada'),
    ("Adibas", "ropa deportiva", 'equilibrada'), ("Naik", "ropa deportiva", 'ambiciosa'),
    ("Pumba", "ropa deportiva", 'conservadora'), ("Niu Balans", "ropa deportiva", 'equilibrada'),
    ("Coca-Kola", "bebidas", 'conservadora'), ("Pepsy", "bebidas", 'equilibrada'),
    ("Red Bul", "bebidas", 'ambiciosa'), ("Heinekan", "bebidas", 'equilibrada'),
    ("Sansumg", "tecnología", 'equilibrada'), ("Spotifai", "tecnología", 'ambiciosa'),
    ("TeamViuer", "tecnología", 'conservadora'), ("Soni", "tecnología", 'equilibrada'),
    ("Bet366", "apuestas", 'ambiciosa'), ("Betguay", "apuestas", 'ambiciosa'),
    ("Codere-te", "apuestas", 'equilibrada'), ("Wplei", "apuestas", 'conservadora'),
    ("Santénder", "banca", 'conservadora'), ("Mastercar", "banca", 'equilibrada'),
    ("Bisa", "banca", 'conservadora'), ("Standar Charte", "banca", 'equilibrada'),
    ("Chevrolé", "autos", 'equilibrada'), ("Jip", "autos", 'conservadora'),
    ("Audí", "autos", 'ambiciosa'), ("Kía Motor", "autos", 'equilibrada'),
]

REP_INICIAL = 50
REP_CUMPLE, REP_FALLA, REP_TITULO, REP_ASCENSO = 6, -5, 8, 8
REP_DESCENSO, REP_QUIEBRA, REP_RESCISION = -10, -15, -8
REP_SIN_INTERES = 15             # por debajo, las marcas pueden no presentarse
PROB_NO_OFERTA = 0.5
FACTOR_DESCENSO, FACTOR_ASCENSO, FACTOR_INVIERNO = 0.60, 1.30, 0.85
PRIMA_FRAC, PRIMA_FIJO = 0.30, 0.88      # prima al contado (× un año de fijo) y fijo que queda
MULTA_FRAC = 0.50                         # rescindir: 50% del fijo que le queda al contrato
NEGOCIAR = {1: (0.10, 0.60), 2: (0.20, 0.30)}   # nivel: (subida de fijo, probabilidad base)
FASE_COPA_DIFICULTAD = ('Fase de liga', 'Octavos', 'Semifinal')
TEXTO_COPA = ("Jugar la copa internacional", "Llegar a octavos de la copa", "Llegar a semifinales de la copa")


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _m(v: int) -> str:
    return f"${int(v) / 1_000_000:.2f}M"


def _rep(p: dict, delta: int) -> None:
    p['reputacion'] = max(0, min(100, int(p.get('reputacion', REP_INICIAL)) + int(delta)))


def mult_reputacion(rep: int) -> float:
    """0 → ×0.80, 50 → ×1.00, 100 → ×1.30 (lineal por tramos)."""
    rep = max(0, min(100, int(rep)))
    return 0.80 + 0.20 * rep / 50 if rep <= 50 else 1.00 + 0.30 * (rep - 50) / 50


def _base(estado: dict) -> int:
    """Patrocinio de fórmula de una temporada para el club del user."""
    from alpha_football import finanzas as F
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    return int(F.base_ingresos(mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1) * F.PATROCINIO_FRAC)


def valor_referencia(estado: dict, espacio: str) -> int:
    return int(_base(estado) * dict(ESPACIOS)[espacio])


# --- objetivos -----------------------------------------------------------------------------

def _juega_copa(estado: dict) -> bool:
    try:
        from alpha_football import competiciones as CP
        return bool(CP.tipo_copa_user(estado))
    except Exception:
        return False


def _puesto_esperado(estado: dict) -> int:
    from alpha_football.market import nivel_club
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    orden = sorted(liga.equipos, key=lambda eq: -nivel_club(eq))
    return next((i + 1 for i, eq in enumerate(orden) if eq is mi), len(orden))


def crear_objetivo(estado: dict, dificultad: int, rng: random.Random, tipo: Optional[str] = None) -> dict:
    """Objetivo de temporada de un contrato según el club y la dificultad (0, 1 o 2)."""
    liga = estado.get('liga')
    n = max(1, int(getattr(liga, 'num_jornadas', 22) or 22))
    n_eq = max(2, len(getattr(liga, 'equipos', []) or []))
    d = max(0, min(2, int(dificultad)))
    if tipo is None:
        tipo = rng.choice(['posicion', 'goles', 'local', 'u21'] + (['copa'] if _juega_copa(estado) else []))
    if tipo == 'posicion':
        meta = max(1, min(n_eq, _puesto_esperado(estado) + (3, 0, -3)[d]))
        texto = "Ganar la liga" if meta == 1 else f"Terminar la liga en el puesto {meta} o mejor"
    elif tipo == 'goles':
        meta = round(n * (1.2, 1.5, 1.9)[d])
        texto = f"Marcar {meta} goles en la liga"
    elif tipo == 'local':
        meta = max(1, round(n / 2 * (0.40, 0.55, 0.70)[d]))
        texto = f"Ganar {meta} partidos de local en la liga"
    elif tipo == 'u21':
        meta = max(1, round((10, 25, 45)[d] * n / 22))
        texto = f"Que los menores de 21 sumen {meta} partidos"
    else:
        tipo, meta, texto = 'copa', FASE_COPA_DIFICULTAD[d], TEXTO_COPA[d]
    return {'tipo': tipo, 'meta': meta, 'texto': texto}


def _valor_actual(estado: dict, tipo: str, posicion: Optional[int] = None):
    """Lo que lleva el club en ese tipo de objetivo (None en copa si no la juega)."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if tipo == 'posicion':
        if posicion is not None:
            return int(posicion)
        from alpha_football.ui.postpartido import posicion_liga
        return int(posicion_liga(liga, mi.id))
    if tipo == 'goles':
        return int(getattr(mi, 'gf', 0) or 0)
    if tipo == 'local':
        return sum(1 for p in getattr(liga, 'calendario', []) or []
                   if p.jugado and p.local_id == mi.id and (p.goles_local or 0) > (p.goles_visitante or 0))
    if tipo == 'u21':
        return sum(int(getattr(j, 'partidos_jugados', 0) or 0) for j in mi.jugadores
                   if int(getattr(j, 'edad', 25) or 25) < 21)
    return estado.get('copa_mejor_fase_temp') or None


def cumple(estado: dict, contrato: dict, posicion: Optional[int] = None) -> Optional[bool]:
    """True/False, o None si esta temporada no aplica (objetivo de copa sin jugar la copa)."""
    obj = contrato.get('objetivo') or {}
    tipo, meta = obj.get('tipo'), obj.get('meta')
    actual = _valor_actual(estado, tipo, posicion)
    if tipo == 'copa':
        if actual is None:
            return None
        from alpha_football.directiva import _indice_fase_copa
        return _indice_fase_copa(actual) >= _indice_fase_copa(meta)
    if tipo == 'posicion':
        return int(actual) <= int(meta)
    return int(actual) >= int(meta)


def progreso(estado: dict, contrato: dict) -> float:
    """Fracción 0..1 para la barra de la pantalla."""
    try:
        obj = contrato.get('objetivo') or {}
        tipo, meta = obj.get('tipo'), obj.get('meta')
        actual = _valor_actual(estado, tipo)
        if tipo == 'copa':
            if actual is None:
                return 0.0
            from alpha_football.directiva import _indice_fase_copa
            f = (_indice_fase_copa(actual) + 1) / (_indice_fase_copa(meta) + 1)
        elif tipo == 'posicion':
            n_eq = len(estado['liga'].equipos)
            f = 1.0 if actual <= meta else 1.0 - (actual - meta) / max(1, n_eq - meta)
        else:
            f = actual / meta if meta else 1.0
        return max(0.0, min(1.0, float(f)))
    except Exception as e:
        logger.error(f"progreso de patrocinio: {e}")
        return 0.0


# --- contratos y estado --------------------------------------------------------------------

def _crear_contrato(estado: dict, marca: tuple, espacio: str, rng: random.Random, anios: int,
                    mult: float = 1.0, fijo: Optional[float] = None) -> dict:
    nombre, rubro, perfil = marca
    f_fijo, f_bono, dificultad = PERFILES[perfil]
    ref = valor_referencia(estado, espacio) * mult
    return {'marca': nombre, 'rubro': rubro, 'espacio': espacio, 'perfil': perfil,
            'fijo': int(fijo if fijo is not None else ref * f_fijo), 'bono': int(ref * f_bono),
            'objetivo': crear_objetivo(estado, dificultad, rng), 'anios': int(anios), 'cumplido_ultima': None}


def _nuevo(estado: dict) -> dict:
    """Los 3 contratos con los que llega el club: rubros distintos y años restantes al azar."""
    rng = random.Random()
    marcas = list(MARCAS)
    rng.shuffle(marcas)
    contratos, rubros = {}, set()
    for espacio, _peso in ESPACIOS:
        marca = next(m for m in marcas if m[1] not in rubros)
        rubros.add(marca[1])
        contratos[espacio] = _crear_contrato(estado, marca, espacio, rng, rng.randint(1, 3))
    return {'club': estado['mi_equipo'].nombre, 'reputacion': REP_INICIAL, 'contratos': contratos,
            'ofertas': [], 'sig_id': 0}


def _valido(p: Any, mi: Any) -> bool:
    if not isinstance(p, dict) or p.get('club') != getattr(mi, 'nombre', None):
        return False
    cs = p.get('contratos')
    if not isinstance(cs, dict) or not isinstance(p.get('ofertas'), list):
        return False
    return all(esp in cs and (cs[esp] is None or (isinstance(cs[esp], dict) and 'marca' in cs[esp] and 'fijo' in cs[esp]))
               for esp, _w in ESPACIOS)


def datos(estado: dict) -> dict:
    """Estado de patrocinios del club del user; si falta, está corrupto o es de otro club, se genera."""
    dc = _dc(estado)
    p = dc.get('patrocinios')
    if not _valido(p, estado.get('mi_equipo')):
        p = dc['patrocinios'] = _nuevo(estado)
    return p


def cobro_jornada(estado: dict) -> int:
    """Lo que pagan los contratos vigentes en una jornada de liga."""
    n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))
    return sum(int(c['fijo']) // n for c in datos(estado)['contratos'].values() if c)


def ingreso_anual(estado: dict) -> int:
    return sum(int(c['fijo']) for c in datos(estado)['contratos'].values() if c)
```

- [ ] **Step 4: Fracciones y cobro en `finanzas.py`**

Reemplazar las dos constantes:

```python
PATROCINIO_FRAC = 0.55          # v4.9.0 (antes 0.40): valor de referencia de los patrocinios de la temporada
TAQUILLA_FRAC = 0.35            # v4.9.0 (antes 0.50): la suma sigue en 0.90 (ingresos_esperados no cambia)
```

En `procesar_jornada`, reemplazar `    patrocinio = int(medio * PATROCINIO_FRAC / n)` por:

```python
    try:   # v4.9.0: cobran los contratos de patrocinio (sin contratos, no hay patrocinio)
        from alpha_football import patrocinios as _P
        patrocinio = _P.cobro_jornada(estado)
    except Exception as e_pat:   # un fallo no deja al club sin cobrar: patrocinio de fórmula
        logger.error(f"Error cobrando los patrocinios: {e_pat}")
        patrocinio = int(medio * PATROCINIO_FRAC / n)
```

- [ ] **Step 5: Actualizar `tests/test_finanzas_v460.py:37`**

Reemplazar `    assert mov['patrocinio'] == int(base * F.PATROCINIO_FRAC / liga.num_jornadas)` por:

```python
    from alpha_football import patrocinios as P                      # v4.9.0: cobran los contratos
    assert mov['patrocinio'] == P.cobro_jornada(e) > 0
```

- [ ] **Step 6: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: `5/5 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_finanzas_v460.py` y `python tests/test_finanzas_v290.py` → Expected: sin FAIL. Si un test de quiebra depende del monto exacto del patrocinio, ajustar el test para que fije los contratos (`P.datos(e)['contratos']`) en vez de cambiar la lógica.

- [ ] **Step 7: Commit** (solo si Diego lo pidió)

---

### Task 2: Ofertas y acciones del usuario

**Files:**
- Modify: `alpha_football/patrocinios.py` (añadir bloque `T2-impl` al final)
- Modify: `tests/test_patrocinios.py` (insertar bloque `T2-test` antes de `TESTS = [` y ampliar la lista)

**Interfaces:**
- Consumes: Task 1 (`datos`, `_crear_contrato`, `mult_reputacion`, `_rep`, `_m`, constantes); `market.ventana_actual(jornada, num_jornadas) -> (ini, fin, nombre)|None`; `finanzas.registrar(estado, clave, monto)`.
- Produces: `generar_ofertas(estado, espacio, rng=None, factor=1.0, anterior=None) -> list[dict]` (cada oferta = contrato + `'id'`, `'renovacion'`, `'negociada'`), `ofertas_de(estado, espacio) -> list`, `firmar(estado, oferta_id, con_prima=False) -> (bool, str)`, `rechazar(estado, oferta_id) -> bool`, `prob_negociar(estado, nivel) -> float`, `negociar(estado, oferta_id, nivel, rng=None) -> (bool, str)`, `multa_rescision(estado, espacio) -> int`, `rescindir(estado, espacio, rng=None) -> (bool, str)`, `_ventana(estado) -> str|None`.

- [ ] **Step 1: Añadir los tests (bloque `T2-test`) y sus nombres a `TESTS`**

<!-- bloque: T2-test -->
```python
class _Azar(random.Random):
    """random() fijo para forzar el éxito o el fracaso de una negociación."""
    def __init__(self, valor):
        super().__init__(1); self._valor = valor
    def random(self):
        return self._valor


def _vaciar(e, espacio):
    p = P.datos(e); viejo = p['contratos'][espacio]; p['contratos'][espacio] = None
    return p, viejo


def test_generar_ofertas_exclusividad_y_valor():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    ofertas = P.generar_ofertas(e, 'manga', random.Random(3))
    ocupados = {c['rubro'] for esp, c in p['contratos'].items() if c}
    assert len(ofertas) == 2 and len({o['rubro'] for o in ofertas}) == 2
    assert not ocupados & {o['rubro'] for o in ofertas}                 # exclusividad de rubro
    assert len({o['id'] for o in ofertas}) == 2 and all(o['espacio'] == 'manga' and not o['renovacion'] for o in ofertas)
    assert P.ofertas_de(e, 'manga') == ofertas and P.ofertas_de(e, 'camiseta') == []
    p['reputacion'] = P.REP_SIN_INTERES
    bajo = P.generar_ofertas(e, 'manga', random.Random(3))              # misma semilla, peor reputación
    p['reputacion'] = 100
    alto = P.generar_ofertas(e, 'manga', random.Random(3))
    assert [o['marca'] for o in bajo] == [o['marca'] for o in alto]
    assert all(a['fijo'] > b['fijo'] * 1.4 for a, b in zip(alto, bajo))   # ×1.30 contra ×0.86
    assert len(P.ofertas_de(e, 'manga')) == 2                           # regenerar reemplaza, no acumula
    print("  test_generar_ofertas_exclusividad_y_valor: OK")


def test_renovacion_solo_si_cumplio():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, viejo = _vaciar(e, 'camiseta')
    viejo['cumplido_ultima'] = True
    ofertas = P.generar_ofertas(e, 'camiseta', random.Random(4), anterior=viejo)
    ren = [o for o in ofertas if o['renovacion']]
    assert len(ofertas) == 3 and len(ren) == 1 and ren[0]['marca'] == viejo['marca']
    assert viejo['fijo'] * 1.10 - 1 <= ren[0]['fijo'] <= viejo['fijo'] * 1.20 + 1
    for estado_obj in (False, None):                                    # falló o no aplicó: no renueva
        viejo['cumplido_ultima'] = estado_obj
        ofertas = P.generar_ofertas(e, 'camiseta', random.Random(4), anterior=viejo)
        assert len(ofertas) == 2 and viejo['marca'] not in {o['marca'] for o in ofertas}
    print("  test_renovacion_solo_si_cumplio: OK")


def test_sin_interesados():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'estadio')
    prob = P.PROB_NO_OFERTA
    try:
        P.PROB_NO_OFERTA = 1.0
        p['reputacion'] = P.REP_SIN_INTERES - 1
        assert P.generar_ofertas(e, 'estadio', random.Random(5)) == []   # nadie se presenta
        p['reputacion'] = P.REP_SIN_INTERES
        assert len(P.generar_ofertas(e, 'estadio', random.Random(5))) == 2
    finally:
        P.PROB_NO_OFERTA = prob
    print("  test_sin_interesados: OK")


def test_firmar_y_prima():
    e = estado_carrera(); mi = e['mi_equipo']; e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    o = dict(P.generar_ofertas(e, 'manga', random.Random(6))[0])
    ok, msg = P.firmar(e, o['id'])
    c = p['contratos']['manga']
    assert ok and o['marca'] in msg and c['marca'] == o['marca'] and c['fijo'] == o['fijo']
    assert not {'id', 'renovacion', 'negociada'} & set(c) and P.ofertas_de(e, 'manga') == []
    assert P.firmar(e, o['id']) == (False, "Esa oferta ya no está disponible.")
    p, _v = _vaciar(e, 'estadio')
    o = dict(P.generar_ofertas(e, 'estadio', random.Random(7))[0])
    bal, lib = mi.balance, F.libro(e)['patrocinio']
    ok, msg = P.firmar(e, o['id'], con_prima=True)
    prima = int(o['fijo'] * P.PRIMA_FRAC)
    assert ok and mi.balance == bal + prima and F.libro(e)['patrocinio'] == lib + prima
    assert p['contratos']['estadio']['fijo'] == int(o['fijo'] * P.PRIMA_FIJO)
    print("  test_firmar_y_prima: OK")


def test_firmar_exclusividad():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    o = P.generar_ofertas(e, 'manga', random.Random(8))[0]
    o['rubro'] = p['contratos']['camiseta']['rubro']                     # como si otra firma hubiera ocupado el rubro
    ok, msg = P.firmar(e, o['id'])
    assert not ok and "rubro" in msg and p['contratos']['manga'] is None
    p['contratos']['manga'] = dict(p['contratos']['estadio'], espacio='manga', rubro='otro')
    ok, msg = P.firmar(e, o['id'])                                       # espacio ya ocupado
    assert not ok
    print("  test_firmar_exclusividad: OK")


def test_rechazar_todo_deja_vacio():
    e = estado_carrera(); e['liga'].jornada_actual = 5; n = e['liga'].num_jornadas
    p, _v = _vaciar(e, 'camiseta')
    antes = P.cobro_jornada(e)
    for o in list(P.generar_ofertas(e, 'camiseta', random.Random(9))):
        assert P.rechazar(e, o['id']) is True
    assert P.rechazar(e, 999) is False
    assert P.ofertas_de(e, 'camiseta') == [] and p['contratos']['camiseta'] is None
    assert P.cobro_jornada(e) == antes == sum(c['fijo'] // n for c in p['contratos'].values() if c)
    print("  test_rechazar_todo_deja_vacio: OK")


def test_negociar():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    assert abs(P.prob_negociar(e, 1) - 0.60) < 1e-9 and abs(P.prob_negociar(e, 2) - 0.30) < 1e-9
    p['reputacion'] = 100
    assert abs(P.prob_negociar(e, 1) - 0.75) < 1e-9
    p['reputacion'] = 0
    assert abs(P.prob_negociar(e, 1) - 0.45) < 1e-9 and abs(P.prob_negociar(e, 2) - 0.15) < 1e-9
    p['reputacion'] = 50
    a, b = P.generar_ofertas(e, 'manga', random.Random(10))
    fijo = a['fijo']
    ok, msg = P.negociar(e, a['id'], 1, _Azar(0.0))
    assert ok and a['fijo'] == int(fijo * 1.10) and a['negociada']
    assert P.negociar(e, a['id'], 2, _Azar(0.0)) == (False, "Ya negociaste esta oferta.") and a['fijo'] == int(fijo * 1.10)
    ok, msg = P.negociar(e, b['id'], 2, _Azar(0.99))
    assert not ok and b['marca'] in msg and [o['id'] for o in P.ofertas_de(e, 'manga')] == [a['id']]   # se retira
    print("  test_negociar: OK")


def test_rescindir():
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']
    liga.calendario = []; liga.jornada_actual = 5                        # mercado cerrado, 0 partidos jugados
    p = P.datos(e); c = p['contratos']['camiseta']; c['anios'] = 2
    multa = int((c['fijo'] + c['fijo'] * 1) * P.MULTA_FRAC)
    assert P.multa_rescision(e, 'camiseta') == multa
    mi.balance = multa - 1
    ok, msg = P.rescindir(e, 'camiseta')
    assert not ok and "Saldo insuficiente" in msg and p['contratos']['camiseta'] is c
    mi.balance = multa + 100
    ok, msg = P.rescindir(e, 'camiseta')
    assert ok and mi.balance == 100 and p['contratos']['camiseta'] is None and p['reputacion'] == 50 + P.REP_RESCISION
    assert P.ofertas_de(e, 'camiseta') == []                             # mercado cerrado: sin ofertas aún
    assert P.rescindir(e, 'camiseta')[0] is False
    liga.jornada_actual = 1                                              # ventana abierta: ofertas de inmediato
    marca = p['contratos']['manga']['marca']; mi.balance = 10 ** 12
    assert P.rescindir(e, 'manga', random.Random(11))[0]
    ofertas = P.ofertas_de(e, 'manga')
    assert ofertas and marca not in {o['marca'] for o in ofertas}        # la marca despechada no vuelve
    print("  test_rescindir: OK")
```

Nombres a añadir en `TESTS`: `test_generar_ofertas_exclusividad_y_valor, test_renovacion_solo_si_cumplio, test_sin_interesados, test_firmar_y_prima, test_firmar_exclusividad, test_rechazar_todo_deja_vacio, test_negociar, test_rescindir`.

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py`
Expected: 8 FAIL (`has no attribute 'generar_ofertas'`…); `5/13 tests pasaron`.

- [ ] **Step 3: Añadir el bloque `T2-impl` al final de `alpha_football/patrocinios.py`**

<!-- bloque: T2-impl -->
```python


# --- ofertas y acciones --------------------------------------------------------------------

def _ventana(estado: dict) -> Optional[str]:
    """'inicio' | 'invierno' | 'cierre' si el mercado está abierto; None si no."""
    from alpha_football.market import ventana_actual
    liga = estado.get('liga')
    v = ventana_actual(int(getattr(liga, 'jornada_actual', 1) or 1), int(getattr(liga, 'num_jornadas', 22) or 22))
    return v[2] if v else None


def ofertas_de(estado: dict, espacio: str) -> list:
    return [o for o in datos(estado)['ofertas'] if o.get('espacio') == espacio]


def generar_ofertas(estado: dict, espacio: str, rng: Optional[random.Random] = None, factor: float = 1.0,
                    anterior: Optional[dict] = None) -> list:
    """Ofertas para un espacio vacío (reemplazan a las que hubiera): la renovación de `anterior`
    si cumplió su objetivo, y hasta 2 marcas nuevas de rubros libres. Retorna las nuevas."""
    p = datos(estado)
    azar = rng or random.Random()
    p['ofertas'] = [o for o in p['ofertas'] if o.get('espacio') != espacio]
    rep = int(p.get('reputacion', REP_INICIAL))
    mult = mult_reputacion(rep) * factor
    ocupados = {c['rubro'] for esp, c in p['contratos'].items() if c and esp != espacio}
    nuevas = []
    if anterior and anterior.get('cumplido_ultima') is True and anterior.get('rubro') not in ocupados:
        o = _crear_contrato(estado, (anterior['marca'], anterior['rubro'], anterior['perfil']), espacio, azar,
                            azar.randint(1, 3), mult, fijo=anterior['fijo'] * azar.uniform(1.10, 1.20))
        o['renovacion'] = True
        nuevas.append(o)
        ocupados.add(anterior['rubro'])
    candidatas = [m for m in MARCAS if m[1] not in ocupados and (not anterior or m[0] != anterior.get('marca'))]
    azar.shuffle(candidatas)
    elegidas = []
    for m in candidatas:
        if m[1] not in {x[1] for x in elegidas}:
            elegidas.append(m)
        if len(elegidas) == 2:
            break
    for m in elegidas:
        variacion = azar.uniform(0.95, 1.05)
        anios = azar.randint(1, 3)
        no_viene = azar.random() < PROB_NO_OFERTA
        if rep < REP_SIN_INTERES and no_viene:
            continue                     # con mala reputación la marca puede no presentarse
        o = _crear_contrato(estado, m, espacio, azar, anios, mult * variacion)
        o['renovacion'] = False
        nuevas.append(o)
    for o in nuevas:
        p['sig_id'] = o['id'] = int(p.get('sig_id', 0) or 0) + 1
        o['negociada'] = False
    p['ofertas'] += nuevas
    return nuevas


def _oferta(p: dict, oferta_id: int) -> Optional[dict]:
    return next((o for o in p['ofertas'] if o.get('id') == oferta_id), None)


def firmar(estado: dict, oferta_id: int, con_prima: bool = False) -> tuple:
    """Firma la oferta. Con prima: 30% de un año al contado y el fijo queda ×0.88."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        o = _oferta(p, oferta_id)
        if o is None:
            return False, "Esa oferta ya no está disponible."
        espacio = o['espacio']
        if p['contratos'].get(espacio):
            return False, "Ese espacio ya tiene patrocinador."
        if any(c and c['rubro'] == o['rubro'] for esp, c in p['contratos'].items() if esp != espacio):
            return False, f"Ya tienes una marca del rubro {o['rubro']} en otro espacio."
        c = {k: v for k, v in o.items() if k not in ('id', 'renovacion', 'negociada')}
        extra = ""
        if con_prima:
            prima = int(c['fijo'] * PRIMA_FRAC)
            c['fijo'] = int(c['fijo'] * PRIMA_FIJO)
            mi.balance = int(mi.balance) + prima
            registrar(estado, 'patrocinio', prima)
            extra = f" Prima de firma: {_m(prima)}."
        p['contratos'][espacio] = c
        p['ofertas'] = [x for x in p['ofertas'] if x.get('espacio') != espacio]
        anios = c['anios']
        return True, (f"{c['marca']} patrocina tu {NOMBRE_ESPACIO[espacio].lower()} por {anios} "
                      f"año{'s' if anios != 1 else ''}: {_m(c['fijo'])} al año.{extra}")
    except Exception as e:
        logger.error(f"No se pudo firmar el patrocinio {oferta_id}: {e}", exc_info=True)
        return False, "No se pudo firmar el patrocinio."


def rechazar(estado: dict, oferta_id: int) -> bool:
    p = datos(estado)
    o = _oferta(p, oferta_id)
    if o is None:
        return False
    p['ofertas'].remove(o)
    return True


def prob_negociar(estado: dict, nivel: int) -> float:
    """Probabilidad de que la marca acepte la subida: base del nivel ± 0.3 puntos por punto de reputación."""
    base = NEGOCIAR[nivel][1]
    rep = int(datos(estado).get('reputacion', REP_INICIAL))
    return max(0.05, min(0.90, base + 0.003 * (rep - 50)))


def negociar(estado: dict, oferta_id: int, nivel: int, rng: Optional[random.Random] = None) -> tuple:
    """Pide +10% (nivel 1) o +20% (nivel 2) de fijo, una vez por oferta. Si falla, la marca se retira."""
    try:
        p = datos(estado)
        o = _oferta(p, oferta_id)
        if o is None:
            return False, "Esa oferta ya no está disponible."
        if o.get('negociada'):
            return False, "Ya negociaste esta oferta."
        if (rng or random.Random()).random() < prob_negociar(estado, nivel):
            o['fijo'] = int(o['fijo'] * (1 + NEGOCIAR[nivel][0]))
            o['negociada'] = True
            return True, f"{o['marca']} acepta: sube el fijo a {_m(o['fijo'])} al año."
        p['ofertas'].remove(o)
        return False, f"{o['marca']} no acepta y retira su oferta."
    except Exception as e:
        logger.error(f"No se pudo negociar el patrocinio {oferta_id}: {e}", exc_info=True)
        return False, "No se pudo negociar la oferta."


def multa_rescision(estado: dict, espacio: str) -> int:
    """50% del fijo que le queda al contrato: lo que falta de esta temporada más las siguientes."""
    c = datos(estado)['contratos'].get(espacio)
    if not c:
        return 0
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    n = max(1, int(getattr(liga, 'num_jornadas', 22) or 22))
    jugadas = sum(1 for x in getattr(liga, 'calendario', []) or [] if x.jugado and mi.id in (x.local_id, x.visitante_id))
    restantes = max(0, n - jugadas)
    return int((c['fijo'] * restantes / n + c['fijo'] * max(0, int(c['anios']) - 1)) * MULTA_FRAC)


def rescindir(estado: dict, espacio: str, rng: Optional[random.Random] = None) -> tuple:
    """Rompe el contrato pagando la multa (−8 de reputación). Con el mercado abierto llegan ofertas ya."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        c = p['contratos'].get(espacio)
        if not c:
            return False, "Ese espacio no tiene patrocinador."
        multa = multa_rescision(estado, espacio)
        if int(mi.balance) < multa:
            return False, f"Saldo insuficiente para la multa de {_m(multa)}."
        mi.balance = int(mi.balance) - multa
        registrar(estado, 'patrocinio', -multa)
        p['contratos'][espacio] = None
        _rep(p, REP_RESCISION)
        ventana = _ventana(estado)
        if ventana in ('inicio', 'invierno'):
            generar_ofertas(estado, espacio, rng, factor=FACTOR_INVIERNO if ventana == 'invierno' else 1.0,
                            anterior={'marca': c['marca'], 'cumplido_ultima': False})
        return True, f"Contrato con {c['marca']} rescindido. Multa: {_m(multa)}."
    except Exception as e:
        logger.error(f"No se pudo rescindir el patrocinio de {espacio}: {e}", exc_info=True)
        return False, "No se pudo rescindir el contrato."
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: `13/13 tests pasaron`.

- [ ] **Step 5: Commit** (solo si Diego lo pidió)

---

### Task 3: Ciclo de temporada, ventanas y correo

**Files:**
- Modify: `alpha_football/patrocinios.py` (añadir bloque `T3-impl` al final)
- Modify: `alpha_football/correo.py` (`REMITENTES`, `FIRMAS`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py` (tras el `try` de `evaluar_temporada`, ~línea 222; y tras `estado['liga_usuario_division'] = ...`, ~línea 385)
- Modify: `alpha_football/finanzas.py` (final de `cierre_temporada`, antes de `return salidas`)
- Modify: `alpha_football/ui/match_screen.py` (tras el bloque `# v4.8.0: cantera`)
- Test: `tests/test_patrocinios.py` (bloque `T3-test`)

**Interfaces:**
- Consumes: Tasks 1–2; `correo.enviar`, `correo.accion`; `finanzas.registrar(estado, clave, monto, temporada)`.
- Produces: `evaluar_temporada(estado, posicion, temporada) -> dict|None`, `cambio_division(estado, ascendio, descendio) -> None`, `cierre_contratos(estado, rng=None) -> dict|None`, `revisar_jornada(estado, rng=None) -> None`; remitente de correo `'patrocinador'`.

- [ ] **Step 1: Añadir los tests (bloque `T3-test`) y sus nombres a `TESTS`**

<!-- bloque: T3-test -->
```python
def _correos(e):
    return [m for m in C.bandeja(e) if m['remitente'] == 'patrocinador']


def test_evaluar_temporada_bonos_y_reputacion():
    e = estado_carrera(); mi = e['mi_equipo']; p = P.datos(e); cs = p['contratos']
    mi.gf = 10; e['copa_mejor_fase_temp'] = None
    cs['camiseta']['objetivo'] = _obj('goles', 5)                        # cumple
    cs['manga']['objetivo'] = _obj('goles', 999)                         # falla
    cs['estadio']['objetivo'] = _obj('copa', 'Octavos')                  # no aplica: no jugó la copa
    bal = mi.balance; bono = cs['camiseta']['bono']
    res = P.evaluar_temporada(e, 5, 1)
    assert res['bonos'] == bono and mi.balance == bal + bono
    assert p['reputacion'] == 50 + P.REP_CUMPLE + P.REP_FALLA
    assert (cs['camiseta']['cumplido_ultima'], cs['manga']['cumplido_ultima'], cs['estadio']['cumplido_ultima']) == (True, False, None)
    assert P.evaluar_temporada(e, 5, 1) is None and mi.balance == bal + bono     # no paga dos veces
    rep = p['reputacion']
    e['liga'].division = 1
    P.evaluar_temporada(e, 1, 2)                                         # campeón de 1ª: +8 además de los objetivos
    assert p['reputacion'] == min(100, rep + P.REP_CUMPLE + P.REP_FALLA + P.REP_TITULO)
    print("  test_evaluar_temporada_bonos_y_reputacion: OK")


def test_cambio_division():
    e = estado_carrera(); p = P.datos(e)
    antes = {esp: (c['fijo'], c['bono']) for esp, c in p['contratos'].items()}
    P.cambio_division(e, False, False)
    assert {esp: (c['fijo'], c['bono']) for esp, c in p['contratos'].items()} == antes and p['reputacion'] == 50
    P.cambio_division(e, False, True)
    assert all(c['fijo'] == int(antes[esp][0] * 0.60) and c['bono'] == int(antes[esp][1] * 0.60)
               for esp, c in p['contratos'].items())
    assert p['reputacion'] == 50 + P.REP_DESCENSO
    antes = {esp: c['fijo'] for esp, c in p['contratos'].items()}
    P.cambio_division(e, True, False)
    assert all(c['fijo'] == int(antes[esp] * 1.30) for esp, c in p['contratos'].items())
    assert p['reputacion'] == 50 + P.REP_DESCENSO + P.REP_ASCENSO
    print("  test_cambio_division: OK")


def test_cierre_contratos_vencen_y_ofertas():
    e = estado_carrera(); mi = e['mi_equipo']; p = P.datos(e); cs = p['contratos']
    e['liga'].jornada_actual = 1; mi.balance = abs(mi.balance) + 1
    cs['camiseta'].update(anios=1, cumplido_ultima=True)
    cs['manga'].update(anios=2, cumplido_ultima=True)
    cs['estadio'].update(anios=1, cumplido_ultima=False)
    marca_cam, marca_est = cs['camiseta']['marca'], cs['estadio']['marca']
    res = P.cierre_contratos(e, random.Random(12))
    assert set(res['vencidos']) == {'camiseta', 'estadio'}
    assert cs['camiseta'] is None and cs['estadio'] is None and cs['manga']['anios'] == 1
    cam, est = P.ofertas_de(e, 'camiseta'), P.ofertas_de(e, 'estadio')
    assert [o['marca'] for o in cam if o['renovacion']] == [marca_cam] and len(cam) == 3
    assert len(est) == 2 and marca_est not in {o['marca'] for o in est} and not any(o['renovacion'] for o in est)
    assert cs['manga']['rubro'] not in {o['rubro'] for o in cam + est}   # exclusividad con el que sigue
    correos = _correos(e)
    assert len(correos) == 1 and correos[0]['accion']['pantalla'] == 'patrocinios_screen'
    assert "Departamento comercial" in C.formatear(e, correos[0])
    rep = p['reputacion']; mi.balance = -1                               # cierre en quiebra
    P.cierre_contratos(e, random.Random(13))
    assert p['reputacion'] == rep + P.REP_QUIEBRA
    print("  test_cierre_contratos_vencen_y_ofertas: OK")


def test_revisar_jornada_ventanas():
    e = estado_carrera(); liga = e['liga']; p = P.datos(e)
    liga.jornada_actual = 1
    for c in p['contratos'].values():
        c['anios'] = 3                                                   # que solo venza la manga
    p['contratos']['manga'].update(anios=1, cumplido_ultima=False)
    P.cierre_contratos(e, random.Random(14))
    assert P.ofertas_de(e, 'manga')
    P.revisar_jornada(e)                                                 # ventana de inicio abierta: siguen
    assert P.ofertas_de(e, 'manga')
    n_correos = len(_correos(e))
    liga.jornada_actual = 5                                              # cerró la ventana: se retiran y avisa
    P.revisar_jornada(e)
    assert p['ofertas'] == [] and p['contratos']['manga'] is None and len(_correos(e)) == n_correos + 1
    P.revisar_jornada(e)
    assert len(_correos(e)) == n_correos + 1                             # no repite el aviso
    liga.jornada_actual = liga.num_jornadas // 2                         # invierno: ofertas nuevas, 15% peores
    P.revisar_jornada(e, random.Random(15))
    inv = P.ofertas_de(e, 'manga')
    assert inv and P.ofertas_de(e, 'camiseta') == []
    ref = P.valor_referencia(e, 'manga')
    assert all(o['fijo'] <= ref * P.PERFILES[o['perfil']][0] * P.FACTOR_INVIERNO * 1.05 + 1 for o in inv)
    ids = [o['id'] for o in inv]
    liga.jornada_actual += 1
    P.revisar_jornada(e, random.Random(16))
    assert [o['id'] for o in P.ofertas_de(e, 'manga')] == ids            # no regenera en la misma ventana
    print("  test_revisar_jornada_ventanas: OK")


def test_enganches_del_ciclo():
    import inspect
    from alpha_football.ui import resumen_temporada_screen as RT, match_screen as MS
    assert 'cierre_contratos' in inspect.getsource(F.cierre_temporada)
    fuente = inspect.getsource(RT)
    assert 'patrocinios' in fuente and 'evaluar_temporada(estado, posicion, temp_anterior)' in fuente
    assert 'cambio_division(estado, user_asc, user_des)' in fuente
    assert 'patrocinios' in inspect.getsource(MS.finalizar_jornada_liga)
    assert C.REMITENTES['patrocinador'] == "Patrocinador"
    print("  test_enganches_del_ciclo: OK")
```

Nombres a añadir en `TESTS`: `test_evaluar_temporada_bonos_y_reputacion, test_cambio_division, test_cierre_contratos_vencen_y_ofertas, test_revisar_jornada_ventanas, test_enganches_del_ciclo`.

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: 5 FAIL; `13/18 tests pasaron`.

- [ ] **Step 3: Añadir el bloque `T3-impl` al final de `alpha_football/patrocinios.py`**

<!-- bloque: T3-impl -->
```python


# --- ciclo de temporada --------------------------------------------------------------------

def _correo(estado: dict, asunto: str, lineas: list) -> None:
    try:
        from alpha_football import correo as C
        C.enviar(estado, 'patrocinador', asunto, "\n".join(lineas), C.accion('patrocinios_screen', "VER PATROCINIOS"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo de patrocinios: {e}")


def _texto_oferta(o: dict) -> str:
    return (f"{o['marca']} ({o['rubro']}{', renovación' if o.get('renovacion') else ''}): {_m(o['fijo'])} al año "
            f"+ bono de {_m(o['bono'])}, {o['anios']} año{'s' if o['anios'] != 1 else ''}. "
            f"Objetivo: {o['objetivo']['texto']}.")


def evaluar_temporada(estado: dict, posicion: int, temporada: int) -> Optional[dict]:
    """Con la tabla final todavía intacta: evalúa el objetivo de cada contrato, paga los bonos
    (al libro de `temporada`) y ajusta la reputación. Una sola vez por temporada."""
    try:
        from alpha_football.finanzas import registrar
        p, mi = datos(estado), estado.get('mi_equipo')
        if p.get('ultimo_cierre') == int(temporada):
            return None
        p['ultimo_cierre'] = int(temporada)
        lineas, total = [], 0
        for espacio, _peso in ESPACIOS:
            c = p['contratos'].get(espacio)
            if not c:
                continue
            ok = cumple(estado, c, posicion)
            c['cumplido_ultima'] = ok
            quien = f"{c['marca']} ({NOMBRE_ESPACIO[espacio].lower()})"
            if ok is True:
                bono = int(c.get('bono', 0) or 0)
                mi.balance = int(mi.balance) + bono
                registrar(estado, 'patrocinio', bono, int(temporada))
                total += bono
                _rep(p, REP_CUMPLE)
                lineas.append(f"{quien}: objetivo cumplido ({c['objetivo']['texto']}). Bono de {_m(bono)}.")
            elif ok is False:
                _rep(p, REP_FALLA)
                lineas.append(f"{quien}: objetivo no cumplido ({c['objetivo']['texto']}). Sin bono.")
            else:
                lineas.append(f"{quien}: su objetivo no aplicaba esta temporada (no jugó la copa).")
        if int(posicion) == 1 and int(getattr(estado.get('liga'), 'division', 1) or 1) == 1:
            _rep(p, REP_TITULO)
            lineas.append("El título de liga mejora la reputación comercial del club.")
        p['resumen_cierre'] = lineas
        return {'bonos': total, 'lineas': lineas}
    except Exception as e:
        logger.error(f"Error evaluando los patrocinios: {e}", exc_info=True)
        return None


def cambio_division(estado: dict, ascendio: bool, descendio: bool) -> None:
    """Cláusula de división de los contratos vigentes (ascenso ×1.30, descenso ×0.60) y reputación."""
    try:
        if not (ascendio or descendio):
            return
        p = datos(estado)
        factor = FACTOR_ASCENSO if ascendio else FACTOR_DESCENSO
        for c in p['contratos'].values():
            if c:
                c['fijo'], c['bono'] = int(c['fijo'] * factor), int(c['bono'] * factor)
        _rep(p, REP_ASCENSO if ascendio else REP_DESCENSO)
        p.setdefault('resumen_cierre', []).append(
            "Por el ascenso, los contratos vigentes suben un 30%." if ascendio
            else "Por el descenso, los contratos vigentes bajan un 40%.")
    except Exception as e:
        logger.error(f"Error aplicando la cláusula de división de los patrocinios: {e}", exc_info=True)


def cierre_contratos(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Cierre financiero (ya en la temporada nueva): −1 año, vencen los que llegan a 0 y llegan
    ofertas para los espacios vacíos. Cerrar en números rojos baja la reputación."""
    try:
        p, mi = datos(estado), estado.get('mi_equipo')
        azar = rng or random.Random()
        lineas = list(p.pop('resumen_cierre', []) or [])
        if int(mi.balance) < 0:
            _rep(p, REP_QUIEBRA)
            lineas.append("Cerrar la temporada en números rojos daña la reputación comercial del club.")
        p['ofertas'] = []
        vencidos = {}
        for espacio, _peso in ESPACIOS:
            c = p['contratos'].get(espacio)
            if not c:
                continue
            c['anios'] = int(c.get('anios', 1) or 1) - 1
            if c['anios'] <= 0:
                vencidos[espacio] = c
                p['contratos'][espacio] = None
                lineas.append(f"Venció el contrato con {c['marca']} ({NOMBRE_ESPACIO[espacio].lower()}).")
        for espacio, _peso in ESPACIOS:
            if p['contratos'].get(espacio):
                continue
            nuevas = generar_ofertas(estado, espacio, azar, anterior=vencidos.get(espacio))
            if nuevas:
                lineas.append(f"Ofertas para {NOMBRE_ESPACIO[espacio].lower()}:")
                lineas += [f"  · {_texto_oferta(o)}" for o in nuevas]
            else:
                lineas.append(f"Ninguna marca presentó oferta para {NOMBRE_ESPACIO[espacio].lower()}.")
        p['ultima_ventana'] = f"{int(estado.get('temporada', 1) or 1)}-inicio"
        if p['ofertas']:
            lineas.append("Tiene hasta el cierre de la ventana de pases para responder; un espacio vacío no cobra.")
        if lineas:
            _correo(estado, "Patrocinios: ofertas sobre la mesa" if p['ofertas'] else "Patrocinios: cierre de temporada", lineas)
        return {'vencidos': list(vencidos), 'ofertas': len(p['ofertas'])}
    except Exception as e:
        logger.error(f"Error en el cierre de los patrocinios: {e}", exc_info=True)
        return None


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Tras cada jornada: al cerrar la ventana se retiran las ofertas sin responder; al abrir la de
    invierno llegan ofertas (15% peores) para los espacios vacíos."""
    try:
        if estado.get('mi_equipo') is None:
            return
        p = datos(estado)
        ventana = _ventana(estado)
        vacios = [esp for esp, _w in ESPACIOS if not p['contratos'].get(esp)]
        nombres = ", ".join(NOMBRE_ESPACIO[esp].lower() for esp in vacios)
        if ventana == 'invierno':
            clave = f"{int(estado.get('temporada', 1) or 1)}-invierno"
            if p.get('ultima_ventana') == clave:
                return
            p['ultima_ventana'] = clave
            lineas = []
            for esp in vacios:
                nuevas = generar_ofertas(estado, esp, rng, factor=FACTOR_INVIERNO)
                lineas += [f"{NOMBRE_ESPACIO[esp]}: {_texto_oferta(o)}" for o in nuevas]
            if lineas:
                _correo(estado, "Patrocinios: ofertas de invierno",
                        lineas + ["A mitad de temporada las marcas pagan menos. Tiene hasta el cierre de la ventana."])
            elif vacios:
                _correo(estado, "Patrocinios: sin interesados",
                        [f"Ninguna marca presentó oferta para: {nombres}. Esos espacios siguen sin cobrar."])
        elif ventana is None and p['ofertas']:
            p['ofertas'] = []
            _correo(estado, "Patrocinios: ofertas retiradas",
                    ["Se cerró la ventana y las marcas retiraron las ofertas sin responder."]
                    + ([f"Sin patrocinador en: {nombres}. No cobrará por esos espacios hasta la próxima ventana."]
                       if vacios else []))
    except Exception as e:
        logger.error(f"Error revisando los patrocinios de la jornada: {e}", exc_info=True)
```

- [ ] **Step 4: Remitente en `correo.py`**

En `REMITENTES`, cambiar `'cantera': "Cantera"}   # v4.8.0: informe semestral` por:

```python
              'cantera': "Cantera",   # v4.8.0: informe semestral
              'patrocinador': "Patrocinador"}   # v4.9.0
```

En `FIRMAS`, cambiar `'cantera': "Coordinación de cantera de {club}"}` por:

```python
          'cantera': "Coordinación de cantera de {club}",
          'patrocinador': "Departamento comercial de {club}"}
```

- [ ] **Step 5: Enganches**

`alpha_football/ui/resumen_temporada_screen.py`, justo después del bloque
`except Exception as e_dir: logger.error(f"Error al evaluar el objetivo de la directiva: {e_dir}")` (misma indentación que ese `try`):

```python
            try:  # v4.9.0: objetivos y bonos de los patrocinios (con la tabla final aún intacta)
                from alpha_football import patrocinios as _patro
                _patro.evaluar_temporada(estado, posicion, temp_anterior)
            except Exception as e_pat:
                logger.error(f"Error evaluando los patrocinios: {e_pat}")
```

En el mismo archivo, justo después de `estado['liga_usuario_division'] = getattr(liga, 'division', 1)` (el del paso 3b):

```python
        try:  # v4.9.0: cláusula de ascenso/descenso de los patrocinios
            from alpha_football import patrocinios as _patro
            _patro.cambio_division(estado, user_asc, user_des)
        except Exception as e_pat:
            logger.error(f"Error en la cláusula de división de los patrocinios: {e_pat}")
```

`alpha_football/finanzas.py`, en `cierre_temporada`, justo antes del `return salidas` final:

```python
    if mi is not None:     # v4.9.0: vencen patrocinios y llegan las ofertas de la ventana de inicio
        try:
            from alpha_football import patrocinios as _P
            _P.cierre_contratos(estado)
        except Exception as e_pat:
            logger.error(f"Error en el cierre de los patrocinios: {e_pat}")
```

`alpha_football/ui/match_screen.py`, tras el bloque `# v4.8.0: cantera`:

```python
        try:  # v4.9.0: patrocinios (ofertas de invierno y ofertas que vencen con la ventana)
            from alpha_football import patrocinios as _patro
            _patro.revisar_jornada(estado)
        except Exception as e_pat:
            logger.error(f"Error revisando los patrocinios: {e_pat}")
```

- [ ] **Step 6: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: `18/18 tests pasaron`.
Run: `python -c "import alpha_football.ui.resumen_temporada_screen, alpha_football.ui.match_screen"` → Expected: sin error.

- [ ] **Step 7: Commit** (solo si Diego lo pidió)

---

### Task 4: Pantalla PATROCINIOS, hub, ayuda y atajos

**Files:**
- Create: `alpha_football/ui/patrocinios_screen.py` (bloque `T4-impl`)
- Modify: `alpha_football/ui/league_screen.py` (`TARJETAS['finanzas']`), `main.py` (`MODULOS_PANTALLA`), `alpha_football/ui/ayuda.py`, `alpha_football/ui/atajos.py`, `alpha_football/ui/finanzas_screen.py:100`
- Modify: `tests/test_hub_v240.py` (lista `'finanzas'`)
- Test: `tests/test_patrocinios.py` (bloque `T4-test`)

**Interfaces:**
- Consumes: Tasks 1–3 (`datos`, `ofertas_de`, `firmar`, `rechazar`, `negociar`, `prob_negociar`, `rescindir`, `multa_rescision`, `progreso`, `cobro_jornada`, `ingreso_anual`, `valor_referencia`, `_m`, `ESPACIOS`, `NOMBRE_ESPACIO`); `ui.objetivos_screen.barra(screen, rect, frac, color)`.
- Produces: `patrocinios_screen.render(screen, estado)`, `_rects()`, `_rect_espacio(i)`, `_rect_rescindir(i)`, `_rects_oferta(k) -> {'fila','firmar','prima','n1','n2','rechazar'}`, `R_OFERTAS`. Claves de `estado`: `'patro_esp'`, `'patro_of'`, `'patro_confirma'`, `'patro_msg'`.

- [ ] **Step 1: Añadir los tests (bloque `T4-test`) y sus nombres a `TESTS`**

<!-- bloque: T4-test -->
```python
def click(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def test_pantalla_patrocinios():
    from alpha_football.ui import patrocinios_screen as PS, league_screen
    assert ("PATROCINIOS", "Marcas, objetivos y ofertas", 'patrocinios_screen') in league_screen.TARJETAS['finanzas']
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']; liga.calendario = []; liga.jornada_actual = 5
    p = P.datos(e); mi.balance = 10 ** 12
    pygame.event.clear()
    assert PS.render(screen, e) is None
    click(PS._rect_espacio(1).center); PS.render(screen, e)
    assert e['patro_esp'] == 1
    # rescindir pide confirmación: primer clic marca, ESC cancela, dos clics rescinden
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    assert e['patro_confirma'] == 'manga' and p['contratos']['manga'] is not None
    key(pygame.K_ESCAPE)
    assert PS.render(screen, e) is None and e['patro_confirma'] is None
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    assert p['contratos']['manga'] is None and "rescindido" in e['patro_msg']
    assert PS.render(screen, e) is None                                  # espacio vacío sin ofertas
    a, b = P.generar_ofertas(e, 'manga', random.Random(17))
    PS.render(screen, e)
    click(PS._rects_oferta(1)['rechazar'].center); PS.render(screen, e)
    assert [o['id'] for o in P.ofertas_de(e, 'manga')] == [a['id']]
    prob = P.prob_negociar
    try:
        P.prob_negociar = lambda _e, _n: 2.0                             # negociación que siempre sale bien
        fijo = a['fijo']
        click(PS._rects_oferta(0)['n1'].center); PS.render(screen, e)
        assert a['fijo'] == int(fijo * 1.10) and a['negociada']
    finally:
        P.prob_negociar = prob
    click(PS._rects_oferta(0)['firmar'].center); PS.render(screen, e)
    assert p['contratos']['manga']['marca'] == a['marca'] and P.ofertas_de(e, 'manga') == []
    e['patro_esp'], e['patro_of'] = 7, 9                                 # índices fuera de rango: se acotan
    assert PS.render(screen, e) is None and e['patro_esp'] == 2 and e['patro_of'] == 0
    p['contratos']['estadio'] = None
    o = P.generar_ofertas(e, 'estadio', random.Random(18))[0]
    bal = mi.balance
    PS.render(screen, e); key(pygame.K_p); PS.render(screen, e)          # P: firmar con prima la oferta elegida
    assert p['contratos']['estadio']['marca'] == o['marca'] and mi.balance == bal + int(o['fijo'] * P.PRIMA_FRAC)
    key(pygame.K_ESCAPE)
    assert PS.render(screen, e) == 'league_screen'
    print("  test_pantalla_patrocinios: OK")


def test_pantalla_registrada_con_ayuda_y_atajos():
    import main
    from alpha_football.ui import ayuda, atajos
    assert 'patrocinios_screen' in main.nombres_pantallas()
    e = estado_carrera()
    its = ayuda.AYUDA['patrocinios_screen'](e)
    assert len(its) >= 3 and all(len(x) <= 110 for _r, _t, x in its)
    assert 'patrocinios_screen' in ayuda._TEXTO_TARJETA
    assert "Firmar" in atajos.texto('patrocinios_screen', e)
    print("  test_pantalla_registrada_con_ayuda_y_atajos: OK")
```

Nombres a añadir en `TESTS`: `test_pantalla_patrocinios, test_pantalla_registrada_con_ayuda_y_atajos`.

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: 2 FAIL; `18/20 tests pasaron`.

- [ ] **Step 3: Crear `alpha_football/ui/patrocinios_screen.py` con el bloque `T4-impl`**

<!-- bloque: T4-impl -->
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Patrocinios (Pygame)
v4.9.0: los 3 espacios (camiseta, manga, estadio) con su contrato, objetivo y años; reputación
comercial; y las ofertas del espacio elegido: firmar (con o sin prima), negociar o rechazar.
"""
from __future__ import annotations

import logging
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

from alpha_football import patrocinios as P
from alpha_football.ui.objetivos_screen import barra

logger = logging.getLogger(__name__)

ESPACIOS = [esp for esp, _w in P.ESPACIOS]
R_OFERTAS = pygame.Rect(16, 392, 1248, 304)        # termina en y=696 (barra de atajos)
OFERTA_Y0, OFERTA_H = 430, 86
PERFIL_TXT = {'conservadora': "Conservadora", 'equilibrada': "Equilibrada", 'ambiciosa': "Ambiciosa"}


def _rects() -> dict:
    return {'volver': pygame.Rect(1116, 12, 148, 40), 'reputacion': pygame.Rect(16, 54, 760, 24)}


def _rect_espacio(i: int) -> pygame.Rect:
    return pygame.Rect(16 + i * 421, 110, 405, 270)


def _rect_rescindir(i: int) -> pygame.Rect:
    r = _rect_espacio(i)
    return pygame.Rect(r.x + 16, r.bottom - 48, 170, 36)


def _rects_oferta(k: int) -> dict:
    y = OFERTA_Y0 + k * OFERTA_H
    return {'fila': pygame.Rect(24, y, R_OFERTAS.width - 16, OFERTA_H - 6),
            'firmar': pygame.Rect(770, y + 20, 104, 40), 'prima': pygame.Rect(882, y + 20, 104, 40),
            'n1': pygame.Rect(994, y + 20, 80, 40), 'n2': pygame.Rect(1082, y + 20, 80, 40),
            'rechazar': pygame.Rect(1170, y + 20, 86, 40)}


def _corto(texto: str, ancho: int, size: str = 'sm') -> str:
    try:
        f = get_font(size)
        if f.size(texto)[0] <= ancho:
            return texto
        while texto and f.size(texto + "…")[0] > ancho:
            texto = texto[:-1]
        return texto + "…"
    except Exception:
        return texto[:48]


def _salir(estado: dict) -> str:
    estado.pop('patro_msg', None)
    estado.pop('patro_confirma', None)
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        p = P.datos(estado)
        esp_i = max(0, min(int(estado.get('patro_esp', 0) or 0), 2))
        of_i = int(estado.get('patro_of', 0) or 0)
        confirma = estado.get('patro_confirma')
        rects = _rects()
        mouse_pos = pygame.mouse.get_pos()
        ofertas = P.ofertas_de(estado, ESPACIOS[esp_i])
        accion = None                                    # ('firmar'|'prima'|'n1'|'n2'|'rechazar', k) o ('rescindir', i)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rects['volver'].collidepoint(ev.pos):
                    return _salir(estado)
                hecho = False
                for i in range(3):
                    if p['contratos'].get(ESPACIOS[i]) and _rect_rescindir(i).collidepoint(ev.pos):
                        esp_i, accion, hecho = i, ('rescindir', i), True
                    elif _rect_espacio(i).collidepoint(ev.pos) and not hecho:
                        if i != esp_i:
                            of_i = 0
                        esp_i, confirma, hecho = i, None, True
                if not hecho:
                    for k in range(len(ofertas)):
                        ro = _rects_oferta(k)
                        for nombre in ('firmar', 'prima', 'n1', 'n2', 'rechazar'):
                            if ro[nombre].collidepoint(ev.pos):
                                of_i, accion = k, (nombre, k)
                        if accion is None and ro['fila'].collidepoint(ev.pos):
                            of_i = k
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    if confirma is None:
                        return _salir(estado)
                    confirma = None
                    estado.pop('patro_msg', None)
                elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    esp_i, of_i, confirma = (esp_i + (1 if ev.key == pygame.K_RIGHT else -1)) % 3, 0, None
                elif ev.key == pygame.K_UP:
                    of_i -= 1
                elif ev.key == pygame.K_DOWN:
                    of_i += 1
                elif ev.key == pygame.K_x or (ev.key == pygame.K_RETURN and confirma is not None):
                    accion = ('rescindir', esp_i)
                elif ev.key in (pygame.K_f, pygame.K_p, pygame.K_1, pygame.K_2, pygame.K_r):
                    accion = ({pygame.K_f: 'firmar', pygame.K_p: 'prima', pygame.K_1: 'n1', pygame.K_2: 'n2',
                               pygame.K_r: 'rechazar'}[ev.key], of_i)

        espacio = ESPACIOS[esp_i]
        ofertas = P.ofertas_de(estado, espacio)
        of_i = max(0, min(of_i, len(ofertas) - 1))
        if accion is not None:
            tipo, idx = accion
            if tipo == 'rescindir':
                if p['contratos'].get(espacio) is None:
                    confirma = None
                elif confirma == espacio:
                    _ok, estado['patro_msg'] = P.rescindir(estado, espacio)
                    confirma = None
                else:
                    confirma = espacio
                    estado['patro_msg'] = (f"¿Rescindir con {p['contratos'][espacio]['marca']}? Multa de "
                                           f"{P._m(P.multa_rescision(estado, espacio))} y −8 de reputación. "
                                           "Pulsa RESCINDIR otra vez (o Enter) · ESC cancela.")
            elif ofertas and 0 <= idx < len(ofertas):
                o = ofertas[idx]
                confirma = None
                if tipo == 'firmar':
                    _ok, estado['patro_msg'] = P.firmar(estado, o['id'])
                elif tipo == 'prima':
                    _ok, estado['patro_msg'] = P.firmar(estado, o['id'], con_prima=True)
                elif tipo in ('n1', 'n2'):
                    _ok, estado['patro_msg'] = P.negociar(estado, o['id'], 1 if tipo == 'n1' else 2)
                else:
                    P.rechazar(estado, o['id'])
                    estado['patro_msg'] = f"Rechazaste la oferta de {o['marca']}."
            ofertas = P.ofertas_de(estado, espacio)
            of_i = max(0, min(of_i, len(ofertas) - 1))
        estado['patro_esp'], estado['patro_of'], estado['patro_confirma'] = esp_i, of_i, confirma

        # --- dibujo ---
        draw_gradient_bg(screen)
        draw_text(screen, "PATROCINIOS", (16, 12), size='lg', color='dorado')
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))
        rep = int(p.get('reputacion', 50))
        draw_text(screen, f"Reputación comercial {rep}/100", (16, 56), size='sm', color='azul')
        barra(screen, pygame.Rect(270, 62, 200, 12), rep / 100, 'verde' if rep >= 50 else 'dorado' if rep >= 15 else 'rojo')
        draw_text(screen, f"Fijo anual: {P._m(P.ingreso_anual(estado))}  ·  Por jornada: {P._m(P.cobro_jornada(estado))}",
                  (490, 56), size='sm', color='blanco')
        if estado.get('patro_msg'):
            draw_text(screen, _corto(str(estado['patro_msg']), 1240), (16, 84), size='sm',
                      color='rojo' if confirma is not None else 'verde')

        n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))
        for i, esp in enumerate(ESPACIOS):
            r = _rect_espacio(i)
            draw_panel(screen, r)
            if i == esp_i:
                pygame.draw.rect(screen, COLORS['dorado'], r, width=2, border_radius=8)
            x, y = r.x + 16, r.y + 12
            n_of = len(P.ofertas_de(estado, esp))
            draw_text(screen, P.NOMBRE_ESPACIO[esp].upper() + (f"  ·  {n_of} oferta{'s' if n_of != 1 else ''}" if n_of else ""),
                      (x, y), size='sm', color='dorado')
            c = p['contratos'].get(esp)
            if not c:
                draw_text(screen, "SIN PATROCINADOR", (x, y + 34), size='md', color='rojo')
                draw_text(screen, f"Dejas de cobrar {P._m(P.valor_referencia(estado, esp) // n)} por jornada",
                          (x, y + 74), size='sm', color='blanco')
                draw_text(screen, "Las ofertas llegan en las ventanas de pases." if not n_of else "Elige una oferta abajo.",
                          (x, y + 100), size='sm', color='azul')
                continue
            draw_text(screen, _corto(c['marca'], r.width - 32, 'lg'), (x, y + 28), size='lg', color='blanco')
            draw_text(screen, f"{c['rubro'].capitalize()}  ·  {PERFIL_TXT.get(c['perfil'], c['perfil'])}", (x, y + 68), size='sm', color='azul')
            draw_text(screen, f"Fijo {P._m(c['fijo'])}/año  ·  Bono {P._m(c['bono'])}", (x, y + 94), size='sm', color='verde')
            draw_text(screen, _corto(c['objetivo']['texto'], r.width - 32), (x, y + 122), size='sm', color='blanco')
            frac = P.progreso(estado, c)
            barra(screen, pygame.Rect(x, y + 150, r.width - 32, 12), frac, 'verde' if frac >= 1.0 else 'dorado')
            anios = int(c.get('anios', 1))
            draw_text(screen, f"Le queda{'n' if anios != 1 else ''} {anios} año{'s' if anios != 1 else ''}",
                      (x, y + 172), size='sm', color='rojo' if anios <= 1 else 'blanco')
            rr = _rect_rescindir(i)
            draw_button(screen, rr, "CONFIRMAR" if confirma == esp else "RESCINDIR",
                        rr.collidepoint(mouse_pos) or confirma == esp)

        draw_panel(screen, R_OFERTAS)
        draw_text(screen, f"OFERTAS PARA {P.NOMBRE_ESPACIO[espacio].upper()}", (R_OFERTAS.x + 16, R_OFERTAS.y + 10),
                  size='sm', color='dorado')
        if not ofertas:
            texto = ("Este espacio ya tiene patrocinador." if p['contratos'].get(espacio)
                     else "No hay ofertas. Llegan al abrir la ventana de pases de inicio o de invierno.")
            draw_text(screen, texto, (R_OFERTAS.x + 16, OFERTA_Y0 + 8), size='md', color='blanco')
        for k, o in enumerate(ofertas[:3]):
            ro = _rects_oferta(k)
            if k == of_i:
                pygame.draw.rect(screen, (30, 45, 75), ro['fila'], border_radius=4)
            x, y = ro['fila'].x + 10, ro['fila'].y + 4
            titulo = f"{o['marca']}  ·  {o['rubro'].capitalize()}  ·  {PERFIL_TXT.get(o['perfil'], o['perfil'])}"
            draw_text(screen, _corto(titulo + ("  ·  RENOVACIÓN" if o.get('renovacion') else ""), 720, 'md'), (x, y),
                      size='md', color='dorado' if o.get('renovacion') else 'blanco')
            draw_text(screen, f"Fijo {P._m(o['fijo'])}/año  ·  Bono {P._m(o['bono'])}  ·  {o['anios']} año{'s' if o['anios'] != 1 else ''}"
                              f"  ·  Prima {P._m(int(o['fijo'] * P.PRIMA_FRAC))}", (x, y + 31), size='sm', color='verde')
            draw_text(screen, _corto("Objetivo: " + o['objetivo']['texto'], 720), (x, y + 54), size='sm', color='blanco')
            draw_button(screen, ro['firmar'], "FIRMAR", ro['firmar'].collidepoint(mouse_pos))
            draw_button(screen, ro['prima'], "PRIMA", ro['prima'].collidepoint(mouse_pos))
            if not o.get('negociada'):
                draw_button(screen, ro['n1'], "+10%", ro['n1'].collidepoint(mouse_pos))
                draw_button(screen, ro['n2'], "+20%", ro['n2'].collidepoint(mouse_pos))
            draw_button(screen, ro['rechazar'], "NO", ro['rechazar'].collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en patrocinios_screen: {e}", exc_info=True)
        return 'league_screen'
```

- [ ] **Step 4: Registro, tarjeta, ayuda, atajos y estimado de Finanzas**

`main.py`, en `MODULOS_PANTALLA`, tras `'finanzas_screen'`:

```python
    'patrocinios_screen': 'alpha_football.ui.patrocinios_screen',      # v4.9.0
```

`alpha_football/ui/league_screen.py`, en `TARJETAS['finanzas']`, tras la tarjeta CONTRATOS:

```python
        ("PATROCINIOS", "Marcas, objetivos y ofertas", 'patrocinios_screen'),   # v4.9.0
```

`alpha_football/ui/ayuda.py`: en `_TEXTO_TARJETA`, tras `'finanzas_screen'`:

```python
    'patrocinios_screen': "Tus 3 patrocinadores, sus objetivos y las ofertas para firmar, negociar o rechazar.",
```

En `_TEXTO_PESTANA`, cambiar `'finanzas': "Resumen económico y contratos.",` por `'finanzas': "Resumen económico, contratos y patrocinios.",`.

Antes del comentario `# ---------------------------------------------------------------- ojeador`:

```python
# ---------------------------------------------------------------- patrocinios (v4.9.0)
def _ayuda_patrocinios(estado: dict) -> list:
    from alpha_football.ui import patrocinios_screen as PS
    r = PS._rects()
    return [
        (r['reputacion'], "Reputación", "Sube al cumplir objetivos y baja al fallarlos, descender o rescindir. Mejora las ofertas."),
        (_union([PS._rect_espacio(i) for i in range(3)]), "Espacios",
         "Camiseta, manga y estadio: marca, fijo, bono, objetivo y años. ← → o clic para elegir."),
        (PS.R_OFERTAS, "Ofertas", "Firma (F), firma con prima (P), pide +10% o +20% (1, 2) o rechaza (R). Vencen con la ventana."),
        (r['volver'], "Volver", "Regresa al hub (también ESC)."),
    ]


```

Junto a `AYUDA['cantera_screen'] = _ayuda_cantera`:

```python
AYUDA['patrocinios_screen'] = _ayuda_patrocinios
```

`alpha_football/ui/atajos.py`, tras la línea de `'finanzas_screen'`:

```python
    'patrocinios_screen': "← → Espacio · ↑ ↓ Oferta · F Firmar · P Prima · 1 2 Negociar · R Rechazar · X Rescindir · H Ayuda · ESC Volver",
```

`alpha_football/ui/finanzas_screen.py:100`, reemplazar la línea `por_jornada = ...` por:

```python
        try:   # v4.9.0: el patrocinio por jornada sale de los contratos
            from alpha_football import patrocinios as _P
            patro_jornada = _P.cobro_jornada(estado)
        except Exception:
            patro_jornada = int(medio * F.PATROCINIO_FRAC / n)
        por_jornada = patro_jornada + int(medio * F.TAQUILLA_FRAC / n) - masa // n
```

`tests/test_hub_v240.py`, cambiar `'finanzas': ['finanzas_screen', 'plantilla_screen']}` por `'finanzas': ['finanzas_screen', 'plantilla_screen', 'patrocinios_screen']}     # v4.9.0`.

- [ ] **Step 5: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_patrocinios.py` → Expected: `20/20 tests pasaron`.
Run: `test_hub_v240.py`, `test_ayuda_v390.py`, `test_finanzas_v290.py` → Expected: sin FAIL.
Renderizar la pantalla a PNG (driver dummy) con un espacio vacío y ofertas, y revisar que nada se solape.

- [ ] **Step 6: Commit** (solo si Diego lo pidió)

---

### Task 5: Regresión completa y contexto

**Files:**
- Modify: `context.md` (fecha, versión v4.9.0 y bitácora)

- [ ] **Step 1: Suite completa**, un archivo a la vez con `PYTHONIOENCODING=utf-8`. Todo fallo se compara contra el código base (worktree de `HEAD`) para separar lo preexistente de lo causado por este trabajo; lo causado se arregla.
- [ ] **Step 2: `context.md`** — encabezado a v4.9.0 y entrada de bitácora "Patrocinios (v4.9.0)" con: módulo, fracciones nuevas, los tres enganches del ciclo, pantalla, tests.
- [ ] **Step 3: Commit** (solo si Diego lo pidió)
