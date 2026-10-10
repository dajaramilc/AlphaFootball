"""v0.4.22.0: banco de técnicos desempleados y cadena de contrataciones de DT entre clubes de la IA."""
import sys, os, json, random
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football import entrenadores as EN, noticias as N, correo as C
from alpha_football.data.entrenadores import DT_REALES, DT_LIBRES_REALES, NOMBRES, APELLIDOS
from alpha_football.estilos import ESTILOS_DT

EN._dts_libres_editor = lambda: []            # los tests no dependen de la base editada del disco


class RngFijo(random.Random):
    """random() siempre devuelve `v` (para forzar o impedir despidos, robos y retirados que entran al banco)."""
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def club(cid, nombre, ovr, balance=60_000_000, estrellas=3.0):
    return SimpleNamespace(id=cid, nombre=nombre, ovr_promedio=float(ovr), balance=balance, estrellas=estrellas,
                           estilo_dt='anchelottismo', puntos=0, gf=0, gc=0, jugadores=[],
                           dt_nombre='', dt_estilo='', dt_calif=0, dt_nacionalidad='', dt_edad=0, dt_sin=False)


def liga(tipo, division, clubes, n=22):
    return SimpleNamespace(nombre=f"{tipo} {division}", tipo=tipo, division=division, equipos=clubes,
                           num_jornadas=n, jornada_actual=1, calendario=[])


def mundo():
    """Cinco ligas chicas: la del user (Premier 1ª), su 2ª, LaLiga 1ª y 2ª, y una de Sudamérica. Tu club tiene
    la media más alta: ningún otro entra en tu banda, así que nadie te ofrece el banquillo por sorpresa."""
    premier1 = liga('premier', 1, [club(1, "Mi Club", 95), club(2, "Grande", 85, estrellas=4.5),
                                   club(3, "Medio", 78), club(4, "Chico", 74, estrellas=2.5)])
    premier2 = liga('premier', 2, [club(11, "Segunda A", 68), club(12, "Segunda B", 66, estrellas=2.5),
                                   club(13, "Segunda C", 64, estrellas=2.5)])
    laliga1 = liga('laliga', 1, [club(21, "Español A", 84, estrellas=4.5), club(22, "Español B", 76)])
    laliga2 = liga('laliga', 2, [club(41, "Español C", 60, estrellas=2.5)])
    brasil1 = liga('brasil', 1, [club(31, "Brasileño A", 72), club(32, "Brasileño B", 70, estrellas=2.5)])
    return {'liga': premier1, 'mi_equipo': premier1.equipos[0], 'temporada': 1, 'datos_carrera': {},
            'primera_division': {'premier': premier1, 'laliga': laliga1, 'brasil': brasil1},
            'segunda_division': {'premier': premier2, 'laliga': laliga2}}


def _club(e, nombre):
    return next((eq, lg) for eq, lg in EN.clubes(e) if eq.nombre == nombre)


def _libres(e, nombre):
    return [x for x in EN.dts(e)['libres'] if x['nombre'] == nombre]


# ── Tarea 3: banco de técnicos ───────────────────────────────────────────────

def test_prestigio_por_calificacion():
    assert [EN.prestigio({'calif': c}) for c in (0, 49, 50, 69, 70, 99)] == ['bajo', 'bajo', 'medio', 'medio', 'alto', 'alto']
    print("  test_prestigio_por_calificacion: OK")


def test_datos_de_tecnicos():
    nombres = [x[0] for x in DT_LIBRES_REALES]
    assert 20 <= len(nombres) == len(set(nombres))
    dirigen = {dt for dt, _estilo in DT_REALES.values()}
    for nombre, estilo, calif, nac, edad in DT_LIBRES_REALES:
        assert nombre not in dirigen, f"{nombre} ya dirige un club"
        assert estilo in ESTILOS_DT and 40 <= calif <= 80 and nac and 35 <= edad <= 80, nombre
    assert len(NOMBRES) == len(set(NOMBRES)) >= 60 and len(APELLIDOS) == len(set(APELLIDOS)) >= 60
    assert set(EN.ESTILOS_POR_POSICION) == {'POR', 'DEF', 'MED', 'DEL'}
    assert all(v and set(v) <= set(ESTILOS_DT) for v in EN.ESTILOS_POR_POSICION.values())
    print("  test_datos_de_tecnicos: OK")


def test_reales_sin_club_entran_una_vez():
    e = mundo()
    ocupado = DT_LIBRES_REALES[0][0]
    _club(e, "Grande")[0].dt_nombre = ocupado                 # el editor lo sentó en un banquillo
    EN.asegurar_dts(e); EN.asegurar_dts(e)
    assert EN.dts(e)['libres_reales_ok'] is True
    assert EN.dt_de(e, _club(e, "Grande")[0])['nombre'] == ocupado and _libres(e, ocupado) == []
    for nombre, estilo, calif, nac, edad in DT_LIBRES_REALES[1:]:
        (dt,) = _libres(e, nombre)                            # una sola vez
        assert (dt['estilo'], dt['calif'], dt['nacionalidad'], dt['edad']) == (estilo, calif, nac, edad)
        assert dt['sueldo'] == EN.sueldo_pedido(calif) and not dt['interino'] and dt['ex_jugador'] is False
    ids = [x['id'] for x in EN.dts(e)['libres']] + [x['id'] for x in EN.dts(e)['por_club'].values()]
    assert len(ids) == len(set(ids))
    print("  test_reales_sin_club_entran_una_vez: OK")


