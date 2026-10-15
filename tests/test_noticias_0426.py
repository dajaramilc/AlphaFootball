"""v0.4.26.0 (xd4): carreras al Balón de Oro y al Sudamericano separadas con media mínima, noticias "pide salir",
"ponen a X en transferibles" y "No ven a X en el equipo", riñas con varias redacciones, patrocinios "ofertas nuevas",
VER COPA en INICIO y sin "Simular resto" en ayuda y atajos."""
import sys, os, copy, random, inspect
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N, noticias_gen as G, premios as PR, salidas as S, correo as C
from alpha_football.paises import SUDAMERICA

_BASE = None


def _estado():
    """Carrera de la Premier con las 10 ligas (se copia: armarla cuesta unos segundos)."""
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
    return copy.deepcopy(_BASE)


class _Azar:
    """random.Random que siempre sortea 'sí' y elige el primero."""
    def random(self): return 0.0
    def choice(self, seq): return list(seq)[0]
    def randint(self, a, b): return a


def _media(j, valor: int) -> None:
    j.ataque = j.defensa = j.fisico = j.tecnica = j.mental = valor


def _poner(j, media: int, goles: int = 0, pj: int = 10) -> None:
    _media(j, media)
    j.partidos_jugados, j.goles, j.promedio_nota = pj, goles, 7.5


# --- premios: media mínima para ganar el Balón de Oro -------------------------------------------------------------

def _jug(nombre, ovr, goles=0, pj=20, nota=7.0, pos='DEL'):
    return NS(nombre=nombre, apellido='X', nombre_completo=f"{nombre} X", overall=ovr, goles=goles, asistencias=0,
              promedio_nota=nota, partidos_jugados=pj, posicion=pos, porterias_cero=0)


def _liga(tipo, clubes):
    eqs = [NS(nombre=n, jugadores=js, puntos=0, gf=0, gc=0) for n, js in clubes]
    return NS(tipo=tipo, nombre=tipo, equipos=eqs, num_jornadas=10)


def test_priorizar_por_media_pone_primero_a_los_que_llegan():
    items = [("a", 80), ("b", 90), ("c", 86), ("d", 70)]
    media = lambda c: c[1]
    assert [c[0] for c in PR.priorizar_por_media(items, media, 85.5)] == ["b", "c", "a", "d"]
    assert [c[0] for c in PR.priorizar_por_media(items, media, 0)] == ["a", "b", "c", "d"]      # sin mínimo no toca


def test_balon_de_oro_exige_media_y_el_sudamericano_no():
    estrella = _jug("Estrella", 90, goles=5)
    goleador = _jug("Goleador", 80, goles=30)
    liga = _liga('brasil', [("Club A", [estrella]), ("Club B", [goleador])])
    balon = PR.calcular_balon_de_oro({'brasil': liga}, {}, 1)
    assert balon['ganador']['nombre'] == "Estrella X"              # el de más goles no llega a 85.5 de media
    sud = PR.calcular_sudamericano({'brasil': liga}, {}, 1)
    assert sud['ganador']['nombre'] == "Goleador X"                # el Sudamericano no pide media mínima


def test_balon_de_oro_sin_nadie_que_llegue_compiten_los_de_mayor_media(caplog):
    flojos = [_jug(f"J{k}", 70 + k, goles=k) for k in range(12)]    # medias 70..81: nadie llega a 85.5
    chapuza = _jug("Chapuza", 60, goles=100)
    liga = _liga('premier', [("Club A", flojos + [chapuza])])
    balon = PR.calcular_balon_de_oro({'premier': liga}, {}, 1)
    assert balon['ganador']['nombre'] != "Chapuza X" and balon['ganador']['ovr'] >= 72
    assert "nadie llega" in caplog.text


# --- noticias: carreras separadas ---------------------------------------------------------------------------------

