# Préstamos de jugadores — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pedir jugadores a préstamo y ceder los propios (6 meses / 1 año, sueldo repartido en %), con idas y vueltas solo en ventana de mercado.

**Architecture:** Módulo nuevo `alpha_football/prestamos.py` (lógica pura, sin UI) + campo persistido `Jugador.prestamo`. Estado de la carrera en `datos_carrera` (`prestamos_pendientes`, `lista_prestamo`, `analisis_prestamos`). Se engancha en el cierre de jornada (`match_screen.finalizar_jornada_liga`), en el inicio de temporada (`resumen_temporada_screen.avanzar_nueva_temporada`) y en las pantallas NEGOCIAR / FAVORITOS / negociación / OFERTAS / PLANTILLA.

**Tech Stack:** Python 3.10, Pygame 2.6. Tests = scripts `python tests/test_x.py` (no pytest), con `SDL_VIDEODRIVER=dummy PYTHONIOENCODING=utf-8`.

**Spec:** `docs/superpowers/specs/2026-09-25-prestamos-design.md`

## Global Constraints

- Duraciones: `6` o `12` meses. 6 meses = la siguiente ventana (inicio→invierno→cierre→invierno de la temporada siguiente); 12 = la misma ventana de la temporada siguiente. Regreso = primer día de esa ventana.
- Idas y vueltas solo con el mercado abierto (`traspasos_pendientes.mercado_abierto`); si está cerrado, quedan pendientes para la próxima ventana.
- % que paga el user al pedir: de 10 en 10 (10..100). Club: mínimo 30% (suplente en su mejor once) / 60% (titular); a 20 puntos o menos del mínimo = "lo analizamos"; menos = rechaza. Sus 3 mejores no se prestan. Nunca con el clásico.
- Jugador acepta si `nivel_club(mi) >= nivel_club(club) - 6` o si sería titular en tu mejor once.
- Ofertas de préstamo de la IA: solo con mercado abierto, 30% por jugador en lista y jornada; contraoferta: dentro del tope = acepta, hasta +15 puntos = "lo analizamos" (50/50 la jornada siguiente), más = se retira.
- Sueldo: masa salarial del user = sus jugadores × % que le toca + % que paga de sus cedidos. La IA no paga sueldos.
- Sin cuota de préstamo, sin opción de compra, sin préstamos entre clubes de la IA.
- Comentarios en español; `logger` en vez de `print`; cada `except` loggea el error (skill resilient-code).
- Nunca atribuir a Claude en commits. No se commitea sin OK de Diego (la sesión no commitea: los pasos "Commit" se reemplazan por "correr la suite del task").

## Review Focus

1. Un préstamo que vuelve en J1 de la temporada siguiente (1 año desde el inicio): el cierre de jornada no corre en J1 → debe revisarse al empezar la temporada (Task 5 lo prueba).
2. Plantilla del user llena (40) al pedir a préstamo → rechazar con mensaje, no pasar de 40 (Task 2 lo prueba).
3. Club dueño o destino que ya no existe por nombre (renombrado en el editor) al volver → el jugador queda en agentes libres, sin crash (Task 1 lo prueba).
4. Contrato que vence durante la cesión → vuelve a su dueño antes del cierre de contratos (Task 4 lo prueba).
5. Oferta de traspaso por un jugador que está a préstamo (la IA la generó antes del filtro) → se purga y `vender` la rechaza (Task 4 lo prueba).

---

### Task 1: Núcleo de préstamos (datos, regreso, ida, vuelta, pendientes)

**Files:**
- Modify: `alpha_football/models.py` (campo `prestamo` en `Jugador` y en `from_dict`)
- Create: `alpha_football/prestamos.py`
- Test: `tests/test_prestamos.py`

**Interfaces:**
- Produces:
  - `Jugador.prestamo: Optional[dict]` = `{'dueno': str, 'club': str, 'pct_dueno': int, 'vuelve': [int, int], 'meses': int}`
  - `prestamos.regreso(estado, meses: int) -> list[int]` ([temporada, jornada])
  - `prestamos.iniciar(estado, jugador, dueno, destino, meses: int, pct_dueno: int) -> str`
  - `prestamos.terminar(estado, jugador) -> str`
  - `prestamos.revisar_jornada(estado, rng=None) -> None`
  - `prestamos.entrantes(estado) -> list` · `prestamos.cedidos(estado, nombre_club=None) -> list[tuple]` ((jugador, club))

- [ ] **Step 1: Test que falla** — crear `tests/test_prestamos.py`:

```python
"""Préstamos (spec 2026-09-25-prestamos-design.md)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, prestamos as P, correo as C
from alpha_football.models import Jugador

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _abierto(e, j=1):
    e['liga'].jornada_actual = j


def test_regreso_por_ventana():
    e = estado_carrera(); n = e['liga'].num_jornadas            # 22: ventanas 1-3, 11-13, 20-22
    _abierto(e, 2)
    assert P.regreso(e, 6) == [1, 11] and P.regreso(e, 12) == [2, 1]
    _abierto(e, 12)
    assert P.regreso(e, 6) == [1, n - 2] and P.regreso(e, 12) == [2, 11]
    _abierto(e, 21)
    assert P.regreso(e, 6) == [2, 11]
    _abierto(e, 8)                                              # cerrado: empieza en el invierno
    assert P.regreso(e, 6) == [1, n - 2]
    print("  test_regreso_por_ventana: OK")


def test_ida_y_vuelta_con_mercado_abierto():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[3]
    j = club.jugadores[10]
    txt = P.iniciar(e, j, club, mi, 6, 40)
    assert j in mi.jugadores and j not in club.jugadores and 'préstamo' in txt
    assert j.prestamo['dueno'] == club.nombre and j.prestamo['pct_dueno'] == 40
    assert P.entrantes(e) == [j]
    e['liga'].jornada_actual = 11                                # llega el invierno
    P.revisar_jornada(e)
    assert j in club.jugadores and j not in mi.jugadores and j.prestamo is None
    assert any('vuelve' in m['asunto'].lower() or 'volvió' in m['asunto'].lower() for m in C.bandeja(e))
    print("  test_ida_y_vuelta_con_mercado_abierto: OK")


def test_acordado_con_mercado_cerrado_espera_la_ventana():
    e = estado_carrera(); _abierto(e, 6)
    mi, club = e['mi_equipo'], e['liga'].equipos[4]
    j = club.jugadores[9]
    txt = P.iniciar(e, j, club, mi, 6, 50)
    assert j in club.jugadores and 'jornada 11' in txt
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))    # guardar / cargar
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in mi.jugadores and j.prestamo['vuelve'] == [1, e['liga'].num_jornadas - 2]
    print("  test_acordado_con_mercado_cerrado_espera_la_ventana: OK")


def test_terminar_antes():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[5]
    j = club.jugadores[8]
    P.iniciar(e, j, club, mi, 12, 50)
    e['liga'].jornada_actual = 5                                 # cerrado → vuelve en la próxima ventana
    assert 'jornada 11' in P.terminar(e, j) and j in mi.jugadores
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in club.jugadores and j.prestamo is None
    j2 = club.jugadores[7]
    P.iniciar(e, j2, club, mi, 12, 50)                           # abierto → vuelve ya
    P.terminar(e, j2)
    assert j2 in club.jugadores and j2.prestamo is None
    print("  test_terminar_antes: OK")


def test_prestamo_se_guarda_en_el_jugador():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[3]; j = club.jugadores[6]
    P.iniciar(e, j, club, e['mi_equipo'], 6, 30)
    copia = Jugador.from_dict(json.loads(json.dumps(j.to_dict())))
    assert copia.prestamo == j.prestamo
    assert Jugador.from_dict({'nombre': 'A', 'apellido': 'B'}).prestamo is None   # saves viejos
    print("  test_prestamo_se_guarda_en_el_jugador: OK")


def test_dueno_desaparecido_queda_libre():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[6]
    j = club.jugadores[5]
    P.iniciar(e, j, club, mi, 6, 50)
    j.prestamo['dueno'] = 'Club Que No Existe'
    P.terminar(e, j)
    assert j not in mi.jugadores and j in e.get('free_agents_list', []) and j.prestamo is None
    print("  test_dueno_desaparecido_queda_libre: OK")


TESTS = [test_regreso_por_ventana, test_ida_y_vuelta_con_mercado_abierto,
         test_acordado_con_mercado_cerrado_espera_la_ventana, test_terminar_antes,
         test_prestamo_se_guarda_en_el_jugador, test_dueno_desaparecido_queda_libre]


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

Run: `SDL_VIDEODRIVER=dummy PYTHONIOENCODING=utf-8 python tests/test_prestamos.py`
Expected: `ImportError: cannot import name 'prestamos'`.

- [ ] **Step 3: Campo en el modelo** — en `alpha_football/models.py`, clase `Jugador`, después de `descontento_avisado: bool = False`:

```python
    # préstamo en curso (solo mientras está cedido): dueño, club donde juega, % del sueldo que
    # paga el dueño, [temporada, jornada] de regreso y duración en meses (prestamos.py)
    prestamo: Optional[dict] = None