def test_save_viejo_completa_edad_y_reales():
    e = mundo(); EN.asegurar_dts(e)
    d = EN.dts(e)
    reales = {x[0] for x in DT_LIBRES_REALES}
    d['libres'] = [x for x in d['libres'] if x['nombre'] not in reales]      # como un guardado de antes de 0.4.22.0
    d.pop('libres_reales_ok')
    for dt in list(d['por_club'].values()) + d['libres']:
        dt.pop('edad'); dt.pop('ex_jugador')
    json.loads(json.dumps(e['datos_carrera']))
    EN.asegurar_dts(e)
    todos = list(d['por_club'].values()) + d['libres']
    assert all(isinstance(dt['edad'], int) and 30 <= dt['edad'] <= 80 for dt in todos)
    assert all(len(_libres(e, n)) == 1 for n in reales)
    edades = {dt['id']: dt['edad'] for dt in todos}
    EN.asegurar_dts(e)                                                       # idempotente: ni duplica ni cambia edades
    assert {dt['id']: dt['edad'] for dt in list(d['por_club'].values()) + d['libres']} == edades
    assert EN.prestigio(d['libres'][0]) in ('bajo', 'medio', 'alto')
    print("  test_save_viejo_completa_edad_y_reales: OK")


def test_banco_se_rellena_bajo_el_minimo():
    e = mundo(); EN.asegurar_dts(e)
    d = EN.dts(e)
    del d['libres'][EN.MIN_BANCO:]
    EN.mantener_banco(e, random.Random(3))
    assert len(d['libres']) == EN.MIN_BANCO                   # con el mínimo justo no se toca
    del d['libres'][EN.MIN_BANCO - 1:]
    viejos = {x['id'] for x in d['libres']}
    EN.mantener_banco(e, random.Random(3))
    assert len(d['libres']) == EN.N_LIBRES
    nuevos = [x for x in d['libres'] if x['id'] not in viejos]
    assert len(nuevos) == EN.N_LIBRES - (EN.MIN_BANCO - 1)
    assert all(x['calif'] <= 60 and x['estilo'] in ESTILOS_DT and x['nacionalidad'] and x['edad'] for x in nuevos)
    print("  test_banco_se_rellena_bajo_el_minimo: OK")


def test_banco_tope_40_salen_los_peores():
    e = mundo(); EN.asegurar_dts(e)
    d = EN.dts(e)
    d['libres'] = [EN._nuevo(e, f"Libre {i}", 'choloismo', 30 + i) for i in range(EN.MAX_BANCO + 5)]
    random.Random(4).shuffle(d['libres'])
    EN.mantener_banco(e)
    assert len(d['libres']) == EN.MAX_BANCO == 40
    assert sorted(x['calif'] for x in d['libres']) == list(range(35, 75))    # salieron los 5 de peor calificación
    print("  test_banco_tope_40_salen_los_peores: OK")


def _retiro(nombre="Crack Viejo", ovr=81, posicion='DEL', edad=37, nacionalidad='Brasil', equipo="Grande"):
    return {'nombre': nombre, 'edad': edad, 'ovr': ovr, 'equipo': equipo, 'posicion': posicion,
            'nacionalidad': nacionalidad, 'regen': "Pibe Nuevo", 'regen_edad': 17, 'regen_pot': 85, 'es_user': False}


def test_retirado_81_entra_con_20pct():
    e = mundo(); EN.asegurar_dts(e)
    n = len(EN.dts(e)['libres'])
    assert EN.retirados_a_banco(e, [_retiro()], RngFijo(0.2)) == [] and len(EN.dts(e)['libres']) == n   # 0,2 no es < 0,2
    (dt,) = EN.retirados_a_banco(e, [_retiro()], RngFijo(0.19))
    assert EN.dts(e)['libres'][-1] is dt and len(EN.dts(e)['libres']) == n + 1
    assert (dt['nombre'], dt['nacionalidad'], dt['edad'], dt['calif']) == ("Crack Viejo", 'Brasil', 37, 45)
    assert dt['ex_jugador'] is True and dt['estilo'] in EN.ESTILOS_POR_POSICION['DEL'] and not dt['interino']
    assert dt['sueldo'] == EN.sueldo_pedido(45) and EN.prestigio(dt) == 'bajo'
    califs = [EN.retirados_a_banco(e, [_retiro(nombre=f"V{o}", ovr=o, posicion='POR')], RngFijo(0.0))[0]['calif']
              for o in (85, 91, 99)]
    assert califs == [53, 65, 65]                              # 45 + (ovr − 81) × 2, tope 65
    json.loads(json.dumps(e['datos_carrera']))
    print("  test_retirado_81_entra_con_20pct: OK")


