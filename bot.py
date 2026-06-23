import pandas as pd
import re
import os
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==========================================
# GÜVENLİ AYARLAR (ŞİFRELER SUNUCUDAN OKUNUR)
# ==========================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
JSONBIN_ID = os.getenv("JSONBIN_BIN_ID")
JSONBIN_KEY = os.getenv("JSONBIN_MASTER_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") 

if not BOT_TOKEN or not JSONBIN_ID or not JSONBIN_KEY:
    print("❌ HATA: Çevre değişkenleri (Environment Variables) Render üzerinde tanımlanmamış!")

print("🤖 Akıllı Asistan Başlatılıyor...")

# --- BULUT HAFIZA (JSONBIN) FONKSİYONLARI ---
def get_bulut_verisi():
    headers = {"X-Master-Key": JSONBIN_KEY}
    try:
        res = requests.get(f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest", headers=headers)
        if res.status_code == 200:
            return res.json().get("record", {"bekleyenler": [], "son_durum": {}})
    except Exception as e:
        print("Bulut Hafıza okunamadı:", e)
    return {"bekleyenler": [], "son_durum": {}}

def set_bulut_verisi(bekleyenler, son_durum):
    headers = {"X-Master-Key": JSONBIN_KEY, "Content-Type": "application/json"}
    payload = {"bekleyenler": bekleyenler, "son_durum": son_durum}
    try:
        requests.put(f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}", json=payload, headers=headers)
    except Exception as e:
        print("Bulut Hafıza güncellenemedi:", e)

# --- CANLI HAFIZA (RAM) VE CSV YÜKLEME ---
hafiza = {
    'df_dosya': pd.DataFrame(), 'df_karar_m10': pd.DataFrame(),
    'df_karar_m11': pd.DataFrame(), 'df_karar_birlesik': pd.DataFrame(),
    'max_m10': {}, 'max_m11': {}, 'son_guncelleme': 0,
    'bekleyenler': [], 'son_durum': {}, 'bulut_yuklendi': False 
}

def veri_yukle(dosya_adi):
    if os.path.exists(dosya_adi):
        try:
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False)
            if len(df.columns) < 2: df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False)
            df = df.fillna("")
            indeks_sutunlari = [col for col in df.columns if 'unnamed' in str(col).lower() or str(col).lower() == 'index']
            if indeks_sutunlari:
                df = df.drop(columns=indeks_sutunlari)
            for col in df.select_dtypes(include=['object', 'string']).columns:
                df[col] = df[col].astype(str).str.strip()
            return df
        except Exception:
            try:
                df = pd.read_csv(dosya_adi, sep=';', encoding='cp1254', low_memory=False)
                if len(df.columns) < 2: df = pd.read_csv(dosya_adi, sep=',', encoding='cp1254', low_memory=False)
                df = df.fillna("")
                indeks_sutunlari = [col for col in df.columns if 'unnamed' in str(col).lower() or str(col).lower() == 'index']
                if indeks_sutunlari:
                    df = df.drop(columns=indeks_sutunlari)
                for col in df.select_dtypes(include=['object', 'string']).columns:
                    df[col] = df[col].astype(str).str.strip()
                return df
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

def en_guncel_belgeler(df):
    if df.empty or 'Kaynak Belge' not in df.columns: return ["Veri Yok"], "Bilinmiyor"
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    unique_files['Parsed_Date'] = pd.to_datetime(unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], format='%d.%m.%Y', errors='coerce')
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    if not valid_files.empty:
        max_date = valid_files['Parsed_Date'].max()
        latest_files = valid_files[valid_files['Parsed_Date'] == max_date]['Kaynak Belge'].tolist()
        return latest_files, max_date.strftime('%d.%m.%Y')
    elif not unique_files.empty:
        return [unique_files.iloc[0]['Kaynak Belge']], "Tarih Bulunamadı"
    return ["Veri Yok"], "Bilinmiyor"

def tum_belgeler(df):
    if df.empty or 'Kaynak Belge' not in df.columns: return []
    return df['Kaynak Belge'].dropna().unique().tolist()

