# Carrera del DT (7a · 7c · 7b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Contrato del DT estilo FIFA con patrimonio, correo de rendimiento + veredicto al cierre, espaldarazo, objetivo internacional (7a); 9 estilos de juego con matriz (7c); DTs parodia en cada club, despidos entre la IA y ofertas de banquillo para el user (7b).

**Architecture:** Lógica en módulos puros testeables (`carrera_dt.py`, `estilos.py`, `entrenadores.py`) + cambios acotados en `directiva.py`; estado persistente en `estado['datos_carrera']` (ya se guarda con la partida). Pantallas Pygame nuevas siguiendo el patrón de `ui/despido_screen.py` (bloque theme con fallback, `render(screen, estado) -> Optional[str]`), registradas en `main.py:PANTALLAS`.

**Tech Stack:** Python 3.10+, Pygame. Tests = scripts con runner propio (`python tests/test_x.py`, `SDL_VIDEODRIVER=dummy`), mismo formato que `tests/test_directiva_v280.py`.

**Spec:** `docs/superpowers/specs/2026-09-23-carrera-dt-design.md`

## Global Constraints

- Idioma: textos de UI, comentarios y docstrings en español; comentarios de versión con el formato `# v3.2.0: ...` (7a), `# v3.3.0: ...` (7c), `# v3.4.0: ...` (7b).
- Resiliencia: todo hook nuevo dentro de `try/except Exception as e: logger.error(...)` como el código vecino; una pantalla nunca debe tirar el juego.
- **NO hacer commits** (Diego prueba todo al final y aprueba el commit). Los pasos "Commit" de este plan se reemplazan por "correr la suite".
- Pantalla 1280×720; fuentes/colores solo vía `alpha_football.ui.theme` (`draw_text(..., size='sm'|'md'|'lg'|'xl', color=<clave de COLORS>)`).
- Constantes del spec (copiar tal cual): sueldo base = max($100K, 4% del balance) × (0.8 + calif/250); variantes 1 año ×1.25 · 2 años ×1.0 · 3 años ×0.85; renovación ×1.10; renovar si calif ≥ 60; indemnización 50% × sueldo × temporadas que faltaban; espaldarazo +15/+30/+50% ↔ meta −1/−2/−3 puestos, negado si calif < 40, una vez por temporada, solo hasta la mitad de la liga; objetivo de copa ±: superado +6 / cumplido +3 / fallado −4; Kloppismo gasta energía ×1.3; bono de estilo +15% / −13%; despido IA 8% por jornada (tras 1/3 de liga, 3+ puestos bajo lo esperado y en la mitad de abajo, máx. 1 por liga por temporada), al cierre 50%; calif DT IA inicial = 50 + (estrellas − 3)·10; despedido a libres con calif −10; oferta al user 60%, dura 3 jornadas; banda: calif ≥ 70 → OVR ≤ tuyo + 10, ≥ 55 → + 5, si no ≤ tuyo.
- Suite completa tras cada tarea: `for f in tests/test_*.py; do SDL_VIDEODRIVER=dummy python "$f" || echo "FALLA $f"; done` (Git Bash, desde la raíz). Debe quedar todo en verde.

## Review Focus

- Save viejo (sin `contrato_dt`, sin `dts`, estilos viejos del editor) → carga sin error, recibe contrato de 2 años y DTs automáticamente. Test en Task 1 (`test_asegurar_contrato_save_viejo`), Task 4 (`test_normalizar_estilo`) y Task 5 (`test_asegurar_dts_idempotente`).
- Despido a mitad de temporada por quiebra (finanzas) → indemnización calculada sin romper aunque no haya objetivo. Test en Task 2 (`test_marcar_despido_indemniza`).
- Club con balance negativo o 0 → sueldo mínimo $100K, nunca negativo. Test en Task 1 (`test_ofertas_balance_negativo`).
- Espaldarazo con meta ya en puesto 1 o 2 → opciones que dejarían la meta < 1 no se ofrecen. Test en Task 2 (`test_espaldarazo_no_baja_de_1`).
- Aceptar oferta de banquillo con la copa en curso / tras rechazar → el club viejo y el nuevo quedan con un DT de la IA consistente (nunca dos DTs, tu club sin DT IA). Test en Task 6 (`test_aceptar_oferta_consistencia`).

---

## Orden y reparto (máx. 3 subagentes)

- **Subagente A:** Tasks 1-3 (7a). **Subagente B:** Task 4 (7c). A y B corren en paralelo (tocan archivos distintos; los dos solo comparten `match_screen.py` en zonas separadas: A en `finalizar_jornada_liga`, B en `_TACTICAS_MENU`).
- **Subagente C:** Tasks 5-6 (7b), cuando A y B terminen.
- Revisión: la hace el controlador (sesión principal) tras cada subagente.

---

### Task 1: `carrera_dt.py` — contrato, patrimonio, renovación (7a, lógica)

**Files:**
- Create: `alpha_football/carrera_dt.py`
- Test: `tests/test_carrera_dt_v320.py`

**Interfaces:**
- Consumes: `directiva.calif_dt(estado) -> int`, `correo.enviar(estado, remitente, asunto, cuerpo, accion)`, `correo.accion(pantalla, texto)`.
- Produces:
  - `ofertas_contrato(estado, equipo, renovacion: bool = False) -> list[dict]` (`[{'anios': 1|2|3, 'sueldo': int}]`)
  - `firmar(estado, equipo, oferta: dict, renovacion: bool = False) -> dict` (contrato)
  - `contrato(estado) -> Optional[dict]`, `patrimonio(estado) -> int`
  - `pagar_jornada(estado) -> int`
  - `indemnizacion(estado, temporada_fin: int) -> int`, `cobrar_indemnizacion(estado, temporada_fin: int) -> int`
  - `revisar_renovacion(estado) -> None`, `rechazar_renovacion(estado) -> None`
  - `contrato_vencido(estado, temporada_fin: int) -> bool`
  - `asegurar_contrato(estado) -> None`

- [ ] **Step 1: Write the failing tests** — `tests/test_carrera_dt_v320.py` (cabecera idéntica a `tests/test_directiva_v280.py` líneas 1-31: imports, `estado_carrera`, `click`; añade `from alpha_football import carrera_dt as CD, correo as C`).

```python
def test_ofertas_contrato_variantes():
    e = estado_carrera()
    mi = e['mi_equipo']; mi.balance = 50_000_000
    of = CD.ofertas_contrato(e, mi)                     # calif inicial 50 → ×1.0
    assert [o['anios'] for o in of] == [1, 2, 3]
    assert of[1]['sueldo'] == 2_000_000                 # 4% de 50M
    assert of[0]['sueldo'] == 2_500_000 and of[2]['sueldo'] == 1_700_000
    ren = CD.ofertas_contrato(e, mi, renovacion=True)
    assert ren[1]['sueldo'] == 2_200_000


def test_ofertas_balance_negativo():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -5_000_000
    assert CD.ofertas_contrato(e, mi)[1]['sueldo'] == 100_000


def test_firmar_y_pagar():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 50_000_000
    c = CD.firmar(e, mi, {'anios': 2, 'sueldo': 1_400_000})
    assert c == {'club': mi.nombre, 'sueldo': 1_400_000, 'desde': 1, 'hasta': 2}
    n = e['liga'].num_jornadas
    assert CD.pagar_jornada(e) == 1_400_000 // n
    assert CD.patrimonio(e) == 1_400_000 // n


def test_indemnizacion():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 3, 'sueldo': 1_000_000})      # hasta T3
    assert CD.indemnizacion(e, 1) == 1_000_000             # faltan 2 → 50% × 2
    assert CD.indemnizacion(e, 3) == 0
    assert CD.cobrar_indemnizacion(e, 2) == 500_000 and CD.patrimonio(e) == 500_000


def test_renovacion_segun_calif():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 1, 'sueldo': 1_000_000})      # vence esta temporada
    e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    e['datos_carrera']['calif_dt'] = 65
    CD.revisar_renovacion(e)
    assert e['datos_carrera']['renovacion_dt'] == {'temporada': 1, 'estado': 'ofrecida'}
    assert C.bandeja(e)[0]['accion']['pantalla'] == 'contrato_dt_screen'
    CD.revisar_renovacion(e)                                    # no repite
    assert sum(1 for m in C.bandeja(e) if 'renovación' in m['asunto'].lower()) == 1
    e2 = estado_carrera(); CD.firmar(e2, e2['mi_equipo'], {'anios': 1, 'sueldo': 1})
    e2['liga'].jornada_actual = e2['liga'].num_jornadas
    e2['datos_carrera']['calif_dt'] = 40
    CD.revisar_renovacion(e2)
    assert e2['datos_carrera']['renovacion_dt']['estado'] == 'negada'


def test_renovar_extiende_y_vencimiento():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 1, 'sueldo': 1_000_000})
    assert CD.contrato_vencido(e, 1)
    CD.firmar(e, mi, {'anios': 2, 'sueldo': 1_200_000}, renovacion=True)
    c = CD.contrato(e)
    assert (c['desde'], c['hasta'], c['sueldo']) == (1, 3, 1_200_000)
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'aceptada'
    assert not CD.contrato_vencido(e, 1)
    CD.rechazar_renovacion(e)
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'rechazada'


def test_asegurar_contrato_save_viejo():
    e = estado_carrera()
    CD.asegurar_contrato(e)
    c = CD.contrato(e)
    assert c['club'] == e['mi_equipo'].nombre and c['hasta'] - c['desde'] == 1
    e['datos_carrera']['contrato_dt']['club'] = 'Otro'          # club distinto → se rehace
    CD.asegurar_contrato(e)
    assert CD.contrato(e)['club'] == e['mi_equipo'].nombre


TESTS = [test_ofertas_contrato_variantes, test_ofertas_balance_negativo, test_firmar_y_pagar,
         test_indemnizacion, test_renovacion_segun_calif, test_renovar_extiende_y_vencimiento,
         test_asegurar_contrato_save_viejo]
```
(Termina con el mismo bloque `if __name__ == '__main__':` que `test_directiva_v280.py`.)

- [ ] **Step 2: Run to verify it fails**
Run: `SDL_VIDEODRIVER=dummy python tests/test_carrera_dt_v320.py` → Expected: `ModuleNotFoundError: alpha_football.carrera_dt`.

- [ ] **Step 3: Implement `alpha_football/carrera_dt.py`**

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Carrera del DT (v3.2.0)
Contrato del DT (sueldo, años), patrimonio personal (no toca la caja del club),
indemnización al ser despedido y oferta de renovación por correo a mitad de temporada.
Estado en datos_carrera: contrato_dt, patrimonio_dt, renovacion_dt.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUELDO_MIN = 100_000
SUELDO_PCT_BALANCE = 0.04
VARIANTES = [(1, 1.25), (2, 1.0), (3, 0.85)]     # (años, multiplicador del sueldo base)
BONO_RENOVACION = 1.10
CALIF_RENOVAR = 60
INDEMNIZACION_FRAC = 0.5


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _temporada(estado: dict) -> int:
    return int(estado.get('temporada', 1) or 1)


def contrato(estado: dict) -> Optional[dict]:
    c = _dc(estado).get('contrato_dt')
    return c if isinstance(c, dict) else None


def patrimonio(estado: dict) -> int:
    return int(_dc(estado).get('patrimonio_dt', 0) or 0)


def _sumar(estado: dict, monto: int) -> None:
    _dc(estado)['patrimonio_dt'] = patrimonio(estado) + max(0, int(monto))


def ofertas_contrato(estado: dict, equipo, renovacion: bool = False) -> list:
    """3 variantes {'anios', 'sueldo'}: más años = menos sueldo anual."""
    from alpha_football.directiva import calif_dt
    base = max(SUELDO_MIN, int(int(getattr(equipo, 'balance', 0) or 0) * SUELDO_PCT_BALANCE))
    base = base * (0.8 + calif_dt(estado) / 250)
    if renovacion:
        base *= BONO_RENOVACION
    return [{'anios': a, 'sueldo': int(round(base * m, -3))} for a, m in VARIANTES]


def firmar(estado: dict, equipo, oferta: dict, renovacion: bool = False) -> dict:
    """Firma el contrato. En renovación se suma a partir del vencimiento actual."""
    anios = max(1, int(oferta.get('anios', 1)))
    actual = contrato(estado)
    if renovacion and actual:
        desde, hasta = actual['desde'], int(actual['hasta']) + anios
        _dc(estado)['renovacion_dt'] = {'temporada': _temporada(estado), 'estado': 'aceptada'}
    else:
        desde = _temporada(estado)
        hasta = desde + anios - 1
        _dc(estado).pop('renovacion_dt', None)
    c = _dc(estado)['contrato_dt'] = {'club': getattr(equipo, 'nombre', '?'), 'sueldo': int(oferta['sueldo']),
                                      'desde': int(desde), 'hasta': int(hasta)}
    logger.info(f"Contrato DT firmado: {c}")
    return c


