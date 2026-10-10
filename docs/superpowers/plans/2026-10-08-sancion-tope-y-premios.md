# v0.4.17.0 — Sanción por tope salarial, evaluación resumida y premios por fecha — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La liga sanciona al club que cierra la temporada sobre el tope salarial (sin fichajes; multa y puntos con mala salud), el veredicto y el correo de cierre explican qué falló, y el Balón de Oro (octubre) y el Jugador Sudamericano del Año (enero) se entregan por fecha.

**Architecture:** Un módulo nuevo sin UI, `sancion_liga.py`, guarda la sanción en `datos_carrera` y expone `motivo_bloqueo`, que consultan los puntos de entrada de fichajes y préstamos. `directiva.py` registra la sanción al evaluar y arma el correo resumido; `finanzas.cierre_temporada` cobra la multa. `premios.py` pasa de "calcular y mostrar" a "calcular, dejar pendiente y entregar por fecha", con una pantalla de gala nueva.

**Tech Stack:** Python 3, Pygame. Tests: archivos `tests/test_*.py` con funciones `test_*`, lista `TESTS` y bloque `__main__` (corren con `python tests/<archivo>.py` y con `python -m pytest`).

**Spec:** `docs/superpowers/specs/2026-10-08-sancion-tope-y-premios-design.md`

## Global Constraints

- Versión de los comentarios nuevos: `v0.4.17.0`. No tocar `VERSION`, el título de la ventana ni el README.
- **Sin commits, stash, reset ni checkout de archivos**: el árbol tiene trabajo sin commit de la sesión `lol`. Cada tarea termina corriendo sus tests, no con un commit.
- Nunca atribuir nada a una IA en git.
- Archivos existentes: solo `Edit` parcial, sin "limpiar" alrededor. Comentarios en español, con la densidad del código vecino.
- Archivos de la sesión `lol`, solo las ediciones acordadas: tupla `pasos` de `dias.revisar_dia`; en `ui/ayuda.py`, quitar la entrada `r['balon']` de `_ayuda_promo`, cambiar la entrada de `R_BALON_ORO` en `_ayuda_carrera` y agregar `_ayuda_gala`; una línea en `ui/atajos.py`; dos entradas en `main.py`; un `if` en `league_screen.render`; el bloque del Balón en `resumen_temporada_screen.avanzar_nueva_temporada`. `lol` las autorizó todas por mensaje. En `ayuda.py` no tocar el bloque de `'league_screen'` ni el de `'calendario_screen'`; en `atajos.py` no tocar esas dos entradas (las está editando él). Cada texto de ayuda, máximo 110 caracteres.
- No leer del dict de `finanzas.presupuesto_temporada` más que `base`, `saldo`, `salud`, `deuda`, `total` (este plan no lo lee).
- Constantes exactas: `MULTA_PCT_BASE = 0.40`, `PUNTOS_MULTA = 6`; salud mala = `finanzas.factor_salud(saldo, base) < 1.0`; galas: último lunes de octubre (Balón de Oro) y 15 de enero (Sudamericano).
- Un rojo en un test de `lol` a medio hacer se avisa por mensaje, no se arregla.

## Review Focus

1. **Save viejo sin las claves nuevas** (sin `sancion_liga`, sin `premios_pendientes`, veredicto sin `motivos`): nada bloquea ni rompe. Tests en las tareas 1, 4 y 5.
2. **DT despedido que cambia de club con la sanción vigente:** el club nuevo ficha normal. Test en la tarea 1.
3. **Compra o préstamo firmado antes del cierre:** se concreta aunque la sanción esté activa. Test en la tarea 2.
4. **Gala pendiente cuando ya pasaron días o hay datos dañados:** la pantalla no se queda trabada, vuelve al hub. Test en la tarea 7.
5. **Premio que nadie entregó** (carrera sin reloj que no llegó a la fecha): se entrega al cerrar la temporada siguiente, sin perderse ni duplicarse. Test en la tarea 5.

---

### Task 1: `sancion_liga.py` — registrar, consultar y cobrar la multa

**Files:**
- Create: `alpha_football/sancion_liga.py`
- Test: `tests/test_sancion_liga_v0417.py` (nuevo)

