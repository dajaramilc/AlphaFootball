# Nacionalidades, renovación, eventos y notificaciones (v0.4.10.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Método elegido por Diego: NATIVO** → superpowers:executing-plans, en esta sesión.

**Goal:** Nacionalidad real de jugadores y DTs, aviso de renovación del jugador contento, 21 eventos aleatorios de vestuario con decisión y registro de noticias, CORREO convertido en NOTIFICACIONES (mensajes / correo) y progreso algo más rápido para los menores de 21.

**Architecture:** Lógica sin UI en módulos propios (`data/nacionalidades.py`, `eventos.py`) enganchada al cierre de jornada de liga que ya existe (`match_screen.finalizar_jornada_liga`). El correo gana un `canal` derivado del remitente; una pantalla nueva `notificaciones_screen` hace de portada y `correo_screen` se reutiliza como lista filtrada. Todo el estado nuevo vive en `datos_carrera` (se guarda solo).

**Tech Stack:** Python 3.10, pygame. Tests = scripts ejecutables (`python tests/test_x.py`), ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-04-nacionalidades-eventos-design.md`

## Global Constraints

- Versión nueva: **0.4.10.0** (vieja `vX.Y.Z` = `0.X.Y.Z`). Comentarios nuevos: `# v0.4.10.0`. No reescribir comentarios `# v4.x` viejos.
- **Git: sin commits hasta que Diego lo pida** (prueba todo al final). Nunca atribuir a Claude ni a una IA en git.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor.
- Comentarios y textos del juego en español. Humor de parodia, sin groserías fuertes.
- **Toda resolución de evento (elegida o por defecto) genera exactamente una noticia** en `datos_carrera['noticias']` (requisito "muy importante" de Diego: la futura sección NOTICIAS lee de ahí).
- Nada de esto aplica a amistosos ni a clubes de la IA (los eventos son solo del user).
- Los textos con `.format` no pueden llevar llaves literales `{}`.
- Cada test corre con `python tests/<archivo>.py` y debe terminar en `N/N tests pasaron`.

## Review Focus

1. **Borrar un correo con decisión pendiente** → no debe servir para esquivar la consecuencia: se aplica la opción por defecto antes de borrar (Task 9).
2. **El protagonista ya no está en el club** (vendido, cedido, libre) cuando se resuelve → el evento se cierra sin efectos y sin excepción (Task 7).
3. **Plantel sin el perfil que pide el evento** (sin polémicos, sin líder, sin extranjeros, sin jóvenes) → ese evento no se sortea; si ninguno aplica, no hay evento (Task 7/8).
4. **Save viejo** con correos sin `canal` ni `evento` y jugadores con el país de la liga → carga, se reparte por remitente y las nacionalidades se corrigen una sola vez (Tasks 2 y 4).
5. **Cambio de temporada con evento pendiente** (se limpian los correos viejos) → se resuelve por defecto antes de limpiar (Task 9).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/data/nacionalidades.py` (nuevo) | Tablas nombre→país (solo extranjeros), país de clubes internacionales, país de DTs, `nacionalidad_real` |
| `alpha_football/eventos.py` (nuevo) | Catálogo de 21 eventos, sorteo, efectos, promesas, resolución, registro de noticias |
| `alpha_football/ui/notificaciones_screen.py` (nuevo) | Portada: MENSAJES \| CORREO con los últimos 5 de cada lado |
| `alpha_football/correo.py` | `canal`, `de_canal`, `no_leidos(canal)`, remitente `presidente` |
| `alpha_football/ui/correo_screen.py` | Lista filtrada por canal + botones de decisión |
| `alpha_football/retiros.py`, `entrenadores.py`, `data/free_agents.py`, `competiciones.py` | Aplicar nacionalidades |
| `alpha_football/salidas.py`, `negociacion.py`, `models.py` | Aviso de renovación |
| `alpha_football/vestuario.py`, `directiva.py` | `ult_res` y correos del presidente |
| `alpha_football/desarrollo.py` | Factor de progreso ≤ 20 años |
| `main.py`, `ui/league_screen.py`, `ui/atajos.py`, `ui/ayuda.py`, `ui/match_screen.py` | Accesos, enganche de jornada, ayuda |

Runner común al final de cada archivo de test nuevo:

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

Cabecera común de cada archivo de test nuevo:

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

---

### Task 1: Progreso más rápido para menores de 21

**Files:**
- Modify: `alpha_football/desarrollo.py:24-36`
- Test: `tests/test_progreso_jovenes.py` (nuevo)

- [ ] **Step 1: Test que falla** — `tests/test_progreso_jovenes.py` (cabecera común sin `estado_carrera`, + runner):

```python
from alpha_football.desarrollo import _factor_progreso_edad as f


def test_menores_de_21_progresan_mas():
    assert f(16) == f(20) == 0.90
    assert f(21) == 0.75                     # los de 21 no cambian
    assert f(20) > f(21) > f(24) > f(27) > f(30) > f(31)


def test_resto_de_tramos_igual():
    assert (f(24), f(27), f(30), f(35)) == (0.55, 0.40, 0.25, 0.08)
```

- [ ] **Step 2:** `python tests/test_progreso_jovenes.py` → FAIL (`0.75 != 0.90`).
- [ ] **Step 3: Implementar** — en `_factor_progreso_edad`, antes de `if edad <= 21:`:

```python
    if edad <= 20:      # v0.4.10.0: los menores de 21 progresan un poco más rápido (antes 0.75)
        return 0.90
```

- [ ] **Step 4:** `python tests/test_progreso_jovenes.py` → `2/2`. Correr también `python tests/test_potencial.py` y `python tests/test_cantera.py`; si alguno fijaba 0.75 para ≤ 20, actualizar el número esperado a 0.90.

---

### Task 2: Nacionalidad real de los jugadores

**Files:**
- Create: `alpha_football/data/nacionalidades.py`
- Modify: `alpha_football/retiros.py:82-90` (`asignar_nacionalidades`) y `:110-113` (`generar_regen`), `alpha_football/data/free_agents.py` (constructor de `Jugador`), `alpha_football/competiciones.py:~545` (pools internacionales)
- Test: `tests/test_nacionalidades.py` (nuevo)

**Interfaces — Produces:**
- `nacionalidades.nacionalidad_real(nombre_completo: str) -> str` (`""` si no está)
- `nacionalidades.NACIONALIDAD_JUGADOR: dict[str, str]`, `PAIS_CLUB: dict[str, str]`, `NACIONALIDAD_DT: dict[str, str]`
- `retiros.nacionalizar(j, pais_defecto: str, forzar: bool) -> None`

- [ ] **Step 1: Volcar los nombres a revisar** (script temporal en el scratchpad, no en el repo):

```python
# scratchpad/volcar_nombres.py — python volcar_nombres.py > nombres.txt
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
d = json.load(open(r'C:\Users\diego\Downloads\AlphaFootball\alpha_football_edited_db.json', encoding='utf-8'))
for liga, equipos in d.items():
    if not isinstance(equipos, list):
        continue
    for e in equipos:
        print(f"## {liga} | {e['nombre']}")
        print("; ".join(f"{j['nombre']} {j['apellido']}" for j in e['jugadores']))
```

- [ ] **Step 2: Escribir `data/nacionalidades.py`.** Leer `nombres.txt` liga por liga y anotar **solo a los extranjeros reconocibles** (el local recibe el país de su liga por defecto). Regla: si no está claro a quién parodia el nombre, no se anota. Estructura exacta del archivo:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Nacionalidades reales (v0.4.10.0)
Nacionalidad de la persona real a la que parodia cada nombre. _POR_PAIS lleva SOLO a los
extranjeros (nacionalidad ≠ país de la liga donde arrancan): el local recibe el país de su liga
(retiros.asignar_nacionalidades). Los nombres inventados o dudosos no se anotan.
"""
from __future__ import annotations

import unicodedata

# país → nombres parodia completos ("Nombre Apellido", tal cual están en los datos)
_POR_PAIS: dict[str, list[str]] = {
    "Francia": ["Leny Yoro-joven", "Paul Pogbanned", "Karim Benzemóvil", "Antoine Griezman-mediocre"],
    "Argentina": ["Lisandro El Carnicero", "Mauro Icardi-flojo"],
    "Bélgica": ["Thibaut Murois", "Eden Hazarrica"],
    # … un bloque por país con TODOS los extranjeros reconocidos de nombres.txt y los 22 libres
}

# clubes de Champions/Libertadores (sin liga jugable): su país hace de "país de la liga"
PAIS_CLUB: dict[str, str] = {
    "Bayerna de Munich": "Alemania", "Borussia Dormund": "Alemania", "Piamonte Calcio": "Italia",
    "Inter de Milan Roto": "Italia", "Milan Abuelo": "Italia", "Paris Saint-Gayman": "Francia",
    "Benfica Maldito": "Portugal", "Puerto FC": "Portugal",
    "Peñaroloso": "Uruguay", "Nacionall de Montevideo": "Uruguay", "Colo Colo Roto": "Chile",
    "Olimpia Abuelo": "Paraguay", "Barcelona Falso de Guayaquil": "Ecuador",
    "Liga de Quito Rota": "Ecuador", "Bolivar Sin Aire": "Bolivia", "Universitario de la U": "Perú",
    "Boca Amargo": "Argentina", "Palmeirras": "Brasil",
}

# DT parodia → país (los 69 de data/entrenadores.DT_REALES, sin repetir alias)
NACIONALIDAD_DT: dict[str, str] = {
    "Pep Guardiolo": "España", "Mikel Artetazo": "España", "Arne Slote": "Países Bajos",
    "Rubén Amorfo": "Portugal", "Enzo Maresco": "Italia", "Thomas Franco": "Dinamarca",
    "Xabi Alonzo": "España", "Hansi Flink": "Alemania", "Diego Cimeone": "Argentina",
    # … el resto de DT_REALES, uno por DT
}


def _norm(texto: str) -> str:
    sin = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    return " ".join(sin.lower().split())


NACIONALIDAD_JUGADOR: dict[str, str] = {n: pais for pais, nombres in _POR_PAIS.items() for n in nombres}
_NORMALIZADO = {_norm(n): p for n, p in NACIONALIDAD_JUGADOR.items()}
_DT_NORMALIZADO = {_norm(n): p for n, p in NACIONALIDAD_DT.items()}


def nacionalidad_real(nombre_completo: str) -> str:
    """País real del jugador parodiado, o '' si no está en la tabla."""
    return NACIONALIDAD_JUGADOR.get(nombre_completo) or _NORMALIZADO.get(_norm(nombre_completo), '')


def nacionalidad_dt(nombre: str) -> str:
    return NACIONALIDAD_DT.get(nombre) or _DT_NORMALIZADO.get(_norm(nombre), '')
```

  Los tres `# …` de arriba marcan dónde va el volumen de datos de este paso (no son código pendiente): se completa recorriendo `nombres.txt` entero (18 ligas) y `DT_REALES` entero. Los nombres de país de los 8 jugables se escriben igual que en `paises.PAISES` (`Inglaterra`, `España`, `Italia`, `Brasil`, `Argentina`, `Colombia`, `Uruguay`, `Ecuador`). Los 22 de `NOMBRES_LIBRES` van **todos** (no tienen liga).

- [ ] **Step 3: Test que falla** — `tests/test_nacionalidades.py` (cabecera común + runner):

```python
import json
from alpha_football.data import nacionalidades as N
from alpha_football.data.free_agents import NOMBRES_LIBRES
from alpha_football.data.entrenadores import DT_REALES
from alpha_football import retiros as R
from alpha_football.models import Jugador

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nombres_base():
    d = json.load(open(os.path.join(RAIZ, 'alpha_football_edited_db.json'), encoding='utf-8'))
    return {f"{j['nombre']} {j['apellido']}" for v in d.values() if isinstance(v, list)
            for e in v for j in e['jugadores']} | {f"{a} {b}" for a, b in NOMBRES_LIBRES}


def test_tabla_sin_huerfanos():
    base = {N._norm(n) for n in _nombres_base()}
    huerfanos = [n for n in N.NACIONALIDAD_JUGADOR if N._norm(n) not in base]
    assert len(N.NACIONALIDAD_JUGADOR) >= 600, len(N.NACIONALIDAD_JUGADOR)
    assert len(huerfanos) <= 0.05 * len(N.NACIONALIDAD_JUGADOR), huerfanos[:10]


def test_muestras_conocidas():
    assert N.nacionalidad_real("Thibaut Murois") == "Bélgica"
    assert N.nacionalidad_real("Lisandro El Carnicero") == "Argentina"
    assert N.nacionalidad_real("thibaut  murois") == "Bélgica"        # normalizado
    assert N.nacionalidad_real("Julián Sofoco") == ""                  # inventado


def test_libres_y_dts_cubiertos():
    assert all(N.nacionalidad_real(f"{a} {b}") for a, b in NOMBRES_LIBRES)
    assert all(N.nacionalidad_dt(dt) for dt, _estilo in DT_REALES.values())


def test_asignar_real_local_y_una_sola_vez():
    e = estado_carrera('premier')
    todos = [j for eq in e['liga'].equipos for j in eq.jugadores]
    for j in todos:
        j.nacionalidad = 'Inglaterra'                 # save viejo: todos con el país de la liga
    R.asignar_nacionalidades(e)
    ext = next(j for j in todos if N.nacionalidad_real(f"{j.nombre} {j.apellido}"))
    assert ext.nacionalidad == N.nacionalidad_real(f"{ext.nombre} {ext.apellido}") != 'Inglaterra'
    assert any(j.nacionalidad == 'Inglaterra' for j in todos)
    assert e['datos_carrera']['nac_reales'] is True
    ext.nacionalidad = 'Marte'                        # ya migrado: no se vuelve a pisar
    R.asignar_nacionalidades(e)
    assert ext.nacionalidad == 'Marte'


def test_regen_de_pais_sin_lista_toma_el_del_club():
    viejo = Jugador(nombre="Jean", apellido="Dupont", posicion="DEL", ataque=70, defensa=40, fisico=65,
                    tecnica=70, mental=65, id=991, edad=36, nacionalidad="Francia")
    regen = R.generar_regen(viejo, random.Random(1), 992, set(), pais_club="Inglaterra")
    assert regen.nacionalidad == "Inglaterra"
    viejo.nacionalidad = "Brasil"
    assert R.generar_regen(viejo, random.Random(1), 993, set(), pais_club="Inglaterra").nacionalidad == "Brasil"
```

