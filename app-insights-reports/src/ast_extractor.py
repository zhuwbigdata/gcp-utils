#!/usr/bin/env python

# std library
import os
import sys
import shutil
import logging
import logging.handlers
import json
import hashlib
import subprocess
import socket
import traceback
import string
from collections import defaultdict
from datetime import datetime, timedelta

# 3rd Party
import urllib3
import pandas as pd
from pandarallel import pandarallel
from elasticsearch6 import Elasticsearch

# local
from config import *

os.environ['UNRAVEL_PROPS'] = unravel_props
from pylib import ioutil
from pylib import util
from pylib import esutil
from pylib import smtp
from pylib import uprops
import sql
from pylib import log

ioutil.write_pidfile('ast-extractor.pid')
pandarallel.initialize()
es_url = es_url or uprops.es_url()
lr_url = lr_url or uprops.lr_url()


def validate_config():
    # ensure java is in PATH
    if not shutil.which('java'):
        print('java command not found. aborting')
        sys.exit(1)

    # ensure parser jars exist
    if default_parser and not os.path.exists(default_parser):
        print(f'{default_parser} does not exist. aborting')
        sys.exit(1)
    for _, parser in parsers.items():
        if not os.path.exists(parser):
            print(f'{parser} does not exit. aborting')
            sys.exit(1)


validate_config()
es = Elasticsearch(es_url, http_auth=(es_username, es_password) if es_username else None)

urllib3.disable_warnings()
http = urllib3.PoolManager(cert_reqs='CERT_NONE')
headers = {'Content-Type': 'application/json'}

date_format = '%Y-%m-%dT%H:%M:%S'
file_lastrun = f'{data_dir}/lastrun'


def compute_timeinterval():
    end_time = datetime.strptime(datetime.now().strftime(date_format), date_format)
    if os.path.exists(file_lastrun):
        with open(file_lastrun, 'r') as f:
            start_time = datetime.strptime(f.read(), date_format)
    else:
        start_time = end_time - timedelta(days=num_days)
    return start_time - timedelta(seconds=margin_sec), end_time


def generate_asts(file_apps, file_asts, jar_path):
    if os.path.exists(file_asts):
        print(f'skippped AST convertion to {file_asts}')
        return
    logger.info(f'generating ast for {file_apps}')
    ast_log_file = open(f'{file_asts}.log', 'w')
    proc = subprocess.run([
        os.path.join(unravel_java_dir, 'java'), '-jar', jar_path,
        file_apps, file_asts, 'queryStringFull', 'jsontxt'
    ],
        stdout=ast_log_file, stderr=ast_log_file
    )
    if proc.returncode != 0:
        if os.path.exists(file_asts):
            os.remove(file_asts)
        raise Exception(f'AST conversion failed. check {ast_log_file}')
    logger.info(f'AST conversion finished')


def read_apps(file_apps):
    chunks = pd.read_json(file_apps, orient='values', lines=True, dtype=True, chunksize=100000)
    apps_df = pd.concat(chunks)
    apps_df = pd.concat([apps_df, generate_features(apps_df)], axis=1)
    apps_df.drop(columns='queryStringFull', inplace=True)
    return apps_df


def generate_features(apps_df):
    logger.info(f'generating features for {len(apps_df)} apps')
    return apps_df.parallel_apply(lambda row: pd.Series(sql.get_features(row)), axis=1)


def read_asts(file_asts):
    def md5_digest(obj) -> str:
        if not isinstance(obj, str):
            return None
        return hashlib.md5(obj.encode()).hexdigest()

    asts_df = pd.read_csv(file_asts)
    asts_df['astHash'] = asts_df['astString'].parallel_apply(md5_digest)
    return asts_df


def send_to_lr(file_apps, file_asts):
    df = pd.merge(read_apps(file_apps), read_asts(file_asts), on='id', how='left')
    logger.info(f'sending {len(df)} docs to LR: {lr_url}')
    for index, row in df.iterrows():
        id = row['id']
        index = esutil.index_for_timestamp('feature-', row['startTime'])
        body = f'{index} apps {id} {id} {row.to_json()}'
        try:
            r = http.request('PUT', f'{lr_url}/logs/hl/hl/{id}/_bulkr', body=body, headers=headers)
            if r.status // 100 != 2:
                logger.error(f'LR request failed: status={r.status} body={body} resp={r.data.decode()}')
        except Exception as err:
            logger.error(f'LR request failed: body={body} error={err}')


