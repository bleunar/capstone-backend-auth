import logging
import sys

class LogWrapper:
    def __init__(self):
        self.logger = logging.getLogger("backend_auth")
        self.logger.setLevel(logging.INFO)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(action)s | %(description)s",
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        if not self.logger.hasHandlers():
            self.logger.addHandler(handler)

    def inform(self, action: str, description: str):
        self.logger.info("", extra={"action": action, "description": description})

    def error(self, action: str, description: str):
        self.logger.error("", extra={"action": action, "description": description})

    def warn(self, action: str, description: str):
        self.logger.warning("", extra={"action": action, "description": description})

    def debug(self, action: str, description: str):
        self.logger.debug("", extra={"action": action, "description": description})


# Create a global instance for reuse
log = LogWrapper()
