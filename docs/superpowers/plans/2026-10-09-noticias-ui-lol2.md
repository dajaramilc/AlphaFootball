# Noticias: interfaz, generadores, prensa, logros, editor y nombres (parte de `lol2`) — plan de implementación

> **Para quien ejecuta:** lo implementa la sesión `lol2` en esta misma sesión (ejecución nativa, tarea por tarea,
> con TDD). La parte de `lol` está en `2026-10-09-cadena-dt-noticias-lol.md`. Los pasos usan casillas `- [ ]`.
> Cada tarea fija archivos, interfaces, casos de prueba exactos y cómo se verifica; el cuerpo de las funciones
> se escribe al implementar siguiendo las notas de la tarea (solo se pegan aquí los fragmentos delicados).

**Objetivo:** que las noticias, la prensa, los logros y el editor ampliado tengan interfaz y lógica propias
(0.4.22.0: nombres genéricos y editor · 0.4.23.0: Noticias).

**Arquitectura:** `lol` entrega el núcleo `noticias.py` (contrato único de publicación). Esta parte lo consume:
`noticias_gen.py` publica los hechos de cada jornada y del cierre de temporada; `prensa.py` y `logros.py` son
lógica pura sobre `datos_carrera`; la UI es `ui/noticias_visual.py` (tarjetas cacheadas, una sola fuente para
feed, pantalla y carga), `ui/noticias_screen.py`, el feed del hub, `ui/prensa_overlay.py` (modal sobre el
prepartido y el postpartido) y el overlay de logros en `career_screen`. El editor se amplía con funciones puras
testeables (`edit_screen.py`) y la UI solo las llama.

**Stack:** Python 3, pygame (SDL dummy en tests), tests como funciones sueltas ejecutables con
`pytest tests/<archivo>.py -q`.

**Spec:** `docs/superpowers/specs/2026-10-09-entrenadores-noticias-design.md` (secciones 3, 6-11).

## Restricciones globales

- Sin commits, stash, checkout ni reset: el árbol tiene trabajo sin commitear de las dos sesiones. (No hay paso de commit.)
- `Edit` puntual en archivos existentes; nunca `Write` sobre uno que ya existe. Tests nuevos en archivos nuevos.
- Avisar a `lol` **antes y después** de tocar: `ui/match_screen.py` (solo la línea de `sim_ctx` ~1191 y nada del
  bloque 436-600), `engine.py`, `partido_ctx.py`, `models.py`, `retiros.py`, `main.py`, `ui/ayuda.py`, `ui/atajos.py`.
- La suite se corre **archivo por archivo** (`pytest tests` entero se cuelga por los `smoke_*`/`diag_*`).
- Cabecera de test (copiar tal cual de `tests/test_notificaciones.py:1-10`): `sys.path.insert`, `SDL_VIDEODRIVER=dummy`,
  `SDL_AUDIODRIVER=dummy`, `pygame.init()`, `screen = pygame.display.set_mode((1280, 720))`,
  `save.guardar_en_slot = lambda *a, **k: None`, `from test_revision_v291 import estado_carrera`. Pie: el bloque
  `if __name__ == '__main__':` de ese mismo archivo (corre todos los `test_*`).
- Si un test importa `main`, restaurar `pygame.event.get` justo después (patrón de `tests/test_calendario.py:352-356`).
- Noticias: máximo 50, caducan a las 3 jornadas, titular ≤ 60 caracteres, importancia 1-5, feed ≥ 3. Imágenes
  verticales 9:16 en `alpha_football/assets/noticias/<categoria><n>.jpg`; sin imagen, color de la categoría.
- Feed del hub: tarjeta 198 × 352 bajo la fila de pestañas, rota cada 5 s, fundido de 180 ms, tecla **N**.
  Carga de temporada: mínimo 3 s solo en el cambio de temporada (0 con SDL dummy); guardar y cargar conservan 0,4 s.
- `publicar()` de `lol`: ids monótonos (cachear por id es seguro), `temporada=`/`jornada=` explícitos pisan a los
  actuales, `accion={'pantalla','texto'}` opcional. **No generar** fichajes, cambios de DT ni cierre del otro continente
  (son de `lol`). Yo publico solo el cierre de la temporada del user, desde `avanzar_nueva_temporada`.
- Cada bloque que corre en cierre de jornada va en su propio `try/except` con `logger.error`; nada nuevo rompe un guardado viejo
  (todo lo nuevo de `datos_carrera` se crea con `setdefault`).
- Prensa: máximo una pregunta antes y una después por partido; nunca en amistosos; siempre se puede SALTAR.
  Tonos: Motivador (+2 moral propia) · Provocador (−2 moral del siguiente rival, noticia importancia 4) ·
  Humilde (+1 moral propia) · Agresivo (`factor_tarjetas` 1.6 en el siguiente partido, ambos equipos).
- Logros: 9 (ver Tarea 7), cada uno publica una noticia `'logro'` de importancia 5.
- Editor: el valor de mercado **no** se edita; el resto de campos del jugador sí. Máximo de plantilla = `market.PLANTILLA_MAXIMA` (40).
- Nombres genéricos: ≥ 100 nombres y ≥ 100 apellidos por país, para los 8 países de `paises.PAISES`.
- Versiones: las sube `lol` (0.4.22.0 = Tarea 1 y 2; 0.4.23.0 = Tareas 3-7).

## Foco de revisión

1. **Hub sin noticias o sin imágenes** (carpeta `assets/noticias` vacía o inexistente, feed vacío): el panel muestra un
   mensaje o el color de la categoría y no lanza excepción (Tarea 3).
2. **Titular largo o palabra gigante** en la tarjeta de 198 px y en la lista: se recorta con "…" sin salirse de la tarjeta (Tarea 3).
3. **Guardado viejo**: `datos_carrera` sin `prensa`, `logros`, `records` ni `noticias_gen`, y base editada vieja sin
   los campos nuevos de DT/jugador, abren y guardan sin `KeyError` (Tareas 2, 4, 6, 7).
4. **Prensa en situaciones raras**: amistoso, sin liga, rival sin jugadores, partido ya consultado → no se ofrece o no
   rompe; SALTAR no cambia moral ni tensión (Tarea 6).
5. **Editor con datos malos**: borrar todos los dígitos de un atributo (queda 0), crear jugador con plantilla llena
   (mensaje y no agrega), quitar el DT de un club ya sin DT, asignar con la lista de libres vacía (Tarea 2).

## Mapa de archivos

| Archivo | Acción | Tarea |
|---|---|---|
| `alpha_football/data/nombres_genericos.py` | crear | 1 |
| `alpha_football/retiros.py` (solo `NOMBRES_POR_PAIS`, ~28-59) | modificar | 1 |
| `alpha_football/ui/edit_screen.py`, `alpha_football/models.py` (campos `dt_*` de `Equipo`) | modificar | 2 |
| `alpha_football/ui/noticias_visual.py`, `ui/noticias_screen.py` | crear | 3 |
| `ui/league_screen.py`, `main.py`, `ui/ayuda.py`, `ui/atajos.py` | modificar | 3 |
| `alpha_football/noticias_gen.py` | crear | 4 |
| `ui/pantalla_carga.py`, `ui/resumen_temporada_screen.py` | modificar | 5 |
| `alpha_football/prensa.py`, `ui/prensa_overlay.py` | crear | 6 |
| `ui/prepartido_screen.py`, `ui/postpartido.py`, `ui/match_screen.py` (1 línea), `partido_ctx.py`, `engine.py` | modificar | 6 |
| `alpha_football/logros.py` | crear | 7 |
| `ui/career_screen.py` | modificar | 7 |
| tests nuevos | crear | uno por tarea (ver cada una) |
| tests viejos de OFICINA y atajos | modificar | 3 |

Orden (spec §13): 1 y 2 no dependen del núcleo de `lol`; de la 3 en adelante hace falta que `lol` avise "contrato listo".

---

### Tarea 1: nombres y apellidos genéricos (8 países)

**Archivos:** crear `alpha_football/data/nombres_genericos.py`, `tests/test_nombres_genericos.py`;
modificar `alpha_football/retiros.py:27-59` (reemplazar el dict literal por el import).

**Produce:**

```python
# data/nombres_genericos.py
NOMBRES_POR_PAIS: dict[str, tuple[list[str], list[str]]]   # claves = paises.PAISES[i]['nombre']
# 'Inglaterra','España','Italia','Brasil','Argentina','Colombia','Uruguay','Ecuador'
```

