# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Negociación (Pygame)
v2.9.0: fichar ya no es directo. 1) oferta al club (acepta, rechaza con contraoferta o
se paga la cláusula); 2) contrato con el jugador (salario anual, años y cláusula).
Las renovaciones usan solo el paso 2. Estado en estado['neg'] (negociacion.iniciar_negociacion).
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import negociacion as N
from alpha_football import finanzas as F
from alpha_football.ui.entrada_monto import editar_valor   # v3.5.0

logger = logging.getLogger(__name__)

R_INFO = pygame.Rect(16, 76, 400, 620)          # v3.9.0: termina en y=696 (antes 704, bajo la barra)
R_CLUB = pygame.Rect(432, 76, 832, 262)
R_JUG = pygame.Rect(432, 350, 832, 296)
CLAUSULAS = [1.5, 2.0, 3.0]


def _orden_foco(etapa: str, modo: str = '') -> list:
    """v4.2.0: botones que recorre el teclado en cada etapa (el primero tiene el foco al entrar)."""
    if modo == 'prestamo' and etapa == 'jugador':      # préstamo: mismo contrato, solo PROPONER
        return ['proponer', 'volver']
    return {'club': ['ofertar', 'clausula', 'monto_menos', 'monto_mas', 'volver'],
            'jugador': ['proponer', 'sal_menos', 'sal_mas', 'anios_menos', 'anios_mas', 'clau_ciclo', 'volver'],
            }.get(etapa, ['volver'])


def _rects() -> dict:
    cx, jx = R_CLUB.x + 20, R_JUG.x + 20
    return {
        'monto_menos': pygame.Rect(cx, R_CLUB.y + 110, 44, 44),
        'monto_mas': pygame.Rect(cx + 320, R_CLUB.y + 110, 44, 44),
        'ofertar': pygame.Rect(cx, R_CLUB.y + 180, 250, 48),
        'clausula': pygame.Rect(cx + 270, R_CLUB.y + 180, 500, 48),    # v3.5.0: cabe el monto exacto
        'sal_menos': pygame.Rect(jx, R_JUG.y + 70, 44, 44),
        'sal_mas': pygame.Rect(jx + 320, R_JUG.y + 70, 44, 44),
        'anios_menos': pygame.Rect(jx + 420, R_JUG.y + 70, 44, 44),
        'anios_mas': pygame.Rect(jx + 620, R_JUG.y + 70, 44, 44),
        'clau_ciclo': pygame.Rect(jx, R_JUG.y + 140, 364, 44),
        'proponer': pygame.Rect(jx, R_JUG.y + 214, 364, 52),
        'volver': pygame.Rect(1016, 650, 248, 44),         # v3.9.0: termina en y=694 (antes 704)
        'monto': pygame.Rect(cx + 50, R_CLUB.y + 110, 264, 44),          # v3.9.0: cajas expuestas (ayuda H)
        'salario': pygame.Rect(jx + 50, R_JUG.y + 70, 264, 44),
        'anios': pygame.Rect(jx + 470, R_JUG.y + 70, 144, 44),
    }


def _m(v) -> str:
    return N.dinero_exacto(v)          # v3.5.0: montos exactos


