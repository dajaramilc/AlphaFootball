# Motor del partido, presentación, teclado/correo y copa (sub-proyectos 9-12, v4.0.0 → v4.3.0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Partidos con tarjetas, lesiones, cambios y notas que salen de lo que pasa en la cancha; resumen y pantalla post-partido (calificaciones + tabla); juego completo sin mouse con atajos M/O y sobre de correo; correos de premios/objetivos de copa, historial con copa y Balón de Oro sobre liga + copa.

**Architecture:** Un módulo nuevo y puro `alpha_football/partido_ctx.py` guarda el estado vivo del partido (`EstadoPartido`: quién está en cancha, tarjetas, cambios, notas, goles, minutos, incidencias) y la única función que lo modifica (`aplicar_evento`). El motor genera eventos y los aplica al ctx; la pantalla en vivo aplica los mismos eventos a su propia copia a medida que los revela (así una re-simulación parte del estado *revelado*). El resultado del motor trae el ctx y todas las capas (desarrollo, energía, vestuario, copa) leen de ahí en vez de re-sortear. La UI post-partido es un módulo nuevo `ui/postpartido.py` compartido por vivo e instantáneo.

**Tech Stack:** Python 3.10+, Pygame; tests con runner propio (archivos `tests/test_*.py` ejecutables con `python`).

**Spec:** `docs/superpowers/specs/2026-09-24-partido-teclado-copa-design.md`

## Global Constraints
- Comentarios de versión `# v4.0.0: ...` (A), `# v4.1.0` (B), `# v4.2.0` (C), `# v4.3.0` (D). Español en comentarios y textos.
- Toda función nueva de UI o hook de cierre: `try/except` + `logger.error(...)` (estilo del repo); nunca romper el bucle.
- **Sin commits** (Diego prueba y aprueba al final). Donde el template dice "Commit", no se commitea.
- Tests: cabecera como `tests/test_ux_v360.py` (SDL dummy, `estado_carrera`, `click`, `key`, `save.guardar_en_slot` anulado). Correr con
  `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python tests/<archivo>.py`.
- Suite completa (tarda >10 min): `for f in tests/test_*.py; do SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python "$f" > /dev/null 2>&1 || echo "FALLA $f"; done`.
- Nada se dibuja en y ≥ 698 salvo la barra de atajos (`ui/atajos.py`, franja 698-720).
- Sin emojis en textos dibujados (la fuente no los tiene: salen como cuadros). Íconos = formas de `pygame.draw`.
- Saves viejos deben seguir cargando: campos nuevos con defaults; nada de lo nuevo se serializa salvo lo indicado.
- La tecla **M** ya silencia la música en `options_screen` (`options_screen.py:268`): el atajo global M no aplica ahí.
- Frecuencias objetivo por partido (ambos equipos): amarillas ~3.5, rojas directas ~0.15, lesiones ~0.25 (hoy `PROB_LESION_90 = 0.012` por jugador), penales ~0.25; media de goles ±0.2 respecto a la actual.

## Review Focus
- Re-simulación en vivo (cambio de mentalidad / táctica) después de una expulsión o lesión revelada → el expulsado/lesionado **no vuelve** a la cancha. Test en Task 5 (`test_resim_respeta_expulsado`).
- Lesión de un jugador del user en vivo con los 5 cambios ya hechos → sigue con 10, no se abre el selector, no revienta. Test en Task 5 (`test_lesion_sin_cambios`).
- Save viejo / partido de la IA sin ctx (llamadas viejas a `desarrollar_plantilla_post_partido(eq, gf, gc)`) → comportamiento de antes, sin excepción. Test en Task 3 (`test_desarrollo_sin_stats_compat`).
- Correo con más de 9 no leídos, o 0 → sobre muestra "9+" / no muestra círculo. Test en Task 10 (`test_sobre_badge`).
- Tecla M/O mientras se escribe en el buscador o el editor (texto_activo) → escribe la letra, no navega. Test en Task 10 (`test_atajos_globales_con_texto`).

## Reparto sugerido
Subagente 1: Tasks 1-3 (A). Subagente 2: Tasks 4-6 (B, después de A). Subagente 3: Tasks 7-10 (C, en paralelo con A/B: no toca engine; en `match_screen.py` solo agrega teclas en la Task 8 **después** de que termine la Task 5). Subagente 4: Tasks 11-12 (D, en paralelo). Task 13 al final (yo).
Si un Edit falla porque otro subagente cambió el archivo: releer la zona y reintentar.

---

## A · Motor del partido (v4.0.0)

### Task 1: `partido_ctx.py` — estado del partido, aplicar_evento, notas

**Files:**
- Create: `alpha_football/partido_ctx.py`
- Test: `tests/test_motor_v400.py` (nuevo)

**Interfaces:**
- Produces (todo lo usan Tasks 2-6):
  - `EstadoPartido` (dataclass) con campos `en_cancha: dict[str, list]` (`'l'`/`'v'` → objetos Jugador), `auto_cambios: dict[str, bool]`, `amarillas: dict`, `expulsados: dict[str,int]`, `fuera: set`, `cambios: dict[str,int]`, `notas: dict`, `goles: dict`, `asist: dict`, `entrada: dict`, `salida: dict`, `incidencias: list`, `ids_equipo: dict[str,str]` (lado → equipo.id); métodos `copia() -> EstadoPartido`, `lado_de_equipo(equipo_id) -> Optional[str]`.
  - `nuevo_estado(local, visitante, once_l: list, once_v: list, auto_l=True, auto_v=True) -> EstadoPartido`
  - `aplicar_evento(ctx, ev: dict) -> None`
  - `minutos_jugados(ctx, fin: int = 90) -> dict[jid, int]`
  - `notas_finales(ctx, goles_l: int, goles_v: int, rng=None) -> dict[jid, float]`
  - `nota_en_vivo(ctx, jid) -> float` (6.0 + deltas, sin resultado ni ruido; la usa B)
  - Constantes `DELTA_NOTA`, `MAX_CAMBIOS = 5`, `MULT_EXPULSION = 0.85`.
- Formato de eventos (dicts; `jid` = `jugador.id`):
  | tipo | claves extra |
  |---|---|
  | `gol` | `jugador_id`, `asistente_id` (o None), `defensor_id`, `penal: bool` |
  | `tiro`, `ocasion` | `jugador_id` (atacante), `defensor_id` |
  | `atajada` | `jugador_id` (portero), `atacante_id` |
  | `defensa` | `jugador_id` (defensor que corta), `atacante_id` |
  | `penal_fallado` | `jugador_id` |
  | `amarilla` | `jugador_id` |
  | `roja` | `jugador_id`, `motivo` (`'directa'`/`'doble amarilla'`), `partidos` |
  | `lesion` | `jugador_id`, `partidos` |
  | `cambio` | `jugador_id` (entra), `sale_id` |
  Todos llevan `minuto`, `tipo`, `equipo_id`, `detalle`, `lado` (`'l'`/`'v'`).

- [ ] **Step 1: Write the failing tests**

```python
"""v4.0.0: motor del partido — tarjetas, lesiones, cambios, notas desde eventos."""
import sys, os, random, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'; os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(40)
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
from alpha_football.models import alineacion_por_defecto, asegurar_ids_unicos
from alpha_football.ui.menu import load_league_teams
from alpha_football import partido_ctx as PC
from alpha_football.engine import _once_titular
save.guardar_en_slot = lambda *a, **k: None


def dos_equipos(tipo='premier'):
    liga = load_league_teams(tipo)
    a, b = liga.equipos[0], liga.equipos[1]
    for e in (a, b):
        asegurar_ids_unicos(e)
    return liga, a, b


def ctx_basico():
    liga, a, b = dos_equipos()
    return a, b, PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b))


def test_amarilla_doble_es_roja():
    a, b, ctx = ctx_basico(); j = ctx.en_cancha['l'][3]
    PC.aplicar_evento(ctx, {'minuto': 10, 'tipo': 'amarilla', 'equipo_id': a.id, 'lado': 'l', 'jugador_id': j.id, 'detalle': ''})
    assert ctx.amarillas[j.id] == 1 and j in ctx.en_cancha['l']
    PC.aplicar_evento(ctx, {'minuto': 50, 'tipo': 'roja', 'equipo_id': a.id, 'lado': 'l', 'jugador_id': j.id,
                            'motivo': 'doble amarilla', 'partidos': 1, 'detalle': ''})
    assert j not in ctx.en_cancha['l'] and j.id in ctx.fuera and ctx.expulsados['l'] == 1
    assert ctx.salida[j.id] == 50
    assert any(i['tipo'] == 'sancion' and i['jugador_id'] == j.id for i in ctx.incidencias)
    print("  test_amarilla_doble_es_roja: OK")


def test_cambio_y_minutos():
    a, b, ctx = ctx_basico()
    sale = ctx.en_cancha['v'][5]
    entra = next(j for j in b.jugadores if j not in ctx.en_cancha['v'])
    PC.aplicar_evento(ctx, {'minuto': 70, 'tipo': 'cambio', 'equipo_id': b.id, 'lado': 'v',
                            'jugador_id': entra.id, 'sale_id': sale.id, '_entra_obj': entra, 'detalle': ''})
    assert entra in ctx.en_cancha['v'] and sale not in ctx.en_cancha['v'] and ctx.cambios['v'] == 1
    m = PC.minutos_jugados(ctx)
    assert m[sale.id] == 70 and m[entra.id] == 20
    assert m[ctx.en_cancha['l'][0].id] == 90
    print("  test_cambio_y_minutos: OK")


def test_notas_desde_eventos():
    a, b, ctx = ctx_basico()
    del_ = next(j for j in ctx.en_cancha['l'] if j.posicion == 'DEL')
    med = next(j for j in ctx.en_cancha['l'] if j.posicion == 'MED')
    df = next(j for j in ctx.en_cancha['v'] if j.posicion == 'DEF')
    por_l = next(j for j in ctx.en_cancha['l'] if j.posicion == 'POR')
    PC.aplicar_evento(ctx, {'minuto': 20, 'tipo': 'gol', 'equipo_id': a.id, 'lado': 'l', 'jugador_id': del_.id,
                            'asistente_id': med.id, 'defensor_id': df.id, 'penal': False, 'detalle': ''})
    assert ctx.goles[del_.id] == 1 and ctx.asist[med.id] == 1
    assert abs(PC.nota_en_vivo(ctx, del_.id) - 7.0) < 1e-9
    assert abs(PC.nota_en_vivo(ctx, df.id) - 5.7) < 1e-9
    notas = PC.notas_finales(ctx, 1, 0, rng=random.Random(1))
    assert 3.0 <= min(notas.values()) and max(notas.values()) <= 10.0
    assert notas[del_.id] > notas[df.id]
    assert notas[por_l.id] >= 6.0 + 0.5 + 0.5 - 0.3      # valla invicta + victoria - ruido máx
    print("  test_notas_desde_eventos: OK")


def test_copia_independiente():
    a, b, ctx = ctx_basico(); c2 = ctx.copia(); j = ctx.en_cancha['l'][2]
    PC.aplicar_evento(c2, {'minuto': 5, 'tipo': 'lesion', 'equipo_id': a.id, 'lado': 'l', 'jugador_id': j.id,
                           'partidos': 2, 'detalle': ''})
    assert j in ctx.en_cancha['l'] and j not in c2.en_cancha['l'] and j.id not in ctx.fuera
    print("  test_copia_independiente: OK")


if __name__ == '__main__':
    for n, f in list(globals().items()):
        if n.startswith('test_') and callable(f):
            f()
    print("OK test_motor_v400")
```