`retiros.NOMBRES_POR_PAIS` pasa a ser el mismo objeto (`from alpha_football.data.nombres_genericos import NOMBRES_POR_PAIS`).
Los consumidores (`nombres.py`, `competiciones.py:616`, `generar_regen`, tests `test_v236.py:313` y `test_nacionalidades.py:66`)
no cambian: siguen leyendo `(nombres, apellidos)`.

- [ ] **Paso 1: tests que fallan** (`tests/test_nombres_genericos.py`)
  - `test_ocho_paises_con_100_o_mas`: `set(N) == {p['nombre'] for p in PAISES}`; por país `len(nombres) >= 100`, `len(apellidos) >= 100`.
  - `test_sin_repetidos`: `len(set(lista)) == len(lista)` en las 16 listas.
  - `test_texto_limpio`: cada entrada coincide con `^[A-Za-zÁÉÍÓÚÜÑáéíóúüñãõçâêôàè' -]+$` y no está vacía ni con espacios en los bordes.
  - `test_retiros_usa_el_banco_nuevo`: `retiros.NOMBRES_POR_PAIS is nombres_genericos.NOMBRES_POR_PAIS`.
  - `test_regen_uruguayo_no_sale_con_nombre_espanol`: `Jugador(... nacionalidad='Uruguay', edad=36)` → `generar_regen(viejo, random.Random(1), 992, set(), pais_club='Uruguay')` devuelve `nacionalidad == 'Uruguay'` y `nombre in N['Uruguay'][0]` y `apellido in N['Uruguay'][1]` (hoy cae al pozo de España).
  - `test_nombre_unico_respeta_el_pais`: `nombres.nombre_unico('Italia', random.Random(3), reservar=False)` → nombre y apellido salen de `N['Italia']`.
- [ ] **Paso 2:** `pytest tests/test_nombres_genericos.py -q` → falla (`ModuleNotFoundError`).
- [ ] **Paso 3: implementar.** Formato compacto para no inflar el archivo:

```python
def _lista(texto: str) -> list:
    return [x.strip() for x in texto.replace("\n", " ").split(",") if x.strip()]

_COL_N = _lista("Juan, Andrés, Carlos, Santiago, ...")   # conservar primero los 20/22 actuales de retiros.py y completar a >= 100
...
NOMBRES_POR_PAIS = {'Colombia': (_COL_N, _COL_A), 'Brasil': (_BRA_N, _BRA_A), ...}   # 8 claves
```

  Nombres compuestos ("Juan David") permitidos; apellidos compuestos no (`nombres.nombre_unico` ya forma los suyos). Italia, Uruguay y
  Ecuador son listas nuevas; las otras cinco conservan sus entradas actuales y suman hasta ≥ 100. Luego, en `retiros.py`, borrar
  el dict (líneas 27-59) y dejar `from alpha_football.data.nombres_genericos import NOMBRES_POR_PAIS  # noqa: E402` en su lugar.
- [ ] **Paso 4: verificar.** `pytest tests/test_nombres_genericos.py tests/test_nacionalidades.py tests/test_v236.py tests/test_pedidos_v440.py -q` en verde.
- [ ] **Paso 5:** avisar a `lol` (tocué `retiros.py`).

---

### Tarea 2: editor ampliado (DT completos, jugador completo, crear jugador)

**Archivos:** modificar `alpha_football/ui/edit_screen.py`, `alpha_football/models.py:340-342` y `:454-456`;
crear `tests/test_editor_ampliado.py` (los tests viejos `tests/test_editor_libres_dts.py`, `test_patrocinios_editor.py`,
`test_ligas_v370.py`, `test_estilos_v330.py` siguen verdes sin tocarlos).

**Produce (todo en `edit_screen.py`, funciones puras sin pygame):**

```python
ATRIBUTOS = ("ataque", "defensa", "fisico", "tecnica", "mental")
PERSONALIDADES = ["normal", "lider", "profesional", "polemico", "mercenario"]
# (clave, etiqueta, tipo, a, b): 'int' -> a=mínimo, b=máximo · 'sel' -> a=lista de opciones, b=None
CAMPOS_JUGADOR_P2: list[tuple]            # 14 campos: ataque…mental, penales, resistencia, moral, energia,
                                          # contrato_anios, salario, clausula, personalidad, nacionalidad
overall_de(j: dict) -> int                # media de los 5 atributos
fijar_campo_int(j, clave, valor, minimo, maximo) -> int
fijar_ovr_todos(j, ovr) -> None           # atajo "todos iguales" (el campo OVR de la página 1)
teclear_entero(actual, char, minimo, maximo, max_digitos) -> int
borrar_digito(actual) -> int
ciclar_opcion(actual, opciones, paso=1) -> str
sanear_jugador(j) -> None                 # lleva cada campo de CAMPOS_JUGADOR_P2 a su rango (se llama al salir del campo)
opciones_nacionalidad(db) -> list         # los 8 países + cualquier otra nacionalidad que ya esté en la base
siguiente_id(db) -> int                   # máximo id de clubes y libres + 1
nuevo_jugador_club(db, liga_clave, idx_equipo) -> int   # índice nuevo o -1 si la plantilla ya tiene PLANTILLA_MAXIMA
prestigio_de(calif) -> str                # 'BAJO' < 50 · 'MEDIO' 50-69 · 'ALTO' >= 70 (mismo corte que entrenadores.prestigio)
quitar_dt(db, club) -> bool               # el DT efectivo pasa a db['_dts_libres']; club['dt_sin'] = True
asignar_dt(db, club, idx_libre) -> bool   # trae el libre al club; el anterior (si lo había) pasa a libres
```

Contrato de datos con la carrera (lo lee `entrenadores.asegurar_dts` de `lol`): club → `dt_nombre`, `dt_estilo`,
`dt_calif`, `dt_nacionalidad`, `dt_edad`, `dt_sin`; `_dts_libres` → `nombre`, `estilo`, `calif`, `nacionalidad`, `edad`.
`Equipo` suma `dt_nacionalidad: str = ""`, `dt_edad: int = 0`, `dt_sin: bool = False` y los lee en `from_dict` igual que `dt_calif`.

**2A — lógica pura**

- [ ] **Paso 1: tests que fallan** (`tests/test_editor_ampliado.py`, `db` mínima `{'premier': [{'nombre': 'Club A', 'balance': 1, 'estrellas': 3.0, 'jugadores': [<dict de Jugador(...).to_dict()>]}], '_dts_libres': [...]}`):
  - `test_fijar_atributo_sincroniza_overall_y_potencial`: subir `ataque` a 99 cambia `overall` y deja `potencial >= overall`; `fijar_campo_int(j, 'moral', 150, 0, 100)` → 100.
  - `test_fijar_ovr_todos`: los 5 atributos iguales, `overall` igual.
  - `test_teclear_y_borrar_digitos`: `teclear_entero(0, '7', 1, 99, 2) == 7`; `teclear_entero(7, '5', ...) == 75`; un tercer dígito no entra; `teclear_entero(50, 'x', ...)` no cambia; `borrar_digito(7) == 0`.
  - `test_sanear_jugador`: `ataque=0`, `moral=300`, `contrato_anios=-1` → 1, 100, 0.
  - `test_ciclar_opcion`: avanza, da la vuelta, y un valor fuera de la lista arranca en la primera.
  - `test_nuevo_jugador_club_respeta_el_maximo`: con 39 → agrega y devuelve 39; con 40 (`PLANTILLA_MAXIMA`) → `-1` y no agrega; el id nuevo no choca con ninguno; nombre y apellido salen de `NOMBRES_POR_PAIS['Inglaterra']` (usa `nombres.nombre_unico(pais, random.Random(id), reservar=False)`: el editor no ensucia el registro global).
  - `test_quitar_dt_lo_manda_a_libres`: club con `dt_nombre='Pep'` → libres crece en 1 con `nombre='Pep'`, club queda `dt_sin True` sin `dt_nombre`; segundo `quitar_dt` → `False` y libres no crece; club con DT real de `DT_REALES` (sin `dt_nombre`) conserva ese nombre en el libre; club sin DT definido genera un nombre con `entrenadores.nombre_generado`.
  - `test_asignar_dt_intercambia`: club con DT A y libre B → club con B (`dt_estilo` normalizado, `estilo_dt` igual), A en libres, B ya no está; `asignar_dt(db, club, 99)` → `False`; con `dt_sin` no agrega saliente.
  - `test_prestigio_de`: 49 → BAJO, 50 → MEDIO, 69 → MEDIO, 70 → ALTO.
  - `test_equipo_from_dict_lee_los_dt_nuevos`: `Equipo.from_dict({... 'dt_nacionalidad': 'Italia', 'dt_edad': 55, 'dt_sin': True})` y sin las claves (base vieja) → `''`, `0`, `False`.
  - `test_campos_nuevos_llegan_a_la_carrera`: `Jugador.from_dict(d)` con `salario=1_234_000`, `clausula`, `contrato_anios=3`, `personalidad='lider'`, `nacionalidad='Uruguay'`, `moral=88`, `resistencia=77`, `penales=91` conserva todo y `finanzas.asegurar_contrato(j)` **no** pisa el salario (solo rellena si `salario <= 0`).
  - `test_base_vieja_abre_y_guarda`: db sin `_dts_libres` y jugadores sin campos nuevos → `sanear_jugador`, `quitar_dt`, `nuevo_jugador_club` no lanzan `KeyError`; `json.dumps(db)` funciona.