- [ ] **Step 4:** `python tests/test_nacionalidades.py` → FAIL (no existe `nac_reales`, `generar_regen` no acepta `pais_club`).

- [ ] **Step 5: `retiros.py`** — reemplazar `asignar_nacionalidades` completo:

```python
def nacionalizar(j: Any, pais_defecto: str, forzar: bool = False) -> None:
    """v0.4.10.0: nacionalidad real si el nombre está en la tabla; si no, el país de su liga."""
    from alpha_football.data.nacionalidades import nacionalidad_real
    actual = getattr(j, 'nacionalidad', '')
    if forzar or not actual:
        real = nacionalidad_real(f"{j.nombre} {j.apellido}")
        if real:
            j.nacionalidad = real
            return
    if not actual:
        j.nacionalidad = pais_defecto


def asignar_nacionalidades(estado: dict) -> None:
    """Nacionalidad real (tabla) o, si falta, el país de la liga donde juega. v0.4.10.0: la tabla
    pisa lo guardado una sola vez por partida (saves viejos: todos tenían el país de su liga)."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.data.nacionalidades import PAIS_CLUB
    dc = estado.setdefault('datos_carrera', {})
    forzar = not dc.get('nac_reales')
    for liga, tipo, _div in ligas_de_la_partida(estado):
        pais = PAIS_POR_LIGA.get(tipo, '')
        for eq in liga.equipos:
            for j in eq.jugadores:
                nacionalizar(j, PAIS_CLUB.get(eq.nombre, pais), forzar)
    for j in estado.get('free_agents_list') or []:
        nacionalizar(j, '', forzar)
    dc['nac_reales'] = True
```

  En `generar_regen`: firma `def generar_regen(retirado, rng, id_nuevo, nombres_usados, pais_club: str = '') -> Any:` y reemplazar la línea `pais = getattr(retirado, 'nacionalidad', '') or 'España'` por:

```python
    pais = getattr(retirado, 'nacionalidad', '') or pais_club or 'España'
    if pais not in NOMBRES_POR_PAIS and pais_club in NOMBRES_POR_PAIS:
        pais = pais_club      # v0.4.10.0: sin lista de nombres de su país, es un canterano local
```

  Buscar con Grep las llamadas a `generar_regen(` en `retiros.py` y pasarles `pais_club=PAIS_POR_LIGA.get(tipo, '')` donde el `tipo` de la liga esté a mano en ese bucle (si el bucle no lo tiene, se deja el valor por defecto).

- [ ] **Step 6: `data/free_agents.py`** — en `get_free_agents`, justo después de crear cada `Jugador(...)` (variable `j`):

```python
            from alpha_football.data.nacionalidades import nacionalidad_real
            j.nacionalidad = nacionalidad_real(f"{nombre} {apellido}")    # v0.4.10.0
```

- [ ] **Step 7: pools internacionales** — leer `competiciones.py` alrededor de la línea 545 (`get_pool_champions`, `get_pool_libertadores`). En el punto donde quedan creados los `Equipo` de la copa (lista de equipos con `jugadores`), añadir:

```python
            from alpha_football.retiros import nacionalizar           # v0.4.10.0
            from alpha_football.data.nacionalidades import PAIS_CLUB
            for _eq in equipos_pool:
                for _j in getattr(_eq, 'jugadores', []) or []:
                    nacionalizar(_j, PAIS_CLUB.get(_eq.nombre, ''))
```

  (`equipos_pool` = el nombre real de la variable en ese punto.) Si un nombre de club del pool no coincide con una clave de `PAIS_CLUB`, corregir la clave en `PAIS_CLUB`.

- [ ] **Step 8:** `python tests/test_nacionalidades.py` → `5/5`. Correr `python tests/test_v236.py` y `python tests/test_cantera.py` (tocan regens/nacionalidad) → pasan.

---

### Task 3: Nacionalidad de los DTs

**Files:**
- Modify: `alpha_football/entrenadores.py:79-87` (`_nuevo`), `:104-127` (`asegurar_dts`), `alpha_football/ui/prepartido_screen.py:584`, `alpha_football/ui/otras_ligas_screen.py:298`
- Test: `tests/test_nacionalidades.py`

**Interfaces — Consumes:** `nacionalidades.nacionalidad_dt(nombre) -> str`, `retiros.PAIS_POR_LIGA`. **Produces:** `dt['nacionalidad']: str` en todo DT.

- [ ] **Step 1: Test que falla** — añadir a `tests/test_nacionalidades.py`:

```python
def test_dts_con_nacionalidad():
    from alpha_football import entrenadores as EN
    e = estado_carrera('premier', idx=5)
    EN.asegurar_dts(e)
    d = EN.dts(e)
    assert all(dt.get('nacionalidad') for dt in d['por_club'].values())
    assert all(dt.get('nacionalidad') for dt in d['libres'])
    pep = next(dt for dt in d['por_club'].values() if dt['nombre'] == "Pep Guardiolo")
    assert pep['nacionalidad'] == "España"
    for dt in d['por_club'].values():                 # save viejo: sin el campo
        dt.pop('nacionalidad')
    EN.asegurar_dts(e)
    assert all(dt.get('nacionalidad') for dt in d['por_club'].values())
```

- [ ] **Step 2:** `python tests/test_nacionalidades.py` → FAIL en `test_dts_con_nacionalidad`.

- [ ] **Step 3: Implementar en `entrenadores.py`.** `_nuevo` gana el parámetro `nacionalidad: str = ''` y lo guarda (`'nacionalidad': str(nacionalidad or '')` en el dict). Añadir bajo `_nuevo`:

```python
def _pais_de_club(estado: dict, equipo) -> str:
    """v0.4.10.0: país de la liga donde juega el club ('' si no se encuentra)."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.retiros import PAIS_POR_LIGA
    for liga, tipo, _div in ligas_de_la_partida(estado):
        if any(eq is equipo for eq in liga.equipos):
            return PAIS_POR_LIGA.get(tipo, '')
    return ''


def _nacionalidad_dt(estado: dict, nombre: str, equipo=None, rng=None) -> str:
    from alpha_football.data.nacionalidades import nacionalidad_dt
    from alpha_football.retiros import PAIS_POR_LIGA
    paises = sorted(set(PAIS_POR_LIGA.values()))
    return (nacionalidad_dt(nombre) or (_pais_de_club(estado, equipo) if equipo is not None else '')
            or (rng or random.Random(nombre)).choice(paises))
```

  En `asegurar_dts`: pasar `nacionalidad=_nacionalidad_dt(estado, nombre, eq)` al `_nuevo` de los clubes; `nacionalidad=_nacionalidad_dt(estado, str(x['nombre']))` al de los libres del editor; y para los libres generados sacar el nombre a una variable (`nom = nombre_generado(rng)`) y pasar `nacionalidad=_nacionalidad_dt(estado, nom, rng=rng)`. Al final de la función, completar saves viejos:

```python
    por_id = {str(eq.id): eq for eq, _liga in clubes(estado)}      # v0.4.10.0: saves sin el campo
    for cid, dt in d['por_club'].items():
        if not dt.get('nacionalidad'):
            dt['nacionalidad'] = _nacionalidad_dt(estado, dt.get('nombre', ''), por_id.get(cid))
    for dt in d['libres']:
        if not dt.get('nacionalidad'):
            dt['nacionalidad'] = _nacionalidad_dt(estado, dt.get('nombre', ''))
```

  Buscar con Grep los demás `_nuevo(` del módulo (interinos en `despedir`/`_reemplazar`) y pasarles `nacionalidad=_nacionalidad_dt(estado, <nombre>, equipo)`.

- [ ] **Step 4: Mostrarla.** `prepartido_screen.py:584`: `return f"DT: {dt['nombre'][:18]} ({dt.get('nacionalidad', '')[:12]}) · {_NE.get(dt['estilo'], '')}"` (si `nacionalidad` está vacía, sin paréntesis). `otras_ligas_screen.py:298`: no cabe otra columna con 18 caracteres → dejar el nombre y añadir la nacionalidad solo si el ancho lo permite tras leer ese bloque; si no cabe, no se toca esa pantalla.

- [ ] **Step 5:** `python tests/test_nacionalidades.py` → `6/6`. `python tests/test_carrera_dt_v320.py` y `python tests/test_editor_libres_dts.py` → pasan.

---

### Task 4: Canales del correo y remitente "presidente"

**Files:**
- Modify: `alpha_football/correo.py`, `alpha_football/vestuario.py:197-214`, `alpha_football/directiva.py:174-177`
- Test: `tests/test_notificaciones.py` (nuevo)

**Interfaces — Produces:**
- `correo.canal(msg: dict) -> 'mensaje' | 'correo'`
- `correo.de_canal(estado, canal: str) -> list[dict]` (orden de la bandeja)
- `correo.no_leidos(estado, canal: Optional[str] = None) -> int`
- `correo.REMITENTES['presidente']`

- [ ] **Step 1: Test que falla** — `tests/test_notificaciones.py` (cabecera común + runner):

```python
from alpha_football import correo as C


def test_canal_por_remitente_y_explicito():
    e = estado_carrera()
    a = C.enviar(e, 'jugador', "a", "x")
    b = C.enviar(e, 'presidente', "b", "x")
    c = C.enviar(e, 'directiva', "c", "x")
    d = C.enviar(e, 'medico', "d", "x")
    assert [C.canal(m) for m in (a, b, c, d)] == ['mensaje', 'mensaje', 'correo', 'correo']
    d['canal'] = 'mensaje'
    assert C.canal(d) == 'mensaje'
    assert C.canal({'remitente': 'jugador', 'asunto': 'save viejo'}) == 'mensaje'


def test_de_canal_y_no_leidos():
    e = estado_carrera()
    for i in range(7):
        C.enviar(e, 'jugador', f"m{i}", "x")
    for i in range(3):
        C.enviar(e, 'club', f"c{i}", "x")
    assert [m['asunto'] for m in C.de_canal(e, 'mensaje')[:5]] == ['m6', 'm5', 'm4', 'm3', 'm2']
    assert len(C.de_canal(e, 'correo')) == 3
    assert (C.no_leidos(e), C.no_leidos(e, 'mensaje'), C.no_leidos(e, 'correo')) == (10, 7, 3)
    C.marcar_leido(e, C.de_canal(e, 'correo')[0]['id'])
    assert (C.no_leidos(e), C.no_leidos(e, 'correo')) == (9, 2)


def test_presidente_escribe_sin_plantilla_formal():
    e = estado_carrera(); e['dt_nombre'] = "Diego Jaramillo"
    m = C.enviar(e, 'presidente', "Bien hecho", "Así se gana un clásico.")
    texto = C.formatear(e, m)
    assert "Estimado" not in texto and "Atentamente" not in texto
    assert texto.endswith("El presidente")
    assert "Atentamente" in C.formatear(e, C.enviar(e, 'directiva', "Objetivos", "…"))
```

- [ ] **Step 2:** `python tests/test_notificaciones.py` → FAIL (`canal` no existe).

- [ ] **Step 3: `correo.py`.** Añadir `'presidente': "Presidente"` a `REMITENTES` (con `# v0.4.10.0`). Tras `accion`:

```python
# v0.4.10.0: NOTIFICACIONES = MENSAJES (lo personal) + CORREO (lo institucional del club)
CANAL_MENSAJE = ('jugador', 'presidente')


def canal(msg: dict) -> str:
    return msg.get('canal') or ('mensaje' if msg.get('remitente') in CANAL_MENSAJE else 'correo')


def de_canal(estado: dict, cual: str) -> list:
    return [m for m in bandeja(estado) if canal(m) == cual]
```

  En `formatear`, antes del `if remitente == 'jugador' …`:

```python
    if remitente == 'presidente':          # v0.4.10.0: personal, sin "Estimado míster… Atentamente"
        return f"{cuerpo}\n\nEl presidente"
```

  Reemplazar `no_leidos`:

```python
def no_leidos(estado: dict, cual: Optional[str] = None) -> int:
    return sum(1 for m in bandeja(estado) if not m.get('leido') and (cual is None or canal(m) == cual))
```

- [ ] **Step 4: Correos que pasan al presidente** (mismo `C.accion`, solo cambian remitente, asunto y cuerpo):

  `vestuario.py` — clásico ganado:
```python
                C.enviar(estado, 'presidente', f"¡Ganamos el clásico a {rival.nombre}!",
                         "Míster, hoy da gusto ser presidente de este club. La gente está feliz y yo también. "
                         "Felicite de mi parte a los muchachos.")
```
  tres victorias:
```python
            C.enviar(estado, 'presidente', "Tres victorias seguidas",
                     "Míster, tres seguidas. Así da gusto ir al palco. Siga así, que la gente ya se ilusiona.")
```
  tres derrotas:
```python
            C.enviar(estado, 'presidente', "Tres derrotas seguidas: tenemos que hablar",
                     "Míster, tres derrotas al hilo. Me paran en la calle para preguntarme qué pasa y ya no sé "
                     "qué contestar. Necesito una reacción ya.",
                     C.accion('objetivos_screen', "VER OBJETIVOS"))
```
  `directiva.py:174` — confianza baja:
```python
        C.enviar(estado, 'presidente', "Estoy preocupado",
                 f"Míster, le soy sincero: la confianza de la directiva en usted cayó a {dc['confianza']}. "
                 "Yo lo sigo defendiendo, pero necesito resultados para seguir haciéndolo.",
                 C.accion('objetivos_screen', "VER OBJETIVOS"))
```

- [ ] **Step 5:** `python tests/test_notificaciones.py` → `3/3`. Correr `python tests/test_vestuario_v310.py`, `python tests/test_correo_v470.py`; donde un test busque los asuntos/remitentes viejos de esos 4 correos, actualizar la aserción al texto nuevo (`'presidente'`, asuntos de arriba).

---

### Task 5: Pantalla NOTIFICACIONES y accesos

**Files:**
- Create: `alpha_football/ui/notificaciones_screen.py`
- Modify: `alpha_football/ui/correo_screen.py:90-145`, `main.py:153,336`, `alpha_football/ui/league_screen.py:365,630-633,1027,1219`, `alpha_football/ui/atajos.py:48`, `alpha_football/ui/ayuda.py:364,824-864`
- Test: `tests/test_notificaciones.py`

**Interfaces — Consumes:** `correo.canal/de_canal/no_leidos`. **Produces:** pantalla `'notificaciones_screen'`; `notificaciones_screen.abrir(estado, canal, msg=None) -> 'correo_screen'`; `estado['correo_canal']` (`'mensaje'|'correo'`) filtra `correo_screen`.

- [ ] **Step 1: Test que falla** — añadir a `tests/test_notificaciones.py`:

```python
def test_portada_y_lista_filtrada():
    from alpha_football.ui import notificaciones_screen as NS, correo_screen as CS
    e = estado_carrera()
    for i in range(7):
        C.enviar(e, 'jugador', f"m{i}", "hola míster")
    C.enviar(e, 'club', "c0", "informe")
    assert [m['asunto'] for m in NS.ultimos(e, 'mensaje')] == ['m6', 'm5', 'm4', 'm3', 'm2']
    assert NS.render(screen, e) is None                       # dibuja sin romperse
    m3 = next(m for m in C.bandeja(e) if m['asunto'] == 'm3')
    assert NS.abrir(e, 'mensaje', m3) == 'correo_screen'
    assert e['correo_canal'] == 'mensaje' and CS._mensajes(e)[e['correo_sel']] is m3
    assert all(C.canal(m) == 'mensaje' for m in CS._mensajes(e))
    assert NS.abrir(e, 'correo') == 'correo_screen' and e['correo_sel'] == 0
    assert [m['asunto'] for m in CS._mensajes(e)] == ['c0']
    assert CS.render(screen, e) is None


def test_m_abre_notificaciones_y_hub():
    import main
    from alpha_football.ui import league_screen
    assert main.SCREEN_MODULES['notificaciones_screen'].endswith('notificaciones_screen')
    assert any(t[2] == 'notificaciones_screen' and t[0] == "NOTIFICACIONES"
               for t in league_screen.TARJETAS['oficina'])
```

  (Si el dict de `main.py:153` o el de `league_screen.py:365` tienen otro nombre que `SCREEN_MODULES`/`TARJETAS`, usar el real; `test_finanzas_v290.py:179` ya usa `league_screen.TARJETAS`.)

- [ ] **Step 2:** `python tests/test_notificaciones.py` → FAIL (módulo no existe).

- [ ] **Step 3: Crear `ui/notificaciones_screen.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Notificaciones (v0.4.10.0). OFICINA > NOTIFICACIONES (tecla M).
Portada del buzón: MENSAJES (jugadores y presidente) a la izquierda y CORREO (el club) a la
derecha, con los últimos 5 de cada lado. Clic/Enter abre la lista completa de ese canal
(correo_screen filtrada). Teclado: ← → panel, ↑ ↓ elegir, Enter abrir, Esc volver.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import correo as C

logger = logging.getLogger(__name__)

R_MENSAJES = pygame.Rect(16, 76, 618, 620)
R_CORREO = pygame.Rect(646, 76, 618, 620)
PANELES = (('mensaje', "MENSAJES", R_MENSAJES), ('correo', "CORREO", R_CORREO))
N_PREVIA = 5
ALTO_ITEM = 100


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def rect_item(panel: int, i: int) -> pygame.Rect:
    r = PANELES[panel][2]
    return pygame.Rect(r.x + 10, r.y + 52 + i * ALTO_ITEM, r.width - 20, ALTO_ITEM - 8)


def rect_todos(panel: int) -> pygame.Rect:
    r = PANELES[panel][2]
    return pygame.Rect(r.x + 10, r.bottom - 58, 220, 46)


def ultimos(estado: dict, canal: str) -> list:
    return C.de_canal(estado, canal)[:N_PREVIA]


def abrir(estado: dict, canal: str, msg: Optional[dict] = None) -> str:
    """Abre la lista completa del canal, con `msg` seleccionado (o el más reciente)."""
    lista = C.de_canal(estado, canal)
    estado['correo_canal'] = canal
    estado['correo_sel'] = next((i for i, m in enumerate(lista) if m is msg), 0)
    return 'correo_screen'


def _pendiente(m: dict) -> bool:
    ev = m.get('evento')
    return bool(ev) and ev.get('resuelto') is None


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        foco = list(estado.get('notif_foco') or [0, 0])
        listas = [ultimos(estado, c) for c, _t, _r in PANELES]
        mouse_pos = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    foco[0] = 0 if ev.key == pygame.K_LEFT else 1
                elif ev.key == pygame.K_DOWN:
                    foco[1] += 1
                elif ev.key == pygame.K_UP:
                    foco[1] -= 1
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    lista = listas[foco[0]]
                    estado['notif_foco'] = foco
                    return abrir(estado, PANELES[foco[0]][0], lista[foco[1]] if lista else None)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
        foco[1] = max(0, min(foco[1], len(listas[foco[0]]) - 1))
        estado['notif_foco'] = foco
        if click:
            if _volver().collidepoint(click):
                return 'league_screen'
            for p, (canal, _t, _r) in enumerate(PANELES):
                if rect_todos(p).collidepoint(click):
                    return abrir(estado, canal)
                for i, m in enumerate(listas[p]):
                    if rect_item(p, i).collidepoint(click):
                        estado['notif_foco'] = [p, i]
                        return abrir(estado, canal, m)

        draw_gradient_bg(screen)
        draw_text(screen, "NOTIFICACIONES", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{C.no_leidos(estado)} sin leer  ·  ← → panel · ↑ ↓ elegir · Enter abrir · Esc volver",
                  (16, 48), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        for p, (canal, titulo, r) in enumerate(PANELES):
            draw_panel(screen, r)
            k = C.no_leidos(estado, canal)
            draw_text(screen, titulo + (f"  ·  {k} sin leer" if k else ""), (r.x + 16, r.y + 14), size='md',
                      color='dorado' if k else 'blanco')
            if not listas[p]:
                draw_text(screen, "Nada por aquí.", (r.x + 16, r.y + 64), size='sm', color='blanco')
            for i, m in enumerate(listas[p]):
                ri = rect_item(p, i)
                if foco == [p, i] or ri.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (40, 60, 95), ri, border_radius=6)
                cab = f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  T{m['temporada']} J{m['jornada']}"
                if _pendiente(m):
                    cab += "  ·  DECISIÓN PENDIENTE"
                draw_text(screen, cab, (ri.x + 8, ri.y + 4), size='sm', color='rojo' if _pendiente(m) else 'azul',
                          shadow=False)
                draw_text(screen, m['asunto'][:56], (ri.x + 8, ri.y + 28), size='sm',
                          color='blanco' if m.get('leido') else 'dorado', shadow=False)
                previa = " ".join(str(m.get('cuerpo', '')).split())[:64]
                draw_text(screen, previa, (ri.x + 8, ri.y + 54), size='sm', color='azul', shadow=False)
            draw_button(screen, rect_todos(p), "VER TODOS", rect_todos(p).collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en notificaciones_screen: {e}", exc_info=True)
        return 'league_screen'
```

- [ ] **Step 4: `correo_screen.py` filtrada.** Añadir antes de `render`:

```python
def _mensajes(estado: dict) -> list:
    """v0.4.10.0: la lista del canal abierto desde NOTIFICACIONES (sin canal: toda la bandeja)."""
    cual = estado.get('correo_canal')
    return C.de_canal(estado, cual) if cual else C.bandeja(estado)
```

  En `render`: las 3 apariciones de `mensajes = C.bandeja(estado)` pasan a `mensajes = _mensajes(estado)`; los tres `return 'league_screen'` de Esc/VOLVER (no el del `except`) pasan a `return 'notificaciones_screen'`; el título pasa a:

```python
        cual = estado.get('correo_canal')
        draw_text(screen, {'mensaje': "MENSAJES", 'correo': "CORREO"}.get(cual, "CORREO"), (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{len(mensajes)} en total  ·  {C.no_leidos(estado, cual)} sin leer  ·  "
                          f"↑/↓ elegir · Enter acción · Supr borrar · Esc volver", (16, 48), size='sm', color='azul')
```

- [ ] **Step 5: Accesos.**
  - `main.py:153`: añadir `'notificaciones_screen': 'alpha_football.ui.notificaciones_screen',      # v0.4.10.0`.
  - `main.py:336`: `destino = 'notificaciones_screen' if ev.key == pygame.K_m else 'options_screen'`.
  - `league_screen.py:365`: `("NOTIFICACIONES", "Mensajes de jugadores y presidente, y correo del club", 'notificaciones_screen'),   # v0.4.10.0`.
  - `league_screen.py:633`: `avisos.insert(0, (f"{k} notificaci{'ones' if k != 1 else 'ón'} sin leer (OFICINA > NOTIFICACIONES)", 'dorado'))`.
  - `league_screen.py:1027`: `n_correo if destino == 'notificaciones_screen' else 0`.
  - `league_screen.py:1219`: `return 'notificaciones_screen'`.
  - Grep `'correo_screen'` en `alpha_football/ui/foco.py`, `league_screen.py` (`_abrir`) y `main.py` por si hay listas de pantallas válidas (p. ej. foco, música, transiciones): añadir `'notificaciones_screen'` donde esté `'correo_screen'`.
  - `atajos.py:48`: añadir `'notificaciones_screen': "← → Panel · ↑ ↓ Elegir · Enter Abrir · O Opciones · H Ayuda · ESC Volver",`.
  - `ayuda.py:364`: añadir `'notificaciones_screen': "Mensajes de jugadores y presidente a la izquierda; correo del club a la derecha. Últimos 5 de cada uno.",` y, junto a `AYUDA['correo_screen']`:

```python
def _ayuda_notificaciones(estado: dict) -> list:     # v0.4.10.0
    from alpha_football.ui import notificaciones_screen as NS
    return [(NS.R_MENSAJES, "Mensajes", "Lo personal: lo que te escriben tus jugadores y el presidente."),
            (NS.R_CORREO, "Correo", "Lo institucional: directiva, secretaría, médicos, cantera, patrocinadores y prensa."),
            (NS.rect_todos(0), "Ver todos", "Abre la lista completa de ese lado. Clic en un mensaje lo abre directo.")]


AYUDA['notificaciones_screen'] = _ayuda_notificaciones
```
  (Respetar la forma real de las tuplas de ayuda de `_ayuda_correo`.)

- [ ] **Step 6:** `python tests/test_notificaciones.py` → `5/5`. Correr `python tests/test_teclado_v420.py`, `python tests/test_hub_v240.py`, `python tests/test_ayuda_v390.py`, `python tests/test_correo_v470.py`, `python tests/test_ux_v360.py`: donde esperen `'correo_screen'` como destino de M/hub/sobre o el texto "CORREO" de la tarjeta, actualizar a `'notificaciones_screen'`/"NOTIFICACIONES".

---

### Task 6: El jugador contento pide renovar