- [ ] **Step 2: Run to verify it fails**
Run: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONIOENCODING=utf-8 python tests/test_motor_v400.py`
Expected: `ModuleNotFoundError: alpha_football.partido_ctx`

- [ ] **Step 3: Implement `alpha_football/partido_ctx.py`**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — ESTADO VIVO DEL PARTIDO (v4.0.0)
Quién está en cancha, tarjetas, cambios, notas, goles, minutos e incidencias de UN partido.
El motor genera eventos y los aplica aquí; la pantalla en vivo aplica los mismos eventos a su
copia a medida que los revela. `aplicar_evento` es la ÚNICA función que modifica el estado.
Las lesiones/sanciones NO se escriben en el jugador hasta el cierre del partido (incidencias):
si se escribieran antes, `_once_titular` metería un suplente por su cuenta.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

NOTA_BASE = 6.0
DELTA_NOTA = {'gol': 1.0, 'asistencia': 0.5, 'atajada': 0.4, 'tiro': -0.2, 'ocasion': -0.2,
              'amarilla': -0.3, 'roja': -1.5, 'penal_fallado': -0.6, 'batido': -0.3, 'defensa': 0.1}
BONO_VALLA = 0.5            # DEF/POR con >= 60' y su equipo sin goles en contra
BONO_RESULTADO = {'G': 0.5, 'E': 0.0, 'P': -0.4}
RUIDO = 0.3
MAX_CAMBIOS = 5
MULT_EXPULSION = 0.85


@dataclass
class EstadoPartido:
    en_cancha: dict
    auto_cambios: dict
    ids_equipo: dict
    amarillas: dict = field(default_factory=dict)
    expulsados: dict = field(default_factory=lambda: {'l': 0, 'v': 0})
    fuera: set = field(default_factory=set)
    cambios: dict = field(default_factory=lambda: {'l': 0, 'v': 0})
    notas: dict = field(default_factory=dict)       # deltas acumulados por jid (sin base)
    goles: dict = field(default_factory=dict)
    asist: dict = field(default_factory=dict)
    entrada: dict = field(default_factory=dict)     # jid -> minuto en que entró (0 = titular)
    salida: dict = field(default_factory=dict)      # jid -> minuto en que salió
    incidencias: list = field(default_factory=list)
    posicion: dict = field(default_factory=dict)    # jid -> 'POR'/'DEF'/'MED'/'DEL'
    lado_jugador: dict = field(default_factory=dict)

    def copia(self) -> 'EstadoPartido':
        """Copia independiente (listas/dicts nuevos; los Jugador son los mismos objetos)."""
        return EstadoPartido(
            en_cancha={k: list(v) for k, v in self.en_cancha.items()},
            auto_cambios=dict(self.auto_cambios), ids_equipo=dict(self.ids_equipo),
            amarillas=dict(self.amarillas), expulsados=dict(self.expulsados), fuera=set(self.fuera),
            cambios=dict(self.cambios), notas=dict(self.notas), goles=dict(self.goles),
            asist=dict(self.asist), entrada=dict(self.entrada), salida=dict(self.salida),
            incidencias=[dict(i) for i in self.incidencias], posicion=dict(self.posicion),
            lado_jugador=dict(self.lado_jugador))

    def lado_de_equipo(self, equipo_id) -> Optional[str]:
        for lado, eid in self.ids_equipo.items():
            if eid == equipo_id:
                return lado
        return None


def _registrar(ctx: EstadoPartido, lado: str, j, minuto: int) -> None:
    jid = getattr(j, 'id', None)
    ctx.entrada.setdefault(jid, minuto)
    ctx.posicion[jid] = getattr(j, 'posicion', 'MED')
    ctx.lado_jugador[jid] = lado


def nuevo_estado(local, visitante, once_l: list, once_v: list, auto_l: bool = True,
                 auto_v: bool = True) -> EstadoPartido:
    ctx = EstadoPartido(en_cancha={'l': list(once_l), 'v': list(once_v)},
                        auto_cambios={'l': auto_l, 'v': auto_v},
                        ids_equipo={'l': getattr(local, 'id', None), 'v': getattr(visitante, 'id', None)})
    for lado in ('l', 'v'):
        for j in ctx.en_cancha[lado]:
            _registrar(ctx, lado, j, 0)
    return ctx


def _sumar(ctx, jid, clave):
    if jid is not None:
        ctx.notas[jid] = ctx.notas.get(jid, 0.0) + DELTA_NOTA[clave]


def _sacar(ctx, lado, jid, minuto):
    ctx.en_cancha[lado] = [j for j in ctx.en_cancha[lado] if getattr(j, 'id', None) != jid]
    ctx.salida[jid] = minuto


def aplicar_evento(ctx: EstadoPartido, ev: dict) -> None:
    """Aplica UN evento al estado. Eventos desconocidos (caotico, mentalidad) no hacen nada."""
    try:
        t = ev.get('tipo'); jid = ev.get('jugador_id'); m = int(ev.get('minuto', 0) or 0)
        lado = ev.get('lado') or ctx.lado_de_equipo(ev.get('equipo_id'))
        if t == 'gol':
            ctx.goles[jid] = ctx.goles.get(jid, 0) + 1; _sumar(ctx, jid, 'gol')
            if ev.get('asistente_id') is not None:
                a = ev['asistente_id']; ctx.asist[a] = ctx.asist.get(a, 0) + 1; _sumar(ctx, a, 'asistencia')
            _sumar(ctx, ev.get('defensor_id'), 'batido')
        elif t in ('tiro', 'ocasion', 'atajada', 'defensa', 'penal_fallado', 'amarilla'):
            _sumar(ctx, jid, t)
            if t == 'amarilla':
                ctx.amarillas[jid] = ctx.amarillas.get(jid, 0) + 1
        elif t == 'roja':
            _sumar(ctx, jid, 'roja')
            ctx.fuera.add(jid); ctx.expulsados[lado] = ctx.expulsados.get(lado, 0) + 1
            _sacar(ctx, lado, jid, m)
            ctx.incidencias.append({'tipo': 'sancion', 'jugador_id': jid, 'partidos': int(ev.get('partidos', 1))})
        elif t == 'lesion':
            ctx.fuera.add(jid); _sacar(ctx, lado, jid, m)
            ctx.incidencias.append({'tipo': 'lesion', 'jugador_id': jid, 'partidos': int(ev.get('partidos', 1))})
        elif t == 'cambio':
            sale = ev.get('sale_id'); entra = ev.get('_entra_obj')
            if sale is not None and sale not in ctx.fuera:
                _sacar(ctx, lado, sale, m)
            if entra is not None:
                ctx.en_cancha[lado].append(entra); _registrar(ctx, lado, entra, m)
            ctx.cambios[lado] = ctx.cambios.get(lado, 0) + 1
    except Exception as e:
        logger.error(f"aplicar_evento: evento inválido {ev.get('tipo')}: {e}")


def minutos_jugados(ctx: EstadoPartido, fin: int = 90) -> dict:
    return {jid: max(0, int(ctx.salida.get(jid, fin)) - int(ent)) for jid, ent in ctx.entrada.items()}


def nota_en_vivo(ctx: EstadoPartido, jid) -> float:
    return round(NOTA_BASE + ctx.notas.get(jid, 0.0), 1)


def notas_finales(ctx: EstadoPartido, goles_l: int, goles_v: int, rng=None) -> dict:
    azar = rng or random.Random()
    mins = minutos_jugados(ctx)
    out = {}
    for jid, mm in mins.items():
        if mm <= 0 and jid not in ctx.fuera:
            continue
        lado = ctx.lado_jugador.get(jid, 'l')
        gf, gc = (goles_l, goles_v) if lado == 'l' else (goles_v, goles_l)
        n = NOTA_BASE + ctx.notas.get(jid, 0.0)
        n += BONO_RESULTADO['G' if gf > gc else 'P' if gf < gc else 'E']
        if gc == 0 and ctx.posicion.get(jid) in ('DEF', 'POR') and mm >= 60:
            n += BONO_VALLA
        n += azar.uniform(-RUIDO, RUIDO)
        out[jid] = max(3.0, min(10.0, round(n, 1)))
    return out
```
Nota: el evento `cambio` lleva `_entra_obj` (el objeto Jugador que entra) además de `jugador_id`; lo pone quien crea el evento (motor o pantalla). `_entra_obj` no se serializa (los eventos no se guardan en el save).

- [ ] **Step 4: Run tests** → los 4 en OK.

---

### Task 2: El motor genera tarjetas, lesiones, penales, atajadas, cambios de la IA y usa el ctx

**Files:**
- Modify: `alpha_football/engine.py` — `Resultado` (~229), `procesar_minuto` (619-740), `simular_partido` (742-820), `_simular_minutos` (822-860), `simular_rango` (863-921), listas de frases (`_GOL`, `_FALLO`, `_ATAQUE`, `_frase_defensa`).
- Test: `tests/test_motor_v400.py`

