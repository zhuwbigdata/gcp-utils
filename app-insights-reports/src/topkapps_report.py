import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from elasticsearch6 import Elasticsearch
import pandas as pd
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

from config import *
from pylib import ioutil
from pylib import esutil
from pylib import apps
from pylib import pdutil
from pylib import dashutil
from pylib import uprops

logger = logging.getLogger('unravel')
es_url = es_url or uprops.es_url()
unravel_url = unravel_url or uprops.unravel_url()


class Report:
    def __init__(self, dest, kind, days, users=[], queues=[], clusters=[], reports=[], topk=100):
        self.dest = dest
        self.kind = kind
        self.days = days
        self.users = users
        self.queues = queues
        self.clusters = clusters
        self.reports = reports
        self.topk = topk

        self.end_time = datetime.now(tz=timezone.utc)
        self.start_time = self.end_time - timedelta(days=self.days)

        self.run_name = dest.split('/')[-1]
        self.job_name = dest.split('/')[-2]

    def download_apps(self, file_apps, es):
        filters = [
            esutil.term('kind', self.kind),
            esutil.range('startTime', gte=self.start_time.isoformat(), lte=self.end_time.isoformat()),
        ]
        if self.users:
            filters.append(esutil.terms('user', *self.users))
        if self.queues:
            filters.append(esutil.terms('queue', *self.queues))
        if self.clusters:
            filters.append(esutil.terms('clusterId', *self.clusters))
        query = {
            'size': es_scroll_size,
            '_source': [
                'id', 'startTime', 'user', 'queue', 'clusterUid',
                'totalDfsBytesWritten', 'totalDfsBytesRead',
                'duration', 'cpuTime', 'vcoreSeconds', 'memorySeconds', 'kind',
            ],
            'query': {'bool': {'filter': filters}},
        }
        return esutil.download(file_apps, es, 'app-*', json.dumps(query))

    def download_features(self, file_features, es):
        filters = [
            esutil.term('kind', self.kind),
            esutil.range('startTime', gte=self.start_time.isoformat(), lte=self.end_time.isoformat()),
            esutil.exists('astHash'),
        ]
        query = {
            'size': 10000,
            '_source': ['id', 'astHash'],
            'query': {'bool': {'filter': filters}},
        }
        return esutil.download(file_features, es, 'feature-*', json.dumps(query))

    def load_data(self, file_apps, file_features):
        logger.info('loading data')
        chunks = pd.read_json(file_apps, orient='values', lines=True, dtype=True, chunksize=100000,
                              convert_dates=apps.date_columns)
        apps_df = pd.concat(chunks)
        apps.apply_column_aliases(apps_df)

        chunks = pd.read_json(file_features, orient='values', lines=True, dtype=True, chunksize=100000)
        features_df = pd.concat(chunk[['id', 'astHash']] for chunk in chunks)

        apps_df = pd.merge(apps_df, features_df, on='id', how='inner')
        apps_df['io'] = apps_df['totalDfsBytesWritten'] + apps_df['totalDfsBytesRead']
        return apps_df

    def generate(self):
        logger.info(f'generating {__name__}: \n{json.dumps(vars(self), indent=2, default=str)}')
        tmp_dir = ioutil.mkdirs(f'{self.dest}/.tmp')

        es = Elasticsearch(es_url, http_auth=(es_username, es_password) if es_username else None)
        try:
            # download apps
            file_apps = f'{tmp_dir}/apps.json'
            num_docs = self.download_apps(file_apps, es)
            if num_docs == 0:
                raise Exception('no app docs. aborting')

            # download features
            file_features = f'{tmp_dir}/features.json'
            num_docs = self.download_features(file_features, es)
            if num_docs == 0:
                raise Exception('no feature docs. aborting')
                return
        finally:
            es.transport.close()

        gb = self.load_data(file_apps, file_features).groupby('astHash')
        app_url_template = apps.URLTemplate(unravel_url=unravel_url)

        def create_links(data):
            df = gb.get_group(data['astHash'])
            n = min(5, df.shape[0])
            ids = df.sample(n=n, random_state=42).sort_values('startTime')
            return ' '.join(ids.apply(app_url_template.make_links(id=True), axis=1).tolist())

        def collect_users(data):
            users = gb.get_group(data['astHash'])['user'].unique().tolist()
            return ', '.join([str(val) for val in users])

        def collect_queues(data):
            queues = gb.get_group(data['astHash'])['queue'].unique().tolist()
            return ', '.join([str(val) for val in queues])

        for m in self.reports:
            logger.info(f'generating trend report for {m}')
            df = pd.concat([
                gb['id'].count().rename('queryRuns'),
                gb['io'].sum(),
                gb['cpuTime'].sum(),
                gb['memorySeconds'].sum(),
                gb['duration'].sum(),
            ], axis=1)
            df = df.nlargest(self.topk, [m, 'queryRuns'])
            df = df.reset_index()

            df[f'{m} Trend'] = df.apply(
                lambda data: pdutil.sparkline(gb.get_group(data['astHash']).sort_values('startTime')[m]), axis=1)
            df['Links to Some App Runs'] = df.apply(create_links, axis=1)
            df['Users'] = df.apply(collect_users, axis=1)
            df['Queues'] = df.apply(collect_queues, axis=1)

            df = df.sort_values(m, ascending=False)

            report_file = f'{self.job_name}_{self.run_name}_{m.lower()}.html'
            df.rename(columns={
                'astHash': 'Query Hash',
                'queryRuns': 'Total Runs',
                'io': 'Total I/O',
                'cpuTime': 'Total CPU Time',
                'memorySeconds': 'Total Memory Seconds',
                'duration': 'Total Duration',
            }, inplace=True)
            title = f'Top {self.topk} {self.kind.title()} Apps by {m.lower()}'
            date_format = '%Y-%m-%d %H:%M:%S %Z'
            config = OrderedDict([
                ('Application Kind', self.kind),
                ('Number of Days',
                 f'{self.days} (from {self.start_time.strftime(date_format)} to {self.end_time.strftime(date_format)})'),
                ('Users', ', '.join(self.users) if self.users else 'All'),
                ('Queues', ', '.join(self.queues) if self.queues else 'All'),
                ('Clusters', ', '.join(self.clusters) if self.clusters else 'All'),
                ('Reports', ', '.join(self.reports)),
                ('Top K', self.topk),
                ('Report', self.job_name),
                ('Run', self.run_name),
            ])
            pdutil.to_html(
                f'{self.dest}/{report_file}',
                df,
                title=title,
                header=title,
                config=config,
                byte_columns=['Total I/O'],
                msec_columns=['Total Duration'],
            )


