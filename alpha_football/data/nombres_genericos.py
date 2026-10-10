# -*- coding: utf-8 -*-
"""
Alpha Football v0.4.22.0 — NOMBRES Y APELLIDOS GENÉRICOS (no parodias) por país.

Los usan los regens (retiros.py), los canteranos, los agentes libres y los jugadores nuevos del
editor para que cada nacionalidad tenga nombres propios y la combinación nombre + apellido casi
nunca se repita. Hay 8 países (los de paises.PAISES) con 100 o más nombres y 100 o más apellidos cada uno.
`retiros.NOMBRES_POR_PAIS` es este mismo diccionario.
"""
from __future__ import annotations


def _lista(texto: str) -> list:
    """'Juan, Pedro' -> ['Juan', 'Pedro'] (separa por comas y por saltos de línea)."""
    return [x.strip() for x in texto.replace("\n", " ").split(",") if x.strip()]


_COLOMBIA_N = _lista("""
Juan, Andrés, Carlos, Santiago, Sebastián, Camilo, Felipe, Jhon, Luis, Daniel,
Kevin, Brayan, Juan David, Jhonatan, Mateo, Samuel, Cristian, Óscar, Duván, Yeison,
Alejandro, Alexander, Álvaro, Anderson, Andrey, Ángel, Antony, Armando, Bladimir, Brandon,
Breiner, César, Cristopher, Dairon, Damián, Darwin, David, Dayro, Deiver, Deyber,
Diego, Diomedes, Edgar, Edwin, Eduardo, Efraín, Elkin, Emerson, Emilio, Erick,
Esteban, Fabián, Fabio, Faustino, Fernando, Francisco, Frank, Freddy, Gabriel, Germán,
Gilberto, Giovanni, Gustavo, Hader, Harold, Héctor, Hernán, Hugo, Iván, Jaime,
Jair, Jairo, James, Javier, Jefferson, Jeison, Jerson, Jesús, Jhoan, Jhon Jairo,
Jorge, José, Josué, Juan Camilo, Juan Carlos, Juan Pablo, Julián, Kleber, Leonardo, Lorenzo,
Manuel, Marcos, Mario, Mauricio, Miguel, Nelson, Néstor, Nicolás, Orlando, Pablo,
Rafael, Ramiro, Raúl, Ricardo, Roberto, Rodrigo, Rubén, Sergio, Stiven, Tomás,
Wilmar, Wílder, William, Yerry, Yimmi
""")
_COLOMBIA_A = _lista("""
Rodríguez, Gómez, Martínez, Hernández, López, García, Moreno, Mosquera, Ramírez, Valencia,
Palacios, Castaño, Rentería, Cuesta, Arboleda, Quiñones, Murillo, Zapata, Ospina, Cardona,
Restrepo, Giraldo, Bedoya, Cuadrado, Acosta, Aguirre, Alzate, Angulo, Arango, Arias,
Ayala, Barrios, Blandón, Bolaños, Borja, Bravo, Cabrera, Caicedo, Calderón, Campaz,
Cano, Carvajal, Castillo, Castro, Chará, Córdoba, Correa, Cortés, Díaz, Duque,
Escobar, Espinosa, Fernández, Figueroa, Flórez, Franco, Gaviria, González, Gutiérrez, Guzmán,
Henao, Herrera, Hurtado, Jaramillo, Lasso, Londoño, Lozano, Marín, Mejía, Mena,
Montoya, Mora, Muñoz, Naranjo, Obando, Ocampo, Orozco, Ortiz, Osorio, Pabón,
Parra, Patiño, Peña, Perea, Pérez, Pineda, Posada, Quintero, Ríos, Rivera,
Rojas, Romero, Rueda, Salazar, Sánchez, Sarmiento, Sierra, Suárez, Tapia, Tobón,
Torres, Trujillo, Uribe, Valderrama, Vargas, Vásquez, Vélez, Villa, Zambrano
""")

