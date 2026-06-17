import streamlit as st
import pandas as pd
import re
import os

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Romanya Vatandaşlık Sorgulama",
    page_icon="https://flagcdn.com/w320/ro.png",
    layout="centered"
)

# --- VERİ YÜKLEME VE ÖNBELLEK ---
@st.cache_data
def veri_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        try:
            df = pd.read_excel(dosya_adi)
            df = df.fillna("")
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# 1. Dosya Durumunu Yükle
df_dosya = veri_yukle("dosyadurumu.xlsx")

# 2. Madde 10 ve Madde 11 Kararlarını Yükle ve Birleştir
df_karar_m10 = veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde10.xlsx")
df_karar_m11 = veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx")

karar_listesi = []
if not df_karar_m10.empty:
    karar_listesi.append(df_karar_m10)
if not df_karar_m11.empty:
    karar_listesi.append(df_karar_m11)

df_karar = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()

# --- GÜNCELLEME BİLGİLERİNİ PDF İSİMLERİNDEN ÇEKME MANTIĞI ---
def en_guncel_belge_bilgisi(df):
    if df.empty or 'Kaynak Belge' not in df.columns:
        return "Veri Yok", "Bilinmiyor"
    
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    
    unique_files['Parsed_Date'] = pd.to_datetime(
        unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], 
        format='%d.%m.%Y', 
        errors='coerce'
    )
    
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        latest_row = valid_files.sort_values(by='Parsed_Date', ascending=False).iloc[0]
        tarih_str = latest_row['Parsed_Date'].strftime('%d.%m.%Y')
        return latest_row['Kaynak Belge'], tarih_str
    elif not unique_files.empty:
        return unique_files.iloc[0]['Kaynak Belge'], "Tarih Bulunamadı"
    
    return "Veri Yok", "Bilinmiyor"

_, dosya_guncelleme_tarihi = en_guncel_belge_bilgisi(df_dosya)
m10_belge, m10_tarih = en_guncel_belge_bilgisi(df_karar_m10)
m11_belge, m11_tarih = en_guncel_belge_bilgisi(df_karar_m11)

# --- ARAYÜZ TASARIMI ---
st.title("Romanya Vatandaşlık Sorgulama")
st.markdown("Madde 10/11 kapsamındaki dosya durumunuzu (Stadiu Dosar) ve karar (Ordin) sonucunuzu tek ekranda görüntüleyin.")

st.info(f"""
🔄 **Dosya Durumu (Stadiu Dosar) Son Güncelleme:** {dosya_guncelleme_tarihi}

📄 **Sisteme Eklenen Son Kararlar:**
- **Madde 10:** {m10_belge} *(Güncelleme: {m10_tarih})*
- **Madde 11:** {m11_belge} *(Güncelleme: {m11_tarih})*
""")

st.markdown("---")

st.markdown("💡 **Örnek Arama Formatı:** 1234/2018 veya 1234/RD/2023")
aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 37064/2023")