```

y en `from_dict`, después de `descontento_avisado=bool(datos.get("descontento_avisado", False)),`:

```python
                prestamo=dict(datos["prestamo"]) if isinstance(datos.get("prestamo"), dict) else None,
```

- [ ] **Step 4: Crear `alpha_football/prestamos.py`**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Préstamos de jugadores (spec 2026-09-25-prestamos-design.md)
Pedir a préstamo y ceder por 6 meses o 1 año con el sueldo repartido en %. El jugador juega y
progresa en el club donde está. Idas y vueltas solo con el mercado abierto: si se acuerda con el
mercado cerrado, queda en datos_carrera['prestamos_pendientes'] para la próxima ventana. Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

DURACIONES = (6, 12)
PCT_PASO = 10
PCT_MIN_SUPLENTE, PCT_MIN_TITULAR = 30, 60
MARGEN_ANALISIS_PEDIDO = 20
MARGEN_ANALISIS_CONTRA = 15
PROB_OFERTA_PRESTAMO = 0.30
PROB_ACEPTA_ANALISIS = 0.5
DIF_NIVEL_JUGADOR = 6


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _pendientes(estado: dict) -> list:
    return _dc(estado).setdefault('prestamos_pendientes', [])


def _nombre(j) -> str:
    return getattr(j, 'nombre_completo', None) or f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _momento(estado: dict) -> tuple:
    liga = estado.get('liga')
    return (int(estado.get('temporada', 1) or 1), int(getattr(liga, 'jornada_actual', 1) or 1),
            int(getattr(liga, 'num_jornadas', 22) or 22))


def _abierto(estado: dict) -> bool:
    from alpha_football.traspasos_pendientes import mercado_abierto
    return mercado_abierto(estado)


def _equipos(estado: dict) -> list:
    from alpha_football.traspasos_pendientes import _equipos as equipos
    return equipos(estado)


def _club(estado: dict, nombre: Optional[str]):
    from alpha_football.traspasos_pendientes import _club as club
    return club(estado, nombre)


def _mi(estado: dict):
    return estado.get('mi_equipo')


def regreso(estado: dict, meses: int) -> list:
    """[temporada, jornada] del regreso: primer día de la ventana que corresponde a la duración."""
    from alpha_football.market import ventanas_mercado
    t, j, n = _momento(estado)
    vs = ventanas_mercado(n)
    if _abierto(estado):
        k = next(i for i, v in enumerate(vs) if v[0] <= j <= v[1])
    else:
        k = next((i for i, v in enumerate(vs) if v[0] > j), None)
        if k is None:
            k, t = 0, t + 1
    if int(meses) >= 12:
        return [t + 1, vs[k][0]]
    k += 1
    if k >= len(vs):
        k, t = 0, t + 1
    return [t, vs[k][0]]


def entrantes(estado: dict) -> list:
    """Jugadores que el user tiene a préstamo (están en su plantilla)."""
    return [j for j in getattr(_mi(estado), 'jugadores', []) or [] if getattr(j, 'prestamo', None)]


def cedidos(estado: dict, nombre_club: Optional[str] = None) -> list:
    """(jugador, club donde juega) de los que `nombre_club` (por defecto el del user) tiene cedidos."""
    dueno = nombre_club or getattr(_mi(estado), 'nombre', None)
    return [(j, eq) for eq in _equipos(estado) for j in eq.jugadores
            if (getattr(j, 'prestamo', None) or {}).get('dueno') == dueno]


def _correo(estado: dict, asunto: str, cuerpo: str, pantalla: str = 'plantilla_screen') -> None:
    try:
        from alpha_football import correo as C
        C.enviar(estado, 'club', asunto, cuerpo, C.accion(pantalla, "VER PLANTILLA"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo del préstamo: {e}")


def _afecta_al_user(estado: dict, *clubes) -> bool:
    mi = getattr(_mi(estado), 'nombre', None)
    return mi is not None and mi in clubes


def _texto_regreso(vuelve: list) -> str:
    return f"la jornada {vuelve[1]} de la temporada {vuelve[0]}"


def _mover_ida(estado: dict, jugador, dueno, destino, reg: dict) -> None:
    from alpha_football.finanzas import quitar_de_plantilla, completar_plantilla
    quitar_de_plantilla(dueno, jugador)
    destino.jugadores.append(jugador)
    if destino is not _mi(estado):
        destino.alineacion_activa = None
    jugador.prestamo = {k: reg[k] for k in ('dueno', 'club', 'pct_dueno', 'vuelve', 'meses')}
    jugador.transferible = False
    lista = _dc(estado).get('lista_prestamo') or []
    if jugador.nombre_completo in lista:
        lista.remove(jugador.nombre_completo)
    if dueno is _mi(estado):
        completar_plantilla(dueno)
    if _afecta_al_user(estado, dueno.nombre, destino.nombre):
        llega = destino is _mi(estado)
        _correo(estado, f"{_nombre(jugador)} {'llegó a préstamo' if llega else 'se fue cedido'}",
                f"{_nombre(jugador)} juega en {destino.nombre} a préstamo hasta {_texto_regreso(reg['vuelve'])}. "
                f"El dueño ({dueno.nombre}) paga el {reg['pct_dueno']}% del sueldo.")


def _mover_vuelta(estado: dict, jugador, motivo: str = "terminó el préstamo") -> None:
    """Devuelve al jugador a su dueño (o a agentes libres si el dueño ya no existe)."""
    from alpha_football.finanzas import quitar_de_plantilla, completar_plantilla
    p = dict(jugador.prestamo or {})
    club = next((eq for eq in _equipos(estado) if jugador in eq.jugadores), None)
    dueno = _club(estado, p.get('dueno'))
    if club is not None:
        quitar_de_plantilla(club, jugador)
        if club is _mi(estado):
            completar_plantilla(club)
    jugador.prestamo = None
    if dueno is not None:
        dueno.jugadores.append(jugador)
        if dueno is not _mi(estado):
            dueno.alineacion_activa = None
    else:
        logger.warning(f"El dueño de {_nombre(jugador)} ({p.get('dueno')}) no existe: queda libre")
        jugador.fin_de_contrato = True
        estado.setdefault('free_agents_list', []).append(jugador)
    if _afecta_al_user(estado, p.get('dueno'), p.get('club')):
        _correo(estado, f"{_nombre(jugador)} vuelve a {p.get('dueno', 'su club')}",
                f"{motivo.capitalize()}: {_nombre(jugador)} dejó {p.get('club', 'el club')} y volvió a {p.get('dueno', 'su club')}.")


def iniciar(estado: dict, jugador, dueno, destino, meses: int, pct_dueno: int) -> str:
    """Préstamo acordado. Con el mercado abierto se mueve ya; si no, espera la ventana. Texto para el correo/UI."""
    from alpha_football.traspasos_pendientes import jornada_apertura
    reg = {'jugador': _nombre(jugador), 'jugador_id': getattr(jugador, 'id', None),
           'dueno': dueno.nombre, 'club': destino.nombre, 'pct_dueno': int(pct_dueno),
           'vuelve': regreso(estado, meses), 'meses': int(meses)}
    if _abierto(estado):
        _mover_ida(estado, jugador, dueno, destino, reg)
        return f"{_nombre(jugador)} juega en {destino.nombre} a préstamo hasta {_texto_regreso(reg['vuelve'])}."
    _pendientes(estado).append(dict(reg, tipo='inicio'))
    texto = (f"{_nombre(jugador)} se irá a {destino.nombre} a préstamo en la jornada {jornada_apertura(estado)}, "
             "en cuanto se abra el mercado.")
    if _afecta_al_user(estado, dueno.nombre, destino.nombre):
        _correo(estado, f"Préstamo acordado: {_nombre(jugador)}", texto)
    return texto


def pendiente_de(estado: dict, jugador) -> Optional[dict]:
    return next((p for p in _pendientes(estado) if p.get('jugador') == _nombre(jugador)), None)


def terminar(estado: dict, jugador) -> str:
    """CONCLUIR PRÉSTAMO: vuelve ya con el mercado abierto; si no, en la próxima ventana."""
    from alpha_football.traspasos_pendientes import jornada_apertura
    if not getattr(jugador, 'prestamo', None):
        return "Ese jugador no está a préstamo."
    if _abierto(estado):
        _mover_vuelta(estado, jugador, "se concluyó el préstamo")
        return f"{_nombre(jugador)} volvió a su club."
    if not any(p.get('tipo') == 'fin' and p.get('jugador') == _nombre(jugador) for p in _pendientes(estado)):
        _pendientes(estado).append({'tipo': 'fin', 'jugador': _nombre(jugador)})
    return f"{_nombre(jugador)} vuelve a su club en la jornada {jornada_apertura(estado)}, cuando se abra el mercado."


def _ejecutar_pendientes(estado: dict) -> None:
    for p in list(_pendientes(estado)):
        _pendientes(estado).remove(p)
        try:
            nombre = p.get('jugador')
            if p.get('tipo') == 'fin':
                j = next((x for eq in _equipos(estado) for x in eq.jugadores
                          if _nombre(x) == nombre and getattr(x, 'prestamo', None)), None)
                if j is not None:
                    _mover_vuelta(estado, j, "se concluyó el préstamo")
                continue
            dueno, destino = _club(estado, p.get('dueno')), _club(estado, p.get('club'))
            j = next((x for x in getattr(dueno, 'jugadores', []) or [] if _nombre(x) == nombre), None)
            if dueno is None or destino is None or j is None:
                if _afecta_al_user(estado, p.get('dueno'), p.get('club')):
                    _correo(estado, f"Se cayó el préstamo de {nombre}",
                            f"{nombre} ya no está disponible: el préstamo quedó sin efecto.")
                continue
            _mover_ida(estado, j, dueno, destino, p)
        except Exception as e:
            logger.error(f"No se pudo concretar el préstamo pendiente de {p.get('jugador')}: {e}", exc_info=True)


def _vencidos(estado: dict) -> None:
    t, jor, _n = _momento(estado)
    for eq in _equipos(estado):
        for j in list(eq.jugadores):
            p = getattr(j, 'prestamo', None)
            if p and [t, jor] >= list(p.get('vuelve') or [0, 0]):
                _mover_vuelta(estado, j)


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada (y J1 de cada temporada): con mercado abierto concreta pendientes y regresos."""
    try:
        if _abierto(estado):
            _ejecutar_pendientes(estado)
            _vencidos(estado)
    except Exception as e:
        logger.error(f"Error revisando los préstamos: {e}", exc_info=True)
```

