import sys
import json
import hashlib
import argparse
from google.cloud import bigtable
from datetime import datetime
import os

# Config from environment variables (set by Docker)
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
instance_id = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
table_id = "products"

def main():
    parser = argparse.ArgumentParser(description='NiFi to Bigtable Ingestion')
    parser.add_argument('--source', help='Scraping source (ebay, walmart, jumia)')
    parser.add_argument('--category', help='Product category')
    args = parser.parse_args()

    try:
        data = sys.stdin.read()
        if not data:
            return
        
        row_data = json.loads(data)
        
        # Connect to Emulator
        client = bigtable.Client(project=project_id, admin=True)
        instance = client.instance(instance_id)
        table = instance.table(table_id)

        # Use arguments if provided, else try smart detection
        url = row_data.get('product_url', '')
        source = args.source
        if not source:
            if "ebay.com" in url: source = "ebay"
            elif "walmart.com" in url: source = "walmart"
            elif "jumia" in url: source = "jumia"
            else: source = "unknown"
        
        category = args.category or row_data.get('category', 'unknown')
        
        # Create a UNIQUE Row Key using the URL hash
        url_hash = hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()[:10]
        row_key = f"{source}#{url_hash}".encode()
        
        row = table.direct_row(row_key)

        # Map JSON fields
        for key, value in row_data.items():
            row.set_cell("metadata", key.encode(), str(value).encode())
        
        # Add metadata from NiFi
        row.set_cell("metadata", b"detected_source", source.encode())
        row.set_cell("metadata", b"detected_category", category.encode())
        row.set_cell("metadata", b"ingested_at", datetime.utcnow().isoformat().encode())

        row.commit()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
