import os
import time
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright

# --- GÜVENLİ AYARLAR ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
JSONBIN_KEY = os.getenv("JSONBIN_MASTER_KEY")
SCRAPER_BIN_ID = os.getenv("SCRAPER_BIN_ID")

URLS = [
    "https://cetatenie.just.ro/ordine-articolul-10/",
    "https://cetatenie.just.ro/ordine-articolul-1-1/"
]

def ayarları_kontrol_et():
    print("🔍 GİZLİ ŞİFRELER KONTROL EDİLİYOR...")
    print(f"- TELEGRAM_BOT_TOKEN: {'✅ Yüklendi' if BOT_TOKEN else '❌ BULUNAMADI!'}")
    print(f"- ADMIN_CHAT_ID: {'✅ Yüklendi' if ADMIN_CHAT_ID else '❌ BULUNAMADI!'}")
    print(f"- JSONBIN_MASTER_KEY: {'✅ Yüklendi' if JSONBIN_KEY else '❌ BULUNAMADI!'}")
    print(f"- SCRAPER_BIN_ID: {'✅ Yüklendi' if SCRAPER_BIN_ID else '❌ BULUNAMADI!'}")

def hafizadan_pdfleri_getir():
    headers = {"X-Master-Key": JSONBIN_KEY}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{SCRAPER_BIN_ID}/latest", headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {}).get("son_pdfler", [])
    except Exception as e:
        print(f"❌ Hafıza okuma hatası: {e}")
    return []

def hafizaya_pdfleri_kaydet(pdf_listesi):
    headers = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
    payload = {"son_pdfler": pdf_listesi}
    try:
        requests.put(f"https://api.jsonbin.io/v3/b/{SCRAPER_BIN_ID}", json=payload, headers=headers)
    except Exception as e:
        print(f"❌ Hafızaya kaydetme hatası: {e}")

def telegrama_mesaj_gonder(mesaj):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": ADMIN_CHAT_ID, "text": mesaj, "parse_mode": "HTML"}
        requests.post(url, json=payload)
        print("✅ Telegram mesajı gönderildi.")
    except Exception as e:
        print(f"❌ Telegram API Hatası: {e}")

def main():
    ayarları_kontrol_et()
    suanki_pdfler = []
    log_mesaji = "🤖 <b>Sistem Tarama Raporu (Radar Modu):</b>\n\n"

    try:
        with sync_playwright() as p:
            print("🌐 Gerçek Ekranlı Tarayıcı Başlatılıyor...")
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1920,1080"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            for url in URLS:
                print(f"\n🔗 Ziyaret ediliyor: {url}")
                isim = "Madde 10" if "10" in url else "Madde 11"
                page = None
                
                try:
                    page = context.new_page()
                    
                    # Sayfaya git ve yüklenmesini bekle
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=45000)
                    except Exception as goto_err:
                        print(f"⚠️ Goto Zaman Aşımı (Önemli değil, devam ediliyor): {goto_err}")
                    
                    # RADAR SİSTEMİ: Şu an ekranda ne var?
                    for _ in range(4): # 20 saniye boyunca sayfayı izle
                        if page.is_closed():
                            break
                        
                        sayfa_basligi = page.title()
                        print(f"👀 Şu anki Sayfa Başlığı: '{sayfa_basligi}'")
                        
                        if "Just a moment" in sayfa_basligi or "Cloudflare" in sayfa_basligi:
                            print("⏳ Cloudflare güvenlik ekranındayız, geçmesi bekleniyor...")
                            time.sleep(5)
                        else:
                            print("✅ Güvenlik ekranı yok gibi görünüyor, asıl siteye ulaşıldı.")
                            time.sleep(3) # İçeriğin oturması için son bir pay
                            break
                    
                    # Çökme kontrolü
                    if page.is_closed():
                        print("❌ Sayfa sekmesi arka planda çökmüş veya kapanmış!")
                        log_mesaji += f"❌ {isim}: Tarayıcı sekmesi çöktü (Cloudflare engeli).\n"
                        continue
                        
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
                                
                    print(f"✅ {isim}: {bulunan_pdf} PDF okundu.")
                    log_mesaji += f"✅ {isim}: {bulunan_pdf} adet PDF okundu.\n"
                    page.close()
                    
                except Exception as e:
                    print(f"❌ {isim} taranırken iç hata: {e}")
                    hata_kisa = str(e).split('\n')[0][:50]
                    log_mesaji += f"❌ {isim}: Hata -> {hata_kisa}\n"
                    if page and not page.is_closed(): page.close()

            browser.close()
    except Exception as e:
        print(f"❌ Ana Tarayıcı Çökme Hatası: {e}")
        log_mesaji += f"❌ Sistem Hatası: Tarayıcı başlatılamadı.\n"

    suanki_pdfler = suanki_pdfler[:30]
    eski_pdfler = hafizadan_pdfleri_getir()
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    if not suanki_pdfler:
        print("⚠️ Site PDF vermedi veya ulaşılamadı.")
        telegrama_mesaj_gonder(log_mesaji + "\n⚠️ <b>Hata:</b> Güvenlik duvarı kırılamadı veya sayfa boş (IP Engeli Olabilir)!")
    
    elif yeni_pdfler:
        print(f"🚨 {len(yeni_pdfler)} YENİ PDF BULUNDU! Telegram'a bildiriliyor...")
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    
    else:
        print("✅ Sistem güncel, yeni PDF yok.")
        telegrama_mesaj_gonder(log_mesaji + "\n✅ <b>Sonuç:</b> Yeni PDF yok. Sistem güncel.")

if __name__ == "__main__":
    main()