- [ ] **Step 5: Correr los tests del task**

Run: `SDL_VIDEODRIVER=dummy PYTHONIOENCODING=utf-8 python tests/test_prestamos.py`
Expected: `6/6 tests pasaron`.

- [ ] **Step 6: Regresión** — `python tests/test_favoritos.py` y `python tests/test_revision_v291.py` (mismo entorno): todo pasa.

---

### Task 2: Pedir a préstamo (club, jugador, análisis) + UI de negociación

**Files:**
- Modify: `alpha_football/prestamos.py` (evaluar pedido, jugador, cerrar, análisis)
- Modify: `alpha_football/negociacion.py` (`iniciar_negociacion` modo `'prestamo'`)
- Modify: `alpha_football/ui/negociacion_screen.py` (modo `'prestamo'`)
- Modify: `alpha_football/ui/buscador_screen.py` y `alpha_football/ui/favoritos_screen.py` (botón PEDIR PRÉSTAMO)
- Test: `tests/test_prestamos.py`

**Interfaces:**
- Consumes: `iniciar`, `regreso` (Task 1).
- Produces:
  - `prestamos.evaluar_pedido(estado, jugador, club, meses, pct_user) -> tuple[str, str]` ('acepta'|'analiza'|'rechaza', mensaje)
  - `prestamos.acepta_jugador(estado, jugador, club) -> tuple[bool, str]`
  - `prestamos.cerrar_pedido(estado, jugador, club, meses, pct_user) -> tuple[bool, str]`
  - `prestamos.resolver_analisis(estado, azar) -> None`
  - neg dict en modo préstamo: `{'modo': 'prestamo', 'meses': 6, 'pct': 50, ...}`
  - `buscador_screen._rects()['prestamo']` (mitad derecha de la fila de FICHAR)

- [ ] **Step 1: Tests que fallan** — agregar a `tests/test_prestamos.py` (y a `TESTS`):

```python
def test_pedido_reglas_del_club():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[2]
    top = sorted(club.jugadores, key=lambda x: -x.overall)[0]
    assert P.evaluar_pedido(e, top, club, 6, 100)[0] == 'rechaza'           # pieza clave
    from alpha_football.formaciones import mejor_once
    tit = {club.jugadores[i].nombre_completo for i in mejor_once(club.jugadores, "4-3-3")}
    top3 = {x.nombre_completo for x in sorted(club.jugadores, key=lambda x: -x.overall)[:3]}
    sup = next(x for x in club.jugadores if x.nombre_completo not in tit | top3)
    assert P.evaluar_pedido(e, sup, club, 6, 30)[0] == 'acepta'
    assert P.evaluar_pedido(e, sup, club, 6, 10)[0] == 'analiza'
    assert e['datos_carrera']['analisis_prestamos'][-1]['jugador'] == sup.nombre_completo
    titular = next(x for x in club.jugadores if x.nombre_completo in tit and x.nombre_completo not in top3)
    assert P.evaluar_pedido(e, titular, club, 6, 30)[0] == 'rechaza'
    assert P.evaluar_pedido(e, titular, club, 6, 60)[0] == 'acepta'
    print("  test_pedido_reglas_del_club: OK")


def test_analisis_se_resuelve_la_jornada_siguiente():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[2]
    from alpha_football.formaciones import mejor_once
    tit = {club.jugadores[i].nombre_completo for i in mejor_once(club.jugadores, "4-3-3")}
    top3 = {x.nombre_completo for x in sorted(club.jugadores, key=lambda x: -x.overall)[:3]}
    sup = next(x for x in club.jugadores if x.nombre_completo not in tit | top3)   # suplente: mínimo 30%
    assert P.evaluar_pedido(e, sup, club, 6, 10)[0] == 'analiza'
    class Si: random = staticmethod(lambda: 0.0)
    P.resolver_analisis(e, Si())                                # misma jornada: nada
    assert sup in club.jugadores
    e['liga'].jornada_actual = 2
    P.resolver_analisis(e, Si())
    assert sup in e['mi_equipo'].jugadores and sup.prestamo['pct_dueno'] == 90
    print("  test_analisis_se_resuelve_la_jornada_siguiente: OK")


def test_plantilla_llena_no_pide():
    e = estado_carrera(); _abierto(e, 1)
    from alpha_football.market import PLANTILLA_MAXIMA
    mi, club = e['mi_equipo'], e['liga'].equipos[2]
    while len(mi.jugadores) < PLANTILLA_MAXIMA:
        mi.jugadores.append(Jugador(nombre='Relleno', apellido=str(len(mi.jugadores)), posicion='MED',
                                    ataque=50, defensa=50, fisico=50, tecnica=50, mental=50))
    ok, msg = P.cerrar_pedido(e, sorted(club.jugadores, key=lambda x: x.overall)[0], club, 6, 100)
    assert not ok and 'Plantilla llena' in msg and len(mi.jugadores) == PLANTILLA_MAXIMA
    print("  test_plantilla_llena_no_pide: OK")


def test_ui_pedir_prestamo_desde_el_buscador():
    from alpha_football.ui import buscador_screen as B, negociacion_screen as NS
    e = estado_carrera(); _abierto(e, 1)
    pygame.event.clear(); B.render(screen, e)
    k, (j, club, _et) = next((i, x) for i, x in enumerate(e['busq_resultados']) if x[1] is not None)
    e['busq']['sel'] = k
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=B._rects()['prestamo'].center))
    assert B.render(screen, e) == 'negociacion_screen'
    neg = e['neg']
    assert neg['modo'] == 'prestamo' and neg['etapa'] == 'club' and neg['meses'] == 6 and neg['pct'] == 50
    pygame.event.clear(); assert NS.render(screen, e) is None
    print("  test_ui_pedir_prestamo_desde_el_buscador: OK")
```

