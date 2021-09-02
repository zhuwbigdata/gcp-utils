from defaults import *

unravel_props = '/path/to/unravel.properties'
unravel_java_dir = '/path/to/jre/bin/'

# elasticsearch endpoint
#es_url = 'localhost:4171'

# uncomment to specify elasticsearch credentials
# es_username='admin'
# es_password='secret'

# num docs to get per scroll page from elasticsearch
es_scroll_size = 100

# unrable ui url
#unravel_url = 'http://congo5.unraveldata.com:3000'

# host and port where server listens
listen_host = '0.0.0.0'
listen_port = 8111

# externally resolvable hostname, used in email link
#advertised_host = 'congo5.unraveldata.com'

# uncomment to send email on failure
# smtp_toaddrs = ['admin@unraveldata.com']

# uncomment to override smtp configuration from unravel.properties
# smtp_host = 'smtp.unraveldata.com'
# smtp_port = 25
# smtp_username = 'admin'
# smtp_password = 'secret'
# smtp_ssl = False
# smtp_fromaddrs = ['admin@unraveldata.com']

################ [AST-Extractor] #################

# Unravel LR endpoint
#lr_url = 'http://localhost:4043'


# list of app kinds, for which features needs to be extracted
kinds = ['hive', 'impala']

# directory used to store files needed
data_dir = 'data'

# number of days to look back for apps for initial batch run
num_days = 250

# default parser jar used to extract ast
default_parser = 'hive-query-parser-1.0-SNAPSHOT-jar-with-dependencies.jar'

# specify parser jar for spcific app kind. if no parser is configured
# default_parser will be used
parsers = {
    'hive': 'hive-query-parser-1.0-SNAPSHOT-jar-with-dependencies.jar',
    'impala': 'hive-query-parser-1.0-SNAPSHOT-jar-with-dependencies.jar',
}

# features are extracted on below scheduled interval(seconds)
schedule_interval_sec = 60

# number of seconds to look back of apps since last run time
margin_sec = 5

# number of last runs for which data is retainded in data_dir
num_runs_retain_data = 5
