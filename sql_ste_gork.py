import re
from collections import OrderedDict

# Define the placeholder used in Requirement 2 and 4
POLICY_PLACEHOLDER = "${POLICY_CTE}"

def extract_ctes(sql_query: str) -> dict:
    """
    Parses a SQL query with CTEs (Common Table Expressions) into a dictionary
    containing CTE definitions and the main query.

    The parsing logic is robust against commas within CTE definitions by relying
    on parenthesis counting to determine the top-level structure.

    Args:
        sql_query: The input SQL string, potentially containing a WITH clause.

    Returns:
        A dictionary where keys are CTE names or 'main_query', and values are
        their respective SQL content.
    """
    # Use OrderedDict to preserve the order of CTEs
    result_queries = OrderedDict()

    # 1. Normalize whitespace and handle comments
    # Remove standard comments for cleaner parsing (single line and multi-line)
    sql_query = re.sub(r'--.*', '', sql_query)
    sql_query = re.sub(r'/\*.*?\*/', '', sql_query, flags=re.DOTALL)
    # Condense multiple spaces/newlines to a single space, then strip
    normalized_sql = re.sub(r'\s+', ' ', sql_query).strip()

    # Check for WITH clause (case insensitive)
    with_match = re.match(r'^WITH\s+', normalized_sql, re.IGNORECASE)
    
    if not with_match:
        # If no WITH clause, the entire query is the main query
        result_queries['main_query'] = normalized_sql
        return dict(result_queries)

    # 2. Extract content after WITH
    content_after_with = normalized_sql[with_match.end():].strip()

    # 3. Handle optional placeholder (${POLICY_CTE})
    if content_after_with.startswith(POLICY_PLACEHOLDER):
        content_after_with = content_after_with[len(POLICY_PLACEHOLDER):].strip()

    # 4. Separate CTE definitions from the Main Query
    
    cte_definitions = content_after_with
    main_query = ''

    # Find the main query by finding the content after the last top-level ')'
    paren_count = 0
    main_query_start_index = -1
    # Iterate backwards to find the closing ')' of the last CTE
    for i in range(len(content_after_with) - 1, -1, -1):
        if content_after_with[i] == ')':
            paren_count += 1
        elif content_after_with[i] == '(':
            paren_count -= 1
        
        # When parenthesis count is zero and we hit the end of the line, 
        # the main query starts here (or immediately after a comma separator)
        if paren_count == 0 and content_after_with[i] == ')':
             # The main query starts right after the closing ')'
            main_query_start_index = i + 1
            break
            
    if main_query_start_index != -1:
        # Check for a separating comma right after the last CTE
        comma_match = re.match(r'\s*,\s*', content_after_with[main_query_start_index:])
        if comma_match:
            main_query_start_index += comma_match.end()

        main_query = content_after_with[main_query_start_index:].strip()
        cte_definitions = content_after_with[:main_query_start_index].strip()
        
        # MODIFICATION: Always add 'main_query' if the separation logic was successful,
        # even if main_query is an empty string (meaning the SQL was incomplete).
        result_queries['main_query'] = main_query
        
        # Remove any trailing comma from CTE definitions if it was meant to separate the last CTE from the main query
        if cte_definitions.endswith(','):
            cte_definitions = cte_definitions[:-1].strip()

    # 5. Parse CTE Definitions (separated by top-level commas)
    cte_parts = []
    current_cte_start = 0
    paren_count = 0
    
    for i in range(len(cte_definitions)):
        char = cte_definitions[i]
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        elif char == ',' and paren_count == 0:
            # Found a top-level comma separator
            cte_parts.append(cte_definitions[current_cte_start:i].strip())
            current_cte_start = i + 1
            
    # Add the last CTE part
    last_part = cte_definitions[current_cte_start:].strip()
    if last_part:
        cte_parts.append(last_part)
        
    # 6. Extract name and SQL for each CTE part
    for part in cte_parts:
        if not part:
            continue

        # Find the 'AS (' pattern (case insensitive)
        as_match = re.search(r'\s+AS\s+\(', part, re.IGNORECASE)
        
        if as_match:
            cte_name = part[:as_match.start()].strip()
            sql_start = as_match.end()
            # End of SQL is the final ')' of this part (the one closing the main AS)
            sql_end = part.rfind(')')
            
            if sql_end > sql_start:
                cte_sql = part[sql_start:sql_end].strip()
                # Store the CTE in the dictionary, preserving order
                result_queries[cte_name] = cte_sql
            # If parsing fails, it's safer to skip the malformed part than crash
                
    return dict(result_queries)


