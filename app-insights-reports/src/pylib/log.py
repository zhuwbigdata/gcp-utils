import sys
import logging

class LogWriter:
    def __init__(self, logfct):
        self.logfct = logfct
        self.buf = []

    def write(self, msg):
        if msg.endswith('\n'):
            self.buf.append(msg[:-1])
            self.logfct(''.join(self.buf))
            self.buf = []
        else:
            self.buf.append(msg)

    def flush(self):
        pass


def redirect_std():
    _stdout, _stderr = sys.stdout, sys.stderr
    
    stdout = logging.getLogger('stdout')
    stdout.setLevel(logging.INFO)
    sys.stdout = LogWriter(stdout.info)
    
    stderr = logging.getLogger('stderr')
    stderr.setLevel(logging.INFO)
    sys.stderr = LogWriter(stderr.info)

    return _stdout, _stderr
