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

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)
from alpha_football.sanciones import sancionado as _sancionado  # noqa: E402  sanción de la competición que se juega

# ── Parametros tacticos ───────────────────────────────────────────────────────
# v0.7: "anchelottismo" es la tactica equilibrada: bono_estilo devuelve 1.0 contra
# cualquiera; su ventaja es la consistencia + la sinergia con la formacion (synergy_equipo).
# v3.3.0: los 9 estilos y su matriz viven en estilos.py (re-exportados aquí).
from alpha_football.estilos import ESTILOS_DT, ESTILO_VENTAJA, NOMBRE_ESTILO, DESC_ESTILO  # noqa: E402

RASGOS: list[str] = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

# v2.5.0: MENTALIDAD (cuánto arriesga el equipo). Eje aparte del estilo (piedra-papel-tijera).
# prob = ataques generados, atk/def = multiplicadores del duelo, def_goleador = % de goles de
# defensas (None = cualquiera de los 10 de campo, uniforme).
MENTALIDADES: list[str] = ["autobus", "defensiva", "normal", "ofensiva", "todo_o_nada"]
NOMBRE_MENTALIDAD: dict[str, str] = {
    "autobus": "AUTOBÚS", "defensiva": "DEFENSIVA", "normal": "NORMAL",
    "ofensiva": "OFENSIVA", "todo_o_nada": "TODO O NADA",
}
EFECTO_MENTALIDAD: dict[str, dict] = {
    "autobus":     {"prob": 0.60, "atk": 0.85, "def": 1.30, "def_goleador": 0.00},
    "defensiva":   {"prob": 0.85, "atk": 0.95, "def": 1.12, "def_goleador": 0.08},
    "normal":      {"prob": 1.00, "atk": 1.00, "def": 1.00, "def_goleador": 0.08},
    "ofensiva":    {"prob": 1.15, "atk": 1.05, "def": 0.92, "def_goleador": 0.15},
    "todo_o_nada": {"prob": 1.35, "atk": 1.10, "def": 0.78, "def_goleador": None},
}


def normalizar_mentalidad(m) -> str:
    """Mentalidad válida (cualquier valor desconocido → 'normal')."""
    return m if m in EFECTO_MENTALIDAD else "normal"


def _decidir_mentalidad(d: float, minuto: int, goles_propios: int, goles_rival: int, es_local: bool) -> str:
    """
    v2.5.0: mentalidad de la IA. `d` = media del once propio − la del rival.
    Base por diferencia de nivel (+2 de local) y, desde cierto minuto, según el marcador.
    """
    try:
        dif = goles_propios - goles_rival
        if dif <= -3:
            return "normal"                       # se rinde
        if dif < 0:
            if minuto >= 82:
                return "todo_o_nada"
            if minuto >= 70:
                return "ofensiva"
        if dif == 1:
            if minuto >= 85 and d < 0:
                return "autobus"
            if minuto >= 75:
                return "defensiva"
        base = d + (2 if es_local else 0)
        if base <= -14 and not es_local:
            return "autobus"
        if base <= -8:
            return "defensiva"
        if base >= 8:
            return "ofensiva"
        return "normal"
    except Exception:
        return "normal"


def mentalidad_ia(equipo, rival, minuto: int, goles_propios: int, goles_rival: int, es_local: bool) -> str:
    """v2.5.0: mentalidad que elegiría la IA para `equipo` en este momento del partido."""
    try:
        return _decidir_mentalidad(_media_once(equipo) - _media_once(rival), minuto,
                                   goles_propios, goles_rival, es_local)
    except Exception:
        return "normal"

# ── Parametros de simulacion ──────────────────────────────────────────────────
# Probabilidad de que ocurra un evento de ataque por equipo por minuto
PROB_ATAQUE: float = 0.14

# Sigma de la distribucion gaussiana en resolver_choque.
# Valor original 12 → casi cero goles por partido.
# Valor calibrado 30 → ~10% de conversion por oportunidad → ~1.3 goles/equipo/partido.
SIGMA_CHOQUE: float = 30.0

UMBRAL_GOL:  float = 50.0   # diff > umbral → gol (v2.3.6: recalibrado con la compresión)
UMBRAL_TIRO: float = 29.0   # diff > umbral → tiro (no convierte)

# Multiplicador de ataque para el equipo local (ventaja de cancha ~6%)
VENTAJA_LOCAL: float = 1.06

# v2.3.6: realismo. Antes la diferencia bruta ataque-defensa crecía sin freno con la
# brecha de media (un 87 vs un 70 ganaba el 100% y el 58% de las veces por 7+ goles).
# Ahora esa diferencia se COMPRIME alrededor del valor típico de un duelo parejo, así
# el favorito sigue ganando la mayoría pero el pequeño puede sorprender.
DIFF_REFERENCIA: float = 7.0     # diff bruta media de un duelo entre equipos parejos
COMPRESION_DIFF: float = 0.40    # cuánto pesa la ventaja individual sobre esa referencia
# Suerte del día por equipo (se suma a sus ocasiones) y "batacazo" del pequeño.
SUERTE_SIGMA: float = 5.0
PROB_BATACAZO: float = 0.22      # prob. de que el equipo claramente inferior tenga su día
BONO_BATACAZO: float = 12.0
BRECHA_BATACAZO: float = 3.0     # diferencia de media (once titular) para ser "pequeño"
# Freno a las goleadas: con +3 o más el que gana levanta el pie (menos ocasiones).
FRENO_GOLEADA: float = 0.55
# v4.4.0: minutos de adición al final (sorteados por partido) y +25% de ocasiones en ellos.
ADICION: tuple = (3, 10)
BONO_GOL_ADICION: float = 1.25

from alpha_football.partido_ctx import (  # noqa: E402  v4.0.0
    aplicar_evento as _aplicar_evento, MULT_EXPULSION as _MULT_EXPULSION, MAX_CAMBIOS as _MAX_CAMBIOS,
    clave as _clave)
from alpha_football.energia import (  # noqa: E402  v4.0.0
    PROB_LESION_90, factor_lesion, DURACION_LESION, PESOS_LESION)

