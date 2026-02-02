import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Configura logging consistente para toda la app.

    - Usa RichHandler si estÃ¡ disponible.
    - Evita duplicar handlers si se llama mÃ¡s de una vez.
    """

    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    try:
        from rich.logging import RichHandler  # type: ignore

        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%H:%M:%S]",
            handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        )
    except Exception:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
