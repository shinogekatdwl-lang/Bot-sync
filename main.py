import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()


import os
import re
import time
from curl_cffi import requests

# Récupération des clés d'environnement
SELLAUTH_API_KEY = os.environ.get("SELLAUTH_API_KEY")
SELLAUTH_SHOP_ID = os.environ.get("SELLAUTH_SHOP_ID")
SWIFTLY_URL = "https://swiftly.cx/products"

# Intervalle de vérification en secondes (ex: 60s)
CHECK_INTERVAL = 60

def fetch_swiftly_products():
    """Récupère et filtre les produits depuis Swiftly."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(SWIFTLY_URL, headers=headers, impersonate="chrome110", timeout=15)
        if response.status_code != 200:
            print(f"❌ Erreur Swiftly HTTP {response.status_code}")
            return []
        
        html = response.text
        raw_items = re.findall(r'<div class="product-card">.*?<h3.*?>(.*?)</h3>.*?<span class="price">.*?(\d+[\.,]?\d*).*?</span>', html, re.DOTALL)
        
        products = []
        for title, price in raw_items:
            clean_title = title.strip()
            clean_price = float(price.replace(',', '.'))
            
            # Filtrage des éléments valides
            if clean_price > 0 and len(clean_title) > 2:
                products.append({
                    "name": clean_title,
                    "price": round(clean_price * 2, 2)  # Prix x2
                })
        return products
    except Exception as e:
        print(f"⚠️ Erreur lors du scraping: {e}")
        return []

def push_to_sellauth(product):
    """Met à jour/crée le produit sur SellAuth avec du stock illimité."""
    url = f"https://api.sellauth.com/v1/shops/{SELLAUTH_SHOP_ID}/products"
    headers = {
        "Authorization": f"Bearer {SELLAUTH_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "title": product["name"],
        "description": f"Acheter {product['name']} - Livraison automatique",
        "type": "service",
        "currency": "EUR",
        "visibility": "public",
        "stock": -1,  # Stock illimité
        "variants": [
            {
                "title": "Default",
                "price": product["price"],
                "stock": -1
            }
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        if res.status_code in [200, 201]:
            print(f"✅ Sync réussi: {product['name']} -> {product['price']}€")
        else:
            print(f"❌ Erreur SellAuth ({product['name']}): Status {res.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur de connexion SellAuth: {e}")

def run_loop():
    print("🚀 Bot démarré en boucle continue...")
    while True:
        print("\n🔍 Vérification des stocks Swiftly...")
        products = fetch_swiftly_products()
        print(f"📦 {len(products)} produits valides détectés.")
        
        for prod in products:
            push_to_sellauth(prod)
            
        print(f"⏳ Pause de {CHECK_INTERVAL} secondes avant la prochaine vérification...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_loop()
