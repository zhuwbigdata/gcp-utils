import re
import os
import sys
import logging

logger = logging.getLogger('unravel')

if 'UNRAVEL_PROPS' not in os.environ:
    logger.error('UNRAVEL_PROPS environment variable is not set')
    sys.exit(1) 

file = os.environ['UNRAVEL_PROPS']
if not os.path.exists(file):
    logger.error(f'{file} does not exist'),
    sys.exit(1)

props = {}
with open(file) as f:
    for line in f.readlines():
        line = line.strip()
        if line.startswith('#'):
            continue
        m = re.search('(.+?)=(.+)', line)
        if m:
            props[m.group(1).strip()] = m.group(2).strip()


def get(key, default=None):
    return props.get(key, default)


def integer(key, default=None):
    value = get(key, None)
    if value:
        return int(value)
    return default


def boolean(key, default=None):
    value = get(key, None)
    if value:
        return value=='true'
    return default


def smtp_host():
    return get('mail.smtp.host')


def smtp_port():
    return integer('mail.smtp.port')


def smtp_username():
    return get('mail.smtp.user')


def smtp_password():
    return get('mail.smtp.pw')


def smtp_fromaddrs():
    return [s.strip() for s in get('mail.smtp.from','').split(',')]


def es_url():
    return get('com.unraveldata.elasticsearch.url')


def unravel_url():
    return get('com.unraveldata.advertised.url')


def advertised_host():
    return get('unravel.host.name')


def lr_url():
    host = get('unravel.lr.host.name')
    port = get('unravel.lr.host.port')
    return str(host) + ':' + str(port)
