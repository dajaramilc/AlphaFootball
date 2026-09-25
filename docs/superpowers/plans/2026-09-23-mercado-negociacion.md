# Mercado y negociación (sub-proyecto 3, v3.5.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Contraofertas en ventas y "lo analizamos" en compras (respuesta por correo 50/50), montos exactos y tecleables, ficha del jugador ofrecido, más ofertas del exterior, rivalidades y descuento por contrato por vencer.

**Architecture:** Lógica nueva en `alpha_football/contraofertas.py` (ventas y análisis) + funciones en `negociacion.py` y `market.py`; UI en `ofertas_screen.py`, `negociacion_screen.py`, `correo_screen.py` y dos componentes nuevos (`ui/ficha_jugador.py`, `ui/entrada_monto.py`). Estado persistente de compras analizadas en `datos_carrera`; las contraofertas de venta viven en el dict de la oferta (como las ofertas mismas, que no se guardan).

**Tech Stack:** Python 3.10+, Pygame; tests con runner propio (`python tests/test_x.py`).

**Spec:** `docs/superpowers/specs/2026-09-23-mercado-negociacion-design.md`

## Global Constraints
- Comentarios en español con `# v3.5.0: ...`; try/except + `logger.error` en cada hook; pantallas con el bloque theme+fallback de `ui/despido_screen.py`.
- **NO hacer commits.** Suite tras cada tarea: `for f in tests/test_*.py; do SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python "$f" > /dev/null 2>&1 || echo "FALLA $f"; done`.
- Constantes: tope = monto × U(1.10, 1.35) (local: ≤ max(monto, balance comprador)); analizar hasta tope × 1.30; 50/50 al resolver; compras analizan desde 85% del mínimo; exterior 25%/jornada + top 3 por media; clásico solo cláusula salvo moral < 40; último año de contrato ×0.75.

## Review Focus
- Oferta cuyo jugador ya no está (vendido, cláusula, venta forzada) y que tenía contraoferta analizándose → al resolver no cobra ni duplica: se descarta en silencio. Test en Task 2 (`test_analisis_jugador_ya_no_esta`).
- Acuerdo de compra aprobado que se usa con la ventana cerrada / otra temporada / jugador ya vendido → no abre la negociación, deja aviso. Test en Task 2 (`test_reanudar_compra_invalida`).
- Contraoferta con monto ≤ oferta o segunda contraoferta → rechazada como inválida sin tocar la oferta. Test en Task 2 (`test_una_sola_contraoferta`).
- Comprador local sin dinero para el tope → el tope nunca supera su balance (salvo que el monto ya lo supere). Test en Task 2 (`test_tope`).
- Teclear montos enormes → se corta en 12 dígitos, sin overflow visual. Test en Task 3 (`test_entrada_monto`).

## Reparto
Subagente A: Tasks 1-2 (lógica). Subagente B: Task 3 (UI), después de A.

---

### Task 1: Precios — valores exactos, contrato por vencer, rivalidad en ofertas, exterior

**Files:**
- Modify: `alpha_football/negociacion.py` (`dinero_exacto`, `precio_fichaje`)
- Modify: `alpha_football/market.py` (`factor_contrato`, `crear_oferta_ui`, `crear_oferta_exterior`)
- Test: `tests/test_mercado_v350.py` (nuevo; cabecera igual a `tests/test_directiva_v280.py` líneas 1-31, + `import random`, `from alpha_football import market as M, negociacion as N, correo as C`)

**Interfaces — Produces:** `negociacion.dinero_exacto(v) -> str`; `market.factor_contrato(j) -> float`; `crear_oferta_exterior(mi_equipo, estado, rng=None, prob=0.25)`.