- [ ] **Step 2: Correr y ver que fallan** (`AttributeError: evaluar_pedido`).

- [ ] **Step 3: Implementar en `prestamos.py`** (al final del archivo):

```python
# --- Pedir a préstamo ──────────────────────────────────────────────────────────

def _titular_en(equipo, jugador) -> bool:
    from alpha_football.formaciones import mejor_once
    js = list(getattr(equipo, 'jugadores', []) or [])
    return any(js[i] is jugador for i in mejor_once(js, "4-3-3"))


def evaluar_pedido(estado: dict, jugador, club, meses: int, pct_user: int) -> tuple:
    """('acepta'|'analiza'|'rechaza', mensaje) del club dueño ante tu pedido de préstamo."""
    mi = _mi(estado)
    pct_user = max(0, min(100, int(pct_user)))
    if jugador in sorted(club.jugadores, key=lambda x: -x.overall)[:3]:
        return 'rechaza', f"{club.nombre}: {_nombre(jugador)} es pieza clave, no se presta."
    try:
        from alpha_football.data.clasicos import es_clasico
        if mi is not None and es_clasico(club, mi):
            return 'rechaza', f"{club.nombre} no le presta jugadores a su clásico."
    except Exception as e:
        logger.error(f"No se pudo revisar el clásico en el préstamo: {e}")
    minimo = PCT_MIN_TITULAR if _titular_en(club, jugador) else PCT_MIN_SUPLENTE
    if pct_user >= minimo:
        return 'acepta', f"{club.nombre} acepta: pagas el {pct_user}% del sueldo."
    if pct_user >= minimo - MARGEN_ANALISIS_PEDIDO:
        t, jor, _n = _momento(estado)
        pend = [a for a in _dc(estado).get('analisis_prestamos', []) if a.get('jugador') != _nombre(jugador)]
        pend.append({'jugador': _nombre(jugador), 'club': club.nombre, 'meses': int(meses), 'pct': pct_user,
                     'jornada': jor, 'temporada': t})
        _dc(estado)['analisis_prestamos'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    return 'rechaza', f"{club.nombre} rechaza: quiere que pagues al menos el {minimo}% del sueldo."


def acepta_jugador(estado: dict, jugador, club) -> tuple:
    """El jugador acepta si tu club no es mucho peor que el suyo o si va a ser titular contigo."""
    from alpha_football.market import nivel_club
    mi = _mi(estado)
    if nivel_club(mi) >= nivel_club(club) - DIF_NIVEL_JUGADOR:
        return True, f"{_nombre(jugador)} acepta ir a préstamo."
    rivales = [x for x in mi.jugadores if x.posicion == jugador.posicion]
    peor_titular = min((x.overall for x in rivales if _titular_en(mi, x)), default=0)
    if jugador.overall > peor_titular:
        return True, f"{_nombre(jugador)} acepta: sabe que va a jugar."
    return False, f"{_nombre(jugador)} no quiere ir: cree que no va a tener minutos."


def cerrar_pedido(estado: dict, jugador, club, meses: int, pct_user: int) -> tuple:
    """Acuerdo con club y jugador: arranca el préstamo (ya o en la próxima ventana)."""
    from alpha_football.market import PLANTILLA_MAXIMA
    mi = _mi(estado)
    if len(mi.jugadores) >= PLANTILLA_MAXIMA:
        return False, f"Plantilla llena ({PLANTILLA_MAXIMA}): libera un lugar antes de pedir a préstamo."
    if pendiente_de(estado, jugador) is not None or getattr(jugador, 'prestamo', None):
        return False, f"{_nombre(jugador)} ya tiene un préstamo acordado."
    return True, iniciar(estado, jugador, club, mi, meses, 100 - int(pct_user))


def resolver_analisis(estado: dict, azar) -> None:
    """Respuesta (50/50) a los pedidos en análisis de jornadas anteriores; si el club acepta y el
    jugador también, el préstamo arranca solo."""
    t, jor, _n = _momento(estado)
    pend = _dc(estado).setdefault('analisis_prestamos', [])
    for a in list(pend):
        if int(a.get('temporada', t)) == t and jor <= int(a.get('jornada', 0)):
            continue
        pend.remove(a)
        club = _club(estado, a.get('club'))
        j = next((x for x in getattr(club, 'jugadores', []) or [] if _nombre(x) == a.get('jugador')), None)
        if club is None or j is None:
            _correo(estado, f"Préstamo sin efecto: {a.get('jugador')}", "El jugador ya no está en ese club.")
            continue
        if azar.random() >= PROB_ACEPTA_ANALISIS:
            _correo(estado, f"{club.nombre} no presta a {a['jugador']}",
                    f"No acepta que pagues el {a['pct']}% del sueldo.")
            continue
        ok_j, msg_j = acepta_jugador(estado, j, club)
        if not ok_j:
            _correo(estado, f"{a['jugador']} no acepta el préstamo", msg_j)
            continue
        ok, msg = cerrar_pedido(estado, j, club, a['meses'], a['pct'])
        _correo(estado, f"{club.nombre} acepta prestarte a {a['jugador']}", msg)
```

- [ ] **Step 4: `negociacion.iniciar_negociacion`** — reemplazar la línea `'etapa': 'club' if modo == 'fichaje' and club is not None else 'jugador',` por:

```python
        'etapa': 'club' if modo in ('fichaje', 'prestamo') and club is not None else 'jugador',
```

y justo antes de `return 'negociacion_screen'`:

```python
    if modo == 'prestamo':
        estado['neg'].update({'meses': 6, 'pct': 50})    # duración y % del sueldo que pagas tú
```

- [ ] **Step 5: `negociacion_screen.py` modo préstamo.** En `render`, dentro del bucle de eventos, primero en la rama `if neg['etapa'] == 'club':` agregar al inicio del bloque:

```python
                if modo == 'prestamo':
                    from alpha_football import prestamos as PR
                    if rects['monto_menos'].collidepoint(p):
                        neg['pct'] = max(PR.PCT_PASO, neg['pct'] - PR.PCT_PASO)
                    elif rects['monto_mas'].collidepoint(p):
                        neg['pct'] = min(100, neg['pct'] + PR.PCT_PASO)
                    elif rects['clausula'].collidepoint(p):
                        neg['meses'] = 12 if neg['meses'] == 6 else 6
                    elif rects['ofertar'].collidepoint(p):
                        resp, msg = PR.evaluar_pedido(estado, j, club, neg['meses'], neg['pct'])
                        neg['msg'] = (msg, {'acepta': 'verde', 'analiza': 'azul'}.get(resp, 'rojo'))
                        if resp == 'acepta':
                            neg['etapa'] = 'jugador'
                        elif resp == 'analiza':
                            neg['etapa'], neg['acuerdo_club'] = 'hecho', False
                    continue
```

