import sys
import json
import hashlib
from google.cloud import bigtable

import os

# Config from environment variables (set by Docker)
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
instance_id = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
table_id = "products"

def main():
    try:
        data = sys.stdin.read()
        if not data:
            return
        
        row_data = json.loads(data)
        
        # Connect to Emulator
        client = bigtable.Client(project=project_id, admin=True)
        instance = client.instance(instance_id)
        table = instance.table(table_id)

        # Smart Source Detection
        url = row_data.get('product_url', '')
        source = "unknown"
        if "ebay.com" in url: source = "ebay"
        elif "walmart.com" in url: source = "walmart"
        elif "jumia" in url: source = "jumia"
        
        # Create a UNIQUE Row Key using the URL hash
        # This prevents collisions!
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        row_key = f"{source}#{url_hash}".encode()
        
        row = table.direct_row(row_key)

        # Map JSON fields
        for key, value in row_data.items():
            # Add the detected source to the data
            row.set_cell("metadata", key.encode(), str(value).encode())
        
        row.set_cell("metadata", b"detected_source", source.encode())

        row.commit()
        # No print here to keep NiFi logs clean, unless there's an error
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
