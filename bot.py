import pandas as pd
import re
import os
import requests
import asyncio
import datetime # Zamanlama için gerekli
import gc # RAM temizliği için çöp toplayıcı
import time  # İnatçı deneme sistemi için
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

# ==========================================
# ☁️ BULUT HAFIZA (JSONBIN) FONKSİYONLARI
# ==========================================
def get_bulut_verisi():
    headers = {"X-Master-Key": JSONBIN_KEY}
    
    for deneme in range(3):
        try:
            url = f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}/latest?t={datetime.datetime.now().timestamp()}"
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.json().get("record", {"bekleyenler": [], "son_durum": {}})
            else:
                print(f"⚠️ Bulut Okuma Hatası (Kod: {res.status_code}) - Deneme {deneme+1}")
        except Exception as e:
            print(f"⚠️ Bulut Bağlantı Sorunu (Okuma Zaman Aşımı) - Deneme {deneme+1}")
        
        time.sleep(2)
        
    print("❌ 3 denemeye rağmen buluttan veri çekilemedi! Verileri ezmemek için sistem duraklatılıyor.")
    return None 

def set_bulut_verisi(bekleyenler, son_durum):
    if len(bekleyenler) < 0:
        print(f"⚠️ GÜVENLİK KİLİDİ DEVREDE! Listede sadece {len(bekleyenler)} kişi var. Veri ezilme riskine karşı kayıt YAPILMADI!")
        return False

    headers = {
        "X-Master-Key": JSONBIN_KEY, 
        "Content-Type": "application/json"
    }
    payload = {"bekleyenler": bekleyenler, "son_durum": son_durum}
    
    for deneme in range(3):
        try:
            res = requests.put(f"https://api.jsonbin.io/v3/b/{JSONBIN_ID}", json=payload, headers=headers, timeout=45)
            
            if res.status_code == 200:
                return True
            else:
                print(f"⚠️ JSONBin Kayıt Hatası (Kod: {res.status_code}) - Deneme {deneme+1}")
        except Exception as e:
            print(f"⚠️ Bulut Hafıza bağlantı sorunu (Yazma Zaman Aşımı) - Deneme {deneme+1}")
        
        time.sleep(2)
        
    print("❌ 3 denemeye rağmen JSONBin'e kayıt yapılamadı!")
    return False

# ==========================================
# 🧠 CANLI HAFIZA (RAM) VE ESNEK VERİ YÜKLEME
# ==========================================
hafiza = {
    'df_dosya': pd.DataFrame(), 'df_karar_m10': pd.DataFrame(),
    'df_karar_m11': pd.DataFrame(), 'df_karar_birlesik': pd.DataFrame(),
    'df_ozel_durum': pd.DataFrame(),
    'max_m10': {}, 'max_m11': {}, 'son_guncelleme': 0,
    'bekleyenler': [], 'son_durum': {}, 'bulut_yuklendi': False 
}

def gercek_dosya_yolu(taban_adi):
    """Dosyanın sistemde hangi uzantıyla var olduğunu bulur."""
    for uzanti in ['.zip', '.xlsx', '.csv']:
        if os.path.exists(taban_adi + uzanti):
            return taban_adi + uzanti
    return None

def veri_yukle_esnek(taban_adi):
    """Bulunan dosyayı uzantısına göre en uygun yöntemle okur"""
    dosya_adi = gercek_dosya_yolu(taban_adi)
    if not dosya_adi:
        return pd.DataFrame()
        
    try:
        if dosya_adi.endswith('.xlsx'):
            df = pd.read_excel(dosya_adi)
        else:
            # .csv veya .zip içindeki csv'leri okur
            df = pd.read_csv(dosya_adi, sep=';', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
            if len(df.columns) < 2: 
                df = pd.read_csv(dosya_adi, sep=',', encoding='utf-8-sig', low_memory=False, on_bad_lines='skip')
                
        df.columns = df.columns.astype(str).str.strip()
        df = df.fillna("")
        
        indeks_sutunlari = [col for col in df.columns if 'unnamed' in str(col).lower() or str(col).lower() == 'index']
        if indeks_sutunlari:
            df = df.drop(columns=indeks_sutunlari)
            
        for col in df.select_dtypes(include=['object', 'string']).columns:
            df[col] = df[col].astype(str).str.strip()
        return df
    except Exception as e:
        print(f"⚠️ {dosya_adi} yüklenirken hata: {e}")
    
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

def en_guncel_belgeler(df, dosya_yolu=None):
    if df.empty or 'Kaynak Belge' not in df.columns: 
        if dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
            return ["Veri/Belge Yok"], dt_str
        return ["Veri Yok"], "Bilinmiyor"
        
    unique_files = df[['Kaynak Belge']].drop_duplicates().copy()
    unique_files['Parsed_Date'] = pd.to_datetime(unique_files['Kaynak Belge'].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0], format='%d.%m.%Y', errors='coerce')
    valid_files = unique_files.dropna(subset=['Parsed_Date'])
    
    if not valid_files.empty:
        max_date = valid_files['Parsed_Date'].max()
        latest_files = valid_files[valid_files['Parsed_Date'] == max_date]['Kaynak Belge'].tolist()
        return latest_files, max_date.strftime('%d.%m.%Y')
    elif not unique_files.empty:
        if dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
            return [unique_files.iloc[0]['Kaynak Belge']], dt_str
        return [unique_files.iloc[0]['Kaynak Belge']], "Tarih Bulunamadı"
    
    return ["Veri Yok"], "Bilinmiyor"

