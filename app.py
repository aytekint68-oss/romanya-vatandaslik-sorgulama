import streamlit as st
import pandas as pd
import os # Dosya tarihlerini kontrol etmek için eklendi

# Sayfa ayarları
st.set_page_config(page_title="Romanya Vatandaşlık Sorgulama", page_icon="🛂", layout="centered")

# Excel dosyalarının son değiştirilme tarihlerini alıyoruz
def dosya_tarihi_getir(dosya_adi):
    if os.path.exists(dosya_adi):
        return os.path.getmtime(dosya_adi)
    return 0

tarih10 = dosya_tarihi_getir("Romanya_Vatandaslik_Tum_Veriler.xlsx")
tarih11 = dosya_tarihi_getir("Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx")

# Fonksiyona bu tarihleri parametre olarak veriyoruz. 
# Tarih değiştiği an Streamlit önbelleği (cache) otomatik olarak kırılır!
@st.cache_data
def veri_yukle(t10, t11):
    # 1. Madde 10 Verilerini Oku
    try:
        df10 = pd.read_excel("Romanya_Vatandaslik_Tum_Veriler.xlsx")
        df10['Kategori'] = "Madde 10"
        df10['Link'] = "https://cetatenie.just.ro/ordine-articolul-10/"
    except Exception as e:
        df10 = pd.DataFrame()
        
    # 2. Madde 11 Verilerini Oku
    try:
        df11 = pd.read_excel("Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx")
        df11['Kategori'] = "Madde 11"
        df11['Link'] = "https://cetatenie.just.ro/ordine-articolul-1-1/"
    except Exception as e:
        df11 = pd.DataFrame()

    # İki tabloyu alt alta birleştir
    df_tum = pd.concat([df10, df11], ignore_index=True)
    
    if not df_tum.empty:
        df_tum = df_tum.fillna("") # Boş alanları temizle
        df_tum['Dosya Numarası'] = df_tum['Dosya Numarası'].astype(str).str.strip()
        
    return df_tum, df10, df11

# Tarih parametrelerini içeri gönderiyoruz
df, df10, df11 = veri_yukle(tarih10, tarih11)

# --- BUNDAN SONRASI ARAYÜZ KODLARINIZLA BİREBİR AYNI KALACAK ---

# --- ARAYÜZ TASARIMI ---
st.title("Romanya Vatandaşlık Karar Sorgulama")

# YENİ AÇIKLAMA METİNLERİ
st.markdown("**Madde 10:** 2019 - 2026, **Madde 11:** 2018 - 2026 yılları arasında yayımlanan kararnamelerde dosya numaranızı anında bulun.")
st.info("⚠️ **Bilgilendirme:** Sadece vatandaşlık onayı alanlar arama sonuçlarında bulunabilir. Henüz onay almamış olan dosyalar aramada görünmez.")

st.divider()

# İKİLİ SON KARAR PANOSU (MADDE 10 VE MADDE 11)
st.markdown("📢 **Sisteme Eklenen Son Kararlar:**")
col1, col2 = st.columns(2)

with col1:
    if not df10.empty:
        son10_tarih = df10.iloc[0]['Tarih']
        son10_pdf = df10.iloc[0]['Kaynak Belge']
        st.success(f"**Madde 10 (Art. 10)**\n\n📅 **Tarih:** {son10_tarih}\n\n📄 **Belge:** {son10_pdf}\n\n🔗 **[Resmi Sayfaya Git](https://cetatenie.just.ro/ordine-articolul-10/)**")

with col2:
    if not df11.empty:
        son11_tarih = df11.iloc[0]['Tarih']
        son11_pdf = df11.iloc[0]['Kaynak Belge']
        st.success(f"**Madde 11 (Art. 11)**\n\n📅 **Tarih:** {son11_tarih}\n\n📄 **Belge:** {son11_pdf}\n\n🔗 **[Resmi Sayfaya Git](https://cetatenie.just.ro/ordine-articolul-1-1/)**")

st.divider()

# ARAMA KUTUSU
aranan_dosya = st.text_input("🔍 Dosya Numaranızı Girin (Örn: 7026/2023):")

if aranan_dosya:
    aranan_temiz = aranan_dosya.strip()
    sonuclar = df[df['Dosya Numarası'] == aranan_temiz].copy()
    
    if not sonuclar.empty:
        st.success(f"🎉 Tebrikler! {aranan_temiz} numaralı dosyanız için {len(sonuclar)} kayıt bulundu.")
        
        sonuclar['Direkt Link'] = sonuclar['Link']
        gosterilecek_tablo = sonuclar.drop(columns=['Link'])
        
        st.dataframe(
            gosterilecek_tablo, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Direkt Link": st.column_config.LinkColumn("📄 Kararı Görüntüle", display_text="Resmi Sayfaya Git 🔗")
            }
        )
    else:
        st.error(f"Maalesef '{aranan_temiz}' numaralı dosya bulunamadı. Lütfen numarayı (Dosya No/Yıl şeklinde) eksiksiz yazdığınızdan emin olun veya henüz onaylanmadığını dikkate alın.")
else:
    st.info("Arama yapmak için yukarıdaki kutuya dosya numaranızı tam olarak yazın.")

st.write("") 

# İLETİŞİM KUTUSU
with st.expander("💡 Görüş, Öneri ve İletişim"):
    st.write("Bu sistem, vatandaşlık sürecinde bekleyenlere kolaylık sağlamak amacıyla tamamen gönüllü olarak geliştirilmiştir.")
    st.markdown("**Bize Ulaşın:** [aytekint68@gmail.com](mailto:aytekint68@gmail)")

st.caption("Yasal Uyarı : Bu proje tamamen açık kaynaklı ve sivil bir girişim olup, verileri kolayca taramak amacıyla oluşturulmuş gayriresmi bir arama motorudur. Sonuçlar hiçbir hukuki bağlayıcılık taşımaz. Resmi ve kesin kararlar her zaman sadece cetatenie.just.ro adresinden teyit edilmelidir.")