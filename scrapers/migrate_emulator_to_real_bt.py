import os
import json
from google.cloud import bigtable
from google.api_core.exceptions import AlreadyExists
from google.cloud.bigtable import column_family

EMULATOR_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "price-intel-local")
EMULATOR_INSTANCE = os.environ.get("BIGTABLE_INSTANCE_ID", "price-intel-instance")
TABLE_ID = "products"
CF_ID = "info"

REAL_PROJECT = "price-intelligence-495411"
REAL_INSTANCE = "price-intelligence"
REAL_CREDS_PATH = "/home/omar/price-intelligence/gcp-credentials.json"

def get_real_client():
    if os.path.exists(REAL_CREDS_PATH):
        # We temporarily unset the emulator host to connect to real GCP
        emulator_host = os.environ.pop("BIGTABLE_EMULATOR_HOST", None)
        # Use explicit service account credentials
        # We need to set GOOGLE_APPLICATION_CREDENTIALS for the client to pick it up if from_service_account_json is not used
        # We'll just pass admin=True which relies on default credentials, so we set the env var
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = REAL_CREDS_PATH
        client = bigtable.Client(project=REAL_PROJECT, admin=True)
        # Restore emulator host for the emulator client
        if emulator_host:
            os.environ["BIGTABLE_EMULATOR_HOST"] = emulator_host
        return client
    else:
        raise Exception(f"Credentials not found at {REAL_CREDS_PATH}")

def ensure_real_table(client):
    instance = client.instance(REAL_INSTANCE)
    table = instance.table(TABLE_ID)
    return table

def main():
    # 1. Connect to emulator
    os.environ["BIGTABLE_EMULATOR_HOST"] = "localhost:8086"
    print("Connecting to local Bigtable emulator...")
    emu_client = bigtable.Client(project=EMULATOR_PROJECT, admin=True)
    emu_instance = emu_client.instance(EMULATOR_INSTANCE)
    emu_table = emu_instance.table(TABLE_ID)

    # 2. Read all rows from emulator
    print(f"Reading rows from emulator table {TABLE_ID}...")
    rows = emu_table.read_rows()
    
    rows_data = []
    for row in rows:
        row_key = row.row_key
        cells_dict = {}
        # Iterate over whatever column families are present
        for cf, cols in row.cells.items():
            cf_name = cf.decode('utf-8') if isinstance(cf, bytes) else cf
            if cf_name == CF_ID:
                for col_name, cells in cols.items():
                    # Keep column names and values as bytes if possible, but the API accepts both
                    cells_dict[col_name] = (cells[0].value, cells[0].timestamp)
        if cells_dict:
            rows_data.append((row_key, cells_dict))
    
    print(f"Found {len(rows_data)} rows in emulator.")

    # 3. Connect to real Bigtable
    print(f"Connecting to real Bigtable in project {REAL_PROJECT} (instance {REAL_INSTANCE})...")
    real_client = get_real_client()
    real_table = ensure_real_table(real_client)

    # 4. Write to real Bigtable
    print("Writing rows to real Bigtable...")
    written = 0
    for row_key, cells_dict in rows_data:
        row = real_table.direct_row(row_key)
        for col_name, (val, ts) in cells_dict.items():
            row.set_cell(CF_ID, col_name, val, timestamp=ts)
        row.commit()
        written += 1
        if written % 500 == 0:
            print(f"  Written {written} rows...")

    print(f"Successfully migrated {written} rows to real Bigtable!")

if __name__ == "__main__":
    main()
