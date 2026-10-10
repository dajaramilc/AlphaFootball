# La temporada por fechas (v0.4.13.0, sub-proyecto G2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (método elegido por Diego: **NATIVO**, tú solo, en una sesión nueva con Sonnet 5.5, sin subagentes). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sin commits:** Diego da el OK final. Nunca atribuir a Claude ni a una IA en git.
> **Orden obligatorio:** G1 (`2026-10-07-avance-por-dias-g1.md`) debe estar implementado ANTES de este plan. G3 (`2026-10-07-ultimo-dia-20-horas-g3.md`) va después.

**Goal:** La temporada se cuenta por fechas: el mercado abre y cierra en días del calendario (la J3 del 5 de septiembre ya no cuenta como "mercado abierto"), los ritmos de mitad de temporada y el fin de temporada se disparan por fecha, la IA mueve el mercado por días y el hub muestra la fecha y la fase primero.

**Architecture:** Módulo sin UI `alpha_football/temporada.py`: un solo sitio que sabe la fase (ventana abierta, mitad, fin) a partir de la fecha de hoy (el reloj de G1, o la fecha del partido de la jornada actual si no hay reloj). `market.ventana_*` conservan su nombre y reciben `estado` opcional; los llamados que deciden por el user o la IA lo pasan. Los ritmos de la temporada (cantera, patrocinios, préstamos, traspasos acordados) ya miran su propia clave y son idempotentes: `dias.revisar_dia` los revisa cada día y detiene CONTINUAR al abrir/cerrar el mercado. Los datos viejos (`vuelve` de préstamos, claves de ventana) se leen sin migración.

**Tech Stack:** Python 3.10 (`datetime`, `random`), pygame. Tests = scripts ejecutables (`python tests/test_x.py`) con ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-07-temporada-por-fechas-g2-design.md`. Depende de C (`calendario.py`) y de G1 (`dias.py`, `datos_carrera['calendario']['dia'|'agenda']`).

## Global Constraints

- Versión: **0.4.13.0**. Comentarios nuevos: `# v0.4.13.0`. No reescribir comentarios viejos. El título de la ventana y el badge del README siguen en 0.4.10.0: no se tocan.
- **Git: sin commits, push, stash, reset ni checkout de archivos.** Los planes y specs están sin commitear: no los reviertas.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor del cambio. Comentarios y textos del juego en español.
- Cada test corre con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` y termina en `N/N tests pasaron`. Hay tests que salen con código 0 aunque impriman `FAIL`: revisar siempre la salida. Corre solo los tests que cada tarea indica; la suite completa va una sola vez, al final (Task 10), en segundo plano.
- Los números de línea son aproximados: ubica cada cambio por el código citado. Si un bloque no existe tal cual (G1 puede haberlo cambiado un poco), adapta lo mínimo y anota la desviación.
- **Calendario** (constantes en `temporada.CALENDARIO`): Europa: temporada 1 jul → 30 jun; ventana de inicio 1 jul – 31 ago; mitad = ventana de invierno 1 – 31 ene. Sudamérica: temporada 1 ene → 31 dic; ventana de inicio 1 – 31 ene; ventana de invierno 1 jul – 31 ago (mitad = 1 jul). Cierres 31 de agosto y 31 de enero.
- Sin reloj, "hoy" = `calendario.fecha_liga(estado, jornada_actual)`. Los tests que fijan `liga.jornada_actual` siguen controlando la fecha, salvo en la J3 y la J13 europeas (y sus equivalentes sudamericanas), que ahora están cerradas: ese cambio es el objetivo.
- Lo que cuenta partidos sigue por jornada: pedidos de la directiva "en las próximas N jornadas", lesiones, sanciones, despidos de DT de la IA, `fechas_jornada` de copa y los "lo analizamos" (se responden al cerrar la jornada siguiente).
- Mismas probabilidades que hoy en ofertas, eventos y rondas de la IA (3 por ventana).

### Desviaciones del spec decididas al planificar

1. **Los "lo analizamos" siguen respondiéndose al cerrar la jornada siguiente** (por partidos); G3 les da hora de respuesta el último día.
2. **Los pedidos de la directiva se crean como hoy** (tras 1 partido y tras la mitad de los partidos jugados); solo el aviso de tope salarial y el espaldarazo usan la mitad por fecha.
3. **Las rondas de la IA por días** son 3 por ventana en días sorteados (sin el último día: la ronda de cierre es de G3). Con reloj no hay ronda de la IA al cerrar la jornada.
4. **`market.ventanas_mercado(n)` no cambia**: sigue siendo el ancla de C. Las jornadas de cada ventana (para `vuelve` y textos) salen de `temporada.ventana_jornadas`.

## Review Focus

1. **J3 y J13 con el reloj o sin él**: el mercado está cerrado aunque la jornada "toque"; abierto en J1, J2, J11, J12 europeas y J10–J12 sudamericanas (Tasks 1 y 2).
2. **Reloj de G1 nacido el 1 de agosto** (o en otra fecha) en un save: no se recalcula y el mercado abre por fecha (Task 6).
3. **Hueco largo antes de la J1** (1 jul → 15 ago): ofertas con tiradas proporcionales y solo dentro de la ventana; la IA hace sus 3 rondas (Task 6).
4. **Fin de temporada con partidos pendientes o movidos**: la temporada no termina antes del último partido y CONTINUAR no entra en bucle (Task 8).
5. **Préstamos y traspasos acordados con el mercado cerrado**: se concretan el primer día de la ventana; un `vuelve` viejo con jornada se traduce sin romper (Tasks 3 y 5).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/temporada.py` (nuevo) | Fechas de ventanas, mitad y fin; fase de hoy; jornadas de cada ventana; días de ronda de la IA |
| `alpha_football/market.py` | `ventana_actual`, `proxima_apertura`, `clave_ventana_traspaso`, `ventana_mercado_abierta` con `estado` opcional; `crear_oferta_ui` con `estado` |
| `alpha_football/traspasos_pendientes.py` | `mercado_abierto` por fecha; `fecha_apertura`, `texto_apertura` |
| `alpha_football/prestamos.py` | `_regreso`, `_vuelve` y textos por fecha |
| `alpha_football/cantera.py`, `salidas.py`, `directiva.py`, `negociacion.py`, `contraofertas.py`, `patrocinios.py`, `mercado_ia.py`, `finanzas.py` | ritmos y ventanas por fecha |
| `alpha_football/dias.py` | `revisar_dia`, hitos que detienen CONTINUAR, rondas de la IA, ofertas dentro de la ventana, fin de temporada |
| `alpha_football/ui/aviso_mercado.py` | cartel y franja por fecha |
| `alpha_football/ui/league_screen.py`, `calendario_screen.py`, `plantilla_screen.py`, `ojeador_screen.py`, `match_screen.py`, `ayuda.py` | hub con la fecha primero, calendario con ventanas, textos |
| `tests/test_temporada.py` (nuevo) | tests de G2 |

Cabecera del archivo de test nuevo (copiar tal cual):

```python
"""v0.4.13.0: la temporada por fechas (ventanas, ritmos de mitad, fin de temporada, hub)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T
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

### Task 1: `temporada.py`: las fechas de la temporada

**Files:**
- Create: `alpha_football/temporada.py`
- Test: `tests/test_temporada.py` (nuevo)

**Interfaces:**
- Consumes: `calendario.anio/continente/_n/sabados/fecha_liga/texto_fecha/MESES`, `dias.activo/hoy` (G1).
- Produces: `temporada.CALENDARIO`, `ORDEN = ('inicio', 'invierno')`, `hitos(estado, t=None) -> dict` (`inicio, cierre1, mitad, cierre2, fin`), `ventanas(estado, t=None) -> {'inicio': (abre, cierra), 'invierno': (abre, cierra)}`, `fecha(estado) -> date`, `ventana_actual(estado) -> Optional[str]`, `ventana_abierta(estado) -> bool`, `ventana_en(estado, d) -> bool`, `ultimo_dia(estado) -> bool`, `dias_para_cierre(estado) -> Optional[int]`, `siguiente_ventana(estado) -> (temporada, nombre)`, `proxima_apertura(estado) -> date`, `hito_del_dia(estado, d) -> 'abre' | 'cierra' | None`, `inicio/mitad/fin(estado) -> date`, `segunda_mitad(estado)`, `es_fin(estado)`, `texto_fase(estado) -> str`, `jornada_de(estado, d, t=None) -> int`, `ventana_jornadas(estado, nombre, t=None) -> (primera, ultima)`, `dias_de_ronda(estado) -> list[date]`, `es_dia_de_ronda(estado, d) -> bool`.

- [ ] **Step 1: Crear el test** con la cabecera, el pie y estos casos:

```python
def test_hitos_y_ventanas_de_cada_continente():
    e = _e()
    h = T.hitos(e)
    assert (h['inicio'], h['cierre1'], h['mitad'], h['cierre2'], h['fin']) == (
        date(2026, 7, 1), date(2026, 8, 31), date(2027, 1, 1), date(2027, 1, 31), date(2027, 6, 30))
    assert T.ventanas(e) == {'inicio': (date(2026, 7, 1), date(2026, 8, 31)),
                             'invierno': (date(2027, 1, 1), date(2027, 1, 31))}
    assert T.hitos(e, 2)['inicio'] == date(2027, 7, 1)                    # la temporada siguiente
    sa = _e('betplay'); hs = T.hitos(sa)
    assert (hs['inicio'], hs['cierre1'], hs['mitad'], hs['cierre2'], hs['fin']) == (
        date(2027, 1, 1), date(2027, 1, 31), date(2027, 7, 1), date(2027, 8, 31), date(2027, 12, 31))
    assert T.inicio(e) == date(2026, 7, 1) and T.mitad(e) == date(2027, 1, 1) and T.fin(e) == date(2027, 6, 30)


def test_fecha_sin_reloj_es_la_del_partido_y_con_reloj_la_del_reloj():
    e = _e()
    assert T.fecha(e) == CAL.fecha_liga(e, 1)
    e['liga'].jornada_actual = 3
    assert T.fecha(e) == CAL.fecha_liga(e, 3)
    D.hoy(e)                                                              # nace el reloj
    assert T.fecha(e) == D.hoy(e)
    CAL.asegurar(e)['dia'] = '2026-10-10'
    assert T.fecha(e) == date(2026, 10, 10)                               # con reloj manda el reloj, no la jornada
    assert T.fecha({}) == date(2026, 7, 1)                                # sin partida: el inicio


def test_el_mercado_esta_cerrado_en_la_j3_y_la_j13_aunque_la_jornada_toque():
    e = _e(); liga = e['liga']
    abiertas = {}
    for j in (1, 2, 3, 4, 10, 11, 12, 13, 14):
        liga.jornada_actual = j
        abiertas[j] = T.ventana_abierta(e)
    assert abiertas == {1: True, 2: True, 3: False, 4: False, 10: False, 11: True, 12: True, 13: False, 14: False}
    sa = _e('betplay'); l = sa['liga']
    for j, esperado in ((1, True), (2, True), (3, False), (9, False), (10, True), (11, True), (12, True), (13, False)):
        l.jornada_actual = j
        assert T.ventana_abierta(sa) == esperado, j