- [ ] **Step 1: Tests**
```python
class RngFijo(random.Random):
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def test_dinero_exacto():
    assert N.dinero_exacto(12_345_000) == "$12,345,000" and N.dinero_exacto(0) == "$0"


def test_factor_contrato():
    e = estado_carrera(); j = e['mi_equipo'].jugadores[3]
    j.contrato_anios = 1; assert M.factor_contrato(j) == 0.75
    base = int(M.precio_compra(j))
    assert N.precio_fichaje(j) == int(base * 0.75)
    j.contrato_anios = 2; assert M.factor_contrato(j) == 1.0 and N.precio_fichaje(j) == base
    j.contrato_anios = 0; assert M.factor_contrato(j) == 1.0


def test_oferta_ia_con_descuento_contrato():
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores: j.contrato_anios = 1
    rivales = [x for x in e['liga'].equipos if x is not mi]
    for r in rivales: r.balance = 10**10
    of = M.crear_oferta_ui(mi, rivales, 1, 10, rng=RngFijo(0.0))
    assert of and of['monto'] == int(of['jugador'].valor * 0.95 * 0.75)


def test_clasico_no_oferta_salvo_moral_baja():
    e = estado_carrera(); mi = e['mi_equipo']; rival = e['liga'].equipos[1]
    mi.rival, rival.rival = rival.nombre, mi.nombre
    rival.balance = 10**10
    for j in mi.jugadores: j.moral = 70; j.transferible = False
    assert M.crear_oferta_ui(mi, [rival], 1, 10, rng=RngFijo(0.0)) is None
    for j in mi.jugadores: j.moral = 30
    assert M.crear_oferta_ui(mi, [rival], 1, 10, rng=RngFijo(0.0)) is not None


def test_exterior_mas_ofertas_y_top3():
    import inspect
    assert inspect.signature(M.crear_oferta_exterior).parameters['prob'].default == 0.25
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores: j.promedio_nota = 0.0; j.goles = j.asistencias = 0
    of = M.crear_oferta_exterior(mi, e, rng=RngFijo(0.0))
    top3 = sorted(mi.jugadores, key=lambda j: -j.overall)[:3]
    assert of and of['jugador'] in top3 and of['exterior']
```
(TESTS + bloque runner como en los demás tests.) Si `es_clasico` de `data/clasicos.py` no reconoce el par por `rival` completo, ajustar el test para usar un par real de `clasicos.py` (leer la función antes).

- [ ] **Step 2: Verificar que fallan.**
- [ ] **Step 3: Implementar.**
```python
# negociacion.py
def dinero_exacto(v) -> str:
    """v3.5.0: monto completo, sin redondear ($12,345,000)."""
    return f"${int(v or 0):,}"


def precio_fichaje(jugador) -> int:
    try:
        from alpha_football.market import precio_compra, factor_contrato
        return int(int(precio_compra(jugador)) * factor_contrato(jugador))   # v3.5.0: último año −25%
    except Exception:
        return int(getattr(jugador, 'valor', 0) or 0)
```
```python
# market.py (junto a calcular_valor)
DESCUENTO_ULTIMO_ANIO = 0.75


def factor_contrato(jugador) -> float:
    """v3.5.0: en el último año de contrato el jugador vale 25% menos (la cláusula no cambia)."""
    try:
        return DESCUENTO_ULTIMO_ANIO if int(getattr(jugador, 'contrato_anios', 0) or 0) == 1 else 1.0
    except Exception:
        return 1.0
```
En `crear_oferta_ui`: `monto = int(valor * azar.uniform(0.95, 1.5) * factor_contrato(objetivo))`; y
```python
        from alpha_football.data.clasicos import es_clasico    # v3.5.0: el clásico solo paga cláusula
        if getattr(objetivo, 'moral', 70) >= 40:
            rivales = [r for r in rivales if not es_clasico(r, mi_equipo)]
        rivales_ok = [r for r in rivales if getattr(r, "balance", 0) >= monto] or list(rivales)
```
(Si el filtro deja la lista vacía → `return None`.)
En `crear_oferta_exterior`: `prob: float = 0.25`; tras armar `buenos`, añadir los 3 mejores por media sin repetir: `for j in sorted(jugadores, key=lambda x: -getattr(x, 'overall', 0))[:3]: if j not in buenos: buenos.append(j)`; `monto = int(valor * azar.uniform(1.3, 2.2) * factor_contrato(objetivo))`. Revisar `match_screen.finalizar_jornada_liga` (llama `_crear_ext(mi_equipo, estado)`, usa el default). Ojo: con `candidatos.sort(key=_rend)` el top 3 por media puede no quedar entre los 3 primeros por rendimiento cuando todos rinden 0; ordenar por `(_rend, overall)` para que el test sea determinista.
- [ ] **Step 4-5:** test verde + suite.

---

### Task 2: Contraofertas (ventas) y análisis de compras