def test_retirado_80_nunca_entra():
    e = mundo(); EN.asegurar_dts(e)
    n = len(EN.dts(e)['libres'])
    assert EN.retirados_a_banco(e, [_retiro(ovr=80), _retiro(ovr=60)], RngFijo(0.0)) == []
    assert len(EN.dts(e)['libres']) == n and N.lista(e) == []
    print("  test_retirado_80_nunca_entra: OK")


def test_retirado_publica_noticia():
    e = mundo(); EN.asegurar_dts(e)
    (dt,) = EN.retirados_a_banco(e, [_retiro(nombre="Crack Viejo", ovr=88)], RngFijo(0.0))
    (n,) = N.lista(e)
    assert n['tipo'] == 'dt_cambio' and n['categoria'] == 'entrenador' and n['importancia'] == 4
    assert n['titular'] == "Crack Viejo se convierte en entrenador" and n['dt_ids'] == [dt['id']]
    assert "Grande" in n['cuerpo'] and n in N.para_feed(e)
    print("  test_retirado_publica_noticia: OK")


def test_editor_dt_sin_y_nacionalidad():
    e = mundo()
    sin, _ = _club(e, "Grande"); sin.nombre = "Manchester Billete"; sin.dt_sin = True     # tiene DT real en la tabla
    con, _ = _club(e, "Medio")
    con.dt_nombre, con.dt_estilo, con.dt_calif, con.dt_nacionalidad, con.dt_edad = "Pep Nuevo", 'cruyffismo', 77, 'Italia', 58
    real, _ = _club(e, "Chico"); real.nombre = "Arsenal Pechofrio"
    orig = EN._dts_libres_editor
    EN._dts_libres_editor = lambda: [{'nombre': 'Libre Uno', 'estilo': 'kloppismo', 'calif': 61, 'nacionalidad': 'Uruguay', 'edad': 44},
                                     {'nombre': 'Libre Dos', 'estilo': 'kloppismo', 'calif': 50}]
    try:
        EN.asegurar_dts(e)
    finally:
        EN._dts_libres_editor = orig
    assert EN.dt_de(e, sin)['nombre'] != DT_REALES["Manchester Billete"][0] and not EN.dt_de(e, sin)['interino']
    dt = EN.dt_de(e, con)
    assert (dt['nombre'], dt['estilo'], dt['calif'], dt['nacionalidad'], dt['edad']) == ("Pep Nuevo", 'cruyffismo', 77, 'Italia', 58)
    assert EN.dt_de(e, real)['nombre'] == DT_REALES["Arsenal Pechofrio"][0] and 30 <= EN.dt_de(e, real)['edad'] <= 80
    (uno,), (dos,) = _libres(e, 'Libre Uno'), _libres(e, 'Libre Dos')
    assert (uno['nacionalidad'], uno['edad']) == ('Uruguay', 44) and dos['nacionalidad'] and 30 <= dos['edad'] <= 80
    print("  test_editor_dt_sin_y_nacionalidad: OK")


def test_procesar_retiros_pasa_figuras_al_banco():
    os.environ['SDL_VIDEODRIVER'] = 'dummy'; os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
    from alpha_football import save, retiros as R
    save.guardar_en_slot = lambda *a, **k: None              # los tests no tocan los slots reales
    from alpha_football.ui.menu import load_league_teams
    lg = load_league_teams('premier'); mi = lg.equipos[0]
    e = {'liga': lg, 'mi_equipo': mi, 'equipos': lg.equipos, 'temporada': 1, 'primera_division': {'premier': lg},
         'segunda_division': {}, 'datos_carrera': {}, 'historial': []}
    EN.asegurar_dts(e)
    for eq in lg.equipos:
        for j in eq.jugadores:
            j.edad = min(j.edad, 30)                          # nadie más se retira
    figura = max(lg.equipos[1].jugadores, key=lambda j: j.overall)
    flojo = min(lg.equipos[2].jugadores, key=lambda j: j.overall)
    assert figura.overall >= EN.OVR_RETIRADO_DT > flojo.overall
    figura.edad = flojo.edad = 38
    nombres = figura.nombre_completo, flojo.nombre_completo
    retiros = R.procesar_retiros(e, RngFijo(0.0))
    assert sorted(r['nombre'] for r in retiros) == sorted(nombres)
    pais = figura.nacionalidad                                # la real de la tabla (procesar_retiros la asigna)
    assert pais and next(r for r in retiros if r['nombre'] == nombres[0])['nacionalidad'] == pais
    (dt,) = _libres(e, nombres[0])
    assert dt['ex_jugador'] and dt['nacionalidad'] == pais and dt['edad'] == 38 and _libres(e, nombres[1]) == []
    assert [n['titular'] for n in N.lista(e)] == [N._recortar(f"{nombres[0]} se convierte en entrenador")]
    print("  test_procesar_retiros_pasa_figuras_al_banco: OK")