if st.button("🔍 Dosyamı ve Kararımı Sorgula"):
    if not aranan_kelime:
        st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
    elif df_dosya.empty:
        st.error("Sistemde şu an 'Dosya Durumu' (dosyadurumu.xlsx) verisi bulunmuyor.")
    else:
        temiz_arama = aranan_kelime.strip().upper().replace(" ", "")
        
        # --- ZORUNLU FORMAT VE YIL KONTROLLERİ ---
        if "/" not in temiz_arama:
            st.warning("⚠️ Eksik giriş yaptınız. Lütfen sadece numara girmeyiniz; araya '/' işareti koyarak yılı da belirtiniz. (Örn: 1234/2023)")
        else:
            parcalar = temiz_arama.split("/")
            ilk_numara = parcalar[0]
            son_yil = parcalar[-1]
            
            # --- HEM SOLU HEM SAĞI AYNI ANDA KONTROL ET ---
            sol_gecerli = ilk_numara.isdigit()
            sag_gecerli = son_yil.isdigit() and len(son_yil) == 4
            
            if not sol_gecerli or not sag_gecerli:
                st.warning("⚠️ Hatalı giriş yaptınız. Lütfen '/' işaretinin solundaki dosya numarasının SADECE rakamlardan oluştuğuna ve sağındaki yıl kısmının tam 4 basamaklı bir sayı olduğuna emin olunuz. (Örn: 1234/2023)")
            
            # Kural 3: Yıl 2017'den BÜYÜK olmalı (2018 ve sonrası)
            elif int(son_yil) <= 2017:
                st.warning("⚠️ Sistem uyarısı: Girilen yıl 2017'den büyük olmalıdır. Lütfen 2018 veya daha güncel bir yıl giriniz.")
            
            else:
                # Tüm doğrulamaları geçen temiz sorgu tetikleniyor
                arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
                df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
                sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                
                if not sonuclar.empty:
                    st.success(f"✅ Dosyanız bulundu! Durum ve Karar bilgileri aşağıdadır:")
                    
                    for index, row in sonuclar.iterrows():
                        with st.container():
                            
                            # --- YENİ MİMARİ: Önce Karar listelerinde arama yapıyoruz ---
                            dosya_no_parcalar = str(row['Dosya No']).split('/')
                            ana_no = dosya_no_parcalar[0].strip()
                            ana_yil = dosya_no_parcalar[-1].strip()
                            
                            karar_bulundu_mu = False
                            k_row = None
                            
                            if not df_karar.empty:
                                karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
                                temiz_karar_metni = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
                                
                                # Gelişmiş Regex: Tam ve kusursuz eşleşme
                                karar_icin_regex = rf"(^|\D){ana_no}/([A-Z]+/)?{ana_yil}($|\D)"
                                karar_sonucu = df_karar[temiz_karar_metni.str.contains(karar_icin_regex, regex=True)]
                                
                                if not karar_sonucu.empty:
                                    karar_bulundu_mu = True
                                    k_row = karar_sonucu.iloc[0]

                            # --- Ekrana Çıktı Verme Kısmı ---
                            st.markdown(f"## 📂 DOSYA BİLGİLERİ: {row['Dosya No']}")
                            st.markdown(f"**📅 Başvuru Kayıt Tarihi:** {row['Başvuru Tarihi']}")
                            
                            if str(row['TERMEN']).strip() and str(row['TERMEN']).strip() != "-":
                                st.markdown(f"**⏳ Sonraki Aşama (TERMEN):** {row['TERMEN']}")
                                
                            solutie_metni = str(row['SOLUTIE']).strip()
                            p_numarasi = None
                            
                            if solutie_metni:
                                p_match = re.search(r'(\d{1,6})\s*/\s*P\s*/\s*(\d{4})', solutie_metni, re.IGNORECASE)
                                if p_match:
                                    p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"
                                    
                            # Akıllı SOLUTIE Gösterimi
                            if solutie_metni:
                                st.success(f"**📝 Karar / Durum (SOLUTIE):** {solutie_metni}")
                            else:
                                if karar_bulundu_mu:
                                    st.info("**📝 Karar / Durum (SOLUTIE):** ANC ana tablosunda boş (Beklemede) görünmesine rağmen, Karar (Ordin) listelerinde OLUMLU sonuç tespit edildi!")
                                else:
                                    st.warning("**📝 Karar / Durum (SOLUTIE):** Henüz bir karar/durum bilgisi girilmemiş (Beklemede).")
                                
                            st.caption(f"📌 Kaynak: {row['Kaynak Belge']}")
                            
                            st.markdown("---")
                            
                            st.markdown("## ⚖️ KARAR (ORDIN) DURUMU")
                            
                            if karar_bulundu_mu:
                                st.success(f"🎉 **TEBRİKLER! Kararınız Yayımlandı.**")
                                
                                # --- Karar Numarası ve PDF Kontrolü ---
                                gosterilecek_karar = p_numarasi
                                kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
                                
                                if not gosterilecek_karar:
                                    pdf_match = re.search(r'(\d+)[^\d]*P[^\d]*.*?(20\d{2})', kaynak_belge_adi, re.IGNORECASE)
                                    if pdf_match:
                                        gosterilecek_karar = f"{pdf_match.group(1)}/P/{pdf_match.group(2)}"
                                    else:
                                        gosterilecek_karar = "Belirtilmemiş (Dosya Karar Listesinde Bulundu)"
                                
                                # --- Copii Minori Arama ---
                                copii_bilgisi = ""
                                tum_satir_metni = " ".join([str(val) for val in k_row.values if str(val) != "nan"])
                                
                                copii_match = re.search(r'Copii\s*minori[^\d]*(\d+)', tum_satir_metni, re.IGNORECASE)
                                
                                if copii_match:
                                    cocuk_sayisi = copii_match.group(1)
                                    copii_bilgisi = f" &nbsp; | &nbsp; 👶 **Copii minori: {cocuk_sayisi}**"
                                else:
                                    for col in k_row.index:
                                        if 'copii' in str(col).lower() and str(k_row[col]).strip() and str(k_row[col]).strip() not in ["nan", "None", ""]:
                                            cocuk_sayisi = str(k_row[col]).strip()
                                            if cocuk_sayisi.replace('.', '', 1).isdigit():
                                                cocuk_sayisi = int(float(cocuk_sayisi))
                                            copii_bilgisi = f" &nbsp; | &nbsp; 👶 **Copii minori: {cocuk_sayisi}**"
                                            break
                                            
                                st.markdown(f"- **Karar Numarası:** {gosterilecek_karar}{copii_bilgisi}")
                                
                                if 'Tarih' in k_row and str(k_row['Tarih']).strip() and str(k_row['Tarih']).strip() != "nan":
                                    st.markdown(f"- **Karar Tarihi:** {k_row['Tarih']}")
                                    
                                st.markdown(f"- **Kaynak Belge:** {kaynak_belge_adi}")
                            else:
                                if p_numarasi:
                                    st.warning(f"⚠️ **Bilgi Notu:** Dosyanızın durum bölümünde bir onay kodu ({p_numarasi}) görünmektedir. **Muhtemelen dosyanız olumlu olarak çözümlenmiş ancak ANC tarafından henüz resmi bir 'Karar (Ordine)' listesi içinde yayımlanmamıştır.** Lütfen ilerleyen güncellemeleri takip ediniz.")
                                else:
                                    st.error("🔴 Dosyanız henüz Karar (Ordin) listelerinde yayımlanmamıştır (Beklemede).")
                                    
                    st.markdown("---")
                else:
                    st.error("❌ Girdiğiniz kriterlere uygun bir dosya bulunamadı. Lütfen dosya numaranızı ve yılını kontrol edip tekrar deneyin.")

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