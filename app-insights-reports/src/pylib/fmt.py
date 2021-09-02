def fmt(num, units):
    num_unit = units[0][1]
    for n, unit in units[1:]:
        if num / n < 1:
            break
        num, num_unit = num / n, unit
    return f'{num:.2f}{num_unit}'


duration_units = [(1, 's'), (60, 'm'), (60, 'h'), (24, 'd')]


def sec(num):
    return fmt(num, duration_units) if type(num) is not str else num


def msec(num):
    return fmt(num / 1000, duration_units) if type(num) is not str else num


byte_units = [(1, 'B')] + [(1024, v + 'B') for v in ['K', 'M', 'G', 'T', 'P', 'E', 'Z']]


def bytes(num):
    return fmt(num, byte_units) if type(num) is not str else num


def duration_sec(num):
    h, m, s = 0, 0, int(num)
    if s >= 60:
        m = s // 60
        s = s % 60
    if m >= 60:
        h = m // 60
        m = m % 60
    return f'{h:02d}:{m:02d}:{s:02d}'
