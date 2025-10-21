import re
from typing import Dict

def parse_sql_ctes(sql: str) -> Dict[str, str]:
    """
    Parse SQL query to extract CTEs and main query into a dictionary.
    
    Args:
        sql: SQL query string containing CTEs
        
    Returns:
        Dictionary with CTE names as keys and their queries as values.
        Main query is stored with key 'main_query'
    """
    # Remove comments and normalize whitespace
    sql = re.sub(r'--[^\n]*', '', sql)  # Remove single-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)  # Remove multi-line comments
    
    result = {}
    
    # Check if query has CTEs
    with_match = re.search(r'\bWITH\b', sql, re.IGNORECASE)
    
    if not with_match:
        # No CTEs, entire query is the main query
        result['main_query'] = sql.strip()
        return result
    
    # Extract the portion after WITH
    after_with = sql[with_match.end():].strip()
    
    # Parse CTEs
    cte_pattern = r'(\w+)\s+AS\s*\('
    position = 0
    cte_list = []
    
    while position < len(after_with):
        match = re.search(cte_pattern, after_with[position:], re.IGNORECASE)
        
        if not match:
            break
            
        cte_name = match.group(1)
        cte_start = position + match.end()
        
        # Find matching closing parenthesis
        paren_count = 1
        i = cte_start
        
        while i < len(after_with) and paren_count > 0:
            if after_with[i] == '(':
                paren_count += 1
            elif after_with[i] == ')':
                paren_count -= 1
            i += 1
        
        cte_end = i - 1
        cte_query = after_with[cte_start:cte_end].strip()
        
        cte_list.append({
            'name': cte_name,
            'query': cte_query,
            'end_pos': position + i
        })
        
        # Check if there's a comma (indicating another CTE) or main query starts
        remaining = after_with[position + i:].strip()
        comma_match = re.match(r'^\s*,', remaining)
        
        if comma_match:
            position = position + i + comma_match.end()
        else:
            # Main query starts here
            position = position + i
            break
    
    # Add CTEs to result dictionary
    for cte in cte_list:
        result[cte['name']] = cte['query']
    
    # Extract main query (everything after the last CTE)
    if cte_list:
        main_query_start = cte_list[-1]['end_pos']
        main_query = after_with[main_query_start:].strip()
        
        # Remove leading comma if present
        main_query = re.sub(r'^\s*,\s*', '', main_query)
    else:
        main_query = after_with
    
    result['main_query'] = main_query.strip()
    
    return result


# Example usage
if __name__ == "__main__":
    sample_sql = """
    WITH sales_cte AS (
        SELECT 
            customer_id,
            SUM(amount) as total_sales
        FROM sales
        WHERE year = 2024
        GROUP BY customer_id
    ),
    customer_cte AS (
        SELECT 
            id,
            name,
            region
        FROM customers
        WHERE status = 'active'
    ),
    filtered_sales AS (
        SELECT 
            s.customer_id,
            s.total_sales,
            c.name
        FROM sales_cte s
        JOIN customer_cte c ON s.customer_id = c.id
        WHERE s.total_sales > 1000
    )
    SELECT 
        name,
        total_sales,
        RANK() OVER (ORDER BY total_sales DESC) as sales_rank
    FROM filtered_sales
    ORDER BY total_sales DESC
    """
    
    result = parse_sql_ctes(sample_sql)
    
    print("Parsed SQL Components:")
    print("=" * 50)
    for key, query in result.items():
        print(f"\n{key}:")
        print("-" * 50)
        print(query)
        print()
