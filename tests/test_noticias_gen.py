"""0.4.23.0: generadores de noticias (cada jornada y cierre de la temporada del user)."""
import sys, os, copy, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N
from alpha_football import noticias_gen as G
from alpha_football.ui import league_screen as L

_BASE = None


def _estado():
    """Carrera de la Premier con los calendarios de todas las ligas armados (se copia: cargarla cuesta ~3 s)."""
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
        L.inicializar_calendario_liga(_BASE['liga'])
        for liga in L._ligas_de_fondo(_BASE):
            L.inicializar_calendario_liga(liga)
    return copy.deepcopy(_BASE)


def _partido(liga, jornada, k=0):
    return [p for p in liga.calendario if p.jornada == jornada][k]


def _jugar(liga, p, gl, gv):
    p.goles_local, p.goles_visitante, p.jugado = gl, gv, True


def _equipo(liga, p, lado='local'):
    eid = p.local_id if lado == 'local' else p.visitante_id
    return next(eq for eq in liga.equipos if eq.id == eid)


class _Azar:
    """random.Random que siempre sortea 'sí' (para forzar los eventos probabilísticos)."""
    def random(self): return 0.0
    def choice(self, seq): return list(seq)[0]
    def randint(self, a, b): return a


def _de_tipo(e, tipo):
    return [n for n in N.lista(e) if n['tipo'] == tipo]


def test_goleada_publica_y_no_duplica():
    e = _estado()
    liga = e['liga']
    p = _partido(liga, 1)
    _jugar(liga, p, 6, 0)
    publicadas = G.generar_jornada(e, rng=random.Random(1))
    res = _de_tipo(e, 'resultado')
    assert publicadas >= 1 and len(res) == 1
    n = res[0]
    assert n['clave'] and "6-0" in n['titular'] and _equipo(liga, p).nombre in n['titular']
    assert n['importancia'] == 4 and n['categoria'] == 'resultado' and len(n['titular']) <= 60
    G.generar_jornada(e, rng=random.Random(1))
    assert len(_de_tipo(e, 'resultado')) == 1                            # el mismo hecho no se publica dos veces


def test_sorpresa_y_clasico():
    e = _estado()
    liga = e['liga']
    p = _partido(liga, 1)
    a, b = _equipo(liga, p), _equipo(liga, p, 'visitante')
    niveles = {a.id: 60, b.id: 75}
    _orig_nivel = G._nivel
    G._nivel = lambda eq: niveles.get(eq.id, 70)
    try:
        _jugar(liga, p, 1, 0)                                            # el flojo gana por 15 de diferencia
        G.generar_jornada(e, rng=random.Random(1))
        n = _de_tipo(e, 'resultado')[0]
        assert n['titular'].startswith("Sorpresa") and n['importancia'] == 4
    finally:
        G._nivel = _orig_nivel
    e2 = _estado()
    liga2 = e2['liga']
    p2 = _partido(liga2, 1)
    a2, b2 = _equipo(liga2, p2), _equipo(liga2, p2, 'visitante')
    a2.rival = b2.nombre
    _jugar(liga2, p2, 2, 1)
    G.generar_jornada(e2, rng=random.Random(1))
    n2 = _de_tipo(e2, 'resultado')[0]
    assert n2['titular'].startswith("Clásico") and n2['importancia'] in (3, 4)
    e3 = _estado()
    liga3 = e3['liga']
    for k in range(5):                                                   # 5 goleadas el mismo día: salen las 2 mejores
        _jugar(liga3, _partido(liga3, 1, k), 5 + k, 0)
    G.generar_jornada(e3, rng=random.Random(1))
    res = _de_tipo(e3, 'resultado')
    assert len(res) == 2 and any("9-0" in n['titular'] for n in res)


def test_otras_ligas_solo_la_mas_destacada():
    e = _estado()
    ajenas = L._ligas_de_fondo(e)
    _jugar(ajenas[0], _partido(ajenas[0], 1), 5, 0)
    _jugar(ajenas[1], _partido(ajenas[1], 1), 7, 0)
    G.generar_jornada(e, rng=random.Random(1))
    res = _de_tipo(e, 'resultado')
    assert len(res) == 1 and "7-0" in res[0]['titular'] and res[0]['importancia'] == 4