**Files:**
- Create: `alpha_football/contraofertas.py`
- Modify: `alpha_football/negociacion.py` (`evaluar_compra`, `reanudar_compra`)
- Modify: `alpha_football/ui/ofertas_screen.py:44-85` (`_aceptar` → delega en `contraofertas.vender`)
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga`: hook `contraofertas.resolver_analisis`, en su propio try)
- Test: `tests/test_mercado_v350.py`

**Interfaces — Produces:**
- `contraofertas.asignar_tope(of, rng=None) -> int`, `vender(estado, of) -> bool`, `retirar(estado, of) -> None`, `contraofertar(estado, of, pedido, rng=None) -> tuple[str, str]` (`'aceptada'|'analizando'|'rechazada'|'invalida'`, mensaje), `resolver_analisis(estado, rng=None) -> None` (ventas + compras).
- `negociacion.evaluar_compra(estado, jugador, club, monto) -> tuple[str, str, int]` (`'acepta'|'analiza'|'rechaza'`, msg, contraoferta), `negociacion.reanudar_compra(estado, compra: dict) -> Optional[str]`.

- [ ] **Step 1: Tests** (añadir a `TESTS`; `from alpha_football import contraofertas as CO`)
```python
def _oferta(e, monto=10_000_000, exterior=False, balance=10**9):
    mi = e['mi_equipo']; j = mi.jugadores[5]; comp = e['liga'].equipos[1]; comp.balance = balance
    of = {'jugador': j, 'comprador': comp, 'monto': monto}
    if exterior: of['exterior'] = True
    e['ofertas_recibidas'] = [of]
    return of


def test_tope():
    e = estado_carrera(); of = _oferta(e)
    t = CO.asignar_tope(of, random.Random(1))
    assert 11_000_000 <= t <= 13_500_000 and CO.asignar_tope(of) == t       # no cambia
    of2 = _oferta(e, balance=10_500_000); assert CO.asignar_tope(of2, RngFijo(0.99)) <= 10_500_000
    of3 = _oferta(e, exterior=True, balance=0); assert CO.asignar_tope(of3, RngFijo(0.99)) > 13_000_000


def test_contraoferta_aceptada():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    mi = e['mi_equipo']; antes = mi.balance; j = of['jugador']
    r, _ = CO.contraofertar(e, of, 11_500_000)
    assert r == 'aceptada' and j not in mi.jugadores and mi.balance == antes + 11_500_000
    assert not e['ofertas_recibidas']


def test_contraoferta_analizando_y_resolucion():
    for v, vendido in ((0.0, True), (0.99, False)):
        e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
        j = of['jugador']; mi = e['mi_equipo']
        r, msg = CO.contraofertar(e, of, 15_000_000)
        assert r == 'analizando' and "analizamos" in msg.lower()
        assert of['contra']['estado'] == 'analizando' and j in mi.jugadores
        CO.resolver_analisis(e, rng=RngFijo(v))                  # misma jornada: no resuelve
        assert of in e['ofertas_recibidas']
        e['liga'].jornada_actual += 1
        CO.resolver_analisis(e, rng=RngFijo(v))
        assert (j not in mi.jugadores) == vendido and not e['ofertas_recibidas']
        assert C.bandeja(e)[0]['remitente'] == 'club'


def test_contraoferta_rechazada():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    r, _ = CO.contraofertar(e, of, 20_000_000)
    assert r == 'rechazada' and not e['ofertas_recibidas'] and of['jugador'] in e['mi_equipo'].jugadores


def test_una_sola_contraoferta():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    assert CO.contraofertar(e, of, 9_000_000)[0] == 'invalida' and 'contra' not in of
    CO.contraofertar(e, of, 15_000_000)
    assert CO.contraofertar(e, of, 11_000_000)[0] == 'invalida'


def test_analisis_jugador_ya_no_esta():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    CO.contraofertar(e, of, 15_000_000)
    from alpha_football.finanzas import quitar_de_plantilla
    quitar_de_plantilla(e['mi_equipo'], of['jugador'])
    antes = e['mi_equipo'].balance
    e['liga'].jornada_actual += 1
    CO.resolver_analisis(e, rng=RngFijo(0.0))
    assert e['mi_equipo'].balance == antes and not e['ofertas_recibidas']


def _objetivo_compra(e, moral=70):
    club = e['liga'].equipos[2]; j = sorted(club.jugadores, key=lambda x: -x.overall)[5]
    j.moral = moral; j.contrato_anios = 3
    return club, j


