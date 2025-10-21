from collections import OrderedDict
import re

def parse_ctes(sql: str) -> OrderedDict:
    """
    Parse a SQL string that begins with a WITH clause and extract:
      - each CTE: { cte_name: "<cte SQL>" }
      - the trailing main query: { "main_query": "<main SQL>" }
    Returns an OrderedDict preserving the CTE order.

    Notes:
      - Handles WITH or WITH RECURSIVE
      - Handles quoted identifiers "like This", and [square_bracketed] (SQL Server style)
      - Balances parentheses and skips over string literals and comments:
          -- single-line comments: -- ... newline
          -- multi-line comments:  /* ... */
          -- string literals: '...', "..." (for dialects that allow " as string)
      - Assumes one top-level WITH block followed by the main query (common case).
    """
    s = sql
    n = len(s)

    def is_ident_char(ch):
        return ch.isalnum() or ch == '_' or ch == '$'

    # Scanner state
    i = 0
    in_sl_comment = False
    in_ml_comment = False
    in_single = False
    in_double = False

    def advance(k=1):
        nonlocal i
        i += k

    # Find the WITH keyword not inside string/comment
    with_pos = -1
    i = 0
    while i < n:
        ch = s[i]
        nxt = s[i+1] if i+1 < n else ''

        # handle exiting comments/strings
        if in_sl_comment:
            if ch == '\n':
                in_sl_comment = False
            advance(); continue
        if in_ml_comment:
            if ch == '*' and nxt == '/':
                in_ml_comment = False
                advance(2); continue
            advance(); continue
        if in_single:
            if ch == "'" and (i+1 >= n or s[i+1] != "'"):
                in_single = False
                advance(); continue
            # handle escaped single quote '' inside strings
            if ch == "'" and i+1 < n and s[i+1] == "'":
                advance(2); continue
            advance(); continue
        if in_double:
            # treat double quotes as identifier quotes; keep simple
            if ch == '"':
                in_double = False
            advance(); continue

        # enter comments/strings
        if ch == '-' and nxt == '-':
            in_sl_comment = True; advance(2); continue
        if ch == '/' and nxt == '*':
            in_ml_comment = True; advance(2); continue
        if ch == "'":
            in_single = True; advance(); continue
        if ch == '"':
            in_double = True; advance(); continue

        # check for WITH at a token boundary (case-insensitive)
        if (ch.lower() == 'w' and
            s[i:i+4].lower() == 'with' and
            (i == 0 or not is_ident_char(s[i-1])) and
            (i+4 >= n or not is_ident_char(s[i+4]))):
            with_pos = i
            break

        advance()

    # If no WITH found, return just the main query
    if with_pos == -1:
        return OrderedDict([('main_query', s.strip().rstrip(';'))])

    # Move i to just after WITH (and optional RECURSIVE)
    i = with_pos + 4

    # helper to skip whitespace/comments
    def skip_ws_comments():
        nonlocal i, in_sl_comment, in_ml_comment, in_single, in_double
        while i < n:
            ch = s[i]
            nxt = s[i+1] if i+1 < n else ''
            if ch.isspace():
                i += 1
                continue
            if ch == '-' and nxt == '-':
                # single-line comment
                i += 2
                while i < n and s[i] != '\n':
                    i += 1
                continue
            if ch == '/' and nxt == '*':
                # multi-line comment
                i += 2
                while i+1 < n and not (s[i] == '*' and s[i+1] == '/'):
                    i += 1
                i = min(i+2, n)  # consume */
                continue
            break

    skip_ws_comments()

    # Optional RECURSIVE
    if s[i:i+9].lower() == 'recursive' and (i+9 >= n or not is_ident_char(s[i+9])):
        i += 9
        skip_ws_comments()

    # Utility: read an identifier (possibly quoted)
    def read_identifier():
        nonlocal i
        skip_ws_comments()
        if i >= n:
            raise ValueError("Unexpected end of SQL while reading identifier")

        if s[i] == '"':
            i += 1
            start = i
            while i < n and s[i] != '"':
                i += 1
            if i >= n:
                raise ValueError('Unterminated "identifier"')
            ident = s[start:i]
            i += 1
            return ident
        if s[i] == '[':  # SQL Server-style
            i += 1
            start = i
            while i < n and s[i] != ']':
                i += 1
            if i >= n:
                raise ValueError('Unterminated [identifier]')
            ident = s[start:i]
            i += 1
            return ident

        # unquoted identifier
        start = i
        if not (s[i].isalpha() or s[i] == '_' or s[i] == '$'):
            raise ValueError(f"Expected identifier at position {i}")
        i += 1
        while i < n and is_ident_char(s[i]):
            i += 1
        return s[start:i]

    # Utility: expect a keyword (like AS), case-insensitive, at token boundary
    def expect_kw(word):
        nonlocal i
        skip_ws_comments()
        m = re.match(rf'(?i){re.escape(word)}\b', s[i:])
        if not m:
            raise ValueError(f"Expected keyword {word} near position {i}")
        i += m.end()

    # Utility: consume a balanced parenthesized block and return inner text
    def read_parenthesized():
        nonlocal i
        skip_ws_comments()
        if i >= n or s[i] != '(':
            raise ValueError(f"Expected '(' at position {i}")
        i += 1
        start = i
        depth = 1
        in_s = False
        in_d = False
        in_sl = False
        in_ml = False
        while i < n:
            ch = s[i]
            nxt = s[i+1] if i+1 < n else ''
            if in_sl:
                if ch == '\n':
                    in_sl = False
                i += 1
                continue
            if in_ml:
                if ch == '*' and nxt == '/':
                    in_ml = False
                    i += 2
                    continue
                i += 1
                continue
            if in_s:
                if ch == "'" and not (i+1 < n and s[i+1] == "'"):
                    in_s = False
                    i += 1
                    continue
                if ch == "'" and i+1 < n and s[i+1] == "'":
                    i += 2
                    continue
                i += 1
                continue
            if in_d:
                if ch == '"':
                    in_d = False
                i += 1
                continue

            # entering string/comment
            if ch == '-' and nxt == '-':
                in_sl = True; i += 2; continue
            if ch == '/' and nxt == '*':
                in_ml = True; i += 2; continue
            if ch == "'":
                in_s = True; i += 1; continue
            if ch == '"':
                in_d = True; i += 1; continue

            if ch == '(':
                depth += 1; i += 1; continue
            if ch == ')':
                depth -= 1
                if depth == 0:
                    inner = s[start:i]
                    i += 1  # consume ')'
                    return inner
                i += 1
                continue
            i += 1

        raise ValueError("Unbalanced parentheses while reading CTE body")

    # Parse CTE list
    result = OrderedDict()
    while True:
        skip_ws_comments()
        cte_name = read_identifier()

        # Optional column list: cte_name (col1, col2, ...)
        skip_ws_comments()
        if i < n and s[i] == '(':
            _ = read_parenthesized()  # discard; columns not needed for mapping

        # AS keyword (some dialects allow materialized hints; tolerate them)
        skip_ws_comments()
        # Allow optional MATERIALIZED/NOT yet still require AS
        # e.g., "as materialized" or "not materialized as"
        # To keep simple and safe, just expect AS
        expect_kw('AS')

        # Body in parentheses
        body = read_parenthesized().strip()
        # Remove a trailing semicolon inside the CTE body if present (rare)
        if body.endswith(';'):
            body = body[:-1].rstrip()
        result[cte_name] = body

        skip_ws_comments()
        # If next non-space char is a comma, there are more CTEs
        if i < n and s[i] == ',':
            i += 1
            continue
        break

    # The rest is main query
    main = s[i:].strip()
    # Strip a trailing semicolon, but keep inner ones
    if main.endswith(';'):
        main = main[:-1].rstrip()
    result['main_query'] = main
    return result


# -------------------
# Example usage
if __name__ == "__main__":
    example_sql = """
    WITH RECURSIVE cte1 AS (
        SELECT * FROM membership WHERE parent_id IS NULL
    ),
    "CTE 2" (id, name) AS (
        SELECT id, name FROM pharmacy WHERE active = 1
    ),
    [cte_three] AS (
        /* demo */
        SELECT m.id, p.name
        FROM membership m
        JOIN pharmacy p ON p.id = m.pharmacy_id
        -- end cte
    )
    SELECT t1.id, t2.name
    FROM cte1 t1
    JOIN "CTE 2" t2 ON t2.id = t1.id;
    """

    d = parse_ctes(example_sql)
    for k, v in d.items():
        print(f"\n== {k} ==\n{v}\n")
