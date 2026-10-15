# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Prensa (v0.4.23.0).
Conferencias de prensa antes y después de los partidos importantes (overlay en el prepartido y el postpartido),
declaraciones de los DT y sus efectos sobre la moral y las tarjetas del siguiente partido.
Lógica pura sobre `estado` y `datos_carrera['prensa']`: nada de pygame aquí.
"""
from __future__ import annotations

import copy
import logging
import random
import re
from typing import Optional

logger = logging.getLogger(__name__)

# v0.4.25.0: ocho tonos; cada pregunta ofrece cuatro de ellos, los que encajan con el momento
TONOS = ('motivador', 'provocador', 'humilde', 'agresivo', 'ironico', 'diplomatico', 'elogioso', 'evasivo')
FACTOR_TENSION = 1.6                  # factor de tarjetas del siguiente partido tras una respuesta agresiva
MOTIVOS = ('copa_final', 'copa_semi', 'clasico', 'titulo', 'descenso', 'lider',      # por prioridad
           'debut', 'cierre', 'racha_mala', 'racha_buena', 'lesionados', 'favorito', 'david', 'rival_directo',
           'figura', 'copa_ronda')
# solo se eligen si lo demás no pide conferencia; las goleadas se deciden con el marcador (postpartido)
_BAJA_PRIORIDAD = ('lider', 'debut', 'cierre', 'racha_mala', 'racha_buena', 'lesionados', 'favorito', 'david',
                   'rival_directo', 'figura', 'copa_ronda')
UMBRAL_GOLEADA = 3                    # diferencia de goles para que el postpartido hable de una goleada
RACHA_BUENA = 3                       # victorias seguidas
RACHA_MALA = 2                        # derrotas seguidas (o SIN_GANAR partidos sin ganar)
SIN_GANAR = 4
MIN_LESIONADOS = 3
MIN_GOLES_FIGURA = 5
MOTIVO_TEXTO = {'copa_final': "Final de copa", 'copa_semi': "Semifinal de copa", 'clasico': "Clásico",
                'titulo': "Pelea por el título", 'descenso': "Lucha por la permanencia", 'lider': "Líder de la liga"}
_MORAL_PROPIA = {'motivador': 2, 'humilde': 1, 'ironico': 1, 'diplomatico': 1}
_MORAL_RIVAL_IRONICO = -1             # el irónico pincha un poco al rival
_MORAL_ELOGIO = 3                     # el elogio sube la moral de la figura de la pregunta
_MORAL_RIVAL = -2                     # provocador
_MORAL_POR_DT_RIVAL = -1              # el DT rival declara en la previa
_IMPORTANCIA = {'provocador': 4, 'motivador': 3, 'agresivo': 3, 'humilde': 2, 'ironico': 3, 'diplomatico': 2,
                'elogioso': 2, 'evasivo': 1}
_TOPE_HECHAS = 80                     # conferencias recordadas en datos_carrera (las más viejas salen)


def mover_moral(jugadores, delta: int) -> None:
    """Suma `delta` a la moral de cada jugador (siempre entre 0 y 100). Una baja se anota en la última causa
    de `causas_moral` ('equipo'), igual que el contagio del polémico en vestuario.actualizar_moral, para que el
    vestuario la explique."""
    for j in jugadores or []:
        try:
            j.moral = max(0, min(100, int(j.moral) + int(delta)))
            if delta < 0 and getattr(j, 'causas_moral', None):
                j.causas_moral[-1]['equipo'] = int(j.causas_moral[-1].get('equipo', 0)) + int(delta)
        except Exception as e:
            logger.error(f"No se pudo mover la moral de {getattr(j, 'apellido', '?')}: {e}")


# ------------------------------------------------------------------ banco de preguntas
def _q(texto: str, motivador: str, provocador: str, humilde: str, agresivo: str) -> dict:
    """Una pregunta con sus cuatro respuestas (una por tono). `{rival}` y `{club}` se rellenan al armar la conferencia."""
    return {'texto': texto, 'respuestas': {'motivador': motivador, 'provocador': provocador,
                                           'humilde': humilde, 'agresivo': agresivo}}


# BANCO[motivo]['pre'] = [preguntas]; BANCO[motivo]['post'][resultado] = [preguntas], resultado = gana|empata|pierde.
BANCO = {
    'copa_final': {
        'pre': [
            _q("Mañana es la final. ¿Cómo llega su equipo?",
               "Con hambre y confianza. Llegamos hasta aquí por méritos propios y vamos a por la copa.",
               "{rival} llega con presión. Las finales las ganan los que no tiemblan, y nosotros no temblamos.",
               "Una final se juega, no se gana antes. Mucho respeto a {rival} y mucho trabajo.",
               "Vamos a pelear cada balón como si fuera el último. Que nadie espere un partido amable."),
            _q("¿Qué le dice a su vestuario antes de la final más importante del año?",
               "Que disfruten: se ganaron estar aquí y merecen levantar esa copa.",
               "Que {rival} se prepare. No vinimos a participar, vinimos a llevarnos el título.",
               "Que sigan siendo ellos mismos. Hacer lo de siempre es lo que nos trajo hasta aquí.",
               "Que dejen todo en la cancha. En una final no se pide permiso: se muerde."),
        ],
        'post': {
            'gana': [
                _q("¡Campeones! ¿Qué significa este título para el club?",
                   "Es el premio a un grupo extraordinario. Esto es solo el comienzo, vamos a seguir creciendo.",
                   "Se lo dedico a los que dudaron. Y a {rival}: la copa ya tiene dueño.",
                   "Hubo mucho trabajo y algo de suerte. {rival} merece todo nuestro respeto.",
                   "Ganamos porque fuimos más fuertes. Quien quiera la copa tendrá que venir a quitárnosla."),
                _q("Levantan la copa. ¿A quién le debe este éxito?",
                   "A los jugadores, al cuerpo técnico y a la afición. Esta copa es de todos.",
                   "A los que dijeron que no llegábamos. Les dejo la copa para que la miren.",
                   "A los jugadores, siempre a ellos. Yo solo les di una mano.",
                   "A la intensidad de este equipo. Hoy mordimos más que nadie."),
            ],
            'empata': [
                _q("La final se resolvió por la mínima. ¿Cómo valora el partido?",
                   "Estoy orgulloso de la entrega del grupo. Pase lo que pase, hoy ya ganamos mucho.",
                   "{rival} se salvó con la igualdad. Tuvimos más y todos lo vieron.",
                   "Fue una final muy pareja, contra un rival digno. Cualquiera pudo ganarla.",
                   "Faltó un poco de maldad. La próxima no nos van a frenar."),
                _q("Igualdad y tensión de principio a fin. ¿Qué se lleva del partido?",
                   "Que este equipo no se rinde jamás. Con esa actitud vamos a ganar muchas cosas.",
                   "Que {rival} se salvó. Cuando nos crezcamos de verdad, no hay quien nos pare.",
                   "El resultado fue justo. Hay que mejorar detalles y seguir trabajando.",
                   "Que hay que ser más duros en cada disputa. Esto es una final y se juega al límite."),
            ],
            'pierde': [
                _q("Se les escapó la copa. ¿Qué explica la derrota?",
                   "Dimos todo. Duele, pero este grupo tiene mucho futuro y vamos a volver más fuertes.",
                   "Nos cobraron caro cada error. {rival} tuvo suerte hoy; en otra final será distinto.",
                   "Fueron mejores y hay que reconocerlo. Felicito a {rival} y aprendemos de esto.",
                   "No hay excusas, pero que nadie se confíe. La revancha será a otro nivel."),
                _q("Perder una final duele. ¿Qué les dice a sus jugadores ahora?",
                   "Que levanten la cabeza. Llegaron hasta aquí y nadie les va a quitar eso.",
                   "Que recuerden esta sensación. {rival} festeja hoy, pero la historia no termina aquí.",
                   "Que acepten el resultado y aprendan. En el fútbol se gana y se pierde.",
                   "Que no se dejen pisar nunca más. La próxima, ni un centímetro de ventaja."),
            ],
        },
    },
    'copa_semi': {
        'pre': [
            _q("Se juega una semifinal. ¿Cómo prepara un partido así?",
               "Con ilusión: estamos a un paso de la final y este grupo está listo.",
               "{rival} se tiene que dar cuenta de que no somos un rival cualquiera.",
               "Con humildad y trabajo. Una semifinal se gana partido a partido.",
               "Vamos a ir al choque desde el primer minuto. En una semi no hay medias tintas."),
            _q("¿Qué le preocupa de {rival} en esta semifinal?",
               "Nada que nos quite el sueño. Nos ocupamos de lo nuestro y confiamos en lo que somos.",
               "Nada. Cuando juguemos a lo nuestro, {rival} tendrá más problemas que nosotros.",
               "Mucho. Tienen jugadores de nivel y sería un error subestimarlos.",
               "Que se atrevan a competir con nosotros. Les vamos a hacer sentir cada balón."),
        ],
        'post': {
            'gana': [
                _q("¡Están en la final! ¿Qué sensación le deja el partido?",
                   "Orgullo total. El equipo compitió con el corazón y se ganó la final.",
                   "Le pasamos por encima a {rival}. Ahora vamos por la copa, y que nadie se confíe.",
                   "Sufrimos y tuvimos algo de fortuna. Pero la final es un premio para todos.",
                   "Fuimos más fuertes en lo físico y en la actitud. A la final vamos a morder más fuerte."),
                _q("Clasifican a la final. ¿Ya piensa en el rival?",
                   "Solo pienso en disfrutar este momento con mi gente. Vamos a por todo.",
                   "No me importa quién llegue. Vamos a ganarle a quien venga.",
                   "Primero hay que descansar y recuperarse. La final será otro partido muy difícil.",
                   "Quien llegue que se prepare. Vamos a ir a muerte por esa copa."),
            ],
            'empata': [
                _q("La semifinal terminó igualada. ¿Cómo la deja?",
                   "Todo se define en el último esfuerzo. Este grupo está hecho para eso.",
                   "{rival} se fue con un empate que no merecía. Aquí mandamos nosotros.",
                   "Es una eliminatoria muy abierta. Ambos equipos hicieron méritos.",
                   "No fuimos tan fuertes como debíamos. La próxima vamos a pisar más duro."),
                _q("Queda todo por decidir. ¿Qué cambiaría?",
                   "Nada. Confío en estos jugadores y en que sacaremos el partido adelante.",
                   "Que nos dejen jugar. {rival} sabe que cuando apretamos no tienen respuesta.",
                   "Ajustaremos detalles. Hay que ser inteligentes y no regalar nada.",
                   "Más intensidad y menos respeto. Si hay que ir fuerte, iremos fuerte."),
            ],
            'pierde': [
                _q("Quedan fuera de la copa. ¿Qué falló?",
                   "Estamos tristes, pero orgullosos. Nos queda aprender y volver mejores.",
                   "{rival} ganó, pero no fue superior. El fútbol a veces es injusto.",
                   "El rival fue mejor y lo reconozco. Hay que felicitarlos y mirar adelante.",
                   "Faltó carácter. Esto no volverá a pasar, se lo aseguro."),
                _q("Se acaba el sueño de la copa. ¿Cómo está el vestuario?",
                   "Golpeado, pero unido. Esta temporada todavía tiene mucho por jugar.",
                   "Con rabia. {rival} lo celebrará, pero nos la van a deber.",
                   "Tranquilos. Es parte de este deporte y toca asumirlo con dignidad.",
                   "Con ganas de pelear. El próximo rival va a pagar por esto."),
            ],
        },
    },
    'clasico': {
        'pre': [
            _q("Llega el clásico. ¿Cómo lo vive un entrenador?",
               "Con orgullo. Es el partido que todos quieren jugar y mi equipo está listo.",
               "El clásico se gana en la cancha, y {rival} sabe que últimamente llevan las de perder.",
               "Con mucho respeto. En un clásico se olvida la tabla y todo puede pasar.",
               "Un clásico se juega con los dientes apretados. Vamos a ir a cada pelota."),
            _q("{rival} dice que son los favoritos. ¿Qué responde?",
               "Que digan lo que quieran. Nosotros nos centramos en nuestro juego.",
               "Que hablen todo lo que quieran. En la cancha se les va a acabar el cuento.",
               "Los favoritos no existen en un clásico. Los dos tenemos opciones.",
               "Que lo demuestren en la cancha. Aquí hablamos con los pies y con el pecho."),
        ],
        'post': {
            'gana': [
                _q("¡Ganan el clásico! ¿Qué le dice a la hinchada?",
                   "Que este triunfo es suyo. Fueron el jugador número doce.",
                   "Que {rival} sepa dónde está su lugar. Esta ciudad es nuestra.",
                   "Que disfruten, pero sin olvidar que sigue la liga y hay mucho trabajo.",
                   "Les ganamos en todas las líneas. Que sepan que la próxima vamos por más."),
                _q("Triunfo en el clásico. ¿Qué fue lo más importante?",
                   "La actitud del equipo. Corrieron por la camiseta y por la gente.",
                   "Mostrar que {rival} no está a nuestra altura. Hoy se vio claro.",
                   "Los tres puntos, nada más. El clásico es un partido más del calendario.",
                   "La contundencia. Les pasamos por encima en cada duelo."),
            ],
            'empata': [
                _q("El clásico terminó en tablas. ¿Se queda con el punto?",
                   "Con la entrega de mis jugadores. Seguimos vivos y vamos a seguir.",
                   "Pudimos ganar y {rival} lo sabe. Se fueron con más de lo que merecían.",
                   "Es un resultado justo en un partido muy disputado.",
                   "Un punto no nos sirve. En el próximo vamos a ir con todo."),
                _q("Hubo mucha tensión y poco fútbol. ¿Qué opina?",
                   "Estos partidos son así. Lo importante es que el equipo no se rindió.",
                   "Los de {rival} se dedicaron a cortar el juego. Nosotros vinimos a jugar.",
                   "El clásico es un partido distinto. Creo que ambos hicimos lo posible.",
                   "Hay que ir más fuerte. Si es a base de choques, vamos a chocar más."),
            ],
            'pierde': [
                _q("Pierden el clásico. ¿Cómo explica el resultado?",
                   "Fue un golpe duro, pero esto no define nuestra temporada. Vamos a levantarnos.",
                   "Nos ganaron por detalles. {rival} sabe que en otro cruce será muy distinto.",
                   "El rival fue mejor. Felicito a {rival} y trabajamos para corregir.",
                   "Esto no se queda así. En el próximo cruce nos las pagan."),
                _q("La hinchada está molesta. ¿Qué les pide?",
                   "Que nos sigan apoyando. Estoy seguro de que le daremos la vuelta a esto.",
                   "Que no se preocupen. {rival} ganó hoy, pero la temporada es larga.",
                   "Tienen razón en molestarse. Debemos pedir disculpas y mejorar.",
                   "Que confíen en este equipo. Vamos a responder con carácter."),
            ],
        },
    },
    'titulo': {
        'pre': [
            _q("Están peleando el título. ¿Cómo maneja la presión?",
               "Con ilusión. Pocos equipos viven esta situación y vamos a disfrutarla.",
               "La presión la tienen los demás. Nosotros jugamos a lo nuestro.",
               "Un partido a la vez. Todavía falta mucho y no podemos relajarnos.",
               "Cada partido es una final. Vamos a pelear cada punto como si fuera el último."),
            _q("{rival} puede cambiar las cuentas del título. ¿Cómo lo ve?",
               "Es una gran oportunidad. Los puntos de hoy valen oro y vamos a por ellos.",
               "{rival} no tiene nada que perder. Nosotros sí, pero no tenemos miedo.",
               "Un rival difícil, como todos. No hay partidos fáciles en esta recta final.",
               "No vamos a regalar nada. Quien se cruce en nuestro camino se lo llevará por delante."),
        ],
        'post': {
            'gana': [
                _q("Otra victoria en la pelea por el título. ¿Qué sensación le deja?",
                   "Estamos más cerca. El equipo está en un nivel enorme y la gente lo disfruta.",
                   "Que sigan mirando nuestra espalda. {rival} fue el último en comprobarlo.",
                   "Tres puntos importantes, pero sin euforia. Quedan muchos partidos y mucho por hacer.",
                   "Les pasamos por encima. Quien nos quiera quitar el título tendrá que pasar por aquí."),
                _q("Ganan y se acercan al título. ¿Ya se siente campeón?",
                   "No hablemos de eso. El equipo merece soñar, pero con los pies en la tierra.",
                   "Los demás ya deberían estar nerviosos. Nosotros estamos en lo nuestro.",
                   "Para nada. Falta mucho y no vamos a confiarnos.",
                   "Vamos a ir por todo. Los demás que se cuiden."),
            ],
            'empata': [
                _q("Pierden dos puntos en la lucha por el título. ¿Qué pasó?",
                   "No nos vamos a lamentar. Ahora a recuperar y seguimos peleando.",
                   "Con todos detrás de la pelota, {rival} no jugó a nada. Seguimos a lo nuestro.",
                   "Hay que aceptarlo. El rival también juega y nos puso en problemas.",
                   "Estoy molesto. Queríamos los tres puntos y vamos a ir con más hambre."),
                _q("Un empate cuando el título está en juego. ¿Es un mal resultado?",
                   "Hay que valorarlo y mirar hacia adelante. Seguimos en la pelea.",
                   "Mal resultado para {rival}: se fueron de aquí con un punto regalado.",
                   "Lo vivimos con calma. Tampoco es una derrota y seguimos adelante.",
                   "No podemos permitirnos más tropiezos. Es hora de exigirnos el doble."),
            ],
            'pierde': [
                _q("Una derrota en plena lucha por el título. ¿Se complica todo?",
                   "Se complica, pero no se acaba. Este grupo ha superado cosas peores.",
                   "Hoy {rival} tuvo suerte. En la tabla nada cambia, y ellos lo saben.",
                   "Es un golpe fuerte y debemos reconocerlo. A trabajar sin buscar culpables.",
                   "Esto duele. Vamos a salir a morder en el próximo partido, se lo prometo."),
                _q("Pierden y el título se aleja. ¿Qué mensaje manda al vestuario?",
                   "Que están a tiempo. Un traspié no cuenta; lo que importa es cómo reaccionemos.",
                   "Que no se les ocurra bajar los brazos. {rival} no nos va a quitar nada.",
                   "Que mantengamos la calma. Hay que analizar y corregir sin dramatizar.",
                   "Que se les acabó la tranquilidad. Desde mañana, trabajo duro y sin excusas."),
            ],
        },
    },
    'descenso': {
        'pre': [
            _q("Están en zona de descenso. ¿Cómo afronta este partido?",
               "Con fe. Este equipo tiene calidad para salir y se lo vamos a demostrar.",
               "Los que nos dan por muertos van a quedar en ridículo. {rival} será el primero.",
               "Con realismo y trabajo. Sabemos que es difícil, pero no hay otra forma de salir.",
               "Estamos con el agua al cuello. Hay que pelear cada balón como una final."),
            _q("La hinchada empieza a preocuparse. ¿Qué les dice?",
               "Que confíen. Vamos a darlo todo por esta camiseta y por la afición.",
               "Que no se dejen llevar por las críticas. Todavía no nos han enterrado.",
               "Que nos entiendan y nos apoyen. Nos necesitamos más que nunca.",
               "Que vengan al estadio, porque van a ver a un equipo que pelea hasta el final."),
        ],
        'post': {
            'gana': [
                _q("Una victoria que da aire en la lucha por la permanencia. ¿Cómo la vive?",
                   "Es un alivio y un impulso. Hay que construir sobre esto y vamos a salir adelante.",
                   "Que {rival} y todos sepan que seguimos vivos. No nos van a enterrar.",
                   "Son tres puntos valiosos, pero aún no hemos hecho nada. A seguir trabajando.",
                   "Les ganamos con hambre. Así vamos a ganar todos los demás hasta salvarnos."),
                _q("Tres puntos de oro. ¿Se acabó la crisis?",
                   "Estamos de vuelta. El equipo recuperó la confianza y eso es lo que importa.",
                   "La crisis la tendrán otros. Nosotros ya dimos nuestra respuesta.",
                   "No. Esto no cambia nada si no lo confirmamos. Sin euforia, a trabajar.",
                   "Para nada. Mientras no estemos a salvo, seguimos en guerra."),
            ],
            'empata': [
                _q("Un punto en la zona baja. ¿Le sirve?",
                   "Es un punto que suma. Con este espíritu llegarán las victorias.",
                   "Pudimos ganarle a {rival}. En el próximo se nos da y verán de qué estamos hechos.",
                   "Es un punto que valoramos. En nuestra situación todo suma.",
                   "No nos alcanza. Necesitamos ganar y para eso hay que ser más fieros."),
                _q("Siguen sin ganar. ¿Qué le falta al equipo?",
                   "Un poco de suerte y de confianza. Y eso llega trabajando.",
                   "Nada que no tengamos. Los resultados llegarán y {rival} lo comprobará.",
                   "Hay cosas por corregir y las vamos a trabajar. No hay soluciones mágicas.",
                   "Más garra y más carácter. Si hay que mojar la camiseta, la mojamos."),
            ],
            'pierde': [
                _q("Otra derrota en la zona de descenso. ¿Qué responde?",
                   "Es duro, pero seguimos creyendo. Todavía hay mucho campeonato y lo vamos a pelear.",
                   "Que no cuenten con nuestro descenso. {rival} ganó hoy, pero esto no se acaba.",
                   "Asumo la responsabilidad. Debemos mejorar muchísimo y rápido.",
                   "Esto no puede seguir así. Nos jugamos la vida y vamos a ir con todo."),
                _q("La presión crece tras la derrota. ¿Cómo la afronta?",
                   "Con unidad. Este vestuario es fuerte y va a salir adelante.",
                   "Que sigan hablando. Cuando nos salvemos, serán los primeros en aplaudir.",
                   "Con humildad y autocrítica. Hay que reconocer lo que no hicimos bien.",
                   "Con el puño cerrado. Se acabaron las contemplaciones."),
            ],
        },
    },
    'lider': {
        'pre': [
            _q("Son líderes de la liga. ¿Cómo gestiona esa posición?",
               "Con orgullo y con los pies en el suelo. El equipo merece estar arriba.",
               "Que los demás miren desde abajo. Estamos arriba por nuestros méritos.",
               "Es una foto del momento. Sabemos que hay que seguir ganando partidos.",
               "Estar arriba te pone la diana. Vamos a defender cada punto con los dientes."),
            _q("{rival} quiere quitarles el liderato. ¿Cómo lo ve?",
               "Es una buena motivación. Vamos a demostrar por qué estamos donde estamos.",
               "Que lo intenten. Nadie le ha podido a este equipo cuando juega a su ritmo.",
               "Un rival serio, como siempre. No existen los partidos fáciles.",
               "Que vengan con todo, que aquí no se les va a regalar nada."),
        ],
        'post': {
            'gana': [
                _q("Siguen líderes tras una nueva victoria. ¿Cuál es el secreto?",
                   "El grupo. Todos rinden y se ayudan. Es un equipo en el mejor sentido.",
                   "No hay secreto. Equipos como {rival} deberían tomar nota.",
                   "Trabajo, constancia y algo de suerte. Pero queda muchísimo por hacer.",
                   "Mentalidad. Ganamos los duelos y no soltamos a nadie. Así seguiremos."),
                _q("Ganan y se afianzan en la cima. ¿Mira hacia atrás?",
                   "Miro hacia adelante. Cada partido es una nueva oportunidad de crecer.",
                   "Los de atrás deberían preocuparse. Nosotros ya no miramos.",
                   "Para nada. Cada rival es difícil y nosotros tampoco somos invencibles.",
                   "Yo no miro a nadie. Que los demás nos miren a nosotros."),
            ],
            'empata': [
                _q("Un empate. ¿Se les escapa el liderato?",
                   "Seguimos arriba y eso es lo importante. Un punto no es malo.",
                   "Con todo el equipo atrás, {rival} no nos iba a ganar. Seguiremos arriba.",
                   "Un punto es un punto. Quizá fue un resultado justo.",
                   "Me molesta, y mucho. Vamos a exigirnos más desde mañana."),
                _q("Un punto ante un rival directo. ¿Está satisfecho?",
                   "Satisfecho con el esfuerzo. Seguimos con la misma ilusión de siempre.",
                   "Satisfecho no. Dejamos escapar tres puntos y {rival} lo sabe.",
                   "Es un buen resultado ante un rival complicado. Lo tomamos con calma.",
                   "No estoy satisfecho. Esperaba más ambición del equipo."),
            ],
            'pierde': [
                _q("Primera derrota del líder. ¿Qué ocurrió?",
                   "Nadie es invencible. Ahora toca levantarse y seguir con el mismo espíritu.",
                   "Un tropiezo. {rival} celebra como si fuese el título, y eso nos motiva.",
                   "Perdimos y hay que aceptarlo. Felicito al rival y a trabajar.",
                   "No vuelve a pasar. Esta derrota nos da hambre y el próximo rival lo notará."),
                _q("Pierden y el liderato peligra. ¿Está preocupado?",
                   "Ocupado, no preocupado. Tenemos un equipo fuerte y volveremos.",
                   "Que se ilusionen unos días. En unas jornadas volveremos a mandar.",
                   "Un poco, claro. La liga es larga, pero hay cosas que corregir ya.",
                   "Hoy me duele. Mañana, a entrenar el doble. Esta derrota no se repite."),
            ],
        },
    },
}

# v0.4.25.0: banco ampliado (preguntas nuevas para los motivos de siempre + motivos contextuales nuevos)
from alpha_football.prensa_banco import BANCO_EXTRA, PREGUNTAS_EXTRA, MOTIVO_TEXTO_EXTRA   # noqa: E402


def _fusionar_banco() -> None:
    for motivo, grupos in PREGUNTAS_EXTRA.items():
        BANCO[motivo]['pre'].extend(grupos.get('pre', []))
        for resultado, preguntas in (grupos.get('post') or {}).items():
            BANCO[motivo]['post'].setdefault(resultado, []).extend(preguntas)
    for motivo, grupos in BANCO_EXTRA.items():
        BANCO[motivo] = grupos
    MOTIVO_TEXTO.update(MOTIVO_TEXTO_EXTRA)


_fusionar_banco()

# Lo que dice el DT rival en la previa (se muestra en el overlay; su costo es -1 de moral si respondes).
DECLARACIONES_RIVAL = (
    "No tenemos nada que temer de {club}. Vamos a imponer nuestro juego.",
    "{club} es un buen equipo, pero vamos a salir a por los tres puntos.",
    "Hemos preparado el partido a fondo. Conocemos las virtudes y los defectos de {club}.",
    "Que nadie se confíe: {club} tiene que ganarnos, y no será fácil.",
    "Vamos a salir a ganar, como siempre. Lo que haga {club} es su problema.",
    "{club} ha tenido altibajos y nosotros llegamos en un gran momento.",
)


# ------------------------------------------------------------------ datos y búsquedas
def _prensa(estado: dict) -> dict:
    """datos_carrera['prensa'] (JSON simple), creado y completado si falta (guardados viejos)."""
    dc = estado.get('datos_carrera')
    if not isinstance(dc, dict):
        dc = estado['datos_carrera'] = {}
    pr = dc.get('prensa')
    if not isinstance(pr, dict):
        pr = dc['prensa'] = {}
    if not isinstance(pr.get('hechas'), dict):
        pr['hechas'] = {}
    if not isinstance(pr.get('moral_rival'), dict):
        pr['moral_rival'] = {}
    pr.setdefault('tension', 0)
    return pr


def _es_mi(estado: dict, equipo) -> bool:
    mi = estado.get('mi_equipo')
    return mi is not None and equipo is not None and (
        equipo is mi or getattr(equipo, 'id', None) == getattr(mi, 'id', -1))


def _rival_de(estado: dict, local, visitante):
    return visitante if _es_mi(estado, local) else local


def _buscar_equipo(estado: dict, equipo_id):
    """El club con ese id en la liga del user, en las demás ligas de la partida o en la lista de equipos."""
    eid = str(equipo_id)
    liga = estado.get('liga')
    candidatos = list(getattr(liga, 'equipos', []) or []) + list(estado.get('equipos') or [])
    try:
        from alpha_football import entrenadores as _en
        candidatos += [eq for eq, _lg in _en.clubes(estado)]
    except Exception as e:
        logger.error(f"prensa: no se pudieron listar los clubes: {e}")
    return next((eq for eq in candidatos if str(getattr(eq, 'id', '')) == eid), None)


def _nombre_dt(estado: dict, equipo) -> str:
    """Nombre del DT de un club IA ('' si no se sabe)."""
    try:
        from alpha_football import entrenadores as _en
        dt = _en.dt_de(estado, equipo)
        if dt and dt.get('nombre'):
            return str(dt['nombre'])
        from alpha_football.data.entrenadores import DT_REALES
        real = DT_REALES.get(getattr(equipo, 'nombre', ''))
        return str(real[0]) if real else ''
    except Exception as e:
        logger.error(f"prensa: no se pudo leer el DT de {getattr(equipo, 'nombre', '?')}: {e}")
        return ''


def _jornada_de_liga(estado: dict) -> int:
    liga = estado.get('liga')
    p = estado.get('partido_actual')
    return int(getattr(p, 'jornada', 0) or getattr(liga, 'jornada_actual', 0) or 0)


def _clave(estado: dict, local, visitante, modo: str) -> str:
    """Un partido del user: temporada, competición, los dos clubes y la jornada (o el id del partido de copa)."""
    if modo == 'copa':
        p = estado.get('partido_copa_dict') or {}
        cuando = p.get('id') or p.get('fase') or '?'
    else:
        cuando = _jornada_de_liga(estado)
    return f"{estado.get('temporada', 1)}:{modo}:{getattr(local, 'id', '?')}:{getattr(visitante, 'id', '?')}:{cuando}"


def _marcar_hecha(estado: dict, clave: str, fase: str) -> None:
    hechas = _prensa(estado)['hechas']
    fases = hechas.setdefault(clave, [])
    if fase not in fases:
        fases.append(fase)
    while len(hechas) > _TOPE_HECHAS:                  # las conferencias más viejas dejan de recordarse
        hechas.pop(next(iter(hechas)))


def _ya_hecha(estado: dict, clave: str, fase: str) -> bool:
    return fase in (_prensa(estado)['hechas'].get(clave) or [])


# ------------------------------------------------------------------ cuándo se ofrece
def _contador(estado: dict, clave: str) -> int:
    """Un contador de logros.contadores (rachas): 0 si el guardado es viejo o no existe."""
    try:
        c = ((estado.get('datos_carrera') or {}).get('logros') or {}).get('contadores') or {}
        return int(c.get(clave) or 0)
    except (TypeError, ValueError):
        return 0


def _tu_figura(mi) -> Optional[object]:
    """El jugador de tu plantel que más goles lleva en la temporada (a igualdad, el de más media)."""
    jugadores = list(getattr(mi, 'jugadores', None) or [])
    if not jugadores:
        return None
    return max(jugadores, key=lambda j: (int(getattr(j, 'goles', 0) or 0), int(getattr(j, 'overall', 0) or 0)))


def contexto(estado: dict, local, visitante, modo: str, pos: Optional[int] = None) -> dict:
    """Lo que la conferencia sabe del momento (los datos que rellenan las preguntas y deciden el motivo): puesto tuyo y
    del rival, rachas, lesionados, tu figura y la ronda de copa. Nunca lanza: lo que no se pueda leer queda en 0."""
    ctx = {'puesto': 0, 'rival_puesto': 0, 'n': 0, 'jornada': 0, 'quedan': 99, 'racha': _contador(estado, 'racha'),
           'derrotas': _contador(estado, 'derrotas_seguidas'), 'sin_ganar': _contador(estado, 'sin_ganar'),
           'lesionados': 0, 'jugador': '', 'jugador_id': '', 'goles_figura': 0, 'fase': ''}
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if mi is not None:
            ctx['lesionados'] = sum(1 for j in getattr(mi, 'jugadores', None) or []
                                    if int(getattr(j, 'lesion_dias', 0) or 0) > 0)
            figura = _tu_figura(mi)
            if figura is not None:
                ctx['jugador'] = str(getattr(figura, 'apellido', '') or getattr(figura, 'nombre', ''))
                ctx['jugador_id'] = str(getattr(figura, 'id', ''))
                ctx['goles_figura'] = int(getattr(figura, 'goles', 0) or 0)
        if modo == 'copa':
            ctx['fase'] = str((estado.get('partido_copa_dict') or {}).get('fase', '') or '')
        if modo == 'liga' and liga is not None and mi is not None and getattr(liga, 'equipos', None):
            tabla = sorted(liga.equipos, key=lambda x: (getattr(x, 'puntos', 0), getattr(x, 'gf', 0) - getattr(x, 'gc', 0),
                                                        getattr(x, 'gf', 0)), reverse=True)
            ctx['n'] = len(tabla)
            ctx['puesto'] = int(pos) if pos else next((i + 1 for i, x in enumerate(tabla) if x.id == mi.id), 0)
            rival = _rival_de(estado, local, visitante)
            ctx['rival_puesto'] = next((i + 1 for i, x in enumerate(tabla)
                                        if rival is not None and x.id == getattr(rival, 'id', None)), 0)
            ctx['jornada'] = _jornada_de_liga(estado)
            ctx['quedan'] = int(getattr(liga, 'num_jornadas', 0) or 0) - ctx['jornada'] + 1
            ctx['diferencia_lider'] = getattr(tabla[0], 'puntos', 0) - getattr(mi, 'puntos', 0)
    except Exception as e:
        logger.error(f"prensa: no se pudo leer el contexto de la conferencia: {e}")
    return ctx


def _motivo_contextual(ctx: dict, fase: str) -> Optional[str]:
    """Los motivos de contexto (v0.4.25.0), por prioridad. Se llaman solo cuando no hay título, descenso ni liderato."""
    n, puesto, rival, jornada = ctx['n'], ctx['puesto'], ctx['rival_puesto'], ctx['jornada']
    if jornada == 1:
        return 'debut'
    if 0 < ctx['quedan'] <= 2:
        return 'cierre'
    if ctx['derrotas'] >= RACHA_MALA or ctx['sin_ganar'] >= SIN_GANAR:
        return 'racha_mala'
    if ctx['racha'] >= RACHA_BUENA:
        return 'racha_buena'
    if fase == 'pre' and ctx['lesionados'] >= MIN_LESIONADOS:
        return 'lesionados'
    if jornada >= 4 and puesto and rival:
        if puesto <= 4 and rival >= n - 3:
            return 'favorito'
        if puesto > n // 2 and rival <= 3:
            return 'david'
        if abs(puesto - rival) == 1 and (puesto <= 4 or puesto >= n - 4):
            return 'rival_directo'
    if jornada >= 5 and ctx['goles_figura'] >= MIN_GOLES_FIGURA:
        return 'figura'
    return None


def motivo_partido(estado: dict, local, visitante, modo: str, pos: Optional[int] = None,
                   fase: str = 'pre') -> Optional[str]:
    """Por qué este partido merece una conferencia (o None). `pos` pisa el puesto de liga del user (el post-partido
    usa el de antes del partido). Nunca en amistosos. Los motivos de tabla solo valen en liga; en copa, la final y
    la semifinal tienen los suyos y cualquier otra ronda es 'copa_ronda'. `fase` ('pre' | 'post'): la enfermería
    llena solo se pregunta en la previa."""
    try:
        if modo == 'amistoso':
            return None
        if modo == 'copa':
            fase_copa = str((estado.get('partido_copa_dict') or {}).get('fase', '')).lower()
            if re.search(r'\bfinal\b', fase_copa):
                return 'copa_final'
            if 'semi' in fase_copa:
                return 'copa_semi'
        from alpha_football.data.clasicos import es_clasico
        if es_clasico(local, visitante):
            return 'clasico'
        if modo == 'copa':
            return 'copa_ronda'
        if modo != 'liga':
            return None
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None or not getattr(liga, 'equipos', None):
            return None
        ctx = contexto(estado, local, visitante, modo, pos)
        puesto, n, jornada, quedan = ctx['puesto'], ctx['n'], ctx['jornada'], ctx['quedan']
        if not puesto:
            return None
        diferencia = ctx.get('diferencia_lider', 0)
        if quedan <= 6 and (puesto == 1 or diferencia <= 3):
            return 'titulo'
        if getattr(liga, 'division', 1) == 1 and puesto >= n - 1 and jornada >= 4:
            return 'descenso'
        if puesto == 1 and jornada >= 4:
            return 'lider'
        return _motivo_contextual(ctx, fase)
    except Exception as e:
        logger.error(f"prensa: no se pudo evaluar el motivo del partido: {e}")
    return None


def _marcas(ctx: Optional[dict], club: str, rival: str) -> dict:
    """Las marcas {…} de las preguntas con su texto (con valores por defecto que suenan bien si falta el dato)."""
    ctx = ctx or {}
    return {'rival': rival, 'club': club, 'jugador': ctx.get('jugador') or "tu goleador",
            'fase': ctx.get('fase') or "la copa", 'puesto': f"{ctx.get('puesto') or '?'}º",
            'racha': str(ctx.get('racha') or RACHA_BUENA), 'lesionados': str(ctx.get('lesionados') or MIN_LESIONADOS)}


def _pregunta(motivo: str, fase: str, resultado: Optional[str], clave: str, club: str, rival: str,
              ctx: Optional[dict] = None) -> dict:
    """La pregunta (determinista por partido y fase) con sus marcas ya rellenadas."""
    grupo = BANCO[motivo]['pre'] if fase == 'pre' else BANCO[motivo]['post'][resultado or 'empata']
    q = copy.deepcopy(random.Random(f"{clave}:{fase}").choice(grupo))
    marcas = _marcas(ctx, club, rival)
    # el elogio solo sube la moral de tu figura si la pregunta habla de ella ({jugador}); si no, es para el plantel
    q['usa_jugador'] = any('{jugador}' in t for t in [q['texto'], *q['respuestas'].values()])

    def _llenar(texto: str) -> str:
        for k, v in marcas.items():
            texto = texto.replace('{' + k + '}', v)
        return texto
    q['texto'] = _llenar(q['texto'])
    q['respuestas'] = {t: _llenar(x) for t, x in q['respuestas'].items()}
    return q


def evaluar_pre(estado: dict, local, visitante, modo: str) -> Optional[dict]:
    """Arma (y deja en estado['prensa_overlay']) la conferencia previa si el partido la merece y no se hizo ya.
    Es barata de llamar en cada cuadro: el resultado de la evaluación se recuerda por partido."""
    try:
        if modo == 'amistoso' or local is None or visitante is None:
            return None
        clave = _clave(estado, local, visitante, modo)
        if _ya_hecha(estado, clave, 'pre'):              # respondida o saltada (su overlay, si sigue, lo cierra la UI)
            return None
        ov = estado.get('prensa_overlay')
        if ov and ov.get('clave') == clave and ov.get('fase') == 'pre':
            return ov
        if estado.get('prensa_pre_visto') == clave:      # ya se vio que este partido no tiene motivo
            return None
        estado.pop('prensa_overlay', None)               # una conferencia de otro partido que quedó colgada
        motivo = motivo_partido(estado, local, visitante, modo, fase='pre')
        if not motivo or not (BANCO.get(motivo) or {}).get('pre'):
            estado['prensa_pre_visto'] = clave
            return None
        mi, rival = estado.get('mi_equipo'), _rival_de(estado, local, visitante)
        club, nombre_rival = getattr(mi, 'nombre', 'tu club'), getattr(rival, 'nombre', 'el rival')
        dt = _nombre_dt(estado, rival)
        frase = random.Random(f"{clave}:dt").choice(DECLARACIONES_RIVAL).replace('{club}', club)
        ctx = contexto(estado, local, visitante, modo)
        pregunta = _pregunta(motivo, 'pre', None, clave, club, nombre_rival, ctx)
        pregunta_jugador = bool(pregunta.get('usa_jugador'))
        estado['prensa_overlay'] = {
            'fase': 'pre', 'clave': clave, 'modo': modo, 'motivo': motivo,
            'pregunta': pregunta,
            'jugador': ctx.get('jugador', '') if pregunta_jugador else '',
            'jugador_id': ctx.get('jugador_id', '') if pregunta_jugador else '',
            'rival': nombre_rival, 'rival_id': str(getattr(rival, 'id', '')), 'club': club,
            'dt_rival': dt or f"El entrenador de {nombre_rival}", 'declaracion': frase,
            'resultado': None, 'marcador': None, 'respuesta': None}
        return estado['prensa_overlay']
    except Exception as e:
        logger.error(f"prensa: no se pudo armar la conferencia previa: {e}", exc_info=True)
        return None


def evaluar_post(estado: dict, local, visitante, gl: int, gv: int, modo: str,
                 pos_antes: Optional[int] = None) -> Optional[dict]:
    """Conferencia de después del partido (el resultado ya está jugado). `pos_antes` = puesto de liga antes del partido."""
    try:
        if modo == 'amistoso' or local is None or visitante is None:
            return None
        clave = _clave(estado, local, visitante, modo)
        if _ya_hecha(estado, clave, 'post'):
            return None
        motivo = motivo_partido(estado, local, visitante, modo, pos=pos_antes, fase='post')
        mi, rival = estado.get('mi_equipo'), _rival_de(estado, local, visitante)
        es_local = _es_mi(estado, local)
        gf, gc = (int(gl), int(gv)) if es_local else (int(gv), int(gl))
        resultado = 'gana' if gf > gc else ('pierde' if gf < gc else 'empata')
        if abs(gf - gc) >= UMBRAL_GOLEADA and (motivo is None or motivo in _BAJA_PRIORIDAD):
            motivo = 'goleada_favor' if gf > gc else 'goleada_contra'      # el marcador manda sobre el contexto menor
        if not motivo or not (BANCO.get(motivo, {}).get('post') or {}).get(resultado):
            return None
        club, nombre_rival = getattr(mi, 'nombre', 'tu club'), getattr(rival, 'nombre', 'el rival')
        ctx = contexto(estado, local, visitante, modo, pos_antes)
        pregunta = _pregunta(motivo, 'post', resultado, clave, club, nombre_rival, ctx)
        pregunta_jugador = bool(pregunta.get('usa_jugador'))
        estado['prensa_overlay'] = {
            'fase': 'post', 'clave': clave, 'modo': modo, 'motivo': motivo,
            'pregunta': pregunta,
            'jugador': ctx.get('jugador', '') if pregunta_jugador else '',
            'jugador_id': ctx.get('jugador_id', '') if pregunta_jugador else '',
            'rival': nombre_rival, 'rival_id': str(getattr(rival, 'id', '')), 'club': club,
            'dt_rival': None, 'declaracion': None,
            'resultado': resultado, 'marcador': f"{gf}-{gc}", 'respuesta': None}
        return estado['prensa_overlay']
    except Exception as e:
        logger.error(f"prensa: no se pudo armar la conferencia posterior: {e}", exc_info=True)
        return None


# ------------------------------------------------------------------ efectos
def _siguiente_rival(estado: dict):
    """El rival de tu próximo partido de liga sin jugar (None si no queda ninguno)."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        actual = estado.get('partido_actual')
        pendientes = [p for p in getattr(liga, 'calendario', []) or []
                      if not getattr(p, 'jugado', False) and p is not actual
                      and mi.id in (p.local_id, p.visitante_id)]
        if not pendientes:
            return None
        p = min(pendientes, key=lambda x: x.jornada)
        return _buscar_equipo(estado, p.visitante_id if p.local_id == mi.id else p.local_id)
    except Exception as e:
        logger.error(f"prensa: no se pudo ubicar al siguiente rival: {e}")
        return None