def test_compra_rangos():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    minimo = N.minimo_club(j, club)
    assert N.evaluar_compra(e, j, club, minimo)[0] == 'acepta'
    r, msg, _ = N.evaluar_compra(e, j, club, int(minimo * 0.9))
    assert r == 'analiza' and "analizamos" in msg.lower()
    assert e['datos_carrera']['analisis_compras'][0]['jugador_id'] == j.id
    r, _, contra = N.evaluar_compra(e, j, club, int(minimo * 0.5))
    assert r == 'rechaza' and contra == minimo


def test_compra_clasico_solo_clausula():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    e['mi_equipo'].rival, club.rival = club.nombre, e['mi_equipo'].nombre
    r, msg, contra = N.evaluar_compra(e, j, club, N.minimo_club(j, club) * 3)
    if j.clausula > N.minimo_club(j, club) * 3:
        assert r == 'rechaza' and "clásico" in msg.lower() and contra == int(j.clausula)
    assert N.evaluar_compra(e, j, club, int(j.clausula))[0] == 'acepta'
    j.moral = 30
    assert N.evaluar_compra(e, j, club, N.minimo_club(j, club))[0] == 'acepta'


def test_compra_analizada_correo_y_reanudar():
    e = estado_carrera(); club, j = _objetivo_compra(e); e['liga'].jornada_actual = 1
    monto = int(N.minimo_club(j, club) * 0.9)
    N.evaluar_compra(e, j, club, monto)
    e['liga'].jornada_actual = 2
    CO.resolver_analisis(e, rng=RngFijo(0.0))
    msg = C.bandeja(e)[0]
    assert msg['accion']['compra']['jugador_id'] == j.id and not e['datos_carrera']['analisis_compras']
    assert N.reanudar_compra(e, msg['accion']['compra']) == 'negociacion_screen'
    assert e['neg']['etapa'] == 'jugador' and e['neg']['monto'] == monto and e['neg']['jugador'] is j


def test_reanudar_compra_invalida():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    compra = {'jugador_id': j.id, 'club_id': club.id, 'monto': 1, 'temporada': 1}
    e['liga'].jornada_actual = 5                                  # ventana cerrada (10 jornadas)
    assert N.reanudar_compra(e, compra) is None and e.get('correo_aviso')
    e['liga'].jornada_actual = 2; compra['temporada'] = 0
    assert N.reanudar_compra(e, compra) is None
