import os
import atexit

def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def read_file(path):
    with open(path, 'rt') as f:
        return f.read()


def write_file(path, content):
    with open(path, 'wt') as f:
        f.write(content)


def write_pidfile(path):
    write_file(path, str(os.getpid()))
    def delete_pidfile():
        if os.path.exists(path):
            os.remove(path)
    atexit.register(delete_pidfile)