# ── Tarea 4: cadena de contrataciones ────────────────────────────────────────

CALIFS = {"Grande": 65, "Medio": 60, "Chico": 55, "Segunda A": 52, "Segunda B": 50, "Segunda C": 48,
          "Español A": 64, "Español B": 58, "Español C": 45, "Brasileño A": 70, "Brasileño B": 69}


class RngSecuencia(random.Random):
    """random() devuelve los valores de la lista en orden y después siempre el último."""
    def __new__(cls, valores): return super().__new__(cls)      # Random.__new__ usaría la lista como semilla
    def __init__(self, valores): super().__init__(1); self.valores = list(valores)
    def random(self): return self.valores.pop(0) if len(self.valores) > 1 else self.valores[0]


def cadena(banco=(40,)):
    """mundo() con cada DT en su calificación de CALIFS (todos del mismo estilo) y un banco a medida."""
    e = mundo(); EN.asegurar_dts(e)
    for eq, _lg in EN.clubes(e):
        if eq.nombre in CALIFS:
            EN.dt_de(e, eq).update(calif=CALIFS[eq.nombre], estilo='anchelottismo', nombre=f"DT {eq.nombre}")
    EN.dts(e)['libres'] = [EN._nuevo(e, f"Libre {c}", 'choloismo', c) for c in banco]
    return e


def _dt(e, nombre):
    return EN.dt_de(e, _club(e, nombre)[0])


def _vacante(e, nombre, rng, **kw):
    """Echa al DT de ese club y cubre la vacante. Devuelve (DT despedido, DT que llega)."""
    eq, lg = _club(e, nombre)
    viejo = EN.despedir(e, eq, lg, "prueba")
    return viejo, EN.cubrir_vacante(e, eq, lg, rng, "prueba", saliente=viejo, **kw)


def _ids_por_club(e):
    return {eq.nombre: (EN.dt_de(e, eq) or {}).get('id') for eq, _lg in EN.clubes(e)}


def _sanos(e):
    """Todo club de la IA tiene DT, el tuyo no, y ningún DT está en dos sitios a la vez."""
    mi = e['mi_equipo']
    en_club = [EN.dt_de(e, eq)['id'] for eq, _lg in EN.clubes(e) if eq is not mi and EN.dt_de(e, eq)]
    assert len(en_club) == len(EN.clubes(e)) - 1 and EN.dt_de(e, mi) is None
    assert len(en_club) == len(set(en_club)) and not set(en_club) & {x['id'] for x in EN.dts(e)['libres']}
    json.loads(json.dumps(e['datos_carrera']))
    return True


def test_orden_de_los_candidatos_a_robo():
    e = cadena(); grande, lg = _club(e, "Grande")
    nombres = lambda: [origen.nombre for _dt_, origen, _l in EN._candidatos_robo(e, grande, lg)]
    # misma liga -> mismo país -> mismo continente; dentro, la mejor calificación. Ni tu club ni otro continente.
    assert nombres() == ["Medio", "Chico", "Segunda A", "Segunda B", "Segunda C", "Español A", "Español B", "Español C"]
    grande.estilo_dt = 'kloppismo'                              # identidad del club: el estilo del DT que se fue
    _dt(e, "Chico")['estilo'] = _dt(e, "Español C")['estilo'] = 'kloppismo'
    assert nombres() == ["Chico", "Medio", "Segunda A", "Segunda B", "Segunda C", "Español C", "Español A", "Español B"]
    print("  test_orden_de_los_candidatos_a_robo: OK")


def test_filtros_de_los_candidatos_a_robo():
    e = cadena(banco=(50,)); grande, lg = _club(e, "Grande")
    nombres = lambda: {origen.nombre for _dt_, origen, _l in EN._candidatos_robo(e, grande, lg)}
    assert nombres() == {"Medio", "Chico", "Segunda A", "Español A", "Español B"}     # mejores que el mejor libre (50)
    _dt(e, "Medio")['interino'] = True                                               # un interino no se roba
    _club(e, "Español A")[0].ovr_promedio = 84.6                                     # no es de menor nivel (< 0,5)
    _club(e, "Segunda A")[0].ovr_promedio = 90.0                                     # 2ª de tu país: división inferior
    _club(e, "Español B")[0].ovr_promedio = 90.0                                     # otro país y mejor media: no
    assert nombres() == {"Chico", "Segunda A"}
    caro = _dt(e, "Chico"); caro['sueldo'] = 5_500_000                               # x1,2 ya no entra en el 10 % del saldo
    assert nombres() == {"Segunda A"}
    grande.balance = 100_000
    assert nombres() == set()                                                        # no puede pagar a nadie
    print("  test_filtros_de_los_candidatos_a_robo: OK")