# v4.0.0: incidencias dentro del partido (probabilidades por equipo y minuto).
PROB_AMARILLA_MIN: float = 3.5 / 180
PROB_ROJA_MIN: float = 0.15 / 180
PROB_PENAL_GOL: float = 0.07        # fracción de los goles que son de penal (no suma goles)
PROB_PENAL_FALLADO: float = 0.06 / 180
PROB_ATAJADA: float = 0.5           # de los tiros fallados, los que ataja el portero
PROB_PALO: float = 0.15             # del resto, los que dan en el palo ('ocasion')
PROB_FALTA_MIN: float = 0.03        # falta peligrosa (solo comentario)
PROB_CAMBIO_IA_MIN: float = 0.2
MINUTO_CAMBIOS_IA: tuple = (60, 80)


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
    ctx:              Any = None                          # v4.0.0: EstadoPartido final (partido_ctx)
    notas:            dict = field(default_factory=dict)  # v4.0.0: {clave jugador: nota final}

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
    """Bonus/malus tactico (matriz de 9 estilos). +10% al ganador, -9% al perdedor.
    v3.9.0: bajado de +15%/-13% (con 9 estilos el contraestilo pesaba más que la media)."""
    if estilo_def in ESTILO_VENTAJA.get(estilo_atk, ()): return 1.10
    if estilo_atk in ESTILO_VENTAJA.get(estilo_def, ()): return 0.91
    return 1.0


def synergy_equipo(equipo) -> float:
    """
    Multiplicador de ataque por SINERGIA entre la formación elegida y la táctica del equipo,
    más la FAMILIARIDAD acumulada con esa táctica (jugar mucho una táctica con buenos
    resultados la potencia, hasta poder superar el bonus base de la formación).

    Devuelve un factor en [0.97, 1.09]. Resiliente: 1.0 si faltan datos.
    """
    try:
        estilo = getattr(equipo, "estilo_dt", "") or ""
        alin = getattr(equipo, "alineacion_activa", None)
        formacion = getattr(alin, "formacion", None) if alin else None
        syn = 1.0
        # Bonus si la táctica coincide con la preferida de la formación.
        # OJO: el motor amplifica mucho los multiplicadores de ataque (umbral gaussiano),
        # así que los bonos son pequeños a propósito (sinergia plena ~ +35% goles, no x2).
        if formacion and estilo:
            try:
                from alpha_football.formaciones import pref as _pref
                if estilo == _pref(formacion):
                    syn += 0.035
            except Exception:
                pass
        # Bonus por familiaridad (0..1 -> hasta +0.05)
        fam = getattr(equipo, "tactica_familiaridad", None) or {}
        try:
            syn += min(0.05, max(0.0, float(fam.get(estilo, 0.0))) * 0.05)
        except Exception:
            pass
        return max(0.97, min(1.09, syn))
    except Exception:
        return 1.0


def actualizar_familiaridad(equipo, gano: bool, empato: bool) -> None:
    """
    Sube la familiaridad del equipo con la táctica que jugó (más si ganó), con leve decay
    de las demás. Acumulador 0..1. Se llama tras el partido del usuario.
    """
    try:
        fam = getattr(equipo, "tactica_familiaridad", None)
        if fam is None:
            fam = {}
            setattr(equipo, "tactica_familiaridad", fam)
        estilo = getattr(equipo, "estilo_dt", "") or ""
        if not estilo:
            return
        inc = 0.06 if gano else (0.02 if empato else 0.0)
        fam[estilo] = max(0.0, min(1.0, fam.get(estilo, 0.0) + inc))
        # Leve decay de las otras tácticas (se "olvida" lo que no se practica)
        for k in list(fam.keys()):
            if k != estilo:
                fam[k] = max(0.0, fam[k] - 0.01)
    except Exception:
        pass


def _prob_penal(jugador) -> float:
    """Probabilidad de convertir un penal según el atributo `penales` del jugador."""
    try:
        pen = getattr(jugador, "penales", 0) or 60
    except Exception:
        pen = 60
    return max(0.30, min(0.92, 0.55 + (pen - 60) * 0.006))


def tanda_penales_jugadores(cobradores_local: list, cobradores_vis: list,
                            rng: Optional[object] = None) -> tuple[bool, str, list]:
    """
    Resuelve una tanda de penales usando el atributo `penales` de los cobradores elegidos.
    5 rondas + muerte súbita. Devuelve (gana_local, "X-Y", secuencia).
    `secuencia` es una lista de dicts con la info de cada disparo:
        {'ronda': int, 'local_mete': bool, 'visitante_mete': bool,
         'cobrador_local': str|None, 'cobrador_visitante': str|None}
    """
    azar = rng or random
    cl = list(cobradores_local) or [None]
    cv = list(cobradores_vis) or [None]

    def _mete(j) -> bool:
        return azar.random() < (_prob_penal(j) if j is not None else 0.55)

    def _nombre(j) -> Optional[str]:
        if j is None:
            return None
        try:
            return getattr(j, 'apellido', None) or getattr(j, 'nombre_completo', None) or str(j)
        except Exception:
            return str(j)

    gl = gv = 0
    secuencia: list = []
    for i in range(5):
        idx_l = i % len(cl)
        idx_v = i % len(cv)
        c_l = cl[idx_l]
        c_v = cv[idx_v]
        mete_l = _mete(c_l)
        mete_v = _mete(c_v)
        if mete_l:
            gl += 1
        if mete_v:
            gv += 1
        secuencia.append({
            'ronda': i + 1,
            'local_mete': mete_l,
            'visitante_mete': mete_v,
            'cobrador_local': _nombre(c_l),
            'cobrador_visitante': _nombre(c_v),
        })

    ronda = 5
    while gl == gv and ronda < 30:
        idx_l = ronda % len(cl)
        idx_v = ronda % len(cv)
        c_l = cl[idx_l]
        c_v = cv[idx_v]
        a = _mete(c_l)
        b = _mete(c_v)
        if a and not b:
            gl += 1
        elif b and not a:
            gv += 1
        ronda += 1
        secuencia.append({
            'ronda': ronda,
            'local_mete': a,
            'visitante_mete': b,
            'cobrador_local': _nombre(c_l),
            'cobrador_visitante': _nombre(c_v),
        })
    if gl == gv:  # tope de seguridad para no colgar
        gl += 1 if azar.random() < 0.5 else 0
        gv += 1 if gl == gv else 0
    return (gl > gv), f"{gl}-{gv}", secuencia


# ── Nucleo de simulacion ──────────────────────────────────────────────────────

