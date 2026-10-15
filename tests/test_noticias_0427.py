"""v0.4.27.0 (sesion4): negrita y líneas en blanco en noticias y correos, ficha del jugador desde NOTICIAS,
noticia de liberación (tuya y de la IA, con tope) y correo largo con desplazamiento."""
import sys, os, copy
from types import SimpleNamespace as NS_
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N, correo as C, negociacion as NG, cantera as CA
from alpha_football.models import Jugador
from alpha_football.ui import noticias_screen as NSC, correo_screen as CS, noticias_visual as V
from alpha_football.ui.theme import get_font

_BASE = None


def _estado():
    """Carrera de la Premier con las 10 ligas (se copia: armarla cuesta unos segundos)."""
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
    return copy.deepcopy(_BASE)


def _tecla(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def _frame(modulo, e):
    pygame.event.clear()
    return modulo.render(screen, e)


def _crack(ovr, jid=870000, apellido="De-prueba"):
    return Jugador(nombre="Crack", apellido=apellido, posicion='DEL', ataque=ovr, defensa=ovr, fisico=ovr,
                   tecnica=ovr, mental=ovr, moral=70, id=jid, edad=27)


# --- negrita ------------------------------------------------------------------------------------------------------

def test_negrita_se_quita_de_titulares_y_asuntos():
    e = _estado()
    assert N.negrita("Ana") == "**Ana**" and N.sin_marcas("a **b** c") == "a b c" and N.sin_marcas(None) == ""
    n = N.publicar(e, 'otro', "Hola **Ana** Pérez", "Cuerpo con **negrita**.")
    assert n['titular'] == "Hola Ana Pérez" and n['cuerpo'] == "Cuerpo con **negrita**."     # el cuerpo la conserva
    m = C.enviar(e, 'club', "Asunto **Ana**", "Cuerpo")
    assert m['asunto'] == "Asunto Ana"


def test_tramos_y_envolver_con_negrita():
    f, fb = get_font('sm'), V.fuente_negrita('sm')
    assert V.tramos("1. **Ana Pérez** (X)") == [("1. ", False), ("Ana Pérez", True), (" (X)", False)]
    texto = "1. **Marcos Alonso Fernández** (Real Madrid) · media 88, 12 goles, 5 asistencias, nota 7.4"
    lineas = V.envolver(texto, f, 260, 10)
    assert len(lineas) >= 2 and all(ln.count("**") % 2 == 0 for ln in lineas)             # marcas balanceadas por línea
    assert N.sin_marcas(" ".join(lineas)) == N.sin_marcas(texto)
    for ln in lineas:                                                   # cada línea cabe, midiendo la negrita (±4 px de kerning)
        assert sum((fb if neg else f).size(t)[0] for t, neg in V.tramos(ln)) <= 260 + 4
    cortado = V.envolver("**" + "palabra " * 40 + "**", f, 200, 2)
    assert len(cortado) == 2 and cortado[-1].endswith("…") and cortado[-1].count("**") % 2 == 0
    # un renglón en blanco entre jugadores se respeta con negrita
    assert V.envolver("**A** uno\n\n**B** dos", f, 400, 5) == ["**A** uno", "", "**B** dos"]


def test_dibujar_linea_con_negrita_no_lanza():
    s = pygame.Surface((400, 40))
    V.dibujar_linea(s, "**Ana** Pérez", (0, 0), size='sm', color='blanco', shadow=True)
    V.dibujar_linea(s, "sin marcas", (0, 20), size='xs', color='dorado')
    assert V.fuente_negrita('sm').size("Ana Pérez")[0] >= get_font('sm').size("Ana Pérez")[0]


# --- jugadores de una noticia -----------------------------------------------------------------------------------

def test_jugadores_de_busca_por_nombre_en_cualquier_club():
    e = _estado()
    mi, otro_club = e['mi_equipo'], e['liga'].equipos[3]
    mio, ajeno = mi.jugadores[2], otro_club.jugadores[4]
    n = N.publicar(e, 'otro', "T", "C", jugadores=[mio, ajeno])
    assert n['jugadores_ids'] == [mio.id, ajeno.id] and n['jugadores_nombres'] == [mio.nombre_completo, ajeno.nombre_completo]
    refs = N.jugadores_de(e, n)
    assert refs[0][0] is mio and refs[0][1] == mi.nombre
    assert refs[1][0] is ajeno and refs[1][1] == otro_club.nombre
    # el que se fue a la bolsa de libres sigue encontrándose
    otro_club.jugadores.remove(ajeno)
    e.setdefault('free_agents_list', []).append(ajeno)
    assert N.jugadores_de(e, n)[1] == (ajeno, "Agente libre")
    # el que ya no existe se omite
    e['free_agents_list'].remove(ajeno)
    assert [x[0] for x in N.jugadores_de(e, n)] == [mio]
    # noticia vieja (sin nombres): solo tu plantilla, por id
    viejo = {'jugadores_ids': [mio.id, 987654]}                # (un id suelto de otro club no se puede ubicar)
    assert [x[0] for x in N.jugadores_de(e, viejo)] == [mio]
    assert N.jugadores_de(e, {}) == []
    # un dato sin id (la ficha del Balón de Oro) se encuentra por nombre
    ficha = {'nombre': mio.nombre_completo, 'equipo': mi.nombre}
    n2 = N.publicar(e, 'premio', "Balón", "C", jugadores=[ficha])
    assert n2['jugadores_ids'] == [-1] and N.jugadores_de(e, n2)[0][0] is mio


# --- ficha desde NOTICIAS ---------------------------------------------------------------------------------------

def test_enter_en_noticia_de_jugador_abre_su_ficha():
    e = _estado()
    mio = e['mi_equipo'].jugadores[1]
    n = N.publicar(e, 'otro', "Noticia de un jugador", "Cuerpo corto.", jugadores=[mio],
                   accion=C.accion('buscador_screen', "VER BUSCADOR"))
    NSC.abrir(e, n['id'])
    assert _frame(NSC, e) is None
    assert NSC.tiene_jugadores(n) and NSC.rect_ver_ficha(n).y < NSC.R_ACCION.y        # los dos botones, apilados
    _tecla(pygame.K_RETURN)
    assert NSC.render(screen, e) is None and e['_noticias_ficha']['refs'][0][0] is mio  # no fue al buscador
    assert _frame(NSC, e) is None                                                      # y se dibuja
    _tecla(pygame.K_ESCAPE)
    assert NSC.render(screen, e) is None and not e.get('_noticias_ficha')              # Esc cierra el overlay, no la pantalla


def test_noticia_sin_jugadores_sigue_yendo_a_su_boton():
    e = _estado()
    n = N.publicar(e, 'economia', "Sin jugadores", "Cuerpo.", accion=C.accion('buscador_screen', "VER BUSCADOR"))
    NSC.abrir(e, n['id'])
    _frame(NSC, e)
    _tecla(pygame.K_RETURN)
    assert NSC.render(screen, e) == 'buscador_screen'


def test_ficha_con_varios_jugadores_cicla_y_avisa_si_ya_no_estan():
    e = _estado()
    js = e['mi_equipo'].jugadores[:3]
    n = N.publicar(e, 'premio', "Tres", "Cuerpo.", jugadores=js)
    NSC.abrir(e, n['id'])
    _frame(NSC, e)
    _tecla(pygame.K_RETURN); NSC.render(screen, e)
    assert e['_noticias_ficha']['idx'] == 0
    _tecla(pygame.K_RIGHT); NSC.render(screen, e)
    assert e['_noticias_ficha']['idx'] == 1
    _tecla(pygame.K_LEFT); NSC.render(screen, e)
    _tecla(pygame.K_LEFT); NSC.render(screen, e)
    assert e['_noticias_ficha']['idx'] == 2                                             # da la vuelta
    _tecla(pygame.K_RETURN); NSC.render(screen, e)
    assert not e.get('_noticias_ficha')
    # un jugador que ya no existe: aviso breve y sin overlay
    fantasma = N.publicar(e, 'otro', "Fantasma", "Cuerpo.", jugadores=[{'id': 999999, 'nombre_completo': "Nadie Existe"}])
    NSC.abrir(e, fantasma['id'])
    _frame(NSC, e)
    _tecla(pygame.K_RETURN); NSC.render(screen, e)
    assert not e.get('_noticias_ficha') and e.get('noticias_aviso')


def test_cuerpo_de_once_jugadores_cabe_en_el_detalle():
    secciones = (("PORTERO", 1), ("DEFENSAS", 4), ("MEDIOS", 3), ("ATACANTES", 3))
    bloques = []
    for titulo, n in secciones:
        bloques.append(titulo + "\n" + "\n\n".join(f"{N.negrita('Nombre Apellido ' + str(i))} · Club de Prueba · 7.{i}"
                                                   for i in range(n)))
    cuerpo = "\n\n".join(bloques)
    disponible = NSC.R_TEXTO.bottom - 8 - (NSC.R_TEXTO.y + 32 + 56 + 6 + 34)           # titular de 2 líneas
    tam, lineas, hueco = NSC._cuerpo_ajustado(cuerpo, NSC.R_TEXTO.width, disponible)
    f = get_font(tam)
    assert not any(ln.endswith("…") for ln in lineas) and len([ln for ln in lineas if ln]) == 15
    assert sum(f.get_linesize() if ln else hueco for ln in lineas) <= disponible


# --- liberaciones: noticia -------------------------------------------------------------------------------------

def test_liberacion_de_la_ia_filtra_por_media_y_tiene_tope():
    e = _estado()
    mia = e['liga'].equipos[2].nombre
    ajena = "Club de Otra Liga"
    NG.registrar_pase(e, _crack(79, 1), ajena, 'Libre', 0, False)               # menos de 80 y de otra liga: nada
    assert not [n for n in N.lista(e) if n.get('liberacion')]
    NG.registrar_pase(e, _crack(77, 2), mia, 'Libre', 0, False)                 # de tu liga basta con 76
    (n,) = [x for x in N.lista(e) if x.get('liberacion')]
    assert n['importancia'] == 3 and n['tipo'] == 'otro' and n['categoria'] == 'fichaje' and n['equipos_ids']
    assert n['jugadores_ids'] == [2] and not n['propio']
    for k, ovr in enumerate((81, 82, 83)):                                      # tope: quedan las 2 de más puntaje
        NG.registrar_pase(e, _crack(ovr, 10 + k), ajena, 'Libre', 0, False)
    libs = [x for x in N.lista(e) if x.get('liberacion')]
    assert len(libs) == NG.MAX_LIBERACIONES_IA_JORNADA
    assert sorted(x['media'] for x in libs) == [82, 83]
    NG.registrar_pase(e, _crack(80, 20), ajena, 'Libre', 0, False)              # más floja que las que hay: no entra
    assert len([x for x in N.lista(e) if x.get('liberacion')]) == NG.MAX_LIBERACIONES_IA_JORNADA
    assert not [x for x in N.lista(e) if x['tipo'] == 'fichaje']                # no cuentan como fichajes
    NG.registrar_pase(e, _crack(90, 21), ajena, 'Libre (fin de contrato)', 0, False)   # fin de contrato: no es noticia
    assert len([x for x in N.lista(e) if x.get('liberacion')]) == NG.MAX_LIBERACIONES_IA_JORNADA


# --- correo: negrita y desplazamiento ---------------------------------------------------------------------------

def test_correo_largo_se_recorre_con_repag_y_rueda():
    e = _estado()
    mi = e['mi_equipo']
    cuerpo = "Altas:\n" + "\n\n".join(f"{N.negrita(j.nombre_completo)} ({j.posicion}, 17 años, media 60)"
                                      for j in mi.jugadores[:12])
    C.enviar(e, 'cantera', "Informe largo", cuerpo)
    C.enviar(e, 'club', "Otro mensaje", "Corto.")
    e.pop('correo_canal', None)
    e['correo_sel'] = 1                                                        # el informe (el más viejo)
    assert _frame(CS, e) is None
    assert len(CS._envolver(C.formatear(e, C.bandeja(e)[1]), CS.R_MSG.width - 40)) > CS.LINEAS_CUERPO
    _tecla(pygame.K_PAGEDOWN); CS.render(screen, e)
    assert e['correo_scroll'] == CS.SALTO_CUERPO
    _tecla(pygame.K_PAGEUP); CS.render(screen, e)
    assert e['correo_scroll'] == 0
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
    CS.render(screen, e)
    assert e['correo_scroll'] == 3
    _tecla(pygame.K_PAGEDOWN); CS.render(screen, e)
    _tecla(pygame.K_PAGEDOWN); CS.render(screen, e)
    _tecla(pygame.K_PAGEDOWN); CS.render(screen, e)
    n_lineas = len(CS._envolver(C.formatear(e, C.bandeja(e)[1]), CS.R_MSG.width - 40))
    assert 0 < e['correo_scroll'] <= n_lineas                                  # nunca más allá del final
    _tecla(pygame.K_UP); CS.render(screen, e)                                   # otro mensaje: vuelve al principio
    assert e['correo_scroll'] == 0


def test_cantera_informe_con_nombres_en_negrita_y_un_jugador_por_parrafo():
    e = _estado()
    js = e['mi_equipo'].jugadores
    res = {'joya': None, 'llegan': [js[0], js[1]], 'se_van': [(js[2], 'edad')], 'mejoran': [(js[3], 3)]}
    CA._correo_informe(e, res)
    cuerpo = C.bandeja(e)[0]['cuerpo']
    assert f"Altas:\n**{js[0].nombre_completo}**" in cuerpo and "; " not in cuerpo
    assert f"**{js[1].nombre_completo}**" in cuerpo and f"**{js[2].nombre_completo}** (cumplió la edad límite)" in cuerpo
    assert f"**{js[3].nombre_completo}** (+3, media" in cuerpo
    assert cuerpo.count("\n\n") == 3                                            # entre las dos altas y entre los 3 bloques
    previa = " ".join(C.sin_marcas(cuerpo).split())
    assert "**" not in previa


# --- favoritos desde la ficha (ronda 2) -------------------------------------------------------------------------

def test_helpers_de_favorito_en_ficha_jugador():
    from alpha_football.ui import ficha_jugador as FJ
    e = _estado()
    mio, ajeno = e['mi_equipo'].jugadores[0], e['liga'].equipos[3].jugadores[4]
    assert FJ.puede_ser_favorito(e, ajeno) and not FJ.puede_ser_favorito(e, mio) and not FJ.puede_ser_favorito(e, None)
    assert FJ.alternar_favorito(e, mio) is None and not NG.es_favorito(e, mio)       # los tuyos no se siguen
    assert "agregado a" in FJ.alternar_favorito(e, ajeno) and NG.es_favorito(e, ajeno)
    assert "quitado de" in FJ.alternar_favorito(e, ajeno) and not NG.es_favorito(e, ajeno)
    FJ.alternar_favorito(e, ajeno)
    FJ.alternar_favorito(e, ajeno)
    FJ.alternar_favorito(e, ajeno)
    assert e['datos_carrera']['favoritos'].count(ajeno.nombre_completo) == 1         # nunca duplicado
    FJ.dibujar_boton_favorito(screen, pygame.Rect(0, 0, 360, 44), e, ajeno, (0, 0))   # se dibuja sin fallar
    FJ.dibujar_boton_favorito(screen, pygame.Rect(0, 0, 360, 44), e, mio, (0, 0))     # y no dibuja nada con un propio


def test_f_y_clic_en_la_ficha_de_noticias_agregan_y_quitan_favorito():
    e = _estado()
    ajeno, mio = e['liga'].equipos[3].jugadores[4], e['mi_equipo'].jugadores[0]
    n = N.publicar(e, 'otro', "Ajeno", "Cuerpo.", jugadores=[ajeno])
    NSC.abrir(e, n['id'])
    _frame(NSC, e)
    _tecla(pygame.K_RETURN); NSC.render(screen, e)
    assert e['_noticias_ficha']['refs'][0][0] is ajeno and not NG.es_favorito(e, ajeno)
    _tecla(pygame.K_f); NSC.render(screen, e)
    assert NG.es_favorito(e, ajeno) and "agregado a" in e['_noticias_ficha']['msg'][0]
    assert _frame(NSC, e) is None                                                   # y se dibuja con "QUITAR DE FAVORITOS"
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=NSC.rects_overlay_ficha()['favorito'].center))
    NSC.render(screen, e)
    assert not NG.es_favorito(e, ajeno) and e.get('_noticias_ficha')                # el clic lo quita y la ficha sigue abierta
    # un jugador tuyo: F no hace nada
    n2 = N.publicar(e, 'otro', "Mio", "Cuerpo.", jugadores=[mio])
    NSC.abrir(e, n2['id'])
    _frame(NSC, e)
    _tecla(pygame.K_RETURN); NSC.render(screen, e)
    _tecla(pygame.K_f); NSC.render(screen, e)
    assert not NG.es_favorito(e, mio) and 'msg' not in e['_noticias_ficha']