def _castigar(estado: dict, equipo, delta: int) -> None:
    """Baja la moral del plantel rival y anota lo que de verdad bajó cada uno (el tope de 0 no regala moral al devolver)."""
    antes = {str(getattr(j, 'id', id(j))): int(j.moral) for j in equipo.jugadores}
    mover_moral(equipo.jugadores, delta)
    devolver = _prensa(estado)['moral_rival'].setdefault(str(equipo.id), {})
    for j in equipo.jugadores:
        cambio = int(j.moral) - antes[str(getattr(j, 'id', id(j)))]
        if cambio:
            clave_j = str(getattr(j, 'id', id(j)))
            devolver[clave_j] = int(devolver.get(clave_j, 0)) + cambio


def _publicar(estado: dict, titular: str, cuerpo: str, importancia: int, clave: str, equipos) -> None:
    from alpha_football import noticias as _n
    _n.publicar(estado, 'declaracion', titular, cuerpo, importancia=importancia, categoria='prensa',
                equipos=equipos, clave=clave)


def _titular_de(tono: str, club: str, objetivo: str, jugador: str = '') -> str:
    from alpha_football import noticias as _n
    elogio = ((f"El DT de {club} elogia a {jugador}", f"{club}: el DT elogia a {jugador}")
              if jugador else ())
    formas = {
        'motivador': (f"El DT de {club} levanta la moral del vestuario", f"{club}: el DT levanta la moral"),
        'provocador': (f"El DT de {club} provoca a {objetivo}", f"{club} provoca al rival"),
        'humilde': (f"El DT de {club} pide humildad y respeto", f"{club}: el DT pide humildad"),
        'agresivo': (f"El DT de {club} promete un partido muy duro", f"{club}: promete un partido duro"),
        'ironico': (f"El DT de {club} responde con ironía", f"{club}: el DT ironiza"),
        'diplomatico': (f"El DT de {club} pide calma y respeto", f"{club}: el DT pide calma"),
        'elogioso': elogio + (f"El DT de {club} elogia a su plantel", f"{club}: el DT elogia al plantel"),
        'evasivo': (f"El DT de {club} evita responder", f"{club}: el DT evita hablar"),
    }[tono]
    return _n.titular(*formas)


