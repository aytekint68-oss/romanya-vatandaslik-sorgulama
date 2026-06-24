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
    log_mesaji = "🤖 <b>Sistem Tarama Raporu (DrissionPage Modu):</b>\n\n"

    try:
        co = ChromiumOptions()
        co.headless(False) # Sanal monitör zorunlu!
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--window-size=1920,1080')
        co.set_user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        page = ChromiumPage(co)

        for url in URLS:
            isim = "Madde 10" if "10" in url else "Madde 11"
            print(f"\n🔗 Ziyaret ediliyor: {isim}")
            
            try:
                # Sayfaya git ve Cloudflare/Yükleme için geniş bir zaman tanı
                page.get(url, timeout=60)
                
                # NET BEKLEME SÜRESİ: Site 10 saniyede açılıyorsa biz 15 saniye bekliyoruz
                print("⏳ Siteye ulaşıldı. Güvenlik doğrulaması ve içerik yüklemesi için 15 saniye bekleniyor...")
                time.sleep(15) 
                
                # Ekstra Kontrol: Eğer 15 saniye yetmediyse ve hala Cloudflare ekranındaysak 10 saniye daha bekle
                if "Just a moment" in page.title or "Cloudflare" in page.title:
                    print("⚠️ Site 15 saniyede açılamadı, ekstra 10 saniye daha bekleniyor...")
                    time.sleep(10)
                
                print(f"👀 Okunan Sayfa Başlığı: {page.title}")
                
                html = page.html
                soup = BeautifulSoup(html, 'html.parser')
                
                linkler = soup.find_all('a', href=True)
                bulunan_pdf = 0
                
                for link in linkler:
                    href = link.get('href', '')
                    # PDF uzantılı linkleri yakala
                    if '.pdf' in href.lower():
                        tam_link = href if href.startswith('http') else f"https://cetatenie.just.ro{href}"
                        if tam_link not in suanki_pdfler:
                            suanki_pdfler.append(tam_link)
                            bulunan_pdf += 1
                            
                print(f"✅ {isim}: {bulunan_pdf} PDF okundu.")
                log_mesaji += f"✅ {isim} <i>({page.title[:20]})</i>: <b>{bulunan_pdf} PDF okundu.</b>\n"
                
            except Exception as e:
                print(f"❌ {isim} taranırken hata: {e}")
                log_mesaji += f"❌ {isim}: Başarısız -> {str(e)[:50]}\n"

        # İşlem bitince tarayıcıyı kapat
        page.quit()
        
    except Exception as e:
        print(f"❌ Ana Tarayıcı Çökme Hatası: {e}")
        log_mesaji += f"❌ Sistem Hatası: Tarayıcı başlatılamadı veya çöktü.\n"

    # PDF Listesini İşleme
    suanki_pdfler = suanki_pdfler[:30] # Sadece en güncel 30 PDF'e odaklan
    eski_pdfler = hafizadan_pdfleri_getir()
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    # DURUM 1: Hiç PDF bulunamadıysa (Sayfa yanlış açıldıysa)
    if not suanki_pdfler:
        print("⚠️ Sayfa açıldı ancak PDF bulunamadı.")
        telegrama_mesaj_gonder(log_mesaji + "\n⚠️ <b>Hata:</b> Sayfa açıldı ancak PDF bulunamadı (HTML yapısı değişmiş olabilir)!")
    
    # DURUM 2: Yeni PDF Bulunduysa
    elif yeni_pdfler:
        print(f"🚨 {len(yeni_pdfler)} YENİ PDF BULUNDU!")
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        # JSONBin hafızasını güncelle
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    
    # DURUM 3: PDF'ler okundu ama hepsi zaten eski/bilinen PDF'ler
    else:
        print("✅ Sistem güncel.")
        telegrama_mesaj_gonder(log_mesaji + "\n✅ <b>Sonuç:</b> Yeni PDF yok. Sistem güncel.")

if __name__ == "__main__":
    main()