**Interfaces:**
- Consumes: todo `partido_ctx` (Task 1).
- Produces:
  - `Resultado.ctx: Optional[EstadoPartido]` (default None) y `Resultado.notas: dict` (jid → nota final, default `{}`).
  - `simular_partido(..., ctx=None, auto_l=True, auto_v=True)` (crea el ctx si no viene; lo devuelve en `Resultado.ctx`).
  - `simular_rango(..., ctx=None)` → sigue devolviendo `(gl, gv, eventos)`; **muta el ctx recibido** (quien quiera conservar el suyo pasa `ctx.copia()`). Si `ctx` es None crea uno interno (compat).
  - `procesar_minuto(..., ctx=None)`: cuando hay ctx, los atacantes/defensores salen de `ctx.en_cancha`.
  - `elegir_cambio_ia(ctx, lado, equipo, minuto) -> Optional[tuple[sale, entra]]`
  - `suplentes_disponibles(ctx, lado, equipo) -> list` (los de `equipo.jugadores` fuera de cancha, no en `ctx.fuera`, no salidos, `lesion_partidos == 0` y `partidos_sancion <= 0`; si el equipo tiene `alineacion_activa` con `convocados`/banco, restringir al banco — ver `formaciones.normalizar_convocados`).

- [ ] **Step 1: Medir la línea base ANTES de tocar el motor** (guardar el número en el test):

```bash
SDL_VIDEODRIVER=dummy PYTHONIOENCODING=utf-8 python -c "
import random; random.seed(7)
from alpha_football.ui.menu import load_league_teams
from alpha_football.engine import simular_partido
L=load_league_teams('premier'); t=0; n=600
for i in range(n):
    a,b=random.sample(L.equipos,2); r=simular_partido(a,b,aplicar_fisico=False); t+=r.goles_local+r.goles_visitante
print('media goles', t/n)"
```
Anotar el valor como `MEDIA_GOLES_BASE` en el test (ej. `MEDIA_GOLES_BASE = 2.71`). Medir también el tiempo de 600 partidos (`time.perf_counter`) como `TIEMPO_BASE`.

- [ ] **Step 2: Tests que fallan**

```python
MEDIA_GOLES_BASE = None   # <- valor del Step 1
TIEMPO_BASE = None        # <- segundos del Step 1

def _muestra(n=600, seed=7):
    from alpha_football.engine import simular_partido
    random.seed(seed); liga = load_league_teams('premier'); rs = []
    for _ in range(n):
        a, b = random.sample(liga.equipos, 2)
        rs.append(simular_partido(a, b, aplicar_fisico=False))
    return rs

def test_frecuencias_y_goles():
    t0 = time.perf_counter(); rs = _muestra(); dt = time.perf_counter() - t0
    n = len(rs); cuenta = lambda t: sum(1 for r in rs for e in r.eventos if e['tipo'] == t) / n
    media = sum(r.goles_local + r.goles_visitante for r in rs) / n
    assert abs(media - MEDIA_GOLES_BASE) <= 0.2, media
    assert 2.8 <= cuenta('amarilla') <= 4.2, cuenta('amarilla')
    rojas_directas = sum(1 for r in rs for e in r.eventos if e['tipo'] == 'roja' and e.get('motivo') == 'directa') / n
    assert 0.08 <= rojas_directas <= 0.25, rojas_directas
    assert 0.15 <= cuenta('lesion') <= 0.40, cuenta('lesion')
    penales = sum(1 for r in rs for e in r.eventos if e['tipo'] == 'penal_fallado' or (e['tipo'] == 'gol' and e.get('penal'))) / n
    assert 0.15 <= penales <= 0.40, penales
    assert cuenta('atajada') > 1 and cuenta('cambio') >= 5
    assert dt <= TIEMPO_BASE * 1.3 + 0.5, dt        # la jornada de 16 ligas no se vuelve lenta
    print("  test_frecuencias_y_goles: OK")

def test_resultado_consistente():
    for r in _muestra(150, seed=3):
        goles_ev = [e for e in r.eventos if e['tipo'] == 'gol']
        assert len(goles_ev) == r.goles_local + r.goles_visitante
        assert sum(r.ctx.goles.values()) == len(goles_ev)
        for lado in ('l', 'v'):
            entraron = sum(1 for jid, m in r.ctx.entrada.items() if m > 0 and r.ctx.lado_jugador[jid] == lado)
            salieron = sum(1 for jid in r.ctx.salida if r.ctx.lado_jugador[jid] == lado)
            assert len(r.ctx.en_cancha[lado]) == 11 + entraron - salieron   # nadie desaparece sin evento
            assert r.ctx.cambios[lado] <= 5 and entraron == r.ctx.cambios[lado]
        for e in r.eventos:
            if e['tipo'] in ('gol', 'tiro', 'amarilla') and e['minuto'] > r.ctx.salida.get(e['jugador_id'], 99):
                assert False, f"{e['tipo']} de un jugador que ya había salido"
        assert r.notas and all(3.0 <= v <= 10.0 for v in r.notas.values())
    print("  test_resultado_consistente: OK")

def test_expulsion_pesa():
    """Un equipo que juega casi todo el partido con 10 anota menos que con 11."""
    from alpha_football.engine import simular_rango
    liga, a, b = dos_equipos(); random.seed(5); g10 = g11 = 0
    for _ in range(300):
        c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b))
        j = c.en_cancha['l'][5]
        PC.aplicar_evento(c, {'minuto': 1, 'tipo': 'roja', 'lado': 'l', 'equipo_id': a.id, 'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1})
        g10 += simular_rango(a, b, 2, 90, ctx=c)[0]
        g11 += simular_rango(a, b, 2, 90, ctx=PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b)))[0]
    assert g10 < g11 * 0.92, (g10, g11)
    print("  test_expulsion_pesa: OK")

def test_sin_auto_cambios_no_reemplaza():
    """Lado del user en vivo (auto=False): una lesión deja 10, el motor no mete suplente."""
    from alpha_football.engine import simular_rango
    liga, a, b = dos_equipos()
    c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b), auto_l=False)
    random.seed(11); _gl, _gv, evs = simular_rango(a, b, 1, 90, ctx=c)
    assert c.cambios['l'] == 0 and not any(e['tipo'] == 'cambio' and e['lado'] == 'l' for e in evs)
    assert c.cambios['v'] >= 1
    print("  test_sin_auto_cambios_no_reemplaza: OK")
```

- [ ] **Step 3: Run** → fallan (`simular_rango() got an unexpected keyword argument 'ctx'`, `Resultado` sin `ctx`).

- [ ] **Step 4: Implementar en `engine.py`**
  1. **`Resultado`**: agregar `ctx: Any = None` y `notas: dict = field(default_factory=dict)` al final (dataclass con defaults; revisar que ningún `Resultado(...)` posicional se rompa: `grep -rn "Resultado(" alpha_football tests`).
  2. **Constantes** junto a las de mentalidad:
     ```python
     # v4.0.0: incidencias en el partido (por equipo y minuto)
     PROB_AMARILLA_MIN = 3.5 / 180
     PROB_ROJA_MIN = 0.15 / 180
     PROB_PENAL_GOL = 0.07        # fracción de goles que son de penal
     PROB_PENAL_FALLADO = 0.004   # por equipo-minuto con ataque, penal errado
     PROB_ATAJADA = 0.5           # de los tiros fallados, cuántos los ataja el portero
     PROB_PALO = 0.15             # de los tiros fallados, cuántos son 'ocasion' (palo/travesaño)
     MINUTO_CAMBIOS_IA = (60, 80)
     ```
     Calibrar `PROB_PENAL_FALLADO` para que penales totales ≈ 0.25/partido (≈0.18 goles de penal + ≈0.07 fallados). **Los goles de penal NO son goles extra**: son un 7% de los `gol` que ya salen de `resolver_choque`, reetiquetados (`penal=True`, frase de penal). Así la media de goles no cambia.
  3. **`procesar_minuto(..., ctx=None)`**: si hay ctx, `ja`/`jd` = `ctx.en_cancha[lado]` (lado del atacante/defensor). Por cada expulsado del atacante: `prob *= 0.9`, `ma *= MULT_EXPULSION`; por cada expulsado del defensor: `md *= MULT_EXPULSION`. Tras `resolver_choque`:
     - `gol` → 7% `penal=True`; `asistente_id` = compañero MED/DEL en cancha distinto del goleador con prob 0.7 (si no hay, None); `defensor_id` = defensor.
     - `tiro` → con `PROB_ATAJADA` emite `atajada` (jugador_id = portero rival en cancha, si hay) **en vez de** `tiro`; si no, con `PROB_PALO` tipo `ocasion` (frase de palo/travesaño); si no, `tiro`.
     - otro resultado (defensa) → tipo `defensa` con `jugador_id` = defensor.
     Cada evento se agrega con `lado` y se aplica con `aplicar_evento(ctx, ev)`.
  4. **Incidencias por minuto** (función nueva `_incidencias_minuto(m, local, visitante, ctx, eventos)` llamada desde `_simular_minutos` después de `procesar_minuto`, solo si hay ctx), para cada lado:
     - amarilla con `PROB_AMARILLA_MIN` a un jugador de campo al azar (DEF/MED con peso 2, DEL 1). Si ya tenía una → evento `roja` `motivo='doble amarilla'`, `partidos=1`, precedido del evento `amarilla` (se muestran los dos).
     - roja directa con `PROB_ROJA_MIN`, `partidos = 2 if random() < 0.2 else 1`.
     - lesión: `p = energia.PROB_LESION_90 / 90 * len(en_cancha) * factor_lesion(media energia_vivo)`; jugador al azar ponderado por `factor_lesion(j.energia_vivo)`; `partidos` con `DURACION_LESION`/`PESOS_LESION`. Si `ctx.auto_cambios[lado]` y quedan cambios y hay suplente del mismo puesto (o cualquiera), emitir enseguida un `cambio` (mismo minuto).
     - penal fallado con `PROB_PENAL_FALLADO` (cobrador = el de mayor `penales` en cancha; si falla, `jugador_id` = cobrador).
     - `falta`: con prob 0.10 un evento narrativo `falta` (sin efecto) — solo para variedad de comentarios.
     - cambios por cansancio de la IA: si `ctx.auto_cambios[lado]` y `MINUTO_CAMBIOS_IA[0] <= m <= MINUTO_CAMBIOS_IA[1]` y `ctx.cambios[lado] < objetivo` (objetivo por lado sorteado una vez y guardado en `ctx.__dict__.setdefault('_objetivo_cambios', {})`: `random.randint(3, 5)`), con prob 0.12 por minuto → `elegir_cambio_ia`: sale el de campo con menor `energia_vivo` (desempate: peor `nota_en_vivo`), entra el suplente disponible del mismo puesto con mayor `overall` (si no hay del mismo puesto, el de mayor overall). El que entra arranca con `energia_vivo = j.energia`.
     Frases nuevas (listas de ≥ 5 frases cada una, estilo del archivo): `_AMARILLA`, `_ROJA`, `_DOBLE_AMARILLA`, `_LESION`, `_CAMBIO`, `_PENAL_GOL`, `_PENAL_FALLO`, `_ATAJADA`, `_PALO`, `_FALTA`, `_DEFENSA_EXTRA`. Ampliar `_GOL`/`_FALLO`/`_ATAQUE` con ≥ 5 frases más cada una (variedad pedida).
  5. **`_simular_minutos`**: recibe `ctx`; la energía inicial se asigna a `ctx.en_cancha` (no a `jl/jv`); pasa `ctx` a `procesar_minuto` y llama `_incidencias_minuto`. Un suplente que entra a mitad de tramo recibe `energia_vivo` al entrar (paso 4).
  6. **`simular_partido(..., ctx=None, auto_l=True, auto_v=True)`**: `asegurar_ids_unicos` de ambos **siempre** (no solo con `aplicar_fisico`); si `ctx is None`: `ctx = nuevo_estado(local, visitante, jl, jv, auto_l, auto_v)`. Al final `notas = notas_finales(ctx, gl, gv)`, y `Resultado(..., ctx=ctx, notas=notas)`. El cierre físico (`aplicar_fisico`) pasa a `cerrar_partido(eq, minutos, incidencias=...)` — ver Task 3 (dejar la llamada preparada con los minutos reales `minutos_jugados(ctx)` filtrados por equipo).
  7. **`simular_rango(..., ctx=None)`**: si `ctx is None` crea uno con `_once_titular`; si viene, **no** recalcula el once (usa `ctx.en_cancha`), salvo el lado con `auto_cambios=False`: ese se resincroniza con `[j for j in _once_titular(eq) if j.id not in ctx.fuera]` para tomar los cambios que el user hizo en el menú táctico (función `resincronizar_user(ctx, lado, equipo)` en `partido_ctx.py`, que también registra la entrada de los nuevos con `_registrar(..., minuto=min_inicio)` y la salida de los que ya no están). `energia_vivo = None` al final igual que hoy.
  8. Los partidos de la IA de fondo (`match_screen.simular_otros_partidos`, `league_screen` 2ª, `competiciones._simular`) no cambian de llamada: reciben ctx y notas por el `Resultado`.

