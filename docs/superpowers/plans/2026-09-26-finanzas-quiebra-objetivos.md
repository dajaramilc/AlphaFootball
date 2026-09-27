# Finanzas, quiebra y objetivos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que quebrar sea posible (user y, rara vez, IA), con objetivos financieros de la directiva, objetivos deportivos más difíciles, espaldarazo como deuda, pantalla OBJETIVOS reorganizada y ofertas de otros clubes durante la temporada.

**Architecture:** La economía vive en `finanzas.py` (ingresos por club, sueldos, rojo del user) y `mercado_ia.py` (cobro/pago y quiebra de la IA). La directiva (`directiva.py`) suma los objetivos financieros y la deuda del espaldarazo a su evaluación de cierre. Un módulo nuevo `ofertas_dt.py` genera las ofertas de clubes por jornada. La UI (`objetivos_screen.py`) solo lee esos módulos.

**Tech Stack:** Python 3.10, pygame 2.6 (tests con `SDL_VIDEODRIVER=dummy`), tests como scripts (`python tests/<archivo>.py`, exit 1 si falla).

**Spec:** `docs/superpowers/specs/2026-09-26-finanzas-quiebra-objetivos-design.md`

## Global Constraints

- Sin commits: Diego prueba todo al final (v4.5.0 tampoco está commiteado). Ningún paso hace `git commit`.
- Comentarios y textos en español, con el estilo del archivo que se toca (comentario corto con versión `v4.6.0:` donde se cambia comportamiento).
- Constantes nuevas al principio de su módulo: `SALARIO_PCT_VALOR = 0.08`, `JORNADAS_ROJO_VENTA = 4`, `PUNTOS_QUIEBRA = 6`, `TOPE_SALARIAL_PCT = 0.70`, `SALDO_MIN_PCT = 0.10`, `MARGEN_OBJETIVO = 0`, `VENTAJA_PARA_TITULO = 5`, `PRECIO_REMATE = 0.60`.
- Todo acceso a datos opcionales con `getattr(..., default)` / `.get` como el resto del código; cada hook nuevo en pantallas va en su propio `try/except` con `logger.error`.
- Campos nuevos en modelos: con default y leídos en `from_dict` (saves viejos cargan sin error).
- Correos con `alpha_football.correo.enviar(estado, remitente, asunto, cuerpo, accion)`; remitente nuevo `'prensa'` → "Prensa".
- La suite completa (`tests/test_*.py`) debe seguir pasando al final.

## Review Focus

1. Partida guardada antes de v4.6.0: la migración de sueldos corre **una sola vez** (cargar dos veces no multiplica dos veces) y una carrera nueva **no** se migra.
2. Aceptar una oferta de club a mitad de temporada: el hub de la liga nueva abre sin error, la jornada es la del calendario nuevo, y no queda una oferta vieja ni un pedido/objetivo del club anterior.
3. Club de la IA que quiebra con plantilla corta o sin compradores con plata: no se desarma por debajo de `PLANTILLA_MIN_VENDEDOR` y los no vendidos quedan en remate para el user.
4. Objetivo guardado en un save viejo (sin `tope_salarial`/`saldo_minimo`): la pantalla y la evaluación no rompen (se completan al leerlo).
5. Despido por quiebra y despido por objetivo en el mismo cierre: un solo despido pendiente con los dos motivos (usa `marcar_despido`, que ya concatena).

---

### Task 1: Economía más dura (sueldos, ingresos por club, migración)

**Files:**
- Modify: `alpha_football/finanzas.py` (constantes arriba, `presupuesto_medio` queda, nuevas funciones, `procesar_jornada`)
- Modify: `alpha_football/ui/league_screen.py:1097-1104` (hook de contratos)
- Modify: `tests/test_finanzas_v290.py` (nada de lógica; ver Step 4)
- Test: `tests/test_finanzas_v460.py` (nuevo)

**Interfaces:**
- Produces:
  - `finanzas.SALARIO_PCT_VALOR = 0.08`
  - `finanzas.presupuesto_base(equipo, tipo: str, division: int) -> int` (punto medio de la banda según estrellas, sin azar)
  - `finanzas.ingresos_esperados(equipo, tipo: str, division: int) -> int` (patrocinio + taquilla de una temporada con empates)
  - `finanzas.migrar_economia(estado: dict) -> bool` (True si migró; marca `datos_carrera['economia_v2']`)

- [ ] **Step 1: Write the failing test** — crear `tests/test_finanzas_v460.py`:

```python
"""v4.6.0: economía más dura, quiebra del user y de la IA, objetivos financieros, espaldarazo como
deuda y ofertas de clubes durante la temporada."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(46)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# ---------------------------------------------------------------- Task 1: economía
def test_ingresos_por_club():
    e = estado_carrera(); liga = e['liga']
    grande = max(liga.equipos, key=lambda x: x.estrellas); chico = min(liga.equipos, key=lambda x: x.estrellas)
    assert F.presupuesto_base(grande, 'premier', 1) > F.presupuesto_base(chico, 'premier', 1)
    base = F.presupuesto_base(grande, 'premier', 1)
    assert F.ingresos_esperados(grande, 'premier', 1) == int(base * F.PATROCINIO_FRAC) + int(base * F.TAQUILLA_FRAC)
    e['mi_equipo'] = grande
    mov = F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert mov['patrocinio'] == int(base * F.PATROCINIO_FRAC / liga.num_jornadas)
    print("  test_ingresos_por_club: OK")


def test_migracion_una_sola_vez():
    e = estado_carrera(); F.asegurar_contratos(e)
    j = e['mi_equipo'].jugadores[0]; j.salario = 1_000_000
    e['datos_carrera']['contratos_v290'] = True           # save viejo: ya tenía contratos
    assert F.migrar_economia(e) and j.salario == 1_600_000
    assert not F.migrar_economia(e) and j.salario == 1_600_000
    print("  test_migracion_una_sola_vez: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_finanzas_v460.py`
Expected: FAIL con `AttributeError: module 'alpha_football.finanzas' has no attribute 'presupuesto_base'`.

- [ ] **Step 3: Implement** — en `alpha_football/finanzas.py`:

Cambiar la constante:
```python
SALARIO_PCT_VALOR = 0.08        # v4.6.0: salario anual = 8% del valor (antes 5%: nadie quebraba)
FACTOR_MIGRACION_SALARIOS = 0.08 / 0.05
```

Agregar debajo de `presupuesto_medio`:
```python
def presupuesto_base(equipo, tipo: str, division: int) -> int:
    """v4.6.0: presupuesto de referencia del club (punto medio de su banda según estrellas, sin azar)."""
    try:
        from alpha_football.mercado_ia import _rango
        lo, hi = _rango(tipo or 'betplay', int(division or 1))
    except Exception:
        lo, hi = 1_000_000, 5_000_000
    t = max(0.0, min(1.0, (float(getattr(equipo, 'estrellas', 3.0) or 3.0) - 2.0) / 3.0))
    return int(lo + t * (hi - lo))


def ingresos_esperados(equipo, tipo: str, division: int) -> int:
    """v4.6.0: patrocinio + taquilla de una temporada (todos empates): base del tope salarial y de la IA."""
    base = presupuesto_base(equipo, tipo, division)
    return int(base * PATROCINIO_FRAC) + int(base * TAQUILLA_FRAC)


def migrar_economia(estado: dict) -> bool:
    """v4.6.0: saves viejos: los sueldos pasan del 5% al 8% del valor (una sola vez)."""
    dc = estado.setdefault('datos_carrera', {})
    if dc.get('economia_v2'):
        return False
    for eq in _todos_los_equipos(estado):
        for j in getattr(eq, 'jugadores', []) or []:
            if int(getattr(j, 'salario', 0) or 0) > 0:
                j.salario = int(round(j.salario * FACTOR_MIGRACION_SALARIOS / 1000)) * 1000
    dc['economia_v2'] = True
    return True
```

En `procesar_jornada`, reemplazar `medio = presupuesto_medio(liga)` por:
```python
    medio = presupuesto_base(mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1)   # v4.6.0: según el club
```

En `alpha_football/ui/league_screen.py`, reemplazar el bloque `# v2.9.0: contratos para toda la partida` por:
```python
        try:  # v2.9.0: contratos para toda la partida (una vez; saves viejos incluidos)
            dc = estado.setdefault('datos_carrera', {})
            from alpha_football.finanzas import asegurar_contratos, migrar_economia
            if not dc.get('contratos_v290'):
                asegurar_contratos(estado)
                dc['contratos_v290'] = True
                dc['economia_v2'] = True          # v4.6.0: carrera nueva: ya nace con los sueldos nuevos
            else:
                migrar_economia(estado)           # v4.6.0: save viejo: sueldos ×1.6 una sola vez
        except Exception as e_con:
            logger.error(f"Error al asignar contratos: {e_con}")
```

- [ ] **Step 4: Run tests**

Run: `python tests/test_finanzas_v460.py` → `2/2 tests pasaron`.
Run: `python tests/test_finanzas_v290.py` → debe pasar (usa `F.SALARIO_PCT_VALOR`, no el número). Si algún test compara con el presupuesto medio, cambiarlo a `F.presupuesto_base(mi, liga.tipo, liga.division)`.

---

### Task 2: Quiebra del user (4 jornadas, correos, temporada en rojo)

