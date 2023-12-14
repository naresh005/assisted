def parse_string(text):
  """
  This function parses a string and returns everything between a left parenthesis and a matching right parenthesis.

  Args:
    text: The string to parse.

  Returns:
    The substring between the left and right parentheses, or an empty string if no parentheses are found.
  """
  stack = []
  start_index = None
  for i, char in enumerate(text):
    if char == "(":
      if start_index is None:
        start_index = i
      stack.append(char)
    elif char == ")":
      if not stack:
        return ""
      stack.pop()
      if not stack:
        return text[start_index + 1:i]
  return ""

# Example usage
text1 = "(employee:894)"
text2 = "(kdlsls(dksldks) goal)"
text3 = "no parentheses here"

print(parse_string(text1))
print(parse_string(text2))
print(parse_string(text3))
