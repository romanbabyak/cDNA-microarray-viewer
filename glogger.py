"""
This module provides a logger setup to init global logger for the application
"""
import logging

#logger setup
def _setup_logger(name="app_logger", level=logging.DEBUG, out=True):
    """
    Sets up a logger with the specified name and logging level

    Args:
        name (str): The name of the logger, default is 'app_logger'
        level (int): The logging level, default is logging.DEBUG

    Returns:
        logging.Logger: A configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if out:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(console_handler)

    return logger

logger = _setup_logger(out=False)  #global_logger
