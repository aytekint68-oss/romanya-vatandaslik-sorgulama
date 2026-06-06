import requests
from bs4 import BeautifulSoup
import pandas as pd
import fitz  # PyMuPDF
import io
import re
import os
import socket

# --- GITHUB SUNUCU (IPv6) HATASINI ÖNLEMEK İÇİN IPv4'E ZORLAMA ---
eski_getaddrinfo = socket.getaddrinfo
def yeni_getaddrinfo(*args, **kwargs):
    cevaplar = eski_getaddrinfo(*args, **kwargs)
    return [cevap for cevap in cevaplar if cevap[0] == socket.AF_INET]
socket.getaddrinfo = yeni_getaddrinfo
# ----------------------------------------------------------------

# Ayarlar: Siteler ve Excel dosyalarınız
KAYNAKLAR = [
    {
        "kategori": "Madde 10",
        "url": "https://cetatenie.just.ro/ordine-articolul-10/",
        "excel_dosyasi": "Romanya_Vatandaslik_Tum_Veriler.xlsx"
    },
    {
        "kategori": "Madde 11",
        "url": "https://cetatenie.just.ro/ordine-articolul-1-1/",
        "excel_dosyasi": "Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx"
    }
]

YIL_FILTRESI = "2026"

def pdf_isle(pdf_url, pdf_adi):
    print(f"İndiriliyor ve okunuyor: {pdf_adi}")
    # Gerçek bir tarayıcı gibi görünmek için User-Agent eklendi
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    response = requests.get(pdf_url, headers=headers, timeout=30)
    pdf_verisi = io.BytesIO(response.content)
    
    doc = fitz.open(stream=pdf_verisi, filetype="pdf")
    dosya_numaralari = set()
    
    # Vatandaşlık dosya formatını arar (Örn: 1234/2026 veya 12345/2026)
    regex = r'\b(\d{1,5}/\d{4})\b'
    
    for sayfa in doc:
        metin = sayfa.get_text()
        eslesmeler = re.findall(regex, metin)
        for eslesme in eslesmeler:
            dosya_numaralari.add(eslesme)
            
    # PDF isminden tarihi yakalar (Örn: 03.06.2026)
    tarih_eslesme = re.search(r'\d{2}\.\d{2}\.\d{4}', pdf_adi)
    tarih = tarih_eslesme.group(0) if tarih_eslesme else "Bilinmiyor"
    
    veriler = []
    for dosya_no in dosya_numaralari:
        veriler.append({
            "Dosya Numarası": dosya_no,
            "Tarih": tarih,
            "Kaynak Belge": pdf_adi
        })
        
    return veriler

for kaynak in KAYNAKLAR:
    print(f"\n--- {kaynak['kategori']} Kontrol Ediliyor ---")
    
    # Mevcut Excel'i oku (varsa)
    if os.path.exists(kaynak['excel_dosyasi']):
        try:
            df_mevcut = pd.read_excel(kaynak['excel_dosyasi'])
            df_mevcut = df_mevcut.dropna(subset=['Kaynak Belge'])
            mevcut_pdfler = df_mevcut['Kaynak Belge'].unique().tolist()
        except:
            df_mevcut = pd.DataFrame(columns=["Dosya Numarası", "Tarih", "Kaynak Belge"])
            mevcut_pdfler = []
    else:
        df_mevcut = pd.DataFrame(columns=["Dosya Numarası", "Tarih", "Kaynak Belge"])
        mevcut_pdfler = []
        
    # Web sayfasını çek
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        r = requests.get(kaynak['url'], headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        yeni_kayitlar = []
        
        # Sayfadaki tüm linkleri tara
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Eğer link bir PDF ise ve içinde 2026 geçiyorsa
            if href.endswith('.pdf') and YIL_FILTRESI in href:
                pdf_adi = href.split('/')[-1]
                tam_url = href if href.startswith('http') else "https://cetatenie.just.ro" + href
                
                # Sadece Excel'de OLMAYAN yeni bir PDF ise işlem yap
                if pdf_adi not in mevcut_pdfler:
                    print(f"Yeni eklenecek PDF bulundu: {pdf_adi}")
                    try:
                        cekilen_veri = pdf_isle(tam_url, pdf_adi)
                        yeni_kayitlar.extend(cekilen_veri)
                    except Exception as e:
                        print(f"PDF okunurken hata oluştu ({pdf_adi}): {e}")
                
        # Yeni verileri Excel'e kaydet
        if yeni_kayitlar:
            df_yeni = pd.DataFrame(yeni_kayitlar)
            # Yeni veriler en üste gelsin diye df_yeni öne yazılır
            df_son = pd.concat([df_yeni, df_mevcut], ignore_index=True)
            df_son.to_excel(kaynak['excel_dosyasi'], index=False)
            print(f"✅ {len(yeni_kayitlar)} yeni onay {kaynak['excel_dosyasi']} dosyasına eklendi.")
        else:
            print("Sitede 2026 yılına ait Excel'inizde olmayan yeni bir PDF bulunamadı.")
            
    except Exception as e:
        print(f"Siteye bağlanırken bir sorun oluştu: {e}")

print("\n🎉 Tüm işlemler başarıyla tamamlandı!")
