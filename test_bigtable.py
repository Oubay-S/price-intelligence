import os
from google.cloud import bigtable
import datetime

# 1. On précise à la librairie qu'on utilise notre conteneur local
os.environ["BIGTABLE_EMULATOR_HOST"] = "localhost:8086"

# 2. Création du client
print("🔌 Connexion à l'émulateur Bigtable local...")
client = bigtable.Client(project="price-intel-local", admin=True)
instance = client.instance("price-intel-instance")
table = instance.table("nutrition_prices")

# 3. Écrire une donnée (comme le ferait Scrapy)
row_key = b"whey-protein-prozis-1kg"
row = table.direct_row(row_key)
row.set_cell(
    column_family_id="product_info",
    column=b"price",
    value=b"29.99",
    timestamp=datetime.datetime.utcnow()
)
row.commit()
print(f"\n🛒 Simulation Scraping : prix détecté à 29.99€")
print(f"✅ Ligne enregistrée dans Bigtable: {row_key.decode()}")

# 4. Lire la donnée pour vérifier (comme le ferait dbt ou Pandas)
read_row = table.read_row(row_key)
if read_row:
    prix_enregistre = read_row.cells["product_info"][b"price"][0].value.decode()
    print(f"🔍 Vérification en base : Le prix de {row_key.decode()} est bien de {prix_enregistre}€")
else:
    print("❌ Ligne non trouvée.")