En la rama de teclado `if ev.type == pygame.KEYDOWN and neg['etapa'] == 'club':` cambiar la condición por `... and neg['etapa'] == 'club' and modo != 'prestamo':` (el % no se teclea).

En la rama `elif neg['etapa'] == 'jugador':` agregar al inicio:

```python
                if modo == 'prestamo':
                    if rects['proponer'].collidepoint(p):
                        from alpha_football import prestamos as PR
                        ok_j, msg_j = PR.acepta_jugador(estado, j, club)
                        if not ok_j:
                            neg['msg'], neg['etapa'], neg['acuerdo_jugador'] = (msg_j, 'rojo'), 'hecho', False
                            continue
                        ok, msg = PR.cerrar_pedido(estado, j, club, neg['meses'], neg['pct'])
                        neg['msg'] = (msg, 'verde' if ok else 'rojo')
                        neg['etapa'] = 'hecho'
                        estado.pop('busq_resultados', None)
                    continue
```

En el dibujo: `titulo = "RENOVACIÓN" if modo == 'renovar' else "NEGOCIACIÓN"` → `titulo = {"renovar": "RENOVACIÓN", "prestamo": "PRÉSTAMO"}.get(modo, "NEGOCIACIÓN")`. En el panel del club (rama `else:` con `activo = neg['etapa'] == 'club'`), si `modo == 'prestamo'` dibujar en lugar del contenido de fichaje:

```python
            if modo == 'prestamo':
                draw_text(screen, f"1. PRÉSTAMO DE {club.nombre.upper()}"[:44], (cx, cy), size='md',
                          color='dorado' if activo else 'verde')
                draw_text(screen, f"Sueldo {_m(j.salario)}/año  ·  Tú pagas {neg['pct']}% = {_m(j.salario * neg['pct'] // 100)}",
                          (cx, cy + 40), size='sm', color='blanco')
                draw_text(screen, "% del sueldo que pagas tú:" + ("  (− / +)" if activo else ""), (cx, cy + 72),
                          size='sm', color='azul')
                _caja(screen, rects['monto'], f"{neg['pct']}%", 'verde' if activo else 'blanco')
                if activo:
                    for k, t in (('monto_menos', '−'), ('monto_mas', '+')):
                        draw_button(screen, rects[k], t, rects[k].collidepoint(mouse_pos))
                    draw_button(screen, rects['ofertar'], "PEDIR", rects['ofertar'].collidepoint(mouse_pos))
                    draw_button(screen, rects['clausula'], f"DURACIÓN: {'6 MESES' if neg['meses'] == 6 else '1 AÑO'} (cambiar)",
                                rects['clausula'].collidepoint(mouse_pos))
                elif neg['etapa'] == 'hecho' and not neg.get('acuerdo_club', True):
                    draw_text(screen, "El club lo analiza: respuesta por correo", (cx + 400, R_CLUB.y + 124), size='sm', color='azul')
                else:
                    draw_text(screen, "Acuerdo cerrado con el club", (cx + 400, R_CLUB.y + 120), size='md', color='verde')
            else:
                # (contenido actual de fichaje, sin cambios, indentado un nivel)
```

En el panel del jugador, si `modo == 'prestamo'` y ya hay acuerdo con el club, en lugar de salario/años/cláusula dibujar:

```python
            if modo == 'prestamo':
                draw_text(screen, f"Mismo contrato. Duración {'6 meses' if neg['meses'] == 6 else '1 año'}; "
                                  f"pagas el {neg['pct']}% del sueldo.", (jx, jy + 44), size='sm', color='blanco')
                if activo:
                    draw_button(screen, rects['proponer'], "PROPONER PRÉSTAMO", rects['proponer'].collidepoint(mouse_pos))
```

y `_orden_foco` para `'jugador'` en préstamo usa solo `['proponer', 'volver']`: cambiar la firma a `_orden_foco(etapa: str, modo: str = '')` y devolver `['proponer', 'volver']` cuando `modo == 'prestamo' and etapa == 'jugador'`; actualizar las 2 llamadas a `_orden_foco(neg['etapa'], modo)`.

- [ ] **Step 6: Botón PEDIR PRÉSTAMO.** En `buscador_screen._rects()` reemplazar `'fichar'` por dos mitades:

```python
        'fichar': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 64, (R_FICHA.width - 50) // 2, 48),
        'prestamo': pygame.Rect(R_FICHA.x + 30 + (R_FICHA.width - 50) // 2, R_FICHA.bottom - 64,
                                (R_FICHA.width - 50) // 2, 48),
```

En `_dibujar_ficha`, después de dibujar FICHAR:

```python
    rp = _rects()['prestamo']
    draw_button(screen, rp, "PRÉSTAMO" if club is not None else "—", rp.collidepoint(mouse_pos))
```

En `render`, antes de `elif rects['fichar'].collidepoint(click_pos) and res:` agregar:

```python
            elif rects['prestamo'].collidepoint(click_pos) and res:
                j, club, _et = res[b['sel']]
                if club is None:
                    _mensaje(estado, "Un agente libre no se pide a préstamo: fíchalo.", 'rojo')
                else:
                    return N.iniciar_negociacion(estado, j, club, 'prestamo', 'buscador_screen')
```

En `favoritos_screen.render`, antes de `elif res and rects['favorito'].collidepoint(click_pos):` agregar el mismo bloque con `'favoritos_screen'` como volver, y en el dibujo, después de `NEGOCIAR FICHAJE`, dibujar `rects['prestamo']` con "PRÉSTAMO". El botón de fichar en favoritos pasa a decir "FICHAR" (entra en la mitad).

- [ ] **Step 7: Correr** `python tests/test_prestamos.py` (10/10), `python tests/test_negociaciones_v270.py`, `python tests/test_favoritos.py`, `python tests/test_teclado_v420.py`: todo pasa. Captura headless de `negociacion_screen` en modo préstamo (etapa club y jugador) revisada a ojo: nada se pisa.

---

### Task 3: Ceder (lista de préstamo, ofertas de la IA, aceptar, contraoferta) + OFERTAS

**Files:**
- Modify: `alpha_football/prestamos.py` (lista, ofertas, aceptar, contraofertar, resolver contras)
- Modify: `alpha_football/ui/ofertas_screen.py`
- Test: `tests/test_prestamos.py`

**Interfaces:**
- Consumes: `iniciar` (Task 1), `resolver_analisis` (Task 2).
- Produces:
  - `prestamos.en_lista(estado, j) -> bool` · `prestamos.alternar_lista(estado, j) -> bool`
  - `prestamos.generar_ofertas(estado, azar) -> list` (dicts en `ofertas_recibidas` con `'prestamo': {'meses', 'pct_ellos'}`)
  - `prestamos.aceptar_oferta(estado, of) -> str`
  - `prestamos.contraofertar(estado, of, pct_pedido) -> tuple[str, str]` ('aceptada'|'analizando'|'rechazada'|'invalida')

- [ ] **Step 1: Tests que fallan** (agregar a `TESTS`):

