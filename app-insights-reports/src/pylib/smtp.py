#!/usr/bin/env python3

import os
import smtplib
import mimetypes
from email.message import EmailMessage

def connect(host, port, username, password, ssl=False, unravel_defaults=False):
    if unravel_defaults:
        from pylib import uprops
        host = host or uprops.smtp_host()
        port = port or uprops.smtp_port()
        username = username or uprops.smtp_username()
        password = password or uprops.smtp_password()
    if ssl:
        server = smtplib.SMTP_SSL(host, port)
    else:
        server = smtplib.SMTP(host, port)

    # identify ourselves, prompting server for supported features
    server.ehlo()

    # If we can encrypt this session, do it
    if server.has_extn('STARTTLS'):
        server.starttls()
        server.ehlo() # reidentify ourselves over TLS connection

    if username and server.has_extn('AUTH'):
        server.login(username, password)

    return server


def create_message(subject, from_addrs, to_addrs, body, html=False, attachments=[]):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = ', '.join(from_addrs)
    msg['To'] = ', '.join(to_addrs)

    subtype = 'html' if html else 'plain'
    if body.startswith('@'):
        with open(body[1:]) as f:
            msg.set_content(f.read(), subtype=subtype)
    else:
        msg.set_content(body, subtype=subtype)

    def attach_file(path):
        ctype, encoding = mimetypes.guess_type(path)   
        if ctype is None or encoding is not None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(path, 'rb') as fp:
            msg.add_attachment(
                fp.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(path)
            )

    for path in attachments:
        if os.path.isfile(path):
            attach_file(path)
        elif os.path.isdir(path):
            for name in os.listdir(path):
                if name.startswith('.'):
                    continue
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    attach_file(filepath)
        else:
            raise Exception(f'{path} is neither file not directory')
    return msg


if __name__=='__main__':
    import argparse
    import uprops

    parser = argparse.ArgumentParser(description='send email')
    parser.add_argument('--host', help='smtp host, required')
    parser.add_argument('--port', help='smtp port', type=int)
    parser.add_argument('--ssl', help='use ssl connection', action='store_true')
    parser.add_argument('--username', help='user name')
    parser.add_argument('--password', help='password')
    parser.add_argument('--subject', help='email subject', required=True)
    parser.add_argument('--from', help='from address, repeatable', action='append', dest='from_addrs', default=[])
    parser.add_argument('--to', help='to address, repeatable', action='append', dest='to_addrs', required=True)
    parser.add_argument('--body', help='email body', required=True)
    parser.add_argument('--html', help='body is html', action='store_true')
    parser.add_argument('--attach', help='attach file or directory', action='append', dest='attachments', default=[])
    args = parser.parse_args()

    msg = create_message(
        subject=args.subject,
        from_addrs=args.from_addrs or uprops.smtp_fromaddrs(),
        to_addrs=args.to_addrs,
        body=args.body,
        html=args.html,
        attachments=args.attachments
    )

    server = connect(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        ssl=args.ssl,
        unravel_defaults=True,
    )

    with server:
        server.send_message(msg)
