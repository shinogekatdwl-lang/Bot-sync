import sys; sys.stdout.reconfigure(line_buffering=True)
import threading
import time
import os
import re
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

SELLAUTH_API_KEY = os.environ.get("SELLAUTH_API_KEY")
SELLAUTH_SHOP_ID = os.environ.get("SELLAUTH_SHOP_ID")
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY")
SWIFTLY_URL = "https://swiftly.cx/products"
CHECK_INTERVAL = 300

def fetch_swiftly_products():
    if not SCRAPERAPI_KEY:
        print("❌ SCRAPERAPI_KEY manquante dans Render")
        return []
        
    proxy_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={SWIFTLY_URL}&render=true"
    try:
        response = requests.get(proxy_url, timeout=60)
        if response.status_code != 200:
            print(f"❌ Erreur Swiftly HTTP {response.status_code}")
            return []
        html = response.text
        raw_items = re.findall(r'<div class="product-card".*?<h3>(.*?)</h3>.*?<span class="price">([\d\.,]+)</span>', html, re.DOTALL)
        products = []
        for title, price in raw_items:
            clean_title = title.strip()
            clean_price = float(price.replace(',', '.'))
            if clean_price > 0 and len(clean_title) > 2:
                products.append({
                    "name": clean_title,
                    "price": round(clean_price * 2, 2)
                })
        return products
    except Exception as e:
        print(f"⚠️ Erreur scraping : {e}")
        return []

def push_to_sellauth(product):
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
        "stock": -1,
        "variants": [{
            "title": "Default",
            "price": product["price"],
            "stock": -1
        }]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            print(f"✅ Produit ajouté : {product['name']}")
        else:
            print(f"⚠️ Erreur SellAuth ({response.status_code}) : {response.text}")
    except Exception as e:
        print(f"⚠️ Erreur réseau SellAuth : {e}")

if __name__ == "__main__":
    while True:
        products = fetch_swiftly_products()
        print(f"🔎 Produits trouvés : {len(products)}")
        for product in products:
            push_to_sellauth(product)
        time.sleep(CHECK_INTERVAL)