```python
def test_lista_y_ofertas_de_prestamo():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    assert P.alternar_lista(e, j) and P.en_lista(e, j)
    siempre = random.Random(3); siempre.random = lambda: 0.0      # siempre hay oferta
    nuevas = P.generar_ofertas(e, siempre)
    assert len(nuevas) == 1 and nuevas[0]['prestamo']['meses'] in (6, 12) and nuevas[0] in e['ofertas_recibidas']
    assert P.generar_ofertas(e, siempre) == []                   # no repite mientras haya una pendiente
    of = nuevas[0]
    P.aceptar_oferta(e, of)
    assert j not in mi.jugadores and j in of['comprador'].jugadores
    assert j.prestamo['dueno'] == mi.nombre and j.prestamo['pct_dueno'] == 100 - of['prestamo']['pct_ellos']
    assert not P.en_lista(e, j) and of not in e['ofertas_recibidas']
    e['liga'].jornada_actual = 5
    assert P.generar_ofertas(e, siempre) == []                   # mercado cerrado: sin ofertas
    print("  test_lista_y_ofertas_de_prestamo: OK")


def test_contraoferta_de_prestamo():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[1]
    comp = e['liga'].equipos[7]
    of = {'jugador': j, 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 40}, 'tope_pct': 60}
    e['ofertas_recibidas'] = [of]
    assert P.contraofertar(e, of, 30)[0] == 'invalida'
    assert P.contraofertar(e, of, 70)[0] == 'analizando' and of['contra']['estado'] == 'analizando'
    class Si: random = staticmethod(lambda: 0.0)
    e['liga'].jornada_actual = 2
    P.resolver_analisis(e, Si())
    assert j in comp.jugadores and j.prestamo['pct_dueno'] == 30
    of2 = {'jugador': mi.jugadores[3], 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 12, 'pct_ellos': 50}, 'tope_pct': 50}
    e['ofertas_recibidas'] = [of2]
    assert P.contraofertar(e, of2, 90)[0] == 'rechazada' and of2 not in e['ofertas_recibidas']
    print("  test_contraoferta_de_prestamo: OK")


def test_ofertas_screen_prestamo():
    from alpha_football.ui import ofertas_screen as OS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[2]
    comp = e['liga'].equipos[8]
    e['ofertas_recibidas'] = [{'jugador': j, 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 60}}]
    pygame.event.clear(); OS.render(screen, e)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a'))
    OS.render(screen, e)
    assert j in comp.jugadores and j.prestamo['pct_dueno'] == 40
    print("  test_ofertas_screen_prestamo: OK")
```

- [ ] **Step 2: Correr y ver que fallan.**

- [ ] **Step 3: Implementar en `prestamos.py`:**

```python
# --- Ceder: lista de préstamo y ofertas de la IA ──────────────────────────────

def _lista(estado: dict) -> list:
    return _dc(estado).setdefault('lista_prestamo', [])


def en_lista(estado: dict, j) -> bool:
    return _nombre(j) in _lista(estado)


def alternar_lista(estado: dict, j) -> bool:
    """Agrega/quita de la lista de préstamo. Uno que ya está a préstamo no se puede listar."""
    if getattr(j, 'prestamo', None):
        return False
    if en_lista(estado, j):
        _lista(estado).remove(_nombre(j))
        return False
    _lista(estado).append(_nombre(j))
    return True


def generar_ofertas(estado: dict, azar) -> list:
    """Con el mercado abierto, cada jugador en lista sin oferta de préstamo pendiente recibe una (30%)."""
    if not _abierto(estado):
        return []
    mi = _mi(estado)
    pendientes = estado.setdefault('ofertas_recibidas', [])
    clubes = [eq for eq in _equipos(estado) if eq is not mi and getattr(eq, 'nombre', None) != mi.nombre]
    nuevas = []
    for j in list(getattr(mi, 'jugadores', []) or []):
        if not en_lista(estado, j) or any(o.get('jugador') is j and o.get('prestamo') for o in pendientes):
            continue
        if azar.random() >= PROB_OFERTA_PRESTAMO or not clubes:
            continue
        comp = azar.choice(clubes)
        of = {'jugador': j, 'comprador': comp, 'monto': 0,
              'prestamo': {'meses': azar.choice(DURACIONES), 'pct_ellos': azar.randint(4, 10) * PCT_PASO}}
        pendientes.append(of)
        nuevas.append(of)
        _correo(estado, f"Oferta de préstamo por {_nombre(j)}",
                f"{comp.nombre} lo quiere a préstamo por {of['prestamo']['meses']} meses y paga el "
                f"{of['prestamo']['pct_ellos']}% del sueldo.", 'ofertas_screen')
    return nuevas


def aceptar_oferta(estado: dict, of: dict) -> str:
    j, comp = of['jugador'], of['comprador']
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o.get('jugador') is not j]
    return iniciar(estado, j, _mi(estado), comp, of['prestamo']['meses'], 100 - int(of['prestamo']['pct_ellos']))


def contraofertar(estado: dict, of: dict, pct_pedido: int) -> tuple:
    """Pedir que paguen más %: dentro del tope acepta, hasta +15 puntos lo analiza, más se retira."""
    pct_pedido = int(pct_pedido)
    base = int(of['prestamo']['pct_ellos'])
    comp = getattr(of.get('comprador'), 'nombre', 'El club')
    if of.get('contra'):
        return 'invalida', "Ya contraofertaste por esta oferta."
    if pct_pedido <= base or pct_pedido > 100:
        return 'invalida', f"Pide más del {base}% (hasta 100%)."
    tope = int(of.setdefault('tope_pct', min(100, base + random.randint(0, 2) * PCT_PASO)))
    if pct_pedido <= tope:
        of['prestamo']['pct_ellos'] = pct_pedido
        return 'aceptada', f"{comp} acepta pagar el {pct_pedido}%. " + aceptar_oferta(estado, of)
    if pct_pedido <= tope + MARGEN_ANALISIS_CONTRA:
        _t, jor, _n = _momento(estado)
        of['contra'] = {'pedido': pct_pedido, 'estado': 'analizando', 'jornada': jor}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o is not of]
    return 'rechazada', f"{comp} considera excesivo el {pct_pedido}% y retira la oferta."


def _resolver_contras(estado: dict, azar) -> None:
    _t, jor, _n = _momento(estado)
    for of in list(estado.get('ofertas_recibidas') or []):
        c = of.get('contra') or {}
        if not of.get('prestamo') or c.get('estado') != 'analizando' or jor <= int(c.get('jornada', 0)):
            continue
        comp = getattr(of.get('comprador'), 'nombre', 'El club')
        if azar.random() < PROB_ACEPTA_ANALISIS and of['jugador'] in getattr(_mi(estado), 'jugadores', []):
            of['prestamo']['pct_ellos'] = int(c['pedido'])
            _correo(estado, f"{comp} acepta tu contraoferta de préstamo", aceptar_oferta(estado, of))
        else:
            estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o is not of]
            _correo(estado, f"{comp} se retira", f"No pagará el {c['pedido']}% por {_nombre(of['jugador'])}.")
```

y en `resolver_analisis` (Task 2), al final de la función, agregar `_resolver_contras(estado, azar)`.

- [ ] **Step 4: `ofertas_screen.py`** —
  - `_aceptar`: si `of.get('prestamo')`: `from alpha_football import prestamos as PR; PR.aceptar_oferta(estado, of); return True`.
  - `_aceptar_sel`: mensaje para préstamo: `f"{jug.nombre_completo} se va cedido a {comp.nombre}."`.
  - `_abrir_contra`: si préstamo, `estado['contra_monto'] = min(100, of['prestamo']['pct_ellos'] + 10)`.
  - `_enviar_contra`: si préstamo, `resultado, msg = PR.contraofertar(estado, of, int(estado.get('contra_monto', 0) or 0))`.
  - Clic en `R_MAS5/R_MAS10/R_MAS25` con préstamo suma 10/20/30 puntos (tope 100) en vez del %.
  - Teclado en el panel: con préstamo, `←`/`→` restan/suman 10 (no se usa `editar_valor`).
  - `_dibujar_tarjeta`: si préstamo, la línea de oferta es `f"{comp.nombre[:20]} · PRÉSTAMO {m} meses · paga {pct}%"` (m = meses).
  - `_dibujar_panel_contra`: si préstamo, título `f"CONTRAOFERTA DE PRÉSTAMO (pagan {pct}%)"`, caja `f"{estado['contra_monto']}%"`, botones "+10" "+20" "+30", texto "← → ajusta".

- [ ] **Step 5: Correr** `python tests/test_prestamos.py` (13/13), `python tests/test_mercado_v350.py`, `python tests/test_invierno_hitos.py`: todo pasa. Captura headless de OFERTAS con una oferta de préstamo y su panel de contraoferta revisada.

---

### Task 4: Sueldo repartido y protecciones

