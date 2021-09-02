#!/usr/bin/env python

import logging
import os
import sys
import glob
import json
import shutil
import signal
import threading
import subprocess
import atexit

import dash
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from pylib import util
from pylib import ioutil
from pylib import dashutil

from config import *
import ast_extractor
from app import app
from pylib import log
import reports_page

ast_extractor.validate_config()

# setup logging
ioutil.mkdirs('logs')
log_handlers = [logging.handlers.RotatingFileHandler('logs/main.log', 'a', 1024 * 1024 * 10, 5)]
if 'DEVELOPMENT' in os.environ:
    log_handlers.append(logging.StreamHandler())
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s |  %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger('unravel')
logger.setLevel(logging.DEBUG)
log.redirect_std()

ioutil.write_pidfile('main.pid')
ioutil.mkdirs('jobs')

app_title = 'App Insights Reports'
app_logo = 'https://www.unraveldata.com/wp-content/themes/unravel/favicon.ico'

if not os.path.exists(unravel_props):
    logger.error(f'{unravel_props} does not exit')
    sys.exit(1)


def app_layout():
    location = dcc.Location(id='url', refresh=False)
    navbar = dbc.Navbar(
        [
            html.A(
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=app_logo, height="30px")),
                        dbc.Col(dbc.NavbarBrand(app_title, className="ml-2")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="/",
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
        ],
        color="dark",
        dark=True,
    )
    page_content = html.Div(id='page-content', style={'margin': 20})
    dialogs = html.Div(id='dialogs')

    return html.Div([location, navbar, page_content, dialogs])


@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
)
def display_page(pathname):
    if pathname == '/':
        return reports_page.layout()
    else:
        return html.H2('Page Not Found')


exiting = threading.Event()
def exiting_vm():
    exiting.set()
    logger.info('exiting')
    for proc in procs:
        logger.info(f'terminating {proc.pid}')
        proc.terminate()
        proc.wait()


atexit.register(exiting_vm)

procs = []
def launch(pyfile):
    while True:
        if exiting.is_set():
            return
        try:
            logger.info(f'starting {pyfile}')
            proc = subprocess.Popen([sys.executable, pyfile], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            procs.append(proc)
            try:
                proc.communicate()
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait()
            return_code = proc.poll()
            procs.remove(proc)
        finally:
            logger.info(f'{pyfile} exited')


threading.Thread(name='scheduler', target=launch, args=('scheduler.py',), daemon=True).start()
threading.Thread(name='ast-extractor', target=launch, args=('ast_extractor.py',), daemon=True).start()

app.title = app_title
app.layout = app_layout
server = app.server

if __name__ == '__main__':
    app.run_server(host=listen_host, port=listen_port)