def reconstruct_sql(original_sql: str, updated_queries: dict) -> str:
    """
    Reconstructs the full SQL query from a dictionary of updated CTEs and the 
    main query, ensuring the original placeholder is reinserted if present.

    Args:
        original_sql: The initial SQL query string (used to check for the placeholder).
        updated_queries: The dictionary containing all CTEs and the main query 
                         (e.g., from a modified output of extract_ctes).

    Returns:
        The reconstructed SQL string.
    """
    # 1. Check if the original SQL contained the placeholder (case-sensitive check on placeholder)
    has_placeholder = POLICY_PLACEHOLDER in original_sql

    # 2. Start reconstruction
    reconstructed_sql = "WITH "

    # 3. Re-insert the placeholder if it was present
    if has_placeholder:
        reconstructed_sql += f"{POLICY_PLACEHOLDER} "

    cte_lines = []
    
    # Preserve the order from the dictionary keys
    cte_names = [name for name in updated_queries if name != 'main_query']
    
    for cte_name in cte_names:
        cte_sql = updated_queries[cte_name].strip()
        
        # Format the CTE for better readability in the reconstructed SQL
        # Use an indentation for the SQL content inside the parenthesis
        indented_sql = '\n'.join(['  ' + line for line in cte_sql.splitlines()])
        line = f"{cte_name} AS (\n{indented_sql}\n)"
        cte_lines.append(line)

    # Join CTEs with a comma and newline
    reconstructed_sql += ",\n".join(cte_lines)
    
    # 4. Append the main query
    if 'main_query' in updated_queries:
        main_query = updated_queries['main_query'].strip()
        if cte_lines:
             # Add a separator newline only if CTEs exist
             reconstructed_sql += "\n\n" 
        reconstructed_sql += main_query

    return reconstructed_sql.strip()


# --- Example Usage ---

if __name__ == '__main__':
    # Example SQL with placeholder, comments, and complex CTEs
    original_sql_with_placeholder = """
    WITH ${POLICY_CTE} 
    
    -- This is CTE 1
    CustomerData AS (
        SELECT 
            cust_id, 
            name,
            -- Sub-query inside CTE
            (SELECT max(order_date) FROM orders WHERE customer_id = cust_id) AS last_order_date 
        FROM customers
        WHERE status = 'Active'
    ),
    
    OrderSummary AS (
        SELECT 
            o.customer_id, 
            SUM(o.amount) AS total_sales,
            COUNT(o.order_id) as order_count
        FROM orders o 
        GROUP BY 1
    )
    
    SELECT 
        c.name, 
        s.total_sales, 
        c.last_order_date
    FROM CustomerData c
    JOIN OrderSummary s 
        ON c.cust_id = s.customer_id
    WHERE s.total_sales > 1000
    ORDER BY c.name;
    """

    print("--- 1. ORIGINAL SQL QUERY ---")
    print(original_sql_with_placeholder.strip())
    print("\n" + "="*50 + "\n")

    # 1. Extract CTEs and Main Query
    extracted_queries = extract_ctes(original_sql_with_placeholder)
    
    print("--- 2. EXTRACTED QUERIES DICTIONARY ---")
    import json
    # Use json.dumps for clean printing of the dictionary
    print(json.dumps(extracted_queries, indent=4))
    print("\n" + "="*50 + "\n")

    # 3. Simulate making changes (Requirement 3)
    # The user modifies the dictionary
    updated_queries = extracted_queries.copy()
    
    # Make a change to 'CustomerData'
    updated_queries['CustomerData'] = """
  SELECT 
    cust_id, 
    name
  FROM customers 
  WHERE status = 'Premium' -- CHANGED: Filter to only Premium customers
"""
    # Make a change to 'main_query'
    updated_queries['main_query'] = """
  SELECT 
    name, 
    total_sales
  FROM CustomerData c
  JOIN OrderSummary s 
    ON c.cust_id = s.customer_id
  WHERE s.total_sales > 5000 -- CHANGED: Higher sales threshold
"""

    print("--- 3. UPDATED QUERIES DICTIONARY (Simulated User Change) ---")
    print(json.dumps(updated_queries, indent=4))
    print("\n" + "="*50 + "\n")

    # 4. Reconstruct the SQL (Requirement 4)
    reconstructed_sql = reconstruct_sql(original_sql_with_placeholder, updated_queries)

    print("--- 4. RECONSTRUCTED SQL QUERY (Placeholder Restored) ---")
    print(reconstructed_sql)
    
    # Example 2: Check reconstruction without placeholder
    sql_no_placeholder = """
    WITH FirstCTE AS (SELECT 1 AS num), SecondCTE AS (SELECT num + 1 AS num2 FROM FirstCTE) 
    SELECT num2 FROM SecondCTE;
    """
    print("\n" + "="*50 + "\n")
    print("--- 5. TESTING WITHOUT PLACEHOLDER ---")
    extracted_no_placeholder = extract_ctes(sql_no_placeholder)
    print("Extracted:")
    print(extracted_no_placeholder)
    reconstructed_no_placeholder = reconstruct_sql(sql_no_placeholder, extracted_no_placeholder)
    print("\nReconstructed:")
    print(reconstructed_no_placeholder)
    