**Files:**
- Modify: `alpha_football/finanzas.py` (`masa_salarial`, `procesar_jornada`, `cierre_temporada`, `vender_mejor`)
- Modify: `alpha_football/prestamos.py` (`limpiar_ofertas`, `cierre_contratos`)
- Modify: `alpha_football/mercado_ia.py` (ronda IA, `_liberar_sobrantes`, `pago_clausulas`)
- Modify: `alpha_football/contraofertas.py` (`vender`), `alpha_football/salidas.py` (`marcar_salida_forzada`), `alpha_football/retiros.py` (correo)
- Modify: `alpha_football/ui/plantilla_screen.py` (`alternar_transferible`, renovar)
- Test: `tests/test_prestamos.py`

**Interfaces:**
- Consumes: `entrantes`, `cedidos`, `_mover_vuelta` (Task 1).
- Produces: `finanzas.masa_salarial(equipo, estado=None) -> int`; `prestamos.limpiar_ofertas(estado)`; `prestamos.cierre_contratos(estado)`.

- [ ] **Step 1: Tests que fallan:**

```python
def test_sueldo_repartido():
    from alpha_football import finanzas as F
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    antes = F.masa_salarial(mi, e)
    club = e['liga'].equipos[3]; entra = club.jugadores[10]
    P.iniciar(e, entra, club, mi, 6, 70)                       # tú pagas el 30%
    assert F.masa_salarial(mi, e) == antes + entra.salario * 30 // 100
    sale = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    antes = F.masa_salarial(mi, e)
    P.iniciar(e, sale, mi, e['liga'].equipos[4], 6, 40)         # sigues pagando el 40%
    assert F.masa_salarial(mi, e) == antes - sale.salario + sale.salario * 40 // 100
    print("  test_sueldo_repartido: OK")


def test_protecciones():
    from alpha_football import contraofertas as CO, mercado_ia as MIA
    from alpha_football.ui.plantilla_screen import alternar_transferible
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[9]
    P.iniciar(e, j, club, mi, 12, 50)
    assert alternar_transferible(j) is False and not j.transferible
    e['ofertas_recibidas'] = [{'jugador': j, 'comprador': e['liga'].equipos[5], 'monto': 1_000_000}]
    assert CO.vender(e, e['ofertas_recibidas'][0]) is False
    P.limpiar_ofertas(e)
    assert e['ofertas_recibidas'] == []
    cedido = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    destino = e['liga'].equipos[6]
    P.iniciar(e, cedido, mi, destino, 12, 50)
    while len(destino.jugadores) <= MIA.PLANTILLA_MAX_IA:
        destino.jugadores.append(Jugador(nombre='X', apellido=str(len(destino.jugadores)), posicion='DEF',
                                         ataque=30, defensa=30, fisico=30, tecnica=30, mental=30))
    cedido.ataque = cedido.defensa = cedido.fisico = cedido.tecnica = cedido.mental = 20
    MIA._liberar_sobrantes(destino)
    assert cedido in destino.jugadores                           # la IA no libera al cedido
    print("  test_protecciones: OK")


def test_contrato_vence_durante_la_cesion():
    from alpha_football import finanzas as F
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    destino = e['liga'].equipos[6]
    P.iniciar(e, j, mi, destino, 12, 50)
    j.contrato_anios = 1
    F.cierre_temporada(e)
    assert j.prestamo is None and j not in destino.jugadores and j not in mi.jugadores
    assert j in e.get('free_agents_list', [])                    # vuelve y se va libre
    print("  test_contrato_vence_durante_la_cesion: OK")
```

- [ ] **Step 2: Correr y ver que fallan.**

- [ ] **Step 3: `finanzas.masa_salarial`:**

```python
def masa_salarial(equipo, estado: Optional[dict] = None) -> int:
    """Sueldos anuales que paga el club: los propios, solo su % de los que tiene a préstamo y, con
    `estado`, el % que sigue pagando de sus cedidos (prestamos.py)."""
    total = 0
    for j in getattr(equipo, 'jugadores', []) or []:
        asegurar_contrato(j)
        p = getattr(j, 'prestamo', None)
        total += int(j.salario) * (100 - int(p['pct_dueno'])) // 100 if p else int(j.salario)
    if estado is not None:
        try:
            from alpha_football.prestamos import cedidos
            for j, _club in cedidos(estado, getattr(equipo, 'nombre', None)):
                total += int(j.salario) * int(j.prestamo['pct_dueno']) // 100
        except Exception as e:
            logger.error(f"No se pudo sumar el sueldo de los cedidos: {e}")
    return total
```

En `procesar_jornada`: `salarios = masa_salarial(mi, estado) // n`. En `negociacion_screen` (texto "Masa salarial") y `finanzas_screen` (si llama `masa_salarial(mi)`), pasar `estado`.

- [ ] **Step 4: `prestamos.py`:**

```python
def limpiar_ofertas(estado: dict) -> None:
    """Un jugador a préstamo no recibe ofertas de traspaso (ni por él ni por los tuyos cedidos)."""
    estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or []
                                   if o.get('prestamo') or not getattr(o.get('jugador'), 'prestamo', None)]


def cierre_contratos(estado: dict) -> None:
    """Antes de descontar contratos: el cedido cuyo contrato vence vuelve a su dueño (ahí queda libre o renueva)."""
    for eq in _equipos(estado):
        for j in list(eq.jugadores):
            if getattr(j, 'prestamo', None) and int(getattr(j, 'contrato_anios', 1) or 1) <= 1:
                _mover_vuelta(estado, j, "se le termina el contrato")
```

`finanzas.cierre_temporada`: primera línea del cuerpo (antes de `asegurar_contratos(estado)`):

```python
    try:   # cedidos con el contrato por vencer vuelven a su dueño antes de descontar
        from alpha_football.prestamos import cierre_contratos
        cierre_contratos(estado)
    except Exception as e_pr:
        logger.error(f"No se pudieron cerrar los préstamos por contrato: {e_pr}")
```

- [ ] **Step 5: Protecciones** (una línea cada una, con comentario "a préstamo: no se toca"):
  - `mercado_ia.py`, bucle `for j in vendedor.jugadores:` de la ronda: `if getattr(j, 'prestamo', None): continue` como primera línea.
  - `mercado_ia._liberar_sobrantes`: `suplentes = [j for j in equipo.jugadores if id(j) not in titulares and not getattr(j, 'prestamo', None)]`.
  - `mercado_ia.pago_clausulas`: en `for j in mi.jugadores:` → `if getattr(j, 'prestamo', None): continue`.
  - `contraofertas.vender`: tras la validación `if jug not in mi_equipo.jugadores:`, agregar `if getattr(jug, 'prestamo', None): return False`.
  - `finanzas.vender_mejor`: `vendibles` excluye `getattr(j, 'prestamo', None)`.
  - `salidas.marcar_salida_forzada`: ordenar solo `[j for j in equipo.jugadores if not getattr(j, 'prestamo', None)]`.
  - `plantilla_screen.alternar_transferible`: primera línea `if getattr(jugador, 'prestamo', None): return False`.
  - `plantilla_screen` (tecla R y clic en `renovar`): no abrir la renovación si `jugadores[orden[pos_sel]].prestamo` (no hace nada).
  - `retiros.procesar_retiros`: tras `retiros.append(...)`, si `getattr(j, 'prestamo', None)` y el user es dueño o club, `correo.enviar(estado, 'club', f"{j.nombre_completo} se retiró", "Estaba a préstamo: el préstamo terminó con su retiro.")`.

- [ ] **Step 6: Correr** `python tests/test_prestamos.py` (16/16), `python tests/test_finanzas_v290.py`, `python tests/test_mercado_v440.py`, `python tests/test_mercado_v350.py`: todo pasa.

---

### Task 5: Enganches de jornada/temporada + PLANTILLA (lista, ficha, CONCLUIR) + ayuda