def test_ventana_actual_cierres_y_proxima_apertura():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-31'
    assert T.ventana_actual(e) == 'inicio' and T.ultimo_dia(e) and T.dias_para_cierre(e) == 0
    assert T.proxima_apertura(e) == date(2027, 1, 1) and T.siguiente_ventana(e) == (1, 'inicio')
    cal['dia'] = '2026-09-01'
    assert T.ventana_actual(e) is None and not T.ultimo_dia(e) and T.dias_para_cierre(e) is None
    assert T.siguiente_ventana(e) == (1, 'invierno') and T.hito_del_dia(e, date(2026, 9, 1)) == 'cierra'
    cal['dia'] = '2027-02-10'
    assert T.proxima_apertura(e) == date(2027, 7, 1) and T.siguiente_ventana(e) == (2, 'inicio')
    assert T.hito_del_dia(e, date(2026, 7, 1)) == 'abre' and T.hito_del_dia(e, date(2026, 7, 2)) is None


def test_mitad_fin_y_texto_de_la_fase():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-12-31'
    assert not T.segunda_mitad(e) and T.texto_fase(e) == "Primera mitad"
    cal['dia'] = '2027-01-01'
    assert T.segunda_mitad(e) and T.texto_fase(e) == "Mercado abierto · cierra en 30 días"
    cal['dia'] = '2027-01-31'
    assert T.texto_fase(e) == "Mercado abierto · último día"
    cal['dia'] = '2027-02-01'
    assert T.texto_fase(e) == "Segunda mitad" and not T.es_fin(e)
    cal['dia'] = '2027-06-30'
    assert T.es_fin(e) and T.texto_fase(e).startswith("Temporada terminada")


def test_jornadas_de_cada_ventana_y_rondas_de_la_ia():
    e = _e()
    assert T.jornada_de(e, date(2026, 7, 1)) == 1 and T.jornada_de(e, date(2026, 9, 1)) == 3
    assert T.jornada_de(e, date(2027, 1, 1)) == 11
    assert T.ventana_jornadas(e, 'inicio') == (1, 2) and T.ventana_jornadas(e, 'invierno') == (11, 12)
    sa = _e('betplay')
    assert T.ventana_jornadas(sa, 'inicio') == (1, 2) and T.ventana_jornadas(sa, 'invierno') == (10, 12)
    r = T.dias_de_ronda(e)
    assert len(r) == 6 and r == T.dias_de_ronda(e)                         # 3 por ventana, estable
    cierres = {b for _a, b in T.ventanas(e).values()}
    assert all(T.ventana_en(e, d) and d not in cierres for d in r)         # dentro de la ventana, nunca el último día
    assert T.es_dia_de_ronda(e, r[0]) and not T.es_dia_de_ronda(e, date(2026, 12, 1))
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: falla al importar (`cannot import name 'temporada'`).

- [ ] **Step 3: Crear `alpha_football/temporada.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — La temporada por fechas (v0.4.13.0)
Un solo sitio que sabe en qué fase de la temporada estamos, a partir de la FECHA de hoy (el reloj de
dias.py; sin reloj, el día del partido de la jornada actual). El mercado abre y cierra en días del
calendario, no en jornadas; la mitad y el fin de temporada también son fechas.
Sin UI.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

# (mes, día, años a sumar al año en que empieza la temporada)
CALENDARIO = {
    'europa': {'inicio': (7, 1, 0), 'cierre1': (8, 31, 0), 'mitad': (1, 1, 1), 'cierre2': (1, 31, 1),
               'fin': (6, 30, 1)},
    'sudamerica': {'inicio': (1, 1, 0), 'cierre1': (1, 31, 0), 'mitad': (7, 1, 0), 'cierre2': (8, 31, 0),
                   'fin': (12, 31, 0)},
}
ORDEN = ('inicio', 'invierno')           # orden de apertura dentro de la temporada (en los dos continentes)
RONDAS_IA_POR_VENTANA = 3


def _anio(estado: dict, t: Optional[int] = None) -> int:
    """Año en que empieza la temporada número `t` (por defecto la actual)."""
    base = CAL.anio(estado)
    return base if t is None else base + int(t) - int(estado.get('temporada', 1) or 1)


def hitos(estado: dict, t: Optional[int] = None) -> dict:
    """{'inicio', 'cierre1', 'mitad', 'cierre2', 'fin'} (fechas) de la temporada `t`."""
    plan = CALENDARIO.get(CAL.continente(estado), CALENDARIO['europa'])
    a = _anio(estado, t)
    return {k: date(a + v[2], v[0], v[1]) for k, v in plan.items()}


def ventanas(estado: dict, t: Optional[int] = None) -> dict:
    h = hitos(estado, t)
    return {'inicio': (h['inicio'], h['cierre1']), 'invierno': (h['mitad'], h['cierre2'])}


def inicio(estado: dict) -> date:
    return hitos(estado)['inicio']


def mitad(estado: dict) -> date:
    return hitos(estado)['mitad']


def fin(estado: dict) -> date:
    return hitos(estado)['fin']


def fecha(estado: dict) -> date:
    """Hoy: el reloj (dias.hoy) si la partida lo tiene; si no, el día del partido de la jornada actual."""
    try:
        from alpha_football import dias
        if dias.activo(estado):
            return dias.hoy(estado)
    except Exception as e:
        logger.error(f"temporada: no se pudo leer el reloj: {e}")
    liga = estado.get('liga')
    if liga is None or estado.get('mi_equipo') is None:
        return inicio(estado)
    return CAL.fecha_liga(estado, int(getattr(liga, 'jornada_actual', 1) or 1))


def ventana_actual(estado: dict) -> Optional[str]:
    """'inicio' | 'invierno' si hoy el mercado está abierto; None si no."""
    h = fecha(estado)
    return next((n for n, (a, b) in ventanas(estado).items() if a <= h <= b), None)


def ventana_abierta(estado: dict) -> bool:
    return ventana_actual(estado) is not None


def ventana_en(estado: dict, d: date) -> bool:
    """¿El día `d` cae dentro de una ventana de mercado de esta temporada?"""
    return any(a <= d <= b for a, b in ventanas(estado).values())


def ultimo_dia(estado: dict) -> bool:
    """¿Hoy es un cierre de mercado (31 de agosto / 31 de enero)?"""
    h = fecha(estado)
    return any(h == b for _a, b in ventanas(estado).values())


def dias_para_cierre(estado: dict) -> Optional[int]:
    n = ventana_actual(estado)
    return None if n is None else (ventanas(estado)[n][1] - fecha(estado)).days


def siguiente_ventana(estado: dict) -> tuple:
    """(temporada, nombre): la ventana abierta hoy o, si el mercado está cerrado, la próxima."""
    t, h = int(estado.get('temporada', 1) or 1), fecha(estado)
    v = ventanas(estado)
    for n in ORDEN:
        if h <= v[n][1]:
            return t, n
    return t + 1, ORDEN[0]


def proxima_apertura(estado: dict) -> date:
    """Primer día de la próxima ventana que todavía no abrió (la de inicio de la temporada siguiente, si no hay más)."""
    t, h = int(estado.get('temporada', 1) or 1), fecha(estado)
    v = ventanas(estado)
    for n in ORDEN:
        if v[n][0] > h:
            return v[n][0]
    return ventanas(estado, t + 1)['inicio'][0]


def hito_del_dia(estado: dict, d: date) -> Optional[str]:
    """'abre' el primer día de una ventana, 'cierra' el día después de su cierre; None el resto."""
    for a, b in ventanas(estado).values():
        if d == a:
            return 'abre'
        if d == b + timedelta(days=1):
            return 'cierra'
    return None


def segunda_mitad(estado: dict) -> bool:
    return fecha(estado) >= mitad(estado)


def es_fin(estado: dict) -> bool:
    return fecha(estado) >= fin(estado)


def texto_fase(estado: dict) -> str:
    """'Mercado abierto · cierra en 19 días', 'Primera mitad', 'Segunda mitad', 'Temporada terminada · fin 30 jun'."""
    n = ventana_actual(estado)
    if n is not None:
        d = dias_para_cierre(estado)
        return "Mercado abierto · último día" if d == 0 else f"Mercado abierto · cierra en {d} día{'s' if d != 1 else ''}"
    if es_fin(estado):
        return f"Temporada terminada · fin {CAL.texto_fecha(fin(estado), False)}"
    return "Segunda mitad" if segunda_mitad(estado) else "Primera mitad"


def _sabs(estado: dict, t: Optional[int] = None) -> tuple:
    return CAL.sabados(CAL._n(estado), CAL.continente(estado), _anio(estado, t))


def jornada_de(estado: dict, d: date, t: Optional[int] = None) -> int:
    """Primera jornada de la temporada `t` cuyo sábado base cae el día `d` o después (n + 1 si ninguna)."""
    sabs = _sabs(estado, t)
    return next((i + 1 for i, s in enumerate(sabs) if s >= d), len(sabs) + 1)


def ventana_jornadas(estado: dict, nombre: str, t: Optional[int] = None) -> tuple:
    """(primera, última) jornada que cae dentro de la ventana (vacía si última < primera)."""
    a, b = ventanas(estado, t)[nombre]
    return jornada_de(estado, a, t), jornada_de(estado, b + timedelta(days=1), t) - 1


def dias_de_ronda(estado: dict) -> list:
    """Los días (sorteados con semilla, sin el último día) en que la IA hace su ronda de fichajes."""
    out: list = []
    for nombre, (a, b) in ventanas(estado).items():
        dias = [a + timedelta(days=k) for k in range((b - a).days)]
        azar = random.Random(f"rondas-{CAL.anio(estado)}-{nombre}")
        out += sorted(azar.sample(dias, min(RONDAS_IA_POR_VENTANA, len(dias))))
    return sorted(out)


def es_dia_de_ronda(estado: dict, d: date) -> bool:
    return d in dias_de_ronda(estado)
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `6/6 tests pasaron`.

---

### Task 2: El mercado por fecha en `market.py` y en quienes deciden

**Files:**
- Modify: `alpha_football/market.py`, `alpha_football/traspasos_pendientes.py`, `alpha_football/salidas.py`, `alpha_football/contraofertas.py`, `alpha_football/negociacion.py`, `alpha_football/mercado_ia.py`, `alpha_football/patrocinios.py`, `alpha_football/ui/ojeador_screen.py`, `alpha_football/ui/match_screen.py`, `alpha_football/dias.py` (`_entregar_oferta` de G1)
- Test: `tests/test_temporada.py`

**Interfaces:**
- Consumes: `temporada.ventana_actual/ventana_abierta/ventana_jornadas/proxima_apertura/jornada_de` (Task 1).
- Produces: `market.ventana_actual(jornada, n, estado=None)`, `market.proxima_apertura(jornada, n, estado=None) -> int`, `market.clave_ventana_traspaso(temporada, jornada, n, estado=None)`, `market.ventana_mercado_abierta(jornada, n, estado=None)`, `market.crear_oferta_ui(..., estado=None)`. Con `estado` (partida con liga) deciden por fecha; sin él, la lógica vieja por jornada.

- [ ] **Step 1: Tests** — agregar a `tests/test_temporada.py`:

```python
def test_market_usa_las_fechas_cuando_recibe_el_estado():
    from alpha_football import market
    e = _e(); liga = e['liga']; liga.jornada_actual = 3
    assert market.ventana_mercado_abierta(3, 22) is True                   # sin estado: la regla vieja por jornada
    assert market.ventana_mercado_abierta(3, 22, estado=e) is False        # con estado: la J3 (5 sep) ya cerró
    liga.jornada_actual = 2
    assert market.ventana_mercado_abierta(2, 22, estado=e) is True
    assert market.ventana_actual(2, 22, estado=e) == (1, 2, 'inicio')
    assert market.clave_ventana_traspaso(1, 2, 22, estado=e) == '1-verano'
    liga.jornada_actual = 3
    assert market.clave_ventana_traspaso(1, 3, 22, estado=e) == '' and market.proxima_apertura(3, 22, estado=e) == 11
    liga.jornada_actual = 11
    assert market.clave_ventana_traspaso(1, 11, 22, estado=e) == '1-invierno'
    liga.jornada_actual = 13
    assert market.proxima_apertura(13, 22, estado=e) == 1                  # la de inicio de la temporada siguiente