# --- HEDEFLİ BİLDİRİM DAĞITIM MOTORU ---
async def bildirimleri_dagit(app_context, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum):
    df_karar = hafiza['df_karar_birlesik']
    df_dosya = hafiza['df_dosya']
    kalan_bekleyenler = []
    bekleyenler = hafiza['bekleyenler'] 
    
    admin_onay_listesi = [] 
    
    print(f"Sistemdeki {len(bekleyenler)} kişiye hedefli bildirim dağıtılıyor...")

    arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if not df_dosya.empty else pd.Series(dtype=str)

    for kisi in bekleyenler:
        chat_id = kisi['chat_id']
        dosya_tam = kisi['dosya_no']
        ana_no, ana_yil = dosya_tam.split('/')
        
        # 🌟 MADDE TÜRÜ TESPİTİ (Ortak kullanım için yukarı taşındı) 🌟
        is_m10 = False
        is_m11 = True 
        madde_turu = "Madde 11" # Varsayılan
        
        if not arama_sutunu.empty:
            arama_kriteri = f"^{ana_no}/.*{ana_yil}$"
            user_row = df_dosya[arama_sutunu.str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
            if not user_row.empty:
                kaynak_dosya_metni = str(user_row.iloc[0].get('Kaynak Belge', ''))
                if re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE):
                    is_m10 = True
                    is_m11 = False
                    madde_turu = "Madde 10"

        onaylandi_mi = False
        if not df_karar.empty:
            karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
            temiz_metin = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
            regex = rf"(?:^|\D){ana_no}/(?:[A-Z]+/)?{ana_yil}(?:$|\D)"
            
            eslesenler = df_karar[temiz_metin.str.contains(regex, regex=True)].copy()
            if not eslesenler.empty:
                eslesenler['Tam_Eslesme'] = temiz_metin.str.extract(rf"({ana_no}/(?:[A-Z]+/)?{ana_yil})")[0]
                aranan_harfli = dosya_tam.replace(" ", "").upper()
                if (eslesenler['Tam_Eslesme'] == aranan_harfli).any():
                    onaylandi_mi = True
                elif not eslesenler.empty:
                    onaylandi_mi = True

        try:
            if onaylandi_mi:
                msg = f"🎉 <b>MÜJDE!</b> Takip ettiğiniz <b>{dosya_tam}</b> numaralı dosyanız onaylandı ve resmi listelerde yayımlandı!\n\nDetayları görmek için bana dosya numaranızı tekrar yazabilirsiniz."
                await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                print(f"✅ {dosya_tam} için MÜJDE iletildi.")
                
                # 🌟 ADMİN LİSTESİNE MADDE TÜRÜYLE BİRLİKTE EKLENDİ
                admin_onay_listesi.append(f"<code>{dosya_tam}</code> <i>({madde_turu})</i>") 
            else:
                kullanici_icin_degisenler = []
                
                if dosya_tarih_degisti:
                    kullanici_icin_degisenler.append(f"Stadiu Dosar Durumu (Güncelleme: {dosya_tarih})")
                
                if is_m10 and eklenen_m10:
                    for b in eklenen_m10: kullanici_icin_degisenler.append(f"Madde 10: {b}")
                
                if is_m11 and eklenen_m11:
                    for b in eklenen_m11: kullanici_icin_degisenler.append(f"Madde 11: {b}")

                if kullanici_icin_degisenler:
                    if len(kullanici_icin_degisenler) > 10:
                        degisim_metni = "\n".join([f"🔹 {liste}" for liste in kullanici_icin_degisenler[:10]]) + f"\n🔹 <i>...ve {len(kullanici_icin_degisenler)-10} belge daha.</i>"
                    else:
                        degisim_metni = "\n".join([f"🔹 {liste}" for liste in kullanici_icin_degisenler])
                        
                    msg = (
                        f"🔔 <b>Sistem Güncellemesi:</b>\n\n"
                        f"ANC sistemine sizin dosya türünüzle ilgili olabilecek yeni veriler yüklenmiştir.\n"
                        f"📂 <b>Sisteme Yeni Eklenenler:</b>\n{degisim_metni}\n\n"
                        f"Maalesef takip ettiğiniz <b>{dosya_tam}</b> numaralı dosyanız bu yeni listelerde görünmemiştir. "
                        f"Dosyanızı sizin için takip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏"
                    )
                    await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                
                kalan_bekleyenler.append(kisi) 
        except Exception as e:
            print(f"Hata ({chat_id}): {e}")
            kalan_bekleyenler.append(kisi)

        await asyncio.sleep(0.05) 

    # 🌟 YÖNETİCİYE (SİZE) ÖZEL TOPLU RAPOR GÖNDERİMİ 🌟
    if admin_onay_listesi and ADMIN_CHAT_ID:
        admin_msg = "👑 <b>SİSTEM RAPORU - ONAY ALAN DOSYALAR</b>\n\n🎉 Yeni listelerde takipteki şu dosyaların kararı çıkmıştır:\n"
        for d in admin_onay_listesi:
            admin_msg += f"✅ {d}\n"
        admin_msg += "\n<i>İlgili kullanıcılara MÜJDE mesajları otomatik olarak iletilmiştir.</i>"
        
        try:
            await app_context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='HTML')
        except Exception as e:
            print(f"Admin'e bildirim gönderilirken hata oluştu: {e}")

    hafiza['bekleyenler'] = kalan_bekleyenler
    hafiza['son_durum'] = yeni_durum
    set_bulut_verisi(kalan_bekleyenler, yeni_durum)
    print("✅ Hedefli bildirim dağıtımı tamamlandı, bulut güncellendi.")

