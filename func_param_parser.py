import re


def extract_string_and_following(input_string):
    pattern = r'(.+?)\s*(\(.*)'
    match = re.search(pattern, input_string)

    if match:
        extracted_string = match.group(1).strip()
        following_content = match.group(2)
        return extracted_string, following_content
    else:
        return None


# Test cases
string1 = "abc (unique count :: xxx_eeke (3232)djdjd)"
result1 = extract_string_and_following(string1)
if result1:
    extracted, following = result1
    print(f"Extracted string: {extracted}")
    print(f"Following content: {following}")

string2 = "some text xyz (another string :: abc (1234) def)"
result2 = extract_string_and_following(string2)
if result2:
    extracted, following = result2
    print(f"Extracted string: {extracted}")
    print(f"Following content: {following}")