- [ ] **Paso 2:** `pytest tests/test_editor_ampliado.py -q` → falla.
- [ ] **Paso 3: implementar** las funciones tras `nuevo_jugador_libre` (`edit_screen.py:478-487`) y los 3 campos en `models.py`.
  Fragmentos delicados:

```python
def teclear_entero(actual, char, minimo, maximo, max_digitos):
    base = int(actual or 0)
    if not str(char).isdigit():
        return base
    s = str(base)
    nuevo = str(char) if s == '0' else s + str(char)
    return base if len(nuevo) > max_digitos else min(maximo, int(nuevo))

def fijar_campo_int(j, clave, valor, minimo, maximo):
    v = max(minimo, min(maximo, int(valor)))
    j[clave] = v
    if clave in ATRIBUTOS:                       # el overall del dict y el techo se mantienen coherentes
        j['overall'] = overall_de(j)
        if int(j.get('potencial') or 0) < j['overall']:
            j['potencial'] = j['overall']
    return v
```

  `quitar_dt` usa `dt_efectivo(club)` (ya existe, `edit_screen.py:448`) para no perder el nombre real; `asignar_dt` pone
  `club['estilo_dt'] = club['dt_estilo']` como hace hoy el dropdown (`edit_screen.py:703`).
- [ ] **Paso 4:** `pytest tests/test_editor_ampliado.py -q` en verde.

**2B — interfaz del editor**

Notas de diseño (para no ampliar las cadenas `elif` existentes): los campos nuevos usan `edit_input_activo = 'p2:<clave>'` y un único
manejador al principio del `KEYDOWN` (antes del `if event.key == K_RETURN`, `edit_screen.py:585`):
`if str(campo_activo).startswith('p2:') and jugador_sel is not None and event.key not in (K_RETURN, K_KP_ENTER): _teclear_p2(...); continue`.

- Página 2 del jugador: botón `R_PAG = pygame.Rect(940, 112, 140, 32)` ("PÁG. 2 ▸" / "◂ PÁG. 1", `estado['edit_pag_jugador']`).
  Rejilla de 14 campos en 2 columnas × 7 filas (`x = 530 / 880`, `y = 170 + fila * 40`, caja `Rect(x + 150, y - 6, 130, 30)`),
  etiquetas cortas ("Salario ($/año)", "Años de contrato", "Cláusula ($)"). Los `'sel'` ciclan con un clic (`ciclar_opcion`).
  Al quedar `edit_input_activo = None` con un jugador elegido se llama `sanear_jugador` (cubre el caso de dejar un atributo en 0).
  El campo OVR de la página 1 pasa a `fijar_ovr_todos` (las líneas 611/656 dejan de repetir la asignación de los 5 atributos).
- Crear jugador de club: en JUGADORES (no LIBRES) aparece `R_NUEVO` ("+ NUEVO JUGADOR") junto a la lista; llama a
  `nuevo_jugador_club`; con `-1` muestra `_mensaje("Plantilla llena (40).")`. En LIBRES sigue `nuevo_jugador_libre`.
- DT (sección ENTRENADORES): fila nueva bajo el sueldo (y ≥ 380, el bloque IMPORTAR/EXPORTAR empieza en 472): Nacionalidad
  (clic cicla `opciones_nacionalidad`), Edad (30-80, campo `p2:`-style `dtx:edad`), "Prestigio: ALTO" (solo texto, `prestigio_de`);
  y, solo para clubes: `QUITAR DT`, selector `‹ nombre (calif) ›` sobre `_dts_libres` (`estado['edit_dt_libre_idx']`) y `ASIGNAR`.
  Club con `dt_sin`: el texto "Sin DT: la carrera le genera uno" y el botón ASIGNAR. Lista de libres vacía → ASIGNAR muestra mensaje y no hace nada.
- [ ] **Paso 5: tests de interfaz** (mismo archivo, `edit_screen.render(screen, e)` con `pygame.event.post`):
  - `test_render_de_cada_seccion_y_pagina`: ENTRENADORES (club, libres, club `dt_sin`), JUGADORES (club, libres) en páginas 1 y 2, CLUBES, LIGAS → `render` devuelve `None` y no lanza.
  - `test_pagina_2_y_edicion_de_atributo`: clic en `R_PAG`, clic en la caja de `ataque`, teclear "9", "9" → el jugador queda con `ataque == 99`; Enter y `overall` recalculado.
  - `test_borrar_todo_se_sanea`: en el campo `defensa`, tres Backspace → al salir del campo `defensa == 1`.
  - `test_boton_crear_jugador_club`: clic en `R_NUEVO` en JUGADORES de un club con 39 → +1; con 40 → mensaje y sin cambio.
  - `test_quitar_y_asignar_dt_desde_la_ui`.
  - `test_guardar_y_recargar_conserva_campos_nuevos`: `guardar_base_datos` a un directorio temporal (cambiar `os.chdir` dentro de `tempfile.TemporaryDirectory`, restaurar al final) y releer con `cargar_base_datos_inicial`.
- [ ] **Paso 6: implementar la UI** siguiendo las notas.
- [ ] **Paso 7: verificar.** `pytest tests/test_editor_ampliado.py tests/test_editor_libres_dts.py tests/test_patrocinios_editor.py tests/test_ligas_v370.py tests/test_estilos_v330.py tests/test_teclado_v420.py tests/test_ayuda_v390.py -q` en verde;
  `python -c "import main"` no falla; avisar a `lol` (toqué `models.py`).
- [ ] **Paso 8 (manual, una vez):** abrir el editor, crear un jugador en un club, editar salario/ataque/personalidad, quitar y asignar un DT, guardar, empezar carrera nueva y comprobarlos en PLANTILLA y en el partido.

---

### Tarea 3: tarjetas visuales, pantalla Noticias, tarjeta de OFICINA y feed del hub

**Requiere** el núcleo de `lol` (`alpha_football/noticias.py` listo). Antes de empezar: `pytest tests/test_noticias_nucleo.py -q` en verde.

**Archivos:** crear `alpha_football/ui/noticias_visual.py`, `alpha_football/ui/noticias_screen.py`,
`tests/test_noticias_visual.py`, `tests/test_noticias_screen.py`, `tests/test_noticias_feed.py`;
modificar `ui/league_screen.py`, `main.py:130-163`, `ui/ayuda.py`, `ui/atajos.py`, y los tests viejos
`tests/test_calendario.py:359`, `tests/test_hub_v240.py:172`, `tests/test_ux_v360.py` (solo si el largo de atajos lo exige).

**Consume (de `lol`):** `noticias.activas/para_feed/ultimas/no_leidas/marcar_leida(estado, id)/imagen(noticia)`, `noticias.COLOR[categoria]`,
`noticias.ETIQUETA[tipo]`; campos de la noticia `id, tipo, categoria, titular, cuerpo, temporada, jornada, importancia`, y `accion` opcional.

**Produce:**

```python
# ui/noticias_visual.py
envolver(texto, fuente, ancho, max_lineas) -> list[str]            # recorta con "…" la última línea
tarjeta(noticia, w, h, titular=True, dim=False, fuente='md', max_lineas=5) -> pygame.Surface   # cacheada por (id,w,h,...)
vaciar_cache() -> None

# ui/noticias_screen.py
R_LISTA, R_DETALLE, R_IMAGEN, R_TEXTO, R_ACCION: pygame.Rect
rect_fila(i) -> Rect;  _volver() -> Rect
abrir(estado, noticia_id=None) -> 'noticias_screen'
render(screen, estado) -> Optional[str]

# ui/league_screen.py
INTERVALO_FEED_MS = 5000; FUNDIDO_MS = 180
R_TARJETA_FEED = pygame.Rect(R_TABLA.centerx - 99, R_TABLA.y + 40, 198, 352)
rect_tab_tabla('noticias'|'liga'|'copa') -> Rect                    # liga y copa NO se mueven
feed_actual(estado, ahora) -> tuple[list, int]                      # (noticias del feed, índice vigente)
alternar_noticias(estado, ahora=None) -> None                       # tecla N
```