def test_robo_viene_de_un_club_menor_de_la_misma_liga():
    e = cadena(); grande, _lg = _club(e, "Grande")
    robado = _dt(e, "Medio"); sueldo_antes, saldo = EN.sueldo(robado), grande.balance
    viejo, llega = _vacante(e, "Grande", RngFijo(0.0))
    assert llega is robado and _dt(e, "Grande") is robado and grande.estilo_dt == robado['estilo']
    assert EN.sueldo(robado) == max(int(sueldo_antes * EN.SUBE_SUELDO_ROBO), EN.sueldo_pedido(robado['calif'])) > sueldo_antes
    assert grande.balance == saldo - EN.sueldo(robado)
    assert _dt(e, "Medio")['id'] not in (robado['id'], viejo['id'])              # el origen cubrió su vacante
    assert any(x['id'] == viejo['id'] and x['calif'] == viejo['calif'] - 10 for x in EN.dts(e)['libres'])
    print("  test_robo_viene_de_un_club_menor_de_la_misma_liga: OK")


def test_origen_queda_cubierto():
    e = cadena(banco=(40, 39, 38))
    for nombre in ("Grande", "Español A", "Brasileño A"):
        _vacante(e, nombre, RngFijo(0.0))
    assert _sanos(e) and not any((EN.dt_de(e, eq) or {}).get('interino') for eq, _lg in EN.clubes(e))
    print("  test_origen_queda_cubierto: OK")


def test_tope_de_4_movimientos():
    e = cadena(); antes = _ids_por_club(e)
    _vacante(e, "Grande", RngFijo(0.0))                         # todos aceptan: la cadena baja mientras pueda
    ahora, cad = _ids_por_club(e), EN._cadena(e)
    assert cad['mov'] == EN.MAX_CADENA == 4
    assert [ahora[c] for c in ("Grande", "Medio", "Chico", "Segunda A")] == \
           [antes[c] for c in ("Medio", "Chico", "Segunda A", "Segunda B")]
    assert ahora["Segunda C"] == antes["Segunda C"]             # habría sido el quinto movimiento
    assert _dt(e, "Segunda B")['nombre'] == "Libre 40" and EN.dts(e)['libres'][0]['nombre'] == "DT Grande"
    assert len(EN.dts(e)['libres']) == 1 and _sanos(e)          # agotado el cupo, la vacante fue al banco
    print("  test_tope_de_4_movimientos: OK")


def test_un_dt_no_se_mueve_dos_veces_en_la_jornada():
    e = cadena(banco=(40, 39, 38))
    x = _dt(e, "Chico")
    _viejo, llega = _vacante(e, "Medio", RngSecuencia([0.0, 0.99]))     # Chico -> Medio; nadie más acepta
    assert llega is x and EN._cadena(e)['mov'] == 1
    z = _dt(e, "Chico")
    assert z['nombre'] == "Libre 40" and {x['id'], z['id']} <= set(EN._cadena(e)['movidos'])
    de_segunda = _dt(e, "Segunda A")
    _viejo, llega = _vacante(e, "Grande", RngFijo(0.0))
    assert llega is de_segunda                                  # ni X ni Z (llegaron hoy): el siguiente de la lista
    assert _dt(e, "Medio") is x and _dt(e, "Chico") is z and _sanos(e)
    print("  test_un_dt_no_se_mueve_dos_veces_en_la_jornada: OK")


def test_contador_se_reinicia_en_la_jornada_siguiente():
    e = cadena()
    _vacante(e, "Grande", RngFijo(0.0))
    assert EN._cadena(e)['mov'] == 4 and EN._cadena(e)['movidos']
    x = _dt(e, "Grande")
    e['liga'].jornada_actual += 1
    assert EN._cadena(e) == {'clave': [1, 2], 'mov': 0, 'movidos': []}
    x['calif'] = 68                                             # ya puede moverse otra vez: se lo lleva un club mayor
    grande, _lg = _club(e, "Grande"); grande.ovr_promedio = 80.0
    _dt(e, "Español B")['calif'] = 41                           # peor que el mejor libre: no interesa
    _viejo, llega = _vacante(e, "Español A", RngFijo(0.0))
    assert llega is x and EN._cadena(e)['mov'] >= 1
    print("  test_contador_se_reinicia_en_la_jornada_siguiente: OK")


def test_sin_aceptacion_va_al_banco():
    e = cadena(banco=(40, 30)); antes = _ids_por_club(e)
    viejo, llega = _vacante(e, "Grande", RngFijo(0.99))         # nadie acepta
    assert llega['nombre'] == "Libre 40" and _dt(e, "Grande") is llega and EN._cadena(e)['mov'] == 0
    assert [x['nombre'] for x in EN.dts(e)['libres']] == ["Libre 30", "DT Grande"]     # el banco pierde uno
    assert {k: v for k, v in _ids_por_club(e).items() if k != "Grande"} == {k: v for k, v in antes.items() if k != "Grande"}
    print("  test_sin_aceptacion_va_al_banco: OK")


def test_no_recontrata_al_que_acaba_de_despedir():
    e = cadena(banco=())
    viejo, llega = _vacante(e, "Brasileño A", RngFijo(0.99))    # sin robo y con el banco vacío salvo el despedido
    assert llega['id'] != viejo['id'] and _libres(e, "DT Brasileño A") and _sanos(e)
    print("  test_no_recontrata_al_que_acaba_de_despedir: OK")


