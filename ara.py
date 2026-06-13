import streamlit as st
import pandas as pd
import re
import os

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Romanya Vatandaşlık Dosya ve Karar Sorgulama",
    page_icon="🇷🇴",
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
df_karar_m10 = veri_yukle("Romanya_Vatandaslik_Tum_Veriler.xlsx")
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
st.markdown("Madde 10/11 kapsamındaki dosya durumunuzu ve karar (Ordine) sonucunuzu tek ekranda görüntüleyin.")

st.info(f"""
🔄 **Dosya Durumu Son Güncelleme:** {dosya_guncelleme_tarihi}

📄 **Sisteme Eklenen Son Kararlar:**
- **Madde 10:** {m10_belge} *(Güncelleme: {m10_tarih})*
- **Madde 11:** {m11_belge} *(Güncelleme: {m11_tarih})*
""")

st.markdown("---")

st.markdown("💡 **Örnek Arama Formatı:** 1234/2017 veya 1234/RD/2017")
aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 514/2026")

if st.button("🔍 Dosyamı ve Kararımı Sorgula"):
    if not aranan_kelime:
        st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
    elif df_dosya.empty:
        st.error("Sistemde şu an 'Dosya Durumu' (dosyadurumu.xlsx) verisi bulunmuyor.")
    else:
        temiz_arama = aranan_kelime.strip().upper().replace(" ", "")
        
        if "/" in temiz_arama:
            parcalar = temiz_arama.split("/")
            ilk_numara = parcalar[0]
            son_yil = parcalar[-1]
            arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
            df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
            sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
        else:
            arama_kriteri = f"^{temiz_arama}/"
            df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
            sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
        
        if not sonuclar.empty:
            st.success(f"✅ Dosyanız bulundu! Durum ve Karar bilgileri aşağıdadır:")
            
            for index, row in sonuclar.iterrows():
                with st.container():
                    st.markdown(f"## 📂 DOSYA BİLGİLERİ: {row['Dosya No']}")
                    st.markdown(f"**📅 Başvuru Kayıt Tarihi:** {row['Başvuru Tarihi']}")
                    
                    if str(row['TERMEN']).strip() and str(row['TERMEN']).strip() != "-":
                        st.markdown(f"**⏳ Sonraki Aşama (TERMEN):** {row['TERMEN']}")
                        
                    solutie_metni = str(row['SOLUTIE']).strip()
                    p_numarasi = None
                    
                    if solutie_metni:
                        st.success(f"**📝 Karar / Durum (SOLUTIE):** {solutie_metni}")
                        
                        p_match = re.search(r'(\d{1,6})\s*/\s*P\s*/\s*(\d{4})', solutie_metni, re.IGNORECASE)
                        if p_match:
                            p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"
                    else:
                        st.error("**📝 Karar / Durum (SOLUTIE):** Henüz bir karar/durum bilgisi girilmemiş (Beklemede).")
                        
                    st.caption(f"📌 Kaynak: {row['Kaynak Belge']}")
                    
                    st.markdown("---")
                    
                    st.markdown("## ⚖️ KARAR (ORDINE) DURUMU")
                    
                    if p_numarasi:
                        st.markdown(f"Sistem, dosyanızın SOLUTIE bölümünde **{p_numarasi}** numaralı bir onay kodu tespit etti. Karar listeleri taranıyor...")
                        
                        if df_karar.empty:
                            st.warning("Sistemde şu an Karar (Ordin) tabloları bulunmuyor.")
                        else:
                            # GÜNCELLEME: P numarasını değil, kullanıcının ANA başvuru numarasını Karar Excel'inde arıyoruz.
                            # Örn: 14852/RD/2022'den 14852 ve 2022'yi ayıkla
                            dosya_no_parcalar = str(row['Dosya No']).split('/')
                            ana_no = dosya_no_parcalar[0].strip()
                            ana_yil = dosya_no_parcalar[-1].strip()
                            karar_icin_regex = f"^{ana_no}/.*{ana_yil}$"
                            
                            # Excel'deki "Dosya No" sütununu otomatik bul ve içinde ara
                            karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
                            
                            karar_sonucu = df_karar[df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.contains(karar_icin_regex, flags=re.IGNORECASE, regex=True)]
                            
                            if not karar_sonucu.empty:
                                k_row = karar_sonucu.iloc[0]
                                st.success(f"🎉 **TEBRİKLER! Kararınız Yayımlandı.**")
                                st.markdown(f"- **Karar Numarası:** {p_numarasi}")
                                
                                if 'Tarih' in k_row and str(k_row['Tarih']).strip():
                                    st.markdown(f"- **Karar Tarihi:** {k_row['Tarih']}")
                                    
                                st.markdown(f"- **Kaynak Belge:** {k_row.get('Kaynak Belge', 'Bilinmiyor')}")
                            else:
                                st.warning(f"⚠️ **Bilgi Notu:** Dosyanızın durum bölümünde bir onay kodu ({p_numarasi}) görünmektedir. **Muhtemelen dosyanız olumlu olarak çözümlenmiş ancak ANC tarafından henüz resmi bir 'Karar (Ordin)' listesi içinde yayımlanmamıştır.** Lütfen ilerleyen güncellemeleri takip ediniz.")
                                
                    else:
                        if solutie_metni:
                            st.info("Bu dosyaya ait bir 'P' (Ordin) numarası tespit edilmedi.")
                        else:
                            st.info("Dosyanız beklemede olduğu için henüz bir karar aşamasına geçilmemiştir.")
                            
            st.markdown("---")
        else:
            st.error("❌ Girdiğiniz kriterlere uygun bir dosya bulunamadı. Lütfen dosya numaranızı ve yılını kontrol edip tekrar deneyin.")

# Alt Bilgi
footer_metni = """
<div style='text-align: center; color: gray; font-size: 0.9em; line-height: 1.5;'>
    <i>Bu platform, Romanya Adalet Bakanlığı Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan resmi listeleri baz alarak otomatik çalışmaktadır.<br>
    Veriler bilgilendirme amaçlıdır. Kesin teyit için resmi kurum kaynaklarını referans alınız.</i>
</div>
"""
st.markdown(footer_metni, unsafe_allow_html=True)