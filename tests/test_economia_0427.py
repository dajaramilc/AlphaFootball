"""0.4.27.0 (sesion2, economía): historial de transacciones con fecha real, venta de camisetas en el objetivo de
Marca, FINANZAS sin los textos de abajo de camisetas y jugador lesionado (a la vista en su ficha y con menos valor).
El techo de 350 M$ solo al empezar temporada vive en test_techo_presupuesto.py."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import finanzas as F
from alpha_football import directiva as D
from alpha_football import dias as DI
from alpha_football import market as M


def _tecla(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _clic(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def _textos(modulo, funcion, *args):
    """Lo que dibuja `funcion` con draw_text de `modulo` capturado: lista de textos."""
    textos, orig = [], modulo.draw_text
    modulo.draw_text = lambda s, t, *a, **k: textos.append(str(t))
    try:
        funcion(*args)
    finally:
        modulo.draw_text = orig
    return textos


# ---------------------------------------------------------------- N: historial de transacciones
def test_registrar_anota_el_movimiento_con_fecha_real_y_signo():
    e = estado_carrera()
    hoy = DI.hoy(e)                                                        # crea el reloj
    F.registrar(e, 'fichajes', 5_000_000, concepto="Fichaje de Fulano (de Zeta FC)")
    F.registrar(e, 'ventas', 3_000_000)
    mov = F.transacciones(e)                                               # el más reciente primero
    assert mov[0]['concepto'] == "Venta de jugador" and mov[0]['importe'] == 3_000_000
    assert mov[1]['concepto'].startswith("Fichaje de Fulano") and mov[1]['importe'] == -5_000_000
    assert mov[0]['fecha'] == hoy.isoformat() == mov[1]['fecha']
    assert F.libro(e)['fichajes'] == 5_000_000 and F.libro(e)['ventas'] == 3_000_000     # el libro sigue igual


def test_un_monto_negativo_de_ingreso_es_un_gasto_y_el_cero_no_se_anota():
    e = estado_carrera()
    F.registrar(e, 'patrocinio', -40_000, concepto="Multa por rescindir con Marca X")
    F.registrar(e, 'taquilla', 0)                                          # visitante: no hay taquilla
    F.anotar_movimiento(e, "Gasto del club (evento)", -250_000, 'evento')
    mov = F.transacciones(e)
    assert [m['importe'] for m in mov] == [-250_000, -40_000]
    assert mov[1]['concepto'].startswith("Multa por rescindir")


def test_el_historial_tiene_tope_y_conserva_lo_reciente():
    e = estado_carrera()
    for i in range(F.HISTORIAL_MAX + 30):
        F.anotar_movimiento(e, f"m{i}", i + 1)
    assert len(e['datos_carrera']['transacciones']) == F.HISTORIAL_MAX
    assert F.transacciones(e)[0]['concepto'] == f"m{F.HISTORIAL_MAX + 29}"


def test_partida_vieja_sin_historial_no_falla():
    assert F.transacciones({'datos_carrera': {}}) == [] and F.transacciones({}) == []
    e = estado_carrera()
    e['datos_carrera']['transacciones'] = 'basura'                         # guardado roto: se rehace
    F.anotar_movimiento(e, "x", 10)
    assert len(F.transacciones(e)) == 1


def test_la_jornada_anota_sus_cobros_y_pagos():
    e = estado_carrera()
    DI.hoy(e)
    mov = F.procesar_jornada(e, True, 2, 0)
    hist = F.transacciones(e)
    conceptos = [m['concepto'] for m in hist]
    assert any(c.startswith("Salarios · jornada") for c in conceptos)
    assert any(c.startswith("Taquilla · jornada") for c in conceptos)
    assert any(c.startswith("Venta de camisetas · jornada") for c in conceptos)
    esperado = mov['patrocinio'] + mov['taquilla'] + mov['camisetas'] - mov['salarios']
    assert sum(m['importe'] for m in hist) == esperado                     # el historial cuadra con el saldo


def test_el_presupuesto_nuevo_queda_en_el_historial():
    e = estado_carrera()
    e['mi_equipo'].balance = 123_000_000
    info = F.aplicar_presupuesto_temporada(e)
    ajuste = [m for m in F.transacciones(e) if m['clave'] == 'presupuesto']
    assert ajuste and ajuste[0]['importe'] == info['total'] - 123_000_000


def test_vender_y_liberar_dejan_su_concepto():
    from alpha_football import contraofertas as CO
    from alpha_football import negociacion as N
    e = estado_carrera()
    mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    j = mi.jugadores[7]
    neto = CO.acreditar_venta(e, j, rival, 10_000_000)
    venta = F.transacciones(e)[0]
    assert venta['importe'] == neto > 0
    assert venta['concepto'] == f"Venta de {j.nombre_completo} a {rival.nombre}"
    otro = mi.jugadores[8]
    ok, _msg = N.liberar_jugador(e, otro)
    assert ok
    libre = next(m for m in F.transacciones(e) if m['concepto'].startswith("Indemnización por liberar a"))
    assert libre['importe'] < 0 and otro.nombre_completo in libre['concepto']


def test_la_pantalla_del_historial_abre_con_t_y_boton_y_se_cierra_con_esc_y_volver():
    from alpha_football.ui import finanzas_screen as FS
    e = estado_carrera()
    DI.hoy(e)
    for i in range(40):                                                    # más filas que las visibles: hay scroll
        F.registrar(e, 'taquilla', 100_000 + i, concepto=f"Taquilla · jornada {i}")
    _tecla(pygame.K_t); assert FS.render(screen, e) is None
    assert e.get('historial_trans_abierto')
    textos = _textos(FS, FS.render, screen, e)
    assert "HISTORIAL DE TRANSACCIONES" in textos and "CONCEPTO" in textos
    assert any("Taquilla · jornada 39" in t for t in textos)               # el más reciente arriba
    _tecla(pygame.K_END); FS.render(screen, e)                             # al fondo de la lista
    assert e['historial_trans_scroll'] == 40 - FS.FILAS_HISTORIAL
    _tecla(pygame.K_ESCAPE); assert FS.render(screen, e) is None
    assert not e.get('historial_trans_abierto')
    _clic(FS.R_HISTORIAL.center); FS.render(screen, e)                     # el botón también abre
    assert e.get('historial_trans_abierto')
    _clic(FS._volver().center); assert FS.render(screen, e) is None        # VOLVER cierra el historial, no FINANZAS
    assert not e.get('historial_trans_abierto')


def test_el_historial_vacio_se_dibuja_sin_romper():
    from alpha_football.ui import finanzas_screen as FS
    e = estado_carrera()
    e['historial_trans_abierto'] = True
    pygame.event.clear()
    textos = _textos(FS, FS.render, screen, e)
    assert any("Aún no hay movimientos" in t for t in textos)


# ---------------------------------------------------------------- A: FINANZAS sin los textos de abajo de camisetas
def test_venta_de_camisetas_sin_los_textos_de_abajo():
    from alpha_football.ui import finanzas_screen as FS
    e = estado_carrera()
    pygame.event.clear()
    textos = _textos(FS, FS.render, screen, e)
    assert "VENTA DE CAMISETAS" in textos and any(t.startswith("Popularidad") for t in textos)
    assert not any(t.startswith("Suma ") and "al valor del club" in t for t in textos)
    assert not any("Se dispara" in t for t in textos)


# ---------------------------------------------------------------- B: camisetas en el objetivo de Marca
def test_marca_puede_ser_de_camisetas_y_cuenta_lo_cobrado():
    e = estado_carrera()
    D.definir_objetivo(e)
    D._dc(e).pop('objetivo_marca', None)
    azar = random.Random(1)
    azar.random = lambda: 0.99                                             # la última de las tres metas
    om = D.definir_objetivo_marca(e, azar)
    assert om['tipo'] == 'camisetas' and om['meta'] == F.meta_camisetas(e) > 0
    assert "camisetas" in om['texto'] and "$" in om['texto'] and "€" not in om['texto']
    assert D.progreso_secundario(e, om) == 0.0 and not D.cumplido_secundario(e, om)
    F.registrar(e, 'camisetas', om['meta'] // 2)
    assert 0.45 < D.progreso_secundario(e, om) < 0.55
    F.registrar(e, 'camisetas', om['meta'])
    assert D.cumplido_secundario(e, om)
    D.revisar_objetivos_secundarios(e)
    assert om['cumplido']
    antes = D.calif_dt(e)
    assert D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)['resultado'] == 'cumplido'
    assert D.calif_dt(e) == antes + D.CALIF_SECUNDARIO['cumplido']


def test_marca_de_camisetas_fallada_si_no_se_cobra():
    e = estado_carrera()
    D.definir_objetivo(e)
    mi = e['mi_equipo']
    D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'camisetas', 'meta': 5_000_000,
                                  'texto': 'x', 'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    F.registrar(e, 'camisetas', 1_000_000)
    assert D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)['resultado'] == 'fallado'


def test_la_meta_de_camisetas_es_10_por_ciento_mas_y_tiene_tope():
    e = estado_carrera()
    e['datos_carrera']['camisetas'] = {'popularidad': 50.0}
    assert abs(F.meta_camisetas(e) - int(F.ingreso_anual_camisetas(e) * F.FACTOR_META_CAMISETAS)) <= 1
    e['datos_carrera']['camisetas'] = {'popularidad': 100.0}               # con la popularidad al tope: se pide sostenerla
    ingreso_tope = F.ingreso_anual_camisetas(e)
    assert F.meta_camisetas(e) <= ingreso_tope
    assert abs(F.meta_camisetas(e) - int(ingreso_tope * F.POP_META_TOPE / 100.0)) <= 1


def test_la_pantalla_de_objetivos_muestra_lo_cobrado_en_camisetas():
    from alpha_football.ui import objetivos_screen as O
    e = estado_carrera(); mi = e['mi_equipo']
    D.definir_objetivo(e)
    D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'camisetas', 'meta': 4_000_000,
                                  'texto': 'Cobrar $4.0M en camisetas esta temporada',
                                  'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    F.registrar(e, 'camisetas', 1_500_000)
    pygame.event.clear()
    textos = _textos(O, O.render, screen, e)
    assert any(t.startswith("Llevas") and "camisetas" in t for t in textos)


# ---------------------------------------------------------------- P: jugador lesionado
def test_la_curva_del_descuento_crece_con_los_dias_de_baja():
    f = M.descuento_por_lesion
    assert f(0) == 0.0 and f(-3) == 0.0 and f(None) == 0.0                 # sano: sin descuento
    assert f(2) < 0.02                                                     # pocos días: casi nada
    assert 0.08 < f(21) < 0.16                                             # semanas: moderado
    assert 0.25 < f(90) < 0.35                                             # meses: fuerte
    dias = [1, 3, 7, 10, 28, 45, 90, 120, 180]
    assert all(f(a) < f(b) for a, b in zip(dias, dias[1:]))                # más días de baja, más descuento
    tope = M.DESCUENTO_LESION_TRAMOS[-1][1]
    assert abs(f(180) - tope) < 1e-9 and f(400) == tope                    # con el piso: nunca pasa del último tramo
    assert abs(M.factor_valor_lesion(90) - 0.70) < 1e-9 and M.factor_valor_lesion(0) == 1.0


def test_el_lesionado_vale_menos_se_afloja_con_los_dias_y_al_sanar_vuelve_a_su_valor():
    e = estado_carrera(); mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.lesion_dias = 0
    sano = M.calcular_valor(j)
    j.valor = sano
    j.lesion_dias = 60
    assert abs(M.calcular_valor(j) - sano * M.factor_valor_lesion(60)) <= 1
    assert M.calcular_valor(j, con_lesion=False) == sano
    assert M.sincronizar_valor_lesionados(e) >= 1                          # lo recalcula el reloj
    valor_60 = j.valor
    assert valor_60 < sano and abs(valor_60 - M.calcular_valor(j)) <= 1
    assert M.sincronizar_valor_lesionados(e) == 0                          # idempotente el mismo día
    j.lesion_dias = 10                                                     # pasan los días: el descuento se afloja
    assert M.sincronizar_valor_lesionados(e) >= 1
    assert valor_60 < j.valor < sano and abs(j.valor - M.calcular_valor(j)) <= 1
    j.lesion_dias = 0                                                      # sana
    assert M.sincronizar_valor_lesionados(e) >= 1
    assert j.valor == sano
    assert e['datos_carrera']['valor_lesion'] == {}                        # ya no queda recordado


def test_la_lista_vieja_de_lesionados_se_migra_sin_romper():
    e = estado_carrera(); j = e['mi_equipo'].jugadores[4]
    j.lesion_dias = 0
    sano = M.calcular_valor(j)
    j.lesion_dias = 40
    clave = f"{j.id}|{j.nombre} {j.apellido}"
    e['datos_carrera']['valor_lesion'] = [clave]                           # formato de la primera versión: una lista
    M.sincronizar_valor_lesionados(e)
    assert isinstance(e['datos_carrera']['valor_lesion'], dict) and e['datos_carrera']['valor_lesion'][clave] == sano
    assert j.valor < sano


def test_estar_lesionado_no_abarata_sueldo_ni_clausula():
    e = estado_carrera(); j = e['mi_equipo'].jugadores[1]
    j.lesion_dias = 0
    sueldo, contrato = F.salario_mercado(j), F.contrato_inicial(j, random.Random(1))
    j.lesion_dias = 30
    assert F.salario_mercado(j) == sueldo
    assert F.contrato_inicial(j, random.Random(1)) == contrato


def test_el_reloj_sincroniza_el_valor_de_los_lesionados():
    e = estado_carrera(); j = e['mi_equipo'].jugadores[2]
    j.lesion_dias = 0
    j.valor = M.calcular_valor(j)
    sano = j.valor
    j.lesion_dias = 14
    DI.hoy(e)
    DI.revisar_dia(e, DI.hoy(e))
    assert j.valor < sano


def test_la_ficha_muestra_lesionado_en_rojo_con_los_dias():
    from alpha_football.ui import ficha_jugador as FJ
    e = estado_carrera(); j = e['mi_equipo'].jugadores[3]
    rect = pygame.Rect(848, 80, 416, 616)
    j.lesion_dias = 0
    sana = _textos(FJ, FJ.dibujar_ficha, screen, rect, j)
    assert not any("LESIONADO" in t for t in sana)
    j.lesion_dias = 25
    pintados = []
    orig = FJ.draw_text
    FJ.draw_text = lambda s, t, pos, size='md', color='blanco', shadow=True: pintados.append((str(t), color))
    try:
        FJ.dibujar_ficha(screen, rect, j)
    finally:
        FJ.draw_text = orig
    les = [(t, c) for t, c in pintados if "LESIONADO" in t]
    assert les and les[0][1] == 'rojo' and "semanas" in les[0][0]
    real = int(round(M.descuento_por_lesion(25) * 100))                    # el % del texto es el de la curva
    assert f"vale {real}% menos" in les[0][0] and real > 0
    j.lesion_dias = 1                                                      # un día: el descuento no llega al 1%
    corto = _textos(FJ, FJ.dibujar_ficha, screen, rect, j)
    assert any(t.startswith("LESIONADO") for t in corto) and not any("vale" in t and "menos" in t for t in corto)


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