- [ ] **Step 5: Run** `tests/test_motor_v400.py` → todo OK. Si `test_frecuencias_y_goles` falla por la media de goles: el penal fallado o la roja están restando goles de más → bajar `PROB_PENAL_FALLADO`, no tocar `resolver_choque`.
- [ ] **Step 6: Run** los tests existentes que usan el motor: `grep -ln "simular_partido\|simular_rango\|procesar_minuto" tests/*.py` y correr cada uno.

---

### Task 3: Una sola fuente de verdad (desarrollo, energía, vestuario, copa)

**Files:**
- Modify: `alpha_football/desarrollo.py:55-135` (`desarrollar_plantilla_post_partido`)
- Modify: `alpha_football/energia.py:102-132` (`cerrar_partido`)
- Modify: `alpha_football/vestuario.py:110-130` (`post_partido_user`)
- Modify (callers): `alpha_football/ui/match_screen.py:267-292` (`simular_otros_partidos`) y `1256-1290` (cierre en vivo), `alpha_football/ui/league_screen.py:160-195` (2ª división), `alpha_football/competiciones.py:888-960` (`_desarrollo_copa`, `_simular`), `alpha_football/ui/copa_screen.py:424-442` (`desarrollo_copa`), `alpha_football/ui/prepartido_screen.py:84-200` (`_simular_instantaneo`)
- Test: `tests/test_motor_v400.py`

**Interfaces:**
- Consumes: `Resultado.ctx`, `Resultado.notas`, `minutos_jugados` (Tasks 1-2).
- Produces:
  - `stats_de_equipo(res_o_ctx, notas, lado) -> dict` en `partido_ctx.py`: `{'jugaron': [jid...], 'goles': {jid:n}, 'asist': {jid:n}, 'notas': {jid:nota}, 'minutos': {jid:min}}` (solo los del lado).
  - `desarrollar_plantilla_post_partido(equipo, gf, gc, indices_jugaron=None, rng=None, stats_partido: Optional[dict] = None) -> list` — con `stats_partido` usa goles/asist/notas reales y los que jugaron (`minutos > 0`); sin él, comportamiento actual.
  - `cerrar_partido(equipo, minutos, rng=None, incidencias: Optional[list] = None) -> list` — con `incidencias` (lista del ctx filtrada al equipo) **no sortea**: aplica `lesion_partidos`/`partidos_sancion` a esos jugadores y devuelve las incidencias en el formato de hoy (`{'tipo', 'jugador', 'partidos'}`); sin él, sortea como hoy.
  - `post_partido_user(..., incidencias: Optional[list] = None, incidencias_rival: Optional[list] = None)` las pasa a `cerrar_partido`.
  - `desarrollo_copa(equipo, gf, gc, jugaron=None, stats_partido=None)` (copa_screen) y `competiciones._desarrollo_copa(equipo, gf, gc, stats_partido=None)` pasan `stats_partido`.
  - En el reporte de desarrollo, cada dict suma `'jugador_id'`, `'amarillas'`, `'roja'`, `'lesion'`, `'minutos'`, `'posicion'` (los usa B para CALIFICACIONES).

- [ ] **Step 1: Tests**

```python
def test_desarrollo_usa_goleadores_reales():
    from alpha_football.engine import simular_partido
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    from alpha_football.partido_ctx import stats_de_equipo
    liga, a, b = dos_equipos(); random.seed(21)
    for _ in range(30):
        r = simular_partido(a, b, aplicar_fisico=False)
        if r.goles_local: break
    antes = {j.id: j.goles for j in a.jugadores}
    rep = desarrollar_plantilla_post_partido(a, r.goles_local, r.goles_visitante,
                                             stats_partido=stats_de_equipo(r.ctx, r.notas, 'l'))
    for j in a.jugadores:
        assert j.goles - antes[j.id] == r.ctx.goles.get(j.id, 0), j.apellido
    for fila in rep:
        assert fila['nota'] == r.notas[fila['jugador_id']]
    print("  test_desarrollo_usa_goleadores_reales: OK")

def test_desarrollo_sin_stats_compat():
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    liga, a, b = dos_equipos()
    rep = desarrollar_plantilla_post_partido(a, 2, 1)
    assert len(rep) == 11 and sum(r['goles'] for r in rep) == 2
    print("  test_desarrollo_sin_stats_compat: OK")

def test_incidencias_del_partido_se_aplican():
    from alpha_football.energia import cerrar_partido
    liga, a, b = dos_equipos(); j = a.jugadores[0]; j.lesion_partidos = 0
    inc = cerrar_partido(a, {x.id: 90 for x in _once_titular(a)},
                         incidencias=[{'tipo': 'lesion', 'jugador_id': j.id, 'partidos': 3}])
    assert j.lesion_partidos == 3 and inc[0]['jugador'] is j and inc[0]['tipo'] == 'lesion'
    otros = [x for x in a.jugadores if x is not j]
    random.seed(0)
    for _ in range(50):
        cerrar_partido(a, {x.id: 90 for x in _once_titular(a)}, incidencias=[])
    assert all(x.partidos_sancion == 0 for x in otros)   # con incidencias=[] no sortea rojas
    print("  test_incidencias_del_partido_se_aplican: OK")
```

- [ ] **Step 2: Run** → fallan (`stats_de_equipo` no existe / `unexpected keyword`).
- [ ] **Step 3: Implementar**
  - `partido_ctx.stats_de_equipo(ctx, notas, lado)` según la interfaz.
  - `desarrollar_plantilla_post_partido`: si `stats_partido`, `participantes` = jugadores de `equipo.jugadores` cuyo `id` esté en `stats_partido['jugaron']`; `gp`/`ap` = de los dicts; `nota` = `stats_partido['notas'].get(j.id)` (si falta, `_nota_partido`); **no** re-sortea. El resto (progreso oculto, valor, potencial, vallas) igual. `valla invicta` sigue igual (`clean_sheet`).
  - `cerrar_partido(..., incidencias=None)`: gasto de energía igual; si `incidencias is not None`, en lugar del sorteo aplica las del equipo (`jugador_id` de un jugador del equipo).
  - `simular_partido` (engine) con `aplicar_fisico`: `cerrar_partido(local, mins_l, incidencias=inc_l)` y lo mismo con visitante, con `mins_*` y `inc_*` filtrados por `ctx.lado_jugador`.
  - Callers: donde hoy se hace `desarrollar_plantilla_post_partido(eq, gf, gc[, jugaron])` tras un `simular_partido`, pasar `stats_partido=stats_de_equipo(res.ctx, res.notas, 'l' | 'v')`. En `_simular_instantaneo` (prepartido): pasar `stats_partido` al desarrollo del user (liga) y a `desarrollo_copa` de ambos (copa); `minutos_user` = `stats['minutos']` del user; `post_partido_user(..., incidencias=inc_user, incidencias_rival=inc_rival)`. **Instantáneo:** el user usa `auto_l/auto_v=True` (reemplazos automáticos). El cierre en vivo de `match_screen` se cablea en la Task 5.
- [ ] **Step 4: Run** `tests/test_motor_v400.py` + `tests/test_vestuario*.py`, `tests/test_copa*.py`, `tests/test_competiciones_v380.py`, `tests/test_fase1_fixes.py` (los que existan). Todos OK.

---

## B · Presentación del partido (v4.1.0)

### Task 4: `ui/postpartido.py` — pantalla CALIFICACIONES / TABLA

**Files:**
- Create: `alpha_football/ui/postpartido.py`
- Test: `tests/test_presentacion_v410.py` (nuevo, cabecera de `test_ux_v360.py`)

