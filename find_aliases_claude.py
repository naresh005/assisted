import re
from collections import defaultdict


def extract_aliases_from_sql(sql):
    """
    Extract all aliases used for table names and CTE names in a SQL query.

    Args:
        sql: SQL query string

    Returns:
        Dictionary with table/CTE names as keys and list of aliases as values
    """
    aliases = defaultdict(list)

    # Remove comments
    sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # Extract CTEs
    cte_pattern = r'\bWITH\b\s+(.*?)(?=\bSELECT\b)'
    cte_match = re.search(cte_pattern, sql, re.IGNORECASE | re.DOTALL)

    cte_names = set()
    if cte_match:
        cte_text = cte_match.group(1)
        # Extract individual CTE definitions
        cte_definitions = re.findall(r'(\w+)\s+AS\s*\(', cte_text, re.IGNORECASE)
        cte_names = set(cte_definitions)

    # Pattern to match table references with aliases
    # Matches: table_name [AS] alias
    # Handles: FROM, JOIN, LEFT JOIN, RIGHT JOIN, INNER JOIN, etc.
    table_alias_pattern = r'\b(?:FROM|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'

    matches = re.findall(table_alias_pattern, sql, re.IGNORECASE)

    for table_name, alias in matches:
        # Skip if alias is a SQL keyword that might be misidentified
        sql_keywords = {'ON', 'WHERE', 'AND', 'OR', 'IN', 'EXISTS', 'NOT', 'AS',
                        'SELECT', 'FROM', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER'}
        if alias.upper() not in sql_keywords:
            aliases[table_name].append(alias)

    # Also check for table references without explicit AS keyword
    # Pattern: table_name alias (where alias is not a keyword or parenthesis)
    implicit_alias_pattern = r'\b(?:FROM|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|OUTER\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:[,\s]|WHERE|ON|GROUP|ORDER|HAVING|LIMIT|$)'

    implicit_matches = re.findall(implicit_alias_pattern, sql, re.IGNORECASE)

    for table_name, alias in implicit_matches:
        sql_keywords = {'ON', 'WHERE', 'AND', 'OR', 'IN', 'EXISTS', 'NOT', 'AS',
                        'SELECT', 'FROM', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER',
                        'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'UNION', 'INTERSECT'}
        if alias.upper() not in sql_keywords and alias != table_name:
            if alias not in aliases[table_name]:
                aliases[table_name].append(alias)

    # Remove duplicates while preserving order
    result = {}
    for table, alias_list in aliases.items():
        seen = set()
        unique_aliases = []
        for alias in alias_list:
            if alias not in seen:
                seen.add(alias)
                unique_aliases.append(alias)
        result[table] = unique_aliases

    return dict(result)


# Test with example queries
sql_query = """
WITH member_cte AS (
    SELECT member_id, name, age
    FROM members
),
hcc_data AS (
    SELECT hcc_id, member_id, hcc_code
    FROM hcc_table
)
SELECT 
    m.member_id,
    m.name,
    h.hcc_code,
    d.department_name
FROM member_cte m
INNER JOIN hcc_data h ON m.member_id = h.member_id
LEFT JOIN departments d ON m.department_id = d.department_id
LEFT JOIN employees e ON m.manager_id = e.employee_id
WHERE m.age > 18
"""

print("Example SQL Query:")
print(sql_query)
print("\n" + "=" * 60)
print("Extracted Aliases:")
print("=" * 60)

aliases = extract_aliases_from_sql(sql_query)
for table_name, alias_list in sorted(aliases.items()):
    print(f"{table_name}: {alias_list}")
