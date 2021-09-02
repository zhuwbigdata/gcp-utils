# helper functions for library

import math
import json
import base64
from string import Template

from pylib import fmt
from pylib import esutil

import pandas as pd
import numpy as np


def percentage(a, b):
    if b == 0:
        return math.nan
    return round(100*float(a)/float(b), 2)


def read_es(es, index, query):
    scroller = esutil.initscroll(es, index, query)
    docs = esutil.iterdocs(es, scroller)
    return pd.DataFrame(docs)


def pick_col(df, column_aliases):
    # return the first column from column_aliases that is 
    # preset in df
    for col in column_aliases:
        if col in df.columns:
            return col
    return None


def ensure_numeric(df, columns):
    # if given columns are not numeric, it replaces
    # them with numeric ones inline
    for col in columns:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df.dtypes[col]):
            df[col] = pd.to_numeric(df[col])


def retain(df_name, df, **kwargs):
    # retains all rows in df, that have columns
    # with specified values
    # kwarg key is column name
    # kwarg value is list of values
    # if list is empty, ignores it
    for field, values in kwargs.items():
        if len(values) == 0:
            continue
        df = df[df[field].isin(values)]
        print(f"{df_name} remaining after filtering by {field}: {len(df)}")
    return df


def explode_listcol(df, index_col, list_col, target_col):
    if list_col is None or list_col not in df.columns:
        return pd.DataFrame([], columns=[index_col, target_col])
    df = df[[index_col, list_col]]
    df = df[df[list_col].notnull()]
    df = df.set_index(index_col)
    df = df[list_col].apply(pd.Series).stack().reset_index(index_col)
    df.rename(columns={0: target_col}, inplace=True)
    return df


def explode_jsoncol(df, json_col):
    # explodes the json_column into individual columns
    # returns the new dataframe
    # assumes json is flat object with no depth
    # if json_column does not exist, does nothing
    if json_col not in df.columns:
        return df

    def to_json(s):
        if pd.isnull(s):
            return pd.Series(dtype='float64')
        return pd.Series(json.loads(s))

    t = df[json_col].apply(to_json)
    return pd.concat([df.drop([json_col], axis=1), t], axis=1)


class HTML:
    def __init__(self, title):
        self.html = ''
        self.ireport = 0
        self.add_template('''
        <html>
        <head lang="en">
            <meta charset="UTF-8">
            <title>{{title}}</title>
            <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.24/css/jquery.dataTables.css">
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.js"></script>
            <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/plug-ins/1.10.24/sorting/file-size.js"></script>
            <script type="text/javascript" charset="utf8" src="https://cdn.datatables.net/plug-ins/1.10.24/sorting/time-elapsed-dhms.js"></script>
        </head>
        <body style="font-family: monospace">
        ''', title=title)

    def add_template(self, template, **variables):
        from jinja2 import Environment, BaseLoader
        t = Environment(loader=BaseLoader()).from_string(template)
        self.html += t.render(**variables)

    def add_anchor(self, name):
        self.add_template('<a name="{{name}}"></a>', name=name)

    def add_anchor_links(self, name={}):
        if not name:
            return
        self.add_template('''            
            <style>
                a:link {
                  text-decoration: none;
                }
                a:visited {
                  color: blue;
                  text-decoration: none;
                }
                a:hover {
                  color: green;
                  text-decoration: underline;
                }
                a:active {
                  text-decoration: underline;        
                }
            </style>
             <div style='float: right; margin-right: 5%;'>
             {% for key, value in name.items() %}
             <a href="#{{value}}" style="font-size: 15px;">{{key}}</a><br>
             {% endfor %}
             </div>
        ''', name=name)

    def add_header(self, header):
        self.add_template('<h1 style="padding: 10px; color: #fff; background-color: #343a40">{{header}}</h1>', header=header)

    def add_config_table(self, config={}):
        if not config:
            return
        self.add_template('''
            {% if config %}
            <table>
              {% for key, value in config.items() %}
              <tr><td style="text-align:right;font-weight:bold">{{key}}:  </td><td>&nbsp;&nbsp;{{value}}</td></tr>
              {% endfor %}
            </table>
            <br>
            {% endif %}
            <br>
        ''', config=config)

    def add_table_info(self, info):
        self.add_template('<p>{{info}}</p>', info=info)

    def add_data_table(self, df, byte_columns=[], sec_columns=[], msec_columns=[]):
        self.ireport += 1
        formatters = {col: fmt.bytes for col in byte_columns}
        formatters.update({col: fmt.sec for col in sec_columns})
        formatters.update({col: fmt.msec for col in msec_columns})
        self.add_template('''
            {{table}}
            <script type="text/javascript">
              $(document).ready( function () {
                $('#{{report}}').DataTable({
                 "order": [],
                 columnDefs: [
                   { type: 'file-size', targets: {{byte_columns}} },
                   { type: 'time-elapsed-dhms', targets: {{duration_columns}} },
                   { className: 'dt-body-right', targets: {{numeric_columns}} }
                 ]
              });
            } );
            </script>
            <br>
            ''',
            report=f'report{self.ireport}',
            table=df.to_html(formatters=formatters, escape=False, index=False, justify='center', table_id=f'report{self.ireport}'),
            byte_columns=[df.columns.get_loc(col) for col in byte_columns],
            duration_columns=[df.columns.get_loc(col) for col in sec_columns+msec_columns],
            numeric_columns=[df.columns.get_loc(col) for col in df.columns if pd.api.types.is_numeric_dtype(df.dtypes[col])],
        )

    def add_line_graph(self, fig, path, filename):
        fig_html = fig.to_html(path+filename)
        fig_html_file = open(path+filename, "w")
        fig_html_file.write(fig_html)
        fig_html_file.close()
        graph = '<p align="center"><iframe src="{}" height="500" width="100%"></iframe></p>'.format(filename)
        self.add_template(graph)

    def write_to_file(self, file):
        with open(file, 'w') as f:
            f.write(self.html)
            f.write('</body></html>')


def to_html(file, df, title, header, config={}, byte_columns=[], sec_columns=[], msec_columns=[]):
    html = HTML(title)
    html.add_header(header)
    html.add_config_table(config)
    html.add_data_table(df, byte_columns, sec_columns, msec_columns)
    html.write_to_file(file)


def sparkline(data,  figsize=(4, 0.25), **kwargs):
    import matplotlib.pyplot as plt
    from io import BytesIO
    data = list(data)
    *_, ax = plt.subplots(1, 1, figsize=figsize, **kwargs)
    ax.plot(data)
    ax.fill_between(range(len(data)), data, len(data)*[min(data)], alpha=0.1)
    ax.set_axis_off()
    img = BytesIO()
    plt.savefig(img)
    plt.close()
    return '<img src="data:image/png;base64, {}" />'.format(base64.b64encode(img.getvalue()).decode())