_BRASIL_N = _lista("""
João, Pedro, Lucas, Gabriel, Matheus, Rafael, Gustavo, Felipe, Vinícius, Thiago,
Bruno, Caio, Rodrigo, Diego, Igor, Luan, Wesley, Kaique, Davi, Everton,
Adriano, Alan, Alex, Alisson, Anderson, André, Arthur, Augusto, Bernardo, Breno,
Carlos, Cauã, Cássio, César, Cláudio, Cristiano, Danilo, Douglas, Eduardo, Elias,
Emerson, Enzo, Erick, Fábio, Fabrício, Fernando, Fred, Gerson, Guilherme, Heitor,
Henrique, Hugo, Humberto, Iago, Ítalo, Jean, Jonas, Jorge, José, Júlio,
Kauê, Leandro, Leonardo, Léo, Lorenzo, Luiz, Marcelo, Marcos, Mário, Mateus,
Maurício, Miguel, Murilo, Nathan, Nelson, Otávio, Paulo, Patrick, Renan, Renato,
Ricardo, Roberto, Rogério, Samuel, Sérgio, Thales, Tiago, Vítor, Wagner, Walter,
Willian, Yuri, Ygor, Wellington, Washington, Raphael, Otto, Nicolas, Natan, Marlon,
Luciano, Lázaro, Kleber, Jefferson, Hélio, Gilberto, Giovani, Diogo, Denílson, Daniel,
Cleiton, Caetano
""")
_BRASIL_A = _lista("""
Silva, Santos, Oliveira, Souza, Lima, Pereira, Costa, Ferreira, Almeida, Carvalho,
Ribeiro, Gomes, Martins, Rocha, Barbosa, Araújo, Nascimento, Moura, Cardoso, Teixeira,
Correia, Dias, Alves, Andrade, Assis, Azevedo, Batista, Bezerra, Borges, Braga,
Brito, Campos, Cavalcante, Coelho, Conceição, Cunha, Duarte, Fernandes, Figueiredo, Fonseca,
Freitas, Garcia, Guimarães, Henrique, Lacerda, Leite, Lopes, Macedo, Machado, Magalhães,
Marques, Medeiros, Melo, Mendes, Miranda, Monteiro, Moraes, Moreira, Nogueira, Nunes,
Paiva, Peixoto, Pinto, Ramos, Reis, Rezende, Rodrigues, Sampaio, Sá, Siqueira,
Tavares, Vasconcelos, Vieira, Xavier, Amaral, Aguiar, Barros, Bastos, Bittencourt, Cordeiro,
Domingues, Esteves, Farias, Franco, Gonçalves, Lemos, Maia, Matos, Neves, Pacheco,
Prado, Queiroz, Ribas, Salgado, Santana, Soares, Toledo, Viana, Barreto, Cabral,
Camargo, Carneiro, Castro, Dantas, Fagundes, Galvão, Holanda, Jesus, Lobo, Mattos, Nobre
""")