def test_lesion_grave_y_sin_repetir():
    e = _estado()
    liga = e['liga']
    j = liga.equipos[3].jugadores[0]
    for a in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental'):
        setattr(j, a, 85)
    j.lesion_dias = 30
    jornada = [3]
    _orig_abs = G._jornada_abs
    G._jornada_abs = lambda estado: jornada[0]
    try:
        G.generar_jornada(e, rng=random.Random(1))
        les = _de_tipo(e, 'lesion')
        assert len(les) == 1 and les[0]['importancia'] == 4 and j.apellido in les[0]['titular'] + les[0]['cuerpo']
        jornada[0] = 6                                                   # 3 jornadas después: no repite
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'lesion')) == 1
        jornada[0] = 12                                                  # 9 jornadas después: sí
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'lesion')) == 2
        j.lesion_dias = 10                                               # una lesión corta no es noticia
        jornada[0] = 40
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'lesion')) == 2
    finally:
        G._jornada_abs = _orig_abs


def test_promesas_cada_6_jornadas():
    e = _estado()
    liga = e['liga']
    # nadie más califica: se las quita a los demás jóvenes con potencial
    for lg in [liga] + L._ligas_de_fondo(e):
        for eq in lg.equipos:
            for x in eq.jugadores:
                x.edad = max(x.edad, 25)
    a, b = liga.equipos[2].jugadores[0], liga.equipos[5].jugadores[0]
    for x, pot in ((a, 92), (b, 88)):
        x.edad, x.potencial = 18, pot
        for at in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental'):
            setattr(x, at, 58)
    jornada = [6]
    _orig_abs = G._jornada_abs
    G._jornada_abs = lambda estado: jornada[0]
    try:
        G.generar_jornada(e, rng=random.Random(1))
        p1 = _de_tipo(e, 'promesa')
        assert len(p1) == 1 and a.apellido in p1[0]['titular'] + p1[0]['cuerpo'] and p1[0]['importancia'] == 3
        jornada[0] = 7
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'promesa')) == 1
        jornada[0] = 12
        G.generar_jornada(e, rng=random.Random(1))
        p2 = _de_tipo(e, 'promesa')
        assert len(p2) == 2 and b.apellido in p2[0]['titular'] + p2[0]['cuerpo']
        jornada[0] = 0                                                   # al empezar la temporada no hay nada que anunciar
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'promesa')) == 2
    finally:
        G._jornada_abs = _orig_abs


def test_candidatos_al_balon_una_vez():
    e = _estado()
    liga = e['liga']
    for k, goles in enumerate((20, 18, 15)):
        x = liga.equipos[k].jugadores[1]
        x.goles, x.partidos_jugados, x.promedio_nota = goles, 11, 8.0
    _orig_user = G._jornada_user
    G._jornada_user = lambda estado: liga.num_jornadas // 2
    try:
        G.generar_jornada(e, rng=random.Random(1))
        pr = [n for n in _de_tipo(e, 'premio')]
        assert len(pr) == 1 and pr[0]['importancia'] == 4 and "Balón de Oro" in pr[0]['titular']
        G.generar_jornada(e, rng=random.Random(1))
        assert len(_de_tipo(e, 'premio')) == 1                           # una vez por temporada
    finally:
        G._jornada_user = _orig_user


def test_records_cerca_y_superado():
    e = _estado()
    liga = e['liga']
    goleador = liga.equipos[1].jugadores[2]
    goleador.goles = 23                                                  # récord base 25: a 2 de distancia
    G.generar_jornada(e, rng=random.Random(1))
    rec = _de_tipo(e, 'record')
    assert len(rec) == 1 and rec[0]['importancia'] == 4
    G.generar_jornada(e, rng=random.Random(1))
    assert len(_de_tipo(e, 'record')) == 1                               # el aviso no se repite
    goleador.goles = 26
    G.generar_jornada(e, rng=random.Random(1))
    assert e['datos_carrera']['records']['goles']['valor'] == 26
    assert len(_de_tipo(e, 'record')) == 2 and "récord" in _de_tipo(e, 'record')[0]['titular'].lower()


def test_polemico_filtra_y_baja_moral():
    e = _estado()
    mi = e['mi_equipo']
    pol = mi.jugadores[4]
    pol.personalidad, pol.moral = 'polemico', 30
    antes = [j.moral for j in mi.jugadores]
    G.generar_jornada(e, rng=_Azar())
    v = _de_tipo(e, 'vestuario')
    assert len(v) == 1 and v[0]['importancia'] == 3 and pol.apellido in v[0]['titular'] + v[0]['cuerpo']
    assert [j.moral for j in mi.jugadores] == [max(0, m - 1) for m in antes]


