import logging
import sys

class LoggingHandler():
    def __init__(self):
        super(LoggingHandler, self).__init__()
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(
            logging.Formatter(fmt="[%(asctime)s: %(levelname)s] [%(name)s] %(message)s")
        )
        self._log.addHandler(handler)
