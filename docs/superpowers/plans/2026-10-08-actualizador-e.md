# Auto-actualización (sub-proyecto E, v0.4.15.0) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Al abrir el juego se compara `VERSION` con el de GitHub y, si hay una versión nueva, se instala sola (ZIP o `git pull --ff-only`) o se avisa en el menú, sin tocar nunca los datos del jugador.

**Architecture:** Un módulo sin UI, `alpha_football/actualizador.py`, con funciones puras y dos únicas puertas al exterior (`_descargar` para la red y `_git` para git) que se inyectan por parámetro: los tests las reemplazan y trabajan en carpetas temporales. `main.py` lo llama una vez (`al_iniciar`) con la ventana creada y antes del menú; el menú solo dibuja el aviso que queda en `estado['aviso_version']`.

**Tech Stack:** Python 3.10 estándar (`urllib.request`, `zipfile`, `tempfile`, `subprocess`, `pathlib`), Pygame solo para la pantalla de carga existente (`ui/pantalla_carga`).

**Spec:** `docs/superpowers/specs/2026-10-06-calendario-mercado-actualizador-design.md`, sección «E · Auto-actualización».

**Método de ejecución:** nativo (superpowers:executing-plans), en esta sesión, sin commits. Diego lo dejó fijado en `EJECUCION-PENDIENTES.md`.

## Global Constraints

- **Seguridad del desarrollo:** durante el desarrollo y los tests NUNCA se toca la red real, ni se ejecuta `git pull`, ni se descarga o copia un ZIP real sobre el repo. Todo test usa descarga y git falsos y una carpeta temporal como «instalación».
- **Nunca se pisan:** `saves/`, `preferencias.json`, `music/`, `musica.txt`, `alpha_football_save.json*`, `alpha_football_edited_db.json`, `alpha_football_db_custom.json`, `context.md`.
- **Validación del ZIP:** trae `main.py` y un `VERSION` igual al consultado; ninguna ruta sale de la carpeta de instalación; se descomprime en una carpeta temporal y recién después se copia. Si algo falla, no se toca nada.
- **Consulta:** `VERSION` de `raw.githubusercontent.com/dajaramilc/AlphaFootball/main`, 4 s de espera. Sin red o con error se sigue jugando sin avisar (queda en el log).
- **`VERSION` = `0.4.10.0`** (lo que hoy muestran el título y el badge): el bump lo decide Diego al cierre. `alpha_football.__version__` lee `VERSION` y el título de la ventana lo usa.
- Comentarios nuevos con `# v0.4.15.0`; textos y comentarios en español; Edit parcial; sin commits.
- Tests: `PYTHONIOENCODING=utf-8 python tests/test_actualizador.py`, deben terminar en `N/N tests pasaron`.

## Review Focus

