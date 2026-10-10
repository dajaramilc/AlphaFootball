"""v0.4.19.0: las lesiones duran días/semanas/meses (no partidos), se curan con el calendario y avisan al recuperarse."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from test_calendario import _e, _jugar   # noqa: E402
from alpha_football import correo as C, energia as E, dias as D   # noqa: E402
from alpha_football.models import Jugador   # noqa: E402


def _altas(e):
    return [m for m in C.bandeja(e) if m['remitente'] == 'medico' and m['asunto'].startswith("Alta médica")]


def test_la_duracion_va_en_dias_con_las_cuatro_gravedades():
    azar = random.Random(7)
    ds = [E.duracion_lesion(azar) for _ in range(4000)]
    assert min(ds) >= 3 and max(ds) <= 180
    assert sum(1 for d in ds if d <= 10) > 0.4 * len(ds)                     # leves: la mitad
    assert any(d <= 10 for d in ds) and any(14 <= d <= 28 for d in ds)
    assert any(30 <= d <= 60 for d in ds) and any(d >= 90 for d in ds)       # y a veces meses
    assert not any(11 <= d <= 13 or 29 == d or 61 <= d <= 89 for d in ds)    # sin huecos inventados


def test_el_texto_dice_dias_semanas_o_meses():
    assert E.texto_lesion(1) == "1 día" and E.texto_lesion(5) == "5 días"
    assert E.texto_lesion(14) == "2 semanas" and E.texto_lesion(21) == "3 semanas"
    assert E.texto_lesion(60) == "2 meses" and E.texto_lesion(180) == "6 meses"
    assert E.texto_lesion(5, corto=True) == "5 d" and E.texto_lesion(21, corto=True) == "3 sem"
    assert E.texto_lesion(90, corto=True) == "3 m" and E.texto_lesion(0) == "0 días"


def test_cerrar_partido_ya_no_descuenta_lesion_y_sortea_dias():
    e = _e(); mi = e['mi_equipo']
    lesionado = mi.jugadores[0]; lesionado.lesion_dias = 20
    E.cerrar_partido(mi, {j.id: 90 for j in mi.jugadores[1:12]}, rng=random.Random(3), incidencias=[])
    assert lesionado.lesion_dias == 20                                       # no jugó y no se cura por partido
    nuevo = mi.jugadores[1]; nuevo.lesion_dias = 0
    inc = E.cerrar_partido(mi, {nuevo.id: 90}, incidencias=[{'tipo': 'lesion', 'jugador': nuevo, 'dias': 25}])
    assert nuevo.lesion_dias == 25 and inc[0]['dias'] == 25 and 'partidos' not in inc[0]


def test_cada_dia_cura_a_todos_y_avisa_solo_de_los_tuyos():
    e = _e(); D.hoy(e)
    mi, rival = e['mi_equipo'], e['liga'].equipos[1] if e['liga'].equipos[1] is not e['mi_equipo'] else e['liga'].equipos[2]
    a, b, r = mi.jugadores[0], mi.jugadores[1], rival.jugadores[0]
    a.lesion_dias, b.lesion_dias, r.lesion_dias = 2, 5, 1
    D.avanzar_dia(e)
    assert (a.lesion_dias, b.lesion_dias, r.lesion_dias) == (1, 4, 0)
    assert _altas(e) == []                                                   # el rival se curó: sin correo
    res = D.avanzar_dia(e)
    assert a.lesion_dias == 0 and b.lesion_dias == 3 and res['correos'] >= 1
    altas = _altas(e)
    assert len(altas) == 1 and a.apellido in altas[0]['asunto'] and altas[0]['accion']['pantalla'] == 'team_screen'
    D.avanzar_dia(e); D.avanzar_dia(e); D.avanzar_dia(e)
    assert b.lesion_dias == 0 and len(_altas(e)) == 2                        # uno por jugador, sin repetir


def test_sin_reloj_cada_jornada_cura_los_dias_de_una_jornada():
    e = _e(); mi = e['mi_equipo']
    j = mi.jugadores[0]; j.lesion_dias = 100
    E.recuperar_todos(e, 3.0)
    assert j.lesion_dias == 97
    E.recuperar_todos(e)                                                     # sin días: lo de una jornada
    assert 97 - 31 <= j.lesion_dias < 97                                     # una jornada dura entre 1 y ~30 días
    j.lesion_dias = 4
    altas = E.recuperar_todos(e, 10.0)
    assert j.lesion_dias == 0 and altas == [j] and len(_altas(e)) == 1


def test_un_partido_no_cura_ni_avisa():
    e = _e(); D.hoy(e); mi = e['mi_equipo']
    j = mi.jugadores[0]; j.lesion_dias = 10
    _jugar(e, 1)
    assert j.lesion_dias == 10 and _altas(e) == []


def test_el_correo_de_la_lesion_dice_el_tiempo():
    from alpha_football import vestuario as V
    e = _e(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    j = mi.jugadores[0]; j.lesion_dias = 0
    V.post_partido_user(e, mi, rival, 1, 0, [], {j.id: 90}, rng=random.Random(1),
                        incidencias=[{'tipo': 'lesion', 'jugador': j, 'jugador_id': j.id, 'dias': 21}])
    m = next(x for x in C.bandeja(e) if x['remitente'] == 'medico' and x['asunto'].startswith("Lesión:"))
    assert j.lesion_dias == 21 and "3 semanas" in m['cuerpo'] and "partido" not in m['cuerpo']


def test_un_save_viejo_en_partidos_se_convierte_a_dias():
    e = _e(); j = e['mi_equipo'].jugadores[0]
    datos = j.to_dict()
    datos.pop('lesion_dias', None); datos['lesion_partidos'] = 3
    assert Jugador.from_dict(datos).lesion_dias == 21
    datos.pop('lesion_partidos'); datos['lesionado'] = True
    assert Jugador.from_dict(datos).lesion_dias == 21
    j.lesion_dias = 40
    assert Jugador.from_dict(j.to_dict()).lesion_dias == 40 and 'lesion_dias' in j.to_dict()


def test_los_eventos_de_vestuario_lesionan_en_semanas():
    from alpha_football import eventos as EV
    e = _e(); a = e['mi_equipo'].jugadores[0]; a.lesion_dias = 0
    lineas = EV.aplicar(e, [('lesion', 'j', 2)], [a], random.Random(1))
    assert a.lesion_dias == 14 and "2 semanas" in lineas[0]


def test_las_pantallas_muestran_el_tiempo():
    from alpha_football.ui import league_screen as L
    e = _e(); mi = e['mi_equipo']
    t0 = mi.jugadores[e['alineacion_activa'].titulares[0]]
    t0.lesion_dias = 21
    avisos = L._alertas_inicio(e, mi)
    assert any(t0.apellido in t and "3 sem" in t for t, _c in avisos)


if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fail = 0
    for t in TESTS:
        try:
            t()
            print(f"  {t.__name__}: OK")
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
