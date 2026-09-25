# Hub de carrera por columnas + copa automática — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la barra de 11 botones de `league_screen` por 6 columnas (INICIO, DIRECCIÓN, NEGOCIACIONES, OFICINA, OPCIONES, GUARDAR) y jugar la copa desde JUGAR en Inicio.

**Architecture:** `league_screen.render` pasa a ser un hub: barra de columnas + `_render_inicio` (tablero) o `_render_tarjetas` (tarjetas por pestaña). La lógica de "armar el partido de copa" y el avance de grupos que vivían en `copa_screen.render` se extraen a funciones puras de `copa_screen` (`preparar_partido_copa`, `sincronizar_copa_user`, `rival_copa_pendiente`, `linea_copa_user`) que Inicio llama. `copa_screen` queda solo de consulta.

**Tech Stack:** Python 3.10, Pygame (1280×720). Tests = scripts planos en `tests/` con `SDL_VIDEODRIVER=dummy`.

**Spec:** `docs/superpowers/specs/2026-09-23-hub-navegacion-design.md`

## Global Constraints

- Pantalla 1280×720; se usan `SCREEN_W`, `SCREEN_H`, `COLORS`, `get_font`, `draw_panel`, `draw_text` de `alpha_football/ui/theme.py` (ya importados en `league_screen`).
- Comentarios y textos en español; marcar los cambios con `v2.4.0` en comentarios/docstrings.
- Patrón resiliente del proyecto: cada bloque de dibujo en `try/except` con `logger.error(...)`.
- Tests: scripts planos (sin pytest). Correr con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` desde la raíz del repo.
- **Sin commits.** Diego aprueba los commits (v2.3.5–v2.3.8 siguen sin commit). Nunca agregar atribución a Claude/IA en git.
- Estado nuevo del hub en `estado`: `hub_tab` (`'inicio'|'direccion'|'negociaciones'|'oficina'`), `hub_bar_foco` (0..5), `hub_foco` (tarjeta / en Inicio 0=JUGAR 1=panel jornada), `hub_jornada_vista`, `hub_jornada_ref`, `hub_toast` (`(texto, hasta_ms, color)`), `_hub_copa_sync`.
- Se eliminan `estado['league_resumen_j']` y `estado['league_kbd_focus']` (solo los usa `league_screen`).

## Review Focus

- User en copa que **nunca abre** la pantalla de copa: los partidos de grupo ajenos se simulan igual y los grupos pasan a cuartos → test `test_sincronizar_simula_ajenos_y_pasa_a_cuartos` (Task 1).
- Eliminatoria lanzada desde JUGAR: `partido_copa_dict` debe quedar vacío o `match_screen` la trata como partido de grupos (`match_screen.py:1113`) → test `test_preparar_partido_copa_eliminatoria` (Task 1).
- Liga terminada con partido de copa pendiente (la final cae en la última jornada): JUGAR juega la copa antes de AVANZAR TEMPORADA → test `test_copa_antes_que_avanzar_temporada` (Task 3).
- Salir de la copa con Esc / VOLVER cae en la pestaña OFICINA; terminar un partido de copa cae en INICIO → test `test_retornos_de_copa` (Task 2).
- El panel de jornada no se queda "pegado" en una jornada vieja tras jugar: se reinicia al cambiar `jornada_actual` → test `test_panel_jornada_teclado_y_reinicio` (Task 3).

---

### Task 1: Helpers de copa para jugarla desde Inicio

**Files:**
- Modify: `alpha_football/ui/copa_screen.py` (insertar bloque nuevo justo antes de `def render(screen, estado: dict) -> str | None:`, hoy línea ~1751)
- Create: `tests/test_hub_v240.py`

**Interfaces:**
- Consumes (ya existen en `copa_screen`): `inicializar_copa_si_falta(estado)`, `_asegurar_bracket_normalizado(estado)`, `_autosimular_otros_grupo(estado, jornada)`, `recalcular_standings_copa(estado)`, `avanzar_fase_bracket(estado)`, `obtener_partido_copa_pendiente(estado) -> (str|None, dict|None)` (grupos: `("Copa Jornada N", partido_dict)`; eliminatorias: `("Copa Cuartos", copa_bracket[fase])`), `obtener_match_usuario_bracket(estado, fase) -> dict`, `encontrar_equipo_copa(nombre, estado)`.
- Produces:
  - `_limites_copa(num_jornadas: int) -> dict` — claves `1, 2, 3, 'cuartos', 'semis', 'final'`.
  - `sincronizar_copa_user(estado: dict) -> None`
  - `rival_copa_pendiente(estado: dict) -> tuple[Optional[str], Optional[str]]` — `(fase_nombre, rival)`.
  - `preparar_partido_copa(estado: dict) -> bool`
  - `linea_copa_user(estado: dict) -> Optional[str]`

- [ ] **Step 1: Crear el archivo de tests con los tests de copa**

`tests/test_hub_v240.py`:

```python
"""v2.4.0: hub de carrera por columnas + copa automática desde JUGAR."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(7)
screen = pygame.display.set_mode((1280, 720))

from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import copa_screen


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def estado_carrera():
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    alin = alineacion_por_defecto(mi)
    mi.alineacion_activa = alin
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': alin, 'primera_division': primeras, 'segunda_division': segunda,
            'team_contexto': 'carrera'}


def estado_copa():
    """Carrera con el user en la copa y la fecha 1 de grupos desbloqueada (J2 de liga)."""
    e = estado_carrera()
    e['copa_clasificado'] = True
    e['liga'].jornada_actual = 2
    copa_screen.inicializar_copa_si_falta(e)
    assert e['copa_user_en_copa'] is True
    return e


def partidos_user(e):
    mi = e['mi_equipo'].nombre
    return [p for p in e['copa_grupo_partidos'] if mi in (p['local'], p['visitante'])]


def test_preparar_partido_copa_grupos():
    e = estado_copa()
    assert copa_screen.preparar_partido_copa(e) is True
    assert e['match_mode'] == 'copa' and e['partido_actual'] is None
    nombres = {e['partido_local_obj'].nombre, e['partido_visitante_obj'].nombre}
    assert e['mi_equipo'].nombre in nombres
    assert e['partido_copa_dict']['jornada'] == 1
    assert 'partido_copa_bracket_fase' not in e
    print("  test_preparar_partido_copa_grupos: OK")


def test_preparar_partido_copa_sin_pendiente():
    e = estado_copa()
    e['liga'].jornada_actual = 1                     # la fecha 1 de copa aún no se desbloquea
    assert copa_screen.preparar_partido_copa(e) is False
    assert e.get('match_mode') != 'copa'
    assert copa_screen.rival_copa_pendiente(e) == (None, None)
    print("  test_preparar_partido_copa_sin_pendiente: OK")


def _ganar_grupos(e):
    """Marca los 3 partidos de grupo del user como ganados 3-0."""
    mi = e['mi_equipo'].nombre
    for p in partidos_user(e):
        local = p['local'] == mi
        p.update(jugado=True, goles_l=3 if local else 0, goles_v=0 if local else 3)


def test_sincronizar_simula_ajenos_y_pasa_a_cuartos():
    e = estado_copa()
    mi = e['mi_equipo'].nombre
    copa_screen.sincronizar_copa_user(e)
    j1 = [p for p in e['copa_grupo_partidos'] if p['jornada'] == 1]
    assert all(p['jugado'] for p in j1 if mi not in (p['local'], p['visitante']))
    assert not any(p['jugado'] for p in partidos_user(e))
    j2 = [p for p in e['copa_grupo_partidos'] if p['jornada'] == 2]
    assert not any(p['jugado'] for p in j2), "la fecha 2 aún no se desbloquea"
    # El user juega sus 3 partidos y la liga llega al umbral de la fecha 3.
    _ganar_grupos(e)
    e['liga'].jornada_actual = copa_screen._limites_copa(e['liga'].num_jornadas)[3]
    copa_screen.sincronizar_copa_user(e)
    assert all(p['jugado'] for p in e['copa_grupo_partidos'])
    assert e['copa_fase_actual'] == 'cuartos'
    print("  test_sincronizar_simula_ajenos_y_pasa_a_cuartos: OK")


def test_preparar_partido_copa_eliminatoria():
    e = estado_copa()
    _ganar_grupos(e)
    e['liga'].jornada_actual = copa_screen._limites_copa(e['liga'].num_jornadas)['cuartos']
    copa_screen.sincronizar_copa_user(e)
    assert e['copa_fase_actual'] == 'cuartos'
    e['partido_copa_dict'] = {'basura': True}         # resto de un partido de grupos anterior
    fase_nombre, rival = copa_screen.rival_copa_pendiente(e)
    assert fase_nombre == "Copa Cuartos" and rival
    assert copa_screen.preparar_partido_copa(e) is True
    assert e['partido_local_obj'] is e['mi_equipo']
    assert e['partido_visitante_obj'].nombre == rival
    assert e['partido_copa_bracket_fase'] == 'cuartos'
    assert 'partido_copa_dict' not in e, "match_screen trata la eliminatoria como grupos si queda"
    print("  test_preparar_partido_copa_eliminatoria: OK")


def test_linea_copa_user():
    e = estado_copa()
    linea = copa_screen.linea_copa_user(e)
    assert linea.startswith("Copa · Grupo, fecha 1 vs ") and "(desde J2)" in linea
    e['copa_fase_actual'] = 'eliminado'
    assert copa_screen.linea_copa_user(e) == "Copa: eliminado"
    e['copa_fase_actual'] = 'campeon'
    e['copa_campeon'] = e['mi_equipo'].nombre
    assert copa_screen.linea_copa_user(e) == "Copa: ¡CAMPEONES!"
    e['copa_user_en_copa'] = False
    assert copa_screen.linea_copa_user(e) is None
    print("  test_linea_copa_user: OK")


TESTS = [test_preparar_partido_copa_grupos, test_preparar_partido_copa_sin_pendiente,
         test_sincronizar_simula_ajenos_y_pasa_a_cuartos, test_preparar_partido_copa_eliminatoria,
         test_linea_copa_user]


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

- [ ] **Step 2: Correr y verificar que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: FAIL en los 5 tests con `AttributeError: module 'alpha_football.ui.copa_screen' has no attribute 'preparar_partido_copa'` (o `_limites_copa` / `linea_copa_user` / `rival_copa_pendiente` / `sincronizar_copa_user`).

- [ ] **Step 3: Implementar los helpers**

En `alpha_football/ui/copa_screen.py`, insertar justo antes de `def render(screen, estado: dict) -> str | None:`:

```python
# ── v2.4.0: la copa se juega desde JUGAR en Inicio (league_screen) ────────────

def _limites_copa(num_jornadas: int) -> dict:
    """Jornada de liga desde la que se juega cada fecha de copa (mismos umbrales que el gating)."""
    return {
        1: 2,
        2: max(3, int(num_jornadas * 0.3)),
        3: max(4, int(num_jornadas * 0.5)),
        'cuartos': max(6, int(num_jornadas * 0.7)),
        'semis': max(8, int(num_jornadas * 0.85)),
        'final': num_jornadas,
    }


def sincronizar_copa_user(estado: dict) -> None:
    """
    v2.4.0: lo que copa_screen.render hacía al entrar, ahora sin abrir la pantalla:
    simula los partidos de grupo ajenos de las fechas ya desbloqueadas, recalcula la tabla
    y pasa a cuartos cuando terminaron los grupos. Idempotente. Solo si el user está en copa
    (el modo espectador lo lleva simular_copa_fondo).
    """
    try:
        liga = estado.get('liga')
        if estado.get('copa_user_en_copa') is False or not liga or not estado.get('mi_equipo'):
            return
        inicializar_copa_si_falta(estado)
        if estado.get('copa_user_en_copa') is False:
            return
        _asegurar_bracket_normalizado(estado)
        if estado.get('copa_fase_actual') != 'grupos':
            return
        limites = _limites_copa(getattr(liga, 'num_jornadas', 10) or 10)
        jornada = getattr(liga, 'jornada_actual', 1)
        for jn in (1, 2, 3):
            if jornada >= limites[jn]:
                _autosimular_otros_grupo(estado, jn)
        recalcular_standings_copa(estado)
        partidos = estado.get('copa_grupo_partidos') or []
        if partidos and all(p.get('jugado', False) for p in partidos):
            avanzar_fase_bracket(estado)
    except Exception as e:
        logger.error(f"Error en sincronizar_copa_user: {e}")


def rival_copa_pendiente(estado: dict) -> tuple[Optional[str], Optional[str]]:
    """v2.4.0: (nombre de la fecha, rival) del partido de copa que toca ahora, o (None, None)."""
    try:
        fase_nombre, partido = obtener_partido_copa_pendiente(estado)
        if not fase_nombre:
            return None, None
        mi_nombre = getattr(estado.get('mi_equipo'), 'nombre', '')
        fase = estado.get('copa_fase_actual', 'grupos')
        if fase != 'grupos':
            partido = obtener_match_usuario_bracket(estado, fase)
        partido = partido or {}
        rival = partido.get('visitante') if partido.get('local') == mi_nombre else partido.get('local')
        return fase_nombre, (rival or partido.get('rival') or None)
    except Exception as e:
        logger.error(f"Error en rival_copa_pendiente: {e}")
        return None, None


def preparar_partido_copa(estado: dict) -> bool:
    """
    v2.4.0: deja `estado` listo para prepartido_screen con el partido de copa pendiente
    (antes vivía en el botón JUGAR de esta pantalla). False si no hay partido o no se
    encuentra al rival; en ese caso no toca el estado.
    """
    try:
        fase_nombre, rival = rival_copa_pendiente(estado)
        if not fase_nombre or not rival:
            return False
        mi = estado.get('mi_equipo')
        fase = estado.get('copa_fase_actual', 'grupos')
        if fase == 'grupos':
            _, partido = obtener_partido_copa_pendiente(estado)
            local = encontrar_equipo_copa(partido['local'], estado)
            visitante = encontrar_equipo_copa(partido['visitante'], estado)
        else:
            partido, local, visitante = None, mi, encontrar_equipo_copa(rival, estado)
        if local is None or visitante is None:
            logger.error(f"preparar_partido_copa: no se encontró un equipo ({fase_nombre} vs {rival}).")
            return False
        estado['match_mode'] = 'copa'
        estado['partido_actual'] = None
        estado['partido_local_obj'] = local
        estado['partido_visitante_obj'] = visitante
        estado.pop('sim_resultado', None)
        if partido is not None:
            estado['partido_copa_dict'] = partido
            estado.pop('partido_copa_bracket_fase', None)
        else:
            # match_screen distingue la eliminatoria porque partido_copa_dict es None.
            estado.pop('partido_copa_dict', None)
            estado['partido_copa_bracket_fase'] = fase
        return True
    except Exception as e:
        logger.error(f"Error en preparar_partido_copa: {e}")
        return False


def linea_copa_user(estado: dict) -> Optional[str]:
    """v2.4.0: texto corto del estado de la copa del user para Inicio (None si no la juega)."""
    try:
        if estado.get('copa_user_en_copa') is False or not estado.get('copa_tipo'):
            return None
        fase = estado.get('copa_fase_actual', 'grupos')
        mi_nombre = getattr(estado.get('mi_equipo'), 'nombre', '')
        if fase == 'campeon':
            return "Copa: ¡CAMPEONES!" if estado.get('copa_campeon') == mi_nombre else "Copa: terminada"
        if fase == 'eliminado':
            return "Copa: eliminado"
        limites = _limites_copa(getattr(estado.get('liga'), 'num_jornadas', 10) or 10)
        if fase == 'grupos':
            pend = sorted((p for p in estado.get('copa_grupo_partidos') or []
                           if not p.get('jugado') and mi_nombre in (p.get('local'), p.get('visitante'))),
                          key=lambda p: p.get('jornada', 0))
            if not pend:
                return "Copa: grupos terminados"
            p = pend[0]
            rival = p['visitante'] if p['local'] == mi_nombre else p['local']
            return f"Copa · Grupo, fecha {p['jornada']} vs {rival} (desde J{limites[p['jornada']]})"
        previa = {'semis': 'cuartos', 'final': 'semis'}.get(fase)
        if previa and ((estado.get('copa_bracket') or {}).get(previa) or {}).get('avanza') != 'user':
            return "Copa: eliminado"
        m = obtener_match_usuario_bracket(estado, fase) or {}
        rival = (m.get('visitante') if m.get('local') == mi_nombre else m.get('local')) or 'por definir'
        return f"Copa · {str(fase).capitalize()} vs {rival} (desde J{limites.get(fase, '?')})"
    except Exception as e:
        logger.error(f"Error en linea_copa_user: {e}")
        return None
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `5/5 tests pasaron`.
Si `test_sincronizar_simula_ajenos_y_pasa_a_cuartos` falla porque `avanzar_fase_bracket` no deja `copa_fase_actual == 'cuartos'`, leer `avanzar_fase_bracket` (`copa_screen.py:548`) y revisar qué exige `_grupos_completos` / los standings; corregir el test solo si el fixture está mal armado (no cambiar `avanzar_fase_bracket`).

- [ ] **Step 5: Sin commit** (ver Global Constraints).

---

### Task 2: La copa vuelve a Inicio y su pantalla queda de consulta

**Files:**
- Modify: `alpha_football/ui/match_screen.py:643-645` y `:1306`
- Modify: `alpha_football/ui/prepartido_screen.py:354-355` y `:584-585`
- Modify: `alpha_football/ui/copa_screen.py` (render: bloque del botón JUGAR ~2216-2256, Esc ~2268-2270, VOLVER ~2310-2313, ramas de clic ~2315-2352)
- Test: `tests/test_hub_v240.py`

**Interfaces:**
- Consumes: `copa_screen.preparar_partido_copa(estado) -> bool` (Task 1).
- Produces: tras un partido de copa → `"league_screen"` con `estado['hub_tab'] = 'inicio'`; al salir de `copa_screen` → `"volver"` con `estado['hub_tab'] = 'oficina'`.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_hub_v240.py` (antes de `TESTS`) y sumar `test_retornos_de_copa` a la lista `TESTS`:

```python
def test_retornos_de_copa():
    from alpha_football.ui import prepartido_screen
    # Resultado de un partido de copa simulado al instante → Inicio.
    e = estado_copa()
    assert copa_screen.preparar_partido_copa(e)
    e['prepartido_resultado'] = {'titulo': '1 - 0', 'goles': []}
    e['hub_tab'] = 'oficina'
    res = prepartido_screen._render_resultado(screen, e, (0, 0), (640, 692))   # botón CONTINUAR
    assert res == 'league_screen' and e['hub_tab'] == 'inicio'
    # Salir de la pantalla de copa con Esc → pestaña OFICINA.
    e = estado_copa()
    e['hub_tab'] = 'inicio'
    key(pygame.K_ESCAPE)
    assert copa_screen.render(screen, e) == 'volver' and e['hub_tab'] == 'oficina'
    # La pantalla de copa ya no lanza partidos: Enter no hace nada con un partido pendiente.
    e = estado_copa()
    key(pygame.K_RETURN)
    copa_screen.render(screen, e)
    assert e.get('match_mode') != 'copa'
    print("  test_retornos_de_copa: OK")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `test_retornos_de_copa: FAIL` (`res == 'copa_screen'`).

- [ ] **Step 3: `prepartido_screen` vuelve a Inicio**

En `alpha_football/ui/prepartido_screen.py`, dentro de `_render_resultado` (CONTINUAR, ~línea 354):

```python
        if mode == 'copa':
            return "copa_screen"
```
→
```python
        if mode == 'copa':
            estado['hub_tab'] = 'inicio'   # v2.4.0: la copa se juega desde Inicio
            return "league_screen"
```

Y en el botón VOLVER del prepartido (~línea 584):

```python
            elif btn_volver.collidepoint(click_pos):
                if match_mode == 'copa':
                    return "copa_screen"
```
→
```python
            elif btn_volver.collidepoint(click_pos):
                if match_mode == 'copa':
                    estado['hub_tab'] = 'inicio'   # v2.4.0
                    return "league_screen"
```

- [ ] **Step 4: `match_screen` vuelve a Inicio**

En `alpha_football/ui/match_screen.py` (~línea 643):

```python
        if not local or not visitante:
            logger.error("No se encontraron los equipos del partido.")
            if match_mode == 'copa':
                return "copa_screen"
```
→
```python
        if not local or not visitante:
            logger.error("No se encontraron los equipos del partido.")
            if match_mode == 'copa':
                estado['hub_tab'] = 'inicio'   # v2.4.0
                return "league_screen"
```

Y al cerrar el partido de copa (~línea 1304-1306, justo después de `estado.pop('sim_tactico_abierto', None)` dentro de la rama de copa):

```python
                    estado.pop('sim_tactico_abierto', None)

                    return "copa_screen"
```
→
```python
                    estado.pop('sim_tactico_abierto', None)

                    estado['hub_tab'] = 'inicio'   # v2.4.0: la copa se juega desde Inicio
                    return "league_screen"
```

- [ ] **Step 5: `copa_screen` sin botón JUGAR**

En `copa_screen.render`, rama de grupos (~línea 2221):

```python
                if partidos_pend_user:
                    tiene_partido_pendiente = True
                    btn_text = f"JUGAR PARTIDO G{jornada_copa_sel}"
                    action_to_return = "jugar_partido_copa"
                    partido_a_jugar = partidos_pend_user[0]
                else:
```
→
```python
                if partidos_pend_user:
                    # v2.4.0: el partido del user se juega desde JUGAR en Inicio.
                    draw_text(screen, "Tu partido de esta fecha se juega desde JUGAR en Inicio.",
                              (710, 620), size='sm', color='dorado')
                else:
```

Rama de eliminatorias (~línea 2246):

```python
                if user_sigue_vivo and fase_data and not fase_data.get('jugado'):
                    tiene_partido_pendiente = True
                    _fase = str(fase_actual) if fase_actual else ''
                    btn_text = f"JUGAR {_fase.upper()}"
                    action_to_return = f"jugar_copa_{_fase}"
                elif not user_sigue_vivo:
```
→
```python
                if user_sigue_vivo and fase_data and not fase_data.get('jugado'):
                    # v2.4.0: el partido del user se juega desde JUGAR en Inicio.
                    draw_text(screen, "Tu partido de esta fase se juega desde JUGAR en Inicio.",
                              (710, 620), size='sm', color='dorado')
                elif not user_sigue_vivo:
```

Esc (~línea 2268):

```python
                if event.key == pygame.K_ESCAPE:
                    return "volver"
```
→
```python
                if event.key == pygame.K_ESCAPE:
                    estado['hub_tab'] = 'oficina'   # v2.4.0: la copa se consulta desde OFICINA
                    return "volver"
```

VOLVER (~línea 2310):

```python
                if back_rect.collidepoint(event.pos):
                    estado.pop('copa_tab', None)
                    estado.pop('copa_jornada_grupo', None)
                    return "volver"
```
→
```python
                if back_rect.collidepoint(event.pos):
                    estado.pop('copa_tab', None)
                    estado.pop('copa_jornada_grupo', None)
                    estado['hub_tab'] = 'oficina'   # v2.4.0
                    return "volver"
```

Ramas de clic ya muertas (~línea 2315): borrar completas las ramas `if action_to_return == "jugar_partido_copa": ...` y `elif action_to_return.startswith("jugar_copa_"): ...` (hasta antes de `elif action_to_return == "simular_resto_copa":`), y cambiar ese `elif` por `if`:

```python
                if tiene_partido_pendiente and jugar_rect.collidepoint(event.pos):
                    if action_to_return == "simular_resto_copa":
```

Luego buscar referencias sueltas: `grep -n "partido_a_jugar\|jugar_partido_copa\|jugar_copa_" alpha_football/ui/copa_screen.py`. Solo pueden quedar la inicialización `partido_a_jugar = None` y el docstring; si queda `partido_a_jugar = None` sin uso, borrarlo.

- [ ] **Step 6: Correr y verificar que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `6/6 tests pasaron`.
Run: `grep -n "return \"copa_screen\"" alpha_football/ui/match_screen.py alpha_football/ui/prepartido_screen.py`
Expected: sin resultados.

- [ ] **Step 7: Sin commit.**

---

### Task 3: `league_screen` como hub (pestañas, tarjetas, Inicio, teclado)

**Files:**
- Modify: `alpha_football/ui/league_screen.py` — reemplazar desde la línea `# --- Barra de menú superior (v2.3.5) ═══...` (hoy ~325) hasta **justo antes** de `    except Exception as error_general:` dentro de `render` (hoy ~771). Todo lo de arriba (`generar_fixture`, `inicializar_calendario_liga`, ligas de fondo, `draw_pitch_lines`, `draw_styled_button`) y el `except` de emergencia final quedan igual. Actualizar el docstring del módulo (línea 2-7).
- Modify: `tests/test_ui_v235.py` — borrar `test_barra_superior_lleva_a_cada_pantalla` y sacarlo de la lista `tests` del `__main__` (lo reemplazan los tests nuevos).
- Test: `tests/test_hub_v240.py`

**Interfaces:**
- Consumes: `copa_screen.sincronizar_copa_user`, `rival_copa_pendiente`, `preparar_partido_copa`, `linea_copa_user` (Task 1).
- Produces (usado por tests y Task 4): `BARRA_MENU`, `PESTANAS`, `TARJETAS`, `R_JUGAR`, `_rects_barra() -> list[Rect]`, `_rects_tarjetas(n) -> list[Rect]`, `_rects_jornada() -> (Rect, Rect)`, `_alertas_inicio(estado, mi_equipo) -> list[(str, str)]`, `_toast(estado, texto, color='verde', ms=3000)`, `render(screen, estado)`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_hub_v240.py` (el import va arriba, junto al de `copa_screen`):

```python
from alpha_football.ui import league_screen
```

y los tests (antes de `TESTS`), sumándolos a `TESTS`:

```python
def test_pestanas_y_tarjetas_llevan_a_cada_pantalla():
    esperado = {'direccion': ['team_screen'],
                'negociaciones': ['market_screen', 'ofertas_screen'],
                'oficina': ['stats_screen', 'copa_screen', 'career_screen', 'otras_ligas_screen']}
    rects = league_screen._rects_barra()
    assert len(rects) == 6
    for i, tab in enumerate(league_screen.PESTANAS):
        if tab == 'inicio':
            continue
        for k, destino in enumerate(esperado[tab]):
            e = estado_carrera()
            click(rects[i].center)
            assert league_screen.render(screen, e) is None and e['hub_tab'] == tab
            click(league_screen._rects_tarjetas(len(esperado[tab]))[k].center)
            assert league_screen.render(screen, e) == destino, (tab, destino)
            pygame.event.clear()
            assert league_screen.render(screen, e) is None and e['hub_tab'] == tab, "vuelve a la misma pestaña"
    e = estado_carrera()
    click(rects[4].center)
    assert league_screen.render(screen, e) == 'options_screen' and e['options_return'] == 'league_screen'
    click(rects[5].center)
    assert league_screen.render(screen, e) == 'save_slots_screen' and e['save_slots_return'] == 'league_screen'
    print("  test_pestanas_y_tarjetas_llevan_a_cada_pantalla: OK")


def test_teclado_pestanas():
    e = estado_carrera()
    key(pygame.K_RIGHT)
    assert league_screen.render(screen, e) is None and e['hub_tab'] == 'direccion'
    key(pygame.K_RETURN)
    assert league_screen.render(screen, e) == 'team_screen' and e['team_contexto'] == 'carrera'
    key(pygame.K_ESCAPE)
    assert league_screen.render(screen, e) is None and e['hub_tab'] == 'inicio'
    key(pygame.K_ESCAPE)
    assert league_screen.render(screen, e) == 'menu'
    print("  test_teclado_pestanas: OK")


def test_panel_jornada_teclado_y_reinicio():
    e = estado_carrera()
    liga = e['liga']
    key(pygame.K_DOWN)
    league_screen.render(screen, e)
    assert e['hub_foco'] == 1 and e['hub_jornada_vista'] == 1
    key(pygame.K_RIGHT)
    league_screen.render(screen, e)
    assert e['hub_tab'] == 'inicio' and e['hub_jornada_vista'] == 2
    for _ in range(40):
        key(pygame.K_RIGHT); league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == liga.num_jornadas
    for _ in range(40):
        key(pygame.K_LEFT); league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 1
    click(league_screen._rects_jornada()[1].center)
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 2
    liga.jornada_actual = 3                              # se jugó una jornada: vuelve al default
    pygame.event.clear()
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 3
    print("  test_panel_jornada_teclado_y_reinicio: OK")


def test_jugar_liga_y_copa():
    e = estado_carrera()
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen'
    assert e['match_mode'] == 'liga' and e['partido_actual'].jornada == 1
    e = estado_copa()
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    e = estado_copa()
    e['hub_tab'] = 'oficina'
    key(pygame.K_j)                                      # J juega desde cualquier pestaña
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    print("  test_jugar_liga_y_copa: OK")


def test_copa_antes_que_avanzar_temporada():
    e = estado_copa()
    liga = e['liga']
    league_screen.inicializar_calendario_liga(liga)
    liga.jornada_actual = liga.num_jornadas
    for p in liga.calendario:
        p.jugado, p.goles_local, p.goles_visitante = True, 0, 0
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    print("  test_copa_antes_que_avanzar_temporada: OK")


def test_alertas_inicio():
    e = estado_carrera()
    mi = e['mi_equipo']
    t0 = mi.jugadores[e['alineacion_activa'].titulares[0]]
    t0.lesion_partidos = 2
    e['ofertas_recibidas'] = [{}, {}]
    avisos = league_screen._alertas_inicio(e, mi)
    assert any(t0.apellido in texto for texto, _ in avisos)
    assert avisos[-1][0] == "2 ofertas sin responder"
    assert len(avisos) <= 3
    print("  test_alertas_inicio: OK")
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: FAIL en los 6 tests nuevos (`AttributeError: ... has no attribute 'PESTANAS'` / `'R_JUGAR'` / `'_rects_tarjetas'` / `'_alertas_inicio'`).

- [ ] **Step 3: Reemplazar la barra y el render**

Docstring del módulo (líneas 2-7) →

```python
"""
ALPHA FOOTBALL — Hub de carrera (Pygame)
v2.4.0: columnas arriba (INICIO, DIRECCIÓN, NEGOCIACIONES, OFICINA, OPCIONES, GUARDAR).
INICIO es el tablero (JUGAR, tabla, jornada, tu club); las demás muestran tarjetas.
También contiene el fixture de la liga y la simulación de las ligas de fondo.
"""
```

Código nuevo que reemplaza el bloque indicado en **Files** (queda seguido del `except Exception as error_general:` existente, que no se toca):

```python
# --- Hub por columnas (v2.4.0) ═══════════════════════════════════════════════

# (clave, línea 1, línea 2, color de acento). Las 4 primeras son pestañas con contenido;
# OPCIONES y GUARDAR abren su pantalla directo.
BARRA_MENU = [
    ('inicio',        "INICIO",    "",        'verde'),
    ('direccion',     "DIRECCIÓN", "EQUIPO",  'azul'),
    ('negociaciones', "NEGOCIA-",  "CIONES",  'dorado'),
    ('oficina',       "OFICINA",   "",        'azul'),
    ('opciones',      "OPCIONES",  "",        'verde'),
    ('guardar',       "GUARDAR",   "",        'rojo'),
]
PESTANAS = [item[0] for item in BARRA_MENU[:4]]
DESTINO_DIRECTO = {'opciones': 'options_screen', 'guardar': 'save_slots_screen'}
TITULOS = {'direccion': "DIRECCIÓN DE EQUIPO", 'negociaciones': "NEGOCIACIONES", 'oficina': "OFICINA"}

# Tarjetas de cada pestaña: (título, subtítulo, pantalla destino). Las de sub-proyectos
# futuros (Plantilla, Historial de pases, Ojeador, Objetivos) se agregan cuando existan.
TARJETAS = {
    'direccion': [
        ("FORMACIÓN", "Once, banco, formación y táctica", 'team_screen'),
    ],
    'negociaciones': [
        ("NEGOCIAR", "Mercado de pases", 'market_screen'),
        ("OFERTAS", "Ofertas recibidas por tus jugadores", 'ofertas_screen'),
    ],
    'oficina': [
        ("ESTADÍSTICAS", "Goleadores, asistencias, vallas", 'stats_screen'),
        ("COPA INTERNACIONAL", "Grupos, llaves y estadísticas", 'copa_screen'),
        ("HISTORIAL DE CARRERA", "Tus temporadas y títulos", 'career_screen'),
        ("OTRAS LIGAS", "Las 10 ligas en vivo", 'otras_ligas_screen'),
    ],
}

# Layout de Inicio
R_TABLA = pygame.Rect(16, 106, 640, 400)
R_HIST = pygame.Rect(16, 516, 640, 192)
R_JUGAR = pygame.Rect(672, 106, 592, 96)
Y_AVISOS = 210
R_JORNADA = pygame.Rect(672, 296, 592, 262)
R_CLUB = pygame.Rect(672, 568, 592, 140)
PARTIDOS_VISIBLES = 6


def _rects_barra() -> list:
    """Reparte las columnas de la barra superior a todo lo ancho."""
    margen, gap, alto, y = 16, 6, 56, 18
    ancho = (SCREEN_W - 2 * margen - gap * (len(BARRA_MENU) - 1)) // len(BARRA_MENU)
    return [pygame.Rect(margen + i * (ancho + gap), y, ancho, alto) for i in range(len(BARRA_MENU))]


def _boton_barra(screen, rect, linea1, linea2, hover, color, enabled=True, foco=False):
    """Botón de la barra superior con texto en 1 o 2 líneas centradas."""
    draw_styled_button(screen, rect, "", hover or foco, color, enabled)
    if foco:
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
    if not enabled:
        txt_color = (110, 110, 120)
    elif hover or foco:
        txt_color = color
    else:
        txt_color = COLORS.get('blanco', (255, 255, 255))
    font = get_font('sm')
    lineas = [l for l in (linea1, linea2) if l]
    alto_total = len(lineas) * 20
    for i, texto in enumerate(lineas):
        surf = font.render(texto, True, txt_color)
        screen.blit(surf, surf.get_rect(center=(rect.centerx, rect.centery - alto_total // 2 + 10 + i * 20)))


def _rects_tarjetas(n: int) -> list:
    """Grilla de 2 columnas centrada para las tarjetas de una pestaña."""
    w, h, gap, cols, y0 = 440, 150, 28, 2, 170
    x0 = (SCREEN_W - (cols * w + (cols - 1) * gap)) // 2
    return [pygame.Rect(x0 + (i % cols) * (w + gap), y0 + (i // cols) * (h + gap), w, h) for i in range(n)]


def _rects_jornada() -> tuple:
    """Botones < > del panel de jornada de Inicio."""
    prev = pygame.Rect(R_JORNADA.right - 92, R_JORNADA.y + 8, 36, 28)
    nxt = pygame.Rect(R_JORNADA.right - 48, R_JORNADA.y + 8, 36, 28)
    return prev, nxt


def _clave_tabla(eq):
    return (getattr(eq, 'puntos', 0), getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0), getattr(eq, 'gf', 0))


def _ultima_jornada_jugada(liga) -> int:
    """Última jornada con partidos jugados (0 si la temporada no empezó)."""
    jugadas = [p.jornada for p in getattr(liga, 'calendario', []) or [] if p.jugado]
    return max(jugadas) if jugadas else 0


def _jornada_por_defecto(liga) -> int:
    """La jornada actual si ya tiene resultados; si no, la última jugada; en la J1, la J1."""
    ja = int(getattr(liga, 'jornada_actual', 1) or 1)
    if any(p.jugado for p in getattr(liga, 'calendario', []) or [] if p.jornada == ja):
        return ja
    ultima = _ultima_jornada_jugada(liga)
    return ultima if ultima > 0 else ja


def _jornada_vista(estado, liga) -> int:
    """Jornada que muestra el panel; vuelve al default cada vez que avanza la liga."""
    ja = getattr(liga, 'jornada_actual', 1)
    if estado.get('hub_jornada_ref') != ja or not estado.get('hub_jornada_vista'):
        estado['hub_jornada_ref'] = ja
        estado['hub_jornada_vista'] = _jornada_por_defecto(liga)
    return int(estado['hub_jornada_vista'])


def _mover_jornada(estado, liga, paso: int) -> None:
    n = int(getattr(liga, 'num_jornadas', 1) or 1)
    estado['hub_jornada_vista'] = max(1, min(n, _jornada_vista(estado, liga) + paso))


def _alertas_inicio(estado, mi_equipo) -> list:
    """Avisos antes de jugar: lesionados/sancionados del once y ofertas sin responder (máx. 3)."""
    avisos = []
    try:
        alin = getattr(mi_equipo, 'alineacion_activa', None) or estado.get('alineacion_activa')
        jugadores = list(getattr(mi_equipo, 'jugadores', []) or [])
        for i in list(getattr(alin, 'titulares', []) or []):
            if not (0 <= i < len(jugadores)):
                continue
            j = jugadores[i]
            if getattr(j, 'lesion_partidos', 0) > 0:
                avisos.append((f"Lesionado en tu once: {j.nombre} {j.apellido} ({j.lesion_partidos} p.)", 'rojo'))
            elif getattr(j, 'partidos_sancion', 0) > 0:
                avisos.append((f"Sancionado en tu once: {j.nombre} {j.apellido}", 'rojo'))
        n = len(estado.get('ofertas_recibidas') or [])
        avisos = avisos[:2 if n else 3]
        if n:
            avisos.append((f"{n} oferta{'s' if n != 1 else ''} sin responder", 'dorado'))
    except Exception as e_av:
        logger.error(f"Error al calcular alertas de Inicio: {e_av}")
    return avisos


def _toast(estado, texto: str, color: str = 'verde', ms: int = 3000) -> None:
    """Aviso temporal que Inicio muestra abajo al centro."""
    estado['hub_toast'] = (texto, pygame.time.get_ticks() + ms, color)


def _abrir(estado, destino: str) -> str:
    """Prepara el contexto que cada pantalla espera y devuelve su nombre."""
    if destino == 'team_screen':
        estado['team_contexto'] = 'carrera'
    elif destino == 'options_screen':
        estado['options_return'] = 'league_screen'
    elif destino == 'save_slots_screen':
        estado['save_slots_return'] = 'league_screen'
    return destino


def _info_partido(estado, liga, mi_equipo) -> tuple:
    """(partido_usuario, esta_finalizada, fase_copa, rival_copa) de la jornada actual."""
    jornada_actual = getattr(liga, "jornada_actual", 1)
    num_jornadas = getattr(liga, "num_jornadas", 14)
    partidos_jornada = [p for p in getattr(liga, "calendario", []) if p.jornada == jornada_actual]
    partido_usuario = next((p for p in partidos_jornada
                            if mi_equipo.id in (p.local_id, p.visitante_id)), None)
    esta_finalizada = (jornada_actual == num_jornadas and all(p.jugado for p in partidos_jornada))
    fase_copa, rival_copa = None, None
    try:
        from alpha_football.ui.copa_screen import rival_copa_pendiente
        fase_copa, rival_copa = rival_copa_pendiente(estado)
    except Exception as e_copa:
        logger.error(f"Error al consultar la copa pendiente: {e_copa}")
    return partido_usuario, esta_finalizada, fase_copa, rival_copa


def _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa) -> Optional[str]:
    """JUGAR: primero la copa si toca, después la liga o el cierre de temporada."""
    if fase_copa:
        from alpha_football.ui.copa_screen import preparar_partido_copa
        if preparar_partido_copa(estado):
            return "prepartido_screen"
        _toast(estado, "No se pudo preparar el partido de copa", color='rojo')
        return None
    if esta_finalizada:
        return "resumen_temporada_screen"
    if partido_usuario is None or partido_usuario.jugado:
        return None
    estado['partido_actual'] = partido_usuario
    estado['match_mode'] = 'liga'
    return "prepartido_screen"


def _textos_jugar(liga, mi_equipo, info) -> tuple:
    """(línea grande, línea 2, línea 3, habilitado) del botón JUGAR."""
    partido_usuario, esta_finalizada, fase_copa, rival_copa = info
    if fase_copa:
        fase = fase_copa.replace("Copa Jornada ", "Grupos F").replace("Copa ", "")
        return "JUGAR", f"COPA · {fase} vs {(rival_copa or '?')[:26]}", "", True
    if esta_finalizada:
        return "AVANZAR TEMPORADA", "La liga terminó: cerrar la temporada", "", True
    if partido_usuario is None or partido_usuario.jugado:
        return "JUGAR", "Sin rival programado", "", False
    es_local = partido_usuario.local_id == mi_equipo.id
    op_id = partido_usuario.visitante_id if es_local else partido_usuario.local_id
    op = next((e for e in liga.equipos if e.id == op_id), None)
    l2 = (f"LIGA · J{partido_usuario.jornada} vs {getattr(op, 'nombre', '?')[:24]} "
          f"({'LOCAL' if es_local else 'VISITANTE'})")
    l3 = (f"DT {(getattr(op, 'estilo_dt', '') or '?').upper()}  ·  OVR {getattr(op, 'ovr_promedio', '?')}  ·  "
          f"Tu OVR {getattr(mi_equipo, 'ovr_promedio', '?')}")
    return "JUGAR", l2, l3, True


def _render_inicio(screen, estado, liga, mi_equipo, info, jugados, mouse_pos, click_pos) -> Optional[str]:
    """Tablero de Inicio: tabla, historial, JUGAR, avisos, panel de jornada y tu club."""
    partido_usuario, esta_finalizada, fase_copa, _rival = info
    foco = int(estado.get('hub_foco', 0))
    es_segunda = getattr(liga, 'division', 1) == 2
    azul = COLORS.get('azul', (0, 191, 255))
    dorado = COLORS.get('dorado', (255, 215, 0))

    # --- Tabla de posiciones ---
    try:
        draw_panel(screen, R_TABLA)
        ty = R_TABLA.y
        draw_text(screen, "TABLA DE POSICIONES", (32, ty + 10), size='md', color='azul')
        equipos_ordenados = sorted(liga.equipos, key=_clave_tabla, reverse=True)
        headers = ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]
        header_x = [32, 70, 318, 360, 402, 444, 486, 528, 570, 612]
        for h, x_pos in zip(headers, header_x):
            draw_text(screen, h, (x_pos, ty + 44), size='sm', color='dorado')
        pygame.draw.line(screen, azul, (28, ty + 66), (644, ty + 66), 1)
        n_total = len(equipos_ordenados)
        row_h = min(36, (R_TABLA.bottom - ty - 82) // max(1, n_total))
        for idx, eq in enumerate(equipos_ordenados, 1):
            y_pos = ty + 76 + (idx - 1) * row_h
            if es_segunda:
                row_color = 'verde' if idx <= 2 else 'blanco'           # suben 2
            else:
                row_color = ('verde' if idx <= 3 else                  # copa
                             'rojo' if idx >= n_total - 1 else 'blanco')  # bajan 2
            if eq.id == mi_equipo.id:
                sub = pygame.Rect(24, y_pos - 4, 624, max(4, row_h - 4))
                pygame.draw.rect(screen, (30, 45, 75), sub, border_radius=4)
                pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), sub, width=1, border_radius=4)
            dg = eq.gf - eq.gc
            valores = [str(idx), eq.nombre[:24], str(eq.pj), str(eq.pg), str(eq.pe), str(eq.pp),
                       str(eq.gf), str(eq.gc), f"+{dg}" if dg > 0 else str(dg), str(eq.puntos)]
            for v, x_pos in zip(valores, header_x):
                draw_text(screen, v, (x_pos, y_pos), size='sm', color=row_color)
    except Exception as e_table:
        logger.error(f"Error al renderizar la tabla: {e_table}")

    # --- Historial de tus partidos ---
    max_offset = max(0, len(jugados) - PARTIDOS_VISIBLES)
    r_up = pygame.Rect(R_HIST.right - 80, R_HIST.y + 6, 32, 26)
    r_down = pygame.Rect(R_HIST.right - 42, R_HIST.y + 6, 32, 26)
    try:
        draw_panel(screen, R_HIST)
        draw_text(screen, f"HISTORIAL DE PARTIDOS ({len(jugados)} jugados)",
                  (32, R_HIST.y + 8), size='sm', color='dorado')
        offset = min(estado.setdefault('hist_scroll_offset', 0), max_offset)
        estado['hist_scroll_offset'] = offset
        draw_styled_button(screen, r_up, "▲", r_up.collidepoint(mouse_pos), azul)
        draw_styled_button(screen, r_down, "▼", r_down.collidepoint(mouse_pos), azul)
        hy = R_HIST.y + 38
        if not jugados:
            draw_text(screen, "Aún no has jugado partidos esta temporada.", (32, hy), size='sm', color='blanco')
        for p in jugados[offset:offset + PARTIDOS_VISIBLES]:
            loc = next((e for e in liga.equipos if e.id == p.local_id), None)
            vis = next((e for e in liga.equipos if e.id == p.visitante_id), None)
            es_local = p.local_id == mi_equipo.id
            ug, rg = (p.goles_local, p.goles_visitante) if es_local else (p.goles_visitante, p.goles_local)
            col = 'verde' if ug > rg else ('rojo' if ug < rg else 'azul')
            ln = (f"J{p.jornada}:  {getattr(loc, 'nombre', '?')[:20]}  {p.goles_local} - "
                  f"{p.goles_visitante}  {getattr(vis, 'nombre', '?')[:20]}")
            draw_text(screen, ln, (32, hy), size='sm', color=col)
            hy += 23
    except Exception as e_hist:
        logger.error(f"Error al renderizar historial: {e_hist}")

    # --- JUGAR ---
    l1, l2, l3, habilitado = _textos_jugar(liga, mi_equipo, info)
    try:
        hover = R_JUGAR.collidepoint(mouse_pos) and habilitado
        draw_styled_button(screen, R_JUGAR, "", hover or foco == 0, COLORS.get('verde', (0, 255, 136)), habilitado)
        if foco == 0 and not hover:
            pygame.draw.rect(screen, dorado, R_JUGAR, width=3, border_radius=8)
        draw_text(screen, l1, (R_JUGAR.x + 20, R_JUGAR.y + 10), size='lg',
                  color='verde' if habilitado else 'blanco')
        draw_text(screen, l2, (R_JUGAR.x + 20, R_JUGAR.y + 48), size='sm',
                  color='dorado' if fase_copa else 'blanco')
        if l3:
            draw_text(screen, l3, (R_JUGAR.x + 20, R_JUGAR.y + 70), size='sm', color='azul')
    except Exception as e_jugar:
        logger.error(f"Error al dibujar JUGAR: {e_jugar}")

    # --- Línea de copa + alertas ---
    try:
        lineas = []
        if not fase_copa:
            from alpha_football.ui.copa_screen import linea_copa_user
            linea = linea_copa_user(estado)
            if linea:
                lineas.append((linea, 'dorado'))
        lineas += _alertas_inicio(estado, mi_equipo)
        for i, (texto, color) in enumerate(lineas[:4]):
            draw_text(screen, texto[:72], (R_JUGAR.x + 4, Y_AVISOS + i * 20), size='sm', color=color)
    except Exception as e_avisos:
        logger.error(f"Error al dibujar avisos: {e_avisos}")

    # --- Panel de jornada (reemplaza "otros partidos" y el overlay de resumen) ---
    r_prev, r_next = _rects_jornada()
    try:
        draw_panel(screen, R_JORNADA)
        if foco == 1:
            pygame.draw.rect(screen, dorado, R_JORNADA, width=2, border_radius=8)
        j = _jornada_vista(estado, liga)
        draw_text(screen, f"JORNADA {j} de {getattr(liga, 'num_jornadas', '?')}",
                  (R_JORNADA.x + 18, R_JORNADA.y + 10), size='md', color='dorado')
        draw_styled_button(screen, r_prev, "<", r_prev.collidepoint(mouse_pos), azul)
        draw_styled_button(screen, r_next, ">", r_next.collidepoint(mouse_pos), azul)
        equipos = {e.id: e for e in liga.equipos}
        partidos = sorted((p for p in getattr(liga, 'calendario', []) or [] if p.jornada == j),
                          key=lambda p: mi_equipo.id not in (p.local_id, p.visitante_id))
        row_h = min(24, (R_JORNADA.height - 56) // max(1, len(partidos)))
        y = R_JORNADA.y + 48
        if not partidos:
            draw_text(screen, "No hay partidos en esta jornada.", (R_JORNADA.x + 18, y), size='sm', color='blanco')
        cx = R_JORNADA.centerx
        for p in partidos:
            if mi_equipo.id in (p.local_id, p.visitante_id):
                pygame.draw.rect(screen, (30, 45, 75),
                                 pygame.Rect(R_JORNADA.x + 10, y - 2, R_JORNADA.width - 20, row_h), border_radius=4)
            n_loc = getattr(equipos.get(p.local_id), 'nombre', '?')[:24]
            n_vis = getattr(equipos.get(p.visitante_id), 'nombre', '?')[:24]
            if p.jugado:
                gl, gv = int(p.goles_local), int(p.goles_visitante)
                marcador = f"{gl} - {gv}"
                c_loc = 'verde' if gl > gv else ('rojo' if gl < gv else 'blanco')
                c_vis = 'verde' if gv > gl else ('rojo' if gv < gl else 'blanco')
            else:
                marcador, c_loc, c_vis = "vs", 'blanco', 'blanco'
            s_loc = get_font('sm').render(n_loc, True, COLORS.get(c_loc, (255, 255, 255)))
            screen.blit(s_loc, s_loc.get_rect(topright=(cx - 40, y)))
            s_res = get_font('sm').render(marcador, True, dorado)
            screen.blit(s_res, s_res.get_rect(midtop=(cx, y)))
            draw_text(screen, n_vis, (cx + 40, y), size='sm', color=c_vis)
            y += row_h
    except Exception as e_jor:
        logger.error(f"Error al dibujar el panel de jornada: {e_jor}")

    # --- Tu club: forma, goleador y presupuesto ---
    try:
        draw_panel(screen, R_CLUB)
        cx0, cy0 = R_CLUB.x + 18, R_CLUB.y + 10
        draw_text(screen, "TU CLUB", (cx0, cy0), size='sm', color='dorado')
        draw_text(screen, "Forma:", (cx0, cy0 + 30), size='sm', color='azul')
        fx = cx0 + 70
        for p in list(reversed(jugados[:5])):
            es_local = p.local_id == mi_equipo.id
            ug, rg = (p.goles_local, p.goles_visitante) if es_local else (p.goles_visitante, p.goles_local)
            letra, col = ('G', 'verde') if ug > rg else (('P', 'rojo') if ug < rg else ('E', 'azul'))
            caja = pygame.Rect(fx, cy0 + 28, 26, 24)
            pygame.draw.rect(screen, COLORS.get(col, azul), caja, width=2, border_radius=4)
            draw_text(screen, letra, (fx + 7, cy0 + 30), size='sm', color=col, shadow=False)
            fx += 32
        if not jugados:
            draw_text(screen, "sin partidos", (cx0 + 70, cy0 + 30), size='sm', color='blanco')
        goleador = max(mi_equipo.jugadores, key=lambda jj: getattr(jj, 'goles', 0), default=None)
        if goleador is not None and getattr(goleador, 'goles', 0) > 0:
            draw_text(screen, f"Goleador: {goleador.nombre} {goleador.apellido} ({goleador.goles})",
                      (cx0, cy0 + 62), size='sm', color='blanco')
        draw_text(screen, f"OVR {getattr(mi_equipo, 'ovr_promedio', 0)}  ·  Plantilla {len(mi_equipo.jugadores)}  ·  "
                          f"Presupuesto ${getattr(mi_equipo, 'balance', 0) / 1_000_000:.1f}M",
                  (cx0, cy0 + 94), size='sm', color='blanco')
    except Exception as e_club:
        logger.error(f"Error al dibujar Tu club: {e_club}")

    # --- Clics ---
    if click_pos:
        if R_JUGAR.collidepoint(click_pos):
            estado['hub_foco'] = 0
            if habilitado:
                return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
        elif r_up.collidepoint(click_pos):
            estado['hist_scroll_offset'] = max(0, estado.get('hist_scroll_offset', 0) - 1)
        elif r_down.collidepoint(click_pos):
            estado['hist_scroll_offset'] = min(max_offset, estado.get('hist_scroll_offset', 0) + 1)
        elif r_prev.collidepoint(click_pos):
            estado['hub_foco'] = 1
            _mover_jornada(estado, liga, -1)
        elif r_next.collidepoint(click_pos):
            estado['hub_foco'] = 1
            _mover_jornada(estado, liga, 1)
    return None


def _render_tarjetas(screen, estado, tab, mouse_pos, click_pos) -> Optional[str]:
    """Pestañas DIRECCIÓN / NEGOCIACIONES / OFICINA: tarjetas grandes que abren cada pantalla."""
    tarjetas = TARJETAS.get(tab, [])
    rects = _rects_tarjetas(len(tarjetas))
    foco = int(estado.get('hub_foco', 0))
    try:
        draw_text(screen, TITULOS.get(tab, tab.upper()), (32, 112), size='lg', color='dorado')
        n_ofertas = len(estado.get('ofertas_recibidas') or [])
        for i, ((titulo, sub, destino), rect) in enumerate(zip(tarjetas, rects)):
            hover = rect.collidepoint(mouse_pos)
            draw_styled_button(screen, rect, "", hover or i == foco, COLORS.get('azul', (0, 191, 255)))
            if i == foco and not hover:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
            draw_text(screen, titulo, (rect.x + 24, rect.y + 40), size='lg', color='blanco')
            draw_text(screen, sub, (rect.x + 24, rect.y + 90), size='sm', color='azul')
            if destino == 'ofertas_screen' and n_ofertas > 0:
                bx, by = rect.right - 30, rect.top + 30
                pygame.draw.circle(screen, (255, 68, 68), (bx, by), 16)
                bs = get_font('md').render(str(n_ofertas), True, (255, 255, 255))
                screen.blit(bs, bs.get_rect(center=(bx, by)))
    except Exception as e_tarj:
        logger.error(f"Error al dibujar las tarjetas de {tab}: {e_tarj}")
    if click_pos:
        for i, ((_t, _s, destino), rect) in enumerate(zip(tarjetas, rects)):
            if rect.collidepoint(click_pos):
                estado['hub_foco'] = i
                return _abrir(estado, destino)
    return None


# --- Renderizador del hub ═════════════════════════════════════════════════════

def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Hub de carrera (v2.4.0): columnas arriba y el contenido de la pestaña activa.
    Retorna la siguiente pantalla o None para seguir aquí.
    """
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        if not liga or not mi_equipo:
            logger.error("Error resiliente: No hay liga o equipo cargado en el estado de liga.")
            return "menu"

        try:
            inicializar_calendario_liga(liga)
        except Exception as error_fixtures:
            logger.error(f"Error al inicializar fixtures de liga: {error_fixtures}")

        # La copa del user avanza sin abrir su pantalla (partidos ajenos, paso a cuartos).
        # Solo se recalcula cuando cambia la jornada, la fase o los partidos jugados.
        try:
            from alpha_football.ui.copa_screen import sincronizar_copa_user

            def _clave_copa():
                return (getattr(liga, 'jornada_actual', 1), estado.get('copa_fase_actual'),
                        sum(1 for p in (estado.get('copa_grupo_partidos') or []) if p.get('jugado')))
            if estado.get('_hub_copa_sync') != _clave_copa():
                sincronizar_copa_user(estado)
                estado['_hub_copa_sync'] = _clave_copa()
        except Exception as e_sync:
            logger.error(f"Error al sincronizar la copa: {e_sync}")

        info = _info_partido(estado, liga, mi_equipo)
        partido_usuario, esta_finalizada, fase_copa, _rival = info
        jugados = sorted(
            (p for p in getattr(liga, 'calendario', [])
             if p.jugado and mi_equipo.id in (p.local_id, p.visitante_id)),
            key=lambda p: p.jornada, reverse=True)
        max_offset = max(0, len(jugados) - PARTIDOS_VISIBLES)

        tab = estado.get('hub_tab') if estado.get('hub_tab') in PESTANAS else 'inicio'
        bar_foco = int(estado.get('hub_bar_foco', 0)) % len(BARRA_MENU)
        if bar_foco < len(PESTANAS) and PESTANAS[bar_foco] != tab:
            bar_foco = PESTANAS.index(tab)          # la pestaña cambió desde otra pantalla
        foco = int(estado.get('hub_foco', 0))

        # --- Eventos ---
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        key_events = []
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click_pos = event.pos
                    elif event.button in (4, 5) and tab == 'inicio' and R_HIST.collidepoint(mouse_pos):
                        paso = -1 if event.button == 4 else 1
                        estado['hist_scroll_offset'] = max(0, min(max_offset, estado.get('hist_scroll_offset', 0) + paso))
                elif event.type == pygame.KEYDOWN:
                    key_events.append(event)
        except Exception as e_events:
            logger.error(f"Error al procesar eventos en league_screen: {e_events}")

        def _guardar_foco():
            estado['hub_tab'], estado['hub_bar_foco'], estado['hub_foco'] = tab, bar_foco, foco

        # --- Teclado ---
        for ev in key_events:
            if ev.key == pygame.K_j:
                _guardar_foco()
                return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
            if ev.key == pygame.K_r:
                tab, bar_foco, foco = 'inicio', 0, 1
            elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                paso = -1 if ev.key == pygame.K_LEFT else 1
                if tab == 'inicio' and foco == 1 and bar_foco == 0:
                    _mover_jornada(estado, liga, paso)
                else:
                    bar_foco = (bar_foco + paso) % len(BARRA_MENU)
                    if bar_foco < len(PESTANAS):
                        tab, foco = PESTANAS[bar_foco], 0
            elif ev.key in (pygame.K_UP, pygame.K_DOWN):
                if tab == 'inicio':
                    foco = 0 if ev.key == pygame.K_UP else 1
                else:
                    n = max(1, len(TARJETAS.get(tab, [])))
                    foco = (foco + (-1 if ev.key == pygame.K_UP else 1)) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                _guardar_foco()
                if bar_foco >= len(PESTANAS):
                    return _abrir(estado, DESTINO_DIRECTO[BARRA_MENU[bar_foco][0]])
                if tab == 'inicio':
                    if foco == 0:
                        return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
                else:
                    tarjetas = TARJETAS.get(tab, [])
                    if tarjetas:
                        return _abrir(estado, tarjetas[foco % len(tarjetas)][2])
            elif ev.key == pygame.K_ESCAPE:
                if tab != 'inicio':
                    tab, bar_foco, foco = 'inicio', 0, 0
                else:
                    return 'menu'

        # --- Clic en la barra ---
        rects = _rects_barra()
        if click_pos:
            for i, rect in enumerate(rects):
                if rect.collidepoint(click_pos):
                    if i < len(PESTANAS):
                        tab, bar_foco, foco = PESTANAS[i], i, 0
                        click_pos = None
                    else:
                        bar_foco = i
                        _guardar_foco()
                        return _abrir(estado, DESTINO_DIRECTO[BARRA_MENU[i][0]])
                    break
        _guardar_foco()

        # --- Fondo ---
        try:
            draw_gradient_bg(screen)
            draw_pitch_lines(screen)
        except Exception:
            screen.fill(COLORS.get('bg', (10, 14, 26)))
        try:
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))
        except Exception:
            pass

        # --- Barra de columnas ---
        try:
            n_ofertas = len(estado.get('ofertas_recibidas', []) or [])
            for i, ((clave, l1, l2, col), rect) in enumerate(zip(BARRA_MENU, rects)):
                color = COLORS.get(col, (0, 191, 255))
                activa = clave == tab
                _boton_barra(screen, rect, l1, l2, rect.collidepoint(mouse_pos) or activa, color,
                             foco=(i == bar_foco and not rect.collidepoint(mouse_pos)))
                if activa:
                    pygame.draw.rect(screen, color, pygame.Rect(rect.x + 8, rect.bottom + 2, rect.width - 16, 4))
                if clave == 'negociaciones' and n_ofertas > 0:
                    bx, by = rect.right - 12, rect.top + 10
                    pygame.draw.circle(screen, (255, 68, 68), (bx, by), 10)
                    bs = get_font('sm').render(str(n_ofertas), True, (255, 255, 255))
                    screen.blit(bs, bs.get_rect(center=(bx, by)))
        except Exception as e_barra:
            logger.error(f"Error al dibujar la barra: {e_barra}")

        # --- Cabecera ---
        try:
            pres_m = getattr(mi_equipo, 'balance', 0) / 1_000_000
            es_segunda = getattr(liga, 'division', 1) == 2
            cabecera = (f"{liga.nombre.upper()[:32]}  ·  {mi_equipo.nombre[:22]}  ·  "
                        f"{'2ª' if es_segunda else '1ª'} División  ·  T{estado.get('temporada', 1)}  ·  "
                        f"Jornada {getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
                        f"${pres_m:.1f}M")
            draw_text(screen, cabecera, (16, 82), size='sm', color='azul')
        except Exception as e_header:
            logger.error(f"Error al dibujar cabecera: {e_header}")

        if tab == 'inicio':
            destino = _render_inicio(screen, estado, liga, mi_equipo, info, jugados, mouse_pos, click_pos)
        else:
            destino = _render_tarjetas(screen, estado, tab, mouse_pos, click_pos)

        # --- Aviso temporal ---
        try:
            toast = estado.get('hub_toast')
            if toast and pygame.time.get_ticks() < toast[1]:
                texto, _hasta, color = (list(toast) + ['verde'])[:3]
                surf = get_font('md').render(texto, True, COLORS.get('bg', (10, 14, 26)))
                caja = surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 40)).inflate(40, 20)
                pygame.draw.rect(screen, COLORS.get(color, (0, 255, 136)), caja, border_radius=8)
                screen.blit(surf, surf.get_rect(center=caja.center))
            elif toast:
                estado.pop('hub_toast', None)
        except Exception as e_toast:
            logger.error(f"Error al dibujar el aviso: {e_toast}")

        return destino
