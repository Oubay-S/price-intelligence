import os
import json
import sys

# Forcer l'encodage UTF-8 pour la console Windows afin d'éviter les erreurs avec les emojis
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def merge_json_files(base_path, output_file):
    all_data = []
    
    # Loop through all folders in scrapers (jumia, sport-direct, ebay)
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Path structure: scrapers/[store]/[category]
                        path_parts = root.split(os.sep)
                        store = path_parts[1] if len(path_parts) > 1 else "unknown"
                        category = path_parts[2] if len(path_parts) > 2 else "general"
                        
                        for item in data:
                            # Super-Sanitize: Force all values to clean strings and remove hidden newlines
                            clean_item = {
                                str(k): str(v).replace('\n', ' ').replace('\r', ' ') if v is not None else "" 
                                for k, v in item.items()
                            }
                            clean_item['store'] = store
                            clean_item['category'] = category
                            all_data.append(clean_item)
                        # all_data.extend(data) - replaced by append loop above
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    # Write as JSONL (One JSON object per line - Best for BigQuery)
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in all_data:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✅ Success! Merged {len(all_data)} products into {output_file} (JSONL format)")


if __name__ == "__main__":
    merge_json_files('scrapers', 'upload_to_bq.json')
