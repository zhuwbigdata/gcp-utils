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
import importlib
from datetime import datetime, timezone

import dash
import dash_table as dt
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from pylib import util
from pylib import ioutil
from pylib import fmt
from pylib import dashutil

from config import *
from app import app
from pylib import cron
import scheduler
import repo
from pylib import log
import topkapps_report

logger = logging.getLogger('unravel')
report_types = {
    'topkapps': 'Top-K Apps',
    'impala_resource_pool_analysis': 'Impala Resource Pool Analysis',
}


def dt2str(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z') if dt else None


def alert(msg):
    return dbc.Alert(
        msg,
        is_open=True,
        duration=4000,
        style={'position': 'fixed', 'top': 66, 'right': 10, 'width': 350},
    )


def notify_scheduler():
    if not os.path.exists('scheduler.pid'):
        return
    pid = ioutil.read_file('scheduler.pid')
    try:
        os.kill(int(pid), signal.SIGHUP)
    except:
        pass


def fetch_jobs():
    jobs = []
    for job_file in repo.jobs():
        job = repo.job_details(job_file)
        jobs.append({
            'id': job.name,
            'report_type': report_types.get(job.report_type, job.report_type),
            'enabled': 'yes' if job.enabled else 'no',
            'schedule': job.schedule,
            'last_run_status': job.last_run_status,
            'last_success_run_time': dt2str(job.last_success_run_time),
            'runs': job.num_runs,
        })
    return jobs


def fetch_jobruns(job_name):
    runs = []
    for run_dir in repo.runs(job_name):
        run = repo.run_details(run_dir)
        runs.append({
            'id': run.name,
            'time': dt2str(run.start_time),
            'status': run.status,
            'duration': fmt.duration_sec(run.duration) if run.duration is not None else None,
        })
    return runs


def layout():
    return html.Div([
        dcc.Interval(
            id='jobs-interval',
            interval=5*1000, # in milliseconds
            n_intervals=0
        ),
        html.Br(),
        dbc.Col(html.Div(id='deletejob-confirm', style={'width': 0, 'height': 0})),
        dbc.Col(html.Div(id='deletejob-alert', style={'width': 0, 'height': 0})),
        dbc.Col(html.Div(id='runjob-alert', style={'width': 0, 'height': 0})),
        dbc.Row([
            dbc.Col(html.H3('Reports:')),
            dbc.Col(dbc.Button('New', id='newjob-button', color='success', size='sm'), width='auto'),
            dbc.Col(dbc.Button('Edit', id='editjob-button', color='info', size='sm'), width='auto'),
            dbc.Col(dbc.Button('Run Now', id='runjob-button', color='info', size="sm"), width='auto'),
            dbc.Col(dbc.Button('Delete', id='deletejob-button', color='danger', size='sm'), width='auto'),
        ], form=True),
        dt.DataTable(
            id='jobs',
            columns=[
                {'name': 'Name', 'id': 'id'},
                {'name': 'Report Type', 'id': 'report_type'},
                {'name': 'Enabled', 'id': 'enabled'},
                {'name': 'Schedule', 'id': 'schedule'},
                {'name': 'Last Run Status', 'id': 'last_run_status'},
                {'name': 'Last Successful Run', 'id': 'last_success_run_time'},
                {'name': '#Runs', 'id': 'runs'},
            ],
            data=fetch_jobs(),
            sort_action='native',
            sort_by=[{'column_id':'id', 'direction':'asc'}],
            filter_action='native',
            fill_width=True,
            page_size=5,
            row_selectable='single',
        ),
        html.Br(), html.Br(),
        dbc.Col(html.Div(id='terminate-confirm', style={'width': 0, 'height': 0})),
        dbc.Col(html.Div(id='terminate-alert', style={'width': 0, 'height': 0})),
        dbc.Row([
            dbc.Col(html.H3('Report', id='job-title')),
            dbc.Col(dbc.Button('Terminate', id='terminatejob-button', color='danger', size='sm'), width='auto'),
        ]),
        dbc.Row([
            dbc.Col(
                dt.DataTable(
                    id='jobruns',
                    columns=[
                        {'name': 'Run', 'id': 'id'},
                        {'name': 'Scheduled Time', 'id': 'time'},
                        {'name': 'Status', 'id': 'status'},
                        {'name': 'Duration', 'id': 'duration'},
                    ],
                    sort_action='native',
                    sort_by=[{'column_id':'time', 'direction':'desc'}],
                    filter_action='native',
                    fill_width=True,
                    page_size=10,
                    row_selectable='single',
                )
            ),
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(html.H4('No Run Selected', id='jobrun-title')),
                        dbc.CardBody([
                            html.Div(id='jobrun-files'),
                        ]),
                    ],
                    style={'height': '100%'},
                ),
                width='auto',
            )
        ]),
    ])