def test_mover_moral():
    from alpha_football import prensa as P
    e = _estado()
    js = e['mi_equipo'].jugadores[:3]
    js[0].moral, js[1].moral, js[2].moral = 99, 0, 50
    js[2].causas_moral = [{'minutos': 0, 'equipo': 0, 'sueldo': 0}]
    P.mover_moral(js, +5)
    assert [j.moral for j in js] == [100, 5, 55]
    P.mover_moral(js, -7)
    assert [j.moral for j in js] == [93, 0, 48] and js[2].causas_moral[-1]['equipo'] == -7
    P.mover_moral([], -1)                                                # lista vacía: no rompe


def test_cierre_usa_temporada_explicita():
    e = _estado()
    e['temporada'] = 2
    liga = e['liga']
    movs = [{'tipo': 'premier', 'ascendidos': ['Club A'], 'descendidos': ['Club B']}]
    n = G.generar_cierre_temporada(e, 1, 'Manchester Billete', {'champions': 'FC Barcelona', 'libertadores': None}, movs)
    assert n >= 4
    assert all(x['temporada'] == 1 and x['jornada'] == liga.num_jornadas for x in N.lista(e))
    camp = _de_tipo(e, 'campeon')
    assert len(camp) == 2 and all(x['importancia'] == 5 for x in camp)   # liga + Champions; Libertadores sin campeón no sale
    assert any("Manchester Billete" in x['titular'] for x in camp)


def test_cierre_ascensos_user_y_resto():
    e = _estado()
    movs = [{'tipo': 'premier', 'ascendidos': ['Club A', 'Club B'], 'descendidos': ['Club C', 'Club D']},
            {'tipo': 'laliga', 'ascendidos': ['Club E'], 'descendidos': ['Club F']}]
    G.generar_cierre_temporada(e, 1, 'Manchester Billete', {}, movs)
    desc = _de_tipo(e, 'descenso')
    asc = [n for n in desc if n['categoria'] == 'ascenso']
    des = [n for n in desc if n['categoria'] == 'descenso']
    assert len(asc) == 1 and asc[0]['importancia'] == 5 and "Club A" in asc[0]['titular'] + asc[0]['cuerpo']
    assert len(des) == 2                                                  # tu país (imp. 5) + el resumen de los demás (imp. 4)
    mio = [n for n in des if n['importancia'] == 5]
    resto = [n for n in des if n['importancia'] == 4]
    assert len(mio) == 1 and "Club C" in mio[0]['titular'] + mio[0]['cuerpo']
    assert len(resto) == 1 and "España" in resto[0]['cuerpo'] and "Club F" in resto[0]['cuerpo']


def test_cierre_por_fases_campeones_antes_y_movimientos_despues():
    """En avanzar_nueva_temporada los ascensos y descensos se aplican DESPUÉS de cerrar la tabla: campeones y
    equipo del año salen antes del cambio de clubes; los movimientos, cuando ya existen."""
    e = _estado()
    liga = e['liga']
    e['temporada'] = 2
    antes = G.generar_cierre_temporada(e, 1, 'Manchester Billete', {}, None)
    assert antes >= 1 and not _de_tipo(e, 'descenso')                    # sin movimientos aún: solo campeón
    movs = [{'tipo': 'premier', 'ascendidos': ['Club A'], 'descendidos': ['Club C']}]
    despues = G.generar_cierre_movimientos(e, 1, movs)
    assert despues == 2 and len(_de_tipo(e, 'descenso')) == 2
    assert all(n['temporada'] == 1 and n['jornada'] == liga.num_jornadas for n in N.lista(e))
    assert G.generar_cierre_movimientos(e, 1, []) == 0
    assert G.generar_cierre_movimientos({}, 1, movs) == 0


def test_equipo_del_ano():
    e = _estado()
    liga = e['liga']
    for eq in liga.equipos:
        for k, x in enumerate(eq.jugadores):
            x.partidos_jugados, x.promedio_nota = liga.num_jornadas, 6.0 + (k % 7) / 10
    G.generar_cierre_temporada(e, 1, 'Manchester Billete', {}, [])
    eq = [n for n in _de_tipo(e, 'premio') if "Equipo del año" in n['titular']]
    assert len(eq) == 1 and eq[0]['importancia'] == 4
    assert "2026/27" in eq[0]['titular']                                 # el año real, no "temporada 1"
    lineas = [ln for ln in eq[0]['cuerpo'].split("\n") if ln.strip()]
    assert len(lineas) == 15                                             # 11 jugadores + 4 títulos de sección
    # v0.4.25.0: por línea (portero, defensas, medios, atacantes), un jugador por renglón con su club y su nota
    titulos = [ln for ln in lineas if ln.isupper()]
    assert titulos == ["PORTERO", "DEFENSAS", "MEDIOS", "ATACANTES"]
    cuenta = {}
    actual = None
    for ln in lineas:
        if ln.isupper():
            actual = ln
            cuenta[actual] = 0
        else:
            cuenta[actual] += 1
            assert ln.count(" · ") == 2                                  # nombre · club · nota
    assert cuenta == {"PORTERO": 1, "DEFENSAS": 4, "MEDIOS": 3, "ATACANTES": 3}
    assert "\n\n" in eq[0]['cuerpo']                                     # una línea en blanco entre secciones
    # v0.4.27.0: el nombre de cada jugador va en negrita y una línea en blanco lo separa del siguiente
    assert all(ln.startswith("**") and ln.count("**") == 2 for ln in lineas if not ln.isupper())
    assert eq[0]['cuerpo'].count("\n\n") == 3 + (4 - 1) + (3 - 1) + (3 - 1)       # 3 entre secciones + 3 + 2 + 2 entre jugadores
    vacio = _estado()                                                    # sin estadísticas: no inventa un equipo
    G.generar_cierre_temporada(vacio, 1, 'X', {}, [])
    assert not [n for n in _de_tipo(vacio, 'premio') if "Equipo del año" in n['titular']]