**3A — tarjetas visuales (`noticias_visual.py`)**

- [ ] **Paso 1: tests que fallan** (`tests/test_noticias_visual.py`; `noticias.imagen` se reemplaza por una función que devuelve un PNG generado con `pygame.image.save` en un directorio temporal, o `None`):
  - `test_sin_imagen_usa_el_color_de_la_categoria`: pixel `(w - 2, 2)` == `noticias.COLOR[categoria]`.
  - `test_con_imagen_recorta_a_cubrir`: imagen horizontal 300×100 de un solo color → la tarjeta de 198×352 es de ese color arriba y mide exacto 198×352.
  - `test_cache_por_id_y_tamano`: `tarjeta(n, 198, 352) is tarjeta(n, 198, 352)`; otro tamaño o `dim=True` → otra superficie; `vaciar_cache()` limpia.
  - `test_titular_largo_se_recorta`: titular de 60 caracteres y una palabra de 40 letras → `envolver` devuelve ≤ `max_lineas`, la última termina en "…" cuando recorta y ninguna línea (salvo la palabra gigante) pasa `ancho`.
  - `test_imagen_rota_no_lanza`: `imagen` devuelve una ruta inexistente → cae al color.
  - `test_degradado_oscurece_el_tercio_inferior`: pixel cerca del borde inferior más oscuro que a 1/3 de la altura con imagen clara.
- [ ] **Paso 2:** ver los tests fallar. **Paso 3: implementar.** `_fondo` (imagen escalada con `smoothscale` a cubrir y recortada centrada, o `fill` con el color), `_degradado` (surface `SRCALPHA` de alto `h/3`, alfa 0 → 215 por líneas), chip con la etiqueta arriba a la izquierda, titular en `get_font(fuente)` sobre el degradado (sombra de 1 px), `dim` = velo negro de 150 de alfa; caché `dict` con tope de 160 (se vacía al llenarse). Todo imagen dentro de `try/except` con `logger.error`.
- [ ] **Paso 4:** `pytest tests/test_noticias_visual.py -q` en verde.

**3B — pantalla Noticias + tarjeta de OFICINA**

- [ ] **Paso 5: tests que fallan** (`tests/test_noticias_screen.py`, `estado_carrera()` y 12 `noticias.publicar(...)` de importancias mezcladas):
  - `test_dibuja_con_lista_y_vacia`: con 12 y con 0 noticias `render` devuelve `None`.
  - `test_flechas_marcan_leida`: ↓ baja `no_leidas` en 1 por noticia visitada; ↑ no pasa del primer índice; RePág/AvPág saltan 10.
  - `test_esc_vuelve_al_hub`: ESC y Backspace → `'league_screen'`; QUIT → `'menu'`; clic en `_volver()` igual.
  - `test_clic_en_fila_selecciona`: clic en `rect_fila(3)` → `estado['noticias_sel'] == 3`.
  - `test_abrir_desde_el_feed_selecciona_por_id`: `abrir(e, id)` y el siguiente `render` deja seleccionada esa noticia, leída.
  - `test_boton_accion`: noticia con `accion={'pantalla': 'buscador_screen', 'texto': 'VER'}` → Enter y clic en `R_ACCION` devuelven `'buscador_screen'`; sin `accion` no hay botón.
  - `test_registro_y_oficina`: con la restauración de `pygame.event.get` tras `import main`: `main.MODULOS_PANTALLA['noticias_screen']` termina en `noticias_screen`; `ayuda.AYUDA['noticias_screen']({})` devuelve ≥ 3 items válidos (dentro de 1280×720, texto ≤ 110); `atajos.ATAJOS['noticias_screen']` contiene "H Ayuda" y mide ≤ 150; `L.TARJETAS['oficina'][1][2] == 'noticias_screen'` y `len(...) == 9`.
  - `test_oficina_de_9_cabe_en_pantalla`: `L._rects_tarjetas(9)`: todos con `right <= 1280`, `bottom <= 696` y sin solaparse; `L._rects_tarjetas(8)` queda igual que hoy (2 columnas).
  - `test_badge_de_no_leidas`: `_render_tarjetas` en OFICINA con 3 sin leer no lanza.
- [ ] **Paso 6: implementar `noticias_screen.py`.** Layout: lista `R_LISTA = Rect(16, 76, 500, 620)` con 10 filas de 56 px (franja de color de la categoría, etiqueta del tipo en `sm`, titular truncado, punto dorado si no leída); detalle `R_DETALLE = Rect(528, 76, 736, 620)`: imagen 9:16 `R_IMAGEN = Rect(544, 92, 330, 586)` con `tarjeta(n, 330, 586, titular=False)`, y a la derecha (`R_TEXTO = Rect(892, 92, 356, 586)`) etiqueta, titular en `lg` (≤ 4 líneas), "Temporada X – Jornada Y" en azul, cuerpo en `sm` (≤ 14 líneas); botón `R_ACCION` (Rect 892, 620, 356, 48) solo con `accion`. Estado: `noticias_sel`, `noticias_scroll`, `noticias_sel_id`. Seleccionar marca leída con `noticias.marcar_leida`. Mismo esquema de `try/except` que `notificaciones_screen.py:66-132` (error → `'league_screen'`).
- [ ] **Paso 7: registro.**
  - `main.py` `MODULOS_PANTALLA`: `'noticias_screen': 'alpha_football.ui.noticias_screen',      # v0.4.23.0`.
  - `ui/ayuda.py`: `_TEXTO_TARJETA['noticias_screen']`, función `_ayuda_noticias` (3 items: lista, detalle, volver) y `AYUDA['noticias_screen']`; actualizar `_TEXTO_PESTANA['oficina']` (ayuda.py:382).
  - `ui/atajos.py`: `'noticias_screen': "↑ ↓ Noticia · RePág AvPág Saltar · Enter Ir · O Opciones · H Ayuda · ESC Volver"`.
  - `league_screen.TARJETAS['oficina'].insert(1, ("NOTICIAS", "Titulares de tu liga y del mundo", 'noticias_screen'))`.
  - `_rects_tarjetas`: con `n > 8` → `w, cols = 392, 3` (3 columnas × 3 filas de 120; con 8 o menos queda igual).
  - `_render_tarjetas`: badge de `noticias.no_leidas(estado)` para `'noticias_screen'`; el subtítulo se ajusta al ancho (helper `_ajustar_texto(txt, fuente, ancho)` con "…"), porque en 392 px los subtítulos largos ya no caben.
  - Tests viejos: `test_calendario.py:359` → `== 9` (y su comentario), `test_hub_v240.py:172` → insertar `'noticias_screen'` en 2ª posición. Avisar a `lol` de ambos.
- [ ] **Paso 8:** `pytest tests/test_noticias_screen.py tests/test_calendario.py tests/test_hub_v240.py tests/test_ayuda_v390.py tests/test_ux_v360.py tests/test_notificaciones.py tests/test_vestuario_v310.py tests/test_directiva_v280.py tests/test_teclado_v420.py -q` en verde.

**3C — feed del hub**

- [ ] **Paso 9: tests que fallan** (`tests/test_noticias_feed.py`):
  - `test_feed_rota_cada_5_s`: 3 noticias de importancia 4; `feed_actual(e, 0)[1] == 0`, a 5000 → 1, 10000 → 2, 15000 → 0; el orden es el de `para_feed`.
  - `test_feed_solo_importancia_3_o_mas`: una de importancia 2 no aparece.
  - `test_n_alterna_y_recuerda_la_pestana`: `alternar_noticias` desde `liga` → `noticias` (`hub_tabla_prev == 'liga'`), otra vez → `liga`; desde `copa` vuelve a `copa`.
  - `test_pestanas_liga_y_copa_no_se_mueven`: `rect_tab_tabla('liga')` y `('copa')` iguales a los de antes (x = `R_TABLA.right - 212` y `-108`), `noticias` queda a su izquierda sin solaparlas; `test_competiciones_v380.py` sigue verde.
  - `test_tarjeta_cabe_bajo_las_pestanas`: `R_TARJETA_FEED` dentro de `R_TABLA` y `R_TARJETA_FEED.top >= rect_tab_tabla('liga').bottom + 4`.
  - `test_hub_dibuja_con_feed_con_y_sin_noticias`: `L.render(screen, e)` con `hub_tabla_tab='noticias'`, con 0 noticias (mensaje) y con 5 (sin imágenes → color) devuelve `None`.
  - `test_clic_en_la_tarjeta_abre_noticias`: clic en `R_TARJETA_FEED.center` → `'noticias_screen'` y `estado['noticias_sel_id']` = id de la noticia vigente.
  - `test_tecla_n_en_el_hub`: KEYDOWN `K_n` con `hub_tab='inicio'` cambia `hub_tabla_tab`; en otra pestaña del hub no hace nada.
  - `test_atajos_del_hub_caben`: `len(atajos.ATAJOS['league_screen']) <= 150` y contiene "N Noticias".
