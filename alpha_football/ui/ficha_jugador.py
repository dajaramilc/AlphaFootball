# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ficha del jugador (v3.5.0)
Ficha compartida (sacada de plantilla_screen._dibujar_ficha): datos, contrato con montos exactos,
atributos, estadísticas y personalidad. La usan PLANTILLA y OFERTAS; cada pantalla dibuja sus botones.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import COLORS, draw_panel, draw_text, get_font
except Exception:
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass
    def get_font(size): return pygame.font.Font(None, 24)

logger = logging.getLogger(__name__)


def _valor(j) -> int:
    v = int(getattr(j, 'valor', 0) or 0)
    if v <= 0:
        try:
            from alpha_football.market import calcular_valor
            v = int(calcular_valor(j))
        except Exception:
            v = 0
    return v


def _ajustar(texto: str, ancho: int) -> str:
    """Recorta `texto` (con …) para que entre en `ancho` píxeles con la fuente chica."""
    f = get_font('sm')
    if f.size(texto)[0] <= ancho:
        return texto
    while texto and f.size(texto + "…")[0] > ancho:
        texto = texto[:-1]
    return texto.rstrip(" ·") + "…"


def dibujar_ficha(screen, rect: pygame.Rect, j, estado_txt: str = "", extra: Optional[list] = None) -> int:
    """Dibuja la ficha de `j` dentro de `rect`. Retorna la y final (para ubicar botones debajo).
    `extra`: líneas [(texto, color)] al final de la ficha (p. ej. amarillas acumuladas)."""
    from alpha_football.negociacion import dinero_exacto
    try:
        from alpha_football.vestuario import PERSONALIDAD_TXT
    except Exception:
        PERSONALIDAD_TXT = {}
    draw_panel(screen, rect)
    x, y = rect.x + 20, rect.y + 14
    try:
        draw_text(screen, f"{j.nombre} {j.apellido}"[:26], (x, y), size='lg', color='dorado')
        y += 40
        linea = f"{j.posicion}  ·  {j.edad} años  ·  {getattr(j, 'nacionalidad', '') or '—'}"
        if estado_txt:
            linea += f"  ·  {estado_txt}"
        draw_text(screen, _ajustar(linea, rect.width - 40), (x, y), size='sm', color='azul')
        y += 30
        draw_text(screen, f"MEDIA {j.overall}   POTENCIAL {getattr(j, 'potencial', 0) or '?'}", (x, y), size='md', color='verde')
        y += 30
        draw_text(screen, f"Valor {dinero_exacto(_valor(j))}  ·  Moral {j.moral}  ·  Energía {int(getattr(j, 'energia', 100))}",
                  (x, y), size='sm', color='blanco')
        y += 24
        anios = int(getattr(j, 'contrato_anios', 0) or 0)
        contrato = f"Contrato {anios} año{'s' if anios != 1 else ''}  ·  {dinero_exacto(getattr(j, 'salario', 0))}/año"
        clausula = f"Cláusula {dinero_exacto(getattr(j, 'clausula', 0))}"
        color_c = 'rojo' if anios <= 1 else 'blanco'
        if rect.width >= 520:            # ficha ancha: contrato y cláusula en una línea
            draw_text(screen, f"{contrato}  ·  {clausula}", (x, y), size='sm', color=color_c)
        else:                            # montos exactos: en la ficha angosta van en dos líneas
            draw_text(screen, contrato, (x, y), size='sm', color=color_c)
            y += 22
            draw_text(screen, clausula, (x, y), size='sm', color='blanco')
        y += 30
        ancho_barra = max(60, min(220, rect.width - 200))
        for nombre, val in (("Ataque", j.ataque), ("Defensa", j.defensa), ("Físico", j.fisico),
                            ("Técnica", j.tecnica), ("Mental", j.mental), ("Penales", getattr(j, 'penales', 0)),
                            ("Resistencia", getattr(j, 'resistencia', 50))):
            val = int(val or 0)
            draw_text(screen, nombre, (x, y), size='sm', color='blanco')
            barra = pygame.Rect(x + 100, y + 4, ancho_barra, 12)
            pygame.draw.rect(screen, (30, 40, 60), barra, border_radius=4)
            lleno = barra.copy(); lleno.width = int(barra.width * max(0, min(99, val)) / 99)
            color = COLORS['verde'] if val >= 80 else COLORS['dorado'] if val >= 65 else COLORS['rojo']
            pygame.draw.rect(screen, color, lleno, border_radius=4)
            draw_text(screen, str(val), (barra.right + 12, y), size='sm', color='blanco')
            y += 22                      # más juntas: deja lugar a las líneas extra
        y += 4
        nota = float(getattr(j, 'promedio_nota', 0.0) or 0.0)
        stats = f"PJ {j.partidos_jugados}  ·  Goles {j.goles}  ·  Asist. {getattr(j, 'asistencias', 0)}  ·  Nota {nota:.1f}"
        draw_text(screen, stats, (x, y), size='sm', color='blanco')
        y += 24
        if j.posicion == 'POR':
            draw_text(screen, f"Vallas invictas: {getattr(j, 'porterias_cero', 0)}", (x, y), size='sm', color='blanco')
            y += 24
        rasgo_txt = f"Rasgo: {str(j.rasgo).replace('_', ' ')}" if getattr(j, 'rasgo', None) else ""
        pers_txt = f"Personalidad: {PERSONALIDAD_TXT.get(getattr(j, 'personalidad', ''), '-')}"
        junto = f"{rasgo_txt}  ·  {pers_txt}" if rasgo_txt else pers_txt
        # v3.9.0: si rasgo + personalidad no caben en el ancho de la ficha, van en dos líneas
        if rasgo_txt and get_font('sm').size(junto)[0] > rect.width - 40:
            draw_text(screen, rasgo_txt, (x, y), size='sm', color='azul')
            y += 24
            junto = pers_txt
        draw_text(screen, junto, (x, y), size='sm', color='azul')
        y += 24
        for texto, color in extra or []:
            draw_text(screen, _ajustar(str(texto), rect.width - 40), (x, y), size='sm', color=color)
            y += 22
    except Exception as e:
        logger.error(f"Error al dibujar la ficha del jugador: {e}")
    return y