###################### [ Job Dialog ] ######################


@app.callback(
    Output('dialogs', 'children'),
    Input('newjob-button', 'n_clicks'),
    Input('editjob-button', 'n_clicks'),
    State('jobs', 'selected_row_ids'),
)
def open_newjob_modal(new_clicks, edit_clicks, jobids):
    invoker = dashutil.invoker()
    job = None
    if invoker=='newjob-button':
        if not new_clicks:
            raise PreventUpdate
    if invoker=='editjob-button':
        if not edit_clicks:
            raise PreventUpdate
        if not jobids:
            return [alert('No Report selected')]
        with open(f'jobs/{jobids[0]}/job.json', 'r') as f:
            job = json.load(f)

    email_to_addrs = None
    email_include_attachments = None
    job_name = None
    if job:
        job_name = jobids[0] if job else None
        email = job.get('notifications', {}).get('email', {})
        email_to_addrs = ','.join(email.get('to_addrs', []))
        email_include_attachments = email.get('include_attachments', False)


    return dbc.Modal(
        [
            dcc.Store(id='job-json', data=job),
            dbc.ModalHeader('Edit Report' if job else 'New Report'),
            dbc.ModalBody([dbc.Form([
                dbc.FormGroup([
                    dbc.Label('Name'),
                    dbc.Input(id='jobname', value=job_name, disabled=bool(job), placeholder='name of the report'),
                    dbc.Tooltip('Name of the Report', target='jobname', placement='bottom-end'),
                ]),
                dbc.FormGroup([
                    dbc.Label('Report Type'),
                    dbc.Select(
                        id='reporttype',
                        options=[{'label': v, 'value': k} for k, v in report_types.items()],
                        value=job['report_type'] if job else 'topkapps',
                    ),
                    dbc.Tooltip(
                        'Top-K Apps: A report that ranks the top K queries '
                        'that contribute the most to io, memory, cpu usage and duration',
                        target='reporttype',
                        placement='bottom-end',
                    ),
                ]),
                dbc.FormGroup([
                    dbc.Label('Schedule'),
                    dbc.InputGroup(
                        [
                            dbc.InputGroupAddon(dbc.Checkbox(
                                id='enabled', checked=job.get('enabled', True) if job else True
                            ), addon_type='prepend'),
                            dbc.Tooltip(
                                'Check to enable scheduling',
                                target='enabled',
                                placement='bottom-end',
                            ),
                            dbc.Input(id='schedule', value=job.get('cron') if job else None),
                            dbc.DropdownMenu(
                                [
                                    dbc.DropdownMenuItem('hourly', id='cron_hourly'),
                                    dbc.DropdownMenuItem('daily', id='cron_daily'),
                                    dbc.DropdownMenuItem('12 hourly', id='cron_12h'),
                                    dbc.DropdownMenuItem('weekly', id='cron_weekly'),
                                    dbc.DropdownMenuItem('monthly', id='cron_monthly'),
                                    dbc.DropdownMenuItem(divider=True),
                                    dbc.DropdownMenuItem('cron expression', id='cron_expr'),
                                ],
                                label='Example', addon_type='prepend'
                            ),
                        ], className='mb-3', size='sm',
                    ),
                ]),
                html.Div(id='schedules', style={'margin-top': 10, 'margin-left': 50}),
                dbc.FormGroup([
                    dbc.Label('Retention'),
                    dbc.InputGroup(
                        [
                            dbc.Input(
                                id='retention', type='number', min=0, step=1,
                                value=job.get('retention_days') if job else None,
                                placeholder='number of days to keep report files',
                            ),
                            dbc.InputGroupAddon("days", addon_type="append"),
                            dbc.Tooltip('Reports older than #days will be purged', target='retention', placement='bottom-end'),
                        ], size="sm",
                    ),
                ]),
                html.Br(),
                dbc.FormGroup([
                    html.H5('Parameters'),
                    html.Div(id='params'),
                ]),
                html.Br(),
                html.H5('Notifications'),
                dbc.FormGroup([
                    dbc.Label('Email To'),
                    dbc.Input(id='email_to_addrs', value=email_to_addrs, placeholder='comma separated emails'),
                    dbc.FormText('leave blank for no email', color='secondary'),
                ]),
                dbc.FormGroup(
                    [
                        dbc.Checkbox(
                            id='email_include_attachments', className='form-check-input',
                            checked=email_include_attachments,
                        ),
                        dbc.Label(
                            'Attach Files to Email',
                            html_for='email_include_attachments',
                            className='form-check-label',
                        ),
                    ],
                    check=True,
                ),
            ])]),
            dbc.ModalFooter(dbc.Row([
                dbc.Col(dbc.Label(id='createjobreply')),
                dbc.Col(dbc.Button("Ok", id='newjob-ok-button', color='primary', size='sm'), width='auto'),
                dbc.Col(dbc.Button("Cancel", id="newjob-cancel-button", color='primary', size="sm"), width='auto'),
            ])),
        ],
        id="newjob-modal",
        scrollable=True,
        is_open=True,
    )
    

