# -*- coding: utf-8 -*-
"""
alpha_football/engine.py

Motor de simulacion de partidos:
- Resuelve ataques y goles minuto a minuto.
- Parametros calibrados para ~1.2-1.5 goles por equipo por partido.
- Logica de tabla de posiciones (Liga BetPlay).

Cambio clave respecto al prototipo original:
  SIGMA_CHOQUE = 30.0  (era 12)
  Con sigma=12 y UMBRAL_GOL=38, la tasa de goles era < 0.1 goles/partido.
  Con sigma=30 se obtiene ~10% por oportunidad → ~1.3 goles/equipo/partido.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

# ── Parametros tacticos ───────────────────────────────────────────────────────
ESTILOS_DT: list[str] = ["haramball", "cruyffismo", "flickismo"]

# Rock-paper-scissors: la clave vence al valor
ESTILO_VENTAJA: dict[str, str] = {
    "cruyffismo": "flickismo",
    "flickismo":  "haramball",
    "haramball":  "cruyffismo",
}

RASGOS: list[str] = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

# ── Parametros de simulacion ──────────────────────────────────────────────────
# Probabilidad de que ocurra un evento de ataque por equipo por minuto
PROB_ATAQUE: float = 0.14

# Sigma de la distribucion gaussiana en resolver_choque.
# Valor original 12 → casi cero goles por partido.
# Valor calibrado 30 → ~10% de conversion por oportunidad → ~1.3 goles/equipo/partido.
SIGMA_CHOQUE: float = 30.0

UMBRAL_GOL:  float = 38.0   # diff > umbral → gol
UMBRAL_TIRO: float = 15.0   # diff > umbral → tiro (no convierte)

# Multiplicador de ataque para el equipo local (ventaja de cancha ~6%)
VENTAJA_LOCAL: float = 1.06


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class Jugador:
    nombre:   str
    apellido: str
    posicion: str
    ataque:   int
    defensa:  int
    fisico:   int
    tecnica:  int
    mental:   int
    moral:    int = 70
    rasgo:    Optional[str] = None
    lesion_partidos: int = 0

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    @property
    def overall(self) -> int:
        return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5

    def poder_ataque_efectivo(self, mult: float = 1.0) -> float:
        base = (self.ataque + self.tecnica * 0.5 + self.fisico * 0.3) * (self.moral / 70)
        if self.rasgo == "regateador":       base *= 1.15
        if self.rasgo == "pulmon_de_hierro": base *= 1.05
        return base * mult

    def poder_defensa_efectivo(self, mult: float = 1.0) -> float:
        base = (self.defensa + self.fisico * 0.5 + self.mental * 0.3) * (self.moral / 70)
        if self.rasgo == "rustico": base *= 1.20
        if self.rasgo == "lider":   base *= 1.08
        return base * mult


@dataclass
class Equipo:
    nombre:    str
    ciudad:    str
    estrellas: float
    estilo_dt: str
    balance:   int
    jugadores: list = field(default_factory=list)
    alineacion_activa: Optional[Any] = None

    @property
    def id(self) -> str:
        """Generador de identificador único de equipo basado en su nombre."""
        try:
            return self.nombre.lower().replace(" ", "_")
        except Exception:
            return "equipo_desconocido"

    @property
    def once_disponible(self) -> list:
        """
        Retorna los 11 jugadores iniciales si el usuario definió una alineación activa válida,
        o cae de vuelta a los jugadores no lesionados.
        """
        try:
            if self.alineacion_activa:
                titulares_indices = self.alineacion_activa.titulares
                disp = []
                for idx in titulares_indices:
                    if 0 <= idx < len(self.jugadores):
                        j = self.jugadores[idx]
                        if j.lesion_partidos == 0:
                            disp.append(j)
                if disp:
                    return disp
        except Exception as e_alin:
            # Resiliencia: si hay error con alineacion_activa, usamos el flujo por defecto
            pass

        disp = [j for j in self.jugadores if j.lesion_partidos == 0]
        return disp if disp else self.jugadores

    def promedio_ataque(self, mult: float = 1.0) -> float:
        j = self.once_disponible
        return sum(x.poder_ataque_efectivo(mult) for x in j) / max(len(j), 1)

    def promedio_defensa(self, mult: float = 1.0) -> float:
        j = self.once_disponible
        return sum(x.poder_defensa_efectivo(mult) for x in j) / max(len(j), 1)

    def promedio_tecnica_mental(self) -> float:
        j = self.once_disponible
        return sum((x.tecnica + x.mental) / 2 for x in j) / max(len(j), 1)

    def jugador_estrella(self) -> Jugador:
        return max(self.jugadores, key=lambda j: j.overall)

    def ovr_promedio(self) -> int:
        if not self.jugadores:
            return 0
        return sum(j.overall for j in self.jugadores) // len(self.jugadores)

    def tick_lesiones(self) -> None:
        for j in self.jugadores:
            if j.lesion_partidos > 0:
                j.lesion_partidos -= 1


@dataclass
class Resultado:
    equipo_local:     str
    equipo_visitante: str
    goles_local:      int
    goles_visitante:  int
    eventos:          list = field(default_factory=list)  # Lista de eventos ocurridos en el partido

    def ganador(self) -> Optional[str]:
        if self.goles_local > self.goles_visitante: return self.equipo_local
        if self.goles_visitante > self.goles_local: return self.equipo_visitante
        return None


@dataclass
class Standing:
    equipo: str
    pj: int = 0
    g:  int = 0
    e:  int = 0
    p:  int = 0
    gf: int = 0
    gc: int = 0
    pts: int = 0

    @property
    def dg(self) -> int:
        return self.gf - self.gc


# ── Tactica ───────────────────────────────────────────────────────────────────

def bono_estilo(estilo_atk: str, estilo_def: str) -> float:
    """Bonus/malus tactico (rock-paper-scissors). +15% al ganador, -13% al perdedor."""
    if ESTILO_VENTAJA.get(estilo_atk) == estilo_def: return 1.15
    if ESTILO_VENTAJA.get(estilo_def) == estilo_atk: return 0.87
    return 1.0


# ── Nucleo de simulacion ──────────────────────────────────────────────────────

def resolver_choque(
    atk:        float,
    def_:       float,
    estilo_atk: str,
    estilo_def: str,
) -> str:
    """
    Resuelve un duelo 1v1 atacante-defensor.
    Retorna 'gol', 'tiro' o 'defensa'.
    """
    poder = atk * bono_estilo(estilo_atk, estilo_def)
    diff  = poder - def_ + random.gauss(0.0, SIGMA_CHOQUE)
    if diff > UMBRAL_GOL:  return "gol"
    if diff > UMBRAL_TIRO: return "tiro"
    return "defensa"


def _probs_ataque(local: Equipo, visitante: Equipo) -> tuple[float, float]:
    """
    Probabilidades de ataque por minuto basadas en posesion (tecnica+mental).
    El equipo local recibe el bonus VENTAJA_LOCAL sobre su tecnica/mental.
    """
    pos_l = local.promedio_tecnica_mental() * VENTAJA_LOCAL
    pos_v = visitante.promedio_tecnica_mental()
    total = pos_l + pos_v or 1.0
    prob_l = PROB_ATAQUE * (pos_l / total) * 2
    prob_v = PROB_ATAQUE * (pos_v / total) * 2
    return prob_l, prob_v


# ── Narrativa (texto plano, sin colorama) ─────────────────────────────────────

_ATAQUE: list[str] = [
    "{j} gambetea dos rivales y dispara...",
    "{j} recibe de espaldas, gira y remata...",
    "{j} queda mano a mano ante el portero...",
    "{j} cobra el tiro libre con rosca...",
    "{j} remata de volea desde el borde del area...",
    "{j} conecta un cabezazo al primer palo...",
    "{j} corre solo tras un pase filtrado...",
    "{j} recoge el rebote y define rapido...",
    "{j} entra en el area con descaro...",
]
_GOL: list[str] = [
    "GOOOOOL! {j} no perdona para {eq}!",
    "GOOOOOL! {j} define con clase — {eq} enloquece!",
    "GOOOL! La pelota toca el palo... y entra! {j}!",
    "GOOOL! {j} engana al portero — pura magia!",
    "GOOOOL! {eq} se va al frente con {j}!",
    "GOOOOL! {j} la manda al rincon, imposible para el portero!",
]
_FALLO: list[str] = [
    "Tiro de {j} por encima del travesano!",
    "{j} remata al cuerpo del portero. Que lastima.",
    "Ocasion perdida de {j} — el balon se va a las gradas.",
    "El portero salva con el pie el remate de {j}.",
    "{j} falla increiblemente solo ante el arco.",
    "El palo le dice NO a {j}!",
]
_DEFENSA: list[str] = [
    "{d} llega con todo y despeja el peligro.",
    "Gran intervencion de {d}, limpia y sin falta.",
    "{d} anticipa bien y corta la jugada.",
    "Tapada monumental del portero {d}!",
    "{d} saca la pelota en la linea — increible!",
]
_SILENCIO: list[str] = [
    "El partido se acomoda...",
    "Fase de juego sin peligro.",
    "Los equipos se estudian en el mediocampo.",
    "Pelota jugada sin profundidad.",
    "Se enfrian los animos en la cancha.",
]


def _emitir_narrativa(
    minuto:          int,
    atacante:        Jugador,
    defensor:        Jugador,
    resultado:       str,
    equipo_atk:      Equipo,
    goles_l:         int,
    goles_v:         int,
    nombre_local:    str,
    nombre_visitante: str,
) -> None:
    pfx = f"  Min {minuto:2d}"
    nb  = random.choice(_ATAQUE).format(j=atacante.nombre_completo)
    if resultado == "gol":
        gol_txt = random.choice(_GOL).format(
            j=atacante.nombre_completo, eq=equipo_atk.nombre
        )
        print(f"{pfx} | {nb}")
        print(f"         {gol_txt}")
        print(f"         [{nombre_local} {goles_l} - {goles_v} {nombre_visitante}]")
    elif resultado == "tiro":
        print(f"{pfx} | {nb}")
        print(f"         " + random.choice(_FALLO).format(j=atacante.nombre_completo))
    else:
        print(f"{pfx} | " + random.choice(_DEFENSA).format(d=defensor.nombre_completo))


def procesar_minuto(
    minuto:    int,
    local:     Equipo,
    visitante: Equipo,
    jug_l:     list,
    jug_v:     list,
    goles_l:   int,
    goles_v:   int,
    narrativa: bool,
    atk_l:     float = 1.0,
    def_l:     float = 1.0,
    atk_v:     float = 1.0,
    def_v:     float = 1.0,
    eventos_acumulados: Optional[list] = None,
) -> tuple[int, int]:
    """
    Simula un minuto de partido.
    Ambos equipos pueden generar una oportunidad en el mismo minuto.
    Retorna (goles_local, goles_visitante) actualizados.
    """
    prob_l, prob_v = _probs_ataque(local, visitante)
    silencio = True

    for es_local, eq_a, eq_d, prob, ma, md, ja, jd in (
        (True,  local,    visitante, prob_l, atk_l, def_v, jug_l, jug_v),
        (False, visitante, local,   prob_v, atk_v, def_l, jug_v, jug_l),
    ):
        if random.random() > prob:
            continue
        silencio  = False
        atacante  = random.choice(ja)
        defensor  = random.choice(jd)
        resultado = resolver_choque(
            atacante.poder_ataque_efectivo(ma),
            defensor.poder_defensa_efectivo(md),
            eq_a.estilo_dt,
            eq_d.estilo_dt,
        )
        if resultado == "gol":
            if es_local: goles_l += 1
            else:        goles_v += 1

        # Generar detalles del evento para match_screen.py
        try:
            detalle_evento = ""
            nb = random.choice(_ATAQUE).format(j=atacante.nombre_completo)
            if resultado == "gol":
                detalle_evento = random.choice(_GOL).format(j=atacante.nombre_completo, eq=eq_a.nombre)
            elif resultado == "tiro":
                detalle_evento = f"{nb}. " + random.choice(_FALLO).format(j=atacante.nombre_completo)
            else:
                detalle_evento = f"{nb}. " + random.choice(_DEFENSA).format(d=defensor.nombre_completo)

            if eventos_acumulados is not None:
                eventos_acumulados.append({
                    "minuto": minuto,
                    "tipo": resultado,
                    "equipo_id": eq_a.id,
                    "detalle": detalle_evento
                })
        except Exception as e_ev:
            # Error recuperable al generar narrativa del evento
            pass

        if narrativa:
            _emitir_narrativa(
                minuto, atacante, defensor, resultado, eq_a,
                goles_l, goles_v, local.nombre, visitante.nombre,
            )

    if narrativa and silencio and minuto % 10 == 0:
        print(f"  Min {minuto:2d} | {random.choice(_SILENCIO)}")

    return goles_l, goles_v


def simular_partido(
    local:       Equipo,
    visitante:   Equipo,
    narrativa:   bool = False,
    decision_mt: Optional[dict] = None,
    con_eventos_caoticos: bool = False,
    *args,
    **kwargs
) -> Resultado:
    """
    Simula 90 minutos completos entre dos equipos.

    decision_mt puede contener claves 'atk_l', 'def_l', 'atk_v', 'def_v'
    como multiplicadores de la 2a mitad (decision de medio tiempo del jugador).
    """
    gl, gv = 0, 0
    jl = local.once_disponible
    jv = visitante.once_disponible
    mt = decision_mt or {}
    eventos_partido = []

    # Agregar evento caótico simulado si se solicita
    if con_eventos_caoticos:
        try:
            if random.random() < 0.3:
                min_caotico = random.randint(10, 85)
                detalles_graciosos = [
                    "¡El DT empieza a gritarle al árbitro con un megáfono! Recibe tarjeta amarilla.",
                    "¡Una invasión de palomas interrumpe momentáneamente el juego!",
                    "¡El portero se tropieza con su propia agujeta pero la defensa despeja rápido!",
                    "¡La afición local hace la ola con entusiasmo, motivando al equipo!"
                ]
                eventos_partido.append({
                    "minuto": min_caotico,
                    "tipo": "caotico",
                    "equipo_id": local.id if random.random() < 0.5 else visitante.id,
                    "detalle": random.choice(detalles_graciosos)
                })
        except Exception as e_caos:
            # Resiliencia: si falla la generación de evento caótico, continuamos
            pass

    for mitad, minutos in ((1, range(1, 46)), (2, range(46, 91))):
        al = mt.get("atk_l", 1.0) if mitad == 2 else 1.0
        dl = mt.get("def_l", 1.0) if mitad == 2 else 1.0
        av = mt.get("atk_v", 1.0) if mitad == 2 else 1.0
        dv = mt.get("def_v", 1.0) if mitad == 2 else 1.0
        for m in minutos:
            gl, gv = procesar_minuto(
                m, local, visitante, jl, jv, gl, gv, narrativa, al, dl, av, dv,
                eventos_acumulados=eventos_partido
            )

    return Resultado(local.nombre, visitante.nombre, gl, gv, eventos=eventos_partido)


def simular_penales(
    moral_local:     float,
    moral_visitante: float,
    base_prob:       float = 0.50,
) -> bool:
    """
    Desempata por tandas de penales.
    Retorna True si gana el equipo con moral_local.
    La diferencia de moral ajusta la prob base en hasta ±7.5pp.
    """
    ajuste = (moral_local - moral_visitante) * 0.003
    prob   = min(max(base_prob + ajuste, 0.25), 0.75)
    return random.random() < prob


# ── Tabla de posiciones (Liga) ────────────────────────────────────────────────

def inicializar_tabla(equipos: list) -> dict[str, Standing]:
    """Crea una tabla vacía para una lista de Equipo."""
    return {e.nombre: Standing(equipo=e.nombre) for e in equipos}


def actualizar_tabla(tabla: dict[str, Standing], res: Resultado) -> None:
    """Aplica el resultado de un partido a la tabla de liga."""
    l = tabla[res.equipo_local]
    v = tabla[res.equipo_visitante]
    l.pj += 1; v.pj += 1
    l.gf += res.goles_local;      l.gc += res.goles_visitante
    v.gf += res.goles_visitante;  v.gc += res.goles_local
    if res.goles_local > res.goles_visitante:
        l.g += 1; l.pts += 3; v.p += 1
    elif res.goles_visitante > res.goles_local:
        v.g += 1; v.pts += 3; l.p += 1
    else:
        l.e += 1; v.e += 1; l.pts += 1; v.pts += 1


def tabla_ordenada(tabla: dict[str, Standing]) -> list[Standing]:
    """Ordena standings: pts → diferencia de goles → goles a favor."""
    return sorted(tabla.values(), key=lambda s: (s.pts, s.dg, s.gf), reverse=True)
