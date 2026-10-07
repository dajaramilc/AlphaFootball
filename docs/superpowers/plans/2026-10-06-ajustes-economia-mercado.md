# Ajustes + Economía y mercado (v0.4.11.0, sub-proyectos A y B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Método elegido por Diego: NATIVO** → superpowers:executing-plans, en una sesión nueva con Sonnet 5.5. Sin commits: Diego da el OK final.

**Goal:** Volver al mensaje desde la pantalla que abrió, goles de todas las competiciones, ofertas al DT con piso, objetivos del user un puesto más exigentes, boost de canteranos, mercado solo en inicio e invierno, sin ronda de pretemporada de la IA y presupuesto recalculado cada temporada.

**Architecture:** Cambios acotados sobre flujos que ya existen. La lógica va en los módulos sin UI (`correo`, `competiciones`, `entrenadores`, `directiva`, `desarrollo`, `market`, `prestamos`, `mercado_ia`, `finanzas`) y las pantallas solo leen. Todo estado nuevo vive en `estado` (transitorio) o `datos_carrera` (se guarda solo).

**Tech Stack:** Python 3.10, pygame. Tests = scripts ejecutables (`python tests/test_x.py`) con ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-06-calendario-mercado-actualizador-design.md` (secciones A y B). Los sub-proyectos C, D, E y F tienen plan propio y van después de este.

## Global Constraints

- Versión: **0.4.11.0**. Comentarios nuevos: `# v0.4.11.0`. No reescribir comentarios `# v4.x` viejos.
- **Git: sin commits hasta que Diego lo pida.** Nunca atribuir a Claude ni a una IA en git.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor del cambio.
- Comentarios y textos del juego en español.
- Cada test corre con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` y termina en `N/N tests pasaron`. Hay tests que salen con código 0 aunque impriman `FAIL`: revisar siempre la salida.
- La exigencia extra de objetivos es **solo del user**; `nivel_temporada` sigue con el criterio actual.
- Los factores del presupuesto son los aprobados: salud 0.80 / 0.90 / 1.00 / 1.10 / 1.20, objetivo 1.25 / 1.10 / 0.85, bonos +0.15 liga y +0.20 copa, multiplicador entre 0.60 y 1.75, piso 10% de la base.
- Ventanas de mercado: solo `inicio` (J1–3) e `invierno` (J n/2 a n/2+2).

## Review Focus

1. **Fichaje o venta acordados después del invierno** (ahora cruzan el cambio de temporada) → el jugador no pierde un año de contrato ni queda libre en el cierre, y el traspaso se concreta al abrir la J1 (Task 6).
2. **Préstamo guardado con ventana `'cierre'`** en un save viejo → vuelve en el inicio de la temporada siguiente, sin excepción (Task 6).
3. **Cierre de temporada con el saldo en rojo** → sigue la sanción de siempre y el presupuesto nuevo descuenta la deuda sin quedar bajo el 10% de la base (Task 8).
4. **Historial que no es de este club o de esta temporada** (llegaste a mitad de año, save viejo sin `objetivo_resultado`) → el factor de objetivo vale 1.0, sin excepción (Task 8).
5. **Marca de retorno vieja** (abriste una pantalla desde un mensaje y saliste por otro camino) → VOLVER en esa pantalla, más tarde, va al hub y no al correo (Task 1).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/correo.py` | + `retorno()`: a dónde va la pantalla abierta desde un mensaje |
| `alpha_football/ui/correo_screen.py` | `_ir` deja la marca `volver_notif` |
| `alpha_football/ui/league_screen.py` | ESC en una pestaña abierta desde un mensaje vuelve al correo |
| `main.py` | usa `correo.retorno` en la transición de pantallas |
| `alpha_football/competiciones.py` | + `goles_copa`, `club_de`, `goles_totales` |
| `alpha_football/ui/team_screen.py`, `ficha_jugador.py`, `plantilla_screen.py` | muestran liga + copa |
| `alpha_football/entrenadores.py` | `en_banda` con piso |
| `alpha_football/directiva.py`, `ofertas_dt.py` | `objetivo_por_ranking(..., exigente)` |
| `tests/calibrar_objetivos.py` (nuevo) | medición manual del cumplimiento de objetivos |
| `alpha_football/models.py`, `cantera.py`, `desarrollo.py` | `Jugador.canterano` y su boost |
| `alpha_football/market.py`, `prestamos.py`, `negociacion.py`, `traspasos_pendientes.py` | ventanas sin cierre |
| `alpha_football/mercado_ia.py`, `ui/resumen_temporada_screen.py` | sin ronda de pretemporada; inicio más activo |
| `alpha_football/finanzas.py`, `ui/objetivos_screen.py` | presupuesto por temporada y sus textos |
| `tests/test_ajustes_v0411.py` (nuevo) | tests de A |
| `tests/test_presupuesto_ventanas.py` (nuevo) | tests de B |

Cabecera común de los dos archivos de test nuevos (copiar tal cual al crearlos):

```python
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
```

Pie común (copiar tal cual al final):

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

### Task 1: Volver a la notificación (A1)

**Files:**
- Modify: `alpha_football/correo.py` (función nueva al final)
- Modify: `alpha_football/ui/correo_screen.py:103-106` (`_ir`)
- Modify: `alpha_football/ui/league_screen.py:1119` y `:1208`
- Modify: `main.py:652` (antes del bloque "3. Transicionar")
- Test: `tests/test_ajustes_v0411.py` (nuevo)

**Interfaces:**
- Produces: `correo.retorno(estado: dict, actual: str, siguiente: Optional[str]) -> Optional[str]`; claves transitorias `estado['volver_notif']` (nombre de pantalla) y `estado['volver_notif_tab']` (pestaña del hub).

- [ ] **Step 1: Crear el test con la cabecera común y estos casos**

```python
"""v0.4.11.0: ajustes (volver a la notificación, goles totales, ofertas DT, objetivos, canteranos)."""
# <cabecera común>
from alpha_football import correo as C


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def test_volver_desde_el_destino_regresa_al_correo():
    for salida in ('volver', 'league_screen'):
        e = {'volver_notif': 'finanzas_screen'}
        assert C.retorno(e, 'finanzas_screen', salida) == 'correo_screen'
        assert 'volver_notif' not in e


def test_navegar_mas_adentro_conserva_la_marca():
    e = {'volver_notif': 'plantilla_screen'}
    assert C.retorno(e, 'plantilla_screen', 'negociacion_screen') == 'negociacion_screen'
    assert C.retorno(e, 'negociacion_screen', 'plantilla_screen') == 'plantilla_screen'
    assert e['volver_notif'] == 'plantilla_screen'
    assert C.retorno(e, 'plantilla_screen', 'volver') == 'correo_screen'


def test_marca_vieja_se_borra_al_seguir_desde_el_hub():
    e = {'volver_notif': 'plantilla_screen'}
    assert C.retorno(e, 'league_screen', 'team_screen') == 'team_screen'
    assert 'volver_notif' not in e
    assert C.retorno(e, 'plantilla_screen', 'volver') == 'volver'      # ya no vuelve al correo


def test_sin_marca_o_sin_cambio_no_toca_nada():
    assert C.retorno({}, 'finanzas_screen', 'volver') == 'volver'
    e = {'volver_notif': 'finanzas_screen'}
    assert C.retorno(e, 'finanzas_screen', None) is None and e['volver_notif'] == 'finanzas_screen'


def test_pestana_del_hub_no_se_borra_al_abrir_una_tarjeta():
    e = {'volver_notif': 'league_screen', 'volver_notif_tab': 'negociaciones'}
    assert C.retorno(e, 'league_screen', 'buscador_screen') == 'buscador_screen'
    assert e['volver_notif'] == 'league_screen'


def test_ir_desde_un_mensaje_deja_la_marca():
    from alpha_football.ui import correo_screen as CS
    e = estado_carrera()
    m1 = C.enviar(e, 'club', "a", "b", C.accion('finanzas_screen', "VER FINANZAS"))
    assert CS._ir(e, m1) == 'finanzas_screen' and e['volver_notif'] == 'finanzas_screen'
    m2 = C.enviar(e, 'club', "a", "b", C.accion('negociaciones', "IR A NEGOCIACIONES"))
    assert CS._ir(e, m2) == 'league_screen'
    assert e['volver_notif'] == 'league_screen' and e['volver_notif_tab'] == 'negociaciones'


def test_esc_en_la_pestana_abierta_desde_un_mensaje_vuelve_al_correo():
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    e['datos_carrera']['aviso_mercado_visto'] = [1, 1]     # sin cartel de mercado
    e.update(hub_tab='negociaciones', volver_notif='league_screen', volver_notif_tab='negociaciones')
    pygame.event.clear(); L.render(screen, e)              # primer cuadro: inicializa el hub
    key(pygame.K_ESCAPE)
    assert L.render(screen, e) == 'correo_screen'
    assert 'volver_notif' not in e and e['hub_tab'] == 'inicio'


def test_cambiar_de_pestana_borra_la_marca_del_hub():
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    e['datos_carrera']['aviso_mercado_visto'] = [1, 1]
    e.update(hub_tab='oficina', volver_notif='league_screen', volver_notif_tab='negociaciones')
    pygame.event.clear(); L.render(screen, e)
    assert 'volver_notif' not in e
# <pie común>
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: los 8 en FAIL (`module 'alpha_football.correo' has no attribute 'retorno'`, `KeyError: 'volver_notif'`).

- [ ] **Step 3: `correo.retorno`** — agregar al final de `alpha_football/correo.py`:

```python
def retorno(estado: dict, actual: str, siguiente: Optional[str]) -> Optional[str]:
    """v0.4.11.0: la pantalla abierta desde un mensaje (estado['volver_notif']) vuelve a ese mensaje
    al salir con VOLVER/ESC, en vez de al hub. Devuelve la pantalla a la que hay que ir."""
    marca = estado.get('volver_notif')
    if not marca or not siguiente:
        return siguiente
    if actual == marca and siguiente in ('volver', 'league_screen'):
        estado.pop('volver_notif', None)
        return 'correo_screen'
    # ya estaba en el hub y siguió por otro camino: la marca era de una visita anterior
    if actual == 'league_screen' and marca != 'league_screen' and siguiente != 'correo_screen':
        estado.pop('volver_notif', None)
    return siguiente
