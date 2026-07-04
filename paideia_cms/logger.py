"""
PDCMS structured logger.

Usage:
    from paideia_cms.logger import get_logger
    log = get_logger(__name__)
    log.debug("Extracting text from %s", file_url)

Behaviour:
    developer_mode = 1  → DEBUG level  (verbose, all steps visible)
    developer_mode = 0  → WARNING level (silent unless something breaks)

Lazy formatting: log.debug("Processing %s", val) — string is never
constructed unless the level is active, so zero cost in production.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"pdcms.{name}")

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s  [PDCMS] %(levelname)-7s  %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False  # don't double-print via root logger

    logger.setLevel(_level())
    return logger


def _level() -> int:
    try:
        import frappe
        return logging.DEBUG if frappe.conf.get("developer_mode") else logging.WARNING
    except Exception:
        return logging.WARNING
