import streamlit as st
import pandas as pd

# Sayfa ayarları
st.set_page_config(page_title="Romanya Vatandaşlık Sorgulama", page_icon="🛂", layout="centered")

# Veriyi hızlı yüklemek için önbelleğe (cache) alıyoruz
@st.cache_data
def veri_yukle():
    df = pd.read_excel("Romanya_Vatandaslik_Tum_Veriler.xlsx")
    df = df.fillna("") # Boş alanları temizle
    df['Dosya Numarası'] = df['Dosya Numarası'].astype(str).str.strip()
    return df

df = veri_yukle()

# Arayüz Tasarımı
st.title("Romanya Vatandaşlık Karar Sorgulama - Madde 10")
st.write("2019 - 2026 yılları arasında yayımlanan kararnamelerde (Ordin) dosya numaranızı anında bulun.")

st.divider()

# --- YENİ EKLENEN BÖLÜM: SON YÜKLENEN KARAR PANOSU ---
# Tablomuz en güncelden eskiye sıralı olduğu için ilk satırı (index 0) alıyoruz
if not df.empty:
    son_tarih = df.iloc[0]['Tarih']
    son_pdf = df.iloc[0]['Kaynak Belge']
    
    # Şık bir bilgi kutusu içinde gösteriyoruz
    st.info(f"""
    📢 **Sisteme Eklenen Son Karar:**
    * **Tarih:** {son_tarih}
    * **Belge Adı:** {son_pdf}
    * 🔗 **[Resmi Sayfada Görüntüle](https://cetatenie.just.ro/ordine-articolul-10/)**
    """)

st.divider()

# Arama Kutusu
aranan_dosya = st.text_input("🔍 Dosya Numaranızı Girin (Örn: 7026/2023):")

if aranan_dosya:
    aranan_temiz = aranan_dosya.strip()
    # Sadece birebir eşleşen kayıtları getirir
    sonuclar = df[df['Dosya Numarası'] == aranan_temiz].copy()
    
    if not sonuclar.empty:
        st.success(f"🎉 Tebrikler! {aranan_temiz} numaralı dosyanız için {len(sonuclar)} kayıt bulundu.")
        
        # Kırık link hatasını sıfırlamak için doğrudan resmi ana sayfaya yönlendiriyoruz
        sonuclar['Direkt Link'] = "https://cetatenie.just.ro/ordine-articolul-10/"
        
        # Tabloyu ekrana bas
        st.dataframe(
            sonuclar, 
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

# Syntax hatasını önlemek için tek satırda yazıldı
st.caption("Not: Bu sistem resmi olmayan, verileri kolaylaştırmak amacıyla oluşturulmuş bir arama motorudur. İlgili belgeyi 'Resmi Sayfaya Git' linkine tıkladıktan sonra Romanya devlet sitesindeki listeden bulabilirsiniz.")