```

Luego: `grep -n "league_resumen_j\|league_kbd_focus\|_resumen_jornada\|_rects_resumen" alpha_football/ main.py -r` → sin resultados.

- [ ] **Step 4: Quitar el test viejo de la barra**

En `tests/test_ui_v235.py`: borrar la función `test_barra_superior_lleva_a_cada_pantalla` completa y quitarla de la lista `tests = [...]` del `__main__`.

- [ ] **Step 5: Correr y verificar que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `12/12 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_ui_v235.py`
Expected: `5/5 tests pasaron`.

- [ ] **Step 6: Sin commit.**

---

### Task 4: GUARDAR sin salir

**Files:**
- Modify: `alpha_football/ui/save_slots_screen.py:170-195`
- Test: `tests/test_hub_v240.py`

**Interfaces:**
- Consumes: `league_screen._toast(estado, texto, color='verde', ms=3000)` (Task 3).
- Produces: guardar con éxito → retorna `estado.get('save_slots_return', 'league_screen')` y `estado['hub_toast'][0] == f"Guardado en slot {n}"`; botón **SALIR AL MENÚ** `pygame.Rect(360, 560, 240, 48)` → `"menu"`.

- [ ] **Step 1: Escribir el test que falla**

Agregar a `tests/test_hub_v240.py` y sumarlo a `TESTS`:

```python
def test_guardar_sin_salir():
    from alpha_football import save
    from alpha_football.ui import save_slots_screen
    orig_slot, orig_partida = save.guardar_en_slot, save.guardar_partida
    llamados = []
    save.guardar_en_slot = lambda est, n, nombre: llamados.append((n, nombre))
    save.guardar_partida = lambda est: llamados.append(('fallback', None))
    try:
        e = estado_carrera()
        e['save_slots_return'] = 'league_screen'
        click((140 + 260, 190 + 26))                     # slot 1
        assert save_slots_screen.render(screen, e) == 'league_screen'
        assert llamados and llamados[0][0] == 1, llamados
        assert e['hub_toast'][0] == "Guardado en slot 1"
        assert e['slot_activo'] == 1
        click((360 + 120, 560 + 24))                     # SALIR AL MENÚ
        assert save_slots_screen.render(screen, e) == 'menu'
    finally:
        save.guardar_en_slot, save.guardar_partida = orig_slot, orig_partida
    print("  test_guardar_sin_salir: OK")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `test_guardar_sin_salir: FAIL` (retorna `'menu'` en vez de `'league_screen'`).