**Interfaces:**
- Consumes: reporte de desarrollo (Task 3: `jugador_id`, `jugador`, `nota`, `goles`, `asistencias`, `amarillas`, `roja`, `lesion`, `minutos`, `posicion`); `competiciones`/`copa_screen`: `copa(estado, tipo)`, `tipo_copa_user`, `tabla_fase_liga(c)`, `tablas_grupos(c)`, `grupo_de(c, nombre)`, `fase_user(estado)`, `linea_estado_user(estado)`, `dibujar_tabla_liga`, `dibujar_grupos`.
- Produces:
  - `armar_datos(estado, modo, local, visitante, gl, gv, ctx, notas, eventos, penales=None) -> dict` → guarda en `estado['postpartido']` = `{'modo', 'titulo', 'eventos': [...lineas de linea_de_tiempo...], 'filas_l': [...], 'filas_v': [...], 'figura': (nombre, nota), 'pos_antes': Optional[int]}`.
  - `filas_calificaciones(equipo, ctx, notas, lado) -> list[dict]` (`nombre`, `pos`, `nota`, `g`, `a`, `amar`, `roja`, `lesion`, `entro`, `salio`), titulares primero (por puesto POR→DEF→MED→DEL) y luego los que entraron.
  - `linea_de_tiempo(eventos, local, visitante) -> list[dict]` con `{'minuto', 'tipo', 'lado', 'texto'}` solo para tipos `gol`, `amarilla`, `roja`, `lesion`, `cambio`, `penal_fallado` (orden por minuto; roja por doble amarilla muestra "2ª amarilla").
  - `dibujar_icono(screen, tipo, centro)` — gol: círculo blanco con borde; amarilla/roja: rectángulo 10×14 amarillo/rojo; lesión: cruz roja sobre círculo blanco; cambio: flechas verde ↑ / roja ↓ (dos triángulos); penal fallado: cruz roja.
  - `render(screen, estado, mouse_pos, click_pos, teclas) -> Optional[str]` → devuelve `'continuar'` con Enter/Espacio o clic en `R_CONTINUAR`; ←/→ o clic en pestañas cambia `estado['postpartido_tab']` entre `'calificaciones'` y `'tabla'` (amistoso: solo calificaciones). ↑/↓ desplaza la lista si no cabe.
  - Rects exportados: `R_TAB_CALIF`, `R_TAB_TABLA`, `R_CONTINUAR` (y=648, como `rects_resultado`), `R_PANEL`.
  - `posicion_liga(liga, equipo_id) -> int` (1-based, orden `_clave_tabla` de league_screen).

- [ ] **Step 1: Tests**

```python
from alpha_football.ui import postpartido as PP
from alpha_football.engine import simular_partido, _once_titular

def _partido(e):
    liga = e['liga']; a, b = liga.equipos[0], liga.equipos[1]
    random.seed(9); r = simular_partido(a, b, aplicar_fisico=False)
    return a, b, r

def test_linea_de_tiempo_filtra_y_ordena():
    e = estado_carrera(); a, b, r = _partido(e)
    lt = PP.linea_de_tiempo(r.eventos, a, b)
    assert [x['minuto'] for x in lt] == sorted(x['minuto'] for x in lt)
    assert {x['tipo'] for x in lt} <= {'gol', 'amarilla', 'roja', 'lesion', 'cambio', 'penal_fallado'}
    assert sum(1 for x in lt if x['tipo'] == 'gol') == r.goles_local + r.goles_visitante
    print("  test_linea_de_tiempo_filtra_y_ordena: OK")

def test_filas_calificaciones():
    e = estado_carrera(); a, b, r = _partido(e)
    filas = PP.filas_calificaciones(a, r.ctx, r.notas, 'l')
    assert len(filas) >= 11 and all(3.0 <= f['nota'] <= 10.0 for f in filas)
    assert filas[0]['pos'] == 'POR'
    print("  test_filas_calificaciones: OK")

def test_postpartido_teclado():
    e = estado_carrera(); a, b, r = _partido(e)
    PP.armar_datos(e, 'liga', a, b, r.goles_local, r.goles_visitante, r.ctx, r.notas, r.eventos)
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RIGHT]) is None and e['postpartido_tab'] == 'tabla'
    assert PP.render(screen, e, (0, 0), None, [pygame.K_LEFT]) is None and e['postpartido_tab'] == 'calificaciones'
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RETURN]) == 'continuar'
    assert PP.render(screen, e, (0, 0), PP.R_CONTINUAR.center, []) == 'continuar'
    print("  test_postpartido_teclado: OK")

def test_amistoso_sin_tabla():
    e = estado_carrera(); a, b, r = _partido(e)
    PP.armar_datos(e, 'amistoso', a, b, 1, 0, r.ctx, r.notas, r.eventos)
    PP.render(screen, e, (0, 0), None, [pygame.K_RIGHT])
    assert e.get('postpartido_tab', 'calificaciones') == 'calificaciones'
    print("  test_amistoso_sin_tabla: OK")
```

- [ ] **Step 2: Run** → `ModuleNotFoundError`.
- [ ] **Step 3: Implementar** según interfaces. Layout (1280×720, nada en y ≥ 698): título + marcador arriba (y 40-120), pestañas en y=130, panel `R_PANEL = Rect(40, 170, 1200, 460)`, `R_CONTINUAR = Rect(520, 648, 240, 44)`.
  - CALIFICACIONES: dos columnas (local izq., visitante der.), una fila por jugador (`pos`, nombre recortado, íconos de g/a/tarjetas/lesión/cambio con `dibujar_icono`, nota a la derecha coloreada: ≥ 8 verde, ≥ 6.5 blanco, ≥ 5.5 dorado, < 5.5 rojo). Arriba del panel: "FIGURA: nombre (nota)".
  - TABLA (liga): tabla de la liga del user con su fila resaltada y flecha ↑ verde / ↓ roja / = según `pos_antes` vs `posicion_liga(...)` ahora. Si la liga tiene 12 equipos cabe entera (fila 30 px).
  - TABLA (copa): si la fase del user es fase de liga (champions) → `dibujar_tabla_liga(screen, R_PANEL, c, user, compacto=True)`; si es grupos → `dibujar_grupos(..., solo=grupo_de(c, user))`; si es llaves → texto grande `linea_estado_user(estado)` ("Pasas a Cuartos" / "Eliminado en ...") + `dibujar_llaves(..., compacto=True)`.
- [ ] **Step 4: Run** → OK.

### Task 5: En vivo — ctx revelado, pausas con aviso, lesión/roja del user, cierre por ctx

**Files:**
- Modify: `alpha_football/ui/match_screen.py` — init (715-790), ticker (792-935), re-simulaciones (`_cambiar_mentalidad_en_vivo` 547-568, táctico 1163-1181, 2ª mitad 1183-1215), `_menu_tactico` (485-515: bloquear expulsados), cierre `finalizado` (1217-1410).
- Test: `tests/test_presentacion_v410.py`

**Interfaces:**
- Consumes: `partido_ctx` (Task 1), `simular_rango(..., ctx=)` y `resincronizar_user` (Task 2), `stats_de_equipo`, `cerrar_partido(..., incidencias=)`, `post_partido_user(..., incidencias=)` (Task 3), `postpartido` (Task 4).
- Produces:
  - `estado['sim_ctx']`: ctx **revelado** (solo eventos ya mostrados). Creado en la init con `nuevo_estado(local, visitante, _once_titular(local), _once_titular(visitante), auto_l=not user_es_local, auto_v=user_es_local)` (amistoso: el user es local).
  - Cada `simular_rango` recibe `ctx=estado['sim_ctx'].copia()` **resincronizado** con el user (`resincronizar_user`) — así el pre-simulado nunca ensucia el revelado.
  - Al revelar un evento: `aplicar_evento(estado['sim_ctx'], e)` (para `cambio` con `_entra_obj`).
  - `PAUSA_MS = {'gol': 2500, 'roja': 2000, 'lesion': 2000, 'amarilla': 1000}` divididos por `sim_velocidad_factor`; `estado['sim_pausa_hasta']` (ticks) y `estado['sim_aviso'] = {'tipo', 'texto', 'color'}`; el reloj no avanza mientras `now < sim_pausa_hasta`; Enter/Espacio la termina.
  - `estado['sim_cambio_forzado'] = jid` cuando se lesiona un jugador del user y quedan cambios: abre el selector (overlay) — lista de suplentes disponibles (`suplentes_disponibles(ctx, lado, user_eq)`), ↑/↓ + Enter o clic; aplica el cambio en la alineación del user (mismo swap que usa `_menu_tactico` para un cambio: buscar la función de swap y reutilizarla; suma `sim_subs_realizadas`, agrega a `sim_salieron`), emite el evento `cambio` al ctx revelado y **re-simula** desde `minuto + 1` hasta el fin de la mitad (igual que el cierre del menú táctico). Sin cambios disponibles: aviso "Sin cambios: juegas con 10" y se re-simula igual (el lesionado ya no está en `en_cancha`).
  - Roja del user: aviso + re-simulación desde `minuto + 1` (el expulsado queda en `fuera`); en `_menu_tactico` un jugador en `sim_ctx.fuera` no puede elegirse como "sale" ni como "entra" (mostrarlo gris con "EXP"/"LES").
  - `estado['sim_nota_por_jugador']` pasa a leerse de `nota_en_vivo(sim_ctx, jid)` (borrar la suma manual de +0.6/+0.3 y el `random.choice` de asistente del ticker: el goleador y el asistente ya vienen en el evento; el texto del gol usa `jugador_id`/`asistente_id` del evento).
  - Cierre: al entrar a `finalizado` (una sola vez, `sim_desarrollo_done`): `notas = notas_finales(sim_ctx, gl, gv)`; desarrollo con `stats_partido=stats_de_equipo(sim_ctx, notas, lado)` para ambos equipos; `post_partido_user(..., minutos=stats['minutos'], incidencias=..., incidencias_rival=...)`; **y además** cerrar la jornada/copa **en ese momento** (liga: `finalizar_jornada_liga(...)`; copa: `registrar_resultado_copa(...)`) para que la pestaña TABLA muestre la posición nueva. Antes de cerrar, guardar `pos_antes = posicion_liga(liga, mi_equipo.id)`. Luego `postpartido.armar_datos(...)` y el panel final se reemplaza por `postpartido.render`; `'continuar'` hace la limpieza de claves y el return de hoy (sin volver a llamar `finalizar_jornada_liga` / `registrar_resultado_copa`: ya están guardados por `partido.jugado` y por el motor de copa, pero **no** llamarlos dos veces).

- [ ] **Step 1: Tests** (manejan el render en vivo con el reloj forzado; ver cómo lo hacen los tests existentes: `grep -ln "match_screen" tests/*.py`, p. ej. el de mentalidad v2.5.0, y copiar su helper para avanzar minutos — típicamente fijando `estado['sim_last_tick'] = -10**9` antes de cada `render`).