def pagar_jornada(estado: dict) -> int:
    """Una jornada de liga del user = sueldo / num_jornadas al patrimonio."""
    c = contrato(estado)
    if not c:
        return 0
    n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 10) or 10))
    monto = int(c['sueldo']) // n
    _sumar(estado, monto)
    return monto


def indemnizacion(estado: dict, temporada_fin: int) -> int:
    c = contrato(estado)
    if not c:
        return 0
    faltan = max(0, int(c['hasta']) - int(temporada_fin))
    return int(int(c['sueldo']) * faltan * INDEMNIZACION_FRAC)


def cobrar_indemnizacion(estado: dict, temporada_fin: int) -> int:
    monto = indemnizacion(estado, temporada_fin)
    _sumar(estado, monto)
    return monto


def revisar_renovacion(estado: dict) -> None:
    """A mitad de temporada, si el contrato vence esta temporada: oferta (calif ≥ 60) o negativa."""
    from alpha_football import correo as C
    from alpha_football.directiva import calif_dt
    liga, c, t = estado.get('liga'), contrato(estado), _temporada(estado)
    if liga is None or not c or int(c['hasta']) != t:
        return
    if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 10) or 10) // 2:
        return
    r = _dc(estado).get('renovacion_dt') or {}
    if r.get('temporada') == t:
        return
    if calif_dt(estado) >= CALIF_RENOVAR:
        _dc(estado)['renovacion_dt'] = {'temporada': t, 'estado': 'ofrecida'}
        C.enviar(estado, 'directiva', "Oferta de renovación de contrato",
                 "Estamos contentos con tu trabajo y queremos que sigas. Mira nuestra propuesta.",
                 C.accion('contrato_dt_screen', "VER OFERTA"))
    else:
        _dc(estado)['renovacion_dt'] = {'temporada': t, 'estado': 'negada'}
        C.enviar(estado, 'directiva', "No renovaremos tu contrato",
                 "Tu contrato vence al final de la temporada y la directiva no lo renovará.")


def rechazar_renovacion(estado: dict) -> None:
    _dc(estado)['renovacion_dt'] = {'temporada': _temporada(estado), 'estado': 'rechazada'}


def contrato_vencido(estado: dict, temporada_fin: int) -> bool:
    c = contrato(estado)
    return bool(c) and int(c['hasta']) <= int(temporada_fin)


def asegurar_contrato(estado: dict) -> None:
    """Saves viejos o club cambiado sin firmar: contrato de 2 años con la variante media."""
    mi = estado.get('mi_equipo')
    c = contrato(estado)
    if mi is None or (c and c.get('club') == getattr(mi, 'nombre', None)):
        return
    firmar(estado, mi, ofertas_contrato(estado, mi)[1])
```

- [ ] **Step 4: Run tests** → `SDL_VIDEODRIVER=dummy python tests/test_carrera_dt_v320.py` → Expected `7/7 tests pasaron`.
- [ ] **Step 5: Run full suite** (ver Global Constraints). Sin commit.

---

### Task 2: `directiva.py` — veredicto, correo de rendimiento, fin de contrato, espaldarazo, objetivo de copa (7a, lógica)

**Files:**
- Modify: `alpha_football/directiva.py` (`evaluar_temporada` 132-176, `marcar_despido` 179-190, `restaurar_despido` 193-207, `cambiar_de_club` 245-284; funciones nuevas al final)
- Modify: `alpha_football/finanzas.py:27` (`CLAVES_LIBRO` + `'directiva'`) y `alpha_football/ui/finanzas_screen.py:103,116` (línea "Directiva" en ingresos y en el neto)
- Test: `tests/test_carrera_dt_v320.py` (añadir)

**Interfaces:**
- Consumes: Task 1 (`carrera_dt.*`).
- Produces:
  - `evaluar_temporada(estado, posicion) -> dict` ahora con claves extra `'veredicto'` (`'felicitacion'|'neutro'|'regano'|'despido'|'fin_contrato'`), `'copa'` (dict o None), `'calif'`, `'confianza'`, `'indemnizacion'`; deja `estado['veredicto_pendiente'] = {'correo_id': int, 'tipo': str, 'info': dict}`.
  - `marcar_despido(estado, motivo, temporada_fin=None, indemnizar=True, titulo="¡DESPEDIDO!")`; `despido_pendiente` gana la clave `'titulo'`.
  - `FASES_COPA = ['Fase de grupos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']`
  - `definir_objetivo_copa(estado) -> Optional[dict]` (`{'temporada', 'fase', 'texto', 'ranking', 'n'}`; guarda `dc['objetivo_copa']`)
  - `evaluar_objetivo_copa(estado, temporada_fin) -> Optional[dict]` (`{'texto', 'fase', 'alcanzada', 'resultado'}`)
  - `ESPALDARAZO = [(0.15, 1), (0.30, 2), (0.50, 3)]`, `opciones_espaldarazo(estado) -> list[dict]` (`{'nivel', 'pct', 'puestos', 'monto', 'disponible': bool}`), `pedir_espaldarazo(estado, nivel: int) -> tuple[bool, str]`

- [ ] **Step 1: Write the failing tests** (añadir a `tests/test_carrera_dt_v320.py` y a `TESTS`; importar `from alpha_football import directiva as D`):

```python
def _con_objetivo(pos_max=5, balance=40_000_000):
    # BetPlay: 8 equipos, 14 jornadas (la Premier de prueba tiene solo 6 y el 5º-6º desciende)
    e = estado_carrera('betplay'); e['mi_equipo'].balance = balance
    D.definir_objetivo(e)
    e['datos_carrera']['objetivo']['pos_max'] = pos_max
    CD.firmar(e, e['mi_equipo'], {'anios': 3, 'sueldo': 1_000_000})
    return e


def test_veredictos():
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 2)['veredicto'] == 'felicitacion'
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 5)['veredicto'] == 'neutro'
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 6)['veredicto'] == 'regano'
    e = _con_objetivo(5); e['datos_carrera']['advertencia_dt'] = True
    ev = D.evaluar_temporada(e, 6)
    assert ev['veredicto'] == 'despido' and e['despido_pendiente']['titulo'] == "¡DESPEDIDO!"
    assert ev['indemnizacion'] == 1_000_000 and CD.patrimonio(e) == 1_000_000   # faltaban 2 temp.
    e = _con_objetivo(5); e['copa_mejor_fase_temp'] = 'Campeón'
    assert D.evaluar_temporada(e, 6)['veredicto'] == 'regano'      # fallar la liga pesa más


def test_correo_rendimiento_y_pendiente():
    e = _con_objetivo(5)
    ev = D.evaluar_temporada(e, 3)
    vp = e['veredicto_pendiente']
    assert vp['tipo'] == ev['veredicto'] and C.bandeja(e)[0]['id'] == vp['correo_id']
    assert C.bandeja(e)[0]['asunto'].startswith("Evaluación de la temporada")
    from alpha_football.ui.resumen_temporada_screen import siguiente_pantalla_tras_temporada
    assert siguiente_pantalla_tras_temporada(e) == 'veredicto_screen'


def test_fin_de_contrato():
    e = _con_objetivo(5)
    CD.firmar(e, e['mi_equipo'], {'anios': 1, 'sueldo': 1_000_000})
    ev = D.evaluar_temporada(e, 3)
    assert ev['veredicto'] == 'fin_contrato'
    assert e['despido_pendiente']['titulo'] == "FIN DE CONTRATO" and CD.patrimonio(e) == 0
    e['despido_pendiente'] = None
    assert D.restaurar_despido(e) and e['despido_pendiente']['titulo'] == "FIN DE CONTRATO"


def test_marcar_despido_indemniza():
    e = estado_carrera()                       # sin objetivo (quiebra a mitad de temporada)
    CD.firmar(e, e['mi_equipo'], {'anios': 2, 'sueldo': 800_000})
    D.marcar_despido(e, "Quiebra")
    assert CD.patrimonio(e) == 400_000


def test_espaldarazo():
    e = _con_objetivo(6, balance=40_000_000)
    ops = D.opciones_espaldarazo(e)
    assert [(o['pct'], o['puestos'], o['monto']) for o in ops] == [
        (0.15, 1, 6_000_000), (0.30, 2, 12_000_000), (0.50, 3, 20_000_000)]
    ok, _ = D.pedir_espaldarazo(e, 1)
    obj = e['datos_carrera']['objetivo']
    assert ok and obj['pos_max'] == 4 and obj['espaldarazo'] == {'pct': 0.30, 'puestos': 2}
    assert e['mi_equipo'].balance == 52_000_000
    assert "4" in obj['texto']
    ok2, msg = D.pedir_espaldarazo(e, 0)
    assert not ok2 and "temporada" in msg.lower()
    assert D.evaluar_temporada(e, 5)['resultado'] == 'fallado'           # meta más alta
    assert e['datos_carrera']['advertencia_dt']                           # conserva 2ª oportunidad


def test_espaldarazo_negado_y_limites():
    e = _con_objetivo(6); e['datos_carrera']['calif_dt'] = 39
    ok, msg = D.pedir_espaldarazo(e, 0)
    assert not ok and "calificación" in msg.lower()
    e = _con_objetivo(6); e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    assert not D.pedir_espaldarazo(e, 0)[0]


def test_espaldarazo_no_baja_de_1():
    e = _con_objetivo(2)
    disp = [o['disponible'] for o in D.opciones_espaldarazo(e)]
    assert disp == [True, False, False]
    assert not D.pedir_espaldarazo(e, 2)[0]


def test_objetivo_copa():
    e = _con_objetivo(5)
    e['copa_user_en_copa'] = False
    assert D.definir_objetivo_copa(e) is None
    e = _con_objetivo(5)
    e['copa_user_en_copa'] = True
    otros = [x for x in e['liga'].equipos if x is not e['mi_equipo']][:7]
    e['copa_equipos_obj'] = {x.nombre: x for x in otros + [e['mi_equipo']]}
    oc = D.definir_objetivo_copa(e)
    assert oc['fase'] in D.FASES_COPA[1:] and oc['n'] == 8
    e['copa_mejor_fase_temp'] = 'Campeón'
    calif_antes = D.calif_dt(e)
    ev = D.evaluar_objetivo_copa(e, 1)
    assert ev['resultado'] in ('superado', 'cumplido')
    assert D.calif_dt(e) - calif_antes in (6, 3)


def test_meta_copa_por_ranking():
    assert D.meta_copa(1, 8, ventaja=9) == 'Campeón'
    assert D.meta_copa(1, 8, ventaja=2) == 'Finalista'
    assert D.meta_copa(4, 8) == 'Semifinal'
    assert D.meta_copa(6, 8) == 'Cuartos'
    assert D.meta_copa(1, 1) == 'Cuartos'
```
Añadir a `TESTS`: `test_veredictos, test_correo_rendimiento_y_pendiente, test_fin_de_contrato, test_marcar_despido_indemniza, test_espaldarazo, test_espaldarazo_negado_y_limites, test_espaldarazo_no_baja_de_1, test_objetivo_copa, test_meta_copa_por_ranking`.

- [ ] **Step 2: Run to verify they fail** → `AttributeError` / `KeyError: 'veredicto'`.

- [ ] **Step 3: Implement.**

3a. `finanzas.py:27`: `CLAVES_LIBRO = ['taquilla', 'patrocinio', 'salarios', 'fichajes', 'ventas', 'premios', 'directiva']`. Verificar que `libro()` crea las claves con `setdefault` para saves viejos (si no, añadir `for k in CLAVES_LIBRO: d.setdefault(k, 0)`). En `finanzas_screen.py:103` añadir `("Directiva", lib['directiva'])` a la lista de ingresos y `'directiva'` a la tupla del neto de la línea 116 (usar `lib.get('directiva', 0)` / `ant.get(...)`).

3b. `directiva.py` — nuevas constantes y funciones (al final del archivo):

```python
# --- v3.2.0: objetivo internacional (solo si estás en la copa) ---
FASES_COPA = ['Fase de grupos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']
TEXTO_META_COPA = {'Cuartos': "Llegar a cuartos de final", 'Semifinal': "Llegar a semifinales",
                   'Finalista': "Llegar a la final", 'Campeón': "Ser campeón de la copa"}