- [ ] **Step 3: Implementar**

En `alpha_football/ui/save_slots_screen.py`, tras el guardado exitoso (~línea 170):

```python
                    # Recordar el slot activo para futuros autoguardados
                    estado['slot_activo'] = slot_n
                    return "menu"
                except Exception as e_save_error:
                    logger.error(f"Fallo al guardar en el slot {slot_n}: {e_save_error}. Intentando fallback.")
                    # Fallback de emergencia: guardar en el slot por defecto alpha_football_save.json
                    try:
                        save.guardar_partida(estado_juego)
                        logger.info("Guardado alternativo en ruta por defecto exitoso.")
                        return "menu"
                    except Exception as e_fatal:
                        logger.critical(f"No se pudo guardar la partida con ningún método: {e_fatal}.")
```
→
```python
                    # Recordar el slot activo para futuros autoguardados
                    estado['slot_activo'] = slot_n
                    # v2.4.0: guardar ya no saca de la partida; se vuelve al hub con un aviso.
                    from alpha_football.ui.league_screen import _toast
                    _toast(estado, f"Guardado en slot {slot_n}")
                    return estado.get('save_slots_return', 'league_screen')
                except Exception as e_save_error:
                    logger.error(f"Fallo al guardar en el slot {slot_n}: {e_save_error}. Intentando fallback.")
                    from alpha_football.ui.league_screen import _toast
                    # Fallback de emergencia: guardar en el slot por defecto alpha_football_save.json
                    try:
                        save.guardar_partida(estado_juego)
                        logger.info("Guardado alternativo en ruta por defecto exitoso.")
                        _toast(estado, "Guardado en el archivo por defecto (falló el slot)", color='dorado')
                    except Exception as e_fatal:
                        logger.critical(f"No se pudo guardar la partida con ningún método: {e_fatal}.")
                        _toast(estado, "No se pudo guardar la partida", color='rojo')
                    return estado.get('save_slots_return', 'league_screen')
```

