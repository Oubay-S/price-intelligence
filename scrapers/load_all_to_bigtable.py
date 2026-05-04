import os
import json
import datetime
import re
from google.cloud import bigtable
from google.cloud.bigtable import column_family

# Set emulator environment variable
os.environ["BIGTABLE_EMULATOR_HOST"] = "localhost:8087"

def get_bigtable_table(project_id='test-project', instance_id='test-instance', table_id='products'):
    """Connects to Bigtable and returns the table object, creating it if necessary."""
    try:
        client = bigtable.Client(project=project_id, admin=True)
        instance = client.instance(instance_id)
        table = instance.table(table_id)
        
        # Try to create the table, ignore if it exists
        try:
            table.create()
            print(f"  Table '{table_id}' created.")
        except:
            pass
            
        # Try to create the column family, ignore if it exists
        cf_id = 'info'
        try:
            cf = table.column_family(cf_id, column_family.MaxVersionsGCRule(100))
            cf.create()
            print(f"  Column family '{cf_id}' created.")
        except:
            pass
            
        return table
    except Exception as e:
        print(f"❌ Bigtable Connection Error: {e}")
        return None

def load_file_to_bigtable(table, file_path, store_name):
    """Loads a single JSON file into Bigtable."""
    if not os.path.exists(file_path):
        return 0
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        category = os.path.basename(os.path.dirname(file_path))
        rows_added = 0
        
        for item in data:
            # Row Key: source#category#name_slug
            name_clean = re.sub(r'[^a-zA-Z0-9]', '', item.get('name', 'unknown'))[:50]
            row_key = f"{store_name}#{category}#{name_clean}".encode('utf-8')
            
            row = table.direct_row(row_key)
            
            ts = datetime.datetime.now()
            if 'scraped_at' in item:
                try: ts = datetime.datetime.fromisoformat(item['scraped_at'])
                except: pass
            
            for key, value in item.items():
                if value is None: continue
                row.set_cell('info', key.encode('utf-8'), str(value).encode('utf-8'), timestamp=ts)
            
            row.set_cell('info', b'source', store_name.encode('utf-8'), timestamp=ts)
            row.set_cell('info', b'category', category.encode('utf-8'), timestamp=ts)
            
            row.commit()
            rows_added += 1
            
        return rows_added
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return 0

def load_all():
    print("🚀 Connecting to Bigtable Emulator (localhost:8087)...")
    table = get_bigtable_table()
    if not table:
        return

    total_rows = 0
    for store in ['jumia', 'walmart', 'ebay']:
        if not os.path.exists(store): continue
        
        print(f"Processing store: {store}")
        for root, dirs, files in os.walk(store):
            for file in files:
                if file.endswith('.json'):
                    path = os.path.join(root, file)
                    count = load_file_to_bigtable(table, path, store)
                    total_rows += count
                        
    print(f"✨ Successfully loaded {total_rows} records into Bigtable!")

if __name__ == "__main__":
    load_all()
