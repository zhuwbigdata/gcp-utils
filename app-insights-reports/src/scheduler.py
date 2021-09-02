#!/usr/bin/env python

import os
import sys
import signal
import shutil
import logging
import logging.handlers
import threading
import subprocess
import json
from datetime import datetime

from pylib import util
from pylib import ioutil
from pylib import cron
from pylib import log

from config import *

logger = logging.getLogger('unravel')

def run(reload):
    logger.info('starting scheduler')
    while True:
        jobs = fetch_jobs()
        if len(jobs)==0:
            reload.wait()
            reload.clear()
            continue
        jobs.append(('0 1 * * *', None)) # for cleanup
        for dt, file in cron.iter(jobs, reload):
            if file:
                run_job(dt, file)
            else:
                apply_retention()
        reload.clear()


def fetch_jobs():
    logger.info('loading jobs')
    jobs = []
    for file in os.listdir('jobs'):
        file = os.path.join('jobs', file)
        if not os.path.isdir(file):
            continue
        file = f'{file}/job.json'
        if not os.path.exists(file):
            continue
        with open(file, 'rt') as f:
            job = json.load(f)
            if 'cron' not in job:
                continue
            if not job.get('enabled', True):
                continue
            jobs.append((job['cron'], file))
    logger.info(f'num_scheduled={len(jobs)}')
    return jobs


def apply_retention():
    logger.info('applying retention')
    jobs = []
    for folder_name in os.listdir('jobs'):
        folder = os.path.join('jobs', folder_name)
        if not os.path.isdir(folder):
            continue
        file = f'{folder}/job.json'
        if not os.path.exists(file):
            continue
        with open(file, 'rt') as f:
            job = json.load(f)
        retention = job.get('retention_days', 1)
        for run_name in os.listdir(folder):
            run_dir = os.path.join(folder, run_name)
            if not os.path.isdir(run_dir):
                continue
            run_time = datetime.strptime(run_name, date_format)
            if (datetime.now()-run_time).days >=retention:
                logger.info(f'deleting {run_dir}')
                shutil.rmtree(run_dir)


def run_job(dt, job_file):
    job_dir = os.path.dirname(job_file)
    job_name = os.path.basename(job_dir)
    run_name = dt.strftime(date_format)
    dest = os.path.join(job_dir, run_name)
    ioutil.mkdirs(dest)
    with open(f'{dest}/log.txt', 'w') as logfile:
        logger.info(f'starting job={job_file} dest={dest}')
        subprocess.Popen(['./job.py', job_file, dest], stdout=logfile, stderr=logfile, start_new_session=True)
    return run_name


if __name__ == '__main__':
    # setup logging
    ioutil.mkdirs('logs')
    log_handlers = [logging.handlers.RotatingFileHandler('logs/scheduler.log', 'a', 1024*1024*10, 5)]
    if 'DEVELOPMENT' in os.environ:
        log_handlers.append(logging.StreamHandler())
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s |  %(message)s',
        handlers=log_handlers
    )
    logger.setLevel(logging.DEBUG)
    log.redirect_std()

    ioutil.mkdirs('jobs')
    ioutil.write_pidfile('scheduler.pid')

    reload = threading.Event()
    def on_sighup(signum, frame):
        reload.set()
    signal.signal(signal.SIGHUP, on_sighup)
    run(reload)
