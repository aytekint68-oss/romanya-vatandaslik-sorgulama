import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import re
import os
import gc
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Romanya Vatandaşlık Sorgulama",
    page_icon="https://flagcdn.com/w320/ro.png",
    layout="centered"
)

# --- ALT FONKSİYONLAR (Esnek Uzantı Okuyucu) ---
def gercek_dosya_yolu(taban_adi):
    """Dosyanın .xlsx, .zip veya .csv uzantılı halini bulur"""
    for uzanti in ['.xlsx', '.zip', '.csv']:
        if os.path.exists(taban_adi + uzanti):
            return taban_adi + uzanti
    return None

def _esnek_veri_oku(taban_adi):
    """Bulunan dosyayı uzantısına göre en uygun yöntemle okur"""
    dosya_adi = gercek_dosya_yolu(taban_adi)
    if not dosya_adi:
        return pd.DataFrame()
        
    try:
        if dosya_adi.endswith('.xlsx'):
            df = pd.read_excel(dosya_adi)
            df.columns = df.columns.astype(str).str.strip()
            return df.fillna("")
        else:
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
            if len(df.columns) < 2:
                df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
            df.columns = df.columns.astype(str).str.strip()
            return df.fillna("")
    except Exception:
        try:
            if not dosya_adi.endswith('.xlsx'):
                df = pd.read_csv(dosya_adi, sep=';', encoding='cp1254', low_memory=False, on_bad_lines='skip')
                if len(df.columns) < 2:
                    df = pd.read_csv(dosya_adi, sep=',', encoding='cp1254', low_memory=False, on_bad_lines='skip')
                df.columns = df.columns.astype(str).str.strip()
                return df.fillna("")
        except Exception: pass
        
    return pd.DataFrame()

def max_ordin_hesapla_vektorel(df_k):
    if df_k.empty: return {}
    ordin_sutunlari = [col for col in df_k.columns if 'ordin' in str(col).lower() or 'karar' in str(col).lower()]
    if not ordin_sutunlari: return {}
    
    ordin_col = ordin_sutunlari[0]
    temp_df = pd.DataFrame()
    
    if 'Kaynak Belge' in df_k.columns:
        temp_df['Yil'] = df_k['Kaynak Belge'].astype(str).str.extract(r'\d{2}[\.\-\_]\d{2}[\.\-\_](\d{4})')[0]
        temp_df['Yil'] = temp_df['Yil'].fillna(df_k['Kaynak Belge'].astype(str).str.extract(r'\b(202\d)\b')[0])
    else:
        temp_df['Yil'] = df_k[ordin_col].astype(str).str.extract(r'\b(202\d)\b')[0]
        
    temp_df['No'] = df_k[ordin_col].astype(str).str.extract(r'(\d{1,6})')[0]
    temp_df['Yil'] = pd.to_numeric(temp_df['Yil'], errors='coerce')
    temp_df['No'] = pd.to_numeric(temp_df['No'], errors='coerce')
    
    return temp_df.dropna().groupby('Yil')['No'].max().to_dict()

def en_guncel_belgeleri_getir(df, dosya_yolu=None):
    if df.empty or 'Kaynak Belge' not in df.columns: 
        if dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
            return ["Veri/Belge Yok"], dt_str
        return ["Veri Yok"], "Bilinmiyor"
    
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    unique_files['Parsed_Date'] = pd.to_datetime(
        unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], 
        format='%d.%m.%Y', 
        errors='coerce'
    )
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        max_date = valid_files['Parsed_Date'].max()
        latest_files_df = valid_files[valid_files['Parsed_Date'] == max_date]
        dosya_listesi = latest_files_df['Kaynak Belge'].tolist()
        tarih_str = max_date.strftime('%d.%m.%Y')
        return dosya_listesi, tarih_str
    elif not unique_files.empty:
        if dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
            return [unique_files.iloc[0]['Kaynak Belge']], dt_str
        return [unique_files.iloc[0]['Kaynak Belge']], "Tarih Bulunamadı"
    
    return ["Veri Yok"], "Bilinmiyor"

def sutun_degeri_al(row, olasi_isimler):
    for col in row.index:
        col_clean = str(col).strip().lower()
        for hedef in olasi_isimler:
            if col_clean == hedef.lower():
                val = str(row[col]).strip()
                if val.lower() not in ['nan', 'none']:
                    return val
    return ""

