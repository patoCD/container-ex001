#
# lib_utils.py
#

from pathlib import Path

import logging
import os
import time

import argparse
from collections.abc import Sized



def find_project_root(start=__file__, marker="pyproject.toml"):
    """
    Busca el directorio raíz del proyecto recorriendo los directorios
    ascendentes desde una ruta inicial hasta encontrar un archivo marcador.

    La función inspecciona la ruta proporcionada y cada uno de sus
    directorios padre hasta localizar un archivo o directorio con el nombre
    especificado en `marker`. Cuando lo encuentra, devuelve la ruta del
    directorio que lo contiene.

    Args:
        start (str | Path, optional):
            Ruta desde la cual comenzar la búsqueda. Por defecto es el
            archivo actual (`__file__`).

        marker (str, optional):
            Nombre del archivo o directorio utilizado como indicador de la
            raíz del proyecto. Por defecto es `"Makefile"`.

    Returns:
        Path:
            Ruta absoluta al directorio raíz del proyecto.

    Raises:
        RuntimeError:
            Si no se encuentra el archivo marcador en la ruta inicial ni en
            ninguno de sus directorios padre.

    Examples:
        >>> root = find_project_root()
        >>> print(root)
        PosixPath('/home/user/my_project')

        >>> root = find_project_root(
        ...     start='/home/user/my_project/src/module.py',
        ...     marker='pyproject.toml'
        ... )
    """

    path = Path(start).resolve()
    
    for parent in [path] + list(path.parents):
        if (parent / marker).exists():
            return parent
    
    raise RuntimeError("No se encontró raíz del proyecto")


# -------------------------
# Logging
# -------------------------
def setup_logging(verbose: bool, dirname = "logs", root_dir=find_project_root()):
    level = logging.DEBUG if verbose else logging.INFO

    log_dir = os.path.join(root_dir, dirname)
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(
        log_dir, 
        f"pipeline_{time.strftime('%Y%m%d_%H%M%S')}.log"
    )

    logger = logging.getLogger()
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(formatter)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return log_file



def opt_get(name, default=None, cast=str):
    """
    Obtiene el valor de un argumento de línea de comandos opcional.

    Crea dinámicamente un argumento con el nombre especificado, analiza los
    argumentos proporcionados al programa y devuelve el valor asociado. Si el
    argumento no está presente, se retorna el valor por defecto indicado.

    Args:
        name (str): Nombre del argumento sin los prefijos ``--``.
            Por ejemplo, ``"port"`` creará el argumento ``--port``.
        default (Any, optional): Valor que se devolverá si el argumento no es
            proporcionado. Por defecto es ``None``.
        cast (Callable, optional): Función utilizada para convertir el valor
            recibido desde la línea de comandos. Por defecto es ``str``.

    Returns:
        Any: Valor del argumento convertido mediante ``cast``, o ``default``
        si el argumento no fue especificado.

    Example:
        >>> # Ejecutando:
        >>> # python app.py --port 8080
        >>> opt_get("port", default=80, cast=int)
        8080

        >>> # Sin especificar --port
        >>> opt_get("port", default=80, cast=int)
        80
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        f"--{name}",
        # dest=name.replace("-", "_"),
        default=default,
        type=cast
    )

    args, _ = parser.parse_known_args()

    return getattr(args, name.replace("-", "_"))


def find_file(filename: str, root_dir = find_project_root()) -> Path:
    """
    Search recursively under ROOT for a file with the given name.

    Args:
        filename: Name of the file to search for.

    Returns:
        Absolute path to the matching file.

    Raises:
        FileNotFoundError: If no matching file is found.
        ValueError: If multiple matching files are found.
    """
    matches = [p for p in root_dir.rglob(filename) if p.is_file()]

    if not matches:
        raise FileNotFoundError(
            f"No file named '{filename}' found under '{root_dir}'."
        )

    if len(matches) > 1:
        raise ValueError(
            f"Multiple files named '{filename}' found:\n" +
            "\n".join(str(p) for p in matches)
        )

    return matches[0].resolve()


def info_desc(obj, label=None):
    """
    Registra información descriptiva de un objeto en el log.

    La función genera un mensaje con el nombre, tipo y tamaño del objeto.
    Si el objeto expone un atributo ``name``, este también se incluye en
    el mensaje registrado.

    Cuando no se proporciona ``label``, la función intenta inferir
    automáticamente el nombre de la variable inspeccionando el contexto
    del llamador.

    Args:
        obj: Objeto que se desea describir.
        label: Etiqueta opcional para identificar el objeto en el log.
            Si es ``None``, se intentará utilizar el nombre de la variable
            asociada al objeto en el ámbito del llamador.

    Returns:
        None.

    Notes:
        - El tamaño se obtiene mediante ``len(obj)`` cuando el objeto
          implementa la interfaz ``Sized``.
        - Para objetos que no implementan ``Sized``, el tamaño se reporta
          como ``"N/A"``.
        - Si el objeto dispone de un atributo ``name``, este se añade al
          mensaje de log.
        - La inferencia automática del nombre utiliza introspección
          mediante ``inspect.currentframe()`` y está pensada
          principalmente para tareas de depuración.

    Example:
        >>> users = ["Alice", "Bob", "Charlie"]
        >>> info_desc(users)
        # users: type=list, size=3

        >>> info_desc(users, label="active_users")
        # active_users: type=list, size=3

        >>> path = Path("data.csv")
        >>> info_desc(path)
        # path: type=PosixPath, size=N/A, name=data.csv
    """
    # Auto-label
    if label is None:
        import inspect
        frame = inspect.currentframe().f_back
        names = [name for name, val in frame.f_locals.items() if val is obj]
        label = names[0] if names else "obj"

    # Type
    obj_type = type(obj).__name__

    # Size/length
    if isinstance(obj, Sized):
        obj_size = len(obj)
    else:
        obj_size = "N/A"

    # Optional: name attribute if present
    obj_name = getattr(obj, "name", None)

    msg = f"{label}: type={obj_type}, size={obj_size}"
    if obj_name is not None:
        msg += f", name={obj_name}"

    logging.debug(msg)




# -------------------------
# Retry decorator
# -------------------------
def retry(retries=3, delay=1, exceptions=(Exception,)):
    def wrapper(func):
        def inner(*args, **kwargs):
            last_error = None

            for attempt in range(1, retries + 1):
                try:
                    logging.debug(f"{func.__name__} attempt {attempt}")
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_error = e
                    logging.warning(
                        f"{func.__name__} failed (attempt {attempt}/{retries}): {e}"
                    )
                    time.sleep(delay * attempt)

            logging.error(f"{func.__name__} failed after {retries} retries")
            raise last_error

        return inner
    return wrapper