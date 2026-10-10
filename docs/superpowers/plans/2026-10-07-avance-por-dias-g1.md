# Avance por días (v0.4.12.0, sub-proyecto G1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sin commits:** Diego da el OK final (igual que en C). Nunca atribuir a Claude ni a una IA en git.

**Goal:** El juego avanza por días: un reloj ("hoy"), los botones CONTINUAR (corre los días hasta que pase algo) y +1 DÍA, y las ofertas, eventos y avisos de jugadores que dejan de caer al cerrar la jornada para llegar en días sueltos del hueco entre partidos.

**Architecture:** Módulo sin UI `alpha_football/dias.py`: reloj (`dia`) y agenda (`agenda`) viven dentro de `datos_carrera['calendario']` (el bloque de C, que ya se rearma solo al cambiar de temporada, liga o club). Al cerrar cada partido se sortea lo que antes caía en el acto y se guarda en la agenda con un día del hueco; cada día que pasa se recupera la energía del día y se entrega lo que vence. Los correos se difieren con un contexto (`diferir_correos`) que desvía `correo.enviar` a la agenda; las ofertas (que llevan objetos y no se guardan) se sortean al cerrar y se crean el día asignado con las mismas funciones de hoy.

**Tech Stack:** Python 3.10 (`datetime`, `contextlib`), pygame. Tests = scripts ejecutables (`python tests/test_x.py`) con ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-07-avance-por-dias-g1-design.md`. Depende de C (`alpha_football/calendario.py`, ya implementado y sin commit). G2 (mercado por fecha, absorbe D) tiene plan propio y va después; E y F no se tocan.

## Global Constraints

- Versión: **0.4.12.0**. Comentarios nuevos: `# v0.4.12.0`. No reescribir comentarios viejos. El título de la ventana y el badge del README siguen en 0.4.10.0 (el bump de 0.4.11.0 tampoco está hecho): no se tocan; Diego decide el bump al cerrar el paquete.
- **Git: sin commits, push, stash, reset ni checkout de archivos.** El plan y los specs están sin commitear: no los reviertas.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor del cambio. Comentarios y textos del juego en español.
- Cada test corre con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` y termina en `N/N tests pasaron`. Hay tests que salen con código 0 aunque impriman `FAIL`: revisar siempre la salida.
- La temporada arranca el **1 de agosto** (Europa) o el **1 de enero** (Sudamérica).
- Los partidos **siempre los juegas tú**: ni CONTINUAR ni +1 DÍA pasan por encima del día de tu próximo partido. Nada de la agenda cae el día de un partido tuyo.
- Mismas probabilidades que hoy: oferta de la IA `PROB_OFERTA_POR_JORNADA` (0.15; 0.45 con transferibles; solo con la ventana de mercado abierta), oferta del exterior 0.25, evento de vestuario `PROB_BASE` 0.12 / `PROB_MAL` 0.45. Una tirada por hueco.
- Lo ligado al partido (resultado, lesiones, sanciones, vestuario del partido, finanzas, confianza) y *Club y directiva* (ofertas de DT, patrocinios, cantera, pedidos de la directiva, sueldo del DT) siguen al cerrar el partido. El mercado de la IA y las ventanas por fecha son de G2.
- Un save sin reloj ni agenda carga y funciona. **Solo el hub (o la pantalla CALENDARIO) crea el reloj**: sin reloj todo se comporta como en C (los tests viejos que no abren el hub no cambian).

### Desviaciones del spec decididas al planificar

1. **Los datos van en `datos_carrera['calendario']['dia']` y `['agenda']`**, no sueltos en `datos_carrera`: ese bloque ya se rearma al cambiar de temporada, liga o club. Consecuencia: cambiar de club a mitad de temporada **no conserva el reloj**; el del club nuevo nace en su próximo partido.
2. **`calendario.hoy` NO delega en `dias.hoy`**: C queda intacto (y sus tests). `calendario_screen` y el hub usan `dias.hoy`.
3. **Sin sorteos en el hueco previo a la J1**: hoy tampoco caen ofertas ni eventos antes de la J1.
4. **La escalada de "pide salir"** (`salidas.subir_escalon`: correos de la directiva y de "quiero irme") **se queda al cerrar** (su efecto sobre la confianza es inmediato). Pasan a días sueltos: el descontento, el "quiere renovar", las ofertas garantizadas, la oferta local, la del exterior y el evento de vestuario.
5. **Sin días libres en el hueco** (fin de la liga): lo agendado se entrega en el acto, para que nunca quede atrapado.

## Review Focus

1. **Última jornada de la liga** (no hay próximo partido): lo agendado llega en el acto y no queda atrapado en la agenda (Task 2).
2. **Save viejo sin reloj/agenda, agenda dañada o con tipos desconocidos, fecha inválida**: carga, juega y no rompe el avance (Tasks 1 y 2).
3. **Hueco corto (3 días → 2 libres) y copa en medio**: nada cae en día de partido, ni de liga ni de copa (Task 2).
4. **Oferta agendada cuando el mercado ya cerró, el jugador ya no está o fue traspasado**: no se crea y no rompe (Task 3).
5. **Partido reprogramado por C**: el reloj nunca retrocede y CONTINUAR nunca salta un partido (Task 1).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/dias.py` (nuevo) | Reloj, `avanzar_dia`, `continuar`, agenda (`programar`, `asignar_dias`, `entregar`, `diferir_correos`), sorteo y entrega de ofertas, textos del hub |
| `alpha_football/correo.py` | `enviar` desvía a la agenda dentro de `diferir_correos`; `entregar` pasa un mensaje a la bandeja |
| `alpha_football/market.py` | `prob_oferta_ia` (la probabilidad que ya usa `crear_oferta_ui`) |
| `alpha_football/salidas.py` | `cierre_jornada`: descontento y renovar diferidos; garantizadas agendadas |
| `alpha_football/eventos.py` | `cierre_jornada`: el sorteo del evento diferido |
| `alpha_football/ui/match_screen.py` | `finalizar_jornada_liga`: con reloj no recupera energía; ofertas agendadas; asignar días al final |
| `alpha_football/ui/league_screen.py` | Botones CONTINUAR / +1 DÍA, textos, tecla `D`, el hub crea el reloj |
| `alpha_football/ui/calendario_screen.py`, `atajos.py`, `ayuda.py` | Hoy = reloj; atajo y ayuda |
| `tests/test_dias.py` (nuevo) | tests de G1 |

Cabecera del archivo de test nuevo (copiar tal cual):

```python
"""v0.4.12.0: avance por días (reloj, agenda, CONTINUAR / +1 DÍA)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, energia as E, dias as D
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

### Task 1: El reloj, AVANZAR DÍA y CONTINUAR

**Files:**
- Create: `alpha_football/dias.py`
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga`, bloque del descanso)
- Test: `tests/test_dias.py` (nuevo)

**Interfaces:**
- Consumes: `calendario.asegurar/anio/continente/eventos_user/proximo_evento/fecha_liga/texto_fecha/dias_por_jornada`, `energia.recuperar_todos(estado, dias)`.
- Produces: `dias.inicio_temporada(estado) -> date`, `activo(estado) -> bool`, `hoy(estado) -> date`, `es_dia_de_continuar(estado) -> bool`, `avanzar_dia(estado) -> dict`, `continuar(estado, parar=True) -> dict`, `hasta_el_partido(estado) -> dict`, `texto_resumen(r) -> str`, `textos_hub(estado) -> Optional[tuple]`. El resumen es `{'dias', 'correos', 'ofertas', 'eventos'}`. Datos: `datos_carrera['calendario']['dia']` = `'AAAA-MM-DD'`.

- [ ] **Step 1: Crear el test** con la cabecera, el pie y estos casos:

```python
def test_el_reloj_nace_al_inicio_de_la_temporada():
    e = _e()
    assert not D.activo(e)                                                 # sin hub, sin reloj
    assert D.hoy(e) == date(2026, 8, 1) and D.activo(e)                    # Europa: 1 de agosto
    assert D.hoy(e) == date(2026, 8, 1)                                    # estable
    sa = _e('betplay')
    assert D.hoy(sa) == date(2027, 1, 1)                                   # Sudamérica: 1 de enero
    assert D.hoy({}) == date(2026, 8, 1) and not D.activo({})              # sin partida: no escribe nada


def test_el_reloj_de_un_save_a_mitad_de_temporada_nace_en_su_proximo_partido():
    e = _e(); _jugar(e, 1); _jugar(e, 2)
    assert D.hoy(e) == CAL.fecha_liga(e, 3)


def test_avanzar_dia_mueve_un_dia_y_no_pasa_del_partido():
    e = _e(); D.hoy(e)
    primero = CAL.fecha_liga(e, 1)
    n = (primero - date(2026, 8, 1)).days
    assert n > 1 and D.es_dia_de_continuar(e)
    r = D.avanzar_dia(e)
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 8, 2)
    for _ in range(n - 1):
        D.avanzar_dia(e)
    assert D.hoy(e) == primero and not D.es_dia_de_continuar(e)            # día de partido: JUGAR
    assert D.avanzar_dia(e)['dias'] == 0 and D.hoy(e) == primero           # no pasa por encima del partido


def test_continuar_llega_al_dia_del_partido():
    e = _e(); D.hoy(e)
    r = D.continuar(e)
    assert D.hoy(e) == CAL.fecha_liga(e, 1)
    assert r['dias'] == (CAL.fecha_liga(e, 1) - date(2026, 8, 1)).days
    assert D.continuar(e)['dias'] == 0                                     # ya es día de partido
    _jugar(e, 1)
    assert D.hasta_el_partido(e)['dias'] > 0 and D.hoy(e) == CAL.fecha_liga(e, 2)


def test_sin_partidos_pendientes_el_reloj_no_corre():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    assert not D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 0
    assert D.continuar({})['dias'] == 0 and not D.es_dia_de_continuar({})   # sin partida


def test_si_el_partido_se_mueve_antes_del_reloj_se_juega_ese_dia():
    e = _e(); D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1)
    hoy = D.hoy(e)
    CAL.asegurar(e)['mov']['liga:2'] = (hoy - timedelta(days=1)).isoformat()   # C lo reprogramó "al pasado"
    assert D.hoy(e) == hoy and not D.es_dia_de_continuar(e)                # el reloj no retrocede
    assert D.avanzar_dia(e)['dias'] == 0


def test_la_energia_se_recupera_cada_dia_como_en_el_reparto_de_c():
    e = _e(); D.hoy(e); j = e['mi_equipo'].jugadores[0]
    total = (CAL.fecha_liga(e, 1) - D.hoy(e)).days
    j.energia = 10
    D.continuar(e)
    esperado = min(100.0, 10 + E.recuperacion(j) * total / CAL.dias_por_jornada(e))
    assert abs(j.energia - esperado) < 1e-6


def test_con_reloj_cerrar_el_partido_no_recupera_energia_y_los_dias_si():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    D.hoy(e); D.hasta_el_partido(e)
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    for j in mi.jugadores:
        j.energia = 10.0
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    assert all(j.energia == 10.0 for j in mi.jugadores)                    # cerrar no recupera: lo hacen los días
    D.hasta_el_partido(e)
    factor = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days / CAL.dias_por_jornada(e)
    bien = [j for j in mi.jugadores if abs(j.energia - min(100.0, 10 + E.recuperacion(j) * factor)) < 1e-6]
    assert len(bien) >= len(mi.jugadores) - 2, (len(bien), len(mi.jugadores))


def test_textos_del_hub_y_resumen():
    e = _e()
    assert D.textos_hub(e) is None                                         # sin reloj: como siempre
    D.hoy(e)
    l1, l2, l3 = D.textos_hub(e)
    assert l1 == "CONTINUAR" and l2.startswith("Próximo: J1") and "(en " in l2 and l2.endswith(")") and len(l2) <= 56 and l3 == ""
    D.hasta_el_partido(e)
    assert D.textos_hub(e) is None                                         # día de partido: JUGAR
    assert D.texto_resumen({'dias': 3, 'ofertas': 1, 'correos': 2, 'eventos': 0}) == "Pasaron 3 días: 1 oferta, 2 correos"
    assert D.texto_resumen({'dias': 1, 'ofertas': 0, 'correos': 0, 'eventos': 1}) == "Pasó 1 día: 1 evento"
    assert D.texto_resumen({'dias': 2, 'ofertas': 0, 'correos': 0, 'eventos': 0}) == "Pasaron 2 días"
    assert D.texto_resumen({'dias': 0}) == "Hoy es día de partido"
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: falla al importar (`cannot import name 'dias'`).

- [ ] **Step 3: Crear `alpha_football/dias.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Avance por días (v0.4.12.0)
El juego avanza día a día entre tus partidos: un reloj ("hoy") que nunca pasa del día de tu próximo
partido, la energía que se recupera cada día y una agenda con lo que llega en días sueltos.
- Datos: dentro de datos_carrera['calendario'] (el bloque de calendario.asegurar, que se rearma solo
  al cambiar de temporada, liga o club): 'dia' = 'AAAA-MM-DD' y 'agenda' = [{'fecha', 'tipo', 'datos'}].
