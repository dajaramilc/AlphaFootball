# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Nacionalidades reales (v0.4.10.0)
Nacionalidad de la persona real a la que parodia cada nombre. _POR_PAIS lleva SOLO a los
extranjeros (nacionalidad ≠ país de la liga donde arrancan): el local recibe el país de su liga
(retiros.asignar_nacionalidades). Los nombres inventados o dudosos no se anotan: mejor local que
inventado. Cubre las 18 ligas, el banco internacional (Champions/Libertadores), los 22 agentes
libres y todos los DTs de data/entrenadores.DT_REALES.
"""
from __future__ import annotations

import unicodedata

# país → nombres parodia completos ("Nombre Apellido", tal cual están en los datos)
_POR_PAIS: dict[str, list[str]] = {
    "Albania": [
        "Ivan Balliuna", "Keidi Barecito", "Uzuni Chinchón", "Myrto Muela", "Berat Djimsitio", "Ardian Ismajlito",
        "Kristjan Asllanito", "Stiven Shpendito", "Bruno Goda-goda", "Arber Hoxha-hoja",
    ],
    "Alemania": [
        "Stefan Ortegon", "Kai Gol-fantasma", "Timo Werner-fallon", "Malick Thiawaii", "Nick Woltemadera",
        "Brajan Grudazo", "Merlin Rolito", "Antonio Lokiger", "Marc Estatua", "Yann Bisseck", "Malick Thiaw",
        "Robin Gosenazo", "Marc-Oliver Kempfito", "Nicolas Kuhnetico", "Jonathan Klinsmanncito",
        "Mesut Ozil-retirado", "Thilo Kehrer-quehacer", "Timon Wellenreuther-ola", "Ilkay Gundogan-gundo",
        "Clement Bischoff-obispito",
    ],
    "Argelia": [
        "Ramy Bensebaini", "Fares Ghedjemito", "Ibrahim Maza-mazo", "Fares Chaibi-chai", "Amine Gouiri-guiri",
        "Aissa Mandi-mandarina", "Nabil Bentaleb-talento", "Anis Hadj Moussa-musaka", "Monsef Bakrar-bacalao",
    ],
    "Argentina": [
        "Alexis El Colorado", "Lisandro El Carnicero", "Alejandro Bichito", "Enzo Dolares", "Cristian Romero-pego",
        "Emiliano Dibu-Bailarin", "Emiliano Buendiario", "Nicolas Dominguito", "Walter Benitezcito",
        "Juan Musso-lento", "Nahuel Molinera", "Rodrigo El Guardaespaldas", "Julian Spider", "Angelito Correa",
        "Giuliano Simeolin", "Paulo Parades", "Valentin Gomezquino", "Giovani Lo Celsito", "Chimy Avilanzado",
        "Juan Foytazo", "Lucas Beltranquilo", "Rossi Rossini", "Alcaraz Millonario", "Carlos Alcaraqueta",
        "Anibal Moreno Rapido", "Flaco Lopez", "Alexander Barboza Rustico", "Thiago Almada", "German Cano Goleador",
        "Agustin Marchesin", "Walter Kannemann Carnicero", "Franco Cristaldo", "Pavon Turbo",
        "Fabrizio Angileri Loco", "Alexandro Bernabeicito", "Renzo Saravia Sarasa", "Alan Franco Tirador",
        "Alan Franco Malo", "Fausto Vera Verita", "Tomas Cuello Largo", "Lucas Romero Pampa", "Lautaro Diaz Soleado",
        "Giuliano Galoppo", "Jonathan Callao", "Pablo Vegetariano", "Rodrigo Garrote", "Ezequiel Piovi Pioja",
        "Ezequiel Piovi", "Eric Remedi", "Fernando De Paul", "Claudio Aquino", "Javier Correa", "Javier Burrai",
        "Damian Diaz-bicho", "Dario Aimar", "Lisandro Alzugaray", "Matias Di Benedetto", "Horacio Calcaterra",
        "Diego Churin", "Esteban Andradazo", "Nicolas Otamendi-general", "Angel DiMaria-fideo", "Nehuen Perez",
        "Alan Varela", "Lautaro Martinez-toro", "Nico Gonzalez", "Boyé Tobillo", "Matias Soulecito",
        "Paulo Dybalazo", "Taty Castellanito", "Santiago Castrito", "Nico Paz-y-Amor", "Maximo Perronito",
        "Giovanni Simeonito", "Leandro Chichizolazo", "Barreal Mágico", "Lucas Romero", "Juan Dybala",
        "Rodrigo Garro", "Vegetti Pirata", "Pablo Vegetti", "Furch Tanque", "Bruno Zapelli Zapallo",
        "Gaston Benavidez Benavente", "Flaco López", "Renzo Saravia", "Alan Franco", "Rodrigo Battaglia",
        "Claudio Aquinito", "Anibal Moreno", "Jose Flaco-Lopez", "Hector Villalba-flecha", "Emiliano Rigoni-ancla",
        "Facundo Bonifazi-pase", "Tiago Palacios-pared", "Facundo Waller-muralla", "Milton Celiz-celoso",
        "Lautaro Diaz-rayo", "Claudio Spinelli-espina", "Juan Manuel Tevez-primo", "Maximiliano Barreiro-barro",
        "Mauro Icardi-flojo", "Enzo Barrenechea-barreno", "Exequiel Palacios-palacete", "Equi Fernandez-equis",
        "Geronimo Rulli-rulo", "Leonardo Balerdi-balero", "Facundo Medina-zurdito", "Walter Benitez-paraguas",
        "Zaid Romero-romerito", "Mauro Icardi-wanda", "Facundo Bruera-bravo",
    ],
    "Armenia": [
        "Henrikh Mkhitaryan",
    ],
    "Australia": [
        "Riley McGreego", "Riley McGreey", "Sol Brynncito", "Jay Idzesito", "Jordan Bos-jefe",
    ],
    "Austria": [
        "Konrad Laimer-corre", "Marcel Sabitzer", "Stefan Poschito", "Michael Svobodita", "Valentino Lazarillo",
        "Xaver Schlager-cancion", "Christoph Baumgartner-jardinero", "Nicolas Seiwald-selva", "Paul Wanner-wanabi",
        "Gernot Trauner-trueno",
    ],
    "Bosnia": [
        "Anel Ahmedhodžić", "Asmir Begovieja", "Vladan Kovacevicho", "Samed Bazdarazo", "Kenan Kodrazo",
        "Sead Kolasinacho", "Edin Dzekolosal", "Dennis Hadzikadunico", "Anel Ahmedhodzic-ahumado",
        "Kerim Alajbegovic-alabanza",
    ],
    "Brasil": [
        "Ederson Penales", "Savinho Regates", "Neto Atajadon", "Gabriel Muralla", "Gabriel Correlotodo",
        "Gabriel Martinellito", "Alisson Manos", "Casemito Silva", "Antony Giros", "Richarlison Pajarito",
        "Bruno Guimaraesquisito", "Joelinton Toro", "Murillo Murallito", "Morato Moraton", "Igor Jesusito",
        "Luiz Juniorcito", "Marcao Marcadon", "Natan Natacion", "Antony Girotrompo", "Samuel Lino-rapido",
        "Eder Limitado", "Ficticius Jr", "Rodryguito Pase", "Endricki Bebe", "Raphinhazo Dias", "Luiz Felipon",
        "Alemao Aleman", "John Victorioso", "Leonardo Coelho", "Ricardo Ade", "Robson Matheus", "Helton Leitecito",
        "Gleison Bremer-muro", "Danilo Capitano", "Douglas Luiz", "Carlos Augusto", "Emerson Royal",
        "Marquinhos Capitano", "Wendell Silva", "Pepe Brasil", "Galeno Turbo", "William Gomes", "Yan Couto",
        "David Nereseta", "Wesley Wesleyano", "Ederson Motorcito", "Dodo Dodotis", "Diego Carlos-tanque",
        "Junior Messiasnico", "Endrick Promesa", "Gabriel Verón", "Willian Bigode", "Leonai Souza-samba",
        "Neymar Duro-en-fiesta", "Marcelo Gordito", "Alex Sandropastoso", "Lucas Beraldo-beraldito",
        "Arthur Augusto-carrilero", "Romulo Cardoso-remo", "Kaua Santos-santito", "Vanderson Lateral-lujo",
        "Caio Henrique-banquero", "Igor Paixao-pasion", "Alisson Santos-sporting", "Lucas Rosa-rosado",
        "Mauro Junior-junior", "Gabriel Sara-sarita", "Pedro Henrique-enrique", "Vinicius Tobias-tobi",
        "Marlon Gomes-goma", "Pedrinho Pedrito-shakhtar", "Eguinaldo Eguinaldo-ego", "Kevin Kelsy-kelsi",
        "Newerton Newerton-nuevo", "Kauan Elias-elias", "Alisson Santana-santo", "Bruno Savio-altiplano",
    ],
    "Bulgaria": [
        "Ilia Gruevski", "Petko Hristovito",
    ],
    "Burkina Faso": [
        "Issa Kaboré", "Edmond Tapsoba-tapon", "Lassina Traore-tractor",
    ],
    "Bélgica": [
        "Kevin De Bronca", "Jeremy Doku-palo", "Leandro Trossardito", "Romeo Lavanda", "Youri Tielemaniaco",
        "Amadou Onanana", "Matz Selfie", "Maxim De Cuypercito", "Thibaut Murois", "Axel Peluca",
        "Koni De Winterfell", "Romelu Lukakazo", "Charles De Ketchupere", "Ignace Van der Brempito",
        "Eden Hazarrica", "Maarten Vandevoordt-vocal", "Johan Bakayoko-bacalao", "Arthur Theate-teatro",
        "Michy Batshuayi-batido", "Arthur Vermeeren-verbena", "Arnaud Bodart-bodega", "Nathan Ngoy-ngoyo",
        "Thomas Meunier-molinero", "Ngalayel Mukau-maullido", "Zeno Debast-debate", "Mika Godts-dios",
        "Arne Engels-angel", "Yorbe Vertessen-vertice",
    ],
    "Cabo Verde": [
        "Logan Costanera",
    ],
    "Camerún": [
        "Andre Manosflojas", "Carlos Balebalazo", "Yvan Neyoucito", "Frank Anguisazo", "Cyril Ngongeado",
        "Emmanuel Ekongazo", "Christian Kofane-cafe",
    ],
    "Canadá": [
        "Tajon Buchananas", "Alphonso Davies-cohete", "Stephen Eustaquio", "Ali Ahmedito", "Jonathan Davidazo",
        "Alistair Johnston-juanito",
    ],
    "Chile": [
        "Erick Pulgar Fuerte", "Paulo Diaz Pegador", "Gabriel Arias Volador", "Gabriel Suazorro",
        "Alexis Sancheztrasnochado", "Felipe Loyola", "Diego Valdes Valde", "Rodrigo Echeverria Echenique",
        "Marcelino Nuñezito", "Guillermo Maripanazo", "Vargas Chileno", "Vargas Lobo", "Gonzalo Maripán",
        "Arturo Vidal-copas", "Alexis Sanchez-quebrado",
    ],
    "Colombia": [
        "Lucho Guajiro", "Moises Millonario", "Daniel Muñoztang", "Jefferson Lermita", "Nelson Deossito",
        "Cucho Hernandito", "Jhon Arias Mago", "Richard Rios Cafe", "Rafael Borre Borroso", "Johan Carbonero Carbon",
        "Johan Carbonero Humo", "Luis Sinisterra Diestro", "Santiago Arias Lesionado", "Robert Renteria Renta",
        "Andres Gomez Lanzado", "Miguel Borjita Colibri", "Juanfer Quintero Panza", "Roger Martinez Frio",
        "Jhohan Romana Muro", "Juan Camilo Portilla", "Alexis Manyoma Mañoso", "Edwuin Cetre Cetro",
        "Alvaro Montero Montaña", "Jaminton Campaz Campeon", "Jhojan Julio", "Jorman Campuzano", "Juan Cabalito",
        "Jhon Lucumiedo", "Duvan Zapatazo", "Carlos Terán Terco", "Steven Mendoza Mandioca", "Sebastian Gomez Coxa",
        "Jherson Mosquera", "Wilmar Barrios", "Richard Rios", "Diego Herazo-cumbiambero", "James Rodriguez-vidrio",
        "Luis Diaz-guajiro", "Davinson Sanchez-tumaco", "Luis Suarez-el-otro",
    ],
    "Congo RD": [
        "Yannick Bolasie Bolsa",
    ],
    "Corea del Sur": [
        "Heung-min Hijo", "Kim Minjae-roto", "Lee Kang-in", "In-beom Hwang-tigre",
    ],
    "Costa Rica": [
        "Rodrigo Urena", "Keylor Navas-banca",
    ],
    "Costa de Marfil": [
        "Ibrahim Sangarage", "Nicolas Pepetazo", "Evan Ndickazo", "Odilon Kossounote", "Issa Doumbiazo",
        "Yan Diomande-diamantito", "Hamed Traore-tractor", "Ousmane Diomande-diamante", "Wilfried Singo-cingo",
    ],
    "Croacia": [
        "Josko Pasaporte", "Mateo Pasecito", "Borna Sosaso", "Luka Viejic", "Luka Sucic", "Ante Crnacazo",
        "Stipe Biukazo", "Stanko Juricazo", "Dinko Horkasito", "Petar Susicazo", "Marin Pongracito",
        "Mario Pasalicuas", "Toma Basicote", "Nikola Vlasicazo", "Milan Badeljazo", "Nikola Morosito",
        "Martin Baturinero", "Marin Sverkito", "Franjo Ivanovic-croata", "Josip Sutalo-sutil",
        "Ivan Perisic-veterano",
    ],
    "Dinamarca": [
        "Christian Eriksenazo", "Rasmus Joyita", "Filip Jorgensenazo", "Andreas Cristales",
        "Martin Braithwaite Vikingo", "Alexander Bah", "Mads Andersen", "Jannik Vestergaardian",
        "Victor Kristiansenado", "Emiliano Marcondesito", "Oscar Schwartauer", "Mathias Kvistgaardito",
        "Mads Roerslevita", "Rasmus Hojlundito", "Oliver Provstgaardia", "Gustav Isaksenado", "Jens Odgaardito",
        "Morten Frendrupazo", "Albert Gronbaekito", "Christian Gytkjaerito", "Victor Froholdt-danes",
        "Rasmus Kristensen-cristal", "Oscar Hojlund-hermanito", "Pierre-Emile Hojbjerg-hielo",
        "Matt ORiley-irlandes", "Mika Biereth-cerveza", "Marius Broholm-brocoli", "Morten Hjulmand-capitan",
        "Anton Gaaei-gaita", "Kasper Dolberg-dolar", "Kasper Schmeichel-hijo", "Jacob Rasmussen-rasmus",
        "Mads Bidstrup-bistec", "Maurits Kjaergaard-carguero", "Conrad Harder-duro", "Casper Tengstedt-tenedor",
    ],
    "Ecuador": [
        "Arboleda Arbolito", "Felix Torres Gemelas", "Jhonny Quinonez", "Enner Valencia Naranja",
        "Hernan Galindez Galan", "Jordy Caicedo Cacao", "Willian Pacho", "John Yeboahcito", "Cazares Equator",
        "Djorkaeff Reasco", "Joel Ordonez-ordenado",
    ],
    "Egipto": [
        "Mo Ensalada", "Sam Morsydad",
    ],
    "Escocia": [
        "Andy Correcaminos", "John McGinebra", "Nathan Pattersonrisa", "Oli McBurnie", "Ross Stewart",
        "Kenny McLeanito", "Dominic Hyamazo", "Scott McTomahawk", "Billy Gilmoura", "Lewis Fergusonazo",
        "Che Adamsguevara", "Liam Hendersonito", "Scott McKenna-mecha",
    ],
    "Eslovaquia": [
        "Stanislav Lobotomka", "Leo Sauer-chucrut",
    ],
    "Eslovenia": [
        "Jan Muroblak", "Andres Vombergar", "Kevin Kampl-campo",
    ],
    "España": [
        "Rodriguez 5 Estrellas", "David Rayamuro", "Mikel Merino-oro", "Robert Manitos", "Marc Peluca",
        "Pedro Porrito", "Pau Torreta", "Yeremy Pinito", "Iker Muniain Navarro", "Josep Martinez", "Fabian Ruiz",
        "Alvaro Morata", "Ivan Marcano", "Alvaro Carreras", "Samu Aghehowa", "Miguel Gutierrito", "Mario Hermosillo",
        "Angelino Angelote", "Mario Gilazo", "Pedro Pedrito Viejo", "David De Gea-mas", "Juan Mirandita",
        "Aaron Martincito", "Jacobo Ramonazo", "Alex Vallecito", "Alberto Morenazo", "Sergi Robertazo",
        "Jesus Rodriguito", "Gerard Yepesito", "Iker Muniain", "David De Gea-silla", "Sergio Ramos-pega",
        "Gabri Veiga-gallego", "Alejandro Grimaldo-zurdazo", "Lucas Vazquez-exmadridista", "Aleix Garcia-metronomo",
        "Matias Fernandez-Pardo-pardo", "Ivan Fresneda-fresa", "Ansu Fati-fatiga", "Hugo Bueno-malo",
        "Sergi Dominguez-domingo",
    ],
    "Estados Unidos": [
        "Chris Riquezas", "Weston McKennie", "Timothy Weah", "Yunus Musah", "Christian Pulisic-USA", "Josh Sargento",
        "Daryl Dikezazo", "Gianluca Busioso", "Malik Tillman-till", "Folarin Balogun-globo", "Sergino Dest-destello",
        "Ricardo Pepi-pepino", "Esmir Bajraktarevic-bajon", "Cameron Carter-Vickers-cartero",
        "Auston Trusty-confiable",
    ],
    "Finlandia": [
        "Marcus Forssy", "Jesse Joronenazo", "Lukas Hradecky-lento", "Viljami Sinisalo-sinsal",
    ],
    "Francia": [
        "William Salivazo", "Ibrahima Konazo", "Leny Yoro-joven", "Malo Gusto", "Wesley Fofanas", "Axel Disasito",
        "Christopher Lesiones", "Yoane Wissaguas", "Arnaud Kalimuendito", "Dilane Bakwando", "Maxence Lacruz",
        "Jaydee Canvoto", "Jean-Philippe Mateteta", "Thierno Barrial", "Lucas Dignidad", "Boubacar Kamarada",
        "Evann Guessandia", "Aurelien Chuminas", "Eduardo Camavingazo", "Ferland Tronky", "Kylian Mbappenal",
        "Jules Kouture", "Clement Lengletazo", "Thomas Limonier", "Antoine Hombregris", "Dimitri Foulquierda",
        "Baptiste Santamarina", "Florian Lejeunito", "Randy Ntekazo", "Tanguy Nianzouzou", "Lucien Agoumetralla",
        "Dimitri Payet Jubilado", "Dayot Upamecano", "Kingsley Coman-fino", "Michael Olise-mago", "Pierre Kalulu",
        "Khephren Thuram", "Benjamin Pavard", "Marcus Thuram", "Mike Maignan-muro", "Theo Hernandez-cohete",
        "Youssouf Fofana", "Lucas Hernandez", "Ousmane Dembele-mago", "Bradley Barcola", "Desire Doue",
        "Warren Zaire-Emery", "Clement Michelines", "Julien Ponceaudo", "Wilson Odobert", "Illan Mesliercito",
        "Georginio Rutterd", "Pierre Ekwat", "Isaac Lihadji", "Boubakary Soumarecito", "Gonalons Tabique",
        "Luca Zidanito", "Lejeune Clavo", "Jonathan Dubasinazo", "Lucas Perrinazo", "Ange-Yoan Bonnyto",
        "Adrien Rabiotazo", "Christopher Nkunkuazo", "Manu Konecta", "Samuel Gigotazo", "Adrien Tamezazo",
        "Jean Butezazo", "Lucas Da Cunhado", "Maxence Caqueretazo", "Mehdi Dorvalito", "Gregoire Defrelito",
        "Payet Francês", "Paul Pogbanned", "Karim Benzemóvil", "Antoine Griezman-mediocre", "Sacha Boey-buey",
        "Jeanuel Belocian-veloz", "Loic Bade-bache", "Martin Terrier-perrito", "Castello Lukeba-castillo",
        "El Chadaille Bitshiabu-bicho", "Tidiam Gomis-gomita", "Jean-Matteo Bahoya-bahia", "Elye Wahi-wifi",
        "Alassane Plea-pleito", "Paul Pogba-regreso", "Kevin Theophile-Catherine-teofilo", "Joane Gadou-gadito",
        "Mamadou Diakhon-diacono",
    ],
    "Gabón": [
        "Pierre-Emerick Auba-viejo", "Pierre-Emerick Aubameyang-antifaz", "Mario Lemina-lamina",
    ],
    "Gales": [
        "Ben Davies-comodin", "Neco Williamsito", "Brennan Johnsonazo", "Aaron Ramseyram", "Ethan Ampadu",
        "Daniel Jamesy", "Jordan Jamesbond", "Chris Mephamazo", "Wes Burnsito", "Danny Wardrobe", "Kieffer Moorena",
        "Nathan Broadheadset", "Gareth Bale-pensionado",
    ],
    "Gambia": [
        "Yankuba Mintehado", "Dawda Camarada",
    ],
    "Georgia": [
        "Georges Mikautadzito", "Khvicha Kvaratskhelia-magia", "Saba Goglichidzito", "Giorgi Kvernadzito",
        "Giorgi Kochorashvili-coche", "Irakli Azarovi-azar",
    ],
    "Ghana": [
        "Thomas Fiesta", "Inaki Billiams", "Joseph Aidoodoo", "Jordan Ayewcito", "Abdul Fatawuau",
        "Kamaldeen Sulemanita", "Caleb Ekubanana", "Alfred Duncanazo", "Mohammed Salisu-salsa",
        "Jeffrey Schlupp-sorbo", "Carlos Forbs-forbes", "Edmund Baidoo-baile",
    ],
    "Grecia": [
        "Stefanos Tzimasas", "Odysseas Vlachodormido", "Vangelis Pavlidis", "Kostas Tsimikaos", "Christos Mandarina",
        "Charalampos Lykogiannidis", "Tasos Douvikaso", "Giorgos Kyriakopoulito", "Grigoris Kastanazo",
        "Fotis Ioannidis-griego", "Christos Tzolis-trolis",
    ],
    "Guinea": [
        "Mouctar Diakhabyte", "Ilaix Moribundo", "Serhou Guirassy-gol", "Seydouba Cissecito", "Amadou Diawarazo",
    ],
    "Guinea Ecuatorial": [
        "Saul Cocotero",
    ],
    "Hungría": [
        "Dominik Impronunciable", "Callum Stylesito", "Adam Nagyito", "Peter Gulacsi-guante", "Willi Orban-urbano",
        "Roland Sallai-salami",
    ],
    "Inglaterra": [
        "Jude Bellin-gol", "Conor Correlotodo", "Harry Kane-gol", "Lloyd Kelly", "Fikayo Tomori",
        "Ruben Loftus-Cheek", "Tammy Abraham", "Danny Namaso", "Jonathan Rowecito", "Brooke Norton-Cuffito",
        "Dele Alli-triste", "Carney Chukwuemeka-trabalenguas", "CJ Egan-Riley-egano", "Angel Gomes-goma",
        "Mason Greenwood-bosque", "Eric Dier-diario", "Bobby Clark-claro", "Jordan Henderson-hendo",
        "Raheem Sterling-libra",
    ],
    "Irlanda": [
        "Caoimhin Kelleherazo", "Mark Traversura", "Jake O'Brienazo", "Seamus Colemanazo", "Gavin Bazunu",
        "Gavin Bazunudo", "Dara O'Sheaque", "Jack Taylorsito", "Ryan Manningazo", "Will Smallbono", "Finn Azazel",
        "Shane Duffyfuerte", "Jayson Molumbrado", "Mikey Johnstonazo", "Evan Fergusonrisa", "Liam Scales-escalera",
        "Adam Idah-ida",
    ],
    "Irlanda del Norte": [
        "Conor Bradley-rapido", "Justin Devenido", "Trai Humez", "Dan Ballardz", "Corry Evansz", "Paddy McNairz",
        "Shea Charleston", "Isaac Pricelandia",
    ],
    "Irán": [
        "Mehdi Taremi",
    ],
    "Islandia": [
        "Orri Oskarsson", "Jóhann Bergur", "Albert Gudmundssonrisa", "Mikael Ellertssonito", "Bjarki Bjarkasonito",
        "Hakon Haraldsson-vikingo",
    ],
    "Israel": [
        "Weissman Punta", "Oscar Gloukh-glu",
    ],
    "Italia": [
        "Riccardo Calafiori-roto", "Jorginho Abuelo", "Guglielmo Paratodo", "Destiny Udogazo", "Sandro Tonalidad",
        "Nicolo Savonata", "Olivier Boscaglio", "Gianluigi Donnarumma-muro", "Luca Koleosho", "Wilfried Gnontoy",
        "Caleb Okolito", "Mario Balotellin", "Emerson Palmieri-palmera", "Nicolo Tresoldi-tres",
    ],
    "Jamaica": [
        "Bobby De Cordova-Rojo", "Leon Bailongo",
    ],
    "Japón": [
        "Takehiro Tomiyaso", "Wataru Endo-viejo", "Kaoru Mitomate", "Daichi Kamadita", "Take Kubo-rubik",
        "Kuryu Matsukito", "Ritsu Doan-don", "Takumi Minamino-minimo", "Hidemasa Morita-mora", "Ko Itakura-tabla",
        "Tsuyoshi Watanabe-wasabi", "Ayase Ueda-lluvia", "Reo Hatate-hatatito", "Daizen Maeda-rayo",
        "Kyogo Furuhashi-puente", "Sota Kitano-quitano",
    ],
    "Kosovo": [
        "Edon Zhegrovazo", "Amir Rrrahmani",
    ],
    "Lituania": [
        "Gvidas Gineitizo",
    ],
    "Luxemburgo": [
        "Leandro Barreiro-barrio",
    ],
    "Macedonia del Norte": [
        "Bojan Miov", "Stole Dimitrievsky", "Eljif Elmasao", "Stefan Ristovski-risto",
    ],
    "Mali": [
        "Yves Bissumazo", "Hamari Moto", "Amadou Haidara-jaiba",
    ],
    "Marruecos": [
        "Noussair Mazraouito", "Yasin Ayarigato", "Nayef Aguardiente", "Sofyan Amrabatido", "Abde Ezzalzoulito",
        "Ilias Akhomachito", "Brahim Diazazo", "Achraf Hakimi-flecha", "Haitam Abaidazo", "Yasser Larouch",
        "Munir El Haddadito", "Neil El Aynaoui-ay", "Adam Masinota", "Zakaria Aboukhlalito",
        "Eliesse Ben Seghir-segundero", "Nayef Aguerd-aguardiente", "Osame Sahraoui-sahara", "Hamza Igamane-iman",
        "Anass Salah-Eddine-sal", "Ismael Saibari-sabio", "Couhaib Driouech-driblin", "Oussama Targhalline-tarjeta",
    ],
    "Montenegro": [
        "Adam Marusicazo", "Nikola Krstovicho",
    ],
    "Mozambique": [
        "Geny Catamo-catamaran",
    ],
    "México": [
        "Johan Vasquezito", "Carlos Tequila-Vela",
    ],
    "Nigeria": [
        "Ola Aina-hola", "Christantus Uchepa", "Umar Sadiqaco", "Tani Oluwaseyito", "Chidera Ejukebox",
        "Akor Adamsito", "Samuel Chukwueze", "Zaidu Sanusi", "Joe Aribobo", "Josh Majazo", "Fisayo Dele-Bashirulo",
        "Ademola Lookmanazo", "Tyronne Ebuehito", "Nathan Tella-tela", "George Ilenikhena-ilegible",
        "Raphael Onyedika-onda", "Victor Osimhen-mascara",
    ],
    "Noruega": [
        "Erling Gasoland", "Martin Odegol", "Orjan Nylandia", "Alexander Gigantoth", "Julian Ryerson",
        "Fredrik Aursnes", "Andreas Schjelderup", "Aune Heggeboso", "Torbjorn Heggemonia", "Marcus Pedersenito",
        "Leo Ostigardazo", "Morten Thorsbyte", "Antonio Nusa-nube", "Oliver Edvardsen-eduardo",
        "Hugo Vetlesen-veleta",
    ],
    "Nueva Zelanda": [
        "Chris Troncoso", "Tommy Smithy",
    ],
    "Panamá": [
        "Luis Mejia", "Jose Cordobazo", "Cecilio Waterman-aguado", "Ismael Diaz-panameno", "Amir Murillo-murcielago",
    ],
    "Paraguay": [
        "Diego Gomezclado", "Gustavo Gominola", "Gatito Fernandez", "Villasanti Pulmon", "Junior Alonso Muro",
        "Damian Bobadilla", "Adam Bareiro", "Lucas Villalba Muro", "Oscar Romero Paraguayo", "Angel Romero Viejo",
        "Ramon Sosa Vendido", "Blas Riveros", "Juan Carlos Portillo", "Matias Galarza", "Alex Arce-gol",
        "Gustavo Gómez", "Romero Paraguaio", "Raul Cáceres", "Blas Armoa", "Néstor Ortigoza", "Ortigoza Volante",
        "Bareiro Tanque", "Junior Alonso", "Williams Riveros", "Gustavo Gomez-capitan", "Anibal Leguizamon-guarani",
        "Richard Schunke-chunche", "Rodney Redes-rotas",
    ],
    "Países Bajos": [
        "Nathan Akejado", "Jurrien Madera", "Virgil El Muro", "Ryan Graven-banco", "Cody Gakpazo",
        "Matthijs De Tronco", "Joshua Zirkzeazo", "Micky Veloz", "Sven Botmanazo", "Bart Verbruguesa",
        "Jan Paul Van Heckerito", "Joel Veltmano", "Mats Wiefferino", "Marco Bizcocho", "Ian Maatsenado",
        "Donyell Malentendido", "Frenkie De Vidrio", "Daley Cegato", "Donny Van de Banco", "Arnaut Danjumo",
        "Arnaut Danjumanji", "Memphis Depaycito", "Donyell Malen", "Teun Koopmeiners", "Stefan de Vrij",
        "Denzel Dumfries", "Tijjani Reijnders", "Zian Flemming", "Joël Piroe", "Crysencio Summervill",
        "Jenson Seeltz", "Tim Krulazo", "Tahith Chong", "Azor Matusiwazo", "Sam Beukemazo", "Noa Langosta",
        "Marten De Roonco", "Tijjani Noslinea", "Thijs Dallingazo", "Luuk de Jong-veterano", "Mark Flekken-flan",
        "Ernest Poku-poquito", "Jeffrey de Lange-langosta", "Calvin Verdonk-verdura", "Bjorn Meijer-mejor",
        "Ludovit Reis-rey",
    ],
    "Perú": [
        "Andre Carrillo Picante", "Lucho Rayo Advincula", "Sheraldo Correcaminos", "Luis Advincula",
    ],
    "Polonia": [
        "Robert Abueloski", "Jakub Stolarcito", "Jan Bednarecho", "Krystian Bielikazo", "Piotr Zielinskazo",
        "Lukasz Skorupskito", "Nicola Zalewskito", "Przemyslaw Wisniewskito", "Arkadiusz Recazo",
        "Yarek Gasiorowski-gas", "Jakub Moder-moda", "Przemyslaw Frankowski-franco",
    ],
    "Portugal": [
        "Ruben Murallas", "Bernardo Bosquecito", "Matheus Nuñito", "Diogo Jotas", "Diogo Corredor", "Bruno Penaldes",
        "Joao Felixazo", "Pedro Neto-rapido", "Renato Veigarrote", "Alvaro Djalito", "Thierry Correita",
        "Andre Almeidita", "Nuno Moreira Portugues", "Raphael Guerreirito", "Joao Palhinha-tractor",
        "Rafael Leao-turbo", "Nuno Mendes-cohete", "Vitinha Motor", "Joao Neves", "Goncalo Ramos", "Bebé Muela",
        "Ricardo Pereirita", "Francisco Conceicaozinho", "Nuno Tavaresco", "Vitinha Vitinhazo", "Pedro Pereirazo",
        "Dany Motazo", "Fabio Silva-portugues", "Tiago Santos-santon", "Andre Gomes-abrigado",
        "Felix Correia-correa", "Paulo Bernardo-sanbernardo",
    ],
    "Rep. Checa": [
        "Ladislav Paquetazo", "Ales Mateju-ju", "Patrik Schick-chic", "Vitezslav Jaros-jarra", "Matej Kovar-kovacho",
    ],
    "Rumanía": [
        "Radu Dragusin", "Ionut Raduloso", "Andrei Ratiuuu", "Adrian Berbecito", "Dennis Man-hombre",
    ],
    "Rusia": [
        "Arsen Zakhariano", "Matvey Safonov", "Aleksandr Golovin-golondrina",
    ],
    "Senegal": [
        "Ismaila Sarrampion", "Idrissa Gueyeperro", "Iliman Ndiayeah", "Pape Sarr-rapido", "Pape Gueyeton",
        "Pathe Cissterna", "Nico Fallon", "Amath Ndiayecito", "Amadou Coundoulazo", "Boulaye Diamante",
        "Cher Ndourmido", "Assane Diaorama", "Demba Thiamazo", "Keita Baldazo", "Lamine Camara-camarita",
    ],
    "Serbia": [
        "Nikola Milenkobrick", "Nemanja Gudeljazo", "Filip Ugrinico", "Dusan Vlahovic-gol", "Strahinja Pavlovic",
        "Marko Grujic", "Aleksandar Radovanovicho", "Marko Dmitrovicho", "Vanja Milinkovic-Salvado",
        "Mile Svilarazo", "Lazar Samardzico", "Ivan Ilicito", "Filip Stankovicito", "Boris Radunovicho",
        "Aleksandar Stankovic-tanque", "Aleksa Terzic-terco", "Petar Ratkov-raton",
    ],
    "Suecia": [
        "Dejan Pelusa", "Lucas Bergvall", "Anthony Elangosta", "Victor Lindelento", "Carl Starfeltro",
        "Williot Swedbergamota", "Isak Hienazo", "Emil Holmsito", "Noel Tornquistito", "Zlatan Ibrahimo-viejito",
        "Samuel Dahl-sueco", "Hugo Larsson-largo", "Gustaf Nilsson-nilo", "Benjamin Nygren-negro",
        "John Mellberg-mel",
    ],
    "Suiza": [
        "Manuel Alkansio", "Fabian Schartazo", "Dan Ndoyito", "Ricardo Rodriguezuela", "Eray Comercial",
        "Ruben Vargasolina", "Djibril Sowtware", "Gregor Kobel-muro", "Yann Sommer-gato", "Zeki Amdouni",
        "Zeki Amdounidos", "Simon Sohmnoliento", "Remo Freulerazo", "Benjamin Siegristo", "Aurele Amenda-enmienda",
        "Philipp Kohn-cono", "Denis Zakaria-zanahoria",
    ],
    "Turquía": [
        "Altay Bayindirazo", "Ferdi Kadiogluten", "Arda Gülercito", "Kenan Yildiz-joya", "Hakan Calhanoglu",
        "Kerem Akturkoglu", "Orkun Kokcu", "Zeki Celiko", "Emirhan Ilkhanazo", "Salih Ozcan-ozono", "Can Uzun-usted",
        "Berke Ozer-ozono",
    ],
    "Túnez": [
        "Hannibal Mejbriri", "Anis Ben Slimanito", "Ellyes Skhiri-esqui", "Sebastian Tounekti-tunecino",
    ],
    "Ucrania": [
        "Oleksandr Zinchenco", "Vitalii Mykolenkito", "Misha Tronco", "Andriy Lunito", "Viktor Chiguanki",
        "Anatoliy Trubin", "Nazariy Rusnak", "Artem Dovbykazo", "Ruslan Malinovskazo", "Ilya Zabarnyi-ucraniano",
    ],
    "Uruguay": [
        "Darwin Caos", "Manuel Ugartazo", "Rodrigo Pinturita", "Fede Pajarito", "Ronald Cristal", "Josema Lesiones",
        "Christian Stuani Viejito", "Guillermo Varela Lenta", "Matias Vinazo", "Nicolas De Arrastra",
        "Nicolas De la Cruzazo", "Piquerez Uruguayita", "Facundo Bernal", "Sergio Rochet Cohete",
        "Agustin Rogel Rudo", "Mateo Ponte Duro", "Nicolas Acevedo Aceite", "Michel Araujo Charrua",
        "Luciano Rodriguez Lucho", "Mauricio Lemos Lento", "Puma Rodriguez Felino", "Edinson Matador Viejito",
        "Miguel Bestia Triste", "Facundo Cambeses", "Fernando Muslerazo", "Gabriel Neves Nieve",
        "Michael Santos Sanito", "Armando Mendez Mendigo", "Hernan Lopez Muñeco", "Maximiliano Falcon",
        "Alan Saldivia", "Sebastian Britos", "Martin Perez-Guedes", "Gonzalo Valle", "Sebastian Gonzalez",
        "Gabriel Villamil", "Brian Ocampito", "Mathias Oliverita", "Matias Vecinito", "Franco Israelito",
        "Valentin Carbonita", "Piquerez Zagueiro", "De Arrascaeta", "Bruno Méndez", "Armando Méndez",
        "Joaquin Piquerez", "Edinson Cavani-matador", "Miguel Merentiel", "Octavio Rivero-rio",
        "Gonzalo Mastriani-maestro", "Guillermo de Amores-amoroso", "Facundo Martinez-oriental",
        "Luis Suarez-muerde-menos", "Maxi Araujo-charrua", "Lucas Torreira-torrija", "Gonzalo Borges-jorge",
        "Alejandro Silva-uruguayo", "Martin Cauteruccio-paceno",
    ],
    "Venezuela": [
        "Jefferson Savarino", "Yeferson Soteldo Enano", "Ferraresi Vinotinto", "Jose Martinez Tanque",
        "Yangel Guerrero", "Miguel Navarro", "Eric Ramirez Ramillete", "Yangel Piedra", "Tomas Rincon",
        "Soteldo Chico", "Otero Vinotinto", "Otero Cruzmaltino", "Romulo Otero-bombazo", "Roberto Rosales-rosa",
    ],
    "Zambia": [
        "Patson Dakazo",
    ],
    "Zimbabue": [
        "Marvelous Nakamba",
    ],
}

# clubes de Champions/Libertadores (sin liga jugable): su país hace de "país de la liga"
PAIS_CLUB: dict[str, str] = {
    "Bayerna de Munich": "Alemania",
    "Borussia Dormund": "Alemania",
    "Bayer Neverkusen": "Alemania",
    "Lata Bull Leipzig": "Alemania",
    "Salchicha de Frankfurt": "Alemania",
    "Paris Saint-Germain Sin Champions": "Francia",
    "Paris Saint-Gayman": "Francia",
    "Olympique Bullabesa": "Francia",
    "AS Paraiso Fiscal": "Francia",
    "Lille Frio": "Francia",
    "Benfica Maldito": "Portugal",
    "Puerto FC": "Portugal",
    "Sporting Sin Gyokeres": "Portugal",
    "Ajax de Amsterdamnada": "Países Bajos",
    "PSV Eindhofen": "Países Bajos",
    "Feyenoord de Rottendam": "Países Bajos",
    "Club Brujas": "Bélgica",
    "Celtic de Glasgow Lluvioso": "Escocia",
    "Galatasaray Kebab": "Turquía",
    "Lata Bull Salzburgo": "Austria",
    "Dinamo de Zagreb Ajedrez": "Croacia",
    "Shakhtar Donetsko": "Ucrania",
    "Piamonte Calcio": "Italia",
    "Inter de Milan Roto": "Italia",
    "Milan Abuelo": "Italia",
    "Colo Colo Roto": "Chile",
    "Olimpia Abuelo": "Paraguay",
    "Bolivar Sin Aire": "Bolivia",
    "Universitario de la U": "Perú",
    "Peñaroloso": "Uruguay",
    "Penarol Roto": "Uruguay",
    "Nacionall de Montevideo": "Uruguay",
    "Barcelona Falso de Guayaquil": "Ecuador",
    "Liga de Quito Rota": "Ecuador",
    "Boca Amargo": "Argentina",
    "Palmeirras": "Brasil",
}

# DT parodia → país (todos los de data/entrenadores.DT_REALES, sin repetir alias)
NACIONALIDAD_DT: dict[str, str] = {
    "Pep Guardiolo": "España",
    "Mikel Artetazo": "España",
    "Xabi Alonzo": "España",
    "Michelín Sánchez": "España",
    "Sergio Frankisco": "España",
    "Ernesto Valverdura": "España",
    "Luis Enriquito": "España",
    "Unai Emerito": "España",
    "Marcelino Toralcito": "España",
    "Carlos Corbatán": "España",
    "Claudio Giraldillo": "España",
    "Íñigo Pérezvallecas": "España",
    "Cesc Fabregazo": "España",
    "Arne Slote": "Países Bajos",
    "Rubén Amorfo": "Portugal",
    "Abel Ferreiro": "Portugal",
    "José Mouriño": "Portugal",
    "Nuno Espíritu Sonto": "Portugal",
    "Leonardo Jardines": "Portugal",
    "Enzo Maresco": "Italia",
    "Davide Anchelotti": "Italia",
    "Francesco Farolillo": "Italia",
    "Massimiliano Alegre": "Italia",
    "Antonio Cuento": "Italia",
    "Gian Piero Gasperonni": "Italia",
    "Maurizio Sarrito": "Italia",
    "Stefano Piolín": "Italia",
    "Vincenzo Italianísimo": "Italia",
    "Marco Barón": "Italia",
    "Thomas Franco": "Dinamarca",
    "Hansi Flink": "Alemania",
    "Fabian Hurzelito": "Alemania",
    "Diego Cimeone": "Argentina",
    "Javier Gandolfo": "Argentina",
    "Lucas Gonzalazo": "Argentina",
    "Claudio Úbida": "Argentina",
    "Marcelo Gayardo": "Argentina",
    "Gustavo Costillas": "Argentina",
    "Julio Vacarí": "Argentina",
    "Damián Ayuda": "Argentina",
    "Carlos Teves": "Argentina",
    "Hernán Crespito": "Argentina",
    "Luis Zubeldilla": "Argentina",
    "Fernando Hortiz": "Argentina",
    "Martín Palermito": "Argentina",
    "Flavio Robado": "Argentina",
    "Matías Almeydazo": "Argentina",
    "Ramón Diazepam": "Argentina",
    "Eduardo Dominguito": "Argentina",
    "Gustavo Quinteto": "Argentina",
    "Ariel Holanda": "Argentina",
    "Mauricio Peregrino": "Argentina",
    "Nicolás Diezmo": "Argentina",
    "Frank Kudelkaos": "Argentina",
    "Guillermo Durito": "Argentina",
    "Javier Rabanito": "Argentina",
    "Marcelo Zuletazo": "Argentina",
    "Jorge Célicono": "Argentina",
    "Mariano Sosito": "Argentina",
    "Hernán Torrejas": "Colombia",
    "David Gonzalito": "Colombia",
    "Alberto Gamerito": "Colombia",
    "Hernán Darío Herrería": "Colombia",
    "Alejandro Restrepito": "Colombia",
    "Leonel Álvarez Pelo": "Colombia",
    "Flabio Torrente": "Colombia",
    "Alfredo Arriaz": "Uruguay",
    "Jorge Baba": "Uruguay",
    "Diego Agüirre": "Uruguay",
    "Pablo Peirana": "Uruguay",
    "Jorge Fósil": "Uruguay",
    "Román Cuellito": "Uruguay",
    "Mathías Corujito": "Uruguay",
    "Jorge Babosa": "Uruguay",
    "Alejandro Apudo": "Uruguay",
    "Fernando Curutchete": "Uruguay",
    "Danielo Núñezito": "Uruguay",
    "Ignacio Pallasito": "Uruguay",
    "Jorge Giordaño": "Uruguay",
    "Martín Varino": "Uruguay",
    "Andrés Carevich": "Uruguay",
    "Filipe Luisão": "Brasil",
    "Mano Menezez": "Brasil",
    "Tiago Nunca": "Brasil",
    "Roger Machacado": "Brasil",
    "Cuca Cucaracha": "Brasil",
    "Rogério Cenicero": "Brasil",
    "Fábio Carrillón": "Brasil",
    "Tercero Castillo": "Ecuador",
    "Paúl Vélez-vélez": "Ecuador",
    "Luis Solero": "Ecuador",
    "Diego Merinito": "Ecuador",
    "Francisco Pintado": "Ecuador",
    "Rafael Dudamelón": "Venezuela",
    "César Farisa": "Venezuela",
    "Niko Kovacho": "Croacia",
    "Igor Todo": "Croacia",
    "Ivan Juricazo": "Croacia",
    "Vincent Compañía": "Bélgica",
    "Eddie Jau": "Inglaterra",
    "Oliver Glasnerazo": "Austria",
    "David Moyitos": "Escocia",
    "Manuel Ingeniero Pellegrini": "Chile",
    "Cristian Chivo": "Rumanía",
    "Patrick Vieirazo": "Francia",
}


def _norm(texto: str) -> str:
    sin = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
    return " ".join(sin.lower().split())


NACIONALIDAD_JUGADOR: dict[str, str] = {n: pais for pais, nombres in _POR_PAIS.items() for n in nombres}
_NORMALIZADO = {_norm(n): p for n, p in NACIONALIDAD_JUGADOR.items()}
_DT_NORMALIZADO = {_norm(n): p for n, p in NACIONALIDAD_DT.items()}


def nacionalidad_real(nombre_completo: str) -> str:
    """País real del jugador parodiado, o '' si no está en la tabla."""
    return NACIONALIDAD_JUGADOR.get(nombre_completo) or _NORMALIZADO.get(_norm(nombre_completo), '')


def nacionalidad_dt(nombre: str) -> str:
    """País real del DT parodiado, o '' si no está en la tabla."""
    return NACIONALIDAD_DT.get(nombre) or _DT_NORMALIZADO.get(_norm(nombre), '')
