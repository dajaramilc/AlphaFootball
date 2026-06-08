# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Prototipo v0.3
Liga BetPlay Colombia + Copa Libertadores | Python 3.10+ | Solo librerias estandar
"""

import random
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ── UTF-8 forzado en Windows ──────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _soporte_emoji() -> bool:
    try:
        "⚽".encode(sys.stdout.encoding or "utf-8")
        return True
    except (UnicodeEncodeError, LookupError):
        return False

EMOJI    = _soporte_emoji()
E_BALON  = "⚽" if EMOJI else "[ ]"
E_ARCO   = "🥅" if EMOJI else "[o]"
E_TROFEO = "🏆" if EMOJI else "[*]"
E_AMARI  = "🟨" if EMOJI else "[A]"
E_LESION = "🚑" if EMOJI else "[+]"
E_DINERO = "💸" if EMOJI else "[$]"
E_FOTO   = "📸" if EMOJI else "[!]"
E_DADO   = "🎲" if EMOJI else "[?]"
E_PUNO   = "🥊" if EMOJI else "[x]"
E_APUNTE = "📋" if EMOJI else "[-]"
E_COPA   = "🌎" if EMOJI else "[C]"
E_STARS  = "⭐" if EMOJI else "*"

# ── COLORAMA OPCIONAL ─────────────────────────
try:
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
    COLOR = True
except ImportError:
    COLOR = False
    class Fore:
        GREEN = YELLOW = RED = CYAN = WHITE = MAGENTA = BLUE = ""
    class Style:
        BRIGHT = RESET_ALL = DIM = ""

def c(texto: str, color: str) -> str:
    if COLOR:
        return color + texto + Style.RESET_ALL
    return texto

# ═══════════════════════════════════════════════
#  CONSTANTES
# ═══════════════════════════════════════════════
ESTILOS_DT = ["haramball", "cruyffismo", "flickismo"]
ESTILO_VENTAJA = {"cruyffismo": "flickismo", "flickismo": "haramball", "haramball": "cruyffismo"}
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

PROB_ATAQUE = 0.13
UMBRAL_GOL  = 38
UMBRAL_TIRO = 15
CUPOS_LIBERTADORES = 2

# Pool aleatorio para fase de grupos Libertadores (elegimos 2 de 4)
POOL_GRUPOS_LIBERTADORES = [
    ("Nacional",       "Montevideo",    2.8),
    ("Boca Juniors",   "Buenos Aires",  4.2),
    ("Palmeiras",      "Sao Paulo",     4.2),
    ("Ind. del Valle", "Sangolqui",     2.5),
]
# Los otros 2 que no quedaron en grupos van a octavos y cuartos
SEMIFINALISTAS_FIJOS = ["River Plate", "Flamengo"]

# Niveles internacionales para rango_attr_int
NIVELES_INT = {
    "Nacional":       2.8,
    "Boca Juniors":   4.2,
    "Palmeiras":      4.2,
    "Ind. del Valle": 2.5,
    "River Plate":    5.0,
    "Flamengo":       5.0,
}

# Pool de nombres para jugadores generados (sustitutos / equipos int)
NOMBRES_GEN = [
    "Carlos", "Luis", "Juan", "Diego", "Miguel", "Andres", "Daniel",
    "Jorge", "Sergio", "Roberto", "Rodrigo", "Sebastian", "Fabian",
    "Omar", "Nelson", "Wilson", "Harold", "Gustavo", "Camilo", "Victor",
]
APELLIDOS_GEN = [
    "Garcia", "Lopez", "Martinez", "Rodriguez", "Hernandez", "Castro",
    "Vargas", "Romero", "Diaz", "Moreno", "Gomez", "Ramos", "Reyes",
    "Torres", "Ramirez", "Cruz", "Flores", "Perez", "Salinas", "Vega",
]

# ── Plantillas reales Liga BetPlay ────────────────────────────────────
# (nombre, apellido, posicion)
PLANTILLAS_REALES: dict[str, list[tuple]] = {
    "Atletico Nacional": [
        ("Kevin",      "Mier",        "POR"),
        ("Cristian",   "Castro",      "DEF"),
        ("Emmanuel",   "Olivera",     "DEF"),
        ("Alvaro",     "Angulo",      "DEF"),
        ("Pablo",      "Rojas",       "DEF"),
        ("Sebastian",  "Gomez",       "MED"),
        ("Marino",     "Hinestroza",  "MED"),
        ("Jarlan",     "Barrera",     "MED"),
        ("Jefferson",  "Duque",       "DEL"),
        ("Adrian",     "Ramos",       "DEL"),
        ("Daniel",     "Mantilla",    "DEL"),
    ],
    "Millonarios FC": [
        ("Alvaro",     "Montero",     "POR"),
        ("Andres",     "Llinas",      "DEF"),
        ("Juan Pablo", "Vargas",      "DEF"),
        ("Larry",      "Vasquez",     "DEF"),
        ("Stiven",     "Vega",        "DEF"),
        ("David",      "Silva",       "MED"),
        ("Daniel",     "Ruiz",        "MED"),
        ("Omar",       "Bertel",      "MED"),
        ("Radamel",    "Falcao",      "DEL"),
        ("Fernando",   "Uribe",       "DEL"),
        ("Leonardo",   "Castro",      "DEL"),
    ],
    "America de Cali": [
        ("Joel",       "Graterol",    "POR"),
        ("Marcelino",  "Carreazo",    "DEF"),
        ("Jeisson",    "Quinones",    "DEF"),
        ("Kevin",      "Andrade",     "DEF"),
        ("Yesus",      "Cabrera",     "DEF"),
        ("Rodrigo",    "Urena",       "MED"),
        ("Carlos",     "Sierra",      "MED"),
        ("Michael",    "Rangel",      "MED"),
        ("Deinner",    "Quinones",    "DEL"),
        ("Pablo",      "Bueno",       "DEL"),
        ("Jorge",      "Marsiglia",   "DEL"),
    ],
    "Junior FC": [
        ("Sebastian",  "Viera",       "POR"),
        ("Fabio",      "Delgado",     "DEF"),
        ("German",     "Mera",        "DEF"),
        ("Darwin",     "Andrade",     "DEF"),
        ("Jose",       "Enamorado",   "DEF"),
        ("Didier",     "Moreno",      "MED"),
        ("Fredy",      "Hinestroza",  "MED"),
        ("Edwuin",     "Cetre",       "MED"),
        ("Carlos",     "Bacca",       "DEL"),
        ("Teofilo",    "Gutierrez",   "DEL"),
        ("Miguel",     "Borja",       "DEL"),
    ],
    "Deportivo Cali": [
        ("Nicolas",    "Vikonis",     "POR"),
        ("Harold",     "Mosquera",    "DEF"),
        ("Juan Pablo", "Segovia",     "DEF"),
        ("Hernando",   "Cope",        "DEF"),
        ("Oscar",      "Lozano",      "DEF"),
        ("Jhon",       "Vasquez",     "MED"),
        ("Andres",     "Colorado",    "MED"),
        ("Kevin",      "Velasco",     "MED"),
        ("Marco",      "Perez",       "DEL"),
        ("Jhon",       "Cordoba",     "DEL"),
        ("Carlos",     "Robles",      "DEL"),
    ],
    "Independiente Santa Fe": [
        ("Leandro",    "Castellanos", "POR"),
        ("Yulian",     "Gomez",       "DEF"),
        ("Jersson",    "Gonzalez",    "DEF"),
        ("Nelson",     "Deossa",      "DEF"),
        ("Andres",     "Cadavid",     "DEF"),
        ("Baldomero",  "Perlaza",     "MED"),
        ("Jhojan",     "Valencia",    "MED"),
        ("Juan",       "Penaloza",    "MED"),
        ("Hugo",       "Rodallega",   "DEL"),
        ("Elvis",      "Perlaza",     "DEL"),
        ("Diego",      "Valdovinos",  "DEL"),
    ],
    "Deportes Tolima": [
        ("Alvaro",     "Villar",      "POR"),
        ("Juan David", "Rios",        "DEF"),
        ("Sergio",     "Mosquera",    "DEF"),
        ("Cristian",   "Bonilla",     "DEF"),
        ("Juan",       "Penaloza",    "DEF"),
        ("Anderson",   "Plata",       "MED"),
        ("Steven",     "Lucumi",      "MED"),
        ("Omar",       "Albornoz",    "MED"),
        ("Michael",    "Moreno",      "DEL"),
        ("Jaminton",   "Campaz",      "DEL"),
        ("Luciano",    "Ospina",      "DEL"),
    ],
    "Once Caldas": [
        ("Diego",      "Novoa",       "POR"),
        ("Cesar",      "Quintero",    "DEF"),
        ("Jhon",       "Garcia",      "DEF"),
        ("Dairon",     "Mosquera",    "DEF"),
        ("Julian",     "Quinones",    "DEF"),
        ("Gustavo",    "Torres",      "MED"),
        ("Rolan",      "Piedrahita",  "MED"),
        ("Jorge",      "Obregon",     "MED"),
        ("Carlos",     "Peralta",     "DEL"),
        ("Brayan",     "Rovira",      "DEL"),
        ("Jose",       "Cuadrado",    "DEL"),
    ],
}

EQUIPOS_DATA = [
    ("Atletico Nacional",       "Medellin",     4.0),
    ("Millonarios FC",          "Bogota",       4.0),
    ("America de Cali",         "Cali",         3.5),
    ("Junior FC",               "Barranquilla", 3.5),
    ("Deportivo Cali",          "Cali",         3.0),
    ("Independiente Santa Fe",  "Bogota",       3.0),
    ("Deportes Tolima",         "Ibague",       3.0),
    ("Once Caldas",             "Manizales",    2.5),
]

POSICIONES_11 = ["POR","DEF","DEF","DEF","DEF","MED","MED","MED","DEL","DEL","DEL"]
POS_ORDEN = {"POR": 0, "DEF": 1, "MED": 2, "DEL": 3}

ASCII_LOGO = r"""
  +--------------------------------------------------+
  |    _  _     ___  _  _    _                       |
  |   /_\| |   | _ \| || |  /_\                      |
  |  / _ \ |__ |  _/| __ | / _ \                     |
  | /_/ \_\____||_|  |_||_|/_/ \_\                   |
  |   ___  ___  ___ ___  ___   _   _    _             |
  |  | __||   \| _ )/_\ | | | / \ | |  | |            |
  |  | _| | |) | _ \ _ \| |_|/ _ \| |__| |__         |
  |  |_|  |___/|___/_/ \_\___/_/ \_\____|____|        |
  +--------------------------------------------------+