```python
from alpha_football.ui import match_screen as MS
from alpha_football import partido_ctx as PC

def _preparar_vivo(e):
    liga = e['liga']; mi = e['mi_equipo']
    p = next(p for p in liga.calendario if p.jornada == liga.jornada_actual and mi.id in (p.local_id, p.visitante_id))
    e['partido_actual'] = p; e['match_mode'] = 'liga'
    return p

def _avanzar(e, hasta):
    while e.get('sim_minuto', 0) < hasta and e.get('sim_estado') in (None, 'jugando', 'segundo_tiempo'):
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0
        pygame.event.clear(); MS.render(screen, e)

def test_resim_respeta_expulsado():
    e = estado_carrera(); _preparar_vivo(e); pygame.event.clear(); MS.render(screen, e)
    ctx = e['sim_ctx']; lado = 'l' if e['partido_actual'].local_id == e['mi_equipo'].id else 'v'
    rival = 'v' if lado == 'l' else 'l'
    j = ctx.en_cancha[rival][4]
    ev = {'minuto': 10, 'tipo': 'roja', 'lado': rival, 'equipo_id': ctx.ids_equipo[rival], 'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1, 'detalle': ''}
    e['sim_eventos'] = [x for x in e['sim_eventos'] if x['minuto'] != 10] + [ev]
    _avanzar(e, 12)
    assert j.id in e['sim_ctx'].fuera
    liga = e['liga']; p = e['partido_actual']
    loc = next(x for x in liga.equipos if x.id == p.local_id); vis = next(x for x in liga.equipos if x.id == p.visitante_id)
    MS._cambiar_mentalidad_en_vivo(e, e['mi_equipo'], loc, vis, 'todo_o_nada', e['sim_minuto'])
    futuros = [x for x in e['sim_eventos'] if x['minuto'] > 12]
    assert all(x.get('jugador_id') != j.id for x in futuros if x['tipo'] in ('gol', 'tiro', 'amarilla', 'ocasion'))
    print("  test_resim_respeta_expulsado: OK")

def test_lesion_sin_cambios():
    e = estado_carrera(); _preparar_vivo(e); pygame.event.clear(); MS.render(screen, e)
    ctx = e['sim_ctx']; lado = 'l' if e['partido_actual'].local_id == e['mi_equipo'].id else 'v'
    e['sim_subs_realizadas'] = 5; ctx.cambios[lado] = 5
    j = ctx.en_cancha[lado][6]
    ev = {'minuto': 20, 'tipo': 'lesion', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador_id': j.id, 'partidos': 2, 'detalle': ''}
    e['sim_eventos'] = [x for x in e['sim_eventos'] if x['minuto'] != 20] + [ev]
    _avanzar(e, 22)
    assert not e.get('sim_cambio_forzado') and len(e['sim_ctx'].en_cancha[lado]) == 10
    print("  test_lesion_sin_cambios: OK")

def test_lesion_abre_selector_y_cambia():
    e = estado_carrera(); _preparar_vivo(e); pygame.event.clear(); MS.render(screen, e)
    ctx = e['sim_ctx']; lado = 'l' if e['partido_actual'].local_id == e['mi_equipo'].id else 'v'
    j = ctx.en_cancha[lado][6]
    ev = {'minuto': 20, 'tipo': 'lesion', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador_id': j.id, 'partidos': 2, 'detalle': ''}
    e['sim_eventos'] = [x for x in e['sim_eventos'] if x['minuto'] != 20] + [ev]
    _avanzar(e, 20)
    assert e.get('sim_cambio_forzado') == j.id
    key(pygame.K_RETURN); MS.render(screen, e)
    assert not e.get('sim_cambio_forzado') and len(e['sim_ctx'].en_cancha[lado]) == 11
    assert e['sim_subs_realizadas'] == 1
    print("  test_lesion_abre_selector_y_cambia: OK")

def test_pausa_en_gol():
    e = estado_carrera(); _preparar_vivo(e); pygame.event.clear(); MS.render(screen, e)
    g = next((x for x in e['sim_eventos'] if x['tipo'] == 'gol'), None)
    if g is None:
        print("  test_pausa_en_gol: (sin goles en 1T, se omite)"); return
    while e['sim_minuto'] < g['minuto']:
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0; pygame.event.clear(); MS.render(screen, e)
    assert e['sim_pausa_hasta'] > pygame.time.get_ticks() and e['sim_aviso']['tipo'] == 'gol'
    m = e['sim_minuto']; e['sim_last_tick'] = -10**9; pygame.event.clear(); MS.render(screen, e)
    assert e['sim_minuto'] == m                       # pausado: no avanza
    key(pygame.K_SPACE); MS.render(screen, e)
    assert e['sim_pausa_hasta'] == 0
    print("  test_pausa_en_gol: OK")
```
(`_cambiar_mentalidad_en_vivo(estado, user_eq, local, visitante, nueva, minuto)` está en `match_screen.py:547`; `'todo_o_nada'` es una clave válida de `EFECTO_MENTALIDAD`.)

- [ ] **Step 2: Run** → fallan (`sim_ctx` no existe).
- [ ] **Step 3: Implementar** según interfaces. El aviso se dibuja centrado (panel 640×120 en y≈300) con `postpartido.dibujar_icono`, texto grande y "Enter para seguir". El confeti del gol se mantiene. Los comentarios del ticker usan el `detalle` de cada evento (los tipos nuevos ya traen frases del motor); `defensa`/`tiro`/`atajada`/`ocasion`/`falta` siguen apareciendo solo como comentario (sin pausa).
- [ ] **Step 4: Run** `tests/test_presentacion_v410.py` + tests existentes de match_screen/mentalidad (`grep -ln "match_screen" tests/*.py`). OK.

### Task 6: Simulación instantánea con línea de tiempo + post-partido

**Files:**
- Modify: `alpha_football/ui/prepartido_screen.py:84-370` (`_simular_instantaneo`, `rects_resultado`, `_render_resultado`)
- Test: `tests/test_presentacion_v410.py`

**Interfaces:**
- Consumes: `postpartido.armar_datos/linea_de_tiempo/dibujar_icono/render/posicion_liga` (Task 4), `Resultado.ctx/notas` (Task 2), stats (Task 3).
- Produces: `estado['prepartido_resultado']` gana `'linea': list` (de `linea_de_tiempo`); `estado['prepartido_paso']` ∈ `{'resumen', 'post'}`.

- [ ] **Step 1: Tests**

```python
from alpha_football.ui import prepartido_screen as PR

def test_instantaneo_resumen_luego_post():
    e = estado_carrera(); p = _preparar_vivo(e); liga = e['liga']
    loc = next(x for x in liga.equipos if x.id == p.local_id); vis = next(x for x in liga.equipos if x.id == p.visitante_id)
    random.seed(4); PR._simular_instantaneo(e, loc, vis)
    r = e['prepartido_resultado']
    assert 'linea' in r and all('minuto' in x for x in r['linea'])
    assert e.get('postpartido') and p.jugado
    key(pygame.K_RETURN); PR.render(screen, e)          # resumen -> post
    assert e.get('prepartido_paso') == 'post'
    key(pygame.K_RETURN); dest = PR.render(screen, e)   # post -> continuar
    assert dest == 'league_screen' and 'prepartido_resultado' not in e
    print("  test_instantaneo_resumen_luego_post: OK")
```
- [ ] **Step 2: Run** → falla (`'linea'`).
- [ ] **Step 3: Implementar**
  - `_simular_instantaneo`: guarda `pos_antes = postpartido.posicion_liga(liga, mi_equipo.id)` antes de `finalizar_jornada_liga`; arma `'linea'`; llama `postpartido.armar_datos(...)` con `res.ctx`, `res.notas`, `res.eventos` (+ `pos_antes`); en copa, igual después de `registrar_resultado_copa`.
  - `_render_resultado` (paso `'resumen'`, default): el panel GOLES pasa a ser **línea de tiempo**: columna local (x del panel + 20) y visitante (alineada a la derecha) con `minuto'` + ícono + texto; ↑/↓ desplazan si hay más de 9 filas. Con penales se mantiene el panel derecho actual. Botón **CONTINUAR** → pasa a `'post'` (Enter/Espacio también).
  - Paso `'post'`: `postpartido.render(...)`; `'continuar'` ejecuta la limpieza y el return que hoy están en el clic de CONTINUAR (`estado.pop('postpartido')`, `prepartido_paso`, `postpartido_tab` incluidos).
- [ ] **Step 4: Run** + tests existentes del prepartido (`grep -ln "prepartido" tests/*.py`, p. ej. `test_hub_v240.py`: actualizar si usaban el rect de CONTINUAR para salir directo — ahora hay dos pasos). OK.

---

## C · Teclado y correo (v4.2.0)

### Task 7: Menú inicial con teclado

**Files:**
- Modify: `alpha_football/ui/menu.py:1054-1110` (paso `'main'`)
- Test: `tests/test_teclado_v420.py` (nuevo)

**Interfaces:**
- Produces: `botones_main() -> list[tuple[str, Rect, str]]` (texto, rect, acción) en orden de foco; `estado['menu_foco']` (int).

- [ ] **Step 1: Tests**

```python
from alpha_football.ui import menu as M

def test_menu_main_teclado():
    e = {'menu_step': 'main'}
    pygame.event.clear(); M.render(screen, e)
    assert e.get('menu_foco', 0) == 0
    key(pygame.K_DOWN); M.render(screen, e); assert e['menu_foco'] == 1
    key(pygame.K_UP); M.render(screen, e); key(pygame.K_UP); M.render(screen, e)
    assert e['menu_foco'] == len(M.botones_main()) - 1          # da la vuelta
    e['menu_foco'] = [b[2] for b in M.botones_main()].index('opciones')
    key(pygame.K_RETURN); assert M.render(screen, e) == 'options_screen'
    print("  test_menu_main_teclado: OK")
```
- [ ] **Step 2: Run** → falla.
- [ ] **Step 3: Implementar**: ↑/↓ (y Tab) mueven `menu_foco` con vuelta; Enter/Espacio ejecutan la misma acción que el clic; el botón con foco se dibuja con `hover=True` (el mouse sobre otro botón mueve el foco a ese). Revisar que los pasos siguientes (`select_country`, división, club, carga, amistoso, `dt_setup`) ya tienen teclado (sí: `menu.py:1185, 1332, 1816, 1898`); el de carga de slots (`rects_slots_carga`) — si no tiene ↑/↓+Enter, agregarlo con el mismo patrón.
- [ ] **Step 4: Run** → OK.

### Task 8: Partido en vivo, menú táctico y penales con teclado

