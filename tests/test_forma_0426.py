"""v0.4.26.0: forma de los jugadores (forma.py), su efecto en el progreso y el potencial, y sus avisos por correo."""
import sys, os, random, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from alpha_football import forma as FO
from alpha_football.models import Jugador, Equipo
from alpha_football.desarrollo import desarrollar_plantilla_post_partido, progresar_pasivo
from alpha_football.partido_ctx import clave


def jug(ovr=70, edad=25, pos='MED', **kw):
    return Jugador("Test", f"J{random.randint(0, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr, edad=edad,
                   id=random.randint(10**6, 10**7), resistencia=60, **kw)


def _equipo(jugadores):
    return Equipo(nombre="Test FC", ciudad="C", estrellas=3.0, estilo_dt="cruyffismo",
                  balance=1_000_000, jugadores=jugadores)


def _jugar(eq, js, nota):
    """Un partido en el que los `js` sacan exactamente `nota` (sin goles ni asistencias)."""
    st = {'jugaron': [clave(j) for j in js], 'goles': {}, 'asist': {}, 'notas': {clave(j): nota for j in js},
          'minutos': {}}
    return desarrollar_plantilla_post_partido(eq, 1, 0, rng=random.Random(1), stats_partido=st)


# --- niveles por promedio de notas ------------------------------------------------------------

def test_niveles_por_promedio_de_las_ultimas_notas():
    assert FO.nivel_por_notas([]) == 'normal'
    assert FO.nivel_por_notas([4.0, 4.0]) == 'normal'            # menos de 3 notas: sin forma
    assert FO.nivel_por_notas([5.0] * 3) == 'pesima'
    assert FO.nivel_por_notas([5.4] * 5) == 'pesima'
    assert FO.nivel_por_notas([5.6] * 5) == 'mala'
    assert FO.nivel_por_notas([5.8] * 5) == 'mala'
    assert FO.nivel_por_notas([5.9] * 5) == 'normal'
    assert FO.nivel_por_notas([6.7] * 5) == 'normal'
    assert FO.nivel_por_notas([6.9] * 5) == 'buena'
    assert FO.nivel_por_notas([9.0] * 5) == 'buena'              # imparable no sale del promedio
    # solo cuentan las últimas 5
    assert FO.nivel_por_notas([4.0] * 4 + [7.5] * 5) == 'buena'


def test_nivel_de_un_jugador_sin_datos_o_con_campos_ausentes():
    assert FO.nivel(types.SimpleNamespace()) == 'normal'
    assert FO.nivel(jug()) == 'normal'
    assert FO.nivel(jug(notas_recientes=[7.0] * 5)) == 'buena'
    assert FO.partidos_restantes(jug()) == 0


# --- racha imparable -----------------------------------------------------------------------------

def test_imparable_se_activa_con_tres_notas_seguidas_de_7_7():
    j = jug(potencial=80)
    assert FO.registrar_nota(j, 7.7) is None
    assert FO.registrar_nota(j, 7.6) is None                     # se rompe la serie
    assert FO.registrar_nota(j, 7.7) is None
    assert FO.registrar_nota(j, 7.9) is None
    assert FO.nivel(j) != 'imparable'
    assert FO.registrar_nota(j, 8.4) == {'tipo': 'entra'}
    assert FO.nivel(j) == 'imparable' and j.forma == 'imparable'
    assert j.imparable_partidos == 0 and FO.partidos_restantes(j) == FO.PARTIDOS_IMPARABLE


def test_imparable_dura_cinco_partidos_y_pasa_a_buena():
    j = jug(potencial=80)
    for _ in range(3):
        FO.registrar_nota(j, 8.0)
    media0 = j.overall
    for restantes in (4, 3, 2, 1):
        assert FO.registrar_nota(j, 6.0) is None
        assert FO.nivel(j) == 'imparable' and FO.partidos_restantes(j) == restantes
    for attr in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental'):   # lo que avanzó durante la racha
        setattr(j, attr, getattr(j, attr) + 3)
    j.potencial += 2
    ev = FO.registrar_nota(j, 6.0)
    assert ev == {'tipo': 'sale', 'media': j.overall - media0, 'potencial': 2} and ev['media'] == 3
    assert j.forma == 'buena' and FO.nivel(j) == 'buena'         # pasa a buena (aunque no tenga notas)
    assert j.imparable_partidos == 0 and FO.partidos_restantes(j) == 0
    FO.registrar_nota(j, 6.0)                                    # su siguiente partido: vuelve a salir de las notas
    assert FO.nivel(j) == 'normal'