_ARGENTINA_N = _lista("""
Juan, Matías, Lautaro, Nicolás, Facundo, Santiago, Tomás, Agustín, Franco, Gonzalo,
Ezequiel, Julián, Thiago, Valentín, Leandro, Maximiliano, Joaquín, Bruno, Lucas, Enzo,
Alan, Alejandro, Alexis, Ariel, Axel, Baltasar, Bautista, Benjamín, Braian, Brian,
Cristian, Damián, Dante, Diego, Eduardo, Emanuel, Emiliano, Ernesto, Esteban, Fabián,
Federico, Fernando, Gabriel, Germán, Gastón, Guido, Guillermo, Gustavo, Héctor, Hernán,
Ignacio, Iván, Jeremías, Jorge, José, Juan Cruz, Juan Manuel, Kevin, Lisandro, Luciano,
Luis, Manuel, Marcelo, Marcos, Mariano, Mario, Martín, Mateo, Mauro, Miguel,
Nahuel, Néstor, Octavio, Pablo, Patricio, Pedro, Rafael, Ramiro, Raúl, Renzo,
Ricardo, Rodrigo, Rubén, Sebastián, Sergio, Simón, Tadeo, Teo, Walter, Yamil,
Marco, Lorenzo, Dylan, Jonathan, Cristóbal, Elías, Horacio, Claudio, Carlos, Aníbal
""")
_ARGENTINA_A = _lista("""
González, Fernández, Rodríguez, López, Martínez, Pérez, Gómez, Díaz, Romero, Sosa,
Álvarez, Benítez, Acosta, Medina, Herrera, Suárez, Aguirre, Giménez, Ledesma, Paredes,
Molina, Correa, Aguilar, Alonso, Arce, Ávalos, Bustos, Cabrera, Cáceres, Campos,
Carrizo, Castillo, Castro, Cardozo, Chávez, Contreras, Cruz, Delgado, Domínguez, Duarte,
Escobar, Farías, Figueroa, Flores, Franco, Funes, Gallardo, García, Godoy, Guzmán,
Gutiérrez, Ibáñez, Juárez, Luna, Maldonado, Mansilla, Márquez, Mendoza, Miranda, Montenegro,
Morales, Moreno, Muñoz, Navarro, Núñez, Ojeda, Olivera, Ortiz, Palacios, Peralta,
Pereyra, Quiroga, Ramírez, Reyes, Ríos, Rivero, Rojas, Rossi, Ruiz, Salas,
Sánchez, Silva, Soria, Toledo, Torres, Vargas, Vega, Vera, Villalba, Villarreal,
Zárate, Barrios, Bravo, Coronel, Dávila, Esquivel, Ferreyra, Gaitán, Heredia, Lucero,
Maidana, Montiel, Pizarro, Robles, Sandoval, Tapia, Urquiza, Vázquez, Videla, Zabala
""")

_ESPANA_N = _lista("""
Pablo, Álvaro, Sergio, Javier, Adrián, Hugo, Marcos, Iker, Unai, Raúl,
Alejandro, Daniel, Mario, Rubén, Iván, Aitor, Jorge, Manuel, Gonzalo, Nacho,
Aarón, Abel, Adolfo, Alberto, Alfonso, Andrés, Ángel, Antonio, Arnau, Asier,
Borja, Carlos, César, Cristian, Dani, David, Diego, Eduardo, Enrique, Eric,
Ernesto, Fernando, Francisco, Gabriel, Gerard, Guillermo, Héctor, Ibai, Ignacio, Imanol,
Isaac, Joan, Joaquín, Jon, Jordi, José, Josep, Juan, Julen, Lucas,
Luis, Marc, Martín, Mateo, Miguel, Mikel, Nil, Óscar, Oriol, Pau,
Pedro, Rafael, Ramón, Roberto, Rodrigo, Samuel, Santiago, Saúl, Sebastián, Tomás,
Víctor, Xavier, Yeray, Aleix, Aimar, Beñat, Gaizka, Iñaki, Lander, Pelayo,
Rober, Salvador, Teo, Bruno, Ander, Fran, Joel, Kike, Lluís, Marcel, Nico, Odei
""")
_ESPANA_A = _lista("""
García, Fernández, González, Rodríguez, López, Martínez, Sánchez, Pérez, Gómez, Martín,
Jiménez, Ruiz, Hernández, Díaz, Moreno, Muñoz, Álvarez, Romero, Navarro, Torres,
Domínguez, Vázquez, Gil, Serrano, Blanco, Molina, Morales, Suárez, Ortega, Delgado,
Castro, Ortiz, Rubio, Marín, Sanz, Iglesias, Medina, Garrido, Cortés, Castillo,
Santos, Lozano, Guerrero, Cano, Prieto, Méndez, Cruz, Calvo, Gallego, Vidal,
León, Márquez, Herrera, Peña, Flores, Cabrera, Campos, Vega, Fuentes, Carrasco,
Diez, Caballero, Reyes, Nieto, Aguilar, Pascual, Santana, Herrero, Montero, Lorenzo,
Hidalgo, Giménez, Ibáñez, Ferrer, Durán, Santiago, Benítez, Mora, Vicente, Vargas,
Arias, Carmona, Crespo, Román, Pastor, Soto, Sáez, Velasco, Moya, Soler,
Parra, Esteban, Bravo, Gallardo, Rojas, Aguirre, Etxeberria, Goikoetxea, Urrutia, Mendizábal,
Aranda, Casado, Bermúdez, Villanueva, Segura, Salas, Palacios, Roldán, Cordero, Redondo
""")