**Files:**
- Modify: `alpha_football/finanzas.py` (`JORNADAS_ROJO_VENTA`, `PUNTOS_QUIEBRA`, `procesar_jornada`, `cierre_temporada`)
- Modify: `alpha_football/directiva.py:cambiar_de_club` (reset `temporadas_en_rojo`)
- Modify: `alpha_football/ui/finanzas_screen.py` (textos del aviso de rojo)
- Modify: `tests/test_finanzas_v290.py` (`test_quiebra_vende_al_mejor_tras_3_jornadas`, `test_fin_de_temporada_contratos_y_quiebra`)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `finanzas.presupuesto_base` (Task 1).
- Produces: `finanzas.JORNADAS_ROJO_VENTA = 4`, `finanzas.PUNTOS_QUIEBRA = 6`; `datos_carrera['temporadas_en_rojo']: int`.

- [ ] **Step 1: Write the failing tests** — agregar a `tests/test_finanzas_v460.py` (antes de `TESTS = ...`):

```python
# ---------------------------------------------------------------- Task 2: quiebra del user
def _asuntos(e):
    return [m['asunto'] for m in e['datos_carrera'].get('correo', [])]


def test_rojo_avisa_y_vende_en_la_4a():
    from alpha_football.market import calcular_valor
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -200_000_000
    estrella = max(mi.jugadores, key=calcular_valor)
    for n in range(1, 4):
        F.procesar_jornada(e, es_local=False, gf=0, gc=0)
        assert estrella in mi.jugadores and e['datos_carrera']['jornadas_en_rojo'] == n
    assert sum(1 for a in _asuntos(e) if 'rojo' in a.lower() or 'negativo' in a.lower()) == 3
    F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert estrella not in mi.jugadores and any('venta forzada' in a.lower() for a in _asuntos(e))
    print("  test_rojo_avisa_y_vende_en_la_4a: OK")


def test_saldo_recuperado_resetea():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -1
    F.procesar_jornada(e, es_local=True, gf=1, gc=0)
    if mi.balance < 0:
        mi.balance = 10_000_000
        F.procesar_jornada(e, es_local=True, gf=1, gc=0)
    assert e['datos_carrera']['jornadas_en_rojo'] == 0
    print("  test_saldo_recuperado_resetea: OK")


def test_temporada_en_rojo_resta_puntos_y_la_2a_despide():
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 3
    mi.balance = -1; mi.puntos = 0
    F.cierre_temporada(e)
    assert mi.puntos == -F.PUNTOS_QUIEBRA and not e.get('despido_pendiente')
    assert e['datos_carrera']['temporadas_en_rojo'] == 1
    mi.balance = -1
    F.cierre_temporada(e)
    assert e['despido_pendiente'] and 'quiebra' in e['despido_pendiente']['motivo'].lower()
    e2 = estado_carrera(); e2['datos_carrera']['temporadas_en_rojo'] = 1; e2['mi_equipo'].balance = 5
    F.cierre_temporada(e2)
    assert e2['datos_carrera']['temporadas_en_rojo'] == 0
    print("  test_temporada_en_rojo_resta_puntos_y_la_2a_despide: OK")
```

- [ ] **Step 2: Run** `python tests/test_finanzas_v460.py` → los 3 nuevos FAIL (vende en la 3ª / despide a la 1ª).

- [ ] **Step 3: Implement** — `alpha_football/finanzas.py`:

```python
JORNADAS_ROJO_VENTA = 4         # v4.6.0: antes 3
PUNTOS_QUIEBRA = 6              # v4.6.0: cerrar la temporada en rojo resta puntos en la siguiente
```

Reemplazar desde `dc = estado.setdefault('datos_carrera', {})` hasta el `return` de `procesar_jornada` por:
```python
    dc = estado.setdefault('datos_carrera', {})
    estado.pop('aviso_finanzas', None)
    from alpha_football import correo as C
    ir = C.accion('finanzas_screen', "VER FINANZAS")
    if mi.balance < 0:
        dc['jornadas_en_rojo'] = n_rojo = int(dc.get('jornadas_en_rojo', 0)) + 1
        if n_rojo >= JORNADAS_ROJO_VENTA:
            dc['jornadas_en_rojo'] = 0
            texto = vender_mejor(estado) or "Quiebra: no se pudo vender a nadie."
            estado['aviso_finanzas'] = texto
            C.enviar(estado, 'directiva', "Venta forzada por deudas",
                     f"{JORNADAS_ROJO_VENTA} jornadas seguidas en rojo. {texto}", ir)
        else:
            faltan = JORNADAS_ROJO_VENTA - n_rojo
            estado['aviso_finanzas'] = aviso = (f"Saldo negativo: en {faltan} jornada{'s' if faltan != 1 else ''} "
                                                f"la directiva venderá a tu mejor jugador")
            C.enviar(estado, 'directiva',
                     "Saldo negativo" if n_rojo == 1 else f"Siguen los números rojos ({n_rojo}/{JORNADAS_ROJO_VENTA})",
                     f"El saldo del club es −${abs(mi.balance) / 1_000_000:.1f}M. {aviso}. "
                     "Vende jugadores o baja la masa salarial para volver a positivo.", ir)
    else:
        if int(dc.get('jornadas_en_rojo', 0) or 0) > 0:
            C.enviar(estado, 'directiva', "Saldo recuperado",
                     "Volviste a números positivos: se cancela la venta forzada.", ir)
        dc['jornadas_en_rojo'] = 0
    return {'patrocinio': patrocinio, 'taquilla': taquilla, 'salarios': salarios}
```

En `cierre_temporada`, reemplazar el bloque final `if mi is not None and mi.balance < 0: ... marcar_despido(...)` por:
```python
    if mi is not None:     # v4.6.0: 1ª temporada en rojo = −6 puntos; 2ª seguida = despido
        dc = estado.setdefault('datos_carrera', {})
        if mi.balance < 0:
            dc['temporadas_en_rojo'] = int(dc.get('temporadas_en_rojo', 0) or 0) + 1
            if dc['temporadas_en_rojo'] >= 2:
                from alpha_football.directiva import marcar_despido
                marcar_despido(estado, f"Quiebra: dos temporadas seguidas en números rojos "
                                       f"(${mi.balance / 1_000_000:.1f}M).")
            else:
                # el cierre corre después del reset de la tabla: los puntos ya son de la temporada nueva
                mi.puntos = int(getattr(mi, 'puntos', 0) or 0) - PUNTOS_QUIEBRA
                from alpha_football import correo as C
                C.enviar(estado, 'directiva', "Temporada cerrada en rojo",
                         f"Cerraste con −${abs(mi.balance) / 1_000_000:.1f}M. La liga te resta {PUNTOS_QUIEBRA} "
                         "puntos esta temporada. Si vuelves a cerrar en rojo, te despedimos.",
                         C.accion('finanzas_screen', "VER FINANZAS"))
        else:
            dc['temporadas_en_rojo'] = 0
```

En `alpha_football/directiva.py:cambiar_de_club`, junto a `dc['jornadas_en_rojo'] = 0`, agregar `dc['temporadas_en_rojo'] = 0`.

En `alpha_football/ui/finanzas_screen.py`, cambiar los 6 textos del aviso de rojo por:
```python
            draw_text(screen, f"¡EN ROJO! {rojo}/{F.JORNADAS_ROJO_VENTA} jornadas.", (x, y + 196), size='sm', color='rojo')
            draw_text(screen, f"Al llegar a {F.JORNADAS_ROJO_VENTA} venden a tu mejor jugador.", (x, y + 220), size='sm', color='rojo')
            draw_text(screen, f"Cerrar así: −{F.PUNTOS_QUIEBRA} pts; 2 temporadas = despido.", (x, y + 244), size='sm', color='rojo')
        else:
            draw_text(screen, "Saldo negativo: no puedes fichar.", (x, y + 196), size='sm', color='azul')
            draw_text(screen, f"{F.JORNADAS_ROJO_VENTA} jornadas en rojo = venta forzada.", (x, y + 220), size='sm', color='azul')
            draw_text(screen, f"Cerrar en rojo: −{F.PUNTOS_QUIEBRA} pts; 2 seguidas = despido.", (x, y + 244), size='sm', color='azul')
```