def veritabanini_kontrol_et(app_context=None):
    if not hafiza['bulut_yuklendi']:
        bulut = get_bulut_verisi()
        hafiza['bekleyenler'] = bulut.get("bekleyenler", [])
        hafiza['son_durum'] = bulut.get("son_durum", {})
        hafiza['bulut_yuklendi'] = True

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
        
        if app_context:
            yeni_m10_belgeler = tum_belgeler(hafiza['df_karar_m10'])
            yeni_m11_belgeler = tum_belgeler(hafiza['df_karar_m11'])
            _, dosya_tarih = en_guncel_belgeler(hafiza['df_dosya'])

            eski_durum = hafiza['son_durum']
            eski_m10 = eski_durum.get("m10_belgeler", [])
            eski_m11 = eski_durum.get("m11_belgeler", [])
            eski_dosya_tarih = eski_durum.get("dosya_tarih", "")

            eklenen_m10 = list(set(yeni_m10_belgeler) - set(eski_m10))
            eklenen_m11 = list(set(yeni_m11_belgeler) - set(eski_m11))

            dosya_tarih_degisti = (dosya_tarih != eski_dosya_tarih and dosya_tarih not in ["Bilinmiyor", "Veri Yok", "Tarih Bulunamadı"])

            yeni_durum = {
                "dosya_tarih": dosya_tarih, 
                "m10_belgeler": yeni_m10_belgeler, 
                "m11_belgeler": yeni_m11_belgeler
            }
            
            if not eski_m10 and not eski_m11:
                hafiza['son_durum'] = yeni_durum
                set_bulut_verisi(hafiza['bekleyenler'], yeni_durum)
            elif eklenen_m10 or eklenen_m11 or dosya_tarih_degisti:
                app_context.create_task(bildirimleri_dagit(app_context, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum))

# İlk yükleme
veritabanini_kontrol_et()

