# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Estilos de juego (v3.3.0)
9 estilos. ESTILO_VENTAJA[a] = estilos a los que `a` le gana (+10% / −9% en el duelo, v3.9.0).
Anchelottismo no gana ni pierde claro contra nadie (se adapta). Tabla de Diego con las
contradicciones resueltas según sus textos y equilibrada (v3.3.0 y v3.9.0; nadie con más de ±1).
Ver spec 2026-09-23-carrera-dt-design.md.
"""
from __future__ import annotations

# Orden original primero (el motor y los tests viejos dependen de él) + los 5 nuevos.
ESTILOS_DT: list[str] = ["haramball", "cruyffismo", "flickismo", "anchelottismo",
                         "kloppismo", "artetismo", "choloismo", "dezerbismo", "fullbackismo"]
ESTILOS_UI: list[str] = sorted(ESTILOS_DT, key=lambda e: e != "anchelottismo")

ESTILO_VENTAJA: dict[str, frozenset] = {
    # v3.9.0: equilibrio pedido por Diego — Cruyff le gana a Arteta, Fullback a Haramball;
    # Klopp–Cruyff y Flick–Fullback pasan a neutros. Nadie queda con más de ±1 de diferencia.
    "cruyffismo":   frozenset({"flickismo", "artetismo"}),
    "flickismo":    frozenset({"haramball", "artetismo"}),
    "haramball":    frozenset({"cruyffismo", "dezerbismo", "kloppismo"}),
    "kloppismo":    frozenset({"choloismo", "fullbackismo"}),
    "artetismo":    frozenset({"haramball", "choloismo", "dezerbismo"}),
    "choloismo":    frozenset({"cruyffismo", "dezerbismo", "fullbackismo"}),
    "dezerbismo":   frozenset({"flickismo", "kloppismo", "fullbackismo"}),
    "fullbackismo": frozenset({"cruyffismo", "haramball"}),
}

NOMBRE_ESTILO: dict[str, str] = {
    "haramball": "Haramball", "cruyffismo": "Cruyffismo", "flickismo": "Flickismo",
    "anchelottismo": "Ancelotismo", "kloppismo": "Kloppismo", "artetismo": "Artetismo",
    "choloismo": "Choloismo", "dezerbismo": "DeZerbismo", "fullbackismo": "Fullbackismo",
}

DESC_ESTILO: dict[str, str] = {
    "haramball": "Bloque bajo y balón largo: muro atrás y segundos balones.",
    "cruyffismo": "Tiki-taka: posesión y pases cortos.",
    "flickismo": "Presión alta y verticalidad rápida.",
    "anchelottismo": "Se adapta a todo: nunca gana ni pierde claro.",
    "kloppismo": "Gegenpress y caos organizado. Gasta 30% más de energía.",
    "artetismo": "Posesión disciplinada y balón parado nuclear.",
    "choloismo": "Bloque medio agresivo, duelos y transiciones cortas.",
    "dezerbismo": "Salida suicida desde el portero y tercer hombre.",
    "fullbackismo": "Laterales voladores y extremos por dentro.",
}

_LEGADO = {"guardiolismo": "cruyffismo", "simeonismo": "choloismo",
           "mourinhismo": "haramball", "bielsismo": "kloppismo"}


def normalizar_estilo(e) -> str:
    """Estilos viejos del editor → los 9 actuales (desconocido = anchelottismo)."""
    k = str(e or "").strip().lower()
    if k in ESTILOS_DT:
        return k
    return _LEGADO.get(k, "anchelottismo")


def factor_gasto_estilo(estilo) -> float:
    """v3.3.0: Kloppismo gasta 30% más de energía (su contrapartida)."""
    return 1.3 if str(estilo or "").lower() == "kloppismo" else 1.0