- Solo el hub (o la pantalla CALENDARIO) crea el reloj: sin reloj todo funciona como antes (activo()).
Sin UI.
"""
from __future__ import annotations

import logging
import random
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

INICIO_TEMPORADA = {'europa': (8, 1), 'sudamerica': (1, 1)}   # (mes, día) en que arranca la temporada
MAX_DIAS = 400                                                # tope de seguridad de continuar()
PROB_OFERTA_EXTERIOR = 0.25                                   # la de market.crear_oferta_exterior


def _cal(estado: dict) -> dict:
    return CAL.asegurar(estado)


def _a_fecha(txt) -> Optional[date]:
    try:
        return date.fromisoformat(txt) if txt else None
    except Exception:
        return None


def inicio_temporada(estado: dict) -> date:
    m, d = INICIO_TEMPORADA.get(CAL.continente(estado), (8, 1))
    return date(CAL.anio(estado), m, d)


def activo(estado: dict) -> bool:
    """¿La partida ya tiene reloj? Lo crea hoy() (el hub, al abrirse)."""
    try:
        return (estado.get('liga') is not None and estado.get('mi_equipo') is not None
                and _a_fecha(_cal(estado).get('dia')) is not None)
    except Exception:
        return False


def hoy(estado: dict) -> date:
    """El día en que estás. Si la partida no tiene reloj lo crea: al inicio de la temporada si no
    has jugado nada; si no, el día de tu próximo partido (save a mitad de temporada)."""
    if estado.get('liga') is None or estado.get('mi_equipo') is None:
        return inicio_temporada(estado)
    cal = _cal(estado)
    d = _a_fecha(cal.get('dia'))
    if d is None:
        evs = CAL.eventos_user(estado)
        prox = next((e for e in evs if not e['jugado']), None)
        if evs and not any(e['jugado'] for e in evs):
            d = min(inicio_temporada(estado), evs[0]['fecha'])
        elif prox is not None:
            d = prox['fecha']
        else:
            d = evs[-1]['fecha'] if evs else inicio_temporada(estado)
        cal['dia'] = d.isoformat()
    return d


def es_dia_de_continuar(estado: dict) -> bool:
    """True si la partida tiene reloj, hoy NO hay partido tuyo y falta alguno: JUGAR pasa a CONTINUAR."""
    try:
        if not activo(estado):
            return False
        prox = CAL.proximo_evento(estado)
        return prox is not None and hoy(estado) < prox['fecha']
    except Exception as e:
        logger.error(f"dias: no se pudo saber si hoy hay partido: {e}")
        return False


def avanzar_dia(estado: dict) -> dict:
    """Pasa un día: mueve el reloj y recupera la energía del día. Nunca pasa del día de tu próximo
    partido (si hoy hay partido no hace nada). Devuelve {'dias', 'correos', 'ofertas', 'eventos'}."""
    res = {'dias': 0, 'correos': 0, 'ofertas': 0, 'eventos': 0}
    try:
        if not es_dia_de_continuar(estado):
            return res
        nueva = hoy(estado) + timedelta(days=1)
        _cal(estado)['dia'] = nueva.isoformat()
        res['dias'] = 1
        try:
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado, 1.0)
        except Exception as e_en:
            logger.error(f"dias: no se pudo recuperar la energía del día: {e_en}")
    except Exception as e:
        logger.error(f"dias: error al avanzar un día: {e}", exc_info=True)
    return res


def continuar(estado: dict, parar: bool = True) -> dict:
    """Corre los días hasta el día de tu próximo partido; con `parar`, se detiene antes si ese día
    llegó algo (correo, oferta, evento). Siempre avanza al menos un día si hoy no hay partido."""
    total = {'dias': 0, 'correos': 0, 'ofertas': 0, 'eventos': 0}
    for _ in range(MAX_DIAS):
        r = avanzar_dia(estado)
        if r['dias'] == 0:
            break
        for k in total:
            total[k] += r[k]
        if parar and (r['correos'] or r['ofertas'] or r['eventos']):
            break
    return total


def hasta_el_partido(estado: dict) -> dict:
    """Corre los días sin detenerse hasta el día de tu próximo partido (tests y migraciones)."""
    return continuar(estado, parar=False)


def texto_resumen(r: dict) -> str:
    """'Pasaron 3 días: 1 oferta, 2 correos'."""
    d = int(r.get('dias', 0) or 0)
    if d <= 0:
        return "Hoy es día de partido"
    partes = []
    for clave, uno, varios in (('ofertas', 'oferta', 'ofertas'), ('eventos', 'evento', 'eventos'),
                               ('correos', 'correo', 'correos')):
        n = int(r.get(clave, 0) or 0)
        if n:
            partes.append(f"{n} {uno if n == 1 else varios}")
    cab = "Pasó 1 día" if d == 1 else f"Pasaron {d} días"
    return f"{cab}: {', '.join(partes)}" if partes else cab


def textos_hub(estado: dict) -> Optional[tuple]:
    """(línea 1, línea 2, línea 3) del botón grande del hub cuando hoy no hay partido; None si hay
    partido hoy, no quedan partidos o la partida no tiene reloj."""
    if not es_dia_de_continuar(estado):
        return None
    prox = CAL.proximo_evento(estado)
    n = (prox['fecha'] - hoy(estado)).days
    donde = "vs" if prox['local'] else "en"
    l2 = (f"Próximo: {prox['etiqueta']} {donde} {str(prox['rival'])[:12]} · "
          f"{CAL.texto_fecha(prox['fecha'], False)} (en {n} día{'s' if n != 1 else ''})")
    return "CONTINUAR", l2[:56], ""
```

- [ ] **Step 4: Correr** — `PYTHONIOENCODING=utf-8 python tests/test_dias.py`. Expected: el único que falla es `test_con_reloj_cerrar_el_partido_no_recupera_energia_y_los_dias_si` (todavía `finalizar_jornada_liga` recupera al cerrar): `8/9 tests pasaron`.

- [ ] **Step 5: Con reloj, cerrar el partido no recupera energía** — en `alpha_football/ui/match_screen.py`, dentro de `finalizar_jornada_liga`, en el bloque `# v0.4.11.0: descanso según el calendario` reemplazar:

```python
            from alpha_football import calendario as _cal_d
            from alpha_football.energia import recuperar_todos as _recuperar_dias
            _cal_d.aplicar_descanso_pendiente(estado)      # por si quedó de una fecha de copa sin cerrar
            descanso = _cal_d.descanso_tras_liga(estado, int(getattr(partido, 'jornada', 0) or 1))
            _recuperar_dias(estado, descanso[0])
```

por:

```python
            from alpha_football import calendario as _cal_d
            from alpha_football import dias as _dias_d
            from alpha_football.energia import recuperar_todos as _recuperar_dias
            if _dias_d.activo(estado):
                descanso = (0.0, 0.0)          # v0.4.12.0: con reloj, la energía se recupera cada día que pasa
            else:
                _cal_d.aplicar_descanso_pendiente(estado)      # por si quedó de una fecha de copa sin cerrar
                descanso = _cal_d.descanso_tras_liga(estado, int(getattr(partido, 'jornada', 0) or 1))
                _recuperar_dias(estado, descanso[0])
```

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `9/9 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `24/24 tests pasaron` (sin hub no hay reloj: C no cambia).

---

### Task 2: La agenda y los correos diferidos

**Files:**
- Modify: `alpha_football/dias.py` (agregar la agenda y cambiar `avanzar_dia`)
- Modify: `alpha_football/correo.py` (`enviar` y `entregar`)
- Test: `tests/test_dias.py`

**Interfaces:**
- Consumes: `dias.hoy/activo/es_dia_de_continuar/_cal/_a_fecha` (Task 1), `calendario.eventos_user`, `correo.bandeja/MAX_CORREOS`.
- Produces: `dias.agenda(estado) -> list`, `programar(estado, tipo, datos=None) -> dict`, `dias_libres(estado) -> list[date]`, `asignar_dias(estado) -> int`, `entregar(estado, hasta: date) -> dict`, `diferir_correos(estado)` (contexto), `correo.entregar(estado, msg) -> dict`. Cada entrada de la agenda: `{'fecha': 'AAAA-MM-DD' | None, 'tipo': 'correo' | 'oferta' | 'oferta_ext' | 'garantizadas', 'datos': dict}`. Dentro de `diferir_correos`, `correo.enviar` devuelve el mensaje (con `id` 0) y lo guarda en la agenda en vez de la bandeja.

- [ ] **Step 1: Tests** — agregar a `tests/test_dias.py`:

```python
def _en_j1(e):
    """Reloj en el día de la J1, ya jugada: el hueco hasta la J2 está por delante."""
    D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1)


def test_la_agenda_asigna_dias_del_hueco_y_es_estable():
    e = _e(); _en_j1(e)
    d1, d2 = CAL.fecha_liga(e, 1), CAL.fecha_liga(e, 2)
    for _ in range(5):
        D.programar(e, 'oferta')
    assert D.asignar_dias(e) == 5 and D.asignar_dias(e) == 0              # la segunda vez no hay nada sin día
    fechas = [date.fromisoformat(it['fecha']) for it in D.agenda(e)]
    assert all(d1 < f < d2 for f in fechas), (fechas, d1, d2)
    f = _e(); _en_j1(f)                                                    # misma partida, mismo sorteo
    for _ in range(5):
        D.programar(f, 'oferta')
    D.asignar_dias(f)
    assert [it['fecha'] for it in D.agenda(f)] == [it['fecha'] for it in D.agenda(e)]


def test_nada_cae_el_dia_de_un_partido_aunque_haya_copa_en_el_hueco():
    e = _e(); _con_copa(e, fecha=0)
    D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1); D.hasta_el_partido(e); _jugar(e, 2)
    d2, copa, d3 = CAL.fecha_liga(e, 2), CAL.fecha_copa(e, 'champions', 0), CAL.fecha_liga(e, 3)
    for _ in range(40):
        D.programar(e, 'oferta')
    D.asignar_dias(e)
    fechas = {date.fromisoformat(it['fecha']) for it in D.agenda(e)}
    assert d2 < copa < d3 and len(fechas) > 3
    assert copa not in fechas and d2 not in fechas and d3 not in fechas
    assert all(d2 < f < d3 for f in fechas)


def test_hueco_corto_de_tres_dias_deja_dos_dias_libres():
    e = _e(); _en_j1(e)
    d1 = CAL.fecha_liga(e, 1)
    CAL.asegurar(e)['mov']['liga:2'] = (d1 + timedelta(days=3)).isoformat()
    assert D.dias_libres(e) == [d1 + timedelta(days=1), d1 + timedelta(days=2)]
    D.programar(e, 'oferta'); D.asignar_dias(e)
    assert date.fromisoformat(D.agenda(e)[0]['fecha']) in D.dias_libres(e)


def test_los_correos_diferidos_van_a_la_agenda_y_llegan_el_dia_sorteado():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        msg = C.enviar(e, 'club', "Hola", "Cuerpo")
        msg['evento'] = {'id': 'x', 'resuelto': None}                      # lo que hace eventos.sortear
    assert C.bandeja(e) == [] and msg['id'] == 0 and D.agenda(e)[0]['tipo'] == 'correo'
    json.dumps(e['datos_carrera'])                                         # se puede guardar la partida
    D.asignar_dias(e)
    fecha = date.fromisoformat(D.agenda(e)[0]['fecha'])
    r = D.continuar(e)
    assert D.hoy(e) == fecha and r['eventos'] == 1 and r['correos'] == 0   # lleva 'evento': cuenta como evento
    assert [m['asunto'] for m in C.bandeja(e)] == ["Hola"] and C.bandeja(e)[0]['id'] == 1
    assert C.bandeja(e)[0]['evento'] == {'id': 'x', 'resuelto': None} and D.agenda(e) == []
    f = _e()                                                               # sin reloj: se envía en el acto
    with D.diferir_correos(f):
        C.enviar(f, 'club', "Ya", "x")
    assert [m['asunto'] for m in C.bandeja(f)] == ["Ya"]


def test_agenda_danada_o_con_tipos_desconocidos_no_rompe_el_avance():
    e = _e(); _en_j1(e)
    e['datos_carrera']['calendario']['agenda'] = "rota"
    assert D.agenda(e) == []
    D.agenda(e).extend([{'fecha': 'no-es-fecha', 'tipo': 'correo', 'datos': {}}, 'basura',
                        {'fecha': None, 'tipo': 'marciano', 'datos': {}}])
    r = D.hasta_el_partido(e)
    assert r['dias'] > 0 and D.hoy(e) == CAL.fecha_liga(e, 2)
    assert D.agenda(e) == [] and C.bandeja(e) == []                        # lo dañado se descarta sin ensuciar el correo


def test_al_final_de_la_liga_lo_agendado_llega_en_el_acto():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Fin", "x")
    D.asignar_dias(e)                                                      # no hay más partidos: sin días libres
    assert [m['asunto'] for m in C.bandeja(e)] == ["Fin"] and D.agenda(e) == []


def test_reloj_y_agenda_sobreviven_a_guardar_y_cargar():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Guardado", "x")
    D.asignar_dias(e)
    f = _e(); f['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))
    assert D.activo(f) and D.hoy(f) == D.hoy(e)
    assert D.agenda(f) == D.agenda(e) and len(D.agenda(f)) == 1
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'programar'` / `'diferir_correos'`).

- [ ] **Step 3: `correo.py`** — en `alpha_football/correo.py`, en `enviar`, reemplazar:

```python
    if firma:
        msg['firma'] = str(firma)
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg
```

por:

```python
    if firma:
        msg['firma'] = str(firma)
    cola = estado.get('_diferir_correos')        # v0.4.12.0: dentro de dias.diferir_correos va a la agenda
    if cola is not None:
        msg['id'] = 0                            # el id se asigna al entregarlo (correo.entregar)
        cola.append({'fecha': None, 'tipo': 'correo', 'datos': msg})
        return msg
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg


def entregar(estado: dict, msg: dict) -> dict:
    """v0.4.12.0: pasa a la bandeja un mensaje que esperaba en la agenda (dias.py)."""
    lista = bandeja(estado)
    msg['id'] = max((int(m.get('id', 0)) for m in lista), default=0) + 1
    lista.insert(0, msg)
    del lista[MAX_CORREOS:]
    return msg
```

- [ ] **Step 4: `dias.py`** — agregar al final:

```python


# --- Agenda ───────────────────────────────────────────────────────────────────

def agenda(estado: dict) -> list:
    """La agenda de la temporada (lista de {'fecha', 'tipo', 'datos'}); una agenda dañada se reinicia."""
    cal = _cal(estado)
    if not isinstance(cal.get('agenda'), list):
        cal['agenda'] = []
    return cal['agenda']


def programar(estado: dict, tipo: str, datos: Optional[dict] = None) -> dict:
    """Agrega algo a la agenda sin día; asignar_dias le pone uno al cerrar el partido."""
    item = {'fecha': None, 'tipo': tipo, 'datos': datos or {}}
    agenda(estado).append(item)
    return item


def dias_libres(estado: dict) -> list:
    """Días entre hoy y tu próxima jornada de liga, sin los días en que juegas (liga o copa)."""
    evs = CAL.eventos_user(estado)
    prox_liga = next((e for e in evs if not e['jugado'] and e['tipo'] == 'liga'), None)
    if prox_liga is None:
        return []
    ocupados = {e['fecha'] for e in evs}
    out, d = [], hoy(estado) + timedelta(days=1)
    while d < prox_liga['fecha']:
        if d not in ocupados:
            out.append(d)
        d += timedelta(days=1)
    return out


def asignar_dias(estado: dict) -> int:
    """Pone día (determinista) a lo que la agenda tiene sin fecha válida. Sin días libres (fin de la
    liga) lo entrega en el acto. Devuelve cuántas entradas asignó."""
    ag = agenda(estado)
    sin = [it for it in ag if isinstance(it, dict) and _a_fecha(it.get('fecha')) is None]
    if not sin:
        return 0
    libres = dias_libres(estado)
    h = hoy(estado)
    club = str(getattr(estado.get('mi_equipo'), 'id', ''))
    jornada = int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1)
    for k, it in enumerate(sin):
        if libres:
            azar = random.Random(f"agenda-{CAL.anio(estado)}-{club}-{jornada}-{k}")
            it['fecha'] = azar.choice(libres).isoformat()
        else:
            it['fecha'] = h.isoformat()
    if not libres:
        entregar(estado, h)
    return len(sin)


def _entregar_oferta(estado: dict, exterior: bool) -> int:
    """Crea la oferta de la IA que se sorteó al cerrar el partido (con las mismas funciones de siempre)."""
    from alpha_football import market
    from alpha_football.ui.match_screen import _correo_oferta
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return 0
    if exterior:
        of = market.crear_oferta_exterior(mi, estado, prob=1.0)
    else:
        rivales = [e for e in liga.equipos if e.id != mi.id]
        of = market.crear_oferta_ui(mi, rivales, liga.jornada_actual, liga.num_jornadas, prob=1.0)
    if of and market.traspasado_en_ventana(estado, of.get('jugador')):
        of = None                                # recién llegado: no se lo puede traspasar en esta ventana
    if not of:
        return 0
    estado.setdefault('ofertas_recibidas', []).append(of)
    _correo_oferta(estado, of, "Oferta del exterior por" if exterior else "Oferta por")
    return 1


def _entregar_item(estado: dict, it: dict) -> tuple:
    """Entrega una entrada de la agenda. Devuelve (clave del resumen, cuántos) o ('', 0)."""
    tipo = it.get('tipo')
    if tipo == 'correo':
        msg = it.get('datos') or {}
        if not msg.get('asunto'):
            return '', 0                         # mensaje dañado: se descarta
        from alpha_football import correo as C
        C.entregar(estado, msg)
        return ('eventos' if msg.get('evento') else 'correos'), 1
    if tipo in ('oferta', 'oferta_ext'):
        return 'ofertas', _entregar_oferta(estado, tipo == 'oferta_ext')
    if tipo == 'garantizadas':
        from alpha_football import salidas
        return 'ofertas', len(salidas.ofertas_garantizadas(estado))
    logger.warning(f"dias: tipo de agenda desconocido '{tipo}': se descarta")
    return '', 0


def entregar(estado: dict, hasta: date) -> dict:
    """Entrega lo que vence hasta `hasta` (incluido). Una entrega que falla se registra y se descarta:
    nunca bloquea el avance del reloj. Devuelve {'correos', 'ofertas', 'eventos'}."""
    res = {'correos': 0, 'ofertas': 0, 'eventos': 0}
    ag = agenda(estado)
    vencen = []
    for it in list(ag):
        if not isinstance(it, dict):
            ag[:] = [x for x in ag if x is not it]       # basura: se descarta
            continue
        f = _a_fecha(it.get('fecha'))
        if f is not None and f <= hasta:
            vencen.append((f, it))
    vencen.sort(key=lambda x: x[0])
    ag[:] = [x for x in ag if all(x is not it for _f, it in vencen)]
    for _f, it in vencen:
        try:
            clave, n = _entregar_item(estado, it)
            if clave:
                res[clave] += n
        except Exception as e:
            logger.error(f"dias: no se pudo entregar '{it.get('tipo')}': {e}", exc_info=True)
    return res


@contextmanager
def diferir_correos(estado: dict):
    """Mientras dura, correo.enviar guarda el mensaje en la agenda (sin día) en vez de en la bandeja.
    Sin reloj no hace nada: los correos se envían en el acto como siempre."""
    if not activo(estado):
        yield
        return
    previo = estado.get('_diferir_correos')
    estado['_diferir_correos'] = agenda(estado)
    try:
        yield
    finally:
        if previo is None:
            estado.pop('_diferir_correos', None)
        else:
            estado['_diferir_correos'] = previo
```

y en `avanzar_dia` (Task 1) reemplazar:

```python
        nueva = hoy(estado) + timedelta(days=1)
        _cal(estado)['dia'] = nueva.isoformat()
        res['dias'] = 1
        try:
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado, 1.0)
        except Exception as e_en:
            logger.error(f"dias: no se pudo recuperar la energía del día: {e_en}")
```

por:

```python
        asignar_dias(estado)                       # por si quedó algo sin día
        nueva = hoy(estado) + timedelta(days=1)
        _cal(estado)['dia'] = nueva.isoformat()
        res['dias'] = 1
        try:
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado, 1.0)
        except Exception as e_en:
            logger.error(f"dias: no se pudo recuperar la energía del día: {e_en}")
        for clave, n in entregar(estado, nueva).items():
            res[clave] += n
```

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `16/16 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_notificaciones.py`
Expected: `N/N tests pasaron` (el cambio en `correo.enviar` no altera nada sin `_diferir_correos`).

---

### Task 3: Ofertas de la IA en días sueltos

**Files:**
- Modify: `alpha_football/market.py` (`prob_oferta_ia`, junto a `crear_oferta_ui`)
- Modify: `alpha_football/dias.py` (`programar_ofertas`)
- Modify: `alpha_football/ui/match_screen.py` (`finalizar_jornada_liga`: ofertas y asignar días)
- Test: `tests/test_dias.py`

**Interfaces:**
- Consumes: `dias.programar/asignar_dias/_entregar_oferta` (Task 2), `market.ventana_mercado_abierta/crear_oferta_ui/crear_oferta_exterior/traspasado_en_ventana`.
- Produces: `market.prob_oferta_ia(mi_equipo, prob=None) -> float`, `dias.programar_ofertas(estado, rng=None) -> list[dict]` (las entradas de agenda creadas: tipos `'oferta'` y/o `'oferta_ext'`).

- [ ] **Step 1: Tests** — agregar:

```python
def test_la_probabilidad_de_oferta_es_la_de_hoy():
    from alpha_football import market
    e = _e(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.transferible = j.pide_salir = False
    assert market.prob_oferta_ia(mi) == market.PROB_OFERTA_POR_JORNADA
    mi.jugadores[3].transferible = True
    assert market.prob_oferta_ia(mi) == market.PROB_OFERTA_CON_TRANSFERIBLES


def test_el_sorteo_de_ofertas_conserva_las_frecuencias_y_respeta_la_ventana():
    e = _e(); liga = e['liga']
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    D.hoy(e); rng = random.Random(7); N = 3000
    liga.jornada_actual = 2                                                # ventana de inicio abierta
    n_loc = n_ext = 0
    for _ in range(N):
        D.agenda(e).clear()
        for it in D.programar_ofertas(e, rng):
            n_loc += it['tipo'] == 'oferta'; n_ext += it['tipo'] == 'oferta_ext'
    assert abs(n_loc / N - 0.15) < 0.03 and abs(n_ext / N - 0.25) < 0.03, (n_loc / N, n_ext / N)
    liga.jornada_actual = 5                                                # ventana cerrada: solo el exterior
    assert all(it['tipo'] == 'oferta_ext' for _ in range(300) for it in D.programar_ofertas(e, rng))


def test_la_oferta_local_se_crea_el_dia_sorteado_y_no_antes():
    e = _e(); _en_j1(e); e['liga'].jornada_actual = 2
    it = D.programar(e, 'oferta'); D.asignar_dias(e)
    fecha = date.fromisoformat(it['fecha'])
    assert not e.get('ofertas_recibidas')
    r = D.continuar(e)
    assert D.hoy(e) == fecha and r['ofertas'] == 1 and len(e['ofertas_recibidas']) == 1
    assert any(m['asunto'].startswith("Oferta por") for m in C.bandeja(e))


def test_oferta_agendada_con_el_mercado_cerrado_no_se_crea_ni_rompe_el_avance():
    e = _e(); _en_j1(e)
    e['liga'].jornada_actual = 5                                           # ventana cerrada ese día
    D.programar(e, 'oferta')
    r = D.hasta_el_partido(e)
    assert r['ofertas'] == 0 and not e.get('ofertas_recibidas') and D.agenda(e) == []
    assert D.hoy(e) == CAL.fecha_liga(e, 2)                                # y el avance siguió sin romperse


def test_la_oferta_del_exterior_se_consume_sin_romper():
    e = _e(); _en_j1(e)
    D.programar(e, 'oferta_ext')
    r = D.hasta_el_partido(e)
    assert r['ofertas'] in (0, 1) and D.agenda(e) == [] and D.hoy(e) == CAL.fecha_liga(e, 2)


def test_cerrar_el_partido_con_reloj_agenda_las_ofertas_con_dia_y_no_las_crea_en_el_acto():
    from alpha_football import market
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    D.hoy(e); D.hasta_el_partido(e)
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    viejo_loc, viejo_ext = market.PROB_OFERTA_POR_JORNADA, D.PROB_OFERTA_EXTERIOR
    market.PROB_OFERTA_POR_JORNADA = D.PROB_OFERTA_EXTERIOR = 1.0
    try:
        finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    finally:
        market.PROB_OFERTA_POR_JORNADA, D.PROB_OFERTA_EXTERIOR = viejo_loc, viejo_ext
    assert not e.get('ofertas_recibidas')                                  # nada en el acto
    tipos = {it['tipo'] for it in D.agenda(e)}
    assert {'oferta', 'oferta_ext'} <= tipos
    assert all(date.fromisoformat(it['fecha']) < CAL.fecha_liga(e, 2) for it in D.agenda(e))
    D.hasta_el_partido(e)
    assert e.get('ofertas_recibidas') and D.agenda(e) == []                # llegaron en los días del hueco
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'prob_oferta_ia'`).

- [ ] **Step 3: `market.py`** — en `alpha_football/market.py`, justo antes de `def crear_oferta_ui`, agregar:

```python
def prob_oferta_ia(mi_equipo: Any, prob: Optional[float] = None) -> float:
    """v0.4.12.0: probabilidad de que la IA oferte esta jornada, la misma que usa crear_oferta_ui
    (más alta si tienes transferibles o jugadores que piden salir)."""
    base = PROB_OFERTA_POR_JORNADA if prob is None else prob
    propios = [j for j in getattr(mi_equipo, "jugadores", []) or [] if not getattr(j, "prestamo", None)]
    hay = any(getattr(j, "transferible", False) or getattr(j, "pide_salir", False) for j in propios)
    return max(base, PROB_OFERTA_CON_TRANSFERIBLES) if hay else base


```

(Si `Optional` no está importado en `market.py`, ya lo está: lo usan `crear_oferta_ui` y `crear_oferta_exterior`.)

- [ ] **Step 4: `dias.py`** — agregar al final:

```python


# --- Ofertas de la IA ─────────────────────────────────────────────────────────

def programar_ofertas(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Sorteo de las ofertas de la IA al cerrar el partido, con las probabilidades de siempre: la oferta
    se crea después, el día que asigna asignar_dias. Devuelve las entradas de agenda creadas."""
    from alpha_football import market
    azar = rng or random.Random()
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    nuevos: list = []
    if liga is None or mi is None:
        return nuevos
    if (market.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas)
            and azar.random() <= market.prob_oferta_ia(mi)):
        nuevos.append(programar(estado, 'oferta'))
    if azar.random() <= PROB_OFERTA_EXTERIOR:
        nuevos.append(programar(estado, 'oferta_ext'))
    return nuevos
