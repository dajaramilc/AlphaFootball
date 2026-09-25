# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — BARRA DE ATAJOS (footer global)
v3.6.0: registro central de los atajos de teclado de cada pantalla. main.py dibuja la barra
al pie (franja de 22 px en y = 698) después del render de cada pantalla, salvo en las que
tienen su propia ayuda (SIN_BARRA). Toda entrada incluye "H Ayuda" (overlay: sub-proyecto 8).
"""
from __future__ import annotations

import logging
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, get_font
except Exception:
    SCREEN_W = 1280
    COLORS = {'azul': (0, 191, 255), 'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 20)

logger = logging.getLogger(__name__)

R_BARRA = pygame.Rect(0, 698, 1280, 22)
SIN_BARRA = {'menu', 'match_screen'}
POR_DEFECTO = "H Ayuda · ESC Volver"

# v3.6.0: atajos reales de cada pantalla (leídos de sus KEYDOWN). Formato "Tecla Acción · ... · H Ayuda".
ATAJOS = {
    'league_screen': "J Jugar · ← → Pestañas · ↑ ↓ Opción · Enter Abrir · R Resultados · M Correo · O Opciones · H Ayuda · ESC Salir",
    'market_screen': "← → Pestañas · F Filtros · P País · RePág AvPág Página · H Ayuda · ESC Volver",
    'copa_screen': "1-4 Pestañas · ← → Fecha/Pestaña · C Copa · R Simular resto · H Ayuda · ESC Volver",   # v3.8.0
    'career_screen': "↑ ↓ Desplazar · H Ayuda · ESC Volver",
    'team_screen': "Flechas Jugador · Espacio Cambiar · Enter OK · A Auto · R Reservas · [ ] Formación · - = Estilo · , . Ment. · H Ayuda · ESC Cancelar",
    'options_screen': "↑ ↓ Opción · ← → Volumen · Enter Activar (GUARDAR en carrera) · H Ayuda · ESC Volver",
    'prepartido_screen': "1-4 Opción · ↑ ↓ Mover · Enter Elegir · H Ayuda · ESC Volver",
    'ofertas_screen': "↑ ↓ ← → Mover · A Aceptar · R Rechazar · Enter Elegir · H Ayuda · ESC Volver",
    'stats_screen': "← → Pestañas · L Liga · T Mi equipo · Enter Elegir · H Ayuda · ESC Volver",
    'save_slots_screen': "↑ ↓ Slot · Enter Guardar/Cargar · Supr Borrar · H Ayuda · ESC Volver",
    'resumen_temporada_screen': "Enter Empezar temporada · H Ayuda",
    'edit_screen': "↑ ↓ Equipo/Jugador · → Plantilla · ← Equipo · Ctrl+S Guardar · Clic Editar · Enter Confirmar texto · H Ayuda · ESC Menú",
    'promo_releg_screen': "Enter Continuar · H Ayuda · ESC Continuar",
    'otras_ligas_screen': "↑ ↓ País · ← → División · C Copas · H Ayuda · ESC Volver",   # v3.8.0
    'plantilla_screen': "↑ ↓ Jugador · Clic columna Ordenar · S Orden · T Transferible · R Renovar · H Ayuda · ESC Volver",
    'buscador_screen': "↑ ↓ Jugador · Tab Campo · Enter Buscar · Filtros · Solo libres · H Ayuda · ESC Volver",
    'historial_pases_screen': "← → Pestaña · ↑ ↓ RePág AvPág Desplazar · H Ayuda · ESC Volver",
    'ojeador_screen': "← → Fichaje · Enter Fichar · M Correo · H Ayuda · ESC Volver",
    'objetivos_screen': "1 2 3 Espaldarazo · H Ayuda · ESC Volver",
    'correo_screen': "↑ ↓ Mensaje · Enter Ir · O Opciones · H Ayuda · ESC Volver",
    'despido_screen': "← → Club · Enter Aceptar · H Ayuda",
    'finanzas_screen': "H Ayuda · ESC Volver",
    'negociacion_screen': "← → Tab Botón · Enter Pulsar · 0-9 Monto · H Ayuda · ESC Cancelar",
    'contrato_dt_screen': "← → Oferta · Enter Aceptar · R Rechazar renovación · H Ayuda · ESC Volver",
    'veredicto_screen': "Enter Continuar · H Ayuda",
    'ofertas_dt_screen': "← → ↑ ↓ Botón · Enter Pulsar · H Ayuda · ESC Volver",
}


def texto(nombre_pantalla: str, estado: dict) -> str:
    """v3.6.0: texto de la barra para la pantalla (por defecto "H Ayuda · ESC Volver")."""
    try:
        estado = estado or {}
        if nombre_pantalla == 'league_screen' and estado.get('hub_tab', 'inicio') != 'inicio':
            return ATAJOS['league_screen'].replace("ESC Salir", "ESC Inicio")
        if nombre_pantalla == 'prepartido_screen' and estado.get('prepartido_resultado'):   # v4.1.0
            return "↑ ↓ Desplazar · ← → Pestaña · Enter Continuar · H Ayuda"
        if nombre_pantalla == 'buscador_screen' and estado.get('filtros_abierto'):
            return "Clic Campo · 0-9 Escribir · Tab Siguiente · Enter Aplicar · H Ayuda · ESC Cerrar"
        return ATAJOS.get(nombre_pantalla, POR_DEFECTO)
    except Exception as e:
        logger.error(f"No se pudo armar la barra de atajos de {nombre_pantalla}: {e}")
        return POR_DEFECTO


def dibujar(screen, nombre_pantalla: str, estado: dict) -> None:
    """v3.6.0: franja semitransparente al pie con los atajos de la pantalla, texto centrado."""
    try:
        if nombre_pantalla in SIN_BARRA:
            return
        franja = pygame.Surface(R_BARRA.size, pygame.SRCALPHA)
        franja.fill((6, 10, 20, 200))
        screen.blit(franja, R_BARRA.topleft)
        pygame.draw.line(screen, (40, 60, 90), R_BARRA.topleft, (R_BARRA.right, R_BARRA.y), 1)
        fuente = get_font('sm')
        partes = texto(nombre_pantalla, estado).split(" · ")
        # si no cabe, se quitan atajos intermedios (se conservan los dos últimos: H Ayuda / ESC)
        while len(partes) > 2 and fuente.size(" · ".join(partes))[0] > R_BARRA.width - 16:
            partes.pop(-3)
        s = fuente.render(" · ".join(partes), True, COLORS.get('azul', (0, 191, 255)))
        screen.blit(s, s.get_rect(center=R_BARRA.center))
    except Exception as e:
        logger.error(f"No se pudo dibujar la barra de atajos: {e}")