def resolver_choque(
    atk:        float,
    def_:       float,
    estilo_atk: str,
    estilo_def: str,
    suerte:     float = 0.0,
) -> str:
    """
    Resuelve un duelo 1v1 atacante-defensor.
    Retorna 'gol', 'tiro' o 'defensa'.
    v2.3.6: la ventaja bruta se comprime hacia DIFF_REFERENCIA (ver arriba) y se suma
    la suerte del día del equipo atacante.
    """
    poder = atk * bono_estilo(estilo_atk, estilo_def)
    bruto = poder - def_
    diff  = (DIFF_REFERENCIA + COMPRESION_DIFF * (bruto - DIFF_REFERENCIA)
             + suerte + random.gauss(0.0, SIGMA_CHOQUE))
    if diff > UMBRAL_GOL:  return "gol"
    if diff > UMBRAL_TIRO: return "tiro"
    return "defensa"


def _once_titular(equipo: Equipo) -> list:
    """
    Devuelve los 11 jugadores que están efectivamente en la cancha.
    Prioriza la alineación activa (titulares) si está completa y sin lesionados;
    si no, completa con los primeros 11 no lesionados disponibles.
    Esto evita que los suplentes del banco marquen goles (v0.8.1).
    """
    try:
        jugadores = list(getattr(equipo, "jugadores", []) or [])
        alin = getattr(equipo, "alineacion_activa", None)
        if alin and getattr(alin, "titulares", None):
            disp = []
            usados = set()
            for idx in alin.titulares:
                if 0 <= idx < len(jugadores) and idx not in usados:
                    j = jugadores[idx]
                    if getattr(j, "lesion_partidos", 0) == 0 and not _sancionado(j):
                        disp.append(j)
                        usados.add(idx)
                        if len(disp) == 11:
                            return disp
            # Si faltan titulares por lesión, completar con los mejores no lesionados
            if len(disp) < 11:
                candidatos = [j for j in jugadores if j not in disp and getattr(j, "lesion_partidos", 0) == 0 and not _sancionado(j)]
                candidatos.sort(key=lambda x: getattr(x, "overall", 0), reverse=True)
                for j in candidatos:
                    if len(disp) >= 11:
                        break
                    disp.append(j)
            if len(disp) == 11:
                return disp
        # Fallback (equipos de la IA sin alineación): v2.3.6 el mejor 4-3-3 disponible.
        # Antes eran "los primeros 11 de la lista", y como las plantillas vienen
        # ordenadas por posición la IA jugaba con 2 porteros, 7 defensas y 0 delanteros.
        no_lesionados = [j for j in jugadores if getattr(j, "lesion_partidos", 0) == 0 and not _sancionado(j)]
        if len(no_lesionados) >= 11:
            try:
                from alpha_football.formaciones import mejor_once
                from alpha_football.energia import puntaje_once
                once = [no_lesionados[i] for i in mejor_once(no_lesionados, "4-3-3", puntaje=puntaje_once)]
                if len(once) == 11:
                    return once
            except Exception as e_once:
                logger.debug(f"mejor_once falló para {getattr(equipo, 'nombre', '?')}: {e_once}")
            return no_lesionados[:11]
        return no_lesionados or list(jugadores)[:11]
    except Exception as e:
        try:
            return list(getattr(equipo, "jugadores", []))[:11]
        except Exception:
            return []


def _media_once(equipo) -> float:
    """Media (OVR) del once que está en la cancha."""
    once = _once_titular(equipo)
    return sum(getattr(j, 'overall', 60) for j in once) / max(1, len(once))


def sortear_suerte(local, visitante, rng=None) -> tuple[float, float]:
    """
    v2.3.6: suerte del día de cada equipo para UN partido (se suma a sus ocasiones).
    Si hay un favorito claro, el pequeño tiene PROB_BATACAZO de tener "su día".
    """
    azar = rng or random
    sl = azar.gauss(0.0, SUERTE_SIGMA)
    sv = azar.gauss(0.0, SUERTE_SIGMA)
    try:
        brecha = _media_once(local) - _media_once(visitante)
    except Exception:
        brecha = 0.0
    if abs(brecha) >= BRECHA_BATACAZO and azar.random() < PROB_BATACAZO:
        if brecha > 0:
            sv += BONO_BATACAZO
        else:
            sl += BONO_BATACAZO
    return sl, sv


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
    # v4.0.0: más variedad
    "{j} tira una pared en la frontal y encara...",
    "{j} arranca desde mitad de cancha a toda velocidad...",
    "{j} aprovecha un error en la salida rival...",
    "{j} llega de segunda linea y saca el zapatazo...",
    "{j} baja el balon con el pecho y prepara el remate...",
    "{j} desborda por la banda y busca el arco...",
]
_GOL: list[str] = [
    "GOOOOOL! {j} no perdona para {eq}!",
    "GOOOOOL! {j} define con clase — {eq} enloquece!",
    "GOOOL! La pelota toca el palo... y entra! {j}!",
    "GOOOL! {j} engana al portero — pura magia!",
    "GOOOOL! {eq} se va al frente con {j}!",
    "GOOOOL! {j} la manda al rincon, imposible para el portero!",
    # v4.0.0: más variedad
    "GOOOL! Golazo de {j}, la clava en el angulo para {eq}!",
    "GOOOL! {j} la empuja en el segundo palo!",
    "GOOOOL! {j} se saca un defensor de encima y define cruzado!",
    "GOOOL! Remate seco de {j}, la red se infla — {eq} celebra!",
    "GOOOL! {j} picándola ante la salida del portero! Que atrevimiento!",
]
_FALLO: list[str] = [
    "Tiro de {j} por encima del travesano!",
    "{j} remata al cuerpo del portero. Que lastima.",
    "Ocasion perdida de {j} — el balon se va a las gradas.",
    "El portero salva con el pie el remate de {j}.",
    "{j} falla increiblemente solo ante el arco.",
    "El palo le dice NO a {j}!",
    # v4.0.0: más variedad
    "{j} le pega mordido y el balon se va desviado.",
    "{j} define con el arco a su merced... y la tira afuera!",
    "Remate de {j} que pasa rozando el poste.",
    "{j} se enreda con el balon en el momento del remate.",
    "{j} prueba de lejos, pero sin direccion.",
]
_DEFENSA: list[str] = [
    "{d} llega con todo y despeja el peligro.",
    "Gran intervencion de {d}, limpia y sin falta.",
    "{d} anticipa bien y corta la jugada.",
    "{d} saca la pelota en la linea — increible!",
    "{d} gana el duelo por arriba y aleja el balon.",
]
# v2.3.6: frases por posición de quien defiende la jugada.
_DEFENSA_POR: list[str] = [
    "Tapada monumental del portero {d}!",
    "{d} vuela y la saca del angulo!",
    "Paradon de {d}, que achica y tapa el remate.",
    "{d} ataja seguro en dos tiempos.",
]
_DEFENSA_MED: list[str] = [
    "{d} recupera en el mediocampo y corta la jugada.",
    "{d} se cruza a tiempo y roba el balon.",
    "Gran lectura de {d}, que intercepta el pase.",
]
_DEFENSA_DEL: list[str] = [
    "{d} baja a ayudar y recupera el balon.",
    "{d} presiona arriba y corta la salida rival.",
    "Sacrificio de {d}, que retrocede y quita el balon.",
]
_FRASES_DEFENSA_POR_POSICION: dict = {
    "POR": _DEFENSA_POR, "DEF": _DEFENSA, "MED": _DEFENSA_MED, "DEL": _DEFENSA_DEL,
}


