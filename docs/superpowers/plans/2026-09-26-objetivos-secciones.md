# Objetivos por secciones Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pantalla OBJETIVOS en secciones (Local · Internacional · Finanzas · Marca · Juveniles), objetivos nuevos de Marca y Juveniles, y ofertas de otros clubes solo en OFERTAS DT con correos que dicen por qué te quieren.

**Architecture:** La lógica de Marca/Juveniles vive en `directiva.py` junto al objetivo de copa (mismo patrón: dict por temporada en `datos_carrera`, evaluado al cierre, solo calificación). `finanzas.valor_club` centraliza el valor del club. La UI se reorganiza en `objetivos_screen.py`; la oferta de `ofertas_dt` pasa a `ofertas_dt_screen.py`.

**Tech Stack:** Python 3.10, pygame 2.6; tests son scripts (`python tests/x.py`, lista `TESTS`), pantalla dummy.

**Spec:** `docs/superpowers/specs/2026-09-26-objetivos-secciones-design.md`

## Global Constraints

- **Sin commits**: Diego prueba todo al final (no hay pasos de commit).
- Correr tests con `PYTHONIOENCODING=utf-8` (la consola cp1252 rompe los `print` con "→").
- Comentarios en español con prefijo `v4.7.0:`; `try/except` + `logger.error` en todo lo que toque UI/correo, como el resto del código.
- Marca/Juveniles: cumplido **+4**, fallado **−3** de calificación; sin dinero ni despido.
- Marca `valor`: meta = valor del club × **1.10**. Marca `estrella`: meta = round(media plantilla) + **5**.
- Juveniles: edad media ≥ **27.5** → meta = edad media − **1.0** (1 decimal); si no, `partidos_u21` (N = max(10, round(2 × nº_u21 × jornadas / 22))) o `fichar_joven` (≤ **21** años).
- Menor de 21 = `edad < 21`.

## Review Focus

- Cambiar de club a mitad de temporada: Marca/Juveniles se vuelven a fijar para el club nuevo (no heredar `ids_inicio` del viejo).
- Vender al fichaje estrella después de cumplir: el objetivo sigue cumplido (flag `cumplido`).
- Save viejo sin `objetivo_marca`/`objetivo_juveniles`: se crean al primer acceso sin romper la pantalla.
- Plantilla vacía o sin menores de 21: sin divisiones por cero; N mínimo 10.
- Con oferta de `ofertas_dt` y ofertas de banquillo a la vez en OFERTAS DT: filas y botones no se pisan (máx. 4 filas en total).

---

### Task 1: `finanzas.valor_club`

**Files:**
- Modify: `alpha_football/finanzas.py` (agregar función cerca de `masa_salarial`, ~línea 97)
- Modify: `alpha_football/ui/finanzas_screen.py` (bloque "VALOR DEL CLUB")
- Test: `tests/test_objetivos_secciones.py` (crear)

**Interfaces:**
- Produces: `valor_club(equipo) -> int` = suma de `j.valor` de `equipo.jugadores` + `equipo.balance`.

- [ ] **Step 1: Crear el archivo de tests con el primer test**

```python
"""Objetivos por secciones: Marca, Juveniles, ofertas de DT (sesión 2026-09-26)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, directiva as D, finanzas as F
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def test_valor_club():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = 1_000_000
    for j in mi.jugadores:
        j.valor = 2_000_000
    assert F.valor_club(mi) == 2_000_000 * len(mi.jugadores) + 1_000_000
    print("  test_valor_club: OK")


TESTS = [test_valor_club]


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

Run: `PYTHONIOENCODING=utf-8 python tests/test_objetivos_secciones.py`
Expected: FAIL (`module 'alpha_football.finanzas' has no attribute 'valor_club'`)

- [ ] **Step 3: Implementar**

En `finanzas.py`:

```python
def valor_club(equipo) -> int:
    """v4.7.0: valor del club = valor de mercado de la plantilla + saldo."""
    return (sum(int(getattr(j, 'valor', 0) or 0) for j in getattr(equipo, 'jugadores', []) or [])
            + int(getattr(equipo, 'balance', 0) or 0))
```

En `finanzas_screen.py`, reemplazar el cálculo inline:

```python
        # v4.7.0: valor del club = valor de mercado de la plantilla + saldo
        valor = F.valor_club(mi)
        draw_text(screen, "VALOR DEL CLUB", (x, y + 124), size='sm', color='azul')
        draw_text(screen, _m(valor), (x, y + 146), size='lg', color='verde' if valor >= 0 else 'rojo')
        proy_valor = valor - mi.balance + proyeccion
        draw_text(screen, f"Proyección al cierre: {_m(proy_valor)}", (x, y + 184), size='sm',
                  color='verde' if proy_valor >= 0 else 'rojo')
