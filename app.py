import streamlit as st
import pandas as pd

# Sayfa ayarları
st.set_page_config(page_title="Romanya Vatandaşlık Sorgulama", page_icon="🛂", layout="centered")

# Veriyi hızlı yüklemek için önbelleğe (cache) alıyoruz
@st.cache_data
def veri_yukle():
    # 1. Madde 10 Verilerini Oku
    try:
        df10 = pd.read_excel("Romanya_Vatandaslik_Tum_Veriler.xlsx")
        df10['Kategori'] = "Madde 10"
        df10['Link'] = "https://cetatenie.just.ro/ordine-articolul-10/"
    except:
        df10 = pd.DataFrame()
        
    # 2. Madde 11 Verilerini Oku
    try:
        df11 = pd.read_excel("Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx")
        df11['Kategori'] = "Madde 11"
        df11['Link'] = "https://cetatenie.just.ro/ordine-articolul-1-1/"
    except:
        df11 = pd.DataFrame()

    # İki tabloyu alt alta birleştir
    df_tum = pd.concat([df10, df11], ignore_index=True)
    
    if not df_tum.empty:
        df_tum = df_tum.fillna("") # Boş alanları temizle
        df_tum['Dosya Numarası'] = df_tum['Dosya Numarası'].astype(str).str.strip()
        
    return df_tum, df10, df11

df, df10, df11 = veri_yukle()

# Arayüz Tasarımı
st.title("Romanya Vatandaşlık Karar Sorgulama - Madde 10/11")
st.write("2019 - 2026 yılları arasında yayımlanan kararnamelerde (Madde 10 ve Madde 11) dosya numaranızı anında bulun.")

st.divider()
# --- İKİLİ SON KARAR PANOSU (MADDE 10 VE MADDE 11) ---
st.markdown("📢 **Sisteme Eklenen Son Kararlar:**")
col1, col2 = st.columns(2)

# Madde 10 için son karar kutusu
with col1:
    if not df10.empty:
        son10_tarih = df10.iloc[0]['Tarih']
        son10_pdf = df10.iloc[0]['Kaynak Belge']
        st.info(f"**Madde 10 (Art. 10)**\n\n📅 **Tarih:** {son10_tarih}\n\n📄 **Belge:** {son10_pdf}\n\n🔗 **[Resmi Sayfaya Git](https://cetatenie.just.ro/ordine-articolul-10/)**")
    else:
        st.warning("Madde 10 Excel dosyası okunamadı.")

# Madde 11 için son karar kutusu
with col2:
    if not df11.empty:
        son11_tarih = df11.iloc[0]['Tarih']
        son11_pdf = df11.iloc[0]['Kaynak Belge']
        st.info(f"**Madde 11 (Art. 11)**\n\n📅 **Tarih:** {son11_tarih}\n\n📄 **Belge:** {son11_pdf}\n\n🔗 **[Resmi Sayfaya Git](https://cetatenie.just.ro/ordine-articolul-1-1/)**")
    else:
        st.error("Madde 11 dosyası bulunamadı! Lütfen dosya adının tam olarak 'Romanya_Vatandaslik_Tum_Veriler_Madde11.xlsx' olduğundan ve GitHub'a yüklendiğinden emin olun.")

st.divider()

# Arama Kutusu
aranan_dosya = st.text_input("🔍 Dosya Numaranızı Girin (Örn: 7026/2023):")

if aranan_dosya:
    aranan_temiz = aranan_dosya.strip()
    sonuclar = df[df['Dosya Numarası'] == aranan_temiz].copy()
    
    if not sonuclar.empty:
        st.success(f"🎉 Tebrikler! {aranan_temiz} numaralı dosyanız için {len(sonuclar)} kayıt bulundu.")
        
        # Linkleri tablo için düzenle
        sonuclar['Direkt Link'] = sonuclar['Link']
        gosterilecek_tablo = sonuclar.drop(columns=['Link']) # Arka plan linkini gizle
        
        # Tabloyu ekrana bas
        st.dataframe(
            gosterilecek_tablo, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Direkt Link": st.column_config.LinkColumn(
                    "📄 Kararı Görüntüle", 
                    display_text="Resmi Sayfaya Git 🔗" 
                )
            }
        )
    else:
        st.error(f"Maalesef '{aranan_temiz}' numaralı dosya bulunamadı. Lütfen numarayı (Yıl/Dosya No şeklinde) eksiksiz yazdığınızdan emin olun.")
else:
    st.info("Arama yapmak için yukarıdaki kutuya dosya numaranızı tam olarak yazın.")

st.write("") 

# İletişim Kutusu
with st.expander("💡 Görüş, Öneri ve İletişim"):
    st.write("Bu sistem, vatandaşlık sürecinde bekleyenlere kolaylık sağlamak amacıyla tamamen gönüllü olarak geliştirilmiştir.")
    st.write("Sistemle ilgili karşılaştığınız hataları, eklenmesini istediğiniz özellikleri veya genel görüşlerinizi iletmekten lütfen çekinmeyin.")
    st.markdown("**Bize Ulaşın:** [sizin.epostaniz@gmail.com](mailto:sizin.epostaniz@gmail.com)")

st.caption("Not: Bu sistem resmi olmayan, verileri kolaylaştırmak amacıyla oluşturulmuş bir arama motorudur. İlgili belgeyi 'Resmi Sayfaya Git' linkine tıkladıktan sonra Romanya devlet sitesindeki listeden bulabilirsiniz.")