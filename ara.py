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

# --- TAM OTOMATİK VERİ YÜKLEME VE ÖNBELLEK (ZIP VE CSV İÇİN OPTİMİZE) ---
@st.cache_data
def veri_yukle(dosya_adi, degistirme_zamani):
    if os.path.exists(dosya_adi):
        try:
            # Önce noktalı virgül (Avrupa/TR Excel CSV) formatını dener
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False)
            
            # Eğer dosya yanlış ayrılmışsa (tek sütun çıkarsa), virgül formatına geçer
            if len(df.columns) < 2:
                df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False)
                
            return df.fillna("")
        except Exception:
            try:
                # B Planı: Windows Türkçe (cp1254) karakter kodlaması ile dener
                df = pd.read_csv(dosya_adi, sep=';', encoding='cp1254', low_memory=False)
                if len(df.columns) < 2:
                    df = pd.read_csv(dosya_adi, sep=',', encoding='cp1254', low_memory=False)
                return df.fillna("")
            except Exception:
                return pd.DataFrame()
    return pd.DataFrame()

def akilli_veri_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        guncelleme_saati = os.path.getmtime(dosya_adi)
        return veri_yukle(dosya_adi, guncelleme_saati)
    return pd.DataFrame()

# =========================================================
# DOSYALARI BURADAN YÜKLÜYORUZ (BÜYÜK DOSYA ARTIK .ZIP)
# =========================================================
df_dosya = akilli_veri_yukle("dosyadurumu.zip") 
df_karar_m10 = akilli_veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde10.csv")
df_karar_m11 = akilli_veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde11.csv")

karar_listesi = []
if not df_karar_m10.empty:
    karar_listesi.append(df_karar_m10)
if not df_karar_m11.empty:
    karar_listesi.append(df_karar_m11)

df_karar = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()

# --- 🌟 GÜNCELLEME: ÇOKLU BELGE GÖSTEREN YENİ NESİL TARAMA MANTIĞI 🌟 ---
def en_guncel_belgeleri_getir(df):
    if df.empty or 'Kaynak Belge' not in df.columns:
        return ["Veri Yok"], "Bilinmiyor"
    
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    
    unique_files['Parsed_Date'] = pd.to_datetime(
        unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], 
        format='%d.%m.%Y', 
        errors='coerce'
    )
    
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        # 1. En yeni tarihi bul
        max_date = valid_files['Parsed_Date'].max()
        # 2. O tarihe ait TÜM dosyaları listeye çek
        latest_files_df = valid_files[valid_files['Parsed_Date'] == max_date]
        dosya_listesi = latest_files_df['Kaynak Belge'].tolist()
        tarih_str = max_date.strftime('%d.%m.%Y')
        
        return dosya_listesi, tarih_str
    elif not unique_files.empty:
        return [unique_files.iloc[0]['Kaynak Belge']], "Tarih Bulunamadı"
    
    return ["Veri Yok"], "Bilinmiyor"

_, dosya_guncelleme_tarihi = en_guncel_belgeleri_getir(df_dosya)
m10_belgeler_listesi, m10_tarih = en_guncel_belgeleri_getir(df_karar_m10)
m11_belgeler_listesi, m11_tarih = en_guncel_belgeleri_getir(df_karar_m11)

# Listeleri Streamlit arayüzü için alt alta güzel görünecek formata sokalım
m10_belgeler_metni = "<br>".join([f"&nbsp;&nbsp;&nbsp;&nbsp;📄 <code>{b}</code>" for b in m10_belgeler_listesi]) if m10_belgeler_listesi else "&nbsp;&nbsp;&nbsp;&nbsp;Veri Yok"
m11_belgeler_metni = "<br>".join([f"&nbsp;&nbsp;&nbsp;&nbsp;📄 <code>{b}</code>" for b in m11_belgeler_listesi]) if m11_belgeler_listesi else "&nbsp;&nbsp;&nbsp;&nbsp;Veri Yok"

# --- SUNUCU DOSTU ŞİMŞEK HIZINDA (VEKTÖREL) MAKSİMUM ORDİN HESAPLAMA MOTORU ---
@st.cache_data
def max_ordin_hesapla_vektorel(df_k):
    if df_k.empty:
        return {}
        
    ordin_sutunlari = [col for col in df_k.columns if 'ordin' in str(col).lower() or 'karar' in str(col).lower()]
    if not ordin_sutunlari:
        return {}
        
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

max_ordin_m10 = max_ordin_hesapla_vektorel(df_karar_m10)
max_ordin_m11 = max_ordin_hesapla_vektorel(df_karar_m11)

# --- ARAYÜZ TASARIMI ---
st.title("Romanya Vatandaşlık Sorgulama")
st.markdown("Madde 10/11 kapsamındaki dosya durumunuzu (**Stadiu Dosar**) ve karar (**Ordin**) sonucunuzu tek ekranda görüntüleyin.")

