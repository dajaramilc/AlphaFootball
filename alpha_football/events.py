"""
Alpha Football v0.4 — Módulo de EVENTOS CAÓTICOS.

Este módulo define el catálogo de eventos paródicos que sacuden los partidos
(lesiones absurdas, expulsiones, clima imposible, invasiones de campo, milagros,
escándalos de vestuario...) y la lógica para generarlos y aplicarlos.

CONTRATO DE DATOS (compartido con engine.py y el resto de módulos)
------------------------------------------------------------------
Un *evento caótico* se representa SIEMPRE como un dict JSON-serializable con
esta forma estable (ver `EventoCaotico.como_dict`):

    {
        "id": str,            # identificador único del evento dentro del partido
        "tipo": str,          # categoría: "lesion" | "expulsion" | "clima" |
                              #            "invasion" | "milagro" | "escandalo"
        "nombre": str,        # nombre paródico mostrado en pantalla
        "descripcion": str,   # texto narrado para la UI / logs
        "minuto": int,        # minuto del partido en que ocurre (0-90)
        "equipo_id": str|None,# equipo afectado; None = afecta el ambiente / ambos
        "efecto": {           # deltas aplicados a los atributos del equipo
            "ataque": int,    # (pueden ser negativos o positivos)
            "defensa": int,
            "medio": int,
            "moral": int
        },
        "duracion": int,      # minutos que dura el efecto; 0 = resto del partido
        "severidad": str      # "leve" | "media" | "grave"
    }

Los atributos del efecto coinciden con los del CONTRATO de equipo definido en
engine.py, de modo que el motor pueda sumarlos directamente sin traducciones.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Categorías válidas de evento. Se exporta para que la UI pueda colorear/iconizar
# cada tipo sin tener que adivinar strings sueltos.
TIPOS_EVENTO = ("lesion", "expulsion", "clima", "invasion", "milagro", "escandalo")

# Severidades válidas, ordenadas de menor a mayor impacto.
SEVERIDADES = ("leve", "media", "grave")


@dataclass
class PlantillaEvento:
    """
    Molde de un evento caótico. El catálogo está hecho de plantillas; al
    generarse un evento real se completan el minuto y el equipo concreto.

    `efecto` se guarda como dict para que sea trivialmente serializable y para
    que coincida campo a campo con los atributos del equipo del CONTRATO.
    """
    tipo: str
    nombre: str
    descripcion: str
    efecto: dict[str, int]
    severidad: str
    # Probabilidad relativa (peso) de que esta plantilla sea elegida frente a
    # las demás. No es porcentaje absoluto: se normaliza contra el total.
    peso: float = 1.0
    # Si es True el efecto golpea al "ambiente" (ambos equipos) en lugar de a
    # un equipo concreto. Útil para el clima.
    afecta_ambiente: bool = False


@dataclass
class EventoCaotico:
    """
    Evento caótico ya materializado dentro de un partido concreto.

    Esta es la representación que viaja por el resto del sistema. Usa
    `como_dict()` para serializar a JSON y `desde_dict()` para reconstruir
    desde un guardado.
    """
    id: str
    tipo: str
    nombre: str
    descripcion: str
    minuto: int
    equipo_id: Optional[str]
    efecto: dict[str, int] = field(default_factory=dict)
    duracion: int = 0
    severidad: str = "leve"

    def como_dict(self) -> dict[str, Any]:
        """Devuelve el evento como dict JSON-serializable (CONTRATO DE DATOS)."""
        return asdict(self)

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> "EventoCaotico":
        """
        Reconstruye un evento desde un dict (p. ej. cargado de un guardado JSON).

        Es tolerante a campos faltantes: aplica valores por defecto razonables
        en lugar de reventar, porque un guardado viejo o de otra versión no debe
        impedir cargar la partida.
        """
        try:
            return cls(
                id=str(datos["id"]),
                tipo=str(datos.get("tipo", "milagro")),
                nombre=str(datos.get("nombre", "Evento desconocido")),
                descripcion=str(datos.get("descripcion", "")),
                minuto=int(datos.get("minuto", 0)),
                equipo_id=datos.get("equipo_id"),
                efecto=dict(datos.get("efecto", {})),
                duracion=int(datos.get("duracion", 0)),
                severidad=str(datos.get("severidad", "leve")),
            )
        except (KeyError, TypeError, ValueError) as error:
            # Dato corrupto: es no-recuperable para ESTE evento, pero no debe
            # tumbar la carga completa. Lanzamos para que el llamador decida
            # (normalmente: descartar este evento y seguir).
            logger.error("Evento caótico corrupto en guardado: %s", error, exc_info=True)
            raise ValueError(f"Evento caótico inválido: {datos!r}") from error


# ---------------------------------------------------------------------------
# CATÁLOGO PARÓDICO
# ---------------------------------------------------------------------------
# Nombres deliberadamente absurdos. Los efectos están balanceados para que un
# solo evento no decida el partido por sí mismo (deltas moderados), salvo los
# "grave" que sí pesan.
CATALOGO_EVENTOS: list[PlantillaEvento] = [
    # --- Lesiones ---
    PlantillaEvento(
        tipo="lesion",
        nombre="Tirón al celebrar un gol que no fue",
        descripcion="El delantero celebra antes de tiempo y se desgarra el orgullo (y el isquio).",
        efecto={"ataque": -8, "moral": -5},
        severidad="media",
        peso=1.5,
    ),
    PlantillaEvento(
        tipo="lesion",
        nombre="El portero se resbala con una bolsa de papas",
        descripcion="Un hincha lanzó snacks al área. El arquero patina y queda sentido.",
        efecto={"defensa": -10},
        severidad="media",
        peso=1.0,
    ),
    PlantillaEvento(
        tipo="lesion",
        nombre="Calambre colectivo por exceso de asado",
        descripcion="La concentración previa fue una parrillada. Medio campo entero camina raro.",
        efecto={"medio": -7, "ataque": -3},
        severidad="grave",
        peso=0.7,
    ),
    # --- Expulsiones ---
    PlantillaEvento(
        tipo="expulsion",
        nombre="Roja por discutir con el banderín de córner",
        descripcion="El central perdió la cabeza con un objeto inanimado. El árbitro no perdona.",
        efecto={"defensa": -12, "medio": -4, "moral": -6},
        severidad="grave",
        peso=0.9,
    ),
    PlantillaEvento(
        tipo="expulsion",
        nombre="Doble amarilla por celebrar con la afición rival",
        descripcion="Festejó de espaldas a su propia hinchada. Polémico, valiente, expulsado.",
        efecto={"ataque": -10, "moral": -4},
        severidad="grave",
        peso=0.8,
    ),
    # --- Clima ---
    PlantillaEvento(
        tipo="clima",
        nombre="Diluvio bíblico de cinco minutos",
        descripcion="El campo se convierte en piscina. El balón flota, nadie controla nada.",
        efecto={"ataque": -5, "medio": -5},
        severidad="leve",
        peso=1.3,
        afecta_ambiente=True,
    ),
    PlantillaEvento(
        tipo="clima",
        nombre="Niebla que esconde la portería",
        descripcion="Visibilidad cero. Los delanteros disparan a la fe.",
        efecto={"ataque": -8},
        severidad="media",
        peso=1.0,
        afecta_ambiente=True,
    ),
    # --- Invasiones de campo ---
    PlantillaEvento(
        tipo="invasion",
        nombre="Perro callejero roba la pelota y marca",
        descripcion="Un can entra al campo, regatea a tres y casi anota. El partido se detiene.",
        efecto={"medio": -4, "moral": 3},
        severidad="leve",
        peso=1.1,
        afecta_ambiente=True,
    ),
    PlantillaEvento(
        tipo="invasion",
        nombre="Streaker con capa de superhéroe",
        descripcion="Un aficionado disfrazado interrumpe el juego. Desconcentración total.",
        efecto={"medio": -6},
        severidad="media",
        peso=0.9,
    ),
    # --- Milagros (efectos positivos) ---
    PlantillaEvento(
        tipo="milagro",
        nombre="Charla motivacional del utilero",
        descripcion="El utilero suelta un discurso épico. El equipo se enciende.",
        efecto={"moral": 10, "ataque": 5},
        severidad="media",
        peso=1.0,
    ),
    PlantillaEvento(
        tipo="milagro",
        nombre="Segundo aire por café triple del DT",
        descripcion="El técnico reparte cafeína legal. Las piernas vuelan.",
        efecto={"medio": 7, "defensa": 4},
        severidad="leve",
        peso=1.0,
    ),
    # --- Escándalos ---
    PlantillaEvento(
        tipo="escandalo",
        nombre="Pelea de vestuario por el aire acondicionado",
        descripcion="Discusión sobre la temperatura ideal. La moral se desploma.",
        efecto={"moral": -12, "medio": -3},
        severidad="grave",
        peso=0.6,
    ),
    PlantillaEvento(
        tipo="escandalo",
        nombre="El capitán filtra el once por error",
        descripcion="Publicó la alineación en sus historias. El rival ya lo sabía todo.",
        efecto={"defensa": -6, "moral": -5},
        severidad="media",
        peso=0.8,
    ),
]


def _validar_catalogo() -> None:
    """
    Verifica que el catálogo respete el CONTRATO antes de usarlo.

    Es una guarda barata que corre una vez al importar: si alguien añade una
    plantilla con un tipo o severidad inválidos, fallamos rápido y claro en
    lugar de generar eventos basura silenciosamente más tarde.
    """
    for plantilla in CATALOGO_EVENTOS:
        if plantilla.tipo not in TIPOS_EVENTO:
            raise ValueError(
                f"Plantilla con tipo inválido '{plantilla.tipo}': {plantilla.nombre}"
            )
        if plantilla.severidad not in SEVERIDADES:
            raise ValueError(
                f"Plantilla con severidad inválida '{plantilla.severidad}': {plantilla.nombre}"
            )
        if plantilla.peso <= 0:
            raise ValueError(f"Plantilla con peso no positivo: {plantilla.nombre}")


# Validación no-recuperable: si el catálogo está mal, el módulo no debe cargar.
_validar_catalogo()


def _elegir_plantilla(rng: random.Random) -> PlantillaEvento:
    """
    Elige una plantilla del catálogo respetando los pesos relativos.

    Usamos `random.choices` con pesos en vez de `choice` uniforme para que los
    eventos raros (graves) salgan menos que los comunes (leves).
    """
    pesos = [plantilla.peso for plantilla in CATALOGO_EVENTOS]
    # choices devuelve una lista; tomamos el primer (y único) elemento.
    return rng.choices(CATALOGO_EVENTOS, weights=pesos, k=1)[0]


def generar_evento(
    minuto: int,
    equipo_local_id: str,
    equipo_visitante_id: str,
    rng: Optional[random.Random] = None,
    contador: int = 0,
) -> EventoCaotico:
    """
    Materializa UN evento caótico para un minuto concreto del partido.

    Parámetros
    ----------
    minuto : minuto del partido (0-90) en que ocurre.
    equipo_local_id / equipo_visitante_id : ids del CONTRATO de equipo.
    rng : generador aleatorio inyectable. Inyectarlo permite partidos
          deterministas (mismas semillas → mismos eventos), clave para
          guardar/cargar y para los tests.
    contador : número de evento dentro del partido, usado para el id único.

    Devuelve un `EventoCaotico` ya listo para aplicarse.
    """
    # Fallback: si no nos pasan rng, creamos uno propio. No es determinista,
    # pero el motor SIEMPRE debería inyectar el suyo.
    if rng is None:
        logger.debug("generar_evento sin rng inyectado; usando uno no determinista")
        rng = random.Random()

    plantilla = _elegir_plantilla(rng)

    # Decidir a quién golpea el evento.
    if plantilla.afecta_ambiente:
        equipo_afectado: Optional[str] = None
    else:
        equipo_afectado = rng.choice([equipo_local_id, equipo_visitante_id])

    # Los eventos graves duran el resto del partido (duracion=0); los demás un
    # tramo corto. Esto da textura sin volverlo determinista por completo.
    if plantilla.severidad == "grave":
        duracion = 0  # resto del partido
    elif plantilla.severidad == "media":
        duracion = rng.randint(15, 30)
    else:
        duracion = rng.randint(5, 12)

    return EventoCaotico(
        id=f"ev-{minuto:02d}-{contador}",
        tipo=plantilla.tipo,
        nombre=plantilla.nombre,
        descripcion=plantilla.descripcion,
        minuto=minuto,
        equipo_id=equipo_afectado,
        efecto=dict(plantilla.efecto),  # copia defensiva: nadie muta el catálogo
        duracion=duracion,
        severidad=plantilla.severidad,
    )


def generar_eventos_partido(
    equipo_local_id: str,
    equipo_visitante_id: str,
    rng: Optional[random.Random] = None,
    intensidad: float = 1.0,
) -> list[EventoCaotico]:
    """
    Genera la tanda completa de eventos caóticos de un partido.

    El número de eventos sale de una distribución controlada por `intensidad`:
    intensidad 1.0 ≈ 0 a 3 eventos por partido (el caos es condimento, no plato
    principal). `intensidad` permite a otros módulos (p. ej. una copa "modo
    locura") subir o bajar el caos sin tocar este código.

    Devuelve los eventos ORDENADOS por minuto, que es como el motor los va a
    consumir durante la simulación.
    """
    if rng is None:
        rng = random.Random()

    # Clamp defensivo de la intensidad para no recibir valores absurdos.
    intensidad = max(0.0, min(intensidad, 5.0))

    # Número base de eventos: una media baja escalada por intensidad.
    media_eventos = 1.2 * intensidad
    # Usamos una aproximación simple: tiramos un dado continuo y redondeamos.
    cantidad = int(round(abs(rng.gauss(media_eventos, 1.0))))
    cantidad = max(0, min(cantidad, 6))  # tope duro: nunca más de 6 por partido

    eventos: list[EventoCaotico] = []
    minutos_usados: set[int] = set()

    for indice in range(cantidad):
        # Evitamos que dos eventos caigan exactamente en el mismo minuto para
        # que la narración no se atropelle.
        minuto = rng.randint(1, 90)
        intentos = 0
        while minuto in minutos_usados and intentos < 5:
            minuto = rng.randint(1, 90)
            intentos += 1
        minutos_usados.add(minuto)

        evento = generar_evento(
            minuto=minuto,
            equipo_local_id=equipo_local_id,
            equipo_visitante_id=equipo_visitante_id,
            rng=rng,
            contador=indice,
        )
        eventos.append(evento)

    eventos.sort(key=lambda ev: ev.minuto)
    logger.debug(
        "Generados %d eventos caóticos (%s vs %s)",
        len(eventos), equipo_local_id, equipo_visitante_id,
    )
    return eventos


def aplicar_efecto(atributos: dict[str, int], evento: EventoCaotico) -> dict[str, int]:
    """
    Aplica el efecto de un evento sobre un dict de atributos de equipo y
    devuelve un dict NUEVO con los valores ajustados.

    No muta la entrada (función pura) para que el motor pueda comparar el antes
    y el después sin sorpresas. Los atributos resultantes se mantienen dentro de
    [0, 100] porque el resto del sistema asume ese rango en el CONTRATO.
    """
    resultado = dict(atributos)
    for clave, delta in evento.efecto.items():
        if clave not in resultado:
            logger.warning(
                "Efecto '%s' ignora atributo desconocido '%s'", evento.nombre, clave
            )
            continue
        try:
            valor_nuevo = int(resultado[clave]) + int(delta)
        except (TypeError, ValueError) as error:
            logger.error(
                "No se pudo aplicar delta a '%s': %s", clave, error, exc_info=True
            )
            continue
        resultado[clave] = max(0, min(valor_nuevo, 100))
    return resultado


def evento_caotico(mi_equipo: Any) -> str:
    """
    Genera un evento caótico aleatorio de temporada (5 originales + 5 nuevos)
    y lo aplica directamente sobre el equipo del usuario.
    Retorna el texto descriptivo del evento para la UI.
    """
    try:
        if mi_equipo is None or not hasattr(mi_equipo, "jugadores") or not mi_equipo.jugadores:
            return "Tranquilidad en el vestuario. No ha ocurrido ningún evento inusual."

        # Aseguramos que tenemos al menos 2 jugadores para peleas
        jugadores = mi_equipo.jugadores
        estrella = max(jugadores, key=lambda j: getattr(j, "overall", 70))
        
        # 10 posibles eventos (5 originales + 5 nuevos)
        tipo_evento = random.randint(1, 10)
        
        if tipo_evento == 1:
            # Escándalo de la estrella
            opc = random.choice(["multar", "perdonar"])
            if opc == "multar":
                estrella.moral = max(0, estrella.moral - 15)
                desc = f"¡ESCÁNDALO! {estrella.nombre_completo} fue captado de fiesta antes del partido. El DT lo multó (moral -15)."
            else:
                estrella.moral = max(0, estrella.moral - 5)
                desc = f"¡ESCÁNDALO! {estrella.nombre_completo} fue captado de fiesta antes del partido. El DT decidió perdonarlo (moral -5)."
            return desc

        elif tipo_evento == 2:
            # Oferta de Arabia rechazada
            valor_base = getattr(estrella, "overall", 70) * 100000
            oferta = int(valor_base * random.uniform(1.2, 1.8))
            desc = f"¡OFERTA ÁRABE! Llegó una oferta de ${oferta:,} por tu estrella {estrella.nombre_completo}. La directiva la rechazó para mantener el vestuario unido."
            return desc

        elif tipo_evento == 3:
            # Pelea de vestuario
            if len(jugadores) >= 2:
                j1 = random.choice(jugadores)
                j2 = random.choice([j for j in jugadores if j != j1])
                opc = random.choice(["mediar", "castigar"])
                if opc == "mediar":
                    j1.moral = min(100, j1.moral + 5)
                    j2.moral = min(100, j2.moral + 5)
                    desc = f"¡PELEA! {j1.nombre_completo} y {j2.nombre_completo} discutieron en el vestuario. El DT medió y se dieron la mano (moral +5)."
                else:
                    j1.moral = max(0, j1.moral - 10)
                    j2.moral = max(0, j2.moral - 10)
                    desc = f"¡PELEA! {j1.nombre_completo} y {j2.nombre_completo} discutieron en el vestuario. El DT los castigó a ambos (moral -10)."
            else:
                desc = "Ambiente tranquilo. No hay suficientes jugadores para armar peleas."
            return desc

        elif tipo_evento == 4:
            # Lesión absurda
            j = random.choice(jugadores)
            j.lesion_partidos = 3
            desc = f"¡MALA SUERTE! {j.nombre_completo} se resbaló bajando del autobús del equipo. ¡Estará lesionado por 3 partidos!"
            return desc

        elif tipo_evento == 5:
            # Charla del utilero (Milagro)
            for j in jugadores:
                j.moral = min(100, j.moral + 10)
            desc = "¡MILAGRO EN EL VESTUARIO! El utilero dio un discurso épico motivacional. ¡La moral de todo el plantel sube +10!"
            return desc

        elif tipo_evento == 6:
            # Lluvia (Físico +20% a ambos)
            # Este evento afecta el ambiente, lo informamos al usuario
            desc = "¡TORMENTA! Pronóstico de lluvia torrencial y barro para la jornada. El juego físico se intensificará para ambos equipos (+20% físico)."
            return desc

        elif tipo_evento == 7:
            # Directiva impone fichaje OVR 55 gratis
            # Creamos un jugador OVR 55
            nuevo = Jugador(
                nombre="Promesa",
                apellido="Impuesta",
                posicion=random.choice(["DEF", "MED", "DEL"]),
                ataque=55, defensa=55, fisico=55, tecnica=55, mental=55,
                moral=70,
                id=random.randint(9000, 9999)
            )
            jugadores.append(nuevo)
            desc = f"¡DECISIÓN CORPORATIVA! La directiva ha fichado gratis y sin tu consentimiento a {nuevo.nombre_completo} (OVR 55) por motivos comerciales."
            return desc

        elif tipo_evento == 8:
            # Jugador pide salir (Moral baja a 20)
            j = random.choice(jugadores)
            j.moral = 20
            desc = f"¡DESCONTENTO! {j.nombre_completo} solicitó formalmente ser transferido a otro club. Al no venderlo de inmediato, su moral bajó a 20."
            return desc

        elif tipo_evento == 9:
            # Árbitro escandaloso
            desc = "¡POLÉMICA ARBITRAL! La comisión técnica ha designado un referí polémico para la fecha. La prensa anticipa fallos escandalosos."
            return desc

        else:
            # Hincha famoso (+5 moral a todos)
            for j in jugadores:
                j.moral = min(100, j.moral + 5)
            desc = "¡VISITA DE LUJO! Un hincha famoso y querido por el club visitó la concentración. ¡La moral del equipo sube +5!"
            return desc

    except Exception as e:
        logger.error(f"Error en evento_caotico: {e}")
        return "Un leve imprevisto ocurrió en los camerinos, pero fue resuelto internamente."


def generar_evento(estado: Any) -> Optional[str]:
    """
    Punto de entrada de eventos para el integrador (main.py).
    Decide de manera aleatoria (40% probabilidad por jornada) si lanza un evento
    y lo aplica sobre el equipo del usuario.
    """
    try:
        # 40% de probabilidad
        if random.random() < 0.40:
            # Encontrar el equipo del usuario
            mi_equipo = None
            if hasattr(estado, "equipo_usuario"):
                # estado es un EstadoJuego objeto
                mi_equipo = estado.equipo_usuario()
            elif isinstance(estado, dict):
                # fallback dict
                mi_equipo = estado.get("mi_equipo")
                
            if mi_equipo is not None:
                return evento_caotico(mi_equipo)
        return None
    except Exception as e:
        logger.error(f"Error en generar_evento del modulo: {e}")
        return None