_INGLATERRA_N = _lista("""
Jack, Harry, Oliver, George, James, Charlie, Thomas, Jacob, Alfie, Oscar,
William, Joshua, Ethan, Callum, Mason, Lewis, Ryan, Connor, Jordan, Tyler,
Aaron, Adam, Alex, Alexander, Andrew, Archie, Arthur, Ben, Benjamin, Blake,
Bradley, Brandon, Cameron, Carl, Cole, Daniel, Danny, David, Dean, Declan,
Dominic, Edward, Elliot, Finley, Frankie, Freddie, Gareth, Gary, Harrison, Henry,
Isaac, Jake, Jamie, Jason, Jay, Jesse, Joe, Joel, Jonathan, Jude,
Kai, Kieran, Kyle, Leo, Liam, Logan, Louis, Luke, Marcus, Mark,
Matthew, Max, Michael, Nathan, Nicholas, Noah, Owen, Patrick, Paul, Peter,
Phil, Reece, Reuben, Rhys, Richard, Robert, Ronnie, Rory, Sam, Samuel,
Scott, Sean, Sebastian, Stanley, Stephen, Theo, Tom, Toby, Tommy, Troy,
Vincent, Wayne, Zach, Ashley, Craig, Dylan, Elijah, Jayden, Kevin, Lloyd
""")
_INGLATERRA_A = _lista("""
Smith, Jones, Taylor, Brown, Williams, Wilson, Johnson, Davies, Robinson, Wright,
Thompson, Evans, Walker, White, Roberts, Green, Hall, Wood, Jackson, Clarke,
Harris, Lewis, Allen, Anderson, Armstrong, Baker, Barnes, Bell, Bennett, Brooks,
Bailey, Butler, Campbell, Carter, Chapman, Clark, Cole, Collins, Cook, Cooper,
Cox, Cross, Dixon, Edwards, Ellis, Fisher, Fletcher, Foster, Fox, Gibson,
Gray, Griffiths, Hamilton, Harrison, Hart, Hayes, Henderson, Hill, Holmes, Howard,
Hudson, Hughes, Hunt, Hunter, James, Kelly, Kennedy, King, Knight, Lawrence,
Lee, Marshall, Martin, Mason, Matthews, Miller, Mills, Mitchell, Moore, Morgan,
Morris, Murray, Nelson, Newman, Owen, Palmer, Parker, Patel, Payne, Pearce,
Phillips, Powell, Price, Reed, Reynolds, Richardson, Rogers, Russell, Saunders, Scott,
Shaw, Simpson, Spencer, Stevens, Stewart, Turner, Walsh, Ward, Watson, Webb
""")