CALIF_COPA = {'superado': 6, 'cumplido': 3, 'fallado': -4}


def meta_copa(r: int, n: int, ventaja: float = 0.0) -> str:
    if n < 2:
        return 'Cuartos'
    if r == 1 and ventaja >= VENTAJA_PARA_TITULO:
        return 'Campeón'
    if r <= n / 4:
        return 'Finalista'
    if r <= n / 2:
        return 'Semifinal'
    return 'Cuartos'


def definir_objetivo_copa(estado: dict) -> Optional[dict]:
    dc = _dc(estado)
    t = int(estado.get('temporada', 1) or 1)
    oc = dc.get('objetivo_copa')
    if isinstance(oc, dict) and oc.get('temporada') == t:
        return oc if oc.get('fase') else None
    if not estado.get('copa_user_en_copa'):
        dc['objetivo_copa'] = {'temporada': t, 'fase': None}
        return None
    mi = estado.get('mi_equipo')
    equipos = [x for x in (estado.get('copa_equipos_obj') or {}).values() if x is not None]
    if mi is not None and not any(x is mi or getattr(x, 'id', None) == mi.id for x in equipos):
        equipos.append(mi)
    ranking = sorted(equipos, key=lambda x: -getattr(x, 'ovr_promedio', 0))
    r = next((i + 1 for i, x in enumerate(ranking) if x is mi or getattr(x, 'id', None) == getattr(mi, 'id', -1)), len(ranking))
    ventaja = (ranking[0].ovr_promedio - ranking[1].ovr_promedio) if len(ranking) > 1 else 0
    fase = meta_copa(r, len(ranking), ventaja)
    oc = dc['objetivo_copa'] = {'temporada': t, 'fase': fase, 'texto': TEXTO_META_COPA[fase],
                                'ranking': r, 'n': len(ranking)}
    return oc


def evaluar_objetivo_copa(estado: dict, temporada_fin: int) -> Optional[dict]:
    oc = _dc(estado).get('objetivo_copa')
    if not isinstance(oc, dict) or oc.get('temporada') != temporada_fin or not oc.get('fase'):
        return None
    alcanzada = estado.get('copa_mejor_fase_temp') or 'Fase de grupos'
    ia = FASES_COPA.index(alcanzada) if alcanzada in FASES_COPA else 0
    im = FASES_COPA.index(oc['fase'])
    resultado = 'superado' if ia > im else 'cumplido' if ia == im else 'fallado'
    ajustar_calif(estado, CALIF_COPA[resultado])
    return {'texto': oc['texto'], 'fase': oc['fase'], 'alcanzada': alcanzada, 'resultado': resultado}


# --- v3.2.0: espaldarazo financiero (más presupuesto a cambio de una meta más alta) ---
ESPALDARAZO = [(0.15, 1), (0.30, 2), (0.50, 3)]
CALIF_ESPALDARAZO = 40


def _texto_meta(pos_max: int) -> str:
    return "Ser campeón de liga" if pos_max <= 1 else f"Terminar entre los {pos_max} primeros"


def opciones_espaldarazo(estado: dict) -> list:
    obj = definir_objetivo(estado) or {}
    ref = int(obj.get('presupuesto_ref', 0) or 0)
    pos_max = int(obj.get('pos_max', 1))
    return [{'nivel': i, 'pct': pct, 'puestos': p, 'monto': int(ref * pct), 'disponible': pos_max - p >= 1}
            for i, (pct, p) in enumerate(ESPALDARAZO)]


def pedir_espaldarazo(estado: dict, nivel: int) -> tuple:
    """(ok, mensaje). Una vez por temporada, hasta la mitad de la liga, con calif ≥ 40."""
    obj = definir_objetivo(estado)
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if not obj or liga is None or mi is None:
        return False, "No hay objetivo esta temporada."
    if obj.get('espaldarazo'):
        return False, "Ya pediste un espaldarazo esta temporada."
    if int(getattr(liga, 'jornada_actual', 1) or 1) > int(getattr(liga, 'num_jornadas', 10) or 10) // 2:
        return False, "Solo se puede pedir hasta la mitad de la temporada."
    if calif_dt(estado) < CALIF_ESPALDARAZO:
        return False, f"La directiva se niega: tu calificación ({calif_dt(estado)}) es muy baja."
    op = opciones_espaldarazo(estado)[int(nivel)]
    if not op['disponible']:
        return False, "La meta no puede subir tanto."
    mi.balance = int(getattr(mi, 'balance', 0) or 0) + op['monto']
    obj['pos_max'] = int(obj['pos_max']) - op['puestos']
    obj['espaldarazo'] = {'pct': op['pct'], 'puestos': op['puestos']}
    obj['texto'] = _texto_meta(obj['pos_max']) + " (espaldarazo)"
    try:
        from alpha_football.finanzas import registrar
        registrar(estado, 'directiva', op['monto'])
    except Exception as e:
        logger.error(f"Error al registrar el espaldarazo: {e}")
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', "Espaldarazo aprobado",
             f"Te damos ${op['monto'] / 1_000_000:.1f}M. A cambio, la meta ahora es: {obj['texto']}.",
             C.accion('objetivos_screen', "VER OBJETIVOS"))
    return True, f"Aprobado: +${op['monto'] / 1_000_000:.1f}M · nueva meta: puesto {obj['pos_max']}."


def texto_evaluacion(info: dict) -> str:
    """Cuerpo del correo de rendimiento."""
    partes = [f"Liga: terminaste {info['posicion']}º (meta: {info.get('texto', '')}) → {info['resultado'].upper()}."]
    m = int(info.get('monto', 0) or 0)
    partes.append(f"{'Premio' if m >= 0 else 'Multa'} de la directiva: ${abs(m) / 1_000_000:.1f}M.")
    if info.get('copa'):
        cp = info['copa']
        partes.append(f"Copa: {cp['alcanzada']} (meta: {cp['texto']}) → {cp['resultado'].upper()}.")
    partes.append(f"Calificación de DT: {info.get('calif')} · confianza: {info.get('confianza')}.")
    v = info.get('veredicto')
    partes.append({'felicitacion': "¡Felicitaciones! Superaste lo que esperábamos.",
                   'neutro': "Cumpliste. Seguimos con el plan.",
                   'regano': "No cumpliste. Te damos una segunda oportunidad: si vuelves a fallar, te despedimos.",
                   'despido': "Decidimos prescindir de tus servicios.",
                   'fin_contrato': "Tu contrato terminó y no seguirás en el club."}.get(v, ""))
    if info.get('indemnizacion'):
        partes.append(f"Indemnización: ${info['indemnizacion'] / 1_000_000:.2f}M a tu patrimonio.")
    return " ".join(partes)
```

3c. `marcar_despido` y `restaurar_despido`:

```python
def marcar_despido(estado: dict, motivo: str, temporada_fin: Optional[int] = None,
                   indemnizar: bool = True, titulo: str = "¡DESPEDIDO!") -> int:
    """
    v2.9.1: deja el despido pendiente en memoria y en datos_carrera (se guarda con la
    partida). v3.2.0: paga la indemnización al patrimonio y guarda el título de la pantalla
    ("FIN DE CONTRATO" cuando no renuevan). Retorna la indemnización cobrada.
    """
    monto = 0
    if indemnizar:
        from alpha_football import carrera_dt as CD
        monto = CD.cobrar_indemnizacion(estado, temporada_fin or int(estado.get('temporada', 1) or 1))
    pend = estado.get('despido_pendiente')
    if pend:
        pend['motivo'] = (pend.get('motivo', '') + " " + motivo).strip()
    else:
        pend = estado['despido_pendiente'] = {'motivo': motivo, 'opciones': opciones_de_club(estado),
                                              'titulo': titulo}
    _dc(estado)['despido_pendiente'] = {'motivo': pend['motivo'], 'titulo': pend.get('titulo', titulo),
                                        'opciones_ids': [o.id for o in pend['opciones']]}
    return monto
```
En `restaurar_despido`, al reconstruir: `estado['despido_pendiente'] = {'motivo': ..., 'opciones': opciones, 'titulo': guardado.get('titulo', "¡DESPEDIDO!")}`.

3d. `evaluar_temporada` — reemplazar desde `if resultado == 'fallado':` hasta el `return info` final por:

```python
    temporada_fin = int(obj.get('temporada') or estado.get('temporada', 1) or 1)
    if resultado == 'fallado':
        # v3.1.0: segunda oportunidad salvo reincidencia o catástrofe
        if es_catastrofico(estado, posicion, pos_max) or dc.get('advertencia_dt'):
            despido = True
            ajustar_calif(estado, CALIF['despido'])
        else:
            dc['advertencia_dt'] = True
            dc['confianza'] = CONFIANZA_TRAS_AVISO
    else:
        dc['advertencia_dt'] = False
        dc['confianza'] = min(100, confianza(estado) + (15 if resultado == 'superado' else 8))
    copa_ev = evaluar_objetivo_copa(estado, temporada_fin)       # v3.2.0
    from alpha_football import carrera_dt as CD
    indem = 0
    if despido:
        veredicto = 'despido'
        indem = marcar_despido(estado, f"No cumpliste: {obj.get('texto', 'el objetivo')} (terminaste {posicion}º).",
                               temporada_fin=temporada_fin)
    elif CD.contrato_vencido(estado, temporada_fin):
        veredicto = 'fin_contrato'
        marcar_despido(estado, "Terminó tu contrato y no hubo renovación.", temporada_fin=temporada_fin,
                       indemnizar=False, titulo="FIN DE CONTRATO")
    elif resultado == 'fallado':
        veredicto = 'regano'
    elif resultado == 'superado' or posicion == 1 or estado.get('copa_mejor_fase_temp') == 'Campeón':
        veredicto = 'felicitacion'
    else:
        veredicto = 'neutro'
    info = {'temporada': obj.get('temporada'), 'texto': obj.get('texto', ''), 'posicion': posicion,
            'resultado': resultado, 'monto': monto, 'despido': despido, 'veredicto': veredicto,
            'copa': copa_ev, 'calif': calif_dt(estado), 'confianza': confianza(estado), 'indemnizacion': indem}
    dc['directiva_ultimo'] = info
    msg = C.enviar(estado, 'directiva', f"Evaluación de la temporada {temporada_fin}", texto_evaluacion(info),
                   C.accion('objetivos_screen', "VER OBJETIVOS"))
    estado['veredicto_pendiente'] = {'correo_id': msg['id'], 'tipo': veredicto, 'info': info}
    return info
```
(Se elimina el correo "Advertencia: no cumpliste el objetivo": ahora va dentro del de rendimiento. Buscar en `tests/` con `grep -rn "Advertencia" tests/` y actualizar las aserciones que lo esperaban al asunto `"Evaluación de la temporada"` + `veredicto == 'regano'`.)

3e. `cambiar_de_club`: en el bloque de `dc.pop(...)` añadir `dc.pop('renovacion_dt', None)` y `dc.pop('objetivo_copa', None)`.

3f. `resumen_temporada_screen.siguiente_pantalla_tras_temporada`: primera línea `if estado.get('veredicto_pendiente'): return "veredicto_screen"`; docstring → "v3.2.0: veredicto → despido → ascensos/descensos → hub".

- [ ] **Step 4: Run** `SDL_VIDEODRIVER=dummy python tests/test_carrera_dt_v320.py` → `16/16`.
- [ ] **Step 5: Run full suite**; arreglar tests viejos que esperaban el correo de advertencia (solo aserciones, no comportamiento).

---

### Task 3: Pantallas y enganches de 7a (contrato, veredicto, objetivos, OFICINA, alta)

**Files:**
- Create: `alpha_football/ui/contrato_dt_screen.py`, `alpha_football/ui/veredicto_screen.py`
- Modify: `main.py:478-525` (importar y registrar `'contrato_dt_screen'`, `'veredicto_screen'`)
- Modify: `alpha_football/ui/menu.py:1587` (alta → contrato)
- Modify: `alpha_football/ui/despido_screen.py` (título de `pend['titulo']`; tras elegir club → contrato 'alta')
- Modify: `alpha_football/ui/league_screen.py:355-362` (tarjeta MI CONTRATO) y `:826-837` (hooks `asegurar_contrato` + `definir_objetivo_copa`)
- Modify: `alpha_football/ui/match_screen.py:537-541` (hooks `pagar_jornada` + `revisar_renovacion`)
- Modify: `alpha_football/ui/objetivos_screen.py` (apartado internacional + botón PEDIR ESPALDARAZO con overlay)
- Test: `tests/test_carrera_dt_v320.py` (añadir tests de pantallas)

**Interfaces:**
- Consumes: Tasks 1-2.
- Produces: pantalla `'contrato_dt_screen'` con `estado['contrato_modo'] ∈ {'alta','renovacion','ver'}` (7b la usa con `'alta'` tras aceptar una oferta); `contrato_dt_screen.modo(estado) -> str`; pantalla `'veredicto_screen'` (`estado['veredicto_paso'] ∈ {0,1}`).

- [ ] **Step 1: Write the failing tests** (añadir a `TESTS`):

```python
def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def test_contrato_screen_alta():
    from alpha_football.ui import contrato_dt_screen as S
    e = estado_carrera(); e['mi_equipo'].balance = 50_000_000
    e['contrato_modo'] = 'alta'
    pygame.event.clear(); assert S.render(screen, e) is None
    key(pygame.K_RIGHT); S.render(screen, e)
    key(pygame.K_RETURN); assert S.render(screen, e) == 'league_screen'
    assert CD.contrato(e)['hasta'] == 3 and 'contrato_modo' not in e
    e['contrato_modo'] = 'alta'; e['promo_releg_data'] = {'x': 1}
    key(pygame.K_RETURN); assert S.render(screen, e) == 'promo_releg_screen'