def layout(params):
    es = Elasticsearch(es_url, http_auth=(es_username, es_password) if es_username else None)
    elastic_search = esutil.ES()
    query = {"aggs": {"min_start_time": {"min": {"field": "startTime"}}, "max_start_time": {"max": {"field": "startTime"}}}}
    aggs = elastic_search.query_es(path='/feature*/_search?size=0', query=query)
    min_start_time = aggs['aggregations']['min_start_time']['value_as_string'] if 'aggregations' in aggs else 0
    max_start_time = aggs['aggregations']['max_start_time']['value_as_string'] if 'aggregations' in aggs else 0
    feature_info = f"Feature generation completed for {min_start_time} to {max_start_time}" if min_start_time is not 0 else 'Feature not available'

    try:
        users_all = sorted(esutil.fetch_values(es, 'app-*', 'user'))
        users_options = [{'label': v, 'value': v} for v in users_all]
        queues_all = sorted(esutil.fetch_values(es, 'app-*', 'queue'))
        queues_options = [{'label': v, 'value': v} for v in queues_all]
        clusters_all = sorted(esutil.fetch_values(es, 'app-*', 'clusterId'))
        clusters_options = [{'label': v, 'value': v} for v in clusters_all]
        report_options = [{'label': 'IO', 'value': 'io'}, {'label': 'Memory Seconds', 'value': 'memorySeconds'},
                          {'label': 'CPU Time', 'value': 'cpuTime'}, {'label': 'Duration', 'value': 'duration'}]
    finally:
        es.transport.close()

    users = params.get('users', []) if params else []
    queues = params.get('queues', []) if params else []
    clusters = params.get('clusters', []) if params else []
    reports = params.get('reports', []) if params else []
    return [
        dbc.FormGroup([
            dbc.Label('Application Kind'),
            dbc.Select(
                id='kind',
                options=[
                    {'label': 'impala', 'value': 'impala'},
                    {'label': 'hive', 'value': 'hive'},
                ],
                value=params['kind'] if params else 'hive',
            ),
            dbc.Tooltip(
                'The app type to base analysis upon',
                target='kind',
                placement='bottom-end',
            ),
        ]),
        dbc.FormGroup([
            dbc.Label(feature_info, style={'backgroundColor': 'rgb(255, 255, 69)'})

        ]),
        dbc.FormGroup([
            dbc.Label('Look Back'),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id='days', type='number', min=0, step=1,
                        value=params['days'] if params else None
                    ),
                    dbc.InputGroupAddon("days", addon_type="append"),
                    dbc.Tooltip(
                        'The period of time over which applications are selected for report generation',
                        target='days',
                        placement='bottom-end',
                    ),
                ], size="sm",
            ),
        ]),
        dbc.FormGroup([
            dbc.Label('Users'),
            dcc.Dropdown(id='users', value=users, options=users_options, multi=True),
            dbc.Tooltip(
                'Select specific users. Leave blank to consider all users',
                target='users',
                placement='bottom-end',
            ),
        ]),
        dbc.FormGroup([
            dbc.Label('Queues'),
            dcc.Dropdown(id='queues', value=queues, options=queues_options, multi=True),
            dbc.Tooltip(
                'Select specific queues. Leave blank to consider all queues',
                target='queues',
                placement='bottom-end',
            ),
        ]),
        dbc.FormGroup([
            dbc.Label('Clusters'),
            dcc.Dropdown(id='clusters', value=clusters, options=clusters_options, multi=True),
            dbc.Tooltip(
                'Select specific clusters. Leave blank to consider all clusters',
                target='clusters',
                placement='bottom-end',
            ),
        ]),
        dbc.FormGroup([
            dbc.Label('Reports'),
            dcc.Dropdown(id='reports', value=reports, options=report_options, multi=True),
            dbc.Tooltip('Select specific reports.', target='reports', placement='bottom-end', ),
        ]),
        dbc.FormGroup([
            dbc.Label('TopK'),
            dbc.Input(id='topk', type="number", min=1, step=1, value=params['topk'] if params else None),
            dbc.Tooltip(
                'number of applications to be shown in the report',
                target='topk',
                placement='bottom-end',
            ),
        ]),
    ]