```

- [ ] **Step 5: Enganches en `finalizar_jornada_liga`** (`alpha_football/ui/match_screen.py`), tres cambios.

(a) En el bloque `# Ofertas tras la jornada`, reemplazar:

```python
            if mi_equipo:
                rivales = [e for e in liga.equipos if e.id != mi_equipo.id]
                oferta_ia = market.crear_oferta_ui(mi_equipo, rivales, liga.jornada_actual, liga.num_jornadas)
```

por:

```python
            if mi_equipo:
                from alpha_football import dias as _dias_of      # v0.4.12.0: con reloj, la oferta se sortea ahora y llega otro día
                _en_dias = _dias_of.activo(estado)
                if _en_dias:
                    _dias_of.programar_ofertas(estado)
                rivales = [e for e in liga.equipos if e.id != mi_equipo.id]
                oferta_ia = None if _en_dias else market.crear_oferta_ui(mi_equipo, rivales, liga.jornada_actual, liga.num_jornadas)
```

(b) En ese mismo bloque, reemplazar:

```python
                _crear_ext = getattr(market, 'crear_oferta_exterior', None)
```

por:

```python
                _crear_ext = None if _en_dias else getattr(market, 'crear_oferta_exterior', None)
```

(c) Al final de la función, después del bloque `# v0.4.11.0: partidos demasiado pegados` (`_cal_ch.revisar_choques(estado)`) y antes del `except Exception as e:` que cierra `finalizar_jornada_liga`:

```python
        try:  # v0.4.12.0: lo que quedó en la agenda recibe su día (ya con los choques resueltos)
            from alpha_football import dias as _dias_fin
            if _dias_fin.activo(estado):
                _dias_fin.asignar_dias(estado)
        except Exception as e_dia:
            logger.error(f"Error asignando los días de la agenda: {e_dia}")
```

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `22/22 tests pasaron`.
Run (uno por uno): `test_ofertas_v230.py` si existe (`ls tests | grep -i oferta` para ver cuáles hay), `test_mercado_v350.py`, `test_negociaciones_v270.py`, `test_integracion_v290.py`.
Expected: todos en `N/N tests pasaron` (sin hub no hay reloj: las ofertas siguen cayendo en el acto).

---

### Task 4: Avisos de jugadores y eventos de vestuario en días sueltos

**Files:**
- Modify: `alpha_football/salidas.py` (`cierre_jornada`)
- Modify: `alpha_football/eventos.py` (`cierre_jornada`)
- Test: `tests/test_dias.py`

**Interfaces:**
- Consumes: `dias.diferir_correos/programar/asignar_dias/_entregar_item` (Task 2), `salidas.revisar_descontento/revisar_renovaciones/ofertas_garantizadas`, `eventos.sortear/pendiente`.
- Produces: con reloj, `salidas.cierre_jornada` y `eventos.cierre_jornada` dejan en la agenda los correos de descontento, "quiere renovar" y del evento (y una entrada `'garantizadas'`); sin reloj no cambia nada.