**Files:**
- Modify: `alpha_football/models.py` (campo + `to_dict`/`from_dict` junto a `descontento_avisado`), `alpha_football/salidas.py` (`limpiar`, `cierre_jornada`, `al_renovar`), `alpha_football/negociacion.py` (ningún cambio si `al_renovar` basta)
- Test: `tests/test_renovacion_aviso.py` (nuevo)

**Interfaces — Produces:** `Jugador.renovacion_avisada: bool`; `salidas.revisar_renovaciones(estado, rng=None) -> list[Jugador]`.

- [ ] **Step 1: Test que falla** — `tests/test_renovacion_aviso.py` (cabecera común + runner):

```python
from alpha_football import correo as C, salidas as S, negociacion as NG
from alpha_football.finanzas import salario_mercado


def _prep(e, mitad=True):
    liga = e['liga']
    liga.jornada_actual = (liga.num_jornadas // 2 + 1) if mitad else 1
    js = e['mi_equipo'].jugadores
    for j in js:
        j.contrato_anios, j.moral = 3, 70
    return js


def _avisos(e):
    return [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']]


def test_avisa_al_contento_en_ultimo_anio():
    e = estado_carrera(); js = _prep(e)
    js[0].contrato_anios, js[0].moral = 1, 80
    assert S.revisar_renovaciones(e) == [js[0]]
    m = _avisos(e)[0]
    assert m['remitente'] == 'jugador' and m['accion']['renovar'] == js[0].id and m['accion']['texto'] == "RENOVAR"
    assert js[0].renovacion_avisada
    assert S.revisar_renovaciones(e) == [] and len(_avisos(e)) == 1       # una sola vez


def test_no_avisa_si_no_cumple():
    e = estado_carrera(); js = _prep(e)
    js[0].contrato_anios, js[0].moral = 1, 74                  # moral baja
    js[1].contrato_anios, js[1].moral, js[1].pide_salir = 1, 90, True
    js[2].contrato_anios, js[2].moral, js[2].prestamo = 1, 90, {'dueno': 'X'}
    js[3].contrato_anios, js[3].moral = 2, 90                  # no es su último año
    assert S.revisar_renovaciones(e) == []
    e2 = estado_carrera(); js2 = _prep(e2, mitad=False)        # primera mitad: todavía no
    js2[0].contrato_anios, js2[0].moral = 1, 90
    assert S.revisar_renovaciones(e2) == []


def test_uno_por_jornada_el_mejor_primero():
    e = estado_carrera(); js = _prep(e)
    cand = sorted(js, key=lambda j: -j.overall)[:3]
    for j in cand:
        j.contrato_anios, j.moral = 1, 90
    assert S.revisar_renovaciones(e) == [cand[0]]
    assert S.revisar_renovaciones(e) == [cand[1]]


def test_renovar_tras_el_aviso_da_moral_extra_y_limpia():
    e = estado_carrera(); js = _prep(e)
    j = js[0]; j.contrato_anios, j.moral = 1, 80
    S.revisar_renovaciones(e)
    NG.renovar(e, j, salario_mercado(j), 3, 1.5)
    assert j.moral == 80 + S.MORAL_RENOVAR_BIEN + S.MORAL_RENOVAR_AVISO
    assert not j.renovacion_avisada


def test_guardado_del_campo():
    from alpha_football.models import Jugador
    j = Jugador(nombre="A", apellido="B", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    assert j.renovacion_avisada is False
```

- [ ] **Step 2:** `python tests/test_renovacion_aviso.py` → FAIL.

- [ ] **Step 3: `models.py`.** Tras `descontento_avisado: bool = False`: `renovacion_avisada: bool = False       # v0.4.10.0: ya escribió pidiendo renovar este contrato`. Grep `descontento_avisado` en `models.py` y replicar el campo en la serialización y la carga exactamente igual (misma forma, clave `"renovacion_avisada"`).

- [ ] **Step 4: `salidas.py`.** Constantes junto a `MORAL_RENOVAR_BIEN`:

```python
MORAL_RENOVAR_AVISO = 5          # v0.4.10.0: extra si renuevas después de que te lo pidió
UMBRAL_QUIERE_RENOVAR = 75
TEXTOS_QUIERE_RENOVAR = {
    'lider': "Míster, este vestuario es mi casa y no me veo en otro lado. Se me acaba el contrato en verano "
             "y quiero seguir liderando este grupo. Siéntese con mi agente cuando pueda.",
    'profesional': "Míster, estoy a gusto, trabajo bien aquí y mi contrato termina al final de la temporada. "
                   "Me gustaría dejarlo resuelto pronto para concentrarme solo en jugar.",
    'mercenario': "Míster, estoy contento aquí, no le voy a mentir. Se me acaba el contrato y prefiero firmar "
                  "con ustedes antes de escuchar a otros… si los números acompañan, claro.",
    'polemico': "Míster, mire que no soy de decir estas cosas, pero aquí estoy bien. Se me vence el contrato: "
                "renuévenme antes de que cambie de opinión.",
    'normal': "Míster, estoy muy contento en el club y mi contrato termina al final de la temporada. "
              "Me encantaría quedarme. ¿Podemos hablar de la renovación?",
}
```

  Función nueva antes de `cierre_jornada`:

```python
def revisar_renovaciones(estado: dict, rng: Optional[random.Random] = None) -> list:
    """v0.4.10.0: un jugador contento (moral ≥ 75) en su último año escribe pidiendo renovar.
    Desde la mitad de la temporada, uno por jornada (el mejor primero) y una vez por contrato."""
    from alpha_football import correo as C
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return []
    if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 22) or 22) // 2:
        return []
    cand = [j for j in list(getattr(mi, 'jugadores', []) or [])
            if int(getattr(j, 'contrato_anios', 0) or 0) == 1 and int(j.moral) >= UMBRAL_QUIERE_RENOVAR
            and not j.pide_salir and not j.salida_forzada and not getattr(j, 'prestamo', None)
            and not getattr(j, 'renovacion_avisada', False)]
    if not cand:
        return []
    j = max(cand, key=lambda x: x.overall)
    texto = TEXTOS_QUIERE_RENOVAR.get(j.personalidad, TEXTOS_QUIERE_RENOVAR['normal'])
    C.enviar(estado, 'jugador', f"{_nombre(j)} quiere renovar", f"{texto}\n{_nombre(j)}",
             {'pantalla': 'negociacion_screen', 'texto': "RENOVAR", 'renovar': j.id})
    j.renovacion_avisada = True
    return [j]
```

  En `cierre_jornada`, tras `revisar_descontento(estado, rng)`: `revisar_renovaciones(estado, rng)`.
  En `al_renovar`, al final (fuera del `if`):

```python
    if getattr(jugador, 'renovacion_avisada', False):      # v0.4.10.0: nos lo pidió y cumplimos
        jugador.moral = min(100, int(jugador.moral) + MORAL_RENOVAR_AVISO)
        jugador.renovacion_avisada = False
```
  En `limpiar(j)`: añadir `j.renovacion_avisada = False`.

- [ ] **Step 5:** `python tests/test_renovacion_aviso.py` → `5/5`. `python tests/test_mercado_v440.py` → pasa.

---

### Task 7: Motor de eventos (`eventos.py`): efectos, noticias, resolución, promesas, sorteo

**Files:**
- Create: `alpha_football/eventos.py`
- Modify: `alpha_football/vestuario.py:205` (`ult_res`)
- Test: `tests/test_eventos.py` (nuevo)

**Interfaces — Produces:**
- `eventos.EVENTOS: list[dict]`, `eventos.POR_ID: dict[str, dict]` (catálogo; en esta tarea solo `rina`, el resto en Task 8)
- `eventos.va_mal(estado) -> bool`
- `eventos.aplicar(estado, efectos: list[tuple], prot: list[Jugador], rng=None) -> list[str]`
- `eventos.registrar_noticia(estado, titular, cuerpo, tipo='vestuario', jugadores=None, evento='', opcion=None) -> dict`
- `eventos.noticias(estado) -> list[dict]`
- `eventos.sortear(estado, rng=None, forzar: Optional[str] = None) -> Optional[dict]` (el mensaje enviado)
- `eventos.pendiente(estado) -> Optional[dict]`
- `eventos.resolver(estado, msg_id: int, indice: int, rng=None) -> list[str]`
- `eventos.resolver_pendientes(estado, rng=None) -> int`
- `eventos.revisar_promesas(estado) -> None`
- `eventos.cierre_jornada(estado, rng=None) -> None`
- `msg['evento'] = {'id', 'protagonistas': [ids], 'opciones': [textos], 'resuelto': None|int, 'resumen': [str]}`

**Formato de efectos** (lista de tuplas `(clave, quien, valor)`):
- `quien`: `'j'` (1er protagonista), `'j2'` (2º), `'plantel'`, `'otros:N'` (N disponibles al azar que no son protagonistas).
- `valor`: `int`, `float` o tupla `(lo, hi)` → `rng.randint`.
- claves: `moral`, `energia`, `forma` (nota que entra a `notas_recientes`), `sancion` (partidos de liga), `lesion` (partidos de baja), `progreso`, `dinero` (fracción de la suma de salarios de `quien`; + cobra, − paga), `promesa` (`{'tipo': 'minutos'|'aumento', 'jornadas': n, 'falla': -m}`).
- especiales: `('confianza', None, n)`, `('texto', "frase")`, `('azar', prob, [efectos_si], [efectos_no])`.

- [ ] **Step 1: Test que falla** — `tests/test_eventos.py` (cabecera común + runner):

```python
from alpha_football import correo as C, eventos as EV, sanciones as S


def _base(mal=False):
    e = estado_carrera()
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
    if mal:
        e['datos_carrera']['ult_res'] = ['P', 'P', 'E']
    return e


def test_va_mal_por_derrotas():
    assert not EV.va_mal(_base())
    assert EV.va_mal(_base(mal=True))


def test_aplicar_efectos_basicos():
    e = _base(); js = e['mi_equipo'].jugadores; a, b = js[0], js[1]
    saldo = e['mi_equipo'].balance
    lineas = EV.aplicar(e, [('moral', 'j', -10), ('moral', 'plantel', 2), ('energia', 'j', -20),
                            ('sancion', 'j', 2), ('lesion', 'j2', 1), ('forma', 'j', 5.0),
                            ('progreso', 'j2', 0.4), ('dinero', 'j', 0.02), ('confianza', None, -3),
                            ('texto', "Nada más.")], [a, b], random.Random(1))
    assert a.moral == 62 and b.moral == 72 and a.energia == 80.0
    assert S.partidos_sancion(a, 'liga') == 2 and b.lesion_partidos == 1
    assert a.notas_recientes[-1] == 5.0 and abs(b.progreso_desarrollo - 0.4) < 1e-9
    assert e['mi_equipo'].balance == saldo + int(a.salario * 0.02)
    assert len(lineas) == 10 and lineas[-1] == "Nada más."


def test_aplicar_acota_y_otros():
    e = _base(); js = e['mi_equipo'].jugadores
    js[0].moral, js[0].energia = 3, 5.0
    EV.aplicar(e, [('moral', 'j', -50), ('energia', 'j', -50), ('energia', 'otros:3', -15)], [js[0]], random.Random(2))
    assert js[0].moral == 0 and js[0].energia == 0.0
    assert sum(1 for j in js[1:] if j.energia == 85.0) == 3


def test_rina_domina_con_polemico_y_mala_racha():
    veces = 0
    for s in range(60):
        e = _base(mal=True)
        e['mi_equipo'].jugadores[4].personalidad = 'polemico'
        m = EV.sortear(e, random.Random(s))
        veces += bool(m and m['evento']['id'] == 'rina')
    assert veces >= 15, veces                         # ~45% de evento × la riña pesa casi todo


def test_sin_polemico_no_hay_rina_y_no_rompe():
    e = _base(mal=True)
    assert EV.sortear(e, random.Random(1), forzar='rina') is None


def test_probabilidad_mayor_si_va_mal():
    def tasa(mal):
        n = 0
        for s in range(300):
            e = _base(mal=mal); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
            n += EV.sortear(e, random.Random(s)) is not None
        return n
    assert tasa(True) > tasa(False)


def test_resolver_aplica_registra_noticia_y_no_repite():
    e = _base(mal=True); pol = e['mi_equipo'].jugadores[4]; pol.personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    assert m['remitente'] == 'jugador' and C.canal(m) == 'mensaje' and len(m['evento']['opciones']) == 3
    assert EV.pendiente(e) is m and EV.sortear(e, random.Random(2), forzar='rina') is None   # hay uno pendiente
    lineas = EV.resolver(e, m['id'], 1, random.Random(3))                # apartar 2 partidos
    assert lineas and S.partidos_sancion(pol, 'liga') == 2
    assert m['evento']['resuelto'] == 1 and m['evento']['resumen'] == lineas
    n = EV.noticias(e)
    assert len(n) == 1 and n[0]['evento'] == 'rina' and n[0]['opcion'] == 1 and n[0]['titular'] and n[0]['cuerpo']
    assert pol.id in n[0]['jugadores']
    assert EV.resolver(e, m['id'], 0) == [] and len(EV.noticias(e)) == 1  # ya resuelto: nada
    e['datos_carrera']['eventos_vistos']['rina'] = EV._abs(e)             # enfriamiento de 6 jornadas
    assert all((x[0]['id'] != 'rina') for x in EV._candidatos(e, random.Random(5)))


def test_pendiente_se_resuelve_por_defecto():
    e = _base(mal=True); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    assert EV.resolver_pendientes(e, random.Random(1)) == 1
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1


def test_protagonista_que_ya_no_esta():
    e = _base(mal=True); pol = e['mi_equipo'].jugadores[4]; pol.personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    e['mi_equipo'].jugadores.remove(pol)
    assert EV.resolver(e, m['id'], 0)                 # devuelve la línea de cierre, sin excepción
    assert m['evento']['resuelto'] == -1 and EV.noticias(e) == []


def test_ult_res_lo_lleva_el_vestuario():
    import inspect
    from alpha_football import vestuario
    assert "ult_res" in inspect.getsource(vestuario.post_partido_user)
```

