import pandas as pd
import re
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==========================================
# TELEGRAM BOT TOKENİNİZİ BURAYA YAPIŞTIRIN
# ==========================================
BOT_TOKEN = "8819617191:AAEYvGjIM7OO5PAqNqUKJiGeionzmNTlGZ8"

print("🤖 Telegram Botu Başlatılıyor, Veritabanları Hazırlanıyor...")

# --- HAFIZA VE OTOMATİK GÜNCELLEME YÖNETİMİ ---
hafiza = {
    'df_dosya': pd.DataFrame(),
    'df_karar_m10': pd.DataFrame(),
    'df_karar_m11': pd.DataFrame(),
    'df_karar_birlesik': pd.DataFrame(),
    'max_m10': {},
    'max_m11': {},
    'son_guncelleme': 0
}

def veri_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        try:
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False)
            if len(df.columns) < 2:
                df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False)
            return df.fillna("")
        except Exception:
            try:
                df = pd.read_csv(dosya_adi, sep=';', encoding='cp1254', low_memory=False)
                if len(df.columns) < 2:
                    df = pd.read_csv(dosya_adi, sep=',', encoding='cp1254', low_memory=False)
                return df.fillna("")
            except Exception:
                return pd.DataFrame()
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

def veritabanini_kontrol_et_ve_yukle():
    ana_dosya = "dosyadurumu.zip"
    if not os.path.exists(ana_dosya):
        return
    
    mevcut_saat = os.path.getmtime(ana_dosya)
    if mevcut_saat > hafiza['son_guncelleme']:
        print("🔄 Yeni dosya tespit edildi. Veritabanı Telegram için güncelleniyor...")
        hafiza['df_dosya'] = veri_yukle("dosyadurumu.zip")
        hafiza['df_karar_m10'] = veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde10.csv")
        hafiza['df_karar_m11'] = veri_yukle("Romanya_Vatandaslik_Tum_Veriler_Madde11.csv")
        
        karar_listesi = []
        if not hafiza['df_karar_m10'].empty: karar_listesi.append(hafiza['df_karar_m10'])
        if not hafiza['df_karar_m11'].empty: karar_listesi.append(hafiza['df_karar_m11'])
        hafiza['df_karar_birlesik'] = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()
        
        hafiza['max_m10'] = max_ordin_hesapla_vektorel(hafiza['df_karar_m10'])
        hafiza['max_m11'] = max_ordin_hesapla_vektorel(hafiza['df_karar_m11'])
        hafiza['son_guncelleme'] = mevcut_saat
        print("✅ Güncelleme tamamlandı.")

# --- EN GÜNCEL BELGE BİLGİSİNİ ÇEKEN FONKSİYON ---
def en_guncel_belge_bilgisi(df):
    if df.empty or 'Kaynak Belge' not in df.columns:
        return "Veri Yok", "Bilinmiyor"
    
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    
    unique_files['Parsed_Date'] = pd.to_datetime(
        unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], 
        format='%d.%m.%Y', 
        errors='coerce'
    )
    
    isimler_tarihsiz = unique_files['Kaynak Belge'].str.replace(r'\d{2}\.\d{2}\.\d{4}', '', regex=True)
    
    unique_files['Karar_No'] = isimler_tarihsiz.str.extract(r'(\d{3,6})')[0]
    unique_files['Karar_No'] = pd.to_numeric(unique_files['Karar_No'], errors='coerce').fillna(0)
    
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        latest_row = valid_files.sort_values(by=['Parsed_Date', 'Karar_No'], ascending=[False, False]).iloc[0]
        tarih_str = latest_row['Parsed_Date'].strftime('%d.%m.%Y')
        return latest_row['Kaynak Belge'], tarih_str
    elif not unique_files.empty:
        return unique_files.iloc[0]['Kaynak Belge'], "Tarih Bulunamadı"
    
    return "Veri Yok", "Bilinmiyor"

# İlk yüklemeyi yap
veritabanini_kontrol_et_ve_yukle()

