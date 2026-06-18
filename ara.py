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
    
    # 1. Aşama: Dosya isminden Gün.Ay.Yıl formatındaki tarihi çek
    unique_files['Parsed_Date'] = pd.to_datetime(
        unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], 
        format='%d.%m.%Y', 
        errors='coerce'
    )
    
    # 2. Aşama: Aynı tarihte birden fazla karar varsa büyük numaralıyı bul (Örn 2050 vs 2054)
    # Karışıklık olmaması için isimdeki tarihi siliyoruz
    isimler_tarihsiz = unique_files['Kaynak Belge'].str.replace(r'\d{2}\.\d{2}\.\d{4}', '', regex=True)
    
    # Kalan metinden (art11 vb. ufak rakamları es geçmek için) 3 veya daha fazla haneli ana dosya numarasını çekiyoruz
    unique_files['Karar_No'] = isimler_tarihsiz.str.extract(r'(\d{3,6})')[0]
    unique_files['Karar_No'] = pd.to_numeric(unique_files['Karar_No'], errors='coerce').fillna(0)
    
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        # 3. Aşama: Önce Tarihe göre, sonra Karar Numarasına göre azalan (en büyük/en yeni) olarak sırala
        latest_row = valid_files.sort_values(by=['Parsed_Date', 'Karar_No'], ascending=[False, False]).iloc[0]
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

st.markdown("💡 **Örnek Arama Formatı:** 1234/2017 veya 37064/2023")
aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 37064/2023")

