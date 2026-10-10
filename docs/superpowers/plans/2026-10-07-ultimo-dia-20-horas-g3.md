# Último día de fichajes: las 20 horas (v0.4.14.0, sub-proyecto G3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (método elegido por Diego: **NATIVO**, tú solo, en una sesión nueva con Sonnet 5.5, sin subagentes). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sin commits:** Diego da el OK final. Nunca atribuir a Claude ni a una IA en git.
> **Orden obligatorio:** G1 (`2026-10-07-avance-por-dias-g1.md`) y G2 (`2026-10-07-temporada-por-fechas-g2.md`) deben estar implementados ANTES de este plan.

**Goal:** El 31 de agosto y el 31 de enero el mercado tiene un reloj de 20 horas: lo que se concreta cuesta horas, "lo analizamos" responde a las 3 horas, cada hora puede entrar una oferta, y a las 0 horas (o con CERRAR MERCADO) el mercado se cierra. El día no pasa mientras queden horas.

**Architecture:** Módulo sin UI `alpha_football/dia_final.py` con el estado del día (`datos_carrera['calendario']['dia_final'] = {'fecha', 'horas', 'cierre'}`). `traspasos_pendientes.puede_concretar(estado, horas)` es la única puerta de "¿puedo inscribir esto ya?": mira el mercado por fecha (G2) y gasta horas el último día; sin horas el trato queda acordado para la próxima ventana, como con el mercado cerrado. Los "lo analizamos" guardan su hora de respuesta en el propio registro (`hora_resp`) y un único predicado `dia_final.vencido` decide cuándo toca responder (por jornada, como siempre, o por hora). `dias.avanzar_dia/continuar` no pasan el día con horas; el hub reemplaza JUGAR por el panel del día.

**Tech Stack:** Python 3.10, pygame. Tests = scripts ejecutables (`python tests/test_x.py`) con ventana dummy.

**Spec:** `docs/superpowers/specs/2026-10-07-ultimo-dia-20-horas-g3-design.md` (reemplaza la sección D del spec del 2026-10-06). Depende de C, G1 (`dias.py`) y G2 (`temporada.py`, `aviso_mercado` por fecha).

## Global Constraints

- Versión: **0.4.14.0**. Comentarios nuevos: `# v0.4.14.0`. No reescribir comentarios viejos. El título de la ventana y el badge del README siguen en 0.4.10.0: no se tocan.
- **Git: sin commits, push, stash, reset ni checkout de archivos.** Los planes y specs están sin commitear: no los reviertas.
- Usar Edit parcial; no reescribir archivos existentes ni "limpiar" alrededor del cambio. Comentarios y textos del juego en español.
- Cada test corre con `PYTHONIOENCODING=utf-8 python tests/<archivo>.py` y termina en `N/N tests pasaron`. Hay tests que salen con código 0 aunque impriman `FAIL`: revisar siempre la salida. Corre solo los tests que cada tarea indica; la suite completa va una sola vez, al final (Task 6), en segundo plano.
- Los números de línea son aproximados: ubica cada cambio por el código citado. Si un bloque no existe tal cual (G1 y G2 pueden haberlo cambiado un poco), adapta lo mínimo y anota la desviación.
- **Horas** (constantes en `dia_final`): 20 horas; AVANZAR 1 HORA = 1; fichaje inscrito (compra, agente libre o préstamo que llega al user) = 3; venta o cesión concretada = 2; "lo analizamos" responde a las 3 horas. Negociar, ofertar y contraofertar no gastan horas: solo lo que se concreta.
- Con menos horas de las que cuesta, el trato queda **acordado para la próxima ventana** (`traspasos_pendientes`), igual que con el mercado cerrado. Un "lo analizamos" pedido con menos de 3 horas se responde en el momento: "no hay tiempo".
- Cada hora: llegan las respuestas que vencen y puede entrar una oferta por un jugador tuyo (**10%**; **25%** si tienes transferibles o alguien que pide salir). A las 0 horas o con CERRAR MERCADO (pide confirmación): se retiran las ofertas sin responder, los análisis pendientes se caen con un correo, la IA hace su ronda de cierre y aparece el cartel MERCADO CERRADO.
- Ni `+1 DÍA` ni `CONTINUAR` avanzan el día de cierre mientras queden horas. `dias.continuar(parar=False)` / `hasta_el_partido` (tests y migraciones) cierran el último día solos.
- Los forzados de la directiva (venta por quiebra) no gastan horas.

### Desviaciones del spec decididas al planificar

1. **Los "lo analizamos" guardan su hora en el propio registro** (`hora_resp`) en vez de una lista `pendientes` dentro de `dia_final`: ya viven en `datos_carrera` y así no hay dos fuentes de verdad.
2. **`analizar_contrato`** (el jugador analiza un contrato) con menos de 3 horas devuelve `None` (rechazo normal con su pedido) en vez de un mensaje propio.
3. **`temporada.hito_del_dia` cambia**: el 'cierra' del día siguiente (G2) desaparece y el día de cierre es el hito `'ultimo'`; el cartel MERCADO CERRADO lo muestra `dia_final.cerrar`.
4. **`puede_concretar` gasta las horas antes de ejecutar** la operación: si un paso posterior falla (p. ej. el jugador ya no está), las horas se pierden. Es lo que pasa en la vida real con un trato caído.

## Review Focus

1. **Pasar de largo**: `+1 DÍA`, `CONTINUAR` y `JUGAR` no saltan el 31 con horas; `hasta_el_partido` lo cierra solo y llega al partido (Task 1).
2. **Horas insuficientes**: un fichaje o venta que cuesta más de lo que queda no gasta nada y queda acordado para la próxima ventana (Task 3).
3. **"Lo analizamos"**: con ≥ 3 horas responde cuando toca (y a las 0 horas se responde antes de cerrar); con menos, "no hay tiempo"; lo que sigue pendiente al cerrar se cae con correo (Tasks 2 y 4).
4. **Save cargado el 31** con el día aún no abierto, abierto o ya cerrado (Tasks 1 y 5).
5. **Cerrar dos veces** (0 horas y CERRAR MERCADO) no duplica correos, rondas de la IA ni cartel (Task 2).

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `alpha_football/dia_final.py` (nuevo) | Horas, costos, avance por hora, cierre, ofertas por hora, respuestas ("lo analizamos") y textos |
| `alpha_football/temporada.py` | `hito_del_dia` ('ultimo'); `ventana_actual` respeta el cierre anticipado |
| `alpha_football/dias.py` | el día no avanza con horas; el hito 'ultimo' abre el día; auto-cierre con `parar=False` |
| `alpha_football/traspasos_pendientes.py` | `puede_concretar` |
| `alpha_football/negociacion.py`, `contraofertas.py`, `prestamos.py` | puertas con horas y "lo analizamos" con hora de respuesta |
| `alpha_football/ui/aviso_mercado.py`, `league_screen.py`, `ayuda.py`, `atajos.py` | cartel, franja, panel del día y atajos |
| `tests/test_dia_final.py` (nuevo) | tests de G3 |

Cabecera del archivo de test nuevo (copiar tal cual):

```python
"""v0.4.14.0: el último día de fichajes (20 horas, costos, "lo analizamos", cierre y hub)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T, dia_final as DF


def _en_el_ultimo_dia():
    """Partida con J1 y J2 jugadas y el reloj recién llegado al 31 de agosto (20 horas)."""
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-30'
    r = D.avanzar_dia(e)
    return e, r
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

### Task 1: El día final: horas, estado y el reloj que no pasa

**Files:**
- Create: `alpha_football/dia_final.py`
- Modify: `alpha_football/temporada.py`, `alpha_football/dias.py`
- Test: `tests/test_dia_final.py` (nuevo)

**Interfaces:**
- Consumes: `calendario.asegurar`, `temporada.fecha/ultimo_dia/ventanas`, `dias.activo/hoy/es_dia_de_continuar/avanzar_dia/continuar` (G1/G2).
- Produces: `dia_final.HORAS_DIA/HORAS_FICHAJE/HORAS_VENTA/HORAS_ANALISIS`, `_bloque(estado)`, `horas(estado) -> int`, `activo(estado) -> bool` (hoy es un último día y quedan horas), `cerrado(estado) -> bool`, `abrir(estado) -> bool`, `gastar(estado, h) -> bool` (gratis fuera del último día), `avanzar_hora(estado, rng=None) -> dict`, `cerrar(estado, rng=None) -> dict`. `temporada.hito_del_dia` devuelve `'abre'` o `'ultimo'`. `dias.avanzar_dia` devuelve `'hito': 'ultimo'` y abre el día; con horas, `es_dia_de_continuar` es False.

- [ ] **Step 1: Crear el test** con la cabecera, el pie y estos casos:

```python
def test_el_ultimo_dia_se_abre_al_llegar_el_reloj_al_cierre_con_20_horas():
    e, r = _en_el_ultimo_dia()
    assert D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'
    assert DF.activo(e) and DF.horas(e) == 20 and not DF.cerrado(e)
    assert T.ventana_abierta(e) and T.ultimo_dia(e)
    assert T.hito_del_dia(e, date(2026, 8, 31)) == 'ultimo' and T.hito_del_dia(e, date(2026, 9, 1)) is None
    assert T.hito_del_dia(e, date(2026, 7, 1)) == 'abre'