def tum_belgeler(df):
    if df.empty or 'Kaynak Belge' not in df.columns: return []
    return df['Kaynak Belge'].dropna().unique().tolist()


# ==========================================
# 🎯 HEDEFLİ BİLDİRİM DAĞITIM MOTORU
# ==========================================
async def bildirimleri_dagit(app_context, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum, ilk_calistirma=False):
    df_karar = hafiza['df_karar_birlesik']
    df_dosya = hafiza['df_dosya']
    df_ozel = hafiza['df_ozel_durum']
    kalan_bekleyenler = []
    bekleyenler = hafiza['bekleyenler'] 
    
    admin_onay_listesi = [] 
    
    ozel_arama_sutunu = pd.Series(dtype=str)
    if not df_ozel.empty and len(df_ozel.columns) >= 3:
        ozel_arama_sutunu = df_ozel.iloc[:, 2].astype(str).str.strip()

    print(f"Sistemdeki {len(bekleyenler)} kişiye hedefli bildirim dağıtılıyor...")

    arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if not df_dosya.empty else pd.Series(dtype=str)
    ozel_bildirim_gecmisi = yeni_durum.get("ozel_bildirimler", [])

    for kisi in bekleyenler:
        chat_id = kisi['chat_id']
        dosya_tam = kisi['dosya_no']
        ana_no, ana_yil = dosya_tam.split('/')
        
        # --- 🚨 40 GÜN KURALI KONTROLÜ ---
        if not df_ozel.empty and not ozel_arama_sutunu.empty:
            ozel_kriter = f"^{ana_no}/.*{ana_yil}$"
            ozel_satirlar = df_ozel[ozel_arama_sutunu.str.contains(ozel_kriter, flags=re.IGNORECASE, regex=True)]
            
            if not ozel_satirlar.empty:
                bildirim_key = f"{chat_id}_{dosya_tam}_40gun"
                
                if bildirim_key not in ozel_bildirim_gecmisi:
                    ozel_satir = ozel_satirlar.iloc[0]
                    ozel_tarih_str = str(ozel_satir.iloc[0]) if len(ozel_satir) > 0 else "-"
                    ozel_isim = str(ozel_satir.iloc[1]) if len(ozel_satir) > 1 else "-"
                    ozel_ek_bilgi = str(ozel_satir.iloc[3]) if len(ozel_satir) > 3 else "-"

                    kalan_gun_mesaji = ""
                    try:
                        parsed_date = pd.to_datetime(ozel_tarih_str, dayfirst=True)
                        gecen_gun = (datetime.datetime.now() - parsed_date).days
                        kalan_gun = 40 - gecen_gun
                        if kalan_gun > 0:
                            kalan_gun_mesaji = f"⏳ <b>DİKKAT! Yasal sürenin dolmasına SON {kalan_gun} GÜN!</b> Lütfen vakit kaybetmeden istenen e-posta adresini kuruma bildiriniz."
                        elif kalan_gun == 0:
                            kalan_gun_mesaji = f"🚨 <b>DİKKAT! Yasal süreniz BUGÜN DOLUYOR!</b> Lütfen acilen istenen e-posta adresini kuruma bildiriniz."
                        else:
                            kalan_gun_mesaji = f"❌ <b>SÜRE DOLDU!</b> (Duyurunun üzerinden {gecen_gun} gün geçmiş). Yasal 40 günlük süreniz dolmuş görünmektedir. Ancak dosyanızın reddedilmemesi ihtimaline karşı yinede ACİLEN istenilen bilgiyi kuruma iletmeniz tavsiye edilir."
                    except Exception:
                        kalan_gun_mesaji = "Lütfen duyurunun yayınlanma tarihinden itibaren 40 gün içinde e-posta adresinizi kuruma bildiriniz."

                    msg_ozel = (
                        f"🚨 <b>ÖNEMLİ BİLDİRİM (Eksik Evrak / İletişim)</b> 🚨\n\n"
                        f"Takip ettiğiniz <b>{dosya_tam}</b> numaralı dosya, Ulusal Vatandaşlık Kurumu'nun (ANC) <b>tarafınıza ulaşılamadığı için</b> yayınladığı özel listede tespit edilmiştir!\n\n"
                        f"📅 <b>Yayınlanma Tarihi:</b> {ozel_tarih_str}\n"
                        f"👤 <b>İsim:</b> {ozel_isim}\n"
                        f"📝 <b>Kurum Notu:</b> {ozel_ek_bilgi}\n\n"
                        f"{kalan_gun_mesaji}\n\n"
                        f"<i>(21/1991 sayılı Kanun'un 34.1. maddesinin 10. fıkrasına göre yapılan bildirimdir.)</i>\n\n"
                        f"🔗 <a href='https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/'>Resmi Kaynak Listesi İçin Tıklayınız</a>"
                    )
                    try:
                        await app_context.bot.send_message(chat_id=chat_id, text=msg_ozel, parse_mode='HTML', disable_web_page_preview=True)
                        ozel_bildirim_gecmisi.append(bildirim_key)
                        print(f"🚨 {dosya_tam} için 40 Gün Acil Uyarı gönderildi!")
                    except Exception as e:
                        print(f"Özel uyarı atılamadı ({chat_id}): {e}")

        is_m10 = False
        is_m11 = True 
        madde_turu = "Madde 11" 
        p_numarasi = None
        
        if not arama_sutunu.empty:
            arama_kriteri = f"^{ana_no}/.*{ana_yil}$"
            user_row = df_dosya[arama_sutunu.str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
            if not user_row.empty:
                kaynak_dosya_metni = str(user_row.iloc[0].get('Kaynak Belge', ''))
                if re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE):
                    is_m10 = True
                    is_m11 = False
                    madde_turu = "Madde 10"
                
                solutie_metni = str(user_row.iloc[0].get('SOLUTIE', '')).strip()
                if solutie_metni:
                    p_match = re.search(r'(\d{1,6})\s*[/]?\s*P\s*[/]?\s*(\d{4})', solutie_metni, re.IGNORECASE)
                    if p_match: 
                        p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}"

        onaylandi_mi = False
        k_row = None
        if not df_karar.empty:
            regex_find = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
            mask_initial = pd.Series(False, index=df_karar.index)
            for col in df_karar.columns:
                if col != 'Kaynak Belge':
                    temiz_sutun = df_karar[col].astype(str).str.replace(r'\s+', '', regex=True)
                    mask_initial |= temiz_sutun.str.contains(regex_find, case=False, regex=True)
            
            final_matches = df_karar[mask_initial]
            if not final_matches.empty:
                onaylandi_mi = True
                k_row = final_matches.iloc[0]

        try:
            if onaylandi_mi:
                kaynak_belge_adi = str(k_row.get('Kaynak Belge', ''))
                gosterilecek_karar = p_numarasi
                
                if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                    k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower() or 'no' in str(col).lower()]
                    if k_ordin_cols:
                        val = str(k_row[k_ordin_cols[0]]).strip()
                        if val and val.lower() not in ['nan', 'none', '']:
                            gosterilecek_karar = val

                if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                    pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)', kaynak_belge_adi, re.IGNORECASE)
                    if pdf_match:
                        gosterilecek_karar = pdf_match.group(1)

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
                
                karar_tarihi = k_row.get('Tarih', 'Belirtilmemiş')
                if pd.isna(karar_tarihi) or str(karar_tarihi).strip() in ["nan", "None", ""]: 
                    date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', kaynak_belge_adi)
                    karar_tarihi = date_match.group(1) if date_match else "Belirtilmemiş"

                msg = (
                    f"🎉 <b>MÜJDE!</b> Takip ettiğiniz <b>{dosya_tam}</b> numaralı dosyanız onaylandı ve resmi listelerde yayımlandı! 💚\n\n"
                    f"📜 <b>Karar No:</b> {gosterilecek_karar}\n"
                    f"📅 <b>Tarih:</b> {karar_tarihi}\n"
                    f"📂 <b>Kaynak:</b> {kaynak_belge_adi}"
                )
                await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')
                print(f"✅ {dosya_tam} için detaylı MÜJDE iletildi.")
                admin_onay_listesi.append(f"<code>{dosya_tam}</code> <i>({madde_turu})</i>") 
            else:
                if not ilk_calistirma and (eklenen_m10 or eklenen_m11 or dosya_tarih_degisti):
                    kullanici_icin_degisenler = []
                    
                    if dosya_tarih_degisti:
                        kullanici_icin_degisenler.append(f"Bot Stadiu Dosar Verilerini Güncelledi: ({dosya_tarih})")
                    
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

    if admin_onay_listesi and ADMIN_CHAT_ID:
        admin_msg = "👑 <b>SİSTEM RAPORU - ONAY ALAN DOSYALAR</b>\n\n🎉 Yeni listelerde takipteki şu dosyaların kararı çıkmıştır:\n"
        for d in admin_onay_listesi:
            admin_msg += f"✅ {d}\n"
        admin_msg += "\n<i>İlgili kullanıcılara MÜJDE mesajları otomatik olarak iletilmiştir.</i>"
        try:
            await app_context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='HTML')
        except Exception as e: print(f"Admin'e rapor hatası: {e}")

    yeni_durum["ozel_bildirimler"] = ozel_bildirim_gecmisi
    hafiza['bekleyenler'] = kalan_bekleyenler
    hafiza['son_durum'] = yeni_durum
    set_bulut_verisi(kalan_bekleyenler, yeni_durum)
    print("✅ Hedefli bildirim dağıtımı tamamlandı, bulut güncellendi.")