# --- TELEGRAM MESAJLAŞMA MANTIĞI ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context) 
    chat_id = str(update.message.chat_id)

    _, dosya_guncelleme_tarihi = en_guncel_belgeler(hafiza['df_dosya'])
    m10_belgeler, _ = en_guncel_belgeler(hafiza['df_karar_m10'])
    m11_belgeler, _ = en_guncel_belgeler(hafiza['df_karar_m11'])

    m10_metin = "\n".join([f"🔸 {b}" for b in m10_belgeler]) if m10_belgeler[0] != "Veri Yok" else "🔸 Veri Yok"
    m11_metin = "\n".join([f"🔸 {b}" for b in m11_belgeler]) if m11_belgeler[0] != "Veri Yok" else "🔸 Veri Yok"

    user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
    
    takip_metni = ""
    if user_takip_listesi:
        dosyalar_alt_alta = "\n".join([f"💚 <code>{d}</code>" for d in user_takip_listesi])
        takip_metni = f"\n━━━━━━━━━━━━━━━━━━\n🔔 <b>Takip Ettiğiniz Dosyalarınız:</b>\n{dosyalar_alt_alta}\n"

    mesaj = (
        "🇹🇩 <b>Romanya Vatandaşlık Sorgulama Botuna Hoş Geldiniz!</b>\n\n"
        "Madde 10/11 kapsamındaki dosya durumunuzu (Stadiu Dosar) ve karar (Ordin) sonucunuzu buradan sorgulayabilirsiniz.\n\n"
        f"<b>Dosya Durumu (Stadiu Dosar) Son Güncelleme:</b> {dosya_guncelleme_tarihi}\n\n"
        f"📄 <b>Sisteme Eklenen Son Kararlar:</b>\n\n"
        f"<b>Madde 10:</b>\n{m10_metin}\n\n"
        f"<b>Madde 11:</b>\n{m11_metin}\n\n"
        "💡 <b>Kullanım:</b>\n"
        "Sadece dosya numaranızı ve yılını yazıp gönderin.\n"
        "<i>Örn: 37064/2023</i> veya <i>1234/2017</i>\n"
        f"{takip_metni}" 
        "━━━━━━━━━━━━━━━━━━\n"
        "⚖️ <b>Yasal Bilgilendirme:</b>\n\n"
        "<i>Bu platform, Romanya Adalet Bakanlığı Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan herkese açık dosya durum (Stadiu Dosar) ve karar (Ordin) listelerini tarayarak çalışan bağımsız bir otomasyon sistemidir. Platformumuzun Romanya Devleti veya herhangi bir resmi kurumla hiçbir resmi bağı veya ortaklığı bulunmamaktadır.\n\n"
        "Sistemde sunulan veriler tamamen bilgilendirme amaçlıdır ve hiçbir şekilde resmi tebligat, onay veya hukuki belge niteliği taşımaz. Veri senkronizasyonunda yaşanabilecek teknik gecikmelerden, hatalardan veya ANC listelerindeki tipografik yanlışlardan platform sorumlu tutulamaz. Nihai ve kesin teyit için her zaman resmi kurum kaynaklarını referans alınız.</i>"
    )
    await update.message.reply_text(mesaj, parse_mode='HTML')

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context)
    aranan_kelime = update.message.text.strip()
    chat_id = str(update.message.chat_id) 
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

    sonuclar['Tekil_Anahtar'] = sonuclar['Arama_Sutunu'].apply(lambda x: f"{str(x).split('/')[0].strip()}_{str(x).split('/')[-1].strip()}")
    sonuclar = sonuclar.drop_duplicates(subset=['Tekil_Anahtar'])

    for index, row in sonuclar.iterrows():
        ana_no, ana_yil = str(row['Tekil_Anahtar']).split('_')[0], str(row['Tekil_Anahtar']).split('_')[-1]
        dosya_no_standart = f"{ana_no}/{ana_yil}"
        bulut_takip_formati = f"{ana_no}/{ana_yil}"
        
        karar_bulundu_mu, k_row, onaylanan_kisi_sayisi = False, None, 0
        
        if not df_karar.empty:
            karar_sutunu = [col for col in df_karar.columns if 'dosya' in col.lower()][0]
            temiz_karar_metni = df_karar[karar_sutunu].astype(str).str.replace(" ", "").str.upper()
            
            regex = rf"(?:^|\D){ana_no}/(?:[A-Z]+/)?{ana_yil}(?:$|\D)"
            karar_sonucu = df_karar[temiz_karar_metni.str.contains(regex, regex=True)].copy()
            
            if not karar_sonucu.empty:
                karar_sonucu['Tam_Eslesme'] = temiz_karar_metni.str.extract(rf"({ana_no}/(?:[A-Z]+/)?{ana_yil})")[0]
                aranan_dosya_harfli = row['Arama_Sutunu'].replace(" ", "").upper()
                
                if (karar_sonucu['Tam_Eslesme'] == aranan_dosya_harfli).any():
                    karar_sonucu = karar_sonucu[karar_sonucu['Tam_Eslesme'] == aranan_dosya_harfli]
                else:
                    en_yaygin = karar_sonucu['Tam_Eslesme'].value_counts().idxmax()
                    karar_sonucu = karar_sonucu[karar_sonucu['Tam_Eslesme'] == en_yaygin]
                
                en_cok_kayit_iceren_belge = karar_sonucu['Kaynak Belge'].value_counts().idxmax()
                karar_sonucu = karar_sonucu[karar_sonucu['Kaynak Belge'] == en_cok_kayit_iceren_belge].copy()
                
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
            f"📂 <b>DOSYA BİLGİLERİ</b>\n\n<b>No:</b> {row['Arama_Sutunu']}\n━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Başvuru Tarihi:</b> {row.get('Başvuru Tarihi', '')}\n⏳ <b>Sonraki Aşama (Termen):</b> {termen}\n"
            f"📝 <b>Kurum Notu:</b> {kurum_notu}\n📂 <b>Kaynak:</b> {kaynak_dosya_metni}\n━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>KARAR (ORDIN) DURUMU</b>\n\n"
        )

        buton_ekle = False
        zaten_takipte = False

        if karar_bulundu_mu:
            gosterilecek_karar = p_numarasi
            kaynak_belge_adi = k_row['Kaynak Belge']
            
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
            takip_listesi = hafiza['bekleyenler']
            
            if any(str(k.get('chat_id')) == str(chat_id) and str(k.get('dosya_no')) == str(bulut_takip_formati) for k in takip_listesi):
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

            if zaten_takipte:
                yanit += "\n━━━━━━━━━━━━━━━━━━\n💚 <b>Dosyanız takip listemizde!</b> Yeni listeler yüklendiğinde size otomatik mesaj göndereceğim. 🔔"

        reply_markup = None
        if buton_ekle:
            klavye = [[InlineKeyboardButton("🔔 Karar Çıkınca Haberdar Et", callback_data=f"kvkk_{ana_no}_{ana_yil}")]]
            reply_markup = InlineKeyboardMarkup(klavye)

        await update.message.reply_text(yanit, parse_mode='HTML', reply_markup=reply_markup)