**Interfaces:**
- Consumes: `finanzas.factor_salud(saldo: int, base: int) -> float`, `finanzas.presupuesto_base(equipo, tipo: str, division: int) -> int`, `finanzas.registrar(estado, clave, monto)`, `correo.enviar`, `correo.accion`.
- Produces: `MULTA_PCT_BASE`, `PUNTOS_MULTA`, `registrar(estado, masa, tope, temporada_fin) -> dict`, `activa(estado) -> Optional[dict]`, `motivo_bloqueo(estado) -> Optional[str]`, `texto(sancion) -> str`, `cobrar_multa(estado) -> Optional[dict]`. Sanción = `{'club', 'temporada', 'masa', 'tope', 'salud_mala', 'multa', 'multa_estado', 'puntos'}` en `datos_carrera['sancion_liga']`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_sancion_liga_v0417.py`:

```python
"""v0.4.17.0: sanción de la liga por tope salarial, veredicto con motivos y evaluación resumida."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(17)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, directiva as D, finanzas as F, sancion_liga as SL
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _base(e):
    mi, liga = e['mi_equipo'], e['liga']
    return F.presupuesto_base(mi, liga.tipo, getattr(liga, 'division', 1) or 1)


def _sancion_mala(e):
    """Sanción con multa ya vigente (temporada 2)."""
    e['mi_equipo'].balance = -1
    s = SL.registrar(e, 12_000_000, 10_000_000, 1)
    e['temporada'] = 2
    return s


# ── Task 1: núcleo ───────────────────────────────────────────────────────────────

def test_registrar_salud_buena_sin_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)                                   # 100% de la base: salud buena
    s = SL.registrar(e, 12_000_000, 10_000_000, 1)
    assert s['club'] == mi.nombre and s['temporada'] == 2
    assert s['salud_mala'] is False and s['multa'] == 0 and s['multa_estado'] is None
    assert e['datos_carrera']['sancion_liga'] is s
    assert "no podrá fichar" in SL.texto(s) and "multa" not in SL.texto(s)
    print("  test_registrar_salud_buena_sin_multa: OK")


def test_registrar_salud_mala_multa_40():
    for pct in (-0.5, 0.10):                                # en rojo y con menos del 25% de la base
        e = estado_carrera(); mi = e['mi_equipo']
        mi.balance = int(_base(e) * pct)
        s = SL.registrar(e, 12_000_000, 10_000_000, 1)
        assert s['salud_mala'] is True and s['multa'] == int(_base(e) * SL.MULTA_PCT_BASE), pct
        assert "impone una multa" in SL.texto(s)
    print("  test_registrar_salud_mala_multa_40: OK")


def test_activa_solo_club_y_temporada():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1)
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None      # la temporada 1 no está sancionada
    e['temporada'] = 2
    assert SL.activa(e) is not None and "Sanción de la liga" in SL.motivo_bloqueo(e)
    e['mi_equipo'] = e['liga'].equipos[3]                              # otro club: no sigue al DT
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None
    e['mi_equipo'] = mi; e['temporada'] = 3                            # dura una temporada
    assert SL.activa(e) is None
    print("  test_activa_solo_club_y_temporada: OK")


def test_sin_sancion_o_datos_rotos_no_bloquea():
    e = estado_carrera()
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None and SL.cobrar_multa(e) is None
    for basura in ("basura", {'club': e['mi_equipo'].nombre}, {'club': e['mi_equipo'].nombre, 'temporada': 'x'}):
        e['datos_carrera']['sancion_liga'] = basura
        assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None, basura
    print("  test_sin_sancion_o_datos_rotos_no_bloquea: OK")


def test_multa_pagada_una_sola_vez():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    mi.balance, mi.puntos = s['multa'] + 500_000, 0
    assert SL.cobrar_multa(e) is s
    assert mi.balance == 500_000 and mi.puntos == 0 and s['multa_estado'] == 'pagada' and s['puntos'] == 0
    assert F.libro(e)['premios'] == -s['multa']
    assert C.bandeja(e)[0]['asunto'].startswith("Sanción de la liga")
    assert SL.cobrar_multa(e) is None and mi.balance == 500_000
    print("  test_multa_pagada_una_sola_vez: OK")


def test_multa_impaga_quita_presupuesto_y_puntos():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    mi.balance, mi.puntos, mi.sancion_puntos = s['multa'] - 1, 0, 0
    SL.cobrar_multa(e)
    assert mi.balance == 0 and mi.puntos == -SL.PUNTOS_MULTA and mi.sancion_puntos == SL.PUNTOS_MULTA
    assert s['multa_estado'] == 'impaga' and s['puntos'] == SL.PUNTOS_MULTA
    assert F.libro(e)['premios'] == -(s['multa'] - 1)                  # solo se llevó lo que había
    assert SL.cobrar_multa(e) is None and mi.puntos == -SL.PUNTOS_MULTA
    print("  test_multa_impaga_quita_presupuesto_y_puntos: OK")


def test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1); e['temporada'] = 2
    saldo = mi.balance
    assert SL.cobrar_multa(e) is None and mi.balance == saldo
    e2 = estado_carrera(); _sancion_mala(e2)
    otro = e2['liga'].equipos[3]; e2['mi_equipo'] = otro; saldo = otro.balance
    assert SL.cobrar_multa(e2) is None and otro.balance == saldo
    print("  test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club: OK")


TESTS = [test_registrar_salud_buena_sin_multa, test_registrar_salud_mala_multa_40,
         test_activa_solo_club_y_temporada, test_sin_sancion_o_datos_rotos_no_bloquea,
         test_multa_pagada_una_sola_vez, test_multa_impaga_quita_presupuesto_y_puntos,
         test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club]

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

Run: `python tests/test_sancion_liga_v0417.py`
Expected: FAIL con `ImportError: cannot import name 'sancion_liga'`.

- [ ] **Step 3: Implementar el módulo**

Crear `alpha_football/sancion_liga.py`:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Sanción de la liga por tope salarial (v0.4.17.0)
Cerrar la temporada con la masa salarial sobre el tope de la directiva trae una sanción de la LIGA al
club: en toda la temporada siguiente no compra, no trae agentes libres ni pide préstamos. Si además
cerró con mala salud financiera, una multa del 40% de su presupuesto base; si el presupuesto nuevo no
alcanza, la liga se lo queda entero y le resta puntos.
- Datos: datos_carrera['sancion_liga'] (una sola; es del club, no del DT).
Sin UI.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MULTA_PCT_BASE = 0.40
PUNTOS_MULTA = 6


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def registrar(estado: dict, masa: int, tope: int, temporada_fin: int) -> dict:
    """Cierre de la temporada `temporada_fin` con la masa sobre el tope: sanciona la siguiente. La salud
    se mide con el saldo de este momento contra el presupuesto base de la liga que se acaba de jugar."""
    from alpha_football.finanzas import factor_salud, presupuesto_base
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    base = presupuesto_base(mi, getattr(liga, 'tipo', 'betplay'), getattr(liga, 'division', 1) or 1)
    salud_mala = factor_salud(int(getattr(mi, 'balance', 0) or 0), base) < 1.0
    s = _dc(estado)['sancion_liga'] = {
        'club': getattr(mi, 'nombre', ''), 'temporada': int(temporada_fin) + 1,
        'masa': int(masa), 'tope': int(tope), 'salud_mala': salud_mala,
        'multa': int(base * MULTA_PCT_BASE) if salud_mala else 0, 'multa_estado': None, 'puntos': 0}
    return s


def activa(estado: dict) -> Optional[dict]:
    """La sanción vigente: la del club que diriges hoy y de la temporada en curso."""
    try:
        s, mi = _dc(estado).get('sancion_liga'), estado.get('mi_equipo')
        if not isinstance(s, dict) or mi is None or s.get('club') != mi.nombre:
            return None
        if int(s.get('temporada') or -1) != int(estado.get('temporada', 1) or 1):
            return None
        return s
    except Exception as e:
        logger.error(f"No se pudo leer la sanción de la liga: {e}")
        return None


def motivo_bloqueo(estado: dict) -> Optional[str]:
    """Texto para rechazar una compra, un agente libre o un préstamo; None si no hay sanción."""
    if activa(estado) is None:
        return None
    return "Sanción de la liga: tu club no puede fichar, traer agentes libres ni pedir préstamos esta temporada."


def texto(s: dict) -> str:
    """Frase del correo de evaluación."""
    t = (f"La liga sanciona al club por superar el tope salarial (${int(s.get('masa', 0)) / 1_000_000:.1f}M sobre "
         f"${int(s.get('tope', 0)) / 1_000_000:.1f}M): no podrá fichar, traer agentes libres ni pedir préstamos "
         f"en toda la temporada {s.get('temporada', '?')}.")
    if s.get('salud_mala'):
        t += (f" Por la mala salud financiera del club, además impone una multa de "
              f"${int(s.get('multa', 0)) / 1_000_000:.1f}M: si el presupuesto no alcanza, se lo quedará entero "
              f"y restará {PUNTOS_MULTA} puntos.")
    return t


def cobrar_multa(estado: dict) -> Optional[dict]:
    """Cierre financiero, ya con el presupuesto nuevo: cobra una sola vez la multa por mala salud."""
    s, mi = activa(estado), estado.get('mi_equipo')
    if s is None or not s.get('salud_mala') or s.get('multa_estado'):
        return None
    multa, saldo = int(s.get('multa', 0) or 0), int(getattr(mi, 'balance', 0) or 0)
    m = lambda v: f"${v / 1_000_000:.1f}M"
    if saldo >= multa:
        cobrado, s['multa_estado'] = multa, 'pagada'
        mi.balance = saldo - multa
        asunto = "Sanción de la liga: multa pagada"
        cuerpo = (f"La liga cobró la multa de {m(multa)} por cerrar la temporada sobre el tope salarial y con mala "
                  f"salud financiera. Presupuesto disponible: {m(mi.balance)}.")
    else:
        cobrado, s['multa_estado'], s['puntos'] = max(0, saldo), 'impaga', PUNTOS_MULTA
        mi.balance = min(0, saldo)
        mi.puntos = int(getattr(mi, 'puntos', 0) or 0) - PUNTOS_MULTA
        mi.sancion_puntos = int(getattr(mi, 'sancion_puntos', 0) or 0) + PUNTOS_MULTA
        asunto = f"Sanción de la liga: sin presupuesto y −{PUNTOS_MULTA} puntos"
        cuerpo = (f"El presupuesto no alcanzó para la multa de {m(multa)} por cerrar la temporada sobre el tope "
                  f"salarial y con mala salud financiera: la liga se quedó con todo el presupuesto ({m(cobrado)}) "
                  f"y le resta {PUNTOS_MULTA} puntos al club en esta temporada.")
    try:
        from alpha_football.finanzas import registrar as _registrar
        _registrar(estado, 'premios', -cobrado)      # mismo renglón que el premio/multa de la directiva
    except Exception as e:
        logger.error(f"No se pudo registrar la multa de la liga: {e}")
    if not estado.get('despido_pendiente'):          # al despedido ya no le sirve
        try:
            from alpha_football import correo as C
            C.enviar(estado, 'directiva', asunto,
                     cuerpo + " Le recordamos que no podrá fichar, traer agentes libres ni pedir préstamos "
                              "durante toda la temporada.",
                     C.accion('finanzas_screen', "VER FINANZAS"))
        except Exception as e:
            logger.error(f"No se pudo avisar la multa de la liga: {e}")
    return s
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: `7/7 tests pasaron`.

---

### Task 2: Bloqueo de compras, agentes libres y préstamos

**Files:**
- Modify: `alpha_football/negociacion.py` (`fichar`, `evaluar_compra`, `reanudar_compra`, `iniciar_negociacion`)
- Modify: `alpha_football/prestamos.py` (`evaluar_pedido`, `cerrar_pedido`)
- Test: `tests/test_sancion_liga_v0417.py`

**Interfaces:**
- Consumes: `sancion_liga.motivo_bloqueo(estado) -> Optional[str]`, `sancion_liga.registrar`.
- Produces: con sanción activa, `negociacion.evaluar_compra(...) == ('rechaza', motivo, 0)`, `negociacion.fichar(...) == (False, motivo)`, `negociacion.reanudar_compra(...) is None` con `estado['correo_aviso'] == motivo`, `estado['neg']['msg'] == (motivo, 'rojo')` al abrir un fichaje o préstamo, `prestamos.evaluar_pedido(...) == ('rechaza', motivo)`, `prestamos.cerrar_pedido(...) == (False, motivo)`. Ninguna firma cambia.

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_sancion_liga_v0417.py`, antes de `TESTS = [`:

```python
# ── Task 2: bloqueo ──────────────────────────────────────────────────────────────

def _sancionar(e):
    """Sanción sin multa vigente en la temporada 2. Devuelve el motivo del bloqueo."""
    e['mi_equipo'].balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1); e['temporada'] = 2
    return SL.motivo_bloqueo(e)


def test_bloqueo_compra_y_agente_libre():
    from alpha_football import negociacion as N
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    motivo = _sancionar(e)
    mi.balance = 10 ** 10
    assert N.evaluar_compra(e, j, club, 10 ** 9) == ('rechaza', motivo, 0)
    assert N.evaluar_compra(e, j, None, 0) == ('rechaza', motivo, 0)          # agente libre
    n = len(mi.jugadores)
    assert N.fichar(e, j, club, 1) == (False, motivo)
    assert j in club.jugadores and len(mi.jugadores) == n and mi.balance == 10 ** 10
    libre = N.asegurar_agentes_libres(e)[0]
    assert N.fichar(e, libre, None, 0) == (False, motivo) and libre not in mi.jugadores
    assert N.reanudar_compra(e, {'club_id': club.id, 'jugador_id': j.id, 'temporada': 2, 'monto': 1}) is None
    assert e['correo_aviso'] == motivo
    print("  test_bloqueo_compra_y_agente_libre: OK")


def test_bloqueo_se_ve_al_abrir_la_negociacion():
    from alpha_football import negociacion as N
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[0]
    motivo = _sancionar(e)
    for modo in ('fichaje', 'prestamo'):
        assert N.iniciar_negociacion(e, j, club, modo, 'buscador_screen') == 'negociacion_screen'
        assert e['neg']['msg'] == (motivo, 'rojo'), modo
    N.iniciar_negociacion(e, mi.jugadores[0], None, 'renovar', 'plantilla_screen')
    assert e['neg']['msg'] is None                                            # renovar sí se puede
    print("  test_bloqueo_se_ve_al_abrir_la_negociacion: OK")


def test_bloqueo_prestamos():
    from alpha_football import prestamos as P
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[2]; j = min(club.jugadores, key=lambda x: x.overall)
    motivo = _sancionar(e)
    n = len(mi.jugadores)
    assert P.evaluar_pedido(e, j, club, 6, 100) == ('rechaza', motivo)
    assert P.cerrar_pedido(e, j, club, 6, 100) == (False, motivo)
    assert len(mi.jugadores) == n and not getattr(j, 'prestamo', None) and P.pendiente_de(e, j) is None
    print("  test_bloqueo_prestamos: OK")


def test_sin_sancion_todo_sigue_igual():
    from alpha_football import negociacion as N, prestamos as P
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    mi.balance = 10 ** 10
    assert N.evaluar_compra(e, j, club, 10 ** 9)[0] == 'acepta'
    assert "Sanción" not in P.evaluar_pedido(e, j, club, 6, 100)[1]
    N.iniciar_negociacion(e, j, club, 'fichaje', 'buscador_screen')
    assert e['neg']['msg'] is None
    print("  test_sin_sancion_todo_sigue_igual: OK")


def test_lo_acordado_antes_se_respeta():
    from alpha_football import traspasos_pendientes as TP
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    TP.diferir_compra(e, j, club, 1)                       # firmado antes del cierre
    _sancionar(e)
    e['liga'].jornada_actual = 1
    assert TP.mercado_abierto(e), "la jornada 1 debe ser ventana"
    assert TP.ejecutar(e) == 1 and j in mi.jugadores and j not in club.jugadores
    print("  test_lo_acordado_antes_se_respeta: OK")
```

Agregar los cinco a `TESTS`:

```python
TESTS = [test_registrar_salud_buena_sin_multa, test_registrar_salud_mala_multa_40,
         test_activa_solo_club_y_temporada, test_sin_sancion_o_datos_rotos_no_bloquea,
         test_multa_pagada_una_sola_vez, test_multa_impaga_quita_presupuesto_y_puntos,
         test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club,
         test_bloqueo_compra_y_agente_libre, test_bloqueo_se_ve_al_abrir_la_negociacion,
         test_bloqueo_prestamos, test_sin_sancion_todo_sigue_igual, test_lo_acordado_antes_se_respeta]
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: fallan `test_bloqueo_compra_y_agente_libre`, `test_bloqueo_se_ve_al_abrir_la_negociacion` y `test_bloqueo_prestamos` (devuelven 'acepta' / `msg` None). Los otros dos nuevos pasan.

- [ ] **Step 3: Bloquear en `negociacion.py`**

En `fichar`, después de `return False, "No hay equipo."`:

```python
    from alpha_football import sancion_liga as SL       # v0.4.17.0: sancionado por la liga no ficha (ni libres)
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return False, bloqueo
```

En `evaluar_compra`, después de `monto = int(monto or 0)`:

```python
    from alpha_football import sancion_liga as SL       # v0.4.17.0: se sabe en la primera oferta
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return 'rechaza', bloqueo, 0
```

En `reanudar_compra`, justo antes de `if motivo:`:

```python
    from alpha_football import sancion_liga as SL       # v0.4.17.0
    motivo = SL.motivo_bloqueo(estado) or motivo
```

En `iniciar_negociacion`, justo antes de `return 'negociacion_screen'`:

```python
    if modo in ('fichaje', 'prestamo'):                 # v0.4.17.0: sancionado por la liga: se ve al abrir
        from alpha_football import sancion_liga as SL
        bloqueo = SL.motivo_bloqueo(estado)
        if bloqueo:
            estado['neg']['msg'] = (bloqueo, 'rojo')
```

- [ ] **Step 4: Bloquear en `prestamos.py`**

En `evaluar_pedido`, después de `pct_user = max(0, min(100, int(pct_user)))`:

```python
    from alpha_football import sancion_liga as SL       # v0.4.17.0: sancionado por la liga tampoco pide préstamos
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return 'rechaza', bloqueo
```

En `cerrar_pedido`, después de `mi = _mi(estado)`:

```python
    from alpha_football import sancion_liga as SL       # v0.4.17.0
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return False, bloqueo
```

- [ ] **Step 5: Correr y ver que pasa, sin romper lo vecino**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: `12/12 tests pasaron`.

Run: `python -m pytest tests/test_negociaciones_v270.py tests/test_mercado_v350.py tests/test_mercado_v440.py tests/test_prestamos.py tests/test_prestamos_pedir.py tests/test_free_agents.py -q`
Expected: todo verde (o los mismos rojos que antes del cambio, si `lol` tiene algo a medio hacer: anotarlos y avisarle).

---

### Task 3: Evaluación de fin de temporada — sanción, motivos, correo resumido y cobro de la multa

**Files:**
- Modify: `alpha_football/directiva.py` (`evaluar_temporada`, `texto_evaluacion`; nuevas `motivos_fallo`, `_lista`, `_fallos_evaluacion`)
- Modify: `alpha_football/finanzas.py` (`cierre_temporada`, tras `aplicar_presupuesto_temporada`)
- Test: `tests/test_sancion_liga_v0417.py`

**Interfaces:**
- Consumes: `sancion_liga.registrar(estado, masa, tope, temporada_fin) -> dict`, `sancion_liga.texto(s) -> str`, `sancion_liga.cobrar_multa(estado)`.
- Produces: `directiva.motivos_fallo(info: dict) -> list[str]`; `info['sancion']` (copia del dict de la sanción o None) e `info['motivos']` en lo que devuelve `evaluar_temporada` y en `estado['veredicto_pendiente']['info']`; `texto_evaluacion(info)` con el formato nuevo (sigue conteniendo `Marca:` y `Juveniles:` cuando esos objetivos existen).

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_sancion_liga_v0417.py`, antes de `TESTS = [`:

```python
# ── Task 3: evaluación ───────────────────────────────────────────────────────────

def _info(**k):
    base = {'posicion': 3, 'resultado': 'cumplido', 'texto': 'Terminar entre los 5 primeros', 'monto': 0,
            'calif': 50, 'confianza': 70, 'veredicto': 'neutro', 'fallos_financieros': []}
    base.update(k)
    return base


def _con_tope(e, pos_max=5):
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=pos_max)
    return obj


def test_motivos_fallo():
    assert D.motivos_fallo({}) == []
    assert D.motivos_fallo(_info()) == []
    m = D.motivos_fallo(_info(resultado='fallado', posicion=9,
                              fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M']))
    assert m == ["Terminaste 9º; la meta era: Terminar entre los 5 primeros",
                 "Masa salarial $12.0M sobre el tope de $10.0M"]
    print("  test_motivos_fallo: OK")


def test_texto_evaluacion_variantes():
    t = D.texto_evaluacion
    assert t(_info()).startswith("Cumplió con todo lo que le pedimos")
    assert t(_info(resultado='superado', veredicto='felicitacion')).startswith("Temporada sobresaliente")
    uno = t(_info(resultado='fallado', posicion=9, veredicto='regano'))
    assert uno.startswith("Cumplió con todo menos con el objetivo de liga") and "muy importante" in uno
    assert "Es su advertencia" in uno
    dos = t(_info(resultado='fallado', posicion=9, veredicto='regano',
                  fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M']))
    assert dos.startswith("No cumplió con lo más importante:") and " y las finanzas (" in dos
    sec = t(_info(juveniles={'texto': 'Fichar un juvenil', 'resultado': 'fallado'},
                  marca={'texto': 'm', 'resultado': 'cumplido'}))
    assert sec.startswith("Cumplió con lo importante. Nos quedó pendiente el objetivo de Juveniles")
    assert "solo afecta su calificación" in sec and "Marca: cumplido" in sec and "Juveniles: fallado" in sec
    mixto = t(_info(resultado='fallado', veredicto='regano',
                    copa={'alcanzada': 'Octavos', 'texto': 'Cuartos', 'resultado': 'fallado'}))
    assert "También quedó pendiente la copa" in mixto and "Copa: fallado" in mixto
    desp = t(_info(resultado='fallado', veredicto='despido', indemnizacion=250_000))
    assert desp.startswith("Lamentamos comunicarle que prescindimos de sus servicios: no cumplió con el objetivo de liga")
    assert "Es su advertencia" not in desp and "indemnización" in desp
    fin = t(_info(veredicto='fin_contrato'))
    assert fin.startswith("Su contrato ha finalizado") and "Cumplió con todo lo que le pedimos" in fin
    san = t(_info(veredicto='regano', fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M'],
                  sancion={'temporada': 2, 'masa': 12_000_000, 'tope': 10_000_000, 'salud_mala': True,
                           'multa': 4_000_000}))
    assert "La liga sanciona al club" in san and "multa de $4.0M" in san and "Finanzas: fallado" in san
    assert t({'posicion': 1, 'resultado': 'cumplido', 'texto': 't'})          # info mínima (saves viejos)
    print("  test_texto_evaluacion_variantes: OK")


def test_evaluar_registra_sancion_y_motivos():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e)
    obj['tope_salarial'] = F.masa_salarial(mi, e) - 1                         # un peso sobre el tope
    obj['saldo_minimo'] = 0
    mi.balance = _base(e) * 2                                                 # salud buena
    info = D.evaluar_temporada(e, 3)                                          # la liga se cumple
    s = e['datos_carrera']['sancion_liga']
    assert s['temporada'] == 2 and s['salud_mala'] is False and s['multa'] == 0
    assert info['sancion'] == s and info['sancion'] is not s and info['veredicto'] == 'regano'
    assert len(info['motivos']) == 1 and info['motivos'][0].startswith("Masa salarial")
    assert e['veredicto_pendiente']['info']['motivos'] == info['motivos']
    txt = C.bandeja(e)[0]['cuerpo']
    assert "Cumplió con todo menos con las finanzas" in txt and "muy importante" in txt
    assert "La liga sanciona al club" in txt and "impone una multa" not in txt
    print("  test_evaluar_registra_sancion_y_motivos: OK")


def test_evaluar_salud_mala_trae_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e); obj['tope_salarial'] = F.masa_salarial(mi, e) - 1
    obj['presupuesto_ref'] = 0                                                # sin premio: el saldo no cambia
    mi.balance = -1_000_000
    info = D.evaluar_temporada(e, 3)
    s = e['datos_carrera']['sancion_liga']
    assert s['salud_mala'] and s['multa'] == int(_base(e) * SL.MULTA_PCT_BASE)
    assert info['sancion']['multa'] == s['multa'] and len(info['motivos']) == 2    # tope y saldo mínimo
    assert "impone una multa" in C.bandeja(e)[0]['cuerpo']
    print("  test_evaluar_salud_mala_trae_multa: OK")


def test_sin_pasar_el_tope_no_hay_sancion():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e); obj['tope_salarial'] = F.masa_salarial(mi, e) + 1; obj['saldo_minimo'] = 0
    info = D.evaluar_temporada(e, 3)
    assert 'sancion_liga' not in e['datos_carrera'] and info['sancion'] is None and info['motivos'] == []
    print("  test_sin_pasar_el_tope_no_hay_sancion: OK")


def test_cierre_financiero_cobra_la_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    F.cierre_temporada(e)
    assert s['multa_estado'] in ('pagada', 'impaga')
    if s['multa_estado'] == 'impaga':
        assert mi.balance <= 0 and mi.sancion_puntos >= SL.PUNTOS_MULTA
    print("  test_cierre_financiero_cobra_la_multa: OK")
```

Agregar a `TESTS`: `test_motivos_fallo, test_texto_evaluacion_variantes, test_evaluar_registra_sancion_y_motivos, test_evaluar_salud_mala_trae_multa, test_sin_pasar_el_tope_no_hay_sancion, test_cierre_financiero_cobra_la_multa`.

- [ ] **Step 2: Correr y ver que falla**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: los seis nuevos fallan (`AttributeError: ... 'motivos_fallo'`, textos viejos, `KeyError: 'sancion_liga'`, `multa_estado` None).

- [ ] **Step 3: `evaluar_temporada` registra la sanción y los motivos**

En `alpha_football/directiva.py`, dentro de `evaluar_temporada`, reemplazar:

```python
    fallos_fin = []
    if mi is not None:     # v4.6.0: objetivos financieros (tope salarial y saldo mínimo al cierre)
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if tope and masa > tope:
            fallos_fin.append(f"masa salarial ${masa / 1_000_000:.1f}M sobre el tope de ${tope / 1_000_000:.1f}M")
```

por:

```python
    fallos_fin = []
    sancion = None
    if mi is not None:     # v4.6.0: objetivos financieros (tope salarial y saldo mínimo al cierre)
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if tope and masa > tope:
            fallos_fin.append(f"masa salarial ${masa / 1_000_000:.1f}M sobre el tope de ${tope / 1_000_000:.1f}M")
            try:   # v0.4.17.0: además la liga sanciona al club (sin fichajes; multa si la salud es mala)
                from alpha_football import sancion_liga as SL
                sancion = SL.registrar(estado, masa, tope,
                                       int(obj.get('temporada') or estado.get('temporada', 1) or 1))
            except Exception as e_san:
                logger.error(f"No se pudo registrar la sanción de la liga: {e_san}")
```

Y reemplazar:

```python
            'fallos_financieros': fallos_fin, 'deuda': deuda}
    dc['directiva_ultimo'] = info
```

por:

```python
            'fallos_financieros': fallos_fin, 'deuda': deuda,
            'sancion': dict(sancion) if sancion else None}     # v0.4.17.0
    info['motivos'] = motivos_fallo(info)
    dc['directiva_ultimo'] = info
```

- [ ] **Step 4: `motivos_fallo` y el correo resumido**

En `alpha_football/directiva.py`, reemplazar la función `texto_evaluacion` completa por:

```python
def motivos_fallo(info: dict) -> list:
    """v0.4.17.0: una frase por objetivo PRINCIPAL fallado (liga y finanzas), para el veredicto."""
    out = []
    if info.get('resultado') == 'fallado':
        out.append(f"Terminaste {info.get('posicion', '?')}º; la meta era: {info.get('texto', '')}")
    out += [str(f)[:1].upper() + str(f)[1:] for f in info.get('fallos_financieros') or []]
    return out


def _lista(xs: list) -> str:
    """'a' / 'a y b' / 'a, b y c'."""
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1] if xs else ""


def _fallos_evaluacion(info: dict) -> tuple:
    """(principales, secundarios) fallados, redactados para el correo. Principales: liga y finanzas."""
    principales, secundarios = [], []
    if info.get('resultado') == 'fallado':
        principales.append(f"el objetivo de liga (terminó {info.get('posicion', '?')}º; la meta era: "
                           f"{info.get('texto', '')})")
    ff = info.get('fallos_financieros') or []
    if ff:
        principales.append("las finanzas (" + "; ".join(str(f) for f in ff) + ")")
    cp = info.get('copa')
    if cp and cp.get('resultado') == 'fallado':
        secundarios.append(f"la copa ({cp.get('alcanzada', '?')}; la meta era: {cp.get('texto', '')})")
    for clave, nombre in (('marca', 'Marca'), ('juveniles', 'Juveniles')):
        ev = info.get(clave)
        if ev and ev.get('resultado') == 'fallado':
            secundarios.append(f"el objetivo de {nombre} ({ev.get('texto', '')})")
    return principales, secundarios


def texto_evaluacion(info: dict) -> str:
    """Cuerpo del correo de rendimiento. v0.4.17.0: un resumen que cambia según qué se cumplió."""
    principales, secundarios = _fallos_evaluacion(info)
    v = info.get('veredicto')
    if v == 'despido':
        partes = ["Lamentamos comunicarle que prescindimos de sus servicios: no cumplió con "
                  f"{_lista(principales) or 'los objetivos'}."]
    elif not principales and not secundarios:
        partes = ["Temporada sobresaliente: superó el objetivo de liga y cumplió con todo lo demás."
                  if info.get('resultado') == 'superado' else "Cumplió con todo lo que le pedimos esta temporada."]
    elif len(principales) == 1:
        partes = [f"Cumplió con todo menos con {principales[0]}, y eso es muy importante para nosotros."]
    elif principales:
        partes = [f"No cumplió con lo más importante: {_lista(principales)}."]
    else:
        inicio = "Superó el objetivo de liga" if info.get('resultado') == 'superado' else "Cumplió con lo importante"
        partes = [f"{inicio}. Nos quedó pendiente {_lista(secundarios)} (solo afecta su calificación)."]
    if principales and secundarios:
        partes.append(f"También quedó pendiente {_lista(secundarios)}.")
    if v == 'fin_contrato':
        partes.insert(0, "Su contrato ha finalizado y no continuará en el club.")
    if v == 'regano':
        partes.append("Es su advertencia: si la próxima temporada vuelve a fallar un objetivo principal, "
                      "prescindiremos de sus servicios.")
    if info.get('sancion'):
        from alpha_football import sancion_liga as SL
        partes.append(SL.texto(info['sancion']))
    detalle = [f"Liga: {info.get('resultado', '?')}",
               "Finanzas: " + ("fallado" if info.get('fallos_financieros') else "cumplido")]
    if info.get('copa'):
        detalle.append(f"Copa: {info['copa'].get('resultado', '?')}")
    for clave, nombre in (('marca', 'Marca'), ('juveniles', 'Juveniles')):     # v4.7.0
        if info.get(clave):
            detalle.append(f"{nombre}: {info[clave].get('resultado', '?')}")
    partes.append("\n\n" + " · ".join(detalle) + ".")
    m = int(info.get('monto', 0) or 0)
    cifras = [f"{'Premio' if m >= 0 else 'Multa'} de la directiva: ${abs(m) / 1_000_000:.1f}M"]
    if info.get('deuda'):
        cifras.append(f"deuda del espaldarazo descontada: ${info['deuda'] / 1_000_000:.1f}M")
    cifras += [f"calificación de DT: {info.get('calif')}", f"confianza: {info.get('confianza')}"]
    if info.get('indemnizacion'):
        cifras.append(f"indemnización: ${info['indemnizacion'] / 1_000_000:.2f}M a tu patrimonio")
    partes.append("\n" + " · ".join(cifras) + ".")
    return " ".join(partes)
```

- [ ] **Step 5: `finanzas.cierre_temporada` cobra la multa**

En `alpha_football/finanzas.py`, después de:

```python
    try:    # v0.4.11.0: el saldo no se arrastra; va después del control de números rojos
        aplicar_presupuesto_temporada(estado)
    except Exception as e_pres:
        logger.error(f"Error fijando el presupuesto de la temporada: {e_pres}")
```

agregar:

```python
    try:    # v0.4.17.0: multa de la liga (tope salarial + mala salud) sobre el presupuesto nuevo
        from alpha_football import sancion_liga as _SL
        _SL.cobrar_multa(estado)
    except Exception as e_san:
        logger.error(f"Error cobrando la multa de la liga: {e_san}")
```

- [ ] **Step 6: Correr y ver que pasa, sin romper lo vecino**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: `18/18 tests pasaron`.

Run: `python -m pytest tests/test_directiva_v280.py tests/test_carrera_dt_v320.py tests/test_finanzas_v290.py tests/test_finanzas_v460.py tests/test_objetivos_secciones.py tests/test_vestuario_v310.py tests/test_correo_v470.py -q`
Expected: todo verde. Si algún test comprobaba una frase del correo viejo, ajustar ESE assert a la frase nueva equivalente (no cambiar el formato nuevo).

---

### Task 4: Pantalla del veredicto con los motivos

**Files:**
- Modify: `alpha_football/ui/veredicto_screen.py` (nueva `lineas_veredicto`; `render` la usa en el paso 2)
- Test: `tests/test_sancion_liga_v0417.py`

**Interfaces:**
- Consumes: `directiva.motivos_fallo(info) -> list[str]`; `info['motivos']`, `info['sancion']`.
- Produces: `veredicto_screen.lineas_veredicto(vp: dict) -> list[tuple[str, str]]` (texto, color).

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_sancion_liga_v0417.py`, antes de `TESTS = [`:

```python
# ── Task 4: veredicto ────────────────────────────────────────────────────────────

def test_veredicto_muestra_motivos_y_sancion():
    from alpha_football.ui import veredicto_screen as V
    info = _info(resultado='fallado', posicion=9, veredicto='regano',
                 fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M'],
                 sancion={'temporada': 2, 'salud_mala': True, 'multa': 4_000_000, 'masa': 12_000_000,
                          'tope': 10_000_000})
    lineas = V.lineas_veredicto({'tipo': 'regano', 'info': info})             # save viejo: sin 'motivos'
    textos = [t for t, _c in lineas]
    assert textos[0] == "Motivo: Terminaste 9º; la meta era: Terminar entre los 5 primeros"
    assert textos[1].startswith("Motivo: Masa salarial")
    assert all(c == 'rojo' for t, c in lineas if t.startswith("Motivo"))
    assert any(t.startswith("Sanción de la liga") and "multa de $4.0M" in t for t in textos)
    assert any(t.startswith("Terminaste 9º") for t in textos) and len(lineas) <= 8
    info['motivos'] = ["Uno", "Dos", "Tres", "Cuatro"]                        # nunca más de 3 motivos
    assert sum(t.startswith("Motivo") for t, _c in V.lineas_veredicto({'tipo': 'despido', 'info': info})) == 3
    ok = V.lineas_veredicto({'tipo': 'neutro', 'info': _info()})
    assert not any(t.startswith(("Motivo", "Sanción")) for t, _c in ok)
    assert V.lineas_veredicto({'tipo': 'regano', 'info': {}})                 # info vacía no rompe
    e = estado_carrera()
    e['veredicto_pendiente'] = {'correo_id': -1, 'tipo': 'regano', 'info': info}; e['veredicto_paso'] = 1
    pygame.event.clear()
    assert V.render(screen, e) is None and 'veredicto_pendiente' in e         # dibuja sin romperse
    print("  test_veredicto_muestra_motivos_y_sancion: OK")
```

Agregar `test_veredicto_muestra_motivos_y_sancion` a `TESTS`.

- [ ] **Step 2: Correr y ver que falla**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: FAIL con `AttributeError: module ... has no attribute 'lineas_veredicto'`.

- [ ] **Step 3: Implementar**

En `alpha_football/ui/veredicto_screen.py`, después de `_envolver`:

```python
def lineas_veredicto(vp: dict) -> list:
    """v0.4.17.0: [(texto, color)] bajo el título: por qué no está conforme la directiva (regaño o
    despido), la sanción de la liga si la hay y las cifras de siempre."""
    info = vp.get('info') or {}
    lineas = []
    if vp.get('tipo') in ('regano', 'despido'):
        motivos = info.get('motivos')
        if motivos is None:                      # saves viejos: el veredicto no los traía
            from alpha_football.directiva import motivos_fallo
            motivos = motivos_fallo(info)
        lineas += [(f"Motivo: {t}", 'rojo') for t in list(motivos)[:3]]
    s = info.get('sancion')
    if s:
        txt = f"Sanción de la liga: sin fichajes, libres ni préstamos en la temporada {s.get('temporada', '?')}"
        if s.get('salud_mala'):
            txt += f" y multa de ${int(s.get('multa', 0) or 0) / 1_000_000:.1f}M"
        lineas.append((txt, 'dorado'))
    m = int(info.get('monto', 0) or 0)
    lineas.append((f"Terminaste {info.get('posicion', '?')}º  ·  meta: {info.get('texto', '')}", 'blanco'))
    if info.get('copa'):
        lineas.append((f"Copa: {info['copa']['alcanzada']}  ·  meta: {info['copa']['texto']}", 'blanco'))
    lineas.append((f"{'Premio' if m >= 0 else 'Multa'}: ${abs(m) / 1_000_000:.1f}M", 'blanco'))
    lineas.append((f"Calificación de DT: {info.get('calif', '?')}  ·  confianza: {info.get('confianza', '?')}",
                   'blanco'))
    return lineas
```

Y en `render`, reemplazar:

```python
        m = int(info.get('monto', 0) or 0)
        lineas = [f"Terminaste {info.get('posicion', '?')}º  ·  meta: {info.get('texto', '')}",
                  f"{'Premio' if m >= 0 else 'Multa'}: ${abs(m) / 1_000_000:.1f}M",
                  f"Calificación de DT: {info.get('calif', '?')}  ·  confianza: {info.get('confianza', '?')}"]
        if info.get('copa'):
            lineas.insert(1, f"Copa: {info['copa']['alcanzada']}  ·  meta: {info['copa']['texto']}")
        for i, t in enumerate(lineas):
            draw_text(screen, t, (SCREEN_W // 2 - get_font('md').size(t)[0] // 2, 320 + i * 40), size='md', color='blanco')
```

por:

```python
        for i, (t, col) in enumerate(lineas_veredicto(vp)):      # v0.4.17.0: motivos y sanción antes de las cifras
            draw_text(screen, t, (SCREEN_W // 2 - get_font('md').size(t)[0] // 2, 300 + i * 40), size='md', color=col)
```

(La variable `info = vp.get('info') or {}` de más arriba queda sin uso en el paso 2: borrar esa línea.)

- [ ] **Step 4: Correr y ver que pasa**

Run: `python tests/test_sancion_liga_v0417.py`
Expected: `19/19 tests pasaron`.

Run: `python -m pytest tests/test_carrera_dt_v320.py tests/test_ayuda_v390.py -q`
Expected: verde.

---

### Task 5: `premios.py` — fechas de gala, Sudamericano, pendientes y entrega

**Files:**
- Modify: `alpha_football/premios.py` (docstring del módulo, imports, funciones nuevas al final)
- Test: `tests/test_premios_v0417.py` (nuevo)

**Interfaces:**
- Consumes: `premios.calcular_balon_de_oro(primeras, segundas, temporada, campeon_copa=None, n_podio=3, datos_copas=None)`, `paises.SUDAMERICA`, `temporada.inicio(estado) -> date`, `temporada.fecha(estado) -> date`, `correo.enviar`.
- Produces:
  - `PREMIOS: dict` — `{'balon_oro': {'nombre', 'palmares', 'frase'}, 'sudamericano': {...}}`.
  - `calcular_sudamericano(primeras, segundas, temporada, campeon_libertadores=None, datos_copas=None, n_podio=3) -> Optional[dict]`.
  - `fecha_entrega(estado, premio: str) -> date`.
  - `cerrar_temporada(estado, primeras, segundas, temporada, campeones_copas=None) -> list` — deja `datos_carrera['premios_pendientes'] = [{'premio', 'fecha_entrega' (ISO), 'datos'}]`.
  - `revisar_jornada(estado, rng=None) -> int` — entrega los vencidos; palmarés en `datos_carrera['balon_oro']` / `['sudamericano']`; galas en `datos_carrera['gala_premio_pendiente'] = [{'premio', 'fecha', 'datos'}]`; marca `estado['_parar_avance'] = True`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_premios_v0417.py`:

```python
"""v0.4.17.0: Balón de Oro en octubre y Jugador Sudamericano del Año en enero (premios por fecha)."""
import sys, os, random
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(23)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, premios as PR, temporada as T
from alpha_football.paises import SUDAMERICA
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _jugados(e, n=20):
    for mapa in (e['primera_division'], e['segunda_division']):
        for liga in mapa.values():
            for eq in getattr(liga, 'equipos', None) or []:
                for j in eq.jugadores:
                    j.partidos_jugados = n


def _datos(equipo_ganador, equipo_2="Otro FC", temporada=1):
    f = lambda nombre, eq: {'nombre': nombre, 'equipo': eq, 'liga': 'Liga', 'posicion': 'DEL', 'ovr': 80,
                            'goles': 20, 'asistencias': 5, 'nota': 7.5, 'pj': 20, 'goles_copa': 0,
                            'asistencias_copa': 0, 'puntaje': 100.0}
    podio = [f("Uno Primero", equipo_ganador), f("Dos Segundo", equipo_2), f("Tres Tercero", "Tercer FC")]
    return {'temporada': temporada, 'ganador': podio[0], 'podio': podio}


def _pendiente(e, premio, fecha, equipo, equipo_2="Otro FC"):
    e['datos_carrera'].setdefault('premios_pendientes', []).append(
        {'premio': premio, 'fecha_entrega': fecha, 'datos': _datos(equipo, equipo_2)})


# ── Task 5: lógica ───────────────────────────────────────────────────────────────

def test_fechas_de_gala():
    e = estado_carrera('premier'); e['temporada'] = 2
    ini = T.inicio(e)
    bo, sa = PR.fecha_entrega(e, 'balon_oro'), PR.fecha_entrega(e, 'sudamericano')
    assert (bo.year, bo.month, bo.weekday()) == (ini.year, 10, 0) and bo.day >= 25    # último lunes de octubre
    assert sa == date(ini.year + 1, 1, 15)                                           # Europa: el enero siguiente
    e = estado_carrera('betplay'); e['temporada'] = 2
    ini = T.inicio(e)
    assert PR.fecha_entrega(e, 'sudamericano') == date(ini.year, 1, 15)              # Sudamérica: a los 15 días
    bo = PR.fecha_entrega(e, 'balon_oro')
    assert (bo.year, bo.month, bo.weekday()) == (ini.year, 10, 0) and bo.day >= 25
    print("  test_fechas_de_gala: OK")


def test_sudamericano_solo_ligas_sudamericanas():
    e = estado_carrera('premier'); _jugados(e)
    crack = e['primera_division']['premier'].equipos[0].jugadores[-1]
    crack.goles = 60                                              # el mejor del mundo juega en Europa
    balon = PR.calcular_balon_de_oro(e['primera_division'], e['segunda_division'], 1)
    sud = PR.calcular_sudamericano(e['primera_division'], e['segunda_division'], 1)
    assert balon['ganador']['nombre'] == crack.nombre_completo
    clubes_sa = {eq.nombre for mapa in (e['primera_division'], e['segunda_division'])
                 for t, liga in mapa.items() if t in SUDAMERICA and liga is not None for eq in liga.equipos}
    assert sud and sud['temporada'] == 1 and all(p['equipo'] in clubes_sa for p in sud['podio'])
    print("  test_sudamericano_solo_ligas_sudamericanas: OK")


def test_cerrar_temporada_deja_pendientes():
    e = estado_carrera('premier'); _jugados(e); e['temporada'] = 2       # la 1 acaba de terminar
    pend = PR.cerrar_temporada(e, e['primera_division'], e['segunda_division'], 1, {})
    assert [p['premio'] for p in pend] == ['balon_oro', 'sudamericano']
    assert pend is e['datos_carrera']['premios_pendientes']
    assert all(p['datos']['temporada'] == 1 and p['datos']['ganador']['nombre'] for p in pend)
    assert pend[0]['fecha_entrega'] == PR.fecha_entrega(e, 'balon_oro').isoformat()
    assert pend[1]['fecha_entrega'] == PR.fecha_entrega(e, 'sudamericano').isoformat()
    assert 'balon_oro' not in e['datos_carrera'] and 'sudamericano' not in e['datos_carrera']
    assert 'balon_oro_ultimo' not in e and not C.bandeja(e)
    print("  test_cerrar_temporada_deja_pendientes: OK")


def test_entrega_en_la_fecha_una_sola_vez():
    e = estado_carrera('premier'); e['temporada'] = 2
    hoy = T.fecha(e)
    _pendiente(e, 'balon_oro', (hoy + timedelta(days=1)).isoformat(), "Otro FC")
    assert PR.revisar_jornada(e) == 0 and 'balon_oro' not in e['datos_carrera']      # todavía no es la gala
    e['datos_carrera']['premios_pendientes'][0]['fecha_entrega'] = hoy.isoformat()
    assert PR.revisar_jornada(e) == 1
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['nombre'] == "Uno Primero"
    msg = C.bandeja(e)[0]
    assert msg['remitente'] == 'prensa' and msg['asunto'] == "Balón de Oro: Uno Primero"
    assert "Dos Segundo" in msg['cuerpo'] and "Tres Tercero" in msg['cuerpo']
    assert not e['datos_carrera'].get('gala_premio_pendiente') and not e.get('_parar_avance')   # nadie de tu club
    assert PR.revisar_jornada(e) == 0 and len(e['datos_carrera']['balon_oro']) == 1
    assert len(C.bandeja(e)) == 1
    print("  test_entrega_en_la_fecha_una_sola_vez: OK")


def test_gala_solo_si_hay_alguien_de_tu_club():
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    hoy = T.fecha(e).isoformat()
    _pendiente(e, 'sudamericano', hoy, "Otro FC", equipo_2=mi.nombre)                # tu jugador quedó 2º
    assert PR.revisar_jornada(e) == 1
    galas = e['datos_carrera']['gala_premio_pendiente']
    assert len(galas) == 1 and galas[0]['premio'] == 'sudamericano' and galas[0]['fecha'] == hoy
    assert e['_parar_avance'] is True
    assert e['datos_carrera']['sudamericano'][-1]['ganador']['nombre'] == "Uno Primero"
    assert C.bandeja(e)[0]['asunto'] == "Jugador Sudamericano del Año: Uno Primero"
    print("  test_gala_solo_si_hay_alguien_de_tu_club: OK")


def test_respaldo_al_cerrar_la_temporada_siguiente():
    e = estado_carrera('premier'); _jugados(e); e['temporada'] = 3; mi = e['mi_equipo']
    _pendiente(e, 'balon_oro', "2999-10-25", mi.nombre)                               # nadie lo entregó
    pend = PR.cerrar_temporada(e, e['primera_division'], e['segunda_division'], 2, {})
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['nombre'] == "Uno Primero"  # entra al palmarés
    assert not e['datos_carrera'].get('gala_premio_pendiente')                        # sin gala atrasada
    assert [p['premio'] for p in pend] == ['balon_oro', 'sudamericano']
    assert all(p['datos']['temporada'] == 2 for p in pend)                            # sin duplicar el viejo
    print("  test_respaldo_al_cerrar_la_temporada_siguiente: OK")


def test_save_viejo_y_datos_danados():
    e = estado_carrera('premier')
    assert PR.revisar_jornada(e) == 0                                                 # sin la clave
    e['datos_carrera']['premios_pendientes'] = ["basura", {'premio': 'no_existe', 'fecha_entrega': "2000-01-01"},
                                                 {'premio': 'balon_oro', 'fecha_entrega': "2000-01-01", 'datos': {}}]
    PR.revisar_jornada(e)
    assert e['datos_carrera']['premios_pendientes'] == []
    assert not e['datos_carrera'].get('balon_oro') and not C.bandeja(e)
    assert PR.revisar_jornada({'datos_carrera': {'premios_pendientes': [{}]}}) == 0   # sin liga ni club
    print("  test_save_viejo_y_datos_danados: OK")


TESTS = [test_fechas_de_gala, test_sudamericano_solo_ligas_sudamericanas, test_cerrar_temporada_deja_pendientes,
         test_entrega_en_la_fecha_una_sola_vez, test_gala_solo_si_hay_alguien_de_tu_club,
         test_respaldo_al_cerrar_la_temporada_siguiente, test_save_viejo_y_datos_danados]

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

Run: `python tests/test_premios_v0417.py`
Expected: los siete fallan con `AttributeError` (`fecha_entrega`, `calcular_sudamericano`, `cerrar_temporada`, `revisar_jornada`).

- [ ] **Step 3: Implementar**

En `alpha_football/premios.py`:

Reemplazar el docstring del módulo por:

```python
"""
Alpha Football v2.3.6 — BALÓN DE ORO.