@app.callback(
    Output('schedules', 'children'),
    Input('schedule', 'value'),
)
def refresh_schedules(expr):
    if not expr:
        return []
    try:
        import cron
        try:
            iter = cron.new(expr)
        except:
            return dbc.Row(dbc.Col(dbc.Label('invalid schedule expression')))
        return [
            dbc.Row(dbc.Col(dbc.Label('sample run times:', style={'font-weight': 'bold'}))),
            dbc.Row(dbc.Col(dbc.Label(dt2str(iter.get_next(datetime))))),
            dbc.Row(dbc.Col(dbc.Label(dt2str(iter.get_next(datetime))))),
            dbc.Row(dbc.Col(dbc.Label(dt2str(iter.get_next(datetime))))),
            dbc.Row(dbc.Col(dbc.Label(dt2str(iter.get_next(datetime))))),
            dbc.Row(dbc.Col(dbc.Label(dt2str(iter.get_next(datetime))))),
        ]
    except:
        logger.exception('error')


@app.callback(
    Output('schedule', 'value'),
    Input('cron_hourly', 'n_clicks'),
    Input('cron_daily', 'n_clicks'),
    Input('cron_12h', 'n_clicks'),
    Input('cron_weekly', 'n_clicks'),
    Input('cron_monthly', 'n_clicks'),
    Input('cron_expr', 'n_clicks'),
)
def on_cron_example(n1, n2, n3, n4, n5, n6):
    invoker = dashutil.invoker()
    if not invoker:
        raise PreventUpdate
    return {
        'cron_hourly': '@hourly',
        'cron_daily': '@daily',
        'cron_12h': '12h',
        'cron_weekly': '@weekly',
        'cron_monthly': '@monthly',
        'cron_yearly': '@yearly',
        'cron_min': '3m',
        'cron_hour': '3h',
        'cron_day': '3d',
        'cron_expr': '* * * * *',
    }.get(dashutil.invoker())


@app.callback(
    Output('params', 'children'),
    Input('reporttype', 'value'),
    State('job-json', 'data')
)
def refresh_jobparams(value, job):
    module = importlib.import_module(f'{value}_report')
    return module.layout(job['params'] if job else None)