1. **Red que responde basura** (portal cautivo, 404 con HTML, respuesta vacía): no es una versión → se sigue jugando, sin aviso y sin descargar nada. → Task 2.
2. **ZIP con rutas maliciosas** (`../`, absolutas, con unidad `C:`, con `\`) o que no es un ZIP: se rechaza y no se toca ningún archivo. → Task 4.
3. **Copia que falla a la mitad** (archivo en uso, sin permisos): lo ya pisado se restaura y lo nuevo se borra; el juego queda como estaba. → Task 4.
4. **El ZIP trae datos del jugador** (`saves/`, `preferencias.json`, `alpha_football_save.json.bak`…): no se pisan aunque vengan en el ZIP. → Task 4.
5. **Copia git con cambios, commits sin subir, sin rama remota o sin git instalado:** ante la duda no se toca: solo aviso, nunca `pull`. Y tras instalar no puede haber un bucle de reinicios si la versión local no alcanzó a la remota. → Task 3 y Task 5.

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `VERSION` (nuevo, raíz) | La versión instalada, una línea. |
| `alpha_football/__init__.py` | `__version__` (lee `VERSION`) y `TITULO`. |
| `alpha_football/actualizador.py` (nuevo) | Versiones, consulta, tipo de copia, ZIP (validar, extraer, copiar con restauración), orquestación `revisar`, `al_iniciar`, `reiniciar`. |
| `main.py` | `set_caption(TITULO)` y la llamada a `al_iniciar` antes del menú. |
| `alpha_football/ui/menu.py` | Dibuja `estado['aviso_version']` en el menú principal. |
| `tests/test_actualizador.py` (nuevo) | Todo lo anterior, sin red y en carpetas temporales. |

---

### Task 1: `VERSION`, `__version__` y el título de la ventana

**Files:**
- Create: `VERSION`
- Modify: `alpha_football/__init__.py`, `main.py` (línea de `pygame.display.set_caption`)
- Test: `tests/test_actualizador.py` (nuevo)

**Interfaces:**
- Produces: `alpha_football.__version__: str`, `alpha_football.TITULO: str` (= `"Alpha Football v" + __version__`).

- [ ] **Step 1: test que falla.** Crear `tests/test_actualizador.py`:

```python
"""v0.4.15.0: auto-actualización. Sin red: la consulta, la descarga y git son falsos, y la «instalación»
es una carpeta temporal."""
import sys, os, io, zipfile, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def test_la_version_sale_del_archivo_version_y_el_titulo_la_usa():
    import alpha_football
    from alpha_football import actualizador as A
    escrita = (RAIZ / 'VERSION').read_text(encoding='utf-8').strip()
    assert A.version_valida(escrita)
    assert alpha_football.__version__ == escrita == A.version_local()
    assert alpha_football.TITULO == f"Alpha Football v{escrita}"
    fuente = (RAIZ / 'main.py').read_text(encoding='utf-8')
    assert "set_caption(TITULO)" in fuente and "Alpha Football v0." not in fuente   # sin versión escrita a mano


if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
```

- [ ] **Step 2:** `PYTHONIOENCODING=utf-8 python tests/test_actualizador.py` → FAIL (`VERSION` no existe / no hay módulo `actualizador`).
- [ ] **Step 3: implementación.** `VERSION` con una línea `0.4.10.0`. En `alpha_football/__init__.py`, bajo el docstring:

```python
def _leer_version() -> str:
    """v0.4.15.0: la versión instalada vive en el archivo VERSION de la raíz (lo usa el actualizador)."""
    try:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0.0'
    except OSError:
        return '0.0.0.0'


__version__ = _leer_version()
TITULO = f"Alpha Football v{__version__}"
```

En `main.py`: `from alpha_football import TITULO` junto a la llamada y `pygame.display.set_caption(TITULO)   # v0.4.15.0: la versión sale de VERSION`. El resto del test lo cubre Task 2 (`version_valida`, `version_local`).

- [ ] **Step 4:** se verifica en verde al terminar Task 2 (el test usa `actualizador`).

### Task 2: versiones y consulta

**Files:**
- Create: `alpha_football/actualizador.py`
- Test: `tests/test_actualizador.py`

**Interfaces:**
- Produces: `raiz() -> Path`, `version_valida(v) -> bool`, `es_mayor(remota, local) -> bool`, `version_local(carpeta=None) -> str`, `_descargar(url, espera) -> bytes`, `consultar(descargar=None) -> Optional[str]`, constantes `URL_VERSION`, `URL_ZIP`, `ESPERA_CONSULTA = 4`, `ESPERA_DESCARGA = 60`.

- [ ] **Step 1: tests que fallan** (antes del `if __name__`):

```python
def test_las_versiones_se_comparan_numero_a_numero():
    from alpha_football import actualizador as A
    assert A.es_mayor('0.4.11.0', '0.4.10.0') and A.es_mayor('0.4.10.0', '0.4.9.2') and A.es_mayor('0.5', '0.4.99.9')
    assert not A.es_mayor('0.4.10.0', '0.4.10.0') and not A.es_mayor('0.4.9.2', '0.4.10.0')
    assert not A.es_mayor('0.4.10', '0.4.10.0')                           # los ceros de la cola no cuentan
    for basura in ('', 'v0.4.11', '<html>', '0.4.x', None, '1', '0..4'):
        assert not A.version_valida(basura) and not A.es_mayor(basura, '0.4.10.0'), basura
    assert A.es_mayor('0.4.10.0', '')                                     # sin VERSION local: cualquier remota es nueva


def test_la_consulta_devuelve_la_version_remota_o_nada():
    from alpha_football import actualizador as A
    pedidos = []

    def buena(url, espera):
        pedidos.append((url, espera))
        return b"0.4.11.0\n"
    assert A.consultar(buena) == '0.4.11.0'
    assert pedidos == [("https://raw.githubusercontent.com/dajaramilc/AlphaFootball/main/VERSION", 4)]

    def sin_red(url, espera):
        raise OSError("sin red")
    assert A.consultar(sin_red) is None
    for basura in (b"<html>Inicia sesion en el wifi</html>", b"", b"404: Not Found", b"\xff\xfe"):
        assert A.consultar(lambda u, e, b=basura: b) is None, basura
```

- [ ] **Step 2:** correr → FAIL (`No module named ... actualizador`).
- [ ] **Step 3: implementación** — cabecera del módulo y estas funciones:

```python
# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Auto-actualización (v0.4.15.0)
Al abrir el juego se compara el archivo VERSION con el de GitHub (rama main). Si hay una versión nueva:
- copia bajada como ZIP (sin .git): baja el ZIP de main, lo valida, lo descomprime en una carpeta temporal
  y copia los archivos encima;
- copia git limpia: git pull --ff-only;
- copia git con cambios sin commitear o commits sin subir: no instala, solo avisa en el menú.
Nunca se pisan los datos del jugador (PROTEGIDOS). Sin red o con cualquier error se sigue jugando: queda
en el log. Las únicas puertas al exterior son _descargar (red) y _git: los tests las reemplazan.
Sin UI: main.py llama a al_iniciar() una vez, con la ventana creada y antes del menú.
"""
from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

logger = logging.getLogger(__name__)

REPO, RAMA = "dajaramilc/AlphaFootball", "main"
URL_VERSION = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/VERSION"
URL_ZIP = f"https://github.com/{REPO}/archive/refs/heads/{RAMA}.zip"
ESPERA_CONSULTA, ESPERA_DESCARGA = 4, 60          # segundos
MAX_BYTES_ZIP = 300 * 1024 * 1024                 # descomprimido: tope contra un ZIP dañado o malicioso
# Datos del jugador: nunca se pisan (carpetas o archivos de la raíz; los prefijos cubren .bak y .tmp)
PROTEGIDOS = ('saves', 'music', 'preferencias.json', 'musica.txt', 'alpha_football_edited_db.json',
              'alpha_football_db_custom.json', 'context.md')
PREFIJOS_PROTEGIDOS = ('alpha_football_save.json',)


def raiz() -> Path:
    """La carpeta de instalación (donde están main.py y VERSION)."""
    return Path(__file__).resolve().parent.parent


# --- Versiones ────────────────────────────────────────────────────────────────

def version_valida(v) -> bool:
    return isinstance(v, str) and re.fullmatch(r"\d+(\.\d+){1,5}", v.strip()) is not None


def es_mayor(remota, local) -> bool:
    """¿`remota` es posterior a `local`? Número a número (0.4.10.0 > 0.4.9.2). Una remota ilegible nunca
    es mayor; contra una local ilegible (sin VERSION), cualquier remota válida lo es."""
    if not version_valida(remota):
        return False
    if not version_valida(local):
        return True
    a = tuple(int(x) for x in remota.strip().split('.'))
    b = tuple(int(x) for x in local.strip().split('.'))
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def version_local(carpeta: Optional[Path] = None) -> str:
    try:
        return (Path(carpeta or raiz()) / 'VERSION').read_text(encoding='utf-8').strip()
    except OSError as e:
        logger.warning(f"actualizador: no se pudo leer VERSION: {e}")
        return ''


# --- Consulta ─────────────────────────────────────────────────────────────────

def _descargar(url: str, espera: int) -> bytes:
    """Baja una URL https. Es la ÚNICA función que toca la red (los tests la reemplazan)."""
    import urllib.request
    if not url.startswith("https://"):
        raise ValueError(f"URL no permitida: {url}")
    with urllib.request.urlopen(url, timeout=espera) as respuesta:
        return respuesta.read()


def consultar(descargar: Optional[Callable] = None) -> Optional[str]:
    """La versión publicada en GitHub, o None si no hay red, tarda más de 4 s o la respuesta no es una
    versión (portal cautivo, 404…). Nunca lanza."""
    try:
        texto = (descargar or _descargar)(URL_VERSION, ESPERA_CONSULTA).decode('utf-8', 'replace').strip()
    except Exception as e:
        logger.info(f"actualizador: sin respuesta de GitHub ({e}); se sigue jugando")
        return None
    if not version_valida(texto):
        logger.warning("actualizador: la respuesta de GitHub no es una versión; se ignora")
        return None
    return texto
```

- [ ] **Step 4:** correr → `3/3 tests pasaron`.

### Task 3: qué tipo de copia es (ZIP, git limpia, git con cambios)

**Files:** Modify `alpha_football/actualizador.py`; Test `tests/test_actualizador.py`.

**Interfaces:**
- Produces: `_git(carpeta, *args) -> (int, str)`, `tipo_copia(carpeta, git=None) -> 'zip' | 'git_limpia' | 'git_sucia'`.

- [ ] **Step 1: tests que fallan:**

```python
def _git_falso(respuestas: dict, llamadas: list):
    """git de mentira: {('status', '--porcelain'): (0, '')…}; lo no previsto falla (rc 1)."""
    def git(carpeta, *args):
        llamadas.append(args)
        return respuestas.get(args, (1, 'comando no previsto'))
    return git


LIMPIA = {('status', '--porcelain'): (0, ''), ('rev-list', '--count', '@{u}..HEAD'): (0, '0\n')}


def test_el_tipo_de_copia_ante_la_duda_no_se_toca():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        llamadas = []
        assert A.tipo_copia(carpeta, _git_falso({}, llamadas)) == 'zip' and llamadas == []   # sin .git no se llama a git
        (carpeta / '.git').mkdir()
        assert A.tipo_copia(carpeta, _git_falso(LIMPIA, [])) == 'git_limpia'
        casos = {
            'cambios sin commitear': dict(LIMPIA, **{('status', '--porcelain'): (0, ' M main.py\n')}),
            'commits sin subir': dict(LIMPIA, **{('rev-list', '--count', '@{u}..HEAD'): (0, '2\n')}),
            'sin rama remota': dict(LIMPIA, **{('rev-list', '--count', '@{u}..HEAD'): (128, 'fatal: no upstream')}),
            'git no responde': {},
        }
        for nombre, respuestas in casos.items():
            assert A.tipo_copia(carpeta, _git_falso(respuestas, [])) == 'git_sucia', nombre
```

- [ ] **Step 2:** correr → FAIL (`tipo_copia` no existe).
- [ ] **Step 3: implementación:**

```python
# --- Tipo de copia ────────────────────────────────────────────────────────────

def _git(carpeta: Path, *args: str) -> tuple:
    """(código de salida, salida) de un comando git en esa carpeta; (1, error) si git no está o no responde."""
    try:
        r = subprocess.run(['git', '-C', str(carpeta), *args], capture_output=True, text=True, timeout=120)
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except Exception as e:
        return 1, str(e)


def tipo_copia(carpeta: Path, git: Optional[Callable] = None) -> str:
    """'zip' (sin .git), 'git_limpia' o 'git_sucia': cambios sin commitear, commits sin subir, sin rama
    remota o git que no responde. Ante la duda es 'git_sucia': no se toca nada."""
    carpeta = Path(carpeta)
    if not (carpeta / '.git').exists():
        return 'zip'
    git = git or _git
    rc, salida = git(carpeta, 'status', '--porcelain')
    if rc != 0 or salida.strip():
        return 'git_sucia'
    rc, salida = git(carpeta, 'rev-list', '--count', '@{u}..HEAD')
    if rc != 0 or salida.strip() != '0':
        return 'git_sucia'
    return 'git_limpia'
```

- [ ] **Step 4:** correr → `4/4 tests pasaron`.

### Task 4: el ZIP — validar, descomprimir en temporal y copiar sin pisar lo protegido

**Files:** Modify `alpha_football/actualizador.py`; Test `tests/test_actualizador.py`.

**Interfaces:**
- Produces: `protegido(rel) -> bool`, `validar_zip(datos, version) -> (ok, motivo, prefijo)`, `extraer(datos, prefijo, destino) -> list[str]`, `copiar(origen, carpeta, rels, respaldo) -> list[str]`, `_copiar_archivo` (alias de `shutil.copy2`, punto de fallo de los tests), `actualizar_zip(carpeta, version, descargar=None, paso=None) -> (ok, motivo)`.

- [ ] **Step 1: tests que fallan:**

```python
def _zip(archivos: dict, prefijo='AlphaFootball-main/') -> bytes:
    """ZIP en memoria como el de GitHub: todo dentro de una carpeta raíz."""
    datos = io.BytesIO()
    with zipfile.ZipFile(datos, 'w') as z:
        for nombre, contenido in archivos.items():
            z.writestr(prefijo + nombre, contenido)
    return datos.getvalue()


NUEVO = {'main.py': "print('nuevo')", 'VERSION': "0.4.11.0\n", 'requirements.txt': "pygame>=2.6\n",
         'alpha_football/__init__.py': "# nuevo", 'alpha_football/nuevo_modulo.py': "x = 1",
         # datos del jugador que NO deben pisarse aunque vengan en el ZIP
         'saves/slot1.json': "ZIP", 'music/cancion.mp3': "ZIP", 'preferencias.json': "ZIP", 'musica.txt': "ZIP",
         'alpha_football_save.json': "ZIP", 'alpha_football_save.json.bak': "ZIP",
         'alpha_football_edited_db.json': "ZIP", 'alpha_football_db_custom.json': "ZIP", 'context.md': "ZIP"}
VIEJO = dict(NUEVO, **{'main.py': "print('viejo')", 'VERSION': "0.4.10.0\n", 'alpha_football/__init__.py': "# viejo"})
VIEJO = {k: (v if v != "ZIP" else "MIO") for k, v in VIEJO.items() if k != 'alpha_football/nuevo_modulo.py'}


def _instalacion(tmp, archivos=VIEJO) -> Path:
    carpeta = Path(tmp) / 'juego'
    for nombre, contenido in archivos.items():
        (carpeta / nombre).parent.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_text(contenido, encoding='utf-8')
    return carpeta


def _foto(carpeta: Path) -> dict:
    return {p.relative_to(carpeta).as_posix(): p.read_text(encoding='utf-8')
            for p in sorted(carpeta.rglob('*')) if p.is_file()}


def test_el_zip_se_valida_antes_de_tocar_nada():
    from alpha_football import actualizador as A
    assert A.validar_zip(_zip(NUEVO), '0.4.11.0') == (True, '', 'AlphaFootball-main/')
    assert A.validar_zip(_zip(NUEVO, prefijo=''), '0.4.11.0') == (True, '', '')            # ZIP plano
    malos = {
        'no es un zip': b"<html>error</html>",
        'sin main.py': _zip({k: v for k, v in NUEVO.items() if k != 'main.py'}),
        'sin VERSION': _zip({k: v for k, v in NUEVO.items() if k != 'VERSION'}),
        'otra versión': _zip(dict(NUEVO, VERSION="0.4.12.0")),
        'sube de carpeta': _zip(dict(NUEVO, **{'../fuera.py': "x"})),
        'sube por dentro': _zip(dict(NUEVO, **{'alpha_football/../../fuera.py': "x"})),
        'ruta absoluta': _zip(dict(NUEVO, **{'/etc/fuera': "x"}), prefijo=''),
        'con unidad': _zip(dict(NUEVO, **{'C:/fuera.py': "x"}), prefijo=''),
        'con barra invertida': _zip(dict(NUEVO, **{'..\\fuera.py': "x"})),
        'vacío': _zip({}),
    }
    for nombre, datos in malos.items():
        ok, motivo, _prefijo = A.validar_zip(datos, '0.4.11.0')
        assert not ok and motivo, nombre


def test_actualizar_por_zip_copia_el_codigo_y_no_pisa_los_datos_del_jugador():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        pedidos = []
        ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', lambda u, e: (pedidos.append((u, e)), _zip(NUEVO))[1])
        assert ok and motivo == '', motivo
        assert pedidos == [("https://github.com/dajaramilc/AlphaFootball/archive/refs/heads/main.zip", 60)]
        foto = _foto(carpeta)
        assert foto['main.py'] == "print('nuevo')" and foto['VERSION'] == "0.4.11.0\n"
        assert foto['alpha_football/__init__.py'] == "# nuevo" and foto['alpha_football/nuevo_modulo.py'] == "x = 1"
        for protegido in ('saves/slot1.json', 'music/cancion.mp3', 'preferencias.json', 'musica.txt',
                          'alpha_football_save.json', 'alpha_football_save.json.bak',
                          'alpha_football_edited_db.json', 'alpha_football_db_custom.json', 'context.md'):
            assert foto[protegido] == "MIO", protegido
        assert A.protegido('saves/x/y.json') and A.protegido('alpha_football_save.json.tmp')
        assert not A.protegido('alpha_football/save.py') and not A.protegido('main.py')


def test_un_zip_malo_o_una_descarga_caida_no_tocan_nada():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)

        def caida(url, espera):
            raise OSError("se cortó")
        for descarga in (caida, lambda u, e: b"basura", lambda u, e: _zip(dict(NUEVO, VERSION="9.9.9")),
                         lambda u, e: _zip(dict(NUEVO, **{'../fuera.py': "x"}))):
            ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', descarga)
            assert not ok and motivo and _foto(carpeta) == antes
        assert not (Path(tmp) / 'fuera.py').exists()


def test_si_la_copia_falla_a_la_mitad_todo_vuelve_a_como_estaba():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        original, hechas = A._copiar_archivo, []

        def falla_en_la_tercera(origen, destino):
            hechas.append(destino)
            if len(hechas) == 3:
                Path(destino).write_text("a medio escribir", encoding='utf-8')     # deja basura, como un disco lleno
                raise PermissionError("archivo en uso")
            return original(origen, destino)
        A._copiar_archivo = falla_en_la_tercera
        try:
            ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', lambda u, e: _zip(NUEVO))
        finally:
            A._copiar_archivo = original
        assert not ok and "archivo en uso" in motivo and len(hechas) == 3
        assert _foto(carpeta) == antes                                    # ni lo pisado ni lo nuevo quedan
```

- [ ] **Step 2:** correr → FAIL (`validar_zip` no existe).
- [ ] **Step 3: implementación:**

```python
# --- ZIP ──────────────────────────────────────────────────────────────────────

_copiar_archivo = shutil.copy2        # la copia hacia la instalación (los tests la hacen fallar)


def protegido(rel: str) -> bool:
    """¿Esa ruta (relativa a la instalación) es un dato del jugador? Esos nunca se pisan."""
    partes = PurePosixPath(str(rel).replace('\\', '/')).parts
    return bool(partes) and (partes[0] in PROTEGIDOS or partes[0].startswith(PREFIJOS_PROTEGIDOS))


def _ruta_segura(nombre: str) -> bool:
    """¿Ese nombre del ZIP se queda dentro de la carpeta? Fuera: absolutas, con unidad, con '..' o con '\\'."""
    if not nombre or '\\' in nombre or ':' in nombre or nombre.startswith('/'):
        return False
    return '..' not in PurePosixPath(nombre).parts


def validar_zip(datos: bytes, version: str) -> tuple:
    """(ok, motivo, prefijo). El ZIP debe traer main.py y un VERSION igual al consultado, y ninguna ruta
    puede salir de la carpeta. `prefijo` es la carpeta raíz del ZIP de GitHub ('AlphaFootball-main/')."""
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombres = z.namelist()
            if not nombres:
                return False, "el ZIP está vacío", ''
            if not all(_ruta_segura(n) for n in nombres):
                return False, "el ZIP trae rutas fuera de la carpeta del juego", ''
            if sum(i.file_size for i in z.infolist()) > MAX_BYTES_ZIP:
                return False, "el ZIP es demasiado grande", ''
            raices = {n.split('/', 1)[0] for n in nombres}
            prefijo = '' if 'main.py' in nombres or len(raices) != 1 else next(iter(raices)) + '/'
            for obligatorio in ('main.py', 'VERSION'):
                if prefijo + obligatorio not in nombres:
                    return False, f"al ZIP le falta {obligatorio}", ''
            dentro = z.read(prefijo + 'VERSION').decode('utf-8', 'replace').strip()
            if dentro != version:
                return False, f"el ZIP es de la versión {dentro!r} y se esperaba la {version}", ''
            return True, '', prefijo
    except Exception as e:
        return False, f"no es un ZIP válido: {e}", ''


def extraer(datos: bytes, prefijo: str, destino: Path) -> list:
    """Descomprime en `destino` (una carpeta temporal) los archivos del ZIP, sin su carpeta raíz.
    Devuelve las rutas relativas extraídas."""
    destino = Path(destino).resolve()
    rels = []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for info in z.infolist():
            rel = info.filename[len(prefijo):] if info.filename.startswith(prefijo) else ''
            if info.is_dir() or not rel:
                continue
            final = (destino / rel).resolve()
            if destino not in final.parents:                 # defensa en profundidad: validar_zip ya lo filtró
                raise ValueError(f"ruta fuera de la carpeta temporal: {info.filename}")
            final.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as origen, open(final, 'wb') as salida:
                shutil.copyfileobj(origen, salida)
            rels.append(rel)
    return rels


def copiar(origen: Path, carpeta: Path, rels: list, respaldo: Path) -> list:
    """Copia sobre la instalación los archivos extraídos, salvo los protegidos. Si una copia falla, deja
    todo como estaba (restaura lo pisado desde `respaldo`, borra lo nuevo) y relanza el error."""
    origen, carpeta, respaldo = Path(origen), Path(carpeta), Path(respaldo)
    hechos = []                                              # (ruta, ¿existía antes?)
    try:
        for rel in rels:
            if protegido(rel):
                continue
            final = carpeta / rel
            existia = final.exists()
            if existia:
                (respaldo / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(final, respaldo / rel)
            hechos.append((rel, existia))                    # antes de copiar: una copia a medias también se deshace
            final.parent.mkdir(parents=True, exist_ok=True)
            _copiar_archivo(origen / rel, final)
    except Exception:
        for rel, existia in reversed(hechos):
            try:
                if existia:
                    shutil.copy2(respaldo / rel, carpeta / rel)
                else:
                    (carpeta / rel).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"actualizador: no se pudo restaurar {rel}: {e}")
        raise
    return [rel for rel, _existia in hechos]


def _sin_paso(titulo: str, texto: str = "", avance: Optional[float] = None) -> None:
    """Paso de carga que no dibuja nada (tests y llamadas sin pantalla)."""


def actualizar_zip(carpeta: Path, version: str, descargar: Optional[Callable] = None,
                   paso: Optional[Callable] = None) -> tuple:
    """(ok, motivo). Baja el ZIP de main, lo valida, lo descomprime en una carpeta temporal y recién
    después copia. Si algo falla, la instalación queda como estaba."""
    paso = paso or _sin_paso
    titulo = f"ACTUALIZANDO A {version}"
    try:
        paso(titulo, "Descargando la versión nueva…", 0.15)
        datos = (descargar or _descargar)(URL_ZIP, ESPERA_DESCARGA)
        paso(titulo, "Comprobando la descarga…", 0.45)
        ok, motivo, prefijo = validar_zip(datos, version)
        if not ok:
            return False, motivo
        with tempfile.TemporaryDirectory(prefix='alpha_football_act_') as tmp:
            rels = extraer(datos, prefijo, Path(tmp) / 'nuevo')
            paso(titulo, "Instalando los archivos…", 0.70)
            copiar(Path(tmp) / 'nuevo', Path(carpeta), rels, Path(tmp) / 'respaldo')
        return True, ''
    except Exception as e:
        logger.error(f"actualizador: no se pudo instalar el ZIP: {e}", exc_info=True)
        return False, str(e)
```

- [ ] **Step 4:** correr → `8/8 tests pasaron`.

### Task 5: `revisar` — consulta, decide e instala (y nunca entra en bucle)

**Files:** Modify `alpha_football/actualizador.py`; Test `tests/test_actualizador.py`.

**Interfaces:**
- Consumes: `consultar`, `es_mayor`, `version_local`, `tipo_copia`, `actualizar_zip`.
- Produces: `actualizar_git(carpeta, version, git=None, paso=None) -> (ok, motivo)`, `instalar_requisitos(carpeta, ejecutar=None) -> bool`, `texto_aviso(version) -> str`, `revisar(carpeta=None, descargar=None, git=None, paso=None, instalar=None) -> dict` con claves `'estado'` (`'sin_red' | 'al_dia' | 'actualizado' | 'aviso'`), `'version'`, `'aviso'`, `'reiniciar'`.

- [ ] **Step 1: tests que fallan:**

```python
def _red(version: bytes, zip_bytes=None, pedidos=None):
    """Red de mentira: VERSION responde `version`; el ZIP, `zip_bytes` (None = no debe pedirse)."""
    def descargar(url, espera):
        if pedidos is not None:
            pedidos.append(url)
        if url.endswith('/VERSION'):
            if version is None:
                raise OSError("sin red")
            return version
        assert zip_bytes is not None, "no debía descargarse el ZIP"
        return zip_bytes
    return descargar


def test_sin_red_o_al_dia_no_se_toca_nada_ni_se_avisa():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        for remota, estado in ((None, 'sin_red'), (b"<html>", 'sin_red'), (b"0.4.10.0", 'al_dia'), (b"0.4.9.2", 'al_dia')):
            r = A.revisar(carpeta, _red(remota))
            assert r['estado'] == estado and not r['reiniciar'] and r['aviso'] == '', (remota, r)
        assert _foto(carpeta) == antes


def test_una_copia_zip_se_actualiza_sola_y_pide_reiniciar():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        pasos, instalaciones = [], []
        r = A.revisar(carpeta, _red(b"0.4.11.0\n", _zip(NUEVO)), paso=lambda t, x="", a=None: pasos.append((t, x)),
                      instalar=lambda c: instalaciones.append(c) or True)
        assert r == {'estado': 'actualizado', 'version': '0.4.11.0', 'aviso': '', 'reiniciar': True}
        assert A.version_local(carpeta) == '0.4.11.0' and _foto(carpeta)['saves/slot1.json'] == "MIO"
        assert pasos and all(t == "ACTUALIZANDO A 0.4.11.0" for t, _x in pasos)
        assert instalaciones == []                                         # requirements.txt no cambió
        assert A.revisar(carpeta, _red(b"0.4.11.0"))['estado'] == 'al_dia'  # tras reiniciar no vuelve a instalar


def test_si_cambian_los_requisitos_se_instalan():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        instalaciones = []
        con_otra_lib = dict(NUEVO, **{'requirements.txt': "pygame>=2.6\notra-lib\n"})
        r = A.revisar(carpeta, _red(b"0.4.11.0", _zip(con_otra_lib)), instalar=lambda c: instalaciones.append(c) or True)
        assert r['estado'] == 'actualizado' and instalaciones == [carpeta]
        ordenes = []
        assert A.instalar_requisitos(carpeta, lambda cmd, **k: ordenes.append(cmd))
        assert ordenes[0][1:5] == ['-m', 'pip', 'install', '-r'] and ordenes[0][5].endswith('requirements.txt')


def test_una_copia_git_limpia_hace_pull_ff_only():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp); (carpeta / '.git').mkdir()
        llamadas = []

        def pull(c, *args):
            llamadas.append(args)
            if args == ('pull', '--ff-only'):
                (c / 'VERSION').write_text("0.4.11.0\n", encoding='utf-8')   # lo que haría el pull de verdad
                return 0, 'Updating'
            return LIMPIA.get(args, (1, ''))
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=pull)
        assert r['estado'] == 'actualizado' and r['reiniciar'] and ('pull', '--ff-only') in llamadas


def test_una_copia_git_con_cambios_solo_avisa():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp); (carpeta / '.git').mkdir()
        antes, llamadas = _foto(carpeta), []
        sucia = dict(LIMPIA, **{('status', '--porcelain'): (0, ' M main.py\n')})
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=_git_falso(sucia, llamadas))
        assert r == {'estado': 'aviso', 'version': '0.4.11.0', 'aviso': "Hay una versión nueva (0.4.11.0)", 'reiniciar': False}
        assert ('pull', '--ff-only') not in llamadas and _foto(carpeta) == antes


def test_si_la_instalacion_falla_o_no_alcanza_la_version_no_hay_bucle_de_reinicios():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        r = A.revisar(carpeta, _red(b"0.4.11.0", b"basura"))               # ZIP inválido
        assert r['estado'] == 'aviso' and not r['reiniciar'] and "0.4.11.0" in r['aviso'] and _foto(carpeta) == antes
        (carpeta / '.git').mkdir()
        ya_estaba = lambda c, *args: (0, 'Already up to date.') if args == ('pull', '--ff-only') else LIMPIA.get(args, (1, ''))
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=ya_estaba)           # el pull "funciona" pero VERSION sigue atrás
        assert r['estado'] == 'aviso' and not r['reiniciar']
        fallo = lambda c, *args: (1, 'fatal: Not possible to fast-forward') if args == ('pull', '--ff-only') else LIMPIA.get(args, (1, ''))
        assert A.revisar(carpeta, _red(b"0.4.11.0"), git=fallo)['estado'] == 'aviso'

        def explota(url, espera):
            raise RuntimeError("algo raro")
        assert A.revisar(carpeta, explota)['estado'] == 'sin_red'           # nunca lanza
```

- [ ] **Step 2:** correr → FAIL (`revisar` no existe).
- [ ] **Step 3: implementación:**

```python
# --- Orquestación ─────────────────────────────────────────────────────────────

def actualizar_git(carpeta: Path, version: str, git: Optional[Callable] = None,
                   paso: Optional[Callable] = None) -> tuple:
    """(ok, motivo): git pull --ff-only en una copia limpia."""
    (paso or _sin_paso)(f"ACTUALIZANDO A {version}", "Bajando los cambios…", 0.40)
    rc, salida = (git or _git)(Path(carpeta), 'pull', '--ff-only')
    return rc == 0, ('' if rc == 0 else salida.strip()[:200])


def _leer(ruta: Path) -> bytes:
    try:
        return Path(ruta).read_bytes()
    except OSError:
        return b''


def instalar_requisitos(carpeta: Path, ejecutar: Optional[Callable] = None) -> bool:
    """pip install -r requirements.txt con el mismo intérprete (como audio.py hace con yt-dlp)."""
    try:
        (ejecutar or subprocess.run)([sys.executable, '-m', 'pip', 'install', '-r',
                                      str(Path(carpeta) / 'requirements.txt')],
                                     capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        logger.error(f"actualizador: no se pudieron instalar las dependencias: {e}")
        return False


def texto_aviso(version: str) -> str:
    return f"Hay una versión nueva ({version})"


def revisar(carpeta: Optional[Path] = None, descargar: Optional[Callable] = None,
            git: Optional[Callable] = None, paso: Optional[Callable] = None,
            instalar: Optional[Callable] = None) -> dict:
    """Consulta GitHub y, si hay una versión nueva, la instala según el tipo de copia.
    Devuelve {'estado': 'sin_red' | 'al_dia' | 'actualizado' | 'aviso', 'version': la remota,
    'aviso': texto para el menú, 'reiniciar': bool}. Nunca lanza: ante cualquier error se sigue jugando."""
    res = {'estado': 'sin_red', 'version': None, 'aviso': '', 'reiniciar': False}
    try:
        carpeta = Path(carpeta or raiz())
        remota = consultar(descargar)
        if remota is None:
            return res
        res['version'] = remota
        if not es_mayor(remota, version_local(carpeta)):
            return dict(res, estado='al_dia')
        aviso = dict(res, estado='aviso', aviso=texto_aviso(remota))
        tipo = tipo_copia(carpeta, git)
        if tipo == 'git_sucia':
            logger.info(f"actualizador: hay una versión nueva ({remota}); la copia git tiene cambios: no se instala")
            return aviso
        requisitos = _leer(carpeta / 'requirements.txt')
        if tipo == 'zip':
            ok, motivo = actualizar_zip(carpeta, remota, descargar, paso)
        else:
            ok, motivo = actualizar_git(carpeta, remota, git, paso)
        if not ok or es_mayor(remota, version_local(carpeta)):   # sin esto, un pull que no trae la versión reiniciaría sin fin
            logger.error(f"actualizador: no se instaló la {remota}: {motivo or 'la versión local no cambió'}")
            return aviso
        if _leer(carpeta / 'requirements.txt') != requisitos:
            (paso or _sin_paso)(f"ACTUALIZANDO A {remota}", "Instalando dependencias…", 0.85)
            (instalar or instalar_requisitos)(carpeta)
        (paso or _sin_paso)(f"ACTUALIZANDO A {remota}", "Listo: reiniciando…", 1.0)
        return dict(res, estado='actualizado', reiniciar=True)
    except Exception as e:
        logger.error(f"actualizador: error inesperado, se sigue jugando: {e}", exc_info=True)
        return res
```

- [ ] **Step 4:** correr → `14/14 tests pasaron`.

### Task 6: integración — `al_iniciar`, `reiniciar`, `main.py` y el aviso del menú

**Files:** Modify `alpha_football/actualizador.py`, `main.py`, `alpha_football/ui/menu.py`; Test `tests/test_actualizador.py`.

**Interfaces:**
- Produces: `al_iniciar(revisar_fn=None) -> dict`, `reiniciar(lanzar=None, salir=None) -> None`, `menu._dibujar_aviso_version(screen, estado)`; `estado['aviso_version']: str`.

- [ ] **Step 1: tests que fallan:**

```python
def test_en_los_tests_al_iniciar_jamas_toca_la_red():
    from alpha_football import actualizador as A
    original = A._descargar

    def prohibido(url, espera):
        raise AssertionError("un test tocó la red")
    A._descargar = prohibido
    try:
        assert A.al_iniciar() == {'estado': 'omitido', 'version': None, 'aviso': '', 'reiniciar': False}
        os.environ['ALPHA_SIN_ACTUALIZAR'] = '1'
        assert A.al_iniciar()['estado'] == 'omitido'
    finally:
        A._descargar = original
        os.environ.pop('ALPHA_SIN_ACTUALIZAR', None)


def test_al_iniciar_muestra_los_pasos_y_devuelve_lo_que_dijo_revisar():
    from alpha_football import actualizador as A
    vistos = []

    def revisar_falso(paso=None, **_k):
        paso("ACTUALIZANDO A 0.4.11.0", "Descargando la versión nueva…", 0.15)
        return {'estado': 'actualizado', 'version': '0.4.11.0', 'aviso': '', 'reiniciar': True}
    r = A.al_iniciar(revisar_falso, mostrar=lambda *a: vistos.append(a), cerrar=lambda: vistos.append('cerrar'))
    assert r['reiniciar'] and vistos == [("ACTUALIZANDO A 0.4.11.0", "Descargando la versión nueva…", 0.15), 'cerrar']
    vistos.clear()
    r = A.al_iniciar(lambda paso=None, **_k: {'estado': 'al_dia', 'version': 'x', 'aviso': '', 'reiniciar': False},
                     mostrar=lambda *a: vistos.append(a), cerrar=lambda: vistos.append('cerrar'))
    assert r['estado'] == 'al_dia' and vistos == []                        # sin nada que instalar no hay pantalla de carga


def test_reiniciar_relanza_el_juego_y_cierra_este_proceso():
    from alpha_football import actualizador as A
    hechos = []
    A.reiniciar(lanzar=lambda cmd, cwd: hechos.append((cmd, cwd)), salir=lambda codigo: hechos.append(codigo))
    assert hechos == [([sys.executable] + sys.argv, str(A.raiz())), 0]


def test_el_menu_muestra_el_aviso_de_version_nueva():
    import pygame; pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from alpha_football.ui import menu
    dib, original = [], menu.draw_text
    menu.draw_text = lambda scr, txt, *a, **k: (dib.append(txt), original(scr, txt, *a, **k))[1]
    try:
        menu._dibujar_aviso_version(screen, {})
        assert dib == []
        menu._dibujar_aviso_version(screen, {'aviso_version': "Hay una versión nueva (0.4.11.0)"})
        assert dib == ["Hay una versión nueva (0.4.11.0)"]
    finally:
        menu.draw_text = original
    fuente = (RAIZ / 'main.py').read_text(encoding='utf-8')
    assert "actualizador.al_iniciar()" in fuente and "estado['aviso_version']" in fuente
```

- [ ] **Step 2:** correr → FAIL (`al_iniciar` no existe).
- [ ] **Step 3: implementación.** En `actualizador.py`:

```python
# --- Arranque ─────────────────────────────────────────────────────────────────

def al_iniciar(revisar_fn: Optional[Callable] = None, mostrar: Optional[Callable] = None,
               cerrar: Optional[Callable] = None) -> dict:
    """Lo que llama main.py al abrir el juego (ventana ya creada, antes del menú): revisa y muestra los
    pasos en la pantalla de carga. En los tests (SDL dummy) o con ALPHA_SIN_ACTUALIZAR=1 no hace nada:
    jamás toca la red."""
    omitido = {'estado': 'omitido', 'version': None, 'aviso': '', 'reiniciar': False}
    if revisar_fn is None and (os.environ.get('SDL_VIDEODRIVER') == 'dummy' or os.environ.get('ALPHA_SIN_ACTUALIZAR')):
        return omitido
    try:
        if mostrar is None or cerrar is None:
            from alpha_football.ui import pantalla_carga
            mostrar, cerrar = mostrar or pantalla_carga.mostrar, cerrar or pantalla_carga.cerrar
        mostrado = []

        def paso(titulo: str, texto: str = "", avance: Optional[float] = None) -> None:
            mostrado.append(titulo)
            mostrar(titulo, texto, avance)
        res = (revisar_fn or revisar)(paso=paso)
        if mostrado:
            cerrar()
        return res
    except Exception as e:
        logger.error(f"actualizador: error al iniciar, se sigue jugando: {e}", exc_info=True)
        return omitido


def reiniciar(lanzar: Optional[Callable] = None, salir: Optional[Callable] = None) -> None:
    """Vuelve a abrir el juego con el código nuevo y cierra este proceso."""
    (lanzar or (lambda cmd, cwd: subprocess.Popen(cmd, cwd=cwd)))([sys.executable] + sys.argv, str(raiz()))
    (salir or sys.exit)(0)
```

En `main.py`, justo después de `clock = pygame.time.Clock()` y antes del `estado = {`:

```python
        # v0.4.15.0: auto-actualización (una vez, con la ventana creada y antes del menú)
        aviso_version = ''
        try:
            from alpha_football import actualizador
            resultado_act = actualizador.al_iniciar()
            if resultado_act.get('reiniciar'):
                pygame.quit()
                actualizador.reiniciar()
            aviso_version = resultado_act.get('aviso') or ''
        except Exception as e_act:
            logger.error(f"No se pudo revisar si hay una versión nueva: {e_act}")
```

y, después de crear el dict `estado`, `estado['aviso_version'] = aviso_version`.

En `menu.py`, antes de `render`:

```python
def _dibujar_aviso_version(screen: pygame.Surface, estado: dict) -> None:
    """v0.4.15.0: el actualizador encontró una versión nueva y no la instaló (copia git con cambios o falla)."""
    aviso = estado.get('aviso_version')
    if aviso:
        draw_text(screen, str(aviso)[:60], (100, 598), size='sm', color='dorado')
```

y en el paso `'main'` de `render`, después de `_dibujar_panel_derecho(screen, estado)`: `_dibujar_aviso_version(screen, estado)`.

- [ ] **Step 4:** correr → `18/18 tests pasaron`. Además: `test_calendario.py` (importa `main`), `test_ui_v235.py`, `test_ux_v360.py`, `test_ayuda_v390.py` y `test_pantalla_carga.py` siguen en verde.

### Task 7: cierre del sub-proyecto

- [ ] **Step 1:** `python -m py_compile main.py alpha_football/actualizador.py alpha_football/__init__.py alpha_football/ui/menu.py`.
- [ ] **Step 2:** comprobación sin pantalla (script en el scratchpad, `SDL_VIDEODRIVER=dummy`, sin red): render del menú con `estado['aviso_version']`, captura con `pygame.image.save` y revisión de que el aviso no pisa botones ni el panel derecho; `actualizador.al_iniciar()` devuelve `'omitido'`. NO se ejecuta `main()` ni `revisar()` contra la carpeta real.
- [ ] **Step 3:** bitácora «Auto-actualización (v0.4.15.0, sub-proyecto E)» en `context.md` y línea en `PROGRESO-PENDIENTES.md`. La suite completa se corre una sola vez al final (instrucción de Diego del 2026-10-08).

## Autorrevisión del plan

- **Cobertura del spec:** 1 versión → Task 1; 2 consulta → Task 2; 3 tabla de copias → Task 3 y 5; 4 nunca se pisan → Task 4; 5 validación del ZIP → Task 4; 6 requisitos, reinicio y pantalla de carga → Task 5 y 6; «aviso en el menú» → Task 6.
- **Fuera de alcance (YAGNI):** borrar archivos que desaparecieron en la versión nueva, verificar firmas, actualizar en segundo plano, botón «actualizar ahora».
- **Tipos:** `paso(titulo, texto, avance)` tiene la misma firma que `pantalla_carga.mostrar`; `git(carpeta, *args) -> (rc, salida)` y `descargar(url, espera) -> bytes` se usan igual en todas las tareas.