_ITALIA_N = _lista("""
Alessandro, Andrea, Antonio, Alberto, Aldo, Alessio, Angelo, Antonino, Armando, Bruno,
Carlo, Christian, Claudio, Cristiano, Daniele, Davide, Dario, Diego, Domenico, Edoardo,
Emanuele, Enrico, Enzo, Fabio, Fabrizio, Federico, Filippo, Flavio, Francesco, Franco,
Gabriele, Gaetano, Gianluca, Gianmarco, Giacomo, Giorgio, Giovanni, Giulio, Giuseppe, Giancarlo,
Guido, Ivan, Jacopo, Leonardo, Lorenzo, Luca, Luciano, Luigi, Manuel, Marco,
Mario, Marino, Massimo, Matteo, Mattia, Maurizio, Michele, Nicola, Nicolò, Orlando,
Pasquale, Paolo, Pietro, Raffaele, Riccardo, Roberto, Rocco, Rosario, Salvatore, Samuele,
Sandro, Sergio, Simone, Stefano, Tommaso, Umberto, Valerio, Vincenzo, Vito, Vittorio,
Walter, Zeno, Elia, Emilio, Ettore, Fausto, Fedele, Gennaro, Ignazio, Italo,
Livio, Lucio, Mirko, Ottavio, Renato, Romeo, Ruggero, Santo, Sebastiano, Tiziano,
Ugo, Alfredo, Amedeo, Bernardo, Cesare, Dino, Eros, Ennio, Fulvio
""")
_ITALIA_A = _lista("""
Rossi, Russo, Ferrari, Esposito, Bianchi, Romano, Colombo, Ricci, Marino, Greco,
Bruno, Gallo, Conti, De Luca, Mancini, Costa, Giordano, Rizzo, Lombardi, Moretti,
Barbieri, Fontana, Santoro, Mariani, Rinaldi, Caruso, Ferrara, Galli, Martini, Leone,
Longo, Gentile, Martinelli, Vitale, Lombardo, Serra, Coppola, De Santis, D'Angelo, Marchetti,
Parisi, Villa, Conte, Ferraro, Ferri, Fabbri, Bianco, Marini, Grasso, Valentini,
Messina, Sala, De Angelis, Gatti, Pellegrini, Palumbo, Sanna, Farina, Rizzi, Monti,
Cattaneo, Morelli, Amato, Silvestri, Mazza, Testa, Grassi, Pellegrino, Carbone, Giuliani,
Benedetti, Barone, Rossetti, Caputo, Montanari, Guerra, Palmieri, Bernardi, Martino, Fiore,
De Rosa, Ferretti, Bellini, Basile, Riva, Donati, Piras, Vitali, Battaglia, Sartori,
Neri, Costantini, Milani, Pagano, Ruggiero, Sorrentino, D'Amico, Orlando, Negri, Bassi, Cirillo
""")

_URUGUAY_N = _lista("""
Alejandro, Álvaro, Andrés, Agustín, Alan, Alexis, Ángel, Antonio, Ariel, Bruno,
Brian, Carlos, Cristian, Damián, Daniel, Darío, Diego, Eduardo, Emiliano, Emilio,
Ernesto, Ezequiel, Fabián, Facundo, Federico, Felipe, Fernando, Franco, Gabriel, Gastón,
Gerardo, Germán, Gonzalo, Guillermo, Gustavo, Hugo, Ignacio, Ismael, Jonathan, Jorge,
José, Juan, Julio, Lautaro, Leandro, Leonardo, Lucas, Luciano, Luis, Marcelo,
Marcos, Mario, Martín, Mathías, Mauricio, Maximiliano, Nicolás, Octavio, Pablo, Pedro,
Rafael, Ramiro, Raúl, Renzo, Ricardo, Rodrigo, Rubén, Sebastián, Santiago, Sergio,
Tabaré, Thiago, Valentín, Walter, Washington, Yonathan, Nelson, Néstor, Matías, Mateo,
Joaquín, Jeremías, Horacio, Hernán, Gianni, Fabricio, Enzo, Elías, Dante, Cristhian,
César, Bautista, Baltasar, Axel, Aníbal, Alfonso, Adrián, Abel, Lorenzo, Maicol, Nahuel
""")
_URUGUAY_A = _lista("""
Rodríguez, González, Fernández, Pérez, Silva, García, Martínez, López, Díaz, Sosa,
Techera, Cabrera, Acosta, Suárez, Núñez, Ferreira, Pereira, Álvarez, Rivero, Rocha,
Olivera, Correa, Machado, Medina, Torres, Gómez, Cardozo, Píriz, Viera, Barrios,
Benítez, Castro, Ramos, Sánchez, Romero, Moreira, Vázquez, Duarte, Méndez, Mora,
Morales, Pintos, Lemos, Gutiérrez, Ortiz, Ríos, Rey, Vega, Giménez, Alonso,
Cáceres, Brun, Varela, Hernández, Peralta, Aguirre, Echeverría, Ferrari, Bueno, Amaral,
Bosch, Cuello, Delgado, Estévez, Fagúndez, Figueroa, Larrosa, Maciel, Maidana, Mendoza,
Nieves, Pedrozo, Quintana, Rebollo, Santos, Sena, Soca, Sorondo, Tejera, Umpiérrez,
Urruty, Vidal, Zabala, Zunino, Berrutti, Burgos, Carballo, Curbelo, Dos Santos, Falcón,
Gadea, Irigoyen, Nogueira, Pagani, Rama, Repetto, Saravia, Vilariño, Aparicio, Bagnasco
""")