def _liga_con_lider(e, jugados_hasta, pts_lider=70, pts_segundo=60):
    """Marca como jugadas las jornadas 1..jugados_hasta y deja una tabla con un líder claro."""
    liga = e['liga']
    for p in liga.calendario:
        p.jugado = p.jornada <= jugados_hasta
        if p.jugado:
            p.goles_local = p.goles_visitante = 0                        # sin goleadas: no mezclar noticias de resultados
    for k, eq in enumerate(liga.equipos):
        eq.puntos, eq.gf, eq.gc = max(0, 40 - k), 10, 10
    lider, segundo = liga.equipos[0], liga.equipos[1]
    lider.puntos, segundo.puntos = pts_lider, pts_segundo
    return liga, lider, segundo


def test_titulo_asegurado_sale_en_el_momento_y_no_se_repite():
    e = _estado()
    liga, lider, segundo = _liga_con_lider(e, e['liga'].num_jornadas - 1)   # solo falta la última jornada
    G.generar_jornada(e, rng=random.Random(1))
    camp = [n for n in _de_tipo(e, 'campeon') if "asegura" in n['titular']]
    assert len(camp) == 1 and lider.nombre in camp[0]['titular'] and camp[0]['importancia'] == 5
    assert "puntos" in camp[0]['cuerpo'] and len(camp[0]['titular']) <= 60
    G.generar_jornada(e, rng=random.Random(1))
    assert len([n for n in _de_tipo(e, 'campeon') if "asegura" in n['titular']]) == 1
    # con la liga terminada se proclama campeón (una sola vez) y el cierre de temporada no lo repite
    for p in liga.calendario:
        p.jugado = True
        p.goles_local = p.goles_visitante = 0
    G.generar_jornada(e, rng=random.Random(1))
    G.generar_jornada(e, rng=random.Random(1))
    campeon = [n for n in _de_tipo(e, 'campeon') if "se proclama campeón" in n['titular']]
    assert len(campeon) == 1 and "2026/27" in campeon[0]['cuerpo']
    G.generar_cierre_temporada(e, 1, lider, {}, [])
    assert len([n for n in _de_tipo(e, 'campeon') if "campeón de" in n['titular']]) == 1


def test_titulo_no_se_asegura_si_el_segundo_aun_alcanza():
    e = _estado()
    liga, lider, segundo = _liga_con_lider(e, 0, pts_lider=70, pts_segundo=60)
    for p in liga.calendario:                                            # quedan 3 jornadas: 60 + 9 = 69 < 70 → asegurado
        p.jugado = p.jornada <= liga.num_jornadas - 3
        if p.jugado:
            p.goles_local = p.goles_visitante = 0
    assert G.estado_del_titulo(liga) is not None
    segundo.puntos = 62                                                  # 62 + 9 = 71 ≥ 70 → todavía se puede perder
    assert G.estado_del_titulo(liga) is None
    G.generar_jornada(e, rng=random.Random(1))
    assert not [n for n in _de_tipo(e, 'campeon') if "asegura" in n['titular'] or "proclama" in n['titular']]


