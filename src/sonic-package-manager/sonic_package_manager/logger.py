#!/usr/bin/env python


import logging
import logging.handlers
import click_log


class Formatter(click_log.ColorFormatter):
    """ Click logging formatter. """

    colors = {
        'error': dict(fg='red'),
        'exception': dict(fg='red'),
        'critical': dict(fg='red'),
        'debug': dict(fg='blue', bold=True),
        'warning': dict(fg='yellow'),
        'info': dict(fg='green', bold=True),
    }


logger = logging.getLogger("sonic-package-manager")
logger.setLevel(logging.INFO)

click_handler = click_log.ClickHandler()
click_handler.formatter = Formatter()

logger.addHandler(click_handler)
logger.addHandler(logging.handlers.SysLogHandler())


def get_logger() -> logging.Logger:
    """
    Returns:
        Logger object.
    """

    return logger

