import logging
from collections import defaultdict, namedtuple

import sqlparse

logger = logging.getLogger('unravel')

def get_features(app):
    """
    Extract features from the given query statement
    returns Features namedtuple
    """
    kind, sql = app['kind'], app['queryStringFull']
    keywords, wheres, functions = defaultdict(int), list(), list()
    try:
        stmts = sqlparse.parse(sql)
    except:
        logger.warning(f'failed to sqlparse: {sql}')
        return {}
    for stmt in stmts:
        aggregate_tokens(stmt.tokens, keywords, wheres, functions)
    f = dict(
        num_of_select_clauses = keywords['SELECT'],
        num_of_where_clauses = keywords['WHERE'],
        num_of_joins = sum([v for k, v in keywords.items() if 'JOIN' in k ]),
        num_of_case_statements = keywords['CASE'],
        num_of_functions = len(functions),
        num_of_order_by_clauses = keywords['ORDER BY'],
        num_of_partition_clauses = keywords['PARTITION'],
        num_of_group_by = keywords['GROUP BY'],
        num_of_subqueries = len([v for v in wheres if 'SELECT' in v]),
    )
    # you can extract additional features specific to kind into `f` here
    return f


def aggregate_tokens(tokens: list, keywords: defaultdict, wheres: list, functions: list) -> None:
    """
    extracts keywords, where clauses and functions from given toknes list
    """
    groups = []
    while True:
        for token in tokens:
            cls = token._get_repr_name()
            #if cls not in ['Whitespace', 'Identifier', 'IdentifierList', 'Punctuation', 'Newline', 'Comment']:
            #    print(f'Class: {cls} , Token: {token}')
            if cls in {'Keyword', 'DML', 'DDL'}:
                keywords[str(token).upper()] += 1
            elif cls == 'Function':
                functions.append(str(token).upper())
            elif cls == 'Where':
                wheres.append(str(token).upper())               
            if token.is_group:
                groups.append(token)
        if len(groups)==0:
            return
        tokens = groups[0]
        groups = groups[1:]


if __name__=='__main__':
    import sys
    print(get_features({'kind':'sql', 'queryStringFull':sys.stdin.read()}))