```

- [ ] **Step 4: Correr y ver que pasa** — mismo comando, Expected: `1/1 tests pasaron`.

---

### Task 2: Objetivos de Marca y Juveniles (lógica)

**Files:**
- Modify: `alpha_football/directiva.py` (nueva sección después de `evaluar_objetivo_copa`; `evaluar_temporada`; `texto_evaluacion`; `_correo_objetivos`; `cambiar_de_club`)
- Modify: `alpha_football/ui/match_screen.py:517-521` (revisar cumplidos tras la jornada)
- Test: `tests/test_objetivos_secciones.py`

**Interfaces:**
- Consumes: `finanzas.valor_club(equipo) -> int` (Task 1).
- Produces:
  - `definir_objetivo_marca(estado) -> Optional[dict]` y `definir_objetivo_juveniles(estado) -> Optional[dict]`; dict: `{'temporada', 'club', 'tipo', 'meta', 'texto', 'ids_inicio': list, 'cumplido': bool}` (+ `'edad_inicio'` en `edad`).
  - `progreso_secundario(estado, oc) -> float` (0..1) y `cumplido_secundario(estado, oc) -> bool`.
  - `revisar_objetivos_secundarios(estado) -> None` (marca `cumplido` y avisa por correo una vez).
  - `evaluar_objetivo_secundario(estado, clave, temporada_fin) -> Optional[dict]` → `{'texto', 'resultado'}`; `info['marca']`, `info['juveniles']`.
  - Constantes `CALIF_SECUNDARIO = {'cumplido': 4, 'fallado': -3}`, `EDAD_ALTA = 27.5`.

- [ ] **Step 1: Tests que fallan** (agregar a `tests/test_objetivos_secciones.py` y a `TESTS`)

```python
def _edades(e, edad):
    for j in e['mi_equipo'].jugadores:
        j.edad = edad


def test_marca_valor_y_estrella():
    e = estado_carrera(); mi = e['mi_equipo']
    D._dc(e).pop('objetivo_marca', None)
    rng = random.Random(1)
    om = D.definir_objetivo_marca(e, rng)
    assert om['tipo'] in ('valor', 'estrella')
    if om['tipo'] == 'valor':
        assert om['meta'] == int(F.valor_club(mi) * 1.10)
    else:
        assert om['meta'] == round(mi.ovr_promedio) + 5
    assert D.definir_objetivo_marca(e) is om          # se fija una vez por temporada
    print("  test_marca_valor_y_estrella: OK")


def test_juveniles_edad_alta_y_normal():
    e = estado_carrera(); _edades(e, 30)
    oj = D.definir_objetivo_juveniles(e, random.Random(1))
    assert oj['tipo'] == 'edad' and oj['meta'] == 29.0
    e = estado_carrera(); _edades(e, 24)
    oj = D.definir_objetivo_juveniles(e, random.Random(1))
    assert oj['tipo'] in ('partidos_u21', 'fichar_joven')
    if oj['tipo'] == 'partidos_u21':
        assert oj['meta'] >= 10
    print("  test_juveniles_edad_alta_y_normal: OK")


