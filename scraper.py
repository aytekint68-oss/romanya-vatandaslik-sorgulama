import os
import requests
from bs4 import BeautifulSoup

# --- GÜVENLİ AYARLAR ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
JSONBIN_KEY = os.getenv("JSONBIN_MASTER_KEY")
SCRAPER_BIN_ID = os.getenv("SCRAPER_BIN_ID")
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY") # YENİ GİZLİ SİLAHIMIZ

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
    except Exception:
        pass
    return []

def hafizaya_pdfleri_kaydet(pdf_listesi):
    headers = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
    payload = {"son_pdfler": pdf_listesi}
    requests.put(f"https://api.jsonbin.io/v3/b/{SCRAPER_BIN_ID}", json=payload, headers=headers)

def telegrama_mesaj_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": mesaj, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except:
        pass

def vekil_sunucu_ile_baglan(hedef_url):
    # ScrapingAnt API'si ile Cloudflare'i aşıyoruz
    api_url = "https://api.scrapingant.com/v2/general"
    params = {
        "url": hedef_url,
        "x-api-key": SCRAPER_API_KEY,
        "browser": "true" # Gerçek tarayıcı gibi davranıp JS engellerini yıkar
    }
    cevap = requests.get(api_url, params=params)
    if cevap.status_code == 200:
        return cevap.text
    else:
        raise Exception(f"API Engeli (Hata Kodu: {cevap.status_code})")

def main():
    print("🔍 Vekil Sunucu (Scraping API) Tarama Başlatılıyor...")
    suanki_pdfler = []
    log_mesaji = "🤖 <b>Sistem Tarama Raporu (API Modu):</b>\n\n"

    for url in URLS:
        isim = "Madde 10" if "10" in url else "Madde 11"
        print(f"🔗 Ziyaret ediliyor: {isim}")
        
        try:
            # Hedef siteyi API üzerinden çek
            html_icerik = vekil_sunucu_ile_baglan(url)
            soup = BeautifulSoup(html_icerik, 'html.parser')
            
            linkler = soup.find_all('a', href=True)
            bulunan_pdf = 0
            for link in linkler:
                href = link['href']
                if 'pdf' in href.lower():
                    tam_link = href if href.startswith('http') else f"https://cetatenie.just.ro{href}"
                    if tam_link not in suanki_pdfler:
                        suanki_pdfler.append(tam_link)
                        bulunan_pdf += 1
                        
            print(f"✅ {isim}: {bulunan_pdf} PDF okundu.")
            log_mesaji += f"✅ {isim}: {bulunan_pdf} adet PDF okundu.\n"
            
        except Exception as e:
            print(f"❌ {isim} taranırken hata: {e}")
            log_mesaji += f"❌ {isim}: Başarısız -> {str(e)[:50]}\n"

    suanki_pdfler = suanki_pdfler[:30]
    eski_pdfler = hafizadan_pdfleri_getir()
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    if not suanki_pdfler:
        print("⚠️ Site PDF vermedi. (Cloudflare hala inat ediyor)")
        telegrama_mesaj_gonder(log_mesaji + "\n⚠️ <b>Hata:</b> Güvenlik duvarı aşılamadı veya sayfada PDF yok!")
    
    elif yeni_pdfler:
        print(f"🚨 {len(yeni_pdfler)} YENİ PDF BULUNDU!")
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    
    else:
        print("✅ Sistem güncel.")
        telegrama_mesaj_gonder(log_mesaji + "\n✅ <b>Sonuç:</b> Yeni PDF yok. Sistem güncel.")

if __name__ == "__main__":
    main()