def test_los_que_deciden_leen_la_fecha():
    from alpha_football import traspasos_pendientes as TP, salidas as S
    e = _e(); liga = e['liga']
    liga.jornada_actual = 3
    assert not TP.mercado_abierto(e) and not S._ventana_abierta(e)
    liga.jornada_actual = 2
    assert TP.mercado_abierto(e) and S._ventana_abierta(e)


def test_la_oferta_de_la_ia_respeta_la_fecha_de_la_ventana():
    from alpha_football import market
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; rivales = [x for x in liga.equipos if x.id != mi.id]
    liga.jornada_actual = 3                                                 # 5 de septiembre: cerrado
    assert market.crear_oferta_ui(mi, rivales, 3, 22, prob=1.0, estado=e) is None
    liga.jornada_actual = 2
    assert market.crear_oferta_ui(mi, rivales, 2, 22, prob=1.0, estado=e) is not None
```

- [ ] **Step 2: Correr y ver que falla** (`unexpected keyword argument 'estado'`).

- [ ] **Step 3: `market.py`** — reemplazar `ventana_actual`, `proxima_apertura` y `clave_ventana_traspaso` por:

```python
def _con_fechas(estado) -> bool:
    """v0.4.13.0: con una partida que ya tiene liga las ventanas se deciden por fecha (temporada.py)."""
    return isinstance(estado, dict) and estado.get('liga') is not None and estado.get('mi_equipo') is not None


def ventana_actual(jornada: int, num_jornadas: int, estado: Any = None) -> Optional[tuple]:
    """La ventana abierta en esa jornada (primera, última, nombre) o None. Con `estado`, por fecha."""
    if _con_fechas(estado):
        from alpha_football import temporada as T
        nombre = T.ventana_actual(estado)
        if nombre is None:
            return None
        primera, ultima = T.ventana_jornadas(estado, nombre)
        return (primera, ultima, nombre)
    return next((v for v in ventanas_mercado(num_jornadas) if v[0] <= int(jornada) <= v[1]), None)


def proxima_apertura(jornada: int, num_jornadas: int, estado: Any = None) -> int:
    """Jornada en que abre la próxima ventana (1 = la de inicio de la temporada siguiente). Con `estado`, por fecha."""
    if _con_fechas(estado):
        from alpha_football import temporada as T
        a = T.proxima_apertura(estado)
        return 1 if a > T.fin(estado) else T.jornada_de(estado, a)
    return next((v[0] for v in ventanas_mercado(num_jornadas) if v[0] > int(jornada)), 1)


def clave_ventana_traspaso(temporada: int, jornada: int, num_jornadas: int, estado: Any = None) -> str:
    """Ventana de traspasos en curso ('<T>-verano' = inicio, '<T>-invierno'). '' con el mercado cerrado."""
    v = ventana_actual(jornada, num_jornadas, estado)
    if v is None:
        return ''
    return f"{int(temporada)}-{'invierno' if v[2] == 'invierno' else 'verano'}"
```

(el cuerpo viejo de las tres funciones, con sus docstrings, se reemplaza completo; las tres están seguidas en `market.py`).

En `traspasado_en_ventana` reemplazar:

```python
        return marca == clave_ventana_traspaso(int(estado.get('temporada', 1) or 1),
                                               int(getattr(liga, 'jornada_actual', 1) or 1),
                                               int(getattr(liga, 'num_jornadas', 22) or 22))
```

por:

```python
        return marca == clave_ventana_traspaso(int(estado.get('temporada', 1) or 1),
                                               int(getattr(liga, 'jornada_actual', 1) or 1),
                                               int(getattr(liga, 'num_jornadas', 22) or 22), estado)
```

Reemplazar `ventana_mercado_abierta`:

```python
def ventana_mercado_abierta(jornada: int, num_jornadas: int, estado: Any = None) -> bool:
    """El mercado está abierto en las jornadas 1-3 y en el invierno (mitad de temporada). v0.4.13.0:
    con `estado`, abierto en los días de las ventanas (temporada.py), no en las jornadas."""
    try:
        return ventana_actual(jornada, num_jornadas, estado) is not None
    except Exception:
        return False
```

En `generar_ofertas_recibidas` reemplazar:

```python
        if not ventana_mercado_abierta(jornada, num_jornadas):
            return []
```

por:

```python
        if not ventana_mercado_abierta(jornada, num_jornadas, estado):
            return []
```

En `crear_oferta_ui` reemplazar la firma `rng: Optional[random.Random] = None, prob: float = PROB_OFERTA_POR_JORNADA) -> Optional[dict]:` por `rng: Optional[random.Random] = None, prob: float = PROB_OFERTA_POR_JORNADA,\n                    estado: Any = None) -> Optional[dict]:` y reemplazar:

```python
        if not ventana_mercado_abierta(jornada, num_jornadas):
            return None
        # a préstamo: no reciben ofertas de traspaso (prestamos.py)
```

por:

```python
        if not ventana_mercado_abierta(jornada, num_jornadas, estado):
            return None
        # a préstamo: no reciben ofertas de traspaso (prestamos.py)
```

- [ ] **Step 4: Quienes deciden** — cinco cambios mecánicos (agregar `estado`):

`alpha_football/traspasos_pendientes.py`, en `mercado_abierto`:

```python
    return ventana_mercado_abierta(int(getattr(liga, 'jornada_actual', 1) or 1),
                                   int(getattr(liga, 'num_jornadas', 22) or 22))
```

→

```python
    return ventana_mercado_abierta(int(getattr(liga, 'jornada_actual', 1) or 1),
                                   int(getattr(liga, 'num_jornadas', 22) or 22), estado=estado)
```

y en `jornada_apertura`:

```python
    return proxima_apertura(int(getattr(liga, 'jornada_actual', 1) or 1),
                            int(getattr(liga, 'num_jornadas', 22) or 22))
```

→

```python
    return proxima_apertura(int(getattr(liga, 'jornada_actual', 1) or 1),
                            int(getattr(liga, 'num_jornadas', 22) or 22), estado=estado)
```

`alpha_football/salidas.py`, en `_ventana_abierta`: igual, agregar `, estado=estado` al `ventana_mercado_abierta(...)`.

`alpha_football/contraofertas.py` (en `_ubicar_contrato`): `not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas)` → `not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas, estado=estado)`.

`alpha_football/negociacion.py`: en `reanudar_compra`, `not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas)` → con `, estado=estado`; y en `registrar_pase`, el bloque:

```python
            jugador.ventana_traspaso = clave_ventana_traspaso(
                int(estado.get('temporada', 1) or 1), int(getattr(liga, 'jornada_actual', 1) or 1),
                int(getattr(liga, 'num_jornadas', 22) or 22))
```

→ el mismo con `, estado=estado)` al final.

`alpha_football/ui/ojeador_screen.py`: `ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas)` → con `, estado=estado`.

- [ ] **Step 5: IA, patrocinios y cierre de jornada**

`alpha_football/mercado_ia.py` (en `ronda_fichajes_ia`), reemplazar:

```python
        from alpha_football.market import ventana_actual
        liga_u = estado.get('liga')
        v = ventana_actual(int(getattr(liga_u, 'jornada_actual', 1) or 1),
                           int(getattr(liga_u, 'num_jornadas', 22) or 22))
        en_inicio = bool(v) and v[2] == 'inicio'
```

por:

```python
        from alpha_football import temporada as _T      # v0.4.13.0: por fecha
        en_inicio = _T.ventana_actual(estado) == 'inicio'
```

`alpha_football/patrocinios.py`, `_ventana`:

```python
    from alpha_football.market import ventana_actual
    liga = estado.get('liga')
    v = ventana_actual(int(getattr(liga, 'jornada_actual', 1) or 1), int(getattr(liga, 'num_jornadas', 22) or 22))
    return v[2] if v else None
```

→

```python
    from alpha_football import temporada as T      # v0.4.13.0: por fecha
    return T.ventana_actual(estado) if estado.get('liga') is not None else None
```

`alpha_football/ui/match_screen.py`, en `finalizar_jornada_liga`: (a) el bloque de la ronda de la IA:

```python
            if _mk.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
                from alpha_football.mercado_ia import ronda_fichajes_ia
                ronda_fichajes_ia(estado, 'ventana')
```

→

```python
            from alpha_football import dias as _dias_ia      # v0.4.13.0: con reloj, la IA hace sus rondas en días de la ventana
            if _mk.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas, estado=estado) and not _dias_ia.activo(estado):
                from alpha_football.mercado_ia import ronda_fichajes_ia
                ronda_fichajes_ia(estado, 'ventana')
```

(b) `if _mk2.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):` → con `, estado=estado`; (c) en la rama vieja de ofertas (G1): `market.crear_oferta_ui(mi_equipo, rivales, liga.jornada_actual, liga.num_jornadas)` → con `, estado=estado`.

`alpha_football/dias.py`, en `_entregar_oferta` (G1): `market.crear_oferta_ui(mi, rivales, liga.jornada_actual, liga.num_jornadas, prob=1.0)` → con `, estado=estado`.

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `9/9 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py; PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: pueden fallar los tests de G1/C que fijan `liga.jornada_actual = 2` o `= 5` y esperan la regla vieja, o que usan el reloj del 1 de agosto; **no se ajustan todavía** (el reloj de G1 cambia en el Task 6). Anota cuáles.

---

### Task 3: Las aperturas y lo acordado, en fechas

**Files:**
- Modify: `alpha_football/traspasos_pendientes.py`, `alpha_football/finanzas.py`, `alpha_football/negociacion.py`, `alpha_football/ui/plantilla_screen.py`
- Test: `tests/test_temporada.py`

**Interfaces:**
- Consumes: `temporada.proxima_apertura` (Task 1), `market.proxima_apertura(.., estado)` (Task 2).
- Produces: `traspasos_pendientes.fecha_apertura(estado) -> date`, `texto_apertura(estado, corto=False) -> str` ('vie 1 ene 2027' / 'vie 1 ene'); `diferir_venta`/`diferir_compra` guardan además `'fecha'` (ISO) junto al `'jornada'` que ya guardan.

- [ ] **Step 1: Tests** — agregar:

```python
def test_lo_acordado_con_el_mercado_cerrado_dice_la_fecha_y_se_concreta_al_abrir():
    from alpha_football import traspasos_pendientes as TP
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; liga.jornada_actual = 3          # 5 de septiembre: cerrado
    assert TP.fecha_apertura(e) == date(2027, 1, 1) and TP.jornada_apertura(e) == 11
    assert TP.texto_apertura(e) == "el " + CAL.texto_fecha(date(2027, 1, 1)) and TP.texto_apertura(e, True) == "vie 1 ene"
    j = mi.jugadores[5]; comprador = liga.equipos[1]
    aviso = TP.diferir_venta(e, j, comprador, 1_000_000)
    assert "1 ene 2027" in aviso and TP.pendiente_de(e, j)['fecha'] == '2027-01-01'
    liga.jornada_actual = 11                                                          # 2 de enero: abierto
    assert TP.mercado_abierto(e) and TP.ejecutar(e) == 1 and TP.pendiente_de(e, j) is None
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'fecha_apertura'`).