def test_ojeador_favorito_con_f_y_con_clic():
    from alpha_football.ui import ojeador_screen as OJ
    e = _estado()
    mi, club = e['mi_equipo'], e['liga'].equipos[3]
    ajeno = club.jugadores[4]
    clave = (tuple(NG._clave_ventana(e)), int(mi.balance), len(mi.jugadores))
    e['_ojeador_recs'] = (clave, [(ajeno, club, "Premier", 1_000_000, "Mejora tu puesto más flojo.")])
    pygame.event.clear()
    assert OJ.render(screen, e) is None
    _tecla(pygame.K_f)
    assert OJ.render(screen, e) is None and NG.es_favorito(e, ajeno)                 # F: la tarjeta con foco
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=OJ._rects_favorito(1)[0].center))
    assert OJ.render(screen, e) is None and not NG.es_favorito(e, ajeno)             # clic en el botón: no abre la negociación


def test_negociacion_favorito_con_f_y_no_con_jugadores_propios():
    from alpha_football.ui import negociacion_screen as NEG
    e = _estado()
    club = e['liga'].equipos[3]
    ajeno, mio = club.jugadores[4], e['mi_equipo'].jugadores[0]
    assert NG.iniciar_negociacion(e, ajeno, club, 'fichaje', 'league_screen') == 'negociacion_screen'
    _frame(NEG, e)
    _tecla(pygame.K_f)
    assert NEG.render(screen, e) is None and NG.es_favorito(e, ajeno)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=NEG._rects()['favorito'].center))
    assert NEG.render(screen, e) is None and not NG.es_favorito(e, ajeno)
    NG.iniciar_negociacion(e, mio, None, 'renovar', 'league_screen')                  # renovar a uno tuyo: sin favoritos
    _frame(NEG, e)
    _tecla(pygame.K_f)
    NEG.render(screen, e)
    assert not NG.es_favorito(e, mio)