def test_contrato_screen_renovacion_y_ver():
    from alpha_football.ui import contrato_dt_screen as S
    e = estado_carrera(); CD.firmar(e, e['mi_equipo'], {'anios': 1, 'sueldo': 1_000_000})
    e['datos_carrera']['renovacion_dt'] = {'temporada': 1, 'estado': 'ofrecida'}
    assert S.modo(e) == 'renovacion'
    click(S.R_RECHAZAR.center); assert S.render(screen, e) == 'league_screen'
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'rechazada'
    assert S.modo(e) == 'ver'
    pygame.event.clear(); assert S.render(screen, e) is None
    key(pygame.K_ESCAPE); assert S.render(screen, e) == 'league_screen'


def test_veredicto_screen_flujo():
    from alpha_football.ui import veredicto_screen as V
    e = _con_objetivo(5); e['datos_carrera']['advertencia_dt'] = True
    D.evaluar_temporada(e, 7)
    pygame.event.clear(); assert V.render(screen, e) is None        # paso 1: el correo
    key(pygame.K_RETURN); assert V.render(screen, e) is None        # paso 2: veredicto
    assert C.bandeja(e)[0]['leido']
    key(pygame.K_RETURN); assert V.render(screen, e) == 'despido_screen'
    assert 'veredicto_pendiente' not in e


def test_despido_lleva_a_contrato():
    from alpha_football.ui import despido_screen as DS
    e = _con_objetivo(5); D.marcar_despido(e, "x")
    r = DS._rects_opciones(len(e['despido_pendiente']['opciones']))[0]
    click(r.center)
    assert DS.render(screen, e) == 'contrato_dt_screen' and e['contrato_modo'] == 'alta'


def test_objetivos_screen_espaldarazo_y_copa():
    from alpha_football.ui import objetivos_screen as O
    e = _con_objetivo(6); e['copa_user_en_copa'] = False
    pygame.event.clear(); assert O.render(screen, e) is None
    click(O.R_ESPALDARAZO.center); O.render(screen, e)
    assert e.get('espaldarazo_abierto')
    key(pygame.K_1); O.render(screen, e)
    assert e['datos_carrera']['objetivo']['pos_max'] == 5 and not e.get('espaldarazo_abierto')
```

- [ ] **Step 2: Run to verify they fail** (`ModuleNotFoundError: contrato_dt_screen`).

- [ ] **Step 3: Implement.**

3a. `alpha_football/ui/contrato_dt_screen.py` (bloque de imports theme con fallback idéntico a `despido_screen.py` líneas 13-25):

```python
"""
ALPHA FOOTBALL — Contrato del DT (Pygame)
v3.2.0: firma estilo FIFA al llegar a un club ('alta'), oferta de renovación ('renovacion')
y consulta del contrato vigente ('ver', tarjeta MI CONTRATO en OFICINA).
"""
# ... imports + fallback theme como despido_screen ...
from alpha_football import carrera_dt as CD
from alpha_football import directiva as D

R_RECHAZAR = pygame.Rect(16, 620, 320, 52)
R_VOLVER = pygame.Rect(SCREEN_W - 216, 12, 200, 44)


def _rects(n: int) -> list:
    return [pygame.Rect(16 + i * 422, 200, 404, 360) for i in range(n)]


def modo(estado: dict) -> str:
    m = estado.get('contrato_modo')
    if m in ('alta', 'renovacion', 'ver'):
        return m
    r = (estado.get('datos_carrera') or {}).get('renovacion_dt') or {}
    if r.get('estado') == 'ofrecida' and r.get('temporada') == int(estado.get('temporada', 1) or 1):
        return 'renovacion'
    return 'ver'


def _m(v) -> str:
    return f"${int(v) / 1_000_000:.2f}M"