if st.button("🔍 Dosyamı ve Kararımı Sorgula"):
    if not aranan_kelime:
        st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
    elif df_dosya.empty:
        st.error("Sistemde şu an 'Dosya Durumu' (dosyadurumu.xlsx) verisi bulunmuyor.")
    else:
        temiz_arama = aranan_kelime.strip()
        
        # --- KONTROLLER ---
        if not re.fullmatch(r'[0-9/]+', temiz_arama):
            st.warning("⚠️ Hatalı giriş yaptınız. Lütfen SADECE rakam ve '/' işareti kullanınız. Örn: 1234/2023")
        elif temiz_arama.count("/") != 1:
            st.warning("⚠️ Hatalı format. Lütfen araya sadece BİR adet '/' işareti koyunuz. Örn: 1234/2023")
        else:
            parcalar = temiz_arama.split("/")
            ilk_numara = parcalar[0]
            son_yil = parcalar[1]
            
            if len(ilk_numara) == 0:
                st.warning("⚠️ Lütfen '/' işaretinden önce dosya numaranızı yazınız. Örn: 1234/2023")
            elif int(ilk_numara) == 0:
                st.warning("⚠️ Hatalı giriş yaptınız. Dosya numarası '0' olamaz.")
            elif len(son_yil) != 4:
                st.warning("⚠️ Hatalı giriş yaptınız. Yıl kısmı KESİNLİKLE 4 basamaklı olmalıdır.")
            elif not (2017 <= int(son_yil) <= 2026):
                st.warning("⚠️ Sistem uyarısı: Dosya yılı yalnızca 2017 ile 2026 yılları arasında olabilir.")
            else:
                arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
                df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
                sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                
                if not sonuclar.empty:
                    st.success(f"✅ Dosyanız bulundu! Durum ve Karar bilgileri aşağıdadır:")
                    
                    for index, row in sonuclar.iterrows():
                        
                        dosya_no_parcalar = str(row['Dosya No']).split('/')
                        ana_no = dosya_no_parcalar[0].strip()
                        ana_yil = dosya_no_parcalar[-1].strip()
                        
                        karar_bulundu_mu = False
                        k_row = None
                        
                        if not df_karar.empty:
                            karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
                            temiz_karar_metni = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
                            karar_icin_regex = rf"(^|\D){ana_no}/([A-Z]+/)?{ana_yil}($|\D)"
                            karar_sonucu = df_karar[temiz_karar_metni.str.contains(karar_icin_regex, regex=True)]
                            
                            if not karar_sonucu.empty:
                                karar_bulundu_mu = True
                                k_row = karar_sonucu.iloc[0]

                        solutie_metni = str(row['SOLUTIE']).strip()
                        p_numarasi = None
                        
                        if solutie_metni:
                            p_match = re.search(r'(\d{1,6})\s*/\s*P\s*/\s*(\d{4})', solutie_metni, re.IGNORECASE)
                            if p_match:
                                p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"

                        # =========================================================
                        # --- YENİ PROFESYONEL VE ESTETİK KART TASARIMI ---
                        # =========================================================
                        with st.container(border=True):
                            
                            # 1. BÖLÜM: ÜST BAŞLIK (Dosya No)
                            st.markdown(f"<h3 style='text-align: center; color: #4F8BF9; margin-bottom: 0;'>📂 DOSYA BİLGİLERİ</h3>", unsafe_allow_html=True)
                            st.markdown(f"<h4 style='text-align: center; margin-top: 0;'>No: {row['Dosya No']}</h4>", unsafe_allow_html=True)
                            st.divider()
                            
                            # 2. BÖLÜM: İKİLİ KOLON (Tarih ve Termen)
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**📅 Başvuru Tarihi:**<br>{row['Başvuru Tarihi']}", unsafe_allow_html=True)
                            with col2:
                                termen_metni = str(row['TERMEN']).strip()
                                if termen_metni and termen_metni != "-":
                                    st.markdown(f"**⏳ Sonraki Aşama (Termen):**<br>{termen_metni}", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**⏳ Sonraki Aşama (Termen):**<br>Belirtilmemiş", unsafe_allow_html=True)
                                    
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # 3. BÖLÜM: DURUM (SOLUTIE)
                            if solutie_metni:
                                st.info(f"**📝 Kurum Notu (Solutie):** {solutie_metni}", icon="ℹ️")
                            else:
                                if karar_bulundu_mu:
                                    st.info("**📝 Kurum Notu (Solutie):** Sistemde not düşülmemiş ancak resmi Karar (Ordin) listelerinde sonuç tespit edildi!", icon="ℹ️")
                                else:
                                    st.warning("**📝 Kurum Notu (Solutie):** Henüz bir not girilmemiş (İnceleme Bekliyor).", icon="⏳")
                                    
                            st.caption(f"📌 Kaynak: {row['Kaynak Belge']}")
                            st.divider()
                            
                            # 4. BÖLÜM: KARAR (ORDIN)
                            st.markdown("<h4 style='text-align: center;'>⚖️ KARAR (ORDIN) DURUMU</h4>", unsafe_allow_html=True)
                            
                            if karar_bulundu_mu:
                                st.success("🎉 **TEBRİKLER! Kararınız yayımlandı.**", icon="✅")
                                
                                # Karar detaylarını şık ve sade bir alt kutuya alıyoruz
                                with st.container(border=True):
                                    gosterilecek_karar = p_numarasi
                                    kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
                                    
                                    if not gosterilecek_karar:
                                        pdf_match = re.search(r'(\d+)[^\d]*P[^\d]*.*?(20\d{2})', kaynak_belge_adi, re.IGNORECASE)
                                        if pdf_match:
                                            gosterilecek_karar = f"{pdf_match.group(1)}/P/{pdf_match.group(2)}"
                                        else:
                                            gosterilecek_karar = "Belirtilmemiş"
                                            
                                    st.markdown(f"📜 **Karar Numarası:** {gosterilecek_karar}")
                                    
                                    if 'Tarih' in k_row and str(k_row['Tarih']).strip() and str(k_row['Tarih']).strip() != "nan":
                                        st.markdown(f"📅 **Karar Tarihi:** {k_row['Tarih']}")
                                        
                                    # Çocuk sayısı arama (Temizlenmiş liste görünümü)
                                    tum_satir_metni = " ".join([str(val) for val in k_row.values if str(val) != "nan"])
                                    copii_match = re.search(r'Copii\s*minori[^\d]*(\d+)', tum_satir_metni, re.IGNORECASE)
                                    
                                    if copii_match:
                                        st.markdown(f"👶 **Çocuk (Copii Minori):** {copii_match.group(1)}")
                                    else:
                                        for col in k_row.index:
                                            if 'copii' in str(col).lower() and str(k_row[col]).strip() and str(k_row[col]).strip() not in ["nan", "None", ""]:
                                                cocuk_sayisi = str(k_row[col]).strip()
                                                if cocuk_sayisi.replace('.', '', 1).isdigit():
                                                    st.markdown(f"👶 **Çocuk (Copii Minori):** {int(float(cocuk_sayisi))}")
                                                break
                                                
                                    st.markdown(f"📂 **Kaynak Belge:** {kaynak_belge_adi}")
                            else:
                                if p_numarasi:
                                    st.warning(f"**Onay Kodu Tespit Edildi ({p_numarasi})**\n\nDosyanız olumlu sonuçlanmış görünmektedir, ancak resmi listelerde henüz yayımlanmamıştır.", icon="⚠️")
                                else:
                                    st.error("🔴 Dosyanız henüz resmi Karar (Ordin) listelerinde yayımlanmamıştır.", icon="❌")
                        st.markdown("<br>", unsafe_allow_html=True)
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