Nota: si `EstadoJuego.from_dict` falla, `estado_juego` no existe y `save.guardar_partida(estado_juego)` lanza `NameError`, que cae en el `except` interno → toast rojo. Es el comportamiento buscado.

Botón nuevo, justo después del bloque de VOLVER (~línea 191, antes de `return None`):

```python
        # v2.4.0: salir al menú es una acción aparte (guardar ya no sale).
        salir_rect = pygame.Rect(360, 560, 240, 48)
        draw_button(screen, salir_rect, "SALIR AL MENÚ", salir_rect.collidepoint(mouse_pos))
        if click_pos and salir_rect.collidepoint(click_pos):
            return "menu"
```

Cambiar el subtítulo (línea ~89) por:
`"Guarda tu progreso en uno de los 5 slots. Sigues jugando después de guardar."`

- [ ] **Step 4: Correr y verificar que pasa**

Run: `PYTHONIOENCODING=utf-8 python tests/test_hub_v240.py`
Expected: `13/13 tests pasaron`.

- [ ] **Step 5: Sin commit.**

---

### Task 5: Verificación completa, capturas y bitácora

**Files:**
- Create (scratchpad, no en el repo): `capturas_hub.py`
- Modify: `context.md` (encabezado + bitácora v2.4.0 + ESTADO ACTUAL)

