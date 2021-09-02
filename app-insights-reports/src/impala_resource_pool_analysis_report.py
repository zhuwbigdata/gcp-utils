import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from os import path
import pandas as pd
import shutil
import plotly.express as px
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from elasticsearch6 import Elasticsearch

from config import *
from pylib import apps
from pylib import esutil
from pylib import ioutil
from pylib import pdutil
from pylib import dashutil
from pylib import uprops

from pandarallel import pandarallel
pandarallel.initialize(progress_bar=False)

logger = logging.getLogger('unravel')
es_url = es_url or uprops.es_url()
unravel_url = unravel_url or uprops.unravel_url()


class Report:
    app_url_template = apps.URLTemplate(unravel_url=unravel_url)

    def __init__(self, dest, interval, queue_config_filepath, days, users=[], queues=[], clusters=[]):
        self.dest = dest
        self.interval = interval
        self.queue_config_filepath = queue_config_filepath
        self.days = days
        self.users = users
        self.queues = queues
        self.clusters = clusters

        self.end_time = datetime.now(tz=timezone.utc)
        self.start_time = self.end_time - timedelta(days=self.days)

        self.run_name = dest.split('/')[-1]
        self.job_name = dest.split('/')[-2]
        self.interval_unit = interval[-3:]

    def download_apps(self, file_apps, es):
        filters = [esutil.range('startTime', gte=self.start_time.isoformat(), lte=self.end_time.isoformat()),
                   esutil.terms('kind', 'impala')]
        if self.users:
            filters.append(esutil.terms('user', *self.users))
        if self.queues:
            filters.append(esutil.terms('queue', *self.queues))
        if self.clusters:
            filters.append(esutil.terms('clusterId', *self.clusters))
        query = {
            'size': es_scroll_size,
            'query': {'bool': {'filter': filters}},
        }
        return esutil.download(file_apps, es, 'app-*', json.dumps(query))

    def load_data(self, file_apps):
        logger.info('loading data')
        chunks = pd.read_json(file_apps, orient='values', lines=True, dtype=True, chunksize=100000,
                              convert_dates=apps.date_columns)
        apps_df = pd.concat(chunks)
        apps.apply_column_aliases(apps_df)
        apps_df['io'] = apps_df['totalDfsBytesWritten'] + apps_df['totalDfsBytesRead']
        return apps_df

    def rename_columns(self, df, columns, inplace=False):
        """Rename dataframe columns.

        Parameters
        ----------
        df : pandas.DataFrame
            Dataframe.
        columns : dict-like
            Alternative to specifying axis. If `df.columns` is
            :obj: `pandas.MultiIndex`-object and has a few levels, pass equal-size tuples.

        Returns
        -------
        pandas.DataFrame or None
            Returns dataframe with modifed columns or ``None`` (depends on `inplace` parameter value).

        Examples
        --------
        columns = pd.Index([1, 2, 3])
        df = pd.DataFrame([[1, 2, 3], [10, 20, 30]], columns=columns)
        ...     1   2   3
        ... 0   1   2   3
        ... 1  10  20  30
        rename_columns(df, columns={1 : 10})
        ...    10   2   3
        ... 0   1   2   3
        ... 1  10  20  30

        MultiIndex

        columns = pd.MultiIndex.from_tuples([("A0", "B0", "C0"), ("A1", "B1", "C1"), ("A2", "B2", "")])
        df = pd.DataFrame([[1, 2, 3], [10, 20, 30]], columns=columns)
        df
        ...    A0  A1  A2
        ...    B0  B1  B2
        ...    C0  C1
        ... 0   1   2   3
        ... 1  10  20  30
        rename_columns(df, columns={("A2", "B2", "") : ("A3", "B3", "")})
        ...    A0  A1  A3
        ...    B0  B1  B3
        ...    C0  C1
        ... 0   1   2   3
        ... 1  10  20  30
        """
        columns_new = []
        for col in df.columns.values:
            if col in columns:
                columns_new.append(columns[col])
            else:
                columns_new.append(col)
        columns_new = pd.Index(columns_new, tupleize_cols=True)

        if inplace:
            df.columns = columns_new
        else:
            df_new = df.copy()
            df_new.columns = columns_new
            return df_new

    def parse_queue_config(self, queue_config, parent_config, config, parent_name):
        my_config = queue_config.get("schedulablePropertiesList")
        name = parent_name + "." + queue_config.get("name") if "name" in queue_config else ""
        if len(queue_config.get("queues")) == 0:
            for key in parent_config[0].keys():
                my_config[0][key] = parent_config[0].get(key) if my_config[0].get(key) is None else my_config[0].get(
                    key)
                my_config[0][key] = 'Not Configured' if my_config[0][key] is None else my_config[0].get(key)
            my_config[0]["name"] = name[1:]
            config.append(my_config[0]) if len(my_config) > 0 else my_config
            return
        for queue in queue_config.get("queues"):
            self.parse_queue_config(queue, my_config, config, name)
        return config

    def get_queue_stats_df(self, df, feature):
        df = df[[feature, 'stats_missing', 'status']]
        df['stat_missing_count'] = df.parallel_apply(lambda row: 1 if row['stats_missing'] == 'true' else 0, axis=1)
        df['status_count'] = df.parallel_apply(lambda row: 1 if row['status'] == 'S' else 0, axis=1)
        queue_stats_df = df.groupby(feature, as_index=False).agg(
            {'stats_missing': 'count', 'stat_missing_count': 'sum', 'status_count': 'sum'})
        queue_stats_df = queue_stats_df.rename(
            columns={'stats_missing': 'Number_of_Queries', 'stat_missing_count': 'stats_missing'})
        queue_stats_df['stats_missing %'] = queue_stats_df.parallel_apply(
            lambda row: round((row.stats_missing / row.Number_of_Queries) * 100, 2), axis=1)
        queue_stats_df['successful queries %'] = queue_stats_df.parallel_apply(
            lambda row: round((row.status_count / row.Number_of_Queries) * 100, 2), axis=1)
        queue_stats_df = queue_stats_df[['queue', 'Number_of_Queries', 'stats_missing %', 'successful queries %']]
        return queue_stats_df

    def get_admission_result_df(self, df):
        df = df[['queue', 'id', 'clusterUid', 'admission_result', 'admission_wait', 'pool', 'kind']]
        df['admission_wait'] = df['admission_wait'].astype(float)
        queue_health_df = df.groupby('queue').agg({'admission_result': 'value_counts'}).unstack(fill_value=0)
        admission_wait_df = df.rename(columns={'admission_wait': 'Wait Time'}).groupby('queue', as_index=False).agg(
            {'Wait Time': ['max', self.prct99, self.prct50], 'pool': 'count'})
        admission_result_df = pd.merge(queue_health_df, admission_wait_df, on='queue', how='outer')
        admission_result_df['admitted_immediately_per'] = admission_result_df.parallel_apply(
            lambda row: round(((row.admission_result['Admitted immediately'] / row.pool['count']) * 100), 2), axis=1)
        admission_result_df['rejected_per'] = admission_result_df.parallel_apply(
            lambda row: round(((row.admission_result['Rejected'] / row.pool['count']) * 100), 2), axis=1) if (
                                'admission_result', 'Rejected') in admission_result_df.columns else 0.00
        admission_result_df['others_per'] = admission_result_df.parallel_apply(
            lambda row: round((100 - row.admitted_immediately_per[''] - row.rejected_per['']), 2), axis=1)
        # wait time violations
        merged_wait_time_df = pd.merge(df, admission_wait_df, on='queue', how='outer')
        wait_time_violation_df = merged_wait_time_df.sort_values('admission_wait', ascending=False)
        wait_time_violation_grp_obj = wait_time_violation_df[['id', 'clusterUid', 'queue', 'kind']].groupby('queue', as_index=False)
        wait_time_violation_df = wait_time_violation_df.groupby('queue', as_index=False).first()
        wait_time_violation_df['violations'] = wait_time_violation_df.parallel_apply(self.create_links,
                                                                    args=(wait_time_violation_grp_obj, 'queue'), axis=1)
        wait_time_df = pd.merge(wait_time_violation_df, admission_wait_df, on='queue', how='outer')
        wait_time_df = wait_time_df[['queue', 'violations']]
        admission_result_df = pd.merge(admission_result_df, wait_time_df, on='queue', how='outer')
        admission_result_df = admission_result_df[[('queue', ''), ('pool', 'count'), ('admitted_immediately_per', ''),
                              ('rejected_per', ''), ('others_per', ''), ('Wait Time', 'max'), ('Wait Time', 'prct99'),
                              ('Wait Time', 'prct50'), ('violations')]]
        admission_result_df.columns = pd.MultiIndex.from_tuples((('Pool', ''), ('Number of Queries', ''),
                                      ('% Admitted Immediately', ''), ('% Rejected', ''),  ('% Others', ''),
                                      ('Wait Time', 'max'), ('Wait Time', '99%tile'), ('Wait Time', '50%tile'),
                                      ('Wait Time', 'Top Links')))
        return admission_result_df

    def get_duration_df(self, df):
        def get_duration(data):
            dur = data['finishedTime'] - data['startTime']
            return dur.total_seconds()

        df = df[['id', 'queue', 'startTime', 'finishedTime', 'clusterUid', 'kind']]
        df['Duration'] = df.parallel_apply(get_duration, axis=1)
        duration_df = df.groupby('queue', as_index=False).agg({'Duration': ['max', self.prct99, self.prct50]})
        # top links computation
        merged_duration_df = pd.merge(duration_df, df, on='queue')
        violation_df = merged_duration_df.sort_values('Duration', ascending=False)
        violation_df_grouped_obj = violation_df[['id', 'clusterUid', 'queue', 'kind']].groupby('queue', as_index=False)
        violation_df = violation_df.groupby('queue', as_index=False).first()
        violation_df['violations'] = violation_df.parallel_apply(self.create_links, args=(violation_df_grouped_obj, ('queue')), axis=1)
        violation_df = violation_df[['queue', 'violations']]
        duration_df = pd.merge(duration_df, violation_df, on='queue', how='outer').drop(['queue'], axis=1)

        duration_df.columns = pd.MultiIndex.from_tuples((('queue', ''), ('Duration', 'max'), ('Duration', '99%tile'),
                                                         ('Duration', '50%tile'), ('Duration', 'Top Links')))
        return duration_df

    def get_worker_node_df(self, df, feature):
        df = df[[feature, 'perHostPeakMemUsage']]
        df = pdutil.explode_jsoncol(df, 'perHostPeakMemUsage')
        df['Number of Worker Nodes Observed'] = df.parallel_apply(lambda x: x.count() - 1, axis=1)
        worker_node_df = df.groupby(feature, as_index=False).agg(
            {'Number of Worker Nodes Observed': ['max', self.prct99, self.prct50]})
        worker_node_df = self.rename_columns(worker_node_df, columns={
            ('Number of Worker Nodes Observed', 'prct99'): ('Number of Worker Nodes Observed', '99%tile'),
            ('Number of Worker Nodes Observed', 'prct50'): ('Number of Worker Nodes Observed', '50%tile')})
        return worker_node_df

    def get_agg_memory_df(self, df, feature):
        df['memory_aggregate_peak'] = df['memory_aggregate_peak'].astype(float)
        df = df.rename(columns={'memory_aggregate_peak': 'Max Aggregate Memory'})
        agg_memory_df = df.groupby(feature, as_index=False).agg({'Max Aggregate Memory': ['max', self.prct99, self.prct50]})
        # top links computation
        merged_agg_memory_df = pd.merge(df, agg_memory_df, on=feature, how='outer')
        violation_df = merged_agg_memory_df.sort_values('Max Aggregate Memory', ascending=False)
        violation_grp_obj = violation_df[['id', 'clusterUid', 'kind', feature]].groupby(feature, as_index=False)
        violation_df = violation_df.groupby(feature, as_index=False).first()
        violation_df['violations'] = violation_df.parallel_apply(self.create_links, args=(violation_grp_obj, feature), axis=1)
        agg_memory_df = pd.merge(violation_df, agg_memory_df, on=feature, how='outer')
        agg_memory_df = agg_memory_df[[feature, ('Max Aggregate Memory', 'max'), ('Max Aggregate Memory', 'prct99'),
                                       ('Max Aggregate Memory', 'prct50'), 'violations']]
        agg_memory_df.columns = pd.MultiIndex.from_tuples(((feature, ''), ('Max Aggregate Memory', 'max'),
                                           ('Max Aggregate Memory', '99%tile'), ('Max Aggregate Memory', '50%tile'),
                                           ('Max Aggregate Memory', 'Top Links')))
        return agg_memory_df

    def get_node_peak_memory_df(self, df, feature):
        df = df[[feature, 'perHostPeakMemUsage']]
        df = pdutil.explode_jsoncol(df, 'perHostPeakMemUsage')
        node_peak_memory_df = df.groupby([feature], as_index=False).max(numeric_only=True)
        node_peak_memory_df['host_peak_max'] = node_peak_memory_df.max(axis=1)
        node_peak_memory_df['host_peak_prct99'] = node_peak_memory_df.quantile(0.99, axis=1)
        node_peak_memory_df['host_peak_prct50'] = node_peak_memory_df.quantile(0.5, axis=1)
        node_peak_memory_df = node_peak_memory_df[[feature, 'host_peak_max', 'host_peak_prct99', 'host_peak_prct50']]
        node_peak_memory_df.columns = pd.MultiIndex.from_tuples(((feature, ''), ('Per Node Peak Memory', 'max'),
                                         ('Per Node Peak Memory', '99%tile'), ('Per Node Peak Memory', '50%tile')))
        return node_peak_memory_df

    def get_per_queue_per_interval_df(self, agg_mem_df, per_host_peak_mem_df, df):
        def get_intervals(data):
            interval = self.interval[:-3] + 's' if self.interval_unit == 'sec' else self.interval
            intervals = pd.date_range(data['startTime'], data['finishedTime'], freq=interval)
            return pd.Series(intervals).dt.floor(interval).tolist()

        def get_links(data, group_obj, feature):
            ids_df = group_obj.get_group((data[feature[0]], data[feature[1]])).head(5)
            return ' <Br>'.join(ids_df.apply(self.app_url_template.make_links(id=True), axis=1).tolist())

        agg_mem_df['Interval'] = agg_mem_df.parallel_apply(get_intervals, axis=1)
        agg_mem_df['memory_aggregate_peak'] = agg_mem_df['memory_aggregate_peak'].astype(float)
        agg_mem_df = agg_mem_df.explode('Interval')
        agg_mem_stats_df = agg_mem_df.groupby(['queue', 'Interval'], as_index=False).agg({'id': 'count', 'memory_aggregate_peak': 'sum'})
        agg_mem_stats_df = agg_mem_stats_df.rename(columns={'id': 'Concurrency Observed', 'memory_aggregate_peak': 'Max Aggregate Memory Observed'})
        # top intervals per queue by memory aggregate
        max_mem_agg_df = agg_mem_stats_df.sort_values('Max Aggregate Memory Observed', ascending=False)
        max_mem_agg_df = max_mem_agg_df.groupby('queue', as_index=False).head(5)
        top_query_df = pd.merge(left=max_mem_agg_df, right=agg_mem_df, on=['queue', 'Interval'], how='left')
        top_query_df = top_query_df.groupby(['queue', 'Interval'], as_index=False).head(5)
        top_query_group_obj = top_query_df[['id', 'clusterUid', 'queue', 'Interval', 'kind']].groupby(['queue', 'Interval'], as_index=False)
        top_query_df = top_query_df.groupby(['queue', 'Interval'], as_index=False).first()
        top_query_df['Top Links'] = top_query_df.parallel_apply(get_links, args=(top_query_group_obj, ('queue', 'Interval')), axis=1)
        top_query_df = top_query_df[['queue', 'Interval', 'Top Links']]
        top_intervals_mem_agg_df = pd.merge(max_mem_agg_df, top_query_df, on=['queue', 'Interval'])
        top_intervals_mem_agg_df['Start Time'] = top_intervals_mem_agg_df['Interval']
        top_intervals_mem_agg_df['End Time'] = top_intervals_mem_agg_df['Interval'] + (timedelta(seconds=int(self.interval[:-3])) if self.interval_unit == 'sec' else timedelta(minutes=int(self.interval[:-3])))
        top_intervals_mem_agg_df = top_intervals_mem_agg_df.rename(columns={'queue': 'Pool'})
        top_intervals_mem_agg_df = top_intervals_mem_agg_df[['Pool', 'Start Time', 'End Time', 'Concurrency Observed', 'Max Aggregate Memory Observed', 'Top Links']]

        per_host_peak_mem_df['Interval'] = per_host_peak_mem_df.parallel_apply(get_intervals, axis=1)
        per_host_peak_mem_df = per_host_peak_mem_df[['id', 'clusterUid', 'queue', 'perHostPeakMemUsage', 'Interval', 'kind']]
        per_host_peak_mem_df = pdutil.explode_jsoncol(per_host_peak_mem_df, 'perHostPeakMemUsage')
        hosts_df = per_host_peak_mem_df
        per_host_peak_mem_df['perHostPeakMemUsage'] = per_host_peak_mem_df.max(axis=1)
        per_host_peak_mem_df = per_host_peak_mem_df.explode('Interval')
        per_host_peak_mem_stats_df = per_host_peak_mem_df.groupby(['queue', 'Interval'], as_index=False).agg({'id': 'count', 'perHostPeakMemUsage': 'max'})
        per_host_peak_mem_stats_df = per_host_peak_mem_stats_df.rename(columns={'id': 'Concurrency Observed', 'perHostPeakMemUsage': 'Max Peak Node Memory Observed'})
        # top intervals per queue by host peak mem usage
        max_peak_host_mem_df = per_host_peak_mem_stats_df.sort_values('Max Peak Node Memory Observed', ascending=False)
        max_peak_host_mem_df = max_peak_host_mem_df.groupby('queue', as_index=False).head(5)
        top_host_df = pd.merge(left=max_peak_host_mem_df, right=per_host_peak_mem_df, on=['queue', 'Interval'], how='left')
        top_host_df = top_host_df.groupby(['queue', 'Interval'], as_index=False).head(5)
        top_host_grp_obj = top_host_df[['id', 'clusterUid', 'queue', 'Interval', 'kind']].groupby(['queue', 'Interval'], as_index=False)
        top_host_df = top_host_df.groupby(['queue', 'Interval'], as_index=False).first()
        top_host_df['Top Links'] = top_host_df.parallel_apply(get_links, args=(top_host_grp_obj, ('queue', 'Interval')), axis=1)
        top_host_df = top_host_df[['queue', 'Interval', 'Top Links']]
        top_intervals_peak_node_mem_df = pd.merge(max_peak_host_mem_df, top_host_df, on=['queue', 'Interval'])
        top_intervals_peak_node_mem_df['Start Time'] = top_intervals_peak_node_mem_df['Interval']
        top_intervals_peak_node_mem_df['End Time'] = top_intervals_peak_node_mem_df['Interval'] + (timedelta(seconds=int(self.interval[:-3])) if self.interval_unit == 'sec' else timedelta(minutes=int(self.interval[:-3])))
        top_intervals_peak_node_mem_df = top_intervals_peak_node_mem_df.rename(columns={'queue': 'Pool'})
        top_intervals_peak_node_mem_df = top_intervals_peak_node_mem_df[['Pool', 'Start Time', 'End Time', 'Concurrency Observed', 'Max Peak Node Memory Observed', 'Top Links']]

        df['Interval'] = df.parallel_apply(get_intervals, axis=1)
        df = df.explode('Interval')
        query_concurrency_df = df.groupby(['queue', 'Interval'], as_index=False).agg({'id': 'count'})
        query_concurrency_df = query_concurrency_df.rename(columns={'id': 'Concurrency Observed'})
        # top intervals per queue by query count
        max_query_count_df = query_concurrency_df.sort_values('Concurrency Observed', ascending=False)
        max_query_count_df = max_query_count_df.groupby('queue', as_index=False).head(5)
        query_count_df = pd.merge(left=max_query_count_df, right=df, on=['queue', 'Interval'], how='left')
        query_count_df = query_count_df.groupby(['queue', 'Interval'], as_index=False).head(5)
        query_count_group_obj = query_count_df[['id', 'clusterUid', 'queue', 'Interval', 'kind']].groupby(['queue', 'Interval'], as_index=False)
        query_count_df = query_count_df.groupby(['queue', 'Interval'], as_index=False).first()
        query_count_df['Top Links'] = query_count_df.parallel_apply(get_links,args=(query_count_group_obj, ('queue', 'Interval')),axis=1)
        query_count_df['Start Time'] = query_count_df['Interval']
        query_count_df['End Time'] = query_count_df['Interval'] + (timedelta(seconds=int(self.interval[:-3])) if self.interval_unit == 'sec' else timedelta(minutes=int(self.interval[:-3])))
        query_count_df = query_count_df.rename(columns={'queue': 'Pool'})
        top_intervals_query_concurrency_df = query_count_df[['Pool', 'Start Time', 'End Time', 'Concurrency Observed', 'Top Links']]

        temporal_agg_mem_df = agg_mem_stats_df.rename(columns={'Max Aggregate Memory Observed': 'Aggregate Memory Observed'})
        temporal_agg_mem_df = temporal_agg_mem_df.groupby('queue', as_index=False).agg(
            {'Aggregate Memory Observed': ['min', 'max', 'mean', self.prct99, self.prct50]})
        temporal_query_concurrency_df = query_concurrency_df.groupby('queue', as_index=False).agg(
            {'Concurrency Observed': ['min', 'max', 'mean', self.prct99, self.prct50]})
        a = pd.merge(temporal_agg_mem_df[
                         [('queue', ''), ('Aggregate Memory Observed', 'max'), ('Aggregate Memory Observed', 'prct99'),
                          ('Aggregate Memory Observed', 'prct50')]], temporal_query_concurrency_df[
                         [('queue', ''), ('Concurrency Observed', 'max'), ('Concurrency Observed', 'prct99')]],
                     on='queue')

        temporal_per_host_mem_usage_df = per_host_peak_mem_stats_df.rename(columns={'Max Peak Node Memory Observed': 'Peak Node Memory Observed'})
        temporal_per_host_mem_usage_df = temporal_per_host_mem_usage_df.groupby('queue', as_index=False).agg(
            {'Peak Node Memory Observed': ['min', 'max', 'mean', self.prct99, self.prct50]})
        hosts_df = hosts_df.drop(columns=['id', 'clusterUid', 'Interval', 'perHostPeakMemUsage'], axis=1)
        hosts_df['Worker Node Usage Observed'] = hosts_df.parallel_apply(lambda x: x.count() - 1, axis=1)
        host_counts_df = hosts_df.groupby('queue', as_index=False).agg({'Worker Node Usage Observed': ['max', self.prct99]})
        b = pd.merge(host_counts_df, temporal_per_host_mem_usage_df[
            [('queue', ''), ('Peak Node Memory Observed', 'max'), ('Peak Node Memory Observed', 'prct99')]], on='queue')
        summary_df = pd.merge(a, b, on='queue', how='outer')
        return top_intervals_mem_agg_df, top_intervals_peak_node_mem_df, top_intervals_query_concurrency_df,\
               agg_mem_stats_df, per_host_peak_mem_stats_df, query_concurrency_df, temporal_agg_mem_df,\
               temporal_per_host_mem_usage_df, temporal_query_concurrency_df, summary_df

    def get_graphs_df(self, agg_mem_df, per_host_peak_mem_df, df):
        def get_intervals(data):
            interval = '5min'
            intervals = pd.date_range(data['startTime'], data['finishedTime'], freq=interval)
            return pd.Series(intervals).dt.round('-' + interval).tolist()

        agg_mem_df['Interval'] = agg_mem_df.parallel_apply(get_intervals, axis=1)
        agg_mem_df['memory_aggregate_peak'] = agg_mem_df['memory_aggregate_peak'].astype(float)
        agg_mem_df = agg_mem_df.explode('Interval')
        agg_mem_stats_df = agg_mem_df.groupby(['queue', 'Interval'], as_index=False).agg(
            {'id': 'count', 'memory_aggregate_peak': 'sum'})
        agg_mem_stats_df = agg_mem_stats_df.rename(
            columns={'id': 'Concurrency Observed', 'memory_aggregate_peak': 'Max Aggregate Memory Observed'})

        per_host_peak_mem_df['Interval'] = per_host_peak_mem_df.parallel_apply(get_intervals, axis=1)
        per_host_peak_mem_df = per_host_peak_mem_df[['id', 'clusterUid', 'queue', 'perHostPeakMemUsage', 'Interval']]
        per_host_peak_mem_df = pdutil.explode_jsoncol(per_host_peak_mem_df, 'perHostPeakMemUsage')
        per_host_peak_mem_df['perHostPeakMemUsage'] = per_host_peak_mem_df.max(axis=1)
        per_host_peak_mem_df = per_host_peak_mem_df.explode('Interval')
        per_host_peak_mem_stats_df = per_host_peak_mem_df.groupby(['queue', 'Interval'], as_index=False).agg(
            {'id': 'count', 'perHostPeakMemUsage': 'max'})
        per_host_peak_mem_stats_df = per_host_peak_mem_stats_df.rename(
            columns={'id': 'query_count', 'perHostPeakMemUsage': 'Max Peak Node Memory Observed'})

        df['Interval'] = df.parallel_apply(get_intervals, axis=1)
        df = df[['queue', 'id', 'clusterUid', 'Interval']]
        df = df.explode('Interval')
        query_concurrency_df = df.groupby(['queue', 'Interval'], as_index=False).agg({'id': 'count'})
        query_concurrency_df = query_concurrency_df.rename(columns={'id': 'Concurrency Observed'})

        return agg_mem_stats_df, per_host_peak_mem_stats_df, query_concurrency_df

    def prct99(self, x):
        return x.quantile(0.99)

    def prct50(self, x):
        return x.quantile(0.5)

    def create_links(self, data, group_obj, feature):
        ids_df = group_obj.get_group(data[feature]).head(5)  # at most 5 queries
        return ' <Br>'.join(ids_df.apply(self.app_url_template.make_links(id=True), axis=1).tolist())

    def generate(self):
        start = time.time()
        logger.info(f'generating {__name__}: \n{json.dumps(vars(self), indent=2, default=str)}')
        tmp_dir = ioutil.mkdirs(f'{self.dest}/.tmp')
        es = Elasticsearch(es_url, http_auth=(es_username, es_password) if es_username else None)

        try:
            # download apps
            file_apps = f'{tmp_dir}/apps.json'
            num_docs = self.download_apps(file_apps, es)
            if num_docs == 0:
               raise Exception('no app docs. aborting')
        finally:
            es.transport.close()

        df = self.load_data(file_apps)
        total_queries = df.shape[0]
        df = df[df.queue.notna()]
        queries_without_pool = total_queries - df.shape[0]
        df = pdutil.explode_jsoncol(df, 'metrics')
        if 'clusterUid' not in df.columns:
            df['clusterUid'] = 'default'

        memory_aggregate_peak_df = df[df.memory_aggregate_peak.notna()]
        per_host_peak_mem_usage_df = df[df.perHostPeakMemUsage.notna()]
        mem_agg_query_eliminated = df.shape[0] - memory_aggregate_peak_df.shape[0]
        per_host_query_eliminated = df.shape[0] - per_host_peak_mem_usage_df.shape[0]

        top_intervals_mem_agg_df, top_intervals_peak_node_mem_df, top_intervals_query_concurrency_df,\
        mem_agg_time_series_df, peak_mem_usage_time_series_df, concurrency_time_series_df, temporal_mem_agg_df,\
        temporal_per_host_mem_usage_df, temporal_query_concurrency_df, summary_df = self.get_per_queue_per_interval_df(
            memory_aggregate_peak_df, per_host_peak_mem_usage_df, df)

        agg_mem_stats_df, per_host_peak_mem_stats_df, query_concurrency_df = self.get_graphs_df(
            memory_aggregate_peak_df, per_host_peak_mem_usage_df, df)

        if self.queue_config_filepath is not None:
            f = open(self.queue_config_filepath)
            data = json.load(f)
            queue_config = self.parse_queue_config(data, dict(), list(), "")
            queue_config_df = pd.DataFrame(queue_config)
            queue_config_df = queue_config_df[
                ['name', 'impalaMaxMemory', 'impalaDefaultQueryMemLimit', 'impalaMaxRunningQueries',
                 'impalaMaxQueuedQueries', 'impalaQueueTimeout']]
            queue_config_df['impalaMaxMemory'] = queue_config_df.apply(lambda row: row.impalaMaxMemory * 1048576 if type(row.impalaMaxMemory) is not str else row.impalaMaxMemory, axis=1)
            queue_config_df['impalaDefaultQueryMemLimit'] = queue_config_df.apply(lambda row: row.impalaDefaultQueryMemLimit * 1048576 if type(row.impalaDefaultQueryMemLimit) is not str else row.impalaDefaultQueryMemLimit, axis=1)
            queue_config_df = queue_config_df.rename(columns={'name': 'queue', 'impalaMaxMemory': 'Max Memory',
                                                              'impalaDefaultQueryMemLimit': 'Default Query Memory Limit',
                                                              'impalaMaxRunningQueries': 'Max Running Queries',
                                                              'impalaMaxQueuedQueries': 'Max Queued Queries',
                                                              'impalaQueueTimeout': 'Queue Timeout'})
            shutil.copyfile(self.queue_config_filepath, self.dest + '/queue-config.json')

        for feature in ['summary', 'details']:
            report_file = f'{self.job_name}_{self.run_name}_{feature.lower()}.html'
            title = f'Impala Apps by {feature.lower()}'
            date_format = '%Y-%m-%d %H:%M:%S %Z'
            config = OrderedDict([
                ('Application Kind', 'Impala'),
                ('Interval', self.interval),
                ('Queue Config File', self.queue_config_filepath),
                ('Number of Days', f'{self.days} (from {self.start_time.strftime(date_format)} to {self.end_time.strftime(date_format)})'),
                ('Users', ', '.join(self.users) if self.users else 'All'),
                ('Queues', ', '.join(self.queues) if self.queues else 'All'),
                ('Clusters', ', '.join(self.clusters) if self.clusters else 'All'),
                ('Report', self.job_name),
                ('Run', self.run_name)
            ])
            anchor = {'Pool Configuration': 'Pool Configuration',
                      'Query-Level Addmission Result': 'query-level-admission-result',
                      'Query-level Performance and Resource Usage': 'query-level-performance',
                      'Temporal Baseline of Aggregate Memory Usage': 'temporal-baseline-aggregate-memory-usage',
                      'Top Time Intervals by Aggregate Memory Used': 'top-time-intervals-aggregate-memory-used',
                      'Temporal Baseline of Query Concurrency': 'temporal-baseline-query-concurrency',
                      'Top Time Intervals by Query Concurrency': 'top-time-intervals-query-concurrency',
                      'Temporal Baseline of Host Peak Mem Usage': 'temporal-baseline-host-peak-mem-usage',
                      'Top Time Intervals by Host Peak Mem Usage': 'top-time-intervals-host-peak-mem-usage'
                      }
            if feature == 'details':
                feature = 'queue'

            html = pdutil.HTML(title)
            html.add_header(title)

            if feature == 'summary':
                html.add_config_table(config)
                html.add_header('Pool Utilization Metrics')
                html.add_table_info('The table below presents the stats on various metrics for each resoure pool detected in the data collected by Unravel.')
                pool_stats_df = self.get_queue_stats_df(df, 'queue')
                if self.queue_config_filepath is not None:
                    pool_stats_df = pd.merge(pool_stats_df, queue_config_df[['queue', 'Max Memory']], on='queue', how='outer')
                else:
                    pool_stats_df['Max Memory'] = 'Not Configured'
                pool_stats_df.columns = pd.MultiIndex.from_tuples((('queue', ''), ('Number of Queries', ''),
                                                                ('% Of Queries Run With Stats Missing', ''),
                                                                ('% of Successful Queries', ''), ('Max Memory Configured', '')))

                summary_df = pd.merge(pool_stats_df, summary_df, on='queue', how='outer')
                summary_df = self.rename_columns(summary_df, columns={
                    ('queue', ''): ('Pool', ''),
                    ('Aggregate Memory Observed', 'prct99'): ('Aggregate Memory Observed', '99%tile'),
                    ('Aggregate Memory Observed', 'prct50'): ('Aggregate Memory Observed', '50%tile'),
                    ('Concurrency Observed', 'prct99'): ('Concurrency Observed', '99%tile'),
                    ('Worker Node Usage Observed', 'prct99'): ('Worker Node Usage Observed', '99%tile'),
                    ('Peak Node Memory Observed', 'prct99'): ('Peak Node Memory Observed', '99%tile')})
                html.add_data_table(summary_df, byte_columns=[('Max Memory Configured', ''),
                                                              ('Aggregate Memory Observed', 'max'),
                                                              ('Aggregate Memory Observed', '99%tile'),
                                                              ('Aggregate Memory Observed', '50%tile'),
                                                              ('Peak Node Memory Observed', 'max'),
                                                              ('Peak Node Memory Observed', '99%tile')])
                html.add_config_table({'Total number of queries': total_queries,
                                       'Queries without pool': queries_without_pool,
                                      'Queries eliminated based on missing memory_aggregate_peak': mem_agg_query_eliminated,
                                       'Queries eliminated based on missing per_host_peak_mem_usage': per_host_query_eliminated})
                html.write_to_file(f'{self.dest}/{report_file}')
                continue

            html.add_anchor_links(anchor)
            html.add_config_table(config)

            if self.queue_config_filepath is not None:
                html.add_anchor('pool-configuration')
                html.add_header('Pool Configuration')
                html.add_table_info("To start with, here's are the settings for each resource pool.")
                queue_config_df = queue_config_df.rename(columns={'queue': 'Pool'})
                html.add_data_table(queue_config_df, byte_columns=['Max Memory', 'Default Query Memory Limit'], msec_columns=['Queue Timeout'])

            html.add_anchor('query-level-admission-result')
            html.add_header('Query-Level Addmission Result')
            html.add_table_info("Query admission result analysis provides a good view of the SLAs as perceived by the clients. The table below presents two main metrics - status of admission control and the wait times associated with all the queries in the data.")
            admission_result_df = self.get_admission_result_df(df)
            html.add_data_table(admission_result_df, msec_columns=[('Wait Time', 'max'), ('Wait Time', '99%tile'), ('Wait Time', '50%tile')])
            html.add_config_table({'Top Links': 'Top 5(at most) queries having max value of wait time.'})

            html.add_anchor('query-level-performance')
            html.add_header('Query-level Performance and Resource Usage')
            html.add_table_info("The following table summarizes the statistics on for metrics - query durations, no of nodes that the queries ran on, max aggregate memory and per node peak memory. A few links are also provided to enable a deeper analysis.")
            query_duration_per_queue_df = self.get_duration_df(df)
            host_counts_df = self.get_worker_node_df(per_host_peak_mem_usage_df, feature)
            a = pd.merge(query_duration_per_queue_df, host_counts_df, on=feature, how='outer')
            mem_agg_peak_df = self.get_agg_memory_df(memory_aggregate_peak_df, feature)
            per_host_peak_mem_feature_df = self.get_node_peak_memory_df(per_host_peak_mem_usage_df, feature)
            b = pd.merge(mem_agg_peak_df, per_host_peak_mem_feature_df, on=feature, how='outer')
            performance_df = pd.merge(a, b, on=feature, how='outer')
            performance_df = self.rename_columns(performance_df, columns={('queue', ''): ('Pool', '')})
            html.add_data_table(performance_df, byte_columns=[('Max Aggregate Memory', 'max'),
                                                ('Max Aggregate Memory', '99%tile'), ('Max Aggregate Memory', '50%tile'),
                                                ('Per Node Peak Memory', 'max'), ('Per Node Peak Memory', '99%tile'),
                                                ('Per Node Peak Memory', '50%tile')], sec_columns=[('Duration', 'max'),
                                                ('Duration', '99%tile'), ('Duration', '50%tile')])
            html.add_config_table({'Top Links (Duration)': 'Top 5(at most) queries having max value of duration.',
                                   'Top Links (Max Aggregate Memory)': 'Top 5(at most) queries having max value of aggregate memory.'})

            html.add_anchor('temporal-baseline-aggregate-memory-usage')
            html.add_header('Temporal Baseline of Aggregate Memory Usage')
            html.add_table_info("Considering only aggregate memory usage as a metric, the following is the summary of the statistics observed by slicing data into intervals of 1 second and summing up the aggregate memory usage across all the queries in each interval. We finally compute the statistics over the series of aggregate memory across the intervals of time.")
            temporal_mem_agg_df = self.rename_columns(temporal_mem_agg_df, columns={('queue', ''): ('Pool', ''),
                ('Aggregate Memory Observed', 'prct99'): ('Aggregate Memory Observed', '99%tile'),
                ('Aggregate Memory Observed', 'prct50'): ('Aggregate Memory Observed', '50%tile')})
            html.add_data_table(temporal_mem_agg_df, byte_columns=[('Aggregate Memory Observed', 'min'),
                                                                   ('Aggregate Memory Observed', 'max'),
                                                                   ('Aggregate Memory Observed', 'mean'),
                                                                   ('Aggregate Memory Observed', '99%tile'),
                                                                   ('Aggregate Memory Observed', '50%tile')])
            html.add_anchor('top-time-intervals-aggregate-memory-used')
            html.add_header('Top Time Intervals by Aggregate Memory Used')
            html.add_table_info("To further understand the temporal baseline for aggregate memory usage we present the top 5 intervals per resource pool based on the total aggregated memory.")
            html.add_data_table(top_intervals_mem_agg_df, byte_columns=['Max Aggregate Memory Observed'])
            html.add_config_table({'Top Links': 'Top 5(at most) Max Aggregate Memory Observed per queue in that interval.'})
            agg_mem_fig = px.line(agg_mem_stats_df, x="Interval", y="Max Aggregate Memory Observed", title='Aggregate Memory Used', color='queue')
            html.add_table_info("Here's a graphical representation of the variations in aggregate memory across the timeline. Interval is 5 minutes")
            html.add_line_graph(agg_mem_fig, path=self.dest+'/', filename='aggregate_memory.html')

            html.add_anchor('temporal-baseline-query-concurrency')
            html.add_header('Temporal Baseline of Query Concurrency')
            html.add_table_info("Considering only query concurrency as a metric, the following is the summary of the statistics observed by slicing data into intervals of 1 second and summing up the number of queries in each interval. We finally compute the statistics over the series of query concurrency observed across the intervals of time.")
            temporal_query_concurrency_df = self.rename_columns(temporal_query_concurrency_df, columns={('queue', ''): ('Pool', ''),
                ('Concurrency Observed', 'prct99'): ('Concurrency Observed', '99%tile'),
                ('Concurrency Observed', 'prct50'): ('Concurrency Observed', '50%tile')})
            html.add_data_table(temporal_query_concurrency_df)
            html.add_anchor('top-time-intervals-query-concurrency')
            html.add_header('Top Time Intervals by Query Concurrency')
            html.add_table_info("To further understand the temporal baseline for query concurrency we present the top 5 intervals per resource pool based on the query concurrency.")
            html.add_data_table(top_intervals_query_concurrency_df)
            html.add_config_table({'Top Links': 'Top 5(at most) Concurrency Observed per queue in that interval.'})
            concurrency_observed_fig = px.line(query_concurrency_df, x="Interval", y="Concurrency Observed", title="Concurrency Observed", color='queue')
            html.add_table_info("Here's a graphical representation of the variations in query concurrency across the timeline. Interval is 5 minutes")
            html.add_line_graph(concurrency_observed_fig, path=self.dest+'/', filename='concurrency_observed.html')

            html.add_anchor('temporal-baseline-host-peak-mem-usage')
            html.add_header('Temporal Baseline of Host Peak Mem Usage')
            html.add_table_info("Considering only the Host level Peak Mem Usage as a metric, the following is the summary of the statistics observed by slicing data into intervals of 1 second and taking the maximum per host peak memory usage across all the hosts in each interval. We finally compute the statistics over the series of per host peak memory across the intervals of time.")
            temporal_per_host_mem_usage_df = self.rename_columns(temporal_per_host_mem_usage_df, columns={('queue', ''): ('Pool', ''),
                ('Peak Node Memory Observed', 'prct99'): ('Peak Node Memory Observed', '99%tile'),
                ('Peak Node Memory Observed', 'prct50'): ('Peak Node Memory Observed', '50%tile')})
            html.add_data_table(temporal_per_host_mem_usage_df, byte_columns=[('Peak Node Memory Observed', 'min'),
                                                                              ('Peak Node Memory Observed', 'max'),
                                                                              ('Peak Node Memory Observed', 'mean'),
                                                                              ('Peak Node Memory Observed', '99%tile'),
                                                                              ('Peak Node Memory Observed', '50%tile')])
            html.add_anchor('top-time-intervals-host-peak-mem-usage')
            html.add_header('Top Time Intervals by Host Peak Mem Usage')
            html.add_table_info("To further understand the temporal baseline for per host peak memory usage we present the top 5 intervals per resource pool based on the max per host peak memory usage.")
            html.add_data_table(top_intervals_peak_node_mem_df, byte_columns=['Max Peak Node Memory Observed'])
            html.add_config_table({'Top Links': 'Top 5(at most) Max Peak Node Memory Observed per queue in that interval.'})
            peak_node_mem_fig = px.line(per_host_peak_mem_stats_df, x="Interval", y="Max Peak Node Memory Observed", title="Host Peak Memory Observed", color='queue')
            html.add_table_info("Here's a graphical representation of the variations in per host peak memory across the timeline. Interval is 5 minutes")
            html.add_line_graph(peak_node_mem_fig, path=self.dest+'/', filename='host_peak_mem.html')

            html.write_to_file(f'{self.dest}/{report_file}')
            logger.info(f'total time taken = {time.time() - start}')


