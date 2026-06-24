import os
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import requests # Telegram ve JSONBin haberleşmesi için standart kütüphane

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
    log_mesaji = "🤖 <b>Sistem Tarama Raporu:</b>\n\n"

    for url in URLS:
        try:
            # Gerçek bir Chrome v110 tarayıcısı gibi davran (Cloudflare'ı aşar)
            response = curl_requests.get(url, impersonate="chrome110", timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
            log_mesaji += f"✅ {isim}: {bulunan_pdf} adet PDF linki okundu.\n"
        except Exception as e:
            isim = "Madde 10" if "10" in url else "Madde 11"
            log_mesaji += f"❌ {isim}: Güvenlik duvarı bağlantıyı kesti!\n"

    # En üstteki 30 PDF'i alalım
    suanki_pdfler = suanki_pdfler[:30]
    eski_pdfler = hafizadan_pdfleri_getir()
    
    yeni_pdfler = [pdf for pdf in suanki_pdfler if pdf not in eski_pdfler]

    # DURUM 1: Site PDF vermediyse veya engellediyse
    if not suanki_pdfler:
        telegrama_mesaj_gonder(log_mesaji + "\n⚠️ <b>Hata:</b> Hiç PDF bulunamadı. Site engelliyor veya HTML yapısı değişmiş!")
    
    # DURUM 2: Yeni PDF Bulunduysa
    elif yeni_pdfler:
        mesaj = "🚨 <b>ANC SİTESİNE YENİ PDF EKLENDİ!</b> 🇹🇩\n\n"
        for pdf in yeni_pdfler:
            dosya_adi = pdf.split('/')[-1]
            mesaj += f"📄 <a href='{pdf}'>{dosya_adi}</a>\n"
        mesaj += "\n<i>Sistemi (CSV dosyalarını) güncellemeyi unutmayın!</i>"
        
        telegrama_mesaj_gonder(mesaj)
        
        # Hafızayı güncelle (Şişmemesi için sadece son 50 PDF'i tutalım)
        guncel_hafiza = list(set(yeni_pdfler + eski_pdfler))[:50]
        hafizaya_pdfleri_kaydet(guncel_hafiza)
    
    # DURUM 3: PDF'ler okundu ama hepsi zaten eski
    else:
        telegrama_mesaj_gonder(log_mesaji + "\n✅ <b>Sonuç:</b> Yeni PDF yok, sistem güncel.")

if __name__ == "__main__":
    main()