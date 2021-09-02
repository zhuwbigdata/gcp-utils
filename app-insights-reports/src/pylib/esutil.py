#!/usr/bin/env python3

import os
import json
import logging
from datetime import datetime
from elasticsearch6 import Elasticsearch
from six.moves import urllib

logger = logging.getLogger('unravel')

def term(field, value):
    return {'term':{field:value}}


def terms(field, *values):
    return {'terms':{field:values}}


def exists(field):
    return {'exists':{'field':field}}


def range(field, **params):
    return {'range':{field:params}}


def prefix(field, value):
    return {'prefix':{field:value}}


def wildcard(field, value):
    return {'wildcard':{field:value}}


def script(src):
    return {'script': {'script':src}}


def query(filters, size=10000):
    must = []
    for k, v in filters.items():
        if isinstance(v, list):
            if len(v)>0:
                must.append({"terms":{k: v}})
        elif isinstance(v, dict):
            must.append({"range":{k: v}})
        elif v is not None:
            must.append({"term":{k: v}})
    return json.dumps({"size":size, "query":{"bool":{"must": must}}})


def initscroll(es, index, query, scroll_timeout='2m'):
    if type(query)!=str:
        query = json.dumps(query)
    return es.search(index=index, body=query, scroll=scroll_timeout)


def iterdocs(es, scroller, scroll_timeout='2m', show_progress=False):
    resp = scroller
    sid = resp.get('_scroll_id')
    total = resp['hits']['total']
    n = 0
    while len(resp['hits']['hits']) > 0:
        for hit in resp['hits']['hits']:
            yield hit['_source']
        n += len(resp['hits']['hits'])
        if show_progress:
            print(f'\rgot {n} of {total} documents', end='')
        if not sid:
            break
        resp = es.scroll(scroll_id=sid, scroll=scroll_timeout)
        sid = resp.get('_scroll_id')
    if sid:
        es.clear_scroll(body={'scroll_id': sid})
    if show_progress:
        print()


def download(file_name, es, index, query, scroll_timeout='2m', transform=None, show_progress=False):
    try:
        with open(file_name, 'w') as file:
            scroll = initscroll(es, index, query, scroll_timeout)
            total = scroll['hits']['total']
            logger.info(f'downloading {total} docs from {index} into {file_name}')
            for doc in iterdocs(es, scroll, scroll_timeout, show_progress):
                if transform is not None:
                    doc = transform(doc)
                json.dump(doc, file)
                file.write(os.linesep)
            return total
    except:
        os.remove(file_name)
        raise


def index_for_timestamp(prefix, ts):
    if type(ts)==str:
        ts = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
    year = ts.strftime("%Y")
    month = ts.strftime("%m")
    day = ts.strftime("%d")
    d = datetime(int(year), int(month), int(day)).toordinal()
    sunday = str(datetime.fromordinal(d - (d % 7)))[8:10]
    saturday = str(datetime.fromordinal(d - (d % 7) + 6))[8:10]
    return prefix + year + month + sunday + "_" + saturday


def fetch_values(es, index, field):
    query = {
        'size': 0,
        'aggs': {
            'values': {
                'terms': {
                    'field': field,
                    'size': 10000,
                }
            }
        }
    }
    r = es.search(index=index, body=json.dumps(query))
    return [b['key'] for b in r['aggregations']['values']['buckets']]


class ES(object):
    def __init__(self, host="http://localhost:4171"):
        self.host = host
        self.es = Elasticsearch(hosts=[self.host], headers={})

    def query_es(self, path, query, return_as_dict=True):
        request = urllib.request.Request("{}{}".format(self.host, path))
        request.add_header("Content-Type", "application/json")
        response = urllib.request.urlopen(request, json.dumps(query).encode("utf-8"))
        if return_as_dict:
            return json.loads(response.read())
        else:
            return response.read()