def layout(params):
    es = Elasticsearch(es_url, http_auth=(es_username, es_password) if es_username else None)
    try:
        users_all = sorted(esutil.fetch_values(es, 'app-*', 'user'))
        users_options = [{'label': v, 'value': v} for v in users_all]
        queues_all = sorted(esutil.fetch_values(es, 'app-*', 'queue'))
        queues_options = [{'label': v, 'value': v} for v in queues_all]
        clusters_all = sorted(esutil.fetch_values(es, 'app-*', 'clusterId'))
        clusters_options = [{'label': v, 'value': v} for v in clusters_all]
        interval_options = [{'label': v, 'value': v} for v in ['1sec', '10sec', '30sec', '1min', '2min', '5min', '10min']]
    finally:
        es.transport.close()
    users = params.get('users', []) if params else []
    queues = params.get('queues', []) if params else []
    clusters = params.get('clusters', []) if params else []
    queue_config_filepath = params.get('queue_config_filepath') if params else None
    return [
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
            dbc.Label('Interval'),
            dcc.Dropdown(id='interval', value='1sec', options=interval_options, multi=False),
            dbc.Tooltip('Time series interval', target='interval', placement='bottom-end'),
        ]),
        dbc.FormGroup([
            dbc.Label('Queue Config File Path'),
            dbc.Input(id='queue_config_filepath', value=queue_config_filepath, type='text', placeholder='path to queue-config.json'),
            dbc.Tooltip('Path To queue-config.json File', target='queue_config_filepath', placement='bottom-end'),
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
            dbc.Label('Pools'),
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
    ]


def params_from_layout(children):
    params = {}
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

    params['interval'] = dashutil.prop(children, 'interval', 'value')

    queue_config_path = dashutil.prop(children, 'queue_config_filepath', 'value')
    params['queue_config_filepath'] = queue_config_path

    users = dashutil.prop(children, 'users', 'value')
    if users:
        params['users'] = users

    queues = dashutil.prop(children, 'queues', 'value')
    if queues:
        params['queues'] = queues

    clusters = dashutil.prop(children, 'clusters', 'value')
    if clusters:
        params['clusters'] = clusters
    return params


if __name__ == '__main__':
    import argparse

    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(levelname)-8s |  %(message)s')

    parser = argparse.ArgumentParser(description='generates resource usage reports')
    parser.add_argument('--dest', help='destination directory', required=True)
    parser.add_argument('--days', help='number of days to look back', required=True, type=int)
    parser.add_argument('--interval', help='interval for time series data', required=True)
    parser.add_argument('--queue_config_filepath', help='path to queue configuration', required=True)
    parser.add_argument('--users', help='users to include', nargs='+', metavar='USER', default=[])
    parser.add_argument('--queues', help='queues to include', nargs='+', metavar='QUEUE', default=[])
    parser.add_argument('--clusters', help='clusters to include', nargs='+', metavar='CLUSTER', default=[])
    args = parser.parse_args()

    Report(**vars(args)).generate()