**Files:**
- Modify: `alpha_football/ui/match_screen.py` (después de la Task 5): eventos del render principal, `_menu_tactico`, `_menu_penales`; `alpha_football/ui/atajos.py` (`SIN_BARRA` sigue sin barra en partido: las teclas se muestran en una línea propia arriba del campo).
- Test: `tests/test_teclado_v420.py`

**Interfaces:**
- Produces: teclas en vivo: **V** velocidad (x1→x2→x5), **T** táctica (abre overlay), **1/2/3** (o ←/→) mentalidad por la tira, **Enter/Espacio** salta aviso / REANUDAR en medio tiempo y táctico / CONTINUAR en post-partido. En `_menu_tactico`: ↑/↓ jugador, **Tab** cambia entre titulares y banco, Enter selecciona (1ª vez = sale, 2ª = entra → swap), **[ ]** formación, **R** reanudar, ESC cierra (= reanudar en táctico en vivo). En `_menu_penales`: ↑/↓ + Enter elige cobradores, **A** automático (los 5 de mayor `penales`), Enter con 5 = DEFINIR.

- [ ] **Step 1: Tests**

```python
def test_vivo_teclas_velocidad_y_tactica():
    from alpha_football.ui import match_screen as MS
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    e['partido_actual'] = next(p for p in liga.calendario if p.jornada == liga.jornada_actual and mi.id in (p.local_id, p.visitante_id))
    e['match_mode'] = 'liga'; pygame.event.clear(); MS.render(screen, e)
    v0 = e['sim_velocidad_factor']; key(pygame.K_v); MS.render(screen, e)
    assert e['sim_velocidad_factor'] != v0
    key(pygame.K_t); MS.render(screen, e); assert e.get('sim_tactico_abierto')
    key(pygame.K_ESCAPE); MS.render(screen, e); assert not e.get('sim_tactico_abierto')
    print("  test_vivo_teclas_velocidad_y_tactica: OK")
```
- [ ] **Step 2-4:** Run → falla; implementar (reusar el código de clic de cada botón; `_menu_tactico` recibe `teclas` como `_menu_penales`); Run → OK + tests de match_screen existentes.

### Task 9: Auditoría de teclado en el resto de pantallas y overlays

**Files (conteo actual de handlers de teclado → lo que falta):**
- `despido_screen.py` (0): ↑/↓ entre ofertas + Enter aceptar; Enter en "Continuar".
- `promo_releg_screen.py`, `resumen_temporada_screen.py`, `veredicto_screen.py` (1): Enter/Espacio en el botón principal; ↑/↓ si hay más de un botón.
- `ofertas_dt_screen.py`, `ojeador_screen.py`, `finanzas_screen.py`, `negociacion_screen.py` (1): foco ↑/↓/Tab sobre sus botones + Enter; en negociación, ←/→ ajusta el monto si hay campo de monto (sin romper `entrada_monto` cuando `texto_activo`).
- `edit_screen.py` (2): Tab/↑/↓ recorre pestañas/botones principales (IMPORTAR, RESTAURAR, APLICAR Y GUARDAR, VOLVER) + Enter; la edición de campos sigue con clic + teclado de texto.
- `career_screen.py`, `correo_screen.py`, `objetivos_screen.py`, `contrato_dt_screen.py`: verificar que cada botón visible tenga tecla (p. ej. en correo, Enter abre y **A** ejecuta la acción del mensaje; ESC vuelve).
- Overlays: diálogo salir de league_screen (ya tiene), filtros del buscador (ya), `ficha_jugador.py` (ESC cierra; ←/→ jugador anterior/siguiente si la pantalla que la abre tiene lista), dropdowns del editor (↑/↓ + Enter + ESC).
- `ui/atajos.py`: actualizar `ATAJOS` de cada pantalla tocada; `ui/ayuda.py`: donde se nombren teclas, agregar las nuevas.
- Test: `tests/test_teclado_v420.py`

**Interfaces:**
- Patrón común (copiar el de `prepartido_screen.botones_menu` + `_navegar`): cada pantalla expone `botones_<pantalla>(estado) -> list[tuple[str, Rect, str]]` y guarda el foco en `estado['foco_<pantalla>']`; el botón con foco se dibuja con `hover=True`.

- [ ] **Step 1: Test genérico de humo** (cada pantalla auditada: con Enter sobre el foco inicial devuelve un destino o cambia estado, y con ESC — donde aplique — devuelve el destino de volver):

```python
PANTALLAS_ESC = ['finanzas_screen', 'ojeador_screen', 'ofertas_dt_screen', 'negociacion_screen',
                 'career_screen', 'correo_screen', 'objetivos_screen', 'contrato_dt_screen']

def test_esc_vuelve_en_todas():
    import importlib
    for nombre in PANTALLAS_ESC:
        e = estado_carrera(); mod = importlib.import_module(f'alpha_football.ui.{nombre}')
        pygame.event.clear(); mod.render(screen, e)
        key(pygame.K_ESCAPE); dest = mod.render(screen, e)
        assert dest, nombre
    print("  test_esc_vuelve_en_todas: OK")

def test_foco_enter_en_pantallas_de_un_boton():
    import importlib
    for nombre in ('promo_releg_screen', 'resumen_temporada_screen', 'veredicto_screen', 'despido_screen'):
        mod = importlib.import_module(f'alpha_football.ui.{nombre}')
        assert hasattr(mod, 'botones_' + nombre.replace('_screen', '')), nombre
    print("  test_foco_enter_en_pantallas_de_un_boton: OK")
```
(Las pantallas que necesitan datos previos — despido, veredicto, promo/releg, negociación — preparar el `estado` como lo hacen sus tests existentes: `grep -ln "<pantalla>" tests/*.py`.)
- [ ] **Step 2-4:** Run → falla; implementar pantalla por pantalla; Run → OK + tests existentes de cada pantalla tocada.

### Task 10: Atajos globales M/O, GUARDAR dentro de Opciones, sobre de correo en INICIO

**Files:**
- Modify: `main.py` (nueva `procesar_atajos_globales(estado, eventos) -> list` llamada justo después de `filtrar_eventos_ayuda`, ~línea 548)
- Modify: `alpha_football/ui/league_screen.py:325-340` (`BARRA_MENU`, `DESTINO_DIRECTO`: quitar `'guardar'`), render de INICIO (sobre de correo)
- Modify: `alpha_football/ui/options_screen.py` (botón GUARDAR PARTIDA solo si hay carrera; navegable con ↑/↓/Enter como las otras opciones)
- Modify: `alpha_football/ui/ayuda.py:404` (texto de la barra: ya no hay GUARDAR), `alpha_football/ui/atajos.py` (league_screen: "M Correo · O Opciones")
- Test: `tests/test_teclado_v420.py`

**Interfaces:**
- Produces:
  - `main.procesar_atajos_globales(estado, eventos) -> list` (devuelve los eventos no consumidos). Activo solo si `estado.get('mi_equipo')` (carrera), no `texto_activo`, no `ayuda_abierta`, y la pantalla actual no está en `SIN_ATAJOS_GLOBALES = {'menu', 'match_screen', 'prepartido_screen', 'options_screen', 'edit_screen', 'buscador_screen', 'despido_screen', 'veredicto_screen', 'contrato_dt_screen', 'resumen_temporada_screen', 'promo_releg_screen', 'save_slots_screen'}`. **M** → `estado['current_screen'] = 'correo_screen'`; **O** → `estado['options_return'] = pantalla actual`, `current_screen = 'options_screen'`. (Si la pantalla actual ya es la destino, no hace nada.) Marcar `estado['pantalla_anterior']` igual que la transición normal.
  - `options_screen`: ítem "GUARDAR PARTIDA" (solo si `estado.get('mi_equipo')` y no `amistoso`) → `estado['save_mode'] = 'guardar'` (usar la clave que hoy usa la barra para abrir `save_slots_screen` en modo guardar: `grep -n "save_slots_screen" alpha_football/ui/league_screen.py`) y devuelve `'save_slots_screen'`; al volver de guardar, ESC regresa a Opciones.
  - `league_screen.R_SOBRE = Rect(1216, 8, 48, 34)` (arriba a la derecha de INICIO; verificar que no pise la barra de columnas: si la barra llega a x=1264, mover la barra o poner el sobre en la fila de título de INICIO — medir con los rects de `BARRA_MENU`); `dibujar_sobre(screen, rect, n)` — sobre dibujado (rect + dos líneas en V), círculo rojo con el número si `n > 0` (`"9+"` si `n > 9`); clic → `'correo_screen'`.

- [ ] **Step 1: Tests**

```python
import main as MAIN
from alpha_football.ui import league_screen as L
from alpha_football import correo as C

def _ev(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode='')

def test_atajos_globales_m_o():
    e = estado_carrera(); e['current_screen'] = 'league_screen'
    quedan = MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m)])
    assert quedan == [] and e['current_screen'] == 'correo_screen'
    e['current_screen'] = 'stats_screen'
    MAIN.procesar_atajos_globales(e, [_ev(pygame.K_o)])
    assert e['current_screen'] == 'options_screen' and e['options_return'] == 'stats_screen'
    print("  test_atajos_globales_m_o: OK")

def test_atajos_globales_con_texto():
    e = estado_carrera(); e['current_screen'] = 'league_screen'; e['texto_activo'] = True
    quedan = MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m)])
    assert len(quedan) == 1 and e['current_screen'] == 'league_screen'
    e['texto_activo'] = False; e['current_screen'] = 'options_screen'
    assert len(MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m)])) == 1   # M = mute en opciones
    print("  test_atajos_globales_con_texto: OK")

def test_guardar_en_opciones_solo_carrera():
    from alpha_football.ui import options_screen as O
    e = estado_carrera(); pygame.event.clear(); O.render(screen, e)
    assert any('GUARDAR' in t for t, *_ in O.items_opciones(e))
    assert not any('GUARDAR' in t for t, *_ in O.items_opciones({}))
    assert 'guardar' not in [b[0] for b in L.BARRA_MENU]
    print("  test_guardar_en_opciones_solo_carrera: OK")

def test_sobre_badge():
    e = estado_carrera()
    assert L.texto_badge(0) is None and L.texto_badge(3) == '3' and L.texto_badge(12) == '9+'
    for i in range(3):
        C.enviar(e, 'club', f'm{i}', 'x')
    e['hub_tab'] = 'inicio'; click(L.R_SOBRE.center)
    assert L.render(screen, e) == 'correo_screen'
    print("  test_sobre_badge: OK")
```
(`O.items_opciones(estado) -> list[tuple[str, ...]]`: si options_screen hoy no tiene una lista así, crearla a partir de su lista de filas navegables — leer `options_screen.py` completo antes.)
- [ ] **Step 2-4:** Run → falla; implementar; Run → OK + `tests/test_ux_v360.py`, `tests/test_hub_v240.py`, `tests/test_ayuda_v390.py` (usan la barra y opciones; actualizar lo que asuma GUARDAR en la barra).