def params_from_layout(children):
    params = {}
    kind = dashutil.prop(children, 'kind', 'value')
    if kind is None:
        raise Exception('kind is not specified')
    params['kind'] = kind

    days = dashutil.prop(children, 'days', 'value')
    if days is None:
        raise Exception('days is not specified')
    try:
        days = int(days)
    except:
        raise Exception('days must be number')
    if days <= 0:
        raise Exception('days must be positive number')
    params['days'] = days

    users = dashutil.prop(children, 'users', 'value')
    if users:
        params['users'] = users

    queues = dashutil.prop(children, 'queues', 'value')
    if queues:
        params['queues'] = queues

    clusters = dashutil.prop(children, 'clusters', 'value')
    if clusters:
        params['clusters'] = clusters

    reports = dashutil.prop(children, 'reports', 'value')
    if reports is None or len(reports) == 0:
        raise Exception('select reports')
    params['reports'] = reports

    topk = dashutil.prop(children, 'topk', 'value')
    if topk is None:
        raise Exception('topk is not specified')
    try:
        topk = int(topk)
    except:
        raise Exception('topk must be number')
    if topk <= 0:
        raise Exception('topk must be positive number')
    params['topk'] = topk

    return params


if __name__ == '__main__':
    import argparse

    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(levelname)-8s |  %(message)s')

    parser = argparse.ArgumentParser(description='generates kip trend reports')
    parser.add_argument('--dest', help='destination directory', required=True)
    parser.add_argument('--kind', help='application kind', required=True)
    parser.add_argument('--days', help='number of days to look back', required=True, type=int)
    parser.add_argument('--users', help='users to include', nargs='+', metavar='USER', default=[])
    parser.add_argument('--queues', help='queues to include', nargs='+', metavar='QUEUE', default=[])
    parser.add_argument('--clusters', help='clusters to include', nargs='+', metavar='CLUSTER', default=[])
    parser.add_argument('--reports', help='reports to include', required=True)
    parser.add_argument('--topk', help='number of apps in report, default 100', type=int, default=100)
    args = parser.parse_args()

    Report(**vars(args)).generate()