```
- [ ] **Step 2: Verificar que fallan.**
- [ ] **Step 3: Implementar.**

`alpha_football/contraofertas.py`:
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Contraofertas y "lo analizamos" (v3.5.0)
Ventas: cada oferta recibida tiene un tope oculto; contraofertar dentro del tope cierra la venta, hasta
+30% del tope queda "en análisis" (respuesta por correo en la jornada siguiente, 50/50) y más arriba
se retira. Compras: las ofertas del user entre el 85% y el 100% del mínimo del club se analizan igual
(negociacion.evaluar_compra) y se resuelven aquí.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

TOPE_RANGO = (1.10, 1.35)
MARGEN_ANALISIS = 1.30
PROB_ACEPTA_ANALISIS = 0.5


def _jornada(estado: dict) -> int:
    return int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1)


def asignar_tope(of: dict, rng: Optional[random.Random] = None) -> int:
    if 'tope' not in of:
        azar = rng or random.Random()
        monto = int(of.get('monto', 0) or 0)
        tope = int(monto * azar.uniform(*TOPE_RANGO))
        if not of.get('exterior'):
            tope = min(tope, max(monto, int(getattr(of.get('comprador'), 'balance', 0) or 0)))
        of['tope'] = tope
    return int(of['tope'])


def retirar(estado: dict, of: dict) -> None:
    estado['ofertas_recibidas'] = [o for o in (estado.get('ofertas_recibidas') or []) if o is not of]


def vender(estado: dict, of: dict) -> bool:
    """Cierra la venta de `of` (lógica que antes vivía en ofertas_screen._aceptar)."""
    # Mover aquí, sin cambios de comportamiento, el cuerpo de ui/ofertas_screen._aceptar (v2.9.x):
    # descartar si el jugador ya no está; quitar TODAS las ofertas por ese jugador; cobrar; registrar
    # 'ventas'; quitar_de_plantilla; pasar al comprador; transferible/pide_salir = False; cobrarle al
    # comprador; registrar_pase; completar_plantilla; transfer_log. Retorna True si vendió.
    ...


def contraofertar(estado: dict, of: dict, pedido: int, rng: Optional[random.Random] = None) -> tuple:
    from alpha_football.negociacion import dinero_exacto
    pedido = int(pedido or 0)
    comp = getattr(of.get('comprador'), 'nombre', 'El club')
    if of.get('contra'):
        return 'invalida', "Ya contraofertaste por esta oferta."
    if pedido <= int(of.get('monto', 0) or 0):
        return 'invalida', "La contraoferta tiene que superar la oferta."
    tope = asignar_tope(of, rng)
    if pedido <= tope:
        of['monto'] = pedido
        vender(estado, of)
        return 'aceptada', f"{comp} acepta {dinero_exacto(pedido)}."
    if pedido <= int(tope * MARGEN_ANALISIS):
        of['contra'] = {'pedido': pedido, 'estado': 'analizando', 'jornada': _jornada(estado)}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    retirar(estado, of)
    return 'rechazada', f"{comp} considera excesivo {dinero_exacto(pedido)} y retira la oferta."


def _resolver_ventas(estado: dict, azar: random.Random) -> None:
    from alpha_football import correo as C
    from alpha_football.negociacion import dinero_exacto
    mi = estado.get('mi_equipo')
    for of in list(estado.get('ofertas_recibidas') or []):
        c = of.get('contra') or {}
        if c.get('estado') != 'analizando' or _jornada(estado) <= int(c.get('jornada', 0)):
            continue
        jug, comp = of.get('jugador'), of.get('comprador')
        if mi is None or jug not in mi.jugadores:
            retirar(estado, of)
            continue
        nombre = getattr(jug, 'nombre_completo', '?')
        if azar.random() < PROB_ACEPTA_ANALISIS:
            of['monto'] = int(c['pedido'])
            vender(estado, of)
            C.enviar(estado, 'club', f"{comp.nombre} acepta tu contraoferta",
                     f"{nombre} se va a {comp.nombre} por {dinero_exacto(c['pedido'])}.")
        else:
            retirar(estado, of)
            C.enviar(estado, 'club', f"{comp.nombre} se retira",
                     f"No pagará {dinero_exacto(c['pedido'])} por {nombre}. La oferta quedó sin efecto.")


def _resolver_compras(estado: dict, azar: random.Random) -> None:
    from alpha_football import correo as C
    from alpha_football.negociacion import dinero_exacto, minimo_club, buscar_en_club
    dc = estado.setdefault('datos_carrera', {})
    pend = dc.setdefault('analisis_compras', [])
    for a in list(pend):
        if _jornada(estado) <= int(a.get('jornada', 0)):
            continue
        pend.remove(a)
        club, j = buscar_en_club(estado, a['club_id'], a['jugador_id'])
        if club is None or j is None:
            continue
        if azar.random() < PROB_ACEPTA_ANALISIS:
            compra = {k: a[k] for k in ('jugador_id', 'club_id', 'monto', 'temporada')}
            C.enviar(estado, 'club', f"{club.nombre} acepta tu oferta",
                     f"Aceptan {dinero_exacto(a['monto'])} por {j.nombre_completo}. "
                     "Negocia el contrato con el jugador mientras la ventana siga abierta.",
                     {'pantalla': 'negociacion_screen', 'texto': "NEGOCIAR CONTRATO", 'compra': compra})
        else:
            C.enviar(estado, 'club', f"{club.nombre} rechaza tu oferta",
                     f"No vende a {j.nombre_completo} por {dinero_exacto(a['monto'])}. "
                     f"Pide {dinero_exacto(minimo_club(j, club))}.")


def resolver_analisis(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Hook de cada jornada de liga del user."""
    azar = rng or random.Random()
    for paso in (_resolver_ventas, _resolver_compras):
        try:
            paso(estado, azar)
        except Exception as e:
            logger.error(f"resolver_analisis ({paso.__name__}): {e}", exc_info=True)
```
(El `...` de `vender` NO es un placeholder de diseño: es mover literalmente el cuerpo de `ofertas_screen._aceptar` líneas 44-85 cambiando `return` por `return False`/`return True`; `ofertas_screen._aceptar(estado, of)` pasa a ser `contraofertas.vender(estado, of)`.)

