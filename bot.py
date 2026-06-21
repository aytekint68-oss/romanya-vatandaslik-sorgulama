import pandas as pd
import re
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==========================================
# AYARLAR (KENDİ BİLGİLERİNİZİ BURAYA YAPIŞTIRIN)
# ==========================================
BOT_TOKEN = "8819617191:AAEYvGjIM7OO5PAqNqUKJiGeionzmNTlGZ8"
JSONBIN_ID = "6a37c90dda38895dfee67f47"
JSONBIN_KEY = "$2a$10$uPjGuKiKSQDQ/aefIBs66uxwscYlgeP/w0tRf79CpRSsLv3XwNn/S"

print("🤖 Akıllı Asistan Başlatılıyor...")

# --- BULUT HAFIZA (JSONBIN) FONKSİYONLARI ---
def get_takip_listesi():
    headers = {"X-Master-Key": JSONBIN_KEY}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest", headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {}).get("bekleyenler", [])
    except Exception as e:
        print("Bulut Hafıza okunamadı:", e)
    return []

def set_takip_listesi(liste):
    headers = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
    payload = {"bekleyenler": liste}
    try:
        requests.put(f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}", json=payload, headers=headers)
    except Exception as e:
        print("Bulut Hafıza güncellenemedi:", e)

# --- CSV YÜKLEME VE HAFIZA ---
hafiza = {
    'df_dosya': pd.DataFrame(), 'df_karar_m10': pd.DataFrame(),
    'df_karar_m11': pd.DataFrame(), 'df_karar_birlesik': pd.DataFrame(),
    'max_m10': {}, 'max_m11': {}, 'son_guncelleme': 0
}

def veri_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        try:
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False)
            if len(df.columns) < 2: df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False)
            return df.fillna("")
        except Exception:
            try:
                df = pd.read_csv(dosya_adi, sep=';', encoding='cp1254', low_memory=False)
                if len(df.columns) < 2: df = pd.read_csv(dosya_adi, sep=',', encoding='cp1254', low_memory=False)
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
    temp_df['Yil'], temp_df['No'] = pd.to_numeric(temp_df['Yil'], errors='coerce'), pd.to_numeric(temp_df['No'], errors='coerce')
    return temp_df.dropna().groupby('Yil')['No'].max().to_dict()

# --- MÜJDE DAĞITIM MOTORU ---
async def mujdeleri_dagit(app_context):
    df_karar = hafiza['df_karar_birlesik']
    if df_karar.empty: return

    bekleyenler = get_takip_listesi()
    if not bekleyenler: return

    kalan_bekleyenler = []
    degisiklik_var = False
    
    print(f"🔍 {len(bekleyenler)} kişi takip ediliyor. Yeni kararlar taranıyor...")

    for kisi in bekleyenler:
        chat_id = kisi['chat_id']
        dosya_tam = kisi['dosya_no']
        ana_no, ana_yil = dosya_tam.split('/')
        
        karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
        temiz_metin = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
        regex = rf"(^|\D){ana_no}/([A-Z]+/)?{ana_yil}($|\D)"
        
        if not df_karar[temiz_metin.str.contains(regex, regex=True)].empty:
            msg = f"🎉 <b>MÜJDE!</b> Takip ettiğiniz <b>{dosya_tam}</b> numaralı dosyanız onaylandı ve resmi listelerde yayımlandı!\n\nDetayları görmek için bana dosya numaranızı tekrar yazabilirsiniz."
            try:
                await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                degisiklik_var = True
                print(f"✅ {dosya_tam} dosyası için müjde gönderildi!")
            except Exception as e:
                print(f"Mesaj gönderilemedi: {e}")
                kalan_bekleyenler.append(kisi) 
        else:
            kalan_bekleyenler.append(kisi) 
            
    if degisiklik_var:
        set_takip_listesi(kalan_bekleyenler) 
        print("✅ Müjde dağıtımı tamamlandı, bulut güncellendi.")

def veritabanini_kontrol_et(app_context=None):
    ana_dosya = "dosyadurumu.zip"
    if not os.path.exists(ana_dosya): return
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
        
        if app_context:
            app_context.create_task(mujdeleri_dagit(app_context))

