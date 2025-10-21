import re


def extract_ctes_to_dict(sql_query):
    """
    Extracts CTEs and the main SELECT query from a SQL query into a dictionary.
    Ignores ${POLICY_CTE} placeholder if present.

    Args:
        sql_query (str): The SQL query containing CTEs and main query.

    Returns:
        tuple: (dict, bool, str) - Dictionary with CTE names and main_query as keys,
               boolean indicating if placeholder was found, and the placeholder string.
    """
    # Normalize the SQL query: remove extra whitespace
    sql_query = ' '.join(sql_query.split()).strip()

    # Check for ${POLICY_CTE} placeholder
    placeholder = None
    has_placeholder = False
    placeholder_pattern = r'with\s+(\${POLICY_CTE})\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+as'
    match = re.match(placeholder_pattern, sql_query, re.IGNORECASE)
    if match:
        placeholder = match.group(1)
        has_placeholder = True
        # Remove placeholder for CTE parsing
        sql_query = re.sub(r'\${POLICY_CTE}\s+', '', sql_query, flags=re.IGNORECASE)

    # Dictionary to store results
    result = {}

    # Regex pattern to match CTEs: WITH cte_name AS ( ... ) optionally followed by comma or main query
    cte_pattern = r'(?:with\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\((.*?)\)(?:,|\s*(?:select|with|$))'

    # Find all CTEs
    cte_matches = re.finditer(cte_pattern, sql_query, re.IGNORECASE | re.DOTALL)

    # Track the end of the last CTE
    last_cte_end = 0

    # Process each CTE
    for match in cte_matches:
        cte_name = match.group(1)
        cte_body = match.group(2).strip()
        result[cte_name] = cte_body
        last_cte_end = match.end()

    # Extract the main query (everything after the last CTE)
    main_query = sql_query[last_cte_end:].strip()
    if main_query.lower().startswith('select'):
        # Clean up any leading commas or whitespace
        main_query = re.sub(r'^\s*,\s*', '', main_query, flags=re.IGNORECASE).strip()
        result['main_query'] = main_query

    return result, has_placeholder, placeholder


def update_sql_with_new_queries(original_sql, updated_queries):
    """
    Updates the original SQL query with modified CTEs and main query from updated_queries.
    Preserves ${POLICY_CTE} placeholder if present.

    Args:
        original_sql (str): The original SQL query.
        updated_queries (dict): Dictionary with updated CTEs and/or main_query.

    Returns:
        str: Updated SQL query with replaced CTEs and main query.
    """
    # Extract CTEs, placeholder info, and normalize original SQL
    query_dict, has_placeholder, placeholder = extract_ctes_to_dict(original_sql)

    # Start building the updated SQL
    updated_sql_parts = []

    # Handle the WITH clause and placeholder
    if query_dict:
        if has_placeholder:
            updated_sql_parts.append(f"WITH {placeholder}")
        else:
            updated_sql_parts.append("WITH")

    # Process each CTE
    cte_list = [(key, value) for key, value in query_dict.items() if key != 'main_query']
    for i, (cte_name, cte_body) in enumerate(cte_list):
        # Use updated query if provided, otherwise use original
        new_cte_body = updated_queries.get(cte_name, cte_body)
        updated_sql_parts.append(f"    {cte_name} AS ({new_cte_body})")
        if i < len(cte_list) - 1:
            updated_sql_parts.append(",")

    # Add the main query
    main_query = updated_queries.get('main_query', query_dict.get('main_query', ''))
    if main_query:
        updated_sql_parts.append(main_query)

    # Join all parts with newlines and proper formatting
    return '\n'.join(updated_sql_parts)


# Example usage
if __name__ == "__main__":
    # Sample SQL query with ${POLICY_CTE} placeholder
    sample_sql = """
    WITH ${POLICY_CTE} cte1 AS (
        SELECT id, name FROM table1 WHERE active = 1
    ),
    cte2 AS (
        SELECT id, count(*) as cnt FROM table2 GROUP BY id
    ),
    cte3 AS (
        SELECT cte1.id, cte1.name, cte2.cnt 
        FROM cte1 
        JOIN cte2 ON cte1.id = cte2.id
    )
    SELECT ${SELECT} cte3.name, cte3.cnt, t3.value 
    FROM cte3 
    JOIN table3 t3 ON cte3.id = t3.id
    WHERE cte3.cnt > 5
    """

    # Extract CTEs and main query
    query_dict, has_placeholder, placeholder = extract_ctes_to_dict(sample_sql)

    # Print extracted dictionary
    print("Extracted Queries:")
    for key, value in query_dict.items():
        print(f"\nKey: {key}")
        print(f"Query:\n{value}")
    print(f"\nHas Placeholder: {has_placeholder}")
    print(f"Placeholder: {placeholder}")

    # Example updated queries (simulating user modifications)
    updated_queries = {
        'cte1': 'SELECT id, name, status FROM table1 WHERE active = 1',
        'main_query': 'SELECT ${SELECT_NO_HCC} cte3.name, cte3.cnt, t3.value, t3.status FROM cte3 JOIN table3 t3 ON cte3.id = t3.id WHERE cte3.cnt > 10'
    }

    # Update the original SQL with new queries
    updated_sql = update_sql_with_new_queries(sample_sql, updated_queries)

    # Print the updated SQL
    print("\nUpdated SQL:")
    print(updated_sql)