- [ ] **Paso 10: implementar en `league_screen.py`.**
  - `rect_tab_tabla` (línea 943): `'noticias'` → `Rect(R_TABLA.right - 324, R_TABLA.y + 8, 104, 28)`; `liga`/`copa` sin cambios.
  - `_dibujar_tabs_tabla` (948): recorrer `(('noticias', "NOTICIAS"), ('liga', "LIGA"), ('copa', "COPA"))`.
  - `_render_inicio` (987): `tabla_tab = estado.get('hub_tabla_tab') if in ('liga', 'copa', 'noticias') else 'liga'`; si es `'noticias'`, `_render_feed(...)` y `raise _TablaDibujada()` (mismo patrón que la copa, línea 991-993).
  - `_render_feed`: título "NOTICIAS", tarjeta central en `R_TARJETA_FEED` con borde dorado, la anterior y la siguiente `dim=True` desplazadas ±150 px con `screen.set_clip` al panel (se ven 150 px de cada una), mensaje "Sin noticias destacadas. Se publican con cada jornada." si no hay; fundido de entrada = velo del color del panel sobre `R_TABLA` con alfa `255 - 255 * (ahora - feed_fade_ms) / FUNDIDO_MS` mientras dure (sin recomponer nada más). Sin trabajo por cuadro: las superficies salen de `noticias_visual.tarjeta` (caché).
  - Clics (`_render_inicio`, bloque 1199-1203): pestaña NOTICIAS → `_fijar_tabla_tab(estado, 'noticias')`; LIGA/COPA igual que hoy (y fijan `hub_tabla_prev`); clic en `R_TARJETA_FEED` con la pestaña activa → `noticias_screen.abrir(estado, <id vigente>)`.
  - Teclado (`render`, bucle 1442): `if ev.key == pygame.K_n and tab == 'inicio': alternar_noticias(estado); continue`.
  - `atajos.ATAJOS['league_screen']`: "C Cerrar mercado" → "C Cerrar" y añadir "N Noticias" (145 caracteres). `ayuda._ayuda_hub` (410-412): incluir la pestaña NOTICIAS y la tecla N.
- [ ] **Paso 11: verificar.** `pytest tests/test_noticias_feed.py tests/test_competiciones_v380.py tests/test_hub_v240.py tests/test_ux_v360.py tests/test_ayuda_v390.py tests/test_teclado_v420.py tests/test_ajustes_v0411.py -q` en verde.
- [ ] **Paso 12 (manual, una vez):** `python main.py`, carrera nueva, entrar al hub, pulsar N varias veces, esperar 10 s y ver que rota; abrir OFICINA > NOTICIAS; comprobar con y sin imágenes en `alpha_football/assets/noticias/`.

---

### Tarea 4: generadores de noticias (`noticias_gen.py`)

**Requiere** `noticias.publicar` y el enganche de `cierre_jornada` de `lol` (Tarea 2 de su plan, ya llama a `noticias_gen.generar_jornada`).

**Archivos:** crear `alpha_football/noticias_gen.py`, `tests/test_noticias_gen.py`.

**Produce:**

```python
generar_jornada(estado, rng=None) -> int      # nº de noticias publicadas; cada generador en su try
generar_cierre_temporada(estado, temporada, campeon_liga, campeones_copas, movimientos) -> int
# memoria de los generadores (JSON simple) en estado['datos_carrera']['noticias_gen'] y ['records']
```

Reglas de implementación (todas con `clave=` en `extra` para no publicar dos veces el mismo hecho; `_ya(estado, clave)` busca en `noticias.lista(estado)`):

| Generador | Fuente | Regla |
|---|---|---|
| `_resultados` (tu liga) | `liga.calendario` de la **última jornada jugada** (`max(p.jornada for p in cal if p.jugado)`; en el enganche `jornada_actual` ya avanzó) | goleada: diferencia ≥ 4 (imp. 3; ≥ 5 → 4) · sorpresa: gana el de menor `market.nivel_club` por ≥ 8 (imp. 3; ≥ 12 → 4) · clásico `data.clasicos.es_clasico` (imp. 3-4). Máx. 2 por jornada, las de mayor puntaje |
| `_resultados` (otras ligas) | `league_screen._ligas_de_fondo(estado)` | solo 1 por jornada en total: la de mayor diferencia (≥ 5) o clásico con diferencia ≥ 3 (imp. 4) |
| `_lesiones` | jugadores de tu liga con `lesion_dias >= 21` y `overall >= 80` | imp. 4 si `overall >= 85` o `lesion_dias >= 60`, si no 3; no repite al mismo jugador en 8 jornadas (memoria `lesiones{jid: jornada_abs}`) |
| `_promesas` | todos los clubes de todas las ligas | cada 6 jornadas: `edad <= 21`, `potencial >= 78`, `potencial - overall >= 12`; el de mayor potencial que no se haya destacado (memoria `promesas`), imp. 3 |
| `_candidatos_balon` | `premios.puntaje_jugador(j, peso, False, False)` con `PESO_LIGA_1A` | en `jornada == num_jornadas // 2` y una vez por temporada; top 3, imp. 4, tipo `premio` |
| `_records` | `datos_carrera['records'] = {'goles': {'valor': 25, 'nombre': ''}, 'asistencias': {'valor': 15, 'nombre': ''}}` (valores iniciales) | el máximo de la temporada a ≤ 3 del récord y sin superarlo → noticia imp. 4 (una vez por jugador y temporada); si lo supera, actualiza el récord y publica "bate el récord" |
| `_polemico` | tu plantel: `personalidad == 'polemico'` y `moral < 50` | probabilidad 0,12 por jornada (`rng`); noticia `vestuario` imp. 3 y `prensa.mover_moral(plantel, -1)` |

`generar_cierre_temporada` publica con `temporada=` y `jornada=num_jornadas` explícitos: campeón de tu liga (tipo `campeon`, imp. 5),
campeones de copa (`campeones_copas`, imp. 5), ascensos y descensos de tu país con `movimientos` (`{'tipo','ascendidos','descendidos'}`; tipo `descenso`,
categoría `'ascenso'` para los ascensos, imp. 5) y una noticia agregada con los demás países (imp. 4), y el equipo del año de tu liga
(1 POR, 4 DEF, 3 MED, 3 DEL por `promedio_nota` con al menos la mitad de los partidos; tipo `premio`, imp. 4).
Titulares ≤ 60 caracteres (los recorta `publicar`); textos con nombres reales del estado, nunca inventados.

- [ ] **Paso 1: tests que fallan** (`tests/test_noticias_gen.py`; `estado_carrera()`, `inicializar_calendario_liga(liga)` y marcar a mano `p.jugado/goles_*`):
  - `test_goleada_publica_y_no_duplica`: 6-0 en la jornada 1 → 1 noticia `resultado` imp. ≥ 3 con `clave`; segunda llamada → sigue 1.
  - `test_sorpresa_y_clasico`: forzar niveles y `mi.rival = rival.nombre`; imp. y tipo correctos; máx. 2 por jornada.
  - `test_otras_ligas_solo_la_mas_destacada`: dos goleadas en ligas de fondo → 1 sola noticia.
  - `test_lesion_grave_y_sin_repetir`: `lesion_dias = 30`, `overall >= 80` → 1 noticia; 3 jornadas después no repite; a las 9 sí.
  - `test_promesas_cada_6_jornadas`: jornada 6 publica, 7 no, 12 publica otra distinta.
  - `test_candidatos_al_balon_una_vez`: a mitad de temporada; segunda llamada no duplica.
  - `test_records_cerca_y_superado`: récord 25, goleador con 23 → noticia; con 26 → `datos_carrera['records']['goles']['valor'] == 26` y noticia de récord.
  - `test_polemico_filtra_y_baja_moral`: `rng` que fuerza el sorteo → noticia `vestuario` y `moral` −1 en todo el plantel.
  - `test_cierre_usa_temporada_explicita`: llamar con `estado['temporada']=2` y `temporada=1` → las noticias salen con `temporada == 1`.
  - `test_cierre_ascensos_user_y_resto`: `movimientos` con tu país y otro → una de tu país (imp. 5, categoría `ascenso` para ascendidos) y una agregada (imp. 4).
  - `test_un_generador_que_falla_no_frena_a_los_demas`: monkeypatch de `_lesiones` lanzando → las demás noticias salen.
  - `test_guardado_viejo`: `datos_carrera = {}` → `generar_jornada` no lanza y crea `noticias_gen`/`records`; `json.dumps(estado['datos_carrera'])` funciona (sin objetos del juego).
  - `test_sin_liga_o_sin_calendario_no_lanza` (foco 3).
