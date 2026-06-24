import cloudscraper
from bs4 import BeautifulSoup
import requests
import os

# --- GÜVENLİ AYARLAR ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
JSONBIN_KEY = os.getenv("JSONBIN_MASTER_KEY")
SCRAPER_BIN_ID = os.getenv("SCRAPER_BIN_ID") # Yeni açtığımız kutunun ID'si

URLS = [
    "https://cetatenie.just.ro/ordine-articolul-10/",
    "https://cetatenie.just.ro/ordine-articolul-1-1/"
]

def hafizadan_pdfleri_getir():
    headers = {"X-Master-Key": JSONBIN_KEY}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{SCRAPER_BIN_ID}/latest", headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {}).get("son_pdfler", [])
    except Exception as e:
        print("Hafıza okunamadı:", e)
    return []

def hafizaya_pdfleri_kaydet(pdf_listesi):
    headers = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
    payload = {"son_pdfler": pdf_listesi}
    requests.put(f"https://api.jsonbin.io/v3/b/{SCRAPER_BIN_ID}", json=payload, headers=headers)

def telegrama_mesaj_gonder(mesaj):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": mesaj, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def main():
    print("🔍 Tarama başlatılıyor...")
    # Cloudflare korumasını aşan özel tarayıcı nesnesi
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    suanki_pdfler = []

    for url in URLS:
        print(f"🌐 Bağlanılıyor: {url}")
        try:
            response = scraper.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sayfadaki tüm linkleri bul ve sadece sonu .pdf olanları al
            linkler = soup.find_all('a', href=True)
            for link in linkler:
                href = link['href']
                if href.endswith('.pdf') or '.pdf' in href.lower():
                    # Link tam URL değilse tamamla
                    tam_link = href if href.startswith('http') else f"https://cetatenie.just.ro{href}"
                    suanki_pdfler.append(tam_link)
        except Exception as e:
            print(f"❌ Siteye bağlanırken hata: {e}")

    # Sadece en üstteki 30 PDF'i kontrol etsek yeterli
    suanki_pdfler = suanki_pdfler[:30]
    
    eski_pdfler = hafizadan_pdfleri_getir()
    
    # Eski listede olmayan YENİ PDF'leri tespit et
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    if yeni_pdfler:
        print(f"🚨 {len(yeni_pdfler)} adet YENİ PDF bulundu!")
        
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        # Hafızayı güncelle (Şişmemesi için sadece son 50 PDF'i tutalım)
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    else:
        print("✅ Yeni PDF yok. Sistem güncel.")

if __name__ == "__main__":
    main()