def test_para_reactivar_hacen_falta_tres_notas_nuevas_despues_de_la_racha():
    j = jug(potencial=80)
    for _ in range(3):
        FO.registrar_nota(j, 8.0)
    for _ in range(FO.PARTIDOS_IMPARABLE):                       # notas altísimas DURANTE la racha: no cuentan
        ev = FO.registrar_nota(j, 9.5)
    assert ev and ev['tipo'] == 'sale' and j.racha_notas_altas == 0
    assert FO.registrar_nota(j, 8.0) is None
    assert FO.registrar_nota(j, 8.0) is None
    assert FO.nivel(j) != 'imparable'
    assert FO.registrar_nota(j, 8.0) == {'tipo': 'entra'}        # la tercera nueva la activa otra vez


def test_registrar_nota_tolera_objetos_sin_campos():
    ns = types.SimpleNamespace(notas_recientes=[])
    assert FO.registrar_nota(ns, 8.0) is None
    assert ns.forma_datos == {} and ns.racha_notas_altas == 1


# --- multiplicador de progreso ---------------------------------------------------------------------

def test_multiplicador_de_forma_moral_y_tope():
    assert FO.multiplicador_progreso(jug(), 'pesima') == 0.5
    assert FO.multiplicador_progreso(jug(), 'mala') == 0.75
    assert FO.multiplicador_progreso(jug(), 'normal') == 1.0
    assert FO.multiplicador_progreso(jug(), 'buena') == 1.5
    assert FO.multiplicador_progreso(jug(), 'imparable') == 2.0
    alto = jug(moral=85)                                         # moral >= 85: ×1.25
    assert FO.multiplicador_progreso(alto, 'normal') == 1.25
    assert abs(FO.multiplicador_progreso(alto, 'buena') - 1.875) < 1e-9
    assert abs(FO.multiplicador_progreso(alto, 'imparable') - 2.5) < 1e-9
    assert FO.multiplicador_progreso(jug(moral=84), 'normal') == 1.0
    assert FO.TOPE_MULT == 3.0


def _progreso_de(notas=None, moral=70, imparable=False, edad=25, canterano=''):
    """Progreso oculto que suma UN partido de nota 8.0 (DEL sin goles: inc 0.11) según la forma de entrada."""
    j = jug(pos='DEL', edad=edad, potencial=95, moral=moral, canterano=canterano, notas_recientes=list(notas or []))
    if imparable:
        j.forma, j.imparable_partidos = 'imparable', 0
    _jugar(_equipo([j]), [j], 8.0)
    return j.progreso_desarrollo


def test_el_progreso_por_partido_sigue_la_forma_y_la_moral():
    base = 0.11 * 0.40                                           # inc 0.11 × factor de edad 25 años
    esperado = {'pesima': 0.5, 'mala': 0.75, 'normal': 1.0, 'buena': 1.5, 'imparable': 2.0}
    assert abs(_progreso_de([5.0] * 5) - base * esperado['pesima']) < 1e-9
    assert abs(_progreso_de([5.6] * 5) - base * esperado['mala']) < 1e-9
    assert abs(_progreso_de() - base * esperado['normal']) < 1e-9
    assert abs(_progreso_de([7.0] * 5) - base * esperado['buena']) < 1e-9
    assert abs(_progreso_de(imparable=True) - base * esperado['imparable']) < 1e-9
    assert abs(_progreso_de([7.0] * 5, moral=85) - base * 1.5 * 1.25) < 1e-9


def test_tope_total_x3_incluye_al_canterano():
    # imparable ×2 · moral ×1.25 · canterano ×1.35 = 3.375 → tope ×3 (22 años: factor de edad 0.55)
    p = _progreso_de(imparable=True, moral=90, edad=22, canterano="Test FC")
    assert abs(p - 0.11 * 0.55 * 3.0) < 1e-9


# --- el reporte y los avisos -----------------------------------------------------------------------