def test_estrella_se_cumple_con_fichaje_y_queda_cumplido():
    e = estado_carrera(); mi = e['mi_equipo']
    om = D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'estrella', 'meta': 80,
                                      'texto': 'Fichar un jugador de media ≥ 80',
                                      'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    assert not D.cumplido_secundario(e, om)
    nuevo = e['liga'].equipos[3].jugadores[0]
    nuevo.overall = 85
    mi.jugadores.append(nuevo)
    D.revisar_objetivos_secundarios(e)
    assert om['cumplido'] and any('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e))
    mi.jugadores.remove(nuevo)                          # venderlo no borra el cumplido
    D.revisar_objetivos_secundarios(e)
    assert om['cumplido']
    n = sum('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e))
    D.revisar_objetivos_secundarios(e)
    assert sum('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e)) == n   # un solo aviso
    print("  test_estrella_se_cumple_con_fichaje_y_queda_cumplido: OK")


def test_fichar_joven_y_edad_y_partidos():
    e = estado_carrera(); mi = e['mi_equipo']
    ids = [j.id for j in mi.jugadores]
    base = {'temporada': 1, 'club': mi.nombre, 'ids_inicio': ids, 'cumplido': False, 'texto': 'x'}
    joven = e['liga'].equipos[3].jugadores[0]; joven.edad = 19
    oj = dict(base, tipo='fichar_joven', meta=21)
    assert not D.cumplido_secundario(e, oj)
    mi.jugadores.append(joven)
    assert D.cumplido_secundario(e, oj)
    _edades(e, 30)
    oj = dict(base, tipo='edad', meta=29.0, edad_inicio=30.0)
    assert not D.cumplido_secundario(e, oj) and D.progreso_secundario(e, oj) == 0.0
    _edades(e, 28)
    assert D.cumplido_secundario(e, oj) and D.progreso_secundario(e, oj) == 1.0
    for j in mi.jugadores:
        j.edad, j.partidos_jugados = 20, 0
    oj = dict(base, tipo='partidos_u21', meta=10)
    assert D.progreso_secundario(e, oj) == 0.0
    mi.jugadores[0].partidos_jugados = 10
    assert D.cumplido_secundario(e, oj)
    print("  test_fichar_joven_y_edad_y_partidos: OK")


def test_cierre_calificacion_y_correo():
    e = estado_carrera(); mi = e['mi_equipo']
    D.definir_objetivo(e)
    D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'estrella', 'meta': 999,
                                  'texto': 'Fichar un jugador de media ≥ 999', 'ids_inicio': [], 'cumplido': True}
    D._dc(e)['objetivo_juveniles'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'fichar_joven', 'meta': 21,
                                      'texto': 'Fichar un jugador de 21 años o menos',
                                      'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    antes = D.calif_dt(e)
    ev_m = D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)
    ev_j = D.evaluar_objetivo_secundario(e, 'objetivo_juveniles', 1)
    assert ev_m['resultado'] == 'cumplido' and ev_j['resultado'] == 'fallado'
    assert D.calif_dt(e) == antes + 4 - 3
    txt = D.texto_evaluacion({'posicion': 1, 'resultado': 'cumplido', 'texto': 't', 'marca': ev_m, 'juveniles': ev_j})
    assert 'Marca:' in txt and 'Juveniles:' in txt
    print("  test_cierre_calificacion_y_correo: OK")


def test_cambiar_de_club_refija_marca_y_juveniles():
    e = estado_carrera()
    D.definir_objetivo_marca(e); D.definir_objetivo_juveniles(e)
    nuevo = e['liga'].equipos[2]
    D.cambiar_de_club(e, nuevo)
    om = D.definir_objetivo_marca(e)
    assert om['club'] == nuevo.nombre and set(om['ids_inicio']) == {j.id for j in nuevo.jugadores}
    print("  test_cambiar_de_club_refija_marca_y_juveniles: OK")
```

`TESTS = [test_valor_club, test_marca_valor_y_estrella, test_juveniles_edad_alta_y_normal, test_estrella_se_cumple_con_fichaje_y_queda_cumplido, test_fichar_joven_y_edad_y_partidos, test_cierre_calificacion_y_correo, test_cambiar_de_club_refija_marca_y_juveniles]`

- [ ] **Step 2: Correr y ver que fallan** — Expected: FAIL (`no attribute 'definir_objetivo_marca'`).

- [ ] **Step 3: Implementar en `directiva.py`** (después de `evaluar_objetivo_copa`)

```python
# --- v4.7.0: objetivos de Marca y Juveniles (solo calificación, como el internacional) ---
CALIF_SECUNDARIO = {'cumplido': 4, 'fallado': -3}
EDAD_ALTA = 27.5
NOMBRE_SECUNDARIO = {'objetivo_marca': 'Marca', 'objetivo_juveniles': 'Juveniles'}


def _edad_media(equipo) -> float:
    js = getattr(equipo, 'jugadores', []) or []
    return round(sum(int(getattr(j, 'edad', 25) or 25) for j in js) / len(js), 1) if js else 0.0


def _vigente(estado: dict, clave: str) -> Optional[dict]:
    oc = _dc(estado).get(clave)
    mi = estado.get('mi_equipo')
    if (isinstance(oc, dict) and oc.get('temporada') == int(estado.get('temporada', 1) or 1)
            and oc.get('club') == getattr(mi, 'nombre', None)):
        return oc
    return None


def _base_secundario(estado: dict, mi) -> dict:
    return {'temporada': int(estado.get('temporada', 1) or 1), 'club': mi.nombre,
            'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}


def definir_objetivo_marca(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Una meta de marca por temporada: valor del club +10% o fichar una estrella (media +5)."""
    oc = _vigente(estado, 'objetivo_marca')
    if oc is not None:
        return oc
    mi = estado.get('mi_equipo')
    if mi is None:
        return None
    from alpha_football.finanzas import valor_club
    oc = _base_secundario(estado, mi)
    if (rng or random.Random()).random() < 0.5:
        meta = int(valor_club(mi) * 1.10)
        oc.update(tipo='valor', meta=meta, texto=f"Llegar a ${meta / 1_000_000:.1f}M de valor del club")
    else:
        meta = round(float(getattr(mi, 'ovr_promedio', 0) or 0)) + 5
        oc.update(tipo='estrella', meta=meta, texto=f"Fichar un jugador de media {meta} o más")
    _dc(estado)['objetivo_marca'] = oc
    return oc


def definir_objetivo_juveniles(estado: dict, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Edad media alta → bajarla 1 año; si no, partidos de menores de 21 o fichar un joven."""
    oc = _vigente(estado, 'objetivo_juveniles')
    if oc is not None:
        return oc
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None:
        return None
    oc = _base_secundario(estado, mi)
    edad = _edad_media(mi)
    if edad >= EDAD_ALTA:
        meta = round(edad - 1.0, 1)
        oc.update(tipo='edad', meta=meta, edad_inicio=edad, texto=f"Bajar la edad media a {meta} años")
    elif (rng or random.Random()).random() < 0.5:
        n_u21 = sum(1 for j in mi.jugadores if int(getattr(j, 'edad', 25) or 25) < 21)
        jornadas = int(getattr(liga, 'num_jornadas', 22) or 22)
        meta = max(10, round(2 * n_u21 * jornadas / 22))
        oc.update(tipo='partidos_u21', meta=meta, texto=f"Que los menores de 21 sumen {meta} partidos")
    else:
        oc.update(tipo='fichar_joven', meta=21, texto="Fichar un jugador de 21 años o menos")
    _dc(estado)['objetivo_juveniles'] = oc
    return oc


def _nuevos(estado: dict, oc: dict) -> list:
    mi = estado.get('mi_equipo')
    ids = set(oc.get('ids_inicio') or [])
    return [j for j in getattr(mi, 'jugadores', []) or [] if j.id not in ids]


def progreso_secundario(estado: dict, oc: dict) -> float:
    """Fracción 0..1 para la barra de la pantalla."""
    mi = estado.get('mi_equipo')
    if not oc or mi is None:
        return 0.0
    if oc.get('cumplido'):
        return 1.0
    t, meta = oc.get('tipo'), oc.get('meta') or 0
    if t == 'valor':
        from alpha_football.finanzas import valor_club
        f = valor_club(mi) / meta if meta > 0 else 0.0
    elif t == 'estrella':
        f = 1.0 if any(int(j.overall) >= int(meta) for j in _nuevos(estado, oc)) else 0.0
    elif t == 'fichar_joven':
        f = 1.0 if any(int(getattr(j, 'edad', 99)) <= int(meta) for j in _nuevos(estado, oc)) else 0.0
    elif t == 'edad':
        ini = float(oc.get('edad_inicio', meta + 1.0))
        f = (ini - _edad_media(mi)) / (ini - float(meta)) if ini > meta else 1.0
    elif t == 'partidos_u21':
        suma = sum(int(getattr(j, 'partidos_jugados', 0) or 0) for j in mi.jugadores
                   if int(getattr(j, 'edad', 25) or 25) < 21)
        f = suma / meta if meta > 0 else 1.0
    else:
        f = 0.0
    return max(0.0, min(1.0, f))


def cumplido_secundario(estado: dict, oc: dict) -> bool:
    return bool(oc and (oc.get('cumplido') or progreso_secundario(estado, oc) >= 1.0))


def revisar_objetivos_secundarios(estado: dict) -> None:
    """Tras cada jornada: si Marca o Juveniles se cumplen, quedan cumplidos y avisa una vez."""
    for clave in ('objetivo_marca', 'objetivo_juveniles'):
        try:
            oc = (definir_objetivo_marca if clave == 'objetivo_marca' else definir_objetivo_juveniles)(estado)
            if not oc or oc.get('cumplido') or not cumplido_secundario(estado, oc):
                continue
            oc['cumplido'] = True
            if _ya_avisado(estado, clave):
                continue
            from alpha_football import correo as C
            C.enviar(estado, 'directiva', f"Objetivo cumplido: {oc['texto']}",
                     f"Objetivo de {NOMBRE_SECUNDARIO[clave].lower()} cumplido. La directiva le felicita.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
        except Exception as e:
            logger.error(f"Error al revisar el objetivo {clave}: {e}")


def evaluar_objetivo_secundario(estado: dict, clave: str, temporada_fin: int) -> Optional[dict]:
    """Al cierre: cumplido +4 / fallado −3 de calificación (sin dinero ni despido)."""
    oc = _dc(estado).get(clave)
    if not isinstance(oc, dict) or oc.get('temporada') != temporada_fin:
        return None
    resultado = 'cumplido' if cumplido_secundario(estado, oc) else 'fallado'
    ajustar_calif(estado, CALIF_SECUNDARIO[resultado])
    return {'texto': oc.get('texto', ''), 'resultado': resultado}
```

En `evaluar_temporada`, después de `copa_ev = evaluar_objetivo_copa(estado, temporada_fin)`:

```python
    marca_ev = evaluar_objetivo_secundario(estado, 'objetivo_marca', temporada_fin)          # v4.7.0
    juveniles_ev = evaluar_objetivo_secundario(estado, 'objetivo_juveniles', temporada_fin)
```

y en `info = {...}` agregar `'marca': marca_ev, 'juveniles': juveniles_ev,`.

En `texto_evaluacion`, después del bloque `if info.get('copa'):`:

```python
    for clave, nombre in (('marca', 'Marca'), ('juveniles', 'Juveniles')):     # v4.7.0
        ev = info.get(clave)
        if ev:
            partes.append(f"{nombre}: {ev['texto']} → {ev['resultado'].upper()}.")
```

En `_correo_objetivos`, antes de la línea `"Si supera el objetivo deportivo..."`, calcular y agregar:

```python
        om, oj = definir_objetivo_marca(estado), definir_objetivo_juveniles(estado)   # v4.7.0
        extra = (f"Marca: {om['texto']}.\n" if om else "") + (f"Juveniles: {oj['texto']}.\n" if oj else "")
```

e insertar `f"{extra}\n"` en el cuerpo tras la línea de "Saldo mínimo al cierre" (reemplazar ese `\n\n` final por `\n` + `extra` + `\n`).

En `cambiar_de_club`, tras `dc.pop('objetivo', None)`:

```python
    dc.pop('objetivo_marca', None)       # v4.7.0: se vuelven a fijar para el club nuevo
    dc.pop('objetivo_juveniles', None)
```

Verificar que `directiva.py` ya importa `random` (sí, línea 11).

- [ ] **Step 4: Hook tras la jornada** — en `alpha_football/ui/match_screen.py`, justo después del `try` de `revisar_objetivo_liga_asegurado`:

```python
        try:  # v4.7.0: Marca y Juveniles (avisa una vez al cumplirse)
            from alpha_football.directiva import revisar_objetivos_secundarios
            revisar_objetivos_secundarios(estado)
        except Exception as e_sec:
            logger.error(f"Error al revisar Marca/Juveniles: {e_sec}")
```

- [ ] **Step 5: Correr** — Expected: `7/7 tests pasaron`. Correr también `tests/test_carrera_dt_v320.py`, `tests/test_directiva_v280.py`, `tests/test_finanzas_v460.py` (sin regresiones).

---

### Task 3: Ofertas de otros clubes solo en OFERTAS DT, con motivo

**Files:**
- Modify: `alpha_football/ofertas_dt.py:116-120` (texto + enlace), docstring línea 7
- Modify: `alpha_football/entrenadores.py:245-256` (`_ofrecer_al_user` recibe motivo), `:298-301`
- Modify: `alpha_football/ui/ofertas_dt_screen.py` (fila de la oferta de `ofertas_dt` + motivo)
- Modify: `alpha_football/ui/league_screen.py:1012-1017` (badge)
- Test: `tests/test_objetivos_secciones.py`; mover `test_pantalla_objetivos_reglas_y_oferta` y el final de `test_oferta_completa_plazo_y_aceptar_va_al_contrato` en `tests/test_finanzas_v460.py`

**Interfaces:**
- Produces: `ofertas_dt_screen.filas(estado) -> list[dict]` con `{'origen': 'calif'|'banquillo', 'club', 'liga', 'club_id', 'motivo', 'plazo'}` (la de `ofertas_dt` primero; total máx. 4). `rect_aceptar(i)`/`rect_rechazar(i)` sin cambios.

- [ ] **Step 1: Tests que fallan**

```python
def test_correos_de_oferta_dicen_por_que():
    from alpha_football import entrenadores as EN, ofertas_dt as O
    e = estado_carrera(); liga = e['liga']; eq = liga.equipos[3]
    D._dc(e)['calif_dt'] = 62
    EN._ofrecer_al_user(e, eq, liga, "iba 7º y se esperaba 3º")
    m = C.bandeja(e)[0]
    assert 'iba 7º' in m['cuerpo'] and '62/100' in m['cuerpo'] and m['accion']['pantalla'] == 'ofertas_dt_screen'
    assert EN.ofertas_activas(e)[0]['motivo'] == "iba 7º y se esperaba 3º"
    e = estado_carrera(); D.definir_objetivo(e); D._dc(e)['calif_dt'] = 55   # banda de medias parecidas
    orig = D._jugadas
    try:
        D._jugadas = lambda l, m: 3
        azar = random.Random(7); azar.random = lambda: 0.0
        O.revisar_jornada(e, azar)
    finally:
        D._jugadas = orig
    m = C.bandeja(e)[0]
    assert '55/100' in m['cuerpo'] and m['accion']['pantalla'] == 'ofertas_dt_screen'
    print("  test_correos_de_oferta_dicen_por_que: OK")


def test_oferta_por_calif_en_ofertas_dt_screen():
    from alpha_football.ui import ofertas_dt_screen as S
    from alpha_football import ofertas_dt as O
    e = estado_carrera(); D.definir_objetivo(e); otro = e['liga'].equipos[3]
    D._dc(e)['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': e['liga'].nombre,
                             'media': 70.0, 'temporada': 1, 'vence': 99}
    fs = S.filas(e)
    assert fs[0]['origen'] == 'calif' and 'calificación' in fs[0]['motivo'].lower()
    pygame.event.clear(); assert S.render(screen, e) is None
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=S.rect_rechazar(0).center))
    S.render(screen, e)
    assert O.oferta_vigente(e) is None
    D._dc(e)['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': e['liga'].nombre,
                             'media': 70.0, 'temporada': 1, 'vence': 99}
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=S.rect_aceptar(0).center))
    assert S.render(screen, e) == 'contrato_dt_screen' and e.get('contrato_modo') == 'alta'
    print("  test_oferta_por_calif_en_ofertas_dt_screen: OK")
```

Agregar ambos a `TESTS`. Correr: FAIL (`_ofrecer_al_user() takes 3 positional arguments`).

- [ ] **Step 2: `entrenadores.py`**

```python
def _ofrecer_al_user(estado: dict, equipo, liga, motivo: str = "") -> None:
    """El club juega con un interino y te escribe: la oferta dura JORNADAS_OFERTA jornadas."""
    from alpha_football import correo as C
    from alpha_football.directiva import calif_dt
    d = dts(estado)
    rng = random.Random(f"interino-{equipo.id}-{estado.get('temporada', 1)}")
    asignar(estado, equipo, _nuevo(estado, nombre_generado(rng) + " (interino)", 'anchelottismo', 40, interino=True))
    d['ofertas'].append({'club_id': str(equipo.id), 'club': equipo.nombre, 'liga': getattr(liga, 'nombre', ''),
                         'jornadas': JORNADAS_OFERTA, 'temporada': int(estado.get('temporada', 1) or 1),
                         'motivo': motivo})
    # v4.7.0: el correo dice por qué te quieren (despido + tu calificación)
    C.enviar(estado, 'club', f"{equipo.nombre} te quiere como DT",
             f"Tras despedir a nuestro entrenador{f' ({motivo})' if motivo else ''} y en vista de su "
             f"calificación como DT ({calif_dt(estado)}/100), nos complace ofrecerle el banquillo de "
             f"{equipo.nombre} ({getattr(liga, 'nombre', '')}). La oferta tiene una validez de "
             f"{JORNADAS_OFERTA} jornadas; puede responder desde OFERTAS DT.",
             C.accion('ofertas_dt_screen', "VER OFERTA"), firma=f"La Directiva de {equipo.nombre}")
```

En `revisar_jornada`, guardar el motivo y pasarlo:

```python
        motivo = f"iba {posicion(liga, eq)}º y se esperaba {esperado(liga, eq)}º"
        despedir(estado, eq, liga, motivo)
        ...
        if en_banda(estado, eq) and puede_ofrecer_al_user(estado) and azar.random() < PROB_OFERTA_USER:
            _ofrecer_al_user(estado, eq, liga, motivo)
```

(reemplaza la línea `despedir(estado, eq, liga, f"va {posicion(liga, eq)}º y se esperaba {esperado(liga, eq)}º")`).

- [ ] **Step 3: `ofertas_dt.py`** — correo nuevo y docstring ("Sin UI (ofertas_dt_screen la muestra)"):

```python
        mi_nombre = getattr(estado.get('mi_equipo'), 'nombre', 'su club')
        C.enviar(estado, 'club', f"{club.nombre} quiere que lo dirijas",
                 f"Su calificación como DT ({D.calif_dt(estado)}/100) y su trabajo en {mi_nombre} no han pasado "
                 f"desapercibidos. Nos complace ofrecerle la dirección técnica de {club.nombre} ({liga_c.nombre}, "
                 f"media {club.ovr_promedio:.1f}) desde este mismo momento. Dispone de {PLAZO} jornadas para "
                 "responder desde OFERTAS DT.",
                 C.accion('ofertas_dt_screen', "VER OFERTA"), firma=f"La Directiva de {club.nombre}")
```

- [ ] **Step 4: `ofertas_dt_screen.py`** — agregar `filas` y usarla en `render`:

```python
def filas(estado: dict) -> list:
    """v4.7.0: la oferta por calificación (ofertas_dt) primero y luego las de banquillo; máx. 4."""
    out = []
    try:
        from alpha_football import ofertas_dt as ODT
        from alpha_football.directiva import _jugadas
        of = ODT.oferta_vigente(estado)
        if of is not None:
            liga, mi = estado.get('liga'), estado.get('mi_equipo')
            quedan = max(0, int(of.get('vence', 0)) - _jugadas(liga, mi)) if liga is not None and mi is not None else 0
            out.append({'origen': 'calif', 'club': of['club'], 'liga': of.get('liga', ''), 'club_id': of['club_id'],
                        'motivo': "Por tu calificación como DT", 'plazo': quedan})
    except Exception as e:
        logger.error(f"No se pudo leer la oferta por calificación: {e}")
    for o in EN.ofertas_activas(estado):
        out.append({'origen': 'banquillo', 'club': o['club'], 'liga': o.get('liga', ''), 'club_id': o['club_id'],
                    'motivo': "Despidieron a su DT" + (f" ({o['motivo']})" if o.get('motivo') else ""),
                    'plazo': int(o.get('jornadas', 0))})
    return out[:4]
```

En `render`: `ofertas = filas(estado)`. En los clics:

```python
                for i, o in enumerate(ofertas):
                    if rect_aceptar(i).collidepoint(ev.pos):
                        if o['origen'] == 'calif':
                            from alpha_football import ofertas_dt as ODT
                            estado['espaldarazo_msg'] = ODT.aceptar(estado)
                            estado['contrato_modo'] = 'alta'
                            return 'contrato_dt_screen'
                        if EN.aceptar_oferta(estado, o['club_id']) is not None:
                            estado['contrato_modo'] = 'alta'
                            return 'contrato_dt_screen'
                    if rect_rechazar(i).collidepoint(ev.pos):
                        if o['origen'] == 'calif':
                            from alpha_football import ofertas_dt as ODT
                            ODT.rechazar(estado)
                        else:
                            EN.rechazar_oferta(estado, o['club_id'])
                        return None
```

En el dibujo de cada fila: línea `y + 60` igual (liga, media, puesto — usar `EN._club_por_id(estado, o['club_id'])`), motivo en `(r.x + 20, r.y + 86)` color `'dorado'`, y el plazo al lado: `f"Vence en {o['plazo']} jornada{'s' if o['plazo'] != 1 else ''}"` en `(r.x + 560, r.y + 86)` color `'rojo'`. Subtítulo de pantalla sin cambios.

- [ ] **Step 5: Badge del hub** (`league_screen.py`):

```python
        try:  # v3.4.0: badge de OFERTAS DT (v4.7.0: + la oferta por calificación)
            from alpha_football.ui.ofertas_dt_screen import filas as _filas_dt
            n_ofertas_dt = len(_filas_dt(estado))
```

- [ ] **Step 6: Mover tests viejos** en `tests/test_finanzas_v460.py`:
  - `test_pantalla_objetivos_reglas_y_oferta`: borrar desde `otro = e['liga'].equipos[3]` hasta el `assert O.oferta_vigente(e) is None ...` (la oferta ya se cubre en Task 3) y renombrar a `test_pantalla_objetivos_reglas` (también en su `TESTS`).
  - `test_oferta_completa_plazo_y_aceptar_va_al_contrato`: quitar el `assert ... OS.texto_plazo ...`, y reemplazar `e['oferta_dt_abierta'] = True` + clic en `OS.R_OFERTA_ACEPTAR` por:

```python
        from alpha_football.ui import ofertas_dt_screen as S
        pygame.event.clear(); _click(S.rect_aceptar(0).center)
        assert S.render(screen, e) == 'contrato_dt_screen' and e.get('contrato_modo') == 'alta'
```

- [ ] **Step 7: Correr** `tests/test_objetivos_secciones.py` (9/9), `tests/test_finanzas_v460.py`, `tests/test_dts_v340.py`, `tests/test_hub_v240.py`, `tests/test_teclado_v420.py`.

---

### Task 4: Pantalla OBJETIVOS en secciones

**Files:**
- Modify: `alpha_football/ui/objetivos_screen.py` (rects, `render`, quitar historial y oferta)
- Modify: `alpha_football/ui/ayuda.py:778-792` (`_ayuda_objetivos`)
- Modify: `alpha_football/ui/atajos.py:46` (sin cambios de teclas: `"I Reglas · H Ayuda · ESC Volver"` se mantiene)
- Test: `tests/test_objetivos_secciones.py`

**Interfaces:**
- Consumes: `definir_objetivo_marca/juveniles`, `progreso_secundario`, `cumplido_secundario` (Task 2).
- Produces: rects `R_TOP, R_LOCAL, R_INTER, R_FIN, R_MARCA, R_JUV`; se eliminan `R_OBJ, R_CONF, R_HIST, R_VER_OFERTA, R_OFERTA*` y `texto_plazo`.

- [ ] **Step 1: Test que falla**

```python
def test_pantalla_objetivos_por_secciones():
    from alpha_football.ui import objetivos_screen as O
    from alpha_football.ui import ayuda
    e = estado_carrera(); D.definir_objetivo(e)
    textos, orig = [], O.draw_text
    O.draw_text = lambda s, t, *a, **k: textos.append(str(t))
    try:
        pygame.event.clear(); assert O.render(screen, e) is None
    finally:
        O.draw_text = orig
    for s in ("LOCAL", "INTERNACIONAL", "FINANZAS", "MARCA", "JUVENILES", "CALIFICACIÓN DE DT"):
        assert any(s in t for t in textos), s
    assert not any("HISTORIAL" in t for t in textos) and not any("OFERTA" in t for t in textos)
    assert not hasattr(O, 'R_HIST') and not hasattr(O, 'R_VER_OFERTA')
    assert len(ayuda.AYUDA['objetivos_screen'](e)) == 8
    print("  test_pantalla_objetivos_por_secciones: OK")
```

Correr: FAIL.

- [ ] **Step 2: Rects nuevos** (reemplazan `R_OBJ … R_OFERTA_RECHAZAR`; `R_REGLAS` se queda):

```python
# v4.7.0: franja de directiva arriba; fila 1 Local/Internacional/Finanzas; fila 2 Marca/Juveniles
R_TOP = pygame.Rect(16, 76, 1248, 96)
R_LOCAL = pygame.Rect(16, 184, 408, 250)
R_INTER = pygame.Rect(436, 184, 408, 250)
R_FIN = pygame.Rect(856, 184, 408, 250)
R_MARCA = pygame.Rect(16, 446, 616, 250)
R_JUV = pygame.Rect(648, 446, 616, 250)          # termina en y=696 (barra de atajos)
R_AYUDA_META = pygame.Rect(R_LOCAL.right - 56, R_LOCAL.y + 12, 36, 36)
R_REGLAS = pygame.Rect(SCREEN_W // 2 - 380, 150, 760, 330)
```

Borrar `texto_plazo` y el import/uso de `ofertas_dt` (`ODT`, `oferta`, `ver_oferta`) en `render`. El bucle de eventos queda: `reglas` overlay, ESC/VOLVER, clic en `R_AYUDA_META` o tecla I.

- [ ] **Step 3: Dibujo** (reemplaza los bloques "Objetivos de la temporada", "Directiva" e "Historial" y el overlay `ver_oferta`):

```python
        def _titulo(r, t):
            draw_panel(screen, r)
            draw_text(screen, t, (r.x + 20, r.y + 14), size='sm', color='azul')

        # --- Directiva: confianza, calificación y pedido ---
        draw_panel(screen, R_TOP)
        c, cal = D.confianza(estado), D.calif_dt(estado)
        tx, ty, ancho = R_TOP.x + 20, R_TOP.y + 12, 400
        draw_text(screen, f"CONFIANZA  {c}/100 · {D.texto_confianza(c)}", (tx, ty), size='sm', color='azul')
        barra(screen, pygame.Rect(tx, ty + 26, ancho, 18), c / 100, 'verde' if c >= 70 else 'dorado' if c >= 45 else 'rojo')
        draw_text(screen, f"CALIFICACIÓN DE DT  {cal}/100", (tx + 430, ty), size='sm', color='azul')
        barra(screen, pygame.Rect(tx + 430, ty + 26, ancho, 18), cal / 100,
              'verde' if cal >= 70 else 'dorado' if cal >= 40 else 'rojo')
        ped = D.pedido_activo(estado)
        draw_text(screen, (texto_pedido(ped, D._jugadas(liga, mi)) if ped else "Sin pedido de la directiva")[:44],
                  (tx + 860, ty + 14), size='sm', color='dorado')

        # --- Local ---
        _titulo(R_LOCAL, "LOCAL")
        x, y = R_LOCAL.x + 20, R_LOCAL.y + 14
        meta_txt = obj.get('texto', '—')
        ancho_meta = R_AYUDA_META.x - x - 12
        while get_font('md').size(meta_txt)[0] > ancho_meta and len(meta_txt) > 4:
            meta_txt = meta_txt[:-2]
        draw_text(screen, meta_txt, (x, y + 40), size='md', color='dorado')
        draw_button(screen, R_AYUDA_META, "?", R_AYUDA_META.collidepoint(mouse_pos))
        pos, meta = _posicion_actual(liga, mi), int(obj.get('pos_max', 99))
        jugado = any(p.jugado for p in getattr(liga, 'calendario', []) or [])
        draw_text(screen, f"Vas {pos}º de {len(liga.equipos)}" if jugado else "La liga aún no empezó",
                  (x, y + 84), size='md', color='azul' if not jugado else 'verde' if pos <= meta else 'rojo')
        draw_text(screen, f"Meta: puesto {meta} o mejor", (x, y + 118), size='sm', color='blanco')

        # --- Internacional ---
        _titulo(R_INTER, "INTERNACIONAL")
        x = R_INTER.x + 20
        oc = D.definir_objetivo_copa(estado)
        if oc:
            draw_text(screen, oc['texto'][:34], (x, y + 40), size='md', color='dorado')
            draw_text(screen, f"Vas: {estado.get('copa_mejor_fase_temp') or 'Fase de liga'}", (x, y + 84),
                      size='md', color='verde')
        else:
            draw_text(screen, "Sin competición esta temporada.", (x, y + 40), size='sm', color='azul')

        # --- Finanzas ---
        _titulo(R_FIN, "FINANZAS")
        x = R_FIN.x + 20
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        frac_m = masa / tope if tope else 0.0
        draw_text(screen, f"MASA SALARIAL  {_m(masa)} / {_m(tope)}", (x, y + 40), size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 64, R_FIN.width - 40, 18), frac_m, color_barra_tope(frac_m))
        minimo, saldo = int(obj.get('saldo_minimo', 0) or 0), int(mi.balance)
        frac_s = saldo / minimo if minimo > 0 else (1.0 if saldo >= 0 else 0.0)
        draw_text(screen, f"SALDO  {'−' if saldo < 0 else ''}{_m(saldo)} / mín. {_m(minimo)}", (x, y + 96),
                  size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 120, R_FIN.width - 40, 18), frac_s,
              'verde' if frac_s >= 1.0 else 'dorado' if frac_s >= 0.5 else 'rojo')
        deuda = D.deuda_espaldarazo(estado)
        if deuda:
            draw_text(screen, f"Deuda espaldarazo: {_m(deuda)} (al cierre)", (x, y + 152), size='sm', color='rojo')

        # --- Marca y Juveniles ---
        for r, titulo, oc2 in ((R_MARCA, "MARCA", D.definir_objetivo_marca(estado)),
                               (R_JUV, "JUVENILES", D.definir_objetivo_juveniles(estado))):
            _titulo(r, titulo)
            if not oc2:
                continue
            x2 = r.x + 20
            hecho = D.cumplido_secundario(estado, oc2)
            draw_text(screen, oc2['texto'][:52], (x2, r.y + 54), size='md', color='dorado')
            barra(screen, pygame.Rect(x2, r.y + 100, r.width - 40, 18), D.progreso_secundario(estado, oc2),
                  'verde' if hecho else 'dorado')
            draw_text(screen, "CUMPLIDO" if hecho else "EN CURSO", (x2, r.y + 132), size='sm',
                      color='verde' if hecho else 'azul')
            draw_text(screen, f"Cumplir: +{D.CALIF_SECUNDARIO['cumplido']} calificación · fallar: "
                              f"{D.CALIF_SECUNDARIO['fallado']}", (x2, r.y + 200), size='sm', color='blanco')