`negociacion.py` — añadir:
```python
UMBRAL_ANALISIS = 0.85
MORAL_BAJA = 40


def buscar_en_club(estado: dict, club_id, jugador_id) -> tuple:
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if str(eq.id) == str(club_id):
                    return eq, next((j for j in eq.jugadores if str(j.id) == str(jugador_id)), None)
    return None, None


def evaluar_compra(estado: dict, jugador, club, monto: int) -> tuple:
    """v3.5.0: ('acepta'|'analiza'|'rechaza', mensaje, contraoferta) para una oferta del user."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    if club is None:
        return 'acepta', "Agente libre: no hay club con quien negociar.", 0
    clausula = int(jugador.clausula or 0)
    if monto >= clausula > 0:
        return 'acepta', f"Pagas la cláusula: {club.nombre} no puede negarse.", 0
    from alpha_football.data.clasicos import es_clasico
    if es_clasico(club, estado.get('mi_equipo')) and int(getattr(jugador, 'moral', 70)) >= MORAL_BAJA:
        return 'rechaza', f"Es tu clásico: solo por la cláusula de {dinero_exacto(clausula)}.", clausula
    minimo = minimo_club(jugador, club)
    if monto >= minimo:
        return 'acepta', f"{club.nombre} acepta {dinero_exacto(monto)}.", 0
    if monto >= int(minimo * UMBRAL_ANALISIS):
        dc = estado.setdefault('datos_carrera', {})
        pend = [a for a in dc.get('analisis_compras', []) if a.get('jugador_id') != jugador.id]
        pend.append({'jugador_id': jugador.id, 'club_id': club.id, 'club': club.nombre,
                     'jugador': jugador.nombre_completo, 'monto': int(monto),
                     'jornada': int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1),
                     'temporada': int(estado.get('temporada', 1) or 1)})
        dc['analisis_compras'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada.", 0
    return 'rechaza', f"{club.nombre} rechaza. Pide {dinero_exacto(minimo)}.", minimo


def reanudar_compra(estado: dict, compra: dict) -> Optional[str]:
    """Desde el correo de 'acepta tu oferta': negociación del contrato con el monto pactado."""
    from alpha_football.market import ventana_mercado_abierta
    liga = estado.get('liga')
    club, j = buscar_en_club(estado, compra.get('club_id'), compra.get('jugador_id'))
    motivo = None
    if int(compra.get('temporada', -1)) != int(estado.get('temporada', 1) or 1):
        motivo = "El acuerdo era de otra temporada."
    elif liga is None or not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
        motivo = "La ventana de fichajes está cerrada."
    elif j is None:
        motivo = "El jugador ya no está en ese club."
    if motivo:
        estado['correo_aviso'] = motivo
        return None
    iniciar_negociacion(estado, j, club, 'fichaje', 'correo_screen')
    estado['neg']['etapa'] = 'jugador'
    estado['neg']['monto'] = int(compra['monto'])
    return 'negociacion_screen'
```
Además reemplazar `_dinero` por `dinero_exacto` en los mensajes de `evaluar_oferta_club` / `evaluar_contrato` (valores exactos). Revisar tests existentes que comparen esos textos (`grep -rn "Pide \\$" tests/`).

`match_screen.finalizar_jornada_liga`, junto a los hooks v3.2.0:
```python
        try:  # v3.5.0: respuestas "lo analizamos" (ventas y compras)
            from alpha_football.contraofertas import resolver_analisis
            resolver_analisis(estado)
        except Exception as e_co:
            logger.error(f"Error al resolver contraofertas: {e_co}")
```
- [ ] **Step 4-5:** test verde + suite (en especial `test_valor_ofertas.py`, `test_negociaciones_v270.py`, `test_finanzas_v290.py`).

---

### Task 3: UI — ficha compartida, monto tecleable, OFERTAS con contraoferta, correo → negociación

**Files:**
- Create: `alpha_football/ui/ficha_jugador.py`, `alpha_football/ui/entrada_monto.py`
- Modify: `alpha_football/ui/plantilla_screen.py:97-149` (usa `dibujar_ficha` + sus botones)
- Modify: `alpha_football/ui/ofertas_screen.py` (rediseño: lista + ficha + contraoferta)
- Modify: `alpha_football/ui/negociacion_screen.py` (teclear monto; `evaluar_compra`; montos exactos)
- Modify: `alpha_football/ui/correo_screen.py:58-63` (acción `compra` + aviso)
- Test: `tests/test_mercado_v350.py`