def test_club_del_user_fuera_de_la_cadena():
    e = cadena(); mi, lg = _club(e, "Mi Club")
    assert EN.cubrir_vacante(e, mi, lg, RngFijo(0.0)) is None and EN.dt_de(e, mi) is None      # nunca es destino
    EN.dts(e)['por_club'][str(mi.id)] = EN._nuevo(e, "Fantasma", 'cruyffismo', 99)             # guardado raro
    mi.ovr_promedio = 70.0
    grande, lg_g = _club(e, "Grande")
    assert "Mi Club" not in [o.nombre for _d, o, _l in EN._candidatos_robo(e, grande, lg_g)]   # ni origen
    del EN.dts(e)['por_club'][str(mi.id)]
    mi.ovr_promedio = 95.0
    for nombre in ("Grande", "Español A", "Brasileño A", "Segunda A"):
        _vacante(e, nombre, RngFijo(0.0))
    assert _sanos(e)
    print("  test_club_del_user_fuera_de_la_cadena: OK")


def test_club_que_no_puede_pagar_no_roba():
    e = cadena(); antes = _ids_por_club(e)
    grande, _lg = _club(e, "Grande"); grande.balance = 300_000
    _viejo, llega = _vacante(e, "Grande", RngFijo(0.0))
    assert EN._cadena(e)['mov'] == 0 and EN.sueldo(llega) <= max(EN.SUELDO_DT_MIN, EN.FRAC_SUELDO_DT * 300_000)
    assert {k: v for k, v in _ids_por_club(e).items() if k != "Grande"} == {k: v for k, v in antes.items() if k != "Grande"}
    print("  test_club_que_no_puede_pagar_no_roba: OK")


def test_vacante_de_cadena_puede_ofrecerse_al_user():
    e = cadena()
    e['mi_equipo'].ovr_promedio = 70.0; e['datos_carrera']['calif_dt'] = 90      # banda: 68 a 80 (Grande, 85, no entra)
    medio, _lg = _club(e, "Medio"); robado = _dt(e, "Medio")
    _viejo, llega = _vacante(e, "Grande", RngFijo(0.0))
    assert llega is robado
    assert EN.dt_de(e, medio)['interino'] and EN._cadena(e)['mov'] == 1          # Medio espera tu respuesta
    (of,) = EN.ofertas_activas(e)
    assert of['club_id'] == str(medio.id) and of['jornadas'] == EN.JORNADAS_OFERTA and "Grande" in of['causa']
    msg = C.bandeja(e)[0]
    assert msg['accion']['pantalla'] == 'ofertas_dt_screen' and "Grande" in msg['cuerpo'] and "despedir" not in msg['cuerpo']
    for _ in range(EN.JORNADAS_OFERTA):                                          # no respondes: contrata sin ofrecerte de nuevo
        EN.revisar_jornada(e, RngFijo(0.99))
    assert not EN.ofertas_activas(e) and not EN.dt_de(e, medio)['interino'] and _sanos(e)
    print("  test_vacante_de_cadena_puede_ofrecerse_al_user: OK")


def test_sin_ofrecer_tampoco_se_ofrecen_las_vacantes_de_la_cadena():
    e = cadena()
    e['mi_equipo'].ovr_promedio = 70.0; e['datos_carrera']['calif_dt'] = 90      # Medio y Chico entran en tu banda
    _viejo, llega = _vacante(e, "Grande", RngFijo(0.0), ofrecer=False)           # p. ej. en el cierre de temporada
    assert llega['nombre'] == "DT Medio" and not EN.ofertas_activas(e) and C.bandeja(e) == []
    assert not any(EN.dt_de(e, eq).get('interino') for eq, _lg in EN.clubes(e) if eq is not e['mi_equipo'])
    assert EN._cadena(e)['mov'] == 4 and _sanos(e)
    print("  test_sin_ofrecer_tampoco_se_ofrecen_las_vacantes_de_la_cadena: OK")