En `tests/test_finanzas_v290.py`:
- `test_quiebra_vende_al_mejor_tras_3_jornadas`: renombrar a `..._tras_4_jornadas`, `range(2)` → `range(3)`.
- `test_fin_de_temporada_contratos_y_quiebra`: después de `mi.balance = -1; F.cierre_temporada(e)` agregar `assert not e.get('despido_pendiente')` y luego `mi.balance = -1; F.cierre_temporada(e)` antes del assert de quiebra existente. Actualizar la lista `TESTS` si enumera los nombres.

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py` y `python tests/test_finanzas_v290.py` → todos pasan.

---

### Task 3: Quiebra de la IA (cobro/pago, remate, sin fichajes, −6, noticia)

**Files:**
- Modify: `alpha_football/models.py` (`Equipo.sin_fichajes_hasta`, `Jugador.remate` + `from_dict`)
- Modify: `alpha_football/correo.py:16` (remitente `'prensa'`)
- Modify: `alpha_football/mercado_ia.py` (`ingresos_fin_temporada`, `quiebra_ia`, `ronda_fichajes_ia`)
- Modify: `alpha_football/negociacion.py` (`precio_fichaje`, `minimo_club`, `registrar_pase`)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `finanzas.ingresos_esperados`, `finanzas.masa_salarial`, `finanzas.PUNTOS_QUIEBRA`, `market.traspasado_en_ventana`.
- Produces:
  - `mercado_ia.PRECIO_REMATE = 0.60`, `mercado_ia.COLCHON_QUIEBRA_IA = 0.0`
  - `mercado_ia.ingresos_fin_temporada(estado, rng=None) -> list[str]` (nombres de los clubes que quebraron)
  - `mercado_ia.quiebra_ia(estado, eq, rng=None) -> list[tuple]` → `[(jugador, comprador_o_None, precio)]`
  - `Equipo.sin_fichajes_hasta: int = 0`, `Jugador.remate: bool = False`

- [ ] **Step 1: Write the failing tests**:

```python
# ---------------------------------------------------------------- Task 3: quiebra de la IA
def test_quiebra_ia_remata_sanciona_y_avisa():
    from alpha_football import mercado_ia as MI
    e = estado_carrera(); liga = e['liga']
    eq = liga.equipos[5]; eq.puntos = 0
    tops = sorted(eq.jugadores, key=lambda j: -j.overall)[:3]
    for c in liga.equipos:
        c.balance = 10**10
    eq.balance = -10**10
    quebrados = MI.ingresos_fin_temporada(e, random.Random(1))
    assert eq.nombre in quebrados
    assert eq.puntos == -F.PUNTOS_QUIEBRA and eq.sin_fichajes_hasta == e['temporada']
    idos = [j for j in tops if j not in eq.jugadores]
    assert 2 <= len(idos) <= 3
    noticia = next(m for m in e['datos_carrera']['correo'] if m['remitente'] == 'prensa')
    assert eq.nombre in noticia['asunto'] and all(j.apellido in noticia['cuerpo'] for j in idos)
    print("  test_quiebra_ia_remata_sanciona_y_avisa: OK")


def test_ia_sin_fichajes_no_compra():
    from alpha_football import mercado_ia as MI
    e = estado_carrera()
    for eq in e['liga'].equipos:
        eq.balance = 10**10
        eq.sin_fichajes_hasta = e['temporada']
    log = MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    assert not any(eq.nombre in l.split(' ficha a ')[0] for eq in e['liga'].equipos for l in log)
    print("  test_ia_sin_fichajes_no_compra: OK")


def test_remate_sin_comprador_queda_barato_para_el_user():
    from alpha_football import mercado_ia as MI, negociacion as N
    from alpha_football.market import calcular_valor
    e = estado_carrera(); eq = e['liga'].equipos[6]
    for c in e['liga'].equipos:
        c.balance = 0                                  # nadie puede pagar
    eq.balance = -1
    rem = MI.quiebra_ia(e, eq, random.Random(3))
    libres = [j for j, comp, _p in rem if comp is None]
    assert libres and all(j.remate and j in eq.jugadores for j in libres)
    j = libres[0]
    assert N.precio_fichaje(j) == int(calcular_valor(j) * MI.PRECIO_REMATE) or N.precio_fichaje(j) == int(j.valor * MI.PRECIO_REMATE)
    assert N.minimo_club(j, eq) == N.precio_fichaje(j)
    N.registrar_pase(e, j, eq.nombre, 'Otro', 1, False)
    assert not j.remate
    print("  test_remate_sin_comprador_queda_barato_para_el_user: OK")


def test_campos_nuevos_persisten():
    from alpha_football.models import Equipo, Jugador
    e = estado_carrera(); eq = e['liga'].equipos[0]; eq.sin_fichajes_hasta = 3
    j = eq.jugadores[0]; j.remate = True
    eq2 = Equipo.from_dict(eq.to_dict())
    assert eq2.sin_fichajes_hasta == 3 and eq2.jugadores[0].remate
    d = eq.to_dict(); d.pop('sin_fichajes_hasta')
    assert Equipo.from_dict(d).sin_fichajes_hasta == 0
    print("  test_campos_nuevos_persisten: OK")
```

- [ ] **Step 2: Run** → FAIL (`ingresos_fin_temporada` devuelve None, no hay `quiebra_ia`).

- [ ] **Step 3: Implement**

`alpha_football/models.py` — en `Jugador`, después de `ventana_traspaso`:
```python
    remate: bool = False                        # v4.6.0: rematado por un club en quiebra (precio 60%)
```
y en `Jugador.from_dict` junto a `ventana_traspaso=...`:
```python
                remate=bool(datos.get("remate", False)),
```
En `Equipo`, después de `puntos...gc` no: agregar junto a `dt_nombre`:
```python
    sin_fichajes_hasta: int = 0   # v4.6.0: quebró: no ficha hasta terminar esa temporada
```
y en `Equipo.from_dict` (en el `cls(...)`):
```python
                sin_fichajes_hasta=int(datos.get("sin_fichajes_hasta", 0) or 0),
```

`alpha_football/correo.py:16`:
```python
REMITENTES = {'directiva': "Directiva", 'jugador': "Jugador", 'medico': "Cuerpo médico", 'club': "Club",
              'prensa': "Prensa"}   # v4.6.0: noticias (quiebras de la IA)
```

`alpha_football/mercado_ia.py` — constantes junto a `INGRESO_TEMPORADA`:
```python
PRECIO_REMATE = 0.60           # v4.6.0: un club en quiebra remata a sus figuras al 60% del valor
N_REMATE = (2, 3)
COLCHON_QUIEBRA_IA = 0.0       # v4.6.0: quiebra si el rojo supera esta fracción de sus ingresos (calibración)
```
Reemplazar `ingresos_fin_temporada` por:
```python
def ingresos_fin_temporada(estado: dict, rng: Optional[random.Random] = None) -> list:
    """
    v4.6.0: al empezar la temporada cada club de la IA cobra sus ingresos (patrocinio + taquilla,
    como el user) y paga su masa salarial. El que queda en rojo quiebra (quiebra_ia).
    Devuelve los nombres de los clubes que quebraron.
    """
    from alpha_football.finanzas import ingresos_esperados, masa_salarial
    azar = rng or random.Random()
    mi_equipo = estado.get('mi_equipo')
    quebrados = []
    for liga, tipo, division in ligas_de_la_partida(estado):
        for eq in liga.equipos:
            for j in eq.jugadores:
                j.remate = False          # el remate dura hasta la temporada siguiente
            if eq is mi_equipo:
                continue  # el user cobra por jornada (finanzas.procesar_jornada)
            ingreso = ingresos_esperados(eq, tipo, division)
            eq.balance = int(getattr(eq, 'balance', 0) or 0) + ingreso - masa_salarial(eq)
            if eq.balance < -COLCHON_QUIEBRA_IA * ingreso:
                quebrados.append(eq)
    for eq in quebrados:
        try:
            quiebra_ia(estado, eq, azar)
        except Exception as e_q:
            logger.error(f"Quiebra de {getattr(eq, 'nombre', '?')} fallida: {e_q}")
    return [eq.nombre for eq in quebrados]


def quiebra_ia(estado: dict, eq: Any, rng: Optional[random.Random] = None) -> list:
    """v4.6.0: remate de 2-3 figuras al 60%, sin fichajes esta temporada, −6 puntos y noticia."""
    from alpha_football.finanzas import PUNTOS_QUIEBRA
    from alpha_football.market import traspasado_en_ventana, calcular_valor
    azar = rng or random.Random()
    temporada = int(estado.get('temporada', 1) or 1)
    mi_equipo = estado.get('mi_equipo')
    eq.sin_fichajes_hasta = temporada
    eq.puntos = int(getattr(eq, 'puntos', 0) or 0) - PUNTOS_QUIEBRA
    compradores = [(c, t) for liga, t, d in ligas_de_la_partida(estado) if d == 1 for c in liga.equipos
                   if c is not eq and c is not mi_equipo]
    figuras = sorted([j for j in eq.jugadores if not getattr(j, 'prestamo', None)
                      and not traspasado_en_ventana(estado, j)], key=lambda j: -j.overall)
    rematados = []
    for j in figuras[:azar.randint(*N_REMATE)]:
        if len(eq.jugadores) <= PLANTILLA_MIN_VENDEDOR:
            break
        precio = int((int(getattr(j, 'valor', 0) or 0) or calcular_valor(j)) * PRECIO_REMATE)
        pueden = [(c, t) for c, t in compradores
                  if int(getattr(c, 'balance', 0) or 0) >= precio and len(c.jugadores) < PLANTILLA_MAX_IA]
        if not pueden:
            j.remate = True           # nadie pudo pagar: el user lo puede comprar al precio de remate
            rematados.append((j, None, precio))
            continue
        comprador, tipo_c = azar.choice(pueden)
        _traspasar(j, eq, comprador, precio, tipo_c)
        try:
            from alpha_football.negociacion import registrar_pase
            registrar_pase(estado, j, eq.nombre, comprador.nombre, precio, False)
        except Exception as e_h:
            logger.error(f"No se pudo registrar el remate: {e_h}")
        rematados.append((j, comprador, precio))
    try:
        from alpha_football import correo as C
        lineas = [f"{j.nombre_completo} ({j.posicion} {j.overall}) → "
                  + (f"{comp.nombre} por ${p / 1_000_000:.1f}M" if comp is not None
                     else f"sin comprador: disponible por ${p / 1_000_000:.1f}M")
                  for j, comp, p in rematados]
        C.enviar(estado, 'prensa', f"Quiebra en {eq.nombre}",
                 f"{eq.nombre} quebró: pierde {PUNTOS_QUIEBRA} puntos y no podrá fichar esta temporada. "
                 + ("Remató a: " + "; ".join(lineas) + "." if lineas else "No tenía a quién rematar."),
                 C.accion('buscador_screen', "VER BUSCADOR"))
    except Exception as e_c:
        logger.error(f"No se pudo enviar la noticia de la quiebra: {e_c}")
    logger.info(f"Quiebra de la IA: {eq.nombre} ({len(rematados)} rematados)")
    return rematados