- [ ] **Step 1: Suite completa**

Run (Git Bash, desde la raíz):
```bash
for f in tests/test_*.py; do echo "== $f"; PYTHONIOENCODING=utf-8 python "$f" > /tmp/out.txt 2>&1 && tail -1 /tmp/out.txt || { echo "FAIL $f"; tail -20 /tmp/out.txt; }; done
```
Expected: ningún `FAIL`. Si un test viejo depende de la barra vieja o de `return "copa_screen"`, adaptarlo al comportamiento nuevo del spec (no revertir el código).

- [ ] **Step 2: Capturas headless**

Script en el scratchpad (`capturas_hub.py`), ejecutado desde la raíz del repo:

```python
import sys, os
sys.path.insert(0, os.getcwd())
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
sys.path.insert(0, os.path.join(os.getcwd(), 'tests'))
from test_hub_v240 import estado_carrera, estado_copa
from alpha_football.ui import league_screen

salida = sys.argv[1]
for nombre, fab, tab in [('inicio', estado_carrera, 'inicio'), ('inicio_copa', estado_copa, 'inicio'),
                         ('direccion', estado_carrera, 'direccion'),
                         ('negociaciones', estado_carrera, 'negociaciones'),
                         ('oficina', estado_carrera, 'oficina')]:
    e = fab()
    e['hub_tab'] = tab
    if nombre == 'inicio':
        e['ofertas_recibidas'] = [{}, {}]
        mi = e['mi_equipo']; mi.jugadores[e['alineacion_activa'].titulares[0]].lesion_partidos = 1
        league_screen._toast(e, "Guardado en slot 1")
    pygame.event.clear()
    league_screen.render(screen, e)
    pygame.image.save(screen, os.path.join(salida, f"hub_{nombre}.png"))
print("ok")
```