- [ ] **Step 3: `traspasos_pendientes.py`** — reemplazar `_cuando` y agregar los dos helpers justo después de `jornada_apertura`:

```python
def fecha_apertura(estado: dict):
    """v0.4.13.0: el día en que vuelve a abrir el mercado."""
    from alpha_football import temporada as T
    return T.proxima_apertura(estado)


def texto_apertura(estado: dict, corto: bool = False) -> str:
    """'el vie 1 ene 2027' (o 'vie 1 ene' si `corto`)."""
    from alpha_football import calendario as CAL
    f = fecha_apertura(estado)
    return CAL.texto_fecha(f, False) if corto else f"el {CAL.texto_fecha(f)}"


def _cuando(estado: dict, j_ap: int) -> str:
    """v0.4.13.0: 'el vie 1 ene 2027, en cuanto se abra el mercado' (la fecha manda; `j_ap` queda por compatibilidad)."""
    return f"{texto_apertura(estado)}, en cuanto se abra el mercado"
```

(el cuerpo viejo de `_cuando`, con su docstring `v0.4.11.0: 'en la jornada N'…`, se reemplaza completo). En `diferir_venta` y `diferir_compra`, en el dict que se agrega a `_pendientes(estado)`, sumar `'fecha': fecha_apertura(estado).isoformat()` junto a la clave `'jornada': j_ap`.

- [ ] **Step 4: Textos con la fecha** — cuatro cambios:

`alpha_football/finanzas.py` (venta forzada): `(se va en la jornada {TP.jornada_apertura(estado)})` → `(se va {TP.texto_apertura(estado)})`.

`alpha_football/negociacion.py` (`fichar`): `f"Ya está acordado: llega en la jornada {TP.jornada_apertura(estado)}."` → `f"Ya está acordado: llega {TP.texto_apertura(estado)}."`; y (`_fichar_diferido`): `f"¡Acuerdo cerrado! {jugador.nombre_completo} llega en la jornada {TP.jornada_apertura(estado)}."` → `f"¡Acuerdo cerrado! {jugador.nombre_completo} llega {TP.texto_apertura(estado)}."`.

`alpha_football/ui/plantilla_screen.py` (panel PRÉSTAMOS): los tres `f" · en J{jornada_apertura(estado)}"` → `f" · en {texto_apertura(estado, True)}"` (importar `texto_apertura` junto a `jornada_apertura` en el `from alpha_football.traspasos_pendientes import ...` de esa función); y en la ficha, `f" · VENDIDO (se va J{p['jornada']})"` → `f" · VENDIDO (se va {p.get('fecha', 'al abrir')})"` con la fecha corta: usar `__import__('alpha_football.calendario', fromlist=['x']).texto_fecha(date.fromisoformat(p['fecha']), False)` si `p.get('fecha')`; si no, conservar `J{p['jornada']}`.

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `10/10 tests pasaron`.
Run (uno por uno): `test_ventana_traspaso.py`, `test_prestamos.py`, `test_negociaciones_v270.py`.
Expected: pueden fallar los que afirman "llega en la jornada N" o dan por abierta la J3; se ajustan en el Task 10.

---

### Task 4: Los ritmos de mitad de temporada, por fecha

**Files:**
- Modify: `alpha_football/cantera.py`, `alpha_football/salidas.py`, `alpha_football/directiva.py`, `alpha_football/negociacion.py`
- Test: `tests/test_temporada.py`

**Interfaces:**
- Consumes: `temporada.segunda_mitad/mitad/siguiente_ventana` (Task 1).
- Produces: `cantera._hito` y `proximo_informe` por fecha; `salidas.revisar_renovaciones` desde `segunda_mitad`; `directiva.avisar_tope_salarial` y `pedir_espaldarazo` con la mitad por fecha; `negociacion._clave_ventana` = `temporada.siguiente_ventana`.

- [ ] **Step 1: Tests** — agregar:

```python
def _sano(e):
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
        j.pide_salir = j.salida_forzada = j.transferible = False
        j.prestamo = None


def test_los_ritmos_de_mitad_cambian_en_la_fecha_no_en_la_jornada():
    from alpha_football import cantera as CA
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-12-31'
    assert CA._hito(e) == '1-inicio' and CA.proximo_informe(e) == CAL.texto_fecha(date(2027, 1, 1), False)
    cal['dia'] = '2027-01-01'
    assert CA._hito(e) == '1-mitad' and CA.proximo_informe(e) == "inicio de la próxima temporada"


def test_quiere_renovar_solo_desde_la_mitad_por_fecha():
    from alpha_football import salidas as S
    e = _e(); D.hoy(e); cal = CAL.asegurar(e); _sano(e)
    j = e['mi_equipo'].jugadores[0]; j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    cal['dia'] = '2026-12-31'
    assert S.revisar_renovaciones(e, random.Random(1)) == []
    cal['dia'] = '2027-01-01'
    assert S.revisar_renovaciones(e, random.Random(1))


def test_el_espaldarazo_y_el_tope_usan_la_mitad_por_fecha():
    from alpha_football import directiva as DI
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    DI.definir_objetivo(e)
    cal['dia'] = '2027-01-01'
    ok, msg = DI.pedir_espaldarazo(e, 0)
    assert not ok and "mitad" in msg
    cal['dia'] = '2026-12-31'
    ok, msg = DI.pedir_espaldarazo(e, 0)
    assert "mitad" not in msg                                              # puede fallar por otra razón, no por la fecha


def test_el_ojeador_trabaja_por_ventana_de_fecha():
    from alpha_football import negociacion as N
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-10'; assert N._clave_ventana(e) == (1, 'inicio')
    cal['dia'] = '2026-09-10'; assert N._clave_ventana(e) == (1, 'invierno')
    cal['dia'] = '2027-02-10'; assert N._clave_ventana(e) == (2, 'inicio')
```

- [ ] **Step 2: Correr y ver que falla** (las cuatro usan la jornada).

- [ ] **Step 3: Cambios.**

`alpha_football/cantera.py`, reemplazar `_hito`:

```python
def _hito(estado: dict) -> str:
    """'<temporada>-inicio' hasta la mitad de la temporada y '<temporada>-mitad' desde ahí (v0.4.13.0: por fecha)."""
    from alpha_football import temporada as T
    return f"{int(estado.get('temporada', 1) or 1)}-{'mitad' if T.segunda_mitad(estado) else 'inicio'}"
```

y `proximo_informe`:

```python
def proximo_informe(estado: dict) -> str:
    """Cuándo llega el próximo informe (texto para la pantalla)."""
    from alpha_football import temporada as T, calendario as CAL
    if T.segunda_mitad(estado):
        return "inicio de la próxima temporada"
    return CAL.texto_fecha(T.mitad(estado), False)
```

`alpha_football/salidas.py`, en `revisar_renovaciones`, reemplazar:

```python
    if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 22) or 22) // 2:
        return []
```

por:

```python
    from alpha_football import temporada as T      # v0.4.13.0: desde la mitad de la temporada (por fecha)
    if not T.segunda_mitad(estado):
        return []
```

`alpha_football/directiva.py`: en `avisar_tope_salarial` reemplazar la línea `mitad = 1 if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 22) or 22) // 2 else 2` por:

```python
        from alpha_football import temporada as _T      # v0.4.13.0: la mitad es una fecha
        mitad = 2 if _T.segunda_mitad(estado) else 1
```

y en `pedir_espaldarazo` reemplazar el bloque `if int(getattr(liga, 'jornada_actual', 1) or 1) > int(getattr(liga, 'num_jornadas', 10) or 10) // 2:\n        return False, "Solo se puede pedir hasta la mitad de la temporada."` por:

```python
    from alpha_football import temporada as _T      # v0.4.13.0
    if _T.segunda_mitad(estado):
        return False, "Solo se puede pedir hasta la mitad de la temporada."
```

(no se toca `revisar_pedido`: los pedidos se crean como hoy).

`alpha_football/negociacion.py`, reemplazar el cuerpo de `_clave_ventana`:

```python
def _clave_ventana(estado: dict) -> tuple:
    """Ventana de mercado actual o la próxima: (temporada, 'inicio'|'invierno'). v0.4.13.0: por fecha."""
    from alpha_football import temporada as T
    return T.siguiente_ventana(estado)
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `14/14 tests pasaron`.
Run (uno por uno): `test_cantera.py`, `test_renovacion_aviso.py`, `test_invierno_hitos.py`, `test_objetivos_secciones.py` (o el que cubra directiva: `ls tests | grep -i objetiv`).
Expected: pueden fallar los que dan por hecho la mitad por jornada (J11 = primera mitad); se ajustan en el Task 10.

---

### Task 5: Préstamos con las ventanas por fecha

**Files:**
- Modify: `alpha_football/prestamos.py`
- Test: `tests/test_temporada.py`

**Interfaces:**
- Consumes: `temporada.siguiente_ventana/ventanas/jornada_de` (Task 1), `traspasos_pendientes.fecha_apertura/texto_apertura` (Task 3).
- Produces: `prestamos._regreso(estado, meses) -> (temporada, nombre de la ventana, jornada)` por fecha; `_vuelve(p, n, estado=None)`; el préstamo guarda `'vuelve_fecha'` (ISO, primer día de la ventana de regreso) y los textos lo usan.

- [ ] **Step 1: Tests** — agregar:

```python
def test_el_regreso_de_un_prestamo_es_el_primer_dia_de_su_ventana():
    from alpha_football import prestamos as PR
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-10'                                              # ventana de inicio abierta
    assert PR._regreso(e, 6) == (1, 'invierno', 11)                         # 6 meses: la de invierno (1 ene)
    assert PR._regreso(e, 12) == (2, 'inicio', 1)                           # 1 año: la misma, la temporada siguiente
    cal['dia'] = '2026-10-10'                                              # cerrado: la próxima es la de invierno
    assert PR._regreso(e, 6) == (2, 'inicio', 1)
    assert PR._regreso(e, 12) == (2, 'invierno', 11)
    sa = _e('betplay'); D.hoy(sa); CAL.asegurar(sa)['dia'] = '2027-01-10'
    assert PR._regreso(sa, 6) == (2027 - 2026, 'invierno', 10)             # Sudamérica: invierno = 1 jul, J10


def test_un_vuelve_viejo_con_jornada_se_traduce_por_su_ventana():
    from alpha_football import prestamos as PR
    e = _e(); D.hoy(e)
    p = {'vuelve': [1, 3], 'ventana': 'invierno'}                           # save viejo: la jornada ya no vale
    assert PR._vuelve(p, 22, e) == [1, 11]
    assert PR._vuelve({'vuelve': [1, 9], 'ventana': 'cierre'}, 22, e) == [2, 1]
    assert PR._vuelve({'vuelve': [1, 9], 'ventana': 0}, 22, e) == [1, 1]