- [ ] **Step 1: Tests** — agregar:

```python
def _plantel_sano(e):
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
        j.pide_salir = j.salida_forzada = j.transferible = False
        j.prestamo = None


def test_el_aviso_de_renovar_llega_en_un_dia_sorteado():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    e['liga'].jornada_actual = 12                                          # pasada la mitad de la temporada
    S.cierre_jornada(e, random.Random(1))
    assert not [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']]
    assert any('quiere renovar' in it['datos'].get('asunto', '') for it in D.agenda(e))
    json.dumps(e['datos_carrera'])
    D.hasta_el_partido(e)
    assert [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']]


def test_sin_reloj_el_aviso_de_renovar_sigue_cayendo_en_el_acto():
    from alpha_football import salidas as S
    e = _e(); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    e['liga'].jornada_actual = 12
    S.cierre_jornada(e, random.Random(1))
    assert [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']] and D.agenda(e) == []


def test_el_descontento_llega_en_un_dia_sorteado():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.moral, j.descontento_avisado = 20, False
    S.cierre_jornada(e, random.Random(1))
    assert not [m for m in C.bandeja(e) if 'descontento' in m['asunto']]
    assert any('descontento' in it['datos'].get('asunto', '') for it in D.agenda(e))
    D.hasta_el_partido(e)
    assert [m for m in C.bandeja(e) if 'descontento' in m['asunto']]


def test_las_ofertas_garantizadas_llegan_un_dia_despues_de_cerrar():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e); e['liga'].jornada_actual = 2   # ventana abierta
    j = e['mi_equipo'].jugadores[0]
    j.pide_salir, j.moral = True, 30
    S.cierre_jornada(e, random.Random(1))
    assert not e.get('ofertas_recibidas') and any(it['tipo'] == 'garantizadas' for it in D.agenda(e))
    r = D.hasta_el_partido(e)
    assert r['ofertas'] >= 1 and e['ofertas_recibidas']


def test_el_evento_de_vestuario_llega_en_un_dia_sorteado():
    from alpha_football import eventos as EV
    e = _e(); _en_j1(e); _plantel_sano(e)
    for s in range(300):                                                   # 12% por jornada: alguna semilla lo da
        EV.cierre_jornada(e, random.Random(s))
        if D.agenda(e):
            break
    assert D.agenda(e), "ningún sorteo dio evento"
    assert not [m for m in C.bandeja(e) if m.get('evento')] and EV.pendiente(e) is None
    json.dumps(e['datos_carrera'])
    r = D.hasta_el_partido(e)
    assert r['eventos'] == 1 and EV.pendiente(e) is not None               # ya se puede decidir
```

- [ ] **Step 2: Correr y ver que falla** (los avisos y el evento caen en el acto).

- [ ] **Step 3: `salidas.py`** — en `cierre_jornada`, dos cambios. Reemplazar:

```python
        revisar_descontento(estado, rng)
        revisar_renovaciones(estado, rng)       # v0.4.10.0
```

por:

```python
        from alpha_football import dias as _dias      # v0.4.12.0: los avisos de jugadores llegan en días sueltos
        with _dias.diferir_correos(estado):
            revisar_descontento(estado, rng)
            revisar_renovaciones(estado, rng)       # v0.4.10.0
```

y reemplazar:

```python
            ofertas_garantizadas(estado, rng)
```

por:

```python
            if _dias.activo(estado):        # v0.4.12.0: la oferta llega en un día del hueco
                if any(getattr(j, 'pide_salir', False) for j in getattr(mi, 'jugadores', []) or []):
                    _dias.programar(estado, 'garantizadas')
            else:
                ofertas_garantizadas(estado, rng)
```

- [ ] **Step 4: `eventos.py`** — en `cierre_jornada`, reemplazar:

```python
        sortear(estado, rng)
```

por:

```python
        from alpha_football import dias as _dias      # v0.4.12.0: el evento llega en un día del hueco
        with _dias.diferir_correos(estado):
            sortear(estado, rng)
```

(Hay otra línea `sortear(` en el módulo — la definición `def sortear(...)`; el cambio es solo en el cuerpo de `cierre_jornada`, justo después de `revisar_promesas(estado)`.)

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `27/27 tests pasaron`.
Run (uno por uno): `test_eventos.py`, `test_renovacion_aviso.py`, `test_salidas_v440.py` (o el que corresponda: `ls tests | grep -i salid`), `test_notificaciones.py`.
Expected: todos en `N/N tests pasaron` (sin reloj no hay diferido).