- [ ] **Step 2:** `python tests/test_eventos.py` → FAIL (no existe `eventos`).

- [ ] **Step 3: Crear `alpha_football/eventos.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Eventos aleatorios de vestuario (v0.4.10.0)
Un sorteo por jornada de liga del user. El evento llega por correo (MENSAJES si lo escribe el
jugador, CORREO si lo informa el club) y pide una decisión; cada opción tiene efectos en moral,
forma, energía, sanción, lesión, dinero, confianza y desarrollo. Sin responder, a la jornada
siguiente se aplica la opción por defecto.
IMPORTANTE: toda resolución deja una noticia en datos_carrera['noticias'] (titular + cuerpo en
tono de prensa): de ahí leerá la futura sección NOTICIAS. Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football import correo as C

logger = logging.getLogger(__name__)

PROB_BASE = 0.12
PROB_MAL = 0.45
ENFRIAMIENTO = 6            # jornadas sin repetir el mismo evento
MAX_NOTICIAS = 100
JORNADAS_MIN_TABLA = 4      # antes de esto la tabla no dice si el equipo va mal


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _nom(j) -> str:
    return f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def _plantel(estado: dict) -> list:
    return list(getattr(estado.get('mi_equipo'), 'jugadores', []) or [])


def _disp(estado: dict) -> list:
    return [j for j in _plantel(estado) if j.disponible]


def _jornada(estado: dict) -> list:
    from alpha_football.salidas import _clave_jornada
    return _clave_jornada(estado)


def _abs(estado: dict) -> int:
    t, j = _jornada(estado)
    return t * 100 + j


def va_mal(estado: dict) -> bool:
    """2+ derrotas en los últimos 3 partidos, o muy por debajo del puesto esperado en la tabla."""
    if list(_dc(estado).get('ult_res', []))[-3:].count('P') >= 2:
        return True
    try:
        from alpha_football.entrenadores import _va_mal
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        return bool(liga is not None and mi is not None and _jornada(estado)[1] >= JORNADAS_MIN_TABLA
                    and _va_mal(liga, mi))
    except Exception as e:
        logger.debug(f"No se pudo leer la tabla para los eventos: {e}")
        return False


# ---------------------------------------------------------------- noticias
def noticias(estado: dict) -> list:
    return _dc(estado).setdefault('noticias', [])


def registrar_noticia(estado: dict, titular: str, cuerpo: str, tipo: str = 'vestuario',
                      jugadores: Optional[list] = None, evento: str = '', opcion: Optional[int] = None) -> dict:
    """Guarda una noticia (lo más nuevo primero). La futura sección NOTICIAS lee de aquí."""
    lista = noticias(estado)
    t, j = _jornada(estado)
    n = {'id': max((int(x.get('id', 0)) for x in lista), default=0) + 1, 'temporada': t, 'jornada': j,
         'tipo': tipo, 'titular': str(titular), 'cuerpo': str(cuerpo), 'jugadores': list(jugadores or []),
         'evento': evento, 'opcion': opcion}
    lista.insert(0, n)
    del lista[MAX_NOTICIAS:]
    return n


# ---------------------------------------------------------------- efectos
def _objetivos(estado: dict, quien, prot: list, rng: random.Random) -> list:
    if quien == 'j':
        return prot[:1]
    if quien == 'j2':
        return prot[1:2]
    if quien == 'plantel':
        return _plantel(estado)
    if isinstance(quien, str) and quien.startswith('otros:'):
        otros = [j for j in _disp(estado) if j not in prot]
        return rng.sample(otros, min(int(quien[6:]), len(otros)))
    return []


def _dinero(monto: int) -> str:
    return f"${abs(int(monto)):,}".replace(',', '.')


def _frase(clave: str, quien: str, v) -> str:
    if clave == 'moral':
        return f"{quien}: moral {v:+d}"
    if clave == 'energia':
        return f"{quien}: energía {v:+d}"
    if clave == 'forma':
        return f"{quien}: forma {'al alza' if v >= 6.5 else 'a la baja'}"
    if clave == 'sancion':
        return f"{quien}: apartado {v} partido{'s' if v != 1 else ''} de liga"
    if clave == 'lesion':
        return f"{quien}: baja {v} partido{'s' if v != 1 else ''}"
    if clave == 'progreso':
        return f"{quien}: acelera su desarrollo"
    return f"{quien}: le diste tu palabra"


def aplicar(estado: dict, efectos: list, prot: list, rng: Optional[random.Random] = None) -> list:
    """Aplica los efectos y devuelve una línea por efecto (para el resumen del correo)."""
    from alpha_football import sanciones as S
    azar = rng or random.Random()
    mi = estado.get('mi_equipo')
    out = []
    for ef in efectos or []:
        clave = ef[0]
        if clave == 'azar':
            out += aplicar(estado, ef[2] if azar.random() < ef[1] else ef[3], prot, azar)
            continue
        if clave == 'texto':
            out.append(ef[1])
            continue
        if clave == 'confianza':
            from alpha_football import directiva as D
            _dc(estado)['confianza'] = max(0, min(100, D.confianza(estado) + int(ef[2])))
            out.append(f"Confianza de la directiva {int(ef[2]):+d}")
            continue
        _, quien, valor = ef
        objs = _objetivos(estado, quien, prot, azar)
        if not objs:
            continue
        etiqueta = "El plantel" if quien == 'plantel' else ", ".join(_nom(j) for j in objs)
        if clave == 'dinero':
            monto = int(sum(int(getattr(j, 'salario', 0) or 0) for j in objs) * valor)
            mi.balance = int(mi.balance) + monto
            out.append(("Multa cobrada: " if monto >= 0 else "Gasto del club: ") + _dinero(monto))
            continue
        v = azar.randint(*valor) if isinstance(valor, tuple) else valor
        for j in objs:
            if clave == 'moral':
                j.moral = max(0, min(100, int(j.moral) + v))
            elif clave == 'energia':
                j.energia = max(0.0, min(100.0, float(j.energia) + v))
            elif clave == 'forma':
                j.notas_recientes = (list(getattr(j, 'notas_recientes', []) or []) + [float(v)])[-5:]
            elif clave == 'sancion':
                S.sumar_sancion(j, int(v), 'liga')
            elif clave == 'lesion':
                j.lesion_partidos = int(getattr(j, 'lesion_partidos', 0) or 0) + int(v)
            elif clave == 'progreso':
                j.progreso_desarrollo = float(getattr(j, 'progreso_desarrollo', 0.0) or 0.0) + float(v)
            elif clave == 'promesa':
                ahora = _abs(estado)
                _dc(estado).setdefault('promesas', []).append(
                    {'tipo': v['tipo'], 'jugador': j.id, 'creada': ahora, 'vence': ahora + int(v['jornadas']),
                     'falla': int(v['falla']), 'salario': int(getattr(j, 'salario', 0) or 0)})
        out.append(_frase(clave, etiqueta, v))
    return out


# ---------------------------------------------------------------- promesas
def revisar_promesas(estado: dict) -> None:
    """Promesas del DT (minutos, aumento): cumplidas se borran; vencidas sin cumplir, el jugador estalla."""
    ahora = _abs(estado)
    por_id = {j.id: j for j in _plantel(estado)}
    quedan = []
    for p in list(_dc(estado).get('promesas', [])):
        j = por_id.get(p.get('jugador'))
        if j is None:
            continue
        if p['tipo'] == 'aumento' and int(getattr(j, 'salario', 0) or 0) > int(p.get('salario', 0)):
            continue
        if p['tipo'] == 'minutos' and ahora > int(p.get('creada', ahora)) and not int(getattr(j, 'jornadas_sin_jugar', 0) or 0):
            continue
        if ahora < int(p['vence']):
            quedan.append(p)
            continue
        j.moral = max(0, min(100, int(j.moral) + int(p['falla'])))
        que = "los minutos que me prometió" if p['tipo'] == 'minutos' else "el aumento que me prometió"
        C.enviar(estado, 'jugador', f"{_nom(j)}: usted no cumplió",
                 f"Míster, sigo esperando {que}. Yo cumplí mi parte y usted no la suya. Que conste.\n{_nom(j)}")
        registrar_noticia(estado, f"{_nom(j)}, molesto con el técnico",
                          f"El jugador asegura en su entorno que el entrenador no cumplió {que.replace('me prometió', 'le prometió')}.",
                          jugadores=[j.id], evento='promesa_rota')
    _dc(estado)['promesas'] = quedan


# ---------------------------------------------------------------- catálogo
def _uno(estado: dict, rng: random.Random, filtro=lambda j: True) -> Optional[list]:
    c = [j for j in _disp(estado) if filtro(j)]
    return [rng.choice(c)] if c else None


def _dos(estado: dict, rng: random.Random, f1=lambda j: True, f2=lambda j: True) -> Optional[list]:
    a = _uno(estado, rng, f1)
    if not a:
        return None
    b = [j for j in _disp(estado) if j is not a[0] and f2(j)]
    return a + [rng.choice(b)] if b else None


EVENTOS: list = [
    {'id': 'rina', 'peso': 4, 'peso_mal': 60, 'solo_mal': True, 'remitente': 'jugador', 'defecto': 2,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'polemico'),
     'asunto': "{j} armó una riña en el vestuario",
     'cuerpo': "A ver, {dt}, se lo digo por escrito porque en el vestuario ya me oyeron todos: este equipo da "
               "pena y el primer responsable es usted. Hoy casi nos vamos a las manos y la próxima no me agarra "
               "nadie. Usted de fútbol sabe lo que yo de ballet. Si no le gusta lo que lee, ya sabe dónde "
               "encontrarme: en la cancha no, porque ahí usted ni aparece.\n{j}",
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('moral', 'j', -10), ('moral', 'plantel', 2), ('dinero', 'j', 0.02)],
          'titular': "{club} multa a {j} por la riña del vestuario",
          'noticia': "El club sancionó económicamente a {j} tras el altercado y el mensaje subido de tono que "
                     "envió al entrenador. El plantel respalda la medida."},
         {'texto': "APARTARLO 2 PARTIDOS", 'efectos': [('sancion', 'j', 2), ('moral', 'j', -15), ('moral', 'plantel', 4)],
          'titular': "{j}, apartado dos partidos tras insultar al técnico",
          'noticia': "Mano dura en {club}: {j} no estará en los dos próximos partidos de liga por la riña del "
                     "vestuario. El grupo cierra filas con el entrenador."},
         {'texto': "DEJARLO PASAR", 'efectos': [('moral', 'plantel', -6), ('confianza', None, -3)],
          'titular': "Riña en el vestuario de {club} y nadie pone orden",
          'noticia': "{j} se encaró con sus compañeros e insultó al técnico, que optó por mirar a otro lado. "
                     "En el plantel y en la directiva cayó mal."},
     ]},
]
POR_ID = {ev['id']: ev for ev in EVENTOS}


# ---------------------------------------------------------------- sorteo y resolución
def pendiente(estado: dict) -> Optional[dict]:
    return next((m for m in C.bandeja(estado) if (m.get('evento') or {}).get('resuelto', 0) is None), None)


def _candidatos(estado: dict, rng: random.Random, forzar: Optional[str] = None) -> list:
    mal = va_mal(estado)
    ahora = _abs(estado)
    vistos = _dc(estado).setdefault('eventos_vistos', {})
    res = []
    for ev in EVENTOS:
        if forzar:
            if ev['id'] != forzar:
                continue
        elif (ev.get('solo_mal') and not mal) or ahora - int(vistos.get(ev['id'], -999)) < ENFRIAMIENTO:
            continue
        try:
            prot = ev['elige'](estado, rng)
        except Exception as e:
            logger.error(f"Evento {ev['id']}: no se pudo elegir protagonista: {e}")
            prot = None
        if prot:
            res.append((ev, prot, ev.get('peso_mal', ev['peso']) if mal else ev['peso']))
    return res


def _fmt(texto: str, estado: dict, prot: list) -> str:
    mi = estado.get('mi_equipo')
    return texto.format(
        j=_nom(prot[0]), j2=_nom(prot[1]) if len(prot) > 1 else '',
        club=getattr(mi, 'nombre', 'el club'), pais=getattr(prot[0], 'nacionalidad', '') or 'su país',
        dt=(str(estado.get('dt_nombre', '') or '').split() or ['míster'])[-1])


def sortear(estado: dict, rng: Optional[random.Random] = None, forzar: Optional[str] = None) -> Optional[dict]:
    """Sortea el evento de la jornada y envía su correo. `forzar`: id de evento (tests / depuración)."""
    azar = rng or random.Random()
    if pendiente(estado) is not None:
        return None
    if not forzar and azar.random() >= (PROB_MAL if va_mal(estado) else PROB_BASE):
        return None
    cands = _candidatos(estado, azar, forzar)
    if not cands:
        return None
    ev, prot, _peso = azar.choices(cands, weights=[c[2] for c in cands])[0]
    msg = C.enviar(estado, ev['remitente'], _fmt(ev['asunto'], estado, prot), _fmt(ev['cuerpo'], estado, prot))
    msg['evento'] = {'id': ev['id'], 'protagonistas': [j.id for j in prot],
                     'opciones': [o['texto'] for o in ev['opciones']], 'resuelto': None, 'resumen': []}
    _dc(estado).setdefault('eventos_vistos', {})[ev['id']] = _abs(estado)
    return msg


def resolver(estado: dict, msg_id: int, indice: int, rng: Optional[random.Random] = None) -> list:
    """Aplica la opción elegida, registra la noticia y devuelve el resumen ([] si ya estaba resuelto)."""
    msg = next((m for m in C.bandeja(estado) if m.get('id') == msg_id), None)
    evd = (msg or {}).get('evento')
    if not evd or evd.get('resuelto') is not None:
        return []
    ev = POR_ID.get(evd.get('id'))
    por_id = {j.id: j for j in _plantel(estado)}
    prot = [por_id[i] for i in evd.get('protagonistas', []) if i in por_id]
    if ev is None or len(prot) < len(evd.get('protagonistas', [])):
        evd['resuelto'] = -1
        evd['resumen'] = ["El asunto se cerró solo: el jugador ya no está en el club."]
        return evd['resumen']
    indice = max(0, min(int(indice), len(ev['opciones']) - 1))
    op = ev['opciones'][indice]
    lineas = aplicar(estado, op['efectos'], prot, rng)
    evd['resuelto'], evd['resumen'] = indice, lineas
    registrar_noticia(estado, _fmt(op['titular'], estado, prot), _fmt(op['noticia'], estado, prot),
                      jugadores=list(evd['protagonistas']), evento=ev['id'], opcion=indice)
    return lineas


def resolver_pendientes(estado: dict, rng: Optional[random.Random] = None) -> int:
    """Los eventos sin responder se resuelven con su opción por defecto ("dejarlo pasar")."""
    n = 0
    for m in list(C.bandeja(estado)):
        evd = m.get('evento') or {}
        if evd and evd.get('resuelto') is None:
            resolver(estado, m['id'], (POR_ID.get(evd.get('id')) or {}).get('defecto', 0), rng)
            n += 1
    return n


def cierre_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga del user: pendientes por defecto, promesas y sorteo del evento."""
    try:
        resolver_pendientes(estado, rng)
        revisar_promesas(estado)
        sortear(estado, rng)
    except Exception as e:
        logger.error(f"Error en los eventos de la jornada: {e}", exc_info=True)
```

