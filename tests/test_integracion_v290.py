"""v2.9.0: integración — 3 temporadas completas con directiva, finanzas, contratos y mentalidad."""
import sys, os, random, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(31)
pygame.display.set_mode((1280, 720))

from alpha_football import save, engine, directiva as D, finanzas as F
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui.league_screen import inicializar_calendario_liga
from alpha_football.ui.match_screen import finalizar_jornada_liga, _ments
from alpha_football.ui import resumen_temporada_screen as R

save.guardar_en_slot = lambda *a, **k: None


class _Contador(logging.Handler):
    def __init__(self):
        super().__init__(logging.ERROR); self.errores = []
    def emit(self, record):
        self.errores.append(record.getMessage())


def test_tres_temporadas_sin_errores():
    contador = _Contador()
    logging.getLogger().addHandler(contador)
    liga = load_league_teams('argentina')
    mi = liga.equipos[3]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
         'segunda_division': segunda, 'datos_carrera': {}, 'historial': [], 'copa_user_en_copa': False}
    F.asegurar_contratos(e)
    for _temporada in range(3):
        D.definir_objetivo(e)
        liga, mi = e['liga'], e['mi_equipo']
        inicializar_calendario_liga(liga)
        for _ in range(liga.num_jornadas):
            p = next((p for p in liga.calendario if p.jornada == liga.jornada_actual
                      and mi.id in (p.local_id, p.visitante_id) and not p.jugado), None)
            if p is None:
                break
            loc = next(x for x in liga.equipos if x.id == p.local_id)
            vis = next(x for x in liga.equipos if x.id == p.visitante_id)
            r = engine.simular_partido(loc, vis, **_ments(loc, vis, mi))
            finalizar_jornada_liga(e, liga, mi, p, r.goles_local, r.goles_visitante)
        R.avanzar_nueva_temporada(e)
        if e.get('despido_pendiente'):
            D.cambiar_de_club(e, e['despido_pendiente']['opciones'][0])
        assert e['historial'][-1].get('objetivo_resultado') in ('superado', 'cumplido', 'fallado')
        assert all(int(j.salario) > 0 and j.contrato_anios >= 1 for j in e['mi_equipo'].jugadores)
    logging.getLogger().removeHandler(contador)
    fin = F.libro(e) if False else e['datos_carrera'].get('finanzas_anterior', {})
    print(f"    T{e['temporada']}: {e['mi_equipo'].nombre} · saldo ${e['mi_equipo'].balance / 1e6:.1f}M · "
          f"objetivos {[h.get('objetivo_resultado') for h in e['historial']]} · errores {len(contador.errores)}")
    assert not contador.errores, contador.errores[:5]
    print("  test_tres_temporadas_sin_errores: OK")


def test_guardar_y_cargar_conserva_lo_nuevo():
    import json
    from alpha_football.models import Liga, EstadoJuego
    from alpha_football import negociacion as N
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    e = {'liga': liga, 'mi_equipo': mi, 'temporada': 1, 'primera_division': primeras,
         'segunda_division': segunda, 'datos_carrera': {}}
    F.asegurar_contratos(e)
    D.definir_objetivo(e); D.actualizar_confianza(e, 2, 0)
    F.procesar_jornada(e, True, 1, 0)
    mi.mentalidad = 'ofensiva'
    mi.jugadores[0].transferible = True
    mi.jugadores[0].salario, mi.jugadores[0].contrato_anios = 1_234_567, 4
    N.registrar_pase(e, mi.jugadores[1], 'A', 'B', 10, False)
    datos = json.loads(json.dumps(save.campos_divisiones(e)))
    cargado = EstadoJuego.from_dict({'ligas': [liga.to_dict()], 'equipo_usuario_id': mi.id,
                                     'liga_usuario_id': liga.tipo, 'temporada': 1, **datos})
    dc = cargado.datos_carrera
    assert dc['objetivo']['texto'] and dc['confianza'] == D.CONFIANZA_INICIAL + 3
    assert dc['finanzas']['patrocinio'] > 0 and dc['historial_pases'][0]['de'] == 'A'
    liga2 = Liga.from_dict(datos['primera_division'][liga.tipo])
    mi2 = next(x for x in liga2.equipos if x.id == mi.id)
    assert mi2.mentalidad == 'ofensiva' and mi2.jugadores[0].transferible
    assert (mi2.jugadores[0].salario, mi2.jugadores[0].contrato_anios) == (1_234_567, 4)
    print("  test_guardar_y_cargar_conserva_lo_nuevo: OK")


if __name__ == '__main__':
    try:
        test_tres_temporadas_sin_errores()
        test_guardar_y_cargar_conserva_lo_nuevo()
        print("\n2/2 tests pasaron")
    except Exception as ex:
        import traceback; traceback.print_exc()
        print(f"  FAIL - {ex}\n\n?/2 tests pasaron")
        sys.exit(1)