**Interfaces — Produces:** `ficha_jugador.dibujar_ficha(screen, rect, j, estado_txt: str = "") -> int`; `entrada_monto.editar_valor(v: int, ev) -> int`; en `ofertas_screen`: `rect_oferta(i) -> Rect`, `R_ACEPTAR`, `R_RECHAZAR`, `R_CONTRA`, `R_ENVIAR`, `R_MAS5`, `R_MAS10`, `R_MAS25`, estado `estado['oferta_sel']`, `estado['contra_abierta']`, `estado['contra_monto']`, `estado['oferta_msg']`.

- [ ] **Step 1: Tests**
```python
def key(k, uni=''):
    pygame.event.clear(); pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def test_entrada_monto():
    from alpha_football.ui.entrada_monto import editar_valor
    ev = lambda k, u='': pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=u)
    assert editar_valor(12, ev(pygame.K_3, '3')) == 123
    assert editar_valor(123, ev(pygame.K_BACKSPACE)) == 12
    assert editar_valor(12, ev(pygame.K_a, 'a')) == 12
    assert editar_valor(10**11, ev(pygame.K_9, '9')) == 10**11       # tope 12 dígitos


def test_ficha_compartida():
    from alpha_football.ui.ficha_jugador import dibujar_ficha
    e = estado_carrera(); j = e['mi_equipo'].jugadores[0]
    y = dibujar_ficha(screen, pygame.Rect(700, 100, 560, 520), j, "Oferta")
    assert 100 < y <= 620


def test_ofertas_screen_contraoferta():
    from alpha_football.ui import ofertas_screen as S
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    pygame.event.clear(); assert S.render(screen, e) is None
    click(S.R_CONTRA.center); S.render(screen, e)
    assert e.get('contra_abierta') and e['contra_monto'] == 11_000_000        # arranca en +10%
    click(S.R_ENVIAR.center); S.render(screen, e)
    assert 'acepta' in e['oferta_msg'][0].lower() and not e['ofertas_recibidas']


def test_negociacion_teclear_y_analiza():
    from alpha_football.ui import negociacion_screen as NS
    e = estado_carrera(); club, j = _objetivo_compra(e)
    N.iniciar_negociacion(e, j, club, 'fichaje', 'buscador_screen')
    e['neg']['monto'] = 0
    for d in str(int(N.minimo_club(j, club) * 0.9)):
        key(getattr(pygame, f'K_{d}'), d); NS.render(screen, e)
    assert e['neg']['monto'] == int(N.minimo_club(j, club) * 0.9)
    e['mi_equipo'].balance = 10**10
    click(NS._rects()['ofertar'].center)
    assert NS.render(screen, e) is None
    assert "analizamos" in e['neg']['msg'][0].lower() and e['datos_carrera']['analisis_compras']


def test_correo_accion_compra():
    from alpha_football.ui import correo_screen as CS
    e = estado_carrera(); club, j = _objetivo_compra(e); e['liga'].jornada_actual = 2
    msg = {'accion': {'pantalla': 'negociacion_screen', 'texto': 'X',
                      'compra': {'jugador_id': j.id, 'club_id': club.id, 'monto': 5, 'temporada': 1}}}
    assert CS._ir(e, msg) == 'negociacion_screen' and e['neg']['monto'] == 5
```
- [ ] **Step 2: Verificar que fallan.**
- [ ] **Step 3: Implementar.**

`ui/entrada_monto.py`:
```python
# -*- coding: utf-8 -*-
"""v3.5.0: montos tecleables. Dígito = v·10 + d (máx. 12 dígitos), Backspace = v // 10."""
import pygame

MAX_MONTO = 10 ** 12 - 1


def editar_valor(v: int, ev) -> int:
    v = int(v or 0)
    if getattr(ev, 'type', None) != pygame.KEYDOWN:
        return v
    if ev.key == pygame.K_BACKSPACE:
        return v // 10
    u = getattr(ev, 'unicode', '') or ''
    if len(u) == 1 and u.isdigit():
        nuevo = v * 10 + int(u)
        return nuevo if nuevo <= MAX_MONTO else v
    return v
```
`ui/ficha_jugador.py`: mover el cuerpo de `plantilla_screen._dibujar_ficha` (líneas 97-145, sin los dos botones del final) a `dibujar_ficha(screen, rect, j, estado_txt="")`, usando `rect` en vez de `R_FICHA`, `dinero_exacto` en valor/salario/cláusula, y `estado_txt` en lugar del cálculo titular/suplente (plantilla le pasa su texto: "Titular"/"Suplente"/lesión/sanción + TRANSFERIBLE/PIDE SALIR; ofertas pasa "Oferta de <club>"). Retorna la `y` final. `plantilla_screen._dibujar_ficha` queda: calcula `estado_txt`, llama `dibujar_ficha(screen, R_FICHA, j, estado_txt)` y dibuja sus 2 botones. Las barras de atributos se escalan al ancho del rect (`min(220, rect.width - 200)`).

