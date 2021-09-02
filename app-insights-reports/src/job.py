#!/usr/bin/env python

import sys
import json
import logging
import shutil
import importlib
from datetime import datetime, timezone

from pylib import ioutil

from config import *

if len(sys.argv) != 3:
    print('args: JOB_FILE DEST_DIR', file=sys.stderr)
    sys.exit(1)
_, job_file, dest = sys.argv

# logging
logger = logging.getLogger('unravel')
logger.setLevel(logging.DEBUG)
logging.basicConfig(format='%(asctime)s %(levelname)-8s |  %(message)s')

# pid file
ioutil.mkdirs(dest)
shutil.copyfile(job_file, f'{dest}/job.json')
ioutil.write_pidfile(f'{dest}/.pid')

# run job
try:
    with open(job_file, 'rt') as f:
        job = json.load(f)
    module = importlib.import_module(f'{job["report_type"]}_report')
    params = job['params']
    params['dest'] = dest
    module.Report(**params).generate()
    
    logger.info('report generated successfully')
    ioutil.write_file(f'{dest}/.success', datetime.now(tz=timezone.utc).strftime(date_format))
    shutil.rmtree(f'{dest}/.tmp', ignore_errors=True)
except:
    logger.exception('report generation failed')
    ioutil.write_file(f'{dest}/.failure', datetime.now(tz=timezone.utc).strftime(date_format))

# notify
for channel, params in job.get('notifications', {}).items():
    try:
        module = importlib.import_module(f'{channel}_notify')
        module.notify(dest, **params)
    except:
        logger.exception(f'failed to send notification by {channel}')
