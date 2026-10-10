"""v0.4.10.0: eventos aleatorios de vestuario (sorteo, efectos, decisión, noticias)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import correo as C, eventos as EV, sanciones as S


_CACHE = {}


def _base(mal=False):
    """Estado de carrera reutilizado (cargarlo cuesta ~1 s y hay tests con cientos de sorteos):
    cada llamada lo deja como nuevo (plantilla copiada, datos_carrera y correo vacíos)."""
    import copy
    if not _CACHE:
        e0 = estado_carrera()
        _CACHE.update(e=e0, jugadores=copy.deepcopy(e0['mi_equipo'].jugadores),
                      balance=e0['mi_equipo'].balance, jornada=e0['liga'].jornada_actual)
    e = _CACHE['e']
    e['mi_equipo'].jugadores[:] = copy.deepcopy(_CACHE['jugadores'])
    e['mi_equipo'].balance = _CACHE['balance']
    e['liga'].jornada_actual = _CACHE['jornada']
    e['datos_carrera'] = {}
    e.pop('correo_canal', None); e.pop('correo_sel', None); e.pop('correo_opc', None)
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
    if mal:
        e['datos_carrera']['ult_res'] = ['P', 'P', 'E']
    return e


def test_va_mal_por_derrotas():
    assert not EV.va_mal(_base())
    assert EV.va_mal(_base(mal=True))


def test_aplicar_efectos_basicos():
    e = _base(); js = e['mi_equipo'].jugadores; a, b = js[0], js[1]
    saldo = e['mi_equipo'].balance
    lineas = EV.aplicar(e, [('moral', 'j', -10), ('moral', 'plantel', 2), ('energia', 'j', -20),
                            ('sancion', 'j', 2), ('lesion', 'j2', 1), ('forma', 'j', 5.0),
                            ('progreso', 'j2', 0.4), ('dinero', 'j', 0.02), ('confianza', None, -3),
                            ('texto', "Nada más.")], [a, b], random.Random(1))
    assert a.moral == 62 and b.moral == 72 and a.energia == 80.0
    assert S.partidos_sancion(a, 'liga') == 2 and b.lesion_dias == 7      # 1 = una semana
    assert a.notas_recientes[-1] == 5.0 and abs(b.progreso_desarrollo - 0.4) < 1e-9
    assert e['mi_equipo'].balance == saldo + int(a.salario * 0.02)
    assert len(lineas) == 10 and lineas[-1] == "Nada más."


def test_aplicar_acota_y_otros():
    e = _base(); js = e['mi_equipo'].jugadores
    js[0].moral, js[0].energia = 3, 5.0
    EV.aplicar(e, [('moral', 'j', -50), ('energia', 'j', -50), ('energia', 'otros:3', -15)], [js[0]], random.Random(2))
    assert js[0].moral == 0 and js[0].energia == 0.0
    assert sum(1 for j in js[1:] if j.energia == 85.0) == 3


def test_rina_domina_con_polemico_y_mala_racha():
    # con el catálogo completo la riña (peso 60 vs 3-10 de cada otro) es el evento más probable, por mucho
    from collections import Counter
    cuenta = Counter()
    for s in range(300):
        e = _base(mal=True)
        e['mi_equipo'].jugadores[4].personalidad = 'polemico'
        m = EV.sortear(e, random.Random(s))
        if m:
            cuenta[m['evento']['id']] += 1
    (top, n_top), (_otro, n_otro) = cuenta.most_common(2)
    assert top == 'rina' and n_top >= 3 * n_otro, cuenta


def test_sin_polemico_no_hay_rina_y_no_rompe():
    e = _base(mal=True)
    assert EV.sortear(e, random.Random(1), forzar='rina') is None


def test_probabilidad_mayor_si_va_mal():
    def tasa(mal):
        n = 0
        for s in range(300):
            e = _base(mal=mal); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
            n += EV.sortear(e, random.Random(s)) is not None
        return n
    assert tasa(True) > tasa(False)


def test_resolver_aplica_registra_noticia_y_no_repite():
    e = _base(mal=True); pol = e['mi_equipo'].jugadores[4]; pol.personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    assert m['remitente'] == 'jugador' and C.canal(m) == 'mensaje' and len(m['evento']['opciones']) == 3
    assert EV.pendiente(e) is m and EV.sortear(e, random.Random(2), forzar='rina') is None   # hay uno pendiente
    lineas = EV.resolver(e, m['id'], 1, random.Random(3))                # apartar 2 partidos
    assert lineas and S.partidos_sancion(pol, 'liga') == 2
    assert m['evento']['resuelto'] == 1 and m['evento']['resumen'] == lineas
    n = EV.noticias(e)
    assert len(n) == 1 and n[0]['evento'] == 'rina' and n[0]['opcion'] == 1 and n[0]['titular'] and n[0]['cuerpo']
    assert pol.id in n[0]['jugadores']
    assert EV.resolver(e, m['id'], 0) == [] and len(EV.noticias(e)) == 1  # ya resuelto: nada
    e['datos_carrera']['eventos_vistos']['rina'] = EV._abs(e)             # enfriamiento de 6 jornadas
    assert all((x[0]['id'] != 'rina') for x in EV._candidatos(e, random.Random(5)))


def test_pendiente_se_resuelve_por_defecto():
    e = _base(mal=True); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    assert EV.resolver_pendientes(e, random.Random(1)) == 1
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1


def test_protagonista_que_ya_no_esta():
    e = _base(mal=True); pol = e['mi_equipo'].jugadores[4]; pol.personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    e['mi_equipo'].jugadores.remove(pol)
    assert EV.resolver(e, m['id'], 0)                 # devuelve la línea de cierre, sin excepción
    assert m['evento']['resuelto'] == -1
    # v0.4.10.0: sin efectos, pero deja igual su noticia (con el nombre y el club) para NOTICIAS
    n = EV.noticias(e)
    assert len(n) == 1 and n[0]['evento'] == 'rina' and n[0]['opcion'] == -1
    assert pol.id in n[0]['jugadores'] and EV._nom(pol) in n[0]['titular'] and n[0]['cuerpo']
    club = e['mi_equipo'].nombre
    assert club in n[0]['titular'] + n[0]['cuerpo'] and '{' not in n[0]['titular'] + n[0]['cuerpo']
    assert EV.resolver(e, m['id'], 0) == [] and len(EV.noticias(e)) == 1      # ya cerrado: no duplica


def test_cierre_por_defecto_sin_uno_de_los_dos_protagonistas():
    e = _base()
    m = EV.sortear(e, random.Random(1), forzar='pelea_entreno')
    ids = m['evento']['protagonistas']
    js = e['mi_equipo'].jugadores
    se_fue = next(j for j in js if j.id == ids[1])
    otro = next(j for j in js if j.id == ids[0])
    js.remove(se_fue)
    assert EV.resolver_pendientes(e, random.Random(1)) == 1                   # sin decidir: por defecto
    n = EV.noticias(e)
    assert len(n) == 1 and n[0]['jugadores'] == ids and n[0]['opcion'] == -1
    assert EV._nom(se_fue) in n[0]['titular'] and EV._nom(otro) not in n[0]['titular']


def test_cierre_sin_nombres_guardados_o_con_evento_desconocido_deja_noticia():
    e = _base(mal=True); pol = e['mi_equipo'].jugadores[4]; pol.personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    m['evento'].pop('nombres')                                    # correo de un save viejo
    e['mi_equipo'].jugadores.remove(pol)
    EV.resolver(e, m['id'], 0)
    n = EV.noticias(e)
    assert len(n) == 1 and n[0]['titular'] and n[0]['cuerpo'] and n[0]['opcion'] == -1
    e2 = _base(mal=True); e2['mi_equipo'].jugadores[4].personalidad = 'polemico'
    m2 = EV.sortear(e2, random.Random(1), forzar='rina')
    m2['evento']['id'] = 'evento_que_ya_no_existe'               # el catálogo cambió entre versiones
    assert EV.resolver(e2, m2['id'], 0) and m2['evento']['resuelto'] == -1
    n2 = EV.noticias(e2)
    assert len(n2) == 1 and n2[0]['titular'] and n2[0]['cuerpo'] and '{' not in n2[0]['titular'] + n2[0]['cuerpo']


def test_ult_res_lo_lleva_el_vestuario():
    import inspect
    from alpha_football import vestuario
    assert "ult_res" in inspect.getsource(vestuario.post_partido_user)


IDS = ['rina', 'pelea_entreno', 'salida_nocturna', 'llega_tarde', 'critica_prensa', 'charla_lider',
       'exige_titular', 'lesion_entreno', 'gripe', 'nace_hijo', 'seleccion', 'nostalgia', 'entreno_extra',
       'escandalo_redes', 'rumor_oferta', 'prima_capitan', 'asado', 'hinchas', 'juvenil_deslumbra',
       'mentor', 'insulta_arbitro']


def _plantel_variado():
    e = _base(mal=True); js = e['mi_equipo'].jugadores
    js[0].personalidad = 'polemico'; js[1].personalidad = 'lider'; js[2].personalidad = 'profesional'
    js[3].personalidad = 'mercenario'; js[4].moral = 40
    js[5].jornadas_sin_jugar = 4; js[5].ataque = js[5].defensa = js[5].fisico = js[5].tecnica = js[5].mental = 95
    js[6].edad = 19; js[7].edad = 33; js[8].nacionalidad = 'Francia'; js[9].edad = 27
    for j in js:
        j.nacionalidad = j.nacionalidad or 'Inglaterra'
    return e


def test_catalogo_completo_y_bien_formado():
    assert [ev['id'] for ev in EV.EVENTOS] == IDS
    for ev in EV.EVENTOS:
        assert ev['remitente'] in C.REMITENTES and 2 <= len(ev['opciones']) <= 3
        assert 0 <= ev['defecto'] < len(ev['opciones']) and ev['peso'] > 0
        for op in ev['opciones']:
            assert op['texto'] == op['texto'].upper() and len(op['texto']) <= 24
            assert op['efectos'] and op['titular'] and op['noticia']


def test_cada_opcion_de_cada_evento_funciona_y_deja_noticia():
    for ev in EV.EVENTOS:
        for i, op in enumerate(ev['opciones']):
            e = _plantel_variado()
            m = EV.sortear(e, random.Random(7), forzar=ev['id'])
            assert m is not None, f"{ev['id']} no encontró protagonista"
            assert '{' not in m['asunto'] and '{' not in m['cuerpo']
            lineas = EV.resolver(e, m['id'], i, random.Random(i))
            assert lineas, (ev['id'], i)
            n = EV.noticias(e)
            assert len(n) == 1 and n[0]['evento'] == ev['id'] and '{' not in n[0]['titular'] + n[0]['cuerpo']
            for j in e['mi_equipo'].jugadores:
                assert 0 <= j.moral <= 100 and 0 <= j.energia <= 100 and j.lesion_dias >= 0


def test_promesas_minutos_y_aumento():
    e = _plantel_variado(); js = e['mi_equipo'].jugadores
    m = EV.sortear(e, random.Random(1), forzar='exige_titular')
    j = next(x for x in js if x.id == m['evento']['protagonistas'][0])
    EV.resolver(e, m['id'], 0)
    assert e['datos_carrera']['promesas'][0]['tipo'] == 'minutos'
    moral = j.moral
    e['datos_carrera']['promesas'][0]['vence'] = EV._abs(e)             # venció y no jugó
    EV.revisar_promesas(e)
    assert j.moral == moral - 12 and e['datos_carrera']['promesas'] == []
    assert any(n['evento'] == 'promesa_rota' for n in EV.noticias(e))
    e2 = _plantel_variado()
    m2 = EV.sortear(e2, random.Random(1), forzar='rumor_oferta')
    j2 = next(x for x in e2['mi_equipo'].jugadores if x.id == m2['evento']['protagonistas'][0])
    EV.resolver(e2, m2['id'], 0)
    j2.salario += 1000                                                   # cumpliste: le subiste el sueldo
    moral2 = j2.moral
    EV.revisar_promesas(e2)
    assert e2['datos_carrera']['promesas'] == [] and j2.moral == moral2


def test_plantel_sin_perfiles_no_rompe():
    e = _base()                                                          # todos 'normal', 25 años, locales
    for j in e['mi_equipo'].jugadores:
        j.edad, j.nacionalidad, j.jornadas_sin_jugar = 26, 'Inglaterra', 0
    for s in range(80):
        EV.cierre_jornada(e, random.Random(s))
    ids = {m['evento']['id'] for m in C.bandeja(e) if m.get('evento')}
    assert not ids & {'rina', 'charla_lider', 'llega_tarde', 'rumor_oferta', 'entreno_extra', 'nostalgia',
                      'juvenil_deslumbra', 'mentor', 'hinchas'}
    assert len(EV.noticias(e)) >= len([m for m in C.bandeja(e) if m.get('evento')]) - 1


def _con_rina():
    e = _base(mal=True); e['mi_equipo'].jugadores[4].personalidad = 'polemico'
    m = EV.sortear(e, random.Random(1), forzar='rina')
    e['correo_canal'], e['correo_sel'] = 'mensaje', 0
    return e, m


def test_clic_en_opcion_resuelve():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    r = CS.rects_evento(3)[1]
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=r.center))
    assert CS.render(screen, e) is None
    assert m['evento']['resuelto'] == 1 and len(EV.noticias(e)) == 1
    assert CS.render(screen, e) is None                    # ya resuelto: muestra el resumen sin botones


def test_teclado_elige_opcion():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    pygame.event.clear()
    for k in (pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_RETURN):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))
    CS.render(screen, e)
    assert m['evento']['resuelto'] == 2


def test_borrar_pendiente_aplica_el_defecto():
    from alpha_football.ui import correo_screen as CS
    e, m = _con_rina()
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE, mod=0, unicode=''))
    CS.render(screen, e)
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1
    assert m not in C.bandeja(e)


def test_cambio_de_temporada_resuelve_pendientes():
    e, m = _con_rina()
    e['temporada'] = 2
    C.limpiar_temporadas_anteriores(e)
    assert m['evento']['resuelto'] == EV.POR_ID['rina']['defecto'] and len(EV.noticias(e)) == 1


def test_enganche_en_el_cierre_de_jornada():
    import inspect
    from alpha_football.ui import match_screen
    assert "eventos" in inspect.getsource(match_screen.finalizar_jornada_liga)


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
