import logging
import ecs_logging
from app.config import LOG_LEVEL


def get_log_level_from_str(log_level_str: str = LOG_LEVEL) -> int:
  log_level_dict = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
  }

  return log_level_dict.get(log_level_str.upper(), logging.INFO)


def setup_logger(
  name: str = __name__,
  log_level: int = get_log_level_from_str(),
) -> logging.Logger:
  logger = logging.getLogger(name)

  # If the logger already has handlers, assume it was already configured and return it
  if logger.handlers:
    return logger

  logger.setLevel(log_level)

  handler = logging.StreamHandler()
  handler.setLevel(log_level)
  handler.setFormatter(ecs_logging.StdlibFormatter())

  logger.addHandler(handler)

  return logger