---

### Task 5: Botones CONTINUAR y +1 DÍA en el hub

**Files:**
- Modify: `alpha_football/ui/league_screen.py`
- Modify: `tests/test_calendario.py` (la fecha del botón cuando hoy no hay partido)
- Test: `tests/test_dias.py`

**Interfaces:**
- Consumes: `dias.hoy/es_dia_de_continuar/continuar/avanzar_dia/texto_resumen/textos_hub` (Task 1).
- Produces: `league_screen.R_DIA` (el botón "+1 DÍA"), `league_screen._avanzar_un_dia(estado)`; `_textos_jugar` devuelve `("CONTINUAR", …)` y `_accion_jugar` corre los días cuando hoy no hay partido. El hub crea el reloj al abrirse.

- [ ] **Step 1: Tests** — agregar a `tests/test_dias.py`:

```python
def _hub(e):
    from alpha_football.ui import league_screen as L
    e['datos_carrera']['aviso_mercado_visto'] = [1, 1]                     # sin el cartel de apertura del mercado
    return L


def test_el_hub_crea_el_reloj_muestra_continuar_y_avanza_con_d_y_enter():
    e = _e(); L = _hub(e)
    pygame.event.clear(); assert L.render(screen, e) is None               # el hub crea el reloj
    assert D.activo(e) and D.es_dia_de_continuar(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"
    antes = D.hoy(e)
    key(pygame.K_d); assert L.render(screen, e) is None
    assert D.hoy(e) == antes + timedelta(days=1) and e['hub_toast'][0].startswith("Pasó 1 día")
    key(pygame.K_RETURN); assert L.render(screen, e) is None               # el foco está en el botón grande
    assert D.hoy(e) == CAL.fecha_liga(e, 1) and e['hub_toast'][0].startswith("Pasaron")
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "JUGAR"
    key(pygame.K_d); assert L.render(screen, e) is None                    # día de partido: D no hace nada
    assert D.hoy(e) == CAL.fecha_liga(e, 1)
    key(pygame.K_RETURN); assert L.render(screen, e) == 'prepartido_screen'


def test_el_boton_mas_un_dia_con_clic_y_solo_si_no_hay_partido():
    e = _e(); L = _hub(e)
    pygame.event.clear(); L.render(screen, e)
    assert L.R_JUGAR.contains(L.R_DIA) and L.R_DIA.bottom <= L.R_JUGAR.bottom
    antes = D.hoy(e)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_DIA.center, button=1))
    assert L.render(screen, e) is None and D.hoy(e) == antes + timedelta(days=1)
    D.hasta_el_partido(e)
    dia = D.hoy(e)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_DIA.center, button=1))
    res = L.render(screen, e)
    assert D.hoy(e) == dia and res == 'prepartido_screen'                  # ese clic cae en JUGAR, no avanza
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'R_DIA'` / el hub sigue mostrando JUGAR).

- [ ] **Step 3: `league_screen.py`** — siete cambios.

(a) Junto a `R_JUGAR = pygame.Rect(672, 106, 592, 96)`, agregar:

```python
R_DIA = pygame.Rect(R_JUGAR.right - 116, R_JUGAR.bottom - 30, 100, 24)   # v0.4.12.0: botón +1 DÍA (dentro de JUGAR)
```

(b) Antes de `def _accion_jugar`, agregar:

```python
def _avanzar_un_dia(estado) -> None:
    """v0.4.12.0: +1 DÍA (tecla D). Pasa un día y avisa lo que llegó; el día de un partido no hace nada."""
    try:
        from alpha_football import dias as _dias
        if _dias.es_dia_de_continuar(estado):
            _toast(estado, _dias.texto_resumen(_dias.avanzar_dia(estado)), color='azul')
    except Exception as e_dias:
        logger.error(f"Error al avanzar un día: {e_dias}")


```

(c) En `_accion_jugar`, justo después de su docstring (antes de `if fase_copa:`):

```python
    try:   # v0.4.12.0: sin partido hoy, JUGAR corre los días hasta que pase algo
        from alpha_football import dias as _dias
        if _dias.es_dia_de_continuar(estado):
            _toast(estado, _dias.texto_resumen(_dias.continuar(estado)), color='azul')
            return None
    except Exception as e_dias:
        logger.error(f"Error al continuar los días: {e_dias}")
```

(d) En `_textos_jugar`, justo después de su docstring (antes de `partido_usuario, esta_finalizada, fase_copa, rival_copa = info`):

```python
    try:   # v0.4.12.0: sin partido hoy, el botón grande es CONTINUAR
        from alpha_football import dias as _dias
        t = _dias.textos_hub(estado) if estado else None
        if t:
            return t[0], t[1], t[2], True
    except Exception as e_dias:
        logger.error(f"Error en los textos de CONTINUAR: {e_dias}")
```

(e) En el bloque que dibuja JUGAR, reemplazar la línea de C:

```python
            _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
```

por:

```python
            if habilitado and l1 == "CONTINUAR":
                from alpha_football import dias as _dias_j
                _txt_fecha = _cal_j.texto_fecha(_dias_j.hoy(estado))        # v0.4.12.0: el día en que estás
            else:
                _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
```

y, en el mismo bloque `try`, después de:

```python
        if l3:
            draw_text(screen, l3, (R_JUGAR.x + 20, R_JUGAR.y + 70), size='sm', color='azul')
```

agregar:

```python
        if l1 == "CONTINUAR":      # v0.4.12.0: avanzar de a un día
            pygame.draw.rect(screen, (30, 45, 75) if R_DIA.collidepoint(mouse_pos) else (15, 22, 40), R_DIA, border_radius=6)
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), R_DIA, width=1, border_radius=6)
            _s_dia = get_font('sm').render("+1 DÍA", True, (255, 255, 255))
            screen.blit(_s_dia, _s_dia.get_rect(center=R_DIA.center))
```

(f) En los clics de `_render_inicio`, antes de `elif R_JUGAR.collidepoint(click_pos):` (R_DIA está dentro de R_JUGAR, así que va primero):

```python
        elif l1 == "CONTINUAR" and R_DIA.collidepoint(click_pos):      # v0.4.12.0
            estado['hub_foco'] = 0
            _avanzar_un_dia(estado)
```

(g) En `render`: la tecla y el reloj. En el bucle `for ev in key_events:`, justo después del bloque de `K_j` (`return _accion_jugar(...)`) y antes de `if ev.key == pygame.K_r:`:

```python
            if ev.key == pygame.K_d and tab == 'inicio':     # v0.4.12.0: +1 DÍA
                _avanzar_un_dia(estado)
                continue
```

y, después del bloque `try` de C (el de `_c['revisado']`) y antes de `# --- Eventos ---`:

```python
        try:  # v0.4.12.0: el reloj del juego (hoy) nace aquí, al abrir el hub de la temporada
            from alpha_football import dias as _dias_r
            _dias_r.hoy(estado)
        except Exception as e_dia:
            logger.error(f"Error creando el reloj del juego: {e_dia}")
```

- [ ] **Step 4: Ajustar el test de C** — en `tests/test_calendario.py`, en `test_hub_y_prepartido_dibujan_la_fecha_sin_errores`, reemplazar:

```python
    assert CAL.texto_proximo(e) in dibujados                               # la fecha sale en el botón JUGAR
```

por:

```python
    from alpha_football import dias as _D                                  # v0.4.12.0: sin partido hoy, el botón dice CONTINUAR con la fecha de hoy
    assert CAL.texto_fecha(_D.hoy(e)) in dibujados
```

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `29/29 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_calendario.py`
Expected: `24/24 tests pasaron`.
Los tests del hub y de teclado que pulsan JUGAR se ajustan en el Task 7 (después de ver cuáles fallan).

---

### Task 6: Pantalla CALENDARIO, atajo y ayuda