def test_copa_se_anuncia_al_jugar_la_final_y_el_cierre_no_la_repite():
    from alpha_football import competiciones as CP
    e = _estado()
    c = e['datos_carrera'].setdefault('copas', {}).setdefault(
        'champions', {'tipo': 'champions', 'temporada': 1, 'campeon': None})
    c['campeon'] = 'Real Madrigal'
    assert G.anunciar_copa(e, c) == 1 and G.anunciar_copa(e, c) == 0
    n = [x for x in _de_tipo(e, 'campeon') if "Champions" in x['titular']]
    assert len(n) == 1 and n[0]['importancia'] == 5 and "Real Madrigal" in n[0]['titular']
    assert "2026/27" in n[0]['cuerpo'] and "temporada 1" not in n[0]['cuerpo']
    G.generar_cierre_temporada(e, 1, None, {'champions': 'Real Madrigal'}, [])
    assert len([x for x in _de_tipo(e, 'campeon') if "Champions" in x['titular']]) == 1
    assert G.anunciar_copa(e, None) == 0 and G.anunciar_copa(e, {'tipo': 'champions'}) == 0


def test_el_cierre_no_nombra_la_copa_del_otro_continente():
    """v0.4.27.0: con los continentes desfasados tu cierre solo nombra (si faltó) la copa de TU continente; la del
    otro ya se anunció cuando se ganó y su "último campeón conocido" no se repite meses después."""
    e = _estado()                                                         # Premier: tu continente es Europa → Champions
    assert G._copas_de_este_cierre(e, {'champions': 'A', 'libertadores': 'B'}) == {'champions', 'libertadores'}
    e['datos_carrera'].setdefault('mundo', {})['desfase'] = True
    assert G._copas_de_este_cierre(e, {'champions': 'A', 'libertadores': 'B'}) == {'champions'}
    G.generar_cierre_temporada(e, 1, None, {'champions': 'Real Madrigal', 'libertadores': 'Club Sudamericano'}, [])
    titulares = [x['titular'] + " " + x['cuerpo'] for x in _de_tipo(e, 'campeon')]
    assert any("Champions" in t and "Real Madrigal" in t for t in titulares)
    assert not any("Libertadores" in t or "Club Sudamericano" in t for t in titulares)


def test_descensos_de_otras_ligas_solo_nombran_a_los_mejores():
    e = _estado()
    liga_b = e['primera_division']['laliga']
    nombres = [eq.nombre for eq in liga_b.equipos][:6]
    for k, eq in enumerate(liga_b.equipos[:6]):
        eq.estrellas = 2.0 + k * 0.5                                    # el sexto es el de más peso
    movs = [{'tipo': 'laliga', 'ascendidos': [], 'descendidos': nombres},
            {'tipo': 'premier', 'ascendidos': ['Club A'], 'descendidos': ['Club C']}]
    G.generar_cierre_temporada(e, 1, None, {}, movs)
    resto = [n for n in _de_tipo(e, 'descenso') if n['importancia'] == 4]
    assert len(resto) == 1
    texto = resto[0]['titular'] + resto[0]['cuerpo']
    assert nombres[5] in texto and nombres[4] in texto and nombres[3] in texto and nombres[2] in texto
    assert nombres[0] not in texto and nombres[1] not in texto            # solo los 4 mejores
    assert "Ascensos y descensos en el resto" not in resto[0]['titular'] and "suben" not in resto[0]['cuerpo']
    assert nombres[5] in resto[0]['cuerpo'].split("\n\n")[1].split("\n")[0]    # el de más peso va primero
    assert G.publicar_descensos_destacados(e, [{'tipo': 'premier', 'descendidos': []}]) == 0


def test_un_generador_que_falla_no_frena_a_los_demas():
    e = _estado()
    liga = e['liga']
    _jugar(liga, _partido(liga, 1), 6, 0)
    original = G._lesiones
    G._lesiones = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("falla de prueba"))
    try:
        G.generar_jornada(e, rng=random.Random(1))
    finally:
        G._lesiones = original
    assert len(_de_tipo(e, 'resultado')) == 1


def test_guardado_viejo_y_json():
    e = _estado()
    e['datos_carrera'] = {}
    G.generar_jornada(e, rng=random.Random(1))
    dc = e['datos_carrera']
    assert 'noticias_gen' in dc and 'records' in dc
    json.dumps({'noticias_gen': dc['noticias_gen'], 'records': dc['records'], 'noticias': dc.get('noticias', [])})
    G.generar_cierre_temporada(e, 1, 'X', {'champions': 'Y'}, [{'tipo': 'premier', 'ascendidos': [], 'descendidos': []}])
    json.dumps(dc['noticias'])


def test_sin_liga_o_sin_calendario_no_lanza():
    assert G.generar_jornada({}) == 0
    assert G.generar_cierre_temporada({}, 1, None, None, None) == 0
    e = estado_carrera()                                                  # liga sin calendario armado
    e['liga'].calendario = []
    assert G.generar_jornada(e, rng=random.Random(1)) >= 0
    e['mi_equipo'] = None
    assert G.generar_jornada(e, rng=random.Random(1)) >= 0


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
