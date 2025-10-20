import re

def extract_ctes(sql: str) -> dict[str, str]:
    s = sql
    n = len(s)
    i = 0

    def skip_ws_and_comments(idx: int) -> int:
        while idx < n:
            # whitespace
            while idx < n and s[idx].isspace():
                idx += 1
            # line comment --
            if idx + 1 < n and s[idx] == '-' and s[idx + 1] == '-':
                idx += 2
                while idx < n and s[idx] != '\n':
                    idx += 1
                continue
            # block comment /* ... */
            if idx + 1 < n and s[idx] == '/' and s[idx + 1] == '*':
                idx += 2
                while idx + 1 < n and not (s[idx] == '*' and s[idx + 1] == '/'):
                    idx += 1
                idx = min(n, idx + 2)
                continue
            break
        return idx

    m = re.search(r'\bWITH\b', s, re.IGNORECASE)
    if not m:
        return {}
    i = skip_ws_and_comments(m.end())

    # optional RECURSIVE
    m2 = re.match(r'RECURSIVE\b', s[i:], re.IGNORECASE)
    if m2:
        i += m2.end()

    def parse_identifier(idx: int):
        idx = skip_ws_and_comments(idx)
        if idx >= n:
            return None, idx
        if s[idx] == '"':  # quoted identifier
            idx += 1
            start = idx
            while idx < n:
                if s[idx] == '"':
                    name = s[start:idx]
                    idx += 1
                    return name, idx
                idx += 1
            return None, idx
        if s[idx] == '[':  # [identifier]
            idx += 1
            start = idx
            while idx < n and s[idx] != ']':
                idx += 1
            name = s[start:idx]
            idx = min(n, idx + 1)
            return name, idx
        start = idx
        while idx < n and (s[idx].isalnum() or s[idx] in ('_', '.', '$')):
            idx += 1
        name = s[start:idx]
        if not name:
            return None, idx
        return name, idx

    def parse_parenthesized(idx: int, open_char='(', close_char=')'):
        idx = skip_ws_and_comments(idx)
        if idx >= n or s[idx] != open_char:
            return None, idx
        depth = 0
        start = idx + 1
        idx += 1
        in_single = in_double = in_bracket_ident = False
        while idx < n:
            ch = s[idx]
            # strings / quoted identifiers
            if in_single:
                if ch == "'" and (idx + 1 < n and s[idx + 1] == "'"):
                    idx += 2
                    continue
                if ch == "'":
                    in_single = False
                    idx += 1
                    continue
                idx += 1
                continue
            if in_double:
                if ch == '"' and (idx + 1 < n and s[idx + 1] == '"'):
                    idx += 2
                    continue
                if ch == '"':
                    in_double = False
                    idx += 1
                    continue
                idx += 1
                continue
            if in_bracket_ident:
                if ch == ']':
                    in_bracket_ident = False
                idx += 1
                continue
            if ch == "'":
                in_single = True; idx += 1; continue
            if ch == '"':
                in_double = True; idx += 1; continue
            if ch == '[':
                in_bracket_ident = True; idx += 1; continue

            # comments inside body
            if ch == '-' and idx + 1 < n and s[idx + 1] == '-':
                idx += 2
                while idx < n and s[idx] != '\n':
                    idx += 1
                continue
            if ch == '/' and idx + 1 < n and s[idx + 1] == '*':
                idx += 2
                while idx + 1 < n and not (s[idx] == '*' and s[idx + 1] == '/'):
                    idx += 1
                idx = min(n, idx + 2)
                continue

            if ch == open_char:
                depth += 1; idx += 1; continue
            if ch == close_char:
                if depth == 0:
                    return s[start:idx], idx + 1
                depth -= 1; idx += 1; continue
            idx += 1
        return None, idx

    ctes = {}
    while True:
        name, i = parse_identifier(i)
        if not name:
            break

        # optional column list after CTE name
        tmp = skip_ws_and_comments(i)
        if tmp < n and s[tmp] == '(':
            _, i = parse_parenthesized(tmp, '(', ')')
        else:
            i = tmp

        i = skip_ws_and_comments(i)
        m_as = re.match(r'AS\b', s[i:], re.IGNORECASE)
        if not m_as:
            break
        i += m_as.end()

        body, i = parse_parenthesized(i, '(', ')')
        if body is None:
            break

        ctes[name] = body.strip()

        i = skip_ws_and_comments(i)
        if i < n and s[i] == ',':
            i += 1
            continue
        else:
            break

    return ctes