def test_el_reporte_trae_la_forma_y_los_eventos_de_la_racha():
    j = jug(pos='DEL', potencial=95)
    eq = _equipo([j])
    entra = [_jugar(eq, [j], 8.0)[0]['forma_evento'] for _ in range(3)]
    assert entra == [None, None, {'tipo': 'entra'}]
    assert FO.nivel(j) == 'imparable'
    fin = [_jugar(eq, [j], 8.0)[0]['forma_evento'] for _ in range(FO.PARTIDOS_IMPARABLE)]
    assert fin[:-1] == [None] * (FO.PARTIDOS_IMPARABLE - 1)
    assert fin[-1]['tipo'] == 'sale' and fin[-1]['media'] >= 0 and fin[-1]['potencial'] >= 0
    assert j.forma == 'buena' and FO.nivel(j) == 'buena'


def test_correos_de_forma_solo_de_jugadores_de_tu_club():
    from alpha_football import vestuario as V, correo as C
    mio, ajeno = jug(), jug()
    mi = _equipo([mio])
    e = {'mi_equipo': mi, 'datos_carrera': {}}
    reporte = [{'obj': mio, 'forma_evento': {'tipo': 'entra'}},
               {'obj': ajeno, 'forma_evento': {'tipo': 'entra'}},          # de otro club: sin correo
               {'obj': mio, 'forma_evento': {'tipo': 'sale', 'media': 2, 'potencial': 1}},
               {'obj': mio, 'forma_evento': None}]
    V._correos_forma(e, mi, reporte)
    msgs = C.bandeja(e)
    assert len(msgs) == 2
    assert any('imparable' in m['asunto'].lower() for m in msgs)
    sale = next(m for m in msgs if 'racha' in m['asunto'].lower())
    assert '+2 de media / +1 de potencial' in sale['cuerpo']


# --- potencial durante la temporada (ítem 3) ---------------------------------------------------------

def _partidos_con_nota(j, n, nota):
    eq = _equipo([j])
    for _ in range(n):
        _jugar(eq, [j], nota)
    return eq


def test_joven_en_buena_forma_sube_potencial_en_la_temporada_con_tope():
    j = jug(ovr=70, edad=20, pos='DEL', potencial=80, notas_recientes=[7.0] * 5)
    eq = _partidos_con_nota(j, 100, 7.0)                         # buena forma todo el tiempo (promedio 7.0)
    assert j.potencial == 80 + FO.TOPE_POT_TEMPORADA and j.forma_datos['pot_temp'] == FO.TOPE_POT_TEMPORADA
    progresar_pasivo(eq, 1, random.Random(0))                    # temporada nueva: el contador vuelve a cero
    assert j.forma_datos['pot_temp'] == 0


def test_no_sube_potencial_por_forma_si_es_mayor_de_24_o_no_esta_en_forma():
    veterano = jug(ovr=70, edad=25, pos='DEL', potencial=80, notas_recientes=[7.0] * 5)
    _partidos_con_nota(veterano, 100, 7.0)
    assert veterano.potencial == 80
    normal = jug(ovr=70, edad=20, pos='DEL', potencial=80, notas_recientes=[6.0] * 5)
    _partidos_con_nota(normal, 100, 6.0)
    assert normal.potencial == 80


# --- saves viejos -------------------------------------------------------------------------------------

def test_save_viejo_sin_campos_de_forma_carga_con_defaults():
    viejo = {'nombre': 'Ana', 'apellido': 'Gol', 'posicion': 'DEL', 'ataque': 70, 'defensa': 60, 'fisico': 65,
             'tecnica': 70, 'mental': 68, 'notas_recientes': [7.0, 7.0, 7.0]}
    j = Jugador.from_dict(viejo)
    assert j.forma == '' and j.imparable_partidos == 0 and j.racha_notas_altas == 0 and j.forma_datos == {}
    assert FO.nivel(j) == 'buena'                                # se deriva de las notas
    raro = Jugador.from_dict(dict(viejo, forma='xyz', imparable_partidos=None, forma_datos='no'))
    assert raro.forma == '' and raro.imparable_partidos == 0 and raro.forma_datos == {}


def test_los_campos_de_forma_se_guardan_y_cargan():
    j = jug(potencial=80)
    j.forma, j.imparable_partidos, j.racha_notas_altas = 'imparable', 2, 1
    j.forma_datos = {'media0': 70, 'pot0': 80, 'pot_temp': 2}
    r = Jugador.from_dict(j.to_dict())
    assert (r.forma, r.imparable_partidos, r.racha_notas_altas) == ('imparable', 2, 1)
    assert r.forma_datos == {'media0': 70, 'pot0': 80, 'pot_temp': 2}
    assert FO.nivel(r) == 'imparable' and FO.partidos_restantes(r) == 3
