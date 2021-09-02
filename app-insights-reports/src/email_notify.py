import os
import logging
from datetime import datetime
from jinja2 import Environment, BaseLoader

from config import *
import repo

from pylib import smtp
os.environ['UNRAVEL_PROPS'] = unravel_props
from pylib import uprops

logger = logging.getLogger('unravel')    
advertised_host = advertised_host or uprops.advertised_host()

t = Environment(loader=BaseLoader()).from_string('''
    <html>
    <body>
        <h1>{{header}}</h1>
        <table>
          {% for key, value in props.items() %}
          <tr><td style="text-align:right;font-weight:bold">{{key}}:  </td><td>{{value}}</td></tr>
          {% endfor %}
          <tr><td style="text-align:right;vertical-align:top;font-weight:bold">files:  </td><td>
          {% for name, url in files.items() %}
          <a href="{{url}}">{{name}}</a><br>
          {% endfor %}
          </td>
        </table>
    </body>
    </html>
''')


def notify(run_dir, to_addrs, include_attachments=True):
    logger.info(f'email.notify run_dir={run_dir}, to_addrs={to_addrs}, include_attchments={include_attachments}')
    server = smtp.connect(
        host=smtp_host,
        port=smtp_port,
        username=smtp_username,
        password=smtp_password,
        ssl=smtp_ssl,
        unravel_defaults=True,
    )

    run = repo.run_details(run_dir)
    if run.status=='failure':
        subject = f'Unravel: report {run.job_name}/{run.name} failed'
    else:
        subject = f'Unravel: report {run.job_name}/{run.name} is ready'
    props = run._asdict()

    files = {}
    for file in os.listdir(run_dir):
        if file.startswith('.'):
            continue
        files[file] = f'http://{advertised_host}:{listen_port}/files/{run.job_name}/{run.name}/{file}'

    msg = smtp.create_message(
        subject = subject,
        from_addrs = smtp_fromaddrs or uprops.smtp_fromaddrs(),
        to_addrs = to_addrs,
        body = t.render(props=props, files=files),
        html=True,
        attachments= [run_dir] if include_attachments else [],
    )

    with server:
        server.send_message(msg)

