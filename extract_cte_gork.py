import re

def extract_ctes(sql):
    """
    Extracts Common Table Expressions (CTEs) from an SQL query and returns them as a dictionary.
    
    Args:
    sql (str): The SQL query string.
    
    Returns:
    dict: A dictionary where keys are CTE names and values are the corresponding CTE SQL (including parentheses).
    
    Note: This parser assumes simple CTE names (alphanumeric + underscore), no column lists in CTE definitions,
    and does not handle quoted strings or comments properly (e.g., parentheses inside strings may cause issues).
    For production use, consider a full SQL parser library like sqlparse.
    """
    sql = sql.strip()
    match = re.match(r'(?i)with\s+', sql)
    if not match:
        return {}
    pos = match.end()
    ctes = {}
    while pos < len(sql):
        # Skip whitespace
        while pos < len(sql) and sql[pos].isspace():
            pos += 1
        if pos >= len(sql):
            break
        # Get CTE name: alphanumeric + _
        name_start = pos
        while pos < len(sql) and (sql[pos].isalnum() or sql[pos] == '_'):
            pos += 1
        name = sql[name_start:pos].strip()
        if not name:
            break
        # Skip whitespace
        while pos < len(sql) and sql[pos].isspace():
            pos += 1
        # Expect 'AS'
        as_match = re.match(r'(?i)as\s*', sql[pos:])
        if not as_match:
            raise ValueError("Expected AS after CTE name")
        pos += as_match.end()
        # Expect '('
        if pos >= len(sql) or sql[pos] != '(':
            raise ValueError("Expected ( after AS")
        pos += 1
        # Find matching )
        depth = 1
        subquery_start = pos
        while pos < len(sql) and depth > 0:
            if sql[pos] == '(':
                depth += 1
            elif sql[pos] == ')':
                depth -= 1
            pos += 1
        if depth > 0:
            raise ValueError("Unbalanced parentheses")
        subquery = sql[subquery_start:pos-1].strip()
        ctes[name] = '(' + subquery + ')'
        # Skip whitespace
        while pos < len(sql) and sql[pos].isspace():
            pos += 1
        # If comma, continue
        if pos < len(sql) and sql[pos] == ',':
            pos += 1
        else:
            break
    return ctes