```
En `ronda_fichajes_ia`, al principio del `for comprador, tipo_c, div_c in compradores:`:
```python
        if int(getattr(comprador, 'sin_fichajes_hasta', 0) or 0) >= int(estado.get('temporada', 1) or 1):
            continue   # v4.6.0: quebró esta temporada
```

`alpha_football/negociacion.py`:
```python
def precio_fichaje(jugador) -> int:
    try:
        from alpha_football.market import precio_compra, factor_contrato, calcular_valor
        if getattr(jugador, 'remate', False):   # v4.6.0: club en quiebra: 60% del valor
            from alpha_football.mercado_ia import PRECIO_REMATE
            return int((int(getattr(jugador, 'valor', 0) or 0) or calcular_valor(jugador)) * PRECIO_REMATE)
        return int(int(precio_compra(jugador)) * factor_contrato(jugador))   # v3.5.0: último año −25%
    except Exception:
        return int(getattr(jugador, 'valor', 0) or 0)
```
En `minimo_club`, primera línea del cuerpo después del docstring:
```python
    if getattr(jugador, 'remate', False):
        return precio_fichaje(jugador)        # v4.6.0: remate: sin recargo de figura
```
En `registrar_pase`, dentro del `try` y antes de `hist.append(...)`: `jugador.remate = False`.

`alpha_football/ui/resumen_temporada_screen.py:437` ya llama `ingresos_fin_temporada(estado)`: no cambia (ahora devuelve la lista; se ignora).

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py` → todos pasan. `python tests/test_mercado_v440.py` y `python tests/test_mercado_v350.py` → pasan.

---

### Task 4: Objetivos más difíciles y objetivos financieros

**Files:**
- Modify: `alpha_football/directiva.py` (constantes, `definir_objetivo`, `evaluar_temporada`, `texto_evaluacion`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py:201-208` (registro del historial)
- Modify: `tests/test_directiva_v280.py:33-42` (margen 0)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `finanzas.ingresos_esperados`, `finanzas.masa_salarial`.
- Produces:
  - `directiva.TOPE_SALARIAL_PCT = 0.70`, `directiva.SALDO_MIN_PCT = 0.10`
  - `directiva.completar_financieros(estado, obj) -> dict` (llena `tope_salarial` y `saldo_minimo` si faltan)
  - objetivo con claves `'tope_salarial': int`, `'saldo_minimo': int`
  - `evaluar_temporada(...)` devuelve además `'fallos_financieros': list[str]` y `'deuda': int` (0 hasta Task 5)

- [ ] **Step 1: Write the failing tests**:

```python
# ---------------------------------------------------------------- Task 4: objetivos
def _objetivo(e, balance=50_000_000):
    from alpha_football import directiva as D
    e['mi_equipo'].balance = balance
    return D.definir_objetivo(e)


def test_objetivo_sin_margen_y_titulo_con_5():
    from alpha_football import directiva as D
    assert D.objetivo_por_ranking(4, 20, 1, 4)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 8)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=5)[:2] == ('campeon', 1)
    print("  test_objetivo_sin_margen_y_titulo_con_5: OK")


def test_objetivos_financieros_definidos_y_completados():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e)
    liga = e['liga']
    assert obj['tope_salarial'] == int(D.TOPE_SALARIAL_PCT * F.ingresos_esperados(e['mi_equipo'], liga.tipo, liga.division))
    assert obj['saldo_minimo'] == int(D.SALDO_MIN_PCT * 50_000_000)
    viejo = {k: v for k, v in obj.items() if k not in ('tope_salarial', 'saldo_minimo')}
    e['datos_carrera']['objetivo'] = viejo                  # save viejo
    assert 'tope_salarial' in D.definir_objetivo(e) and 'saldo_minimo' in D.definir_objetivo(e)
    print("  test_objetivos_financieros_definidos_y_completados: OK")


def test_fallo_financiero_cuenta_como_fallo():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e)
    obj['tope_salarial'] = 1                                # masa salarial muy por encima
    info = D.evaluar_temporada(e, 1)                        # deportivo superado
    assert info['resultado'] == 'superado' and info['fallos_financieros']
    assert info['veredicto'] == 'regano' and e['datos_carrera']['advertencia_dt']
    e2 = estado_carrera(); obj2 = _objetivo(e2); obj2['tope_salarial'] = 10**12
    e2['mi_equipo'].balance = 0                             # saldo < mínimo (10% de 50M)
    obj2['presupuesto_ref'] = 50_000_000
    assert D.evaluar_temporada(e2, 1)['fallos_financieros']
    print("  test_fallo_financiero_cuenta_como_fallo: OK")
```

Y el aviso de tope salarial a mitad de temporada:
```python
def test_aviso_tope_salarial_una_vez_por_mitad():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e); obj['tope_salarial'] = 1
    e['liga'].jornada_actual = 3
    D.avisar_tope_salarial(e); D.avisar_tope_salarial(e)
    avisos = [m for m in e['datos_carrera']['correo'] if 'tope salarial' in m['asunto'].lower()]
    assert len(avisos) == 1
    e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    D.avisar_tope_salarial(e)
    assert len([m for m in e['datos_carrera']['correo'] if 'tope salarial' in m['asunto'].lower()]) == 2
    print("  test_aviso_tope_salarial_una_vez_por_mitad: OK")
```

- [ ] **Step 2: Run** → FAIL (`('mitad', 5)` / no hay `tope_salarial`).

- [ ] **Step 3: Implement** — `alpha_football/directiva.py`:

```python
MARGEN_OBJETIVO = 0            # v4.6.0: la meta es el ranking por media (antes +1: ~70-85% de cumplimiento)
VENTAJA_PARA_TITULO = 5        # v4.6.0: antes 8
TOPE_SALARIAL_PCT = 0.70       # v4.6.0: la masa salarial no puede pasar el 70% de los ingresos esperados
SALDO_MIN_PCT = 0.10           # v4.6.0: cerrar con al menos el 10% del presupuesto inicial
```
Nueva función (debajo de `_dc`):
```python
def completar_financieros(estado: dict, obj: dict) -> dict:
    """v4.6.0: tope de masa salarial y saldo mínimo del objetivo (también para objetivos de saves viejos)."""
    if not isinstance(obj, dict):
        return obj
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if 'tope_salarial' not in obj and liga is not None and mi is not None:
        from alpha_football.finanzas import ingresos_esperados
        obj['tope_salarial'] = int(TOPE_SALARIAL_PCT * ingresos_esperados(
            mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1))
    if 'saldo_minimo' not in obj:
        obj['saldo_minimo'] = int(SALDO_MIN_PCT * max(0, int(obj.get('presupuesto_ref', 0) or 0)))
    return obj
```
En `definir_objetivo`: `return obj` del objetivo ya guardado → `return completar_financieros(estado, obj)`; y el `return obj` final (objetivo nuevo) → `return completar_financieros(estado, obj)`.

En `evaluar_temporada`, después de la línea `mi.balance = int(getattr(mi, 'balance', 0) or 0) + monto` (dentro del `if mi is not None:`) agregar el bloque de deuda (queda en 0 hasta Task 5) y los financieros, y usar `fallo` en lugar de `resultado == 'fallado'`:
```python
    deuda = 0      # v4.6.0: Task 5 descuenta aquí la deuda del espaldarazo
    completar_financieros(estado, obj)
    fallos_fin = []
    if mi is not None:
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if tope and masa > tope:
            fallos_fin.append(f"masa salarial ${masa / 1_000_000:.1f}M sobre el tope de ${tope / 1_000_000:.1f}M")
        minimo = int(obj.get('saldo_minimo', 0) or 0)
        if int(mi.balance) < minimo:
            fallos_fin.append(f"saldo ${mi.balance / 1_000_000:.1f}M bajo el mínimo de ${minimo / 1_000_000:.1f}M")
    fallo = resultado == 'fallado' or bool(fallos_fin)
```
Luego:
- después de `ajustar_calif(estado, CALIF[resultado])` agregar `if fallos_fin and resultado != 'fallado': ajustar_calif(estado, CALIF['fallado'])`.
- `if resultado == 'fallado':  # v3.1.0: segunda oportunidad...` → `if fallo:`.
- `elif resultado == 'fallado': veredicto = 'regano'` → `elif fallo: veredicto = 'regano'`.
- En el `motivo` del despido: `f"No cumpliste: {obj.get('texto', 'el objetivo')} (terminaste {posicion}º)."` → agregar `+ (f" Finanzas: {'; '.join(fallos_fin)}." if fallos_fin else "")`.
- `info = {...}` agrega `'fallos_financieros': fallos_fin, 'deuda': deuda`.

En `texto_evaluacion`, después de la línea de "Premio/Multa":
```python
    ff = info.get('fallos_financieros') or []
    partes.append("Finanzas: " + ("FALLADO (" + "; ".join(ff) + ")." if ff else "CUMPLIDO."))
    if info.get('deuda'):
        partes.append(f"Se descontó la deuda del espaldarazo: ${info['deuda'] / 1_000_000:.1f}M.")
```