# 🌟 ÇOKLU BELGELERİN YER ALDIĞI GÜNCELLENMİŞ BİLGİ KUTUSU 🌟
st.info(f"""
🔄 **Dosya Durumu (Stadiu Dosar) Son Güncelleme:** {dosya_guncelleme_tarihi}

📑 **Sisteme Eklenen Son Kararlar:**<br>
**Madde 10:**<br>{m10_belgeler_metni}<br><br>
**Madde 11:**<br>{m11_belgeler_metni}
""", icon="ℹ️")

st.markdown("---")

st.markdown("💡 **Örnek Arama Formatı:** 1234/2017 veya 37064/2023")
aranan_kelime = st.text_input("Dosya Numaranız (No/Yıl):", placeholder="Örn: 37064/2023")

if st.button("🔍 Dosyamı ve Kararımı Sorgula"):
    if not aranan_kelime:
        st.warning("Lütfen arama yapmak için bir dosya numarası girin.")
    elif df_dosya.empty:
        st.error("Sistemde şu an 'Dosya Durumu' verisi bulunmuyor.")
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
                            karar_icin_regex = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
                            karar_sonucu = df_karar[temiz_karar_metni.str.contains(karar_icin_regex, regex=True, case=False)]
                            
                            if not karar_sonucu.empty:
                                karar_bulundu_mu = True
                                k_row = karar_sonucu.iloc[0]

                        solutie_metni = str(row['SOLUTIE']).strip()
                        p_numarasi = None
                        user_ordin_no = 0
                        user_ordin_yil = 0
                        
                        if solutie_metni:
                            p_match = re.search(r'(\d{1,6})\s*[/]?\s*P\s*[/]?\s*(\d{4})', solutie_metni, re.IGNORECASE)
                            if p_match:
                                p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"
                                user_ordin_no = int(p_match.group(1))
                                user_ordin_yil = int(p_match.group(2))

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
                                    
                            kaynak_dosya_metni = str(row.get('Kaynak Belge', ''))
                            st.markdown(f"📂 **Kaynak Belge (Stadiu Dosar):** {kaynak_dosya_metni}")
                            st.divider()
                            
                            # 4. BÖLÜM: KARAR (ORDIN)
                            st.markdown("<h4 style='text-align: center;'>⚖️ KARAR (ORDIN) DURUMU</h4>", unsafe_allow_html=True)
                            
                            if karar_bulundu_mu:
                                st.success("🎉 **TEBRİKLER! Kararınız yayımlandı.**", icon="✅")
                                
                                with st.container(border=True):
                                    kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
                                    gosterilecek_karar = p_numarasi
                                    
                                    # CSV Sütunlarından kontrol et
                                    if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                                        k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower() or 'no' in str(col).lower()]
                                        if k_ordin_cols:
                                            val = str(k_row[k_ordin_cols[0]]).strip()
                                            if val and val.lower() not in ['nan', 'none', '']:
                                                gosterilecek_karar = val

                                    # Eğer hâlâ yoksa PDF dosya isminden numarayı ayıkla
                                    if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                                        pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)', kaynak_belge_adi, re.IGNORECASE)
                                        if pdf_match:
                                            gosterilecek_karar = pdf_match.group(1)

                                    # 🌟 FORMAT STANDARTLAŞTIRICI (XX/P/YYYY) 🌟
                                    if gosterilecek_karar and str(gosterilecek_karar).strip().lower() not in ['nan', 'none', '', 'belirtilmemiş']:
                                        clean_no_match = re.search(r'(\d+)', str(gosterilecek_karar))
                                        if clean_no_match:
                                            pure_no = clean_no_match.group(1)
                                            yil_match = re.search(r'\b(202\d)\b', kaynak_belge_adi)
                                            if not yil_match:
                                                yil_match = re.search(r'\b(202\d)\b', str(k_row.get('Tarih', '')))
                                            pure_year = yil_match.group(1) if yil_match else "2026"
                                            gosterilecek_karar = f"{pure_no}/P/{pure_year}"
                                        else:
                                            gosterilecek_karar = "Belirtilmemiş"
                                    else:
                                        gosterilecek_karar = "Belirtilmemiş"

                                    st.markdown(f"📜 **Karar Numarası:** {gosterilecek_karar}")
                                    
                                    karar_tarihi = k_row.get('Tarih', 'Belirtilmemiş')
                                    if pd.isna(karar_tarihi) or str(karar_tarihi).strip() in ["nan", "None", ""]: 
                                        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', kaynak_belge_adi)
                                        karar_tarihi = date_match.group(1) if date_match else "Belirtilmemiş"
                                        
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
                                <a href="https://t.me/vatandaslik_sorgulama_bot" target="_blank" style="
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