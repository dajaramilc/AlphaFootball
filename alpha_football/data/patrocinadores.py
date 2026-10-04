# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Catálogo de patrocinadores (v4.9.1)
MARCAS: 150 marcas parodia (nombre, rubro, perfil, región). La región limita dónde pueden aparecer:
'global' en cualquier club, 'europa' solo en clubes europeos y 'sudamerica' solo en los sudamericanos.
PATROCINIOS_REALES: lo que lleva hoy cada club de 1ª en la vida real (en parodia) para la primera
temporada: camiseta = patrocinador principal, manga = marca de ropa, estadio = naming del estadio.
None = sin dato fiable o sin patrocinador: ese espacio se rellena con una marca de su región al azar.
Fuentes: Wikipedia (temporadas 2026-27 en Europa, 2026 en Sudamérica) y prensa deportiva; Girona usa 2025-26.
"""
C, E, A = 'conservadora', 'equilibrada', 'ambiciosa'
G, EU, SA = 'global', 'europa', 'sudamerica'

MARCAS = [   # (marca parodia, rubro, perfil, región)
    # ropa deportiva
    ("Adibas", "ropa deportiva", E, G), ("Naik", "ropa deportiva", A, G), ("Pumba", "ropa deportiva", C, G),
    ("Niu Balans", "ropa deportiva", E, G), ("Umbrow", "ropa deportiva", C, G), ("Cappa", "ropa deportiva", C, G),
    ("Makron", "ropa deportiva", C, G), ("Le Gallo Deportif", "ropa deportiva", E, G),
    ("Phila", "ropa deportiva", C, G), ("Rebook", "ropa deportiva", E, G), ("Lotte", "ropa deportiva", C, G),
    ("Misuno", "ropa deportiva", E, G), ("Yoma", "ropa deportiva", C, EU), ("Jummel", "ropa deportiva", E, EU),
    ("Castor", "ropa deportiva", E, EU), ("Diadura", "ropa deportiva", C, EU), ("EA Siete", "ropa deportiva", A, EU),
    ("Ruje", "ropa deportiva", C, SA), ("Atómico", "ropa deportiva", C, SA),
    ("Maratón Sports", "ropa deportiva", E, SA), ("Bomán", "ropa deportiva", C, SA),
    # aerolínea
    ("Fly Emirados", "aerolínea", A, G), ("Qatar Airguais", "aerolínea", E, G), ("Etihat", "aerolínea", C, G),
    ("Turquish Erlains", "aerolínea", E, G), ("Riad Air", "aerolínea", A, G), ("Ryanhair", "aerolínea", E, EU),
    ("Iberio", "aerolínea", C, EU), ("Latan Airlines", "aerolínea", E, SA), ("Avianka", "aerolínea", E, SA),
    ("Gool Linhas Aéreas", "aerolínea", A, SA), ("Aerolíneas Argentonas", "aerolínea", C, SA),
    ("Kopa Airlines", "aerolínea", E, SA),
    # bebidas
    ("Coca-Kola", "bebidas", C, G), ("Pepsy", "bebidas", E, G), ("Red Bul", "bebidas", A, G),
    ("Heinekan", "bebidas", E, G), ("Gatorada", "bebidas", E, G), ("Budwaiser", "bebidas", E, G),
    ("Estrella Galaica", "bebidas", E, EU), ("Léte Agua", "bebidas", C, EU), ("Knocks Hidrata", "bebidas", A, EU),
    ("Guines", "bebidas", C, EU), ("Guaraná Antártida", "bebidas", E, SA), ("Bramha", "bebidas", E, SA),
    ("Skoll", "bebidas", E, SA), ("Quilmez", "bebidas", E, SA), ("Pocker", "bebidas", E, SA),
    ("Águilucho", "bebidas", E, SA), ("Cerveza Anduina", "bebidas", E, SA), ("Fernet Branko", "bebidas", A, SA),
    ("Aguardiente Nariñez", "bebidas", C, SA),
    # tecnología
    ("Sansumg", "tecnología", E, G), ("Spotifai", "tecnología", A, G), ("TeamViuer", "tecnología", C, G),
    ("Soni", "tecnología", E, G), ("Qualcomb Snapdrogan", "tecnología", A, G), ("Hawey", "tecnología", E, G),
    ("Lenobo", "tecnología", C, G), ("Gugle", "tecnología", A, G), ("Temporario", "tecnología", E, G),
    ("Shaomi", "tecnología", A, G), ("Mercado Libro", "tecnología", E, SA), ("Rapi", "tecnología", A, SA),
    # apuestas
    ("Bet366", "apuestas", A, G), ("Betguay", "apuestas", A, G), ("Codere-te", "apuestas", E, G),
    ("Wplei", "apuestas", C, G), ("Betanio", "apuestas", A, G), ("Betsun", "apuestas", E, G),
    ("Steik", "apuestas", A, G), ("Betfeir", "apuestas", E, G), ("Buin", "apuestas", E, G),
    ("Sportinbet", "apuestas", E, G), ("Vebet", "apuestas", A, G), ("Eurobett", "apuestas", E, EU),
    ("Guillermo Colina", "apuestas", C, EU), ("Superbete", "apuestas", A, SA),
    ("Esportes da Suerte", "apuestas", A, SA), ("H3Bet", "apuestas", A, SA), ("Betnacionall", "apuestas", E, SA),
    ("DeportesBet Ar", "apuestas", E, SA), ("Casino Bs As Online", "apuestas", E, SA),
    ("Misterbet", "apuestas", E, SA), ("BetPlei", "apuestas", E, SA), ("Doradabet", "apuestas", E, SA),
    ("Rashbet", "apuestas", A, SA), ("Pixbit", "apuestas", A, SA), ("Vive Suerte Bet", "apuestas", A, SA),
    ("Bet7C", "apuestas", A, SA), ("City Centro Online", "apuestas", E, SA),
    # banca
    ("Santénder", "banca", C, G), ("Mastercar", "banca", E, G), ("Bisa", "banca", C, G),
    ("Standar Charte", "banca", E, G), ("Amerikan Expres", "banca", E, G), ("HSBS", "banca", C, EU),
    ("Kutxabanca", "banca", C, EU), ("Abanka", "banca", C, EU), ("Revolute", "banca", A, EU),
    ("Barclais", "banca", E, EU), ("BBVE", "banca", C, EU), ("Bagdadi Capital", "banca", E, EU),
    ("CMC Mercados", "banca", E, EU), ("Marez", "banca", E, EU), ("Banco Supervieja", "banca", C, SA),
    ("Nubanc", "banca", A, SA), ("Itaúba", "banca", C, SA), ("Bradescón", "banca", C, SA),
    ("Bancolombio", "banca", C, SA), ("Banco do Brasol", "banca", C, SA), ("Daviviendo", "banca", E, SA),
    ("Banco Pinchincha", "banca", C, SA), ("Mercado Pagó", "banca", E, SA), ("Banco Galicio", "banca", C, SA),
    ("Banco Oriental", "banca", C, SA),
    # autos
    ("Chevrolé", "autos", E, G), ("Jip", "autos", C, G), ("Audí", "autos", A, G), ("Kía Motor", "autos", E, G),
    ("Reno", "autos", E, G), ("Toyoto", "autos", C, G), ("Volkswagon", "autos", C, G),
    ("Suzuku", "autos", C, G), ("BMV", "autos", A, G),
    # seguros
    ("Aya Seguros", "seguros", E, G), ("Alianz Seguros", "seguros", C, EU), ("Real-e Seguros", "seguros", C, EU),
    ("Vitalidad", "seguros", E, EU), ("Zura Seguros", "seguros", C, SA),
    # telecomunicaciones
    ("Digui Telecom", "telecomunicaciones", E, EU), ("Mediacomm", "telecomunicaciones", E, EU),
    ("Vodafón", "telecomunicaciones", C, EU), ("Claroh", "telecomunicaciones", E, SA),
    ("Tigue", "telecomunicaciones", E, SA), ("Movistár", "telecomunicaciones", C, G),
    # energía
    ("Pulsé Luz y Gas", "energía", E, EU), ("Gri Eléctrica", "energía", E, G), ("Petrobrasa", "energía", C, SA),
    # alimentos
    ("Colanto", "alimentos", C, SA), ("Saputto Quesos", "alimentos", C, EU),
    # cripto y turismo
    ("Sirkle USDC", "cripto", A, G), ("Visita Ruanda", "turismo", A, EU),
    # construcción, salud y servicios
    ("TM Inmobiliaria", "construcción", C, EU), ("MRB Construtora", "construcción", C, SA),
    ("Holzim Cemento", "construcción", C, G), ("Mapey Adhesivos", "construcción", C, G),
    ("Pamesa Cerámica", "construcción", E, EU), ("Neo Químico", "salud", E, SA),
    ("Hil Dikinson Abogados", "servicios", C, EU),
]

# club (nombre parodia) -> {'camiseta': marca, 'manga': marca de ropa, 'estadio': marca o None}
PATROCINIOS_REALES = {
    # Premier League 2026-27
    "Manchester Billete": {'camiseta': "Etihat", 'manga': "Pumba", 'estadio': "Etihat"},
    "Arsenal Pechofrio": {'camiseta': "Fly Emirados", 'manga': "Adibas", 'estadio': "Fly Emirados"},
    "Pool de Higado": {'camiseta': "Standar Charte", 'manga': "Adibas", 'estadio': None},
    "Manchester Desunido": {'camiseta': "Qualcomb Snapdrogan", 'manga': "Adibas", 'estadio': None},
    "Chelsea Guarderia": {'camiseta': "Sirkle USDC", 'manga': "Naik", 'estadio': None},
    "Spurs sin Copas": {'camiseta': "Aya Seguros", 'manga': "Naik", 'estadio': None},
    "Newcastle Petrodolar": {'camiseta': "Knocks Hidrata", 'manga': "Adibas", 'estadio': None},
    "Aston Villano": {'camiseta': "Visita Ruanda", 'manga': "Adibas", 'estadio': None},
    "Nottingham Deforestado": {'camiseta': "Marez", 'manga': "Adibas", 'estadio': None},
    "Brighton Algoritmo": {'camiseta': "Amerikan Expres", 'manga': "Naik", 'estadio': "Amerikan Expres"},
    "Crystal Palacete": {'camiseta': "Temporario", 'manga': "Makron", 'estadio': None},
    "Everton Caramelo": {'camiseta': "CMC Mercados", 'manga': "Castor", 'estadio': "Hil Dikinson Abogados"},
    # LaLiga 2026-27 (Girona: 2025-26, ya descendió)
    "Real Madriz": {'camiseta': "Fly Emirados", 'manga': "Adibas", 'estadio': None},
    "FC Farcelona": {'camiseta': "Spotifai", 'manga': "Naik", 'estadio': "Spotifai"},
    "Patetico de Madriz": {'camiseta': "Riad Air", 'manga': "Naik", 'estadio': "Riad Air"},
    "Girona Sorpresa": {'camiseta': "Etihat", 'manga': "Pumba", 'estadio': None},
    "Real Suciedad": {'camiseta': "Bagdadi Capital", 'manga': "Yoma", 'estadio': "Real-e Seguros"},
    "Athletic de Bilbao": {'camiseta': "Kutxabanca", 'manga': "Castor", 'estadio': None},
    "Submarino Oxidado": {'camiseta': "Pamesa Cerámica", 'manga': "Yoma", 'estadio': None},
    "Betis Manque Pierda": {'camiseta': "Gri Eléctrica", 'manga': "Jummel", 'estadio': None},
    "Sevilla Sin Monchi": {'camiseta': None, 'manga': "Adibas", 'estadio': None},
    "Valencia Sin Estadio": {'camiseta': "TM Inmobiliaria", 'manga': "Pumba", 'estadio': None},
    "Celta de Viejo": {'camiseta': "Estrella Galaica", 'manga': "Jummel", 'estadio': "Abanka"},
    "Rayo Vallecansado": {'camiseta': "Digui Telecom", 'manga': "Umbrow", 'estadio': None},
    # Serie A 2026-27
    "Piamonte Calcio": {'camiseta': "Jip", 'manga': "Adibas", 'estadio': "Alianz Seguros"},
    "Inter de Milan Roto": {'camiseta': "Betsun", 'manga': "Naik", 'estadio': None},
    "Milan Abuelo": {'camiseta': "Fly Emirados", 'manga': "Pumba", 'estadio': None},
    "Napoli Pizzeria": {'camiseta': None, 'manga': "EA Siete", 'estadio': None},
    "Roma Imperio Caido": {'camiseta': "Eurobett", 'manga': "Adibas", 'estadio': None},
    "Lazio Aguila Calva": {'camiseta': None, 'manga': "Misuno", 'estadio': None},
    "Atalanta Diosa Cansada": {'camiseta': "Léte Agua", 'manga': "Niu Balans", 'estadio': "Niu Balans"},
    "Fiorentina Violeta Marchita": {'camiseta': "Mediacomm", 'manga': "Yoma", 'estadio': None},
    "Bologna Mortadela": {'camiseta': "Saputto Quesos", 'manga': "Makron", 'estadio': None},
    "Como Lago Rico": {'camiseta': "Revolute", 'manga': "Adibas", 'estadio': None},
    "Torino Granate Triste": {'camiseta': "Suzuku", 'manga': "Yoma", 'estadio': None},
    "Genoa Pesto": {'camiseta': "Pulsé Luz y Gas", 'manga': "Cappa", 'estadio': None},
    # Brasileirão 2026
    "Flamenguito": {'camiseta': "Betanio", 'manga': "Adibas", 'estadio': None},
    "Palmerinha": {'camiseta': "Sportinbet", 'manga': "Pumba", 'estadio': "Nubanc"},
    "Botaagua": {'camiseta': "Vebet", 'manga': "Misuno", 'estadio': None},
    "Don Pablo": {'camiseta': "Superbete", 'manga': "Niu Balans", 'estadio': None},
    "Flumando": {'camiseta': "Superbete", 'manga': "Pumba", 'estadio': None},
    "Gremiont": {'camiseta': None, 'manga': "Niu Balans", 'estadio': None},
    "Corinchados": {'camiseta': "Esportes da Suerte", 'manga': "Naik", 'estadio': "Neo Químico"},
    "Colorado Desteñido": {'camiseta': None, 'manga': "Adibas", 'estadio': None},
    "Galo Cansado": {'camiseta': "H3Bet", 'manga': "Naik", 'estadio': "MRB Construtora"},
    "Cruzeiro Endeudado": {'camiseta': "Betnacionall", 'manga': "Adibas", 'estadio': None},
    "Bahía Citizen": {'camiseta': None, 'manga': "Pumba", 'estadio': None},
    "Vasco da Goma": {'camiseta': None, 'manga': "Naik", 'estadio': None},
    # Liga Profesional Argentina 2026
    "Boca Grande": {'camiseta': "Betsun", 'manga': "Adibas", 'estadio': None},
    "River Au": {'camiseta': "Betanio", 'manga': "Adibas", 'estadio': None},
    "Corriendo": {'camiseta': "Betsun", 'manga': "Naik", 'estadio': None},
    "Desindependiente": {'camiseta': "DeportesBet Ar", 'manga': "Pumba", 'estadio': None},
    "San Lorenzont": {'camiseta': "Casino Bs As Online", 'manga': "Atómico", 'estadio': None},
    "Talleres de tallarines": {'camiseta': "Holzim Cemento", 'manga': "Le Gallo Deportif", 'estadio': None},
    "Pincharratas de La Plata": {'camiseta': "Banco Supervieja", 'manga': "Ruje", 'estadio': None},
    "Vélez Sarsfall": {'camiseta': None, 'manga': "Makron", 'estadio': None},
    "Rosario Canalla": {'camiseta': "City Centro Online", 'manga': "Le Gallo Deportif", 'estadio': None},
    "Lanús Granate Oxidado": {'camiseta': "Mapey Adhesivos", 'manga': "Umbrow", 'estadio': None},
    "Argentinos Juniorsitos": {'camiseta': "Misterbet", 'manga': "Umbrow", 'estadio': None},
    "Huracán Brisa": {'camiseta': "Misterbet", 'manga': "Cappa", 'estadio': None},
    # Liga BetPlay 2026
    "Narconal": {'camiseta': "Betsun", 'manga': "Naik", 'estadio': None},
    "Pobres Vagos": {'camiseta': "Cerveza Anduina", 'manga': "Adibas", 'estadio': None},
    "ABerica de Cali": {'camiseta': "Pocker", 'manga': "Rebook", 'estadio': None},
    "Junior daddy": {'camiseta': "BetPlei", 'manga': "Adibas", 'estadio': None},
    "Deportivo Casi": {'camiseta': "Wplei", 'manga': None, 'estadio': None},
    "Independiente Chanda fe": {'camiseta': "Colanto", 'manga': "Phila", 'estadio': None},
    "Deportes Llorima": {'camiseta': "BetPlei", 'manga': "Umbrow", 'estadio': None},
    "Once Faldas": {'camiseta': "Colanto", 'manga': "Rebook", 'estadio': None},
    "Poderoso de la Montaña Rusa": {'camiseta': "Colanto", 'manga': "Adibas", 'estadio': None},
    "Leopardos Desmanchados": {'camiseta': None, 'manga': "Lotte", 'estadio': None},
    "Volcánico Apagado de Pasto": {'camiseta': "Aguardiente Nariñez", 'manga': "Bomán", 'estadio': None},
    # Uruguay y Ecuador: solo la marca de ropa (sin fuente fiable del patrocinador principal)
    "Penarol Roto": {'camiseta': None, 'manga': "Pumba", 'estadio': None},
    "Nacionall de Montevideo": {'camiseta': None, 'manga': "Umbrow", 'estadio': None},
    "Barcelona Falso de Guayaquil": {'camiseta': None, 'manga': "Maratón Sports", 'estadio': None},
    "Liga de Quito Rota": {'camiseta': None, 'manga': "Pumba", 'estadio': None},
    "Independiente del Valle de Lagrimas": {'camiseta': None, 'manga': "Maratón Sports", 'estadio': None},
}

# La base editada (alpha_football_edited_db.json) renombra 3 clubes de LaLiga: mismos patrocinios.
ALIAS_BD_EDITADA = {"Real Vadrid": "Real Madriz", "Gordona": "Girona Sorpresa", "Flaco de bilbao": "Athletic de Bilbao"}
for _alias, _orig in ALIAS_BD_EDITADA.items():
    PATROCINIOS_REALES[_alias] = PATROCINIOS_REALES[_orig]
