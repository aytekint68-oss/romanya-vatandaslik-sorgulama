import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

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

# Karar dosyalarını tek bir havuzda topluyoruz (Hata vermemesi için boş olmayanları birleştiriyoruz)
karar_listesi = []
if not df_karar_m10.empty:
    karar_listesi.append(df_karar_m10)
if not df_karar_m11.empty:
    karar_listesi.append(df_karar_m11)

df_karar = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()


# --- SİSTEM GÜNCELLEME BİLGİLERİNİ ÇEKME ---
dosya_guncelleme_tarihi = "Bilinmiyor"
son_karar_belgesi = "Bilinmiyor"

# Dosya durumu güncelleme tarihi
if os.path.exists("dosyadurumu.xlsx"):
    timestamp = os.path.getmtime("dosyadurumu.xlsx")
    dosya_guncelleme_tarihi = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")

# En son güncellenen karar dosyasının adını bulma
if not df_karar.empty and 'Kaynak Belge' in df_karar.columns:
    # İki tablodan gelen en üstteki veriyi (en yeni belgeyi) alır
    son_karar_belgesi = df_karar['Kaynak Belge'].iloc[0]


# --- ARAYÜZ TASARIMI ---
st.title("Romanya Vatandaşlık Sorgulama Merkezi")
st.markdown("Madde 10/11 kapsamındaki dosya durumunuzu ve karar (Ordin) sonucunuzu tek ekranda görüntüleyin.")

# Üst Bilgi Paneli (Güncelleme Detayları)
st.info(f"🔄 **Dosya Durumu Son Güncelleme:** {dosya_guncelleme_tarihi}\n\n📄 **Sisteme Eklenen Son Karar Listesi:** {son_karar_belgesi}")

st.markdown("---")

# Arama Kutusu
st.markdown("💡 **Örnek Arama Formatı:** 1234/2017 veya 1234/RD/2017")
aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 514/2026")

if st.button("🔍 Dosyamı ve Kararımı Sorgula"):
    if not aranan_kelime:
        st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
    elif df_dosya.empty:
        st.error("Sistemde şu an 'Dosya Durumu' (dosyadurumu.xlsx) verisi bulunmuyor.")
    else:
        # Arama Kriterini Temizle
        temiz_arama = aranan_kelime.strip().upper().replace(" ", "")
        
        # Akıllı & Tam Eşleşme Mantığı (Dosya Durumu İçin)
        if "/" in temiz_arama:
            parcalar = temiz_arama.split("/")
            ilk_numara = parcalar[0]
            son_yil = parcalar[-1]
            arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
            # Sütun adının güvenliği için str.strip() uygulayarak arıyoruz
            df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
            sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
        else:
            arama_kriteri = f"^{temiz_arama}/"
            df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
            sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
        
        # --- SONUÇLARI GÖSTERME (AŞAMA 1: DOSYA DURUMU) ---
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
                        
                        # SOLUTIE içindeki 'P' numarasını (Örn: 1153/P/2018) yakalayan dedektif kod
                        p_match = re.search(r'(\d{1,6})\s*/\s*P\s*/\s*(\d{4})', solutie_metni, re.IGNORECASE)
                        if p_match:
                            # Tertemiz hale getir
                            p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"
                    else:
                        st.error("**📝 Karar / Durum (SOLUTIE):** Henüz bir karar/durum bilgisi girilmemiş (Beklemede).")
                        
                    st.caption(f"📌 Kaynak: {row['Kaynak Belge']}")
                    
                    st.markdown("---")
                    
                    # --- SONUÇLARI GÖSTERME (AŞAMA 2: KARAR KONTROLÜ) ---
                    st.markdown("## ⚖️ KARAR (ORDİN) DURUMU")
                    
                    if p_numarasi:
                        st.markdown(f"Sistem, dosyanızın SOLUTIE bölümünde **{p_numarasi}** numaralı bir karar kodu tespit etti. Madde 10 ve Madde 11 listeleri taranıyor...")
                        
                        if df_karar.empty:
                            st.warning("Sistemde şu an Karar (Ordin) tabloları bulunmuyor.")
                        else:
                            # Karar tablosunda numarayı aramak için sütun adını tespit ediyoruz (Örn: Dosya Numarasi, Dosya No vb.)
                            karar_sutunu = 'Dosya Numarasi' if 'Dosya Numarasi' in df_karar.columns else ('Dosya No' if 'Dosya No' in df_karar.columns else df_karar.columns[0])
                            
                            # Tam eşleşme arar
                            karar_sonucu = df_karar[df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.contains(f"^{p_numarasi.replace('/', '/')}$", flags=re.IGNORECASE, regex=True)]
                            
                            if not karar_sonucu.empty:
                                k_row = karar_sonucu.iloc[0]
                                st.success(f"🎉 **TEBRİKLER! Kararınız Yayımlandı.**")
                                st.markdown(f"- **Karar Numarası:** {p_numarasi}")
                                
                                # Tarih bilgisi varsa ekle
                                if 'Tarih' in k_row and str(k_row['Tarih']).strip():
                                    st.markdown(f"- **Karar Tarihi:** {k_row['Tarih']}")
                                    
                                st.markdown(f"- **Kaynak Belge:** {k_row.get('Kaynak Belge', 'Bilinmiyor')}")
                            else:
                                # Karar listesinde bulunamazsa verilecek özel bilgi notu
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