# --- TELEGRAM BOT KOMUTLARI ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Veritabanı bilgilerini al
    _, dosya_guncelleme_tarihi = en_guncel_belge_bilgisi(hafiza['df_dosya'])
    m10_belge, _ = en_guncel_belge_bilgisi(hafiza['df_karar_m10'])
    m11_belge, _ = en_guncel_belge_bilgisi(hafiza['df_karar_m11'])

    mesaj = (
        "🇹🇩 <b>Romanya Vatandaşlık Sorgulama Botuna Hoş Geldiniz!</b>\n\n"
        "Madde 10/11 kapsamındaki dosya durumunuzu (Stadiu Dosar) ve karar (Ordin) sonucunuzu buradan sorgulayabilirsiniz.\n\n"
        f"<b>Dosya Durumu (Stadiu Dosar) Son Güncelleme:</b> {dosya_guncelleme_tarihi}\n"
        f"📄 <b>Sisteme Eklenen Son Kararlar:</b>\n"
        f"<b>Madde 10:</b> {m10_belge}\n"
        f"<b>Madde 11:</b> {m11_belge}\n\n"
        "💡 <b>Kullanım:</b>\n"
        "Sadece dosya numaranızı ve yılını yazıp gönderin.\n"
        "<i>Örn: 37064/2023</i> veya <i>1234/2017</i>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚖️ <i><b>Yasal Bilgilendirme:</b> Bu platform, Romanya Adalet Bakanlığı Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan herkese açık dosya durum (Stadiu Dosar) ve karar (Ordin) listelerini tarayarak çalışan <b>bağımsız</b> bir otomasyon sistemidir. Romanya Devleti veya herhangi bir resmi kurumla hiçbir resmi bağı veya ortaklığı bulunmamaktadır.\n\n"
        "Sistemde sunulan veriler tamamen <b>bilgilendirme amaçlıdır</b> ve hiçbir şekilde resmi tebligat, onay veya hukuki belge niteliği taşımaz. Veri senkronizasyonunda yaşanabilecek teknik gecikmelerden, hatalardan veya ANC listelerindeki tipografik yanlışlardan platform sorumlu tutulamaz. Nihai ve kesin teyit için her zaman resmi kurum kaynaklarını referans alınız.</i>"
    )
    await update.message.reply_text(mesaj, parse_mode='HTML')

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Her sorgudan önce veritabanı değişmiş mi diye kontrol et (Şimşek hızında)
    veritabanini_kontrol_et_ve_yukle()
    
    aranan_kelime = update.message.text.strip()
    df_dosya = hafiza['df_dosya']
    df_karar = hafiza['df_karar_birlesik']
    
    if df_dosya.empty:
        await update.message.reply_text("❌ Sistemde şu an veri bulunmuyor. Lütfen daha sonra tekrar deneyin.")
        return

    # --- KONTROLLER ---
    if not re.fullmatch(r'[0-9/]+', aranan_kelime):
        await update.message.reply_text("⚠️ <b>Hatalı giriş:</b> Lütfen SADECE rakam ve '/' işareti kullanınız. Örn: 1234/2023", parse_mode='HTML')
        return
    if aranan_kelime.count("/") != 1:
        await update.message.reply_text("⚠️ <b>Hatalı format:</b> Lütfen araya sadece BİR adet '/' işareti koyunuz. Örn: 1234/2023", parse_mode='HTML')
        return
        
    parcalar = aranan_kelime.split("/")
    ilk_numara, son_yil = parcalar[0], parcalar[1]
    
    if len(ilk_numara) == 0 or int(ilk_numara) == 0:
        await update.message.reply_text("⚠️ Hatalı giriş. Dosya numarası '0' veya boş olamaz.")
        return
    if len(son_yil) != 4 or not (2017 <= int(son_yil) <= 2026):
        await update.message.reply_text("⚠️ Sistem uyarısı: Yıl KESİNLİKLE 4 basamaklı ve 2017-2026 arasında olmalıdır.")
        return

    # --- ARAMA İŞLEMİ ---
    arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
    df_dosya['Arama_Sutunu'] = df_dosya['Dosya No'].astype(str).str.strip()
    sonuclar = df_dosya[df_dosya['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]

    if sonuclar.empty:
        await update.message.reply_text("❌ <b>Bulunamadı:</b> Girdiğiniz kriterlere uygun bir dosya bulunamadı. Lütfen kontrol edip tekrar deneyin.", parse_mode='HTML')
        return

    # Sonuç bulunduysa döngüyle mesajı oluştur
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
        p_numarasi, user_ordin_no, user_ordin_yil = None, 0, 0
        
        if solutie_metni:
            p_match = re.search(r'(\d{1,6})\s*[/]?\s*P\s*[/]?\s*(\d{4})', solutie_metni, re.IGNORECASE)
            if p_match:
                p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"
                user_ordin_no = int(p_match.group(1))
                user_ordin_yil = int(p_match.group(2))

        kaynak_dosya_metni = str(row.get('Kaynak Belge', ''))
        termen_metni = str(row.get('TERMEN', '')).strip()
        termen = termen_metni if termen_metni and termen_metni != "-" else "Belirtilmemiş"
        
        kurum_notu = solutie_metni if solutie_metni else ("Sistemde not düşülmemiş ancak resmi listelerde sonuç tespit edildi!" if karar_bulundu_mu else "Henüz bir not girilmemiş (İnceleme Bekliyor).")

        # --- MESAJI İNŞA ET (HTML) ---
        yanit = (
            f"📂 <b>DOSYA BİLGİLERİ</b>\n"
            f"<b>No:</b> {row['Dosya No']}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Başvuru Tarihi:</b> {row.get('Başvuru Tarihi', '')}\n"
            f"⏳ <b>Sonraki Aşama (Termen):</b> {termen}\n\n"
            f"📝 <b>Kurum Notu (Solutie):</b>\n{kurum_notu}\n\n"
            f"📂 <b>Kaynak Belge:</b> {kaynak_dosya_metni}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>KARAR (ORDIN) DURUMU</b>\n"
        )

        if karar_bulundu_mu:
            gosterilecek_karar = p_numarasi
            kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
            if not gosterilecek_karar:
                pdf_match = re.search(r'(\d+)[^\d]*P[^\d]*.*?(20\d{2})', kaynak_belge_adi, re.IGNORECASE)
                gosterilecek_karar = f"{pdf_match.group(1)}/P/{pdf_match.group(2)}" if pdf_match else "Belirtilmemiş"
            
            karar_tarihi = k_row.get('Tarih', '')
            if pd.isna(karar_tarihi) or str(karar_tarihi).strip() == "nan":
                karar_tarihi = "Belirtilmemiş"
                
            # Çocuk sayısı arama
            tum_satir_metni = " ".join([str(val) for val in k_row.values if str(val) != "nan"])
            copii_match = re.search(r'Copii\s*minori[^\d]*(\d+)', tum_satir_metni, re.IGNORECASE)
            cocuk = copii_match.group(1) if copii_match else "Bulunamadı"
            if cocuk == "Bulunamadı":
                for col in k_row.index:
                    if 'copii' in str(col).lower() and str(k_row[col]).strip() not in ["nan", "None", ""]:
                        c_val = str(k_row[col]).strip()
                        if c_val.replace('.', '', 1).isdigit():
                            cocuk = str(int(float(c_val)))
                            break

            # Eğer çocuk bulunamazsa, çocuk satırını komple gizle
            cocuk_satiri = f"👶 <b>Çocuk (Copii Minori):</b> {cocuk}\n" if cocuk != "Bulunamadı" else ""

            yanit += (
                f"🎉 <b>TEBRİKLER! Kararınız yayımlandı.</b>\n\n"
                f"📜 <b>Karar Numarası:</b> {gosterilecek_karar}\n"
                f"📅 <b>Karar Tarihi:</b> {karar_tarihi}\n"
                f"{cocuk_satiri}"
                f"📂 <b>Kaynak Belge:</b> {kaynak_belge_adi}"
            )
        else:
            is_m10 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
            madde_adi = "Madde 10" if is_m10 else "Madde 11"
            
            if p_numarasi and user_ordin_yil > 0:
                max_pub_ordin = hafiza['max_m10'].get(user_ordin_yil, 0) if is_m10 else hafiza['max_m11'].get(user_ordin_yil, 0)
                
                if max_pub_ordin > 0 and user_ordin_no == max_pub_ordin:
                    yanit += f"⚠️ <b>{p_numarasi}</b>\n\nDosya durumunuzda bir karar numarası tespit edilmiştir. Sistem verilerine göre, <b>{user_ordin_yil}</b> yılı için yayımlanan en güncel <b>{madde_adi}</b> kararı tam olarak sizin numaranız olan <b>{max_pub_ordin}/{user_ordin_yil}</b>'dir.\n\nTeknik bir hata sonucu dosya numaranız ordin listesine eklenmemiş olabilir veya onay verilmemiş olup listeden çıkarılmış olabilirsiniz. Resmi tebligat ve ilerleyen duyuruları takip etmenizi öneririz."
                elif max_pub_ordin > 0 and user_ordin_no < max_pub_ordin:
                    yanit += f"🚨 <b>{p_numarasi}</b>\n\nSistem verilerine göre, <b>{user_ordin_yil}</b> yılı için yayımlanan en son <b>{madde_adi}</b> kararı <b>{max_pub_ordin}/{user_ordin_yil}</b> numarasıdır.\n\nSizin karar numaranız ({user_ordin_no}) bu yayımlanan kararların gerisinde kalmıştır veya listelere dahil edilmemiştir. Bu durum, dosyanızın maalesef <b>OLUMSUZ (RED)</b> sonuçlanmış olabileceğini göstermektedir. Lütfen kesin ve nihai sonuç için adresinize gelecek resmi tebligatı bekleyiniz."
                elif max_pub_ordin > 0 and user_ordin_no > max_pub_ordin:
                    yanit += f"ℹ️ <b>{p_numarasi}</b>\n\nSistem verilerine göre, <b>{user_ordin_yil}</b> yılı için yayımlanan en son <b>{madde_adi}</b> kararı <b>{max_pub_ordin}/{user_ordin_yil}</b> numarasıdır.\n\nSizin karar numaranız ({user_ordin_no}) henüz bu sıraya ulaşmamıştır. Bu durum, dosyanızın büyük ihtimalle <b>OLUMLU (ONAY)</b> sonuçlandığını ve sıradaki listelerde yayımlanmak üzere beklediğini müjdelemektedir. Gelecek listeleri heyecanla takip edebilirsiniz! 🎉"
                else:
                    yanit += f"⚠️ <b>{p_numarasi}</b>\n\nDosyanız olumlu sonuçlanmış görünmektedir, ancak <b>{user_ordin_yil}</b> yılına ait resmi listeler henüz yayımlanmamıştır."
            else:
                yanit += "❌ 🔴 Dosyanız henüz resmi Karar (Ordin) listelerinde yayımlanmamıştır."

        await update.message.reply_text(yanit, parse_mode='HTML')

# --- BOTU ÇALIŞTIR ---
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Komut ve Mesajları Bağla
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    
    print("✅ Bot başarıyla ayağa kalktı! Telegram üzerinden mesaj gönderebilirsiniz.")
    app.run_polling()