def test_noticias_de_despido_y_fichaje():
    e = cadena(); grande, _lg = _club(e, "Grande")
    robado = _dt(e, "Medio")
    viejo, _llega = _vacante(e, "Grande", RngSecuencia([0.0, 0.99]))
    # una sola noticia por club afectado: Grande (despidió y robó) y Medio (lo perdió y fue al banco)
    en_grande, en_medio = N.lista(e)[::-1]
    assert [n['titular'] for n in (en_grande, en_medio)] == [
        "DT Medio reemplaza a DT Grande en el Grande", "Libre 40 reemplaza a DT Medio en el Medio"]
    assert all(n['tipo'] == 'dt_cambio' and n['importancia'] == 4 for n in (en_grande, en_medio))
    assert en_grande['equipos_ids'] == [grande.id, _club(e, "Medio")[0].id] and en_grande['dt_ids'] == [robado['id'], viejo['id']]
    assert "despidió a DT Grande (prueba)" in en_grande['cuerpo'] and "banquillo de Medio" in en_grande['cuerpo']
    assert en_medio['equipos_ids'] == [_club(e, "Medio")[0].id] and en_medio['dt_ids'][1] == robado['id']
    assert "para dirigir a Grande" in en_medio['cuerpo'] and "sin club" in en_medio['cuerpo']
    # 2ª división de otro país: importancia 2 (se ve en Noticias, no en el feed); la 2ª de tu país sí entra
    for nombre, imp in (("Español C", 2), ("Segunda C", 4)):
        antes = len(N.lista(e))
        _vacante(e, nombre, RngFijo(0.99))
        n = N.lista(e)[0]
        assert len(N.lista(e)) == antes + 1 and n['titular'].endswith(f"reemplaza a DT {nombre} en el {nombre}")
        assert n['importancia'] == imp, nombre
    assert all(len(n['titular']) <= 60 for n in N.lista(e))
    print("  test_noticias_de_despido_y_fichaje: OK")


def test_titulares_largos_usan_la_forma_corta():
    e = cadena()
    _dt(e, "Grande")['nombre'] = "Manuel Ingeniero Pellegrini"; _dt(e, "Medio")['nombre'] = "Hernán Darío Herrería"
    eq, lg = _club(e, "Grande"); eq.nombre = "Paris Saint-Germain Sin Champions"
    _club(e, "Medio")[0].nombre = "Independiente del Valle de Lagrimas"
    viejo = EN.despedir(e, eq, lg, "prueba")
    EN.cubrir_vacante(e, eq, lg, RngFijo(0.0), "prueba", saliente=viejo)
    titulares = [n['titular'] for n in N.lista(e)]
    assert len(titulares) >= 2 and all(len(t) <= 60 and not t.endswith('…') for t in titulares), titulares
    assert titulares[-1] == "Paris Saint-Germain Sin Champions cambia de técnico"          # la forma más corta
    print("  test_titulares_largos_usan_la_forma_corta: OK")


def test_despido_ya_no_envia_correo():
    e = cadena()
    _vacante(e, "Medio", RngFijo(0.99))                         # un club de TU liga
    assert C.bandeja(e) == [] and len(N.lista(e)) == 1
    print("  test_despido_ya_no_envia_correo: OK")


def test_una_noticia_por_vacante():
    e = cadena(banco=(40, 39))
    _vacante(e, "Grande", RngFijo(0.99))                        # despido + reemplazo del banco en la misma pasada
    (n,) = N.lista(e)
    assert n['titular'] == "Libre 40 reemplaza a DT Grande en el Grande" and "sin club" in n['cuerpo']
    del N.lista(e)[:]
    e = cadena(banco=(40,))
    _vacante(e, "Español A", RngSecuencia([0.0, 0.99]))         # cadena: roba a Español B, que va al banco
    assert [n['titular'] for n in N.lista(e)[::-1]] == [
        "DT Español B reemplaza a DT Español A en el Español A", "Libre 40 reemplaza a DT Español B en el Español B"]
    e = cadena()
    _vacante(e, "Grande", RngFijo(0.0))                         # la cadena larga: 4 robos y un fichaje del banco
    assert len(N.lista(e)) == 5 and all(" reemplaza a " in n['titular'] for n in N.lista(e))
    assert len({n['equipos_ids'][0] for n in N.lista(e)}) == 5  # una por club afectado
    print("  test_una_noticia_por_vacante: OK")


def test_despido_con_interino_y_llegada_tienen_su_noticia():
    e = cadena()
    e['mi_equipo'].ovr_promedio = 85.0; e['datos_carrera']['calif_dt'] = 90      # Grande entra en tu banda
    grande, _lg = _club(e, "Grande")
    viejo, llega = _vacante(e, "Grande", RngFijo(0.0))          # te ofrecen el banquillo: queda un interino
    assert llega is None and EN.dt_de(e, grande)['interino']
    (n,) = N.lista(e)
    assert n['titular'] == "El Grande despide a DT Grande" and n['dt_ids'] == [viejo['id']] and "prueba" in n['cuerpo']
    for _ in range(EN.JORNADAS_OFERTA):                         # no respondes: llega un técnico
        EN.revisar_jornada(e, RngFijo(0.99))
    llegada, despido = N.lista(e)
    nuevo = EN.dt_de(e, grande)
    assert despido is n and not nuevo['interino'] and llegada['dt_ids'] == [nuevo['id']]
    assert llegada['titular'] == f"{nuevo['nombre']} firma por el Grande" and "sin club" in llegada['cuerpo']
    print("  test_despido_con_interino_y_llegada_tienen_su_noticia: OK")