- [ ] **Step 4: `vestuario.py`** — justo después de `dc['racha'] = racha` (línea ~206):

```python
        # v0.4.10.0: últimos 3 resultados SIN reiniciar (racha se vacía al avisar): eventos.va_mal
        dc['ult_res'] = (list(dc.get('ult_res', [])) + ['G' if gf > gc else 'P' if gf < gc else 'E'])[-3:]
```

- [ ] **Step 5:** `python tests/test_eventos.py` → `10/10`. Si `S.partidos_sancion`/`S.sumar_sancion` usan otro nombre de competición que `'liga'`, ajustar al real (ver `sanciones._norm`).

---

### Task 8: Los otros 20 eventos del catálogo

**Files:**
- Modify: `alpha_football/eventos.py` (lista `EVENTOS`)
- Test: `tests/test_eventos.py`

**Interfaces — Consumes:** formato de efectos y helpers `_uno`/`_dos` de Task 7. **Produces:** 21 eventos en `EVENTOS`, cada uno con `id, peso, remitente, defecto, elige, asunto, cuerpo, opciones[{texto, efectos, titular, noticia}]`.

- [ ] **Step 1: Test que falla** — añadir a `tests/test_eventos.py`:

```python
IDS = ['rina', 'pelea_entreno', 'salida_nocturna', 'llega_tarde', 'critica_prensa', 'charla_lider',
       'exige_titular', 'lesion_entreno', 'gripe', 'nace_hijo', 'seleccion', 'nostalgia', 'entreno_extra',
       'escandalo_redes', 'rumor_oferta', 'prima_capitan', 'asado', 'hinchas', 'juvenil_deslumbra',
       'mentor', 'insulta_arbitro']


def _plantel_variado():
    e = _base(mal=True); js = e['mi_equipo'].jugadores
    js[0].personalidad = 'polemico'; js[1].personalidad = 'lider'; js[2].personalidad = 'profesional'
    js[3].personalidad = 'mercenario'; js[4].moral = 40
    js[5].jornadas_sin_jugar = 4; js[5].ataque = js[5].defensa = js[5].fisico = js[5].tecnica = js[5].mental = 95
    js[6].edad = 19; js[7].edad = 33; js[8].nacionalidad = 'Francia'; js[9].edad = 27
    for j in js:
        j.nacionalidad = j.nacionalidad or 'Inglaterra'
    return e


def test_catalogo_completo_y_bien_formado():
    assert [ev['id'] for ev in EV.EVENTOS] == IDS
    for ev in EV.EVENTOS:
        assert ev['remitente'] in C.REMITENTES and 2 <= len(ev['opciones']) <= 3
        assert 0 <= ev['defecto'] < len(ev['opciones']) and ev['peso'] > 0
        for op in ev['opciones']:
            assert op['texto'] == op['texto'].upper() and len(op['texto']) <= 24
            assert op['efectos'] and op['titular'] and op['noticia']


def test_cada_opcion_de_cada_evento_funciona_y_deja_noticia():
    for ev in EV.EVENTOS:
        for i, op in enumerate(ev['opciones']):
            e = _plantel_variado()
            m = EV.sortear(e, random.Random(7), forzar=ev['id'])
            assert m is not None, f"{ev['id']} no encontró protagonista"
            assert '{' not in m['asunto'] and '{' not in m['cuerpo']
            lineas = EV.resolver(e, m['id'], i, random.Random(i))
            assert lineas, (ev['id'], i)
            n = EV.noticias(e)
            assert len(n) == 1 and n[0]['evento'] == ev['id'] and '{' not in n[0]['titular'] + n[0]['cuerpo']
            for j in e['mi_equipo'].jugadores:
                assert 0 <= j.moral <= 100 and 0 <= j.energia <= 100 and j.lesion_partidos >= 0


def test_promesas_minutos_y_aumento():
    e = _plantel_variado(); js = e['mi_equipo'].jugadores
    m = EV.sortear(e, random.Random(1), forzar='exige_titular')
    j = next(x for x in js if x.id == m['evento']['protagonistas'][0])
    EV.resolver(e, m['id'], 0)
    assert e['datos_carrera']['promesas'][0]['tipo'] == 'minutos'
    moral = j.moral
    e['datos_carrera']['promesas'][0]['vence'] = EV._abs(e)             # venció y no jugó
    EV.revisar_promesas(e)
    assert j.moral == moral - 12 and e['datos_carrera']['promesas'] == []
    assert any(n['evento'] == 'promesa_rota' for n in EV.noticias(e))
    e2 = _plantel_variado()
    m2 = EV.sortear(e2, random.Random(1), forzar='rumor_oferta')
    j2 = next(x for x in e2['mi_equipo'].jugadores if x.id == m2['evento']['protagonistas'][0])
    EV.resolver(e2, m2['id'], 0)
    j2.salario += 1000                                                   # cumpliste: le subiste el sueldo
    moral2 = j2.moral
    EV.revisar_promesas(e2)
    assert e2['datos_carrera']['promesas'] == [] and j2.moral == moral2


def test_plantel_sin_perfiles_no_rompe():
    e = _base()                                                          # todos 'normal', 25 años, locales
    for j in e['mi_equipo'].jugadores:
        j.edad, j.nacionalidad, j.jornadas_sin_jugar = 26, 'Inglaterra', 0
    for s in range(80):
        EV.cierre_jornada(e, random.Random(s))
    ids = {m['evento']['id'] for m in C.bandeja(e) if m.get('evento')}
    assert not ids & {'rina', 'charla_lider', 'llega_tarde', 'rumor_oferta', 'entreno_extra', 'nostalgia',
                      'juvenil_deslumbra', 'mentor', 'hinchas'}
    assert len(EV.noticias(e)) >= len([m for m in C.bandeja(e) if m.get('evento')]) - 1
```

- [ ] **Step 2:** `python tests/test_eventos.py` → FAIL (`EVENTOS` solo tiene `rina`).

- [ ] **Step 3: Añadir a `eventos.py`**, antes de `EVENTOS`, los helpers de condición:

```python
def _pais_liga(estado: dict) -> str:
    try:
        from alpha_football.cantera import _tipo_liga
        from alpha_football.retiros import PAIS_POR_LIGA
        return PAIS_POR_LIGA.get(_tipo_liga(estado, estado.get('mi_equipo')), '')
    except Exception:
        return ''


def _media(estado: dict) -> float:
    js = _plantel(estado)
    return sum(j.overall for j in js) / len(js) if js else 0


def _figura(estado: dict, rng: random.Random) -> Optional[list]:
    d = _disp(estado)
    return [max(d, key=lambda j: j.overall)] if d else None


def _extranjero(estado: dict, rng: random.Random) -> Optional[list]:
    pais = _pais_liga(estado)
    return _uno(estado, rng, lambda j: bool(j.nacionalidad) and bool(pais) and j.nacionalidad != pais)


def _seleccionable(estado: dict, rng: random.Random) -> Optional[list]:
    top = sorted(_disp(estado), key=lambda j: -j.overall)[:8]
    c = [j for j in top if j.nacionalidad]
    return [rng.choice(c)] if c else None
```

  Y añadir a la lista `EVENTOS`, después de `rina` y en este orden, estos 20 dicts:

```python
    {'id': 'pelea_entreno', 'peso': 6, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _dos(e, r),
     'asunto': "Pelea en el entrenamiento: {j} y {j2}",
     'cuerpo': "En el entrenamiento de hoy {j} entró muy fuerte a {j2} y terminaron a los empujones. {j2} "
               "salió lastimado y pasó por la enfermería. El cuerpo técnico espera su decisión.",
     'opciones': [
         {'texto': "SANCIONAR AL AGRESOR", 'efectos': [('lesion', 'j2', (1, 2)), ('sancion', 'j', 1), ('moral', 'j', -6), ('moral', 'plantel', 2)],
          'titular': "{j}, sancionado por lesionar a un compañero",
          'noticia': "{club} apartó un partido a {j} tras la entrada que dejó tocado a {j2} en el entrenamiento."},
         {'texto': "MEDIAR ENTRE LOS DOS", 'efectos': [('lesion', 'j2', (1, 2)), ('moral', 'j', -4), ('moral', 'j2', -4)],
          'titular': "Tensión en {club}: {j} y {j2}, a los empujones",
          'noticia': "El técnico reunió a {j} y {j2} para limar asperezas. {j2} será baja por el golpe y ninguno "
                     "quedó conforme."},
     ]},
    {'id': 'salida_nocturna', 'peso': 7, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j} fue visto de fiesta antes del partido",
     'cuerpo': "Nos llegan fotos de {j} en una discoteca a altas horas de la madrugada. Hoy llegó al "
               "entrenamiento con ojeras y arrastrando los pies.",
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('energia', 'j', -20), ('moral', 'j', -6), ('dinero', 'j', 0.01)],
          'titular': "Multa a {j} por su noche de fiesta",
          'noticia': "{club} multó a {j} tras ser fotografiado de madrugada en una discoteca en plena semana de partido."},
         {'texto': "PERDONARLO", 'efectos': [('energia', 'j', -20), ('moral', 'plantel', -2)],
          'titular': "{j} sale de fiesta y no pasa nada",
          'noticia': "Las fotos de {j} de madrugada circularon por todos lados. El club no tomó medidas y en el "
                     "vestuario hubo caras largas."},
     ]},
    {'id': 'llega_tarde', 'peso': 6, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad in ('polemico', 'mercenario')),
     'asunto': "{j} llegó una hora tarde a entrenar",
     'cuerpo': "{j} se presentó una hora tarde al entrenamiento, sin avisar y con gafas oscuras. Dijo que "
               "había tráfico. Vive a cinco minutos.",
     'opciones': [
         {'texto': "AL BANQUILLO", 'efectos': [('sancion', 'j', 1), ('moral', 'j', -6), ('moral', 'plantel', 1)],
          'titular': "{j} se queda fuera por indisciplina",
          'noticia': "El técnico de {club} dejó a {j} fuera del próximo partido de liga por llegar tarde al entrenamiento."},
         {'texto': "UNA CHARLA Y YA", 'efectos': [('moral', 'j', -2)],
          'titular': "Llamado de atención a {j}",
          'noticia': "{j} llegó tarde a entrenar y todo quedó en una charla privada con el técnico."},
     ]},
    {'id': 'critica_prensa', 'peso': 6, 'remitente': 'prensa', 'defecto': 2,
     'elige': lambda e, r: _uno(e, r, lambda j: int(j.moral) < 50),
     'asunto': "{j} critica al técnico en una entrevista",
     'cuerpo': "En una entrevista publicada hoy, {j} declaró: «No entiendo los planteamientos del técnico, "
               "y no soy el único». Le pedimos su versión antes de publicar la segunda parte.",
     'opciones': [
         {'texto': "SANCIONARLO", 'efectos': [('sancion', 'j', 1), ('moral', 'j', -10), ('confianza', None, 2)],
          'titular': "{club} castiga a {j} por sus declaraciones",
          'noticia': "Las críticas públicas de {j} al entrenador le costaron un partido de sanción interna. La "
                     "directiva respaldó al técnico."},
         {'texto': "HABLAR CON ÉL", 'efectos': [('moral', 'j', 6)],
          'titular': "{j} y el técnico hacen las paces",
          'noticia': "Tras sus polémicas declaraciones, {j} se reunió con el entrenador. «Está todo aclarado», dijo al salir."},
         {'texto': "IGNORARLO", 'efectos': [('confianza', None, -4), ('moral', 'plantel', -2)],
          'titular': "Silencio del técnico ante las críticas de {j}",
          'noticia': "El entrenador de {club} no respondió a las críticas de {j}. En la directiva no gustó la falta de autoridad."},
     ]},
    {'id': 'charla_lider', 'peso': 5, 'peso_mal': 12, 'solo_mal': True, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'lider'),
     'asunto': "{j}: quiero reunir al vestuario",
     'cuerpo': "Míster, esto no puede seguir así. Quiero juntar a los muchachos, solos, sin cuerpo técnico, "
               "y decirnos las cosas a la cara. Necesito su permiso.\n{j}",
     'opciones': [
         {'texto': "APOYAR LA CHARLA", 'efectos': [('moral', 'plantel', 6)],
          'titular': "{j} reúne al plantel de {club}",
          'noticia': "El capitán sin brazalete, {j}, juntó al vestuario a puerta cerrada con el aval del técnico. "
                     "«Salimos más unidos», contó un jugador."},
         {'texto': "CORTARLA", 'efectos': [('moral', 'j', -8), ('moral', 'plantel', -2)],
          'titular': "El técnico frena la reunión que pedía {j}",
          'noticia': "{j} quiso reunir al plantel de {club} para hablar de la mala racha y el entrenador se lo impidió."},
     ]},
    {'id': 'exige_titular', 'peso': 7, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: int(getattr(j, 'jornadas_sin_jugar', 0) or 0) >= 3 and j.overall >= _media(e)),
     'asunto': "{j}: quiero jugar",
     'cuerpo': "Míster, llevo semanas mirando los partidos desde el banco y no vine a {club} a eso. Estoy "
               "mejor que varios de los que juegan. Póngame o dígame de frente que no cuenta conmigo.\n{j}",
     'opciones': [
         {'texto': "PROMETERLE MINUTOS", 'efectos': [('moral', 'j', 8), ('promesa', 'j', {'tipo': 'minutos', 'jornadas': 3, 'falla': -12})],
          'titular': "{j} tendrá su oportunidad",
          'noticia': "El técnico de {club} le prometió minutos a {j}, que venía reclamando un lugar en el equipo."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'j', -8)],
          'titular': "{j} seguirá en el banco",
          'noticia': "{j} pidió ser titular y el entrenador de {club} le respondió que el puesto se gana entrenando."},
     ]},
    {'id': 'lesion_entreno', 'peso': 6, 'remitente': 'medico', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j} se resintió entrenando",
     'cuerpo': "{j} sintió un pinchazo muscular en el entrenamiento. Podemos darle reposo completo o "
               "infiltrarlo para que vuelva antes, con riesgo de recaída.",
     'opciones': [
         {'texto': "REPOSO COMPLETO", 'efectos': [('lesion', 'j', (2, 3))],
          'titular': "{j}, baja por una lesión muscular",
          'noticia': "{club} no quiso arriesgar: {j} hará reposo completo tras resentirse en un entrenamiento."},
         {'texto': "INFILTRARLO", 'efectos': [('lesion', 'j', 1), ('azar', 0.3, [('lesion', 'j', 3), ('texto', "Recaída: la lesión se agravó.")], [])],
          'titular': "{j} fuerza para volver cuanto antes",
          'noticia': "{j} fue infiltrado para acortar los plazos de su lesión muscular. En el cuerpo médico de {club} cruzan los dedos."},
     ]},
    {'id': 'gripe', 'peso': 5, 'remitente': 'medico', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "Brote de gripe en el vestuario",
     'cuerpo': "{j} llegó con fiebre y ya hay otros dos con síntomas. Podemos aislarlos unos días o dejar "
               "que entrenen con el grupo.",
     'opciones': [
         {'texto': "AISLARLOS", 'efectos': [('lesion', 'j', 1), ('lesion', 'otros:2', 1)],
          'titular': "Gripe en {club}: tres jugadores aislados",
          'noticia': "Un brote de gripe dejó fuera de combate a {j} y a otros dos compañeros, que no estarán en el próximo partido."},
         {'texto': "QUE ENTRENEN IGUAL", 'efectos': [('energia', 'j', -15), ('energia', 'otros:5', -15)],
          'titular': "La gripe se extiende por el vestuario de {club}",
          'noticia': "{j} entrenó con fiebre y el virus corrió por el vestuario: medio plantel llega tocado al fin de semana."},
     ]},
    {'id': 'nace_hijo', 'peso': 4, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: 22 <= int(j.edad) <= 34),
     'asunto': "{j}: voy a ser papá",
     'cuerpo': "Míster, mi hijo nace esta semana. Sé que hay partido, pero quiero estar ahí. Le pido permiso "
               "para ausentarme; vuelvo enseguida y con más ganas que nunca.\n{j}",
     'opciones': [
         {'texto': "DARLE PERMISO", 'efectos': [('lesion', 'j', 1), ('moral', 'j', 15)],
          'titular': "{j} fue papá y se pierde un partido",
          'noticia': "{club} le dio permiso a {j} para estar en el nacimiento de su hijo. «Nunca voy a olvidar el gesto del técnico», dijo."},
         {'texto': "NEGARLO", 'efectos': [('moral', 'j', -10)],
          'titular': "{j} no tuvo permiso para el nacimiento de su hijo",
          'noticia': "El técnico de {club} no liberó a {j}, que se enteró del nacimiento de su hijo en la concentración."},
     ]},
    {'id': 'seleccion', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': _seleccionable,
     'asunto': "{pais} convoca a {j}",
     'cuerpo': "La federación de {pais} nos pide a {j} para un amistoso entre semana. No es fecha oficial: "
               "podemos negarnos. Si viaja, volverá cansado.",
     'opciones': [
         {'texto': "DEJARLO IR", 'efectos': [('energia', 'j', -25), ('moral', 'j', 8)],
          'titular': "{j} viaja con {pais}",
          'noticia': "{club} cedió a {j} a su selección para un amistoso. El jugador volvió feliz y con muchas horas de vuelo encima."},
         {'texto': "RETENERLO", 'efectos': [('moral', 'j', -8)],
          'titular': "{club} no cede a {j} a {pais}",
          'noticia': "El club se negó a liberar a {j} para el amistoso de {pais}. El jugador no ocultó su malestar."},
     ]},
    {'id': 'nostalgia', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': _extranjero,
     'asunto': "{j}: extraño mi casa",
     'cuerpo': "Míster, llevo meses sin ver a mi familia y se me está haciendo cuesta arriba. Necesito unos "
               "días en {pais} para recargar. Le prometo que vuelvo otro.\n{j}",
     'opciones': [
         {'texto': "DARLE DÍAS LIBRES", 'efectos': [('lesion', 'j', 1), ('moral', 'j', 10)],
          'titular': "{j} viaja a {pais} con permiso del club",
          'noticia': "{club} le dio unos días libres a {j}, que extrañaba a su familia. Se perderá un partido."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'j', -6), ('forma', 'j', 5.0)],
          'titular': "{j}, con la cabeza en {pais}",
          'noticia': "{j} pidió permiso para viajar a su país y no lo consiguió. En los entrenamientos se lo nota apagado."},
     ]},
    {'id': 'entreno_extra', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'profesional'),
     'asunto': "{j}: quiero quedarme a entrenar más",
     'cuerpo': "Míster, quiero hacer doble turno esta semana por mi cuenta: definición y físico. Sé que "
               "llegaré más cargado al partido, pero siento que lo necesito.\n{j}",
     'opciones': [
         {'texto': "PERMITIRLO", 'efectos': [('forma', 'j', 7.5), ('energia', 'j', -12), ('progreso', 'j', 0.15)],
          'titular': "{j}, el último en irse del entrenamiento",
          'noticia': "{j} hace doble turno por voluntad propia. «Es un ejemplo para los más jóvenes», dicen en {club}."},
         {'texto': "FRENARLO", 'efectos': [('texto', "Nada cambia: descansa como el resto.")],
          'titular': "El técnico cuida las cargas de {j}",
          'noticia': "{j} quería entrenar doble turno, pero el cuerpo técnico de {club} prefirió no sobrecargarlo."},
     ]},
    {'id': 'escandalo_redes', 'peso': 6, 'remitente': 'prensa', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "Escándalo: el video de {j} en redes",
     'cuerpo': "Un video de {j} burlándose de los hinchas rivales se hizo viral y hay pedidos de sanción. "
               "¿Cuál es la postura del club?",
     'opciones': [
         {'texto': "MULTARLO", 'efectos': [('moral', 'j', -6), ('confianza', None, 2), ('dinero', 'j', 0.01)],
          'titular': "{club} multa a {j} por su video viral",
          'noticia': "El club tomó distancia del video de {j} y lo sancionó económicamente. «No representa nuestros valores», dice el comunicado."},
         {'texto': "DEFENDERLO", 'efectos': [('moral', 'j', 6), ('confianza', None, -3)],
          'titular': "El técnico sale a defender a {j}",
          'noticia': "«Es un chico, se equivocó y ya está», dijo el entrenador de {club} sobre el video de {j}. A la directiva no le hizo gracia."},
     ]},
    {'id': 'rumor_oferta', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: j.personalidad == 'mercenario'),
     'asunto': "{j}: me están llamando de afuera",
     'cuerpo': "Míster, mi agente dice que hay un club dispuesto a pagarme el doble. Yo aquí estoy bien, pero "
               "uno tiene familia. Si me mejoran el contrato, me olvido del tema.\n{j}",
     'opciones': [
         {'texto': "PROMETER UN AUMENTO", 'efectos': [('moral', 'j', 6), ('promesa', 'j', {'tipo': 'aumento', 'jornadas': 6, 'falla': -10})],
          'titular': "{club} le mejorará el contrato a {j}",
          'noticia': "Ante el interés de otros clubes, el técnico le prometió a {j} una mejora salarial en las próximas semanas."},
         {'texto': "IGNORARLO", 'efectos': [('moral', 'j', -6), ('forma', 'j', 5.0)],
          'titular': "{j}, distraído por los rumores",
          'noticia': "{j} dejó saber que tiene ofertas y en {club} no se dieron por enterados. Su rendimiento lo está notando."},
     ]},
    {'id': 'prima_capitan', 'peso': 5, 'remitente': 'jugador', 'defecto': 1,
     'elige': _figura,
     'asunto': "{j}: el plantel pide una prima",
     'cuerpo': "Míster, hablo en nombre de todos: los muchachos piden una prima por ganar el próximo partido. "
               "No es mucho y el grupo lo tomaría como un gesto.\n{j}",
     'opciones': [
         {'texto': "PAGAR LA PRIMA", 'efectos': [('dinero', 'plantel', -0.01), ('moral', 'plantel', 5)],
          'titular': "{club} premia a su plantel",
          'noticia': "La directiva aprobó la prima que pidió el plantel por boca de {j}. El vestuario, encantado."},
         {'texto': "NEGARSE", 'efectos': [('moral', 'plantel', -3)],
          'titular': "No habrá prima en {club}",
          'noticia': "El plantel pidió una prima a través de {j} y la respuesta fue no. «Para eso están los sueldos», dijeron desde el club."},
     ]},
    {'id': 'asado', 'peso': 6, 'remitente': 'jugador', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "{j}: ¿hacemos un asado de equipo?",
     'cuerpo': "Míster, con los muchachos queremos hacer un asado esta semana, todos juntos con las familias. "
               "¿El club invita? Prometemos no pasarnos… mucho.\n{j}",
     'opciones': [
         {'texto': "EL CLUB INVITA", 'efectos': [('dinero', 'plantel', -0.002), ('moral', 'plantel', 4), ('energia', 'plantel', -5)],
          'titular': "Asado de camaradería en {club}",
          'noticia': "El plantel compartió un asado organizado por {j} y pagado por el club. Hubo risas, guitarra y más de uno llegó pesado al entrenamiento."},
         {'texto': "PROHIBIRLO", 'efectos': [('moral', 'plantel', -2)],
          'titular': "El técnico de {club} cancela el asado del plantel",
          'noticia': "{j} había organizado un asado de equipo y el entrenador lo prohibió: «Primero hay que ganar»."},
     ]},
    {'id': 'hinchas', 'peso': 4, 'peso_mal': 10, 'solo_mal': True, 'remitente': 'club', 'defecto': 1,
     'elige': _figura,
     'asunto': "Hinchas esperan al plantel a la salida",
     'cuerpo': "Un grupo de hinchas se plantó en la puerta del entrenamiento para reclamar por los resultados. "
               "Increparon a varios jugadores, sobre todo a {j}. Piden que alguien dé la cara.",
     'opciones': [
         {'texto': "DAR LA CARA", 'efectos': [('confianza', None, 4), ('moral', 'plantel', 2)],
          'titular': "El técnico de {club} habla con los hinchas",
          'noticia': "El entrenador salió a hablar con los hinchas que reclamaban en la puerta y se llevó hasta algún aplauso. {j} lo acompañó."},
         {'texto': "SALIR POR ATRÁS", 'efectos': [('confianza', None, -4), ('moral', 'plantel', -2)],
          'titular': "El plantel de {club} esquiva a su hinchada",
          'noticia': "Los hinchas esperaron en vano: técnico y jugadores, con {j} a la cabeza, salieron por la puerta trasera."},
     ]},
    {'id': 'juvenil_deslumbra', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r, lambda j: int(j.edad) <= 21),
     'asunto': "{j} la está rompiendo en los entrenamientos",
     'cuerpo': "Queremos avisarle que {j} lleva dos semanas siendo el mejor de las prácticas. Con trabajo "
               "específico y confianza puede dar un salto.",
     'opciones': [
         {'texto': "DARLE BOLA", 'efectos': [('progreso', 'j', 0.4), ('moral', 'j', 6)],
          'titular': "{j}, la joya que ilusiona a {club}",
          'noticia': "El cuerpo técnico le armó un plan especial a {j}, que viene deslumbrando en los entrenamientos."},
         {'texto': "PEDIR CALMA", 'efectos': [('texto', "Nada cambia: sigue su curso normal.")],
          'titular': "Paciencia con {j}",
          'noticia': "«Hay que llevarlo de a poco», dijo el técnico de {club} sobre {j}, la sensación de las prácticas."},
     ]},
    {'id': 'mentor', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _dos(e, r, lambda j: int(j.edad) >= 31, lambda j: int(j.edad) <= 21),
     'asunto': "{j} se ofrece a apadrinar a {j2}",
     'cuerpo': "{j} se quedó después del entrenamiento trabajando con {j2} y propone hacerlo todas las "
               "semanas. Solo necesitan que les organicemos el espacio.",
     'opciones': [
         {'texto': "FOMENTARLO", 'efectos': [('progreso', 'j2', 0.4), ('moral', 'j', 4), ('moral', 'j2', 4)],
          'titular': "{j}, maestro de {j2}",
          'noticia': "El veterano {j} tomó bajo su ala a {j2}: se quedan a trabajar juntos después de cada entrenamiento de {club}."},
         {'texto': "NO METERSE", 'efectos': [('texto', "Nada cambia: cada uno a lo suyo.")],
          'titular': "{j} y {j2}, cada uno por su lado",
          'noticia': "{j} quiso apadrinar a {j2}, pero el cuerpo técnico de {club} prefirió no cambiar las rutinas."},
     ]},
    {'id': 'insulta_arbitro', 'peso': 5, 'remitente': 'club', 'defecto': 1,
     'elige': lambda e, r: _uno(e, r),
     'asunto': "La liga sanciona a {j} por insultar al árbitro",
     'cuerpo': "{j} publicó en redes que el árbitro del último partido «tenía la camiseta rival debajo». La "
               "liga le abrió expediente: un partido. Podemos apelar, pero si sale mal serán dos.",
     'opciones': [
         {'texto': "APELAR", 'efectos': [('azar', 0.5, [('texto', "Apelación ganada: sin sanción.")], [('sancion', 'j', 2)])],
          'titular': "{club} apela la sanción a {j}",
          'noticia': "El club recurrió el castigo a {j} por sus dichos contra el árbitro. El comité ya resolvió y en {club} lo acatan."},
         {'texto': "ACEPTAR LA SANCIÓN", 'efectos': [('sancion', 'j', 1)],
          'titular': "Un partido de suspensión para {j}",
          'noticia': "{j} cumplirá un partido de sanción por sus publicaciones contra el árbitro. {club} no apelará."},
     ]},
```