Run: `python <scratchpad>/capturas_hub.py <scratchpad>` y revisar las 5 PNG con Read. Verificar: nada se superpone (cabecera vs barra, avisos vs panel de jornada), textos no se cortan contra los bordes, tarjetas centradas, JUGAR muestra "COPA · Grupos F1 vs …" en `inicio_copa`. Ajustar coordenadas si hace falta y repetir.

- [ ] **Step 3: Probar en vivo (opcional si hay display)**

Run: `python main.py` → cargar una partida, recorrer las 6 columnas con mouse y teclado, jugar un partido de liga y volver a Inicio. Revisar el log por errores.

- [ ] **Step 4: Bitácora**

En `context.md`: actualizar `**Última actualización:**` y `**Sesión actual:**` (v2.4.0, sub-proyecto 1 de 6), agregar la sección `## Bitácora — v2.4.0 (claude, 2026-09-23)` antes de `## 🔴 ESTADO ACTUAL` con: hub por columnas, tarjetas, copa desde JUGAR (`preparar_partido_copa`, `sincronizar_copa_user`), `copa_screen` de consulta, panel de jornada único, alertas, guardar sin salir, tests (`tests/test_hub_v240.py`, 13 casos) y resultado de la suite. En ESTADO ACTUAL → "Lo que falta": validar en vivo v2.4.0; sub-proyecto 2 (Mentalidad, spec `docs/superpowers/specs/2026-09-23-mentalidad-design.md`) y 3-6 pendientes.

- [ ] **Step 5: Sin commit.** Reportar a Diego el resultado de la suite y las capturas.
