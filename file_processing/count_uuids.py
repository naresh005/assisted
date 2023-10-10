import json
import re
from collections import Counter

# Helper function to recursively search for UUIDs in a JSON structure
def find_uuids(data, uuid_pattern):
    matches = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            matches += find_uuids(key, uuid_pattern) + find_uuids(value, uuid_pattern)
    elif isinstance(data, list):
        for item in data:
            matches += find_uuids(item, uuid_pattern)
    elif isinstance(data, str):
        matches += re.findall(uuid_pattern, data)

    return matches

# Pattern to identify UUIDs
uuid_pattern = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b')

# 1. Read the JSON file
with open('uuids.json', 'r') as f:
    data = json.load(f)

# 2. Extract UUIDs and 3. Count the occurrences
uuids_found = find_uuids(data, uuid_pattern)
uuid_counts = Counter(uuids_found)

# 4. Sort by occurrence count
sorted_uuids = sorted(uuid_counts.items(), key=lambda x: x[1])

# 5. Display the results
for uuid, count in sorted_uuids:
    print(f"{uuid} - {count}")

# Note: Ensure 'uuids.json' is in the same directory as this script or provide the full path.