```

- [ ] **Step 2: Correr y ver que falla** (el regreso sigue por jornada).

- [ ] **Step 3: `prestamos.py`** — reemplazar `_regreso` y `_vuelve` completos:

```python
def _regreso(estado: dict, meses: int) -> tuple:
    """(temporada, nombre de la ventana, jornada) del regreso: el primer día de la ventana que
    corresponde a la duración (v0.4.13.0: las ventanas son fechas, temporada.py)."""
    from alpha_football import temporada as T
    t, nombre = T.siguiente_ventana(estado)               # la abierta hoy o, si está cerrado, la próxima
    if int(meses) >= 12:
        t += 1
    else:
        k = T.ORDEN.index(nombre) + 1
        if k >= len(T.ORDEN):                              # desde el invierno, 6 meses = el inicio de la siguiente
            t, nombre = t + 1, T.ORDEN[0]
        else:
            nombre = T.ORDEN[k]
    abre = T.ventanas(estado, t)[nombre][0]
    return t, nombre, T.jornada_de(estado, abre, t)


def _vuelve(p: dict, n: int, estado: Optional[dict] = None) -> list:
    """Regreso con la jornada recalculada por su ventana (la liga pudo cambiar de tamaño; v0.4.13.0: o las
    ventanas pasaron a fechas). La ventana se guarda por nombre; 'cierre' (saves de antes) vale el inicio
    de la temporada siguiente; los índices son saves aún más viejos."""
    from alpha_football import temporada as T
    v = list(p.get('vuelve') or [0, 0])
    k = p.get('ventana')
    if estado is None:
        return v
    if k == 'cierre':
        t = int(v[0]) + 1
        return [t, T.jornada_de(estado, T.ventanas(estado, t)['inicio'][0], t)]
    nombre = k if k in T.ORDEN else (T.ORDEN[k] if isinstance(k, int) and 0 <= k < len(T.ORDEN) else None)
    if nombre is not None:
        t = int(v[0])
        v[1] = T.jornada_de(estado, T.ventanas(estado, t)[nombre][0], t)
    return v
```

En `_vencidos`, reemplazar `p['vuelve'] = _vuelve(p, n)` por `p['vuelve'] = _vuelve(p, n, estado)`.

En `iniciar`, agregar `'vuelve_fecha'` al registro: reemplazar

```python
           'vuelve': [t, jv], 'ventana': k, 'meses': int(meses)}
```

por:

```python
           'vuelve': [t, jv], 'ventana': k, 'meses': int(meses),
           'vuelve_fecha': _fecha_regreso(estado, t, k)}
```

y agregar la función auxiliar junto a `_regreso`:

```python
def _fecha_regreso(estado: dict, t: int, nombre: str) -> str:
    """Primer día de la ventana de regreso (ISO), para los textos."""
    from alpha_football import temporada as T
    return T.ventanas(estado, t)[nombre][0].isoformat()
```

En `_mover_ida`, sumar `'vuelve_fecha'` a la lista de claves que se copian: `('dueno', 'club', 'pct_dueno', 'vuelve', 'meses', 'ventana')` → `('dueno', 'club', 'pct_dueno', 'vuelve', 'meses', 'ventana', 'vuelve_fecha')`.

Textos: reemplazar `_texto_regreso` y `_periodo`:

```python
def _texto_regreso(vuelve: list, fecha: Optional[str] = None) -> str:
    if fecha:                                        # v0.4.13.0: la fecha manda
        from datetime import date as _d
        from alpha_football import calendario as CAL
        return f"el {CAL.texto_fecha(_d.fromisoformat(fecha))}"
    return f"la jornada {vuelve[1]} de la temporada {vuelve[0]}"
```

```python
def _periodo(p: dict) -> str:
    """'Periodo: 6 meses (desde J3 T1 hasta J11 T1).' (con fecha de regreso: '… hasta el vie 1 ene 2027.')"""
    d, v = p.get('desde'), p.get('vuelve') or ['?', '?']
    dur = "1 año" if int(p.get('meses', 6) or 6) >= 12 else "6 meses"
    desde = f"desde J{d[1]} T{d[0]} " if d else ""          # préstamos de saves previos no la tienen
    hasta = _texto_regreso(v, p.get('vuelve_fecha')) if p.get('vuelve_fecha') else f"J{v[1]} T{v[0]}"
    return f"Periodo: {dur} ({desde}hasta {hasta})."
```

y en los dos lugares que llaman `_texto_regreso(...)`: el correo de 'ida' → `_texto_regreso(p.get('vuelve') or ['?', '?'], p.get('vuelve_fecha'))`; y en `iniciar` el mensaje `hasta {_texto_regreso(reg['vuelve'])}` → `hasta {_texto_regreso(reg['vuelve'], reg.get('vuelve_fecha'))}`.

En los mensajes de préstamo acordado con el mercado cerrado (`iniciar` y `concluir`): reemplazar `f"{_nombre(jugador)} se irá a {destino.nombre} a préstamo en la jornada {ap}, "` por `f"{_nombre(jugador)} se irá a {destino.nombre} a préstamo {texto_apertura(estado)}, "` y `f"{_nombre(jugador)} vuelve a su club en la jornada {jornada_apertura(estado)}, cuando se abra el mercado."` por `f"{_nombre(jugador)} vuelve a su club {texto_apertura(estado)}, cuando se abra el mercado."` (importar `texto_apertura` junto a `jornada_apertura` en esas funciones). En `_correo_prestamo`, evento `'acordado'`, reemplazar `f"a préstamo en la jornada {(p.get('desde') or ['?', '?'])[1]}, en cuanto se abra el mercado.")` por `f"a préstamo {_cuando_acordado(p)}, en cuanto se abra el mercado.")` y agregar:

```python
def _cuando_acordado(p: dict) -> str:
    """'el vie 1 ene 2027' o, en saves viejos, 'en la jornada N'."""
    if p.get('desde_fecha'):
        from datetime import date as _d
        from alpha_football import calendario as CAL
        return f"el {CAL.texto_fecha(_d.fromisoformat(p['desde_fecha']))}"
    return f"en la jornada {(p.get('desde') or ['?', '?'])[1]}"
```

y en `iniciar`, al armar `reg['desde']`, sumar `reg['desde_fecha'] = fecha_apertura(estado).isoformat()` (importar `fecha_apertura` de `traspasos_pendientes` junto a `jornada_apertura`).

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `16/16 tests pasaron`.
Run (uno por uno): `test_prestamos.py`, `test_prestamos_pedir.py`, `test_prestamos_pulido.py`, `test_prestamos_sueldo.py`.
Expected: pueden fallar los que afirman la jornada de regreso o dan por abierta la J3; se ajustan en el Task 10.

---

### Task 6: Los días revisan los ritmos; la IA y las ofertas en la ventana

**Files:**
- Modify: `alpha_football/dias.py`
- Test: `tests/test_temporada.py`, `tests/test_dias.py` (fechas de G1)

**Interfaces:**
- Consumes: `temporada.*` (Task 1), `cantera.revisar_jornada`, `patrocinios.revisar_jornada`, `prestamos.revisar_jornada`, `traspasos_pendientes.ejecutar/limpiar_ofertas`, `mercado_ia.ronda_fichajes_ia`, `dias.programar_ofertas/asignar_dias/avanzar_dia/continuar/texto_resumen` (G1).
- Produces: `dias.revisar_dia(estado, fecha) -> Optional[str]` (`'abre'` / `'cierra'` / None); `avanzar_dia` devuelve además `'hito'`; `continuar` se detiene en un hito; `dias.inicio_temporada` = `temporada.inicio`; `programar_ofertas` agenda dentro de la ventana con una tirada por cada 14 días libres.

- [ ] **Step 1: Tests** — agregar a `tests/test_temporada.py`:

```python
def test_el_reloj_nace_el_1_de_julio_en_europa_y_el_1_de_enero_en_sudamerica():
    e = _e(); sa = _e('betplay')
    assert D.hoy(e) == date(2026, 7, 1) and D.hoy(sa) == date(2027, 1, 1)


def test_continuar_se_detiene_al_abrir_y_al_cerrar_el_mercado():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    _jugar(e, 1); _jugar(e, 2)                                             # el próximo partido es la J3 (5 de septiembre)
    cal['dia'] = '2026-08-30'
    r = D.continuar(e)                                                     # 31 ago: sigue abierto, ni abre ni cierra
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 8, 31) and not r.get('hito')
    r = D.continuar(e)
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 9, 1) and r['hito'] == 'cierra'
    assert D.texto_resumen(r) == "Pasó 1 día: cierra el mercado"
    cal['dia'] = '2026-06-30'                                              # (antes del inicio: abre el 1 de julio)
    assert D.avanzar_dia(e)['hito'] == 'abre'


def test_cada_dia_se_revisan_los_ritmos_y_se_concretan_los_traspasos_al_abrir():
    from alpha_football import traspasos_pendientes as TP
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; D.hoy(e); cal = CAL.asegurar(e)
    for jor in range(1, 11):
        _jugar(e, jor)                                                     # el próximo partido es la J11 (2 de enero)
    cal['dia'] = '2026-12-31'
    liga.jornada_actual = 11
    j = mi.jugadores[5]; TP.diferir_venta(e, j, liga.equipos[1], 1_000_000)  # cerrado hasta el 1 de enero
    assert TP.pendiente_de(e, j) is not None
    D.avanzar_dia(e)                                                       # 1 de enero: abre
    assert D.hoy(e) == date(2027, 1, 1) and TP.pendiente_de(e, j) is None and j not in mi.jugadores


def test_la_ia_hace_sus_rondas_en_los_dias_sorteados_de_la_ventana():
    from alpha_football import mercado_ia as MIA
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    _jugar(e, 1); _jugar(e, 2)                                             # el próximo partido es la J3: los días de julio y agosto están libres
    dia = T.dias_de_ronda(e)[0]
    llamadas = []
    original = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: llamadas.append(modo) or []
    try:
        cal['dia'] = (dia - timedelta(days=1)).isoformat()
        D.avanzar_dia(e)                                                   # llega al día de ronda
        siguiente = (dia + timedelta(days=1))
        assert llamadas == ['ventana'] and D.hoy(e) == dia
        if siguiente not in T.dias_de_ronda(e):
            D.avanzar_dia(e); assert llamadas == ['ventana']              # el día siguiente no hay ronda
    finally:
        MIA.ronda_fichajes_ia = original


def test_las_ofertas_se_agendan_dentro_de_la_ventana_y_el_hueco_largo_tira_mas_veces():
    from alpha_football import market
    e = _e(); D.hoy(e)                                                     # 1 de julio: hueco de 45 días hasta la J1
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    viejo = market.PROB_OFERTA_POR_JORNADA
    market.PROB_OFERTA_POR_JORNADA = 1.0                                    # siempre sale
    try:
        nuevos = [it for it in D.programar_ofertas(e, random.Random(3)) if it['tipo'] == 'oferta']
    finally:
        market.PROB_OFERTA_POR_JORNADA = viejo
    assert len(nuevos) == len(D.dias_libres(e)) // 14 >= 3
    D.asignar_dias(e)
    assert all(T.ventana_en(e, date.fromisoformat(it['fecha'])) for it in D.agenda(e))
```

- [ ] **Step 2: Correr y ver que falla** (el reloj nace el 1 de agosto, no hay `hito`).

- [ ] **Step 3: `dias.py`** — cuatro cambios.

(a) El inicio sale de `temporada`. Reemplazar:

```python
def inicio_temporada(estado: dict) -> date:
    m, d = INICIO_TEMPORADA.get(CAL.continente(estado), (8, 1))
    return date(CAL.anio(estado), m, d)
```

por:

```python
def inicio_temporada(estado: dict) -> date:
    from alpha_football import temporada as T      # v0.4.13.0: 1 jul (Europa) / 1 ene (Sudamérica)
    return T.inicio(estado)