def _frase_defensa(defensor) -> str:
    """Frase de una jugada defendida acorde a la posición REAL de quien la defiende."""
    frases = _FRASES_DEFENSA_POR_POSICION.get(getattr(defensor, 'posicion', 'DEF'), _DEFENSA)
    return random.choice(frases).format(d=defensor.nombre_completo)
# v4.0.0: frases de las incidencias nuevas ({j} = protagonista, {d} = portero/defensor).
_ATAJADA: list[str] = [
    "{j} remata con fuerza... y {d} vuela para sacarla!",
    "Atajadon de {d} ante el disparo de {j}!",
    "{d} achica rapido y le tapa el mano a mano a {j}.",
    "{j} busca el palo lejano, pero {d} esta atento.",
    "{d} saca una mano milagrosa al cabezazo de {j}!",
    "Seguridad total de {d}: bloca el remate de {j}.",
]
_PALO: list[str] = [
    "Uyyy! {j} estrella el balon en el palo!",
    "El travesaño salva al rival: remate de {j} que se estrella arriba.",
    "{j} pega en el poste! Se salvo el arco!",
    "La pelota de {j} besa el palo y sale!",
    "Ocasion clarisima de {j}: palo y fuera!",
]
_AMARILLA: list[str] = [
    "Tarjeta amarilla para {j} por una entrada tardia.",
    "{j} ve la amarilla por protestar.",
    "Amarilla a {j}: corto un contragolpe con falta.",
    "El arbitro amonesta a {j} por un agarron.",
    "{j} se lleva la amarilla por perder tiempo.",
    "Entrada fuerte de {j}: amarilla.",
]
_DOBLE_AMARILLA: list[str] = [
    "Segunda amarilla para {j}: se va a la calle!",
    "{j} ve la segunda amarilla y deja a su equipo con uno menos!",
    "Doble amarilla a {j}. Expulsado!",
    "{j} vuelve a pegar y el arbitro no perdona: roja por doble amarilla.",
    "Error infantil de {j}: segunda amarilla y afuera.",
]
_ROJA: list[str] = [
    "ROJA DIRECTA para {j}! Planchazo terrible!",
    "{j} se va expulsado por una agresion!",
    "Roja a {j} por cortar una ocasion manifiesta de gol!",
    "El arbitro saca la roja sin dudar: {j} a la ducha!",
    "Entrada criminal de {j}: roja directa!",
]
_LESION: list[str] = [
    "{j} se tira al cesped con gestos de dolor... no puede seguir!",
    "Mala noticia: {j} se toca el muslo y pide el cambio.",
    "{j} cae mal tras un choque y sale lesionado.",
    "{j} se retuerce en el suelo: entran las asistencias.",
    "{j} siente un pinchazo en la rodilla. Se acabo su partido.",
]
_CAMBIO: list[str] = [
    "Cambio: entra {e} por {s}.",
    "Mueve el banquillo: {s} deja su lugar a {e}.",
    "Sale {s}, entra {e}.",
    "Aire fresco: {e} ingresa por {s}.",
    "{s} se va ovacionado; entra {e}.",
]
_PENAL_GOL: list[str] = [
    "PENAL! {j} lo cambia por gol con frialdad para {eq}!",
    "GOOOL de penal! {j} manda al portero a un lado y la pelota al otro!",
    "Penal convertido por {j}: fuerte y arriba!",
    "{j} no falla desde los once pasos — gol de {eq}!",
    "Penal a lo Panenka de {j}! Gol de {eq}!",
]
_PENAL_FALLO: list[str] = [
    "PENAL para {eq}... y {j} lo falla! Se va desviado!",
    "Penal atajado! El portero adivina el remate de {j}!",
    "{j} la manda por encima del travesaño desde el punto penal!",
    "{j} estrella el penal en el palo!",
    "Que nervios: {j} resbala y el penal se va lejos.",
]
_FALTA: list[str] = [
    "Falta peligrosa sobre {j} en la frontal del area.",
    "{j} es derribado cerca del area: tiro libre.",
    "Juego brusco: le hacen falta a {j} en la banda.",
    "El arbitro pita falta a favor de {j}.",
    "{j} provoca la falta con un regate endiablado.",
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
        print(f"{pfx} | " + _frase_defensa(defensor))


def _evento_jugada(minuto: int, resultado: str, eq_a, eq_d, atacante, defensor, ja: list, jd: list,
                   lado_a: str, ctx=None) -> dict:
    """
    v4.0.0: arma el evento de una jugada y lo aplica al ctx. Un 'gol' puede ser de penal (mismo
    gol, otra frase) y lleva asistente; un 'tiro' puede ser atajada del portero u 'ocasion'
    (palo); la jugada defendida suma al defensor. Los objetos van en el evento (ver partido_ctx).
    """
    nb = random.choice(_ATAQUE).format(j=atacante.nombre_completo)
    ev = {"minuto": minuto, "tipo": resultado, "equipo_id": eq_a.id, "lado": lado_a,
          "jugador": atacante, "jugador_id": getattr(atacante, "id", None),
          "defensor": defensor, "defensor_id": getattr(defensor, "id", None)}
    if resultado == "gol":
        ev["penal"] = random.random() < PROB_PENAL_GOL
        frases = _PENAL_GOL if ev["penal"] else _GOL
        ev["detalle"] = random.choice(frases).format(j=atacante.nombre_completo, eq=eq_a.nombre)
        asistente = None
        if not ev["penal"] and random.random() < 0.7:
            cands = [j for j in ja if j is not atacante and getattr(j, "posicion", "") in ("MED", "DEL")]
            cands = cands or [j for j in ja if j is not atacante and getattr(j, "posicion", "") != "POR"]
            asistente = random.choice(cands) if cands else None
        ev["asistente"] = asistente
        ev["asistente_id"] = getattr(asistente, "id", None)
        if asistente is not None:
            ev["detalle"] += f" (asist. {getattr(asistente, 'apellido', '')})"
    elif resultado == "tiro":
        portero = next((j for j in jd if getattr(j, "posicion", "") == "POR"), None)
        r = random.random()
        if portero is not None and r < PROB_ATAJADA:
            ev.update(tipo="atajada", jugador=portero, jugador_id=getattr(portero, "id", None),
                      atacante=atacante, equipo_id=eq_d.id, lado="v" if lado_a == "l" else "l")
            ev["detalle"] = random.choice(_ATAJADA).format(j=atacante.nombre_completo, d=portero.nombre_completo)
        elif r < PROB_ATAJADA + (1 - PROB_ATAJADA) * PROB_PALO:
            ev["tipo"] = "ocasion"
            ev["detalle"] = random.choice(_PALO).format(j=atacante.nombre_completo)
        else:
            ev["detalle"] = f"{nb} " + random.choice(_FALLO).format(j=atacante.nombre_completo)
    else:
        ev.update(tipo="defensa", jugador=defensor, jugador_id=getattr(defensor, "id", None),
                  atacante=atacante, equipo_id=eq_d.id, lado="v" if lado_a == "l" else "l")
        ev["detalle"] = f"{nb} " + _frase_defensa(defensor)
    if ctx is not None:
        _aplicar_evento(ctx, ev)
    return ev


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
    suerte_l:  float = 0.0,
    suerte_v:  float = 0.0,
    ment_l:    str = "normal",
    ment_v:    str = "normal",
    probs:     Optional[tuple] = None,
    ctx:       Any = None,
) -> tuple[int, int]:
    """
    Simula un minuto de partido.
    Ambos equipos pueden generar una oportunidad en el mismo minuto.
    v2.5.0: `ment_l`/`ment_v` = mentalidad ya resuelta de cada lado (ver EFECTO_MENTALIDAD).
    v4.0.0: con `ctx` (partido_ctx.EstadoPartido) juegan los que están en cancha; cada jugador
    que falte (expulsado / lesionado sin cambio) resta ataque y defensa; cada evento se aplica al ctx.
    Retorna (goles_local, goles_visitante) actualizados.
    """
    # v3.7.0: `probs` precalculadas por tramo (la posesión no cambia minuto a minuto; con
    # 16 ligas recalcularla 90 veces por partido era la mitad del tiempo de una jornada).
    prob_l, prob_v = probs if probs else _probs_ataque(local, visitante)
    silencio = True
    ef_l = EFECTO_MENTALIDAD.get(ment_l, EFECTO_MENTALIDAD["normal"])
    ef_v = EFECTO_MENTALIDAD.get(ment_v, EFECTO_MENTALIDAD["normal"])

    for es_local, eq_a, eq_d, prob, ma, md, ja, jd, suerte, ef_a in (
        (True,  local,    visitante, prob_l * ef_l["prob"], atk_l * ef_l["atk"], def_v * ef_v["def"],
         jug_l, jug_v, suerte_l - suerte_v * 0.5, ef_l),
        (False, visitante, local,   prob_v * ef_v["prob"], atk_v * ef_v["atk"], def_l * ef_l["def"],
         jug_v, jug_l, suerte_v - suerte_l * 0.5, ef_v),
    ):
        lado_a, lado_d = ('l', 'v') if es_local else ('v', 'l')
        if ctx is not None:   # v4.0.0
            ja, jd = ctx.en_cancha[lado_a], ctx.en_cancha[lado_d]
            if not ja or not jd:
                continue
            menos_a, menos_d = 11 - len(ja), 11 - len(jd)
            if menos_a > 0:
                prob *= 0.9 ** menos_a
                ma *= _MULT_EXPULSION ** menos_a
            if menos_d > 0:
                md *= _MULT_EXPULSION ** menos_d
        if minuto > 90:   # v4.4.0: en la adición todos van al ataque
            prob *= BONO_GOL_ADICION
        # v2.3.6: con 3+ goles de ventaja el que gana levanta el pie (goleadas de 7 raras).
        ventaja = (goles_l - goles_v) if es_local else (goles_v - goles_l)
        if ventaja >= 3:
            prob *= FRENO_GOLEADA ** (ventaja - 2)
        if random.random() > prob:
            continue
        silencio  = False
        # v0.8.1: 8% de probabilidad de que un defensa (DEF) sea el atacante en un gol
        # (cabezazo en un córner, jugada a balón parado). El 92% restante se fuerza
        # a MED/DEL, ya que el XI tiene 4 defensas y la selección natural daba 36% de
        # goles a defensas sin este control.
        # v2.5.0: el % de defensas depende de la mentalidad; en TODO O NADA ataca
        # cualquiera de los 10 de campo.
        atacante = None
        pct_def = ef_a["def_goleador"]
        try:
            if pct_def is None:
                campo = [j for j in ja if getattr(j, 'posicion', '') != 'POR']
                if campo:
                    atacante = random.choice(campo)
            elif random.random() < pct_def:
                # Probabilidad baja: que sea un defensa el que protagonice el ataque.
                defs = [j for j in ja if getattr(j, 'posicion', '') == 'DEF']
                if defs:
                    atacante = random.choice(defs)
        except Exception:
            pass
        if atacante is None:
            # Selección normal: priorizar MED/DEL (excluye POR y DEF, que no atacan en juego).
            try:
                no_atk = [j for j in ja if getattr(j, 'posicion', '') not in ('DEF', 'POR')]
                atacante = random.choice(no_atk) if no_atk else random.choice(ja)
            except Exception:
                atacante = random.choice(ja)
        defensor  = random.choice(jd)
        resultado = resolver_choque(
            atacante.poder_ataque_efectivo(ma),
            defensor.poder_defensa_efectivo(md),
            eq_a.estilo_dt,
            eq_d.estilo_dt,
            suerte,
        )
        if resultado == "gol":
            if es_local: goles_l += 1
            else:        goles_v += 1

        # Generar detalles del evento para match_screen.py
        try:
            if eventos_acumulados is not None:
                eventos_acumulados.append(_evento_jugada(minuto, resultado, eq_a, eq_d, atacante, defensor,
                                                         ja, jd, lado_a, ctx))
        except Exception as e_ev:
            logger.debug(f"procesar_minuto: no se pudo narrar la jugada: {e_ev}")

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
    ment_l: str = "ia",
    ment_v: str = "ia",
    aplicar_fisico: bool = True,
    ctx: Any = None,
    auto_l: bool = True,
    auto_v: bool = True,
    **kwargs
) -> Resultado:
    """
    Simula 90 minutos completos (más 3-10 de adición, v4.4.0) entre dos equipos.
    v2.5.0: `ment_l`/`ment_v` = mentalidad fija de cada lado o "ia" (la decide la IA).

    decision_mt puede contener claves 'atk_l', 'def_l', 'atk_v', 'def_v'
    como multiplicadores de la 2a mitad (decision de medio tiempo del jugador).
    """
    gl, gv = 0, 0
    # v3.1.0: el cierre físico cuenta minutos por id. v4.0.0: siempre (desarrollo y UI usan ids).
    from alpha_football.models import asegurar_ids_unicos
    asegurar_ids_unicos(local)
    asegurar_ids_unicos(visitante)
    # v0.8.1: solo los 11 titulares pueden participar (evita goles del banco).
    jl = _once_titular(local)
    jv = _once_titular(visitante)
    # v0.8.5: guard — si una plantilla queda vacía (datos corruptos / equipo sin jugadores),
    # devolvemos un marcador por defecto en vez de reventar con "list index out of range".
    # Tras el fix de copa los equipos siempre traen plantilla; esto es defensa en profundidad.
    if not jl or not jv:
        return Resultado(local.nombre, visitante.nombre, 0, 0, eventos=[])
    mt = decision_mt or {}
    eventos_partido = []
    if ctx is None:   # v4.0.0: estado vivo del partido (tarjetas, lesiones, cambios, notas)
        from alpha_football.partido_ctx import nuevo_estado
        ctx = nuevo_estado(local, visitante, jl, jv, auto_l, auto_v)
    # v0.7: sinergia formación/táctica/familiaridad sobre el ataque de cada equipo.
    syn_l = synergy_equipo(local)
    syn_v = synergy_equipo(visitante)
    suerte_l, suerte_v = sortear_suerte(local, visitante)

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

    d = _media_once(local) - _media_once(visitante) if "ia" in (ment_l, ment_v) else 0.0
    previas: dict = {}
    ctx.fin = 90 + random.randint(*ADICION)   # v4.4.0: minutos de adición
    for mitad, minutos in ((1, range(1, 46)), (2, range(46, ctx.fin + 1))):
        al = (mt.get("atk_l", 1.0) if mitad == 2 else 1.0) * syn_l
        dl = mt.get("def_l", 1.0) if mitad == 2 else 1.0
        av = (mt.get("atk_v", 1.0) if mitad == 2 else 1.0) * syn_v
        dv = mt.get("def_v", 1.0) if mitad == 2 else 1.0
        gl, gv = _simular_minutos(local, visitante, jl, jv, minutos, gl, gv, narrativa,
                                  al, dl, av, dv, eventos_partido, suerte_l, suerte_v,
                                  ment_l, ment_v, d, previas, ctx=ctx)

    for j in ctx.jugadores.values():
        j.energia_vivo = None
    from alpha_football.partido_ctx import notas_finales, minutos_por_id, incidencias_de
    if aplicar_fisico:   # v3.1.0: partidos de la IA (el user cierra su parte en vestuario)
        from alpha_football.energia import cerrar_partido
        cerrar_partido(local, minutos_por_id(ctx, 'l'), incidencias=incidencias_de(ctx, 'l'))
        cerrar_partido(visitante, minutos_por_id(ctx, 'v'), incidencias=incidencias_de(ctx, 'v'))
    return Resultado(local.nombre, visitante.nombre, gl, gv, eventos=eventos_partido,
                     ctx=ctx, notas=notas_finales(ctx, gl, gv))


