from datetime import datetime, timezone
from collections import namedtuple
import heapq
import itertools
import threading

from croniter import croniter


def iter(jobs, stop: threading.Event):
    Entry = namedtuple('Entry', ['dt', 'count', 'iter', 'job'])
    pq, counter = [], itertools.count()
    for (expr, job) in jobs:
        iter = new(expr)
        heapq.heappush(pq, Entry(iter.get_next(datetime), next(counter), iter, job))
    while True:
        entry = heapq.heappop(pq)
        heapq.heappush(pq, Entry(entry.iter.get_next(datetime), next(counter), entry.iter, entry.job))
        sec = (entry.dt - datetime.now(tz=timezone.utc)).total_seconds()
        if sec > 0:
            if stop.wait(sec):
                return
        yield entry.dt, entry.job


def new(expr):
    try:
        if expr.endswith('m'):  # 3m
            expr = f'*/{expr[:-1]} * * * *'
        elif expr.endswith('h'):  # 3h
            expr = f'0 */{expr[:-1]} * * *'
        elif expr.endswith('d'):  # 3d
            expr = f'0 0 */{expr[:-1]} * *'

        return croniter(expr, datetime.now(tz=timezone.utc))
    except:
        raise Exception(f'invalid schedule: {expr}')
