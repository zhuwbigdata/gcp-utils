import os
import logging
import traceback
import time
from datetime import datetime, timedelta

logger = logging.getLogger('unravel')

def sleep_until(dt):
    while True:
        sec = (dt - datetime.now()).total_seconds()
        if sec<1:
            break
        time.sleep(sec)


# usage: sys.excepthook = util.log_exception
def log_exception(*exc_info):
    text = "".join(traceback.format_exception(*exc_info))
    logger.error("Unhandled exception:\n%s", text)