Aviso de tope salarial (nueva función en `directiva.py`, debajo de `completar_financieros`):
```python
def avisar_tope_salarial(estado: dict) -> None:
    """v4.6.0: correo (una vez por mitad de temporada) si la masa salarial pasa el tope."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        obj = definir_objetivo(estado)
        if not obj or liga is None or mi is None:
            return
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        if not tope or masa <= tope:
            return
        mitad = 1 if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 22) or 22) // 2 else 2
        avisos = obj.setdefault('avisos_tope', [])
        if mitad in avisos:
            return
        avisos.append(mitad)
        from alpha_football import correo as C
        C.enviar(estado, 'directiva', "Te pasaste del tope salarial",
                 f"La masa salarial es ${masa / 1_000_000:.1f}M y el tope es ${tope / 1_000_000:.1f}M. "
                 "Si cierras la temporada así, el objetivo cuenta como fallado.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
    except Exception as e:
        logger.error(f"Error al revisar el tope salarial: {e}")
```
Y en `alpha_football/ui/match_screen.py`, justo después de `revisar_pedido(estado)`:
```python
            from alpha_football.directiva import avisar_tope_salarial   # v4.6.0
            avisar_tope_salarial(estado)
```

En `alpha_football/ui/resumen_temporada_screen.py`, dentro del `try` de `evaluar_temporada`, agregar:
```python
                registro['fallos_financieros'] = list(ev_dir.get('fallos_financieros') or [])
```

En `tests/test_directiva_v280.py:37-41` actualizar a margen 0:
```python
    assert D.objetivo_por_ranking(4, 20, 1, 4)[:2] == ('copa', 4)        # v4.6.0: sin margen
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 8)
    assert D.objetivo_por_ranking(15, 20, 1, 4)[:2] == ('salvarse', 18)
    assert D.objetivo_por_ranking(1, 8, 2, 0)[:2] == ('ascenso', 2)
    assert D.objetivo_por_ranking(5, 8, 2, 0)[:2] == ('mitad', 5)
```
y `ventaja=3` sigue dando `('copa', 4)` (3 < 5). Si hay un test que mide el % de cumplimiento en 1000 temporadas, bajar su rango esperado a 0.40-0.70.

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py`, `python tests/test_directiva_v280.py`, `python tests/test_carrera_dt_v320.py` → pasan (si `test_carrera_dt_v320` falla por el margen, ajustar la posición esperada en 1 puesto en ese assert, sin cambiar lógica).

---

### Task 5: Espaldarazo financiero como deuda

**Files:**
- Modify: `alpha_football/directiva.py` (`pedir_espaldarazo`, `evaluar_temporada`)
- Modify: `tests/test_carrera_dt_v320.py:160-163` (dict del espaldarazo)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `evaluar_temporada` con `deuda` y `fallos_fin` (Task 4).
- Produces: `obj['espaldarazo'] = {'pct', 'puestos', 'deuda': int}`; `directiva.deuda_espaldarazo(estado) -> int`.

- [ ] **Step 1: Write the failing test**:

```python
# ---------------------------------------------------------------- Task 5: espaldarazo = deuda
def test_espaldarazo_se_descuenta_al_cierre():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e, balance=40_000_000)
    obj['tope_salarial'] = 10**12; obj['saldo_minimo'] = 0
    e['liga'].jornada_actual = 1
    ok, _ = D.pedir_espaldarazo(e, 0)
    assert ok and D.deuda_espaldarazo(e) == 6_000_000 and e['mi_equipo'].balance == 46_000_000
    info = D.evaluar_temporada(e, 1)
    assert info['deuda'] == 6_000_000
    assert e['mi_equipo'].balance == 46_000_000 + info['monto'] - 6_000_000
    print("  test_espaldarazo_se_descuenta_al_cierre: OK")
```

- [ ] **Step 2: Run** → FAIL (`deuda_espaldarazo` no existe).

- [ ] **Step 3: Implement** — `alpha_football/directiva.py`:

```python
def deuda_espaldarazo(estado: dict) -> int:
    """v4.6.0: lo que se debe a la directiva por el espaldarazo de esta temporada (se paga al cierre)."""
    obj = (_dc(estado).get('objetivo') or {})
    return int((obj.get('espaldarazo') or {}).get('deuda', 0) or 0)
```
En `pedir_espaldarazo`:
- `obj['espaldarazo'] = {'pct': op['pct'], 'puestos': op['puestos']}` → `obj['espaldarazo'] = {'pct': op['pct'], 'puestos': op['puestos'], 'deuda': op['monto']}`
- asunto del correo `"Espaldarazo aprobado"` → `"Espaldarazo financiero aprobado"`; cuerpo: agregar al final `" Ojo: se descuenta de las ganancias del club al cerrar la temporada."`
- mensaje de retorno: `f"Aprobado: +${...}M · nueva meta: puesto {obj['pos_max']} · se devuelve al cierre."`

En `evaluar_temporada`, reemplazar `deuda = 0      # v4.6.0: Task 5 ...` por:
```python
    deuda = int((obj.get('espaldarazo') or {}).get('deuda', 0) or 0)
    if deuda and mi is not None:   # v4.6.0: el espaldarazo se devuelve de las ganancias (puede dejarte en rojo)
        mi.balance = int(mi.balance) - deuda
        try:
            from alpha_football.finanzas import registrar
            registrar(estado, 'directiva', -deuda, int(obj.get('temporada') or estado.get('temporada', 1) or 1))
        except Exception as e:
            logger.error(f"No se pudo registrar la deuda del espaldarazo: {e}")
```
(debe quedar **antes** del cálculo de `fallos_fin`).

En `tests/test_carrera_dt_v320.py:162`:
```python
    assert ok and obj['pos_max'] == 4 and obj['espaldarazo'] == {'pct': 0.30, 'puestos': 2, 'deuda': 12_000_000}
```

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py` y `python tests/test_carrera_dt_v320.py` → pasan.

---

### Task 6: Ofertas de clubes durante la temporada

**Files:**
- Create: `alpha_football/ofertas_dt.py`
- Modify: `alpha_football/ui/match_screen.py:~480` (hook tras `revisar_pedido`)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `directiva.calif_dt`, `directiva.cambiar_de_club`, `directiva._jugadas`, `negociacion.buscar_en_club`.
- Produces (usados por Task 7):
  - `ofertas_dt.MAX_POR_TEMPORADA = 2`, `ofertas_dt.PLAZO = 2`
  - `ofertas_dt.oferta_vigente(estado) -> Optional[dict]` → `{'club_id', 'club', 'liga', 'media', 'temporada', 'vence'}`
  - `ofertas_dt.revisar_jornada(estado, rng=None) -> None`
  - `ofertas_dt.aceptar(estado) -> str` (mensaje)
  - `ofertas_dt.rechazar(estado) -> None`

- [ ] **Step 1: Write the failing tests**:

```python
# ---------------------------------------------------------------- Task 6: ofertas de clubes
class _Siempre(random.Random):
    def random(self):
        return 0.0


def test_oferta_segun_calif_y_maximo_2():
    from alpha_football import ofertas_dt as O, directiva as D
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    inicializar_calendario_liga(liga)
    e['datos_carrera']['calif_dt'] = 80
    D._jugadas = lambda l, m: 3
    O.revisar_jornada(e, _Siempre(1))
    of = O.oferta_vigente(e)
    assert of and of['media'] >= mi.ovr_promedio
    assert any('dirijas' in m['asunto'].lower() or 'quiere' in m['asunto'].lower() for m in e['datos_carrera']['correo'])
    O.rechazar(e); assert O.oferta_vigente(e) is None
    O.revisar_jornada(e, _Siempre(2)); O.rechazar(e)
    O.revisar_jornada(e, _Siempre(3))
    assert O.oferta_vigente(e) is None                         # ya hubo 2 esta temporada
    print("  test_oferta_segun_calif_y_maximo_2: OK")


def test_oferta_vence_y_aceptar_cambia_de_club():
    from alpha_football import ofertas_dt as O, directiva as D
    e = estado_carrera(); liga = e['liga']
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    inicializar_calendario_liga(liga)
    e['datos_carrera']['calif_dt'] = 55
    D._jugadas = lambda l, m: 3
    O.revisar_jornada(e, _Siempre(4))
    assert O.oferta_vigente(e)
    D._jugadas = lambda l, m: 3 + O.PLAZO
    O.revisar_jornada(e, random.Random(5))                    # sin sorteo favorable: solo vence
    assert O.oferta_vigente(e) is None
    D._jugadas = lambda l, m: 4
    e['datos_carrera']['ofertas_dt_temporada'] = [1, 0]
    O.revisar_jornada(e, _Siempre(6))
    of = O.oferta_vigente(e); viejo = e['mi_equipo']
    msg = O.aceptar(e)
    assert e['mi_equipo'] is not viejo and e['mi_equipo'].nombre == of['club'] and of['club'] in msg
    assert O.oferta_vigente(e) is None and e['historial'][-1].get('se_fue')
    assert 'objetivo' not in e['datos_carrera'] and 'pedido' not in e['datos_carrera']
    from alpha_football.ui import league_screen as LS
    pygame.event.clear()
    assert LS.render(screen, e) != 'menu'                     # el hub de la liga nueva abre
    assert e['liga'].jornada_actual >= 1 and any(eq is e['mi_equipo'] for eq in e['liga'].equipos)
    print("  test_oferta_vence_y_aceptar_cambia_de_club: OK")