TESTS = [test_negrita_se_quita_de_titulares_y_asuntos, test_tramos_y_envolver_con_negrita,
         test_dibujar_linea_con_negrita_no_lanza, test_jugadores_de_busca_por_nombre_en_cualquier_club,
         test_enter_en_noticia_de_jugador_abre_su_ficha, test_noticia_sin_jugadores_sigue_yendo_a_su_boton,
         test_ficha_con_varios_jugadores_cicla_y_avisa_si_ya_no_estan, test_cuerpo_de_once_jugadores_cabe_en_el_detalle,
         test_liberacion_de_la_ia_filtra_por_media_y_tiene_tope, test_correo_largo_se_recorre_con_repag_y_rueda,
         test_cantera_informe_con_nombres_en_negrita_y_un_jugador_por_parrafo,
         test_helpers_de_favorito_en_ficha_jugador, test_f_y_clic_en_la_ficha_de_noticias_agregan_y_quitan_favorito,
         test_ojeador_favorito_con_f_y_con_clic, test_negociacion_favorito_con_f_y_no_con_jugadores_propios]


if __name__ == '__main__':
    fallas = 0
    for t in TESTS:
        try:
            t()
            print(f"  {t.__name__}: OK")
        except Exception as exc:                      # noqa: BLE001
            fallas += 1
            print(f"  {t.__name__}: FALLA {exc!r}")
    print("TODO OK" if not fallas else f"{fallas} fallas")
    sys.exit(1 if fallas else 0)