```

- [ ] **Step 4: `correo_screen._ir`** — reemplazar las dos últimas líneas de `_ir`:

```python
    from alpha_football.ui.league_screen import _abrir
    return _abrir(estado, acc['pantalla'])
```

por:

```python
    from alpha_football.ui.league_screen import _abrir
    destino = _abrir(estado, acc['pantalla'])
    estado['volver_notif'] = destino            # v0.4.11.0: VOLVER/ESC regresa a este mensaje
    if destino == 'league_screen':              # el destino es una pestaña del hub
        estado['volver_notif_tab'] = estado.get('hub_tab')
    return destino
```

- [ ] **Step 5: `league_screen.render`** — dos cambios.

Justo después de la línea `tab = estado.get('hub_tab') if estado.get('hub_tab') in PESTANAS else 'inicio'`:

```python
        # v0.4.11.0: pestaña abierta desde un mensaje; si ya está en otra, no vuelve al correo
        if estado.get('volver_notif') == 'league_screen' and tab != estado.get('volver_notif_tab'):
            estado.pop('volver_notif', None)
```

Y en el manejo de teclas, reemplazar:

```python
            elif ev.key == pygame.K_ESCAPE:
                if tab != 'inicio':
```

por:

```python
            elif ev.key == pygame.K_ESCAPE:
                if tab != 'inicio' and estado.get('volver_notif') == 'league_screen':   # v0.4.11.0
                    estado.pop('volver_notif', None)
                    tab, bar_foco, foco = 'inicio', 0, 0
                    _guardar_foco()
                    return 'correo_screen'
                if tab != 'inicio':
```

- [ ] **Step 6: `main.py`** — inmediatamente antes del comentario `# 3. Transicionar o salir según la respuesta de la pantalla`:

```python
            # v0.4.11.0: lo que se abrió desde un mensaje vuelve a ese mensaje
            try:
                from alpha_football.correo import retorno as _retorno_notif
                next_screen = _retorno_notif(estado, current_screen, next_screen)
            except Exception as e_ret:
                logger.error(f"Error al resolver el retorno a notificaciones: {e_ret}")
```

- [ ] **Step 7: Correr y ver que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `8/8 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_notificaciones.py; PYTHONIOENCODING=utf-8 python tests/test_teclado_v420.py; PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: los tres terminan en `N/N tests pasaron`.

---

### Task 2: Goles de todas las competiciones (A2)

**Files:**
- Modify: `alpha_football/competiciones.py` (después de `registrar_stats`, línea ~955)
- Modify: `alpha_football/ui/team_screen.py:710`
- Modify: `alpha_football/ui/ficha_jugador.py:101-102`
- Modify: `alpha_football/ui/plantilla_screen.py:444`
- Test: `tests/test_ajustes_v0411.py`

**Interfaces:**
- Produces: `competiciones.goles_copa(estado) -> dict` (`{(club, nombre_completo): goles}`), `competiciones.club_de(estado, jugador) -> str`, `competiciones.goles_totales(estado, jugador, club: Optional[str] = None, indice: Optional[dict] = None) -> int`.

- [ ] **Step 1: Tests** — agregar a `tests/test_ajustes_v0411.py`:

```python
def test_goles_totales_suma_liga_y_copas():
    from alpha_football import competiciones as CP
    e = estado_carrera(); mi = e['mi_equipo']; j = mi.jugadores[0]
    j.goles = 4
    assert CP.goles_totales(e, j) == 4                                 # sin copas: solo liga
    e['datos_carrera']['copas'] = {
        'champions': {'stats': {f"{mi.nombre}|{j.nombre_completo}": {'nombre': j.nombre_completo, 'club': mi.nombre, 'goles': 3},
                                f"Otro|{j.nombre_completo}": {'nombre': j.nombre_completo, 'club': 'Otro', 'goles': 9}}},
        'libertadores': {'stats': {}}}
    assert CP.goles_totales(e, j) == 7                                 # no suma al homónimo de otro club
    assert CP.goles_totales(e, j, mi.nombre, CP.goles_copa(e)) == 7    # con club e índice dados
    assert CP.club_de(e, j) == mi.nombre
    rival = e['liga'].equipos[1]
    assert CP.club_de(e, rival.jugadores[0]) == rival.nombre


def test_goles_totales_con_datos_rotos():
    from alpha_football import competiciones as CP
    e = estado_carrera(); j = e['mi_equipo'].jugadores[0]; j.goles = 2
    e['datos_carrera']['copas'] = {'champions': None, 'libertadores': {'stats': {'x': {'goles': 'n/a'}}}}
    assert CP.goles_totales(e, j) == 2
    assert CP.goles_totales({}, j) == 2
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: los 2 nuevos en FAIL (`no attribute 'goles_totales'`).

- [ ] **Step 3: Helpers** — en `alpha_football/competiciones.py`, después de `registrar_stats`:

```python
def goles_copa(estado: dict) -> dict:
    """v0.4.11.0: {(club, nombre completo): goles} sumando las copas de la temporada en curso."""
    out: dict = {}
    for c in ((estado.get('datos_carrera') or {}).get('copas') or {}).values():
        for s in ((c or {}).get('stats') or {}).values():
            try:
                k = (s.get('club', ''), s.get('nombre', ''))
                out[k] = out.get(k, 0) + int(s.get('goles', 0) or 0)
            except Exception as e_s:
                logger.debug(f"competiciones: fila de goles de copa inválida {s}: {e_s}")
    return out


def club_de(estado: dict, jugador) -> str:
    """v0.4.11.0: nombre del club donde está el jugador ('' si no se encuentra)."""
    mi = estado.get('mi_equipo')
    if mi is not None and any(x is jugador for x in getattr(mi, 'jugadores', []) or []):
        return str(getattr(mi, 'nombre', '') or '')
    ligas = [estado.get('liga')]
    for clave in ('primera_division', 'segunda_division'):
        ligas += list((estado.get(clave) or {}).values())
    for liga in ligas:
        for eq in getattr(liga, 'equipos', []) or []:
            if any(x is jugador for x in getattr(eq, 'jugadores', []) or []):
                return str(getattr(eq, 'nombre', '') or '')
    return ''


def goles_totales(estado: dict, jugador, club: Optional[str] = None, indice: Optional[dict] = None) -> int:
    """v0.4.11.0: goles de liga + copa. `indice` = goles_copa(estado) ya calculado (listas largas)."""
    liga = int(getattr(jugador, 'goles', 0) or 0)
    try:
        idx = indice if indice is not None else goles_copa(estado)
        if not idx:
            return liga
        club = club if club is not None else club_de(estado, jugador)
        return liga + int(idx.get((club, getattr(jugador, 'nombre_completo', '')), 0))
    except Exception as e_g:
        logger.debug(f"competiciones: no se pudieron sumar los goles de copa: {e_g}")
        return liga
```