def suplentes_disponibles(ctx, lado: str, equipo) -> list:
    """
    v4.0.0: quiénes pueden entrar: de la plantilla, fuera de cancha, que no hayan jugado ya este
    partido, sin lesión ni sanción. Si el equipo tiene convocados (banco del user), solo esos.
    """
    from alpha_football.partido_ctx import clave
    jugadores = list(getattr(equipo, "jugadores", []) or [])
    alin = getattr(equipo, "alineacion_activa", None)
    convocados = list(getattr(alin, "convocados", []) or []) if alin is not None else []
    base = [jugadores[i] for i in convocados if 0 <= i < len(jugadores)] if convocados else jugadores
    return [j for j in base
            if clave(j) not in ctx.entrada
            and getattr(j, "lesion_partidos", 0) == 0 and not _sancionado(j)]


def _energia_hoy(ctx, j, minuto: int) -> float:
    from alpha_football.energia import energia_en_minuto
    from alpha_football.partido_ctx import clave
    return energia_en_minuto(j, max(0, minuto - int(ctx.entrada.get(clave(j), 0))))


def elegir_cambio_ia(ctx, lado: str, equipo, minuto: int, sale=None) -> Optional[tuple]:
    """
    v4.0.0: (sale, entra) de un cambio de la IA. Sale el de campo más cansado (desempate: peor
    nota en vivo) o `sale` si ya viene dado; entra el mejor suplente de su puesto (o el mejor).
    """
    from alpha_football.partido_ctx import clave, nota_en_vivo
    if sale is None:
        campo = [j for j in ctx.en_cancha[lado] if getattr(j, "posicion", "") != "POR"]
        if not campo:
            return None
        sale = min(campo, key=lambda j: (_energia_hoy(ctx, j, minuto), nota_en_vivo(ctx, clave(j))))
    sups = suplentes_disponibles(ctx, lado, equipo)
    if not sups:
        return None
    mismo = [j for j in sups if getattr(j, "posicion", "") == getattr(sale, "posicion", "")] or sups
    return sale, max(mismo, key=lambda j: getattr(j, "overall", 0))