def test_carreras_balon_y_sudamericano_separadas(monkeypatch):
    e = _estado()
    liga = e['liga']
    n = int(liga.num_jornadas)
    estrella = liga.equipos[1].jugadores[0]
    _poner(estrella, 95, goles=30)
    tipo_sa = next(t for t, l in e['primera_division'].items() if t in SUDAMERICA and l is not None)
    brasileno = e['primera_division'][tipo_sa].equipos[0].jugadores[0]
    _poner(brasileno, 80, goles=25)
    ids_sa = {eq.id for mapa in (e['primera_division'], e['segunda_division']) for t, l in mapa.items()
              if t in SUDAMERICA and l is not None for eq in l.equipos}
    jornada = {'v': n // 2}
    monkeypatch.setattr(G, '_jornada_user', lambda estado: jornada['v'])

    assert G._candidatos_sudamericano(e, None) == 0                  # a mitad de temporada solo el Balón
    assert G._candidatos_balon(e, None) == 1
    premios = [x for x in N.lista(e) if x['tipo'] == 'premio']
    assert len(premios) == 1 and "Balón de Oro" in premios[0]['titular'] and "Sudamericano" not in premios[0]['titular']
    # v0.4.27.0: el nombre va en negrita ('**...**') y una línea en blanco separa a cada candidato
    assert f"1. **{estrella.nombre_completo}**" in premios[0]['cuerpo'] and "media 95" in premios[0]['cuerpo']
    assert G._candidatos_balon(e, None) == 0                         # una vez por temporada

    jornada['v'] = n * 3 // 4                                        # otra fecha: el Sudamericano
    assert G._candidatos_balon(e, None) == 0
    assert G._candidatos_sudamericano(e, None) == 1
    premios = [x for x in N.lista(e) if x['tipo'] == 'premio']
    sud = next(x for x in premios if "Sudamericano" in x['titular'])
    assert len(premios) == 2 and "Balón de Oro" not in sud['titular']
    assert f"1. **{brasileno.nombre_completo}**" in sud['cuerpo']
    assert sud['equipos_ids'] and set(sud['equipos_ids']) <= ids_sa   # solo clubes sudamericanos
    assert G._candidatos_sudamericano(e, None) == 0


# --- noticias: "X pide salir" -------------------------------------------------------------------------------------

def test_pide_salir_publica_una_vez_y_otra_si_vuelve_a_pedirlo():
    e = _estado()
    j = e['mi_equipo'].jugadores[3]
    j.pide_salir = True
    assert S.anunciar_pide_salir(e) == [j]
    nots = [x for x in N.lista(e) if x['tipo'] == 'vestuario' and "pide salir" in x['titular']]
    assert len(nots) == 1 and j.id in nots[0]['jugadores_ids'] and j.nombre in nots[0]['cuerpo']
    assert S.anunciar_pide_salir(e) == []                            # no repite mientras siga pidiéndolo
    S.limpiar(j)
    assert S.anunciar_pide_salir(e) == [] and e['datos_carrera']['pide_salir_noticiado'] == []
    j.pide_salir = True
    assert S.anunciar_pide_salir(e) == [j]                           # lo pide otra vez: otra noticia
    assert len([x for x in N.lista(e) if "pide salir" in x['titular']]) == 2


# --- noticias: "Sorpresa: ponen a X en transferibles" -------------------------------------------------------------

def test_transferibles_sorpresa_marca_caduca_y_no_repite(monkeypatch):
    e = _estado()
    mi = e['mi_equipo']
    ja = {'v': 50}
    monkeypatch.setattr(G, '_jornada_abs', lambda estado: ja['v'])
    assert G._transferibles(e, _Azar()) == 1
    nots = [x for x in N.lista(e) if "transferibles" in x['titular']]
    assert len(nots) == 1 and nots[0]['tipo'] == 'otro' and nots[0]['categoria'] == 'fichaje'
    pid = nots[0]['jugadores_ids'][0]
    marcado = next(j for eq, j in G._jugadores(e['liga']) if j.id == pid)
    assert marcado.transferible is True and marcado not in mi.jugadores
    assert G._transferibles(e, _Azar()) == 0                         # enfriamiento entre noticias
    ja['v'] += G.JORNADAS_TRANSFERIBLE                               # vence la marca y llega otro jugador
    assert G._transferibles(e, _Azar()) == 1
    assert marcado.transferible is False
    otros = [x for x in N.lista(e) if "transferibles" in x['titular']]
    assert len(otros) == 2 and otros[0]['jugadores_ids'] != otros[1]['jugadores_ids']


# --- noticias: "No ven a X en el equipo" ----------------------------------------------------------------------------

def test_no_ven_a_un_bueno_y_sano_una_vez_por_racha():
    e = _estado()
    eq = e['liga'].equipos[1]
    j = max(eq.jugadores, key=lambda x: x.overall)
    for x in eq.jugadores:
        _media(x, 60)                                                 # solo él es "bueno"
    _media(j, 85)
    j.lesion_dias, j.partidos_sancion = 0, 0
    assert G._no_ven(e, None) == 0                                   # empieza el rastreo
    eq.pj += 4                                                       # su club juega 4 y él no suma minutos
    assert G._no_ven(e, None) == 1
    nots = [x for x in N.lista(e) if x['tipo'] == 'vestuario' and x['titular'].startswith("No ven a")]
    assert len(nots) == 1 and j.id in nots[0]['jugadores_ids']
    eq.pj += 2
    assert G._no_ven(e, None) == 0                                   # la misma racha no se repite
    j.partidos_jugados += 1                                          # juega: la racha se corta
    eq.pj += 1
    assert G._no_ven(e, None) == 0
    eq.pj += 4                                                       # y vuelve a sentarse
    assert G._no_ven(e, None) == 1
    j.lesion_dias = 10                                               # lesionado: no es decisión del técnico
    eq.pj += 6
    assert G._no_ven(e, None) == 0 and G._clave_j(eq, j) not in e['datos_carrera']['noticias_gen']['sin_jugar']


# --- eventos: riñas con varias redacciones ------------------------------------------------------------------------

def test_rinas_tienen_varias_redacciones_y_el_sorteo_las_usa():
    from alpha_football import eventos as EV
    datos = dict(j="Ana Pérez", j2="Luis Gómez", club="Club", pais="País", dt="Míster")
    for id_ in ('rina', 'pelea_entreno'):
        variantes = EV.POR_ID[id_]['variantes']
        assert 6 <= len(variantes) <= 8
        assert len({a for a, _c in variantes}) == len(variantes)    # asuntos distintos
        for asunto, cuerpo in variantes:
            assert asunto.format(**datos) and cuerpo.format(**datos)
    e = _estado()
    e['mi_equipo'].jugadores[2].personalidad = 'polemico'
    for id_ in ('rina', 'pelea_entreno'):
        asuntos = set()
        for semilla in range(30):
            m = EV.sortear(e, random.Random(semilla), forzar=id_)
            assert m is not None
            asuntos.add(m['asunto'])
            m['evento']['resuelto'] = 0                              # que no quede pendiente
        assert len(asuntos) >= 4, (id_, asuntos)


# --- patrocinios: "ofertas nuevas" ----------------------------------------------------------------------------------

def test_patrocinios_a_mitad_de_temporada_avisa_ofertas_nuevas():
    from alpha_football import patrocinios as P
    e = _estado()
    liga = e['liga']
    p = P.datos(e)
    liga.jornada_actual = 1
    for c in p['contratos'].values():
        c['anios'] = 3
    p['contratos']['manga'].update(anios=1, cumplido_ultima=False)
    P.cierre_contratos(e, random.Random(14))
    liga.jornada_actual = 5                                          # cerró la ventana de inicio
    P.revisar_jornada(e)
    liga.jornada_actual = liga.num_jornadas // 2                     # ventana de invierno
    P.revisar_jornada(e, random.Random(15))
    asuntos = [m['asunto'] for m in C.bandeja(e) if m['remitente'] == 'patrocinador']
    assert any("ofertas nuevas" in a for a in asuntos) and not any("invierno" in a.lower() for a in asuntos)


# --- menú: VER COPA y sin "Simular resto" ------------------------------------------------------------------------

def test_ver_copa_lleva_a_otras_ligas_si_no_juegas_la_copa(monkeypatch):
    from alpha_football import competiciones as CP
    from alpha_football.ui import league_screen as L, otras_ligas_screen as O
    e = _estado()
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']      # sin el cartel del mercado (come clics)
    e['hub_tab'], e['hub_tabla_tab'] = 'inicio', 'copa'
    monkeypatch.setattr(CP, 'tipo_copa_user', lambda estado: None)
    assert L._sin_copa_continental(e) is True
    pygame.event.clear()
    assert L.render(screen, e) is None                               # se dibuja con solo el botón
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=L.R_VER_COPA.center))
    assert L.render(screen, e) == 'otras_ligas_screen'
    assert e['otras_ligas_copas'] is True and e['otras_ligas_copa_sel'] in ('champions', 'libertadores')
    pygame.event.clear()
    assert O.render(screen, e) is None                               # Otras ligas abre en la sección de copas


def test_sin_simular_resto_en_ayuda_y_atajos():
    from alpha_football.ui import atajos, ayuda
    assert "Simular resto" not in atajos.ATAJOS['copa_screen']
    assert "Simular resto" not in inspect.getsource(ayuda._ayuda_copa)