- [ ] **Step 4: Tarjeta de Dirección de equipo** — en `alpha_football/ui/team_screen.py`, reemplazar en la lista `datos`:

```python
                 ("Goles", getattr(jsel, 'goles', 0)), ("Rasgo", getattr(jsel, 'rasgo', '') or '-'),
```

por:

```python
                 ("Goles", _goles_totales(estado, jsel)), ("Rasgo", getattr(jsel, 'rasgo', '') or '-'),   # v0.4.11.0: liga + copa
```

y agregar, junto a los demás helpers privados del módulo (antes de la función que dibuja la ficha):

```python
def _goles_totales(estado: dict, j) -> int:
    """v0.4.11.0: goles de todas las competiciones para la tarjeta del jugador."""
    try:
        from alpha_football.competiciones import goles_totales
        return goles_totales(estado, j, getattr(estado.get('mi_equipo'), 'nombre', None))
    except Exception as e:
        logger.error(f"No se pudieron sumar los goles de copa: {e}")
        return int(getattr(j, 'goles', 0) or 0)
```

- [ ] **Step 5: Ficha compartida** — en `alpha_football/ui/ficha_jugador.py`, reemplazar:

```python
        stats = f"PJ {j.partidos_jugados}  ·  Goles {j.goles}  ·  Asist. {getattr(j, 'asistencias', 0)}  ·  Nota {nota:.1f}"
```

por:

```python
        goles = j.goles
        try:   # v0.4.11.0: liga + copa (la ficha no recibe el estado: usa el de la partida activa)
            from alpha_football import market as _mk, competiciones as _cp
            goles = _cp.goles_totales(_mk.ACTIVE_ESTADO or {}, j)
        except Exception:
            pass
        stats = f"PJ {j.partidos_jugados}  ·  Goles {goles}  ·  Asist. {getattr(j, 'asistencias', 0)}  ·  Nota {nota:.1f}"
```

- [ ] **Step 6: Columna de PLANTILLA** — en `alpha_football/ui/plantilla_screen.py`, reemplazar `f"{j.goles}/{getattr(j, 'asistencias', 0)}"` por `f"{_goles(j)}/{getattr(j, 'asistencias', 0)}"` y, antes del bucle que arma `valores` (misma función, fuera del `for` de jugadores), agregar:

```python
            try:   # v0.4.11.0: goles de liga + copa, con el índice calculado una vez por cuadro
                from alpha_football import competiciones as _cp
                _idx_goles, _club = _cp.goles_copa(estado), getattr(estado.get('mi_equipo'), 'nombre', '')
                _goles = lambda jj: _cp.goles_totales(estado, jj, _club, _idx_goles)
            except Exception:
                _goles = lambda jj: jj.goles
```

Si el orden por la columna de goles usa `j.goles` (buscar `goles` en el mismo archivo), dejarlo igual: ordena por liga.

- [ ] **Step 7: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `10/10 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_plantilla_v260.py; PYTHONIOENCODING=utf-8 python tests/test_ui_v235.py`
Expected: ambos en `N/N tests pasaron`.

---

### Task 3: Ofertas al DT con piso (A3)

**Files:**
- Modify: `alpha_football/entrenadores.py:245-253` (`en_banda`)
- Test: `tests/test_ajustes_v0411.py`; revisar `tests/test_dts_v340.py:163-168`

**Interfaces:**
- Produces: `entrenadores.BANDAS_OFERTA` y `en_banda(estado, equipo) -> bool` con piso.

- [ ] **Step 1: Tests** — agregar:

```python
def test_en_banda_tiene_piso():
    from alpha_football import entrenadores as EN
    e = estado_carrera(); mi = e['mi_equipo']

    class Club:
        pass
    q = Club()
    for calif, dentro, fuera in ((75, (-2, 0, 10), (-3, 11, -20)),
                                 (60, (-4, 0, 5), (-5, 6, -20)),
                                 (30, (-6, -3, 0), (-7, 1, -20))):
        e['datos_carrera']['calif_dt'] = calif
        for d in dentro:
            q.ovr_promedio = mi.ovr_promedio + d
            assert EN.en_banda(e, q), (calif, d)
        for d in fuera:
            q.ovr_promedio = mi.ovr_promedio + d
            assert not EN.en_banda(e, q), (calif, d)
```

- [ ] **Step 2: Correr y ver que falla** (los casos `-20`, `-3`, `-5`, `-7` entran hoy).

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `test_en_banda_tiene_piso: FAIL`.

- [ ] **Step 3: Implementar** — reemplazar `en_banda` entera:

```python
# v0.4.11.0: (calificación mínima, piso, techo) de media respecto de la tuya. Antes solo había
# techo y cualquier club más flojo podía ofrecerte el banquillo.
BANDAS_OFERTA = ((70, -2, 10), (55, -4, 5), (0, -6, 0))


def en_banda(estado: dict, equipo) -> bool:
    """¿El club está a tu alcance según tu calificación? (≥70: −2 a +10 · ≥55: −4 a +5 · resto: −6 a 0)."""
    from alpha_football.directiva import calif_dt
    mi = estado.get('mi_equipo')
    if mi is None:
        return False
    c, ovr, suyo = calif_dt(estado), mi.ovr_promedio, getattr(equipo, 'ovr_promedio', 0)
    piso, techo = next((p, t) for minimo, p, t in BANDAS_OFERTA if c >= minimo)
    return ovr + piso <= suyo <= ovr + techo
```

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `11/11 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_dts_v340.py`
Expected: `N/N tests pasaron`. Si `test_oferta_al_user_y_vencimiento` falla en `assert EN.en_banda(e, club)` (el mejor rival quedó más de 2 por debajo del user), cambiar en ese test la línea que elige `club` por el rival más parecido:

```python
    club = min((x for x in liga.equipos if x is not e['mi_equipo']),
               key=lambda x: abs(x.ovr_promedio - e['mi_equipo'].ovr_promedio))
```

---

### Task 4: Objetivos más exigentes para el user (A4)

**Files:**
- Modify: `alpha_football/directiva.py:29-55` (constantes y `objetivo_por_ranking`) y `:146`
- Modify: `alpha_football/ofertas_dt.py:70`
- Create: `tests/calibrar_objetivos.py`
- Test: `tests/test_ajustes_v0411.py`

**Interfaces:**
- Produces: `directiva.objetivo_por_ranking(r, n, division, cupo, ventaja=0.0, exigente=False) -> tuple`; constantes `PUESTO_EXTRA_USER`, `VENTAJA_TITULO_USER`, `EXIGENTE_SOLO_MITAD_ALTA`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_objetivo_exigente_solo_con_el_parametro():
    from alpha_football import directiva as D
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 8)                       # IA: como antes
    assert D.objetivo_por_ranking(8, 20, 1, 4, exigente=True)[:2] == ('mitad', 7)
    assert D.objetivo_por_ranking(5, 20, 1, 4, exigente=True)[:2] == ('copa', 4)          # 5º por media: copa
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=3)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=3, exigente=True)[:2] == ('campeon', 1)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=2, exigente=True)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(3, 12, 2, 0, exigente=True)[:2] == ('ascenso', 2)
    assert D.objetivo_por_ranking(1, 12, 1, 3, exigente=True)[1] >= 1                     # nunca bajo el 1º


def test_el_objetivo_del_user_es_el_exigente():
    from alpha_football import directiva as D
    from alpha_football.ui.copa_screen import cupos_copa
    e = estado_carrera('premier', 5); liga, mi = e['liga'], e['mi_equipo']
    obj = D.definir_objetivo(e)
    rk = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)
    r = next(i + 1 for i, x in enumerate(rk) if x is mi)
    esperado = D.objetivo_por_ranking(r, len(rk), 1, cupos_copa('premier'),
                                      rk[0].ovr_promedio - rk[1].ovr_promedio, exigente=True)
    assert (obj['tipo'], obj['pos_max']) == esperado[:2]
```

- [ ] **Step 2: Correr y ver que falla** (`unexpected keyword argument 'exigente'`).

- [ ] **Step 3: Implementar** — en `alpha_football/directiva.py`, después de la línea de `MARGEN_MASA_INICIAL`:

```python
PUESTO_EXTRA_USER = 1          # v0.4.11.0: al user se le pide un puesto más que su ranking por media
VENTAJA_TITULO_USER = 3        # v0.4.11.0: y el título con 3+ de media sobre el 2º
EXIGENTE_SOLO_MITAD_ALTA = False   # v0.4.11.0: ver tests/calibrar_objetivos.py
```

Cambiar la firma y el arranque de `objetivo_por_ranking` (el resto del cuerpo no cambia, salvo la comparación del título):

```python
def objetivo_por_ranking(r: int, n: int, division: int, cupo: int, ventaja: float = 0.0,
                         exigente: bool = False) -> tuple:
```

Reemplazar `meta = min(n, r + MARGEN_OBJETIVO)` por:

```python
    meta = min(n, r + MARGEN_OBJETIVO)
    ventaja_titulo = VENTAJA_PARA_TITULO
    if exigente:                       # v0.4.11.0: solo el user como DT (la IA sigue como antes)
        ventaja_titulo = VENTAJA_TITULO_USER
        if not EXIGENTE_SOLO_MITAD_ALTA or r <= n // 2:
            meta = max(1, meta - PUESTO_EXTRA_USER)
```

y `if r == 1 and ventaja >= VENTAJA_PARA_TITULO:` por `if r == 1 and ventaja >= ventaja_titulo:`.

En `definir_objetivo` (línea 146): `objetivo_por_ranking(r, len(ranking), division, cupo, ventaja, exigente=True)`.
En `ofertas_dt._objetivo_de` (línea 70): agregar `, exigente=True` como último argumento de `D.objetivo_por_ranking(...)`.
`nivel_temporada.py:149` **no se toca**.

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `13/13 tests pasaron`.

- [ ] **Step 5: Script de calibración** — crear `tests/calibrar_objetivos.py`:

```python
"""v0.4.11.0: calibración de los objetivos del user (manual). Simula temporadas completas de una liga
y mide cuántas veces un club cumple su meta con el criterio de la IA y con el exigente del user.
Uso: python tests/calibrar_objetivos.py [temporadas] [liga]"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
logging.disable(logging.CRITICAL)
from alpha_football import directiva as D
from alpha_football.ui.menu import load_league_teams
from alpha_football.ui.league_screen import _simular_jornada_liga_fondo
from alpha_football.ui.copa_screen import cupos_copa

T = int(sys.argv[1]) if len(sys.argv) > 1 else 60
tipo = sys.argv[2] if len(sys.argv) > 2 else 'premier'
cumple = {False: 0, True: 0}
total = 0
for _ in range(T):
    liga = load_league_teams(tipo)
    assert all(eq.pj == 0 for eq in liga.equipos), "load_league_teams devolvió una liga ya jugada"
    rk = sorted(liga.equipos, key=lambda e: -e.ovr_promedio)
    ventaja = rk[0].ovr_promedio - rk[1].ovr_promedio
    metas = {eq.id: {ex: D.objetivo_por_ranking(r, len(rk), 1, cupos_copa(tipo), ventaja, exigente=ex)[1]
                     for ex in (False, True)} for r, eq in enumerate(rk, 1)}
    while _simular_jornada_liga_fondo(liga):
        pass
    tabla = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    for pos, eq in enumerate(tabla, 1):
        total += 1
        for ex in (False, True):
            cumple[ex] += pos <= metas[eq.id][ex]
antes, ahora = 100 * cumple[False] / total, 100 * cumple[True] / total
print(f"{tipo}: {T} temporadas, {total} clubes-temporada")
print(f"Cumplimiento con el criterio de la IA: {antes:.1f}%  ·  exigente (user): {ahora:.1f}%  ·  caída: {antes - ahora:.1f} puntos")
print("Objetivo: caída entre 10 y 15 puntos.")
```

- [ ] **Step 6: Medir y fijar el criterio**

Run: `PYTHONIOENCODING=utf-8 python tests/calibrar_objetivos.py 60 premier` y luego `... 60 betplay`.
- Si la caída queda entre 10 y 15 puntos en las dos (o por debajo de 10): dejar `EXIGENTE_SOLO_MITAD_ALTA = False`.
- Si pasa de 15 en alguna: poner `EXIGENTE_SOLO_MITAD_ALTA = True`, volver a medir y anotar las dos mediciones.
- Anotar los números medidos en el comentario de la constante (`# medido: premier X→Y, betplay X→Y`).

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py; PYTHONIOENCODING=utf-8 python tests/test_directiva_v280.py; PYTHONIOENCODING=utf-8 python tests/test_finanzas_v460.py; PYTHONIOENCODING=utf-8 python tests/test_objetivos_secciones.py`
Expected: todos en `N/N tests pasaron`. Si alguno comparaba `definir_objetivo` con `objetivo_por_ranking(...)` sin `exigente`, agregar `exigente=True` a esa comparación del test.

---

### Task 5: Boost de canteranos (A5)

**Files:**
- Modify: `alpha_football/models.py:107` (campo) y `:292` (`from_dict`)
- Modify: `alpha_football/cantera.py:225` (`subir`)
- Modify: `alpha_football/desarrollo.py:24` (helper) y `:198`
- Modify: `alpha_football/ui/ficha_jugador.py:108`
- Test: `tests/test_ajustes_v0411.py`

**Interfaces:**
- Produces: `Jugador.canterano: str` (nombre del club que lo formó; `''` = no es canterano), `desarrollo.factor_canterano(j, equipo) -> float`, constantes `BOOST_CANTERANO = 1.5`, `EDAD_BOOST_CANTERANO = 23`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_canterano_se_guarda():
    from alpha_football.models import Jugador
    j = Jugador(nombre="A", apellido="B", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    assert j.canterano == ''
    j.canterano = 'Club X'
    assert Jugador.from_dict(j.to_dict()).canterano == 'Club X'
    viejo = j.to_dict(); viejo.pop('canterano', None)                              # save viejo: sin el campo
    assert Jugador.from_dict(viejo).canterano == ''


def test_subir_de_la_cantera_marca_al_canterano():
    from alpha_football import cantera as CA
    e = estado_carrera(); mi = e['mi_equipo']
    jid = CA.cantera(e)[0].id
    ok, _msg = CA.subir(e, jid)
    assert ok
    assert next(x for x in mi.jugadores if x.id == jid).canterano == mi.nombre


def test_factor_canterano():
    from alpha_football import desarrollo as DS
    from alpha_football.models import Jugador
    e = estado_carrera(); mi, otro = e['mi_equipo'], e['liga'].equipos[1]
    j = Jugador(nombre="A", apellido="B", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    j.edad = 19
    assert DS.factor_canterano(j, mi) == 1.0                    # no es canterano
    j.canterano = mi.nombre
    assert DS.factor_canterano(j, mi) == DS.BOOST_CANTERANO == 1.5
    assert DS.factor_canterano(j, otro) == 1.0                  # vendido o cedido: se apaga
    j.edad = DS.EDAD_BOOST_CANTERANO
    assert DS.factor_canterano(j, mi) == 1.5
    j.edad = DS.EDAD_BOOST_CANTERANO + 1
    assert DS.factor_canterano(j, mi) == 1.0
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'canterano'`, `no attribute 'factor_canterano'`).

- [ ] **Step 3: Modelo** — en `alpha_football/models.py`, debajo del campo `joya`:

```python
    canterano: str = ""                         # v0.4.11.0: club que lo formó (subido desde su cantera); '' = no
```

y en `from_dict`, debajo de `joya=bool(datos.get("joya", False)),`:

```python
                canterano=str(datos.get("canterano", "") or ""),                     # v0.4.11.0
```

- [ ] **Step 4: Cantera** — en `cantera.subir`, debajo de `j.joya = False ...`:

```python
        j.canterano = getattr(mi, 'nombre', '') or ''     # v0.4.11.0: progresa más rápido en su club
```

- [ ] **Step 5: Desarrollo** — en `alpha_football/desarrollo.py`, debajo de `_factor_progreso_edad`:

```python
BOOST_CANTERANO = 1.5          # v0.4.11.0
EDAD_BOOST_CANTERANO = 23


def factor_canterano(j: Any, equipo: Any) -> float:
    """v0.4.11.0: el canterano (hasta 23 años) progresa ×1.5 mientras siga en el club que lo formó."""
    origen = getattr(j, 'canterano', '') or ''
    if origen and origen == getattr(equipo, 'nombre', None) \
            and int(getattr(j, 'edad', 25) or 25) <= EDAD_BOOST_CANTERANO:
        return BOOST_CANTERANO
    return 1.0
```

y reemplazar `j.progreso_desarrollo += inc * _factor_progreso_edad(edad_j)` por:

```python
        j.progreso_desarrollo += inc * _factor_progreso_edad(edad_j) * factor_canterano(j, equipo)
```

- [ ] **Step 6: Ficha** — en `alpha_football/ui/ficha_jugador.py`, debajo de la línea `rasgo_txt = ...`:

```python
        if getattr(j, 'canterano', ''):             # v0.4.11.0
            rasgo_txt = f"{rasgo_txt}  ·  Canterano" if rasgo_txt else "Canterano"
```

- [ ] **Step 7: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_ajustes_v0411.py`
Expected: `16/16 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_cantera.py; PYTHONIOENCODING=utf-8 python tests/test_progreso_jovenes.py; PYTHONIOENCODING=utf-8 python tests/test_desarrollo_pasivo.py`
Expected: los tres en `N/N tests pasaron`.

---

### Task 6: Ventanas de mercado sin cierre (B3)

**Files:**
- Modify: `alpha_football/market.py:563-595`
- Modify: `alpha_football/prestamos.py:88-121` y `:365-372`
- Modify: `alpha_football/negociacion.py:389-396`
- Modify: `alpha_football/traspasos_pendientes.py:53-82`
- Modify: `alpha_football/finanzas.py:348-350` (bucle de contratos de `cierre_temporada`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py:495` (tras el bloque de préstamos de la J1)
- Modify: `tests/test_invierno_hitos.py:19-26`, `tests/test_ventana_traspaso.py:33`, `tests/test_negociaciones_v270.py:118-120`
- Test: `tests/test_presupuesto_ventanas.py` (nuevo)

**Interfaces:**
- Produces: `market.ventanas_mercado(n)` → `[(1, 3, 'inicio'), (11, 13, 'invierno')]` para 22 jornadas; `clave_ventana_traspaso` sin el caso cierre; `traspasos_pendientes._cuando(estado, j_ap) -> str`.

- [ ] **Step 1: Crear `tests/test_presupuesto_ventanas.py`** con la cabecera común y:

```python
"""v0.4.11.0: mercado sin ventana de cierre ni pretemporada de la IA; presupuesto por temporada."""
# <cabecera común>
from alpha_football import market as M, prestamos as PR, traspasos_pendientes as TP, finanzas as F
from alpha_football import correo as C


def test_solo_inicio_e_invierno():
    assert M.ventanas_mercado(22) == [(1, 3, 'inicio'), (11, 13, 'invierno')]
    assert [j for j in range(1, 23) if M.ventana_mercado_abierta(j, 22)] == [1, 2, 3, 11, 12, 13]
    assert M.proxima_apertura(5, 22) == 11 and M.proxima_apertura(15, 22) == 1
    assert M.clave_ventana_traspaso(2, 2, 22) == '2-verano'
    assert M.clave_ventana_traspaso(2, 12, 22) == '2-invierno'
    assert M.clave_ventana_traspaso(2, 21, 22) == ''


def test_liga_corta_solo_tiene_inicio():
    assert M.ventanas_mercado(6) == [(1, 3, 'inicio')]
    assert M.proxima_apertura(4, 6) == 1


def test_regreso_de_prestamos_sin_cierre():
    e = estado_carrera(); liga = e['liga']
    liga.jornada_actual = 2                                     # ventana de inicio
    assert PR._regreso(e, 6) == (1, 'invierno', 11)
    assert PR._regreso(e, 12) == (2, 'inicio', 1)
    liga.jornada_actual = 12                                    # ventana de invierno
    assert PR._regreso(e, 6) == (2, 'inicio', 1)
    assert PR._regreso(e, 12) == (2, 'invierno', 11)
    liga.jornada_actual = 18                                    # cerrado, pasado el invierno
    assert PR._regreso(e, 6) == (2, 'invierno', 11)             # arranca en el inicio de la T2
    assert PR._regreso(e, 12) == (3, 'inicio', 1)


def test_prestamo_viejo_con_ventana_de_cierre():
    assert PR._vuelve({'vuelve': [1, 20], 'ventana': 'cierre'}, 22) == [2, 1]
    assert PR._vuelve({'vuelve': [1, 11], 'ventana': 'invierno'}, 22) == [1, 11]
    assert PR._vuelve({'vuelve': [2, 1], 'ventana': 'inicio'}, 22) == [2, 1]


def test_texto_de_lo_acordado_tras_el_invierno():
    e = estado_carrera(); mi = e['mi_equipo']; e['liga'].jornada_actual = 8
    rival = e['liga'].equipos[1]
    assert "en la jornada 11" in TP.diferir_venta(e, mi.jugadores[0], rival, 1_000_000)
    e['liga'].jornada_actual = 16
    txt = TP.diferir_compra(e, rival.jugadores[0], rival, 1_000_000)
    assert "al empezar la próxima temporada" in txt and "jornada 1," not in txt


def test_acordado_no_pierde_contrato_en_el_cierre():
    e = estado_carrera(); mi = e['mi_equipo']; rival = e['liga'].equipos[1]
    e['liga'].jornada_actual = 16
    llega, sale = rival.jugadores[0], mi.jugadores[0]
    llega.contrato_anios, sale.contrato_anios = 3, 1
    TP.diferir_compra(e, llega, rival, 1_000_000)
    TP.diferir_venta(e, sale, rival, 1_000_000)
    e['temporada'] = 2
    F.cierre_temporada(e)
    assert llega.contrato_anios == 3                            # el contrato pactado no pierde un año
    assert sale in mi.jugadores and not getattr(sale, 'fin_de_contrato', False)   # vendido: no queda libre
    e['liga'].jornada_actual = 1
    assert TP.ejecutar(e) == 2
    assert llega in mi.jugadores and sale in rival.jugadores
# <pie común>
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_presupuesto_ventanas.py`
Expected: los 6 en FAIL (todavía existe la ventana de cierre).

- [ ] **Step 3: `market.py`** — reemplazar `ventanas_mercado` y `clave_ventana_traspaso`:

```python
def ventanas_mercado(num_jornadas: int) -> list:
    """[(primera, última, nombre)] de las ventanas de la temporada: inicio (1-3) e invierno a mitad
    de temporada (J n/2 a n/2+2). El invierno se omite si no entra. v0.4.11.0: sin ventana de cierre."""
    n = max(1, int(num_jornadas or 22))
    d = DURACION_VENTANA
    ventanas = [(1, min(d, n), 'inicio')]
    medio = n // 2
    if medio > d + 1 and medio + d - 1 < n - d:
        ventanas.append((medio, medio + d - 1, 'invierno'))
    return ventanas
```

```python
def clave_ventana_traspaso(temporada: int, jornada: int, num_jornadas: int) -> str:
    """Ventana de traspasos en curso ('<T>-verano' = inicio, '<T>-invierno'). '' con el mercado cerrado."""
    v = ventana_actual(jornada, num_jornadas)
    if v is None:
        return ''
    return f"{int(temporada)}-{'invierno' if v[2] == 'invierno' else 'verano'}"
```

Actualizar también los dos docstrings que dicen "y en las 3 últimas" (`proxima_apertura` no cambia; `ventana_mercado_abierta`: "en las jornadas 1-3 y en el invierno (mitad de temporada)").

- [ ] **Step 4: `prestamos.py`** — en `_regreso`, reemplazar el bloque final:

```python
    k += 1
    if k >= len(vs):
        # desde el cierre, 6 meses = el invierno de la temporada siguiente (el inicio es la misma
        # ventana de verano); sin invierno, el cierre siguiente
        k, t = (1 if len(vs) > 2 else len(vs) - 1), t + 1
    return t, vs[k][2], vs[k][0]
```

por:

```python
    k += 1
    if k >= len(vs):
        # v0.4.11.0 (sin ventana de cierre): desde el invierno, 6 meses = el inicio de la siguiente
        k, t = 0, t + 1
    return t, vs[k][2], vs[k][0]
```

En `_vuelve`, antes de `if isinstance(k, str):`:

```python
    if k == 'cierre':                  # v0.4.11.0: save de antes; esa ventana ya no existe
        return [int(v[0]) + 1, vs[0][0]]
```

En `_avisar_contratos`, reemplazar:

```python
    from alpha_football.market import ventanas_mercado
    t, jor, n = _momento(estado)
    vs = ventanas_mercado(n)
    if len(vs) < 2 or not vs[-1][0] <= jor <= vs[-1][1]:
        return
```

por:

```python
    t, jor, n = _momento(estado)
    if jor < n - 2:                    # v0.4.11.0: las 3 últimas jornadas (ya no hay ventana de cierre)
        return
```

- [ ] **Step 5: `negociacion._clave_ventana`** — reemplazar el cuerpo desde `nombre = ...`:

```python
    nombre = next((v[2] for v in ventanas_mercado(getattr(liga, 'num_jornadas', 22)) if j <= v[1]), None)
    if nombre is None:                 # v0.4.11.0: pasado el invierno, la próxima es el inicio siguiente
        return (temporada + 1, 'inicio')
    return (temporada, nombre)
```

y el docstring: `"""Ventana de mercado actual o la próxima: (temporada, 'inicio'|'invierno')."""`.

- [ ] **Step 6: `traspasos_pendientes.py`** — agregar debajo de `jornada_apertura`:

```python
def _cuando(estado: dict, j_ap: int) -> str:
    """v0.4.11.0: 'en la jornada N' o, si la próxima ventana ya es la de la temporada siguiente, eso."""
    if int(j_ap) > int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1):
        return f"en la jornada {j_ap}, en cuanto se abra el mercado"
    return "al empezar la próxima temporada, en cuanto se abra el mercado"
```

y usarlo en los dos `return`:

```python
    return f"{_nombre(jugador)} se irá a {getattr(comprador, 'nombre', 'su nuevo club')} {_cuando(estado, j_ap)}."
```

```python
    return f"{_nombre(jugador)} llegará {_cuando(estado, j_ap)}."
```

- [ ] **Step 7: Contratos de lo acordado** — en `finanzas.cierre_temporada`, antes de `for eq in _todos_los_equipos(estado):`:

```python
    acordados = set()       # v0.4.11.0: ya traspasados, esperan la J1: su contrato no corre ni vencen
    try:
        from alpha_football import traspasos_pendientes as _TP
        acordados = {(p.get('jugador'), str(p.get('jugador_id'))) for p in _TP._pendientes(estado)}
    except Exception as e_tp:
        logger.error(f"No se pudieron leer los traspasos acordados: {e_tp}")
```

y como primera línea dentro de `for j in list(eq.jugadores):`:

```python
            if acordados and (getattr(j, 'nombre_completo', ''), str(getattr(j, 'id', ''))) in acordados:
                continue
```

- [ ] **Step 8: Concretar al abrir la J1** — en `resumen_temporada_screen.avanzar_nueva_temporada`, después del bloque `try/except` de `_prestamos_j1(estado)`:

```python
        try:  # v0.4.11.0: sin ventana de cierre, lo acordado tras el invierno se concreta al abrir la J1
            from alpha_football import traspasos_pendientes as _tp_j1
            _tp_j1.ejecutar(estado)
            _tp_j1.limpiar_ofertas(estado)
        except Exception as e_tp:
            logger.error(f"Error concretando los traspasos acordados al empezar la temporada: {e_tp}")
```

- [ ] **Step 9: Tests viejos que daban por hecha la ventana de cierre**

`tests/test_invierno_hitos.py`, `test_ventanas_con_invierno`:

```python
    assert M.ventanas_mercado(22) == [(1, 3, 'inicio'), (11, 13, 'invierno')]
    abiertas = [j for j in range(1, 23) if M.ventana_mercado_abierta(j, 22)]
    assert abiertas == [1, 2, 3, 11, 12, 13]
    assert AM.eventos_ventana(22) == {1: 'abre', 4: 'cierra', 11: 'abre', 14: 'cierra'}
    e = estado_carrera(); e['liga'].jornada_actual = 8
    assert TP.jornada_apertura(e) == 11                  # acordado en J8 → llega en el invierno
    e['liga'].jornada_actual = 15
    assert TP.jornada_apertura(e) == 1                   # v0.4.11.0: tras el invierno, la J1 siguiente
```

`tests/test_ventana_traspaso.py:33`: `assert clave_ventana_traspaso(1, 21, n) == ''               # v0.4.11.0: ya no hay ventana de cierre`.

`tests/test_negociaciones_v270.py:118-120`:

```python
    e['liga'].jornada_actual = e['liga'].num_jornadas    # pasado el invierno: se recalculan para la próxima
    N.recomendaciones_ojeador(e)
    assert tuple(e['datos_carrera']['ojeador']['clave']) == (2, 'inicio')
```

- [ ] **Step 10: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_presupuesto_ventanas.py`
Expected: `6/6 tests pasaron`.
Run (uno por uno, revisando la salida): `test_invierno_hitos.py`, `test_ventana_traspaso.py`, `test_negociaciones_v270.py`, `test_mercado_v440.py`, `test_mercado_v350.py`, `test_prestamos.py`, `test_prestamos_pedir.py`, `test_prestamos_pulido.py`, `test_prestamos_sueldo.py`, `test_patrocinios.py`.
Expected: todos en `N/N tests pasaron`. Un test que falle por operar en las jornadas 20–22 con el mercado abierto se corrige moviendo su jornada a la 12 (invierno) si prueba una operación en ventana, o cambiando lo esperado a "acordado para la J1" si prueba el final de la temporada; no se toca el código del juego para que pase.

---

### Task 7: Sin mercado de pretemporada de la IA (B2)

**Files:**
- Modify: `alpha_football/ui/resumen_temporada_screen.py:454-463`
- Modify: `alpha_football/mercado_ia.py:322-351`
- Test: `tests/test_presupuesto_ventanas.py`

**Interfaces:**
- Produces: constantes `mercado_ia.PROB_CLUB_VENTANA = 0.25`, `PROB_CLUB_INICIO = 0.50`. `ronda_fichajes_ia(estado, 'pretemporada')` sigue existiendo (lo usan tests y la calibración) pero el juego ya no lo llama.

- [ ] **Step 1: Tests** — agregar a `tests/test_presupuesto_ventanas.py`:

```python
def _temporada_jugable(tipo='argentina', idx=3):
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera(tipo, idx)
    e['copa_user_en_copa'] = False
    inicializar_calendario_liga(e['liga'])
    return e


def test_el_cambio_de_temporada_no_corre_la_ronda_de_pretemporada():
    from alpha_football import mercado_ia as MI
    from alpha_football.ui import resumen_temporada_screen as R
    e = _temporada_jugable()
    modos, original = [], MI.ronda_fichajes_ia
    MI.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: modos.append(modo) or []
    try:
        R.avanzar_nueva_temporada(e)
    finally:
        MI.ronda_fichajes_ia = original
    assert e['temporada'] == 2 and 'pretemporada' not in modos


def test_la_ventana_de_inicio_mueve_mas_clubes_que_el_invierno():
    from alpha_football import mercado_ia as MI
    e = estado_carrera()
    vistos, original = [], MI._buscar_refuerzo
    MI._buscar_refuerzo = lambda comprador, *a, **k: vistos.append(comprador.nombre)   # devuelve None: no ficha
    try:
        n_inicio = n_invierno = 0
        for semilla in range(1, 11):                    # 10 rondas de cada una: no depende de una semilla
            e['liga'].jornada_actual = 2
            MI.ronda_fichajes_ia(e, 'ventana', random.Random(semilla)); n_inicio += len(vistos); vistos.clear()
            e['liga'].jornada_actual = 12
            MI.ronda_fichajes_ia(e, 'ventana', random.Random(semilla)); n_invierno += len(vistos); vistos.clear()
    finally:
        MI._buscar_refuerzo = original
    assert n_invierno > 0 and n_inicio > n_invierno * 1.4, (n_inicio, n_invierno)
```

- [ ] **Step 2: Correr y ver que falla** (hoy corre `'pretemporada'` y las dos ventanas mueven lo mismo).

- [ ] **Step 3: Cambio de temporada** — en `avanzar_nueva_temporada`, reemplazar:

```python
        _pc.mostrar("PASANDO DE TEMPORADA", "Mercado de pretemporada", 0.65)
        # 4c. v2.3.7: ingresos de la IA y mercado de pretemporada (los recién
        #     ascendidos fichan más para intentar mantenerse).
        try:
            from alpha_football.mercado_ia import ingresos_fin_temporada, ronda_fichajes_ia
            ingresos_fin_temporada(estado)
            estado['mercado_ia_log'] = []
            ronda_fichajes_ia(estado, 'pretemporada')
        except Exception as e_mia:
            logger.error(f"Error en el mercado de pretemporada de la IA: {e_mia}")
```

por:

```python
        _pc.mostrar("PASANDO DE TEMPORADA", "Ingresos de los clubes", 0.65)
        # 4c. Ingresos de la IA. v0.4.11.0: ya no hay ronda de pretemporada (la IA fichaba antes
        #     que el user); ahora ficha en la ventana de inicio, jornada a jornada, a la vez que él.
        try:
            from alpha_football.mercado_ia import ingresos_fin_temporada
            ingresos_fin_temporada(estado)
            estado['mercado_ia_log'] = []
        except Exception as e_mia:
            logger.error(f"Error en los ingresos de temporada de la IA: {e_mia}")
```

- [ ] **Step 4: Ventana de inicio más activa** — en `alpha_football/mercado_ia.py`, junto a las constantes del módulo (debajo de `MEJORA_MINIMA`):

```python
PROB_CLUB_VENTANA = 0.25       # clubes que buscan refuerzo por jornada con el mercado abierto
PROB_CLUB_INICIO = 0.50        # v0.4.11.0: en la ventana de inicio (reemplaza a la ronda de pretemporada)
```

En `ronda_fichajes_ia`, antes de `log = []`:

```python
    en_inicio = False              # v0.4.11.0
    try:
        from alpha_football.market import ventana_actual
        liga_u = estado.get('liga')
        v = ventana_actual(int(getattr(liga_u, 'jornada_actual', 1) or 1),
                           int(getattr(liga_u, 'num_jornadas', 22) or 22))
        en_inicio = bool(v) and v[2] == 'inicio'
    except Exception as e_v:
        logger.error(f"No se pudo leer la ventana de mercado: {e_v}")
```

y reemplazar la rama `else` del modo:

```python
        else:
            if azar.random() > 0.25:
                continue
            intentos, fraccion = 1, 0.6
```

por:

```python
        else:
            if azar.random() > (PROB_CLUB_INICIO if en_inicio else PROB_CLUB_VENTANA):
                continue
            intentos, fraccion = (2 if es_asc and en_inicio else 1), 0.6
```

Actualizar el docstring: `modo='ventana': 25% de los clubes (50% en la ventana de inicio; los recién ascendidos, 2 intentos), con el 60%.`

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_presupuesto_ventanas.py`
Expected: `8/8 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_v236.py; PYTHONIOENCODING=utf-8 python tests/test_finanzas_v460.py; PYTHONIOENCODING=utf-8 python tests/test_integracion_v290.py`
Expected: los tres en `N/N tests pasaron`.

---

### Task 8: Presupuesto por temporada (B1)

**Files:**
- Modify: `alpha_football/finanzas.py` (constantes y funciones nuevas antes de `cierre_temporada`; llamada dentro de `cierre_temporada`)
- Modify: `alpha_football/directiva.py:118-120` (`_correo_objetivos`)
- Modify: `alpha_football/ui/objetivos_screen.py:44` y la lista `filas` de REGLAS
- Test: `tests/test_presupuesto_ventanas.py`

**Interfaces:**
- Consumes: `finanzas.presupuesto_base(equipo, tipo, division) -> int`; `estado['historial'][-1]` con `temporada`, `equipo`, `objetivo_resultado`, `campeon_liga`; `datos_carrera['campeones_copas'][-1]` = `{'temporada', 'champions', 'libertadores'}`.
- Produces: `finanzas.factor_salud(saldo, base) -> float`, `finanzas.presupuesto_temporada(base, saldo, resultado, campeon_liga=False, campeon_copa=False) -> dict` (claves `base, saldo, salud, objetivo, bonos, mult, deuda, total`), `finanzas.aplicar_presupuesto_temporada(estado) -> Optional[dict]`; `datos_carrera['presupuesto_temporada']`.

- [ ] **Step 1: Tests** — agregar a `tests/test_presupuesto_ventanas.py`:

```python
def test_factor_salud_por_tramos():
    b = 100_000_000
    assert F.factor_salud(-1, b) == 0.80
    assert F.factor_salud(0, b) == 0.90 and F.factor_salud(24_999_999, b) == 0.90
    assert F.factor_salud(25_000_000, b) == 1.00 and F.factor_salud(74_999_999, b) == 1.00
    assert F.factor_salud(75_000_000, b) == 1.10 and F.factor_salud(149_999_999, b) == 1.10
    assert F.factor_salud(150_000_000, b) == 1.20 and F.factor_salud(10 ** 10, b) == 1.20
    assert F.factor_salud(50, 0) == 1.20                       # base 0: no divide por cero


def test_el_sobrante_no_pasa_de_temporada():
    p = F.presupuesto_temporada(100_000_000, 900_000_000, 'cumplido')
    assert p['salud'] == 1.20 and p['objetivo'] == 1.10 and p['bonos'] == 0
    assert 131_999_999 <= p['total'] <= 132_000_001
    assert F.presupuesto_temporada(100_000_000, 50_000_000, 'superado')['total'] == 125_000_000
    assert F.presupuesto_temporada(100_000_000, 50_000_000, 'fallado')['total'] == 85_000_000
    assert F.presupuesto_temporada(100_000_000, 50_000_000, '')['total'] == 100_000_000   # sin dato: neutro


def test_topes_del_multiplicador():
    alto = F.presupuesto_temporada(100_000_000, 900_000_000, 'superado', True, True)   # 1.2 × 1.25 × 1.35
    assert alto['mult'] == 1.75 and alto['total'] == 175_000_000
    bajo = F.presupuesto_temporada(100_000_000, -1, 'fallado')                         # 0.8 × 0.85 = 0.68
    assert abs(bajo['mult'] - 0.68) < 1e-9


def test_la_deuda_se_descuenta_con_piso():
    p = F.presupuesto_temporada(100_000_000, -50_000_000, 'fallado')
    assert p['deuda'] == 50_000_000 and 17_999_999 <= p['total'] <= 18_000_001
    assert F.presupuesto_temporada(100_000_000, -500_000_000, 'fallado')['total'] == 10_000_000


def test_el_cierre_fija_el_presupuesto_y_avisa():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = 999_000_000
    e['temporada'] = 2
    e['historial'] = [{'temporada': 1, 'equipo': mi.nombre, 'objetivo_resultado': 'cumplido', 'campeon_liga': 'Otro'}]
    F.cierre_temporada(e)
    base = F.presupuesto_base(mi, e['liga'].tipo, 1)
    esperado = F.presupuesto_temporada(base, 999_000_000, 'cumplido')
    assert mi.balance == esperado['total'] < 999_000_000
    assert e['datos_carrera']['presupuesto_temporada']['total'] == mi.balance
    m = next(x for x in C.bandeja(e) if x['asunto'] == "Presupuesto de la temporada 2")
    assert m['remitente'] == 'directiva' and m['accion']['pantalla'] == 'finanzas_screen'


def test_titulos_e_historial_ajeno():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 0
    e['temporada'] = 2
    e['historial'] = [{'temporada': 1, 'equipo': mi.nombre, 'objetivo_resultado': 'superado', 'campeon_liga': mi.nombre}]
    e['datos_carrera']['campeones_copas'] = [{'temporada': 1, 'champions': mi.nombre, 'libertadores': 'Otro'}]
    info = F.aplicar_presupuesto_temporada(e)
    assert info['objetivo'] == 1.25 and abs(info['bonos'] - 0.35) < 1e-9
    e2 = estado_carrera(); e2['temporada'] = 2; e2['mi_equipo'].balance = 0
    e2['historial'] = [{'temporada': 1, 'equipo': 'Otro club', 'objetivo_resultado': 'superado'}]
    assert F.aplicar_presupuesto_temporada(e2)['objetivo'] == 1.0          # ese registro no es de este club
    e3 = estado_carrera(); e3['temporada'] = 2; e3['mi_equipo'].balance = 0
    assert F.aplicar_presupuesto_temporada(e3)['objetivo'] == 1.0          # save viejo, sin historial


def test_en_rojo_sigue_la_sancion_y_descuenta_la_deuda():
    e = estado_carrera(); mi = e['mi_equipo']
    base = F.presupuesto_base(mi, e['liga'].tipo, 1)
    mi.balance = -int(base * 0.2)
    e['temporada'] = 2
    F.cierre_temporada(e)
    assert e['datos_carrera']['temporadas_en_rojo'] == 1 and mi.sancion_puntos == F.PUNTOS_QUIEBRA
    assert mi.balance >= int(base * F.PISO_PRESUPUESTO) and mi.balance > 0


def test_reglas_de_objetivos_entran_en_el_panel():
    from alpha_football.ui import objetivos_screen as OS
    assert OS.R_REGLAS.height >= 18 + 9 * 38
    assert OS.R_REGLAS.bottom <= 690
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'factor_salud'`).

- [ ] **Step 3: Funciones** — en `alpha_football/finanzas.py`, inmediatamente antes de `def cierre_temporada`:

```python
# v0.4.11.0: presupuesto por temporada. El saldo no se arrastra: al cerrar, el club se queda con
# el sobrante y fija un presupuesto nuevo según su tamaño (base), su salud y el objetivo deportivo.
SALUD_ROJO = 0.80
SALUD_TRAMOS = ((0.25, 0.90), (0.75, 1.00), (1.50, 1.10))    # (saldo/base menor que, factor)
SALUD_MAX = 1.20
FACTOR_OBJETIVO = {'superado': 1.25, 'cumplido': 1.10, 'fallado': 0.85}
BONO_LIGA, BONO_COPA = 0.15, 0.20
MULT_MIN, MULT_MAX = 0.60, 1.75
PISO_PRESUPUESTO = 0.10


def factor_salud(saldo: int, base: int) -> float:
    """Cómo cerró el club respecto de su presupuesto base: en rojo 0.80 … más de 150% 1.20."""
    if int(saldo) < 0:
        return SALUD_ROJO
    r = int(saldo) / max(1, int(base))
    return next((f for tope, f in SALUD_TRAMOS if r < tope), SALUD_MAX)


def presupuesto_temporada(base: int, saldo: int, resultado: str, campeon_liga: bool = False,
                          campeon_copa: bool = False) -> dict:
    """Desglose del presupuesto nuevo: base × salud × objetivo × (1 + bonos), entre ×0.60 y ×1.75;
    la deuda se descuenta entera (piso: 10% de la base)."""
    base, saldo = int(base), int(saldo)
    salud = factor_salud(saldo, base)
    objetivo = FACTOR_OBJETIVO.get(resultado, 1.0)
    bonos = (BONO_LIGA if campeon_liga else 0.0) + (BONO_COPA if campeon_copa else 0.0)
    mult = max(MULT_MIN, min(MULT_MAX, salud * objetivo * (1 + bonos)))
    deuda = max(0, -saldo)
    total = max(int(base * PISO_PRESUPUESTO), int(round(base * mult)) - deuda)
    return {'base': base, 'saldo': saldo, 'salud': salud, 'objetivo': objetivo, 'bonos': bonos,
            'mult': mult, 'deuda': deuda, 'total': total}


def aplicar_presupuesto_temporada(estado: dict) -> Optional[dict]:
    """Cierre de temporada (ya con la liga y la división nuevas): reemplaza el saldo por el
    presupuesto de la temporada que empieza y lo comunica por correo."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None or liga is None:
        return None
    temporada = int(estado.get('temporada', 1) or 1)
    dc = estado.setdefault('datos_carrera', {})
    reg = (estado.get('historial') or [{}])[-1] or {}
    propio = reg.get('equipo') == mi.nombre and int(reg.get('temporada', 0) or 0) == temporada - 1
    copas = (dc.get('campeones_copas') or [{}])[-1] or {}
    campeon_copa = int(copas.get('temporada', 0) or 0) == temporada - 1 and \
        mi.nombre in [v for k, v in copas.items() if k != 'temporada']
    base = presupuesto_base(mi, getattr(liga, 'tipo', 'betplay'), getattr(liga, 'division', 1) or 1)
    info = presupuesto_temporada(base, int(getattr(mi, 'balance', 0) or 0),
                                 reg.get('objetivo_resultado', '') if propio else '',
                                 propio and reg.get('campeon_liga') == mi.nombre, campeon_copa)
    mi.balance = info['total']
    dc['presupuesto_temporada'] = dict(info, temporada=temporada)
    try:
        from alpha_football import correo as C
        m = lambda v: f"${v / 1_000_000:.1f}M"
        cierre = (f"Cierre de la temporada anterior: {m(info['saldo'])} (el sobrante queda en las arcas del club)."
                  if info['saldo'] >= 0 else
                  f"Cierre de la temporada anterior: −{m(info['deuda'])} (la deuda se descuenta del presupuesto).")
        titulos = f" Títulos: +{int(round(info['bonos'] * 100))}%." if info['bonos'] else ""
        C.enviar(estado, 'directiva', f"Presupuesto de la temporada {temporada}",
                 "La directiva ha fijado el presupuesto de la nueva temporada.\n\n"
                 f"{cierre}\n"
                 f"Presupuesto base del club: {m(info['base'])}.\n"
                 f"Salud financiera: ×{info['salud']:.2f}. Objetivo deportivo: ×{info['objetivo']:.2f}.{titulos}\n\n"
                 f"Presupuesto disponible: {m(info['total'])}.",
                 C.accion('finanzas_screen', "VER FINANZAS"))
    except Exception as e:
        logger.error(f"No se pudo avisar el presupuesto de la temporada: {e}")
    return info
