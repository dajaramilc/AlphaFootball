# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Banco de la rueda de prensa según la situación real del partido (v0.4.27.0).
Solo datos (nada de lógica, nada de pygame): `prensa.py` los fusiona con su BANCO.

- BANCO_CONTEXTO: motivos nuevos. Copa: fase de liga / de grupos (`grupos*`), ida y vuelta de las eliminatorias
  (`copa_ida`, `vuelta_*`, `copa_penales`). Liga: último partido y título / descenso matemáticos (`titulo_cerca`,
  `campeon_ya`, `descendido`, `ultima_jornada`, `salvado`).
- 'post' va por resultado del partido (gana | empata | pierde) salvo los motivos de copa que se deciden por la
  eliminatoria (`copa_penales`, `vuelta_remontada_ok`, `vuelta_ventaja_perdida`): ahí 'gana' = tú avanzas y
  'pierde' = quedas fuera. 'cualquiera' sirve si el resultado no importa; 'campeon_sin_ganar' es el título cerrado
  sin ganar el partido.
- Marcas: {rival}, {club}, {fase} y {ida} (el marcador de la ida desde tu lado, p. ej. "2-0").
- DECLARACIONES_*: lo que dice el DT rival en la previa ({club} = tu club).
"""
from __future__ import annotations

from alpha_football.prensa_banco import _q


BANCO_CONTEXTO = {
    # ------------------------------------------------------------------ copa: fase de liga / de grupos
    'grupos': {
        'pre': [
            _q("Arranca un nuevo partido de la primera fase de la copa. ¿Qué espera del equipo?",
               m="Que compita con ambición. Queremos meternos en las eliminatorias y cada punto cuenta.",
               h="Que sea serio y constante. En esta fase no se gana nada, pero se puede perder todo.",
               i="Que no se despiste: aquí los puntos se cuentan de uno en uno y se echan mucho de menos.",
               s="Que haga su trabajo. De la clasificación hablaremos cuando toque."),
            _q("{rival} es el siguiente en la primera fase. ¿Qué tan importante es este partido?",
               a="Muy importante. Cada punto de esta fase puede ser el que nos clasifique o nos deje fuera.",
               d="Como todos: hay que respetar al rival y sumar con inteligencia.",
               p="Lo importante lo decidimos nosotros. {rival} tendrá que adaptarse a nuestro ritmo.",
               e="Un rival de nivel. Merece respeto y exige lo mejor de mis jugadores."),
        ],
        'post': {
            'gana': [
                _q("Victoria en la primera fase de la copa. ¿Qué lectura hace del partido?",
                   m="Muy buena: el equipo compitió con personalidad y se lleva tres puntos que valen oro.",
                   h="Tres puntos importantes, pero quedan partidos. Esto no se ha terminado.",
                   e="Los jugadores estuvieron a la altura de la competición. Les felicito por su entrega.",
                   s="Los tres puntos, que es lo que cuenta. Mañana analizaremos el partido con calma."),
                _q("Ganan a {rival}. ¿Les acerca a la clasificación?",
                   d="Nos acerca, sí, pero la clasificación se decide al final. Sin euforia.",
                   p="Nos acerca, y le recordamos a {rival} que aquí no venimos de paso.",
                   a="Hay que seguir así. Si queremos pasar, hay que ganar los partidos que se puedan ganar.",
                   i="Algo más cerca, sí. Ahora a descansar, que este camino es largo."),
            ],
            'empata': [
                _q("Empate en la primera fase de la copa. ¿Es un punto que suma o que quita?",
                   h="Suma, pero sabe a poco. En esta fase cada punto cuenta y hay que pelear por más.",
                   m="Suma. Compitiendo así, los tres puntos llegarán pronto.",
                   a="Quita. Veníamos a ganar y no podemos regalar puntos en esta competición.",
                   d="Es un resultado justo ante un rival de nivel. Seguimos sumando."),
                _q("Reparto de puntos con {rival}. ¿Qué le faltó al equipo?",
                   p="Nada. {rival} jugó a no perder y se llevó un punto que no le correspondía.",
                   i="Un gol más. Siempre es lo que falta cuando se empata, ¿no?",
                   s="Prefiero dejarlo para el análisis del cuerpo técnico. No voy a adelantar conclusiones.",
                   e="Los jugadores lo dieron todo. Quizá faltó un poco de fortuna en las áreas."),
            ],
            'pierde': [
                _q("Derrota en la primera fase de la copa. ¿Cómo queda la clasificación?",
                   h="Complicada, no lo voy a negar. Hay que corregir errores y recuperar puntos pronto.",
                   m="Abierta todavía. Con esta plantilla y lo que queda, hay tiempo de reaccionar.",
                   a="Mal. No se puede perder así y toca responder con otra cara.",
                   d="Es un golpe, pero la fase es larga. Hay que mantener la calma y trabajar."),
                _q("Pierden ante {rival}. ¿Hay motivos para la preocupación?",
                   s="No es el momento de sacar conclusiones. Primero hay que ver el partido con tranquilidad.",
                   p="Preocupación, ninguna. {rival} ganó hoy, pero esta fase es larga y nos volveremos a ver.",
                   i="Siempre hay motivos para preocuparse en el fútbol. Para eso nos pagan, ¿no?",
                   e="Confío en mis jugadores. Un tropiezo no borra lo que han hecho en esta competición."),
            ],
        },
    },
    # Vas primero en tu grupo (o en la tabla de la fase de liga) y todavía no tienes el pase asegurado.
    'grupos_lider': {
        'pre': [
            _q("Son líderes de la primera fase de la copa. ¿Cómo gestionan ese puesto?",
               m="Con orgullo: es el premio al trabajo. Y con hambre, porque el liderato se defiende ganando.",
               h="Con humildad. Es una foto del momento y todavía queda mucho por decidir.",
               i="Con la naturalidad de quien sabe que el liderato dura hasta el siguiente partido.",
               a="Con exigencia. Los líderes no pueden relajarse: el que afloja se queda atrás."),
            _q("{rival} quiere quitarles el primer puesto. ¿Qué espera?",
               p="Que lo intenten. A este equipo no le quitan nada si juega a lo suyo.",
               d="Un rival respetable. Nos centramos en lo nuestro, que es lo que depende de nosotros.",
               s="Espero un partido de fútbol. Del resto hablaremos cuando haya terminado.",
               e="{rival} es un gran equipo y exige lo mejor de los míos. Merece todo el respeto."),
        ],
        'post': {
            'gana': [
                _q("Ganan y siguen arriba en la primera fase. ¿Qué mensaje manda al resto?",
                   p="Que vengan a quitárnoslo si pueden. Este equipo no regala puntos ni puestos.",
                   m="Que seguimos creciendo. Esto es solo un paso: queremos llegar lejos en la copa.",
                   h="Ninguno. Hay que seguir trabajando: en esta fase todo se puede perder rápido.",
                   e="Que tenemos un grupo de jugadores extraordinario. Merecen todos los elogios."),
                _q("El liderato se afianza. ¿Mira ya a las eliminatorias?",
                   d="Todavía no. Primero hay que cerrar la clasificación y luego pensaremos en lo demás.",
                   a="A lo que viene: cada partido que ganemos nos acerca. No hay otra manera.",
                   i="Solo al calendario, para ver cuándo toca el próximo viaje largo.",
                   s="Hablaré de las eliminatorias cuando estemos clasificados. Hoy, solo tres puntos."),
            ],
            'empata': [
                _q("El líder empata. ¿Se complica el liderato de la primera fase?",
                   h="Un punto es un punto. Seguimos arriba, aunque nos faltó contundencia.",
                   a="Me molesta. Teníamos que ganar y hay que ser más fuertes en las áreas.",
                   d="No tanto. Seguimos arriba y el equipo compitió bien ante un rival complicado.",
                   p="{rival} se llevó un punto con un partido a la defensiva. El liderato sigue siendo nuestro."),
            ],
            'pierde': [
                _q("El líder cae. ¿Qué responde a quienes dicen que el equipo se desinfla?",
                   m="Que sigan mirando: nos levantaremos. Una derrota no borra lo que hicimos hasta ahora.",
                   h="Que tienen razón en lo que toca: hay que corregir. Y ahora más que nunca, trabajar.",
                   i="Que lo anoten en su libreta y que no se olviden de apuntar también lo anterior.",
                   a="Que se esperen. Esta derrota nos da hambre y el próximo rival lo va a notar."),
            ],
        },
    },
    # Pase a la siguiente ronda asegurado matemáticamente (todavía quedan partidos de la primera fase).
    'grupos_clasificado': {
        'pre': [
            _q("Ya están clasificados para la siguiente ronda. ¿Cómo afronta lo que queda de esta fase?",
               m="Con ambición: queremos acabar lo más arriba posible y llegar fuertes a las eliminatorias.",
               d="Con calma y seriedad. Hay partidos por jugar y no vamos a regalar nada.",
               i="Con la tranquilidad de quien ya tiene el pase y aún le quedan cosas que demostrar.",
               e="Con orgullo por lo logrado. Los jugadores han hecho un trabajo enorme para estar aquí."),
            _q("Con el pase en el bolsillo, ¿rotará la plantilla ante {rival}?",
               s="El once lo verá cuando salga al campo. No adelanto nada.",
               a="Jugará el que mejor esté. Quien salte al campo tendrá que ganarse el puesto.",
               d="Quizá cambiemos algo, pero respetando la competición y al rival.",
               h="Lo mejor para el equipo, que es lo que importa. Hay que cuidar a los que vienen cargados."),
        ],
        'post': {
            'gana': [
                _q("Ganan estando ya clasificados. ¿Qué le dice a la afición?",
                   m="Que gracias por todo. Vamos a seguir con la misma ilusión hasta el final.",
                   h="Que seguimos trabajando. El pase es un paso, y la copa tiene mucho recorrido.",
                   e="Que este equipo merece todo su apoyo. Nos están llevando en volandas.",
                   i="Que no se acostumbren mal: puede parecer fácil, pero no lo es."),
            ],
            'empata': [
                _q("Un empate con el pase asegurado. ¿Es un punto que sirve?",
                   d="Sirve para mantener el puesto y llegar a las eliminatorias en buen momento.",
                   a="Sirve de poco: queríamos ganar y acabar arriba. Es lo que exige este equipo.",
                   s="Clasificados o no, todos los puntos se pelean. No hay más que decir.",
                   h="Un punto siempre suma. Hay que mejorar y apurar los puestos de arriba."),
            ],
            'pierde': [
                _q("Pierden con la clasificación asegurada. ¿Le preocupa la confianza del equipo?",
                   m="Para nada. Este grupo sabe lo que vale y llegará fuerte a la siguiente fase.",
                   h="Un poco: no es la imagen que queremos dar. Hay que corregir antes de las eliminatorias.",
                   i="Mucho: toda derrota es una lección. Menos mal que ya estamos clasificados.",
                   a="No se puede llegar a las eliminatorias con esta imagen. Lo vamos a corregir."),
            ],
        },
    },
    # A un resultado de quedar eliminados (una derrota los dejaría fuera) o fuera de los puestos que pasan.
    'grupos_peligro': {
        'pre': [
            _q("Están a un paso de quedar eliminados. ¿Qué se juega el equipo?",
               m="Todo. Y precisamente por eso saldremos a ganar con el corazón. Este equipo no se rinde.",
               h="Mucho. Una derrota sería un golpe duro y hay que evitarla con trabajo.",
               a="La vida. Es una final y la vamos a jugar como tal, sin dar un paso atrás.",
               d="Una oportunidad: con calma y cabeza fría podemos darle la vuelta a la situación."),
            _q("Perder ante {rival} podría dejarles fuera. ¿Cómo maneja la presión?",
               i="Con humor, que es la mejor forma de no volverse loco. Pero muy en serio con el partido.",
               p="La presión la tiene {rival}, que no quiere ser el que nos dé el empujón. Nosotros, a lo nuestro.",
               s="Mi forma de manejarla es no hablar de ella. Prefiero hablar con mis jugadores.",
               e="Con la fe que me dan mis jugadores. Son los mejores compañeros en un momento así."),
        ],
        'post': {
            'gana': [
                _q("Ganan y siguen vivos en la copa. ¿Qué siente?",
                   m="Alivio y orgullo. El equipo mostró carácter y sigue peleando por la clasificación.",
                   h="Mucho alivio, pero aún no hemos hecho nada. Hay que seguir sumando.",
                   i="Que he envejecido diez años en noventa minutos. Pero los puntos valen la pena.",
                   a="Esto es lo que hay que hacer: ganar cuando te lo juegas todo. Y ahora, a más."),
            ],
            'empata': [
                _q("Un empate que deja las cosas en el aire. ¿Cómo lo valora?",
                   d="Un punto que aún nos mantiene con vida, aunque exige mucho más en lo que queda.",
                   h="Un resultado corto. Seguimos vivos, pero necesitamos ganar para depender de nosotros.",
                   a="Insuficiente. Necesitamos ganar y para eso hay que ser mucho más fieros.",
                   s="Hablaremos de cuentas cuando quede claro lo que necesitamos. Hoy, a descansar."),
            ],
            'pierde': [
                _q("Otra derrota cuando se jugaban la vida. ¿Hay margen para la esperanza?",
                   m="Mientras haya una posibilidad, este grupo va a pelear. No hay que dar nada por perdido.",
                   h="Poco, lo reconozco. Pero vamos a luchar hasta que las matemáticas digan lo contrario.",
                   a="Sí, y hay que usarlo. No vamos a bajar los brazos. Esto no se ha terminado.",
                   s="No voy a hacer una valoración en caliente. Primero analizaremos lo sucedido."),
            ],
        },
    },
    # Solo queda una mínima posibilidad matemática de pasar.
    'grupos_milagro': {
        'pre': [
            _q("Solo una mínima opción matemática les mantiene vivos. ¿Cómo se afronta algo así?",
               m="Con fe. Mientras las matemáticas nos dejen respirar, este equipo va a pelear.",
               h="Con realismo: lo tenemos muy difícil. Pero vamos a ir a ganar y a ver qué pasa.",
               i="Con calculadora y rezos. Mi parte es ganar; lo demás ya depende de otros.",
               a="Hay que ganar, y seguir ganando. Si hay una opción, la vamos a ir a buscar."),
            _q("Necesitan ganar y esperar otros resultados. ¿Se siente cómodo así?",
               d="Cómodo no, pero en paz: haremos lo que depende de nosotros y el resto lo decidirá el fútbol.",
               p="Cómodo o no, aquí estamos, y nadie nos va a regalar nada. Ni nosotros a ellos.",
               s="Prefiero no depender de nada que no controle. Hoy solo tenemos un partido que ganar.",
               e="Con los jugadores que tengo, cómodo siempre. Han demostrado que no se rinden."),
        ],
        'post': {
            'gana': [
                _q("Ganan y mantienen vivo el sueño. ¿Cree en el milagro?",
                   m="Creo en este grupo. Si uno cree, el fútbol da sorpresas. Vamos a seguir.",
                   h="Creo en trabajar. Hemos hecho lo que dependía de nosotros y ahora hay que esperar.",
                   i="Creo en lo que veo: tres puntos. Lo del milagro lo dejo para quien tenga mejor fe.",
                   a="El milagro nos lo tenemos que ganar. Esto es un paso, pero hay que seguir ganando."),
            ],
            'empata': [
                _q("Empatan cuando necesitaban ganar. ¿Se acaba la ilusión?",
                   h="Casi, pero no del todo. Mientras haya algo de matemática, seguiremos dando la cara.",
                   d="No voy a dramatizar. El equipo compitió y nos queda el orgullo de llegar hasta el final.",
                   a="Este resultado no nos vale. Nos quedan partidos y vamos a pelearlos hasta el último minuto.",
                   s="No voy a hacer declaraciones sobre eso. Hay que analizar el partido con calma."),
            ],
            'pierde': [
                _q("Con esta derrota, el milagro se aleja. ¿Qué queda por jugar?",
                   h="El orgullo y la dignidad. Hay que despedirse de la competición con la cabeza alta.",
                   m="Queda competir, que es lo que nos ha traído hasta aquí. Y aprender para volver más fuertes.",
                   d="Respetar la competición y a la afición, que no deja de apoyarnos. Eso queda.",
                   i="Queda lo mismo que antes: nada de matemáticas, pero muchísimas ganas de hacerlo bien."),
            ],
        },
    },
    # Eliminados matemáticamente: lo que queda de la primera fase es un trámite.
    'grupos_eliminado': {
        'pre': [
            _q("Ya están eliminados de la copa. ¿Qué le pide al equipo en lo que queda?",
               h="Dignidad. Estamos fuera, pero tenemos camiseta, afición y un nombre que defender.",
               m="Que compitan con orgullo y que aprendamos de lo que no hicimos bien.",
               a="Que no se les ocurra relajarse. Aquí se compite hasta el final, sin excusas.",
               d="Que cierren la competición con seriedad y respeto al rival y a la afición."),
            _q("Sin opciones en la copa, ¿qué sentido tiene el partido ante {rival}?",
               p="El mismo que para {rival}: un partido de fútbol. Y a nosotros nos gusta ganarlos.",
               i="El de siempre: jugar, ganar y volver a casa. Lo demás es literatura.",
               e="El de honrar a nuestra afición, que no merece menos. Daremos todo lo que tengamos.",
               s="Prefiero no analizarlo. Tenemos un partido por delante y lo jugaremos como corresponde."),
        ],
        'post': {
            'gana': [
                _q("Ganan estando ya eliminados. ¿Es un consuelo?",
                   h="Algo, aunque el resultado no cambia lo que ya está escrito. Pero se agradece.",
                   m="Es una forma digna de despedirse y una base para lo que viene. Estoy orgulloso.",
                   i="Un poco, como cuando te dan el postre después de haber perdido la comida.",
                   a="Consuelo, no. Hemos ganado, pero queríamos estar peleando por mucho más."),
            ],
            'empata': [
                _q("Empate sin nada en juego. ¿Qué se lleva de la noche?",
                   d="Que el equipo compitió con seriedad. En estas circunstancias, eso ya es mucho.",
                   s="Poca cosa. La competición ya había terminado para nosotros.",
                   m="Orgullo: hasta el final se respetó la camiseta. Hay que aprender de esto.",
                   i="Un punto en la libreta y un par de ideas para el año que viene."),
            ],
            'pierde': [
                _q("Otra derrota en una copa que ya estaba perdida. ¿Qué responde?",
                   h="Que nos tocó una fase muy complicada y no estuvimos a la altura. Hay que aprender.",
                   a="Que no hay excusas. Estar eliminados no justifica perder y pondremos las cosas en su sitio.",
                   d="Que la competición es así: a veces no sale. Hay que mirar adelante con calma.",
                   s="No tengo nada que decir sobre una competición que ya no es la nuestra."),
            ],
        },
    },

    # ------------------------------------------------------------------ copa: eliminatorias a ida y vuelta
    # Partido de ida (playoff, octavos, cuartos) y, en el postpartido, también el de la ida de una semifinal.
    'copa_ida': {
        'pre': [
            _q("Empieza la eliminatoria ante {rival}: {fase}. ¿Cómo se afronta la ida?",
               m="Con ambición: queremos llegar a la vuelta con ventaja y hacernos fuertes.",
               h="Con prudencia. Una ida no decide nada, pero un mal resultado puede complicarlo todo.",
               d="Con inteligencia: ni lanzarse ni encerrarse. Son 180 minutos y hay que saber gestionarlos.",
               a="A morder desde el primer minuto. Quien llegue a la vuelta con ventaja manda."),
            _q("La eliminatoria es a ida y vuelta. ¿Qué pesa más: no perder o ganar la ida?",
               i="Ganar es importante, pero no volver a casa con la mochila cargada. Lo ideal: ambas.",
               p="Ganar. {rival} tiene que saber que aquí no venimos a especular.",
               s="Eso se lo digo a mi equipo, no a ustedes. Ya me dirán después si acerté.",
               e="Lo importante es jugar bien. Con los jugadores que tengo, confío en cualquier resultado."),
        ],
        'post': {
            'gana': [
                _q("Ganan la ida ante {rival}. ¿Está la eliminatoria encarrilada?",
                   h="Para nada. Falta la vuelta y {rival} sabe sufrir. Hay que ser humildes.",
                   m="Hemos dado un paso importante, pero hay que cerrar el trabajo en la vuelta.",
                   p="Encarrilada no, casi resuelta. {rival} va a tener que remar mucho en la vuelta.",
                   d="Es una buena ventaja, pero la eliminatoria está abierta. Hay que mantener la cabeza fría."),
                _q("Victoria en la ida. ¿Qué cambiaría para la vuelta?",
                   a="Nada de especular. Salir a por ellos como en la ida y cerrar la eliminatoria.",
                   i="Casi nada, solo que el balón siga entrando. No cambio una receta que funciona.",
                   s="Las decisiones tácticas las comentaremos cuando llegue el momento. Hay que descansar.",
                   e="Nada. Los jugadores están haciendo un trabajo enorme y no hay que tocarlos."),
            ],
            'empata': [
                _q("Empate en la ida. ¿Quién sale mejor parado para la vuelta?",
                   d="Nadie, o los dos. La eliminatoria está abierta y todo se decidirá en la vuelta.",
                   m="Nosotros: llegamos con confianza y con la eliminatoria a nuestro alcance.",
                   h="{rival} no ha perdido y nosotros tampoco. Será un partido de máxima igualdad.",
                   a="Da igual. El resultado de la ida no sirve de nada si no ganamos la vuelta."),
                _q("La ida terminó igualada. ¿Qué espera de la vuelta?",
                   p="Una eliminatoria de máxima tensión, y {rival} lo sabe: a nosotros nos favorece.",
                   i="Un partido de los que se juegan con los dientes apretados. Y yo, con los nervios de punta.",
                   s="Prefiero no adelantar nada. Primero analizaremos esta ida con el cuerpo técnico.",
                   e="Un partido de los que le gustan a los futbolistas. Con estos jugadores, voy confiado."),
            ],
            'pierde': [
                _q("Pierden la ida ante {rival}. ¿Queda opción en la vuelta?",
                   m="Muchísima. Estamos vivos y la vuelta nos va a encontrar con muchas ganas de remontar.",
                   h="La tenemos, aunque cuesta arriba. Hay que corregir errores y ser muy precisos.",
                   a="Claro. La eliminatoria no está terminada y vamos a dar el golpe en la vuelta.",
                   i="Más opciones de las que parece. Nadie dijo que el camino fuese fácil, ni corto."),
                _q("Derrota en la ida. ¿Qué mensaje deja a sus jugadores?",
                   d="Que mantengan la calma: es solo la mitad de la eliminatoria y queda mucho por hacer.",
                   p="Que no se achiquen. {rival} no ha ganado nada y en la vuelta se van a dar cuenta.",
                   e="Que confío en ellos. Con esta plantilla, hay equipo para dar la vuelta a esto.",
                   s="Los mensajes son para el vestuario. Aquí no hay nada que añadir."),
            ],
        },
    },
    # Vuelta con ventaja: ganaste la ida ({ida}).
    'vuelta_ventaja': {
        'pre': [
            _q("Llegan con ventaja de la ida ({ida}). ¿Cómo se afronta una vuelta así?",
               h="Con respeto. La ventaja es corta y {rival} jugará con todo. No podemos confiarnos.",
               m="Con confianza: hemos hecho lo más difícil y ahora hay que cerrar el trabajo.",
               d="Con calma y cabeza. Hay que saber sufrir y no dar nada por hecho.",
               a="Sin especular. Hay que salir a ganar la eliminatoria y no a defender un resultado."),
            _q("{rival} necesita remontar. ¿Teme una reacción?",
               p="Que remonten si pueden. Aquí vamos a defender lo nuestro con uñas y dientes.",
               i="Siempre se teme. Pero lo de remontar es fácil de decir y difícil de hacer.",
               s="Prefiero no hablar de miedos. Hablaré de lo que ocurra en el campo.",
               e="Sabemos de lo que es capaz {rival}. Por eso hay que respetarlos al máximo."),
        ],
        'post': {},
    },
    # Vuelta a remontar: perdiste la ida ({ida}).
    'vuelta_remontada': {
        'pre': [
            _q("Perdieron la ida ({ida}). ¿Cómo se prepara una remontada?",
               m="Con fe. Este equipo ha demostrado que puede con todo. Les vamos a dar la vuelta.",
               a="Salir a por ellos desde el primer minuto. Hay que ser valientes y no dar un paso atrás.",
               h="Con cabeza y mucho trabajo. Tenemos que ser inteligentes y aprovechar cada ocasión.",
               d="Con serenidad. Hay un camino por recorrer y no podemos precipitarnos."),
            _q("{rival} llega con ventaja. ¿Ve a su equipo capaz de remontar?",
               p="Los veo a ellos nerviosos. Les va a tocar sufrir como no han sufrido nunca.",
               i="Capaz sí. Probable depende de que mis jugadores no escuchen lo que dice la prensa.",
               e="Con estos jugadores, todo es posible. Confío plenamente en ellos.",
               s="Eso se verá en el campo. Aquí nadie va a adelantar nada."),
        ],
        'post': {},
    },
    # Vuelta con la eliminatoria igualada: empataste la ida ({ida}).
    'vuelta_igualada': {
        'pre': [
            _q("La eliminatoria llega igualada ({ida}). ¿Qué decidirá la vuelta?",
               d="Los detalles. En una eliminatoria así, una jugada puntual lo decide todo.",
               m="La personalidad. Vamos a salir a ganar sin miedos y a hacer nuestro partido.",
               i="La suerte, y alguien que meta un gol más que el otro. Es una teoría revolucionaria.",
               a="Las ganas. Quien más quiera esta eliminatoria será el que pase de ronda."),
            _q("Quien gane pasa. ¿Qué le dice a su vestuario antes de la vuelta?",
               h="Que disfruten y que sean ellos mismos. Hay que hacer lo que sabemos, sin ansiedad.",
               p="Que {rival} sabe lo que nos jugamos y que nosotros vamos a ser mejores.",
               s="Eso se lo digo a ellos antes del partido. La prensa se enterará por el resultado.",
               e="Que confío en ellos como en nadie. Ya nos han traído hasta aquí con su trabajo."),
        ],
        'post': {},
    },
    # La eliminatoria (o la final) se definió desde los doce pasos: 'gana' = avanzas / campeón, 'pierde' = fuera.
    'copa_penales': {
        'pre': [],
        'post': {
            'gana': [
                _q("Lo resuelven en los penales y lo ganan. ¿Qué siente en este momento?",
                   m="Una alegría inmensa. Los jugadores tuvieron personalidad en el momento más difícil.",
                   h="Mucha suerte también. Una tanda es una lotería y esta vez nos tocó a nosotros.",
                   i="Que he envejecido cinco años en cinco minutos. Pero con este resultado, valió la pena.",
                   e="Orgullo por los que tiraron y por todos los que sufrieron con ellos. Esto es de todos."),
                _q("Ganan en los penales ante {rival}. ¿Es cuestión de suerte o de preparación?",
                   d="De las dos cosas. Hay trabajo detrás, pero siempre ayuda un poco de fortuna.",
                   a="De carácter. Los penales se ganan con cabeza fría y mucha convicción.",
                   p="De superioridad. {rival} flaqueó cuando más se necesitaba y nosotros no.",
                   s="No voy a analizarlo. El resultado es el que es, y hoy nos favorece."),
            ],
            'pierde': [
                _q("Caen en los penales ante {rival}. ¿Qué sentimiento les queda?",
                   h="Mucho dolor. Hicimos un partido muy serio y el azar de los penales nos dejó fuera.",
                   m="Orgullo por lo que hicieron y pena por lo que no fue. Volveremos más fuertes.",
                   d="Es parte del juego. Hay que levantarse y asumir con respeto lo ocurrido.",
                   a="Rabia. No tiene explicación, pero habrá que ser más fuertes en las áreas."),
                _q("Eliminados en los penales. ¿Se arrepiente de algo?",
                   i="De no haber metido un gol más en los 90 minutos. Es una solución mucho más cómoda.",
                   s="Prefiero esperar a repasar el partido para valorarlo. No voy a hacerlo en caliente.",
                   e="De nada. Mis jugadores lo dieron todo y no se les puede reprochar nada.",
                   p="De nada. {rival} pasa, pero no fue superior. Nos vamos con la cabeza alta."),
            ],
        },
    },
    # Pasas la eliminatoria tras perder la ida.
    'vuelta_remontada_ok': {
        'pre': [],
        'post': {
            'gana': [
                _q("¡Remontada! Dieron la vuelta a la eliminatoria. ¿Qué significa para el equipo?",
                   m="Es la prueba de que este grupo no se rinde nunca. Hoy hicimos historia.",
                   h="Un mérito enorme de los jugadores. Fuimos mejores que nunca cuando más hacía falta.",
                   p="Que {rival} tome nota: con este equipo no hay nada decidido hasta el último minuto.",
                   e="Es de los jugadores. Su esfuerzo y su fe nos han traído hasta aquí."),
                _q("Pasan de ronda tras perder la ida. ¿Qué cambió en la vuelta?",
                   a="La actitud. Salimos con otra cara, con hambre, y se notó desde el primer balón.",
                   d="Hubo ajustes y mucha paciencia. Supimos esperar el momento y aprovecharlo.",
                   i="El resultado de la ida, por suerte. Aunque no lo había planeado así.",
                   s="No voy a desvelar los secretos del vestuario. Lo importante es el resultado."),
            ],
        },
    },
    # Quedas fuera de la eliminatoria pese a haber ganado la ida.
    'vuelta_ventaja_perdida': {
        'pre': [],
        'post': {
            'pierde': [
                _q("Eliminados pese a ganar la ida. ¿Cómo se explica algo así?",
                   h="Cometimos errores que no podíamos permitirnos. Es un golpe muy duro y hay que asumirlo.",
                   m="Es una lección muy dura. Pero la temporada sigue y este grupo sabrá levantarse.",
                   a="No tiene perdón. Teníamos la eliminatoria en la mano y la dejamos escapar.",
                   s="Prefiero no hacer valoraciones en caliente. Habrá que revisar el partido con calma."),
                _q("Tenían la ventaja de la ida y se les escapó. ¿Qué falló?",
                   d="La gestión de los momentos. Hubo minutos clave en los que no estuvimos a la altura.",
                   i="Un detalle sin importancia: no marcamos más que ellos. Por lo demás, todo bien.",
                   p="Nada que ver con el juego: {rival} tuvo suerte hoy, pero lo suyo no fue mérito.",
                   e="Nada de eso. Mis jugadores lo dieron todo. A veces el fútbol es injusto con los valientes."),
            ],
        },
    },

    # ------------------------------------------------------------------ liga: título, descenso y último partido
    # Puedes asegurar el título con este partido (si ganas, ya no te alcanza nadie).
    'titulo_cerca': {
        'pre': [
            _q("Si ganan hoy, pueden asegurar el título. ¿Cómo se afronta un partido así?",
               m="Con ilusión y la cabeza fría. Hemos trabajado todo el año para tener esta oportunidad.",
               h="Con respeto. Falta el último paso, y ese es siempre el más difícil de dar.",
               a="A por todas. Si lo tenemos al alcance, hoy hay que cerrarlo y no dejarlo para después.",
               d="Con serenidad. Es un partido más y hay que jugarlo como todos los demás."),
            _q("El título puede decidirse contra {rival}. ¿Siente que el equipo está listo?",
               p="Más que listo. {rival} sabe que hoy no hay quien nos pare.",
               i="Listo está. Yo, no tanto: llevo semanas sin dormir bien y el café ya no me hace efecto.",
               s="Eso se verá en la cancha. No voy a hacer más declaraciones antes del partido.",
               e="Con estos jugadores, siempre. Merecen disfrutar de un partido así y lo van a hacer."),
        ],
        'post': {
            'gana': [
                _q("¡Campeones de liga! ¿Qué significa este título para usted y para el club?",
                   m="Lo es todo. Un año de trabajo, de esfuerzo y de confianza. Este título es de todos.",
                   h="Un sueño hecho realidad gracias a los jugadores y a la afición. Estoy muy agradecido.",
                   p="Es para los que dudaron. Y para {rival}: hoy la fiesta es nuestra.",
                   e="Es para los jugadores, que son los verdaderos campeones. Ellos se lo han ganado."),
            ],
            'campeon_sin_ganar': [
                _q("No ganaron, pero son campeones por los resultados. ¿Cómo se vive algo así?",
                   i="Con una sonrisa de oreja a oreja y un poco de confusión. Pero con el título en la mano.",
                   h="Con humildad: no fue el partido que queríamos, pero el título es de este grupo.",
                   m="Con una alegría enorme. La temporada ha sido espectacular y esto es la guinda.",
                   d="Con serenidad y gratitud. Ahora toca celebrar, con la cabeza alta."),
            ],
            'empata': [
                _q("No pudieron cerrar el título hoy. ¿Qué pasa por la cabeza del equipo?",
                   m="Que sigue dependiendo de nosotros. Vamos a ir a por el título sin darle más vueltas.",
                   h="Un poco de decepción, pero hay que levantar la cabeza. El próximo partido es otra final.",
                   a="Que hay que ser más contundentes. Teníamos que ganar y no lo conseguimos.",
                   d="Calma. Todavía dependemos de nosotros y eso es lo más importante."),
            ],
            'pierde': [
                _q("Pierden y el título tendrá que esperar. ¿Les pesa la presión?",
                   h="Un poco, no lo voy a negar. Pero es parte de pelear por cosas grandes.",
                   m="No. Seguimos al frente y el equipo tiene fuerza para cerrarlo en lo que queda.",
                   a="Vamos a responder. El título sigue siendo nuestro y no lo vamos a soltar.",
                   s="No voy a hablar de presión. Hay que trabajar y mirar al siguiente partido."),
            ],
        },
    },
    # Ya eres campeón matemático: el partido ya no se juega por el título.
    'campeon_ya': {
        'pre': [
            _q("Ya son campeones. ¿Cómo mantiene la motivación en lo que queda?",
               m="Con orgullo. Queremos cerrar la temporada a la altura de lo que hemos conseguido.",
               h="Recordando que un campeón se demuestra todos los partidos. No hay que relajarse.",
               i="Prometiéndoles que si se relajan, mañana entrenamos doble. Funciona de maravilla.",
               e="Con el agradecimiento a esta afición. Se merecen una temporada redonda hasta el final."),
            _q("Con el título en el bolsillo, ¿habrá rotaciones ante {rival}?",
               d="Veremos. Hay que cuidar a los que vienen cargados y dar minutos a los que lo merecen.",
               a="Jugará el que esté mejor. En este club, nadie tiene el puesto asegurado.",
               s="El once se sabrá cuando salga. No voy a adelantar nada.",
               p="Jugará quien tenga que jugar. {rival} va a tener que esforzarse igual."),
        ],
        'post': {
            'gana': [
                _q("El campeón sigue ganando. ¿Se plantea batir algún récord?",
                   m="Nos ilusiona. Queremos acabar con la mejor temporada de la historia del club.",
                   h="No pienso en eso. Voy partido a partido, con la humildad de siempre.",
                   i="Mientras mis jugadores no se aburran, lo planteo todo. Hasta ganar la liga otra vez.",
                   s="Ni lo planteo ni lo descarto. Hablamos al final del curso."),
            ],
            'empata': [
                _q("El campeón empata. ¿Se ha relajado el equipo?",
                   h="Quizá un poco. Es normal, pero tenemos que exigirnos en lo que queda.",
                   a="No lo voy a permitir. Un campeón no puede dar estas imágenes.",
                   d="Para nada. Fue un partido igualado ante un rival que compitió bien.",
                   i="Un poco, sí: anoche vi a un jugador preguntar si el título se cobra en efectivo."),
            ],
            'pierde': [
                _q("El campeón pierde. ¿Le preocupa la imagen que deja?",
                   m="No. El título está ganado y esto no lo cambia. Sacaremos lo bueno del partido.",
                   a="Sí, y no voy a permitirlo. Hay que cerrar el curso a la altura de un campeón.",
                   d="Es una derrota sin consecuencias, pero no por eso deja de ser una derrota.",
                   s="No tengo comentarios. Lo importante es lo que se consiguió y eso nadie lo borra."),
            ],
        },
    },
    # Descenso matemático (o consumado en la última jornada).
    'descendido': {
        'pre': [
            _q("El descenso ya es matemático. ¿Cómo afronta los partidos que quedan?",
               h="Con dignidad y trabajo. Se lo debemos a la afición y a la camiseta.",
               m="Con orgullo. Queremos cerrar la temporada compitiendo y empezar a construir lo que viene.",
               d="Con respeto a la competición y a los rivales. Hasta el último partido.",
               s="Prefiero no hablar de eso. Cada cosa tiene su momento y este no lo es."),
            _q("Descendidos ya, ¿qué le dice a la afición ante {rival}?",
               e="Gracias por su apoyo y por su cariño. Se merecen mejores noticias.",
               a="Que vamos a luchar este partido como si se jugara todo, porque la camiseta lo merece.",
               i="Que lamentamos haberles fallado y que no vamos a permitirnos otro mal rato en la cancha.",
               p="Que {rival} no crea que nos tiene a la baja: vamos a pelear cada pelota."),
        ],
        'post': {
            'gana': [
                _q("Ganan con el descenso consumado. ¿Es el principio de la reconstrucción?",
                   h="Esperemos que sí. Hay que pensar en lo bueno y en cómo volver cuanto antes.",
                   m="Lo es. Hay un grupo con ganas de cambiar la historia y volver más fuertes.",
                   d="Es un buen momento para empezar a pensar con calma y en positivo.",
                   a="Esto debía ser lo normal. No nos podemos conformar con ganar partidos intrascendentes."),
            ],
            'empata': [
                _q("Empatan con el descenso consumado. ¿Qué lectura hace?",
                   d="Que hay que cerrar la temporada con dignidad. No se puede hacer más que eso.",
                   h="Una lectura de realismo: no tenemos la calidad suficiente y hay que asumirlo.",
                   s="Ninguna lectura. La temporada acabó hace tiempo para nosotros.",
                   m="Que estamos compitiendo y ese es el mejor camino para empezar de nuevo."),
            ],
            'pierde': [
                _q("Otra derrota con el descenso consumado. ¿Cómo se levanta un equipo así?",
                   h="Con trabajo y humildad. Hay que reconocer los errores y no volver a cometerlos.",
                   m="Con unidad. Este club es mucho más que un mal año y se volverá a levantar.",
                   a="Con exigencia a cada uno. Quien no esté dispuesto a pelear no tiene sitio en este equipo.",
                   d="Con calma y con la vista en el futuro. Hay que construir y no mirar más para atrás."),
            ],
        },
    },
    # Último partido de la liga sin título ni descenso en juego.
    'ultima_jornada': {
        'pre': [
            _q("Último partido de la temporada. ¿Con qué sensación cierran el curso?",
               m="Con orgullo. El equipo ha dado todo y queremos cerrar con una victoria.",
               h="Con sentimientos encontrados. Ha habido cosas buenas y otras que debemos mejorar.",
               i="Con las maletas casi hechas y las ganas intactas. Un último esfuerzo y a las vacaciones.",
               e="Con agradecimiento. Los jugadores y la afición han hecho que valiera la pena el año."),
            _q("Se acaba la liga. ¿Qué balance haría antes de enfrentarse a {rival}?",
               d="Prefiero esperar a que termine. Los balances se hacen con calma y sin el partido en la cabeza.",
               s="Al terminar el partido. Hoy toca jugar y hacerlo bien.",
               h="Positivo en muchas cosas, mejorable en otras. Siempre se puede hacer más.",
               a="No es el momento. Aún quedan 90 minutos y hay que cerrar el año como se debe."),
        ],
        'post': {
            'gana': [
                _q("Cierran la liga con una victoria. ¿Con qué se queda de la temporada?",
                   m="Con el carácter de este grupo. Se ha peleado cada partido y se ha crecido mucho.",
                   h="Con el trabajo diario y con lo que aprendimos. Hay mucho que agradecer.",
                   e="Con la entrega de los jugadores y el cariño de la afición. Han sido increíbles.",
                   i="Con que se acabó. Y con que ganamos el último, que siempre deja mejor sabor de boca."),
            ],
            'empata': [
                _q("Empate en el último partido. ¿Cómo valora la temporada?",
                   d="Con sensaciones mixtas, pero con la satisfacción de haber competido hasta el final.",
                   h="Quizá faltó contundencia en momentos clave. Hay que aprender de ello.",
                   a="Hay mucho que mejorar. Esta temporada nos enseña que hay que exigirse más.",
                   s="Los balances los haremos con tiempo y con el cuerpo técnico. Ahora toca descansar."),
            ],
            'pierde': [
                _q("Cierran el curso con una derrota. ¿Qué mensaje deja a la afición?",
                   h="Que lo sentimos. Este equipo tiene que aprender de lo que pasó y volver mejor.",
                   m="Que seguiremos trabajando. Esta temporada nos deja cosas buenas y mucho aprendizaje.",
                   a="Que el próximo año vamos a venir con más hambre. No nos conformamos con esto.",
                   d="Gracias por su apoyo. Hay que descansar, reflexionar y volver con ilusión."),
            ],
        },
    },
    # Solo postpartido: te salvas del descenso en la última jornada.
    'salvado': {
        'pre': [],
        'post': {
            'cualquiera': [
                _q("¡Salvados en la última jornada! ¿Qué sentimiento prevalece?",
                   h="Alivio y mucho agradecimiento. Hemos sufrido, pero el grupo sacó el carácter.",
                   m="Orgullo. Este equipo nunca bajó los brazos y hoy ha sido recompensado.",
                   i="Que he envejecido diez años esta temporada. Pero merece la pena cada cana.",
                   e="Admiración por mis jugadores. Soportaron una presión enorme y estuvieron a la altura."),
                _q("Se salvan del descenso. ¿Qué cambiaría para la próxima temporada?",
                   d="Muchas cosas, con calma. Hay que aprender de este año y construir sobre una base sólida.",
                   a="Todo lo que sea necesario. No podemos volver a pasar por esto.",
                   s="Hablaremos de eso con la directiva. Ahora es un día para celebrar.",
                   p="Que nadie vuelva a darnos por muertos. Hoy hemos demostrado quiénes somos."),
            ],
        },
    },
}

# Cómo se llama cada motivo nuevo en el overlay (y en la noticia de la declaración).
MOTIVO_TEXTO_CONTEXTO = {
    'grupos': "Primera fase de la copa",
    'grupos_lider': "Líder de la primera fase",
    'grupos_clasificado': "Con el pase asegurado",
    'grupos_peligro': "Al borde de la eliminación",
    'grupos_milagro': "Con una opción matemática",
    'grupos_eliminado': "Ya eliminados de la copa",
    'copa_ida': "Ida de la eliminatoria",
    'vuelta_ventaja': "Vuelta con ventaja",
    'vuelta_remontada': "Vuelta a remontar",
    'vuelta_igualada': "Vuelta de una eliminatoria igualada",
    'copa_penales': "Definición por penales",
    'vuelta_remontada_ok': "Remontada en la vuelta",
    'vuelta_ventaja_perdida': "Ventaja perdida",
    'titulo_cerca': "Con opción de cerrar el título",
    'campeon_ya': "Con el título ya ganado",
    'descendido': "Con el descenso consumado",
    'ultima_jornada': "Última jornada de liga",
    'salvado': "Salvados del descenso",
}


# Lo que dice el DT rival en la previa. DECLARACIONES_GENERALES se suma a las seis de siempre; las de
# DECLARACIONES_POR_MOTIVO salen más a menudo cuando el partido tiene ese motivo (ver prensa._declaracion_rival).
DECLARACIONES_GENERALES = (
    "Respetamos a {club}, pero nosotros salimos a ganar en cualquier campo.",
    "{club} tiene jugadores de mucha calidad. Nuestro plan es no dejarlos jugar cómodos.",
    "Llevamos días trabajando en frenar a {club}. Estamos listos.",
    "Cada partido es una final para nosotros, y contra {club} lo será todavía más.",
    "No nos preocupa {club}. Nos preocupa jugar bien nosotros, y lo demás vendrá solo.",
    "Les vamos a poner las cosas difíciles a {club}. Eso se lo prometo.",
    "Hablar de favoritos es cosa de periodistas. {club} tendrá que sudar para ganarnos.",
    "Para ganar a {club} hay que ser mejores durante noventa minutos, y vamos a serlo.",
    "Hay que tener mucho cuidado con {club}: tienen pegada y saben cómo hacernos daño.",
    "Mi equipo está motivado y confía en sí mismo. {club} lo va a notar desde el primer minuto.",
    "{club} juega bien, pero tiene puntos débiles. Los hemos estudiado muy bien.",
    "El fútbol no entiende de nombres. {club} tendrá que demostrarlo en el campo.",
    "No pienso en lo que diga {club}. Mi equipo sale a imponer sus condiciones.",
    "Vamos a competir de tú a tú con {club}. Sin miedos y sin complejos.",
    "Tenemos mucho respeto por {club}, pero nuestro objetivo es llevarnos los tres puntos.",
    "{club} es un rival incómodo. Por eso mismo nos gusta jugar contra ellos.",
    "Los partidos contra {club} nunca son fáciles, y eso nos motiva todavía más.",
    "Hemos visto muchos vídeos de {club}. Hay cosas que nos gustan y cosas que no les vamos a permitir.",
    "Sabemos lo que es {club}. Ahora toca demostrar lo que somos nosotros.",
    "No le vamos a regalar nada a {club}. Quien quiera los puntos de este partido tendrá que ganárselos.",
    "Estamos preparados para lo que nos plantee {club}. Tenemos nuestra receta y confiamos en ella.",
    "{club} no es invencible. Vamos a intentar ganarles con lo que mejor sabemos hacer.",
    "El partido contra {club} es una gran oportunidad para nosotros. Vamos a aprovecharla.",
    "Los jugadores están enchufados y con ganas de demostrar su nivel ante {club}.",
    "No es un partido más: {club} merece respeto y nosotros, salir a darlo todo.",
    "He pedido a mis jugadores concentración total. {club} castiga cualquier error.",
)

DECLARACIONES_POR_MOTIVO = {
    'copa_final': (
        "Es una final: no hay nada que perder y todo por ganar. {club} no nos va a quitar la copa.",
        "Una final no se juega, se gana. Y nosotros venimos a llevarnos la copa, {club}.",
        "Hemos llegado hasta aquí por méritos propios. {club} tendrá que quitarnos la copa de las manos.",
        "Las finales son de quien más las quiere, y nosotros la queremos más que {club}.",
    ),
    'copa_semi': (
        "Una semifinal es un premio, pero queremos más. {club} no nos va a frenar.",
        "Estar en semifinales es un orgullo, pero no basta. Vamos a por la final.",
        "La semifinal es una oportunidad histórica. {club} debe saber que vamos con todo.",
    ),
    'copa_ronda': (
        "Es copa: no hay segundas oportunidades. {club} lo sabe tan bien como nosotros.",
        "La copa es un sueño y no pensamos soltarlo. {club} tendrá que quitárnoslo.",
    ),
    'copa_ida': (
        "Una ida de eliminatoria: queremos ganar, pero sin perder de vista lo que viene después.",
        "Contra {club} lo importante es llegar vivos a la vuelta, y mejor si es con ventaja.",
        "Son dos partidos con {club}. Hoy toca empezar bien y no cometer errores de novato.",
    ),
    'vuelta_ventaja': (       # el rival es quien tiene que remontar
        "Tenemos que remontar a {club}. Es difícil, pero este equipo ha hecho cosas más difíciles.",
        "Nos toca arriesgar. {club} tiene la ventaja, pero la eliminatoria no está terminada.",
        "No tenemos nada que perder: {club} lleva la ventaja y nosotros, la obligación de remontar.",
    ),
    'vuelta_remontada': (     # el rival llega con ventaja
        "Tenemos ventaja ante {club}, pero no está nada hecho. Esto es una vuelta, y hay que jugarla.",
        "No vamos a especular con el resultado de la ida. Queremos cerrar la eliminatoria con otra victoria.",
        "La ventaja es corta y {club} es peligroso. No podemos confiarnos ni un minuto.",
    ),
    'vuelta_igualada': (
        "Todo abierto con {club}. La vuelta será de máxima tensión y vamos a ir a por ella.",
        "Quien gane pasa. {club} lo sabe y nosotros también: hoy no hay lugar para el error.",
    ),
    'grupos': (
        "La primera fase es larga, pero cada punto con {club} puede valer una clasificación.",
        "No venimos a esta copa de paseo. {club} lo va a comprobar.",
    ),
    'grupos_lider': (
        "{club} manda en la primera fase. Nos toca demostrar que a los líderes también se les gana.",
        "Vamos a por el líder. Un equipo grande se mide ante los mejores, y {club} lo es.",
    ),
    'grupos_clasificado': (
        "{club} ya está clasificado, y eso no nos va a quitar las ganas de ganarle.",
        "Sabemos que {club} puede rotar. Nosotros iremos con lo mejor que tengamos.",
    ),
    'grupos_peligro': (
        "{club} se juega la vida, y eso los hace peligrosos. Hay que estar muy atentos.",
        "Un equipo al borde del precipicio es el más peligroso. No vamos a confiarnos con {club}.",
    ),
    'grupos_milagro': (
        "{club} está contra las cuerdas, y ya sabemos lo que es eso. Vamos a ir a muerte.",
        "Nadie regala nada. {club} tendrá que ganarnos y nosotros no vamos a facilitárselo.",
    ),
    'grupos_eliminado': (
        "{club} ya no tiene opciones, pero no dejaremos que sea un partido fácil.",
        "Sin nada en juego para {club}, nosotros sí tenemos mucho. Y vamos a ir a por los tres puntos.",
    ),
    'clasico': (
        "Contra {club} se olvida la tabla y todo vale. Un clásico es un partido distinto.",
        "Un clásico se gana con el corazón. Y el nuestro late más fuerte que el de {club}.",
        "Contra {club}, el favorito no existe. Hay que ganarlo en la cancha, y nada más.",
    ),
    'titulo': (
        "{club} pelea por el título, pero hoy nos toca a nosotros fastidiarles la fiesta.",
        "Sabemos lo que se juega {club}. A nosotros nos toca complicárselo todo lo que podamos.",
        "El título no se decide aquí, pero nosotros no se lo vamos a poner fácil a {club}.",
    ),
    'titulo_cerca': (
        "{club} tiene el título al alcance. Vamos a hacer todo lo posible por evitar que lo celebre hoy.",
        "Si {club} quiere cerrar el título, tendrá que ganárnoslo. No se lo vamos a regalar.",
    ),
    'campeon_ya': (
        "{club} ya es campeón y merece respeto. Pero nosotros también tenemos orgullo y vamos a ganar.",
        "Ya son campeones, pero no vamos a ponérselo fácil. Nosotros jugamos hasta el último partido.",
    ),
    'descenso': (
        "{club} está en una situación delicada, y eso lo hace peligroso. No nos vamos a confiar.",
        "Los equipos que se juegan la permanencia pelean como leones. {club} va a salir a morder.",
    ),
    'descendido': (
        "{club} ya conoce su destino, pero eso no lo hace menos peligroso. Hay que respetarlos.",
    ),
    'lider': (
        "{club} manda en la tabla. Nos toca demostrar que a los líderes también se les gana.",
        "Vamos a por el líder. Un equipo grande se mide ante los mejores, y {club} lo es.",
    ),
    'racha_buena': (
        "{club} viene en racha, pero todas las rachas se acaban. Hoy puede acabar la suya.",
        "Les han salido muchos partidos seguidos. Nosotros vamos a cortarle la racha a {club}.",
    ),
    'racha_mala': (
        "{club} atraviesa un mal momento, pero eso los hace peligrosos: llegan con rabia.",
        "No me fío de {club}: un equipo herido es peligroso y necesita ganar.",
    ),
    'favorito': (             # tú eres el favorito: el rival juega de aspirante
        "Nadie nos da opciones contra {club}. Eso nos libera. Vamos a por la sorpresa.",
        "{club} es el favorito, lo sabemos. Pero en el fútbol no siempre gana el que debe.",
    ),
    'david': (                # tú eres el aspirante: el rival es el grande
        "Jugamos como favoritos, y eso nos exige. Hay que respetar a {club} y no confiarnos.",
        "Nos toca ser los grandes. Y los grandes no pueden permitirse un día malo contra {club}.",
    ),
    'debut': (
        "Empezar la temporada contra {club} es un desafío. Queremos arrancar con una victoria.",
        "El primer partido siempre es especial. {club} nos va a poner a prueba desde el primer minuto.",
    ),
    'cierre': (
        "Se acaba el curso. Queremos despedirnos de nuestra gente con un buen resultado ante {club}.",
    ),
    'ultima_jornada': (
        "El último partido es para dejar un buen recuerdo. Vamos a por la victoria contra {club}.",
        "Se acaba la liga y queremos despedirnos con una victoria ante {club}.",
    ),
}
