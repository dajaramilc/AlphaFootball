"""Alpha Football v0.4 — paquete del juego."""


def _leer_version() -> str:
    """v0.4.15.0: la versión instalada vive en el archivo VERSION de la raíz (lo usa el actualizador)."""
    try:
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0.0'
    except OSError:
        return '0.0.0.0'


__version__ = _leer_version()
TITULO = f"Alpha Football v{__version__}"
