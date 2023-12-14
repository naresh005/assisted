import re


def extract_funcname_and_arguments(expression):
    pattern = r'(.+?)\s*(\(.*)'
    match = re.search(pattern, expression)

    if match:
        func_name = match.group(1).strip()
        argument_str = match.group(2)
        return func_name, argument_str
    else:
        return None


def trim_argument_str(text):
    """
   Returns:
     function name
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


def parse_action_argument(argument):
    pattern = r"\[([A-Za-z0-9_]+)::([A-Za-z0-9_]+)\]"
    match = re.match(pattern, argument)
    table_name = None
    column_name = None
    if match:
        table_name = match.group(1)
        column_name = match.group(2)

    return table_name, column_name


expression1 = "unique count ( [EMPLOYEE_TBL::EMPLOYEE_ID_1] )"
func_name, arguments_str = extract_funcname_and_arguments(expression1)
print(f"function_name: {func_name}")
print(f"arguments_str: {arguments_str}")

arguments_str = trim_argument_str(arguments_str).strip()

print(f"trimmed argument_str: {arguments_str}")

argument_list = arguments_str.split(",")
print(f"argument_list {argument_list}")

if len(argument_list) == 1:
    table_name, column_name = parse_action_argument(argument_list[0])
    print(f"table_name: {table_name}")
    print(f"column_name: {column_name}")
