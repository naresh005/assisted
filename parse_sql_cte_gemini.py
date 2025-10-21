import re
import pprint

def parse_sql_with_ctes(sql_query: str) -> dict:
    """
    Parses an SQL query containing a WITH clause (CTEs) and extracts the CTEs
    and the final SELECT statement into a dictionary.

    It ignores dynamic placeholders (e.g., ${POLICY_CTE}) that may appear
    within the CTE declaration block.

    The keys in the resulting dictionary will be the CTE names, and 'main_query'
    for the final SELECT statement.

    Args:
        sql_query: The input SQL query string.

    Returns:
        A dictionary mapping CTE names to their query bodies, including the
        'main_query' key for the final SELECT statement. Returns an empty
        dictionary if the input query is empty.
    """
    # 1. Normalize and check for existence
    sql_query = sql_query.strip()
    if not sql_query:
        return {}

    cte_data = {}

    # 2. Check for WITH clause (case-insensitive)
    with_match = re.match(r"\s*WITH\s+", sql_query, re.IGNORECASE)
    
    if not with_match:
        # If no WITH clause, the entire query is the main query
        main_query = sql_query.rstrip(';')
        return {"main_query": main_query}

    # Extract the part of the query after 'WITH '
    # This block contains all CTEs and the main query
    cte_block_and_main_query = sql_query[with_match.end():].strip()
    
    # NEW: Remove placeholders like ${...} from the CTE block before parsing.
    # This ensures that placeholders don't interfere with CTE name extraction.
    placeholder_pattern = r'\$\{[^}]+\}'
    cte_block_and_main_query = re.sub(placeholder_pattern, ' ', cte_block_and_main_query).strip()

    current_pos = 0
    main_query_start_index = -1
    
    # Loop to process CTEs sequentially
    while current_pos < len(cte_block_and_main_query):
        
        # --- 1. Find the CTE name and the 'AS (' structure ---
        # Look for the AS ( pattern to delineate the CTE name from its body
        # Search starts from the current position
        as_match = re.search(r'\s+AS\s+\(', cte_block_and_main_query[current_pos:], re.IGNORECASE)
        
        if not as_match:
            # If 'AS (' is not found, we assume the rest is the main query
            main_query_start_index = current_pos
            break
            
        # Extract the CTE name (from current_pos up to as_match.start())
        cte_name_raw = cte_block_and_main_query[current_pos : current_pos + as_match.start()].strip()
        cte_name = re.sub(r'[,;]$', '', cte_name_raw).strip() # Clean up any trailing comma/semicolon
        
        # Advance current_pos to the opening parenthesis of the CTE body
        current_pos += as_match.start() + as_match.group(0).find('(')
        
        # --- 2. Parse the CTE body using parenthesis counting ---
        current_pos += 1  # Skip the opening '('
        start_of_body = current_pos
        parenthesis_level = 1 # Start with 1, waiting for it to return to 0
        
        while current_pos < len(cte_block_and_main_query):
            char = cte_block_and_main_query[current_pos]
            
            if char == '(':
                parenthesis_level += 1
            elif char == ')':
                parenthesis_level -= 1
                
            current_pos += 1
            
            if parenthesis_level == 0:
                # Found the end of the CTE body
                end_of_body = current_pos - 1
                cte_body = cte_block_and_main_query[start_of_body:end_of_body].strip()
                
                if cte_name:
                    cte_data[cte_name] = cte_body
                
                # --- 3. Check for continuation (,) or main query (no ,) ---
                
                # Skip whitespace after the closing ')'
                while current_pos < len(cte_block_and_main_query) and cte_block_and_main_query[current_pos].isspace():
                    current_pos += 1
                    
                if current_pos < len(cte_block_and_main_query) and cte_block_and_main_query[current_pos] == ',':
                    current_pos += 1 # Skip the comma, ready for next CTE name
                    # Skip whitespace after the comma
                    while current_pos < len(cte_block_and_main_query) and cte_block_and_main_query[current_pos].isspace():
                        current_pos += 1
                    # Break the inner loop to continue the outer loop for the next CTE
                    break 
                else:
                    # No comma found, the rest is the main query
                    main_query_start_index = current_pos
                    current_pos = len(cte_block_and_main_query) # Set to end to stop outer loop
                    break # Break the inner loop
            
        # If we exited the inner loop (e.g., due to EOF) but the level wasn't 0, 
        # it suggests an error, so we stop parsing CTEs.
        if parenthesis_level != 0 and main_query_start_index == -1:
             # The error likely happened in the current CTE body, so the main query
             # starts after the last successfully parsed CTE.
             main_query_start_index = current_pos
             
    # --- 4. Extract and assign the Main Query ---
    main_query = ""
    if main_query_start_index != -1 and main_query_start_index < len(cte_block_and_main_query):
        main_query = cte_block_and_main_query[main_query_start_index:].strip()
        # Remove trailing semicolon if present
        if main_query.endswith(';'):
            main_query = main_query[:-1].strip()
            
    cte_data["main_query"] = main_query
    
    return cte_data


# --- Example Usage ---

# This example includes a placeholder (${POLICY_CTE}) that should be ignored.
sample_sql = """
WITH ${POLICY_CTE}
  RegionalSales AS (
    -- This CTE selects regional sales data
    SELECT
      Region,
      SUM(Revenue) AS TotalRevenue,
      COUNT(DISTINCT CustomerID) AS TotalCustomers
    FROM Sales
    WHERE OrderDate >= '2024-01-01'
    GROUP BY Region
  ),
  TopPerformers AS (
    -- This CTE finds top performers using a subquery and window function
    SELECT
      Region,
      TotalRevenue,
      RANK() OVER (ORDER BY TotalRevenue DESC) AS RevenueRank
    FROM RegionalSales
    WHERE TotalRevenue > 500000
    AND EXISTS (
      SELECT 1 FROM Customers WHERE Status = 'Active'
    )
  )
SELECT 
  Region, 
  TotalRevenue, 
  RevenueRank
FROM 
  TopPerformers
WHERE 
  RevenueRank <= 5
ORDER BY 
  RevenueRank;
"""

simple_sql = "SELECT * FROM users;"

sql_with_single_cte = """
WITH SingleCTE AS (
    SELECT id, name FROM employees WHERE status = 'active'
)
SELECT * FROM SingleCTE;
"""

# Run the examples
parsed_data = parse_sql_with_ctes(sample_sql)
parsed_simple = parse_sql_with_ctes(simple_sql)
parsed_single_cte = parse_sql_with_ctes(sql_with_single_cte)

# Print the results
print("--- Sample SQL Query (with Placeholder) ---")
print(f"Original Query: \n{sample_sql}")
print("Parsed Dictionary:")
pprint.pprint(parsed_data)

print("\n--- Simple SELECT Query ---")
print("Parsed Dictionary:")
pprint.pprint(parsed_simple)

print("\n--- Single CTE Query ---")
print("Parsed Dictionary:")
pprint.pprint(parsed_single_cte)
