import re
from typing import Dict, List, Tuple

class SQLCTEReplaceError(Exception):
    pass

def _strip_trailing_semicolon(s: str) -> Tuple[str, bool]:
    s = s.rstrip()
    had = s.endswith(";")
    return (s[:-1].rstrip() if had else s, had)

def _find_kw(text: str, kw: str, start: int = 0) -> int:
    """Case-insensitive find of a keyword token starting at or after 'start'."""
    m = re.search(rf"\b{re.escape(kw)}\b", text[start:], flags=re.IGNORECASE)
    return -1 if not m else start + m.start()

def _skip_ws(text: str, i: int) -> int:
    while i < len(text) and text[i].isspace():
        i += 1
    return i

def _read_ident_or_quoted(text: str, i: int) -> Tuple[str, int]:
    """
    Read an identifier or a quoted identifier ("x" or [x] or `x`), returns value + new index.
    Handles simple quoting styles common across engines.
    """
    i = _skip_ws(text, i)
    if i >= len(text):
        return "", i
    ch = text[i]
    if ch in '"`[':
        quote = ']' if ch == '[' else ch
        i += 1
        start = i
        while i < len(text):
            if text[i] == quote:
                # Handle doubled quote escaping for " and `
                if quote in '"`' and i + 1 < len(text) and text[i + 1] == quote:
                    i += 2
                    continue
                val = text[start:i]
                i += 1
                return val, i
            i += 1
        raise SQLCTEReplaceError("Unterminated quoted identifier in CTE name.")
    # bare identifier (allow dots for schemas? not typical for CTE name—accept simple)
    m = re.match(r"[A-Za-z_][A-Za-z0-9_$]*", text[i:])
    if not m:
        raise SQLCTEReplaceError(f"Expected identifier at position {i}.")
    val = m.group(0)
    i += len(val)
    return val, i

def _read_until_matching_paren(text: str, i: int) -> Tuple[str, int]:
    """
    Starting with text[i] == '(', return content inside balanced parentheses and index after ')'.
    Supports nested parentheses and strings (single/double quotes).
    """
    i = _skip_ws(text, i)
    if i >= len(text) or text[i] != '(':
        raise SQLCTEReplaceError("Expected '(' for CTE body.")
    depth = 0
    start = i + 1
    i += 1
    in_str = None
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == in_str:
                # handle escaped quotes by doubling (SQL style) or backslash
                if i + 1 < len(text) and text[i + 1] == in_str:
                    i += 2
                    continue
                in_str = None
            elif ch == '\\':  # tolerate backslash-escapes inside strings
                i += 2
                continue
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            i += 1
            continue
        if ch == '(':
            depth += 1
        elif ch == ')':
            if depth == 0:
                # content is between start and i
                return text[start:i], i + 1
            depth -= 1
        i += 1
    raise SQLCTEReplaceError("Unbalanced parentheses in CTE body.")

def _parse_cte_headers(sql: str, with_pos: int) -> Tuple[List[Tuple[str, str]], int]:
    """
    Parse the WITH list starting at with_pos ('WITH' already located).
    Returns:
      - list of (header_text, cte_name) in order where header_text is like 'cte(col1, col2)'
      - index where the WITH-clause ends (start of main query)
    """
    i = with_pos
    # consume 'WITH' (possibly 'WITH RECURSIVE')
    m = re.match(r"(?is)\s*WITH\s+(RECURSIVE\s+)?", sql[i:])
    if not m:
        raise SQLCTEReplaceError("Could not parse WITH.")
    i += m.end()
    headers: List[Tuple[str, str]] = []

    while True:
        i = _skip_ws(sql, i)
        # read CTE name (identifier or quoted)
        cte_name, i2 = _read_ident_or_quoted(sql, i)
        i = _skip_ws(sql, i2)

        header_start = i2  # after name
        # optional column list
        if i < len(sql) and sql[i] == '(':
            # find matching )
            cols, i_after_cols = _read_until_matching_paren(sql, i)
            i = _skip_ws(sql, i_after_cols)
            header_text = sql[i2:i_after_cols]  # includes "(...)"
        else:
            header_text = sql[i2:_skip_ws(sql, i)]

        # expect AS
        as_pos = _find_kw(sql, "AS", i)
        if as_pos < 0:
            raise SQLCTEReplaceError("Expected AS in CTE header.")
        # move to '(' after AS
        i = _skip_ws(sql, as_pos + 2)
        body, i_after = _read_until_matching_paren(sql, i)
        i = _skip_ws(sql, i_after)

        full_header_text = (cte_name + header_text[len(cte_name):]).strip()  # preserves optional (cols)
        headers.append((full_header_text, cte_name))

        # If next non-ws is a comma, continue to next CTE; otherwise break (WITH list done)
        if i < len(sql) and sql[i] == ',':
            i += 1
            continue
        break

    return headers, i

def replace_cte_and_main(sql: str, replacements: Dict[str, str]) -> str:
    """
    Replace each CTE body and the main query with provided SQL strings.
    replacements must include all CTE names (case-insensitive) present in 'sql' and 'main_query'.
    """
    if not isinstance(sql, str) or not isinstance(replacements, dict):
        raise SQLCTEReplaceError("Provide a SQL string and a dict of replacements.")

    sql0, had_semicolon = _strip_trailing_semicolon(sql)

    # Locate WITH (if any)
    with_pos = _find_kw(sql0, "WITH", 0)
    output_parts: List[str] = []

    if with_pos >= 0:
        headers, end_with_idx = _parse_cte_headers(sql0, with_pos)
        # Build WITH clause with replaced bodies
        output_parts.append(sql0[:with_pos])  # prefix before WITH (e.g., comments)
        output_parts.append("WITH ")

        rep_keys = {k.lower(): v for k, v in replacements.items()}
        new_ctes = []
        for header_text, cte_name in headers:
            key = cte_name.lower()
            if key not in rep_keys:
                raise SQLCTEReplaceError(f"Missing replacement for CTE '{cte_name}'.")
            body_sql = rep_keys[key].strip()
            new_ctes.append(f"{header_text} AS (\n{body_sql}\n)")
        output_parts.append(",\n".join(new_ctes))
        output_parts.append("\n")

        # Replace main query
        if "main_query" not in rep_keys:
            raise SQLCTEReplaceError("Missing 'main_query' in replacements.")
        output_parts.append(rep_keys["main_query"].strip())
    else:
        # No CTEs; just replace main query
        rep_keys = {k.lower(): v for k, v in replacements.items()}
        if "main_query" not in rep_keys:
            raise SQLCTEReplaceError("Missing 'main_query' in replacements.")
        output_parts.append(rep_keys["main_query"].strip())

    result = "".join(output_parts)
    return result + (";" if had_semicolon else "")

# -----------------------
# Example
# -----------------------
if __name__ == "__main__":
    original_sql = """
    WITH cte1 AS (
      SELECT 1 AS a
    ), cte2(x, y) AS (
      SELECT 2, 3
    )
    SELECT * FROM cte1 JOIN cte2 ON cte1.a = cte2.x;
    """

    replacements = {
        "cte1": "SELECT client_id, acct_num FROM membership",
        "cte2": "SELECT client_id, acct_num FROM pharmacy",
        "main_query": "SELECT c1.client_id FROM cte1 c1 JOIN cte2 c2 ON c1.client_id = c2.client_id"
    }

    print(replace_cte_and_main(original_sql, replacements))