```

y eliminar la constante `INICIO_TEMPORADA` (queda sin uso).

(b) Agregar al final de `dias.py` (antes de `diferir_correos` o al final del módulo):

```python


# --- Lo que ocurre por fecha ──────────────────────────────────────────────────

def revisar_dia(estado: dict, fecha: date) -> Optional[str]:
    """v0.4.13.0: los ritmos de la temporada. Cantera, patrocinios, préstamos y traspasos acordados miran su
    propia clave y son idempotentes: se revisan cada día (al abrir una ventana concretan lo acordado, al
    llegar la mitad renuevan la cantera, etc.). La IA hace su ronda en los días sorteados de la ventana.
    Devuelve 'abre' / 'cierra' si hoy abre el mercado o es el día siguiente a su cierre."""
    from alpha_football import temporada as T
    pasos = (('cantera', 'revisar_jornada'), ('patrocinios', 'revisar_jornada'), ('prestamos', 'revisar_jornada'))
    for modulo, funcion in pasos:
        try:
            mod = __import__(f"alpha_football.{modulo}", fromlist=[funcion])
            getattr(mod, funcion)(estado)
        except Exception as e:
            logger.error(f"dias: no se pudo revisar {modulo}: {e}", exc_info=True)
    try:
        from alpha_football import traspasos_pendientes as TP
        TP.ejecutar(estado)
        TP.limpiar_ofertas(estado)
    except Exception as e:
        logger.error(f"dias: no se pudieron concretar los traspasos acordados: {e}", exc_info=True)
    try:
        if T.es_dia_de_ronda(estado, fecha):
            from alpha_football.mercado_ia import ronda_fichajes_ia
            ronda_fichajes_ia(estado, 'ventana')
    except Exception as e:
        logger.error(f"dias: no se pudo hacer la ronda de la IA: {e}", exc_info=True)
    return T.hito_del_dia(estado, fecha)
```

(c) En `avanzar_dia`, después de `for clave, n in entregar(estado, nueva).items(): res[clave] += n`, agregar:

```python
        try:
            hito = revisar_dia(estado, nueva)
            if hito:
                res['hito'] = hito
        except Exception as e_rev:
            logger.error(f"dias: error revisando el día: {e_rev}", exc_info=True)
```

y en `continuar`, reemplazar el cuerpo del bucle:

```python
        r = avanzar_dia(estado)
        if r['dias'] == 0:
            break
        for k in total:
            total[k] += r[k]
        if parar and (r['correos'] or r['ofertas'] or r['eventos']):
            break
```

por:

```python
        r = avanzar_dia(estado)
        if r['dias'] == 0:
            break
        for k in ('dias', 'correos', 'ofertas', 'eventos'):
            total[k] += r[k]
        if r.get('hito'):
            total['hito'] = r['hito']
        if parar and (r['correos'] or r['ofertas'] or r['eventos'] or r.get('hito')):
            break
```

y en `texto_resumen`, antes de `cab = ...`, agregar:

```python
    if r.get('hito') == 'abre':
        partes.append("abre el mercado")
    elif r.get('hito') == 'cierra':
        partes.append("cierra el mercado")
