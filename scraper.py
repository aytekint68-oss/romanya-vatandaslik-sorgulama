import os
import time
from bs4 import BeautifulSoup
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# --- GÜVENLİ AYARLAR ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
JSONBIN_KEY = os.getenv("JSONBIN_MASTER_KEY")
SCRAPER_BIN_ID = os.getenv("SCRAPER_BIN_ID")

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

def main():
    print("🔍 DrissionPage (Hayalet Mod) Tarama Başlatılıyor...")
    suanki_pdfler = []
    log_mesaji = "🤖 <b>Sistem Tarama Raporu (DrissionPage Modu):</b>\n\n"

    try:
        # Gerçek Chrome'u kılık değiştirerek başlatıyoruz
        co = ChromiumOptions()
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        page = ChromiumPage(co)

        for url in URLS:
            isim = "Madde 10" if "10" in url else "Madde 11"
            print(f"\n🔗 Ziyaret ediliyor: {isim}")
            
            try:
                page.get(url)
                print("⏳ Cloudflare JS Testi için bekleniyor (15 sn)...")
                time.sleep(15) # Korumanın bizi geçirmesi için bekliyoruz
                
                html = page.html
                soup = BeautifulSoup(html, 'html.parser')
                
                linkler = soup.find_all('a', href=True)
                bulunan_pdf = 0
                for link in linkler:
                    href = link.get('href', '')
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

        page.quit()
        
    except Exception as e:
        log_mesaji += f"❌ Tarayıcı başlatılamadı: {str(e)[:50]}\n"

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