"""

NARRATIVAS_ATAQUE = [
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
NARRATIVAS_GOL = [
    "GOOOOOL! {j} no perdona para {eq}!",
    "GOOOOOL! {j} define con clase — {eq} enloquece!",
    "GOOOL! La pelota toca el palo... y entra! {j}!",
    "GOOOL! {j} engana al portero — pura magia!",
    "GOOOOL! {eq} se va al frente con {j}!",
    "GOOOOL! {j} la manda al rincon, imposible para el portero!",
]
NARRATIVAS_FALLO = [
    "Tiro de {j} por encima del travesano!",
    "{j} remata al cuerpo del portero. Que lastima.",
    "Ocasion perdida de {j} — el balon se va a las gradas.",
    "El portero salva con el pie el remate de {j}.",
    "{j} falla increiblemente solo ante el arco.",
    "El palo le dice NO a {j}!",
]
NARRATIVAS_DEFENSA = [
    "{d} llega con todo y despeja el peligro.",
    "Gran intervencion de {d}, limpia y sin falta.",
    f"{{d}} mete la pierna fuerte... {E_AMARI} amarilla para el!",
    "{d} anticipa bien y corta la jugada.",
    "Tapada monumental del portero {d}!",
    "{d} saca la pelota en la linea — increible!",
]
NARRATIVAS_TRANQUILO = [
    "El partido se acomoda...",
    "Fase de juego sin peligro.",
    "Los equipos se estudian en el mediocampo.",
    "Pelota jugada sin profundidad.",
    "Se enfrian los animos en la cancha.",
]

# ═══════════════════════════════════════════════
#  DATACLASSES
# ═══════════════════════════════════════════════
@dataclass
class Jugador:
    nombre: str
    apellido: str
    posicion: str
    ataque: int
    defensa: int
    fisico: int
    tecnica: int
    mental: int
    moral: int = 70
    rasgo: Optional[str] = None
    lesion_partidos: int = 0

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}"

    @property
    def overall(self) -> int:
        return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5

    def poder_ataque_efectivo(self, mult: float = 1.0) -> float:
        base = (self.ataque + self.tecnica * 0.5 + self.fisico * 0.3) * (self.moral / 70)
        if self.rasgo == "regateador":    base *= 1.15
        if self.rasgo == "pulmon_de_hierro": base *= 1.05
        return base * mult

    def poder_defensa_efectivo(self, mult: float = 1.0) -> float:
        base = (self.defensa + self.fisico * 0.5 + self.mental * 0.3) * (self.moral / 70)
        if self.rasgo == "rustico": base *= 1.20
        if self.rasgo == "lider":   base *= 1.08
        return base * mult


@dataclass
class Equipo:
    nombre: str
    ciudad: str
    estrellas: float
    estilo_dt: str
    balance: int
    jugadores: list = field(default_factory=list)

    @property
    def once_disponible(self):
        disp = [j for j in self.jugadores if j.lesion_partidos == 0]
        return disp if disp else self.jugadores

    def promedio_ataque(self, mult: float = 1.0) -> float:
        j = self.once_disponible
        return sum(x.poder_ataque_efectivo(mult) for x in j) / len(j)

    def promedio_defensa(self, mult: float = 1.0) -> float:
        j = self.once_disponible
        return sum(x.poder_defensa_efectivo(mult) for x in j) / len(j)

    def promedio_tecnica_mental(self) -> float:
        j = self.once_disponible
        return sum((x.tecnica + x.mental) / 2 for x in j) / len(j)

    def jugador_estrella(self) -> "Jugador":
        return max(self.jugadores, key=lambda j: j.overall)

    def ovr_promedio(self) -> int:
        return sum(j.overall for j in self.jugadores) // len(self.jugadores)

    def tick_lesiones(self):
        for j in self.jugadores:
            if j.lesion_partidos > 0:
                j.lesion_partidos -= 1


@dataclass
class Resultado:
    equipo_local: str
    equipo_visitante: str
    goles_local: int
    goles_visitante: int

    def ganador(self) -> Optional[str]:
        if self.goles_local > self.goles_visitante:  return self.equipo_local
        if self.goles_visitante > self.goles_local:  return self.equipo_visitante
        return None


@dataclass
class Standing:
    equipo: str
    pj: int = 0; g: int = 0; e: int = 0; p: int = 0
    gf: int = 0; gc: int = 0; pts: int = 0

    @property
    def dg(self) -> int: return self.gf - self.gc


# ═══════════════════════════════════════════════
#  GENERACION
# ═══════════════════════════════════════════════
_nombres_usados: set = set()

def _nombre_gen() -> tuple[str, str]:
    """Nombre aleatorio del pool generico (para suplentes / equipos int)."""
    for _ in range(200):
        n, a = random.choice(NOMBRES_GEN), random.choice(APELLIDOS_GEN)
        if f"{n}{a}" not in _nombres_usados:
            _nombres_usados.add(f"{n}{a}")
            return n, a
    return random.choice(NOMBRES_GEN), random.choice(APELLIDOS_GEN)

def r(lo: int, hi: int, bonus: int = 0) -> int:
    """randint seguro — evita rangos invalidos."""
    a = min(lo + bonus, hi - 1)
    return random.randint(a, hi)

def _attrs(lo: int, hi: int, posicion: str) -> tuple[int,int,int,int,int]:
    mid = (lo + hi) // 2
    if posicion == "POR":
        return r(lo,mid-5), r(mid,hi,5),  r(mid-5,hi), r(lo,hi),    r(mid,hi)
    if posicion == "DEF":
        return r(lo,mid),   r(mid,hi,5),  r(mid,hi),   r(lo,hi),    r(mid-5,hi)
    if posicion == "MED":
        return r(lo+5,hi),  r(lo+5,hi),   r(lo,hi),    r(mid,hi,5), r(mid-5,hi)
    # DEL
    return     r(mid+3,hi), r(lo,mid-5),  r(lo+5,hi),  r(mid,hi),   r(lo,hi)

def rango_co(estrellas: float) -> tuple[int, int]:
    """Colombiano: tope realista ~73-75 OVR para los mejores."""
    base = int(40 + estrellas * 5)
    return base, min(base + 20, 76)

def rango_int(nivel: float) -> tuple[int, int]:
    """Internacional: base alta, ~80-92 OVR."""
    base = int(60 + nivel * 6)
    return base, min(base + 20, 95)

def generar_jugador_pos(posicion: str, lo: int, hi: int) -> Jugador:
    n, a = _nombre_gen()
    atk, def_, fis, tec, men = _attrs(lo, hi, posicion)
    rasgo = random.choice(RASGOS) if random.random() < 0.28 else None
    return Jugador(nombre=n, apellido=a, posicion=posicion,
                   ataque=atk, defensa=def_, fisico=fis, tecnica=tec, mental=men, rasgo=rasgo)

def generar_equipo_real(nombre: str, ciudad: str, estrellas: float) -> Equipo:
    """Genera equipo con plantel de nombres reales si disponible."""
    estilo  = random.choice(ESTILOS_DT)
    balance = int(estrellas * 800_000)
    lo, hi  = rango_co(estrellas)
    plantilla = PLANTILLAS_REALES.get(nombre, [])
    jugadores = []
    for (pnombre, papellido, pos) in plantilla:
        atk, def_, fis, tec, men = _attrs(lo, hi, pos)
        rasgo = random.choice(RASGOS) if random.random() < 0.28 else None
        jugadores.append(Jugador(nombre=pnombre, apellido=papellido, posicion=pos,
                                  ataque=atk, defensa=def_, fisico=fis,
                                  tecnica=tec, mental=men, rasgo=rasgo))
    # Rellenar si faltan posiciones
    posiciones_actuales = [j.posicion for j in jugadores]
    for pos in POSICIONES_11:
        if pos not in posiciones_actuales:
            jugadores.append(generar_jugador_pos(pos, lo, hi))
            posiciones_actuales.append(pos)
    return Equipo(nombre=nombre, ciudad=ciudad, estrellas=estrellas,
                  estilo_dt=estilo, balance=balance, jugadores=jugadores[:11])

def generar_rival_int(nombre: str, ciudad: str, nivel: float) -> Equipo:
    """Equipo internacional con stats superiores."""
    lo, hi = rango_int(nivel)
    jugadores = [generar_jugador_pos(pos, lo, hi) for pos in POSICIONES_11]
    return Equipo(nombre=nombre, ciudad=ciudad, estrellas=nivel,
                  estilo_dt=random.choice(ESTILOS_DT), balance=0, jugadores=jugadores)

def generar_liga() -> list[Equipo]:
    return [generar_equipo_real(n, ci, e) for n, ci, e in EQUIPOS_DATA]

def calcular_precio(j: Jugador) -> int:
    """Precio de mercado basado en OVR."""
    return max(50_000, (j.overall - 45) ** 2 * 3_500)


# ═══════════════════════════════════════════════
#  MOTOR DE SIMULACION
# ═══════════════════════════════════════════════
def bono_estilo(ea: str, ed: str) -> float:
    if ESTILO_VENTAJA.get(ea) == ed:   return 1.15
    if ESTILO_VENTAJA.get(ed) == ea:   return 0.87
    return 1.0

def resolver_choque(atk: float, def_: float, ea: str, ed: str) -> str:
    poder = atk * bono_estilo(ea, ed)
    diff  = poder - def_ + random.gauss(0, 12)
    if diff > UMBRAL_GOL:  return "gol"
    if diff > UMBRAL_TIRO: return "tiro"
    return "defensa"

def _procesar_minuto(
    minuto: int,
    local: Equipo, visitante: Equipo,
    jug_l: list, jug_v: list,
    goles_l: int, goles_v: int,
    narrativa: bool,
    atk_l: float, def_l: float, atk_v: float, def_v: float,
) -> tuple[int, int]:
    pos_l   = local.promedio_tecnica_mental()
    pos_v   = visitante.promedio_tecnica_mental()
    total   = pos_l + pos_v or 1
    prob_l  = PROB_ATAQUE * (pos_l / total) * 2
    prob_v  = PROB_ATAQUE * (pos_v / total) * 2
    silencio = True

    for es_local, eq_a, eq_d, prob, ma, md, ja, jd in [
        (True,  local,    visitante, prob_l, atk_l, def_v, jug_l, jug_v),
        (False, visitante, local,   prob_v, atk_v, def_l, jug_v, jug_l),
    ]:
        if random.random() > prob:
            continue
        silencio   = False
        atacante   = random.choice(ja)
        defensor   = random.choice(jd)
        resultado  = resolver_choque(
            atacante.poder_ataque_efectivo(ma),
            defensor.poder_defensa_efectivo(md),
            eq_a.estilo_dt, eq_d.estilo_dt,
        )
        if resultado == "gol":
            if es_local: goles_l += 1
            else:        goles_v += 1

        if narrativa:
            pfx = c(f"  Min {minuto:2d}", Fore.WHITE)
            nb  = random.choice(NARRATIVAS_ATAQUE).format(j=atacante.nombre_completo)
            if resultado == "gol":
                txt = random.choice(NARRATIVAS_GOL).format(j=atacante.nombre_completo, eq=eq_a.nombre)
                print(f"{pfx} | {nb}")
                print(c(f"         {E_BALON}  {txt}", Fore.GREEN + Style.BRIGHT))
                print(c(f"         [{local.nombre} {goles_l} - {goles_v} {visitante.nombre}]", Fore.CYAN))
            elif resultado == "tiro":
                print(f"{pfx} | {nb}")
                print(f"         {E_ARCO}  " + random.choice(NARRATIVAS_FALLO).format(j=atacante.nombre_completo))
            else:
                print(f"{pfx} | " + random.choice(NARRATIVAS_DEFENSA).format(d=defensor.nombre_completo))

    if narrativa and silencio and minuto % 10 == 0:
        print(c(f"  Min {minuto:2d} | {random.choice(NARRATIVAS_TRANQUILO)}", Style.DIM))

    return goles_l, goles_v


def simular_partido(
    local: Equipo, visitante: Equipo,
    narrativa: bool = False, velocidad: float = 1.0,
    decision_mt: Optional[dict] = None,
) -> Resultado:
    """Simula 90 min. decision_mt puede contener multiplicadores de 2da mitad."""
    gl, gv = 0, 0
    jl = local.once_disponible
    jv = visitante.once_disponible
    mt = decision_mt or {}

    for mitad, rango_min in [(1, range(1,46)), (2, range(46,91))]:
        al = mt.get("atk_l",1.0) if mitad==2 else 1.0
        dl = mt.get("def_l",1.0) if mitad==2 else 1.0
        av = mt.get("atk_v",1.0) if mitad==2 else 1.0
        dv = mt.get("def_v",1.0) if mitad==2 else 1.0
        for m in rango_min:
            gl, gv = _procesar_minuto(m, local, visitante, jl, jv, gl, gv, narrativa, al, dl, av, dv)
            if narrativa:
                time.sleep(velocidad)

    return Resultado(local.nombre, visitante.nombre, gl, gv)


# ═══════════════════════════════════════════════
#  DECISION MEDIO TIEMPO
# ═══════════════════════════════════════════════
def decision_medio_tiempo(mi_equipo: Equipo, rival: Equipo,
                           goles_mios: int, goles_rival: int,
                           soy_local: bool) -> dict:
    limpiar()
    print(c("\n  ══════════ MEDIO TIEMPO ══════════", Fore.CYAN))
    if soy_local:
        print(c(f"\n  {mi_equipo.nombre}  {goles_mios}  -  {goles_rival}  {rival.nombre}", Fore.YELLOW + Style.BRIGHT))
    else:
        print(c(f"\n  {rival.nombre}  {goles_rival}  -  {goles_mios}  {mi_equipo.nombre}", Fore.YELLOW + Style.BRIGHT))

    print(c(f"\n  Rival juega: {rival.estilo_dt}  |  Tu estilo: {mi_equipo.estilo_dt}", Fore.WHITE))
    separador("-", 50)
    print(c("\n  Instruccion tactica para la 2da mitad:\n", Fore.CYAN))
    print("  [1] Cerrar el partido      (DEF +20%, ATK -10%)")
    print("  [2] Buscar el gol          (ATK +25%, DEF -15%)")
    print("  [3] Cambiar estilo tactico (giro de piedra-papel-tijera)")
    print("  [4] Mantener el esquema")
    separador("-", 50)

    while True:
        opc = input(c("\n  Tu decision [1-4]: ", Fore.YELLOW)).strip()
        if opc in "1234": break
        print(c("  Opcion invalida.", Fore.RED))

    if opc == "1":
        print(c("\n  Equipo cerrado. A defender el resultado.", Fore.CYAN))
        return {"atk_l":0.90,"def_l":1.20,"atk_v":1.0,"def_v":1.0} if soy_local \
          else {"atk_v":0.90,"def_v":1.20,"atk_l":1.0,"def_l":1.0}
    if opc == "2":
        print(c("\n  Todo al ataque. Riesgo alto, recompensa alta.", Fore.GREEN))
        return {"atk_l":1.25,"def_l":0.85,"atk_v":1.0,"def_v":1.0} if soy_local \
          else {"atk_v":1.25,"def_v":0.85,"atk_l":1.0,"def_l":1.0}
    if opc == "3":
        estilos_otros = [e for e in ESTILOS_DT if e != mi_equipo.estilo_dt]
        mi_equipo.estilo_dt = random.choice(estilos_otros)
        print(c(f"\n  Cambio de estilo: ahora juegas {mi_equipo.estilo_dt}.", Fore.YELLOW))
    else:
        print(c("\n  Mismo esquema. Los jugadores saben que hacer.", Fore.WHITE))
    return {"atk_l":1.0,"def_l":1.0,"atk_v":1.0,"def_v":1.0}


# ═══════════════════════════════════════════════
#  TABLA DE POSICIONES
# ═══════════════════════════════════════════════
def inicializar_tabla(equipos: list[Equipo]) -> dict[str, Standing]:
    return {e.nombre: Standing(equipo=e.nombre) for e in equipos}

def actualizar_tabla(tabla: dict[str, Standing], res: Resultado):
    l, v = tabla[res.equipo_local], tabla[res.equipo_visitante]
    l.pj += 1; v.pj += 1
    l.gf += res.goles_local;    l.gc += res.goles_visitante
    v.gf += res.goles_visitante; v.gc += res.goles_local
    if   res.goles_local > res.goles_visitante: l.g+=1; l.pts+=3; v.p+=1
    elif res.goles_visitante > res.goles_local: v.g+=1; v.pts+=3; l.p+=1
    else: l.e+=1; v.e+=1; l.pts+=1; v.pts+=1

def tabla_ordenada(tabla: dict[str, Standing]) -> list[Standing]:
    return sorted(tabla.values(), key=lambda s: (s.pts, s.dg, s.gf), reverse=True)

def mostrar_tabla(tabla: dict[str, Standing], equipo_usuario: str):
    ordenada = tabla_ordenada(tabla)
    print(c(f"\n  {E_TROFEO} TABLA — Liga BetPlay Colombia", Fore.CYAN))
    separador("-", 70)
    print(f"  {'#':>2}  {'Equipo':<30} {'PJ':>2} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'DG':>4} {'PTS':>4}  Copa")
    separador("-", 70)
    for i, s in enumerate(ordenada, 1):
        copa = c("LIBERTADORES", Fore.GREEN) if i <= CUPOS_LIBERTADORES else ""
        base = f"  {i:>2}  {s.equipo:<30} {s.pj:>2} {s.g:>2} {s.e:>2} {s.p:>2} {s.gf:>3} {s.gc:>3} {s.dg:>4} {s.pts:>4}"
        col  = Fore.CYAN if s.equipo == equipo_usuario else ""
        print(c(base, col) + (f"  {copa}" if copa else ""))
    separador("-", 70)
    print()


# ═══════════════════════════════════════════════
#  FIXTURE
# ═══════════════════════════════════════════════
def generar_fixture(equipos: list[Equipo]) -> list[list[tuple[Equipo,Equipo]]]:
    n, lista, jornadas = len(equipos), equipos[:], []
    for _ in range(n - 1):
        jornadas.append([(lista[i], lista[n-1-i]) for i in range(n//2)])
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]
    return jornadas


# ═══════════════════════════════════════════════
#  MERCADO DE PASES
# ═══════════════════════════════════════════════
def mercado_de_pases(mi_equipo: Equipo, liga: list[Equipo]) -> None:
    """Ventana de transferencias pre-Libertadores."""
    max_fichajes = 3
    fichajes     = 0

    while fichajes < max_fichajes:
        limpiar()
        print(c(f"\n  {E_DINERO} MERCADO DE PASES — Pre Copa Libertadores", Fore.CYAN + Style.BRIGHT))
        separador()
        print(c(f"  Balance disponible: ${mi_equipo.balance:,}  |  Fichajes restantes: {max_fichajes - fichajes}", Fore.YELLOW))

        # ── Oferta entrante (una por apertura, aleatoria) ──────────────
        if fichajes == 0:
            estrella = mi_equipo.jugador_estrella()
            oferta   = int(calcular_precio(estrella) * random.uniform(1.05, 1.35))
            rival_of = random.choice([e for e in liga if e != mi_equipo])
            print(c(f"\n  {E_FOTO} OFERTA ENTRANTE de {rival_of.nombre}:", Fore.YELLOW))
            print(f"     ${oferta:,} por {estrella.nombre_completo} (OVR {estrella.overall}, {estrella.posicion})")
            print(f"  [1] Aceptar   [2] Rechazar")
            oa = input(c("  Tu decision [1/2]: ", Fore.YELLOW)).strip()
            if oa == "1":
                mi_equipo.balance += oferta
                mi_equipo.jugadores.remove(estrella)
                lo, hi = rango_co(mi_equipo.estrellas)
                suplente = generar_jugador_pos(estrella.posicion, lo, hi)
                mi_equipo.jugadores.append(suplente)
                print(c(f"  Vendido. Llega {suplente.nombre_completo} como reemplazo.", Fore.GREEN))
                input(c("  [Enter]  ", Fore.CYAN))
            else:
                print(f"  {estrella.nombre_completo} se queda. El camerino aplaude.")
                input(c("  [Enter]  ", Fore.CYAN))

        # ── Jugadores disponibles en el mercado ─────────────────────────
        limpiar()
        print(c(f"\n  {E_DINERO} JUGADORES DISPONIBLES  |  Balance: ${mi_equipo.balance:,}  |  Fichajes: {max_fichajes - fichajes}", Fore.CYAN))
        separador("-", 68)
        print(f"  {'#':<4} {'Jugador':<24} {'Pos':>4} {'OVR':>4} {'Club':<28} {'Precio':>12}")
        separador("-", 68)

        disponibles = []
        for eq in liga:
            if eq == mi_equipo:
                continue
            for j in sorted(eq.jugadores, key=lambda x: -x.overall):
                disponibles.append((j, eq))
        disponibles.sort(key=lambda x: -x[0].overall)
        top = disponibles[:15]

        for i, (j, eq) in enumerate(top, 1):
            precio = calcular_precio(j)
            puede  = c("OK", Fore.GREEN) if precio <= mi_equipo.balance else c("SIN FONDOS", Fore.RED)
            print(f"  {i:<4} {j.nombre_completo:<24} {j.posicion:>4} {j.overall:>4} {eq.nombre:<28} ${precio:>10,}  {puede}")

        separador("-", 68)
        print(f"\n  [1-{len(top)}] Fichar jugador  |  [0] Cerrar mercado")

        raw = input(c("\n  Numero: ", Fore.YELLOW)).strip()
        if raw == "0":
            break
        try:
            idx = int(raw) - 1
            if not (0 <= idx < len(top)):
                raise ValueError
        except ValueError:
            print(c("  Opcion invalida.", Fore.RED))
            time.sleep(1)
            continue

        jugador_obj, club_origen = top[idx]
        precio = calcular_precio(jugador_obj)
        if precio > mi_equipo.balance:
            print(c("  No tienes fondos suficientes.", Fore.RED))
            time.sleep(1.5)
            continue

        # Confirmar
        print(c(f"\n  Fichar a {jugador_obj.nombre_completo} (OVR {jugador_obj.overall}) por ${precio:,}? [s/N] ", Fore.YELLOW), end="")
        if input().strip().lower() == "s":
            mi_equipo.balance -= precio
            club_origen.jugadores.remove(jugador_obj)
            # Si mi equipo tiene mas de 11, retirar al de menor OVR en esa posicion
            misma_pos = [j for j in mi_equipo.jugadores if j.posicion == jugador_obj.posicion]
            if len(misma_pos) >= 2:
                peor = min(misma_pos, key=lambda j: j.overall)
                mi_equipo.jugadores.remove(peor)
                # Volver peor al club origen
                club_origen.jugadores.append(peor)
            mi_equipo.jugadores.append(jugador_obj)
            fichajes += 1
            print(c(f"\n  {E_BALON} {jugador_obj.nombre_completo} firma por {mi_equipo.nombre}!", Fore.GREEN + Style.BRIGHT))
            print(f"  Balance restante: ${mi_equipo.balance:,}")
            time.sleep(1.5)

    print(c("\n  Mercado cerrado. A prepararse para la Libertadores.", Fore.CYAN))
    time.sleep(1)


# ═══════════════════════════════════════════════
#  COPA LIBERTADORES
# ═══════════════════════════════════════════════
def _partido_copa(mi_equipo: Equipo, rival: Equipo, fase: str, narrativa: bool) -> bool:
    """
    Juega un partido eliminatorio.
    Retorna True si mi_equipo gana (o empata en final -> penales).
    """
    limpiar()
    soy_local = random.random() < 0.5  # local aleatorio
    local     = mi_equipo if soy_local else rival
    visit     = rival     if soy_local else mi_equipo

    print(c(f"\n  {E_COPA} COPA LIBERTADORES — {fase}", Fore.CYAN + Style.BRIGHT))
    print(c(f"  {local.nombre}  vs  {visit.nombre}", Fore.WHITE))
    print(c(f"  Estilos: {local.estilo_dt}  vs  {visit.estilo_dt}", Style.DIM))
    separador("-", 55)

    if narrativa:
        # Simulo con narrativa en dos mitades y decision de MT
        jl = local.once_disponible
        jv = visit.once_disponible
        print(c("\n  -- PRIMERA MITAD --\n", Fore.YELLOW))
        gl, gv = 0, 0
        for m in range(1, 46):
            gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, True, 1.0,1.0,1.0,1.0)
            time.sleep(1.0)
        goles_mios  = gl if soy_local else gv
        goles_rival = gv if soy_local else gl
        mt = decision_medio_tiempo(mi_equipo, rival, goles_mios, goles_rival, soy_local)
        limpiar()
        print(c(f"\n  {E_COPA} COPA LIBERTADORES — {fase} | 2da mitad", Fore.CYAN + Style.BRIGHT))
        print(c(f"  Marcador al descanso: {gl} - {gv}", Fore.YELLOW))
        separador("-", 55)
        print(c("\n  -- SEGUNDA MITAD --\n", Fore.YELLOW))
        for m in range(46, 91):
            gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, True,
                                      mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                      mt.get("atk_v",1.0), mt.get("def_v",1.0))
            time.sleep(1.0)
    else:
        # Rapido con MT
        jl = local.once_disponible
        jv = visit.once_disponible
        gl, gv = 0, 0
        for m in range(1, 46):
            gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, False, 1.0,1.0,1.0,1.0)
        goles_mios  = gl if soy_local else gv
        goles_rival = gv if soy_local else gl
        mt = decision_medio_tiempo(mi_equipo, rival, goles_mios, goles_rival, soy_local)
        for m in range(46, 91):
            gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, False,
                                      mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                      mt.get("atk_v",1.0), mt.get("def_v",1.0))

    separador("-", 55)
    goles_mios  = gl if soy_local else gv
    goles_rival = gv if soy_local else gl

    if goles_mios > goles_rival:
        print(c(f"\n  RESULTADO: {local.nombre} {gl} - {gv} {visit.nombre}", Fore.GREEN + Style.BRIGHT))
        print(c(f"  {mi_equipo.nombre} avanza a la siguiente fase!", Fore.GREEN))
        pausa()
        return True
    elif goles_mios < goles_rival:
        print(c(f"\n  RESULTADO: {local.nombre} {gl} - {gv} {visit.nombre}", Fore.RED + Style.BRIGHT))
        print(c(f"  {mi_equipo.nombre} queda eliminado. Hasta aqui llego el camino.", Fore.RED))
        pausa()
        return False
    else:
        # Empate → penales (50/50 con bonificacion por moral)
        print(c(f"\n  EMPATE {gl} - {gv}! Vamos a PENALES!", Fore.YELLOW + Style.BRIGHT))
        time.sleep(1.5)
        moral_mia = sum(j.moral for j in mi_equipo.jugadores) / len(mi_equipo.jugadores)
        moral_riv = sum(j.moral for j in rival.jugadores) / len(rival.jugadores)
        prob_gano = 0.50 + (moral_mia - moral_riv) * 0.003
        gano      = random.random() < min(max(prob_gano, 0.25), 0.75)
        if gano:
            print(c(f"\n  {E_BALON} {mi_equipo.nombre} gana en penales! Milagro!", Fore.GREEN + Style.BRIGHT))
            pausa()
            return True
        else:
            print(c(f"\n  {mi_equipo.nombre} cae en penales. El futbol es cruel.", Fore.RED))
            pausa()
            return False


def copa_libertadores(mi_equipo: Equipo, otro_colombiano: Equipo,
                      narrativa: bool) -> str:
    """
    Flujo completo. Retorna 'campeon', 'subcampeon' o 'eliminado_<fase>'.
    """
    limpiar()
    # Armar el pool y asignar grupos vs eliminatorias
    pool = list(POOL_GRUPOS_LIBERTADORES)
    random.shuffle(pool)
    en_grupos   = pool[:2]  # 2 rivales en grupo
    en_knockout = pool[2:]  # 2 van a octavos y cuartos

    rivales_grupos    = [generar_rival_int(n, ci, nv) for n, ci, nv in en_grupos]
    rivales_knockout  = [generar_rival_int(n, ci, nv) for n, ci, nv in en_knockout]
    semis_orden       = SEMIFINALISTAS_FIJOS[:]
    random.shuffle(semis_orden)
    rival_semis = generar_rival_int(semis_orden[0], "Sudamerica", 5.0)
    rival_final = generar_rival_int(semis_orden[1], "Sudamerica", 5.0)

    # Mostrar bracket
    print(c(f"\n  {E_COPA} COPA LIBERTADORES", Fore.CYAN + Style.BRIGHT))
    separador()
    print(c("\n  GRUPO A:", Fore.YELLOW))
    for eq in [mi_equipo, otro_colombiano] + rivales_grupos:
        pais = "Colombia" if eq in [mi_equipo, otro_colombiano] else eq.ciudad
        print(f"    • {eq.nombre:<28}  OVR prom: {eq.ovr_promedio():>2}  ({pais})")
    print(c("\n  RUTA ELIMINATORIA (si clasifica):", Fore.YELLOW))
    print(f"    Octavos: vs {rivales_knockout[0].nombre}")
    print(f"    Cuartos: vs {rivales_knockout[1].nombre}")
    print(f"    Semis:   vs {rival_semis.nombre}")
    print(f"    Final:   vs {rival_final.nombre}")
    separador()
    pausa()

    # ══ FASE DE GRUPOS ══════════════════════════
    grupo = [mi_equipo, otro_colombiano] + rivales_grupos
    tabla_g: dict[str, Standing] = {e.nombre: Standing(equipo=e.nombre) for e in grupo}

    # Partidos del grupo (todos contra todos)
    enfrentamientos = [(grupo[i], grupo[j]) for i in range(4) for j in range(i+1, 4)]

    limpiar()
    print(c(f"\n  {E_COPA} FASE DE GRUPOS", Fore.CYAN + Style.BRIGHT))
    separador()

    for local, visit in enfrentamientos:
        es_mi_partido = (local == mi_equipo or visit == mi_equipo)
        if es_mi_partido:
            soy_l = (local == mi_equipo)
            limpiar()
            print(c(f"\n  {E_COPA} GRUPO A — {local.nombre}  vs  {visit.nombre}", Fore.CYAN + Style.BRIGHT))
            separador("-", 55)
            # Primera mitad
            jl = local.once_disponible
            jv = visit.once_disponible
            gl, gv = 0, 0
            if narrativa:
                print(c("\n  -- PRIMERA MITAD --\n", Fore.YELLOW))
                for m in range(1, 46):
                    gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, True, 1.0,1.0,1.0,1.0)
                    time.sleep(1.0)
            else:
                for m in range(1, 46):
                    gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, False, 1.0,1.0,1.0,1.0)

            gm = gl if soy_l else gv
            gr = gv if soy_l else gl
            mt = decision_medio_tiempo(mi_equipo, visit if soy_l else local, gm, gr, soy_l)

            if narrativa:
                limpiar()
                print(c(f"\n  {E_COPA} GRUPO A — {local.nombre}  vs  {visit.nombre} | 2da mitad", Fore.CYAN + Style.BRIGHT))
                print(c(f"  Descanso: {gl} - {gv}", Fore.YELLOW)); separador("-",55)
                print(c("\n  -- SEGUNDA MITAD --\n", Fore.YELLOW))
                for m in range(46, 91):
                    gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, True,
                                              mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                              mt.get("atk_v",1.0), mt.get("def_v",1.0))
                    time.sleep(1.0)
            else:
                for m in range(46, 91):
                    gl, gv = _procesar_minuto(m, local, visit, jl, jv, gl, gv, False,
                                              mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                              mt.get("atk_v",1.0), mt.get("def_v",1.0))

            separador("-", 55)
            color_r = Fore.GREEN if (gl>gv and soy_l) or (gv>gl and not soy_l) else \
                      Fore.RED   if (gl<gv and soy_l) or (gv<gl and not soy_l) else Fore.YELLOW
            print(c(f"\n  RESULTADO: {local.nombre} {gl} - {gv} {visit.nombre}", color_r + Style.BRIGHT))
            res = Resultado(local.nombre, visit.nombre, gl, gv)
            actualizar_tabla(tabla_g, res)
            pausa()
        else:
            res = simular_partido(local, visit, narrativa=False)
            actualizar_tabla(tabla_g, res)

    # Mostrar tabla de grupos
    limpiar()
    print(c(f"\n  {E_COPA} TABLA — GRUPO A", Fore.CYAN + Style.BRIGHT))
    separador("-", 55)
    print(f"  {'#':>2}  {'Equipo':<28} {'PJ':>2} {'G':>2} {'E':>2} {'P':>2} {'GF':>3} {'GC':>3} {'PTS':>4}")
    separador("-", 55)
    orden_g = sorted(tabla_g.values(), key=lambda s: (s.pts, s.dg, s.gf), reverse=True)
    for i, s in enumerate(orden_g, 1):
        zona = c("CLASIFICA", Fore.GREEN) if i <= 2 else c("eliminado", Fore.RED)
        col  = Fore.CYAN if s.equipo == mi_equipo.nombre else ""
        print(c(f"  {i:>2}  {s.equipo:<28} {s.pj:>2} {s.g:>2} {s.e:>2} {s.p:>2} {s.gf:>3} {s.gc:>3} {s.pts:>4}  {zona}", col))
    separador("-", 55)

    # ¿Clasifico?
    clasificados_g = [s.equipo for s in orden_g[:2]]
    if mi_equipo.nombre not in clasificados_g:
        print(c(f"\n  {mi_equipo.nombre} queda eliminado en la fase de grupos.", Fore.RED))
        pausa()
        return "eliminado_grupos"
    print(c(f"\n  {E_BALON} {mi_equipo.nombre} clasifica a los octavos de final!", Fore.GREEN + Style.BRIGHT))
    pausa()

    # ══ OCTAVOS ══════════════════════════════════
    if not _partido_copa(mi_equipo, rivales_knockout[0], "OCTAVOS DE FINAL", narrativa):
        return "eliminado_octavos"

    # ══ CUARTOS ══════════════════════════════════
    if not _partido_copa(mi_equipo, rivales_knockout[1], "CUARTOS DE FINAL", narrativa):
        return "eliminado_cuartos"

    # ══ SEMIFINAL ════════════════════════════════
    if not _partido_copa(mi_equipo, rival_semis, f"SEMIFINAL vs {rival_semis.nombre}", narrativa):
        return "eliminado_semis"

    # ══ FINAL ════════════════════════════════════
    if not _partido_copa(mi_equipo, rival_final, f"GRAN FINAL vs {rival_final.nombre}", narrativa):
        return "subcampeon"

    return "campeon"


# ═══════════════════════════════════════════════
#  EVENTOS CAOTICOS
# ═══════════════════════════════════════════════
def evento_caotico(equipo: Equipo, dt_nombre: str) -> None:
    evento = random.randint(1, 5)
    limpiar()
    print(c(f"\n  {E_DADO} EVENTO INESPERADO", Fore.YELLOW))
    separador()

    if evento == 1:
        e = equipo.jugador_estrella()
        print(f"\n  {E_FOTO} ESCANDALO! {e.nombre_completo} fue captado de fiesta")
        print(f"     la noche anterior al partido. Los tabloides enloquecen.\n")
        print(f"  [1] Multar  (moral -15)   [2] Perdonar  (moral -5)")
        opc = input(c("  Tu decision [1/2]: ", Fore.YELLOW)).strip()
        e.moral = max(0, e.moral - (15 if opc=="1" else 5))
        print(c(f"  {'Multado' if opc=='1' else 'Perdonado'}. El equipo sigue adelante.", Fore.YELLOW))

    elif evento == 2:
        e = equipo.jugador_estrella()
        oferta = int(calcular_precio(e) * random.uniform(1.1, 1.4))
        print(f"\n  {E_DINERO} OFERTA ARABE por {e.nombre_completo} (OVR {e.overall}): ${oferta:,}")
        print(f"  [1] Aceptar   [2] Rechazar")
        if input(c("  [1/2]: ", Fore.YELLOW)).strip() == "1":
            equipo.balance += oferta
            equipo.jugadores.remove(e)
            lo, hi = rango_co(equipo.estrellas)
            rep = generar_jugador_pos(e.posicion, lo, hi)
            equipo.jugadores.append(rep)
            print(c(f"  Vendido. Llega {rep.nombre_completo}. Balance: ${equipo.balance:,}", Fore.GREEN))
        else:
            print(f"  {e.nombre_completo} se queda.")

    elif evento == 3:
        j1 = random.choice(equipo.jugadores)
        j2 = random.choice([j for j in equipo.jugadores if j != j1])
        print(f"\n  {E_PUNO} PELEA! {j1.nombre_completo} vs {j2.nombre_completo}")
        print(f"  [1] Mediar   [2] Castigar a los dos")
        if input(c("  [1/2]: ", Fore.YELLOW)).strip() == "1":
            if random.random() < 0.6:
                j1.moral = min(100, j1.moral+5); j2.moral = min(100, j2.moral+5)
                print("  Mediaste bien. Se dieron la mano.")
            else:
                j1.moral = max(0, j1.moral-5); j2.moral = max(0, j2.moral-5)
                print("  La mediacion fracaso. Ambiente tenso.")
        else:
            j1.moral = max(0, j1.moral-10); j2.moral = max(0, j2.moral-10)
            print(c("  Sancionados. Orden reestablecido.", Fore.RED))

    elif evento == 4:
        t = random.choice(equipo.once_disponible)
        t.lesion_partidos = 3
        print(f"\n  {E_LESION} LESION! {t.nombre_completo} ({t.posicion}) — fuera 3 partidos.")
        print(c("  Mala suerte.", Fore.RED))

    else:
        hincha = random.choice(["Dona Consuelo","El Toro Ramirez","Pacho Berrinches",
                                "La Mechuda de la Norte","El Gordo del Palco"])
        print(f"\n  {E_DADO} {hincha} invadio el entrenamiento con empanadas.")
        print(c("  El club no se pronuncio. Hay que amar este futbol.", Fore.GREEN))

    input(c("\n  [Enter para continuar] ", Fore.CYAN))


# ═══════════════════════════════════════════════
#  HELPERS DE PANTALLA
# ═══════════════════════════════════════════════
def limpiar():
    os.system("cls" if os.name == "nt" else "clear")

def separador(char: str = "=", largo: int = 64):
    print(c(f"  {char * largo}", Fore.CYAN))

def pausa():
    input(c("\n  [Enter para continuar]  ", Fore.CYAN))

def mostrar_plantilla(equipo: Equipo):
    print(c(f"\n  PLANTILLA — {equipo.nombre}", Fore.CYAN))
    separador("-", 65)
    print(f"  {'POS':<5} {'Nombre':<24} {'OVR':>3} {'ATK':>3} {'DEF':>3} {'FIS':>3} {'TEC':>3} {'MEN':>3}  Rasgo")
    separador("-", 65)
    for j in sorted(equipo.jugadores, key=lambda x: POS_ORDEN.get(x.posicion, 9)):
        estado  = c(f" [LES-{j.lesion_partidos}J]", Fore.RED) if j.lesion_partidos > 0 else ""
        rasgo_s = c(j.rasgo, Fore.YELLOW) if j.rasgo else c("-", Style.DIM)
        print(f"  {j.posicion:<5} {j.nombre_completo:<24} {j.overall:>3} {j.ataque:>3} {j.defensa:>3} {j.fisico:>3} {j.tecnica:>3} {j.mental:>3}  {rasgo_s}{estado}")
    separador("-", 65)
    print(f"  OVR promedio del equipo: {equipo.ovr_promedio()}")

def mostrar_equipos(equipos: list[Equipo]):
    print(c("\n  EQUIPOS — Liga BetPlay Colombia", Fore.CYAN))
    separador("-", 62)
    print(f"  {'#':<3} {'Equipo':<30} {'Ciudad':<16} {'OVR':>4}  Estrellas")
    separador("-", 62)
    for i, e in enumerate(equipos, 1):
        ovr = e.ovr_promedio()
        stars = (E_STARS * int(e.estrellas)) + ("+" if e.estrellas % 1 else "")
        print(f"  {i:<3} {e.nombre:<30} {e.ciudad:<16} {ovr:>4}  {stars}")
    separador("-", 62)


# ═══════════════════════════════════════════════
#  SIMULAR PARTIDO INTERACTIVO (liga)
# ═══════════════════════════════════════════════
def jugar_partido_liga(mi_equipo: Equipo, local: Equipo, visitante: Equipo,
                        narrativa: bool) -> Resultado:
    """Juega el partido del usuario con MT decision incluida."""
    soy_local = (local == mi_equipo)
    limpiar()
    print(c(f"\n  {E_BALON}  {local.nombre}  vs  {visitante.nombre}", Fore.CYAN + Style.BRIGHT))
    print(c(f"  Estilos: {local.estilo_dt}  vs  {visitante.estilo_dt}", Style.DIM))
    separador("-", 55)

    jl = local.once_disponible
    jv = visitante.once_disponible
    gl, gv = 0, 0

    if narrativa:
        print(c("\n  -- PRIMERA MITAD --\n", Fore.YELLOW))
        for m in range(1, 46):
            gl, gv = _procesar_minuto(m, local, visitante, jl, jv, gl, gv, True, 1.0,1.0,1.0,1.0)
            time.sleep(1.0)
    else:
        for m in range(1, 46):
            gl, gv = _procesar_minuto(m, local, visitante, jl, jv, gl, gv, False, 1.0,1.0,1.0,1.0)

    gm = gl if soy_local else gv
    gr = gv if soy_local else gl
    mt = decision_medio_tiempo(mi_equipo, visitante if soy_local else local, gm, gr, soy_local)

    if narrativa:
        limpiar()
        print(c(f"\n  {E_BALON}  {local.nombre}  vs  {visitante.nombre} | 2da mitad", Fore.CYAN + Style.BRIGHT))
        print(c(f"  Descanso: {gl} - {gv}", Fore.YELLOW)); separador("-",55)
        print(c("\n  -- SEGUNDA MITAD --\n", Fore.YELLOW))
        for m in range(46, 91):
            gl, gv = _procesar_minuto(m, local, visitante, jl, jv, gl, gv, True,
                                      mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                      mt.get("atk_v",1.0), mt.get("def_v",1.0))
            time.sleep(1.0)
    else:
        for m in range(46, 91):
            gl, gv = _procesar_minuto(m, local, visitante, jl, jv, gl, gv, False,
                                      mt.get("atk_l",1.0), mt.get("def_l",1.0),
                                      mt.get("atk_v",1.0), mt.get("def_v",1.0))

    separador("-", 55)
    gm = gl if soy_local else gv
    gr = gv if soy_local else gl
    color_r = Fore.GREEN if gm > gr else (Fore.RED if gm < gr else Fore.YELLOW)
    print(c(f"\n  RESULTADO FINAL: {local.nombre} {gl} - {gv} {visitante.nombre}", color_r + Style.BRIGHT))
    return Resultado(local.nombre, visitante.nombre, gl, gv)


# ═══════════════════════════════════════════════
#  HELPERS DE PERSISTENCIA
# ═══════════════════════════════════════════════
def _pretemporada(equipos: list[Equipo], mi_equipo: Equipo) -> None:
    """Resetea lesiones y rellena plantillas de equipos rivales si quedaron cortos."""
    for e in equipos:
        # Recuperacion pre-temporada: lesiones a 0, moral sube un poco
        for j in e.jugadores:
            j.lesion_partidos = 0
            j.moral = min(100, j.moral + 10)
        # Si algun rival vendio jugadores y quedo con menos de 11, rellenamos
        if e != mi_equipo and len(e.jugadores) < 11:
            lo, hi = rango_co(e.estrellas)
            faltantes = 11 - len(e.jugadores)
            posiciones_actuales = [j.posicion for j in e.jugadores]
            for pos in POSICIONES_11:
                if faltantes <= 0:
                    break
                if posiciones_actuales.count(pos) < POSICIONES_11.count(pos):
                    e.jugadores.append(generar_jugador_pos(pos, lo, hi))
                    posiciones_actuales.append(pos)
                    faltantes -= 1

def _mostrar_historial(historial: list[dict], mi_equipo_nombre: str) -> None:
    if not historial:
        return
    print(c(f"\n  {E_APUNTE} HISTORIAL DE TEMPORADAS — {mi_equipo_nombre}", Fore.CYAN))
    separador("-", 62)
    print(f"  {'T':<4} {'Pos':>4} {'Pts':>4} {'GF':>4} {'GC':>4}  Liga              Copa Libertadores")
    separador("-", 62)
    for h in historial:
        lib_txt = h.get("libertadores", "-")
        lib_col = Fore.GREEN if "campeon" in lib_txt else \
                  Fore.YELLOW if "sub" in lib_txt or "semi" in lib_txt else \
                  Fore.RED if "eliminado" in lib_txt else ""
        linea = f"  {h['temporada']:<4} {h['pos']:>4} {h['pts']:>4} {h['gf']:>4} {h['gc']:>4}  {h['campeon_liga']:<18}"
        print(linea + c(lib_txt, lib_col))
    separador("-", 62)


# ═══════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════
def main():
    limpiar()
    print(c(ASCII_LOGO, Fore.CYAN))
    print(c(f"     {E_COPA}  Liga BetPlay + Copa Libertadores — v0.3  {E_COPA}", Fore.YELLOW))
    separador()

    dt_nombre = input(c("\n  Como te llamas, DT? ", Fore.YELLOW)).strip() or "Mister"
    print(c(f"\n  Bienvenido, {dt_nombre}. Que empiece el show.\n", Fore.GREEN))
    pausa()

    equipos = generar_liga()

    # ── Elegir equipo (solo al inicio) ────────────
    limpiar()
    mostrar_equipos(equipos)
    while True:
        try:
            opcion = int(input(c("\n  Elige tu equipo [1-8]: ", Fore.YELLOW))) - 1
            if 0 <= opcion <= 7: break
        except ValueError: pass
        print(c("  Opcion invalida.", Fore.RED))

    mi_equipo = equipos[opcion]
    print(c(f"\n  Elegiste: {mi_equipo.nombre} ({mi_equipo.ciudad})", Fore.GREEN))
    limpiar()
    mostrar_plantilla(mi_equipo)
    pausa()

    # ── Elegir estilo (solo al inicio) ────────────
    limpiar()
    print(c("\n  ELIGE TU ESTILO TACTICO", Fore.CYAN))
    separador("-", 55)
    for i, (est, desc) in enumerate({
        "haramball":  "Alta presion, ritmo brutal    — vence a cruyffismo",
        "cruyffismo": "Posesion y triangulos          — vence a flickismo",
        "flickismo":  "Contragolpe y verticalidad     — vence a haramball",
    }.items(), 1):
        marca = c(" <- ACTUAL", Fore.YELLOW) if est == mi_equipo.estilo_dt else ""
        print(f"  [{i}] {est:<14} {desc}{marca}")
    separador("-", 55)
    while True:
        try:
            est_opc = int(input(c("\n  Tu estilo [1-3]: ", Fore.YELLOW))) - 1
            if 0 <= est_opc <= 2: break
        except ValueError: pass
        print(c("  Opcion invalida.", Fore.RED))
    mi_equipo.estilo_dt = ESTILOS_DT[est_opc]
    print(c(f"\n  Confirmado: {mi_equipo.estilo_dt}.", Fore.GREEN))
    pausa()

    # ── Estado persistente entre temporadas ───────
    historial: list[dict] = []
    temporada = 1

    # ══════════════════════════════════════════════
    #  LOOP PRINCIPAL — persiste entre temporadas
    # ══════════════════════════════════════════════
    while True:

        # ── Inicio de temporada ───────────────────
        limpiar()
        print(c(f"\n  {E_BALON}  TEMPORADA {temporada}  —  {mi_equipo.nombre}", Fore.CYAN + Style.BRIGHT))
        print(c(f"  DT: {dt_nombre}  |  Estilo: {mi_equipo.estilo_dt}  |  Balance: ${mi_equipo.balance:,}", Fore.WHITE))
        separador()

        # Mostrar historial si hay temporadas previas
        if historial:
            _mostrar_historial(historial, mi_equipo.nombre)

        # Pre-temporada: recuperar lesiones, rellenar rivales
        _pretemporada(equipos, mi_equipo)

        # Temporadas 2+: mercado de inicio de temporada + cambio de estilo opcional
        if temporada > 1:
            print(c(f"\n  Nueva temporada. Hay que reforzar el plantel.", Fore.YELLOW))
            print(f"  Balance actual: ${mi_equipo.balance:,}  |  OVR promedio: {mi_equipo.ovr_promedio()}")
            print(f"  Plantilla actual: {len(mi_equipo.jugadores)} jugadores")
            separador("-", 50)
            print("  [1] Ir al mercado de pases")
            print("  [2] Cambiar estilo tactico")
            print("  [3] Ver plantilla")
            print("  [4] Comenzar la temporada")
            while True:
                opc_pre = input(c("\n  Opcion: ", Fore.YELLOW)).strip()
                if opc_pre == "1":
                    mercado_de_pases(mi_equipo, equipos)
                elif opc_pre == "2":
                    limpiar()
                    print(c("\n  CAMBIAR ESTILO", Fore.CYAN))
                    separador("-", 40)
                    for ii, est in enumerate(ESTILOS_DT, 1):
                        marca = c(" <- ACTUAL", Fore.YELLOW) if est == mi_equipo.estilo_dt else ""
                        print(f"  [{ii}] {est}{marca}")
                    try:
                        nuevo = int(input(c("  Nuevo estilo [1-3]: ", Fore.YELLOW))) - 1
                        if 0 <= nuevo <= 2:
                            mi_equipo.estilo_dt = ESTILOS_DT[nuevo]
                            print(c(f"  Estilo cambiado a: {mi_equipo.estilo_dt}", Fore.GREEN))
                    except ValueError:
                        pass
                elif opc_pre == "3":
                    limpiar()
                    mostrar_plantilla(mi_equipo)
                    pausa()
                    limpiar()
                    print(c(f"\n  {E_BALON}  TEMPORADA {temporada}  —  {mi_equipo.nombre}", Fore.CYAN + Style.BRIGHT))
                    separador()
                elif opc_pre == "4":
                    break
                else:
                    print(c("  Opcion invalida.", Fore.RED))
        else:
            pausa()

        # ── Generar fixture y tabla frescos ───────
        fixture = generar_fixture(equipos)
        tabla   = inicializar_tabla(equipos)

        # ══ LOOP LIGA ════════════════════════════
        for num_j, jornada in enumerate(fixture, 1):
            limpiar()
            print(c(f"\n  {E_BALON} T{temporada} — JORNADA {num_j} / {len(fixture)}", Fore.CYAN + Style.BRIGHT))
            print(c(f"  {mi_equipo.nombre}  |  Balance: ${mi_equipo.balance:,}  |  OVR: {mi_equipo.ovr_promedio()}", Style.DIM))
            separador()

            for e in equipos:
                e.tick_lesiones()

            mi_partido, rivales_p = None, []
            for l, v in jornada:
                if l == mi_equipo or v == mi_equipo: mi_partido = (l, v)
                else: rivales_p.append((l, v))

            print(f"\n  Programa:")
            for l, v in jornada:
                marca = c("  << TU PARTIDO >>", Fore.CYAN) if (l==mi_equipo or v==mi_equipo) else ""
                print(f"    {l.nombre:<30} vs  {v.nombre}{marca}")

            print()
            narrativa = input(c("  Ver narrativa minuto a minuto? [s/N]: ", Fore.YELLOW)).strip().lower() == "s"

            if mi_partido:
                res_mio = jugar_partido_liga(mi_equipo, *mi_partido, narrativa)
                actualizar_tabla(tabla, res_mio)

            print(c("\n  Otros resultados:", Fore.WHITE))
            for l, v in rivales_p:
                res = simular_partido(l, v, narrativa=False)
                actualizar_tabla(tabla, res)
                print(f"    {res.equipo_local:<30} {res.goles_local} - {res.goles_visitante}  {res.equipo_visitante}")
                time.sleep(0.12)

            mostrar_tabla(tabla, mi_equipo.nombre)

            if random.random() < 0.25:
                evento_caotico(mi_equipo, dt_nombre)
                limpiar()

            if num_j < len(fixture):
                pausa()

        # ══ FIN DE TEMPORADA ═════════════════════
        limpiar()
        print(c(f"\n  {E_TROFEO}  FIN DE TEMPORADA {temporada}  {E_TROFEO}", Fore.CYAN + Style.BRIGHT))
        separador()
        mostrar_tabla(tabla, mi_equipo.nombre)

        ordenada = tabla_ordenada(tabla)
        campeon  = ordenada[0]
        clasif   = [s.equipo for s in ordenada[:CUPOS_LIBERTADORES]]
        mi_pos   = next(i for i, s in enumerate(ordenada, 1) if s.equipo == mi_equipo.nombre)
        mi_s     = tabla[mi_equipo.nombre]

        if campeon.equipo == mi_equipo.nombre:
            print(c(f"  {E_TROFEO} CAMPEON DE LIGA! {mi_equipo.nombre}!", Fore.GREEN + Style.BRIGHT))
        else:
            print(c(f"  Campeon de liga: {campeon.equipo} ({campeon.pts} pts)", Fore.YELLOW))
            print(f"  Tu equipo: {mi_pos}° lugar — {mi_s.pts} pts  (GF:{mi_s.gf} GC:{mi_s.gc})")

        print(c(f"\n  Clasificados a Copa Libertadores:", Fore.YELLOW))
        for i, eq_nombre in enumerate(clasif, 1):
            tag = c("  << TU EQUIPO >>", Fore.CYAN) if eq_nombre == mi_equipo.nombre else ""
            print(c(f"    {i}. {eq_nombre}{tag}", Fore.GREEN))
        separador()

        # ── Copa Libertadores ─────────────────────
        resultado_lib = "-"
        if mi_equipo.nombre in clasif:
            print(c(f"\n  {E_COPA} {mi_equipo.nombre} clasifico a la Copa Libertadores!", Fore.GREEN + Style.BRIGHT))
            if input(c("  Jugar Copa Libertadores? [s/N]: ", Fore.YELLOW)).strip().lower() == "s":
                print(c("\n  Se abre el mercado de pases pre-copa.", Fore.YELLOW))
                pausa()
                mercado_de_pases(mi_equipo, equipos)

                otro_nombre     = [eq for eq in clasif if eq != mi_equipo.nombre]
                otro_colombiano = next((e for e in equipos if e.nombre == otro_nombre[0]), equipos[1]) \
                                  if otro_nombre else equipos[1]

                narrativa_lib = input(c("\n  Ver narrativa en la Libertadores? [s/N]: ", Fore.YELLOW)).strip().lower() == "s"
                resultado_lib = copa_libertadores(mi_equipo, otro_colombiano, narrativa_lib)

                limpiar()
                print(c(f"\n  {E_COPA} COPA LIBERTADORES T{temporada} — RESULTADO FINAL", Fore.CYAN + Style.BRIGHT))
                separador()
                msgs = {
                    "campeon":           (Fore.GREEN + Style.BRIGHT, f"{E_TROFEO} CAMPEON DE AMERICA! {mi_equipo.nombre}! {dt_nombre}, leyenda del futbol!"),
                    "subcampeon":        (Fore.YELLOW,               f"Subcampeon de America. Muy cerca del sueno, {dt_nombre}."),
                    "eliminado_semis":   (Fore.YELLOW,               f"Eliminados en semis. Gran participacion, {dt_nombre}."),
                    "eliminado_cuartos": (Fore.RED,                  f"Eliminados en cuartos. La copa es otro nivel."),
                    "eliminado_octavos": (Fore.RED,                  f"Eliminados en octavos. Hay que crecer mas."),
                    "eliminado_grupos":  (Fore.RED,                  f"Eliminados en grupos. La proxima sera."),
                }
                col, msg = msgs.get(resultado_lib, (Fore.WHITE, ""))
                print(c(f"\n  {msg}", col))
                separador()
                pausa()
        else:
            print(c(f"\n  {mi_equipo.nombre} no clasifico a Libertadores esta temporada.", Fore.RED))
            if mi_pos <= 4:
                print(c("  Cerca. La proxima hay que apretar.", Fore.YELLOW))

        # ── Guardar en historial ──────────────────
        historial.append({
            "temporada":      temporada,
            "pos":            mi_pos,
            "pts":            mi_s.pts,
            "gf":             mi_s.gf,
            "gc":             mi_s.gc,
            "campeon_liga":   campeon.equipo[:18],
            "libertadores":   resultado_lib,
        })

        # ── Siguiente temporada? ──────────────────
        separador()
        print(c(f"\n  Balance acumulado: ${mi_equipo.balance:,}", Fore.YELLOW))
        print(c(f"  OVR promedio del plantel: {mi_equipo.ovr_promedio()}", Fore.WHITE))
        print()
        if input(c("  Jugar temporada " + str(temporada + 1) + "? [s/N]: ", Fore.YELLOW)).strip().lower() == "s":
            temporada += 1
            # El balance recibe un bonus de premio de liga
            premio = {1: 500_000, 2: 350_000, 3: 200_000}.get(mi_pos, 100_000)
            mi_equipo.balance += premio
            print(c(f"\n  Premio de liga: +${premio:,}  |  Nuevo balance: ${mi_equipo.balance:,}", Fore.GREEN))
            time.sleep(1.5)
        else:
            limpiar()
            print(c(f"\n  === CARRERA DE {dt_nombre} con {mi_equipo.nombre} ===", Fore.CYAN + Style.BRIGHT))
            separador()
            _mostrar_historial(historial, mi_equipo.nombre)
            print(c(f"\n  Gracias por jugar ALPHA FOOTBALL. {E_BALON}\n", Fore.GREEN))
            break


if __name__ == "__main__":
    main()