```
Nota: estos tests reemplazan `D._jugadas`; al final del archivo de tests no importa porque cada test fija su propio valor. Guardar el original al inicio del bloque si otro test posterior lo usa: `_JUGADAS_ORIG = None` no es necesario porque Tasks 7 no usa `_jugadas`.

- [ ] **Step 2: Run** → FAIL (`No module named 'alpha_football.ofertas_dt'`).

- [ ] **Step 3: Implement** — crear `alpha_football/ofertas_dt.py`:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ofertas de otros clubes para que los dirijas (v4.6.0)
Al cerrar cada jornada de liga (menos las 3 últimas) puede llegar una oferta de un club de las
ligas vivas según tu calificación de DT: alta = clubes mejores, media = parecidos, baja = rara vez
y peores. Máximo 2 por temporada, una vigente a la vez, con 2 jornadas para responder.
Aceptar = directiva.cambiar_de_club a mitad de temporada. Sin UI (objetivos_screen la muestra).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

MAX_POR_TEMPORADA = 2
PLAZO = 2                       # jornadas para responder
# (calif mínima, probabilidad por jornada, banda de media relativa a la tuya)
NIVELES = [(70, 0.10, (0.0, 8.0)), (40, 0.07, (-4.0, 4.0)), (0, 0.02, (-12.0, -2.0))]


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def oferta_vigente(estado: dict) -> Optional[dict]:
    of = _dc(estado).get('oferta_dt')
    return of if isinstance(of, dict) else None


def _contador(estado: dict) -> list:
    temporada = int(estado.get('temporada', 1) or 1)
    c = _dc(estado).get('ofertas_dt_temporada')
    if not isinstance(c, list) or len(c) != 2 or int(c[0]) != temporada:
        c = _dc(estado)['ofertas_dt_temporada'] = [temporada, 0]
    return c


def _nivel(calif: int) -> tuple:
    return next((p, banda) for minimo, p, banda in NIVELES if calif >= minimo)


def _candidatos(estado: dict, banda: tuple) -> list:
    mi = estado.get('mi_equipo')
    ovr = float(getattr(mi, 'ovr_promedio', 70) or 70)
    out = []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if eq is mi or getattr(eq, 'id', None) == getattr(mi, 'id', None):
                    continue
                if ovr + banda[0] <= float(getattr(eq, 'ovr_promedio', 0) or 0) <= ovr + banda[1]:
                    out.append((eq, liga))
    return out


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga: vence la oferta vieja y, con suerte, llega una nueva."""
    try:
        from alpha_football import directiva as D, correo as C
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None or estado.get('despido_pendiente'):
            return
        jugadas = D._jugadas(liga, mi)
        of = oferta_vigente(estado)
        if of is not None:
            if jugadas >= int(of.get('vence', 0)):
                _dc(estado).pop('oferta_dt', None)
                C.enviar(estado, 'club', f"Venció la oferta de {of['club']}",
                         "No respondiste a tiempo: el club buscó otro entrenador.")
            return
        cont = _contador(estado)
        n = int(getattr(liga, 'num_jornadas', 22) or 22)
        if cont[1] >= MAX_POR_TEMPORADA or jugadas < 1 or jugadas > n - 3:
            return
        azar = rng or random.Random()
        prob, banda = _nivel(D.calif_dt(estado))
        if azar.random() >= prob:
            return
        cands = _candidatos(estado, banda)
        if not cands:
            return
        club, liga_c = azar.choice(cands)
        cont[1] += 1
        _dc(estado)['oferta_dt'] = {'club_id': club.id, 'club': club.nombre, 'liga': liga_c.nombre,
                                    'media': round(float(club.ovr_promedio), 1),
                                    'temporada': int(estado.get('temporada', 1) or 1), 'vence': jugadas + PLAZO}
        C.enviar(estado, 'club', f"{club.nombre} quiere que lo dirijas",
                 f"{club.nombre} ({liga_c.nombre}, media {club.ovr_promedio:.1f}) te ofrece ser su DT desde ya. "
                 f"Tienes {PLAZO} jornadas para responder en OBJETIVOS.",
                 C.accion('objetivos_screen', "VER OFERTA"))
    except Exception as e:
        logger.error(f"Error al revisar las ofertas de clubes: {e}")


def rechazar(estado: dict) -> None:
    _dc(estado).pop('oferta_dt', None)


def aceptar(estado: dict) -> str:
    """Cambia de club a mitad de temporada. La temporada en el club viejo queda como 'se fue'."""
    from alpha_football import directiva as D
    from alpha_football.negociacion import buscar_en_club
    of = oferta_vigente(estado)
    if of is None:
        return "No hay oferta vigente."
    nuevo, _j = buscar_en_club(estado, of['club_id'], None)
    _dc(estado).pop('oferta_dt', None)
    if nuevo is None:
        return f"{of['club']} ya no está disponible."
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    obj = _dc(estado).get('objetivo') or {}
    orden = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    pos = next((i + 1 for i, e in enumerate(orden) if e is mi), len(orden))
    estado.setdefault('historial', []).append({
        'temporada': int(estado.get('temporada', 1) or 1), 'equipo': mi.nombre, 'pos': pos, 'posicion': pos,
        'pts': mi.puntos, 'puntos': mi.puntos, 'gf': mi.gf, 'gc': mi.gc, 'campeon_liga': '—',
        'libertadores': '—', 'bono_liga': 0, 'bono_copa': 0, 'bono_total': 0,
        'objetivo': obj.get('texto', ''), 'objetivo_resultado': 'se fue', 'directiva_monto': 0,
        'despedido': False, 'se_fue': True})
    D.cambiar_de_club(estado, nuevo)
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', f"Bienvenido a {nuevo.nombre}",
             f"Dejaste {mi.nombre} para dirigir a {nuevo.nombre}. La directiva te fijará un objetivo nuevo.",
             C.accion('objetivos_screen', "VER OBJETIVOS"))
    return f"Ahora diriges a {nuevo.nombre}."
```

En `alpha_football/ui/match_screen.py`, justo después de `revisar_pedido(estado)`:
```python
            from alpha_football.ofertas_dt import revisar_jornada as _ofertas_dt   # v4.6.0
            _ofertas_dt(estado)
```

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py` → pasan. Verificar `buscar_en_club(estado, id, None)` devuelve `(club, None)` (compara `str(j.id) == 'None'`, no encuentra jugador: correcto).

---

### Task 7: Pantalla OBJETIVOS reorganizada (+ ayuda, finanzas)

**Files:**
- Modify: `alpha_football/ui/objetivos_screen.py` (rects, `render`, overlays)
- Modify: `alpha_football/ui/ayuda.py:762-777` (`_ayuda_objetivos`)
- Modify: `alpha_football/ui/finanzas_screen.py` (línea de deuda del espaldarazo)
- Test: `tests/test_finanzas_v460.py`

**Interfaces:**
- Consumes: `directiva.completar_financieros`, `directiva.deuda_espaldarazo`, `finanzas.masa_salarial`, `ofertas_dt.oferta_vigente/aceptar/rechazar`.
- Produces: rects `R_OBJ, R_CONF, R_HIST, R_AYUDA_META, R_ESPALDARAZO, R_OVERLAY, R_REGLAS, R_VER_OFERTA, R_OFERTA, R_OFERTA_ACEPTAR, R_OFERTA_RECHAZAR`; `barra(screen, rect, frac, color)`; `color_barra_tope(frac) -> str`.

- [ ] **Step 1: Write the failing tests**:

```python
# ---------------------------------------------------------------- Task 7: pantalla OBJETIVOS
def _click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_pantalla_objetivos_reglas_y_oferta():
    from alpha_football.ui import objetivos_screen as OS
    from alpha_football import ofertas_dt as O
    e = estado_carrera(); _objetivo(e)
    assert OS.color_barra_tope(0.5) == 'verde' and OS.color_barra_tope(0.9) == 'dorado' and OS.color_barra_tope(1.2) == 'rojo'
    pygame.event.clear(); assert OS.render(screen, e) is None
    _click(OS.R_AYUDA_META.center); OS.render(screen, e)
    assert e.get('objetivos_reglas_abierto')
    _click((5, 5)); OS.render(screen, e)
    assert not e.get('objetivos_reglas_abierto')
    otro = e['liga'].equipos[3]
    e['datos_carrera']['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': e['liga'].nombre,
                                       'media': 70.0, 'temporada': 1, 'vence': 99}
    pygame.event.clear(); OS.render(screen, e)
    _click(OS.R_VER_OFERTA.center); OS.render(screen, e)
    assert e.get('oferta_dt_abierta')
    _click(OS.R_OFERTA_RECHAZAR.center); OS.render(screen, e)
    assert O.oferta_vigente(e) is None and not e.get('oferta_dt_abierta')
    print("  test_pantalla_objetivos_reglas_y_oferta: OK")
