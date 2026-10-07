"""v0.4.10.0: el jugador contento pide renovar."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

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
    j.renovacion_avisada = True
    assert Jugador.from_dict(j.to_dict()).renovacion_avisada is True


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
