"""v4.6.0: las bajas (roja / lesión sin cambio) pesan según la línea que queda con hueco,
y registro de formaciones ampliado (todas las tácticas tienen formación preferida)."""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from types import SimpleNamespace

from alpha_football import save
from alpha_football import partido_ctx as PC
from alpha_football import formaciones as F
from alpha_football.estilos import ESTILOS_DT
from alpha_football.models import asegurar_ids_unicos
from alpha_football.ui.menu import load_league_teams
from alpha_football.engine import _once_titular

save.guardar_en_slot = lambda *a, **k: None


def _once(formacion='4-3-3'):
    return [SimpleNamespace(posicion=p) for p in F.puestos(formacion)]


def _equipos():
    liga = load_league_teams('premier')
    a, b = liga.equipos[0], liga.equipos[1]
    for e in (a, b):
        asegurar_ids_unicos(e)
    return a, b


def _sin(once, pos, n=1):
    """Quita n jugadores de la posición `pos`."""
    out, quitados = [], 0
    for j in once:
        if j.posicion == pos and quitados < n:
            quitados += 1
            continue
        out.append(j)
    return out


# ---------------------------------------------------------------- mult_bajas
def test_con_once_completo_no_hay_castigo():
    assert PC.mult_bajas(_once(), '4-3-3') == (1.0, 1.0, 1.0)
    print("  test_con_once_completo_no_hay_castigo: OK")


def test_sin_delantero_pierde_ataque_no_defensa():
    p_del, a_del, d_del = PC.mult_bajas(_sin(_once(), 'DEL'), '4-3-3')
    p_def, a_def, d_def = PC.mult_bajas(_sin(_once(), 'DEF'), '4-3-3')
    assert p_del < p_def and a_del < a_def, "sin delantero debe generar/atacar menos"
    assert d_def < d_del, "sin defensa debe defender peor"
    assert d_del > 0.95 and a_def > 0.85
    print("  test_sin_delantero_pierde_ataque_no_defensa: OK")


def test_castigo_se_acumula_con_9_y_8():
    for pos, eje in (('DEL', 1), ('DEF', 2), ('MED', 0)):
        m1 = PC.mult_bajas(_sin(_once(), pos, 1), '4-3-3')[eje]
        m2 = PC.mult_bajas(_sin(_once(), pos, 2), '4-3-3')[eje]
        m3 = PC.mult_bajas(_sin(_once(), pos, 3), '4-3-3')[eje]
        assert 1.0 > m1 > m2 > m3, (pos, m1, m2, m3)
        assert abs(m2 - m1 * m1) < 1e-9, "cada baja multiplica de nuevo"
    print("  test_castigo_se_acumula_con_9_y_8: OK")


def test_tapar_el_hueco_mueve_el_castigo():
    """Expulsan un DEF; si sale un DEL y entra un DEF, el hueco pasa al ataque."""
    once = _sin(_once(), 'DEF')
    tapado = _sin(once, 'DEL') + [SimpleNamespace(posicion='DEF')]
    assert PC.mult_bajas(tapado, '4-3-3') == PC.mult_bajas(_sin(_once(), 'DEL'), '4-3-3')
    print("  test_tapar_el_hueco_mueve_el_castigo: OK")


def test_sin_arquero_defiende_mucho_peor():
    d_por = PC.mult_bajas(_sin(_once(), 'POR'), '4-3-3')[2]
    d_def = PC.mult_bajas(_sin(_once(), 'DEF'), '4-3-3')[2]
    assert d_por < d_def
    print("  test_sin_arquero_defiende_mucho_peor: OK")


def test_once_desbalanceado_reparte_el_castigo():
    """Con 10 y dos líneas incompletas (sobra gente en otra) el castigo total es el de UNA baja."""
    once = _sin(_sin(_once(), 'DEL'), 'DEF') + [SimpleNamespace(posicion='MED')]
    p, a, d = PC.mult_bajas(once, '4-3-3')
    p1, a1, d1 = PC.mult_bajas(_sin(_once(), 'DEL'), '4-3-3')
    p2, a2, d2 = PC.mult_bajas(_sin(_once(), 'DEF'), '4-3-3')
    assert abs(math.log(a) - (math.log(a1) + math.log(a2)) / 2) < 1e-9
    assert abs(math.log(d) - (math.log(d1) + math.log(d2)) / 2) < 1e-9
    print("  test_once_desbalanceado_reparte_el_castigo: OK")