**Files:**
- Modify: `alpha_football/ui/calendario_screen.py`
- Modify: `alpha_football/ui/atajos.py`
- Modify: `alpha_football/ui/ayuda.py`
- Test: `tests/test_dias.py`

**Interfaces:**
- Consumes: `dias.hoy` (Task 1), `league_screen.R_DIA` (Task 5).

- [ ] **Step 1: Tests** — agregar:

```python
def test_la_pantalla_calendario_resalta_el_dia_del_reloj():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert D.activo(e) and e['cal_mes'] == [2026, 8]                       # abre en el mes de hoy (1 de agosto)
    D.hasta_el_partido(e); _jugar(e, 1); D.hasta_el_partido(e); _jugar(e, 2); D.hasta_el_partido(e)
    e.pop('cal_mes', None)
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [D.hoy(e).year, D.hoy(e).month]                 # hoy = la fecha de la copa


def test_atajo_y_ayuda_del_hub_conocen_los_dias():
    from alpha_football.ui import atajos, ayuda, league_screen as L
    e = _e(); e['hub_tab'] = 'inicio'
    assert "D +1 Día" in atajos.ATAJOS['league_screen']
    its = ayuda.items('league_screen', e)
    assert any(r == L.R_DIA and t == "+1 DÍA" and len(x) <= 110 for r, t, x in its)
    assert all(len(x) <= 110 for _r, _t, x in its)
```

- [ ] **Step 2: Correr y ver que falla** (el calendario abre en el mes de la copa, falta el atajo y el ítem de ayuda).

- [ ] **Step 3: `calendario_screen.py`** — en `render`, reemplazar:

```python
        hoy = CAL.hoy(estado)
```

por:

```python
        from alpha_football import dias as DIAS            # v0.4.12.0: "hoy" es el día del reloj
        hoy = DIAS.hoy(estado)
```

y reemplazar:

```python
        draw_text(screen, f"Próximo partido: {CAL.texto_fecha(hoy)}", (520, 70), size='sm', color='azul')
```

por:

```python
        draw_text(screen, f"Hoy: {CAL.texto_fecha(hoy)} · Próximo: {CAL.texto_proximo(estado) or '-'}",
                  (520, 70), size='sm', color='azul')
```

- [ ] **Step 4: `atajos.py`** — en `ATAJOS['league_screen']` reemplazar `"J Jugar · ← → Pestañas` por `"J Jugar · D +1 Día · ← → Pestañas` (el resto de la línea igual).

- [ ] **Step 5: `ayuda.py`** — en `_ayuda_hub`, reemplazar el ítem de JUGAR:

```python
            (L.R_JUGAR, "JUGAR", "Juega la próxima fecha (liga o copa). Tecla J o Enter con el foco aquí."),
```

por:

```python
            (L.R_JUGAR, "JUGAR", "Juega el partido del día. Sin partido hoy es CONTINUAR: corre los días hasta que llegue algo (J o Enter)."),
            (L.R_DIA, "+1 DÍA", "Avanza un solo día (tecla D). Solo aparece cuando hoy no hay partido."),
```

y, en `_ayuda_calendario`, el texto del ítem "Mes" por: `"Tus partidos de liga y copa, día por día. En dorado, hoy; en rojo, el cierre del mercado."`.

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dias.py`
Expected: `31/31 tests pasaron`.
Run (uno por uno): `test_calendario.py`, `test_ayuda_v390.py`, `test_ux_v360.py`.
Expected: `24/24`, y los otros dos en `N/N tests pasaron`. Si `test_ayuda_v390.test_hub_por_pestana` enumera los títulos del hub y exige la lista exacta, agregar `"+1 DÍA"`; si `test_ux_v360` mide el ancho de la barra de atajos y no cabe, acortar `Resultados` a `Result.` en esa línea.

---

### Task 7: Tests viejos del hub, suite completa y cierre de G1

**Files:**
- Modify: los tests del hub que pulsen JUGAR (se ven al correrlos; ver abajo)
- Modify: `context.md` (bitácora y pendientes; fecha del encabezado)

- [ ] **Step 1: Ver qué tests viejos cambian.** Con el hub creando el reloj, todo test que renderice `league_screen`, pulse JUGAR/Enter/J y espere `'prepartido_screen'` o `'copa'` ahora corre días en vez de abrir el partido. Correr uno por uno: `test_hub_v240.py`, `test_teclado_v420.py`, `test_ux_v360.py`, `test_integracion_v290.py`, `test_copa_v430.py`, `test_presentacion_v410.py`, `test_ayuda_v390.py`, `test_notificaciones.py`.

- [ ] **Step 2: Ajustar los que fallen, sin debilitarlos.** Receta: en el test, antes de pulsar JUGAR, llevar el reloj al día del partido:

```python
    from alpha_football import dias as D                  # v0.4.12.0: el hub ahora corre los días hasta el partido
    D.hoy(e); D.hasta_el_partido(e)
```

Si un test pulsa JUGAR *después* de haber cerrado un partido con el reloj ya creado, repetir `D.hasta_el_partido(e)`. Si un test espera una oferta, un evento o un aviso al cerrar la jornada **con el reloj ya creado**, ahora quedó en la agenda: llamar `D.hasta_el_partido(e)` antes de asertar. Un test que falla por otra razón es un bug del cambio: buscar la causa raíz, no ajustar el test.

- [ ] **Step 3: Suite completa, una sola vez y un archivo a la vez.** Lanzarla con la opción de segundo plano de la herramienta (no con `nohup`), escribiendo el resumen en una carpeta temporal fuera del repo:

```bash
cd "C:/Users/diego/Downloads/AlphaFootball" && mkdir -p "$TEMP/af_suite_g1" && : > "$TEMP/af_suite_g1/resumen.txt" && for f in tests/test_*.py; do
  b=$(basename "$f" .py); PYTHONIOENCODING=utf-8 timeout 1200 python "$f" > "$TEMP/af_suite_g1/$b.log" 2>&1; rc=$?
  echo "$b rc=$rc FAIL=$(grep -c 'FAIL' "$TEMP/af_suite_g1/$b.log") · $(tail -1 "$TEMP/af_suite_g1/$b.log" | cut -c1-80)" >> "$TEMP/af_suite_g1/resumen.txt"
done; echo TERMINADO >> "$TEMP/af_suite_g1/resumen.txt"
```

Expected: cada línea con `rc=0` y `FAIL=0`. `test_motor_v400` mide tiempos del motor y puede fallar una vez por carga de la máquina: repetirlo solo antes de investigar.

- [ ] **Step 4: Comprobación sin pantalla** — con `SDL_VIDEODRIVER=dummy` y un estado de carrera con el calendario armado: renderizar un cuadro del hub (debe decir CONTINUAR), pulsar `D`, pulsar Enter hasta el día del partido (debe decir JUGAR), abrir `calendario_screen` y `prepartido_screen`, y simular una temporada de 22 partidos cerrando cada uno con `finalizar_jornada_liga` y corriendo `D.hasta_el_partido` entre partidos. Confirmar que no hay excepciones ni líneas `ERROR` en el log y que al final no queda nada atrapado en `D.agenda(e)`. Repetir con `estado_carrera('betplay')` (el reloj nace el 1 de enero de 2027).

- [ ] **Step 5: `context.md`** — agregar la bitácora "2026-10-07 — Avance por días (v0.4.12.0, sub-proyecto G1, sin commit)" con: el módulo `dias.py` y sus funciones, dónde viven `dia` y `agenda` (dentro de `datos_carrera['calendario']`), qué cae en días sueltos y qué sigue al cerrar el partido, el mecanismo `diferir_correos` y el sorteo de ofertas, la energía diaria, los botones y la tecla `D`, las cinco desviaciones del spec y los tests viejos ajustados. Actualizar la fecha del encabezado y dejar como pendientes: G2 (mercado por fecha, absorbe D), E, F, el bump de versión (título y badge siguen en 0.4.10.0) y la prueba a mano: CONTINUAR se detiene en una oferta o un correo, +1 DÍA, JUGAR el día del partido, energía tras una semana con copa, y guardar/cargar a mitad de un hueco.
