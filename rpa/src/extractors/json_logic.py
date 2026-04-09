import json

def extract_variables_from_json(data, prefix="", depth=0, max_depth=15):
    """
    Recursive function to flatten nested JSON and extract variables.
    Handles stringified JSON within fields and specifically looks for FASIH media arrays.
    """
    variables = {}
    if depth > max_depth:
        return variables

    if depth == 0:
        print(f"   🐛 [Extractor] Starting extraction. Data type: {type(data)}")

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}{key}"
            
            # Handle FASIH media array pattern: [{"url": "...", "fileName": "..."}]
            if isinstance(value, list) and len(value) > 0:
                # Check if it's a media array
                if isinstance(value[0], dict) and "url" in value[0]:
                    print(f"   ✨ [Extractor] Found Media Array at '{new_key}' (count: {len(value)})")
                    for i, media_item in enumerate(value):
                        media_url = media_item.get("url")
                        if media_url:
                            variables[f"{new_key}_{i}"] = media_url
                    continue
                else:
                    # Regular list
                    variables.update(extract_variables_from_json(value, f"{new_key}__", depth + 1))
            
            elif isinstance(value, dict):
                variables.update(extract_variables_from_json(value, f"{new_key}__", depth + 1))
            
            elif isinstance(value, str):
                # Check if it's a stringified JSON
                if (value.startswith("{") and value.endswith("}")) or (value.startswith("[") and value.endswith("]")):
                    try:
                        inner_data = json.loads(value)
                        variables.update(extract_variables_from_json(inner_data, f"{new_key}__", depth + 1))
                    except:
                        variables[new_key] = value
                else:
                    variables[new_key] = value
            else:
                variables[new_key] = value
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            # NEW: FASIH Specialized array handling (matches Dashboard TS extractVariables logic)
            if isinstance(item, dict) and "dataKey" in item and "answer" in item:
                ans = item["answer"]
                dk = item["dataKey"]
                if isinstance(ans, list) and len(ans) > 0 and isinstance(ans[0], dict) and "url" in ans[0]:
                    print(f"   ✨ [Extractor] Found DataKey Media: '{dk}'")
                    # Exactly match the UI logic (takes first url, maps directly to dataKey)
                    variables[dk] = ans[0]["url"]
                else:
                    variables.update(extract_variables_from_json(item, f"{prefix}{i}__", depth + 1))
            else:
                variables.update(extract_variables_from_json(item, f"{prefix}{i}__", depth + 1))
            
    if depth == 0:
        print(f"   🐛 [Extractor] Finished. Extracted {len(variables)} variables.")
    return variables
