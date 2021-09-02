import os
import string
import json
import hashlib
import urllib
import subprocess
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pylib import pdutil
from pylib import esutil
from collections import namedtuple

date_columns = ['startTime', 'finishedTime', 'endTime']
json_columns = ['metrics', 'queryTimeline']


def download(file_apps, es, kind, from_time, to_time, queues=[], users=[]):
    if os.path.exists(file_apps):
        print(f'skippped importing {file_apps}')
        return
    query = esutil.query({
        'kind': kind,
        'startTime': {'gte': from_time.isoformat(), 'lte': to_time.isoformat()},
        'queue': queues,
        'user': users,
    })
    esutil.download(file_apps, es, 'app-*', query, show_progress=True)


def generate_asts(file_apps, file_asts, jar_path):
    if os.path.exists(file_asts):
        print(f'skippped AST convertion to {file_asts}')
        return
    ast_log_file = open(f'{file_asts}.log', 'w')
    proc = subprocess.run([
            'java', '-jar', jar_path,
            file_apps, file_asts, 'queryStringFull', 'jsontxt'
        ],
        stdout=ast_log_file, stderr=ast_log_file
    )
    if proc.returncode != 0:
        if os.path.exists(file_asts):
            os.remove(file_asts)
        raise Exception(f'AST conversion failed. check {ast_log_file}')
    print(f'AST conversion finished')


def add_asthash(apps_df, file_asts):
    def md5_digest(obj) -> str:
        if not isinstance(obj, str):
            return None
        return hashlib.md5(obj.encode()).hexdigest()
    asts_df = pd.read_csv(file_asts, converters={'astString':md5_digest})
    asts_df.rename(columns={'astString':'astHash'}, inplace=True)
    return pd.merge(apps_df, asts_df, on='id', how='left')


def resource_usage_summary(sub_df, all_df):
    metrics = ['duration', 'cpuTime', 'memorySeconds', 'totalDfsBytesRead', 'totalDfsBytesWritten',
              'storageWaitTime', 'networkSendWaitTime', 'networkReceiveWaitTime']
    summary = []
    for m in metrics:
        if m not in all_df:
            continue
        total = all_df[m].sum()
        if total > 0:
            summary.append({'metric':m, 'percent': pdutil.percentage(sub_df[m].sum(), total)})
    return pd.DataFrame(summary)


def extract_input_tables(apps_df):
    inputs_df = pdutil.explode_listcol(apps_df, index_col='id', list_col='inputTables', target_col='db_table')
    inputs_df[['db', 'table']] = inputs_df["db_table"].str.split(".", expand=True)
    return inputs_df


def extract_hosts(apps_df):
    return pdutil.explode_listcol(apps_df, index_col='id', list_col=pdutil.pick_col(apps_df, ['instances','hosts']), target_col='hosts')


class URLTemplate:
    kind_path = {
        "mr": "jobs",
        "oozielaunchermr": "jobs",
        "hive": "hive_queries",
        "spark": "spark",
        "impala": "impala",
        "tez": "tez",
        "workflow": "workflow",
    }

    url_template = string.Template('${unravel_url}/#/app/application/${kind_path}?execId=${id}&clusterUid=${clusterUid}')

    def __init__(self, unravel_url, fmt='html'):
        self.unravel_url = unravel_url
        self.fmt = fmt

    def make_link(self, row, txt=None):
        id = row['id']
        vars = {
            'unravel_url': self.unravel_url,
            'kind_path': self.kind_path[row['kind']],
            'id': urllib.parse.quote(id),
            'clusterUid': '',
        }
        v = 'clusterUid'
        if v in row:
            vars[v] = urllib.parse.quote(row[v])

        url = self.url_template.substitute(vars)
        if txt is None:
            txt = id
        if self.fmt == 'markdown':
            return f'[{txt}]({url})'
        return f'<a href="{url}" target="_blank">{txt}</a>'

    def make_links(self, id=False):
        i = 0

        def inner(row):
            nonlocal i
            i += 1
            return self.make_link(row, i) if id is False else self.make_link(row)
        return inner


column_aliases = {
    'cpuTime': ['vcoreSeconds'],
}

def apply_column_aliases(df):
    columns = {}
    for col, aliases in column_aliases.items():
        for alias in aliases:
            if alias in df.columns:
                columns[alias] = col
    if columns:
        df.rename(columns=columns, inplace=True)


def merge_column_aliases(df):
    for col, aliases in column_aliases.items():
        series = None
        for c in [col, *aliases]:
            if c not in df.columns:
                continue
            if series is None:
                series = df[c]
            else:
                series = series.fillna(df[c])
        if series is not None:
            df[col] = series
            df.drop([c for c in aliases if c in df.columns], axis=1, inplace=True)


def columns_from_env(prefix, **kwargs):
    columns = []
    for suffix, value in kwargs.items():
       env = f'{prefix}_{suffix.upper()}'
       if env in os.environ and os.environ[env]=='true':
           if isinstance(value, list):
               columns.extend(value)
           else:
               columns.append(value)
    return columns


class Filter:
    def __init__(self, apps_df):
        self.apps_df = apps_df
        self.filter = pd.Series(np.zeros(len(apps_df), dtype=bool))
        self.info = []

    def remove(self, filter, filter_desc):
        count = filter.sum()
        self.info.append({'filter': filter_desc, 'count': count, 'percent': pdutil.percentage(count, len(self.apps_df))})
        self.filter |= filter

    def remove_nulls(self, columns):
        for m in columns:
            if m not in self.apps_df.columns:
                continue
            self.remove(self.apps_df[m].isnull(), f'missing {m}')

    def remove_values(self, column, values):
        if column not in self.apps_df:
            return
        for value in values:
            self.remove(self.apps_df[column]==value, f'{column}={value}')

    def apply(self):
        self.removed = self.filter.sum()
        self.summary_df = pd.DataFrame(self.info)
        self.summary = f'apps removed: {pdutil.percentage(self.filter.sum(), len(self.apps_df))}% {self.filter.sum()}/{len(self.apps_df)}'
        self.resource_usage_summary = resource_usage_summary(self.apps_df[self.filter], self.apps_df)
        apps_df = self.apps_df[~self.filter]
        apps_df.reset_index(drop=True, inplace=True)
        self.apps_df = None
        self.filter = None
        return apps_df