def evento_cambio(minuto: int, lado: str, equipo, sale, entra, ya_fuera: bool = False) -> dict:
    """v4.0.0: evento 'cambio' (entra por sale). `ya_fuera` = el que sale ya dejó la cancha (lesión)."""
    return {"minuto": minuto, "tipo": "cambio", "equipo_id": getattr(equipo, "id", None), "lado": lado,
            "jugador": entra, "jugador_id": getattr(entra, "id", None), "entra": entra,
            "sale": None if ya_fuera else sale, "sale_id": getattr(sale, "id", None), "sale_obj": sale,
            "detalle": random.choice(_CAMBIO).format(e=entra.nombre_completo, s=sale.nombre_completo)}


_FACTOR_LESION_MAX: float = 3.0   # energia.factor_lesion(0) con UMBRAL 60 (cota para el sorteo)
# v4.0.0: un solo sorteo por equipo y minuto; cada incidencia ocupa su tramo de [0, 1).
_C_AMARILLA = PROB_AMARILLA_MIN
_C_ROJA = _C_AMARILLA + PROB_ROJA_MIN
_C_LESION = _C_ROJA + PROB_LESION_90 / 90 * 11 * _FACTOR_LESION_MAX
_C_PENAL = _C_LESION + PROB_PENAL_FALLADO
_C_FALTA = _C_PENAL + PROB_FALTA_MIN


