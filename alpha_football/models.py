# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — MODELOS Y CONTRATO DE DATOS.

Este módulo define las estructuras de datos (dataclasses) del juego: Jugador, Equipo,
Liga, Resultado, Standing y el EstadoJuego raíz.
Incluye lógica de serialización y deserialización tolerante a fallos para dar soporte
a versiones anteriores del guardado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

# Configuración del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Versión del esquema de datos
SCHEMA_VERSION = 5

# Enums de navegación y UI
class Pantalla(str, Enum):
    MENU = "menu"
    SELECCION_LIGA = "seleccion_liga"
    SELECCION_EQUIPO = "seleccion_equipo"
    TEMPORADA = "temporada"
    PARTIDO = "partido"
    MERCADO = "mercado"
    COPA = "copa"
    CAREER = "career"  # Historial de carrera

@dataclass
class Jugador:
    """
    Representa un futbolista de parodia con sus 5 atributos principales
    y sus rasgos/moral correspondientes.
    """
    nombre: str
    apellido: str
    posicion: str  # POR, DEF, MED, DEL
    ataque: int
    defensa: int
    fisico: int
    tecnica: int
    mental: int
    moral: int = 70
    rasgo: Optional[str] = None
    lesion_partidos: int = 0
    id: int = 0                  # Identificador para mercado/guardado
    partidos_sancion: int = 0
    goles: int = 0
    # --- Fase 3: desarrollo dinámico y valor de mercado ---
    asistencias: int = 0
    partidos_jugados: int = 0
    promedio_nota: float = 0.0
    progreso_desarrollo: float = 0.0   # acumulador oculto; al llegar a 1.0 sube OVR
    valor: int = 0                     # valor de mercado recalculado tras cada partido
    edad: int = 25
    # v0.8.x: techo de OVR del jugador ("potencial final"). Si 0 = "aún sin calcular"
    # (se deriva perezosamente con `desarrollo.calcular_potencial` cuando hace falta).
    # El desarrollo por partido y el pasivo por temporada NUNCA dejan que el OVR lo supere.
    potencial: int = 0
    # --- v0.7: atributo de penales y estadística de vallas invictas ---
    penales: int = 0                   # habilidad para cobrar penales (0 = derivar de tecnica/mental)
    porterias_cero: int = 0            # vallas invictas (clean sheets) para la tabla de porteros

    def __post_init__(self):
        # Si no se especificó el atributo de penales, derivarlo de técnica/mental (cubre
        # TODOS los sitios de creación: data/*, plantilla, free_agents, internacional...).
        try:
            if not self.penales:
                self.penales = (int(self.tecnica) + int(self.mental)) // 2
        except Exception:
            self.penales = 60

    @property
    def overall(self) -> int:
        """Promedio simple de los 5 atributos de habilidad."""
        try:
            return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5
        except Exception as e:
            logger.error(f"Error al calcular overall: {e}. Retornando 50 por defecto.")
            return 50

    @property
    def nombre_completo(self) -> str:
        """Nombre y apellido juntos."""
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def disponible(self) -> bool:
        """Indica si el jugador puede ser alineado en el partido."""
        return self.lesion_partidos == 0 and self.partidos_sancion <= 0

    def poder_ataque_efectivo(self, mult: float = 1.0) -> float:
        """Calcula la efectividad ofensiva modificada por moral y rasgos."""
        try:
            base = (self.ataque + self.tecnica * 0.5 + self.fisico * 0.3) * (self.moral / 70.0)
            if self.rasgo == "regateador":
                base *= 1.15
            elif self.rasgo == "pulmon_de_hierro":
                base *= 1.05
            return max(1.0, base * mult)
        except Exception as e:
            logger.error(f"Error al calcular poder de ataque efectivo: {e}")
            return float(self.ataque)

    def poder_defensa_efectivo(self, mult: float = 1.0) -> float:
        """Calcula la efectividad defensiva modificada por moral y rasgos."""
        try:
            base = (self.defensa + self.fisico * 0.5 + self.mental * 0.3) * (self.moral / 70.0)
            if self.rasgo == "rustico":
                base *= 1.20
            elif self.rasgo == "lider":
                base *= 1.08
            return max(1.0, base * mult)
        except Exception as e:
            logger.error(f"Error al calcular poder de defensa efectivo: {e}")
            return float(self.defensa)

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario plano para JSON."""
        # v0.8.1: 'overall' es @property (calculado de los 5 atributos), así que
        # asdict() no lo incluye. Lo añadimos explícitamente para que el editor
        # y otros consumidores lo lean bien sin tener que recalcular.
        d = asdict(self)
        try:
            d["overall"] = self.overall
        except Exception:
            d["overall"] = 50
        return d

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Jugador":
        """Deserializa de forma tolerante a fallos y compatible con versiones viejas."""
        try:
            nombre = str(datos.get("nombre", "Jugador"))
            
            # Soporte si no había apellido separado
            if "apellido" in datos:
                apellido = str(datos["apellido"])
            else:
                partes = nombre.split(" ", 1)
                nombre = partes[0]
                apellido = partes[1] if len(partes) > 1 else "Parodia"

            posicion = str(datos.get("posicion", "MED"))
            
            # Carga compatible de atributos de habilidades o general
            if "ataque" in datos:
                ataque = int(datos["ataque"])
                defensa = int(datos["defensa"])
                fisico = int(datos["fisico"])
                tecnica = int(datos["tecnica"])
                mental = int(datos["mental"])
            else:
                nivel = int(datos.get("nivel", datos.get("overall", 60)))
                ataque = defensa = fisico = tecnica = mental = nivel

            moral = int(datos.get("moral", 70))
            rasgo = datos.get("rasgo")
            
            # Manejo de lesiones y sanciones
            lesion_partidos = int(datos.get("lesion_partidos", 0))
            if lesion_partidos == 0 and datos.get("lesionado", False):
                lesion_partidos = 3
                
            partidos_sancion = int(datos.get("partidos_sancion", 0))
            goles = int(datos.get("goles", 0))
            # Fase 3: campos de desarrollo y valor (tolerantes con saves viejos)
            asistencias = int(datos.get("asistencias", 0))
            partidos_jugados = int(datos.get("partidos_jugados", 0))
            promedio_nota = float(datos.get("promedio_nota", 0.0))
            progreso_desarrollo = float(datos.get("progreso_desarrollo", 0.0))
            valor = int(datos.get("valor", 0))
            edad = int(datos.get("edad", 25))
            # v0.8.x: potencial (techo de OVR). 0 = "sin calcular" → se derivará perezoso
            # en `asignar_valores_iniciales` o al aplicar el primer desarrollo. Tolerante:
            # saves viejos sin la clave cargan con 0 sin romper.
            potencial = int(datos.get("potencial", 0))
            # v0.7: penales (si falta, se deriva de técnica/mental) y vallas invictas.
            penales = int(datos.get("penales", 0)) or ((tecnica + mental) // 2)
            porterias_cero = int(datos.get("porterias_cero", 0))
            import random
            id_jug = int(datos.get("id", random.randint(1000, 9999) if "id" not in datos else datos["id"]))

            return cls(
                nombre=nombre,
                apellido=apellido,
                posicion=posicion,
                ataque=ataque,
                defensa=defensa,
                fisico=fisico,
                tecnica=tecnica,
                mental=mental,
                moral=moral,
                rasgo=rasgo,
                lesion_partidos=lesion_partidos,
                id=id_jug,
                partidos_sancion=partidos_sancion,
                goles=goles,
                asistencias=asistencias,
                partidos_jugados=partidos_jugados,
                promedio_nota=promedio_nota,
                progreso_desarrollo=progreso_desarrollo,
                valor=valor,
                edad=edad,
                penales=penales,
                porterias_cero=porterias_cero,
                potencial=potencial
            )
        except Exception as e:
            logger.warning(f"Excepción al reconstruir Jugador: {e}. Usando fallback.")
            return cls("Jugador", "Desconocido", "MED", 60, 60, 60, 60, 60)

@dataclass
class Equipo:
    """
    Representa un club de fútbol, su presupuesto, su estilo de juego,
    la lista de jugadores y estadísticas en la liga.
    """
    nombre: str
    ciudad: str
    estrellas: float
    estilo_dt: str
    balance: int
    jugadores: list[Jugador] = field(default_factory=list)
    es_usuario: bool = False
    # v0.7: nombre corto (anti-solapamiento en menús) y familiaridad táctica acumulada.
    nombre_corto: str = ""
    tactica_familiaridad: dict[str, float] = field(default_factory=dict)

    # Estadísticas de liga acumuladas
    puntos: int = 0
    pj: int = 0
    pg: int = 0
    pe: int = 0
    pp: int = 0
    gf: int = 0
    gc: int = 0

    @property
    def id(self) -> str:
        """Genera un identificador único estable a partir de su nombre."""
        return self.nombre.lower().replace(" ", "_")

    @property
    def corto(self) -> str:
        """Nombre corto para menús; si no se definió, recorta el nombre largo."""
        if self.nombre_corto:
            return self.nombre_corto
        return self.nombre[:14]

    @property
    def once_disponible(self) -> list[Jugador]:
        """Retorna los jugadores habilitados (sin lesiones)."""
        disponibles = [j for j in self.jugadores if j.disponible]
        return disponibles if disponibles else self.jugadores

    @property
    def ovr_promedio(self) -> int:
        """Promedio overall de los jugadores del club."""
        if not self.jugadores:
            return 0
        return sum(j.overall for j in self.jugadores) // len(self.jugadores)

    @property
    def jugador_estrella(self) -> Jugador:
        """El jugador con mayor overall."""
        if not self.jugadores:
            raise ValueError("El equipo no tiene jugadores.")
        return max(self.jugadores, key=lambda j: j.overall)

    def promedio_ataque(self, mult: float = 1.0) -> float:
        """Promedio de poder ofensivo efectivo de los alineados."""
        disponibles = self.once_disponible
        if not disponibles:
            return 0.0
        return sum(j.poder_ataque_efectivo(mult) for j in disponibles) / len(disponibles)

    def promedio_defensa(self, mult: float = 1.0) -> float:
        """Promedio de poder defensivo efectivo de los alineados."""
        disponibles = self.once_disponible
        if not disponibles:
            return 0.0
        return sum(j.poder_defensa_efectivo(mult) for j in disponibles) / len(disponibles)

    def promedio_tecnica_mental(self) -> float:
        """Promedio de técnica y mentalidad combinadas (usado para posesión)."""
        disponibles = self.once_disponible
        if not disponibles:
            return 0.0
        return sum((j.tecnica + j.mental) / 2.0 for j in disponibles) / len(disponibles)

    def tick_lesiones(self):
        """Disminuye en 1 jornada el contador de lesiones de los jugadores."""
        for j in self.jugadores:
            if j.lesion_partidos > 0:
                j.lesion_partidos -= 1

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        datos = asdict(self)
        datos["jugadores"] = [j.to_dict() for j in self.jugadores]
        return datos

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Equipo":
        """Deserializa tolerando campos ausentes."""
        try:
            jugadores_datos = datos.get("jugadores", [])
            jugadores = [Jugador.from_dict(j) for j in jugadores_datos]
            
            # Soporte de mapeo balance vs presupuesto (esquema Claude millones vs enteros)
            balance = int(datos.get("balance", datos.get("presupuesto", 10.0) * 1_000_000))
            if balance < 1000: # Claude usaba presupuestos como 50 (millones)
                balance = int(balance * 1_000_000)

            return cls(
                nombre=str(datos.get("nombre", "Equipo")),
                ciudad=str(datos.get("ciudad", "Ciudad")),
                estrellas=float(datos.get("estrellas", 3.0)),
                estilo_dt=str(datos.get("estilo_dt", "cruyffismo")),
                balance=balance,
                jugadores=jugadores,
                es_usuario=bool(datos.get("es_usuario", False)),
                nombre_corto=str(datos.get("nombre_corto", "")),
                tactica_familiaridad=dict(datos.get("tactica_familiaridad", {}) or {}),
                puntos=int(datos.get("puntos", 0)),
                pj=int(datos.get("pj", 0)),
                pg=int(datos.get("pg", 0)),
                pe=int(datos.get("pe", 0)),
                pp=int(datos.get("pp", 0)),
                gf=int(datos.get("gf", 0)),
                gc=int(datos.get("gc", 0))
            )
        except Exception as e:
            logger.error(f"Error al reconstruir Equipo: {e}")
            return cls("Equipo Ficticio", "Ciudad", 3.0, "cruyffismo", 5_000_000, [])

@dataclass
class Resultado:
    """Representa el marcador de un partido finalizado."""
    equipo_local: str
    equipo_visitante: str
    goles_local: int
    goles_visitante: int
    penales: Optional[str] = None
    ganador: Optional[str] = None

@dataclass
class Standing:
    """Una entrada en la tabla de clasificaciones de la liga."""
    equipo: Equipo
    pj: int = 0
    g: int = 0
    e: int = 0
    p: int = 0
    gf: int = 0
    gc: int = 0
    pts: int = 0

    @property
    def dg(self) -> int:
        """Diferencia de goles."""
        return self.gf - self.gc

@dataclass
class Partido:
    """Un partido agendado en el fixture de liga o copa."""
    local_id: str
    visitante_id: str
    jornada: int = 0
    goles_local: Optional[int] = None
    goles_visitante: Optional[int] = None
    penales: Optional[str] = None
    jugado: bool = False
    ganador_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Partido":
        return cls(
            local_id=str(datos["local_id"]),
            visitante_id=str(datos["visitante_id"]),
            jornada=int(datos.get("jornada", 0)),
            goles_local=datos.get("goles_local"),
            goles_visitante=datos.get("goles_visitante"),
            penales=datos.get("penales"),
            jugado=bool(datos.get("jugado", False)),
            ganador_id=datos.get("ganador_id")
        )

@dataclass
class Liga:
    """Representa una liga nacional en el sistema multi-liga."""
    nombre: str
    tipo: str  # betplay, laliga, premier, brasil, argentina
    equipos: list[Equipo]
    num_jornadas: int
    calendario: list[Partido] = field(default_factory=list)
    jornada_actual: int = 1

    def to_dict(self) -> dict[str, Any]:
        datos = asdict(self)
        datos["equipos"] = [e.to_dict() for e in self.equipos]
        datos["calendario"] = [p.to_dict() for p in self.calendario]
        return datos

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Liga":
        try:
            equipos = [Equipo.from_dict(e) for e in datos.get("equipos", [])]
            calendario = [Partido.from_dict(p) for p in datos.get("calendario", [])]
            return cls(
                nombre=str(datos.get("nombre", "Liga")),
                tipo=str(datos.get("tipo", "betplay")),
                equipos=equipos,
                num_jornadas=int(datos.get("num_jornadas", 14)),
                calendario=calendario,
                jornada_actual=int(datos.get("jornada_actual", 1))
            )
        except Exception as e:
            logger.error(f"Error al reconstruir Liga: {e}")
            return cls("Liga", "betplay", [], 14)

@dataclass
class Copa:
    """Almacena el estado de un torneo internacional de copa."""
    tipo: str  # libertadores, champions
    nombre: str
    fase: str = "grupos"  # grupos, octavos, cuartos, semifinal, final, terminada
    equipos_ids: list[str] = field(default_factory=list)
    partidos: list[Partido] = field(default_factory=list)
    campeon_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        datos = asdict(self)
        datos["partidos"] = [p.to_dict() for p in self.partidos]
        return datos

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Copa":
        partidos = [Partido.from_dict(p) for p in datos.get("partidos", [])]
        return cls(
            tipo=str(datos.get("tipo", "libertadores")),
            nombre=str(datos.get("nombre", "Copa")),
            fase=str(datos.get("fase", "grupos")),
            equipos_ids=list(datos.get("equipos_ids", [])),
            partidos=partidos,
            campeon_id=datos.get("campeon_id")
        )

@dataclass
class OfertaMercado:
    """Una oferta de transferencia activa."""
    jugador_id: int
    equipo_origen_id: str
    equipo_destino_id: str
    monto: int
    aceptada: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "OfertaMercado":
        return cls(
            jugador_id=int(datos["jugador_id"]),
            equipo_origen_id=str(datos["equipo_origen_id"]),
            equipo_destino_id=str(datos["equipo_destino_id"]),
            monto=int(datos["monto"]),
            aceptada=datos.get("aceptada")
        )

@dataclass
class EventoCaotico:
    """Guarda un evento caótico aleatorio que afecta la partida."""
    tipo: str
    titulo: str
    descripcion: str
    equipo_id: Optional[str] = None
    jugador_id: Optional[int] = None
    efecto: dict[str, Any] = field(default_factory=dict)
    resuelto: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "EventoCaotico":
        return cls(
            tipo=str(datos.get("tipo", "clima")),
            titulo=str(datos.get("titulo", "Evento")),
            descripcion=str(datos.get("descripcion", "")),
            equipo_id=datos.get("equipo_id"),
            jugador_id=datos.get("jugador_id"),
            efecto=dict(datos.get("efecto", {})),
            resuelto=bool(datos.get("resuelto", False))
        )

@dataclass
class ConfigAudio:
    """Configuración persistente de sonido."""
    activado: bool = True
    volumen: float = 0.5

@dataclass
class EstadoJuego:
    """
    Estado raíz persistente del juego. Almacena ligas, copas,
    la carrera del usuario y configuración de audio.
    """
    ligas: list[Liga] = field(default_factory=list)
    copas: list[Copa] = field(default_factory=list)
    equipo_usuario_id: Optional[str] = None
    liga_usuario_id: Optional[str] = None
    temporada: int = 1
    mercado: list[OfertaMercado] = field(default_factory=list)
    eventos_pendientes: list[EventoCaotico] = field(default_factory=list)
    audio: ConfigAudio = field(default_factory=ConfigAudio)
    pantalla_actual: Pantalla = Pantalla.MENU
    
    # Historial de campañas pasadas para career_screen
    historial: list[dict[str, Any]] = field(default_factory=list)
    
    # Historial de transferencias realizadas (registro de mercado)
    transfer_log: list[str] = field(default_factory=list)
    
    # Alineación activa elegida por el usuario
    alineacion_activa: Optional[Alineacion] = None

    # v0.7: identidad del director técnico elegida al iniciar carrera
    dt_nombre: str = ""
    dt_nacionalidad: str = ""

    # Persistencia de copa internacional
    copa_tipo: Optional[str] = None
    copa_fase_actual: Optional[str] = None
    copa_grupo_standing: list[Any] = field(default_factory=list)
    copa_bracket: dict[str, Any] = field(default_factory=dict)
    copa_grupo_partidos: list[dict[str, Any]] = field(default_factory=list)
    copa_jornada_grupo: int = 1
    copa_tab: Optional[str] = None
    copa_grupos: dict[str, list[str]] = field(default_factory=dict)
    copa_grupos_standings: dict[str, list[Any]] = field(default_factory=dict)
    copa_bracket_otros: dict[str, Any] = field(default_factory=dict)

    # v0.8.7.5: estado de clasificación del usuario a la copa internacional.
    # Persistirlos evita que, tras un save/load, el historial muestre "Fase de grupos"
    # en lugar de "No clasificado" cuando el usuario no clasificó: el flag se perdía y
    # `copa_user_en_copa` caía al default True en el resumen de temporada.
    copa_clasificado: Optional[bool] = None
    copa_user_en_copa: Optional[bool] = None
    copa_clasificado_motivo: str = ""
    copa_mejor_fase_temp: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        try:
            alin_dict = None
            if self.alineacion_activa:
                alin_dict = {
                    "titulares": list(self.alineacion_activa.titulares),
                    "formacion": str(self.alineacion_activa.formacion)
                }
        except Exception as e_alin:
            logger.error(f"Error al serializar alineación activa: {e_alin}. Ignorando alineación.")
            alin_dict = None

        # Serializar standings de copa convirtiendo objetos Standing a diccionarios
        standings_dict = []
        for st in self.copa_grupo_standing:
            if hasattr(st, 'equipo'):
                standings_dict.append({
                    "equipo": st.equipo,
                    "pj": st.pj,
                    "g": st.g,
                    "e": st.e,
                    "p": st.p,
                    "gf": st.gf,
                    "gc": st.gc,
                    "pts": st.pts
                })
            else:
                standings_dict.append(dict(st))

        # Serializar copa_grupos_standings
        grupos_standings_dict = {}
        for g_name, st_list in self.copa_grupos_standings.items():
            g_list = []
            for st in st_list:
                if hasattr(st, 'equipo'):
                    g_list.append({
                        "equipo": st.equipo,
                        "pj": st.pj,
                        "g": st.g,
                        "e": st.e,
                        "p": st.p,
                        "gf": st.gf,
                        "gc": st.gc,
                        "pts": st.pts
                    })
                else:
                    g_list.append(dict(st))
            grupos_standings_dict[g_name] = g_list

        return {
            "ligas": [l.to_dict() for l in self.ligas],
            "copas": [c.to_dict() for c in self.copas],
            "equipo_usuario_id": self.equipo_usuario_id,
            "liga_usuario_id": self.liga_usuario_id,
            "temporada": self.temporada,
            "mercado": [o.to_dict() for o in self.mercado],
            "eventos_pendientes": [e.to_dict() for e in self.eventos_pendientes],
            "audio": asdict(self.audio),
            "pantalla_actual": self.pantalla_actual.value,
            "historial": list(self.historial),
            "transfer_log": list(self.transfer_log),
            "alineacion_activa": alin_dict,
            "dt_nombre": self.dt_nombre,
            "dt_nacionalidad": self.dt_nacionalidad,
            "copa_tipo": self.copa_tipo,
            "copa_fase_actual": self.copa_fase_actual,
            "copa_grupo_standing": standings_dict,
            "copa_bracket": self.copa_bracket,
            "copa_grupo_partidos": self.copa_grupo_partidos,
            "copa_jornada_grupo": self.copa_jornada_grupo,
            "copa_tab": self.copa_tab,
            "copa_grupos": self.copa_grupos,
            "copa_grupos_standings": grupos_standings_dict,
            "copa_bracket_otros": self.copa_bracket_otros,
            "copa_clasificado": self.copa_clasificado,
            "copa_user_en_copa": self.copa_user_en_copa,
            "copa_clasificado_motivo": self.copa_clasificado_motivo,
            "copa_mejor_fase_temp": self.copa_mejor_fase_temp
        }

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "EstadoJuego":
        try:
            ligas = [Liga.from_dict(l) for l in datos.get("ligas", [])]
            copas = [Copa.from_dict(c) for c in datos.get("copas", [])]
            
            audio_datos = datos.get("audio", {})
            audio = ConfigAudio(
                activado=bool(audio_datos.get("activado", True)),
                volumen=float(audio_datos.get("volumen", 0.5))
            )
            
            pantalla_str = datos.get("pantalla_actual", Pantalla.MENU.value)
            try:
                pantalla = Pantalla(pantalla_str)
            except ValueError:
                pantalla = Pantalla.MENU

            # Cargar alineación activa con fallback tolerante si falla
            alineacion_activa = None
            try:
                alin_datos = datos.get("alineacion_activa")
                if alin_datos:
                    alineacion_activa = Alineacion(
                        titulares=list(alin_datos.get("titulares", [])),
                        formacion=str(alin_datos.get("formacion", "4-3-3"))
                    )
            except Exception as e_alin_load:
                logger.error(f"Error recuperable al cargar alineación activa: {e_alin_load}. Usando alineación nula.")
                alineacion_activa = None

            # Cargar historial y transfer_log con retrocompatibilidad
            hist_cargado = datos.get("historial", [])
            trans_cargado = datos.get("transfer_log", [])
            
            # Si transfer_log está vacío pero el historial tiene strings (debido al bug anterior),
            # movemos esos strings al transfer_log y limpiamos historial.
            if hist_cargado and not trans_cargado:
                if any(isinstance(x, str) for x in hist_cargado):
                    trans_cargado = [x for x in hist_cargado if isinstance(x, str)]
                    hist_cargado = [x for x in hist_cargado if isinstance(x, dict)]

            # Reconstruir Standing de copa
            copa_grupo_standing = []
            for st in datos.get("copa_grupo_standing", []):
                try:
                    from alpha_football.models import Standing
                    copa_grupo_standing.append(Standing(
                        equipo=st.get("equipo", ""),
                        pj=int(st.get("pj", 0)),
                        g=int(st.get("g", 0)),
                        e=int(st.get("e", 0)),
                        p=int(st.get("p", 0)),
                        gf=int(st.get("gf", 0)),
                        gc=int(st.get("gc", 0)),
                        pts=int(st.get("pts", 0))
                    ))
                except Exception:
                    copa_grupo_standing.append(st)

            # Reconstruir copa_grupos_standings
            copa_grupos_standings = {}
            for g_name, st_list in datos.get("copa_grupos_standings", {}).items():
                g_list = []
                for st in st_list:
                    try:
                        from alpha_football.models import Standing
                        g_list.append(Standing(
                            equipo=st.get("equipo", ""),
                            pj=int(st.get("pj", 0)),
                            g=int(st.get("g", 0)),
                            e=int(st.get("e", 0)),
                            p=int(st.get("p", 0)),
                            gf=int(st.get("gf", 0)),
                            gc=int(st.get("gc", 0)),
                            pts=int(st.get("pts", 0))
                        ))
                    except Exception:
                        g_list.append(st)
                copa_grupos_standings[g_name] = g_list

            return cls(
                ligas=ligas,
                copas=copas,
                equipo_usuario_id=datos.get("equipo_usuario_id"),
                liga_usuario_id=datos.get("liga_usuario_id"),
                temporada=int(datos.get("temporada", 1)),
                mercado=[OfertaMercado.from_dict(o) for o in datos.get("mercado", [])],
                eventos_pendientes=[EventoCaotico.from_dict(e) for e in datos.get("eventos_pendientes", [])],
                audio=audio,
                pantalla_actual=pantalla,
                historial=list(hist_cargado),
                transfer_log=list(trans_cargado),
                alineacion_activa=alineacion_activa,
                dt_nombre=str(datos.get("dt_nombre", "")),
                dt_nacionalidad=str(datos.get("dt_nacionalidad", "")),
                copa_tipo=datos.get("copa_tipo"),
                copa_fase_actual=datos.get("copa_fase_actual"),
                copa_grupo_standing=copa_grupo_standing,
                copa_bracket=datos.get("copa_bracket", {}),
                copa_grupo_partidos=datos.get("copa_grupo_partidos", []),
                copa_jornada_grupo=int(datos.get("copa_jornada_grupo", 1)),
                copa_tab=datos.get("copa_tab"),
                copa_grupos=datos.get("copa_grupos", {}),
                copa_grupos_standings=copa_grupos_standings,
                copa_bracket_otros=datos.get("copa_bracket_otros", {}),
                copa_clasificado=datos.get("copa_clasificado"),
                copa_user_en_copa=datos.get("copa_user_en_copa"),
                copa_clasificado_motivo=str(datos.get("copa_clasificado_motivo", "")),
                copa_mejor_fase_temp=datos.get("copa_mejor_fase_temp")
            )
        except Exception as e:
            logger.critical(f"Error crítico al deserializar EstadoJuego: {e}. Retornando estado vacío.")
            return cls()

    def liga_por_id(self, liga_id: str) -> Optional[Liga]:
        for liga in self.ligas:
            if liga.tipo == liga_id or liga.nombre.lower() == liga_id.lower():
                return liga
        return None

    def equipo_usuario(self) -> Optional[Equipo]:
        if not self.equipo_usuario_id:
            return None
        for l in self.ligas:
            for eq in l.equipos:
                if eq.id == self.equipo_usuario_id or eq.nombre == self.equipo_usuario_id:
                    return eq
        return None

    def todos_los_equipos(self) -> list[Equipo]:
        equipos = []
        for l in self.ligas:
            equipos.extend(l.equipos)
        return equipos

    def equipo_por_id(self, equipo_id: str) -> Optional[Equipo]:
        for eq in self.todos_los_equipos():
            if eq.id == equipo_id or eq.nombre == equipo_id:
                return eq
        return None


@dataclass
class Alineacion:
    """
    Alineación/Formación de los 11 titulares elegidos por el usuario.
    Guarda los índices de los jugadores dentro de la plantilla del equipo.
    """
    titulares: list[int] = field(default_factory=list)   # Índices en equipo.jugadores
    formacion: str = "4-3-3"

    def esta_completa(self) -> bool:
        """Determina si se han seleccionado exactamente 11 jugadores."""
        try:
            return len(self.titulares) == 11
        except Exception as e:
            logger.error(f"Error en esta_completa: {e}")
            return False

    def conteo_por_posicion(self, jugadores: list) -> dict[str, int]:
        """Cuenta cuántos jugadores titulares hay por cada posición táctica."""
        conteo = {"POR": 0, "DEF": 0, "MED": 0, "DEL": 0}
        try:
            for idx in self.titulares:
                if 0 <= idx < len(jugadores):
                    pos = jugadores[idx].posicion
                    if pos in conteo:
                        conteo[pos] += 1
        except Exception as e:
            logger.error(f"Error al contar posiciones: {e}")
        return conteo

    def es_valida(self, jugadores: list) -> bool:
        """
        Validación flexible (red de seguridad para no bloquear la edición manual):
        exactamente 11 titulares, 1 Portero, al menos 3 DEF, 2 MED y 1 DEL.
        Sirve para CUALQUIER formación del registro.
        """
        try:
            if len(self.titulares) != 11:
                return False
            c = self.conteo_por_posicion(jugadores)
            return c["POR"] == 1 and c["DEF"] >= 3 and c["MED"] >= 2 and c["DEL"] >= 1
        except Exception as e:
            logger.error(f"Error al validar alineación: {e}. Retornando False por seguridad.")
            return False

    def cumple_formacion(self, jugadores: list, formacion: Optional[str] = None) -> bool:
        """True si el conteo por posición coincide EXACTO con las cuotas de la formación."""
        try:
            from alpha_football.formaciones import cuotas as _cuotas
            objetivo = _cuotas(formacion or self.formacion)
            c = self.conteo_por_posicion(jugadores)
            return all(c.get(pos, 0) == n for pos, n in objetivo.items())
        except Exception as e:
            logger.error(f"Error al validar cuotas de formación: {e}")
            return self.es_valida(jugadores)


def alineacion_por_defecto(equipo: Equipo) -> Alineacion:
    """
    Genera una alineación por defecto utilizando los primeros 11 jugadores del equipo.
    """
    try:
        if not equipo or not equipo.jugadores:
            return Alineacion(titulares=[], formacion="4-3-3")
        jugadores = equipo.jugadores
        # Tomamos los primeros 11 índices
        titulares = list(range(min(11, len(jugadores))))
        return Alineacion(titulares=titulares, formacion="4-3-3")
    except Exception as e:
        logger.error(f"Error al generar alineación por defecto: {e}. Usando alineación vacía.")
        return Alineacion(titulares=[], formacion="4-3-3")
