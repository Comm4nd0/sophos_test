import logging
from os import path
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_dirs(directory):
    """
    Validated existence of required directories and create if they don't exist.
    :return: boolean
    """
    if not path.exists(directory):
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logging.info(f"Created dir: {directory}")
            return True
        except OSError as error:
            logging.critical(f"Failed to auto create dir: {directory}")
            logging.debug(error)
            return False
        except Exception as error:
            logging.critical(f"Failed to auto create dir: {directory}")
            logging.debug(error)
            return False
    else:
        logging.info(f"Directory '{directory}' exists!")
        return True