`ui/ofertas_screen.py` (rediseño, conservar `_aceptar` como wrapper `return contraofertas.vender(estado, of)` si algún test lo usa):
- Layout: lista a la izquierda `rect_oferta(i) = Rect(16, 110 + i*96, 640, 84)` (máx. 5 visibles, scroll con ↑/↓ que mueve `oferta_sel`), ficha a la derecha `R_FICHA = Rect(672, 110, 592, 440)` con `dibujar_ficha(..., f"Oferta de {comp.nombre}")`.
- Botones bajo la ficha: `R_ACEPTAR = Rect(672, 566, 186, 48)`, `R_RECHAZAR = Rect(875, 566, 186, 48)`, `R_CONTRA = Rect(1078, 566, 186, 48)`; teclas A / R / C sobre la oferta seleccionada.
- Tarjeta: `"{comprador} ofrece {dinero_exacto(monto)}"`, jugador, `"EXTERIOR"` si aplica, y si `of.get('contra')`: `"ANALIZANDO: pediste {dinero_exacto(pedido)}"` (sin botones de contraoferta).
- CONTRAOFERTAR abre un panel (`contra_abierta`) sobre la ficha con `contra_monto` inicial = `int(monto * 1.10)`, botones `R_MAS5`, `R_MAS10`, `R_MAS25` (suman % del monto original), dígitos/Backspace con `editar_valor`, `R_ENVIAR` (Enter) → `CO.contraofertar(estado, of, contra_monto)` → `estado['oferta_msg'] = (mensaje, color)` (verde aceptada, azul analizando, rojo rechazada/invalida); ESC cierra el panel. Ubicar `R_ENVIAR` dentro del panel (p. ej. `Rect(900, 470, 240, 48)`), y los +% en `y=400`.
- Mensaje `oferta_msg` en `(16, 660)`.
- Revisar `tests/` que usen la navegación de teclado vieja de ofertas (`grep -rn "ofertas_screen" tests/`) y adaptar solo sus aserciones.

`ui/negociacion_screen.py`:
- En la etapa `'club'`, cada KEYDOWN pasa por `neg['monto'] = editar_valor(neg['monto'], ev)`; mostrar el monto con `dinero_exacto` y la leyenda "(escribe la cifra o usa − / +)".
- OFERTAR usa `N.evaluar_compra(estado, j, club, neg['monto'])`: `'acepta'` → etapa `'jugador'` (como hoy); `'analiza'` → `neg['msg'] = (msg, 'azul')` y `neg['etapa'] = 'hecho'` (la negociación termina hasta el correo); `'rechaza'` → `neg['msg'] = (msg, 'rojo')` y, si hay contraoferta, `neg['monto'] = contra` (como hoy).
- `_m` → `dinero_exacto` en montos, salario y cláusula.

`ui/correo_screen.py`:
```python
def _ir(estado: dict, msg: dict) -> Optional[str]:
    acc = msg.get('accion') or {}
    if acc.get('compra'):          # v3.5.0: el club aceptó tu oferta → contrato con el jugador
        from alpha_football.negociacion import reanudar_compra
        return reanudar_compra(estado, acc['compra'])
    if not acc.get('pantalla'):
        return None
    from alpha_football.ui.league_screen import _abrir
    return _abrir(estado, acc['pantalla'])
```
Y dibujar `estado.pop('correo_aviso', None)` en rojo bajo el botón de acción si existe (guardarlo en `estado['correo_aviso_vis']` para que dure hasta cambiar de mensaje).
- [ ] **Step 4-5:** tests verdes + suite + `SDL_VIDEODRIVER=dummy python -c "import main"`. Captura headless de OFERTAS con 3 ofertas (una analizando) para verificar que nada se solapa.
