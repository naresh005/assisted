import re
from collections import defaultdict


def find_sql_aliases(sql_query: str) -> dict:
    """
    Parses a complex SQL query to find all table names and CTE names, and maps
    them to the aliases used for them in FROM and JOIN clauses.

    Args:
        sql_query: The input SQL query string.

    Returns:
        A dictionary mapping base names (table/CTE) to a list of their aliases,
        preserving the original case from the query.
    """
    # Dictionary to store {base_name: set_of_aliases}. Using a set ensures uniqueness.
    alias_map = defaultdict(set)

    # 1. Optional: Clean up comments and excessive whitespace
    # This step is no longer used for the regex search, but is a good practice for analysis.
    # Note: We do NOT convert to uppercase here to preserve case during extraction.
    temp_query = re.sub(r'/\*[\s\S]*?\*/', '', sql_query)  # Remove multiline comments
    temp_query = re.sub(r'--.*', '', temp_query)  # Remove single-line comments

    # --- Part 1: Identify CTE names (Base Names) ---
    # Pattern: Captures a word followed by ' AS ('
    # We search against the original query to preserve the CTE name's case.
    cte_name_pattern = re.compile(r'(\w+)\s+AS\s+\(', re.IGNORECASE)

    # Search for all CTE definitions in the query
    for match in cte_name_pattern.finditer(sql_query):
        # The CTE name is the base name itself. It will be referenced later.
        cte_name = match.group(1).strip()
        # Add itself to the map as a recognized base name (case-preserved)
        alias_map[cte_name].add(cte_name)

        # --- Part 2: Identify Table/CTE references and Aliases in FROM/JOIN clauses ---
    # Pattern:
    # 1. Looks for keywords: FROM, JOIN, LEFT JOIN, etc. (non-capturing group)
    # 2. Captures the base name (table or CTE, potentially multi-part like 'schema.table')
    # 3. Optional 'AS' keyword (non-capturing)
    # 4. Captures the alias (the final word after the base name)
    reference_pattern = re.compile(
        r'\b(?:FROM|JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|CROSS\s+JOIN)\b\s+([\w\.]+)(?:\s+AS\s+)?\s*([\w]+)',
        re.IGNORECASE
    )

    # Search for all table/CTE usages in the query.
    # CRITICAL FIX: Searching against the original 'sql_query' preserves the case of
    # the captured groups (base name and alias).
    for match in reference_pattern.finditer(sql_query):
        base_name = match.group(1).strip()
        alias = match.group(2).strip()

        # Only add the alias if it is different from the base name
        if base_name != alias:
            alias_map[base_name].add(alias)

    # Final cleanup and formatting: Convert sets to sorted lists
    # We only return entries where actual aliases (other than the base name itself) were found.
    final_result = {
        name: sorted(list(aliases - {name}))
        for name, aliases in alias_map.items()
        if aliases - {name}  # Only include if there are aliases that aren't the base name
    }

    return final_result


# --- Example of a Complex SQL Query ---
sample_sql_query = """
WITH
  SalesData AS (
    SELECT 
        product_id, 
        sale_date, 
        amount 
    FROM 
        Raw.Sales s  -- Table aliased as 's'
    WHERE 
        sale_date >= '2024-01-01'
  ),
  ProductInfo AS (
    SELECT 
        id, 
        name 
    FROM 
        Catalog.Products AS P  -- Table aliased as 'P' (uppercase alias test)
  )
SELECT
  pi.name AS Product_Name,
  SUM(sd.amount) AS Total_Sales
FROM
  ProductInfo PI  -- CTE aliased as 'PI' (uppercase alias test)
INNER JOIN
  SalesData sd ON PI.id = sd.product_id  -- CTE aliased as 'sd'
LEFT JOIN
  External.Suppliers Sup ON Sup.product_id = PI.id -- Table aliased as 'Sup' (mixed case alias test)
WHERE
  PI.id IS NOT NULL;
"""

# Execute the function with the sample query
aliases = find_sql_aliases(sample_sql_query)

# --- Print Results ---
print("--- SQL Query Alias Extraction ---")
print(f"Query:\n{sample_sql_query}")
print("\nResults:")
if aliases:
    for base_name, alias_list in aliases.items():
        print(f"Base Name: {base_name.ljust(20)} | Aliases: {', '.join(alias_list)}")
else:
    print("No aliases found in FROM/JOIN clauses.")