def _incidencias_minuto(m: int, local, visitante, ctx, eventos: list) -> None:
    """
    v4.0.0: tarjetas, lesiones, penales fallados, faltas y cambios de la IA de un minuto.
    Las lesiones y sanciones quedan en ctx.incidencias (se escriben en el jugador al cierre).
    Un solo número al azar por equipo decide si pasa algo (corre 180 veces por partido × 16 ligas).
    """
    def emitir(ev):
        eventos.append(ev)
        _aplicar_evento(ctx, ev)
        if ev["tipo"] == "cambio":   # el que entra juega con su energía de hoy
            ev["entra"].energia_vivo = float(getattr(ev["entra"], "energia", 100.0))

    for lado, eq in (("l", local), ("v", visitante)):
        cancha = ctx.en_cancha[lado]
        if not cancha:
            continue
        r = random.random()
        if r < _C_FALTA:
            base = {"minuto": m, "equipo_id": ctx.ids_equipo.get(lado), "lado": lado}
            campo = [j for j in cancha if getattr(j, "posicion", "") != "POR"] or cancha
            if r < _C_AMARILLA:
                j = random.choices(campo, weights=[2 if getattr(x, "posicion", "") in ("DEF", "MED") else 1
                                                   for x in campo])[0]
                emitir({**base, "tipo": "amarilla", "jugador": j, "jugador_id": j.id,
                        "detalle": random.choice(_AMARILLA).format(j=j.nombre_completo)})
                if ctx.amarillas.get(_clave(j), 0) >= 2:
                    emitir({**base, "tipo": "roja", "jugador": j, "jugador_id": j.id, "motivo": "doble amarilla",
                            "partidos": 1, "detalle": random.choice(_DOBLE_AMARILLA).format(j=j.nombre_completo)})
            elif r < _C_ROJA:
                j = random.choice(campo)
                emitir({**base, "tipo": "roja", "jugador": j, "jugador_id": j.id, "motivo": "directa",
                        "partidos": 2 if random.random() < 0.2 else 1,
                        "detalle": random.choice(_ROJA).format(j=j.nombre_completo)})
            elif r < _C_LESION:
                # se acepta según la energía media (más cansados, más lesiones) y los que quedan
                energias = [(j.energia_vivo if j.energia_vivo is not None else j.energia) for j in cancha]
                acepta = factor_lesion(sum(energias) / len(energias)) / _FACTOR_LESION_MAX * len(cancha) / 11
                if random.random() < acepta:
                    j = random.choices(cancha, weights=[factor_lesion(e) for e in energias])[0]
                    emitir({**base, "tipo": "lesion", "jugador": j, "jugador_id": j.id,
                            "partidos": random.choices(DURACION_LESION, weights=PESOS_LESION)[0],
                            "detalle": random.choice(_LESION).format(j=j.nombre_completo)})
                    if ctx.auto_cambios.get(lado) and ctx.cambios.get(lado, 0) < _MAX_CAMBIOS:
                        par = elegir_cambio_ia(ctx, lado, eq, m, sale=j)
                        if par:
                            emitir(evento_cambio(m, lado, eq, par[0], par[1], ya_fuera=True))
            elif r < _C_PENAL:
                # los penales convertidos salen de los goles normales (ver _evento_jugada)
                j = max(cancha, key=lambda x: getattr(x, "penales", 0) or 0)
                emitir({**base, "tipo": "penal_fallado", "jugador": j, "jugador_id": j.id,
                        "detalle": random.choice(_PENAL_FALLO).format(j=j.nombre_completo, eq=eq.nombre)})
            else:   # falta peligrosa: solo comentario
                j = random.choice(cancha)
                eventos.append({**base, "tipo": "falta", "jugador": j, "jugador_id": j.id,
                                "detalle": random.choice(_FALTA).format(j=j.nombre_completo)})
        # Cambios de la IA por cansancio
        if (MINUTO_CAMBIOS_IA[0] <= m <= MINUTO_CAMBIOS_IA[1] and ctx.auto_cambios.get(lado)
                and random.random() < PROB_CAMBIO_IA_MIN):
            objetivo = ctx.objetivo_cambios.setdefault(lado, random.randint(3, 5))
            if ctx.cambios.get(lado, 0) < min(objetivo, _MAX_CAMBIOS):
                par = elegir_cambio_ia(ctx, lado, eq, m)
                if par:
                    emitir(evento_cambio(m, lado, eq, par[0], par[1]))