```

`y` se toma de `R_LOCAL.y + 14` para las tres tarjetas de la fila 1 (misma altura). Actualizar el docstring del módulo: "v4.7.0: secciones Local/Internacional/Finanzas/Marca/Juveniles; sin historial ni ofertas (van en OFERTAS DT)".

- [ ] **Step 4: Ayuda** (`_ayuda_objetivos`):

```python
def _ayuda_objetivos(estado: dict) -> list:
    from alpha_football.ui import objetivos_screen as O
    if estado.get('objetivos_reglas_abierto'):     # v4.6.0
        return [(O.R_REGLAS, "Reglas", "Premio o multa según cómo termines, y qué cuenta como fallo. Clic o ESC cierra.")]
    return [
        (O.R_TOP, "Directiva", "Confianza, calificación de DT y pedido activo de la directiva."),
        (O.R_LOCAL, "Local", "Meta de liga y cómo vas."),
        (O.R_AYUDA_META, "Reglas", "Qué pasa si superas, cumples o fallas (tecla I)."),
        (O.R_INTER, "Internacional", "Meta de copa y fase alcanzada (solo calificación)."),
        (O.R_FIN, "Finanzas", "Tope de masa salarial y saldo mínimo al cierre."),
        (O.R_MARCA, "Marca", "Meta de marca de la temporada: +4 / −3 de calificación."),
        (O.R_JUV, "Juveniles", "Meta de juveniles de la temporada: +4 / −3 de calificación."),
        (O._volver(), "Volver", "Regresa al hub (también ESC)."),
    ]
```

- [ ] **Step 5: Correr** `tests/test_objetivos_secciones.py` (10/10), `tests/test_finanzas_v460.py`, `tests/test_carrera_dt_v320.py`, `tests/test_ux_v360.py`, `tests/test_teclado_v420.py`, `tests/test_directiva_v280.py`.

- [ ] **Step 6: Captura visual** — renderizar `objetivos_screen`, `ofertas_dt_screen` (con oferta por calificación y una de banquillo) y `finanzas_screen` con `SDL_VIDEODRIVER=dummy`, guardar PNG en el scratchpad y revisar que no haya textos pisados ni desbordes.