```

- [ ] **Step 2: Run** → FAIL (`no attribute 'color_barra_tope'`).

- [ ] **Step 3: Implement** — `alpha_football/ui/objetivos_screen.py`:

Rects (reemplazan los de arriba):
```python
R_OBJ = pygame.Rect(16, 76, 620, 400)
R_CONF = pygame.Rect(648, 76, 616, 400)
R_HIST = pygame.Rect(16, 488, 1248, 208)       # termina en y=696 (barra de atajos)
R_AYUDA_META = pygame.Rect(R_OBJ.right - 56, R_OBJ.y + 40, 36, 36)
R_ESPALDARAZO = pygame.Rect(R_OBJ.x + 20, R_OBJ.bottom - 52, 380, 40)
R_OVERLAY = pygame.Rect(SCREEN_W // 2 - 360, 180, 720, 340)
R_REGLAS = pygame.Rect(SCREEN_W // 2 - 380, 150, 760, 330)
R_VER_OFERTA = pygame.Rect(R_CONF.x + 20, R_CONF.bottom - 52, 220, 40)
R_OFERTA = pygame.Rect(SCREEN_W // 2 - 340, 190, 680, 300)
R_OFERTA_ACEPTAR = pygame.Rect(R_OFERTA.x + 60, R_OFERTA.bottom - 70, 240, 48)
R_OFERTA_RECHAZAR = pygame.Rect(R_OFERTA.right - 300, R_OFERTA.bottom - 70, 240, 48)
```
Helpers:
```python
def color_barra_tope(frac: float) -> str:
    """Verde hasta el 85% del tope, dorado hasta el 100%, rojo por encima."""
    return 'verde' if frac < 0.85 else 'dorado' if frac <= 1.0 else 'rojo'


def barra(screen, rect: pygame.Rect, frac: float, color: str) -> None:
    pygame.draw.rect(screen, (30, 40, 60), rect, border_radius=6)
    lleno = rect.copy(); lleno.width = int(rect.width * max(0.0, min(1.0, frac)))
    pygame.draw.rect(screen, COLORS[color], lleno, border_radius=6)
```
Eventos (en `render`, reemplazar el bucle de eventos). Estados: `espaldarazo_abierto`, `objetivos_reglas_abierto`, `oferta_dt_abierta` (uno a la vez):
```python
        from alpha_football import ofertas_dt as ODT
        oferta = ODT.oferta_vigente(estado)
        reglas = bool(estado.get('objetivos_reglas_abierto'))
        ver_oferta = bool(estado.get('oferta_dt_abierta')) and oferta is not None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            clic = ev.pos if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 else None
            esc = ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)
            if reglas:        # v4.6.0: overlay "?" con las reglas del objetivo
                if esc or clic:
                    estado.pop('objetivos_reglas_abierto', None); reglas = False
                continue
            if ver_oferta:    # v4.6.0: overlay de la oferta de otro club
                if clic and R_OFERTA_ACEPTAR.collidepoint(clic):
                    estado.pop('oferta_dt_abierta', None)
                    estado['espaldarazo_msg'] = ODT.aceptar(estado)
                    return 'league_screen'
                if (clic and R_OFERTA_RECHAZAR.collidepoint(clic)) or esc:
                    if not esc:
                        ODT.rechazar(estado); oferta = None
                    estado.pop('oferta_dt_abierta', None); ver_oferta = False
                continue
            if abierto:       # v3.2.0: overlay del espaldarazo (1/2/3 o clic; ESC cierra)
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    nivel = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[ev.key]
                elif esc:
                    estado.pop('espaldarazo_abierto', None); abierto = False
                elif clic:
                    nivel = next((i for i, r in enumerate(_rects_espaldarazo()) if r.collidepoint(clic)), None)
                continue
            if esc or (clic and _volver().collidepoint(clic)):
                estado.pop('espaldarazo_msg', None)
                return 'league_screen'
            if (clic and R_AYUDA_META.collidepoint(clic)) or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_i):
                estado['objetivos_reglas_abierto'] = reglas = True
            elif clic and R_ESPALDARAZO.collidepoint(clic) and not obj.get('espaldarazo'):
                estado['espaldarazo_abierto'] = abierto = True
            elif clic and oferta is not None and R_VER_OFERTA.collidepoint(clic):
                estado['oferta_dt_abierta'] = ver_oferta = True
```
Panel izquierdo (reemplaza el bloque `# --- Objetivo ---` hasta antes de `# --- Confianza ---`):
```python
        draw_panel(screen, R_OBJ)
        x, y = R_OBJ.x + 20, R_OBJ.y + 14
        draw_text(screen, "OBJETIVOS DE LA TEMPORADA", (x, y), size='sm', color='azul')
        draw_text(screen, obj.get('texto', '—'), (x, y + 26), size='lg', color='dorado')
        draw_button(screen, R_AYUDA_META, "?", R_AYUDA_META.collidepoint(mouse_pos))
        pos = _posicion_actual(liga, mi)
        meta = int(obj.get('pos_max', 99))
        jugado = any(p.jugado for p in getattr(liga, 'calendario', []) or [])
        estado_txt = (f"Vas {pos}º de {len(liga.equipos)}  ·  meta: puesto {meta} o mejor" if jugado
                      else f"La liga aún no empezó  ·  meta: puesto {meta} o mejor")
        draw_text(screen, estado_txt, (x, y + 72), size='md',
                  color='azul' if not jugado else 'verde' if pos <= meta else 'rojo')
        oc = D.definir_objetivo_copa(estado)
        draw_text(screen, (f"INTERNACIONAL: {oc['texto']} · vas: {estado.get('copa_mejor_fase_temp') or 'Fase de liga'}"
                           if oc else "INTERNACIONAL: sin competición esta temporada.")[:74],
                  (x, y + 104), size='sm', color='dorado' if oc else 'azul')
        # v4.6.0: objetivos financieros con barras
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        frac_m = masa / tope if tope else 0.0
        draw_text(screen, f"MASA SALARIAL  {_m(masa)} / tope {_m(tope)}", (x, y + 140), size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 166, R_OBJ.width - 40, 18), frac_m, color_barra_tope(frac_m))
        minimo, saldo = int(obj.get('saldo_minimo', 0) or 0), int(mi.balance)
        frac_s = saldo / minimo if minimo > 0 else (1.0 if saldo >= 0 else 0.0)
        draw_text(screen, f"SALDO  {'−' if saldo < 0 else ''}{_m(saldo)} / mínimo al cierre {_m(minimo)}",
                  (x, y + 196), size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 222, R_OBJ.width - 40, 18), frac_s,
              'verde' if frac_s >= 1.0 else 'dorado' if frac_s >= 0.5 else 'rojo')
        deuda = D.deuda_espaldarazo(estado)
        if deuda:
            draw_text(screen, f"Deuda con la directiva: {_m(deuda)} (se descuenta al cierre)", (x, y + 250),
                      size='sm', color='rojo')
        pedido_esp = bool(obj.get('espaldarazo'))
        draw_button(screen, R_ESPALDARAZO, "ESPALDARAZO YA PEDIDO" if pedido_esp else "PEDIR ESPALDARAZO FINANCIERO",
                    (not pedido_esp) and R_ESPALDARAZO.collidepoint(mouse_pos))
        msg_esp = estado.get('espaldarazo_msg')
        if msg_esp:
            draw_text(screen, msg_esp[:64], (x, R_ESPALDARAZO.y - 26), size='sm',
                      color='verde' if msg_esp.startswith(("Aprobado", "Ahora")) else 'rojo')
```
Panel derecho (reemplaza `# --- Confianza ---` hasta antes de `# --- Historial ---`):
```python
        draw_panel(screen, R_CONF)
        x2, y2 = R_CONF.x + 20, R_CONF.y + 14
        c = D.confianza(estado)
        draw_text(screen, f"CONFIANZA DE LA DIRECTIVA  {c} / 100  ·  {D.texto_confianza(c)}", (x2, y2), size='sm', color='azul')
        barra(screen, pygame.Rect(x2, y2 + 28, R_CONF.width - 40, 22), c / 100,
              'verde' if c >= 70 else 'dorado' if c >= 45 else 'rojo')
        cal = D.calif_dt(estado)
        draw_text(screen, f"CALIFICACIÓN DE DT  {cal} / 100", (x2, y2 + 70), size='sm', color='azul')
        barra(screen, pygame.Rect(x2, y2 + 98, R_CONF.width - 40, 22), cal / 100,
              'verde' if cal >= 70 else 'dorado' if cal >= 40 else 'rojo')
        ped = D.pedido_activo(estado)
        draw_text(screen, (texto_pedido(ped, D._jugadas(liga, mi))[:70] if ped
                           else "Sin pedido activo de la directiva"), (x2, y2 + 142), size='sm', color='dorado')
        if oferta is not None:
            draw_text(screen, f"OFERTA: {oferta['club']} ({oferta['liga']}) quiere que lo dirijas", (x2, y2 + 180),
                      size='sm', color='verde')
            draw_text(screen, f"Responde antes de la jornada {oferta['vence'] + 1}", (x2, y2 + 206), size='sm', color='azul')
            draw_button(screen, R_VER_OFERTA, "VER OFERTA", R_VER_OFERTA.collidepoint(mouse_pos))
```
Historial: en el texto de cada fila, `res.upper()` → `('FALLADO (FINANZAS)' if r.get('fallos_financieros') and res != 'fallado' else res.upper())`; y color `'azul'` si `r.get('se_fue')`. Mostrar `regs[-6:]` (panel más bajo).

Overlays (al final de `render`, antes de `return None`; el del espaldarazo ya existe: cambiar su título a `"PEDIR ESPALDARAZO FINANCIERO"` y su pie a `"Se descuenta de las ganancias al cerrar la temporada.  ·  ESC para cerrar"`):
```python
        if reglas:
            _velo(screen); draw_panel(screen, R_REGLAS)
            pygame.draw.rect(screen, COLORS['dorado'], R_REGLAS, width=2, border_radius=8)
            ref = int(obj.get('presupuesto_ref', 0) or 0)
            filas = [("REGLAS DEL OBJETIVO", 'dorado'),
                     (f"Si lo superas: +{int(D.PREMIO['superado'] * 100)}% del presupuesto inicial (+{_m(ref * D.PREMIO['superado'])})", 'verde'),
                     (f"Si lo cumples: +{int(D.PREMIO['cumplido'] * 100)}% (+{_m(ref * D.PREMIO['cumplido'])})", 'verde'),
                     (f"Si fallas: −{abs(int(D.PREMIO['fallado'] * 100))}% (−{_m(ref * D.PREMIO['fallado'])}) y "
                      + ("TE ECHAN (ya tenías advertencia)" if (estado.get('datos_carrera') or {}).get('advertencia_dt')
                         else "advertencia (segunda oportunidad)"), 'rojo'),
                     ("Descender o quedar 4+ puestos por debajo de la meta = despido directo", 'rojo'),
                     ("Pasar el tope salarial o cerrar bajo el saldo mínimo = objetivo fallado", 'rojo'),
                     (f"Ranking de tu plantilla al empezar: {obj.get('ranking_inicial', '?')}º por media", 'azul'),
                     ("Clic o ESC para cerrar", 'blanco')]
            for i, (t, col) in enumerate(filas):
                draw_text(screen, t, (R_REGLAS.x + 20, R_REGLAS.y + 18 + i * 38), size='md' if i == 0 else 'sm', color=col)
        if ver_oferta:
            _velo(screen); draw_panel(screen, R_OFERTA)
            pygame.draw.rect(screen, COLORS['verde'], R_OFERTA, width=2, border_radius=8)
            draw_text(screen, f"OFERTA DE {oferta['club'].upper()[:26]}", (R_OFERTA.x + 20, R_OFERTA.y + 18), size='lg', color='dorado')
            draw_text(screen, f"{oferta['liga']}  ·  media {oferta['media']}", (R_OFERTA.x + 20, R_OFERTA.y + 70), size='md', color='azul')
            draw_text(screen, "Si aceptas, dejas tu club ahora y la directiva nueva te fija otro objetivo.",
                      (R_OFERTA.x + 20, R_OFERTA.y + 116), size='sm', color='blanco')
            draw_text(screen, "Esta temporada en tu club actual queda en el historial como 'se fue'.",
                      (R_OFERTA.x + 20, R_OFERTA.y + 144), size='sm', color='blanco')
            draw_button(screen, R_OFERTA_ACEPTAR, "ACEPTAR", R_OFERTA_ACEPTAR.collidepoint(mouse_pos))
            draw_button(screen, R_OFERTA_RECHAZAR, "RECHAZAR", R_OFERTA_RECHAZAR.collidepoint(mouse_pos))
```
con el helper:
```python
def _velo(screen) -> None:
    velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))
```
y el overlay del espaldarazo existente usa `_velo(screen)` en lugar de su velo inline.

`alpha_football/ui/ayuda.py` `_ayuda_objetivos`: agregar casos para los overlays nuevos y los rects:
```python
    if estado.get('objetivos_reglas_abierto'):
        return [(O.R_REGLAS, "Reglas", "Premio o multa según cómo termines, y qué cuenta como fallo. Clic o ESC cierra.")]
    if estado.get('oferta_dt_abierta'):
        return [(O.R_OFERTA_ACEPTAR, "Aceptar", "Dejas tu club ahora y diriges al nuevo."),
                (O.R_OFERTA_RECHAZAR, "Rechazar", "Sigues en tu club; la oferta desaparece.")]
    return [
        (O.R_OBJ, "Objetivos", "Meta deportiva, internacional y financieras (tope salarial y saldo mínimo)."),
        (O.R_AYUDA_META, "Reglas", "Qué pasa si superas, cumples o fallas (tecla I)."),
        (O.R_ESPALDARAZO, "Espaldarazo financiero", "Dinero ya a cambio de una meta más alta; se descuenta al cierre."),
        (O.R_CONF, "Directiva", "Confianza, calificación de DT, pedido activo y ofertas de otros clubes."),
        (O.R_HIST, "Historial", "Cómo terminó cada temporada con su objetivo."),
        (O._volver(), "Volver", "Regresa al hub (también ESC)."),
    ]
```
(los niveles del espaldarazo quedan como están, con el texto "se descuenta al cierre").

`alpha_football/ui/finanzas_screen.py`: debajo del "NETO DE LA TEMPORADA", si `D.deuda_espaldarazo(estado)`:
```python
        try:   # v4.6.0: deuda del espaldarazo financiero
            from alpha_football.directiva import deuda_espaldarazo
            deuda = deuda_espaldarazo(estado)
            if deuda:
                draw_text(screen, f"Deuda con la directiva: {_m(deuda)} (se descuenta al cierre)",
                          (lx + 420, ly + 110), size='sm', color='rojo')
        except Exception as e_deuda:
            logger.error(f"No se pudo mostrar la deuda del espaldarazo: {e_deuda}")
```

- [ ] **Step 4: Run** `python tests/test_finanzas_v460.py` y `python tests/test_ayuda_v390.py` → pasan. Captura visual: renderizar `objetivos_screen` con una oferta y el overlay de reglas a PNG en el scratchpad y revisar que nada se pise (textos dentro de sus paneles, barras alineadas).

---

### Task 8: Calibración y suite completa

**Files:**
- Create: `tests/calibrar_finanzas.py` (script manual; no empieza con `test_` para no correr en la suite)
- Modify (si hace falta): constantes `mercado_ia.COLCHON_QUIEBRA_IA`, `finanzas.SALARIO_PCT_VALOR`

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Write the calibration script**:

```python
"""v4.6.0: calibración de la economía (manual). Mide quiebras de la IA por temporada y la plata
de un club del user prudente vs derrochador. Uso: python tests/calibrar_finanzas.py [temporadas]"""
import sys, os, random, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
logging.disable(logging.CRITICAL)
from alpha_football import finanzas as F, mercado_ia as MI
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.models import alineacion_por_defecto

T = int(sys.argv[1]) if len(sys.argv) > 1 else 5
liga = load_league_teams('premier'); mi = liga.equipos[0]; mi.alineacion_activa = alineacion_por_defecto(mi)
primeras, segunda = _ligas_por_division(liga, {}, {})
e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1, 'primera_division': primeras,
     'segunda_division': segunda, 'datos_carrera': {'economia_v2': True}, 'historial': []}
F.asegurar_contratos(e)
MI.asignar_presupuestos_realistas(e, incluir_usuario=False, rng=random.Random(1))
total = 0
for t in range(1, T + 1):
    e['temporada'] = t
    q = MI.ingresos_fin_temporada(e, random.Random(t))
    MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(100 + t))
    for _ in range(3):
        MI.ronda_fichajes_ia(e, 'ventana', random.Random(200 + t))
    total += len(q)
    print(f"T{t}: {len(q)} quiebras IA {q}")
print(f"Promedio: {total / T:.2f} quiebras de la IA por temporada (objetivo ≈ 1)")
for tipo in ('premier', 'laliga', 'brasil', 'argentina', 'betplay'):
    lg = load_league_teams(tipo)
    for eq in (max(lg.equipos, key=lambda x: x.estrellas), min(lg.equipos, key=lambda x: x.estrellas)):
        ing = F.ingresos_esperados(eq, tipo, 1)
        masa = sum(F.contrato_inicial(j, random.Random(0))[0] for j in eq.jugadores)
        print(f"{tipo:9} {eq.nombre[:18]:18} ingresos {ing / 1e6:6.1f}M  sueldos {masa / 1e6:6.1f}M  "
              f"neto {(ing - masa) / 1e6:+6.1f}M  (derrochador +30% masa: {(ing - masa * 1.3) / 1e6:+6.1f}M)")
```

- [ ] **Step 2: Run** `python tests/calibrar_finanzas.py 5`.
Criterios: promedio de quiebras de la IA entre 0.5 y 1.5 por temporada **contando las 10 ligas** (el script usa las ligas que arma `_ligas_por_division`); el "derrochador" (+30% masa) queda negativo en la mayoría de las ligas y el prudente positivo en la mayoría.
- Si las quiebras de la IA son > 1.5: subir `COLCHON_QUIEBRA_IA` (0.1 → 0.2 → 0.3) y repetir.
- Si son < 0.5: bajarlo a 0.0 y, si ya está en 0, no tocar (la IA ficha con fracciones del saldo; ≥ 0 quiebras raras es aceptable según "que no sea común").
- Si el prudente también queda negativo en la mayoría: bajar `SALARIO_PCT_VALOR` a 0.07 y repetir.
Anotar los valores finales en el comentario de cada constante.

- [ ] **Step 3: Run the full suite** (6 lotes en paralelo, como en la sesión):

```bash
ls tests/test_*.py > /tmp/all.txt
for i in 0 1 2 3 4 5; do (awk "NR%6==$i" /tmp/all.txt | while read f; do python "$f" > "/tmp/$(basename $f).log" 2>&1; echo "$(basename $f) exit=$?"; done > /tmp/b$i.txt) & done; wait
cat /tmp/b*.txt | grep -v "exit=0"; echo "OK: $(cat /tmp/b*.txt | grep -c exit=0) / $(wc -l < /tmp/all.txt)"
```
Expected: `OK: N / N`. Si algo falla, leer su `.log`, corregir y repetir el archivo.

- [ ] **Step 4: Actualizar `context.md`** (bitácora "v4.6.0: finanzas, quiebra y objetivos" con constantes finales y lo que falta probar a mano: correos de rojo, noticia de quiebra, oferta de club a mitad de temporada).