# --- BUTON TIKLAMA VE KVKK SÜRECİ ---
async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("kvkk_"):
        _, ilk_no, son_yil = query.data.split('_')
        
        kvkk_metni = (
            "🛡️ <b>KVKK Aydınlatma ve Onay</b>\n\n"
            f"<b>{ilk_no}/{son_yil}</b> numaralı dosyanızı takibe almak üzeresiniz.\n\n"
            "Size otomatik bildirim gönderebilmemiz için <b>Telegram ID'niz</b> and <b>Dosya Numaranız</b> "
            "sunucularımızda güvenle saklanacaktır. Bu veriler <u>sadece</u> size haber vermek amacıyla kullanılır "
            "ve asla üçüncü şahıslarla paylaşılmaz.\n\n"
            "Devam etmek için onaylıyor musunuz?"
        )
        klavye = [
            [InlineKeyboardButton("✅ Okudum, Onaylıyorum", callback_data=f"takip_{ilk_no}_{son_yil}")],
            [InlineKeyboardButton("❌ Reddediyorum", callback_data="iptal_takip")]
        ]
        
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=query.message.chat_id, 
            text=kvkk_metni, 
            parse_mode='HTML', 
            reply_markup=InlineKeyboardMarkup(klavye)
        )
        return

    if query.data == "iptal_takip":
        await query.edit_message_text(text="❌ Takip işlemi iptal edildi. Verileriniz kaydedilmedi.", parse_mode='HTML')
        return

    if query.data.startswith("takip_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no_temiz = f"{ilk_no}/{son_yil}"
        chat_id = str(query.message.chat_id) 
        
        if any(str(k.get('chat_id')) == str(chat_id) and str(k.get('dosya_no')) == str(dosya_no_temiz) for k in hafiza['bekleyenler']):
            await query.edit_message_text(text=f"✅ {dosya_no_temiz} numaralı dosya zaten takip listenizde!")
            return
            
        hafiza['bekleyenler'].append({"chat_id": chat_id, "dosya_no": dosya_no_temiz})
        set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum']) 
        
        await query.edit_message_text(
            text=f"🔔 <b>Harika! KVKK onayınız alındı.</b>\n\n{dosya_no_temiz} numaralı dosyanızı takibe aldım. Yeni listelerde yayımlandığı an size otomatik müjde veya güncelleme mesajı göndereceğim.", 
            parse_mode='HTML'
        )

if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def post_init(application: Application):
        veritabanini_kontrol_et(application)
        
    app.post_init = post_init
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    
    app.run_polling()