# ==========================================
# 📈 YÖNETİCİYE ÖZEL GÜNLÜK ÖZET RAPOR
# ==========================================
async def gunluk_otomatik_rapor(context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID:
        bekleyenler = hafiza['bekleyenler']
        total_dosya = len(bekleyenler)
        
        count_m10, count_m11 = 0, 0
        df_dosya = hafiza['df_dosya']
        arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if not df_dosya.empty else pd.Series(dtype=str)
        
        for kisi in bekleyenler:
            dosya_tam = kisi['dosya_no']
            try:
                ana_no, ana_yil = dosya_tam.split('/')
                is_m10 = False
                if not arama_sutunu.empty:
                    arama_kriteri = f"^{ana_no}/.*{ana_yil}$"
                    user_row = df_dosya[arama_sutunu.str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                    if not user_row.empty:
                        kaynak_dosya_metni = str(user_row.iloc[0].get('Kaynak Belge', ''))
                        if re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE):
                            is_m10 = True
                if is_m10: count_m10 += 1
                else: count_m11 += 1
            except Exception:
                count_m11 += 1

        tsi_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
        saat_metni = tsi_now.strftime("%H:%M")
        
        rapor_msg = (
            f"📊 <b>GÜNLÜK ÖZET SİSTEM RAPORU</b>\n\n"
            f"🕒 <b>Saat:</b> {saat_metni} (TSİ)\n\n"
            f"👥 Bot veritabanında anlık olarak takip edilen ve karar bekleyen <b>toplam dosya sayısı:</b> <code>{total_dosya}</code>\n\n"
            f"🔸 <b>Madde 10 Dosya Sayısı:</b> <code>{count_m10}</code>\n\n"
            f"🔸 <b>Madde 11 Dosya Sayısı:</b> <code>{count_m11}</code>\n\n"
            f"<i>Sistem 7/24 ANC listelerini nöbette beklemeye devam ediyor. 🇹🇩</i>"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=rapor_msg, parse_mode='HTML')
            print(f"✅ Günlük admin özet raporu ({saat_metni}) kırılımlarla birlikte başarıyla gönderildi.")
        except Exception as e:
            print(f"Günlük rapor gönderilirken hata oluştu: {e}")

# ==========================================
# 🔍 VERİTABANI KONTROL MERKEZİ
# ==========================================
def veritabanini_kontrol_et(app_context=None):
    if not hafiza['bulut_yuklendi']:
        bulut = get_bulut_verisi()
        if bulut is None:
            print("⚠️ Bulut okunamadı, veritabanı kontrolü geçici olarak iptal edildi.")
            return

        hafiza['bekleyenler'] = bulut.get("bekleyenler", [])
        hafiza['son_durum'] = bulut.get("son_durum", {})
        hafiza['bulut_yuklendi'] = True

    # Check multiple triggers for an update
    dosyalar_kontrol = ["dosyadurumu.zip", "dosyadurumu.csv", "Dosya_Durumlari.xlsx", "Dosya_Durumlari.csv"]
    mevcut_saat = 0
    for d in dosyalar_kontrol:
        if os.path.exists(d):
            mevcut_saat = max(mevcut_saat, os.path.getmtime(d))
    
    if mevcut_saat > hafiza['son_guncelleme'] and mevcut_saat > 0:
        print("🔄 Yeni dosya(lar) tespit edildi. Veritabanı Telegram için güncelleniyor...")
        
        hafiza['df_dosya'] = veri_yukle_esnek("dosyadurumu")
        df_m10 = veri_yukle_esnek("Romanya_Vatandaslik_Tum_Veriler_Madde10")
        df_m11 = veri_yukle_esnek("Romanya_Vatandaslik_Tum_Veriler_Madde11")
        hafiza['df_ozel_durum'] = veri_yukle_esnek("Dosya_Durumlari") 
        
        hafiza['max_m10'] = max_ordin_hesapla_vektorel(df_m10)
        hafiza['max_m11'] = max_ordin_hesapla_vektorel(df_m11)
        
        yeni_m10_belgeler = tum_belgeler(df_m10)
        yeni_m11_belgeler = tum_belgeler(df_m11)
        
        karar_listesi = []
        if not df_m10.empty: karar_listesi.append(df_m10)
        if not df_m11.empty: karar_listesi.append(df_m11)
        hafiza['df_karar_birlesik'] = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()
        
        del df_m10
        del df_m11
        hafiza['df_karar_m10'] = pd.DataFrame()
        hafiza['df_karar_m11'] = pd.DataFrame()
        gc.collect() 
        
        hafiza['son_guncelleme'] = mevcut_saat
        
        if app_context:
            # DİNAMİK YOL İLE TARİH TESPİTİ
            gercek_dosya = gercek_dosya_yolu("dosyadurumu")
            _, dosya_tarih = en_guncel_belgeler(hafiza['df_dosya'], gercek_dosya)
            
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
                "m11_belgeler": yeni_m11_belgeler,
                "ozel_bildirimler": eski_durum.get("ozel_bildirimler", [])
            }
            
            ilk_calistirma = not bool(eski_durum)
            app_context.create_task(bildirimleri_dagit(app_context, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum, ilk_calistirma))