@app.callback(
    Output('createjobreply', 'children'),
    Output('newjob-modal', 'is_open'),
    Input('newjob-ok-button', 'n_clicks'),
    Input('newjob-cancel-button', 'n_clicks'),
    State('newjob-modal', 'is_open'),
    State('newjob-modal', 'children'),
)
def close_newjob_modal(ok_clicks, cancel_clicks, is_open, children):
    invoker = dashutil.invoker()
    if invoker=='newjob-cancel-button':
        return '', not bool(cancel_clicks)
    if not ok_clicks:
        return '', is_open
    try:
        job_name = dashutil.prop(children, 'jobname', 'value')
        if job_name is None:
            raise Exception('name is not specified')
        if not dashutil.prop(children, 'job-json', 'data'):
            if os.path.isdir(f'jobs/{job_name}'):
                raise Exception(f'report {job_name} already exists')
        enabled = bool(dashutil.prop(children, 'enabled', 'checked'))
        job = {'enabled': enabled}
        schedule = dashutil.prop(children, 'schedule', 'value')
        if enabled and not schedule:
            raise Exception('schedule is not specified')
        if schedule:
            cron.new(schedule)
            job['cron'] = schedule

        retention = dashutil.prop(children, 'retention', 'value')
        if retention is None:
            raise Exception('retention is not specified')
        try:
            retention = int(retention)
        except:
            raise Exception('retention must be number')
        if retention<=0:
            raise Exception('retention must be positive number')
        job['retention_days'] = retention

        report_type = dashutil.prop(children, 'reporttype', 'value')
        module = importlib.import_module(f'{report_type}_report')
        params_layout = dashutil.prop(children, 'params', 'children')
        job['report_type'] = report_type
        job['params'] = module.params_from_layout(params_layout)

        job['notifications'] = {}
        email_to_addrs = dashutil.prop(children, 'email_to_addrs', 'value')
        if email_to_addrs:
            job['notifications']['email'] = {
                'to_addrs': [ s.strip() for s in email_to_addrs.split(',')],
                'include_attachments': bool(dashutil.prop(children, 'email_include_attachments', 'checked'))
            }

        ioutil.mkdirs(f'jobs/{job_name}')
        with open(f'jobs/{job_name}/job.json', 'wt') as f:
            json.dump(job, f, indent=4)
        notify_scheduler()
        return f'report {job_name} created successfully', False
    except Exception as ex: 
        logger.exception('error occurred')
        return str(ex), True


###################### [ Hilight Selected Rows ] ######################


def hilight_selected_rows(selRows):
    if selRows is None:
        return dash.no_update
    return [
        {"if": {"filter_query": "{{id}} ={}".format(i)}, 'backgroundColor': '#f0f5ff'}
        for i in selRows
    ]


@app.callback(
    Output("jobs", "style_data_conditional"),
    Input("jobs", "derived_viewport_selected_row_ids"),
)
def style_selected_job_rows(selRows):
    return hilight_selected_rows(selRows)


@app.callback(
    Output("jobruns", "style_data_conditional"),
    Input("jobruns", "derived_viewport_selected_row_ids"),
)
def style_selected_jobrun_rows(selRows):
    return hilight_selected_rows(selRows)


###################### [ Refresh ] ######################


@app.callback(
    Output('jobs', 'data'),
    Input('jobs-interval', 'n_intervals')
)
def refresh_jobs(n_intervals):
    return fetch_jobs()


@app.callback(
    Output('job-title', 'children'),
    Output('jobruns', 'data'),
    Input('jobs', 'selected_row_ids'),
    Input('jobs-interval', 'n_intervals')
)
def refresh_runs(jobids, _):
    if not jobids:
        return 'No Report Selected', []
    return f'Runs of {jobids[0]} Report', fetch_jobruns(jobids[0])


@app.callback(
    Output('jobrun-title', 'children'),
    Output('jobrun-files', 'children'),
    Input('jobruns', 'selected_row_ids'),
    State('jobs', 'selected_row_ids'),
)
def refresh_files(runids, jobids):
    if not runids:
        return 'No Run Selected', []
    folder = f'jobs/{jobids[0]}/{runids[0]}'
    children = []
    def add_link(name, file):
        if not os.path.exists(f'{folder}/{file}'):
            return
        href=f'/files/{jobids[0]}/{runids[0]}/{file}'
        children.append(dbc.Col(dcc.Link(name, href=href, style={'color':'blue'}, target='_blank'), width='auto'))

    for file in sorted(os.listdir(folder)):
        if file.startswith('.'):
            continue
        if file=='job.json' or file=='log.txt':
            continue
        add_link(file, file)
    if not children:
        children.append(html.Label('no files found'))
    children.append(html.Hr())
    add_link('Input Parameters', 'job.json')
    add_link('Log File', 'log.txt')
    return f'Run {runids[0]}', children