```

(d) `programar_ofertas` dentro de la ventana. Reemplazar su cuerpo (después de la línea `if liga is None or mi is None: return nuevos`):

```python
    from alpha_football import temporada as T
    libres = dias_libres(estado)
    en_ventana = [d for d in libres if T.ventana_en(estado, d)]       # v0.4.13.0: solo caen días con el mercado abierto
    if en_ventana:
        for _ in range(max(1, len(en_ventana) // 14)):                # huecos largos: una tirada por cada 14 días
            if azar.random() <= market.prob_oferta_ia(mi):
                nuevos.append(programar(estado, 'oferta', {'dias': [d.isoformat() for d in en_ventana]}))
    for _ in range(max(1, len(libres) // 14)):
        if azar.random() <= PROB_OFERTA_EXTERIOR:
            nuevos.append(programar(estado, 'oferta_ext'))
    return nuevos
```

(se elimina el `if market.ventana_mercado_abierta(...) and azar.random() <= ...` viejo) y, en `asignar_dias`, reemplazar la elección del día:

```python
        if libres:
            azar = random.Random(f"agenda-{CAL.anio(estado)}-{club}-{jornada}-{k}")
            it['fecha'] = azar.choice(libres).isoformat()
```

por:

```python
        pool = [d for d in libres if d.isoformat() in (it.get('datos') or {}).get('dias', [])] or libres
        if pool:
            azar = random.Random(f"agenda-{CAL.anio(estado)}-{club}-{jornada}-{k}")
            it['fecha'] = azar.choice(pool).isoformat()
```

(el resto, la rama `else` con `h.isoformat()`, no cambia).

- [ ] **Step 4: Fechas de G1 en `tests/test_dias.py`** — el reloj nace el 1 de julio. Reemplazar en ese archivo `date(2026, 8, 1)` por `date(2026, 7, 1)`, `date(2026, 8, 2)` por `date(2026, 7, 2)` y `date(2027, 1, 1)` queda igual; en `test_el_reloj_nace_al_inicio_de_la_temporada` los comentarios "1 de agosto" → "1 de julio". En `test_el_hub_crea_el_reloj_...` no cambia nada.

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `21/21 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: los tests de G1 que fijan `jornada_actual = 12` (renovar) o dependen de la ventana por jornada pueden fallar; se ajustan en el Task 10. El resto en verde.

---

### Task 7: Cartel, franja y cabecera del mercado por fecha

**Files:**
- Modify: `alpha_football/ui/aviso_mercado.py`, `alpha_football/ui/league_screen.py`
- Test: `tests/test_temporada.py`

**Interfaces:**
- Consumes: `temporada.fecha/hito_del_dia/ventanas/proxima_apertura/ventana_actual/dias_para_cierre/ventana_abierta` (Task 1), `dias.continuar` (que se detiene en los hitos).
- Produces: `aviso_mercado.evento_pendiente(estado) -> Optional[tuple]` = `('abre'|'cierra', 'AAAA-MM-DD')`; `aviso_mercado_visto = [temporada, 'AAAA-MM-DD']`; `aviso_mercado_activo = {'tipo', 'fecha', 'foco'}`; franja "MERCADO ABIERTO · cierra en N días" / "ÚLTIMO DÍA"; cabecera con `15 ago · J1/22`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_el_cartel_sale_el_dia_que_abre_y_el_dia_despues_de_cerrar():
    from alpha_football.ui import aviso_mercado as AM
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    assert AM.evento_pendiente(e) == ('abre', '2026-07-01')                 # el reloj nace el día que abre el mercado
    AM._abrir(e, 'abre', '2026-07-01')
    assert AM.evento_pendiente(e) is None and e['datos_carrera']['aviso_mercado_visto'] == [1, '2026-07-01']
    assert e['aviso_mercado_activo']['fecha'] == '2026-07-01'
    cal['dia'] = '2026-08-15'; e['aviso_mercado_activo'] = None
    assert AM.evento_pendiente(e) is None
    cal['dia'] = '2026-09-01'
    assert AM.evento_pendiente(e) == ('cierra', '2026-09-01')
    assert any("Se abrió" in m['asunto'] for m in C.bandeja(e))


def test_la_franja_y_la_cabecera_cuentan_dias():
    from alpha_football.ui import aviso_mercado as AM
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-12'
    assert AM._texto_franja(e) == ("MERCADO ABIERTO · cierra en 19 días", 'verde')
    assert AM._texto_franja(e, True) == ("MERCADO ABIERTO · 19 d.", 'verde')
    cal['dia'] = '2026-08-31'
    assert AM._texto_franja(e) == ("MERCADO ABIERTO · ÚLTIMO DÍA", 'dorado')
    cal['dia'] = '2026-09-02'
    assert AM._texto_franja(e) is None
```

- [ ] **Step 2: Correr y ver que falla** (`evento_pendiente` devuelve jornadas).

- [ ] **Step 3: `aviso_mercado.py`** — reemplazar `eventos_ventana`, `_hasta`, `_reabre` y `evento_pendiente` (las cuatro funciones seguidas, hasta antes de `_abrir`) por:

```python
def _hasta(estado: dict) -> str:
    """Último día de la ventana abierta hoy ('vie 31 ene')."""
    from alpha_football import temporada as T, calendario as CAL
    n = T.ventana_actual(estado)
    return CAL.texto_fecha(T.ventanas(estado)[n][1], False) if n else CAL.texto_fecha(T.fecha(estado), False)


def _reabre(estado: dict) -> str:
    from alpha_football import temporada as T, calendario as CAL
    return f"Reabre el {CAL.texto_fecha(T.proxima_apertura(estado))}."


def _liga(estado):
    return estado.get('liga')


def evento_pendiente(estado: dict) -> Optional[tuple]:
    """v0.4.13.0: ('abre', 'AAAA-MM-DD') el primer día de una ventana, ('cierra', …) el día siguiente a su
    cierre; None el resto o si ya se vio. Solo con reloj (en el hub); sin él no hay cartel."""
    if _liga(estado) is None:
        return None
    from alpha_football import dias, temporada as T
    if not dias.activo(estado):
        return None
    d = T.fecha(estado)
    tipo = T.hito_del_dia(estado, d)
    if not tipo:
        return None
    clave = [int(estado.get('temporada', 1) or 1), d.isoformat()]
    if (estado.get('datos_carrera') or {}).get('aviso_mercado_visto') == clave:
        return None
    return tipo, d.isoformat()
```

(la definición vieja de `_liga`, que quedaba entre `_reabre` y `evento_pendiente`, se reemplaza dentro del mismo bloque: no debe quedar duplicada).

Reemplazar `_abrir`:

```python
def _abrir(estado: dict, tipo: str, fecha: str) -> None:
    dc = estado.setdefault('datos_carrera', {})
    dc['aviso_mercado_visto'] = [int(estado.get('temporada', 1) or 1), fecha]
    # con el mercado cerrado no hay a qué ir: el foco arranca en CONTINUAR
    estado['aviso_mercado_activo'] = {'tipo': tipo, 'fecha': fecha, 'foco': 0 if tipo == 'abre' else 1}
    try:
        from alpha_football import correo as C
        if tipo == 'abre':
            C.enviar(estado, 'club', "Se abrió el mercado de pases",
                     f"Hasta el {_hasta(estado)} se pueden cerrar fichajes, recibir ofertas y pagar cláusulas.",
                     C.accion('negociaciones', "IR A NEGOCIACIONES"))
        else:
            C.enviar(estado, 'club', "Se cerró el mercado de pases",
                     "El mercado de pases ha cerrado. " + _reabre(estado))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo del mercado: {e}")
```

En `_ancho_cabecera` y en la cabecera de `league_screen.render`, reemplazar el tramo `{'2ª' if ... else '1ª'} División  ·  T{estado.get('temporada', 1)}  ·  ` + `Jornada {getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  ` por `... Div.  ·  T{t}  ·  {_fecha_corta(estado)} · J{j}/{n}  ·  `. Concretamente, en `aviso_mercado._ancho_cabecera` y `league_screen.render` (la línea que arma `cabecera`):

```python
f"{'2ª' if getattr(liga, 'division', 1) == 2 else '1ª'} División  ·  T{estado.get('temporada', 1)}  ·  "
f"Jornada {getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
```

→

```python
f"{'2ª' if getattr(liga, 'division', 1) == 2 else '1ª'} Div.  ·  T{estado.get('temporada', 1)}  ·  "
f"{fecha_corta(estado)} · J{getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
```

(en `league_screen` la primera línea usa `es_segunda` en vez de `getattr(...) == 2`: conservar esa variante) y agregar en `aviso_mercado.py` la función pública:

```python
def fecha_corta(estado: dict) -> str:
    """'15 ago' (la fecha de hoy sin día de la semana ni año), para la cabecera del hub."""
    try:
        from alpha_football import temporada as T, calendario as CAL
        d = T.fecha(estado)
        return f"{d.day} {CAL.MESES[d.month - 1]}"
    except Exception:
        return "-"
```

y en `league_screen.py` importar `from alpha_football.ui.aviso_mercado import fecha_corta` dentro del `try` de la cabecera.

Reemplazar `_texto_franja`:

```python
def _texto_franja(estado: dict, corto: bool = False) -> Optional[tuple]:
    if _liga(estado) is None:
        return None
    from alpha_football import temporada as T
    if not T.ventana_abierta(estado):
        return None
    d = T.dias_para_cierre(estado)
    if d <= 0:
        return ("MERCADO · ÚLTIMO DÍA" if corto else "MERCADO ABIERTO · ÚLTIMO DÍA"), 'dorado'
    return (f"MERCADO ABIERTO · {d} d." if corto
            else f"MERCADO ABIERTO · cierra en {d} día{'s' if d != 1 else ''}"), 'verde'
```

y en `dibujar` reemplazar el bloque

```python
        n = int(getattr(_liga(estado), 'num_jornadas', 22) or 22)
        if abre:
            linea = f"Hasta la jornada {_hasta(int(act.get('jornada', 1)), n)}: fichajes, ofertas y cláusulas."
        else:
            linea = _reabre(int(act.get('jornada', 1)), n)
```

por:

```python
        if abre:
            linea = f"Hasta el {_hasta(estado)}: fichajes, ofertas y cláusulas."
        else:
            linea = _reabre(estado)
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `23/23 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_mercado_v440.py`
Expected: pueden fallar los que dan por hecho el cartel por jornada o miden el ancho al límite; si `test_franja_no_choca_y_render` falla por ancho, quitar el día de la semana de la cabecera ya está evitado (`15 ago`); si aun así no entra, acortar `Div.` ya aplicado: anota la desviación. El resto se ajusta en el Task 10.

---

### Task 8: El fin de temporada por fecha

**Files:**
- Modify: `alpha_football/dias.py`, `alpha_football/ui/league_screen.py`
- Test: `tests/test_temporada.py`, `tests/test_dias.py` (G1)

**Interfaces:**
- Consumes: `temporada.fin/es_fin/texto_fase` (Task 1), `dias.es_dia_de_continuar/textos_hub` (G1).
- Produces: `dias.es_dia_de_continuar` sin partidos pendientes = hoy < fin; `textos_hub` con la línea del fin; `league_screen._info_partido.esta_finalizada` solo desde la fecha de fin (con reloj).

- [ ] **Step 1: Tests** — agregar:

```python
def test_despues_del_ultimo_partido_continuar_corre_hasta_el_fin_de_temporada():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 22).isoformat()
    assert D.es_dia_de_continuar(e)                                         # faltan días hasta el 30 de junio
    l1, l2, l3 = D.textos_hub(e)
    assert l1 == "CONTINUAR" and "Fin de temporada" in l3 and l3.endswith(")")
    r = D.continuar(e)
    assert D.hoy(e) == date(2027, 6, 30) and r['dias'] == (date(2027, 6, 30) - CAL.fecha_liga(e, 22)).days
    assert not D.es_dia_de_continuar(e) and D.textos_hub(e) is None
    assert D.avanzar_dia(e)['dias'] == 0                                    # el día del fin no pasa


def test_el_hub_dice_avanzar_temporada_solo_desde_la_fecha_de_fin():
    from alpha_football.ui import league_screen as L
    e = _e(); D.hoy(e)
    for p in e['liga'].calendario:                                         # toda la liga jugada (no solo tus partidos)
        p.jugado = True
    e['liga'].jornada_actual = 22
    cal = CAL.asegurar(e); cal['dia'] = '2027-06-01'
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert info[1] is False                                                 # la liga terminó, pero no la temporada
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"
    cal['dia'] = '2027-06-30'
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert info[1] is True and L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "AVANZAR TEMPORADA"


def test_la_temporada_nueva_nace_el_dia_despues_del_fin():
    e = _e(); D.hoy(e)
    CAL.asegurar(e)['dia'] = '2027-06-30'
    e['temporada'] = 2                                                      # lo que hace avanzar_nueva_temporada
    assert D.hoy(e) == date(2027, 7, 1) and T.inicio(e) == date(2027, 7, 1)
```

- [ ] **Step 2: Correr y ver que falla** (sin partidos pendientes no corre).

- [ ] **Step 3: `dias.py`** — reemplazar el cuerpo de `es_dia_de_continuar`:

```python
def es_dia_de_continuar(estado: dict) -> bool:
    """True si la partida tiene reloj y hoy NO es el día de tu próximo partido: JUGAR pasa a CONTINUAR.
    v0.4.13.0: sin partidos pendientes, los días corren hasta el fin de la temporada."""
    try:
        if not activo(estado):
            return False
        h = hoy(estado)
        prox = CAL.proximo_evento(estado)
        if prox is not None:
            return h < prox['fecha']
        from alpha_football import temporada as T
        return h < T.fin(estado)
    except Exception as e:
        logger.error(f"dias: no se pudo saber si hoy hay partido: {e}")
        return False
```

y en `textos_hub`, reemplazar desde `prox = CAL.proximo_evento(estado)` hasta el `return` por:

```python
    from alpha_football import temporada as T
    prox = CAL.proximo_evento(estado)
    h = hoy(estado)
    if prox is None:                                         # v0.4.13.0: los días que faltan para el fin
        n = (T.fin(estado) - h).days
        l3 = f"Fin de temporada: {CAL.texto_fecha(T.fin(estado), False)} (en {n} día{'s' if n != 1 else ''})"
        return "CONTINUAR", l2_fecha_fase(estado), l3[:56]
    n = (prox['fecha'] - h).days
    donde = "vs" if prox['local'] else "en"
    l3 = (f"Próximo: {prox['etiqueta']} {donde} {str(prox['rival'])[:12]} · "
          f"{CAL.texto_fecha(prox['fecha'], False)} (en {n} día{'s' if n != 1 else ''})")
    return "CONTINUAR", l2_fecha_fase(estado), l3[:56]
```

y agregar encima de `textos_hub`:

```python
def l2_fecha_fase(estado: dict) -> str:
    """'mié 12 ago 2026 · Mercado abierto · cierra en 19 días': la fecha y la fase, lo principal del hub."""
    from alpha_football import temporada as T
    return f"{CAL.texto_fecha(hoy(estado))} · {T.texto_fase(estado)}"[:56]
```

(el test de G1 `test_textos_del_hub_y_resumen` cambia: ver Step 4).

- [ ] **Step 4: `league_screen.py`** — en `_info_partido`, después de la línea que calcula `esta_finalizada`:

```python
    if esta_finalizada:
        try:   # v0.4.13.0: con reloj, la temporada termina en su fecha (30 jun / 31 dic), no al jugar la última jornada
            from alpha_football import dias as _dias_f, temporada as _T_f
            if _dias_f.activo(estado) and not _T_f.es_fin(estado):
                esta_finalizada = False
        except Exception as e_fin:
            logger.error(f"Error al leer el fin de temporada: {e_fin}")
```

- [ ] **Step 5: Ajustar los tests de G1 que cambian** — en `tests/test_dias.py`:

`test_sin_partidos_pendientes_el_reloj_no_corre` → reemplazar el cuerpo por:

```python
def test_sin_partidos_pendientes_el_reloj_corre_hasta_el_fin_de_temporada():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    assert D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 1       # v0.4.13.0: faltan días hasta el 30 de junio
    D.continuar(e, parar=False)
    assert not D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 0
    assert D.continuar({})['dias'] == 0 and not D.es_dia_de_continuar({})   # sin partida
```

`test_textos_del_hub_y_resumen`: reemplazar las dos primeras aserciones de formato:

```python
    l1, l2, l3 = D.textos_hub(e)
    assert l1 == "CONTINUAR" and l2.startswith("mié 1 jul 2026") and "Mercado abierto" in l2
    assert l3.startswith("Próximo: J1") and "(en " in l3 and l3.endswith(")") and len(l3) <= 56
```

(1 de julio de 2026 es miércoles).

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `26/26 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: en verde salvo los de renovar/ventana por jornada anotados (Task 10).

---

### Task 9: El hub con la fecha primero y el calendario con las ventanas

**Files:**
- Modify: `alpha_football/ui/league_screen.py`, `alpha_football/ui/calendario_screen.py`, `alpha_football/ui/ayuda.py`
- Test: `tests/test_temporada.py`, `tests/test_calendario.py` (límites del mes)

**Interfaces:**
- Consumes: `dias.l2_fecha_fase/textos_hub` (Task 8), `temporada.hitos/ventana_en` (Task 1).
- Produces: la línea 2 de CONTINUAR = fecha + fase y la 3 = próximo partido; `calendario_screen.limites` = (inicio de temporada, fin); celdas de ventana abierta con franja verde y etiqueta FIN TEMPORADA.

- [ ] **Step 1: Tests** — agregar:

```python
def test_el_hub_pone_la_fecha_y_la_fase_primero():
    from alpha_football.ui import league_screen as L
    e = _e(); D.hoy(e); e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    l1, l2, l3, hab = L._textos_jugar(e['liga'], e['mi_equipo'], info, e)
    assert l1 == "CONTINUAR" and l2.startswith("mié 1 jul 2026 · Mercado abierto · cierra en 61 días") and l3.startswith("Próximo: J1")
    dibujados, original = [], L.draw_text
    L.draw_text = lambda scr, txt, *a, **k: (dibujados.append(txt), original(scr, txt, *a, **k))[1]
    try:
        pygame.event.clear(); L.render(screen, e)
    finally:
        L.draw_text = original
    cab = next(t for t in dibujados if "PREMIER" in t.upper() and " · " in t)
    assert "1 jul · J1/22" in cab and "Jornada " not in cab                 # la fecha primero; la jornada, chica


def test_la_pantalla_calendario_abarca_toda_la_temporada_y_marca_las_ventanas():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    assert KS.limites(e) == ((2026, 7), (2027, 6))                          # del 1 de julio al 30 de junio
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [2026, 7]                                        # abre en el mes de hoy (el reloj nace el 1 jul)
```

- [ ] **Step 2: Correr y ver que falla.**

- [ ] **Step 3: `league_screen.py`** — (a) el cartel del mercado intercepta teclas el día que abre: ya lo maneja `aviso_mercado.manejar`. (b) En el bloque que dibuja JUGAR (G1/C), reemplazar la parte de la fecha de arriba a la derecha:

```python
            if habilitado and l1 == "CONTINUAR":
                from alpha_football import dias as _dias_j
                _txt_fecha = _cal_j.texto_fecha(_dias_j.hoy(estado))        # v0.4.12.0: el día en que estás
            else:
                _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
```

por:

```python
            if habilitado and l1 == "CONTINUAR":
                _txt_fecha = ""                                 # v0.4.13.0: la fecha y la fase van en la línea 2
            else:
                _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
```

y la línea 3 de CONTINUAR (el próximo partido) la dibuja el `if l3:` existente en azul. Ajustar el color de la línea 2 para que la fecha y la fase salgan en dorado también con CONTINUAR: en el `draw_text(screen, l2, ...)` existente, cambiar `color='dorado' if fase_copa else 'blanco'` por `color='dorado' if (fase_copa or l1 == "CONTINUAR") else 'blanco'`.

- [ ] **Step 4: `calendario_screen.py`** — reemplazar `limites`:

```python
def limites(estado: dict) -> tuple:
    """((año, mes) del inicio de la temporada o del primer partido, (año, mes) del fin o del último partido)."""
    from alpha_football import temporada as T
    fechas = [ev['fecha'] for ev in CAL.eventos_user(estado)]
    h = T.hitos(estado)
    fechas += [h['inicio'], h['fin']]
    return (min(fechas).year, min(fechas).month), (max(fechas).year, max(fechas).month)
```

y en `render`, dentro del bucle de celdas, justo después de dibujar el número del día, agregar:

```python
            try:   # v0.4.13.0: franja verde en los días con el mercado abierto; fin de temporada
                from alpha_football import temporada as _T
                if _T.ventana_en(estado, d):
                    pygame.draw.rect(screen, (0, 140, 80), pygame.Rect(rc.x, rc.y, rc.width, 4), border_radius=2)
                if d == _T.fin(estado):
                    draw_text(screen, "FIN TEMPORADA", (rc.x + 6, rc.y + 26), size='sm', color='azul', shadow=False)
            except Exception as e_vent:
                logger.error(f"Error al marcar las ventanas en el calendario: {e_vent}")
```

- [ ] **Step 5: `ayuda.py`** — en `_ayuda_calendario` cambiar el texto del ítem "Mes" por `"Tus partidos día por día. Franja verde: mercado abierto; rojo: cierre; dorado: hoy."` (≤110 caracteres).

- [ ] **Step 6: Ajustar el test de C** — en `tests/test_calendario.py`, `test_pantalla_calendario_navega_y_vuelve`: reemplazar `assert KS.limites(e) == ((2026, 8), (2027, 5))` por `((2026, 7), (2027, 6))`; `assert e['cal_mes'] == [2026, 8]` (dos veces) por `[2026, 7]`; `key(pygame.K_RIGHT); KS.render(screen, e); assert e['cal_mes'] == [2026, 9]` por `[2026, 8]`; y el bucle final `for _ in range(14)` / `assert e['cal_mes'] == [2027, 5]` por `for _ in range(14)` / `[2027, 6]`.

- [ ] **Step 7: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: `28/28 tests pasaron`.
Run (uno por uno): `test_calendario.py`, `test_ayuda_v390.py`, `test_ux_v360.py`.
Expected: `24/24`, y los otros en `N/N tests pasaron`.

---

### Task 10: Tests viejos, suite completa y cierre de G2

**Files:**
- Modify: los tests que den por hecha la regla vieja (se ven al correrlos)
- Modify: `context.md`

- [ ] **Step 1: Ver qué tests viejos cambian.** Correr uno por uno: `test_ventana_traspaso.py`, `test_invierno_hitos.py`, `test_mercado_v350.py`, `test_mercado_v440.py`, `test_negociaciones_v270.py`, `test_prestamos.py`, `test_prestamos_pedir.py`, `test_prestamos_pulido.py`, `test_prestamos_sueldo.py`, `test_patrocinios.py`, `test_cantera.py`, `test_renovacion_aviso.py`, `test_ajustes_v0411.py`, `test_presupuesto_ventanas.py`, `test_hub_v240.py`, `test_teclado_v420.py`, `test_dias.py`, `test_calendario.py`, `test_ofertas*.py`, `test_objetivos*.py`.

- [ ] **Step 2: Ajustar sin debilitar.** Recetas:
  - *"Abierto en la J3 / J13"*: ahora cerrado (5 de septiembre, 6 de febrero). Cambiar la jornada del test a J2 / J12 (abierto) o el resultado esperado a cerrado, según lo que pruebe el test.
  - *"La mitad empieza en la jornada 11/12"*: la mitad es el 1 de enero; la J11 (2 de enero) ya es segunda mitad. Mover el límite del test una jornada o fijar el reloj con `CAL.asegurar(e)['dia'] = 'AAAA-MM-DD'` tras `D.hoy(e)`.
  - *Textos "llega en la jornada N" / "vuelve J11 T1"*: ahora dicen la fecha (`TP.texto_apertura(e)`, `vuelve_fecha`); ajustar la cadena esperada o compararla con `CAL.texto_fecha(...)`.
  - *Cartel de mercado por jornada* (`aviso_mercado_visto = [1, jornada]`, `eventos_ventana`, `aviso_mercado_activo['jornada']`): el cartel ahora es por fecha y solo con reloj. Para silenciarlo en un test de hub: crear el reloj antes (`D.hoy(e)`) y fijar `e['datos_carrera']['aviso_mercado_visto'] = [1, D.hoy(e).isoformat()]`. Los helpers `_hub` de `test_dias.py` y los `aviso_mercado_visto = [1, 1]` de `test_calendario.py` y `test_ajustes_v0411.py` se cambian así.
  - *Tests de G1 que fijan `liga.jornada_actual = 12` para "quiere renovar"*: ahora manda la fecha; fijar `CAL.asegurar(e)['dia'] = '2027-02-01'` en vez de la jornada.
  - *Reloj del 1 de agosto*: ya cambió a 1 de julio (Task 6).
  Un test que falla por otra razón es un bug del cambio: buscar la causa raíz.

  **Tests de G1 que cambian por G2** (`tests/test_dias.py`; el mercado ahora lo decide la fecha del reloj, no `liga.jornada_actual`):
  - `_hub(e)`: el cartel de apertura sale el 1 de julio y se come las teclas. Reemplazar su cuerpo por `D.hoy(e); e['datos_carrera']['aviso_mercado_visto'] = [1, D.hoy(e).isoformat()]; from alpha_football.ui import league_screen as L; return L` (el reloj nace antes del primer `render`; las aserciones "el hub crea el reloj" se conservan con `assert D.activo(e)`).
  - `test_el_sorteo_de_ofertas_conserva_las_frecuencias_y_respeta_la_ventana` → reemplazar por:

    ```python
    def test_el_sorteo_de_ofertas_conserva_las_frecuencias_y_respeta_la_ventana():
        e = _e(); _en_j1(e)                                                # reloj el día de la J1: hueco corto = 1 tirada
        for j in e['mi_equipo'].jugadores:
            j.transferible = j.pide_salir = False
        rng = random.Random(7); N = 3000
        n_loc = n_ext = 0
        for _ in range(N):
            D.agenda(e).clear()
            for it in D.programar_ofertas(e, rng):
                n_loc += it['tipo'] == 'oferta'; n_ext += it['tipo'] == 'oferta_ext'
        assert abs(n_loc / N - 0.15) < 0.03 and abs(n_ext / N - 0.25) < 0.03, (n_loc / N, n_ext / N)
        for j in range(2, 10):
            _jugar(e, j)
        CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 9).isoformat()          # el hueco hasta la J10 cae en noviembre/diciembre: cerrado
        assert all(it['tipo'] == 'oferta_ext' for _ in range(300) for it in D.programar_ofertas(e, rng))
    ```

  - `test_oferta_agendada_con_el_mercado_cerrado_no_se_crea_ni_rompe_el_avance`: cambiar `e['liga'].jornada_actual = 5` por `for j in range(2, 10): _jugar(e, j)` y `CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 9).isoformat()`; la aserción final pasa a `D.hoy(e) == CAL.fecha_liga(e, 10)`.
  - `test_el_aviso_de_renovar_llega_en_un_dia_sorteado`: fijar la mitad con el reloj, no con la jornada. Reemplazar `e['liga'].jornada_actual = 12` por `CAL.asegurar(e)['dia'] = '2027-02-01'` y, al final, reemplazar `D.hasta_el_partido(e)` por `D.asignar_dias(e); D.entregar(e, date(2100, 1, 1))` (el reloj ya pasó de los partidos pendientes).
  - `test_sin_reloj_el_aviso_de_renovar_sigue_cayendo_en_el_acto` y los demás tests de salidas/eventos de G1 que no mueven el reloj quedan igual.
  - En `tests/test_calendario.py`, `test_hub_y_prepartido_dibujan_la_fecha_sin_errores`: la fecha del botón CONTINUAR vive ahora en la línea 2; reemplazar la última aserción por `assert any(t.startswith(CAL.texto_fecha(_D.hoy(e))) for t in dibujados)`.

- [ ] **Step 3: Suite completa, una sola vez y un archivo a la vez**, en segundo plano (no con `nohup`):

```bash
cd "C:/Users/diego/Downloads/AlphaFootball" && mkdir -p "$TEMP/af_suite_g2" && : > "$TEMP/af_suite_g2/resumen.txt" && for f in tests/test_*.py; do
  b=$(basename "$f" .py); PYTHONIOENCODING=utf-8 timeout 1200 python "$f" > "$TEMP/af_suite_g2/$b.log" 2>&1; rc=$?
  echo "$b rc=$rc FAIL=$(grep -c 'FAIL' "$TEMP/af_suite_g2/$b.log") · $(tail -1 "$TEMP/af_suite_g2/$b.log" | cut -c1-80)" >> "$TEMP/af_suite_g2/resumen.txt"
done; echo TERMINADO >> "$TEMP/af_suite_g2/resumen.txt"
```

Expected: cada línea con `rc=0` y `FAIL=0`. `test_motor_v400` mide tiempos y puede fallar una vez por carga: repetirlo solo antes de investigar.

- [ ] **Step 4: Comprobación sin pantalla** — con `SDL_VIDEODRIVER=dummy` y un estado de carrera con el calendario armado (`tests/test_calendario._e()`): renderizar un cuadro del hub el 1 de julio (debe salir el cartel MERCADO ABIERTO y, tras cerrarlo, CONTINUAR con la fecha y la fase), llevar el reloj con `D.continuar` por toda la temporada jugando cada partido con `finalizar_jornada_liga` y sin errores en el log; confirmar que el mercado cierra el 31 de agosto y reabre el 1 de enero, que la J3 no vuelve a abrir el mercado, que el 30 de junio aparece AVANZAR TEMPORADA y que tras avanzar la temporada el reloj nace el 1 de julio. Repetir con `estado_carrera('betplay')` (1 de enero; invierno el 1 de julio). Guardar capturas del hub y de CALENDARIO con `pygame.image.save` y mirarlas.

- [ ] **Step 5: `context.md`** — agregar la bitácora "2026-10-07 — La temporada por fechas (v0.4.13.0, sub-proyecto G2, sin commit)" con: `temporada.py` y sus funciones, el calendario (Europa y Sudamérica), cómo se decide el mercado (parámetro `estado` en `market.ventana_*`), los ritmos que pasaron a fecha y los que siguen por jornada, `dias.revisar_dia` y los hitos, las rondas de la IA, el fin de temporada por fecha, el hub con la fecha primero, las cuatro desviaciones del spec y los tests viejos ajustados. Actualizar la fecha del encabezado y dejar como pendientes: G3 (las 20 horas), E, F, el bump de versión y la prueba a mano: el cartel de apertura, CONTINUAR deteniéndose el 1 de julio y el 1 de septiembre, la J3 sin mercado, préstamos y traspasos acordados concretándose el primer día de la ventana, la cantera en la mitad (1 de enero), el fin de temporada el 30 de junio y la temporada nueva el 1 de julio.