- [ ] **Paso 2:** `pytest tests/test_noticias_gen.py -q` → falla. **Paso 3: implementar** (helpers privados `_jornada_abs`, `_ligas`, `_texto_*` puros).
- [ ] **Paso 4:** `pytest tests/test_noticias_gen.py tests/test_noticias_nucleo.py -q` en verde. **Paso 5:** avisar a `lol` "generadores listos" (no se toca `match_screen.py`).

---

### Tarea 5: carga de temporada con titulares

**Archivos:** modificar `ui/pantalla_carga.py`, `ui/resumen_temporada_screen.py`; crear `tests/test_carga_noticias.py`
(`tests/test_pantalla_carga.py` no se toca: su `_Espia` fija la firma `mostrar(titulo, paso, avance)`, así que **esa firma no cambia**).

**Produce (`pantalla_carga.py`):**

```python
MINIMO_TEMPORADA = 0.0 if SDL dummy else 3.0
fijar_titulares(noticias: list[dict] | None) -> None      # las ~8-10 noticias que desfilan; None/[] las quita
cerrar(minimo: float | None = None) -> None               # None = MINIMO (0.4); mientras espera redibuja ~30 fps con los titulares
```

- Diseño: los titulares se dibujan a la derecha (`Rect(980, 160, 225, 400)`, no pisan el título ni la barra, que quedan en 340-940); una noticia cada
  3,5 s con fundido de 0,4 s al entrar y al salir (`set_alpha` sobre la superficie cacheada de `noticias_visual.tarjeta(n, 225, 400)`, alfa vuelto a `None`),
  encabezado "ÚLTIMAS NOTICIAS". Índice por tiempo transcurrido (`time.monotonic() - _inicio_titulares`), sin estado por cuadro más allá de eso.
  Sin titulares el dibujo es idéntico al de hoy. Los pasos largos bloquean sin redibujar: el desfile se anima de verdad en la espera de `cerrar(minimo=...)`, que memoriza el último `(titulo, paso, avance)` y lo redibuja cada ~33 ms con `pygame.event.pump()`.
- `resumen_temporada_screen.avanzar_nueva_temporada`: textos de etapa (los porcentajes y el orden no cambian): 0.05 "Cerrando temporada…" · 0.25 "Actualizando clasificaciones y descensos…" ·
  0.5 "Generando agentes libres…" (retiros y regens) · 0.65 "Procesando mercado de pases…" · 0.8 "Contratos y finanzas…" · 0.9 "Preparando nueva temporada…" · 0.94 y 0.97 y 1.0 como hoy.
  Al empezar: `_pc.fijar_titulares(noticias.ultimas(estado, 10))`; tras publicar el cierre (abajo) se vuelve a fijar. En el `finally`: `_pc.cerrar(minimo=_pc.MINIMO_TEMPORADA)` y `_pc.fijar_titulares(None)`.
- Publicación del cierre de **tu** temporada (justo después de `estado['promo_releg_data']['premio_ascenso_user'] = ...`, línea 324, que es cuando existen `campeon_nombre` (142), `campeones_copas` (113) y `movimientos` (317)):
  `noticias_gen.generar_cierre_temporada(estado, temp_anterior, campeon_nombre, campeones_copas, movimientos)` en su propio `try`; el equipo del año se calcula antes del reset de estadísticas. Después de armar `historial` (línea ~204): `logros.revisar(estado)` (Tarea 7; mientras no exista, el `import` va dentro del `try` y falla en silencio).

- [ ] **Paso 1: tests que fallan** (`tests/test_carga_noticias.py`):
  - `test_sin_titulares_dibuja_como_antes`: `mostrar(...)` sin titulares deja intactos título y barra (mismos píxeles de `test_pantalla_carga.test_dibuja_titulo_y_barra`).
  - `test_con_titulares_dibuja_la_tarjeta`: tras `fijar_titulares([n1, n2])` hay píxeles distintos del fondo en `Rect(980, 160, 225, 400)`; con `fijar_titulares(None)` vuelve el fondo.
  - `test_el_indice_rota_por_tiempo`: función pura `titular_vigente(n, transcurrido)` → 0 a 0 s, 1 a 3,6 s, 0 a 7,2 s (con 2 noticias); alfa 0 en el borde y 255 en el centro del tramo.
  - `test_cerrar_con_minimo_espera_y_redibuja`: con `time.monotonic` y `time.sleep` falsos, `cerrar(minimo=1.0)` redibuja varias veces y termina; `cerrar()` sin argumento conserva el comportamiento; en SDL dummy `MINIMO_TEMPORADA == 0.0`.
  - `test_temporada_usa_los_textos_nuevos`: con `_Espia` (copiar de `test_pantalla_carga.py`) sobre `avanzar_nueva_temporada(estado_carrera ya jugada)` los `paso` contienen, en este orden, "Cerrando temporada", "Actualizando clasificaciones y descensos", "Generando agentes libres", "Procesando mercado de pases", "Preparando nueva temporada", y `avance` sube monótono hasta 1.0.
  - `test_cierre_de_temporada_publica_noticias_con_la_temporada_cerrada`: tras `avanzar_nueva_temporada`, hay noticias `campeon` con `temporada == temporada_anterior`.
  - `test_carga_sin_noticias`: carrera nueva sin ninguna noticia → la carga completa no lanza (foco).
- [ ] **Paso 2:** ver fallar. **Paso 3: implementar** `pantalla_carga.py` y los `Edit` puntuales en `resumen_temporada_screen.py`.
- [ ] **Paso 4: verificar.** `pytest tests/test_carga_noticias.py tests/test_pantalla_carga.py tests/test_temporada.py tests/test_temporadas_continente.py tests/test_premios_v0417.py -q` en verde.
- [ ] **Paso 5 (manual, una vez):** terminar una temporada en el juego y ver los titulares desfilar con la carga.

---

### Tarea 6: conferencias de prensa (overlay) y `factor_tarjetas`

**Requiere** `noticias.publicar`.

**Archivos:** crear `alpha_football/prensa.py`, `alpha_football/ui/prensa_overlay.py`, `tests/test_prensa.py`;
modificar `ui/prepartido_screen.py` (`render` 455 y `_render` 491-497, `_simular_instantaneo` 101), `ui/postpartido.py` (`armar_datos` 130 y `render` 361),
`ui/match_screen.py:1191` (una línea), `partido_ctx.py:43-74`, `engine.py` (`simular_partido` 899-938 y `_incidencias_minuto` 1056-1060).

**Produce:**

```python
# prensa.py  (lógica pura sobre datos_carrera['prensa'] = {'hechas': {clave: ['pre','post']}, 'tension': 0|FACTOR, 'moral_rival': {...}})
TONOS = ('motivador', 'provocador', 'humilde', 'agresivo'); FACTOR_TENSION = 1.6
motivo_partido(estado, local, visitante, modo) -> Optional[str]    # 'copa_final'|'copa_semi'|'clasico'|'titulo'|'descenso'|'lider'|None
evaluar_pre(estado, local, visitante, modo) -> Optional[dict]      # arma y guarda estado['prensa_overlay']
evaluar_post(estado, local, visitante, gl, gv, modo, pos_antes=None) -> Optional[dict]
responder(estado, conferencia, tono) -> dict                       # aplica efectos, publica la noticia, devuelve {'texto','efectos'}
saltar(estado) -> None                                             # cierra el overlay sin efectos y marca la fase como hecha
mover_moral(jugadores, delta) -> None                              # clamp 0-100; si delta < 0 suma a causas_moral[-1]['equipo']
factor_tarjetas(estado) -> float                                   # 1.0 sin tensión o en amistoso; FACTOR_TENSION si la hay
consumir_tension(estado) -> None                                   # al terminar el partido del user: borra la tensión y devuelve la moral al rival
# ui/prensa_overlay.py
activo(estado) -> bool
manejar(estado, teclas, click_pos) -> None                         # modal: quien llama descarta sus teclas y su clic
dibujar(screen, estado, mouse_pos) -> None
rect_respuesta(i) -> Rect;  R_SALTAR: Rect;  R_PANEL: Rect
# partido_ctx.EstadoPartido.factor_tarjetas: float = 1.0           # se copia en copia()
# engine.py
_remapear_sorteo_tarjetas(r: float, k: float) -> float            # k=1 → identidad; ensancha solo [0, _C_ROJA)
simular_partido(..., factor_tarjetas: float = 1.0, ...)           # se asigna al ctx que crea
```

