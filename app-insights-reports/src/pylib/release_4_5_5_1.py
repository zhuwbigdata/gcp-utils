import json
import re
import os

def ImpalaUnderestimatedCountOfRowsEvent(row):
    tt = re.search(r'<ul><li>Stale statistics on tables? (.+?) caused large underestimation of rows produced.</li></ul>', row['detail']).group(1).split(' and ') 
    if len(tt)==2 and tt[0].endswith(', '):
        tmp = tt[0][:-2].split(', ')
        tmp.append(tt[1])
        tt = tmp
    return tt

def ImpalaNonColumnarTablesEvent(row):
    return re.findall(r'<li>    - Table (.+?) was scanned in ', row['detail'])

def ImpalaNonPrunedPartitionsEvent(row):
    return re.findall(r' partitions of table (.+?)\.', row['detail'])

def ImpalaTablesMissingStatsEvent(row):
    return re.findall(r'<li>    - (.+?)</li>', row['detail'])

# no data to test
def ImpalaNonPartitionedTableEvent(row):
    return re.findall(r'<li>    - Table (.+?) was scanned by ', row['detail'])

# no data to test
def ImpalaTooManyPartitionsEvent(row):
    return re.findall(r'<li>    - Table (.+?) has ', row['detail'])

table_funcs = {
    'ImpalaUnderestimatedCountOfRowsEvent': ImpalaUnderestimatedCountOfRowsEvent,
    'ImpalaNonColumnarTablesEvent': ImpalaNonColumnarTablesEvent,
    'ImpalaNonPrunedPartitionsEvent': ImpalaNonPrunedPartitionsEvent,
    'ImpalaTablesMissingStatsEvent': ImpalaTablesMissingStatsEvent,
    'ImpalaNonPartitionedTableEvent': ImpalaNonPartitionedTableEvent,
    'ImpalaTooManyPartitionsEvent': ImpalaTooManyPartitionsEvent,
}

descriptions = {
    'ImpalaUnderestimatedCountOfRowsEvent': 'Stale statistics cause large underestimation of rows produced during the query execution. Stale table statistics can cause the optimizer to pick an inefficient query execution plan',
    'ImpalaNonColumnarTablesEvent': 'Reading data from tables with a large number of columns that are stored in non-columnar formats. (e.g. TextFile, SequenceFile, Avro) requires that each record be completely read from disk, even if only a few columns are required. On the other hand, columnar formats, like Parquet, allow reading only the required columns from the disk, which can significantly improve performance. Consider using a columnar format such as Parquet',
    'ImpalaNonPrunedPartitionsEvent': 'Consider adding a filtering condition to prune some partitions',
    'ImpalaTablesMissingStatsEvent': 'Use the COMPUTE STATS statement to gather statistics for these tables',
    'ImpalaNonPartitionedTableEvent': 'Consider possible partitioning strategies for these tables based on frequently used filter conditions',
    'ImpalaTooManyPartitionsEvent': 'The tables have too many partitions. For each partition additional metadata need to be kept in memory, which can put pressure in the NameNode. To address this issue, consider using a different partitioning scheme for these tables based on frequently used filter conditions',
    'ImpalaNoFilterEvent': 'The SQL query does not contain any filtering conditions. Consider adding filtering conditions that will reduce the result set size',
    'ImpalaTooManyJoinsEvent': 'Queries contain too many joins. Consider denormalizing some tables to reduce the number of joins required',
    'ImpalaTooManyFiltersEvent': 'Impala has a maximum limit of 2000 expressions. Consolidate some expressions by replacing repetitive sequences with single operators like IN or BETWEEN',
}

if __name__ == "__main__":
    import sys
    if len(sys.argv)!=3:
        print("args: <file> <event-name>", file=sys.stderr)
        sys.exit(1)    
    file_name, event_name = sys.argv[1], sys.argv[2]
    n = 0
    with open(file_name, 'r') as file:
        for line in file:
            event = json.loads(line)
            if event['eventName']==event_name:
                n += 1
                func = table_funcs.get(event_name)
                detail = event['detail']
                print("DETAIL:", detail)
                t = func(event)
                print("TABLES:", t)
                print("----------------")
    print(n, "events found", file=sys.stderr)