def test_el_club_que_dejas_entra_en_la_cadena():
    acepta = EN.PROB_ACEPTA_ROBO
    try:
        for prob, llega in ((1.0, "DT Grande"), (0.0, "Libre 40")):          # se lo roba a un club menor / va al banco
            EN.PROB_ACEPTA_ROBO = prob
            e = cadena()
            viejo, nuevo = e['mi_equipo'], _club(e, "Medio")[0]
            del_nuevo = EN.dt_de(e, nuevo)
            e['mi_equipo'] = nuevo                                           # directiva.cambiar_de_club ya te movió
            EN.al_cambiar_club(e, viejo, nuevo)
            assert EN.dt_de(e, nuevo) is None                                # tu club nuevo: el DT eres tú
            dt = EN.dt_de(e, viejo)
            assert dt and not dt['interino'] and dt['nombre'] == llega, (prob, dt)
            assert _libres(e, "DT Medio") == [del_nuevo]                     # el que desplazaste queda libre
            assert not EN.ofertas_activas(e) and _sanos(e)
            de_viejo = [n for n in N.lista(e) if viejo.id in n['equipos_ids'] and viejo.nombre in n['titular']]
            assert len(de_viejo) == 1 and de_viejo[0]['tipo'] == 'dt_cambio' and llega in de_viejo[0]['titular']
            assert EN._cadena(e)['mov'] == (4 if prob else 0)
    finally:
        EN.PROB_ACEPTA_ROBO = acepta
    print("  test_el_club_que_dejas_entra_en_la_cadena: OK")


def _hundir(lg, eq):
    """Deja a `eq` último en la tabla y a mitad de temporada."""
    lg.jornada_actual = lg.num_jornadas // 2 + 1
    for x in lg.equipos:
        x.puntos = 30
    eq.puntos = 0


def _laliga_de_5(e):
    lg = e['primera_division']['laliga']
    lg.equipos += [club(23, "Español D", 70), club(24, "Español E", 69), club(25, "Español F", 68)]
    return lg


def test_revisar_jornada_despide_encadena_y_cuida_el_banco():
    e = mundo(); lg = _laliga_de_5(e)
    EN.asegurar_dts(e)
    for eq, _l in EN.clubes(e):
        if eq is not e['mi_equipo']:
            EN.dt_de(e, eq).update(calif=CALIFS.get(eq.nombre, 50), nombre=f"DT {eq.nombre}")
    libres = EN.dts(e)['libres'] = [EN._nuevo(e, f"Libre {i}", 'choloismo', 40) for i in range(EN.MIN_BANCO)]
    fuerte, _l = _club(e, "Español A"); viejo = EN.dt_de(e, fuerte)
    _hundir(lg, fuerte)
    EN.revisar_jornada(e, RngFijo(0.99))                        # 99 % > 8 %: no echa
    assert EN.dt_de(e, fuerte) is viejo and N.lista(e) == [] and len(libres) == EN.MIN_BANCO
    del libres[0]
    EN.revisar_jornada(e, RngFijo(0.0))
    nuevo = EN.dt_de(e, fuerte)
    assert nuevo['id'] != viejo['id'] and nuevo['nombre'] == "DT Español B"       # robado en su misma liga
    assert EN._cadena(e)['mov'] == 4 and EN.dts(e)['despidos_temp'] == {'laliga-1': 1}
    assert len(libres) == EN.N_LIBRES                           # el banco bajó del mínimo: se rellenó
    assert N.lista(e)[-1]['titular'] == "DT Español B reemplaza a DT Español A en el Español A" and _sanos(e)
    assert len(N.lista(e)) == 5 and "iba 5º" in N.lista(e)[-1]['cuerpo']         # una por club; con el motivo del despido
    json.loads(json.dumps(e['datos_carrera']))
    print("  test_revisar_jornada_despide_encadena_y_cuida_el_banco: OK")


def test_cierre_temporada_no_deja_clubes_sin_dt():
    e = mundo(); lg = _laliga_de_5(e)
    EN.asegurar_dts(e)
    d = EN.dts(e)
    d['libres'] = [EN._nuevo(e, "Libre 40", 'choloismo', 40)]
    fuerte, _l = _club(e, "Español A"); viejo = EN.dt_de(e, fuerte)['id']
    _hundir(lg, fuerte)
    del d['por_club'][str(_club(e, "Chico")[0].id)]             # un club sin DT (guardado raro)
    interino, lg_i = _club(e, "Segunda A")
    EN._ofrecer_al_user(e, interino, lg_i, "prueba")
    d['despidos_temp'] = {'x': 1}
    # casi todos entran en tu banda: aun así el cierre no te ofrece ninguna vacante (ni las de la cadena),
    # porque las ofertas se borran al terminar y el club se quedaría con el interino toda la temporada
    e['mi_equipo'].ovr_promedio = 76.0; e['datos_carrera']['calif_dt'] = 90
    EN.cierre_temporada(e, RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] != viejo and _sanos(e)
    assert not any(EN.dt_de(e, eq).get('interino') for eq, _l in EN.clubes(e) if eq is not e['mi_equipo'])
    assert d['despidos_temp'] == {} and d['ofertas'] == []
    print("  test_cierre_temporada_no_deja_clubes_sin_dt: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


if __name__ == '__main__':
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