Reglas:

- **Cuándo se ofrece** (`motivo_partido`, por prioridad): final o semifinal de copa (`partido_copa_bracket_fase` con `\bfinal\b` / `semi`) · clásico
  (`data.clasicos.es_clasico`) · título (liga, tú líder o a ≤ 3 puntos y quedan ≤ 6 jornadas) · descenso (1ª división, últimos 2 puestos, jornada ≥ 4) ·
  líder (puesto 1, jornada ≥ 4). Nunca en `modo == 'amistoso'`. Clave del partido: `f"{temporada}:{modo}:{local.id}:{visitante.id}:{jornada_o_fase}"`;
  `hechas[clave]` evita repetir la misma fase; pre y post son independientes.
- **Preguntas:** banco `BANCO[motivo]['pre']` (lista) y `BANCO[motivo]['post'][resultado]` con `resultado ∈ {'gana','empata','pierde'}`; cada pregunta
  `{'texto': str, 'respuestas': {tono: str}}` con los 4 tonos. Mínimo 2 preguntas por motivo y fase, textos ≤ 100 caracteres. Elección determinista por
  `random.Random(clave)`. En la fase `pre`, además, el DT rival declara (`mover_moral(tu plantel, -1)`, noticia `declaracion` imp. 2) y su frase se muestra en el overlay.
- **Efectos de `responder`:** motivador → `mover_moral(mi plantel, +2)`; humilde → `+1`; provocador → `mover_moral(plantel del siguiente rival, -2)` y se
  anota `moral_rival = {'id', 'delta': -2}` para devolverlo en `consumir_tension` (los clubes de la IA no recalculan moral; sin esto el castigo sería permanente);
  en `pre` el siguiente rival es el rival del partido, en `post` el rival de tu próximo partido sin jugar en `liga.calendario`; agresivo → `prensa['tension'] = FACTOR_TENSION`.
  Toda respuesta publica `noticias.publicar(estado, 'declaracion', titular, cuerpo, importancia=…, categoria='prensa')`: provocador 4, motivador y agresivo 3, humilde 2.
- **Dónde:** `postpartido.armar_datos` (llamado por el partido en vivo, `match_screen.py:1087`, y por la simulación instantánea, `prepartido_screen.py:159/214/227`)
  primero `prensa.consumir_tension(estado)` si `modo != 'amistoso'`, y después `prensa.evaluar_post(...)`. `prepartido_screen.render` llama `evaluar_pre` antes de `_render`
  y dibuja el overlay después; `postpartido.render` consume teclas/clic si el overlay está activo y lo dibuja al final.
- **Tarjetas:** `partido_ctx.EstadoPartido.factor_tarjetas` (se copia en `copia()`); en `engine._incidencias_minuto`, tras `r = random.random()`:

```python
k = getattr(ctx, 'factor_tarjetas', 1.0)
if k != 1.0:      # v0.4.23.0: tono agresivo en la prensa: ensancha solo el tramo de tarjetas
    r = _remapear_sorteo_tarjetas(r, k)

def _remapear_sorteo_tarjetas(r, k):
    return r / k if r < k * _C_ROJA else r - (k - 1.0) * _C_ROJA
```

  Asignación explícita (sin estado global ni sincronización por cuadro): `match_screen.py` justo tras `estado['sim_ctx'] = nuevo_estado(...)` (línea 1191-1192):
  `estado['sim_ctx'].factor_tarjetas = prensa.factor_tarjetas(estado)` (en `try`); `prepartido_screen._simular_instantaneo` (línea 101) pasa
  `factor_tarjetas=prensa.factor_tarjetas(estado)` a `simular_partido`, que lo copia al `ctx` que crea (engine.py:938). Los partidos IA-IA no lo pasan → 1.0.

- [ ] **Paso 1: tests que fallan** (`tests/test_prensa.py`):
  - `test_motivos_y_prioridad`: clásico, final de copa (gana a clásico), título, descenso, líder, nada; amistoso → `None`.
  - `test_una_vez_por_fase_y_partido`: tras `responder` o `saltar` en `pre`, `evaluar_pre` del mismo partido → `None`, `evaluar_post` sí; otro partido sí.
  - `test_banco_completo`: cada motivo × fase (× resultado en post) tiene ≥ 2 preguntas con los 4 tonos, textos no vacíos ≤ 100.
  - `test_motivador_y_humilde`: moral +2 / +1 (con tope 100); la noticia sale `declaracion`/`prensa` con la importancia indicada.
  - `test_provocador_baja_moral_rival_y_se_devuelve`: −2 al rival; `consumir_tension` lo devuelve; si el rival quedó sin jugadores no lanza.
  - `test_agresivo_pone_tension_y_se_consume`: `factor_tarjetas == 1.6` hasta `consumir_tension`; en amistoso siempre 1.0.
  - `test_saltar_no_cambia_nada`: moral, tensión y noticias intactas; `prensa_overlay` borrado.
  - `test_rival_dt_declara_en_pre`: baja −1 al plantel propio y publica la declaración.
  - `test_mover_moral_anota_causa`: con `delta < 0` y `causas_moral` no vacía se suma a `['equipo']` de la última; `moral` queda en 0-100.
  - `test_datos_carrera_json_y_save_viejo`: `datos_carrera = {}` → ninguna función lanza; `json.dumps(datos_carrera)` funciona.
  - `test_remapeo_del_sorteo`: con `k=1.0` identidad en una rejilla de 10 000 valores; con `k=1.6` la masa que cae en `[0, _C_ROJA)` es `1.6 × _C_ROJA` y la masa del tramo de lesiones/penales/faltas (`[_C_ROJA, _C_FALTA)`) no cambia (tolerancia 1e-3); el remapeo es monótono.
  - `test_ctx_copia_el_factor`: `nuevo_estado(...).copia().factor_tarjetas` conserva el valor; `simular_partido(local, visit, factor_tarjetas=1.6)` devuelve `res.ctx.factor_tarjetas == 1.6`.
  - `test_overlay_dibuja_y_consume`: `manejar` con teclas 1-4 responde, con Esc/S salta, clic en `R_SALTAR` salta, clic en `rect_respuesta(2)` responde; `dibujar` no lanza con y sin respuesta ya dada (muestra la consecuencia y CONTINUAR).
  - `test_prepartido_ofrece_el_overlay_en_un_clasico`: `mi.rival = rival.nombre`, `partido_actual` de la jornada, `prepartido_screen.render` → `estado['prensa_overlay']['fase'] == 'pre'`; con el overlay activo ENTER/1-4 no activa ninguna opción del prepartido (el partido no arranca).
  - `test_postpartido_ofrece_el_overlay`: `armar_datos(estado, 'liga', ...)` en un clásico → overlay `post`; en un amistoso → ninguno; `PP.render(..., teclas=[K_RETURN])` con el overlay activo no devuelve `'continuar'`.
- [ ] **Paso 2:** ver fallar. **Paso 3:** implementar `prensa.py` (banco incluido) y `ui/prensa_overlay.py`
  (velo `SRCALPHA` de 170, panel `R_PANEL = Rect(190, 120, 900, 480)`, encabezado "CONFERENCIA DE PRENSA — PREVIA / POSTPARTIDO", motivo, frase del DT rival en pre, pregunta en `md`,
  4 respuestas en cajas `rect_respuesta(i)` con el tono en dorado y el texto en `sm` envuelto con `noticias_visual.envolver`, botón SALTAR abajo a la derecha; tras responder, la consecuencia y CONTINUAR).