Al cerrar la temporada se elige al mejor jugador de TODAS las ligas (1ª y 2ª de los
5 países) según su rendimiento de la temporada: nota media, goles, asistencias,
vallas invictas, títulos (liga y copa) y el peso de la liga donde jugó.
Mecánica pura y testeable: recibe las ligas y devuelve un dict serializable.

v0.4.17.0: los premios se CALCULAN al cerrar la temporada pero se ENTREGAN en una fecha: el Balón de
Oro el último lunes de octubre y el Jugador Sudamericano del Año (los que juegan en las ligas
sudamericanas) el 15 de enero. Mientras tanto esperan en datos_carrera['premios_pendientes'].
"""
```

Reemplazar `from typing import Any, Optional` por:

```python
from datetime import date, timedelta
from typing import Any, Optional
```

Y agregar al final del archivo:

```python


# ── v0.4.17.0: premios por fecha ─────────────────────────────────────────────────

PREMIOS = {
    'balon_oro': {'nombre': "Balón de Oro", 'palmares': 'balon_oro', 'frase': "gana el Balón de Oro"},
    'sudamericano': {'nombre': "Jugador Sudamericano del Año", 'palmares': 'sudamericano',
                     'frase': "es elegido Jugador Sudamericano del Año"},
}


def calcular_sudamericano(primeras: dict, segundas: dict, temporada: int, campeon_libertadores=None,
                          datos_copas: Optional[dict] = None, n_podio: int = 3) -> Optional[dict]:
    """El mejor de los que juegan en las ligas sudamericanas (1ª y 2ª), con su Libertadores. Misma
    fórmula y mismo dict que el Balón de Oro."""
    from alpha_football.paises import SUDAMERICA
    solo = lambda mapa: {t: l for t, l in (mapa or {}).items() if t in SUDAMERICA}
    copas = {k: v for k, v in (datos_copas or {}).items() if k == 'libertadores'}
    return calcular_balon_de_oro(solo(primeras), solo(segundas), temporada, campeon_libertadores, n_podio, copas)


def _gala_en(premio: str, anio: int) -> date:
    if premio == 'sudamericano':
        return date(anio, 1, 15)
    d = date(anio, 10, 31)                               # Balón de Oro: último lunes de octubre
    return d - timedelta(days=d.weekday())


def fecha_entrega(estado: dict, premio: str) -> date:
    """La primera gala de ese premio en o después del inicio de la temporada en curso (al cerrar una
    temporada, la que acaba de empezar)."""
    from alpha_football import temporada as T
    ini = T.inicio(estado)
    d = _gala_en(premio, ini.year)
    return d if d >= ini else _gala_en(premio, ini.year + 1)


def _pendientes(estado: dict) -> list:
    dc = estado.setdefault('datos_carrera', {})
    if not isinstance(dc.get('premios_pendientes'), list):
        dc['premios_pendientes'] = []
    return dc['premios_pendientes']


def _entregar(estado: dict, p: dict, gala: bool = True) -> bool:
    """Entrega un premio: palmarés, noticia de Prensa y, si alguien del podio juega en tu club, la gala.
    Un pendiente dañado (premio desconocido o sin ganador) se descarta."""
    cfg, datos = PREMIOS.get(p.get('premio')), p.get('datos') or {}
    g = datos.get('ganador') or {}
    if cfg is None or not g:
        return False
    dc = estado.setdefault('datos_carrera', {})
    dc.setdefault(cfg['palmares'], []).append(datos)
    podio = datos.get('podio') or [g]
    try:
        from alpha_football import correo as C
        otros = "".join(f" {i + 2}º: {x.get('nombre', '?')} ({x.get('equipo', '?')})."
                        for i, x in enumerate(podio[1:3]))
        C.enviar(estado, 'prensa', f"{cfg['nombre']}: {g.get('nombre', '?')}",
                 f"{g.get('nombre', '?')} ({g.get('equipo', '?')}, {g.get('liga', '?')}) {cfg['frase']} de la "
                 f"temporada {datos.get('temporada', '?')}: {g.get('goles', 0)} goles, {g.get('asistencias', 0)} "
                 f"asistencias y nota {float(g.get('nota', 0) or 0):.2f}.{otros}",
                 C.accion('career_screen', "VER PALMARÉS"))
    except Exception as e:
        logger.error(f"No se pudo anunciar el {cfg['nombre']}: {e}")
    mi = getattr(estado.get('mi_equipo'), 'nombre', None)
    if gala and mi and any(x.get('equipo') == mi for x in podio):
        dc.setdefault('gala_premio_pendiente', []).append(
            {'premio': p['premio'], 'fecha': p.get('fecha_entrega'), 'datos': datos})
        estado['_parar_avance'] = True                   # dias.continuar frena el día de la gala
    return True


def cerrar_temporada(estado: dict, primeras: dict, segundas: dict, temporada: int,
                     campeones_copas: Optional[dict] = None) -> list:
    """Cierre de temporada, con las tablas finales intactas: calcula los premios de `temporada` y los
    deja pendientes hasta su gala. Lo que siguiera pendiente de la anterior se entrega ya, sin gala."""
    pend = _pendientes(estado)
    for p in list(pend):
        try:
            if isinstance(p, dict):
                _entregar(estado, p, gala=False)
        except Exception as e:
            logger.error(f"No se pudo entregar un premio atrasado: {e}")
    del pend[:]
    campeones = campeones_copas or {}
    datos_copas = (estado.get('datos_carrera') or {}).get('copas')
    calculos = (
        ('balon_oro', lambda: calcular_balon_de_oro(primeras, segundas, temporada,
                                                   [c for c in campeones.values() if c], datos_copas=datos_copas)),
        ('sudamericano', lambda: calcular_sudamericano(primeras, segundas, temporada,
                                                       campeones.get('libertadores'), datos_copas)),
    )
    for premio, calcular in calculos:
        try:
            datos = calcular()
            if datos:
                pend.append({'premio': premio, 'fecha_entrega': fecha_entrega(estado, premio).isoformat(),
                             'datos': datos})
                logger.info(f"{PREMIOS[premio]['nombre']} T{temporada}: {datos['ganador']['nombre']} "
                            f"({datos['ganador']['equipo']}), se entrega el {pend[-1]['fecha_entrega']}")
        except Exception as e:
            logger.error(f"Error calculando el {PREMIOS[premio]['nombre']}: {e}")
    return pend


def revisar_jornada(estado: dict, rng=None) -> int:
    """Entrega los premios cuya gala ya llegó. Idempotente y sin UI: se llama cada día (dias.revisar_dia)
    y después de cada partido. Devuelve cuántos entregó."""
    pend = (estado.get('datos_carrera') or {}).get('premios_pendientes')
    if not pend or estado.get('liga') is None or estado.get('mi_equipo') is None:
        return 0
    from alpha_football import temporada as T
    hoy = T.fecha(estado).isoformat()
    vencen = [p for p in pend if not isinstance(p, dict) or str(p.get('fecha_entrega') or '') <= hoy]
    entregados = 0
    for p in vencen:
        pend.remove(p)
        try:
            entregados += int(isinstance(p, dict) and _entregar(estado, p))
        except Exception as e:
            logger.error(f"No se pudo entregar un premio: {e}", exc_info=True)
    return entregados
```

- [ ] **Step 4: Correr y ver que pasa**

Run: `python tests/test_premios_v0417.py`
Expected: `7/7 tests pasaron`.

Run: `python -m pytest tests/test_copa_v430.py -q`
Expected: verde (usa `calcular_balon_de_oro`, que no cambió).

---

### Task 6: Enganches — cierre de temporada, cada día y después de cada partido

**Files:**
- Modify: `alpha_football/ui/resumen_temporada_screen.py` (bloque del Balón en `avanzar_nueva_temporada`, ~293-304)
- Modify: `alpha_football/dias.py` (tupla `pasos` de `revisar_dia`)
- Modify: `alpha_football/ui/match_screen.py` (junto a `patrocinios.revisar_jornada`, ~565-569)
- Modify: `tests/test_v236.py:161-171`, `tests/test_competiciones_v380.py:449-450`
- Test: `tests/test_premios_v0417.py`

**Interfaces:**
- Consumes: `premios.cerrar_temporada(estado, primeras, segundas, temporada, campeones_copas)`, `premios.revisar_jornada(estado)`.
- Produces: tras `avanzar_nueva_temporada`, `datos_carrera['premios_pendientes']` con los dos premios; `estado['balon_oro_ultimo']` deja de existir.

- [ ] **Step 1: Escribir el test que falla**

En `tests/test_premios_v0417.py`, antes de `TESTS = [`:

```python
# ── Task 6: enganches ────────────────────────────────────────────────────────────

def test_el_reloj_entrega_el_dia_de_la_gala():
    from alpha_football import dias
    e = estado_carrera('premier'); e['temporada'] = 2; mi = e['mi_equipo']
    hoy = dias.hoy(e)                                             # crea el reloj
    _pendiente(e, 'balon_oro', hoy.isoformat(), mi.nombre)
    assert dias.revisar_dia(e, hoy) is not False                  # devuelve el hito del día (o None)
    assert e['datos_carrera']['balon_oro'][-1]['ganador']['equipo'] == mi.nombre
    assert e['datos_carrera']['premios_pendientes'] == [] and e['datos_carrera']['gala_premio_pendiente']
    print("  test_el_reloj_entrega_el_dia_de_la_gala: OK")
```

Agregar `test_el_reloj_entrega_el_dia_de_la_gala` a `TESTS`.

Y ajustar los dos tests existentes que leían el palmarés justo después del cierre.

`tests/test_v236.py`, reemplazar:

```python
    balon = (estado['datos_carrera'].get('balon_oro') or [None])[-1]
    assert balon and balon['ganador']['nombre'], balon
```

por:

```python
    # v0.4.17.0: el Balón se calcula al cierre pero se entrega en octubre: queda pendiente
    pend = {p['premio']: p for p in estado['datos_carrera']['premios_pendientes']}
    assert set(pend) == {'balon_oro', 'sudamericano'} and 'balon_oro' not in estado['datos_carrera']
    from alpha_football import premios as _PR
    for p in pend.values():
        p['fecha_entrega'] = "2000-01-01"
    assert _PR.revisar_jornada(estado) == 2
    balon = (estado['datos_carrera'].get('balon_oro') or [None])[-1]
    assert balon and balon['ganador']['nombre'], balon
    assert estado['datos_carrera']['sudamericano'][-1]['ganador']['nombre']
```

`tests/test_competiciones_v380.py`, reemplazar:

```python
    balon = e['datos_carrera']['balon_oro'][-1]
    assert balon['temporada'] == 1 and 'goles_copa' in balon['ganador']
```

por:

```python
    # v0.4.17.0: el Balón queda pendiente hasta octubre (premios.revisar_jornada lo entrega)
    balon = next(p['datos'] for p in e['datos_carrera']['premios_pendientes'] if p['premio'] == 'balon_oro')
    assert balon['temporada'] == 1 and 'goles_copa' in balon['ganador']
    assert 'balon_oro' not in e['datos_carrera']
```

- [ ] **Step 2: Correr y ver que falla**

Run: `python tests/test_premios_v0417.py`
Expected: `test_el_reloj_entrega_el_dia_de_la_gala` FAIL con `KeyError: 'balon_oro'`.

Run: `python -m pytest tests/test_v236.py::test_temporada_completa_descensos_y_balon tests/test_competiciones_v380.py::test_fin_de_temporada_copas_y_balon -q`
Expected: los dos FAIL con `KeyError: 'premios_pendientes'`.

- [ ] **Step 3: El cierre deja los premios pendientes**

En `alpha_football/ui/resumen_temporada_screen.py`, reemplazar:

```python
        try:
            from alpha_football.premios import calcular_balon_de_oro
            # v3.8.0: campeones de las dos copas + goles/asistencias de copa de cada jugador
            balon = calcular_balon_de_oro(primeras, segunda, temp_anterior,
                                          [c for c in campeones_copas.values() if c],
                                          datos_copas=(estado.get('datos_carrera') or {}).get('copas'))
            if balon:
                estado.setdefault('datos_carrera', {}).setdefault('balon_oro', []).append(balon)
                estado['balon_oro_ultimo'] = balon
                logger.info(f"Balón de Oro T{temp_anterior}: {balon['ganador']['nombre']} ({balon['ganador']['equipo']})")
        except Exception as e_balon:
            logger.error(f"Error calculando el Balón de Oro: {e_balon}")
```

por:

```python
        try:   # v0.4.17.0: Balón de Oro y Sudamericano del Año se calculan aquí y se entregan en su gala
            from alpha_football import premios as _premios
            _premios.cerrar_temporada(estado, primeras, segunda, temp_anterior, campeones_copas)
        except Exception as e_balon:
            logger.error(f"Error calculando los premios de la temporada: {e_balon}")
```

Y en el comentario de más arriba cambiar `#   - Balón de Oro al mejor rendimiento de las 10 ligas` por `#   - Balón de Oro y Sudamericano del Año (se entregan en octubre y en enero)`.

- [ ] **Step 4: Revisar cada día y después de cada partido**

En `alpha_football/dias.py`, en `revisar_dia`, reemplazar:

```python
    pasos = (('cantera', 'revisar_jornada'), ('patrocinios', 'revisar_jornada'), ('prestamos', 'revisar_jornada'))
```

por:

```python
    pasos = (('cantera', 'revisar_jornada'), ('patrocinios', 'revisar_jornada'), ('prestamos', 'revisar_jornada'),
             ('premios', 'revisar_jornada'))                     # v0.4.17.0: galas del Balón de Oro y del Sudamericano
```

(Si `lol` ya cambió esa tupla, agregar solo el elemento `('premios', 'revisar_jornada')` al final.)

En `alpha_football/ui/match_screen.py`, después de:

```python
        try:  # v4.9.0: patrocinios (ofertas de invierno y ofertas que vencen con la ventana)
            from alpha_football import patrocinios as _patro
            _patro.revisar_jornada(estado)
        except Exception as e_pat:
            logger.error(f"Error revisando los patrocinios: {e_pat}")
```

agregar:

```python
        try:  # v0.4.17.0: partidas sin reloj: la gala del Balón de Oro / Sudamericano se revisa aquí
            from alpha_football import premios as _premios_j
            _premios_j.revisar_jornada(estado)
        except Exception as e_prem:
            logger.error(f"Error revisando los premios: {e_prem}")
```

- [ ] **Step 5: Correr y ver que pasa**

Run: `python tests/test_premios_v0417.py`
Expected: `8/8 tests pasaron`.

Run: `python -m pytest tests/test_v236.py tests/test_competiciones_v380.py tests/test_dias.py tests/test_copa_v430.py -q`
Expected: verde.

---

### Task 7: Pantallas — gala, hub, ascensos sin Balón y palmarés doble

**Files:**
- Create: `alpha_football/ui/gala_balon_screen.py`
- Modify: `main.py` (`MODULOS_PANTALLA`, `SIN_ATAJOS_GLOBALES`)
- Modify: `alpha_football/ui/league_screen.py` (`render`, tras el `try` de `restaurar_despido`)
- Modify: `alpha_football/ui/atajos.py` (una línea en `ATAJOS`)
- Modify: `alpha_football/ui/ayuda.py` (`_ayuda_promo`, `_ayuda_carrera`, nuevo `_ayuda_gala`)
- Modify: `alpha_football/ui/promo_releg_screen.py` (sin caja del Balón)
- Modify: `alpha_football/ui/career_screen.py` (dos palmarés)
- Test: `tests/test_premios_v0417.py`

**Interfaces:**
- Consumes: `datos_carrera['gala_premio_pendiente'] = [{'premio', 'fecha', 'datos'}]`, `premios.PREMIOS`, `datos_carrera['balon_oro']`, `datos_carrera['sudamericano']`.
- Produces: pantalla `'gala_balon_screen'` (`render(screen, estado) -> Optional[str]`: None mientras se ve, `'league_screen'` al terminar); `career_screen.palmares(estado) -> list[tuple[str, list]]`.

- [ ] **Step 1: Escribir los tests que fallan**

En `tests/test_premios_v0417.py`, antes de `TESTS = [`:

```python
# ── Task 7: pantallas ────────────────────────────────────────────────────────────

def test_gala_screen_flujo():
    from alpha_football.ui import gala_balon_screen as G
    e = estado_carrera('premier'); mi = e['mi_equipo']
    e['datos_carrera']['gala_premio_pendiente'] = [
        {'premio': 'balon_oro', 'fecha': "2027-10-25", 'datos': _datos(mi.nombre)},
        {'premio': 'sudamericano', 'fecha': "2028-01-15", 'datos': _datos("Otro FC", equipo_2=mi.nombre)}]
    pygame.event.clear(); assert G.render(screen, e) is None                  # se queda en la gala
    assert len(e['datos_carrera']['gala_premio_pendiente']) == 2
    key(pygame.K_RETURN); assert G.render(screen, e) is None                   # pasa a la segunda
    assert [g['premio'] for g in e['datos_carrera']['gala_premio_pendiente']] == ['sudamericano']
    key(pygame.K_RETURN); assert G.render(screen, e) == 'league_screen'
    assert e['datos_carrera']['gala_premio_pendiente'] == []
    print("  test_gala_screen_flujo: OK")


def test_gala_screen_no_se_traba():
    from alpha_football.ui import gala_balon_screen as G
    e = estado_carrera('premier')
    pygame.event.clear(); assert G.render(screen, e) == 'league_screen'        # sin galas
    e['datos_carrera']['gala_premio_pendiente'] = ["basura", {'premio': 'balon_oro'}, {'datos': {'ganador': {}}}]
    pygame.event.clear(); assert G.render(screen, e) == 'league_screen'        # datos dañados: se descartan
    assert e['datos_carrera']['gala_premio_pendiente'] == []
    e['datos_carrera']['gala_premio_pendiente'] = [{'premio': 'otro', 'fecha': "ayer",
                                                    'datos': {'ganador': {'nombre': "X"}}}]
    pygame.event.clear(); assert G.render(screen, e) is None                   # incompleta pero dibujable
    print("  test_gala_screen_no_se_traba: OK")


def test_hub_abre_la_gala_y_esta_registrada():
    orig_get = pygame.event.get                      # main reemplaza pygame.event.get al importarse
    try:
        import main
    finally:
        pygame.event.get = orig_get
    assert 'gala_balon_screen' in main.nombres_pantallas() and 'gala_balon_screen' in main.SIN_ATAJOS_GLOBALES
    from alpha_football.ui import league_screen as L, atajos as A, ayuda as AY
    assert 'gala_balon_screen' in A.ATAJOS and len(AY.items('gala_balon_screen', {})) >= 3
    e = estado_carrera('premier')
    e['datos_carrera']['gala_premio_pendiente'] = [{'premio': 'balon_oro', 'fecha': "2027-10-25",
                                                    'datos': _datos(e['mi_equipo'].nombre)}]
    pygame.event.clear(); assert L.render(screen, e) == 'gala_balon_screen'
    print("  test_hub_abre_la_gala_y_esta_registrada: OK")


def test_ascensos_sin_balon_y_palmares_doble():
    from alpha_football.ui import promo_releg_screen as P, career_screen as K, ayuda as AY
    assert 'balon' not in P.rects_promo()
    e = estado_carrera('premier')
    assert not any(t == "Balón de Oro" for _r, t, _x in AY.items('promo_releg_screen', e))
    e['promo_releg_data'] = {'ascendidos': [], 'descendidos': []}
    pygame.event.clear(); assert P.render(screen, e) is None                   # dibuja sin la caja
    e['datos_carrera']['balon_oro'] = [_datos("A", temporada=t) for t in (1, 2, 3, 4)]
    e['datos_carrera']['sudamericano'] = [_datos("B", temporada=1)]
    pal = K.palmares(e)
    assert [t for t, _l in pal] == ["BALÓN DE ORO", "SUDAMERICANO DEL AÑO"]
    assert [b['temporada'] for b in pal[0][1]] == [4, 3, 2] and [b['temporada'] for b in pal[1][1]] == [1]
    pygame.event.clear(); assert K.render(screen, e) is None
    assert K.palmares({'datos_carrera': {}}) == [("BALÓN DE ORO", []), ("SUDAMERICANO DEL AÑO", [])]
    print("  test_ascensos_sin_balon_y_palmares_doble: OK")
```

Agregar los cuatro a `TESTS`.

- [ ] **Step 2: Correr y ver que falla**

Run: `python tests/test_premios_v0417.py`
Expected: los cuatro nuevos fallan (`ImportError: gala_balon_screen`, `'balon' in rects_promo()`, `AttributeError: palmares`).

- [ ] **Step 3: La pantalla de gala**

Crear `alpha_football/ui/gala_balon_screen.py`:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Gala de premios (Pygame, v0.4.17.0)
Balón de Oro (octubre) y Jugador Sudamericano del Año (enero). Solo se abre si el ganador o alguien
del podio juega en tu club: el hub la muestra una vez por gala (datos_carrera['gala_premio_pendiente']).
Enter, Espacio o clic pasa a la siguiente gala o vuelve al hub.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, SCREEN_H, get_font, draw_gradient_bg, draw_text
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre')
R_PREMIO = pygame.Rect(140, 70, 1000, 110)       # expuestos (ayuda H)
R_GANADOR = pygame.Rect(140, 210, 1000, 170)
R_PODIO = pygame.Rect(140, 410, 1000, 120)


def _pendientes(estado: dict) -> list:
    dc = estado.setdefault('datos_carrera', {})
    if not isinstance(dc.get('gala_premio_pendiente'), list):
        dc['gala_premio_pendiente'] = []
    return dc['gala_premio_pendiente']


def _valida(g) -> bool:
    return isinstance(g, dict) and bool(((g.get('datos') or {}).get('ganador') or {}).get('nombre'))


def _fecha_larga(txt) -> str:
    try:
        d = date.fromisoformat(str(txt))
        return f"Gala del {d.day} de {MESES[d.month - 1]} de {d.year}"
    except Exception:
        return ""


def _centrado(screen, txt: str, y: int, size: str, color: str) -> None:
    draw_text(screen, txt, (SCREEN_W // 2 - get_font(size).size(txt)[0] // 2, y), size=size, color=color)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        pend = _pendientes(estado)
        while pend and not _valida(pend[0]):         # gala dañada: se descarta y no traba el hub
            pend.pop(0)
        if not pend:
            return 'league_screen'
        avanzar = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                                                        pygame.K_ESCAPE):
                avanzar = True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                avanzar = True
        if avanzar:
            pend.pop(0)
            while pend and not _valida(pend[0]):
                pend.pop(0)
            return None if pend else 'league_screen'

        from alpha_football.premios import PREMIOS
        gala = pend[0]
        datos = gala['datos']
        g = datos['ganador']
        nombre = (PREMIOS.get(gala.get('premio')) or {}).get('nombre', "Premio de la temporada")
        mi = getattr(estado.get('mi_equipo'), 'nombre', None)
        color = lambda x: 'verde' if mi and x.get('equipo') == mi else 'blanco'

        draw_gradient_bg(screen)
        _centrado(screen, f"{nombre.upper()} · TEMPORADA {datos.get('temporada', '?')}", 90, 'xl', 'dorado')
        _centrado(screen, _fecha_larga(gala.get('fecha')), 150, 'sm', 'azul')
        _centrado(screen, str(g.get('nombre', '?'))[:40], 230, 'xl', color(g))
        _centrado(screen, f"{str(g.get('equipo', '?'))[:28]} · {str(g.get('liga', '?'))[:32]} · "
                          f"{g.get('posicion', '?')} {g.get('ovr', '?')}", 300, 'md', 'blanco')
        _centrado(screen, f"{g.get('goles', 0)} goles · {g.get('asistencias', 0)} asistencias · "
                          f"nota {float(g.get('nota', 0) or 0):.2f} · {g.get('pj', 0)} partidos", 340, 'md', 'azul')
        for i, x in enumerate((datos.get('podio') or [])[1:3]):
            _centrado(screen, f"{i + 2}º  {str(x.get('nombre', '?'))[:30]} ({str(x.get('equipo', '?'))[:24]}) · "
                              f"{x.get('goles', 0)} G · nota {float(x.get('nota', 0) or 0):.2f}",
                      430 + i * 44, 'md', color(x))
        draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
        return None
    except Exception as e:
        logger.error(f"Error en gala_balon_screen: {e}", exc_info=True)
        estado.setdefault('datos_carrera', {})['gala_premio_pendiente'] = []
        return 'league_screen'
```

- [ ] **Step 4: Registrar la pantalla y abrirla desde el hub**

En `main.py`, en `MODULOS_PANTALLA`, después de la línea de `'veredicto_screen'`:

```python
    'gala_balon_screen': 'alpha_football.ui.gala_balon_screen',   # v0.4.17.0
```

En `main.py`, en `SIN_ATAJOS_GLOBALES`, reemplazar `'negociacion_screen'}` por `'negociacion_screen', 'gala_balon_screen'}`.

En `alpha_football/ui/league_screen.py`, dentro de `render`, justo después de:

```python
        except Exception as e_desp:
            logger.error(f"Error al revisar el despido pendiente: {e_desp}")
```

agregar:

```python

        # v0.4.17.0: gala del Balón de Oro / Sudamericano del Año (solo si alguien del podio es de tu club)
        if (estado.get('datos_carrera') or {}).get('gala_premio_pendiente'):
            return 'gala_balon_screen'
```

En `alpha_football/ui/atajos.py`, después de la línea `'veredicto_screen': "Enter Continuar · H Ayuda",`:

```python
    'gala_balon_screen': "Enter Continuar · H Ayuda",   # v0.4.17.0
```

En `alpha_football/ui/ayuda.py`, después de `AYUDA['veredicto_screen'] = _ayuda_veredicto`:

```python


# ---------------------------------------------------------------- gala de premios (v0.4.17.0)
def _ayuda_gala(estado: dict) -> list:
    from alpha_football.ui import gala_balon_screen as G
    return [
        (G.R_PREMIO, "Premio", "Qué premio se entrega, de qué temporada y la fecha de la gala."),
        (G.R_GANADOR, "Ganador", "El ganador con su club, su liga y sus números; en verde si juega en tu club."),
        (G.R_PODIO, "Podio", "Segundo y tercer puesto; en verde los de tu club."),
        (R(12, 652, 300, 36), "Continuar", "Enter, Espacio o clic para seguir."),
    ]


AYUDA['gala_balon_screen'] = _ayuda_gala
```

- [ ] **Step 5: Ascensos sin la caja del Balón**

En `alpha_football/ui/promo_releg_screen.py`:

Borrar de `rects_promo` la línea `'balon': pygame.Rect(40, 100, SCREEN_W - 80, 96),`.

Borrar el bloque que empieza en `# v2.3.6: Balón de Oro de la temporada que terminó (mejor rendimiento de las 10 ligas)` y termina en el `draw_text(screen, "BALÓN DE ORO: sin candidatos esta temporada", ...)` con su `size='md', color='azul')` (las 19 líneas entre `_centrado(sub, 64, 'sm', 'azul')` y `# Tu país: ascendidos (izq.) y descendidos (der.)`), dejando una línea en blanco entre ambos.

Borrar la línea `estado.pop('balon_oro_ultimo', None)`.

En `alpha_football/ui/ayuda.py`, en `_ayuda_promo`, borrar la línea:

```python
        (r['balon'], "Balón de Oro", "Mejor jugador de la temporada entre las 10 ligas y su podio."),
```

- [ ] **Step 6: Palmarés doble en CARRERA**

En `alpha_football/ui/career_screen.py`, antes de `def render(`:

```python
def palmares(estado: dict) -> list:
    """v0.4.17.0: [(título, los 3 últimos ganadores, del más nuevo al más viejo)] de los dos premios."""
    dc = estado.get('datos_carrera') or {}
    return [(titulo, list(reversed(list(dc.get(clave) or [])[-3:])))
            for titulo, clave in (("BALÓN DE ORO", 'balon_oro'), ("SUDAMERICANO DEL AÑO", 'sudamericano'))]
```

Y reemplazar el bloque:

```python
        # --- Balón de Oro (palmarés de todas las ligas) ---
        balones = list(((estado.get('datos_carrera') or {}).get('balon_oro') or []))
        caja_bo = R_BALON_ORO
        draw_panel(screen, caja_bo)
        draw_text(screen, "BALÓN DE ORO", (caja_bo.x + 18, caja_bo.y + 12), size='md', color='dorado')
        if not balones:
            draw_text(screen, "Se entrega al cerrar cada", (caja_bo.x + 18, caja_bo.y + 56), size='sm', color='blanco')
            draw_text(screen, "temporada al mejor de las 10 ligas.", (caja_bo.x + 18, caja_bo.y + 80), size='sm', color='blanco')
        for i, b in enumerate(reversed(balones[-6:])):
            g = b.get('ganador') or {}
            yy = caja_bo.y + 50 + i * 38
            es_mio = g.get('equipo') == mi_equipo.nombre
            draw_text(screen, f"T{b.get('temporada', '?')}  {str(g.get('nombre', '?'))[:22]}", (caja_bo.x + 18, yy),
                      size='sm', color='verde' if es_mio else 'blanco')
            draw_text(screen, f"{str(g.get('equipo', '?'))[:18]} · {g.get('goles', 0)} G · {g.get('nota', 0):.1f}",
                      (caja_bo.x + 40, yy + 18), size='sm', color='azul', shadow=False)
```

por:

```python
        # --- Premios (v0.4.17.0: Balón de Oro en octubre y Sudamericano del Año en enero) ---
        caja_bo = R_BALON_ORO
        draw_panel(screen, caja_bo)
        for k, (titulo, ganadores) in enumerate(palmares(estado)):
            y0 = caja_bo.y + 8 + k * 140
            draw_text(screen, titulo, (caja_bo.x + 18, y0), size='md', color='dorado')
            if not ganadores:
                draw_text(screen, "Se entrega en octubre." if k == 0 else "Se entrega en enero.",
                          (caja_bo.x + 18, y0 + 36), size='sm', color='blanco')
            for i, b in enumerate(ganadores):
                g = b.get('ganador') or {}
                yy = y0 + 30 + i * 36
                es_mio = g.get('equipo') == mi_equipo.nombre
                draw_text(screen, f"T{b.get('temporada', '?')}  {str(g.get('nombre', '?'))[:22]}", (caja_bo.x + 18, yy),
                          size='sm', color='verde' if es_mio else 'blanco')
                draw_text(screen, f"{str(g.get('equipo', '?'))[:18]} · {g.get('goles', 0)} G · {g.get('nota', 0):.1f}",
                          (caja_bo.x + 40, yy + 17), size='sm', color='azul', shadow=False)
```

En `alpha_football/ui/ayuda.py`, en `_ayuda_carrera`, reemplazar:

```python
        (C.R_BALON_ORO, "Balón de Oro", "Ganadores de cada temporada entre las 10 ligas; en verde si es de tu club."),
```

por:

```python
        (C.R_BALON_ORO, "Premios", "Balón de Oro y Sudamericano del Año de cada temporada; en verde si es de tu club."),
```

- [ ] **Step 7: Correr y ver que pasa**

Run: `python tests/test_premios_v0417.py`
Expected: `12/12 tests pasaron`.

Run: `python -m pytest tests/test_ayuda_v390.py tests/test_ux_v360.py tests/test_divisiones_v235.py tests/test_carrera_dt_v320.py tests/test_hub_v240.py tests/test_ui_v235.py tests/test_teclado_v420.py -q`
Expected: verde.

- [ ] **Step 8: Verlo en el juego**

Con la skill `run`: abrir una carrera, forzar una gala (en una consola de Python con el save cargado, o editando el save de prueba: `datos_carrera['gala_premio_pendiente']` con un ganador de tu club) y comprobar a ojo la gala, la pantalla de ascensos sin la caja y el palmarés de CARRERA. Captura de pantalla de cada una. Ajustar posiciones solo si algo se encima.

---

### Task 8: Verificación final y continuidad

**Files:**
- Modify: `context.md` (estado actual + bitácora "Sanción por tope salarial y premios por fecha")
- Modify: `C:\Users\diego\.claude\projects\C--Users-diego-Downloads-AlphaFootball\memory\numeracion-versiones.md` y su línea en `MEMORY.md`

- [ ] **Step 1: Suite completa**

Run: `python -m pytest tests -q -p no:cacheprovider`
Expected: todo verde. Un rojo en archivos de `lol` (dias, dia_final, calendario, temporada, notificaciones, presupuesto_ventanas, pedidos) se le avisa por mensaje con el nombre del test y la traza; no se toca.

- [ ] **Step 2: Los dos archivos nuevos por su runner**

Run: `python tests/test_sancion_liga_v0417.py && python tests/test_premios_v0417.py`
Expected: `19/19 tests pasaron` y `12/12 tests pasaron`.

- [ ] **Step 3: Avisar a `lol` y actualizar la continuidad**

Mensaje a `lol` con la lista exacta de lo tocado en sus archivos (tupla de `dias.revisar_dia`, `ayuda.py` ×3, `atajos.py` ×1, `main.py` ×2, `league_screen.render` ×1, bloque del Balón) y el resultado de la suite.

En `context.md`: fecha del encabezado, v0.4.17.0 "implementado SIN commit", y una bitácora corta con las reglas (sanción, multa 40%, −6 puntos, galas) y los archivos nuevos. En la memoria: 0.4.15.0 = E, 0.4.16.0 = F, 0.4.17.0 = sanción + premios (en curso), próxima libre 0.4.18.0.

- [ ] **Step 4: Informe a Diego**

Qué quedó hecho, resultado de los tests con sus números, qué se vio en el juego, y que no hay commit (lo decide él).
