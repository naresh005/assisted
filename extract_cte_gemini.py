import re
from typing import Dict, Optional

def extract_ctes(sql_query: str) -> Dict[str, str]:
    """
    Extracts Common Table Expressions (CTEs) from a SQL query string.

    This function uses regular expressions to find patterns matching:
    [WITH [RECURSIVE] or ,] CTE_NAME AS (CTE_SQL)

    Note on limitations: A simple regex cannot guarantee correct parsing of
    queries with deeply nested, unbalanced parentheses (e.g., if a subquery
    within the CTE contains unmatched parens in a string literal or comment).

    Args:
        sql_query: The input SQL query string.

    Returns:
        A dictionary where keys are CTE names (str) and values are the
        corresponding CTE SQL definitions (str).
    """

    # --- 1. Pre-process the query ---
    # Remove standard SQL comments (single-line -- and multi-line /* */)
    # Note: This step is crucial for reliable regex matching.
    cleaned_query = re.sub(r'/\*[\s\S]*?\*/', '', sql_query)
    cleaned_query = re.sub(r'--.*', '', cleaned_query)

    # Normalize whitespace (replace newlines/tabs with spaces for easier matching)
    cleaned_query = ' '.join(cleaned_query.split())

    # --- 2. Define the Regex Pattern ---
    # Pattern explanation (using re.IGNORECASE):
    # (?:,\s*|\bWITH\s+RECURSIVE\s*|\bWITH\s*): Non-capturing group matching the start
    #   of a CTE block: a comma, or the 'WITH [RECURSIVE]' keyword.
    # (\w+): Group 1 (CTE Name) - Matches one or more word characters.
    # \s+AS\s*: Matches ' AS '
    # \(([\s\S]*?)\): Group 2 (CTE SQL) - Non-greedily matches all content,
    #   including spaces/newlines, until the closing parenthesis ')' is found.
    # (?=\s*(?:,|$|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bMERGE\b)):
    #   Positive lookahead assertion: ensures the match is immediately followed
    #   by (non-capturing):
    #   - a comma (for the next CTE)
    #   - end of string ($)
    #   - or the start of the main query (SELECT/INSERT/etc.)
    
    CTE_PATTERN = re.compile(
        r"(?:,\s*|\bWITH\s+RECURSIVE\s*|\bWITH\s*)(\w+)\s+AS\s*\(([\s\S]*?)\)(?=\s*(?:,|$|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bMERGE\b))",
        re.IGNORECASE
    )

    # --- 3. Extract and Build Dictionary ---
    cte_dictionary = {}
    
    # Use findall to get all matches. Each match is a tuple (cte_name, cte_sql)
    matches = CTE_PATTERN.findall(cleaned_query)

    for cte_name, cte_sql in matches:
        # The regex sometimes captures leading/trailing spaces in the SQL
        cte_dictionary[cte_name.lower()] = cte_sql.strip()

    return cte_dictionary

# --- Example Usage ---
if __name__ == "__main__":
    sample_query = """
    WITH RECURSIVE
        employee_hierarchy AS (
            SELECT
                employee_id,
                manager_id,
                employee_name
            FROM employees
            WHERE manager_id IS NULL -- Top-level managers
        ),
        monthly_sales AS (
            /* Calculate total revenue for 2024 Q3 */
            SELECT
                customer_id,
                SUM(amount) AS total_revenue
            FROM transactions
            WHERE transaction_date >= '2024-07-01'
            GROUP BY 1
        )
    -- Main query starts here
    SELECT
        t1.employee_name,
        t2.total_revenue
    FROM employee_hierarchy AS t1
    JOIN monthly_sales AS t2 ON t1.employee_id = t2.customer_id
    WHERE t2.total_revenue > 10000;
    """

    print("--- Input SQL Query ---")
    print(sample_query)
    
    ctes = extract_ctes(sample_query)

    print("\n--- Extracted CTEs ---")
    if ctes:
        for name, sql in ctes.items():
            print(f"CTE Name: {name}")
            print(f"CTE SQL:\n{sql}\n{'-'*20}")
    else:
        print("No CTEs found.")
        
    print("\n--- Dictionary Output ---")
    print(ctes)
    
    # Another example with single CTE
    single_cte_query = """
    WITH product_counts AS (
        SELECT category, COUNT(*) as count FROM products GROUP BY category
    )
    SELECT * FROM product_counts WHERE count > 5;
    """
    print("\n--- Single CTE Example ---")
    print(extract_ctes(single_cte_query))
    
    # Example with different casing and structure
    case_query = """
    WiTh item_data As (
        SELECT id, price FROM items
    ),
    FINAL_REPORT AS (
        SELECT item_data.price * 1.1 as final_price from item_data
    )
    SELECT * FROM FINAL_REPORT;
    """
    print("\n--- Case-Insensitive Example ---")
    print(extract_ctes(case_query))