def _salir(estado: dict, m: str) -> str:
    estado.pop('contrato_modo', None)
    estado.pop('contrato_sel', None)
    if m == 'alta' and estado.get('promo_releg_data'):
        return 'promo_releg_screen'
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mi = estado.get('mi_equipo')
        if mi is None:
            return 'league_screen'
        m = modo(estado)
        ofertas = CD.ofertas_contrato(estado, mi, renovacion=(m == 'renovacion')) if m != 'ver' else []
        sel = max(0, min(int(estado.get('contrato_sel', 1) or 0), max(0, len(ofertas) - 1)))
        rects = _rects(len(ofertas))
        mouse_pos = pygame.mouse.get_pos()
        elegido = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    sel = max(0, sel - 1)
                elif ev.key == pygame.K_RIGHT:
                    sel = min(max(0, len(ofertas) - 1), sel + 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and ofertas:
                    elegido = sel
                elif ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) and m != 'alta':
                    return _salir(estado, m)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(ev.pos):
                        elegido = i
                if m == 'renovacion' and R_RECHAZAR.collidepoint(ev.pos):
                    CD.rechazar_renovacion(estado)
                    return _salir(estado, m)
                if m != 'alta' and R_VOLVER.collidepoint(ev.pos):
                    return _salir(estado, m)
        estado['contrato_sel'] = sel
        if elegido is not None:
            CD.firmar(estado, mi, ofertas[elegido], renovacion=(m == 'renovacion'))
            return _salir(estado, m)

        draw_gradient_bg(screen)
        titulo = {'alta': "CONTRATO DE DT", 'renovacion': "RENOVACIÓN DE CONTRATO", 'ver': "MI CONTRATO"}[m]
        draw_text(screen, titulo, (16, 16), size='xl', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {getattr(estado.get('liga'), 'nombre', '')}  ·  "
                          f"Calificación de DT {D.calif_dt(estado)}", (16, 84), size='md', color='verde')
        if m != 'alta':
            draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        if m == 'ver':
            c = CD.contrato(estado) or {}
            ren = (estado.get('datos_carrera') or {}).get('renovacion_dt') or {}
            lineas = [(f"Sueldo anual: {_m(c.get('sueldo', 0))}", 'blanco'),
                      (f"Contrato: temporada {c.get('desde', '?')} a {c.get('hasta', '?')}", 'blanco'),
                      (f"Patrimonio personal: {_m(CD.patrimonio(estado))}", 'dorado'),
                      (f"Renovación: {ren.get('estado', 'sin novedades')}", 'azul')]
            for i, (t, col) in enumerate(lineas):
                draw_text(screen, t, (32, 160 + i * 44), size='lg', color=col)
            clubes = (estado.get('datos_carrera') or {}).get('clubes_dirigidos') or []
            draw_text(screen, "CLUBES DIRIGIDOS", (32, 360), size='md', color='azul')
            for i, cd in enumerate(clubes[-6:]):
                draw_text(screen, f"T{cd.get('temporada')}: {cd.get('de')} → {cd.get('a')}", (32, 396 + i * 30),
                          size='sm', color='blanco')
            return None
        draw_text(screen, "Elige tu contrato (← → y Enter, o clic):", (16, 140), size='md', color='blanco')
        for i, (of, r) in enumerate(zip(ofertas, rects)):
            activo = i == sel or r.collidepoint(mouse_pos)
            draw_panel(screen, r)
            if activo:
                pygame.draw.rect(screen, COLORS['dorado'], r, width=3, border_radius=8)
            x, y = r.x + 24, r.y + 24
            draw_text(screen, f"{of['anios']} AÑO{'S' if of['anios'] > 1 else ''}", (x, y), size='xl', color='dorado')
            draw_text(screen, f"Sueldo anual {_m(of['sueldo'])}", (x, y + 90), size='md', color='verde')
            draw_text(screen, f"Total {_m(of['sueldo'] * of['anios'])}", (x, y + 130), size='md', color='blanco')
            draw_text(screen, "Más estabilidad" if of['anios'] == 3 else "Más sueldo" if of['anios'] == 1
                      else "Equilibrado", (x, y + 180), size='sm', color='azul')
            draw_button(screen, pygame.Rect(r.x + 20, r.bottom - 68, r.width - 40, 48), "FIRMAR", activo)
        if m == 'renovacion':
            draw_button(screen, R_RECHAZAR, "RECHAZAR (me voy al final)", R_RECHAZAR.collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en contrato_dt_screen: {e}", exc_info=True)
        return 'league_screen'
```

3b. `alpha_football/ui/veredicto_screen.py` (mismo bloque theme):

```python
"""
ALPHA FOOTBALL — Veredicto de fin de temporada (Pygame)
v3.2.0: paso 1 = el correo de rendimiento abierto; Enter → paso 2 = veredicto a pantalla completa
(felicitación / cumplida / regaño / despido / fin de contrato); Enter → despido, ascensos o hub.
"""
# ... imports + fallback theme ...
from alpha_football import correo as C

VEREDICTOS = {'felicitacion': ("¡FELICITACIONES!", 'dorado'), 'neutro': ("TEMPORADA CUMPLIDA", 'azul'),
              'regano': ("LA DIRECTIVA NO ESTÁ CONFORME", 'rojo'), 'despido': ("¡DESPEDIDO!", 'rojo'),
              'fin_contrato': ("FIN DE CONTRATO", 'blanco')}


def _siguiente(estado: dict) -> str:
    estado.pop('veredicto_pendiente', None)
    estado.pop('veredicto_paso', None)
    if estado.get('despido_pendiente'):
        return 'despido_screen'
    if estado.get('promo_releg_data'):
        return 'promo_releg_screen'
    return 'league_screen'


def _envolver(texto: str, ancho: int = 92) -> list:
    lineas, linea = [], ""
    for p in texto.split():
        if len(linea) + len(p) + 1 > ancho:
            lineas.append(linea); linea = p
        else:
            linea = (linea + " " + p).strip()
    return lineas + ([linea] if linea else [])


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        vp = estado.get('veredicto_pendiente')
        if not vp:
            return _siguiente(estado)
        paso = int(estado.get('veredicto_paso', 0) or 0)
        msg = next((m for m in C.bandeja(estado) if m.get('id') == vp.get('correo_id')), None)
        avanzar = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                avanzar = True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                avanzar = True
        if avanzar:
            if paso == 0:
                if msg:
                    C.marcar_leido(estado, msg['id'])
                estado['veredicto_paso'] = 1
                return None
            return _siguiente(estado)

        draw_gradient_bg(screen)
        info = vp.get('info') or {}
        if paso == 0:
            draw_text(screen, "CORREO NUEVO", (16, 16), size='lg', color='azul')
            r = pygame.Rect(16, 80, SCREEN_W - 32, 540)
            draw_panel(screen, r)
            draw_text(screen, "De: Directiva", (r.x + 24, r.y + 20), size='sm', color='azul')
            draw_text(screen, (msg or {}).get('asunto', 'Evaluación de la temporada'), (r.x + 24, r.y + 50),
                      size='lg', color='dorado')
            for i, l in enumerate(_envolver((msg or {}).get('cuerpo', ''))):
                draw_text(screen, l, (r.x + 24, r.y + 110 + i * 32), size='md', color='blanco')
            draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
            return None
        titulo, color = VEREDICTOS.get(vp.get('tipo'), ("TEMPORADA TERMINADA", 'blanco'))
        draw_text(screen, titulo, (SCREEN_W // 2 - get_font('xl').size(titulo)[0] // 2, 200), size='xl', color=color)
        m = int(info.get('monto', 0) or 0)
        lineas = [f"Terminaste {info.get('posicion', '?')}º  ·  meta: {info.get('texto', '')}",
                  f"{'Premio' if m >= 0 else 'Multa'}: ${abs(m) / 1_000_000:.1f}M",
                  f"Calificación de DT: {info.get('calif', '?')}  ·  confianza: {info.get('confianza', '?')}"]
        if info.get('copa'):
            lineas.insert(1, f"Copa: {info['copa']['alcanzada']}  ·  meta: {info['copa']['texto']}")
        for i, t in enumerate(lineas):
            draw_text(screen, t, (SCREEN_W // 2 - get_font('md').size(t)[0] // 2, 320 + i * 40), size='md', color='blanco')
        draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
        return None
    except Exception as e:
        logger.error(f"Error en veredicto_screen: {e}", exc_info=True)
        return _siguiente(estado)
```
(Si `get_font` del theme recibe otra cosa que `'xl'`/`'md'`, usar la misma firma que ya usa `resumen_temporada_screen._centrado` para centrar.)

3c. `main.py`: tras `from alpha_football.ui.negociacion_screen import render as negociacion_render` añadir
```python
            from alpha_football.ui.contrato_dt_screen import render as contrato_dt_render   # v3.2.0
            from alpha_football.ui.veredicto_screen import render as veredicto_render
```
y en `PANTALLAS`: `'contrato_dt_screen': contrato_dt_render, 'veredicto_screen': veredicto_render,`.

3d. `menu.py:1586-1587`: justo antes de `return "league_screen"` del alta:
```python
                    estado['contrato_modo'] = 'alta'      # v3.2.0: firma estilo FIFA antes del hub
                    return "contrato_dt_screen"
```
(Asegurarse de que `datos_carrera` de la carrera nueva no arrastra `contrato_dt` de otra partida; si `estado['datos_carrera']` se reutiliza, hacer `estado.setdefault('datos_carrera', {}).pop('contrato_dt', None)` antes.)

3e. `despido_screen.py`: título `draw_text(screen, pend.get('titulo', "¡DESPEDIDO!"), ...)`; el texto de la línea 150 pasa a "Te ofrecen el banquillo. Elige dónde sigue tu carrera:"; al elegir club:
```python
                        D.cambiar_de_club(estado, eq)
                        estado['contrato_modo'] = 'alta'      # v3.2.0: contrato con el club nuevo
                        return 'contrato_dt_screen'
```

3f. `league_screen.py`: en `TARJETAS['oficina']` añadir `("MI CONTRATO", "Sueldo, años, patrimonio y renovación", 'contrato_dt_screen'),`. Verificar que `_abrir(estado, 'contrato_dt_screen')` no requiere registro extra (si `_abrir` tiene una lista blanca, añadirla) y hacer que la tarjeta limpie `estado.pop('contrato_modo', None)` para caer en modo 'ver'/'renovacion'. Tras el bloque de `definir_objetivo` (línea ~828):
```python
        try:  # v3.2.0: contrato del DT (saves viejos) y objetivo internacional
            from alpha_football.carrera_dt import asegurar_contrato
            asegurar_contrato(estado)
            from alpha_football.directiva import definir_objetivo_copa
            definir_objetivo_copa(estado)
        except Exception as e_dt:
            logger.error(f"Error en contrato/objetivo de copa: {e_dt}")
```
Nota: `definir_objetivo_copa` debe correr después de `sincronizar_copa_user` (que llena `copa_equipos_obj`); está después en el render, bien.

3g. `match_screen.py:537-541` (bloque v3.1.0 de `finalizar_jornada_liga`), después de `revisar_pedido(estado)`:
```python
            from alpha_football import carrera_dt as _cd      # v3.2.0: sueldo y renovación del DT
            _cd.pagar_jornada(estado)
            _cd.revisar_renovacion(estado)
```

3h. `objetivos_screen.py`:
- Constante `R_ESPALDARAZO = pygame.Rect(<x dentro de R_OBJ>, <R_OBJ.bottom - 56>, 320, 44)` (ubicar dentro del panel del objetivo, debajo de la línea "Ranking de tu plantilla..."; si no cabe, reducir `R_HIST` 60 px y bajar el panel).
- En eventos: clic en `R_ESPALDARAZO` → `estado['espaldarazo_abierto'] = True`. Con el overlay abierto: teclas `K_1/K_2/K_3` → nivel 0/1/2 (o clic en las 3 opciones) → `ok, msg = D.pedir_espaldarazo(estado, nivel)`; `estado['espaldarazo_msg'] = msg`; `estado.pop('espaldarazo_abierto')`. `ESC` cierra el overlay (y no sale de la pantalla mientras está abierto).
- Overlay: panel centrado con las 3 opciones de `D.opciones_espaldarazo(estado)`: `"1) +15% ($X.XM) → meta 1 puesto más alta"`, en gris si `not disponible`; aviso "Si fallas: segunda oportunidad como siempre".
- Mostrar `estado.get('espaldarazo_msg')` bajo el botón (verde si empieza con "Aprobado", rojo si no). Botón deshabilitado visualmente si `obj.get('espaldarazo')`.
- Apartado **INTERNACIONAL** (línea en R_OBJ o panel propio): `oc = D.definir_objetivo_copa(estado)`; si `oc`: `f"INTERNACIONAL: {oc['texto']} · vas: {estado.get('copa_mejor_fase_temp') or 'Fase de grupos'}"`; si no: `"INTERNACIONAL: sin competición esta temporada, no hay meta."`

- [ ] **Step 4: Run** `SDL_VIDEODRIVER=dummy python tests/test_carrera_dt_v320.py` → `21/21`.
- [ ] **Step 5: Run full suite** + smoke manual headless: `SDL_VIDEODRIVER=dummy python -c "import main"` no debe fallar al importar. Sin commit.

---

### Task 4: 9 estilos de juego (7c)

**Files:**
- Create: `alpha_football/estilos.py`
- Modify: `alpha_football/engine.py:24-35` (importar de `estilos`), `:267-271` (`bono_estilo`), `:835-839` (gasto en vivo)
- Modify: `alpha_football/energia.py:47-48, 98-117` (multiplicador de gasto)
- Modify: `alpha_football/models.py:393` (`normalizar_estilo`)
- Modify: `alpha_football/ui/team_screen.py:307,473`, `alpha_football/ui/match_screen.py:553`, `alpha_football/ui/edit_screen.py:35,451,466`
- Test: `tests/test_estilos_v330.py`

**Interfaces:**
- Produces (`alpha_football/estilos.py`, re-exportado por `engine`): `ESTILOS_DT: list[str]`, `ESTILO_VENTAJA: dict[str, frozenset[str]]`, `NOMBRE_ESTILO: dict[str, str]`, `DESC_ESTILO: dict[str, str]`, `normalizar_estilo(e: str) -> str`, `factor_gasto_estilo(estilo: str) -> float`, `ESTILOS_UI: list[str]` (anchelottismo primero).

- [ ] **Step 1: Write the failing tests** `tests/test_estilos_v330.py` (cabecera: sys.path + `SDL_VIDEODRIVER=dummy` + `pygame.init()` como `test_directiva_v280.py`):

```python
from alpha_football import estilos as ES, engine, energia as E
from alpha_football.models import Equipo


def test_nueve_estilos():
    assert len(ES.ESTILOS_DT) == 9 and set(ES.ESTILOS_DT) == set(ES.NOMBRE_ESTILO) == set(ES.DESC_ESTILO)
    assert engine.ESTILOS_DT is ES.ESTILOS_DT
    assert ES.ESTILOS_UI[0] == 'anchelottismo' and sorted(ES.ESTILOS_UI) == sorted(ES.ESTILOS_DT)


def test_matriz_sin_contradicciones():
    total = 0
    for a, gana in ES.ESTILO_VENTAJA.items():
        for b in gana:
            assert a not in ES.ESTILO_VENTAJA.get(b, ()), f"{a} y {b} se ganan mutuamente"
            total += 1
    assert total == 20
    assert 'anchelottismo' not in ES.ESTILO_VENTAJA
    assert all('anchelottismo' not in g for g in ES.ESTILO_VENTAJA.values())


def test_matriz_de_diego():
    V = ES.ESTILO_VENTAJA
    assert V['cruyffismo'] == {'flickismo'}
    assert V['flickismo'] == {'haramball', 'artetismo', 'fullbackismo'}
    assert V['haramball'] == {'cruyffismo', 'dezerbismo', 'kloppismo'}
    assert V['kloppismo'] == {'cruyffismo', 'choloismo', 'fullbackismo'}
    assert V['artetismo'] == {'haramball', 'choloismo', 'dezerbismo'}
    assert V['choloismo'] == {'cruyffismo', 'dezerbismo', 'fullbackismo'}
    assert V['dezerbismo'] == {'flickismo', 'kloppismo', 'fullbackismo'}
    assert V['fullbackismo'] == {'cruyffismo'}


def test_bono_estilo():
    assert engine.bono_estilo('artetismo', 'haramball') == 1.15
    assert engine.bono_estilo('haramball', 'artetismo') == 0.87
    assert engine.bono_estilo('artetismo', 'cruyffismo') == 1.0          # equilibrado a neutro
    assert engine.bono_estilo('anchelottismo', 'kloppismo') == 1.0
    assert engine.bono_estilo('desconocido', 'haramball') == 1.0


def test_kloppismo_gasta_mas():
    assert ES.factor_gasto_estilo('kloppismo') == 1.3 and ES.factor_gasto_estilo('haramball') == 1.0
    from alpha_football.ui.menu import load_league_teams
    liga = load_league_teams('premier')
    j = liga.equipos[0].jugadores[0]; j.energia = 100.0
    normal = E.energia_en_minuto(j, 90)
    klopp = E.energia_en_minuto(j, 90, mult=1.3)
    assert round(100 - klopp, 6) == round((100 - normal) * 1.3, 6) or klopp == 0.0


def test_normalizar_estilo():
    assert ES.normalizar_estilo('guardiolismo') == 'cruyffismo'
    assert ES.normalizar_estilo('simeonismo') == 'choloismo'
    assert ES.normalizar_estilo('mourinhismo') == 'haramball'
    assert ES.normalizar_estilo('bielsismo') == 'kloppismo'
    assert ES.normalizar_estilo('chapecoense') == 'anchelottismo'
    assert ES.normalizar_estilo('KLOPPISMO') == 'kloppismo'
    eq = Equipo.from_dict({'nombre': 'X', 'estilo_dt': 'simeonismo', 'jugadores': []})
    assert eq.estilo_dt == 'choloismo'


def test_listas_ui_unificadas():
    from alpha_football.ui import team_screen, edit_screen
    assert team_screen.TACTICAS == ES.ESTILOS_UI
    assert edit_screen.ESTILOS_TACTICOS == ES.ESTILOS_UI


TESTS = [test_nueve_estilos, test_matriz_sin_contradicciones, test_matriz_de_diego, test_bono_estilo,
         test_kloppismo_gasta_mas, test_normalizar_estilo, test_listas_ui_unificadas]
```
(+ bloque runner `if __name__ == '__main__':` igual al de los otros tests.)

- [ ] **Step 2: Run to verify it fails** → `ModuleNotFoundError: alpha_football.estilos`.

- [ ] **Step 3: Implement.**

3a. `alpha_football/estilos.py`:
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Estilos de juego (v3.3.0)
9 estilos. ESTILO_VENTAJA[a] = estilos a los que `a` le gana (+15% / −13% en el duelo).
Anchelottismo no gana ni pierde claro contra nadie (se adapta). Tabla de Diego con las
contradicciones resueltas según sus textos y dos pares equilibrados a neutro
(Artetismo–Cruyffismo, Fullbackismo–Haramball). Ver spec 2026-09-23-carrera-dt-design.md.
"""
from __future__ import annotations

# Orden original primero (el motor y los tests viejos dependen de él) + los 5 nuevos.
ESTILOS_DT: list[str] = ["haramball", "cruyffismo", "flickismo", "anchelottismo",
                         "kloppismo", "artetismo", "choloismo", "dezerbismo", "fullbackismo"]
ESTILOS_UI: list[str] = sorted(ESTILOS_DT, key=lambda e: e != "anchelottismo")

ESTILO_VENTAJA: dict[str, frozenset] = {
    "cruyffismo":   frozenset({"flickismo"}),
    "flickismo":    frozenset({"haramball", "artetismo", "fullbackismo"}),
    "haramball":    frozenset({"cruyffismo", "dezerbismo", "kloppismo"}),
    "kloppismo":    frozenset({"cruyffismo", "choloismo", "fullbackismo"}),
    "artetismo":    frozenset({"haramball", "choloismo", "dezerbismo"}),
    "choloismo":    frozenset({"cruyffismo", "dezerbismo", "fullbackismo"}),
    "dezerbismo":   frozenset({"flickismo", "kloppismo", "fullbackismo"}),
    "fullbackismo": frozenset({"cruyffismo"}),
}

NOMBRE_ESTILO: dict[str, str] = {
    "haramball": "Haramball", "cruyffismo": "Cruyffismo", "flickismo": "Flickismo",
    "anchelottismo": "Ancelotismo", "kloppismo": "Kloppismo", "artetismo": "Artetismo",
    "choloismo": "Choloismo", "dezerbismo": "DeZerbismo", "fullbackismo": "Fullbackismo",
}

DESC_ESTILO: dict[str, str] = {
    "haramball": "Bloque bajo y balón largo: muro atrás y segundos balones.",
    "cruyffismo": "Tiki-taka: posesión y pases cortos.",
    "flickismo": "Presión alta y verticalidad rápida.",
    "anchelottismo": "Se adapta a todo: nunca gana ni pierde claro.",
    "kloppismo": "Gegenpress y caos organizado. Gasta 30% más de energía.",
    "artetismo": "Posesión disciplinada y balón parado nuclear.",
    "choloismo": "Bloque medio agresivo, duelos y transiciones cortas.",
    "dezerbismo": "Salida suicida desde el portero y tercer hombre.",
    "fullbackismo": "Laterales voladores y extremos por dentro.",
}

_LEGADO = {"guardiolismo": "cruyffismo", "simeonismo": "choloismo",
           "mourinhismo": "haramball", "bielsismo": "kloppismo"}


def normalizar_estilo(e) -> str:
    """Estilos viejos del editor → los 9 actuales (desconocido = anchelottismo)."""
    k = str(e or "").strip().lower()
    if k in ESTILOS_DT:
        return k
    return _LEGADO.get(k, "anchelottismo")


def factor_gasto_estilo(estilo) -> float:
    return 1.3 if str(estilo or "").lower() == "kloppismo" else 1.0
```

3b. `engine.py:24-35`: reemplazar la definición de `ESTILOS_DT` y `ESTILO_VENTAJA` por
```python
# v3.3.0: los 9 estilos y su matriz viven en estilos.py (re-exportados aquí).
from alpha_football.estilos import ESTILOS_DT, ESTILO_VENTAJA, NOMBRE_ESTILO, DESC_ESTILO  # noqa: E402
```
y `bono_estilo`:
```python
def bono_estilo(estilo_atk: str, estilo_def: str) -> float:
    """Bonus/malus tactico (matriz de 9 estilos). +15% al ganador, -13% al perdedor."""
    if estilo_def in ESTILO_VENTAJA.get(estilo_atk, ()): return 1.15
    if estilo_atk in ESTILO_VENTAJA.get(estilo_def, ()): return 0.87
    return 1.0
```
Luego `grep -rn "ESTILO_VENTAJA" alpha_football main.py` y adaptar cualquier otro uso que lo trate como `dict[str, str]` (p. ej. `ESTILO_VENTAJA.get(x) == y` → `y in ESTILO_VENTAJA.get(x, ())`; textos "vence a X" → unir con `", ".join(NOMBRE_ESTILO[s] for s in sorted(...))`).

3c. `energia.py`:
```python
def energia_en_minuto(j, minutos: int, mult: float = 1.0) -> float:
    return max(0.0, float(getattr(j, 'energia', 100.0)) - gasto_por_minuto(j) * mult * max(0, int(minutos)))
```
En `cerrar_partido`, antes del `for`: `from alpha_football.estilos import factor_gasto_estilo` y `mult = factor_gasto_estilo(getattr(equipo, 'estilo_dt', ''))` (v3.3.0: Kloppismo gasta más); usar `energia_en_minuto(j, m, mult)`. En `engine.py:835-839` (energía en vivo) pasar el `mult` del equipo del jugador: leer el bloque, y donde se itera por equipo usar `energia_en_minuto(j, prev, factor_gasto_estilo(equipo.estilo_dt))`. En `team_screen.py:362` pasar `factor_gasto_estilo(mi_equipo.estilo_dt)` si el equipo está a mano en esa función (si no, dejarlo).

3d. `models.py:393`: `estilo_dt=_normalizar_estilo(datos.get("estilo_dt", "cruyffismo")),` con `from alpha_football.estilos import normalizar_estilo as _normalizar_estilo` (import local dentro de `from_dict` para no crear ciclos).

3e. UI:
- `team_screen.py:307`: `from alpha_football.estilos import ESTILOS_UI as TACTICAS, NOMBRE_ESTILO  # v3.3.0` (en lugar de la lista). Línea 473: mostrar `NOMBRE_ESTILO.get(mi_equipo.estilo_dt, ...)` en vez de `.capitalize()`. Debajo del selector de ESTILO dibujar `DESC_ESTILO[mi_equipo.estilo_dt]` en `size='sm'` si hay lugar (revisar solapes; si no cabe, omitir). Línea 203: si muestra el estilo del rival, usar `NOMBRE_ESTILO`.
- `match_screen.py:553`: `_TACTICAS_MENU = ESTILOS_UI` importado de `estilos` (si está sin uso, borrarlo).
- `edit_screen.py:35`: `from alpha_football.estilos import ESTILOS_UI as ESTILOS_TACTICOS, NOMBRE_ESTILO`; línea 451: `NOMBRE_ESTILO.get(normalizar_estilo(equipo_sel.get('estilo_dt')), 'Ancelotismo').upper()`. El dropdown de 9 × 30 px desde y=413 llega a 683 (< 720): cabe.
- `grep -rn "anchelottismo\", \"cruyffismo\"\|\"haramball\"\]" alpha_football` para cazar otras listas fijas de 4 estilos y reemplazarlas por `ESTILOS_UI`.

- [ ] **Step 4: Run** `SDL_VIDEODRIVER=dummy python tests/test_estilos_v330.py` → `7/7`.
- [ ] **Step 5: Run full suite** (en especial `test_mentalidad_v250.py` y `test_vestuario_v310.py`, que usan el motor). Sin commit.

---

### Task 5: DTs en cada club (7b, datos + asignación)

**Files:**
- Create: `alpha_football/data/entrenadores.py`, `alpha_football/entrenadores.py`
- Modify: `alpha_football/models.py` (`Equipo.dt_nombre: str = ""` + `to_dict`/`from_dict`)
- Modify: `alpha_football/directiva.py:cambiar_de_club` (llamar a `entrenadores.al_cambiar_club`)
- Modify: `alpha_football/ui/league_screen.py` (hook `asegurar_dts` junto a `asegurar_contrato`)
- Test: `tests/test_dts_v340.py`

**Interfaces:**
- Consumes: `estilos.ESTILOS_DT`, `estilos.normalizar_estilo` (Task 4); `directiva.cambiar_de_club` (existente).
- Produces (`alpha_football/entrenadores.py`):
  - `dts(estado) -> dict` (`{'por_club': {str(equipo_id): dt}, 'libres': [dt], 'historial': [], 'despidos_temp': {}, 'ofertas': [], 'sig_id': int}`)
  - `dt = {'id': int, 'nombre': str, 'estilo': str, 'calif': int, 'interino': bool}`
  - `clubes(estado) -> list[tuple[equipo, liga]]` (las 10 ligas, sin repetir)
  - `asegurar_dts(estado) -> None` (idempotente), `dt_de(estado, equipo) -> Optional[dict]`
  - `asignar(estado, equipo, dt) -> None` (sincroniza `equipo.estilo_dt`)
  - `mejor_libre(estado) -> dict` (lo saca de libres; genera uno si no hay)
  - `al_cambiar_club(estado, viejo, nuevo) -> None`
  - `calif_inicial(equipo) -> int`, `nombre_generado(rng) -> str`

- [ ] **Step 1: Write the failing tests** `tests/test_dts_v340.py` (cabecera como `test_directiva_v280.py`, con `estado_carrera`):

```python
from alpha_football import entrenadores as EN, directiva as D, estilos as ES
from alpha_football.data.entrenadores import DT_REALES


def test_todo_club_ia_tiene_dt():
    e = estado_carrera()
    EN.asegurar_dts(e)
    mi = e['mi_equipo']
    for eq, _liga in EN.clubes(e):
        dt = EN.dt_de(e, eq)
        if eq is mi:
            assert dt is None
        else:
            assert dt and dt['estilo'] in ES.ESTILOS_DT and eq.estilo_dt == dt['estilo']
    assert len(EN.dts(e)['libres']) >= 20


def test_dt_reales_cubren_primeras():
    e = estado_carrera(); EN.asegurar_dts(e)
    for liga in e['primera_division'].values():
        for eq in liga.equipos:
            assert eq.nombre in DT_REALES, f"falta DT real para {eq.nombre}"
            nombre, estilo = DT_REALES[eq.nombre]
            assert estilo in ES.ESTILOS_DT and nombre


def test_asegurar_dts_idempotente():
    e = estado_carrera(); EN.asegurar_dts(e)
    antes = {k: v['id'] for k, v in EN.dts(e)['por_club'].items()}
    EN.asegurar_dts(e)
    assert {k: v['id'] for k, v in EN.dts(e)['por_club'].items()} == antes


def test_calif_inicial():
    class Q: estrellas = 4.5
    assert EN.calif_inicial(Q()) == 65
    Q.estrellas = 1.0; assert EN.calif_inicial(Q()) == 30


def test_override_editor():
    e = estado_carrera()
    otro = e['liga'].equipos[1]; otro.dt_nombre = "Profe Inventado"
    EN.asegurar_dts(e)
    assert EN.dt_de(e, otro)['nombre'] == "Profe Inventado"


def test_mejor_libre_y_cambio_de_club():
    e = estado_carrera(); EN.asegurar_dts(e)
    mi, nuevo = e['mi_equipo'], e['liga'].equipos[3]
    dt_nuevo = EN.dt_de(e, nuevo)
    n_libres = len(EN.dts(e)['libres'])
    D.cambiar_de_club(e, nuevo)
    assert EN.dt_de(e, nuevo) is None                        # ahora el DT eres tú
    assert EN.dt_de(e, mi) is not None                       # tu club viejo contrató a alguien
    assert any(d['id'] == dt_nuevo['id'] for d in EN.dts(e)['libres'])
    assert len(EN.dts(e)['libres']) == n_libres               # entra uno, sale otro


def test_persistencia_en_save():
    import json
    e = estado_carrera(); EN.asegurar_dts(e)
    copia = json.loads(json.dumps(e['datos_carrera']))       # datos_carrera debe ser JSON puro
    assert copia['dts']['por_club']


TESTS = [test_todo_club_ia_tiene_dt, test_dt_reales_cubren_primeras, test_asegurar_dts_idempotente,
         test_calif_inicial, test_override_editor, test_mejor_libre_y_cambio_de_club, test_persistencia_en_save]
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement.**

3a. `alpha_football/data/entrenadores.py`:
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — DTs reales parodiados (v3.4.0)
DT_REALES: nombre parodia del club → (nombre parodia del DT, estilo). DTs reales de la
temporada 2025-26 con parodia obvia. 2ª división y DTs libres: nombres generados.
Editables desde el editor (campo DT del equipo → Equipo.dt_nombre pisa a esta tabla).
"""
DT_REALES: dict[str, tuple[str, str]] = {
    # Premier
    "Manchester Billete": ("Pep Guardiolo", "cruyffismo"),
    "Arsenal Pechofrio": ("Mikel Artetazo", "artetismo"),
    "Pool de Higado": ("Arne Slote", "flickismo"),
    # ... una entrada por CADA club de las 1ª de los 5 países y de data/internacional.py
}

NOMBRES = ["Carlos", "Jorge", "Luis", "Miguel", "Sergio", "Diego", "Pablo", "Andrés", "Marcelo", "Ricardo",
           "Fernando", "Gustavo", "Hernán", "Julio", "Óscar", "Raúl", "Walter", "Nelson", "Iván", "Mauricio"]
APELLIDOS = ["Pizarrón", "Tiza", "Banquillo", "Silbato", "Cono", "Pechera", "Pizarra", "Táctico", "Rondo",
             "Libreta", "Cronómetro", "Vestuario", "Charla", "Esquema", "Doble Pivote", "Cal", "Césped",
             "Botines", "Rotación", "Cabezazo"]
```
**Relleno obligatorio de `DT_REALES`:** recorrer los clubes con
`python -c "from alpha_football.ui.menu import load_league_teams; [print(t, [e.nombre for e in load_league_teams(t).equipos]) for t in ('premier','laliga','betplay','argentina','brasil')]"` y los de `alpha_football/data/internacional.py`; para cada club poner el DT real 2025-26 de ese club con un nombre parodia obvio (cambiar 1-2 letras o un juego de palabras, estilo de los nombres de club) y un estilo de `ESTILOS_DT` coherente con su juego real (p. ej. Simeone → `choloismo`, De Zerbi → `dezerbismo`, Arteta → `artetismo`, Ancelotti → `anchelottismo`, Klopp-escuela → `kloppismo`, Flick → `flickismo`). `test_dt_reales_cubren_primeras` obliga a cubrir todas las 1ª.

3b. `models.py`: campo `dt_nombre: str = ""  # v3.4.0: DT puesto a mano en el editor` en `Equipo`; incluirlo en `to_dict` y `from_dict` (`dt_nombre=str(datos.get("dt_nombre", "") or "")`).

3c. `alpha_football/entrenadores.py`:
```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Entrenadores (v3.4.0)
Cada club de la IA tiene un DT (nombre, estilo, calificación). El estilo del club es el de su
DT. Los clubes que van mal echan a su DT y contratan al mejor libre; si el club entra en tu
banda de nivel, primero te ofrecen el banquillo a ti. Estado en datos_carrera['dts'].
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football.estilos import ESTILOS_DT, normalizar_estilo

logger = logging.getLogger(__name__)

N_LIBRES = 20


def dts(estado: dict) -> dict:
    d = estado.setdefault('datos_carrera', {}).setdefault('dts', {})
    for k, v in (('por_club', {}), ('libres', []), ('historial', []), ('despidos_temp', {}),
                 ('ofertas', []), ('sig_id', 1)):
        d.setdefault(k, v)
    return d


def clubes(estado: dict) -> list:
    vistos, out = set(), []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if id(eq) not in vistos:
                    vistos.add(id(eq)); out.append((eq, liga))
    return out


def calif_inicial(equipo) -> int:
    return max(20, min(90, int(round(50 + (float(getattr(equipo, 'estrellas', 3.0) or 3.0) - 3) * 10))))


def nombre_generado(rng: random.Random) -> str:
    from alpha_football.data.entrenadores import NOMBRES, APELLIDOS
    return f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"


def _nuevo(estado: dict, nombre: str, estilo: str, calif: int, interino: bool = False) -> dict:
    d = dts(estado)
    dt = {'id': int(d['sig_id']), 'nombre': nombre, 'estilo': normalizar_estilo(estilo),
          'calif': int(calif), 'interino': bool(interino)}
    d['sig_id'] = int(d['sig_id']) + 1
    return dt


def dt_de(estado: dict, equipo) -> Optional[dict]:
    return dts(estado)['por_club'].get(str(getattr(equipo, 'id', '')))


def asignar(estado: dict, equipo, dt: dict) -> None:
    dts(estado)['por_club'][str(equipo.id)] = dt
    equipo.estilo_dt = dt['estilo']


def _es_mi(estado: dict, equipo) -> bool:
    mi = estado.get('mi_equipo')
    return mi is not None and (equipo is mi or getattr(equipo, 'id', None) == getattr(mi, 'id', -1))


def asegurar_dts(estado: dict) -> None:
    """Idempotente: da DT a todo club IA que no tenga y llena la bolsa de libres."""
    from alpha_football.data.entrenadores import DT_REALES
    d = dts(estado)
    rng = random.Random(f"dts-{estado.get('temporada', 1)}-{len(d['por_club'])}")
    for eq, _liga in clubes(estado):
        if _es_mi(estado, eq) or str(eq.id) in d['por_club']:
            continue
        real = DT_REALES.get(eq.nombre)
        nombre = (getattr(eq, 'dt_nombre', '') or '').strip() or (real[0] if real else nombre_generado(rng))
        estilo = real[1] if real else getattr(eq, 'estilo_dt', 'anchelottismo')
        asignar(estado, eq, _nuevo(estado, nombre, estilo, calif_inicial(eq)))
    while len(d['libres']) < N_LIBRES:
        d['libres'].append(_nuevo(estado, nombre_generado(rng), rng.choice(ESTILOS_DT), rng.randint(35, 70)))


def mejor_libre(estado: dict) -> dict:
    d = dts(estado)
    candidatos = [x for x in d['libres'] if not x.get('interino')]
    if not candidatos:
        return _nuevo(estado, nombre_generado(random.Random(d['sig_id'])), 'anchelottismo', 45)
    mejor = max(candidatos, key=lambda x: x['calif'])
    d['libres'].remove(mejor)
    return mejor


def al_cambiar_club(estado: dict, viejo, nuevo) -> None:
    """El user deja `viejo` y toma `nuevo`: el DT de `nuevo` va a libres, `viejo` contrata."""
    d = dts(estado)
    saliente = d['por_club'].pop(str(getattr(nuevo, 'id', '')), None)
    if viejo is not None and viejo is not nuevo:
        asignar(estado, viejo, mejor_libre(estado))
    if saliente and not saliente.get('interino'):
        d['libres'].append(saliente)
    d['ofertas'] = [o for o in d['ofertas'] if o.get('club_id') != str(getattr(nuevo, 'id', ''))]
```
(`mejor_libre` se llama antes de devolver al saliente a la bolsa, así `test_mejor_libre_y_cambio_de_club` mantiene el tamaño de libres.)

3d. `directiva.cambiar_de_club`: después de `estado['mi_equipo'] = nuevo` (y antes del log):
```python
    try:  # v3.4.0: DTs de la IA (tu club viejo contrata, el DT del nuevo queda libre)
        from alpha_football.entrenadores import al_cambiar_club
        al_cambiar_club(estado, viejo, nuevo)
    except Exception as e_dt:
        logger.error(f"cambiar_de_club: error con los DTs: {e_dt}")
```

3e. `league_screen.py`: dentro del try v3.2.0 (Task 3, 3f) añadir `from alpha_football.entrenadores import asegurar_dts; asegurar_dts(estado)`.

- [ ] **Step 4: Run** `SDL_VIDEODRIVER=dummy python tests/test_dts_v340.py` → `7/7`.
- [ ] **Step 5: Run full suite.** Sin commit.

---

### Task 6: Despidos entre la IA, ofertas de banquillo y dónde se ve el DT (7b)

**Files:**
- Modify: `alpha_football/entrenadores.py` (funciones nuevas)
- Create: `alpha_football/ui/ofertas_dt_screen.py`
- Modify: `alpha_football/ui/match_screen.py:537-541` (hook `revisar_jornada`)
- Modify: `alpha_football/ui/resumen_temporada_screen.py` (hook `cierre_temporada` después de `evaluar_temporada`)
- Modify: `alpha_football/ui/league_screen.py` (tarjeta OFERTAS DT + badge en `:770`)
- Modify: `main.py` (registrar `'ofertas_dt_screen'`)
- Modify: `alpha_football/ui/edit_screen.py` (campo "DT (nombre)" del equipo)
- Modify: `alpha_football/ui/prepartido_screen.py` y `alpha_football/ui/otras_ligas_screen.py` (mostrar DT)
- Test: `tests/test_dts_v340.py` (añadir)

**Interfaces:**
- Consumes: Task 5; `directiva.cambiar_de_club`, `directiva.calif_dt`; `correo.enviar/accion`; `contrato_dt_screen` con `estado['contrato_modo'] = 'alta'` (Task 3).
- Produces: `posicion(liga, equipo) -> int`, `esperado(liga, equipo) -> int`, `en_banda(estado, equipo) -> bool`, `despedir(estado, equipo, liga, motivo: str) -> dict`, `revisar_jornada(estado, rng=None) -> None`, `cierre_temporada(estado, rng=None) -> None`, `ofertas_activas(estado) -> list[dict]` (`{'club_id', 'club', 'liga', 'jornadas', 'temporada'}`), `aceptar_oferta(estado, club_id: str) -> Optional[equipo]`, `rechazar_oferta(estado, club_id: str) -> None`. Constantes `PROB_DESPIDO_JORNADA = 0.08`, `PROB_DESPIDO_CIERRE = 0.5`, `PUESTOS_BAJO = 3`, `PROB_OFERTA_USER = 0.6`, `JORNADAS_OFERTA = 3`.

- [ ] **Step 1: Write the failing tests** (añadir a `tests/test_dts_v340.py` y a `TESTS`):

```python
class RngFijo(random.Random):
    """random() siempre devuelve `v` (para forzar despidos/ofertas)."""
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def _hundir(liga, eq):
    """Deja a `eq` último en la tabla y a mitad de temporada."""
    liga.jornada_actual = liga.num_jornadas // 2 + 1
    for x in liga.equipos:
        x.puntos = 30
    eq.puntos = 0


def _liga_ia(e):
    # una liga que NO es la del user, para aislar
    return next(l for l in e['primera_division'].values() if l is not e['liga'])


def test_posicion_y_esperado():
    e = estado_carrera(); EN.asegurar_dts(e)
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    assert EN.esperado(liga, fuerte) == 1
    _hundir(liga, fuerte)
    assert EN.posicion(liga, fuerte) == len(liga.equipos)


def test_despido_ia_umbral_y_tope():
    e = estado_carrera(); EN.asegurar_dts(e)
    e['datos_carrera']['calif_dt'] = 0                       # sin ofertas al user
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    viejo = EN.dt_de(e, fuerte)
    _hundir(liga, fuerte)
    EN.revisar_jornada(e, rng=RngFijo(0.99))                 # 99% > 8% → no echa
    assert EN.dt_de(e, fuerte)['id'] == viejo['id']
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] != viejo['id']
    assert any(d['id'] == viejo['id'] and d['calif'] == viejo['calif'] - 10 for d in EN.dts(e)['libres'])
    otro = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)[1]
    dt_otro = EN.dt_de(e, otro); _hundir(liga, otro)
    EN.revisar_jornada(e, rng=RngFijo(0.0))                  # tope: 1 por liga por temporada
    assert EN.dt_de(e, otro)['id'] == dt_otro['id']


def test_no_echa_antes_de_un_tercio():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 0
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    _hundir(liga, fuerte); liga.jornada_actual = 1
    viejo = EN.dt_de(e, fuerte)['id']
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] == viejo


def test_oferta_al_user_y_vencimiento():
    e = estado_carrera(); EN.asegurar_dts(e)
    e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    assert EN.en_banda(e, club)
    _hundir(liga, club)
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    of = EN.ofertas_activas(e)
    assert len(of) == 1 and of[0]['club_id'] == str(club.id) and of[0]['jornadas'] == 3
    assert EN.dt_de(e, club)['interino'] and C.bandeja(e)[0]['accion']['pantalla'] == 'ofertas_dt_screen'
    for _ in range(3):
        EN.revisar_jornada(e, rng=RngFijo(0.99))
    assert not EN.ofertas_activas(e) and not EN.dt_de(e, club)['interino']


def test_en_banda_por_calif():
    e = estado_carrera(); mi = e['mi_equipo']
    class Q: pass
    q = Q(); q.ovr_promedio = mi.ovr_promedio + 7
    e['datos_carrera']['calif_dt'] = 75; assert EN.en_banda(e, q)
    e['datos_carrera']['calif_dt'] = 60; assert not EN.en_banda(e, q)
    q.ovr_promedio = mi.ovr_promedio + 4; assert EN.en_banda(e, q)
    e['datos_carrera']['calif_dt'] = 30; assert not EN.en_banda(e, q)


def test_aceptar_oferta_consistencia():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    viejo = e['mi_equipo']; liga = e['liga']
    club = max((x for x in liga.equipos if x is not viejo), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    nuevo = EN.aceptar_oferta(e, str(club.id))
    assert nuevo is club and e['mi_equipo'] is club
    assert EN.dt_de(e, club) is None and EN.dt_de(e, viejo) is not None
    assert not EN.ofertas_activas(e)
    ids = [d['id'] for d in EN.dts(e)['por_club'].values()]
    assert len(ids) == len(set(ids))                         # ningún DT en dos clubes


def test_rechazar_oferta():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    EN.rechazar_oferta(e, str(club.id))
    assert not EN.ofertas_activas(e) and not EN.dt_de(e, club)['interino']


def test_cierre_temporada():
    e = estado_carrera(); EN.asegurar_dts(e)
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    _hundir(liga, fuerte); viejo = EN.dt_de(e, fuerte)['id']
    EN.dts(e)['despidos_temp'] = {'x': 1}
    EN.cierre_temporada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] != viejo and EN.dts(e)['despidos_temp'] == {}


def test_ofertas_dt_screen():
    from alpha_football.ui import ofertas_dt_screen as S
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    pygame.event.clear(); assert S.render(screen, e) is None
    click(S.rect_aceptar(0).center)
    assert S.render(screen, e) == 'contrato_dt_screen' and e['contrato_modo'] == 'alta'
    assert e['mi_equipo'] is club
```
(Importar `random` y `from alpha_football import correo as C` en la cabecera.)

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement.**

3a. `entrenadores.py` — añadir:
```python
PROB_DESPIDO_JORNADA = 0.08
PROB_DESPIDO_CIERRE = 0.5
PUESTOS_BAJO = 3
PROB_OFERTA_USER = 0.6
JORNADAS_OFERTA = 3


def _clave_liga(liga) -> str:
    return f"{getattr(liga, 'tipo', '?')}-{getattr(liga, 'division', 1)}"


def posicion(liga, equipo) -> int:
    tabla = sorted(liga.equipos, key=lambda x: (-x.puntos, -(x.gf - x.gc), -x.gf))
    return next((i + 1 for i, x in enumerate(tabla) if x is equipo), len(tabla))


def esperado(liga, equipo) -> int:
    ranking = sorted(liga.equipos, key=lambda x: -getattr(x, 'ovr_promedio', 0))
    return next((i + 1 for i, x in enumerate(ranking) if x is equipo), len(ranking))


def _va_mal(liga, equipo) -> bool:
    p = posicion(liga, equipo)
    return p >= esperado(liga, equipo) + PUESTOS_BAJO and p > len(liga.equipos) / 2


def en_banda(estado: dict, equipo) -> bool:
    from alpha_football.directiva import calif_dt
    mi = estado.get('mi_equipo')
    if mi is None:
        return False
    c, ovr, suyo = calif_dt(estado), mi.ovr_promedio, getattr(equipo, 'ovr_promedio', 0)
    tope = ovr + 10 if c >= 70 else ovr + 5 if c >= 55 else ovr
    return suyo <= tope


def despedir(estado: dict, equipo, liga, motivo: str) -> dict:
    """Saca al DT del club (a libres con calif −10) y lo anota. Retorna el DT despedido."""
    d = dts(estado)
    viejo = d['por_club'].pop(str(equipo.id), None) or {}
    if viejo and not viejo.get('interino'):
        viejo['calif'] = max(0, int(viejo['calif']) - 10)
        d['libres'].append(viejo)
    d['historial'].append({'temporada': int(estado.get('temporada', 1) or 1), 'club': equipo.nombre,
                           'dt': viejo.get('nombre', '?'), 'motivo': motivo})
    del d['historial'][:-300]
    if liga is estado.get('liga'):
        from alpha_football import correo as C
        C.enviar(estado, 'club', f"Cambio de DT en {equipo.nombre}",
                 f"{equipo.nombre} despidió a {viejo.get('nombre', 'su DT')}: {motivo}")
    return viejo


def _reemplazar(estado: dict, equipo) -> None:
    asignar(estado, equipo, mejor_libre(estado))


def _ofrecer_al_user(estado: dict, equipo, liga) -> None:
    from alpha_football import correo as C
    d = dts(estado)
    rng = random.Random(f"interino-{equipo.id}-{estado.get('temporada', 1)}")
    asignar(estado, equipo, _nuevo(estado, nombre_generado(rng) + " (interino)", 'anchelottismo', 40, interino=True))
    d['ofertas'].append({'club_id': str(equipo.id), 'club': equipo.nombre, 'liga': getattr(liga, 'nombre', ''),
                         'jornadas': JORNADAS_OFERTA, 'temporada': int(estado.get('temporada', 1) or 1)})
    C.enviar(estado, 'club', f"{equipo.nombre} te quiere como DT",
             f"{equipo.nombre} ({getattr(liga, 'nombre', '')}) despidió a su DT y te ofrece el banquillo. "
             f"La oferta vale {JORNADAS_OFERTA} jornadas.", C.accion('ofertas_dt_screen', "VER OFERTA"))


def ofertas_activas(estado: dict) -> list:
    t = int(estado.get('temporada', 1) or 1)
    return [o for o in dts(estado)['ofertas'] if o.get('temporada') == t and o.get('jornadas', 0) > 0]


def _club_por_id(estado: dict, club_id: str):
    return next(((eq, lg) for eq, lg in clubes(estado) if str(eq.id) == str(club_id)), (None, None))


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Tras cada jornada de liga del user: vencen ofertas y los clubes IA que van mal echan a su DT."""
    azar = rng or random.Random()
    d = dts(estado)
    for o in list(d['ofertas']):                      # 1) las ofertas pendientes pierden una jornada
        o['jornadas'] = int(o.get('jornadas', 0)) - 1
        if o['jornadas'] <= 0:
            d['ofertas'].remove(o)
            eq, _lg = _club_por_id(estado, o['club_id'])
            if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
                _reemplazar(estado, eq)
    for eq, liga in clubes(estado):                    # 2) despidos de la IA
        if _es_mi(estado, eq) or dt_de(estado, eq) is None or dt_de(estado, eq).get('interino'):
            continue
        n = max(1, int(getattr(liga, 'num_jornadas', 10) or 10))
        if int(getattr(liga, 'jornada_actual', 1) or 1) <= n / 3:
            continue
        if d['despidos_temp'].get(_clave_liga(liga), 0) >= 1 or not _va_mal(liga, eq):
            continue
        if azar.random() >= PROB_DESPIDO_JORNADA:
            continue
        despedir(estado, eq, liga, f"va {posicion(liga, eq)}º y se esperaba {esperado(liga, eq)}º")
        d['despidos_temp'][_clave_liga(liga)] = d['despidos_temp'].get(_clave_liga(liga), 0) + 1
        if en_banda(estado, eq) and azar.random() < PROB_OFERTA_USER:
            _ofrecer_al_user(estado, eq, liga)
        else:
            _reemplazar(estado, eq)


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Fin de temporada: los que terminaron 3+ puestos bajo lo esperado echan con 50%."""
    azar = rng or random.Random()
    d = dts(estado)
    for eq, liga in clubes(estado):
        if _es_mi(estado, eq) or dt_de(estado, eq) is None:
            continue
        if posicion(liga, eq) >= esperado(liga, eq) + PUESTOS_BAJO and azar.random() < PROB_DESPIDO_CIERRE:
            despedir(estado, eq, liga, "no cumplió en la temporada")
            _reemplazar(estado, eq)
        elif (dt_de(estado, eq) or {}).get('interino'):
            _reemplazar(estado, eq)
    d['despidos_temp'] = {}
    d['ofertas'] = []


def aceptar_oferta(estado: dict, club_id: str):
    """Cambio inmediato de club (sin indemnización: renunciaste)."""
    eq, _lg = _club_por_id(estado, club_id)
    if eq is None or not any(o['club_id'] == str(club_id) for o in ofertas_activas(estado)):
        return None
    from alpha_football.directiva import cambiar_de_club
    cambiar_de_club(estado, eq)                        # llama a al_cambiar_club (quita la oferta)
    dts(estado)['ofertas'] = []
    return eq


def rechazar_oferta(estado: dict, club_id: str) -> None:
    d = dts(estado)
    d['ofertas'] = [o for o in d['ofertas'] if o['club_id'] != str(club_id)]
    eq, _lg = _club_por_id(estado, club_id)
    if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
        _reemplazar(estado, eq)
```
Nota: en `test_aceptar_oferta_consistencia` el club nuevo tiene un interino; `al_cambiar_club` lo saca de `por_club` y, por ser interino, no lo manda a libres (correcto).

3b. `ui/ofertas_dt_screen.py` (bloque theme como `despido_screen.py`):
```python
"""
ALPHA FOOTBALL — Ofertas de banquillo (Pygame)
v3.4.0: clubes que echaron a su DT y te quieren. ACEPTAR = cambio inmediato + contrato;
RECHAZAR = contratan a otro. Las ofertas duran 3 jornadas.
"""
# ... imports + fallback theme ...
from alpha_football import entrenadores as EN

R_VOLVER = pygame.Rect(SCREEN_W - 216, 12, 200, 44)


def _fila(i: int) -> pygame.Rect:
    return pygame.Rect(16, 110 + i * 130, SCREEN_W - 32, 116)


def rect_aceptar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 440, r.y + 34, 200, 48)


def rect_rechazar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 220, r.y + 34, 200, 48)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        ofertas = EN.ofertas_activas(estado)[:4]
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return 'league_screen'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if R_VOLVER.collidepoint(ev.pos):
                    return 'league_screen'
                for i, o in enumerate(ofertas):
                    if rect_aceptar(i).collidepoint(ev.pos) and EN.aceptar_oferta(estado, o['club_id']) is not None:
                        estado['contrato_modo'] = 'alta'
                        return 'contrato_dt_screen'
                    if rect_rechazar(i).collidepoint(ev.pos):
                        EN.rechazar_oferta(estado, o['club_id'])
        draw_gradient_bg(screen)
        draw_text(screen, "OFERTAS DE BANQUILLO", (16, 16), size='xl', color='dorado')
        draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        if not ofertas:
            draw_text(screen, "Ningún club te busca por ahora. Cuando un club que va mal eche a su DT "
                              "y tu calificación alcance, te escribirán.", (16, 120), size='md', color='blanco')
        for i, o in enumerate(ofertas):
            r = _fila(i); draw_panel(screen, r)
            eq, liga = EN._club_por_id(estado, o['club_id'])
            draw_text(screen, o['club'][:26], (r.x + 20, r.y + 14), size='lg', color='dorado')
            if eq is not None:
                draw_text(screen, f"{o['liga'][:28]}  ·  MEDIA {eq.ovr_promedio}  ·  va {EN.posicion(liga, eq)}º",
                          (r.x + 20, r.y + 60), size='sm', color='azul')
            draw_text(screen, f"Vence en {o['jornadas']} jornada{'s' if o['jornadas'] != 1 else ''}",
                      (r.x + 20, r.y + 86), size='sm', color='rojo')
            draw_button(screen, rect_aceptar(i), "ACEPTAR", rect_aceptar(i).collidepoint(mouse_pos))
            draw_button(screen, rect_rechazar(i), "RECHAZAR", rect_rechazar(i).collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en ofertas_dt_screen: {e}", exc_info=True)
        return 'league_screen'
```

3c. Enganches:
- `match_screen.py` (bloque v3.1.0, después de los hooks de Task 3): `from alpha_football.entrenadores import revisar_jornada as _dts_jornada; _dts_jornada(estado)  # v3.4.0`.
- `resumen_temporada_screen.py`: tras el try de `evaluar_temporada` (y ANTES del swap de ascensos, porque usa la tabla final): `try: from alpha_football.entrenadores import cierre_temporada as _dts_cierre; _dts_cierre(estado) except Exception as e: logger.error(...)`.
- `league_screen.py`: `TARJETAS['oficina']` + `("OFERTAS DT", "Clubes que te quieren como DT", 'ofertas_dt_screen'),`; en `:770` extender el badge: `n_badge = ... if destino == 'ofertas_dt_screen'` con `len(EN.ofertas_activas(estado))` (import local en try). Añadir aviso en INICIO como el de correo sin leer (línea ~479) si hay ofertas: `"N club(es) te quieren como DT (OFICINA > OFERTAS DT)"`.
- `main.py`: registrar `'ofertas_dt_screen'`.
- `edit_screen.py`: en el panel del equipo, bajo "Estilo Táctico (DT)", un input de texto "DT (nombre)" que edita `equipo_sel['dt_nombre']`, con el mismo patrón que el input de presupuesto (`estado['edit_input_activo'] = 'team_dt'`, escribir con KEYDOWN/unicode, Backspace borra). Recolocar el dropdown de estilos si se solapa (el dropdown se dibuja encima; mantenerlo al final del bloque).
- `prepartido_screen.py`: donde se muestra el rival, añadir `f"DT: {dt['nombre']} · {NOMBRE_ESTILO.get(dt['estilo'], '')}"` si `EN.dt_de(estado, rival)`; `otras_ligas_screen.py`: en la tabla/lista de cada club, una columna o subtítulo "DT" con el nombre (truncar a 18 caracteres); si no hay lugar, mostrarlo solo al seleccionar el club.

- [ ] **Step 4: Run** `SDL_VIDEODRIVER=dummy python tests/test_dts_v340.py` → `16/16`.
- [ ] **Step 5: Run full suite** + `SDL_VIDEODRIVER=dummy python -c "import main"`. Sin commit.

---

## Cierre (controlador)

- [ ] Revisión final del diff completo contra el spec.
- [ ] Actualizar `context.md`: bitácora v3.2.0 / v3.3.0 / v3.4.0 (sub-proyecto 7), "Siguiente: sub-proyecto 3", pendiente del sub-proyecto 8 (ayuda con H).
