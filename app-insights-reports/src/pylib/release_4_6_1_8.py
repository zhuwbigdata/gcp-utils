import json
import re
import os

def SqlTooManyPartitionsEvent(row):
    return re.findall(r'<li>    - Table (.+?) has ', row['detail'])

def SqlNonPartitionedTableEvent(row):
    return re.findall(r'<li>    - Table (.+?) was scanned by ', row['detail'])

def SqlNonPrunedPartitionsEvent(row):
    return re.findall(r' partitions of table (.+?)\.', row['detail'])

def SqlUnderestimatedCountOfRowsEvent(row):
    tt = re.search(r'<ul><li>Stale statistics on tables? (.+?) caused large underestimation of rows produced', row['detail']).group(1).split(' and ')
    if len(tt)==2 and tt[0].endswith(', '):
        tmp = tt[0][:-2].split(', ')
        tmp.append(tt[1])
        tt = tmp
    return tt

def SqlCartesianProductEvent(row):
    return re.search(r'<ul><li>This query performed a cartesian product between tables (.+?)</li></ul>', row['detail']).group(1).split(' and ')

def ImpalaTimeBreakdownEvent(row):
    tt = []
    if 'actions' in row:
        actions = row['actions']
        tt.extend(re.findall(r'COMPUTE STATS (.+?);', actions))
        tt.extend(re.findall(r'Consider creating partitions on table (.+?) based on these filter conditions\.', actions))
        tt.extend(re.findall(r'Table (.+?) is in non-columnar format. To improve the efficiency of the table scan consider using a columnar format such as PARQUET or RCFile\.', actions))
        tt.extend(re.findall(r' partitions of table (.+?) were scanned. Consider using a predicate to prune some partitions\.', actions))
    return tt

table_funcs = {
    'SqlTooManyPartitionsEvent': SqlTooManyPartitionsEvent,
    'SqlNonPartitionedTableEvent': SqlNonPartitionedTableEvent,
    'SqlNonPrunedPartitionsEvent': SqlNonPrunedPartitionsEvent,
    'SqlUnderestimatedCountOfRowsEvent': SqlUnderestimatedCountOfRowsEvent,
    'SqlCartesianProductEvent': SqlCartesianProductEvent,
    'ImpalaTimeBreakdownEvent': ImpalaTimeBreakdownEvent,
}

descriptions = {
    'SqlTooManyPartitionsEvent': 'The tables have too many partitions. For each partition additional metadata need to be kept in memory, which can put pressure in the NameNode. To address this issue, consider using a different partitioning scheme for these tables based on frequently used filter conditions',
    'SqlNonPartitionedTableEvent': 'Consider possible partitioning strategies for these tables based on frequently used filter conditions',
    'SqlNonPrunedPartitionsEvent': 'Consider adding a filtering condition to prune some partitions',
    'SqlUnderestimatedCountOfRowsEvent': 'Stale statistics cause large underestimation of rows produced during the query execution. Stale table statistics can cause the optimizer to pick an inefficient query execution plan',
    'SqlCartesianProductEvent': 'This table was referenced by a query doing a cartesian product. Review the query to confirm that the use of CROSS JOIN is intended and justifies the cost. Use other types of joins where join columns are specified whenever possible',
    'ImpalaTooManyFiltersEvent': 'Impala has a maximum limit of 2000 expressions. Consolidate some expressions by replacing repetitive sequences with single operators like IN or BETWEEN',
    'SqlTooManyJoinsEvent': 'Review the query and the schema to see if all these joins are necessary. If queries often involve many joins, consider whether materialized views or schema denormalization would be worth the overhead to address this problem in the long run',
    'SqlNoFilterEvent': 'Queries do not contain any filtering conditions in the WHERE clause. Consider adding filtering conditions in the WHERE clause if appropriate',
    'SqlLargeResultEvent': 'Queries returned a significant number of rows. If only a sample of the result is needed, use LIMIT to return fewer rows and allow the query to terminate early. If a large result is by design, consider writing it to a file if not already done',
    'SqlTooManyGroupByEvent': 'Review the query to see if all these fields are needed. If appropriate, use fewer fields in GROUP BY clause to improve performance',
    'SqlSelectStarEvent': 'SELECT * retrieves all the columns of the table, which might affect the query performance. Review the query to confirm that SELECT * is indeed necessary. If not, specify only the necessary columns',
    'SqlLikeClauseEvent': 'Queries used the case-sensitive LIKE clause and returned 0 rows. Consider using ILIKE for case-insensitive comparison',
    'SqlAggregateSortOrderEvent': 'Aggregate and Sort Operator columns are in different order. Review the query to confirm that this is intended. If appropriate, putting these columns in the same order might improve the query performance',
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
                print("DETAIL:", event.get('detail'))
                print("ACTIONS:", event.get('actions'))
                t = func(event)
                print("TABLES:", t)
                print("----------------")
    print(n, "events found", file=sys.stderr)