def _caja(screen, rect, texto, color='blanco'):
    pygame.draw.rect(screen, (15, 22, 40), rect, border_radius=6)
    pygame.draw.rect(screen, COLORS['azul'], rect, width=1, border_radius=6)
    s = get_font('md').render(texto, True, COLORS[color])
    screen.blit(s, s.get_rect(center=rect.center))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna la pantalla de origen al terminar/cancelar, o None para seguir aquí."""
    try:
        neg = estado.get('neg')
        if neg is not None and not neg.get('_foco_listo'):   # v4.2.0: cada negociación arranca en OFERTAR
            for k in ('foco_neg_club', 'foco_neg_jugador', 'foco_neg_hecho'):
                estado.pop(k, None)
            neg['_foco_listo'] = True
        mi = estado.get('mi_equipo')
        if not neg or mi is None:
            return 'league_screen'
        j, club, modo = neg['jugador'], neg['club'], neg['modo']
        rects = _rects()
        mouse_pos = pygame.mouse.get_pos()
        precio = N.precio_fichaje(j)
        paso_monto = max(10_000, int(precio * 0.05))
        pedido_ref = N.salario_pedido(j, modo, neg['clausula_mult'])
        paso_sal = max(5_000, int(pedido_ref * 0.05))

        def salir():
            destino = neg.get('volver', 'league_screen')
            estado.pop('neg', None)
            return destino

        # v4.2.0: ← → / Tab recorren los botones de la etapa, Enter los pulsa (los dígitos siguen al monto)
        from alpha_football.ui.foco import traducir_eventos, marcar
        orden_foco = _orden_foco(neg['etapa'], modo)
        _foco, eventos = traducir_eventos(estado, f"foco_neg_{neg['etapa']}", [rects[k] for k in orden_foco],
                                          list(pygame.event.get()))
        for ev in eventos:
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return salir()
            if ev.type == pygame.KEYDOWN and neg['etapa'] == 'club' and modo != 'prestamo':   # v3.5.0: monto tecleable (el % no)
                neg['monto'] = editar_valor(neg['monto'], ev)
                continue
            if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
                continue
            p = ev.pos
            if rects['volver'].collidepoint(p):
                return salir()
            if neg['etapa'] == 'club':
                if modo == 'prestamo':      # préstamo: % del sueldo que pagas y duración
                    from alpha_football import prestamos as PR
                    if rects['monto_menos'].collidepoint(p):
                        neg['pct'] = max(PR.PCT_PASO, neg['pct'] - PR.PCT_PASO)
                    elif rects['monto_mas'].collidepoint(p):
                        neg['pct'] = min(100, neg['pct'] + PR.PCT_PASO)
                    elif rects['clausula'].collidepoint(p):
                        neg['meses'] = 12 if neg['meses'] == 6 else 6
                    elif rects['ofertar'].collidepoint(p):
                        resp, msg = PR.evaluar_pedido(estado, j, club, neg['meses'], neg['pct'])
                        neg['msg'] = (msg, {'acepta': 'verde', 'analiza': 'azul'}.get(resp, 'rojo'))
                        if resp == 'acepta':
                            neg['etapa'] = 'jugador'
                        elif resp == 'analiza':
                            neg['etapa'], neg['acuerdo_club'] = 'hecho', False
                    continue
                if rects['monto_menos'].collidepoint(p):
                    neg['monto'] = max(0, neg['monto'] - paso_monto)
                elif rects['monto_mas'].collidepoint(p):
                    neg['monto'] += paso_monto
                elif rects['ofertar'].collidepoint(p) or rects['clausula'].collidepoint(p):
                    if rects['clausula'].collidepoint(p):
                        neg['monto'] = int(j.clausula)
                    if neg['monto'] > mi.balance:
                        neg['msg'] = ("No te alcanza el presupuesto para esa oferta.", 'rojo')
                        continue
                    # v3.5.0: acepta / "lo analizamos" (respuesta por correo) / rechaza
                    resp, msg, contra = N.evaluar_compra(estado, j, club, neg['monto'])
                    if resp == 'acepta':
                        neg['msg'] = (msg, 'verde')
                        neg['etapa'] = 'jugador'
                    elif resp == 'analiza':
                        neg['msg'] = (msg, 'azul')
                        neg['etapa'], neg['acuerdo_club'] = 'hecho', False
                    else:
                        neg['msg'] = (msg, 'rojo')
                        if contra:
                            neg['contra_club'] = contra
            elif neg['etapa'] == 'jugador':
                if modo == 'prestamo':      # préstamo: el jugador acepta o no (mismo contrato)
                    if rects['proponer'].collidepoint(p):
                        from alpha_football import prestamos as PR
                        ok_j, msg_j = PR.acepta_jugador(estado, j, club)
                        if not ok_j:
                            neg['msg'], neg['etapa'], neg['acuerdo_jugador'] = (msg_j, 'rojo'), 'hecho', False
                            continue
                        ok, msg = PR.cerrar_pedido(estado, j, club, neg['meses'], neg['pct'])
                        neg['msg'] = (msg, 'verde' if ok else 'rojo')
                        neg['etapa'] = 'hecho'
                        estado.pop('busq_resultados', None)
                    continue
                if rects['sal_menos'].collidepoint(p):
                    neg['salario'] = max(F.SALARIO_MIN, neg['salario'] - paso_sal)
                elif rects['sal_mas'].collidepoint(p):
                    neg['salario'] += paso_sal
                elif rects['anios_menos'].collidepoint(p):
                    neg['anios'] = max(1, neg['anios'] - 1)
                elif rects['anios_mas'].collidepoint(p):
                    neg['anios'] = min(5, neg['anios'] + 1)
                elif rects['clau_ciclo'].collidepoint(p):
                    i = CLAUSULAS.index(neg['clausula_mult']) if neg['clausula_mult'] in CLAUSULAS else 1
                    neg['clausula_mult'] = CLAUSULAS[(i + 1) % len(CLAUSULAS)]
                elif rects['proponer'].collidepoint(p):
                    ok, msg, contra = N.evaluar_contrato(j, neg['salario'], neg['anios'], neg['clausula_mult'], modo)
                    if not ok:
                        aviso = N.analizar_contrato(estado, neg)     # v4.4.0: "lo analizo" si está cerca
                        if aviso:
                            neg['msg'] = (aviso, 'azul')
                            neg['etapa'], neg['acuerdo_jugador'] = 'hecho', False
                        else:
                            neg['msg'] = (msg, 'rojo')
                        continue
                    if modo == 'renovar':
                        N.renovar(estado, j, neg['salario'], neg['anios'], neg['clausula_mult'])
                        neg['msg'], neg['etapa'] = (f"¡{j.nombre_completo} renovó por {neg['anios']} años!", 'verde'), 'hecho'
                    else:
                        ok, msg = N.completar_fichaje(estado, j, club, neg['monto'], neg['salario'],
                                                      neg['anios'], neg['clausula_mult'])
                        neg['msg'] = (msg, 'verde' if ok else 'rojo')
                        if ok:
                            neg['etapa'] = 'hecho'
                            estado.pop('busq_resultados', None)

        # --- Dibujo ---
        draw_gradient_bg(screen)
        titulo = {"renovar": "RENOVACIÓN", "prestamo": "PRÉSTAMO"}.get(modo, "NEGOCIACIÓN")
        draw_text(screen, f"{titulo}: {j.nombre_completo}"[:52], (16, 14), size='lg', color='dorado')
        draw_text(screen, f"Tu presupuesto {_m(mi.balance)}  ·  Masa salarial {_m(F.masa_salarial(mi, estado))}/año",
                  (16, 50), size='sm', color='verde' if mi.balance >= 0 else 'rojo')

        draw_panel(screen, R_INFO)
        x, y = R_INFO.x + 20, R_INFO.y + 16
        for texto, size, color in (
                (getattr(club, 'nombre', mi.nombre if modo == 'renovar' else 'Agente libre')[:26], 'md', 'azul'),
                (f"{j.posicion}  ·  {j.edad} años", 'md', 'blanco'),
                (f"MEDIA {j.overall}  ·  POT {getattr(j, 'potencial', 0) or '?'}", 'lg', 'verde'),
                (f"Valor {_m(F._valor(j))}", 'sm', 'blanco'),
                (f"Precio de mercado {_m(precio)}", 'sm', 'blanco'),
                ("", 'sm', 'blanco'),
                ("CONTRATO ACTUAL", 'sm', 'dorado'),
                (f"Salario {_m(j.salario)} / año", 'sm', 'blanco'),
                (f"Le quedan {j.contrato_anios} año{'s' if j.contrato_anios != 1 else ''}", 'sm', 'blanco'),
                (f"Cláusula {_m(j.clausula)}", 'sm', 'blanco')):
            if texto:
                draw_text(screen, texto, (x, y), size=size, color=color)
            y += 44 if size == 'lg' else 32

        # Paso 1: club
        draw_panel(screen, R_CLUB)
        cx, cy = R_CLUB.x + 20, R_CLUB.y + 14
        if modo == 'renovar' or club is None:
            draw_text(screen, "1. CLUB", (cx, cy), size='md', color='azul')
            draw_text(screen, "Renovación: no hay club con quien negociar." if modo == 'renovar'
                      else "Agente libre: sin traspaso, solo contrato.", (cx, cy + 40), size='md', color='blanco')
        elif modo == 'prestamo':
            # préstamo: % del sueldo que pagas (de 10 en 10) y duración 6 meses / 1 año
            activo = neg['etapa'] == 'club'
            draw_text(screen, f"1. PRÉSTAMO DE {club.nombre.upper()}"[:44], (cx, cy), size='md',
                      color='dorado' if activo else 'verde')
            draw_text(screen, f"Sueldo {_m(j.salario)}/año  ·  Tú pagas {neg['pct']}% = {_m(j.salario * neg['pct'] // 100)}",
                      (cx, cy + 40), size='sm', color='blanco')
            draw_text(screen, "% del sueldo que pagas tú:" + ("  (− / +)" if activo else ""), (cx, cy + 72),
                      size='sm', color='azul')
            _caja(screen, rects['monto'], f"{neg['pct']}%", 'verde' if activo else 'blanco')
            if activo:
                for k, t in (('monto_menos', '−'), ('monto_mas', '+')):
                    draw_button(screen, rects[k], t, rects[k].collidepoint(mouse_pos))
                draw_button(screen, rects['ofertar'], "PEDIR", rects['ofertar'].collidepoint(mouse_pos))
                draw_button(screen, rects['clausula'], f"DURACIÓN: {'6 MESES' if neg['meses'] == 6 else '1 AÑO'} (cambiar)",
                            rects['clausula'].collidepoint(mouse_pos))
            elif neg['etapa'] == 'hecho' and not neg.get('acuerdo_club', True):
                draw_text(screen, "El club lo analiza: respuesta por correo", (cx + 400, R_CLUB.y + 124), size='sm', color='azul')
            else:
                draw_text(screen, "Acuerdo cerrado con el club", (cx + 400, R_CLUB.y + 120), size='md', color='verde')
        else:
            activo = neg['etapa'] == 'club'
            draw_text(screen, f"1. OFERTA A {club.nombre.upper()}"[:44], (cx, cy), size='md',
                      color='dorado' if activo else 'verde')
            draw_text(screen, f"Precio de mercado {_m(precio)}  ·  Cláusula {_m(j.clausula)}"
                      + (f"  ·  Pidieron {_m(neg['contra_club'])}" if neg.get('contra_club') else ""),
                      (cx, cy + 40), size='sm', color='blanco')
            draw_text(screen, "Tu oferta:" + ("  (escribe la cifra o usa − / +)" if activo else ""),
                      (cx, cy + 72), size='sm', color='azul')
            _caja(screen, rects['monto'], _m(neg['monto']),
                  'verde' if activo else 'blanco')
            if activo:
                for k, t in (('monto_menos', '−'), ('monto_mas', '+')):
                    draw_button(screen, rects[k], t, rects[k].collidepoint(mouse_pos))
                draw_button(screen, rects['ofertar'], "OFERTAR", rects['ofertar'].collidepoint(mouse_pos))
                draw_button(screen, rects['clausula'], f"PAGAR CLÁUSULA ({_m(j.clausula)})",
                            rects['clausula'].collidepoint(mouse_pos))
            elif neg['etapa'] == 'hecho' and not neg.get('acuerdo_club', True):
                draw_text(screen, "El club lo analiza: respuesta por correo", (cx + 400, R_CLUB.y + 124), size='sm', color='azul')
            else:
                draw_text(screen, "Acuerdo cerrado con el club", (cx + 400, R_CLUB.y + 120), size='md', color='verde')

        # Paso 2: jugador
        draw_panel(screen, R_JUG)
        jx, jy = R_JUG.x + 20, R_JUG.y + 14
        activo = neg['etapa'] == 'jugador'
        draw_text(screen, "2. CONTRATO CON EL JUGADOR", (jx, jy), size='md',
                  color='dorado' if activo else ('verde' if neg['etapa'] == 'hecho' else 'azul'))
        if neg['etapa'] == 'club' or not neg.get('acuerdo_club', True):
            draw_text(screen, "Primero cierra el acuerdo con el club.", (jx, jy + 44), size='md', color='blanco')
        elif modo == 'prestamo':
            # préstamo: sigue con su contrato; solo hay que convencer al jugador
            draw_text(screen, f"Mismo contrato. Duración {'6 meses' if neg['meses'] == 6 else '1 año'}; "
                              f"pagas el {neg['pct']}% del sueldo.", (jx, jy + 44), size='sm', color='blanco')
            if activo:
                draw_button(screen, rects['proponer'], "PROPONER PRÉSTAMO", rects['proponer'].collidepoint(mouse_pos))
        else:
            draw_text(screen, f"Salario anual (pide {_m(pedido_ref)})", (jx, jy + 36), size='sm', color='azul')
            draw_text(screen, "Años", (jx + 420, jy + 36), size='sm', color='azul')
            _caja(screen, rects['salario'], _m(neg['salario']),
                  'verde' if neg['salario'] >= pedido_ref else 'blanco')
            _caja(screen, rects['anios'], str(neg['anios']))
            if activo:
                for k, t in (('sal_menos', '−'), ('sal_mas', '+'), ('anios_menos', '−'), ('anios_mas', '+')):
                    draw_button(screen, rects[k], t, rects[k].collidepoint(mouse_pos))
                draw_button(screen, rects['clau_ciclo'], f"CLÁUSULA ×{neg['clausula_mult']:g}  ({_m(F._valor(j) * neg['clausula_mult'])})",
                            rects['clau_ciclo'].collidepoint(mouse_pos))
                draw_button(screen, rects['proponer'], "PROPONER CONTRATO", rects['proponer'].collidepoint(mouse_pos))
                draw_text(screen, "Cláusula más alta = pide más salario.",
                          (jx + 400, R_JUG.y + 152), size='sm', color='azul')
                draw_text(screen, "Con 32+ años firma hasta 2 años.", (jx + 400, R_JUG.y + 176), size='sm', color='azul')
                costo = neg['salario'] * neg['anios']
                draw_text(screen, f"Costo total del contrato: {_m(costo)}", (jx + 400, R_JUG.y + 226), size='sm', color='blanco')
            elif not neg.get('acuerdo_jugador', True):     # v4.4.0
                draw_text(screen, "El jugador lo analiza: respuesta por correo", (jx, R_JUG.y + 152), size='md', color='azul')

        msg = neg.get('msg')
        if msg:
            # v3.5.0: montos exactos alargan los mensajes → hasta 2 líneas que no pisan el botón VOLVER
            fuente, lineas, linea = get_font('sm'), [], ""
            for palabra in str(msg[0]).split():
                prueba = (linea + " " + palabra).strip()
                if fuente.size(prueba)[0] > rects['volver'].x - 448 and linea:
                    lineas.append(linea)
                    linea = palabra
                else:
                    linea = prueba
            for k, texto in enumerate((lineas + [linea])[:2]):
                draw_text(screen, texto, (432, 654 + k * 24), size='sm', color=msg[1])
        draw_button(screen, rects['volver'], "VOLVER" if neg['etapa'] == 'hecho' else "CANCELAR",
                    rects['volver'].collidepoint(mouse_pos))
        orden_foco = _orden_foco(neg['etapa'], modo)
        marcar(screen, rects[orden_foco[int(estado.get(f"foco_neg_{neg['etapa']}", 0) or 0) % len(orden_foco)]])
        return None
    except Exception as e:
        logger.error(f"Error en negociacion_screen: {e}", exc_info=True)
        estado.pop('neg', None)
        return 'league_screen'