- [ ] **Step 4:** `python tests/test_eventos.py` → `14/14`. Si `test_cada_opcion…` falla porque `_plantel_variado` no produce protagonista para algún id (p. ej. `j.disponible` falso), ajustar el fixture, no el catálogo.

---

### Task 9: Decisión en pantalla y enganche de jornada

**Files:**
- Modify: `alpha_football/ui/correo_screen.py` (botones de decisión, borrar), `alpha_football/ui/match_screen.py:~476` (enganche), `alpha_football/correo.py` (`limpiar_temporadas_anteriores`), `alpha_football/ui/ayuda.py` (`_ayuda_correo`)
- Test: `tests/test_eventos.py`

**Interfaces — Consumes:** `eventos.resolver`, `eventos.resolver_pendientes`, `eventos.cierre_jornada`, `msg['evento']`. **Produces:** `correo_screen.rects_evento(n: int) -> list[pygame.Rect]`.

- [ ] **Step 1: Test que falla** — añadir a `tests/test_eventos.py`:

```python
def _con_rina():
    e = _base(mal=True); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    e['correo_canal'], e['correo_sel'] = 'mensaje', 0
    return e, m


def test_clic_en_opcion_resuelve():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    r = CS.rects_evento(3)[1]
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center))
    assert CS.render(screen, e) is None
    assert m['evento']['resuelto'] == 1 and len(EV.noticias(e)) == 1
    assert CS.render(screen, e) is None                    # ya resuelto: muestra el resumen sin botones


def test_teclado_elige_opcion():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    pygame.event.clear()
    for k in (pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_RETURN):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))
    CS.render(screen, e)
    assert m['evento']['resuelto'] == 2


def test_borrar_pendiente_aplica_el_defecto():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE, mod=0, unicode=''))
    CS.render(screen, e)
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1
    assert m not in C.bandeja(e)


def test_cambio_de_temporada_resuelve_pendientes():
    e, m = _con_rina()
    e['temporada'] = 2
    C.limpiar_temporadas_anteriores(e)
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1


def test_enganche_en_el_cierre_de_jornada():
    import inspect
    from alpha_football.ui import match_screen
    assert "eventos" in inspect.getsource(match_screen.finalizar_jornada_liga)
```

- [ ] **Step 2:** `python tests/test_eventos.py` → FAIL.

- [ ] **Step 3: `correo_screen.py`.** Bajo `R_BORRAR`:

```python
ALTO_OPCION = 46            # v0.4.10.0: botones de decisión de un evento (uno por opción, apilados)


def rects_evento(n: int) -> list:
    base = _rect_accion()
    return [pygame.Rect(base.x, base.y - (n - 1 - i) * ALTO_OPCION, 420, ALTO_OPCION - 6) for i in range(n)]


def _evento_pendiente(m: dict) -> Optional[dict]:
    ev = m.get('evento')
    return ev if ev and ev.get('resuelto') is None else None


def _borrar(estado: dict, m: dict) -> None:
    """v0.4.10.0: borrar un evento sin responder no esquiva la consecuencia: se aplica la de por defecto."""
    if _evento_pendiente(m):
        from alpha_football import eventos as EV
        EV.resolver_pendientes(estado)
    C.borrar(estado, m['id'])
```

  En `render`:
  - Tras calcular `sel`: `opc = int(estado.get('correo_opc', 0) or 0)`.
  - Las dos llamadas `C.borrar(estado, mensajes[sel]['id'])` pasan a `_borrar(estado, mensajes[sel])`.
  - Antes del `if ev.key == pygame.K_DOWN:` añadir el manejo de teclado del evento (con `continue` para que Enter no dispare `_ir`):

```python
                pend = _evento_pendiente(mensajes[sel]) if mensajes else None
                if pend and ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    opc = max(0, min(len(pend['opciones']) - 1, opc + (1 if ev.key == pygame.K_RIGHT else -1)))
                    continue
                if pend and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    from alpha_football import eventos as EV
                    EV.resolver(estado, mensajes[sel]['id'], opc)
                    opc = 0
                    continue
```
  - Al cambiar `sel` con ↑/↓ o clic en fila: `opc = 0`.
  - En el bloque de clic, antes del `if click and mensajes and _rect_accion()…`:

```python
            pend = _evento_pendiente(mensajes[sel]) if (click and mensajes) else None
            if pend:
                for i, r in enumerate(rects_evento(len(pend['opciones']))):
                    if r.collidepoint(click):
                        from alpha_football import eventos as EV
                        EV.resolver(estado, mensajes[sel]['id'], i)
                        opc = 0
                click = None            # con decisión pendiente no hay botón de acción
```
  - Junto a `estado['correo_sel'] = sel`: `estado['correo_opc'] = opc`.
  - Dibujo: el cuerpo se recorta para dejar sitio. Reemplazar `[:LINEAS_CUERPO]` por `[:LINEAS_CUERPO - (6 if m.get('evento') else 0)]` y, tras dibujar el botón de acción:

```python
        evd = m.get('evento')                              # v0.4.10.0: decisión o su resultado
        if evd and evd.get('resuelto') is None:
            for i, r in enumerate(rects_evento(len(evd['opciones']))):
                draw_button(screen, r, evd['opciones'][i], r.collidepoint(mouse_pos) or i == opc)
        elif evd:
            elegido = evd['opciones'][evd['resuelto']] if 0 <= int(evd['resuelto']) < len(evd['opciones']) else "—"
            y0 = _rect_accion().y - 3 * 24
            draw_text(screen, f"Decidiste: {elegido}", (x, y0), size='sm', color='dorado')
            for k, linea in enumerate(_envolver(" · ".join(evd.get('resumen') or []), R_MSG.width - 240)[:4]):
                draw_text(screen, linea, (x, y0 + 24 + k * 22), size='sm', color='azul')
```
  - En la línea de ayuda del encabezado añadir `← → opción` cuando hay decisión pendiente (opcional si no cabe).

- [ ] **Step 4: `correo.py`** — al inicio de `limpiar_temporadas_anteriores`:

```python
    try:   # v0.4.10.0: un evento sin responder no se pierde al limpiar: se aplica su opción por defecto
        from alpha_football import eventos as EV
        EV.resolver_pendientes(estado)
    except Exception as e:
        logger.error(f"No se pudieron cerrar los eventos pendientes: {e}")
```

- [ ] **Step 5: `match_screen.py`** — en `finalizar_jornada_liga`, justo después del bloque `try/except` de `_salidas_cierre(estado)`:

```python
        try:  # v0.4.10.0: evento aleatorio de vestuario de la jornada (eventos.py)
            from alpha_football.eventos import cierre_jornada as _eventos_cierre
            _eventos_cierre(estado)
        except Exception as e_ev:
            logger.error(f"Error en los eventos de la jornada: {e_ev}")
```

- [ ] **Step 6: Ayuda.** En `_ayuda_correo` añadir un ítem: `(C._rect_accion(), "Decisiones", "Algunos mensajes piden una decisión: elige con clic o ← → y Enter. Si no respondes antes del próximo partido de liga, se deja pasar.")` (respetando la forma de las tuplas).

- [ ] **Step 7:** `python tests/test_eventos.py` → `19/19`. `python tests/test_correo_v470.py` y `python tests/test_ayuda_v390.py` → pasan.

---

### Task 10: Cierre — suite completa, juego real y documentación

**Files:**
- Modify: `main.py:539` (título), `README.md:11` (badge), `context.md`

- [ ] **Step 1: Versión.** `main.py`: `set_caption("Alpha Football v0.4.10.0")`. `README.md`: badge `versión-0.4.10.0`.
- [ ] **Step 2: Suite completa.** `for f in tests/test_*.py; do python "$f" > /dev/null 2>&1 || echo "FAIL $f"; done` → sin líneas `FAIL`. Arreglar cada fallo en su causa (no relajar aserciones que detecten un bug real).
- [ ] **Step 3: Humo en el juego real** (skill `run` o script dummy): cargar una carrera, simular 10 jornadas con `match_screen.finalizar_jornada_liga`/sim instantánea y comprobar que (a) no hay excepciones en el log, (b) `datos_carrera['noticias']` tiene una entrada por evento resuelto, (c) NOTIFICACIONES dibuja con datos reales, (d) la ficha de un extranjero conocido muestra su país.
- [ ] **Step 4: `context.md`.** Actualizar encabezado (v0.4.10.0, fecha 2026-10-04) y añadir bitácora "Nacionalidades, eventos y notificaciones": qué se hizo, que la sección NOTICIAS queda pendiente y lee de `datos_carrera['noticias']`, la regla de numeración `0.X.Y.Z`, y "sin commit".
- [ ] **Step 5:** Informar a Diego: resultado de la suite con números, qué probar a mano, y que no se hizo commit.