def run(run_dir, start_time, end_time):
    # prepare run dir
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir)
    os.makedirs(run_dir)

    # query elasticsearch and dump to files
    query = json.dumps({
        'size': 10000,
        '_source': ['id', 'kind', 'startTime', 'queryStringFull'],
        'query': {'bool': {'filter': [
            esutil.terms('kind', *kinds),
            esutil.range('startTime', gte=start_time.isoformat(), lt=end_time.isoformat()),
        ]}}
    })
    parser2file = {}

    def open_file(parser):
        if parser not in parser2file:
            dir = ioutil.mkdirs(f'{run_dir}/{os.path.basename(parser)}')
            parser2file[parser] = open(f'{dir}/apps.json', 'w')
        return parser2file[parser]

    kind2file = {}
    scroll = esutil.initscroll(es, 'app-*', query)
    logger.info(f'downloading {scroll["hits"]["total"]} apps from elasticsearch')
    for doc in esutil.iterdocs(es, scroll):
        kind = doc['kind']
        if kind not in kind2file:
            parser = parsers.get(kind, default_parser)
            if parser is None:
                continue
            kind2file[kind] = open_file(parser)
        file_apps = kind2file[kind]
        json.dump(doc, file_apps)
        file_apps.write(os.linesep)

    for parser, file_apps in parser2file.items():
        file_apps.close()
        file_asts = f'{os.path.dirname(file_apps.name)}/asts.csv'
        generate_asts(file_apps.name, file_asts, parser)
        send_to_lr(file_apps.name, file_asts)

    with open(file_lastrun, 'wt') as f:
        f.write(end_time.strftime(date_format))


hostname = socket.gethostname()
mail_template = string.Template('''
host:         ${host}
run_interval: ${start_time} to ${end_time}
run_dir:      ${run_dir}
details:
${details}
''')


def send_email(**kwargs):
    logger.info('sending email')
    msg = smtp.create_message(
        subject=f'ast-extractor run failed on {kwargs["host"]}',
        from_addrs=smtp_fromaddrs or uprops.smtp_fromaddrs(),
        to_addrs=smtp_toaddrs,
        body=mail_template.substitute(kwargs),
    )
    try:
        server = smtp.connect(
            host=smtp_host,
            port=smtp_port,
            username=smtp_username,
            password=smtp_password,
            ssl=smtp_ssl,
            unravel_defaults=True,
        )
        with server:
            server.send_message(msg)
    except:
        logger.exception('send_email failed')


if __name__ == '__main__':
    # setup logging
    ioutil.mkdirs('logs')
    log_handlers = [logging.handlers.RotatingFileHandler('logs/ast-extractor.log', 'a', 1024 * 1024 * 10, 5)]
    if 'DEVELOPMENT' in os.environ:
        log_handlers.append(logging.StreamHandler())
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s |  %(message)s',
        handlers=log_handlers
    )
    logger = logging.getLogger('unravel')
    logger.setLevel(logging.DEBUG)
    log.redirect_std()

    ioutil.mkdirs(data_dir)
    while True:
        start_time, end_time = compute_timeinterval()
        logger.info(f'start_time: {start_time.isoformat()}, end_time: {end_time.isoformat()}')

        # delete old run dirs if necessary
        run_dirs = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
        sorted(run_dirs)
        while len(run_dirs) > 0 and len(run_dirs) >= num_runs_retain_data:
            shutil.rmtree(os.path.join(data_dir, run_dirs[0]))
            run_dirs = run_dirs[1:]

        run_dir = os.path.join(data_dir, end_time.isoformat())
        try:
            run(run_dir, start_time, end_time)
        except:
            logger.exception('run failed')
            try:
                if smtp_toaddrs:
                    send_email(
                        host=hostname,
                        start_time=start_time, end_time=end_time,
                        run_dir=os.path.abspath(run_dir),
                        details=traceback.format_exc(),
                    )
            except:
                logger.exception('send email failed')
        next_run = end_time + timedelta(seconds=schedule_interval_sec)
        logger.info(f'next_run: {next_run.isoformat()}')
        util.sleep_until(next_run)
