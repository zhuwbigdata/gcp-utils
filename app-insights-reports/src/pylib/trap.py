import signal

exit = False

def on_signal(signum, frame):
    global exit
    exit = True

signal.signal(signal.SIGINT, on_signal)
signal.signal(signal.SIGTERM, on_signal)