def _simular_minutos(local, visitante, jl, jv, minutos, gl, gv, narrativa, al, dl, av, dv,
                     eventos, suerte_l, suerte_v, ment_l, ment_v, d, previas,
                     minutos_previos: Optional[dict] = None, ctx: Any = None) -> tuple[int, int]:
    """
    v4.0.0: con `ctx` juegan los de ctx.en_cancha y hay incidencias (tarjetas, lesiones, cambios).
    v2.5.0: simula un tramo de minutos resolviendo la mentalidad de cada lado. Un lado en
    'ia' la recalcula cada minuto con el marcador; cada cambio queda como evento
    'mentalidad' (el valor inicial no). `previas` guarda la última de cada lado entre tramos.
    v3.1.0: `minutos_previos` = {id(jugador): minutos ya jugados}; por defecto, desde el 1'.
    """
    # v3.1.0: cada jugador juega el tramo con la energía que tiene al empezarlo.
    from alpha_football.energia import energia_en_minuto
    from alpha_football.estilos import factor_gasto_estilo
    primer = minutos[0] if len(minutos) else 1
    if ctx is not None:
        jl, jv = ctx.en_cancha['l'], ctx.en_cancha['v']
    # v3.3.0: el gasto depende del estilo de cada equipo (Kloppismo gasta más).
    for eq_j, lista_j in ((local, jl), (visitante, jv)):
        mult = factor_gasto_estilo(getattr(eq_j, 'estilo_dt', ''))
        for j in list(lista_j):
            # un suplente que entró en el partido gasta desde su minuto de entrada, no desde el 1'
            entro = int(ctx.entrada.get(id(j), 0) or 0) if ctx is not None else 0
            prev = (minutos_previos or {}).get(id(j), max(0, primer - 1 - entro))
            j.energia_vivo = energia_en_minuto(j, prev, mult)
    probs = _probs_ataque(local, visitante)   # v3.7.0: una vez por tramo
    for m in minutos:
        ml = (_decidir_mentalidad(d, m, gl, gv, True) if ment_l == "ia"
              else normalizar_mentalidad(ment_l))
        mv = (_decidir_mentalidad(-d, m, gv, gl, False) if ment_v == "ia"
              else normalizar_mentalidad(ment_v))
        for lado, eq, mm in (("l", local, ml), ("v", visitante, mv)):
            if lado in previas and previas[lado] != mm and eventos is not None:
                eventos.append({
                    "minuto": m, "tipo": "mentalidad", "equipo_id": getattr(eq, "id", None),
                    "mentalidad": mm,
                    "detalle": f"{getattr(eq, 'nombre', 'Equipo')} pasa a {NOMBRE_MENTALIDAD[mm]}",
                })
            previas[lado] = mm
        gl, gv = procesar_minuto(
            m, local, visitante, jl, jv, gl, gv, narrativa, al, dl, av, dv,
            eventos_acumulados=eventos, suerte_l=suerte_l, suerte_v=suerte_v,
            ment_l=ml, ment_v=mv, probs=probs, ctx=ctx,
        )
        if ctx is not None and eventos is not None:
            _incidencias_minuto(m, local, visitante, ctx, eventos)
    return gl, gv


def simular_rango(
    local:     Equipo,
    visitante: Equipo,
    min_inicio: int,
    min_fin:    int,
    mult:       Optional[dict] = None,
    eventos:    Optional[list] = None,
    goles_previos: tuple = (0, 0),
    ment_l:     str = "ia",
    ment_v:     str = "ia",
    minutos_previos: Optional[dict] = None,
    ctx:        Any = None,
) -> tuple[int, int, list]:
    """
    v4.0.0: `ctx` (partido_ctx.EstadoPartido) se MUTA con lo que pase en el tramo; quien quiera
    conservar el suyo pasa `ctx.copia()`. El lado del user (auto_cambios False) se resincroniza
    con su alineación (cambios hechos en el menú táctico). Sin ctx se crea uno interno.

    Simula SOLO los minutos [min_inicio, min_fin] (inclusive) entre dos equipos.

    Permite al frontend simular una mitad a la vez: la decisión de medio tiempo
    (multiplicadores atk_l/def_l/atk_v/def_v en `mult`) afecta de verdad la 2ª mitad,
    porque esos minutos se simulan DESPUÉS de elegir la charla. Reutiliza procesar_minuto.

    v2.3.6: `goles_previos` = marcador antes del tramo (para el freno a las goleadas) y
    `mult` puede traer 'suerte_l'/'suerte_v' (la suerte sorteada al inicio del partido,
    para que no cambie entre mitades). Sin ellas se sortea una nueva.

    Retorna (goles_local_del_rango, goles_visitante_del_rango, eventos_acumulados).
    """
    m = mult or {}
    # v0.7: la sinergia (formación/táctica/familiaridad) también afecta tramos sueltos.
    al = float(m.get("atk_l", 1.0)) * synergy_equipo(local)
    dl = float(m.get("def_l", 1.0))
    av = float(m.get("atk_v", 1.0)) * synergy_equipo(visitante)
    dv = float(m.get("def_v", 1.0))
    # v0.8.1: solo los 11 titulares.
    jl = _once_titular(local)
    jv = _once_titular(visitante)
    ev = eventos if eventos is not None else []
    # v0.8.5: guard de plantilla vacía (ver simular_partido) para no romper el motor.
    if not jl or not jv:
        return 0, 0, ev
    from alpha_football import partido_ctx as _pc
    if ctx is None:
        ctx = _pc.nuevo_estado(local, visitante, jl, jv)
    else:
        for lado, eq in (('l', local), ('v', visitante)):
            if not ctx.auto_cambios.get(lado, True):
                _pc.resincronizar_user(ctx, lado, _once_titular(eq), int(min_inicio) - 1)
    if 'suerte_l' in m and 'suerte_v' in m:
        sl, sv = float(m['suerte_l']), float(m['suerte_v'])
    else:
        sl, sv = sortear_suerte(local, visitante)
    gl0, gv0 = int(goles_previos[0]), int(goles_previos[1])
    # v2.5.0: mentalidad. La del inicio del tramo es la que decidiría la IA en el minuto
    # anterior, así un cambio en el primer minuto del tramo también genera evento.
    d = _media_once(local) - _media_once(visitante) if "ia" in (ment_l, ment_v) else 0.0
    previas: dict = {}
    if int(min_inicio) > 1:
        m0 = int(min_inicio) - 1
        previas["l"] = (_decidir_mentalidad(d, m0, gl0, gv0, True) if ment_l == "ia"
                        else normalizar_mentalidad(ment_l))
        previas["v"] = (_decidir_mentalidad(-d, m0, gv0, gl0, False) if ment_v == "ia"
                        else normalizar_mentalidad(ment_v))
    gl, gv = _simular_minutos(local, visitante, jl, jv, range(int(min_inicio), int(min_fin) + 1),
                              gl0, gv0, False, al, dl, av, dv, ev, sl, sv, ment_l, ment_v, d, previas,
                              minutos_previos, ctx=ctx)
    for j in list(jl) + list(jv) + list(ctx.jugadores.values()):
        j.energia_vivo = None
    return gl - gl0, gv - gv0, ev


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