```

- [ ] **Step 4: Llamarla en el cierre** — en `cierre_temporada`, inmediatamente antes de `if mi is not None:     # v4.9.0: vencen patrocinios ...`:

```python
    try:    # v0.4.11.0: el saldo no se arrastra; va después del control de números rojos
        aplicar_presupuesto_temporada(estado)
    except Exception as e_pres:
        logger.error(f"Error fijando el presupuesto de la temporada: {e_pres}")
```

- [ ] **Step 5: Textos** — en `directiva._correo_objetivos`, reemplazar:

```python
                 f"cumple, {m(ref * PREMIO['cumplido'])}. Fallar cualquiera de los objetivos supone una "
                 "advertencia, y reincidir, la rescisión de su contrato.",
```

por:

```python
                 f"cumple, {m(ref * PREMIO['cumplido'])}. Fallar cualquiera de los objetivos supone una "
                 "advertencia, y reincidir, la rescisión de su contrato.\n\n"
                 "El saldo no pasa de una temporada a otra: superar el objetivo sube el presupuesto de la "
                 "próxima un 25%; cumplirlo, un 10%; fallarlo lo baja un 15%.",
```

En `alpha_football/ui/objetivos_screen.py`: `R_REGLAS = pygame.Rect(SCREEN_W // 2 - 380, 150, 760, 368)` (antes 330) y, en la lista `filas`, antes de `("Clic o ESC para cerrar", 'blanco')`:

```python
                     ("El saldo no pasa de temporada: el presupuesto siguiente sube 25% / 10% o baja 15%", 'azul'),   # v0.4.11.0
```

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_presupuesto_ventanas.py`
Expected: `16/16 tests pasaron`.
Run (uno por uno): `test_finanzas_v290.py`, `test_finanzas_v460.py`, `test_integracion_v290.py`, `test_objetivos_secciones.py`, `test_directiva_v280.py`, `test_carrera_dt_v320.py`, `test_ayuda_v390.py`.
Expected: todos en `N/N tests pasaron`. Un test que comparaba el saldo tras `cierre_temporada` o `avanzar_nueva_temporada` con "saldo anterior + premio" pasa a comparar contra `e['datos_carrera']['presupuesto_temporada']['total']`.

---

### Task 9: Cierre de A + B

**Files:**
- Modify: `context.md` (bitácora y pendientes; fecha del encabezado)

- [ ] **Step 1: Suite completa, un archivo a la vez**

```bash
cd "C:/Users/diego/Downloads/AlphaFootball" && for f in tests/test_*.py; do
  PYTHONIOENCODING=utf-8 python "$f" > "$TEMP/af_test.log" 2>&1; rc=$?
  echo "$(basename "$f") rc=$rc $(grep -c 'FAIL' "$TEMP/af_test.log") FAIL · $(tail -1 "$TEMP/af_test.log")"
done
```

Expected: cada línea con `rc=0`, `0 FAIL` y `N/N tests pasaron`. Lo que no cumpla se arregla antes de seguir (primero entender si el test daba por hecha una regla que este plan cambió; si es así se ajusta el test, si no, es un bug del cambio).

- [ ] **Step 2: Juego real** — `python main.py`, cargar una partida y comprobar a mano: abrir un correo con botón (VER FINANZAS) y volver con ESC al mismo mensaje; la tarjeta de un jugador con goles de copa en Dirección de equipo; OBJETIVOS → REGLAS con la fila nueva dentro del panel.

- [ ] **Step 3: `context.md`** — agregar la bitácora "2026-10-06 — Ajustes, economía y mercado (v0.4.11.0, sub-proyectos A y B, sin commit)" con: los cinco ajustes, las ventanas (solo inicio e invierno), la IA sin pretemporada, la fórmula del presupuesto y los números medidos en `calibrar_objetivos.py`. Actualizar la fecha del encabezado y los pendientes (C, D, E y F del spec).