# =========================================================
# 🌟 MERKEZİ VERİTANI YÜKLEYİCİSİ
# =========================================================
@st.cache_data(max_entries=1, ttl=3600, show_spinner="Yeni veriler senkronize ediliyor, lütfen bekleyin...")
def veritabanini_hazirla(guncelleme_tetikleyici):
    df_d = _esnek_veri_oku("dosyadurumu")
    df_d_eski = _esnek_veri_oku("dosyadurumu_eski")
    df_m10 = _esnek_veri_oku("Romanya_Vatandaslik_Tum_Veriler_Madde10")
    df_m11 = _esnek_veri_oku("Romanya_Vatandaslik_Tum_Veriler_Madde11")
    df_ozel_durum = _esnek_veri_oku("Dosya_Durumlari")

    yol_d = gercek_dosya_yolu("dosyadurumu")
    yol_m10 = gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde10")
    yol_m11 = gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde11")

    _, d_tarih = en_guncel_belgeleri_getir(df_d, yol_d)
    m10_list, m10_tarih = en_guncel_belgeleri_getir(df_m10, yol_m10)
    m11_list, m11_tarih = en_guncel_belgeleri_getir(df_m11, yol_m11)
    
    max_m10 = max_ordin_hesapla_vektorel(df_m10)
    max_m11 = max_ordin_hesapla_vektorel(df_m11)

    k_list = []
    if not df_m10.empty: k_list.append(df_m10)
    if not df_m11.empty: k_list.append(df_m11)
    df_k = pd.concat(k_list, ignore_index=True) if k_list else pd.DataFrame()

    del df_m10
    del df_m11
    del k_list
    gc.collect()

    return df_d, df_k, d_tarih, m10_list, m11_list, max_m10, max_m11, df_ozel_durum, df_d_eski

def dosya_zaman_damgasi_al():
    tabanlar = ["dosyadurumu", "dosyadurumu_eski", "Romanya_Vatandaslik_Tum_Veriler_Madde10", "Romanya_Vatandaslik_Tum_Veriler_Madde11", "Dosya_Durumlari"]
    uzantilar = ['.xlsx', '.zip', '.csv']
    tetikleyici_kod = ""
    for taban in tabanlar:
        for uzanti in uzantilar:
            d = taban + uzanti
            if os.path.exists(d):
                mtime = os.path.getmtime(d)
                size = os.path.getsize(d)
                tetikleyici_kod += f"{mtime}_{size}_"
                break
    return tetikleyici_kod

df_dosya, df_karar, dosya_guncelleme_tarihi, m10_belgeler_listesi, m11_belgeler_listesi, max_ordin_m10, max_ordin_m11, df_ozel, df_dosya_eski = veritabanini_hazirla(dosya_zaman_damgasi_al())

