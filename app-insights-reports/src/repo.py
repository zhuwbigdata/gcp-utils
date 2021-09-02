import os
import glob
import json
from collections import namedtuple
from datetime import datetime, timezone

from config import *

from pylib import ioutil

JobDetails = namedtuple('JobDetails', ['name', 'report_type', 'enabled', 'schedule', 'last_run_status', 'last_success_run_time', 'num_runs'])
RunDetails = namedtuple('RunDetails', ['name', 'job_name', 'start_time', 'status', 'duration'])

import logging
logger = logging.getLogger('unravel')


def jobs():
    return sorted(glob.glob('jobs/*/*.json'))


def job_details(job_file):
    with open(job_file) as f:
        job = json.load(f)
    name = job_file.split('/')[-2]
    run_dirs = runs(name)
    last_run_status = None
    last_success_run_time = None
    for run_dir in run_dirs:
        run = run_details(run_dir)
        if run.status=='running':
            continue
        if not last_run_status:
                last_run_status = run.status
        if run.status=='success':
            last_success_run_time = run.start_time
            break
    return JobDetails(
        name = name,
        report_type = job['report_type'],
        enabled = job.get('enabled', True),
        schedule = job.get('cron', 'adhoc'),
        last_run_status = last_run_status,
        last_success_run_time = last_success_run_time,
        num_runs = len(run_dirs),
    )


def runs(job_name):
    return sorted([s[:-1] for s in glob.glob(f'jobs/{job_name}/*/')], reverse=True)


def run_details(run_dir):
    name = run_dir.split('/')[-1]
    job_name = run_dir.split('/')[-2]
    start_time = datetime.strptime(name, date_format).replace(tzinfo=timezone.utc)
    print(start_time)
    status = None
    end_time = None
    if os.path.exists(run_dir+'/.success'):
        status = 'success'
        end_time = datetime.strptime(ioutil.read_file(run_dir+'/.success'), date_format).replace(tzinfo=timezone.utc)
    elif os.path.exists(run_dir+'/.failure'):
        status  = 'failure'
        end_time = datetime.strptime(ioutil.read_file(run_dir+'/.failure'), date_format).replace(tzinfo=timezone.utc)
    elif os.path.exists(run_dir+'/.killed'):
        status  = 'killed'
    elif os.path.exists(run_dir+'/.pid'):
        pid = ioutil.read_file(run_dir+'/.pid')
        try:
            os.kill(int(pid), 0)
            status = 'running'
            end_time = datetime.now(tz=timezone.utc)
        except:
            status = 'killed'
    logger.info(f"start = {start_time}, end = {end_time}")
    return RunDetails(
        name= name,
        job_name = job_name,
        start_time = start_time,
        status = status,
        duration= (end_time - start_time).total_seconds() if end_time is not None else None,
    )