def en_guncel_belge_bilgisi(df):
    if df.empty or 'Kaynak Belge' not in df.columns: return "Veri Yok", "Bilinmiyor"
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    unique_files['Parsed_Date'] = pd.to_datetime(unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], format='%d.%m.%Y', errors='coerce')
    isimler_tarihsiz = unique_files['Kaynak Belge'].str.replace(r'\d{2}\.\d{2}\.\d{4}', '', regex=True)
    unique_files['Karar_No'] = pd.to_numeric(isimler_tarihsiz.str.extract(r'(\d{3,6})')[0], errors='coerce').fillna(0)
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    if not valid_files.empty:
        latest_row = valid_files.sort_values(by=['Parsed_Date', 'Karar_No'], ascending=[False, False]).iloc[0]
        return latest_row['Kaynak Belge'], latest_row['Parsed_Date'].strftime('%d.%m.%Y')
    elif not unique_files.empty:
        return unique_files.iloc[0]['Kaynak Belge'], "Tarih Bulunamadı"
    return "Veri Yok", "Bilinmiyor"

# İlk yükleme
veritabanini_kontrol_et()

# --- TELEGRAM MESAJLAŞMA MANTIĞI ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "⚖️ <i><b>Yasal Bilgilendirme:</b> Bu platform bağımsız bir otomasyon sistemidir. Veriler bilgilendirme amaçlıdır. Nihai teyit için resmi kaynakları referans alınız.</i>"
    )
    await update.message.reply_text(mesaj, parse_mode='HTML')

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context)
    aranan_kelime = update.message.text.strip()
    chat_id = update.message.chat_id
    df_dosya, df_karar = hafiza['df_dosya'], hafiza['df_karar_birlesik']
    
    if df_dosya.empty:
        await update.message.reply_text("❌ Sistemde veri bulunmuyor.")
        return

    if not re.fullmatch(r'[0-9/]+', aranan_kelime) or aranan_kelime.count("/") != 1:
        await update.message.reply_text("⚠️ <b>Hatalı format:</b> Lütfen araya sadece BİR adet '/' işareti koyunuz. Örn: 1234/2023", parse_mode='HTML')
        return
        
    parcalar = aranan_kelime.split("/")
    ilk_numara, son_yil = parcalar[0], parcalar[1]
    if not ilk_numara.isdigit() or int(ilk_numara) == 0 or len(son_yil) != 4 or not (2017 <= int(son_yil) <= 2026):
        await update.message.reply_text("⚠️ Sistem uyarısı: Geçersiz dosya numarası veya yıl.")
        return

    arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
    df_gecici = df_dosya.copy()
    df_gecici['Arama_Sutunu'] = df_gecici['Dosya No'].astype(str).str.strip()
    sonuclar = df_gecici[df_gecici['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)].copy()

    if sonuclar.empty:
        await update.message.reply_text("❌ <b>Bulunamadı:</b> Girdiğiniz kriterlere uygun dosya bulunamadı.", parse_mode='HTML')
        return

    # Mükerrer temizliği
    sonuclar['Tekil_Anahtar'] = sonuclar['Arama_Sutunu'].apply(lambda x: f"{str(x).split('/')[0].strip()}_{str(x).split('/')[-1].strip()}")
    sonuclar = sonuclar.drop_duplicates(subset=['Tekil_Anahtar'])

    for index, row in sonuclar.iterrows():
        ana_no, ana_yil = str(row['Tekil_Anahtar']).split('_')[0], str(row['Tekil_Anahtar']).split('_')[-1]
        dosya_no_standart = f"{ana_no}/{ana_yil}"
        
        karar_bulundu_mu, k_row, onaylanan_kisi_sayisi = False, None, 0
        
        if not df_karar.empty:
            karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
            temiz_karar_metni = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
            karar_sonucu = df_karar[temiz_karar_metni.str.contains(rf"(^|\D){ana_no}/([A-Z]+/)?{ana_yil}($|\D)", regex=True)]
            
            if not karar_sonucu.empty:
                karar_bulundu_mu, k_row, onaylanan_kisi_sayisi = True, karar_sonucu.iloc[0], len(karar_sonucu)

        solutie_metni = str(row['SOLUTIE']).strip()
        p_numarasi, user_ordin_no, user_ordin_yil = None, 0, 0
        if solutie_metni:
            p_match = re.search(r'(\d{1,6})\s*[/]?\s*P\s*[/]?\s*(\d{4})', solutie_metni, re.IGNORECASE)
            if p_match: p_numarasi, user_ordin_no, user_ordin_yil = f"{p_match.group(1)}/P/{p_match.group(2)}", int(p_match.group(1)), int(p_match.group(2))

        kaynak_dosya_metni = str(row.get('Kaynak Belge', ''))
        termen_metni = str(row.get('TERMEN', '')).strip()
        termen = termen_metni if termen_metni and termen_metni != "-" else "Belirtilmemiş"
        kurum_notu = solutie_metni if solutie_metni else ("Sistemde not düşülmemiş ancak listelerde onay tespit edildi!" if karar_bulundu_mu else "Henüz bir not girilmemiş (İnceleme Bekliyor).")

        yanit = (
            f"📂 <b>DOSYA BİLGİLERİ</b>\n<b>No:</b> {row['Arama_Sutunu']}\n━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Başvuru Tarihi:</b> {row.get('Başvuru Tarihi', '')}\n⏳ <b>Sonraki Aşama (Termen):</b> {termen}\n\n"
            f"📝 <b>Kurum Notu:</b>\n{kurum_notu}\n\n📂 <b>Kaynak:</b> {kaynak_dosya_metni}\n━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>KARAR (ORDIN) DURUMU</b>\n"
        )

        buton_ekle = False
        zaten_takipte = False

        if karar_bulundu_mu:
            kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
            gosterilecek_karar = p_numarasi
            if not gosterilecek_karar:
                pdf_match = re.search(r'(\d+)[^\d]*P[^\d]*.*?(20\d{2})', kaynak_belge_adi, re.IGNORECASE)
                gosterilecek_karar = f"{pdf_match.group(1)}/P/{pdf_match.group(2)}" if pdf_match else "Belirtilmemiş"
            
            karar_tarihi = k_row.get('Tarih', 'Belirtilmemiş')
            if pd.isna(karar_tarihi) or str(karar_tarihi).strip() in ["nan", "None", ""]: karar_tarihi = "Belirtilmemiş"
                
            toplam_cocuk = 0
            for _, kr in karar_sonucu.iterrows():
                tum_satir_metni = " ".join([str(val) for val in kr.values if str(val) not in ["nan", "None", ""]])
                copii_match = re.search(r'Copii\s*minori[^\d]*(\d+)', tum_satir_metni, re.IGNORECASE)
                if copii_match: toplam_cocuk += int(copii_match.group(1))
                else:
                    for col in kr.index:
                        if 'copii' in str(col).lower() and str(kr[col]).strip() not in ["nan", "None", ""]:
                            c_val = str(kr[col]).strip()
                            if c_val.replace('.', '', 1).isdigit():
                                toplam_cocuk += int(float(c_val))
                                break

            yetiskin_satiri = f"👥 <b>Reşit Kişi Sayısı:</b> {onaylanan_kisi_sayisi}\n" if onaylanan_kisi_sayisi > 1 else ""
            cocuk_satiri = f"👶 <b>Çocuk (Copii Minori):</b> {toplam_cocuk}\n" if toplam_cocuk > 0 else ""

            yanit += f"🎉 <b>TEBRİKLER! Kararınız yayımlandı.</b>\n\n📜 <b>Karar No:</b> {gosterilecek_karar}\n📅 <b>Tarih:</b> {karar_tarihi}\n{yetiskin_satiri}{cocuk_satiri}📂 <b>Kaynak:</b> {kaynak_belge_adi}"
        else:
            # 🌟 YENİ: Karar çıkmadıysa bulut listesini kontrol et
            takip_listesi = get_takip_listesi()
            if any(k['chat_id'] == chat_id and k['dosya_no'] == dosya_no_standart for k in takip_listesi):
                zaten_takipte = True
            else:
                buton_ekle = True

            is_m10 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
            madde_adi = "Madde 10" if is_m10 else "Madde 11"
            
            if p_numarasi and user_ordin_yil > 0:
                max_pub_ordin = hafiza['max_m10'].get(user_ordin_yil, 0) if is_m10 else hafiza['max_m11'].get(user_ordin_yil, 0)
                if max_pub_ordin > 0 and user_ordin_no == max_pub_ordin:
                    yanit += f"⚠️ <b>{p_numarasi}</b>\n\nDosya durumunuzda karar tespit edildi. Sistemdeki son {madde_adi} kararı sizin numaranızdır ({max_pub_ordin}/{user_ordin_yil}). Listelere eklenmemiş olabilirsiniz, resmi tebligatı bekleyiniz."
                elif max_pub_ordin > 0 and user_ordin_no < max_pub_ordin:
                    yanit += f"🚨 <b>{p_numarasi}</b>\n\nSistemdeki son {madde_adi} kararı {max_pub_ordin}/{user_ordin_yil}. Sizin kararınız ({user_ordin_no}) geride kalmış. Dosyanız OLUMSUZ sonuçlanmış olabilir. Tebligatı bekleyiniz."
                elif max_pub_ordin > 0 and user_ordin_no > max_pub_ordin:
                    yanit += f"ℹ️ <b>{p_numarasi}</b>\n\nSistemdeki son {madde_adi} kararı {max_pub_ordin}/{user_ordin_yil}. Numaranız ({user_ordin_no}) sıraya ulaşmamış. Dosyanız büyük ihtimalle OLUMLU sonuçlandı, yayımlanması bekleniyor! 🎉"
                else:
                    yanit += f"⚠️ <b>{p_numarasi}</b>\n\nDosyanız olumlu sonuçlanmış ancak {user_ordin_yil} yılı listeleri yayımlanmamıştır."
            else:
                yanit += "❌ 🔴 Dosyanız henüz resmi Karar (Ordin) listelerinde yayımlanmamıştır."

            # 🌟 YENİ: Eğer takipteyse yasal bilginin hemen üstüne (veya durumun altına) ibareyi ekle
            if zaten_takipte:
                yanit += "\n\n💚 <b>Dosyanız takip listemizde!</b> Yeni listeler yüklendiğinde bir gelişme olursa size otomatik mesaj göndereceğim. 🔔"

        # BUTON MANTIĞI
        reply_markup = None
        if buton_ekle:
            klavye = [[InlineKeyboardButton("🔔 Karar Çıkınca Haberdar Et", callback_data=f"takip_{ana_no}_{ana_yil}")]]
            reply_markup = InlineKeyboardMarkup(klavye)

        await update.message.reply_text(yanit, parse_mode='HTML', reply_markup=reply_markup)

# --- BUTON TIKLAMA (TAKİP SİSTEMİ) ---
async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("takip_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no = f"{ilk_no}/{son_yil}"
        chat_id = query.message.chat_id
        
        liste = get_takip_listesi()
        
        if any(k['chat_id'] == chat_id and k['dosya_no'] == dosya_no for k in liste):
            await query.edit_message_reply_markup(reply_markup=None)
            await context.bot.send_message(chat_id=chat_id, text=f"✅ {dosya_no} numaralı dosya zaten takip listenizde!")
            return
            
        liste.append({"chat_id": chat_id, "dosya_no": dosya_no})
        set_takip_listesi(liste)
        
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(chat_id=chat_id, text=f"🔔 <b>Harika!</b> {dosya_no} numaralı dosyanızı takibe aldım. Yeni listelerde yayımlandığı an size otomatik müjde mesajı göndereceğim.", parse_mode='HTML')

# --- BOTU BAŞLAT ---
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def post_init(application: Application):
        veritabanini_kontrol_et(application)
        
    app.post_init = post_init
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    
    app.run_polling()