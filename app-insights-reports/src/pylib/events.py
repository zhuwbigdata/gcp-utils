import os
import json
import hashlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pdutil
import esutil

entity_types = dict(
    mr=0,
    hive=1,
    spark=2,
    admin=3,
    reg_user=4,
    cluster=5,
    cpu=6,
    memory=7,
    container=8,
    network=9,
    table=10,
    partition=11,
    oozie=12,
    workflow=13,
    workflow_node=14,
    tez=15,
    impala=16,
    entity=17,
    redshift=18
)

def download(file_events, es, entity_type, from_time, to_time, queues=[], users=[]):
    if os.path.exists(file_events):
        print(f'skippped importing {file_events}')
        return
    query = esutil.query({
        'entityType': entity_types[entity_type],
        'eventTime': {'gte': from_time.isoformat(), 'lte': to_time.isoformat()},
        'queue': queues,
        'user': users,
    })
    esutil.download(file_events, es, 'ev-*', query, show_progress=True)


def extract_values(events_df, func_extractor, target_col):
    df = pd.DataFrame()
    df['entityId'] = events_df['entityId']
    df['values'] = events_df.apply(func_extractor, axis=1)
    return pdutil.explode_listcol(df, index_col='entityId', list_col='values', target_col=target_col)
