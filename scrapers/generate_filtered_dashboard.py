import os
import json
import datetime
from google.cloud import bigtable

# Set emulator environment variable

def main():
    print("🚀 Connecting to Bigtable Emulator...")
    
    all_products = []
    all_keys = set()
    
    try:
        client = bigtable.Client(project='test-project', admin=True)
        instance = client.instance('test-instance')
        table = instance.table('products')
        
        rows = table.read_rows()
        
        row_count = 0
        for row in rows:
            row_count += 1
            latest_data = {}
            history_data = [] 
            
            for cf, cols in row.cells.items():
                for col_name, cells in cols.items():
                    key = col_name.decode('utf-8')
                    all_keys.add(key)
                    
                    latest_val = cells[0].value.decode('utf-8')
                    latest_data[key] = latest_val
                    
                    if key == 'current_price':
                        for cell in cells:
                            history_data.append({
                                'date': cell.timestamp.isoformat(),
                                'price': cell.value.decode('utf-8')
                            })
            
            latest_data['full_history'] = history_data
            latest_data['history_count'] = len(history_data)
            all_products.append(latest_data)

        if not all_products:
            print("⚠️ No data found in Bigtable. Run load_all_to_bigtable.py first!")
            return

        print(f"✨ Successfully loaded {len(all_products)} products from Bigtable.")
        
    except Exception as e:
        print(f"❌ Bigtable Error: {e}")
        return

    # Organize Columns
    priority = ['source', 'category', 'image_url', 'name', 'current_price', 'price_before_discount', 'discount', 'stars', 'availability', 'sizes', 'features', 'product_url', 'scraped_at', 'history']
    columns = [p for p in priority if p in all_keys or p == 'history']
    for k in sorted(all_keys):
        if k not in columns and k not in ['full_history', 'history_count']:
            columns.append(k)

    # Generate HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8"><title>Bigtable Inventory Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;800&display=swap" rel="stylesheet">
        <style>
            :root {{ 
                --bg: #0B0F19; 
                --card: rgba(255,255,255,0.03); 
                --accent: #3B82F6; 
                --text: #E2E8F0; 
                --muted: #94A3B8;
            }}
            body {{ background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; padding: 40px; margin:0; }}
            h1 {{ margin-bottom: 30px; font-weight: 800; font-size: 2.5rem; }}
            .card {{ 
                background: var(--card); border: 1px solid rgba(255,255,255,0.1); border-radius: 24px; 
                padding: 30px; overflow-x: auto; backdrop-filter: blur(10px);
            }}
            table {{ width: 100%; border-collapse: collapse; white-space: nowrap; }}
            th {{ text-align: left; color: var(--muted); font-size: 0.75rem; padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); text-transform: uppercase; }}
            td {{ padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.02); vertical-align: middle; }}
            tr:hover td {{ background: rgba(255,255,255,0.02); }}
            
            .price {{ color: #4ADE80; font-weight: bold; font-size: 1.1rem; }}
            .badge {{ background: rgba(59,130,246,0.1); color: #60A5FA; padding: 5px 12px; border-radius: 20px; font-size: 0.7rem; font-weight: 600; border: 1px solid rgba(59,130,246,0.2); }}
            
            .btn-link {{ 
                display: inline-block; padding: 8px 16px; background: var(--accent); color: white; 
                text-decoration: none; border-radius: 8px; font-size: 0.8rem; font-weight: bold; 
                transition: transform 0.2s, background 0.2s;
            }}
            .btn-link:hover {{ background: #2563EB; transform: translateY(-1px); }}
            
            .btn-history {{ 
                background: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.1); 
                padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 0.75rem; 
            }}
            .btn-history:hover {{ background: rgba(255,255,255,0.1); }}
            
            .product-img {{ width: 50px; height: 50px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); }}
        </style>
    </head>
    <body>
        <div style="max-width: 1600px; margin: 0 auto;">
            <h1>Pulse Dashboard <small style="font-size: 1rem; color: var(--muted); font-weight: 400;">(Bigtable Edition)</small></h1>
            <div class="card">
                <table>
                    <thead><tr>{"".join(f"<th>{c.replace('_',' ')}</th>" for c in columns)}</tr></thead>
                    <tbody>
    """

    for p in all_products:
        html_content += "<tr>"
        currency = "MAD"
        for col in columns:
            val = p.get(col, "-")
            if col == 'history':
                hist_json = json.dumps(p["full_history"])
                display = f'<button class="btn-history" onclick=\'alert("Price History for {p.get("name")}\\n" + JSON.stringify({hist_json}, null, 2).replace(/\"/g, " "))\'>History ({p["history_count"]})</button>'
            elif col == 'image_url' and val != "-":
                display = f'<img src="{val}" class="product-img" onerror="this.src=\'https://via.placeholder.com/50\'">'
            elif col == 'product_url' and val != "-":
                display = f'<a href="{val}" target="_blank" class="btn-link">Link</a>'
            elif col == 'current_price' and val != "-":
                display = f'<span class="price">{val} <small style="font-weight:400; font-size:0.7em;">{currency}</small></span>'
            elif col == 'source' or col == 'category':
                display = f'<span class="badge">{val}</span>'
            else:
                display = str(val)[:60] + "..." if len(str(val)) > 60 else val
            
            html_content += f"<td>{display}</td>"
        html_content += "</tr>"

    html_content += "</tbody></table></div></div></body></html>"
    
    with open("bigtable_dashboard.html", "w", encoding='utf-8') as f:
        f.write(html_content)
    print("✨ Dashboard successfully updated with 'Link' buttons.")

if __name__ == "__main__":
    main()