- [ ] **Paso 4:** avisar a `lol` y editar `partido_ctx.py`, `engine.py`, `match_screen.py:1191`, `prepartido_screen.py`, `postpartido.py`; avisar de nuevo al terminar.
- [ ] **Paso 5: verificar.** `pytest tests/test_prensa.py tests/test_simulacion.py tests/test_mentalidad_v250.py tests/test_bajas_rival_cambios.py tests/test_lesiones_dias_v0419.py tests/test_presentacion_v410.py tests/test_ajustes_v04141.py tests/test_vestuario_v310.py tests/test_dias.py -q` en verde.
- [ ] **Paso 6 (manual, una vez):** jugar un clásico: ver el overlay antes (con la declaración del DT rival) y después, responder agresivo y comprobar más tarjetas en el siguiente partido.

---

### Tarea 7: logros del DT

**Archivos:** crear `alpha_football/logros.py`, `tests/test_logros.py`; modificar `ui/career_screen.py` (eventos 256-270, cabecera 273-277, y el overlay), `ui/ayuda.py:443-452` (`_ayuda_carrera`), `ui/atajos.py:30`, `ui/postpartido.py` (`armar_datos`, una llamada).

**Produce:**

```python
# logros.py  — estado en datos_carrera['logros'] = {'obtenidos': {id: {'temporada', 'jornada'}}, 'contadores': {'pj', 'racha', 'clasicos_seguidos'}}
LOGROS: list[tuple[str, str, str]]    # (id, título, descripción)
logros(estado) -> dict                                            # setdefault de la estructura
registrar_partido(estado, local, visitante, gl, gv, modo, pos_antes=None) -> list[str]   # ids desbloqueados
revisar(estado) -> list[str]                                      # título de liga, final continental, fichaje de lujo
desbloquear(estado, logro_id, temporada=None, jornada=None) -> Optional[dict]   # publica la noticia 'logro' imp. 5; None si ya estaba
para_overlay(estado) -> list[dict]    # [{'id','titulo','descripcion','obtenido','temporada','jornada'}], obtenidos primero (más reciente arriba)
# ui/career_screen.py
R_LOGROS = pygame.Rect(SCREEN_W - 440, 22, 200, 48);  R_PANEL_LOGROS = pygame.Rect(240, 100, 800, 540)
filas_logros(estado) -> list;  rect_fila_logro(i) -> Rect
```

Los 9 logros (id · condición):

| id | Condición |
|---|---|
| `titulo_liga` | alguna temporada del `estado['historial']` con `pos == 1` |
| `final_continental` | `historial[*]['libertadores']` o `estado['copa_mejor_fase_temp']` con `re.search(r'\bfinal\b|campe', texto_normalizado)` (`semifinal` no cuenta) |
| `pj_50`, `pj_100`, `pj_200` | contador `pj` (liga + copa, no amistosos), +1 por llamada a `registrar_partido` |
| `racha_8` | `racha` (se reinicia con empate o derrota) llega a 8 |
| `salvado` | última jornada de liga de 1ª división (`max(p.jornada jugados) == num_jornadas`), `pos_antes >= n - 1` y posición final `<= n - 2` |
| `clasicos_3` | `clasicos_seguidos` llega a 3 (solo cuentan clásicos de `es_clasico`; un clásico no ganado lo reinicia) |
| `fichaje_84` | `revisar`: algún jugador de `mi_equipo.jugadores` con `overall >= 84`, `ventana_traspaso` no vacía y `canterano == ''` |

- Llamadores: `postpartido.armar_datos` (para `modo in ('liga','copa')`, en su propio `try`, calcula `pos_despues` con `posicion_liga`), `noticias_gen.generar_jornada` (`logros.revisar` al final, en su `try`) y
  `avanzar_nueva_temporada` (después de armar `historial`; Tarea 5). Cada desbloqueo publica `noticias.publicar(estado, 'logro', f"Logro: {titulo}", descripcion, importancia=5, accion={'pantalla': 'career_screen', 'texto': 'VER LOGROS'})`.
- Overlay en `career_screen`: botón LOGROS (tecla L) abre `estado['career_logros'] = True` con panel `R_PANEL_LOGROS`, filas de 52 px (8 visibles, rueda o ↑ ↓ para desplazar, `career_logros_scroll`);
  obtenidos con ✓ dorado y "T3 · J12", pendientes atenuados con su descripción. Mientras está abierto consume todos los eventos: ESC/Backspace o clic fuera lo cierra **sin** salir de la pantalla.

- [ ] **Paso 1: tests que fallan** (`tests/test_logros.py`):
  - `test_estructura_y_json`: `logros({})`/`datos_carrera={}` crea la estructura; `json.dumps` funciona; guardado viejo sin la clave no lanza (foco 3).
  - `test_pj_50_100_200`: 50 llamadas desbloquean `pj_50` justo en la 50ª, no antes ni dos veces; amistoso no cuenta.
  - `test_racha_8`: 7 victorias, un empate, 8 victorias → solo el segundo tramo desbloquea.
  - `test_clasicos_3`: gana 2, empata uno, gana 3 → desbloquea solo con 3 seguidos; un partido no clásico no rompe la cuenta.
  - `test_salvado_en_la_ultima`: pos_antes ≥ n−1, final ≤ n−2 en la última jornada → sí; en otra jornada o en 2ª división → no.
  - `test_titulo_y_final`: historial con `pos == 1`; `libertadores='Subcampeón'` y `'Final'` sí, `'Semifinal'` no; `copa_mejor_fase_temp='Final'` en curso sí.
  - `test_fichaje_84`: con `ventana_traspaso` y `overall 84` sí; canterano o sin ventana no.
  - `test_desbloquear_publica_noticia_y_una_sola_vez`: noticia tipo `logro`, imp. 5, con `accion`; segunda llamada → `None`, sin noticia nueva; `temporada`/`jornada` actuales.
  - `test_para_overlay_orden`: 9 filas, obtenidos primero, los demás con descripción.
  - `test_career_overlay`: `career_screen.render` con `career_logros=True` → `None`; ESC lo cierra sin devolver `'volver'`; con el overlay cerrado ESC sí vuelve; clic en `R_LOGROS` y tecla L lo abren; rueda desplaza sin pasar de los límites; con 0 logros obtenidos dibuja.
  - `test_registro_ayuda_y_atajos`: `ayuda.AYUDA['career_screen']({})` sigue válida (≥ 3 items, texto ≤ 110) e incluye el botón; `atajos.ATAJOS['career_screen']` contiene "L Logros" y "H Ayuda".
- [ ] **Paso 2:** ver fallar. **Paso 3:** implementar `logros.py` y los `Edit` puntuales en `career_screen.py`, `ayuda.py`, `atajos.py`, `postpartido.armar_datos`.
- [ ] **Paso 4: verificar.** `pytest tests/test_logros.py tests/test_hub_v240.py tests/test_ayuda_v390.py tests/test_ux_v360.py tests/test_correo_v470.py tests/test_premios_v0417.py -q` en verde.
- [ ] **Paso 5 (manual, una vez):** jugar unas jornadas, abrir OFICINA > HISTORIAL DE CARRERA > LOGROS y ver el panel; comprobar la noticia al desbloquear.

---

## Autorevisión (hecha al escribir el plan)

- **Cobertura del spec:** §6 feed, pantalla, carga → Tareas 3 y 5 · §7 generadores → 4 (más el cierre de temporada) · §8 prensa/overlay/tarjetas → 6 · §9 logros → 7 · §10 editor → 2 · §11 nombres → 1 · §3 imágenes y `accion` → 3A/3B.
- **Cambios acordados con `lol`:** tarjeta 198×352, pestaña NOTICIAS a la izquierda, N con `hub_tabla_prev`, atajos recortados, OFICINA a 3 columnas, `valor` fuera del editor, mínimo de 3 s como parámetro de `cerrar()`, moral por delta directo, asignación explícita de `factor_tarjetas`, prensa como overlay, `publicar(temporada=, jornada=, accion=)`.
- **Detalles que esta lectura del código añade al spec:** (1) `test_pantalla_carga.py` fija la firma de `mostrar`, por eso los titulares entran con `fijar_titulares`; (2) la moral de los clubes IA no se recalcula, por eso el castigo del Provocador se devuelve en `consumir_tension`; (3) en el enganche de cierre `liga.jornada_actual` ya avanzó, por eso los generadores leen la última jornada jugada; (4) `armar_datos` es el único punto común del partido en vivo y de la simulación instantánea, por eso la prensa post y los logros se enganchan ahí.
- **Pendiente de confirmar con `lol` al ejecutar:** que `noticias.imagen` y `noticias.COLOR` acepten una categoría desconocida (la tarjeta cae a un color por defecto si no); y el nombre exacto de las claves `ETIQUETA`/`COLOR` cuando publique su contrato.