# =========================================================
# 🌟 HTML ŞABLONU (Madde 10/11 Sorgulama Aracı)
# =========================================================
MADDE_SORGULAMA_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Romanya Vatandaşlığı Sorgulama Aracı</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: transparent;
            color: #333;
            margin: 0;
            padding: 5px;
            display: flex;
            justify-content: center;
        }
        .container {
            background-color: #fff;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            max-width: 600px;
            width: 100%;
            border: 1px solid #e6e6e6;
        }
        h1 {
            font-size: 22px;
            color: #0056b3;
            text-align: center;
            margin-bottom: 25px;
            line-height: 1.4;
        }
        .question { margin-bottom: 20px; }
        .question label {
            display: block;
            font-weight: bold;
            margin-bottom: 10px;
        }
        select, input[type="date"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
            font-family: inherit;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #0056b3;
            color: #fff;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin-top: 15px;
            transition: background-color 0.3s;
        }
        button:hover { background-color: #004494; }
        .result {
            margin-top: 25px;
            padding: 15px;
            border-radius: 4px;
            font-weight: normal;
            display: none;
            line-height: 1.5;
        }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .info {
            font-size: 12px;
            color: #666;
            margin-top: 25px;
            text-align: justify;
            border-top: 1px solid #eee;
            padding-top: 15px;
            line-height: 1.5;
        }
        .disclaimer { margin-top: 10px; font-weight: bold; color: #555; }
    </style>
</head>
<body>
<div class="container">
    <h1>Romanya Vatandaşlığı<br>Madde 10 / Madde 11 ?</h1>
    <div class="question">
        <label for="birthPlace">1. Atanızın Doğduğu Bölge Neresiydi?</label>
        <select id="birthPlace">
            <option value="none">Seçiniz...</option>
            <option value="dobruca">Güney Dobruca Bölgesi (Silistre, Pazarcık, Balçık, Tutrakan vb. - Şu an Bulgaristan'da)</option>
            <option value="romanya">Mevcut Romanya Sınırları İçindeki Bir Şehir (Köstence, Bükreş, Mecidiye vb.)</option>
            <option value="diger">Diğer / Bilmiyorum</option>
        </select>
    </div>
    <div class="question">
        <label for="migrationDate">2. Atanızın Türkiye'ye Göç Ettiği Tarih Nedir?</label>
        <input type="date" id="migrationDate">
    </div>
    <div class="question">
        <label for="degree">3. Vatandaşlığı kaybeden atanıza göre kaçıncı derece altsoysunuz?</label>
        <select id="degree">
            <option value="none">Seçiniz...</option>
            <option value="1">1. Derece (Çocuğuyum)</option>
            <option value="2">2. Derece (Torunuyum)</option>
            <option value="3">3. Derece (Torununun Çocuğuyum)</option>
            <option value="4">4. Derece veya daha uzak</option>
        </select>
    </div>
    <button onclick="calculateEligibility()">Durumumu Sorgula</button>
    <div id="resultBox" class="result"></div>
    <div class="info">
        <strong>Kanuni Bilgilendirme:</strong> Bu araç 21/1991 sayılı Romanya Vatandaşlık Kanunu baz alınarak hazırlanmıştır. Madde 10, vatandaşlığı kaybedenler ve 2. dereceye kadar altsoyları içindir. Madde 11 ise vatandaşlığı kendilerine atfedilemeyen nedenlerle kaybedenler veya iradeleri dışında ellerinden alınanlar ile 3. dereceye kadar altsoyları içindir. Her iki durumda da Romence bilme şartı aranmaktadır. Sınır değişiklikleri için tarihi dönüm noktası olan 7 Eylül 1940 (Krayova Antlaşması) referans alınmıştır.
        <div class="disclaimer">
            Sorumluluk Reddi Beyanı: Bu uygulama yalnızca genel bilgilendirme amacıyla oluşturulmuş olup kesinlikle hukuki bir tavsiye niteliği taşımamaktadır. Aracın, Romanya Milli Vatandaşlık Otoritesi (ANC) veya herhangi bir resmi Romanya devlet kurumu ile hiçbir resmi bağı, sponsorluğu veya ilişiği bulunmamaktadır. Vatandaşlık başvurularında nihai karar yetkisi ve yasal süreç yönetimi tamamen Romanya resmi makamlarına aittir. Kesin ve güncel bilgi için lütfen bir hukuk danışmanına veya doğrudan resmi makamlara başvurunuz.
        </div>
    </div>
</div>
<script>
    function calculateEligibility() {
        const place = document.getElementById('birthPlace').value;
        const migrationDateStr = document.getElementById('migrationDate').value;
        const degree = parseInt(document.getElementById('degree').value);
        const resultBox = document.getElementById('resultBox');
        
        resultBox.style.display = 'block';
        resultBox.className = 'result';
        if (place === 'none' || !migrationDateStr || isNaN(degree)) {
            resultBox.innerHTML = "Lütfen tüm soruları eksiksiz cevaplayınız (Tarih dahil).";
            resultBox.classList.add('error');
            return;
        }
        const migrationDate = new Date(migrationDateStr);
        const treatyDate = new Date('1940-09-07');
        const isPreTreaty = migrationDate < treatyDate;

        if (isPreTreaty) {
            if (degree <= 2) {
                resultBox.innerHTML = `🎉 <strong>Sonuç: Madde 10 Kapsamındasınız.</strong><br><br>Atanız Krayova Antlaşması'ndan (7 Eylül 1940) önce göç ettiği için vatandaşlığı kendi iradesiyle bırakmış sayılır. Bu durum sizi <strong>Madde 10</strong> kapsamına sokar. Sadece 1. ve 2. derece altsoylar başvuru yapabilir. Dereceniz uygun olduğu için başvuru hakkınız bulunmaktadır.`;
                resultBox.classList.add('success');
            } else {
                resultBox.innerHTML = `❌ <strong>Sonuç: Başvuru Hakkınız Bulunmuyor.</strong><br><br>Atanız Krayova Antlaşması'ndan (7 Eylül 1940) önce göç ettiği için süreç <strong>Madde 10</strong> kapsamındadır. Madde 10 kapsamında sadece 2. dereceye kadar olan altsoylar (çocuk ve torun) başvuru yapabilir. 3. derece ve sonrasına hak tanınmamıştır.`;
                resultBox.classList.add('error');
            }
        } else if (place === 'dobruca' && !isPreTreaty) {
            if (degree <= 3) {
                resultBox.innerHTML = `🎉 <strong>Sonuç: Madde 11 Kapsamındasınız.</strong><br><br>Atanız Güney Dobruca bölgesinde doğmuş ve 7 Eylül 1940'taki sınır değişikliğini o topraklarda yaşamıştır. Romanya vatandaşlığını kendi kusuru olmaksızın (iradesi dışında) kaybettiği için süreç <strong>Madde 11</strong> kapsamındadır. 3. dereceye kadar altsoyların başvuru hakkı vardır.`;
                resultBox.classList.add('success');
            } else {
                resultBox.innerHTML = `❌ <strong>Sonuç: Başvuru Hakkınız Bulunmuyor.</strong><br><br>Süreç Madde 11 kapsamında olsa da, yasaya göre en fazla 3. dereceye kadar olan altsoylar (çocuk, torun, torun çocuğu) başvuru yapabilir. 4. derece ve ötesi için hak bulunmamaktadır.`;
                resultBox.classList.add('error');
            }
        } else if (place === 'romanya' && !isPreTreaty) {
            if (degree <= 3) {
                resultBox.innerHTML = `⚠️ <strong>Sonuç: Durum İncelemesi Gerekiyor.</strong><br><br>Atanız mevcut Romanya sınırlarında doğmuş ve 7 Eylül 1940 sonrasında göç etmiş. Eğer vatandaşlıktan dönemin rejimi tarafından zorla çıkarıldıysa <strong>Madde 11</strong> (3. dereceye kadar hak verir), kendi isteğiyle çıktıysa <strong>Madde 10</strong> (2. dereceye kadar hak verir) devreye girer. Atanızın vatandaşlıktan çıkış belgesi belirleyici olacaktır.`;
                resultBox.classList.add('warning');
            } else {
                resultBox.innerHTML = `❌ <strong>Sonuç: Başvuru Hakkınız Bulunmuyor.</strong><br><br>Dereceniz 4 veya daha uzak olduğu için Madde 10 veya Madde 11 kapsamında herhangi bir başvuru hakkınız yasal olarak bulunmamaktadır.`;
                resultBox.classList.add('error');
            }
        } else {
            resultBox.innerHTML = `⚠️ <strong>Özel Durum:</strong><br><br>Seçtiğiniz kombinasyon net bir ayrıma girmemektedir. Hangi madde üzerinden ilerleyeceğiniz, atanızın vatandaşlıktan çıkış gerekçesinin yazdığı belgelere (Romanya veya Bulgaristan arşivlerinden çıkacak kayıtlara) göre netlik kazanacaktır.`;
            resultBox.classList.add('warning');
        }
    }
</script>
</body>
</html>
"""

# --- ARAYÜZ TASARIMI ---
st.title("Romanya Vatandaşlık Sorgulama")
st.markdown("Uygulamamıza hoş geldiniz. İşlem yapmak istediğiniz aracı sekmelerden seçebilirsiniz.")

# SEKMELER (TABS) OLUŞTURULUYOR
# Streamlit listeye yazılan ilk sekmeyi (tab1) otomatik olarak sayfada varsayılan (açık) sekme yapar.
tab1, tab2 = st.tabs(["🔍 Dosya ve Karar Sorgulama", "📋 Madde 10/11 Uygunluk Testi"])

# =========================================================
# 1. SEKME: DOSYA VE KARAR SORGULAMA
# =========================================================
with tab1:
    m10_items = "".join([f"<li style='margin-bottom: 5px;'>🔹 {b}</li>" for b in m10_belgeler_listesi]) if m10_belgeler_listesi and m10_belgeler_listesi[0] != "Veri Yok" else "<li style='margin-bottom: 5px;'>🔹 <i>Veri Yok</i></li>"
    m11_items = "".join([f"<li style='margin-bottom: 5px;'>🔹 {b}</li>" for b in m11_belgeler_listesi]) if m11_belgeler_listesi and m11_belgeler_listesi[0] != "Veri Yok" else "<li style='margin-bottom: 5px;'>🔹 <i>Veri Yok</i></li>"

    info_box_html = f"""<div style="background-color: rgba(42, 171, 238, 0.1); border-left: 5px solid #2aabee; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
    <div style="font-size: 1.1em; margin-bottom: 10px;">🔄 <strong>Dosya Durumu (Stadiu Dosar) Son Güncelleme:</strong> {dosya_guncelleme_tarihi}</div>
    <div style="font-size: 1.1em; margin-bottom: 10px;">📑 <strong>Sisteme Eklenen Son Kararlar:</strong></div>
    <div style="font-size: 1.1em; margin-bottom: 5px;"><strong>Madde 10:</strong></div>
    <ul style="list-style-type: none; padding-left: 20px; font-size: 1.1em; margin-top: 0;">
    {m10_items}
    </ul>
    <div style="font-size: 1.1em; margin-bottom: 5px; margin-top: 10px;"><strong>Madde 11:</strong></div>
    <ul style="list-style-type: none; padding-left: 20px; font-size: 1.1em; margin-top: 0;">
    {m11_items}
    </ul>
    </div>"""

    st.markdown(info_box_html, unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("💡 **Örnek Arama Formatı:** 1234/2022 veya 1234/RD/2022")

    with st.form(key="arama_formu"):
        aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 9402/RD/2024")
        arama_baslatildi = st.form_submit_button("🔍 Dosyamı ve Kararımı Sorgula")

    if arama_baslatildi:
        if not aranan_kelime:
            st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
        elif df_dosya.empty:
            st.error("Sistemde şu an 'Dosya Durumu' verisi bulunmuyor.")
        else:
            with st.spinner("Dosyanız aranıyor, lütfen bekleyin..."):
                temiz_arama = aranan_kelime.strip().replace(" ", "")
                
                # --- AKILLI ARAMA KONTROLLERİ ---
                if not re.fullmatch(r'[a-zA-Z0-9/]+', temiz_arama):
                    st.warning("⚠️ Hatalı giriş yaptınız. Lütfen SADECE rakam, harf ve '/' işareti kullanınız. Örn: 1234/2023 veya 9402/RD/2024")
                elif "/" not in temiz_arama:
                    st.warning("⚠️ Hatalı format. Lütfen araya '/' işareti koyunuz. Örn: 1234/2023")
                else:
                    parcalar = temiz_arama.split("/")
                    ilk_numara = "".join(filter(str.isdigit, parcalar[0]))
                    son_yil = "".join(filter(str.isdigit, parcalar[-1]))
                    
                    mevcut_yil = datetime.datetime.now().year
                    
                    if len(ilk_numara) == 0 or int(ilk_numara) == 0:
                        st.warning("⚠️ Hatalı giriş yaptınız. Dosya numarası geçersiz.")
                    elif len(son_yil) != 4 or not (2017 <= int(son_yil) <= mevcut_yil):
                        st.warning(f"⚠️ Sistem uyarısı: Dosya yılı yalnızca 2017 ile {mevcut_yil} yılları arasında olabilir.")
                    else:
                        arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
                        
                        # Dosya No sütununu dinamik bul
                        dosya_no_col = next((col for col in df_dosya.columns if any(x in str(col).lower() for x in ['dosya', 'nr. dosar', 'nr dosar'])), df_dosya.columns[0])
                        df_dosya['Arama_Sutunu'] = df_dosya[dosya_no_col].astype(str).str.strip()
                        sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                        
                        if not sonuclar.empty:
                            st.success(f"✅ Dosyanız bulundu! Durum ve Karar bilgileri aşağıdadır:")
                            
                            # --- ÖZEL DURUM BİLDİRİMİ (Dosya_Durumlari.xlsx) ---
                            ozel_durum_var_mi = False
                            ozel_sonuc = pd.DataFrame()
                            if not df_ozel.empty and len(df_ozel.columns) >= 3:
                                df_ozel['Arama_Sutunu'] = df_ozel.iloc[:, 2].astype(str).str.strip()
                                ozel_sonuc = df_ozel[df_ozel['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                                if not ozel_sonuc.empty:
                                    ozel_durum_var_mi = True
                            
                            for index, row in sonuclar.iterrows():
                                dosya_no_val = str(row[dosya_no_col]).strip()
                                dosya_no_parcalar = dosya_no_val.split('/')
                                ana_no = dosya_no_parcalar[0].strip()
                                ana_yil = dosya_no_parcalar[-1].strip()
                                
                                karar_bulundu_mu = False
                                k_row = None
                                
                                if not df_karar.empty:
                                    karar_sutunu = [col for col in df_karar.columns if 'dosya' in str(col).lower() or 'nr' in str(col).lower()][0]
                                    temiz_karar_metni = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
                                    karar_icin_regex = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
                                    karar_sonucu = df_karar[temiz_karar_metni.str.contains(karar_icin_regex, regex=True, case=False)]
                                    
                                    if not karar_sonucu.empty:
                                        karar_bulundu_mu = True
                                        k_row = karar_sonucu.iloc[0]

                                # Ham verileri çek
                                basvuru_tarihi = sutun_degeri_al(row, ['Başvuru Tarihi', 'DATA ÎNREGISTRĂRII', 'DATA INREGISTRARII', 'Tarih'])
                                termen_metni = sutun_degeri_al(row, ['TERMEN', 'Termen', 'Sonraki Aşama'])
                                solutie_metni = sutun_degeri_al(row, ['SOLUTIE', 'Solutie', 'Kurum Notu'])

                                # 1. Solutie içinde tarih (GG.AA.YYYY) aranır:
                                solutie_tarih_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', solutie_metni)
                                if solutie_tarih_match and not re.search(r'\d+\s*/?\s*P', solutie_metni, re.IGNORECASE):
                                    if not termen_metni or termen_metni.lower() in ['nan', 'none', '-', 'belirtilmemiş']:
                                        termen_metni = solutie_tarih_match.group(1)
                                    solutie_metni = "" 

                                # 2. Termen içindeki tarihi temizle ve formatla
                                if termen_metni:
                                    termen_tarih_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', termen_metni)
                                    if termen_tarih_match:
                                        termen_metni = termen_tarih_match.group(1).replace('/', '.').replace('-', '.')
                                    else:
                                        if termen_metni.lower() in ['nan', 'none', '-']:
                                            termen_metni = ""

                                # 3. Başvuru tarihini temizle
                                if basvuru_tarihi:
                                    basvuru_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', basvuru_tarihi)
                                    if basvuru_match:
                                        basvuru_tarihi = basvuru_match.group(1).replace('/', '.').replace('-', '.')

                                eski_termen_metni = ""
                                if not df_dosya_eski.empty:
                                    eski_dosya_col = next((col for col in df_dosya_eski.columns if any(x in str(col).lower() for x in ['dosya', 'nr. dosar', 'nr dosar'])), df_dosya_eski.columns[0])
                                    eski_match = df_dosya_eski[df_dosya_eski[eski_dosya_col].astype(str).str.strip().str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                                    if not eski_match.empty:
                                        e_val = sutun_degeri_al(eski_match.iloc[0], ['TERMEN', 'Termen', 'Sonraki Aşama'])
                                        e_match_date = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_val)
                                        eski_termen_metni = e_match_date.group(1).replace('/', '.').replace('-', '.') if e_match_date else e_val

                                termen_ekran_yazisi = termen_metni if termen_metni else "Belirtilmemiş"
                                
                                if eski_termen_metni and termen_metni and eski_termen_metni.lower() not in ['nan', 'none', '', 'belirtilmemiş'] and eski_termen_metni != termen_metni:
                                    termen_ekran_yazisi = f"{termen_metni} <br><span style='font-size:0.85em; color:#777;'>(Önceki: {eski_termen_metni}) 🔄</span>"

                                p_numarasi = None
                                user_ordin_no = 0
                                user_ordin_yil = 0
                                
                                if solutie_metni:
                                    p_match = re.search(r'(\d{1,6})\s*[/]?\s*P(?:\s*[/]?\s*(\d{4}))?', solutie_metni, re.IGNORECASE)
                                    if p_match:
                                        user_ordin_no = int(p_match.group(1))
                                        if p_match.group(2):
                                            user_ordin_yil = int(p_match.group(2))
                                            p_numarasi = f"{user_ordin_no}/P/{user_ordin_yil}"
                                        else:
                                            p_numarasi = f"{user_ordin_no}/P"

                                # --- KİŞİ LİSTEDEYSE 40 GÜN HESAPLAMASI VE UYARISI ---
                                if ozel_durum_var_mi and not ozel_sonuc.empty:
                                    ozel_satir = ozel_sonuc.iloc[0]
                                    ozel_tarih_str = str(ozel_satir.iloc[0]) if len(ozel_satir) > 0 else "-"
                                    ozel_isim = str(ozel_satir.iloc[1]) if len(ozel_satir) > 1 else "-"
                                    ozel_dosya = str(ozel_satir.iloc[2]) if len(ozel_satir) > 2 else "-"
                                    ozel_ek_bilgi = str(ozel_satir.iloc[3]) if len(ozel_satir) > 3 else "-"
                                    
                                    kalan_gun_mesaji = ""
                                    icon_tipi = "⚠️"
                                    
                                    try:
                                        parsed_date = pd.to_datetime(ozel_tarih_str, dayfirst=True)
                                        gecen_gun = (datetime.datetime.now() - parsed_date).days
                                        kalan_gun = 40 - gecen_gun
                                        
                                        if kalan_gun > 0:
                                            kalan_gun_mesaji = f"⏳ **DİKKAT! Yasal sürenin dolmasına SON {kalan_gun} GÜN!** Lütfen vakit kaybetmeden istenen e-posta adresini kuruma bildiriniz."
                                            icon_tipi = "⚠️"
                                        elif kalan_gun == 0:
                                            kalan_gun_mesaji = f"🚨 **DİKKAT! Yasal süreniz BUGÜN DOLUYOR!** Lütfen acilen istenen e-posta adresini kuruma bildiriniz."
                                            icon_tipi = "🚨"
                                        else:
                                            kalan_gun_mesaji = f"❌ **SÜRE DOLDU!** (Duyurunun üzerinden {gecen_gun} gün geçmiş). Yasal 40 günlük süreniz dolmuş görünmektedir. Ancak dosyanızın reddedilmemesi ihtimaline karşı yinede **ACİLEN** istenilen bilgiyi kuruma iletmeniz tavsiye edilir."
                                            icon_tipi = "❌"
                                    except Exception:
                                        kalan_gun_mesaji = "Lütfen duyurunun yayınlanma tarihinden itibaren 40 gün içinde e-posta adresinizi kuruma bildiriniz."
                                    
                                    st.error(f"""
                                    🚨 **ÖNEMLİ BİLDİRİM (Eksik Evrak / İletişim)**
                                    
                                    Dosyanız, Ulusal Vatandaşlık Kurumu'nun (ANC) tarafınıza ulaşılamadığı için yayınladığı özel listede tespit edilmiştir. 
                                    
                                    * **Yayınlanma Tarihi:** {ozel_tarih_str}
                                    * **İsim:** {ozel_isim}
                                    * **Dosya Numarası:** {ozel_dosya}
                                    * **Bilgi Notu:** {ozel_ek_bilgi}
                                    
                                    **{kalan_gun_mesaji}**
                                    
                                    *(21/1991 sayılı Kanun'un 34.1. maddesinin 10. fıkrasına göre yapılan bildirimdir.)*
                                    
                                    🔗 **Resmi Kaynak Listesi:** [cetatenie.just.ro/category/confirmari-corespondenta-electronica/](https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/)
                                    """, icon=icon_tipi)

                                with st.container(border=True):
                                    
                                    st.markdown(f"<h3 style='text-align: center; color: #4F8BF9; margin-bottom: 0;'>📂 DOSYA BİLGİLERİ</h3>", unsafe_allow_html=True)
                                    st.markdown(f"<h4 style='text-align: center; margin-top: 0;'>No: {dosya_no_val}</h4>", unsafe_allow_html=True)
                                    st.divider()
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown(f"**📅 Başvuru Tarihi:**<br>{basvuru_tarihi if basvuru_tarihi else 'Belirtilmemiş'}", unsafe_allow_html=True)
                                    with col2:
                                        st.markdown(f"**⏳ Sonraki Aşama (Termen):**<br>{termen_ekran_yazisi}", unsafe_allow_html=True)
                                            
                                    st.markdown("<br>", unsafe_allow_html=True)
                                    
                                    if solutie_metni:
                                        st.info(f"**📝 Kurum Notu (Solutie):** {solutie_metni}", icon="ℹ️")
                                    else:
                                        if karar_bulundu_mu:
                                            st.info("**📝 Kurum Notu (Solutie):** Sistemde not düşülmemiş ancak resmi Karar (Ordin) listelerinde sonuç tespit edildi!", icon="ℹ️")
                                        else:
                                            st.warning("**📝 Kurum Notu (Solutie):** Henüz bir not girilmemiş (İnceleme Bekliyor).", icon="⏳")
                                            
                                    kaynak_dosya_metni = sutun_degeri_al(row, ['Kaynak Belge', 'Kaynak', 'Dosya Adi'])
                                    st.markdown(f"📂 **Kaynak Belge (Stadiu Dosar):** {kaynak_dosya_metni}")
                                    st.divider()
                                    
                                    st.markdown("<h4 style='text-align: center;'>⚖️ KARAR (ORDIN) DURUMU</h4>", unsafe_allow_html=True)
                                    
                                    if karar_bulundu_mu:
                                        st.success("🎉 **TEBRİKLER! Kararınız yayımlandı.**", icon="✅")
                                        
                                        with st.container(border=True):
                                            kaynak_belge_adi = sutun_degeri_al(k_row, ['Kaynak Belge', 'Kaynak', 'Dosya Adi'])
                                            gosterilecek_karar = ""
                                            
                                            k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower()]
                                            if k_ordin_cols:
                                                val = str(k_row[k_ordin_cols[0]]).strip()
                                                if val and val.lower() not in ['nan', 'none', '']:
                                                    gosterilecek_karar = val

                                            if not gosterilecek_karar or gosterilecek_karar.lower() in ['nan', 'none', '', 'belirtilmemiş']:
                                                pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)\s*[/]?\s*([pP])?', kaynak_belge_adi, re.IGNORECASE)
                                                if pdf_match:
                                                    no_kismi = pdf_match.group(1)
                                                    p_harfi = "/P" if pdf_match.group(2) else ""
                                                    gosterilecek_karar = f"{no_kismi}{p_harfi}"

                                            if not gosterilecek_karar and p_numarasi:
                                                gosterilecek_karar = p_numarasi

                                            if gosterilecek_karar:
                                                p_format_match = re.search(r'(\d+)\s*[/]?\s*P', str(gosterilecek_karar), re.IGNORECASE)
                                                if p_format_match:
                                                    gosterilecek_karar = f"{p_format_match.group(1)}/P"
                                                else:
                                                    sadece_sayi = re.search(r'(\d+)', str(gosterilecek_karar))
                                                    gosterilecek_karar = f"{sadece_sayi.group(1)}/P" if sadece_sayi else str(gosterilecek_karar)
                                            else:
                                                gosterilecek_karar = "Belirtilmemiş"

                                            st.markdown(f"📜 **Karar Numarası:** {gosterilecek_karar}")
                                            
                                            karar_tarihi = sutun_degeri_al(k_row, ['Tarih', 'Data', 'Karar Tarihi'])
                                            if not karar_tarihi or str(karar_tarihi).strip().lower() in ["nan", "none", ""]: 
                                                date_match = re.search(r'(\d{2}[._\s]\d{2}[._\s]\d{4})', kaynak_belge_adi)
                                                if date_match:
                                                    karar_tarihi = date_match.group(1).replace('_', '.').replace('-', '.')
                                                else:
                                                    karar_tarihi = "Belirtilmemiş"
                                                
                                            st.markdown(f"📅 **Karar Tarihi:** {karar_tarihi}")
                                            st.markdown(f"📂 **Kaynak Belge (Ordin):** {kaynak_belge_adi}")
                                    else:
                                        is_m10 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
                                        madde_adi = "Madde 10" if is_m10 else "Madde 11"
                                        
                                        if p_numarasi and user_ordin_yil > 0:
                                            max_pub_ordin = max_ordin_m10.get(user_ordin_yil, 0) if is_m10 else max_ordin_m11.get(user_ordin_yil, 0)
                                            
                                            if max_pub_ordin > 0 and user_ordin_no == max_pub_ordin:
                                                st.warning(f"**{p_numarasi}**\n\nDosya durumunuzda bir karar numarası tespit edilmiştir. Sistem verilerine göre, **{user_ordin_yil}** yılı için yayımlanan en güncel **{madde_adi}** kararı tam olarak sizin numaranız olan **{max_pub_ordin}/{user_ordin_yil}**'dir.\n\nTeknik bir hata sonucu dosya numaranız ordin listesine eklenmemiş olabilir veya onay verilmemiş olup listeden çıkarılmış olabilirsiniz. Resmi tebligat ve ilerleyen duyuruları takip etmenizi öneririz.", icon="⚠️")
                                            elif max_pub_ordin > 0 and user_ordin_no < max_pub_ordin:
                                                st.error(f"**{p_numarasi}**\n\nSistem verilerine göre, **{user_ordin_yil}** yılı için yayımlanan en son **{madde_adi}** kararı **{max_pub_ordin}/{user_ordin_yil}** numarasıdır.\n\nSizin karar numaranız ({user_ordin_no}) bu yayımlanan kararların gerisinde kalmıştır veya listelere dahil edilmemiştir. Bu durum, dosyanızın maalesef **OLUMSUZ (RED)** sonuçlanmış olabileceğini göstermektedir. Lütfen kesin ve nihai sonuç için adresinize gelecek resmi tebligatı bekleyiniz.", icon="🚨")
                                            elif max_pub_ordin > 0 and user_ordin_no > max_pub_ordin:
                                                st.info(f"**{p_numarasi}**\n\nSistem verilerine göre, **{user_ordin_yil}** yılı için yayımlanan en son **{madde_adi}** kararı **{max_pub_ordin}/{user_ordin_yil}** numarasıdır.\n\nSizin karar numaranız ({user_ordin_no}) henüz bu sıraya ulaşmamıştır. Bu durum, dosyanızın büyük ihtimalle **OLUMLU (ONAY)** sonuçlandığını ve sıradaki listelerde yayımlanmak üzere beklediğini müjdelemektedir. Gelecek listeleri heyecanla takip edebilirsiniz! 🎉", icon="ℹ️")
                                            else:
                                                st.warning(f"**{p_numarasi}**\n\nDosyanız olumlu sonuçlanmış görünmektedir, ancak **{user_ordin_yil}** yılına ait resmi listeler henüz yayımlanmamıştır.", icon="⚠️")
                                        else:
                                            st.error("🔴 Dosyanız henüz resmi Karar (Ordin) listelerinde yayımlanmamıştır.", icon="❌")
                                        
                                        st.markdown("<br>", unsafe_allow_html=True)
                                        
                                        telegram_button_html = """
                                        <a href="https://telegram.me/vatandaslik_sorgulama_bot" target="_blank" style="
                                            display: block;
                                            width: 100%;
                                            text-align: center;
                                            background-color: #2AABEE;
                                            color: white;
                                            padding: 15px;
                                            border-radius: 8px;
                                            font-weight: 900;
                                            font-size: 18px;
                                            text-decoration: none;
                                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                                        ">
                                            🔔 Telegram Botu İle Beni Haberdar Et
                                        </a>
                                        """
                                        st.markdown(telegram_button_html, unsafe_allow_html=True)

                                st.markdown("<br>", unsafe_allow_html=True)
                        else:
                            st.error("❌ Girdiğiniz kriterlere uygun bir dosya bulunamadı. Lütfen dosya numaranızı ve yılını kontrol edip tekrar deneyin.")

# =========================================================
# 2. SEKME: HTML SORGULAMA ARACI
# =========================================================
with tab2:
    st.markdown("### Vatandaşlık Hakkı Ön Değerlendirmesi")
    st.write("Aşağıdaki aracı kullanarak atalarınızın göç bilgilerine göre Madde 10 veya Madde 11 kapsamında olup olmadığınızı inceleyebilirsiniz.")
    # components.html kullanılarak HTML kodu sorunsuzca çalıştırılır
    components.html(MADDE_SORGULAMA_HTML, height=850, scrolling=True)


# --- YASAL VE ALMANAK ALT BİLGİ (FOOTER) ---
footer_metni = """
<div style='color: gray; font-size: 0.9em; line-height: 1.5; margin-top: 30px;'>
    <div style='text-align: left; margin-bottom: 15px;'>
        <i>Bu platform, Romanya Adalet Bakanlığı Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan herkese açık dosya durum (Stadiu Dosar) ve karar (Ordin) listelerini tarayarak çalışan <b>bağımsız</b> bir otomasyon sistemidir. Platformumuzun Romanya Devleti veya herhangi bir resmi kurumla <b>hiçbir resmi bağı veya ortaklığı bulunmamaktadır.</b><br><br>
        Sistemde sunulan veriler tamamen <b>bilgilendirme amaçlıdır</b> ve hiçbir şekilde resmi tebligat, onay veya hukuki belge niteliği taşımaz. Veri senkronizasyonunda yaşanabilecek teknik gecikmelerden, hatalardan veya ANC listelerindeki tipografik yanlışlardan platform sorumlu tutulamaz. Nihai ve kesin teyit için her zaman resmi kurum kaynaklarını referans alınız.</i>
    </div>
    <div style='text-align: center;'>
        <span style='font-size: 1em;'><b>© 2026 Tasarım ve Geliştirme: <a href="mailto:aytekint@hotmail.com" style="color: #4F8BF9; text-decoration: none;">Aytekin Topçu</a></b></span>
    </div>
</div>
"""
st.markdown(footer_metni, unsafe_allow_html=True)