def _jugador_de(estado: dict, conf: dict):
    """El jugador de tu plantel por el que preguntaron (None si la pregunta no lo menciona)."""
    jid = str(conf.get('jugador_id') or '')
    mi = estado.get('mi_equipo')
    if not jid or mi is None:
        return None
    return next((j for j in getattr(mi, 'jugadores', None) or [] if str(getattr(j, 'id', '')) == jid), None)


def responder(estado: dict, conferencia: Optional[dict] = None, tono: str = 'humilde') -> dict:
    """Aplica los efectos del tono elegido, publica la declaración y deja la respuesta en la conferencia.
    Devuelve {'texto': lo que dijiste, 'efectos': [qué cambió]}. Responder dos veces no aplica nada más."""
    vacio = {'texto': '', 'efectos': []}
    try:
        conf = conferencia if conferencia is not None else estado.get('prensa_overlay')
        if not conf or tono not in TONOS or tono not in (conf.get('pregunta') or {}).get('respuestas', {}):
            return vacio
        if conf.get('respuesta'):
            return conf['respuesta']
        mi = estado.get('mi_equipo')
        club, rival = conf.get('club') or getattr(mi, 'nombre', 'tu club'), conf.get('rival', 'el rival')
        texto = conf['pregunta']['respuestas'][tono]
        efectos, objetivo_nombre = [], rival
        if conf['fase'] == 'pre' and conf.get('declaracion') and mi is not None:
            if tono == 'diplomatico':             # responder con altura le quita el golpe a las palabras del DT rival
                efectos.append(f"Respondes con calma: las palabras de {conf['dt_rival']} no afectan a tu vestuario")
            else:
                mover_moral(mi.jugadores, _MORAL_POR_DT_RIVAL)
                efectos.append(f"Las palabras de {conf['dt_rival']} te cuestan {_MORAL_POR_DT_RIVAL} de moral")
            from alpha_football import noticias as _n
            _publicar(estado, _n.titular(f"{conf['dt_rival']} manda un mensaje antes del partido",
                                         f"El DT de {rival} manda un mensaje"),
                      f"{conf['dt_rival']}, entrenador de {rival}: «{conf['declaracion']}»", 2,
                      f"prensa:{conf['clave']}:dt", [mi, conf.get('rival_id')])
        if tono in _MORAL_PROPIA and mi is not None:
            mover_moral(mi.jugadores, _MORAL_PROPIA[tono])
            efectos.append(f"+{_MORAL_PROPIA[tono]} de moral en tu plantel")
        if tono in ('provocador', 'ironico'):
            delta = _MORAL_RIVAL if tono == 'provocador' else _MORAL_RIVAL_IRONICO
            objetivo = (_buscar_equipo(estado, conf.get('rival_id')) if conf['fase'] == 'pre'
                        else _siguiente_rival(estado))
            if objetivo is not None and getattr(objetivo, 'jugadores', None):
                _castigar(estado, objetivo, delta)
                objetivo_nombre = objetivo.nombre
                efectos.append(f"{delta} de moral en {objetivo.nombre} hasta que juegues contra ellos")
            elif tono == 'provocador':
                efectos.append("No te queda un rival al que provocar")
        elif tono == 'agresivo':
            _prensa(estado)['tension'] = FACTOR_TENSION
            efectos.append("Más tarjetas en tu próximo partido, para los dos equipos")
        elif tono == 'elogioso' and mi is not None:
            figura = _jugador_de(estado, conf)
            if figura is not None:
                mover_moral([figura], _MORAL_ELOGIO)
                nombre_figura = getattr(figura, 'apellido', '') or getattr(figura, 'nombre', '')
                efectos.append(f"+{_MORAL_ELOGIO} de moral en {nombre_figura}")
            else:
                mover_moral(mi.jugadores, 1)
                efectos.append("+1 de moral en tu plantel")
        elif tono == 'evasivo':
            efectos.append("No dices nada que pueda traerte problemas")
        if conf['fase'] == 'pre':
            cuando = f"Antes del partido ante {rival} ({MOTIVO_TEXTO[conf['motivo']].lower()})"
        else:
            verbo = {'gana': "ganar", 'empata': "empatar", 'pierde': "perder"}[conf['resultado']]
            cuando = f"Tras {verbo} {conf['marcador']} ante {rival}"
        _publicar(estado, _titular_de(tono, club, objetivo_nombre, conf.get('jugador') if tono == 'elogioso' else ''),
                  f"{cuando}, el DT de {club} dijo: «{texto}»", _IMPORTANCIA[tono],
                  f"prensa:{conf['clave']}:{conf['fase']}", [mi, conf.get('rival_id')])
        conf['respuesta'] = {'tono': tono, 'texto': texto, 'efectos': efectos}
        _marcar_hecha(estado, conf['clave'], conf['fase'])
        return conf['respuesta']
    except Exception as e:
        logger.error(f"prensa: no se pudo responder la conferencia: {e}", exc_info=True)
        return vacio