---

## D · Copa, objetivos, historial, Balón de Oro (v4.3.0)

### Task 11: Correos de premio por fase y de objetivo cumplido

**Files:**
- Modify: `alpha_football/ui/copa_screen.py:181-220` (`cobrar_premios_copa`)
- Modify: `alpha_football/directiva.py` (nuevas `revisar_objetivo_copa_cumplido(estado)` y `revisar_objetivo_liga_asegurado(estado)`; ver `definir_objetivo` 59, `definir_objetivo_copa` 450, `meta_copa` 431, `_indice_fase_copa` 425)
- Modify: `alpha_football/ui/match_screen.py` `finalizar_jornada_liga` (llamar `revisar_objetivo_liga_asegurado` al final, en su propio try) y `copa_screen.registrar_resultado_copa` / `simular_copa_fondo` (tras cobrar premios, `revisar_objetivo_copa_cumplido`)
- Test: `tests/test_copa_v430.py` (nuevo)

**Interfaces:**
- Produces:
  - `premio_total(tipo) -> int` (suma de la tabla) y `texto_premio(tipo, fase, acumulado) -> str` en copa_screen: `"Premio por alcanzar {fase}: ${monto:,} ({p}% del premio total; acumulado {q}%)"` con p/q enteros redondeados.
  - En `cobrar_premios_copa`: un correo `C.enviar(estado, 'directiva', f"Premio de {nombre_copa}: {fase}", texto_premio(...), C.accion('finanzas_screen', "VER FINANZAS"))` **por cada fase cobrada** en esa llamada.
  - `revisar_objetivo_copa_cumplido(estado) -> bool`: si hay objetivo de copa, la fase actual del user (`competiciones.fase_user`) alcanza o supera la meta (`_indice_fase_copa`) y `datos_carrera['objetivos_avisados']` no tiene `('copa', temporada)` → correo "Objetivo cumplido: {meta} en {copa}" + marca. Devuelve si envió.
  - `revisar_objetivo_liga_asegurado(estado) -> bool`: meta de liga = `pos_max` del objetivo; asegurado si la cantidad de equipos que **todavía pueden** superar tus puntos (`puntos_rival + 3 * partidos_restantes_rival > tus_puntos`) más los que ya están por encima es `< pos_max` … es decir, `peor_posicion_posible(liga, mi) <= pos_max`. Correo "Objetivo asegurado: terminar entre los {pos_max} primeros" una vez por temporada (`('liga', temporada)`). Para metas de "no descender", asegurado cuando la peor posición posible queda fuera de la zona de descenso.
  - `peor_posicion_posible(liga, equipo) -> int` en directiva (empates en puntos cuentan como posible sobrepaso: criterio conservador).

- [ ] **Step 1: Tests**

```python
from alpha_football.ui import copa_screen as CS
from alpha_football import directiva as D, correo as C

def test_texto_premio_porcentajes():
    total = CS.premio_total('champions')
    t = CS.texto_premio('champions', 'Cuartos', 11_000_000)
    assert 'Cuartos' in t and f"{round(5_000_000 * 100 / total)}%" in t and f"{round(11_000_000 * 100 / total)}%" in t
    print("  test_texto_premio_porcentajes: OK")

def test_peor_posicion_posible():
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    for eq in liga.equipos: eq.puntos = 0
    mi.puntos = 100; liga.jornada_actual = liga.num_jornadas
    for p in liga.calendario: p.jugado = True
    assert D.peor_posicion_posible(liga, mi) == 1
    for p in liga.calendario: p.jugado = False
    mi.puntos = 0
    assert D.peor_posicion_posible(liga, mi) == len(liga.equipos)
    print("  test_peor_posicion_posible: OK")

def test_objetivo_liga_avisa_una_vez():
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    D.definir_objetivo(e)
    for p in liga.calendario: p.jugado = True
    for eq in liga.equipos: eq.puntos = 0
    mi.puntos = 99
    n0 = len(C.bandeja(e))
    assert D.revisar_objetivo_liga_asegurado(e) is True and len(C.bandeja(e)) == n0 + 1
    assert D.revisar_objetivo_liga_asegurado(e) is False and len(C.bandeja(e)) == n0 + 1
    print("  test_objetivo_liga_avisa_una_vez: OK")
```
(Si `definir_objetivo` necesita más estado, prepararlo como `tests/test_directiva_v280.py`. Verificar cómo se llaman los atributos de puntos del equipo/tabla: `_clave_tabla` de league_screen usa `eq.puntos`, `eq.gf`, `eq.gc`.)
- [ ] **Step 2-4:** Run → falla; implementar; Run → OK + `tests/test_directiva_v280.py`, `tests/test_competiciones_v380.py`, `tests/test_carrera_dt*.py`.

### Task 12: Historial de INICIO con partidos de copa + Balón de Oro sobre liga + copa

**Files:**
- Modify: `alpha_football/ui/league_screen.py:680-760` (historial de INICIO)
- Read only: `alpha_football/competiciones.py:907-935` (`_acumular_stats` ya cuenta `pj` por jugador de copa; con la Task 3 el reporte trae solo a los que jugaron de verdad)
- Modify: `alpha_football/premios.py:59-110` (`_stats_copa_por_jugador` devuelve también `pj`; `min_pj` y el filtro usan liga + copa)
- Test: `tests/test_copa_v430.py`

**Interfaces:**
- Produces:
  - `partidos_historial(estado) -> list[dict]` en league_screen: `{'orden': (jornada, 0|1), 'etiqueta': 'J5' | 'UCL' | 'LIB', 'local', 'visitante', 'gl', 'gv', 'es_local': bool}` — liga (partidos jugados del user) + copa (partidos jugados del user en `competiciones.copa(estado, tipo_copa_user(estado))['partidos']`, con jornada `jornada_de_fecha(fecha, n_fechas, num_jornadas)`); orden cronológico; copa después de la liga en la misma jornada. Penales en copa: `" (4-3 p)"` al final.
  - `premios._stats_copa_por_jugador` → `{(club, nombre): {'goles', 'asist', 'vallas', 'pj'}}` (`pj` ya se acumula en `competiciones._acumular_stats`; solo falta leerlo).
  - `calcular_balon_de_oro`: `pj_total = partidos_jugados + sc.get('pj', 0)`; `partidos_copa_eq` = máximo `pj` de copa entre los jugadores de ese club (proxy de partidos de copa del equipo); `min_pj = max(3, int((jornadas + partidos_copa_eq) * MIN_PARTIDOS_PCT))`; filtro `pj_total < min_pj`. En la ficha, `'pj'` = `pj_total`.

- [ ] **Step 1: Tests**

```python
def test_historial_incluye_copa():
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    import alpha_football.competiciones as K
    K.iniciar_temporada(e, forzar=True)
    tipo = K.tipo_copa_user(e)
    if tipo is None:
        print("  test_historial_incluye_copa: (el club no juega copa, se omite)"); return
    c = K.copa(e, tipo); user = K._nombre_user(e)
    p = next(x for x in c['partidos'] if user in (x['local'], x['visitante']))
    K.registrar_resultado_user(e, p['id'], 2, 1)
    h = L.partidos_historial(e)
    assert any(x['etiqueta'] in ('UCL', 'LIB') for x in h)
    print("  test_historial_incluye_copa: OK")

def test_balon_de_oro_cuenta_copa():
    from alpha_football import premios as P
    e = estado_carrera(); liga = e['liga']
    for eq in liga.equipos:
        for j in eq.jugadores:
            j.partidos_jugados = 0; j.goles = 0; j.asistencias = 0
    eq0 = liga.equipos[0]; estrella = eq0.jugadores[0]
    estrella.partidos_jugados = int(liga.num_jornadas * 0.3)            # solo con liga no llega al 50%
    estrella.goles = 30
    # relleno: alguien que sí califique para que haya podio
    otro = liga.equipos[1].jugadores[0]; otro.partidos_jugados = liga.num_jornadas; otro.goles = 1
    primeras = {liga.tipo if hasattr(liga, 'tipo') else 'premier': liga}
    copas = {'champions': {'stats': {f"{eq0.nombre}|{estrella.nombre_completo}": {
        'nombre': estrella.nombre_completo, 'club': eq0.nombre, 'pos': estrella.posicion,
        'goles': 8, 'asist': 0, 'pj': 10, 'vallas': 0}}}}
    sin = P.calcular_balon_de_oro(primeras, {}, 1, datos_copas=None)
    con = P.calcular_balon_de_oro(primeras, {}, 1, datos_copas=copas)
    nombres = lambda r: [f['nombre'] for f in (r or {}).get('podio', [])]
    assert estrella.nombre_completo not in nombres(sin)
    assert estrella.nombre_completo in nombres(con)
    print("  test_balon_de_oro_cuenta_copa: OK")
```
(Verificar la clave del nombre en la ficha de `calcular_balon_de_oro._ficha` — si no es `'nombre'`, ajustar la lambda — y la clave de liga que espera `primeras`: la misma que devuelve `_ligas_por_division`.)
- [ ] **Step 2-4:** Run → falla; implementar; en el render del historial usar `partidos_historial` (color verde/rojo/azul como hoy; etiqueta al inicio: `J5:` o `UCL:`). Run → OK + `tests/test_premios*.py`, `tests/test_competiciones_v380.py`, `tests/test_hub_v240.py`.

---

## Task 13: Cierre (yo, al final)
- [ ] `ui/ayuda.py`: páginas de partido en vivo (pausas, selector de lesión, teclas V/T/1-3), post-partido (pestañas), INICIO (sobre de correo, M/O), Opciones (GUARDAR). `ui/atajos.py` coherente con todo lo anterior.
- [ ] Suite completa en verde (comando en Global Constraints). Reportar la salida real.
- [ ] Prueba manual rápida con la skill `run` si está disponible: simular instantáneo, jugar un partido en vivo con una lesión, abrir correo con M.
- [ ] `context.md`: bitácora v4.0.0 → v4.3.0, fecha 2026-09-24.