# ==========================================
# 💬 TELEGRAM MESAJLAŞMA MANTIĞI
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context) 
    chat_id = str(update.message.chat_id)

    gercek_dosya = gercek_dosya_yolu("dosyadurumu")
    _, dosya_guncelleme_tarihi = en_guncel_belgeler(hafiza['df_dosya'], gercek_dosya)
    
    df_k = hafiza['df_karar_birlesik']
    if not df_k.empty and 'Kaynak Belge' in df_k.columns:
        m10_files, _ = en_guncel_belgeler(df_k[df_k['Kaynak Belge'].str.contains(r'art[.\- ]*10|m10|madde10', case=False, regex=True)], gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde10"))
        m11_files, _ = en_guncel_belgeler(df_k[df_k['Kaynak Belge'].str.contains(r'art[.\- ]*11|m11|madde11', case=False, regex=True)], gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde11"))
    else:
        m10_files, m11_files = ["Veri Yok"], ["Veri Yok"]

    m10_metin = "\n".join([f"🔸 {b}" for b in m10_files]) if m10_files and m10_files[0] != "Veri Yok" else "🔸 Veri Yok"
    m11_metin = "\n".join([f"🔸 {b}" for b in m11_files]) if m11_files and m11_files[0] != "Veri Yok" else "🔸 Veri Yok"

    user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
    
    reply_markup = None
    takip_metni = ""
    if user_takip_listesi:
        dosyalar_alt_alta = "\n".join([f"💚 <code>{d}</code>" for d in user_takip_listesi])
        takip_metni = f"\n━━━━━━━━━━━━━━━━━━\n🔔 <b>Takip Ettiğiniz Dosyalarınız:</b>\n\n{dosyalar_alt_alta}\n"
        
        klavye = [[InlineKeyboardButton("❌ Dosya Takibini Bırak", callback_data="menu_birak")]]
        reply_markup = InlineKeyboardMarkup(klavye)

    mesaj = (
        "🇹🇩 <b>Romanya Vatandaşlık Sorgulama Botuna Hoş Geldiniz!</b>\n\n"
        "Madde 10/11 kapsamındaki dosya durumunuzu (Stadiu Dosar) ve karar (Ordin) sonucunuzu buradan sorgulayabilirsiniz.\n\n"
        f"<b>Bot Veritabanı Son Güncelleme:</b> {dosya_guncelleme_tarihi}\n\n"
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
    await update.message.reply_text(mesaj, parse_mode='HTML', reply_markup=reply_markup)

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context)
    aranan_kelime = update.message.text.strip()
    chat_id = str(update.message.chat_id) 
    df_dosya, df_karar = hafiza['df_dosya'], hafiza['df_karar_birlesik']
    df_ozel = hafiza['df_ozel_durum'] 
    
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
        
        # --- 🚨 MANUEL SORGULAMADA 40 GÜN KONTROLÜ ---
        ozel_mesaj_baslik = ""
        if not df_ozel.empty and len(df_ozel.columns) >= 3:
            ozel_arama = df_ozel.iloc[:, 2].astype(str).str.strip()
            ozel_sonuc = df_ozel[ozel_arama.str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
            
            if not ozel_sonuc.empty:
                ozel_satir = ozel_sonuc.iloc[0]
                ozel_tarih_str = str(ozel_satir.iloc[0]) if len(ozel_satir) > 0 else "-"
                ozel_isim = str(ozel_satir.iloc[1]) if len(ozel_satir) > 1 else "-"
                ozel_ek_bilgi = str(ozel_satir.iloc[3]) if len(ozel_satir) > 3 else "-"

                kalan_gun_mesaji = ""
                try:
                    parsed_date = pd.to_datetime(ozel_tarih_str, dayfirst=True)
                    gecen_gun = (datetime.datetime.now() - parsed_date).days
                    kalan_gun = 40 - gecen_gun
                    if kalan_gun > 0:
                        kalan_gun_mesaji = f"⏳ <b>DİKKAT! Yasal sürenin dolmasına SON {kalan_gun} GÜN!</b> Lütfen vakit kaybetmeden istenen e-posta adresini kuruma bildiriniz."
                    elif kalan_gun == 0:
                        kalan_gun_mesaji = f"🚨 <b>DİKKAT! Yasal süreniz BUGÜN DOLUYOR!</b> Lütfen acilen istenen e-posta adresini kuruma bildiriniz."
                    else:
                        kalan_gun_mesaji = f"❌ <b>SÜRE DOLDU!</b> (Duyurunun üzerinden {gecen_gun} gün geçmiş). Yine de ACİLEN istenilen bilgiyi kuruma iletmeniz tavsiye edilir."
                except Exception:
                    kalan_gun_mesaji = "Lütfen yayınlanma tarihinden itibaren 40 gün içinde e-posta adresinizi kuruma bildiriniz."

                ozel_mesaj_baslik = (
                    f"🚨 <b>ÖNEMLİ BİLDİRİM (Eksik Evrak / İletişim)</b> 🚨\n\n"
                    f"Dosyanız ANC'nin tarafınıza ulaşılamadığı için yayınladığı özel listede tespit edilmiştir!\n\n"
                    f"📅 <b>Yayınlanma Tarihi:</b> {ozel_tarih_str}\n"
                    f"👤 <b>İsim:</b> {ozel_isim}\n"
                    f"📝 <b>Kurum Notu:</b> {ozel_ek_bilgi}\n\n"
                    f"{kalan_gun_mesaji}\n\n"
                    f"<i>(21/1991 sayılı Kanun'un 34.1. maddesinin 10. fıkrasına göre yapılan bildirimdir.)</i>\n"
                    f"🔗 <a href='https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/'>Resmi Kaynak Listesi İçin Tıklayın</a>\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                )

        karar_bulundu_mu, k_row = False, None
        
        solutie_metni = str(row['SOLUTIE']).strip()
        p_numarasi, user_ordin_no, user_ordin_yil = None, 0, 0
        if solutie_metni:
            p_match = re.search(r'(\d{1,6})\s*[/]?\s*P\s*[/]?\s*(\d{4})', solutie_metni, re.IGNORECASE)
            if p_match: p_numarasi, user_ordin_no, user_ordin_yil = f"{p_match.group(1)}/P/{p_match.group(2)}", int(p_match.group(1)), int(p_match.group(2))

        if not df_karar.empty:
            regex_find = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
            mask_initial = pd.Series(False, index=df_karar.index)
            for col in df_karar.columns:
                if col != 'Kaynak Belge':
                    temiz_sutun = df_karar[col].astype(str).str.replace(r'\s+', '', regex=True)
                    mask_initial |= temiz_sutun.str.contains(regex_find, case=False, regex=True)
            
            final_matches = df_karar[mask_initial]
            if not final_matches.empty:
                karar_bulundu_mu = True
                k_row = final_matches.iloc[0]

        kaynak_dosya_metni = str(row.get('Kaynak Belge', ''))
        termen_metni = str(row.get('TERMEN', '')).strip()
        termen = termen_metni if termen_metni and termen_metni != "-" else "Belirtilmemiş"
        kurum_notu = solutie_metni if solutie_metni else ("Sistemde not düşülmemiş ancak listelerde onay tespit edildi!" if karar_bulundu_mu else "Henüz bir not girilmemiş (İnceleme Bekliyor).")

        yanit = ozel_mesaj_baslik + (
            f"📂 <b>DOSYA BİLGİLERİ</b>\n\n<b>No:</b> {row['Arama_Sutunu']}\n━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>Başvuru Tarihi:</b> {row.get('Başvuru Tarihi', '')}\n⏳ <b>Sonraki Aşama (Termen):</b> {termen}\n"
            f"📝 <b>Kurum Notu (Solutie):</b> {kurum_notu}\n📂 <b>Kaynak:</b> {kaynak_dosya_metni}\n━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>KARAR (ORDIN) DURUMU</b>\n\n"
        )

        buton_ekle = False
        zaten_takipte = False

        if karar_bulundu_mu:
            kaynak_belge_adi = k_row['Kaynak Belge']
            gosterilecek_karar = p_numarasi
            
            if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower() or 'no' in str(col).lower()]
                if k_ordin_cols:
                    val = str(k_row[k_ordin_cols[0]]).strip()
                    if val and val.lower() not in ['nan', 'none', '']:
                        gosterilecek_karar = val

            if not gosterilecek_karar or str(gosterilecek_karar).strip().lower() in ['nan', 'none', '', 'belirtilmemiş']:
                pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)', kaynak_belge_adi, re.IGNORECASE)
                if pdf_match:
                    gosterilecek_karar = pdf_match.group(1)

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
            
            karar_tarihi = k_row.get('Tarih', 'Belirtilmemiş')
            if pd.isna(karar_tarihi) or str(karar_tarihi).strip() in ["nan", "None", ""]: 
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', kaynak_belge_adi)
                karar_tarihi = date_match.group(1) if date_match else "Belirtilmemiş"

            yanit += f"🎉 ✅ <b>TEBRİKLER! Kararınız yayımlandı.</b> 💚\n\n📜 <b>Karar No:</b> {gosterilecek_karar}\n📅 <b>Tarih:</b> {karar_tarihi}\n📂 <b>Kaynak:</b> {kaynak_belge_adi}"
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

        await update.message.reply_text(yanit, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)

# ==========================================
# 🔘 BUTON TIKLAMA VE KVKK SÜRECİ
# ==========================================
async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    
    if query.data.startswith("kvkk_"):
        _, ilk_no, son_yil = query.data.split('_')
        
        kvkk_metni = (
            "🛡️ <b>KVKK Aydınlatma ve Açık Rıza Metni</b>\n\n"
            f"<b>{ilk_no}/{son_yil}</b> numaralı dosyanızı otomatik takibe almak üzeresiniz.\n\n"
            "Romanya Vatandaşlık Sorgulama Platformu olarak, size dosya durumunuz değiştiğinde anlık bildirim gönderebilmemiz amacıyla; "
            "<b>Telegram Chat ID</b> ve <b>Dosya Numaranız</b> güvenli bulut sunucularımızda işlenecektir.\n\n"
            "Bu veriler <b>sadece</b> size bilgilendirme mesajı atmak için kullanılır; hiçbir ticari amaca hizmet etmez ve asla üçüncü şahıslarla paylaşılmaz. "
            "İstediğiniz an bota /start yazıp altta çıkacak olan <b>Dosya Takibini Bırak</b> butonuna tıklayarak seçeceğiniz verilerinizin sistemimizden <b>kalıcı olarak siliniyor olmasını</b> sağlayabilirsiniz.\n\n"
            "Verilerinizin bu amaçlarla işlenmesini onaylıyor musunuz?"
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
        
        bulut_verisi = get_bulut_verisi()
        if bulut_verisi is None:
            await query.edit_message_text(text="⚠️ Sistemde geçici bir sunucu yoğunluğu var. Lütfen 5-10 dakika sonra tekrar deneyin.")
            return
            
        hafiza['bekleyenler'] = bulut_verisi.get("bekleyenler", [])
        hafiza['son_durum'] = bulut_verisi.get("son_durum", {})

        if any(str(k.get('chat_id')) == str(chat_id) and str(k.get('dosya_no')) == str(dosya_no_temiz) for k in hafiza['bekleyenler']):
            await query.edit_message_text(text=f"✅ {dosya_no_temiz} numaralı dosya zaten takip listenizde!")
            return
            
        hafiza['bekleyenler'].append({"chat_id": chat_id, "dosya_no": dosya_no_temiz})
        
        kayit_basarili = set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum']) 
        
        if kayit_basarili:
            await query.edit_message_text(
                text=f"🔔 <b>Harika! KVKK onayınız alındı.</b>\n\n{dosya_no_temiz} numaralı dosyanızı takibe aldım. Yeni listelerde yayımlandığı an size otomatik müjde veya güncelleme mesajı göndereceğim.", 
                parse_mode='HTML'
            )
        else:
            hafiza['bekleyenler'].pop() 
            await query.edit_message_text(
                text="⚠️ <b>Bulut Kayıt Hatası!</b>\n\nSunucularda anlık bir yoğunluk yaşandığı için kaydınız tamamlanamadı. Lütfen daha sonra bota dosya numaranızı tekrar yazarak şansınızı deneyin.", 
                parse_mode='HTML'
            )
        return

    if query.data == "menu_birak":
        user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        
        if not user_takip_listesi:
            await query.edit_message_text(text="❌ Takip listenizde aktif dosya bulunamadı.", parse_mode='HTML')
            return
            
        if 'secilenler' not in context.user_data:
            context.user_data['secilenler'] = []
            
        context.user_data['secilenler'] = [d for d in context.user_data['secilenler'] if d in user_takip_listesi]
        secilenler = context.user_data['secilenler']
        
        soru_metni = (
            "📋 <b>Dosya Takip Yönetim Paneli (Çoklu Seçim)</b>\n\n"
            "Takibini iptal etmek istediğiniz dosyaları aşağıdaki listeden işaretleyiniz. "
            "Seçim bittiğinde altta çıkacak olan toplu silme butonuna basabilirsiniz:"
        )
        
        klavye = []
        for d in user_takip_listesi:
            ilk_no, son_yil = d.split('/')
            durum_emojisi = "✅" if d in secilenler else "⬜"
            klavye.append([InlineKeyboardButton(f"{durum_emojisi} {d}", callback_data=f"tsil_{ilk_no}_{son_yil}")])
            
        if secilenler:
            klavye.append([InlineKeyboardButton(f"🗑️ Seçilenleri Sil ({len(secilenler)})", callback_data="toplusil_onay")])
            
        klavye.append([InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="silvazgec")])
        
        await query.edit_message_text(text=soru_metni, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data.startswith("tsil_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no_temiz = f"{ilk_no}/{son_yil}"
        
        if 'secilenler' not in context.user_data:
            context.user_data['secilenler'] = []
            
        if dosya_no_temiz in context.user_data['secilenler']:
            context.user_data['secilenler'].remove(dosya_no_temiz)
        else:
            context.user_data['secilenler'].append(dosya_no_temiz)
            
        user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        secilenler = context.user_data['secilenler']
        
        klavye = []
        for d in user_takip_listesi:
            i_no, s_yil = d.split('/')
            durum_emojisi = "✅" if d in secilenler else "⬜"
            klavye.append([InlineKeyboardButton(f"{durum_emojisi} {d}", callback_data=f"tsil_{i_no}_{s_yil}")])
            
        if secilenler:
            klavye.append([InlineKeyboardButton(f"🗑️ Seçilenleri Sil ({len(secilenler)})", callback_data="toplusil_onay")])
            
        klavye.append([InlineKeyboardButton("🔙 Ana Menüye Dön", callback_data="silvazgec")])
        
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_onay":
        secilenler = context.user_data.get('secilenler', [])
        if not secilenler:
            await query.answer("Lütfen önce listeden en az bir dosya seçiniz!", show_alert=True)
            return
            
        dosyalar_raporu = "\n".join([f"❌ <code>{d}</code>" for d in secilenler])
        
        if len(secilenler) == 1:
            baslik = "TAKİP İPTAL ONAYI"
            fiil_cumlesi = f"Seçtiğiniz şu <b>1</b> adet dosyanın takibini bırakmak üzeresiniz:\n"
        else:
            baslik = "TOPLU SİLME ONAYI"
            fiil_cumlesi = f"Seçtiğiniz şu <b>{len(secilenler)}</b> adet dosyanın takibini aynı anda bırakmak üzeresiniz:\n"
            
        soru_metni = (
            f"⚠️ <b>{baslik}</b>\n\n"
            f"{fiil_cumlesi}\n{dosyalar_raporu}\n\n"
            f"Bu işlem sonucunda verileriniz sunucudan tamamen silinecektir. Onaylıyor musunuz?"
        )
        
        klavye = [
            [InlineKeyboardButton("✅ Evet, Sil", callback_data="toplusil_confirm")],
            [InlineKeyboardButton("❌ Hayır, Seçim Menüsüne Dön", callback_data="menu_birak")]
        ]
        await query.edit_message_text(text=soru_metni, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_confirm":
        secilenler = context.user_data.get('secilenler', [])
        if not secilenler:
            await query.edit_message_text(text="❌ İptal edilecek veri bulunamadı.", parse_mode='HTML')
            return
            
        bulut_verisi = get_bulut_verisi()
        if bulut_verisi is None:
            await query.edit_message_text(text="⚠️ Sistemde geçici bir sunucu yoğunluğu var. Silme işlemi yapılamadı, lütfen daha sonra tekrar deneyin.")
            return
            
        hafiza['bekleyenler'] = bulut_verisi.get("bekleyenler", [])
        hafiza['son_durum'] = bulut_verisi.get("son_durum", {})
        
        eski_liste = list(hafiza['bekleyenler']) 
        
        hafiza['bekleyenler'] = [k for k in hafiza['bekleyenler'] if not (str(k.get('chat_id')) == chat_id and k.get('dosya_no') in secilenler)]
        
        kayit_basarili = set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum'])
        
        if kayit_basarili:
            context.user_data['secilenler'] = []
            await query.edit_message_text(
                text=f"🚀 <b>İşlem Başarılı!</b>\n\nSeçmiş olduğunuz {len(secilenler)} adet dosyanın takibi iptal edilmiş ve KVKK uyarınca verileriniz kalıcı olarak imha edilmiştir.", 
                parse_mode='HTML'
            )
        else:
            hafiza['bekleyenler'] = eski_liste 
            await query.edit_message_text(
                text="⚠️ <b>Bulut Güncelleme Hatası!</b>\n\nSunucularda anlık bir yoğunluk yaşandığı için silme işlemi tamamlanamadı. Lütfen daha sonra tekrar deneyin.", 
                parse_mode='HTML'
            )
        return

    if query.data == "silvazgec":
        context.user_data['secilenler'] = []
        await query.edit_message_text(text="❌ Takip iptal işleminden vazgeçildi. Verileriniz korunuyor.", parse_mode='HTML')
        return

# ==========================================
# ⚙️ ANA ÇALIŞTIRMA VE ZAMANLAYICI (POLLING)
# ==========================================
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def post_init(application: Application):
        async def baslangic_taramasi(context: ContextTypes.DEFAULT_TYPE):
            veritabanini_kontrol_et(context.application)
            
        application.job_queue.run_once(baslangic_taramasi, 2)
        
        # ÇİFT ZAMANLI RAPOR SİSTEMİ (TSİ -> UTC ÇEVRİMİ İLE)
        saat_aksam = datetime.time(17, 0, 0)  # 20:00 TSİ       
        
        application.job_queue.run_daily(gunluk_otomatik_rapor, time=saat_aksam)
        print("⏰ Günlük saat 20:00 özet raporlama görevleri zamanlayıcıya eklendi.")
        
    app.post_init = post_init
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    
    app.run_polling()