def saltar(estado: dict) -> None:
    """Cierra la conferencia sin efectos (o, si ya respondiste, la cierra tras ver las consecuencias)."""
    try:
        ov = estado.pop('prensa_overlay', None)
        if ov and ov.get('clave'):
            _marcar_hecha(estado, ov['clave'], ov['fase'])
    except Exception as e:
        logger.error(f"prensa: no se pudo cerrar la conferencia: {e}")


def factor_tarjetas(estado: dict) -> float:
    """1.0 sin tensión o en un amistoso; FACTOR_TENSION si una respuesta agresiva sigue pendiente. Nunca lanza."""
    try:
        if estado.get('match_mode') == 'amistoso':
            return 1.0
        pr = (estado.get('datos_carrera') or {}).get('prensa') or {}
        return float(FACTOR_TENSION) if float(pr.get('tension') or 0) > 1.0 else 1.0
    except Exception as e:
        logger.error(f"prensa: no se pudo leer la tensión: {e}")
        return 1.0


def consumir_tension(estado: dict) -> None:
    """Al terminar un partido oficial del user: se acaba la tensión y el rival recupera la moral que le quitó el
    Provocador (los clubes de la IA no recalculan moral: sin esto el castigo sería permanente)."""
    try:
        pr = _prensa(estado)
        pr['tension'] = 0
        devoluciones, pr['moral_rival'] = pr['moral_rival'], {}
        for club_id, por_jugador in devoluciones.items():
            equipo = _buscar_equipo(estado, club_id)
            for j in (getattr(equipo, 'jugadores', None) or []):
                d = por_jugador.get(str(getattr(j, 'id', id(j))))
                if d:
                    j.moral = max(0, min(100, int(j.moral) - int(d)))
    except Exception as e:
        logger.error(f"prensa: no se pudo cerrar la tensión del partido: {e}", exc_info=True)