###################### [ Run Now ] ######################


@app.callback(
    Output('runjob-alert', 'children'),
    Input('runjob-button', 'n_clicks'),
    State('jobs', 'selected_row_ids'),
)
def run_job(n_clicks, jobids):
    if not n_clicks:
        return []
    if not jobids:
        return [alert('No Report selected')]

    # disable the job
    job_file = f'jobs/{jobids[0]}/job.json'
    run_name = scheduler.run_job(datetime.now(tz=timezone.utc), job_file)
    return [alert(f'Run {run_name} started')]


###################### [ Terminate ] ######################


@app.callback(
    Output('terminate-confirm', 'children'),
    Input('terminatejob-button', 'n_clicks'),
    State('jobruns', 'selected_row_ids'),
    State('jobs', 'selected_row_ids'),
)
def confirm_terminatejobrun(n_clicks, runids, jobids):
    if not n_clicks:
        return []
    if not runids:
        return [alert('No Report-Run selected')]
    try:
        pid = ioutil.read_file(f'jobs/{jobids[0]}/{runids[0]}/.pid')
    except:
        return [alert('Selected Report-Run must be running')]
    return [dcc.ConfirmDialog(
        id='terminate-confirmdlg',
        message=f'Are you sure you want to terminate {jobids[0]}/{runids[0]}?',
        displayed=True,
    )]


@app.callback(
    Output('terminate-alert', 'children'),
    Input('terminate-confirmdlg', 'submit_n_clicks'),
    State('jobruns', 'selected_row_ids'),
    State('jobs', 'selected_row_ids'),
)
def terminate_jobrun(submit_n_clicks, runids, jobids):
    if not submit_n_clicks:
        return []
    if not runids:
        return [alert('No Report-Run selected')]
    try:
        pid = ioutil.read_file(f'jobs/{jobids[0]}/{runids[0]}/.pid')
    except:
        return [alert('Selected Report-Run must be running')]
    try:
        os.kill(int(pid), signal.SIGKILL)
        #ioutil.create_file(f'jobs/{jobids[0]}/{runids[0]}/.killed', '')
        shutil.rmtree(f'jobs/{jobids[0]}/{runids[0]}/.pid', ignore_errors=True)
        return [alert(f'{jobids[0]}/{runids[0]} is terminated')]
    except:
        return [alert('Selected Report-Run must be running')]


###################### [ Delete Job ] ######################


@app.callback(
    Output('deletejob-confirm', 'children'),
    Input('deletejob-button', 'n_clicks'),
    State('jobs', 'selected_row_ids'),
)
def confirm_deletejob(n_clicks, jobids):
    if not n_clicks:
        return []
    if not jobids:
        return [alert('No Report selected')]
    return [dcc.ConfirmDialog(
        id='deletejob-confirmdlg',
        message=f'Are you sure you want to delete job {jobids[0]}?',
        displayed=True,
    )]


@app.callback(
    Output('deletejob-alert', 'children'),
    Input('deletejob-confirmdlg', 'submit_n_clicks'),
    State('jobs', 'selected_row_ids'),
)
def delete_job(submit_n_clicks, jobids):
    if not submit_n_clicks:
        return []
    if not jobids:
        return [alert('No Report selected')]

    # disable the job
    job_file = f'jobs/{jobids[0]}/job.json'
    with open(job_file, 'r') as f:
        job = json.load(f)
    if job.get('enabled', True):
        job['enabled'] = False
        with open(job_file, 'w') as f:
            json.dump(job, f)
        notify_scheduler()

    # terminate running if any
    for run_dir in repo.runs(jobids[0]):
        try:
            pid = ioutil.read_file(f'{run_dir}/.pid')
            os.kill(int(pid), signal.SIGKILL)
            #ioutil.create_file(f'{run_dir}/.killed', '')
            shutil.rmtree(f'{run_dir}/.pid', ignore_errors=True)
        except:
            pass
    shutil.rmtree(f'jobs/{jobids[0]}')
    return [alert(f'Report {jobids[0]} deleted')]
