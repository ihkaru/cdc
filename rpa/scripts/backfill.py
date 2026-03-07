import os
import json
from sqlalchemy import create_engine, text

# Connect using the RPA container's environment variable
engine = create_engine(os.environ.get("DATABASE_URL", "postgresql://fasih:fasih123@postgres:5432/fasih_dashboard"))

def extract_flat_data(data: dict) -> dict:
    flat = {}
    
    # 1. Base keys (not objects)
    for k, v in data.items():
        if not isinstance(v, (dict, list)):
            if isinstance(v, str) and (v.startswith('{') or v.startswith('[')):
                continue # skip stringified json for root level
            flat[k] = v
            
    # 2. pre_defined_data
    pre_str = data.get("pre_defined_data")
    if pre_str and isinstance(pre_str, str) and pre_str.startswith('{'):
        try:
            pre_obj = json.loads(pre_str)
            for item in pre_obj.get("predata", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
        except:
            pass
            
    # 3. content (answers)
    content = data.get("content")
    if content:
        if isinstance(content, str) and content.startswith('{'):
            try:
                content = json.loads(content)
            except:
                content = {}
        if isinstance(content, dict):
            for item in content.get("data", []):
                if isinstance(item, dict) and "dataKey" in item:
                    flat[item["dataKey"]] = item.get("answer")
                    
    # 4. region_metadata
    region = data.get("region_metadata")
    if isinstance(region, dict):
        for k, v in region.items():
            if not isinstance(v, (dict, list)):
                flat[f"region_{k}"] = v
            elif k == "level" and isinstance(v, list):
                for lvl in v:
                    if isinstance(lvl, dict):
                        flat[f"region_level_{lvl.get('id')}"] = lvl.get("name")
                        
    return flat

def main():
    print("Starting deeply nested backfill for flat_data...")
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, data_json FROM assignments WHERE data_json IS NOT NULL"))
        rows = res.fetchall()
        
        updated = 0
        for row in rows:
            try:
                # data_json is saved as a string in the DB, so we parse it first
                data_string = row[1]
                data = json.loads(data_string) if isinstance(data_string, str) else data_string
                flat = extract_flat_data(data)
                
                conn.execute(
                    text("UPDATE assignments SET flat_data = :flat WHERE id = :id"),
                    {"flat": json.dumps(flat), "id": row[0]}
                )
                updated += 1
            except Exception as e:
                print(f"Error on {row[0]}: {e}")
        
        conn.commit()
        print(f"Backfill complete. Updated {updated} rows with flattened JSON.")

if __name__ == "__main__":
    main()