def test_calibrado_igual_que_antes_en_promedio():
    """Goles con 10 promediados por quién ve más rojas (DEF/MED x2, 4-3-3) ≈ el viejo 0.90/0.85/0.85 plano."""
    from alpha_football.engine import simular_rango
    a, b = _equipos()
    nuevo = dict(PC.MULT_HUECO)
    viejo = {k: (0.90, 0.85, 0.85) for k in nuevo}

    def goles(tabla, pos, n=200):
        PC.MULT_HUECO.update(tabla); random.seed(3); gf = gc = 0
        try:
            for _ in range(n):
                c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b)); c.auto_cambios['l'] = False
                j = next(x for x in c.en_cancha['l'] if x.posicion == pos)
                PC.aplicar_evento(c, {'minuto': 1, 'tipo': 'roja', 'lado': 'l', 'equipo_id': a.id, 'jugador': j,
                                      'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1})
                g = simular_rango(a, b, 2, 90, ctx=c)
                gf += g[0]; gc += g[1]
        finally:
            PC.MULT_HUECO.update(nuevo)
        return gf, gc

    pesos = {'DEF': 2 * 4, 'MED': 2 * 3, 'DEL': 1 * 3}
    prom = [sum(w * goles(nuevo, p)[k] for p, w in pesos.items()) / 17 for k in (0, 1)]
    antes = goles(viejo, 'MED')
    for real, ref in zip(prom, antes):
        assert abs(real - ref) < ref * 0.15, (prom, antes)
    print(f"  test_calibrado_igual_que_antes_en_promedio: OK nuevo {[round(x) for x in prom]} vs antes {antes}")


def test_formacion_desconocida_usa_433():
    assert PC.mult_bajas(_sin(_once(), 'DEL'), 'no-existe') == PC.mult_bajas(_sin(_once(), 'DEL'), '4-3-3')
    print("  test_formacion_desconocida_usa_433: OK")


# ---------------------------------------------------------------- motor
def test_motor_sin_delantero_anota_menos_que_sin_defensa():
    from alpha_football.engine import simular_rango
    a, b = _equipos()
    random.seed(7)
    goles = {'DEL': [0, 0], 'DEF': [0, 0]}          # [a favor, en contra] del equipo con 10
    for _ in range(300):
        for pos in ('DEL', 'DEF'):
            c = PC.nuevo_estado(a, b, _once_titular(a), _once_titular(b))
            j = next(x for x in c.en_cancha['l'] if x.posicion == pos)
            PC.aplicar_evento(c, {'minuto': 1, 'tipo': 'roja', 'lado': 'l', 'equipo_id': a.id, 'jugador': j,
                                  'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1})
            c.auto_cambios['l'] = False
            gl, gv = simular_rango(a, b, 2, 90, ctx=c)[:2]
            goles[pos][0] += gl
            goles[pos][1] += gv
    assert goles['DEL'][0] < goles['DEF'][0] * 0.85, goles
    assert goles['DEF'][1] > goles['DEL'][1] * 1.1, goles
    print(f"  test_motor_sin_delantero_anota_menos_que_sin_defensa: OK {goles}")


# ---------------------------------------------------------------- formaciones
def test_hay_17_formaciones_validas():
    fs = F.lista_formaciones()
    assert len(fs) == 17 and len(set(fs)) == 17
    for f in fs:
        c = F.cuotas(f)
        assert sum(c.values()) == 11 and c['POR'] == 1, f
        assert c['DEF'] >= 3 and c['MED'] >= 2 and c['DEL'] >= 1, f      # Alineacion.es_valida
        pos = F.posiciones(f)
        assert len(pos) == 11 and all(0 < x < 1 and 0 < y < 1 for x, y in pos), f
        assert F.puestos(f) == ['POR'] * 1 + ['DEF'] * c['DEF'] + ['MED'] * c['MED'] + ['DEL'] * c['DEL'], f
        ys = [y for _, y in pos]
        assert ys == sorted(ys, reverse=True), f"{f}: puestos deben ir de atrás hacia adelante"
        assert len(set(pos)) == 11, f"{f}: dos puestos en el mismo punto"
    print("  test_hay_17_formaciones_validas: OK")


def test_todas_las_tacticas_tienen_formacion():
    prefs = {F.pref(f) for f in F.lista_formaciones()}
    assert prefs <= set(ESTILOS_DT)
    assert set(ESTILOS_DT) <= prefs, set(ESTILOS_DT) - prefs
    print("  test_todas_las_tacticas_tienen_formacion: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_bajas_por_linea")
