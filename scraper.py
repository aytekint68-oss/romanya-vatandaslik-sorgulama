import os
import time
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": mesaj, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def main():
    suanki_pdfler = []
    log_mesaji = "🤖 <b>Sistem Tarama Raporu (Playwright Stealth):</b>\n\n"

    # Playwright (Gerçek Chrome) Başlatılıyor
    with sync_playwright() as p:
        # Korumalara yakalanmamak için özel argümanlar
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        for url in URLS:
            try:
                page = context.new_page()
                stealth_sync(page) # Robot olduğumuzu gizleyen anahtar (Stealth Mode)
                
                # Siteye git
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # ÖNEMLİ: Cloudflare JS kontrolünü (İnsan mısınız?) geçmek için 15 saniye bekle
                time.sleep(15)
                
                # Sayfanın tamamen yüklenmiş HTML'ini al
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                linkler = soup.find_all('a', href=True)
                bulunan_pdf = 0
                for link in linkler:
                    href = link['href']
                    if 'pdf' in href.lower():
                        tam_link = href if href.startswith('http') else f"https://cetatenie.just.ro{href}"
                        if tam_link not in suanki_pdfler:
                            suanki_pdfler.append(tam_link)
                            bulunan_pdf += 1
                            
                isim = "Madde 10" if "10" in url else "Madde 11"
                log_mesaji += f"✅ {isim}: {bulunan_pdf} adet PDF okundu.\n"
                page.close()
                
            except Exception as e:
                isim = "Madde 10" if "10" in url else "Madde 11"
                hata_detayi = str(e)[:60]
                log_mesaji += f"❌ {isim}: Hata oluştu -> {hata_detayi}\n"
                if 'page' in locals(): page.close()

        browser.close()

    # En üstteki 30 PDF'i alalım
    suanki_pdfler = suanki_pdfler[:30]
    eski_pdfler = hafizadan_pdfleri_getir()
    
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    # DURUM 1: Site PDF vermediyse (Hala engel varsa)
    if not suanki_pdfler:
        telegrama_mesaj_gonder(log_mesaji + "\n⚠️ <b>Hata:</b> Güvenlik duvarı aşılamadı veya sayfada PDF yok!")
    
    # DURUM 2: Yeni PDF Bulunduysa
    elif yeni_pdfler:
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        # Hafızayı güncelle
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    
    # DURUM 3: PDF'ler okundu ama hepsi eski
    else:
        telegrama_mesaj_gonder(log_mesaji + "\n✅ <b>Sonuç:</b> Korumalar aşıldı, yeni PDF yok. Sistem güncel.")

if __name__ == "__main__":
    main()