**Files:**
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py` (`avanzar_nueva_temporada`)
- Modify: `alpha_football/ui/plantilla_screen.py`
- Modify: `alpha_football/ui/ayuda.py`, `alpha_football/ui/atajos.py`
- Test: `tests/test_prestamos.py`

**Interfaces:**
- Consumes: `revisar_jornada`, `resolver_analisis`, `generar_ofertas`, `limpiar_ofertas`, `alternar_lista`, `en_lista`, `entrantes`, `cedidos`, `terminar` (Tasks 1-4).
- Produces: `plantilla_screen._rects()['lista_prestamo']`, `['prestamos']`; overlay `estado['prestamos_abierto']`; `plantilla_screen.rects_overlay_prestamos(n) -> list`.

- [ ] **Step 1: Tests que fallan:**

```python
def test_vuelve_al_empezar_la_temporada():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = estado_carrera(); _abierto(e, 2); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[10]
    P.iniciar(e, j, club, mi, 12, 50)                           # vuelve en J1 de la T2
    for p in getattr(e['liga'], 'calendario', []) or []:
        p.jugado = True
    avanzar_nueva_temporada(e)
    assert e['temporada'] == 2 and j.prestamo is None and any(x is j for x in club.jugadores)
    print("  test_vuelve_al_empezar_la_temporada: OK")


def test_plantilla_lista_y_concluir():
    from alpha_football.ui import plantilla_screen as PS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[10]
    P.iniciar(e, j, club, mi, 12, 50)
    pygame.event.clear(); PS.render(screen, e)
    idx = mi.jugadores.index(j); e['plantilla_sel'] = idx
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PS._rects()['prestamos'].center))
    PS.render(screen, e)
    assert e.get('prestamos_abierto')
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PS.rects_overlay_prestamos(1)[0][1].center))
    PS.render(screen, e)
    assert j.prestamo is None and j in club.jugadores           # mercado abierto: vuelve ya
    otro = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    e['plantilla_sel'] = mi.jugadores.index(otro); e['prestamos_abierto'] = False
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0, unicode='p'))
    PS.render(screen, e)
    assert P.en_lista(e, otro)
    print("  test_plantilla_lista_y_concluir: OK")
```

- [ ] **Step 2: Correr y ver que fallan.**

- [ ] **Step 3: Enganches.** En `match_screen.finalizar_jornada_liga`, después del bloque `resolver_analisis(estado)` (v3.5.0):

```python
        try:  # préstamos: idas/vueltas en ventana, análisis, ofertas de préstamo y purga de ofertas
            from alpha_football import prestamos as _pr
            import random as _rnd
            _azar = _rnd.Random()
            _pr.revisar_jornada(estado, _azar)
            _pr.resolver_analisis(estado, _azar)
            _pr.generar_ofertas(estado, _azar)
            _pr.limpiar_ofertas(estado)
        except Exception as e_pr:
            logger.error(f"Error con los préstamos de la jornada: {e_pr}")
```

En `resumen_temporada_screen.avanzar_nueva_temporada`, después del bloque de `ofertas_garantizadas` (v4.4.0):

```python
        try:  # J1 es ventana: vuelven los préstamos de 1 año y arrancan los acordados
            from alpha_football.prestamos import revisar_jornada as _prestamos_j1
            _prestamos_j1(estado)
        except Exception as e_pr:
            logger.error(f"Error con los préstamos al empezar la temporada: {e_pr}")
```

- [ ] **Step 4: PLANTILLA.**
  - `_rects()`: `'renovar'` pasa a la mitad izquierda y se agrega `'lista_prestamo'` a la derecha, más el botón de cabecera:

```python
        'renovar': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 122, (R_FICHA.width - 50) // 2, 48),
        'lista_prestamo': pygame.Rect(R_FICHA.x + 30 + (R_FICHA.width - 50) // 2, R_FICHA.bottom - 122,
                                      (R_FICHA.width - 50) // 2, 48),
        'prestamos': pygame.Rect(440, 18, 250, 44),
```

  - Texto de botones: `"RENOVAR (R)"` y `"QUITAR DE PRÉSTAMO (P)"`/`"A PRÉSTAMO (P)"`; si el jugador ya está a préstamo, `"A PRÉSTAMO"` deshabilitado (sin acción).
  - Tecla `P` y clic en `'lista_prestamo'` → `prestamos.alternar_lista(estado, jugadores[orden[pos_sel]])`.
  - Cabecera: `draw_button(screen, rects['prestamos'], f"PRÉSTAMOS ({n})", ...)` con `n = len(entrantes) + len(cedidos)`; clic → `estado['prestamos_abierto'] = not ...`.
  - Ficha (`_dibujar_ficha`): si `j.prestamo` → `estado_txt += f" · A PRÉSTAMO de {p['dueno']} (vuelve J{p['vuelve'][1]} T{p['vuelve'][0]})"`; si `prestamos.en_lista(estado, j)` → `" · EN LISTA DE PRÉSTAMO"`.
  - Overlay (con `estado['prestamos_abierto']` consume los clics y Esc lo cierra):

```python
R_OVERLAY_PR = pygame.Rect(140, 120, 1000, 480)


def rects_overlay_prestamos(n: int) -> list:
    """[(fila, botón CONCLUIR)] de cada préstamo listado en el overlay."""
    out = []
    for i in range(min(n, 10)):
        fila = pygame.Rect(R_OVERLAY_PR.x + 20, R_OVERLAY_PR.y + 70 + i * 38, R_OVERLAY_PR.width - 40, 34)
        out.append((fila, pygame.Rect(fila.right - 210, fila.y + 2, 200, 30)))
    return out


def _filas_prestamos(estado: dict) -> list:
    """[(jugador, texto)]: los que tienes a préstamo y los tuyos cedidos."""
    from alpha_football import prestamos as PR
    filas = []
    for j in PR.entrantes(estado):
        p = j.prestamo
        filas.append((j, f"A PRÉSTAMO  {j.nombre_completo[:22]}  de {p['dueno'][:20]}  ·  pagas {100 - p['pct_dueno']}%  ·  vuelve J{p['vuelve'][1]} T{p['vuelve'][0]}"))
    for j, eq in PR.cedidos(estado):
        p = j.prestamo
        filas.append((j, f"CEDIDO  {j.nombre_completo[:22]}  en {eq.nombre[:20]}  ·  pagas {p['pct_dueno']}%  ·  vuelve J{p['vuelve'][1]} T{p['vuelve'][0]}"))
    return filas
```

    Dibujo: panel oscuro `R_OVERLAY_PR`, título "PRÉSTAMOS", cada fila con su texto y botón "CONCLUIR PRÉSTAMO"; sin filas: "No tienes préstamos." Clic en un botón → `msg = prestamos.terminar(estado, j)`; se muestra `msg` 3 s abajo del panel (`estado['plantilla_msg'] = (msg, ticks + 3000)`).
  - Pie de la lista: `"↑↓ elegir · T transferible · R renovar · P préstamo · clic encabezado ordena · verde = titular"`.

- [ ] **Step 5: Ayuda y atajos.** `ayuda._ayuda_plantilla`: agregar `(r['lista_prestamo'], "Préstamo", "Pone al jugador en la lista de préstamo: los clubes te mandan ofertas de cesión (tecla P).")` y `(r['prestamos'], "Préstamos", "Tus jugadores a préstamo y los cedidos, con CONCLUIR PRÉSTAMO.")` (≤ 110 caracteres). `ayuda._ayuda_buscador`: `(r['prestamo'], "Préstamo", "Pide al jugador a préstamo por 6 meses o 1 año pagando un % del sueldo.")`. `atajos.ATAJOS['plantilla_screen']` agrega `P Préstamo`.

- [ ] **Step 6: Correr** `python tests/test_prestamos.py` (18/18), `python tests/test_ayuda_v390.py`, `python tests/test_ux_v360.py`, `python tests/test_plantilla_v260.py`, `python tests/test_hub_v240.py`: todo pasa. Capturas headless de PLANTILLA con el overlay abierto y de la ficha revisadas.

- [ ] **Step 7: Suite completa** archivo por archivo (`for f in tests/test_*.py; do python "$f"; done` con el entorno de arriba): todo en verde. Actualizar `context.md` (bitácora "Préstamos") al terminar.