def test_con_horas_el_dia_no_pasa_ni_con_mas_un_dia_ni_con_continuar():
    e, _ = _en_el_ultimo_dia()
    assert not D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 0
    assert D.continuar(e)['dias'] == 0 and D.hoy(e) == date(2026, 8, 31)


def test_hasta_el_partido_cierra_el_ultimo_dia_solo():
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-22'
    D.hasta_el_partido(e)                                                  # pasa por el 31 de agosto sin quedarse
    assert D.hoy(e) == CAL.fecha_liga(e, 3) and not T.ventana_abierta(e)
    assert any(m['asunto'] == "Se cerró el mercado de pases" for m in C.bandeja(e))


def test_avanzar_hora_gasta_una_hora_y_a_las_cero_se_cierra_el_mercado():
    e, _ = _en_el_ultimo_dia()
    for _ in range(19):
        assert DF.avanzar_hora(e, random.Random(1))['horas'] == 1
    assert DF.horas(e) == 1 and DF.activo(e)
    r = DF.avanzar_hora(e, random.Random(1))
    assert r['cerro'] and DF.horas(e) == 0 and not DF.activo(e) and DF.cerrado(e) and not T.ventana_abierta(e)
    assert e['aviso_mercado_activo']['tipo'] == 'cierra'
    assert DF.avanzar_hora(e)['horas'] == 0                                # cerrado: no gasta más
    assert D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 1 and D.hoy(e) == date(2026, 9, 1)


def test_los_costos_en_horas_y_fuera_del_ultimo_dia_es_gratis():
    e, _ = _en_el_ultimo_dia()
    assert DF.gastar(e, DF.HORAS_FICHAJE) and DF.horas(e) == 17
    assert DF.gastar(e, DF.HORAS_VENTA) and DF.horas(e) == 15
    assert not DF.gastar(e, 99) and DF.horas(e) == 15                      # no alcanza: no gasta
    f = _e(); D.hoy(f)
    assert DF.gastar(f, 3) is True and not DF.activo(f)                    # un día cualquiera: sin horas