_ECUADOR_N = _lista("""
Alexander, Alex, Ángel, Antonio, Anthony, Bryan, Byron, Carlos, Cristian, Cristhian,
Damián, Darwin, David, Diego, Edison, Edwin, Eduardo, Enner, Erick, Fabricio,
Fernando, Fidel, Franklin, Gabriel, Geovanny, Gonzalo, Gustavo, Henry, Hernán, Holger,
Iván, Jaime, Javier, Jefferson, Jhon, Jhonny, Joel, Jonathan, Jorge, José,
Juan, Júnior, Kevin, Kléber, Leonardo, Luis, Marcos, Mario, Michael, Miguel,
Moisés, Nelson, Nicolás, Óscar, Pablo, Patricio, Pedro, Pervis, Renato, Ricardo,
Richard, Roberto, Rodrigo, Segundo, Sebastián, Stalin, Vinicio, Washington, Wellington, Wilmer,
Wilson, Xavier, Yaimar, Alan, Andrés, Antony, Arturo, Bolívar, César, Christian,
Dixon, Elvis, Ezequiel, Félix, Galo, Gilson, Hugo, Ismael, Jairo, Joao,
Kenny, Lenín, Marlon, Milton, Narciso, Orlando, Rafael, Rolando, Walter, Willian
""")
_ECUADOR_A = _lista("""
Mina, Caicedo, Valencia, Estupiñán, Ibarra, Preciado, Plata, Hincapié, Gruezo, Arboleda,
Ayoví, Cifuentes, Cortez, Mena, Castillo, Rodríguez, Cevallos, Intriago, Lastra, Mosquera,
Quiñónez, Ordóñez, Palacios, Chalá, Bolaños, Campos, Carabalí, Caviedes, Cabezas, Cuero,
Chávez, Delgado, Espinoza, Estrada, Franco, García, Garcés, González, Guerrero, Guevara,
Herrera, Jácome, Landázuri, León, Loor, López, Lozano, Macías, Mendoza, Montaño,
Morales, Moreira, Muñoz, Navarrete, Obregón, Ortiz, Pacheco, Paredes, Paz, Pérez,
Pinargote, Quintero, Ramírez, Reasco, Reyes, Ríos, Rivera, Rojas, Romero, Ruiz,
Salazar, Sánchez, Sarmiento, Segura, Solórzano, Suárez, Tello, Terán, Tigrero, Torres,
Vargas, Vélez, Villacís, Villamar, Yagual, Zambrano, Zúñiga, Aguirre, Albán, Almeida,
Andrade, Bravo, Calero, Cedeño, Cobo, Cruz, Dávila, Egas, Flores, Gallegos, Gómez, Játiva
""")


# (nombres, apellidos) por nacionalidad; las claves son los nombres de paises.PAISES.
NOMBRES_POR_PAIS = {
    'Colombia': (_COLOMBIA_N, _COLOMBIA_A),
    'Brasil': (_BRASIL_N, _BRASIL_A),
    'Argentina': (_ARGENTINA_N, _ARGENTINA_A),
    'España': (_ESPANA_N, _ESPANA_A),
    'Inglaterra': (_INGLATERRA_N, _INGLATERRA_A),
    'Italia': (_ITALIA_N, _ITALIA_A),
    'Uruguay': (_URUGUAY_N, _URUGUAY_A),
    'Ecuador': (_ECUADOR_N, _ECUADOR_A),
}