def test_un_save_cargado_el_31_arranca_con_20_horas_y_el_dia_cerrado_se_conserva():
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-31'                                  # cargado en el último día, sin abrir
    assert not DF.activo(e) and DF.abrir(e) and DF.horas(e) == 20
    assert not DF.abrir(e)                                                 # ya estaba abierto
    DF.cerrar(e)
    f = _e(); f['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))
    assert DF.cerrado(f) and not DF.activo(f) and not DF.abrir(f)          # cerrado, sigue cerrado al cargar
```

- [ ] **Step 2: Correr y ver que falla**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: falla al importar (`cannot import name 'dia_final'`).

- [ ] **Step 3: `alpha_football/dia_final.py`:**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Último día de fichajes (v0.4.14.0)
El 31 de agosto y el 31 de enero el mercado tiene un reloj de 20 horas. Lo que se concreta cuesta horas
(fichajes 3, ventas 2); "lo analizamos" responde a las 3 horas. A las 0 horas, o con CERRAR MERCADO, se
cierra: se retiran las ofertas, caen los análisis pendientes, la IA hace su ronda de cierre y el mercado
queda cerrado el resto del día. Datos: datos_carrera['calendario']['dia_final'] = {'fecha', 'horas', 'cierre'}
(dentro del bloque de C, que se rearma solo al cambiar de temporada, liga o club).
Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

HORAS_DIA = 20
HORAS_FICHAJE = 3            # fichaje inscrito: compra, agente libre o préstamo que llega al user
HORAS_VENTA = 2              # venta o cesión concretada
HORAS_ANALISIS = 3           # "lo analizamos" responde a las 3 horas
PROB_OFERTA_HORA = 0.10
PROB_OFERTA_HORA_TRANSFERIBLES = 0.25


def _hoy_iso(estado: dict) -> str:
    from alpha_football import temporada as T
    return T.fecha(estado).isoformat()


def _bloque(estado: dict) -> Optional[dict]:
    """El estado del último día de HOY (None si hoy no se abrió ninguno)."""
    b = CAL.asegurar(estado).get('dia_final')
    return b if isinstance(b, dict) and b.get('fecha') == _hoy_iso(estado) else None


def horas(estado: dict) -> int:
    b = _bloque(estado)
    return int(b.get('horas', 0) or 0) if b else 0


def activo(estado: dict) -> bool:
    """Hoy es un último día y quedan horas: el reloj de horas corre y el día no pasa."""
    try:
        return horas(estado) > 0
    except Exception:
        return False


def cerrado(estado: dict) -> bool:
    """Hoy es un último día cuyo mercado ya se cerró (0 horas o CERRAR MERCADO)."""
    try:
        b = _bloque(estado)
        return b is not None and int(b.get('horas', 0) or 0) <= 0
    except Exception:
        return False


def abrir(estado: dict) -> bool:
    """Empieza el último día (20 horas) si hoy es un cierre de mercado y aún no se abrió. True si lo abrió."""
    try:
        from alpha_football import temporada as T
        if estado.get('liga') is None or not T.ultimo_dia(estado) or _bloque(estado) is not None:
            return False
        CAL.asegurar(estado)['dia_final'] = {'fecha': _hoy_iso(estado), 'horas': HORAS_DIA}
        return True
    except Exception as e:
        logger.error(f"dia_final: no se pudo abrir el último día: {e}", exc_info=True)
        return False


def gastar(estado: dict, h: int) -> bool:
    """Gasta `h` horas del último día. Fuera de él es gratis (True). Con horas insuficientes no gasta (False).
    Tras gastar responde lo que vence y, si quedan 0 horas, cierra el mercado."""
    if not activo(estado):
        return True
    b = _bloque(estado)
    if int(b['horas']) < int(h):
        return False
    b['horas'] = int(b['horas']) - int(h)
    _tras_pasar_horas(estado)
    return True


def _tras_pasar_horas(estado: dict, rng: Optional[random.Random] = None) -> None:
    responder(estado, rng)
    if horas(estado) <= 0:
        cerrar(estado, rng)


_RESPONDIENDO = False        # evita la reentrada: una venta aceptada dentro de una respuesta gasta horas


def responder(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Las respuestas de 'lo analizamos' cuya hora llegó (contraofertas y préstamos). Sin reentrada."""
    global _RESPONDIENDO
    if _RESPONDIENDO:
        return
    _RESPONDIENDO = True
    azar = rng or random.Random()
    try:
        from alpha_football import contraofertas, prestamos
        contraofertas.resolver_analisis(estado, azar)
        prestamos.resolver_analisis(estado, azar)
    except Exception as e:
        logger.error(f"dia_final: no se pudieron resolver los análisis: {e}", exc_info=True)
    finally:
        _RESPONDIENDO = False


def avanzar_hora(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Pasa 1 hora (AVANZAR 1 HORA); a las 0 horas se cierra el mercado. (Task 2: respuestas y ofertas por hora.)
    Devuelve {'horas', 'correos', 'ofertas', 'cerro'}."""
    res = {'horas': 0, 'correos': 0, 'ofertas': 0, 'cerro': False}
    if not activo(estado):
        return res
    b = _bloque(estado)
    b['horas'] = int(b['horas']) - 1
    res['horas'] = 1
    if b['horas'] <= 0:
        cerrar(estado, rng)
        res['cerro'] = True
    return res


def cerrar(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Cierra el mercado del último día. Idempotente. (Task 2: retira ofertas, cae análisis y ronda de la IA.)"""
    res = {'ofertas': 0, 'analisis': 0, 'ronda': False}
    b = _bloque(estado)
    if b is None or b.get('cierre'):
        return res
    b['cierre'] = True
    b['horas'] = 0
    try:
        from alpha_football.ui import aviso_mercado as AM
        AM._abrir(estado, 'cierra', _hoy_iso(estado))
    except Exception as e:
        logger.error(f"dia_final: no se pudo mostrar el cierre: {e}", exc_info=True)
    return res
```

- [ ] **Step 4: `temporada.py`** — dos cambios.

(a) Reemplazar `hito_del_dia`:

```python
def hito_del_dia(estado: dict, d: date) -> Optional[str]:
    """'abre' el primer día de una ventana, 'ultimo' el día de su cierre (el último día de fichajes); None el resto."""
    for a, b in ventanas(estado).values():
        if d == a:
            return 'abre'
        if d == b:
            return 'ultimo'
    return None
```

(b) Reemplazar `ventana_actual`:

```python
def ventana_actual(estado: dict) -> Optional[str]:
    """'inicio' | 'invierno' si hoy el mercado está abierto; None si no (o si el último día ya se cerró)."""
    h = fecha(estado)
    n = next((n for n, (a, b) in ventanas(estado).items() if a <= h <= b), None)
    if n is not None:
        try:
            from alpha_football import dia_final
            if dia_final.cerrado(estado):
                return None                     # v0.4.14.0: CERRAR MERCADO / 0 horas cierran antes de la medianoche
        except Exception as e:
            logger.error(f"temporada: no se pudo leer el último día: {e}")
    return n
```

- [ ] **Step 5: `dias.py`** — cuatro cambios.

(a) En `es_dia_de_continuar`, justo después de `if not activo(estado): return False`:

```python
        from alpha_football import dia_final as DF
        if DF.activo(estado):
            return False                       # v0.4.14.0: el último día no pasa mientras queden horas
```

(b) En `avanzar_dia`, reemplazar:

```python
            hito = revisar_dia(estado, nueva)
            if hito:
                res['hito'] = hito
```

por:

```python
            hito = revisar_dia(estado, nueva)
            if hito:
                res['hito'] = hito
            if hito == 'ultimo':               # v0.4.14.0: llegó el cierre del mercado: empiezan las 20 horas
                from alpha_football import dia_final as DF
                DF.abrir(estado)
```

(c) En `continuar`, al inicio del cuerpo del bucle `for _ in range(MAX_DIAS):`:

```python
        if not parar:                          # v0.4.14.0: tests y migraciones: el último día se cierra solo
            from alpha_football import dia_final as DF
            if DF.activo(estado):
                DF.cerrar(estado)
```

(d) En `texto_resumen`, junto a los textos de hito: `elif r.get('hito') == 'ultimo': partes.append("último día de fichajes")`.

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: `6/6 tests pasaron`.
Run: `PYTHONIOENCODING=utf-8 python tests/test_temporada.py`
Expected: fallan los tests de G2 que esperan el hito `'cierra'` (`test_ventana_actual_cierres_y_proxima_apertura`, `test_continuar_se_detiene_al_abrir_y_al_cerrar_el_mercado`, `test_el_cartel_sale_el_dia_que_abre_y_el_dia_despues_de_cerrar`): se ajustan en el Task 6. Anota cuáles.

---

### Task 2: El cierre completo y las ofertas por hora

**Files:**
- Modify: `alpha_football/dia_final.py`
- Test: `tests/test_dia_final.py`

**Interfaces:**
- Consumes: `dias._entregar_oferta` (G1), `mercado_ia.ronda_fichajes_ia(estado, modo, rng)`, `ui.aviso_mercado._abrir` (G2), `correo.enviar`.
- Produces: `dia_final.prob_oferta_hora(estado) -> float`, `cerrar(estado, rng)` completo (`{'ofertas', 'analisis', 'ronda'}`), `_caer_analisis(estado) -> int`; `avanzar_hora` entrega respuestas, ofertas y cierra.

- [ ] **Step 1: Tests** — agregar:

```python
def test_cada_hora_puede_entrar_una_oferta_con_el_10_o_el_25_por_ciento():
    e, _ = _en_el_ultimo_dia()
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    assert DF.prob_oferta_hora(e) == 0.10
    e['mi_equipo'].jugadores[3].transferible = True
    assert DF.prob_oferta_hora(e) == 0.25
    llamadas = []
    original = D._entregar_oferta
    D._entregar_oferta = lambda estado, exterior: llamadas.append(exterior) or 1
    try:
        for transf, esperado in ((False, 0.10), (True, 0.25)):
            e['mi_equipo'].jugadores[3].transferible = transf
            llamadas.clear(); rng = random.Random(5); N = 2000
            for _ in range(N):
                DF._bloque(e)['horas'] = 20                                # que no cierre
                DF.avanzar_hora(e, rng)
            assert abs(len(llamadas) / N - esperado) < 0.03, (transf, len(llamadas) / N)
            assert not any(llamadas)                                       # son ofertas locales, no del exterior
    finally:
        D._entregar_oferta = original


def test_cerrar_retira_ofertas_cae_los_analisis_hace_la_ronda_y_no_se_repite():
    from alpha_football import mercado_ia as MIA
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']
    e['ofertas_recibidas'] = [{'jugador': mi.jugadores[3], 'comprador': liga.equipos[1], 'monto': 1}]
    dc = e['datos_carrera']
    dc['analisis_compras'] = [{'jugador_id': 1, 'club_id': 2, 'club': 'X', 'jugador': 'Y', 'monto': 5,
                               'jornada': 3, 'temporada': 1, 'hora_resp': 10},
                              {'jugador_id': 7, 'club_id': 2, 'club': 'X', 'jugador': 'Z', 'monto': 5,
                               'jornada': 3, 'temporada': 1}]                  # el de la jornada siguiente se queda
    llamadas = []
    original = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: llamadas.append(modo) or []
    try:
        r = DF.cerrar(e)
        assert DF.cerrar(e) == {'ofertas': 0, 'analisis': 0, 'ronda': False}   # idempotente
    finally:
        MIA.ronda_fichajes_ia = original
    assert r == {'ofertas': 1, 'analisis': 1, 'ronda': True} and llamadas == ['ventana']
    assert e['ofertas_recibidas'] == [] and [a['jugador'] for a in dc['analisis_compras']] == ['Z']
    caidos = [m for m in C.bandeja(e) if "Se cayó el trato por Y" in m['asunto']]
    assert len(caidos) == 1 and "se acabó el mercado" in caidos[0]['cuerpo'].lower()
    assert len([m for m in C.bandeja(e) if m['asunto'] == "Se cerró el mercado de pases"]) == 1
```

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'prob_oferta_hora'`).

- [ ] **Step 3: `dia_final.py`** — reemplazar `avanzar_hora` y `cerrar` por las versiones completas y agregar `prob_oferta_hora` y `_caer_analisis`:

```python
def prob_oferta_hora(estado: dict) -> float:
    """10% por hora; 25% si tienes transferibles o alguien que pide salir."""
    mi = estado.get('mi_equipo')
    hay = any(getattr(j, 'transferible', False) or getattr(j, 'pide_salir', False)
              for j in getattr(mi, 'jugadores', []) or [])
    return PROB_OFERTA_HORA_TRANSFERIBLES if hay else PROB_OFERTA_HORA


def avanzar_hora(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Pasa 1 hora (AVANZAR 1 HORA): llegan las respuestas que vencen y puede entrar una oferta por un
    jugador tuyo; a las 0 horas se cierra el mercado. Devuelve {'horas', 'correos', 'ofertas', 'cerro'}."""
    res = {'horas': 0, 'correos': 0, 'ofertas': 0, 'cerro': False}
    if not activo(estado):
        return res
    from alpha_football import correo as C
    azar = rng or random.Random()
    b = _bloque(estado)
    b['horas'] = int(b['horas']) - 1
    res['horas'] = 1
    n0 = len(C.bandeja(estado))
    responder(estado, azar)
    res['correos'] = max(0, len(C.bandeja(estado)) - n0)
    if b['horas'] > 0 and azar.random() < prob_oferta_hora(estado):
        try:
            from alpha_football import dias
            res['ofertas'] = dias._entregar_oferta(estado, False)
        except Exception as e:
            logger.error(f"dia_final: no se pudo crear la oferta de la hora: {e}", exc_info=True)
    if b['horas'] <= 0:
        cerrar(estado, azar)
        res['cerro'] = True
    return res


def _caer_analisis(estado: dict) -> int:
    """Los 'lo analizamos' con hora de respuesta que no llegaron a responder se caen, cada uno con su correo."""
    from alpha_football import correo as C
    dc = estado.setdefault('datos_carrera', {})
    n = 0
    for clave in ('analisis_compras', 'analisis_contratos', 'analisis_prestamos'):
        vivos = []
        for a in dc.get(clave) or []:
            if a.get('hora_resp') is None:
                vivos.append(a)
                continue
            n += 1
            C.enviar(estado, 'club', f"Se cayó el trato por {a.get('jugador', 'el jugador')}",
                     "Se acabó el mercado antes de que respondieran: el trato queda sin efecto.")
        dc[clave] = vivos
    return n


def cerrar(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Cierra el mercado del último día (0 horas o CERRAR MERCADO). Idempotente: retira las ofertas sin
    responder, cae los análisis pendientes (con correo), la IA hace su ronda de cierre y aparece el cartel
    MERCADO CERRADO. Devuelve {'ofertas', 'analisis', 'ronda'}."""
    res = {'ofertas': 0, 'analisis': 0, 'ronda': False}
    b = _bloque(estado)
    if b is None or b.get('cierre'):
        return res
    b['cierre'] = True                                   # primero la marca: nada se hace dos veces
    azar = rng or random.Random()
    try:
        res['ofertas'] = len(estado.get('ofertas_recibidas') or [])
        estado['ofertas_recibidas'] = []
        res['analisis'] = _caer_analisis(estado)
    except Exception as e:
        logger.error(f"dia_final: no se pudieron limpiar las ofertas y los análisis: {e}", exc_info=True)
    try:
        from alpha_football.mercado_ia import ronda_fichajes_ia
        ronda_fichajes_ia(estado, 'ventana', azar)       # con el mercado todavía abierto: ronda de cierre
        res['ronda'] = True
    except Exception as e:
        logger.error(f"dia_final: no se pudo hacer la ronda de cierre: {e}", exc_info=True)
    b['horas'] = 0
    try:
        from alpha_football.ui import aviso_mercado as AM
        AM._abrir(estado, 'cierra', _hoy_iso(estado))
    except Exception as e:
        logger.error(f"dia_final: no se pudo mostrar el cierre: {e}", exc_info=True)
    return res
```

(`_caer_analisis` puede ir antes de `cerrar`; el orden de definición en el módulo no importa).

- [ ] **Step 4: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: `8/8 tests pasaron`.

---

### Task 3: Las puertas del mercado cobran horas

**Files:**
- Modify: `alpha_football/traspasos_pendientes.py`, `alpha_football/negociacion.py`, `alpha_football/contraofertas.py`, `alpha_football/prestamos.py`
- Test: `tests/test_dia_final.py`

**Interfaces:**
- Consumes: `dia_final.gastar/HORAS_FICHAJE/HORAS_VENTA` (Task 1), `traspasos_pendientes.mercado_abierto`.
- Produces: `traspasos_pendientes.puede_concretar(estado, horas) -> bool` (mercado abierto y, el último día, con horas suficientes: las gasta). `negociacion.fichar`, `contraofertas.vender` y `prestamos.iniciar` la usan.

- [ ] **Step 1: Tests** — agregar:

```python
def test_un_fichaje_cuesta_3_horas_y_con_menos_queda_acordado_para_la_proxima_ventana():
    from alpha_football import negociacion as N, traspasos_pendientes as TP
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']; mi.balance = 10 ** 12
    DF._bloque(e)['horas'] = 2
    club, j = liga.equipos[1], liga.equipos[1].jugadores[0]
    ok, msg = N.fichar(e, j, club, 1_000)
    assert ok and TP.pendiente_de(e, j) is not None and j not in mi.jugadores and DF.horas(e) == 2
    DF._bloque(e)['horas'] = 5
    club2, j2 = liga.equipos[2], liga.equipos[2].jugadores[0]
    ok, msg = N.fichar(e, j2, club2, 1_000)
    assert ok and j2 in mi.jugadores and TP.pendiente_de(e, j2) is None and DF.horas(e) == 2


def test_una_venta_cuesta_2_horas_y_sin_horas_queda_acordada():
    from alpha_football import contraofertas as CO, traspasos_pendientes as TP
    e, _ = _en_el_ultimo_dia(); mi, comp = e['mi_equipo'], e['liga'].equipos[1]; comp.balance = 10 ** 12
    j = mi.jugadores[8]
    assert CO.vender(e, {'jugador': j, 'comprador': comp, 'monto': 5_000_000}) and j not in mi.jugadores
    assert DF.horas(e) == 18
    j2 = mi.jugadores[8]; DF._bloque(e)['horas'] = 1
    assert CO.vender(e, {'jugador': j2, 'comprador': comp, 'monto': 5_000_000})
    assert TP.pendiente_de(e, j2) is not None and j2 in mi.jugadores and DF.horas(e) == 1


def test_fuera_del_ultimo_dia_las_puertas_no_cobran_horas():
    from alpha_football import contraofertas as CO
    e = _e(); D.hoy(e); mi, comp = e['mi_equipo'], e['liga'].equipos[1]; comp.balance = 10 ** 12
    j = mi.jugadores[8]
    assert CO.vender(e, {'jugador': j, 'comprador': comp, 'monto': 5_000_000}) and j not in mi.jugadores
    assert DF.horas(e) == 0 and not DF.activo(e)


def test_un_prestamo_que_llega_cuesta_3_horas_y_una_cesion_2():
    from alpha_football import prestamos as PR
    e, _ = _en_el_ultimo_dia(); mi, otro = e['mi_equipo'], e['liga'].equipos[1]
    j = otro.jugadores[0]
    PR.iniciar(e, j, otro, mi, 6, 50)                                      # llega a tu club
    assert j in mi.jugadores and DF.horas(e) == 17
    j2 = mi.jugadores[10]
    PR.iniciar(e, j2, mi, otro, 6, 50)                                     # tu jugador se va cedido
    assert j2 in otro.jugadores and DF.horas(e) == 15
```

- [ ] **Step 2: Correr y ver que falla** (no cobran horas).

- [ ] **Step 3: `traspasos_pendientes.py`** — agregar junto a `mercado_abierto`:

```python
def puede_concretar(estado: dict, horas: int) -> bool:
    """v0.4.14.0: ¿se puede inscribir/concretar esto ya? Mercado abierto y, el último día, con horas
    suficientes (las gasta). Es la única puerta de las operaciones del user."""
    if not mercado_abierto(estado):
        return False
    from alpha_football import dia_final as DF
    return DF.gastar(estado, horas)
```

- [ ] **Step 4: Las tres puertas.**

`alpha_football/negociacion.py` (`fichar`), reemplazar:

```python
    if not TP.mercado_abierto(estado):
        return _fichar_diferido(estado, jugador, club, precio)
```

por:

```python
    from alpha_football import dia_final as DF      # v0.4.14.0: el último día, un fichaje cuesta 3 horas
    if not TP.puede_concretar(estado, DF.HORAS_FICHAJE):
        return _fichar_diferido(estado, jugador, club, precio)
```

`alpha_football/contraofertas.py` (`vender`), reemplazar `    if not TP.mercado_abierto(estado):\n        # mercado cerrado: la plata llega ya, el jugador se va cuando se abra la ventana` por:

```python
    from alpha_football import dia_final as DF      # v0.4.14.0: el último día, una venta cuesta 2 horas
    if not TP.puede_concretar(estado, DF.HORAS_VENTA):
        # mercado cerrado: la plata llega ya, el jugador se va cuando se abra la ventana
```

`alpha_football/prestamos.py` (`iniciar`), reemplazar la línea `    if _abierto(estado):\n        _mover_ida(estado, jugador, dueno, destino, reg)` por:

```python
    from alpha_football import dia_final as DF      # v0.4.14.0: llega a tu club = 3 horas; sale cedido = 2
    from alpha_football.traspasos_pendientes import puede_concretar
    if puede_concretar(estado, DF.HORAS_FICHAJE if destino is _mi(estado) else DF.HORAS_VENTA):
        _mover_ida(estado, jugador, dueno, destino, reg)
```

(la línea `return f"... juega en {destino.nombre} a préstamo hasta ..."` que sigue no cambia).

- [ ] **Step 5: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: `12/12 tests pasaron`.
Run (uno por uno): `test_negociaciones_v270.py`, `test_ventana_traspaso.py`, `test_prestamos.py`.
Expected: `N/N tests pasaron` (fuera del último día no hay cambio).

---

### Task 4: "Lo analizamos" con hora de respuesta

**Files:**
- Modify: `alpha_football/dia_final.py`, `alpha_football/contraofertas.py`, `alpha_football/negociacion.py`, `alpha_football/prestamos.py`
- Test: `tests/test_dia_final.py`

**Interfaces:**
- Consumes: `dia_final.horas/_bloque/responder` (Tasks 1 y 2).
- Produces: `dia_final.analisis(estado) -> (ok, hora_resp)`, `texto_respuesta(hora, uno=False) -> str`, `vencido(estado, item) -> bool`. Cada "lo analizamos" pedido el último día guarda `hora_resp`; las cinco resoluciones por jornada usan `vencido`.

- [ ] **Step 1: Tests** — agregar:

```python
def test_vencido_por_jornada_como_siempre_o_por_hora():
    e, _ = _en_el_ultimo_dia()
    liga = e['liga']; liga.jornada_actual = 3
    assert not DF.vencido(e, {'jornada': 3}) and DF.vencido(e, {'jornada': 2})        # la regla de siempre
    assert DF.vencido(e, {'jornada': 3, 'temporada': 7})                              # otra temporada: ya toca
    assert not DF.vencido(e, {'jornada': 3, 'hora_resp': 17}) and DF.horas(e) == 20
    DF._bloque(e)['horas'] = 17
    assert DF.vencido(e, {'jornada': 3, 'hora_resp': 17})                             # llegó su hora
    CAL.asegurar(e)['dia'] = '2026-09-02'
    assert DF.vencido(e, {'jornada': 3, 'hora_resp': 5})                              # el día final ya pasó


def test_analisis_con_horas_responde_a_las_3_horas_y_con_menos_no_hay_tiempo():
    from alpha_football import contraofertas as CO
    e, _ = _en_el_ultimo_dia(); mi, comp = e['mi_equipo'], e['liga'].equipos[1]
    assert DF.analisis(e) == (True, 17) and DF.texto_respuesta(17) == "Te responden en 3 horas."
    assert DF.texto_respuesta(None) == "Te responden por correo en la próxima jornada."
    of = {'jugador': mi.jugadores[4], 'comprador': comp, 'monto': 900, 'tope': 1000}
    e['ofertas_recibidas'] = [of]
    res, msg = CO.contraofertar(e, of, 1001)
    assert res == 'analizando' and of['contra']['hora_resp'] == 17 and "3 horas" in msg
    DF.avanzar_hora(e, random.Random(2)); DF.avanzar_hora(e, random.Random(2))
    assert of['contra']['estado'] == 'analizando' and DF.horas(e) == 18               # todavía no es su hora
    n0 = len(C.bandeja(e))
    DF.avanzar_hora(e, random.Random(2))                                              # la tercera hora: responde
    assert len(C.bandeja(e)) > n0 and of not in e['ofertas_recibidas']                # acepta (vende) o se retira
    DF._bloque(e)['horas'] = 2                                                        # menos de 3 horas
    of2 = {'jugador': mi.jugadores[5], 'comprador': comp, 'monto': 900, 'tope': 1000}
    e['ofertas_recibidas'] = [of2]
    res, msg = CO.contraofertar(e, of2, 1001)
    assert res == 'rechazada' and "no hay tiempo" in msg and e['ofertas_recibidas'] == []


def test_un_analisis_que_vence_justo_a_las_0_horas_se_responde_antes_de_cerrar():
    from alpha_football import negociacion as N
    from alpha_football.data.clasicos import es_clasico
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']
    club = next(x for x in liga.equipos[1:] if not es_clasico(x, mi))               # el clásico solo vende por la cláusula
    j = club.jugadores[0]
    DF._bloque(e)['horas'] = 3
    minimo = N.minimo_club(j, club)
    res, msg, _c = N.evaluar_compra(e, j, club, int(minimo * N.UMBRAL_ANALISIS) + 1)
    assert res == 'analiza' and "3 horas" in msg
    assert e['datos_carrera']['analisis_compras'][0]['hora_resp'] == 0
    DF.avanzar_hora(e, random.Random(1)); DF.avanzar_hora(e, random.Random(1)); DF.avanzar_hora(e, random.Random(1))
    assert DF.cerrado(e) and e['datos_carrera']['analisis_compras'] == []
    asuntos = [m['asunto'] for m in C.bandeja(e)]
    assert any("acepta tu oferta" in a or "rechaza tu oferta" in a for a in asuntos)  # respondió antes de cerrar
    assert not any("Se cayó el trato" in a for a in asuntos)
```

(En `test_analisis_con_horas_...` la respuesta es 50/50: si acepta, `vender` gasta 2 horas más; por eso solo se afirma lo que vale en los dos casos: la hora guardada, que antes de su hora sigue en análisis, que a la tercera hora llega un correo y la oferta sale de la lista, y que con menos de 3 horas no hay tiempo. La reentrada está cubierta por la guarda de `responder`.)

- [ ] **Step 2: Correr y ver que falla** (`no attribute 'vencido'`).

- [ ] **Step 3: `dia_final.py`** — agregar:

```python
def analisis(estado: dict) -> tuple:
    """(ok, hora_resp) de un 'lo analizamos' pedido ahora. Fuera del último día: (True, None), se responde al
    cerrar la jornada siguiente. El último día: con 3 horas o más responde cuando queden `horas - 3`
    (True, h); con menos, (False, None): "no hay tiempo"."""
    if not activo(estado):
        return True, None
    h = horas(estado)
    if h < HORAS_ANALISIS:
        return False, None
    return True, h - HORAS_ANALISIS


def texto_respuesta(hora: Optional[int], uno: bool = False) -> str:
    """'Te responden en 3 horas.' o 'Te responden por correo en la próxima jornada.' ('Te responde…' si `uno`)."""
    quien = "Te responde" if uno else "Te responden"
    return f"{quien} por correo en la próxima jornada." if hora is None else f"{quien} en {HORAS_ANALISIS} horas."


def vencido(estado: dict, item: dict) -> bool:
    """¿Ya toca responder este 'lo analizamos'? Con hora de respuesta (pedido el último día): cuando quedan esas
    horas o menos, o si el último día ya pasó. Sin ella, la regla de siempre: la jornada siguiente."""
    t = int(estado.get('temporada', 1) or 1)
    if int(item.get('temporada', t) or t) != t:
        return True
    hr = item.get('hora_resp')
    if hr is not None:
        return horas(estado) <= int(hr) if _bloque(estado) is not None else True
    return int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1) > int(item.get('jornada', 0) or 0)
```

- [ ] **Step 4: Las cinco creaciones.**

`alpha_football/contraofertas.py` (`contraofertar`), reemplazar:

```python
    if pedido <= int(tope * MARGEN_ANALISIS):
        of['contra'] = {'pedido': pedido, 'estado': 'analizando', 'jornada': _jornada(estado)}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
```

por:

```python
    if pedido <= int(tope * MARGEN_ANALISIS):
        from alpha_football import dia_final as DF      # v0.4.14.0: el último día responde a las 3 horas
        ok, hora = DF.analisis(estado)
        if not ok:
            retirar(estado, of)
            return 'rechazada', f"{comp}: no hay tiempo para analizarlo hoy y retira la oferta."
        of['contra'] = {'pedido': pedido, 'estado': 'analizando', 'jornada': _jornada(estado)}
        if hora is not None:
            of['contra']['hora_resp'] = hora
        return 'analizando', f"{comp}: \"Lo analizamos\". {DF.texto_respuesta(hora)}"
```

`alpha_football/negociacion.py` (`evaluar_compra`), reemplazar:

```python
    if monto >= int(minimo * UMBRAL_ANALISIS):
        dc = estado.setdefault('datos_carrera', {})
```

por:

```python
    if monto >= int(minimo * UMBRAL_ANALISIS):
        from alpha_football import dia_final as DF      # v0.4.14.0
        ok, hora = DF.analisis(estado)
        if not ok:
            return 'rechaza', f"{club.nombre}: no hay tiempo para analizarlo hoy.", minimo
        dc = estado.setdefault('datos_carrera', {})
```

y reemplazar:

```python
        dc['analisis_compras'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada.", 0
```

por:

```python
        if hora is not None:
            pend[-1]['hora_resp'] = hora
        dc['analisis_compras'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". {DF.texto_respuesta(hora)}", 0
```

`alpha_football/negociacion.py` (`analizar_contrato`), reemplazar:

```python
    club = neg.get('club')
    dc = estado.setdefault('datos_carrera', {})
    pend = [a for a in dc.get('analisis_contratos', []) if a.get('jugador_id') != j.id]
```

por:

```python
    from alpha_football import dia_final as DF          # v0.4.14.0: sin 3 horas no hay análisis (rechazo normal)
    ok, hora = DF.analisis(estado)
    if not ok:
        return None
    club = neg.get('club')
    dc = estado.setdefault('datos_carrera', {})
    pend = [a for a in dc.get('analisis_contratos', []) if a.get('jugador_id') != j.id]
```

y reemplazar:

```python
    dc['analisis_contratos'] = pend
    return f"{j.nombre_completo}: \"Lo analizo\". Te responde por correo en la próxima jornada."
```

por:

```python
    if hora is not None:
        pend[-1]['hora_resp'] = hora
    dc['analisis_contratos'] = pend
    return f"{j.nombre_completo}: \"Lo analizo\". {DF.texto_respuesta(hora, uno=True)}"
```

`alpha_football/prestamos.py` (`evaluar_pedido`), reemplazar:

```python
        t, jor, _n = _momento(estado)
        # un solo análisis por jugador: el nuevo pedido reemplaza al anterior
```

por:

```python
        from alpha_football import dia_final as DF      # v0.4.14.0
        ok, hora = DF.analisis(estado)
        if not ok:
            return 'rechaza', f"{club.nombre}: no hay tiempo para analizarlo hoy."
        t, jor, _n = _momento(estado)
        # un solo análisis por jugador: el nuevo pedido reemplaza al anterior
```

y reemplazar:

```python
        _dc(estado)['analisis_prestamos'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
```

por:

```python
        if hora is not None:
            pend[-1]['hora_resp'] = hora
        _dc(estado)['analisis_prestamos'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". {DF.texto_respuesta(hora)}"
```

`alpha_football/prestamos.py` (`contraofertar`), reemplazar:

```python
        _t, jor, _n = _momento(estado)
        of['contra'] = {'pedido': pct_pedido, 'estado': 'analizando', 'jornada': jor}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
```

por:

```python
        from alpha_football import dia_final as DF      # v0.4.14.0
        ok, hora = DF.analisis(estado)
        if not ok:
            estado['ofertas_recibidas'] = [o for o in estado.get('ofertas_recibidas') or [] if o is not of]
            return 'rechazada', f"{comp}: no hay tiempo para analizarlo hoy y retira la oferta."
        _t, jor, _n = _momento(estado)
        of['contra'] = {'pedido': pct_pedido, 'estado': 'analizando', 'jornada': jor}
        if hora is not None:
            of['contra']['hora_resp'] = hora
        return 'analizando', f"{comp}: \"Lo analizamos\". {DF.texto_respuesta(hora)}"
```

- [ ] **Step 5: Los cinco predicados** — cada resolución usa `vencido`.

`alpha_football/contraofertas.py`: en `_resolver_ventas`, agregar `from alpha_football import dia_final as DF` junto a los imports de la función y reemplazar `if c.get('estado') != 'analizando' or _jornada(estado) <= int(c.get('jornada', 0)):` por `if c.get('estado') != 'analizando' or not DF.vencido(estado, c):`. En `_resolver_compras`: agregar el import y reemplazar `if _jornada(estado) <= int(a.get('jornada', 0)):` por `if not DF.vencido(estado, a):`. En `_resolver_contratos`: agregar el import y reemplazar `if int(a.get('temporada', temporada)) == temporada and _jornada(estado) <= int(a.get('jornada', 0)):` por `if not DF.vencido(estado, a):`.

`alpha_football/prestamos.py`: en `resolver_analisis`, agregar `from alpha_football import dia_final as DF` al inicio y reemplazar `if int(a.get('temporada', t)) == t and jor <= int(a.get('jornada', 0)):` por `if not DF.vencido(estado, a):`. En `_resolver_contras`, agregar el import y reemplazar `if not of.get('prestamo') or c.get('estado') != 'analizando' or jor <= int(c.get('jornada', 0)):` por `if not of.get('prestamo') or c.get('estado') != 'analizando' or not DF.vencido(estado, c):`.

- [ ] **Step 6: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: `15/15 tests pasaron`.
Run (uno por uno): `test_contraofertas*.py` (`ls tests | grep -i contra`), `test_negociaciones_v270.py`, `test_prestamos_pedir.py`, `test_prestamos_pulido.py`.
Expected: `N/N tests pasaron` (fuera del último día `vencido` es la regla de siempre; un análisis de otra temporada ahora también se responde).

---

### Task 5: El panel del día, la franja y el cartel

**Files:**
- Modify: `alpha_football/dia_final.py`, `alpha_football/dias.py`, `alpha_football/ui/aviso_mercado.py`, `alpha_football/ui/league_screen.py`, `alpha_football/ui/ayuda.py`, `alpha_football/ui/atajos.py`
- Test: `tests/test_dia_final.py`

**Interfaces:**
- Consumes: `dia_final.activo/horas/avanzar_hora/cerrar` (Tasks 1 y 2), `dias.textos_hub` (G1/G2), `aviso_mercado._abrir/_texto_franja` (G2), `league_screen._accion_jugar/_render_inicio` (G1).
- Produces: `dia_final.textos(estado) -> (l1, l2, l3)` (`"ÚLTIMO DÍA"`), `texto_hora(r) -> str`; `league_screen.R_HORA`, `R_CERRAR`, `_avanzar_hora(estado)`, `_pedir_cierre(estado)` (pide confirmación; tecla `C`); franja "ÚLTIMO DÍA · quedan N h"; cartel `'ultimo'` ("tienes 20 horas") y `'cierra'`.

- [ ] **Step 1: Tests** — agregar:

```python
def _hub_ultimo(e):
    from alpha_football.ui import league_screen as L
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-08-31']          # sin el cartel de inicio del día
    return L


def test_el_hub_muestra_el_panel_del_dia_y_avanza_horas_con_enter_y_clic():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    l1, l2, l3, hab = L._textos_jugar(e['liga'], e['mi_equipo'], info, e)
    assert l1 == "ÚLTIMO DÍA" and "quedan 20 h" in l2 and l3 == "" and hab
    pygame.event.clear(); assert L.render(screen, e) is None
    key(pygame.K_RETURN); assert L.render(screen, e) is None
    assert DF.horas(e) == 19 and e['hub_toast'][0].startswith("Pasó 1 hora")
    assert L.R_JUGAR.contains(L.R_HORA) and L.R_JUGAR.contains(L.R_CERRAR) and not L.R_HORA.colliderect(L.R_CERRAR)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_HORA.center, button=1))
    assert L.render(screen, e) is None and DF.horas(e) == 18
    key(pygame.K_d); L.render(screen, e); assert D.hoy(e) == date(2026, 8, 31) and DF.horas(e) == 18   # D no pasa el día


def test_cerrar_el_mercado_pide_confirmacion_y_despues_el_dia_sigue():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    pygame.event.clear(); L.render(screen, e)
    key(pygame.K_c); L.render(screen, e)
    assert e.get('confirmar_cierre_mercado') and DF.horas(e) == 20          # primera vez: solo pregunta
    key(pygame.K_RETURN); L.render(screen, e)                               # Enter confirma
    assert DF.cerrado(e) and not e.get('confirmar_cierre_mercado') and not T.ventana_abierta(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"


def test_la_franja_el_cartel_y_los_textos_del_ultimo_dia():
    from alpha_football.ui import aviso_mercado as AM
    e, _ = _en_el_ultimo_dia()
    assert AM._texto_franja(e) == ("ÚLTIMO DÍA · quedan 20 h", 'dorado')
    assert AM._texto_franja(e, True) == ("ÚLTIMO DÍA · 20 h", 'dorado')
    assert AM.evento_pendiente(e) == ('ultimo', '2026-08-31')
    AM._abrir(e, 'ultimo', '2026-08-31')
    assert e['aviso_mercado_activo']['tipo'] == 'ultimo' and AM.evento_pendiente(e) is None
    asunto = [m for m in C.bandeja(e) if m['asunto'] == "Último día de fichajes"]
    assert asunto and "20 horas" in asunto[0]['cuerpo']
    DF.cerrar(e)
    assert AM._texto_franja(e) is None and DF.texto_hora({'horas': 1, 'correos': 1, 'ofertas': 1}) == "Pasó 1 hora: 1 oferta, 1 correo"
    assert DF.texto_hora({'horas': 1, 'cerro': True}) == "Pasó 1 hora: se cerró el mercado"
```

- [ ] **Step 2: Correr y ver que falla.**

- [ ] **Step 3: `dia_final.py`** — agregar los textos:

```python
def textos(estado: dict) -> tuple:
    """(línea 1, línea 2, línea 3) del botón grande del hub durante el último día."""
    from alpha_football import temporada as T
    return ("ÚLTIMO DÍA", f"{CAL.texto_fecha(T.fecha(estado))} · quedan {horas(estado)} h", "")   # la 3ª línea la ocupan los botones


def texto_hora(r: dict) -> str:
    """'Pasó 1 hora: 1 oferta, 1 correo' / 'Pasó 1 hora: se cerró el mercado'."""
    partes = []
    if int(r.get('ofertas', 0) or 0):
        partes.append(f"{int(r['ofertas'])} oferta{'s' if int(r['ofertas']) != 1 else ''}")
    if int(r.get('correos', 0) or 0):
        partes.append(f"{int(r['correos'])} correo{'s' if int(r['correos']) != 1 else ''}")
    if r.get('cerro'):
        partes.append("se cerró el mercado")
    return "Pasó 1 hora" + (f": {', '.join(partes)}" if partes else "")
```

- [ ] **Step 4: `dias.py`** — en `textos_hub`, antes de `if not es_dia_de_continuar(estado): return None`:

```python
    from alpha_football import dia_final as DF          # v0.4.14.0: el último día, el panel de las horas
    if DF.activo(estado):
        return DF.textos(estado)
```

- [ ] **Step 5: `aviso_mercado.py`** — cuatro cambios.

(a) `_texto_franja`: justo después de `if _liga(estado) is None: return None` y el import de `temporada`:

```python
    from alpha_football import dia_final as DF          # v0.4.14.0
    if DF.activo(estado):
        h = DF.horas(estado)
        return (f"ÚLTIMO DÍA · {h} h" if corto else f"ÚLTIMO DÍA · quedan {h} h"), 'dorado'
```

(b) `_abrir`: el foco y el correo del tipo `'ultimo'`. Reemplazar la línea `estado['aviso_mercado_activo'] = {'tipo': tipo, 'fecha': fecha, 'foco': 0 if tipo == 'abre' else 1}` por `... 'foco': 0 if tipo in ('abre', 'ultimo') else 1}` y, en el `try` del correo, reemplazar `        else:\n            C.enviar(estado, 'club', "Se cerró el mercado de pases",` por:

```python
        elif tipo == 'ultimo':
            C.enviar(estado, 'club', "Último día de fichajes",
                     "Hoy cierra el mercado: tienes 20 horas para concretar tus operaciones. Cada fichaje cuesta "
                     "3 horas y cada venta 2; \"lo analizamos\" responde a las 3 horas. Lo que no llegue a "
                     "inscribirse queda acordado para la próxima ventana.",
                     C.accion('negociaciones', "IR A NEGOCIACIONES"))
        else:
            C.enviar(estado, 'club', "Se cerró el mercado de pases",
```

(c) `dibujar`: reemplazar las líneas del título y el color:

```python
        abre = act.get('tipo') == 'abre'
        color = COLORS.get('verde' if abre else 'rojo', (0, 255, 136))
```

por:

```python
        tipo_c = act.get('tipo')
        abre = tipo_c in ('abre', 'ultimo')
        color = COLORS.get({'abre': 'verde', 'ultimo': 'dorado'}.get(tipo_c, 'rojo'), (0, 255, 136))
```

y `s = get_font('xl').render("MERCADO ABIERTO" if abre else "MERCADO CERRADO", True, color)` por `s = get_font('xl').render({'abre': "MERCADO ABIERTO", 'ultimo': "ÚLTIMO DÍA DE FICHAJES"}.get(tipo_c, "MERCADO CERRADO"), True, color)`, y la línea de texto (la de G2):

```python
        if abre:
            linea = f"Hasta el {_hasta(estado)}: fichajes, ofertas y cláusulas."
        else:
            linea = _reabre(estado)
```

por:

```python
        if tipo_c == 'ultimo':
            from alpha_football import dia_final as _DF
            linea = f"Tienes {_DF.horas(estado) or _DF.HORAS_DIA} horas: fichajes 3 h, ventas 2 h."
        elif abre:
            linea = f"Hasta el {_hasta(estado)}: fichajes, ofertas y cláusulas."
        else:
            linea = _reabre(estado)
```

(d) `evento_pendiente` no cambia: `hito_del_dia` ya devuelve `'ultimo'` (Task 1) y el cierre no genera cartel por fecha.

- [ ] **Step 6: `league_screen.py`** — siete cambios.

(a) Junto a `R_DIA`:

```python
R_HORA = pygame.Rect(R_JUGAR.x + 20, R_JUGAR.bottom - 32, 200, 26)        # v0.4.14.0: AVANZAR 1 HORA (último día)
R_CERRAR = pygame.Rect(R_JUGAR.x + 232, R_JUGAR.bottom - 32, 200, 26)     # v0.4.14.0: CERRAR MERCADO
```

(b) Antes de `_accion_jugar`, agregar:

```python
def _avanzar_hora(estado) -> None:
    """v0.4.14.0: AVANZAR 1 HORA el último día. Cancela una confirmación de cierre pendiente."""
    try:
        from alpha_football import dia_final as _DF
        estado.pop('confirmar_cierre_mercado', None)
        if _DF.activo(estado):
            _toast(estado, _DF.texto_hora(_DF.avanzar_hora(estado)), color='azul')
    except Exception as e_df:
        logger.error(f"Error al avanzar una hora: {e_df}")


def _pedir_cierre(estado) -> None:
    """v0.4.14.0: CERRAR MERCADO: la primera vez pide confirmación; la segunda (Enter, C o clic) cierra."""
    try:
        from alpha_football import dia_final as _DF
        if not _DF.activo(estado):
            return
        if estado.get('confirmar_cierre_mercado'):
            estado.pop('confirmar_cierre_mercado', None)
            _DF.cerrar(estado)
            _toast(estado, "Mercado cerrado", color='rojo')
        else:
            estado['confirmar_cierre_mercado'] = True
    except Exception as e_df:
        logger.error(f"Error al cerrar el mercado: {e_df}")
```

(c) En `_accion_jugar`, antes del bloque de CONTINUAR (G1), agregar:

```python
    try:   # v0.4.14.0: el último día, JUGAR avanza una hora (o confirma el cierre si estaba pedido)
        from alpha_football import dia_final as _DF
        if _DF.activo(estado):
            if estado.get('confirmar_cierre_mercado'):
                _pedir_cierre(estado)
            else:
                _avanzar_hora(estado)
            return None
    except Exception as e_df:
        logger.error(f"Error en el último día: {e_df}")
```

(d) En el bloque que dibuja JUGAR, después del `if l1 == "CONTINUAR": ...` (botón +1 DÍA) agregar:

```python
        if l1 == "ÚLTIMO DÍA":      # v0.4.14.0: AVANZAR 1 HORA y CERRAR MERCADO
            for _rb, _tb in ((R_HORA, "AVANZAR 1 HORA"),
                             (R_CERRAR, "¿CERRAR? ENTER" if estado.get('confirmar_cierre_mercado') else "CERRAR MERCADO")):
                pygame.draw.rect(screen, (30, 45, 75) if _rb.collidepoint(mouse_pos) else (15, 22, 40), _rb, border_radius=6)
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), _rb, width=1, border_radius=6)
                _sb = get_font('sm').render(_tb, True, (255, 255, 255))
                screen.blit(_sb, _sb.get_rect(center=_rb.center))
```

y en la línea de la fecha de arriba a la derecha: para `l1 == "ÚLTIMO DÍA"` no se dibuja (la línea 2 ya lleva la fecha): en el bloque de `_txt_fecha` (G2) el `else` ya queda vacío si `l1 != "JUGAR"`.

(e) En los clics de `_render_inicio`, antes de `elif l1 == "CONTINUAR" and R_DIA.collidepoint(click_pos):`:

```python
        elif l1 == "ÚLTIMO DÍA" and R_HORA.collidepoint(click_pos):      # v0.4.14.0
            estado['hub_foco'] = 0
            _avanzar_hora(estado)
        elif l1 == "ÚLTIMO DÍA" and R_CERRAR.collidepoint(click_pos):
            estado['hub_foco'] = 0
            _pedir_cierre(estado)
```

(f) En el teclado de `render`, después del bloque de `K_d`:

```python
            if ev.key == pygame.K_c and tab == 'inicio':     # v0.4.14.0: CERRAR MERCADO
                _pedir_cierre(estado)
                continue
```

(g) En `render`, después del bloque que crea el reloj (G1):

```python
        try:  # v0.4.14.0: un save cargado un día de cierre con el mercado abierto arranca con 20 horas
            from alpha_football import dia_final as _DF_r
            _DF_r.abrir(estado)
        except Exception as e_df:
            logger.error(f"Error abriendo el último día: {e_df}")
```

- [ ] **Step 7: Ayuda y atajos.** `alpha_football/ui/atajos.py`: en `ATAJOS['league_screen']` reemplazar `D +1 Día · ` por `D +1 Día · C Cerrar mercado · ` si cabe en la barra (si `test_ux_v360` mide el ancho y no entra, dejar solo `D +1 Día` y poner el atajo `C` en la ayuda). `alpha_football/ui/ayuda.py`: en `_ayuda_hub`, después del ítem `+1 DÍA`, agregar `(L.R_HORA, "AVANZAR 1 HORA", "Solo el último día de fichajes: pasa una hora (Enter). Fichaje 3 h, venta 2 h.")` y `(L.R_CERRAR, "CERRAR MERCADO", "Cierra el mercado antes de las 0 horas (tecla C); pide confirmación.")` (≤110 caracteres cada texto).

- [ ] **Step 8: Correr**

Run: `PYTHONIOENCODING=utf-8 python tests/test_dia_final.py`
Expected: `18/18 tests pasaron`.
Run (uno por uno): `test_ayuda_v390.py`, `test_ux_v360.py`, `test_teclado_v420.py`.
Expected: `N/N tests pasaron`. Si `test_ayuda_v390.test_items_validos` revisa solapamientos o cobertura de rects del hub, agregar lo que pida siguiendo lo que ya hay para `R_DIA`.

---

### Task 6: Tests viejos, suite completa y cierre de G3

**Files:**
- Modify: los tests de G1/G2 que esperaban el hito `'cierra'` o pasaban el 31 sin cerrar el mercado
- Modify: `context.md`

- [ ] **Step 1: Ajustar los tests de G2 que cambian** (`tests/test_temporada.py`):
  - `test_ventana_actual_cierres_y_proxima_apertura`: reemplazar `assert T.siguiente_ventana(e) == (1, 'invierno') and T.hito_del_dia(e, date(2026, 9, 1)) == 'cierra'` por `assert T.siguiente_ventana(e) == (1, 'invierno') and T.hito_del_dia(e, date(2026, 9, 1)) is None and T.hito_del_dia(e, date(2026, 8, 31)) == 'ultimo'`.
  - `test_continuar_se_detiene_al_abrir_y_al_cerrar_el_mercado`: ahora `continuar` desde el 30 de agosto se detiene el 31 con el hito `'ultimo'` y el día no pasa; reemplazar el cuerpo después de `cal['dia'] = '2026-08-30'` por:

    ```python
    r = D.continuar(e)
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'
    assert D.texto_resumen(r) == "Pasó 1 día: último día de fichajes"
    assert D.continuar(e)['dias'] == 0                                     # con horas, el día no pasa
    cal['dia'] = '2026-06-30'                                              # (antes del inicio: abre el 1 de julio)
    assert D.avanzar_dia(e)['hito'] == 'abre'
    ```
  - `test_el_cartel_sale_el_dia_que_abre_y_el_dia_despues_de_cerrar` → renombrar a `..._abre_y_el_ultimo_dia` y reemplazar la parte final (`cal['dia'] = '2026-09-01'` …) por `cal['dia'] = '2026-08-31'; assert AM.evento_pendiente(e) == ('ultimo', '2026-08-31'); cal['dia'] = '2026-09-01'; assert AM.evento_pendiente(e) is None`.
  - `test_la_franja_y_la_cabecera_cuentan_dias`: el 31 de agosto, sin abrir el día, la franja sigue diciendo `("MERCADO ABIERTO · ÚLTIMO DÍA", 'dorado')` (no hay horas todavía); sin cambio.
  - Los tests de G1/G2 que atraviesan el 31 con `D.hasta_el_partido` siguen bien (se cierra solo); los que usan `D.continuar(e)` con `parar=True` por el 31 ahora se detienen: usar `hasta_el_partido` o cerrar con `DF.cerrar(e)`.

- [ ] **Step 2: Correr uno por uno** los tests de mercado, negociación, préstamos, hub y teclado: `test_ventana_traspaso.py`, `test_mercado_v350.py`, `test_mercado_v440.py`, `test_negociaciones_v270.py`, `test_prestamos*.py`, `test_ofertas*.py`, `test_hub_v240.py`, `test_teclado_v420.py`, `test_ux_v360.py`, `test_ayuda_v390.py`, `test_dias.py`, `test_temporada.py`, `test_calendario.py`. Ajustar sin debilitar: un test que da por hecho que se puede operar el 31 sin horas o sin cerrar el mercado se ajusta con `DF.abrir`/`DF.cerrar` o moviendo el reloj; uno que falla por otra razón es un bug del cambio: buscar la causa raíz.

- [ ] **Step 3: Suite completa, una sola vez y un archivo a la vez**, en segundo plano (no con `nohup`):

```bash
cd "C:/Users/diego/Downloads/AlphaFootball" && mkdir -p "$TEMP/af_suite_g3" && : > "$TEMP/af_suite_g3/resumen.txt" && for f in tests/test_*.py; do
  b=$(basename "$f" .py); PYTHONIOENCODING=utf-8 timeout 1200 python "$f" > "$TEMP/af_suite_g3/$b.log" 2>&1; rc=$?
  echo "$b rc=$rc FAIL=$(grep -c 'FAIL' "$TEMP/af_suite_g3/$b.log") · $(tail -1 "$TEMP/af_suite_g3/$b.log" | cut -c1-80)" >> "$TEMP/af_suite_g3/resumen.txt"
done; echo TERMINADO >> "$TEMP/af_suite_g3/resumen.txt"
```

Expected: cada línea con `rc=0` y `FAIL=0`. `test_motor_v400` mide tiempos y puede fallar una vez por carga: repetirlo solo antes de investigar.

- [ ] **Step 4: Comprobación sin pantalla** — con `SDL_VIDEODRIVER=dummy` y un estado de carrera con el calendario armado (`tests/test_calendario._e()`): jugar J1 y J2, llevar el reloj con `D.continuar` hasta el 31 de agosto (debe detenerse con el cartel ÚLTIMO DÍA y 20 horas), renderizar el hub (panel con AVANZAR 1 HORA y CERRAR MERCADO), fichar a alguien (3 horas), pedir un "lo analizamos", avanzar horas hasta su respuesta, cerrar con CERRAR MERCADO (confirmando) y ver el cartel MERCADO CERRADO y la ronda de la IA; confirmar que `+1 DÍA` y `CONTINUAR` antes del cierre no pasan el día, que después sí, y que no hay excepciones ni líneas `ERROR` en el log. Repetir el 31 de enero y con `estado_carrera('betplay')` (cierres el 31 de enero y el 31 de agosto). Guardar capturas del hub el último día con `pygame.image.save` y mirarlas.

- [ ] **Step 5: `context.md`** — agregar la bitácora "2026-10-07 — Último día de fichajes: las 20 horas (v0.4.14.0, sub-proyecto G3, sin commit)" con: `dia_final.py` y sus funciones, dónde vive el estado (`datos_carrera['calendario']['dia_final']`), la tabla de costos, `traspasos_pendientes.puede_concretar` como única puerta, el predicado `vencido` y `hora_resp` de "lo analizamos", el cierre (retira ofertas, cae análisis con correo, ronda de la IA, cartel), el panel del hub y la tecla `C`, las cuatro desviaciones del spec y los tests viejos ajustados. Actualizar la fecha del encabezado y dejar como pendientes: E (auto-actualización), F (temporadas por continente), el bump de versión (título y badge siguen en 0.4.10.0) y la prueba a mano: el cartel de ÚLTIMO DÍA, AVANZAR 1 HORA, un fichaje de 3 horas, uno que no alcanza y queda acordado, "lo analizamos" respondiendo a las 3 horas, CERRAR MERCADO con confirmación, el cierre a las 0 horas y que `+1 DÍA` y `CONTINUAR` no saltan el 31.
