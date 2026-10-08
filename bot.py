import pandas as pd
import re
import os
import asyncio
import datetime
import gc
import time
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==========================================
# 🌐 ÇOKLU DİL SÖZLÜĞÜ (i18n)
# ==========================================
DIL_SOZLUGU = {
    "tr": {
        "karsilama": (
            "🇹🇩 <b>Romanya Vatandaşlık Sorgulama Botuna Hoş Geldiniz!</b>\n\n"
            "Madde 10/11 kapsamındaki dosya durumunuzu (Stadiu Dosar) ve karar (Ordin) sonucunuzu buradan sorgulayabilirsiniz.\n\n"
            "<b>Stadiu Dosar Son Güncelleme:</b> {tarih}\n\n"
            "📄 <b>Sisteme Eklenen Son Kararlar:</b>\n\n"
            "<b>Madde 10:</b>\n{m10_liste}\n\n"
            "<b>Madde 11:</b>\n{m11_liste}\n\n"
            "💡 <b>Kullanım:</b>\n"
            "Sadece dosya numaranızı ve yılını yazıp gönderin.\n"
            "<i>Örn: 1234/2020</i>\n\n"          
            "{takip}"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚖️ <b>Yasal Bilgilendirme:</b>\n\n"
            "<i>Bu platform, Romanya Adalet Bakanlığı Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan herkese açık dosya durum (Stadiu Dosar) ve karar (Ordin) listelerini tarayarak çalışan bağımsız bir otomasyon sistemidir. Platformumuzun Romanya Devleti veya herhangi bir resmi kurumla hiçbir resmi bağı veya ortaklığı bulunmamaktadır.\n\n"
            "Sistemde sunulan veriler tamamen bilgilendirme amaçlıdır ve hiçbir şekilde resmi tebligat, onay veya hukuki belge niteliği taşımaz. Veri senkronizasyonunda yaşanabilecek teknik gecikmelerden, hatalardan veya ANC listelerindeki tipografik yanlışlardan platform sorumlu tutulamaz. Nihai ve kesin teyit için her zaman resmi kurum kaynaklarını referans alınız.</i>"
        ),
        "secim": "🇹🇷 Lütfen dil seçin:\n\n🇷🇺 Пожалуйста, выберите язык:\n\n🇷🇴 Vă rugăm să selectați limba:",
        "secildi": "🇹🇷 Dil Türkçe olarak ayarlandı.\nLütfen dosya numaranızı gönderin (Örn: 1234/2023).",
        "bos": "❌ Sistemde veri bulunmuyor.",
        "format": "⚠ <b>Hatalı format:</b> Lütfen araya sadece BİR adet '/' işareti koyunuz. Örn: 1234/2023",
        "gecersiz": "⚠️ Sistem uyarısı: Geçersiz dosya numarası veya yıl.",
        "bulunamadi": "❌ <b>Bulunamadı:</b> Girdiğiniz kriterlere uygun dosya bulunamadı.",
        "dosya_baslik": "📂 <b>DOSYA BİLGİLERİ</b>",
        "basvuru": "Başvuru Tarihi",
        "termen": "Sonraki Aşama (Termen)",
        "solutie": "Kurum Notu (Solutie)",
        "kaynak": "Kaynak",
        "karar_baslik": "KARAR (ORDIN) DURUMU",
        "onay_var": "🎉 ✅ <b>TEBRİKLER! Kararınız yayımlandı.</b> 💚",
        "karar_no": "Karar No",
        "tarih": "Tarih",
        "henuz_yok": "❌ 🔴 Dosyanız henüz resmi Karar (Ordin) listelerinde yayımlanmamıştır.",
        "takipte": "💚 <b>Dosyanız takip listemizde!</b> Yeni listeler yüklendiğinde size otomatik mesaj göndereceğim. 🔔",
        "buton_takip": "🔔 Karar Çıkınca Haberdar Et",
        "buton_birak": "❌ Dosya Takibini Bırak",
        "kvkk": "🛡️ <b>KVKK Aydınlatma ve Açık Rıza Metni</b>\n\n<b>{dosya}</b> numaralı dosyanızı otomatik takibe almak üzeresiniz.\nSistemimiz sadece size bildirim atmak için dosya numaranızı ve Telegram ID'nizi bulut sunucularda saklar.\n\nVerilerinizin işlenmesini onaylıyor musunuz?",
        "onay_evet": "✅ Okudum, Onaylıyorum",
        "onay_hayir": "❌ Reddediyorum",
        "iptal": "❌ İşlem iptal edildi.",
        "takip_basarili": "🔔 <b>Harika! Onayınız alındı.</b>\n\n{dosya} numaralı dosyanızı takibe aldım. Yeni listelerde yayımlandığı an size otomatik mesaj göndereceğim.",
        "zaten_takip": "✅ {dosya} numaralı dosya zaten takip listenizde!",
        "hata_bulut": "⚠️ Sistemde geçici bir sunucu yoğunluğu var. Lütfen tekrar deneyin.",
        "menu_sil_baslik": "📋 <b>Dosya Takip Yönetim Paneli</b>\nTakibini iptal etmek istediğiniz dosyaları işaretleyiniz:",
        "secilenleri_sil": "🗑️ Seçilenleri Sil ({sayi})",
        "ana_menu_don": "🔙 Ana Menüye Dön",
        "sil_onay_soru": "⚠️ <b>TAKİP İPTAL ONAYI</b>\n\nSeçtiğiniz dosyaların takibini bırakmak üzeresiniz:\n{liste}\n\nOnaylıyor musunuz?",
        "evet_sil": "✅ Evet, Sil",
        "hayir_don": "❌ Hayır, Dön",
        "sil_basarili": "🚀 <b>İşlem Başarılı!</b>\nSeçmiş olduğunuz dosyaların takibi iptal edilmiştir.",
        "uyari_40_gun": "🚨 <b>ÖNEMLİ BİLDİRİM (Eksik Evrak)</b> 🚨\nDosyanız ANC'nin tarafınıza ulaşılamadığı için yayınladığı özel listede tespit edilmiştir!\n\n📅 Yayınlanma: {tarih}\n👤 İsim: {isim}\n📝 Not: {not_}\n\n{kalan_gun_msg}\n🔗 <a href='https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/'>Resmi Kaynak</a>",
        "gun_kaldi": "⏳ <b>DİKKAT! Yasal sürenin dolmasına SON {gun} GÜN!</b>",
        "bugun_doluyor": "🚨 <b>DİKKAT! Yasal süreniz BUGÜN DOLUYOR!</b>",
        "sure_doldu": "❌ <b>SÜRE DOLDU!</b> ({gun} gün geçmiş). Acilen evrakları iletin.",
        "mujde_onay": "🎉 <b>MÜJDE!</b> Takip ettiğiniz <b>{dosya}</b> numaralı dosyanız onaylandı! 💚\n\n📜 Karar No: {karar}\n📅 Tarih: {tarih}\n📂 Kaynak: {kaynak}",
        "guncelleme_sistem": "🔔 <b>Sistem Güncellemesi:</b>\nANC sistemine sizin dosya türünüzle ilgili yeni kararlar (ordin) yüklenmiştir:\n{yeni_dosyalar}\n\nMaalesef sizin dosyanız (<b>{dosya}</b>) bu yeni listelerde görünmemiştir. Takip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏",
        "termen_degisti": "🔄 <b>ÖNEMLİ: İnceleme Tarihiniz (Termen) Değişti!</b>\n\nTakip ettiğiniz <b>{dosya}</b> dosyasının tarihi güncellendi:\nEski: <del>{eski}</del>\nYeni: {yeni}",
        "stadiu_guncellendi": "🔔 <b>Sistem Güncellemesi:</b>\nANC Stadiu Dosar listesi güncellendi ({tarih}). Durumunuzu kontrol edebilirsiniz.",
        "takip_baslik": "🔔 <b>Takip Ettiğiniz Dosyalarınız:</b>"
    },
    "ru": {
        "karsilama": (
            "🇹🇩 <b>Добро пожаловать в бот проверки гражданства Румынии!</b>\n\n"
            "Здесь вы можете проверить состояние вашего досье (Stadiu Dosar) и выход приказа (Ordin) по Статьям 10 и 11.\n\n"
            "<b>Последнее обновление Stadiu Dosar:</b> {tarih}\n\n"
            "📄 <b>Последние добавленные приказы:</b>\n\n"
            "<b>Статья 10:</b>\n{m10_liste}\n\n"
            "<b>Статья 11:</b>\n{m11_liste}\n\n"
            "💡 <b>Использование:</b>\n"
            "Просто отправьте номер вашего досье и год.\n"
            "<i>Например: 1234/2020</i>\n\n"
            "{takip}"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚖️ <b>Юридическое уведомление:</b>\n\n"
            "<i>Данная платформа представляет собой независимую автоматизированную систему, которая сканирует общедоступные списки состояния досье (Stadiu Dosar) и приказов (Ordin), публикуемые Национальным органом по гражданству (ANC) Министерства юстиции Румынии. Наша платформа не имеет официальных связей или партнерских отношений с государством Румыния или какими-либо официальными учреждениями.\n\n"
            "Предоставляемые данные носят исключительно информационный характер и не являются официальным уведомлением, подтверждением или юридическим документом. Платформа не несет ответственности за технические задержки синхронизации данных, системные ошибки или опечатки в официальных списках ANC. Для окончательного подтверждения всегда обращайтесь к официальным источникам.</i>"
        ),
        "secildi": "🇷🇺 Язык установлен на русский.\nПожалуйста, отправьте номер вашего досье (Например: 1234/2023).",
        "bos": "❌ Нет данных в системе.",
        "format": "⚠ <b>Неверный формат:</b> Используйте только ОДИН знак '/'. Пример: 1234/2023",
        "gecersiz": "⚠️️ Системное предупреждение: Недопустимый номер досье или год.",
        "bulunamadi": "❌ <b>Не найдено:</b> Досье по вашим критериям не найдено.",
        "dosya_baslik": "📂 <b>ИНФОРМАЦИЯ О ДОСЬЕ</b>",
        "basvuru": "Дата подачи",
        "termen": "Следующий этап (Termen)",
        "solutie": "Решение (Soluție)",
        "kaynak": "Источник",
        "karar_baslik": "СТАТУС ПРИКАЗА (ORDIN)",
        "onay_var": "🎉 ✅ <b>ПОЗДРАВЛЯЕМ! Ваш приказ опубликован.</b> 💚",
        "karar_no": "Номер приказа",
        "tarih": "Дата",
        "henuz_yok": "❌ 🔴 Ваше досье еще не опубликовано в официальных списках приказов (Ordin).",
        "takipte": "💚 <b>Досье отслеживается!</b> Я отправлю вам автоматическое сообщение, когда оно появится в новых списках. 🔔",
        "buton_takip": "🔔 Уведомить о выходе приказа",
        "buton_birak": "❌ Отменить отслеживание",
        "kvkk": "🛡️ <b>Согласие на обработку данных</b>\n\nВы собираетесь включить автоматическое отслеживание досье <b>{dosya}</b>.\nБот сохранит ваш Telegram ID только для отправки уведомлений.\n\nВы согласны на обработку ваших данных?",
        "onay_evet": "✅ Да, согласен",
        "onay_hayir": "❌ Отказываюсь",
        "iptal": "❌ Операция отменена.",
        "takip_basarili": "🔔 <b>Отлично!</b>\n\nДосье {dosya} добавлено в список отслеживания. Я отправлю вам уведомление, как только появится приказ.",
        "zaten_takip": "✅ Досье {dosya} уже отслеживается!",
        "hata_bulut": "⚠️ Ошибка сервера. Пожалуйста, попробуйте позже.",
        "menu_sil_baslik": "📋 <b>Панель управления отслеживанием</b>\nВыберите досье, отслеживание которых хотите отменить:",
        "secilenleri_sil": "🗑️ Удалить выбранные ({sayi})",
        "ana_menu_don": "🔙 Назад в меню",
        "sil_onay_soru": "⚠️ <b>ПОДТВЕРЖДЕНИЕ ОТМЕНЫ</b>\n\nВы собираетесь отменить отслеживание следующих досье:\n{liste}\n\nВы подтверждаете?",
        "evet_sil": "✅ Да, удалить",
        "hayir_don": "❌ Нет, назад",
        "sil_basarili": "🚀 <b>Успешно!</b>\nОтслеживание выбранных досье отменено.",
        "uyari_40_gun": "🚨 <b>ВАЖНОЕ УВЕДОМЛЕНИЕ</b> 🚨\nВаше досье найдено в специальном списке ANC!\n\n📅 Дата публикации: {tarih}\n👤 Имя: {isim}\n📝 Примечание: {not_}\n\n{kalan_gun_msg}\n🔗 <a href='https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/'>Официальный источник</a>",
        "gun_kaldi": "⏳ <b>ВНИМАНИЕ! Осталось {gun} ДНЕЙ!</b>",
        "bugun_doluyor": "🚨 <b>ВНИМАНИЕ! Срок истекает СЕГОДНЯ!</b>",
        "sure_doldu": "❌ <b>СРОК ИСТЕК!</b> (прошло {gun} дней).",
        "mujde_onay": "🎉 <b>ОТЛИЧНЫЕ НОВОСТИ!</b> Досье <b>{dosya}</b> одобрено! 💚\n\n📜 Приказ №: {karar}\n📅 Дата: {tarih}\n📂 Источник: {kaynak}",
        "guncelleme_sistem": "🔔 <b>Обновление системы:</b>\nВ систему ANC добавлены новые приказы (ordin):\n{yeni_dosyalar}\n\nК сожалению, ваше досье (<b>{dosya}</b>) в этих новых списках не найдено. Продолжаю отслеживание, не теряйте надежду! 🙏",
        "termen_degisti": "🔄 <b>ВАЖНО: Дата рассмотрения (Termen) изменена!</b>\n\nДосье: <b>{dosya}</b>\nСтарая: <del>{eski}</del>\nНовая: {yeni}",
        "stadiu_guncellendi": "🔔 <b>Обновление системы:</b>\nСписки Stadiu Dosar обновлены ({tarih}). Проверьте свой статус.",
        "takip_baslik": "🔔 <b>Отслеживаемые досье:</b>"
    },
    "ro": {
        "karsilama": (
            "🇹🇩 <b>Bun venit la botul de verificare a cetățeniei române!</b>\n\n"
            "Aici puteți verifica stadiul dosarului dvs. (Stadiu Dosar) și soluția/ordinul conform Articolelor 10 și 11.\n\n"
            "<b>Ultima actualizare Stadiu Dosar:</b> {tarih}\n\n"
            "📄 <b>Ultimele ordine adăugate în sistem:</b>\n\n"
            "<b>Articolul 10:</b>\n{m10_liste}\n\n"
            "<b>Articolul 11:</b>\n{m11_liste}\n\n"
            "💡 <b>Utilizare:</b>\n"
            "Trimiteți doar numărul dosarului și anul.\n"
            "<i>Ex: 1234/2020</i>\n\n"            
            "{takip}"
            "━━━━━━━━━━━━━━━━━━\n"
            "⚖️ <b>Informare juridică:</b>\n\n"
            "<i>Această platformă este un sistem automatizat independent, creat pentru a scana listele publice privind stadiul dosarelor (Stadiu Dosar) și ordinele publicate de Autoritatea Națională pentru Cetățenie (ANC) din cadrul Ministerului Justiției din România. Platforma noastră nu are nicio legătură oficială sau parteneriat cu statul român sau cu vreo instituție publică.\n\n"
            "Datele prezentate au un caracter strict informativ și nu constituie o notificare oficială, o aprobare legală sau un document juridic. Platforma nu poate fi trasă la răspundere pentru eventuale întârzieri tehnice de sincronizare, erori de procesare sau greșeli tipografice existente în listele publicate de ANC. Pentru o confirmare definitivă și sigură, consultați întotdeauna sursele oficiale ale instituției.</i>"
        ),
        "secildi": "🇷🇴 Limba a fost setată la română.\nVă rugăm să trimiteți numărul dosarului (Ex: 1234/2023).",
        "bos": "❌ Nu există date în sistem.",
        "format": "⚠ <b>Format invalid:</b> Folosiți un singur semn '/'. Ex: 1234/2023",
        "gecersiz": "⚠️ Avertisment: Număr dosar sau an invalid.",
        "bulunamadi": "❌ <b>Nu a fost găsit:</b> Niciun dosar nu a fost găsit.",
        "dosya_baslik": "📂 <b>INFORMAȚII DOSAR</b>",
        "basvuru": "Data înregistrării",
        "termen": "Următorul termen",
        "solutie": "Soluție (Notă instituție)",
        "kaynak": "Sursă",
        "karar_baslik": "STARE ORDIN",
        "onay_var": "🎉 ✅ <b>FELICITĂRI! Ordinul dvs. a fost publicat.</b> 💚",
        "karar_no": "Nr. Ordin",
        "tarih": "Data",
        "henuz_yok": "❌ 🔴 Dosarul dvs. nu a fost încă publicat în listele oficiale de ordine.",
        "takipte": "💚 <b>Dosarul este urmărit!</b> Vă voi trimite un mesaj automat când va apărea pe noile liste. 🔔",
        "buton_takip": "🔔 Anunță-mă când apare ordinul",
        "buton_birak": "❌ Oprește urmărirea dosarului",
        "kvkk": "🛡️ <b>Consimțământ date</b>\n\nUrmează să urmăriți automat dosarul <b>{dosya}</b>.\nSistemul va salva ID-ul de Telegram doar pentru notificări.\n\nSunteți de acord cu prelucrarea datelor?",
        "onay_evet": "✅ Da, sunt de acord",
        "onay_hayir": "❌ Refuz",
        "iptal": "❌ Operațiune anulată.",
        "takip_basarili": "🔔 <b>Excelent!</b>\n\nDosarul {dosya} este urmărit. Vă voi anunța când apare ordinul.",
        "zaten_takip": "✅ Dosarul {dosya} este deja în lista dvs.!",
        "hata_bulut": "⚠️ Eroare de server. Vă rugăm să încercați mai târziu.",
        "menu_sil_baslik": "📋 <b>Panou administrare dosare</b>\nSelectați dosarele pe care nu mai doriți să le urmăriți:",
        "secilenleri_sil": "🗑️ Șterge selecția ({sayi})",
        "ana_menu_don": "🔙 Înapoi la meniu",
        "sil_onay_soru": "⚠️ <b>CONFIRMARE ȘTERGERE</b>\n\nUrmează să opriți urmărirea următoarelor dosare:\n{liste}\n\nConfirmați?",
        "evet_sil": "✅ Da, șterge",
        "hayir_don": "❌ Nu, înapoi",
        "sil_basarili": "🚀 <b>Succes!</b>\nUrmărirea dosarelor selectate a fost oprită.",
        "uyari_40_gun": "🚨 <b>NOTIFICARE IMPORTANTĂ</b> 🚨\nDosarul dvs. a fost găsit în lista specială ANC!\n\n📅 Data publicării: {tarih}\n👤 Nume: {isim}\n📝 Notă: {not_}\n\n{kalan_gun_msg}\n🔗 <a href='https://cetatenie.just.ro/category/confirmari-corespondenta-electronica/'>Sursa oficială</a>",
        "gun_kaldi": "⏳ <b>ATENȚIE! Au mai rămas {gun} ZILE!</b>",
        "bugun_doluyor": "🚨 <b>ATENȚIE! Termenul expiră ASTĂZI!</b>",
        "sure_doldu": "❌ <b>TERMEN EXPIRAT!</b> (au trecut {gun} zile).",
        "mujde_onay": "🎉 <b>VEȘTI BUNE!</b> Dosarul <b>{dosya}</b> a fost aprobat! 💚\n\n📜 Ordin Nr: {karar}\n📅 Data: {tarih}\n📂 Sursă: {kaynak}",
        "guncelleme_sistem": "🔔 <b>Actualizare sistem:</b>\nAu fost adăugate noi ordine (ordin) în sistemul ANC:\n{yeni_dosyalar}\n\nDin păcate, dosarul dvs. (<b>{dosya}</b>) nu a apărut în aceste noi liste. Urmăresc în continuare, nu vă pierdeți speranța! 🙏",
        "termen_degisti": "🔄 <b>IMPORTANT: Termenul a fost modificat!</b>\n\nDosar: <b>{dosya}</b>\nVechi: <del>{eski}</del>\nNou: {yeni}",
        "stadiu_guncellendi": "🔔 <b>Actualizare sistem:</b>\nListele Stadiu Dosar au fost actualizate ({tarih}).",
        "takip_baslik": "🔔 <b>Dosarele urmărite:</b>"
    }
}

# ==========================================
# GÜVENLİ AYARLAR
# ==========================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID") 

if not BOT_TOKEN or not MONGO_URI:
    print("❌ HATA: Çevre değişkenleri tanımlanmamış!", flush=True)

print("🤖 Akıllı Asistan Başlatılıyor...", flush=True)

# ==========================================
# ☁️ MONGODB BAĞLANTISI
# ==========================================
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["VatandaslikBot"]
    koleksiyon = db["Hafiza"]
    client.admin.command('ping')
    print("✅ MongoDB Atlas bağlantısı kuruldu!", flush=True)
except Exception as e:
    print(f"❌ MongoDB Bağlantı Hatası: {e}", flush=True)

def get_bulut_verisi():
    try:
        veri = koleksiyon.find_one({"_id": "bulut_hafiza"})
        if veri:
            return {
                "bekleyenler": veri.get("bekleyenler", []), 
                "son_durum": veri.get("son_durum", {}),
                "kullanici_dilleri": veri.get("kullanici_dilleri", {})
            }
        else:
            return {"bekleyenler": [], "son_durum": {}, "kullanici_dilleri": {}}
    except Exception as e:
        print(f"⚠️ MongoDB Okuma Hatası: {e}", flush=True)
        return None 

def set_bulut_verisi(bekleyenler, son_durum, kullanici_dilleri=None):
    if len(bekleyenler) < 0:
        return False
        
    if kullanici_dilleri is None:
        kullanici_dilleri = hafiza.get('kullanici_dilleri', {})

    try:
        koleksiyon.update_one(
            {"_id": "bulut_hafiza"}, 
            {"$set": {
                "bekleyenler": bekleyenler, 
                "son_durum": son_durum,
                "kullanici_dilleri": kullanici_dilleri
            }}, 
            upsert=True
        )
        return True
    except Exception as e:
        print(f"❌ MongoDB Kayıt Hatası: {e}", flush=True)
        return False

# ==========================================
# 🧠 CANLI HAFIZA
# ==========================================
hafiza = {
    'df_dosya': pd.DataFrame(), 
    'df_dosya_eski': pd.DataFrame(),
    'df_karar_birlesik': pd.DataFrame(),
    'df_ozel_durum': pd.DataFrame(),
    'max_m10': {}, 'max_m11': {}, 'son_guncelleme': 0,
    'bekleyenler': [], 'son_durum': {}, 'bulut_yuklendi': False,
    'son_m10_belgeler': ["Veri Yok"], 
    'son_m11_belgeler': ["Veri Yok"],
    'kullanici_dilleri': {}  
}

def gercek_dosya_yolu(taban_adi):
    for uzanti in ['.zip', '.xlsx', '.csv']:
        if os.path.exists(taban_adi + uzanti):
            return taban_adi + uzanti
    return None

def veri_yukle_esnek(taban_adi):
    dosya_adi = gercek_dosya_yolu(taban_adi)
    if not dosya_adi:
        return pd.DataFrame()
        
    df = pd.DataFrame()
    try:
        if dosya_adi.endswith('.xlsx'):
            df = pd.read_excel(dosya_adi)
        else:
            basarili = False
            kodlamalar = ['utf-8-sig', 'utf-8', 'cp1250', 'cp1254', 'latin1']
            
            for enc in kodlamalar:
                if basarili: break
                try:
                    df = pd.read_csv(dosya_adi, sep=';', encoding=enc, low_memory=False, on_bad_lines='skip')
                    if len(df.columns) < 2:
                        df = pd.read_csv(dosya_adi, sep=',', encoding=enc, low_memory=False, on_bad_lines='skip')
                    if len(df.columns) > 1:
                        basarili = True
                except Exception:
                    continue 
                    
        if df.empty: return df
        df.columns = df.columns.astype(str).str.strip()
        df = df.fillna("")
        
        indeks_sutunlari = [col for col in df.columns if 'unnamed' in str(col).lower() or str(col).lower() == 'index']
        if indeks_sutunlari:
            df = df.drop(columns=indeks_sutunlari)
            
        for col in df.select_dtypes(include=['object', 'string']).columns:
            df[col] = df[col].astype(str).str.strip()
            
        return df
    except Exception:
        pass
    return pd.DataFrame()

def sutun_degeri_al(row, olasi_isimler, haric_kelimeler=None):
    if haric_kelimeler is None: haric_kelimeler = []
    for col in row.index:
        col_clean = str(col).strip().lower()
        if any(h.lower() in col_clean for h in haric_kelimeler): continue
        for hedef in olasi_isimler:
            if hedef.lower() == col_clean or hedef.lower() in col_clean:
                val = str(row[col]).strip()
                if val.lower() not in ['nan', 'none']: return val
    return ""

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

def gercek_dosya_yolu(taban_adi):
    for uzanti in ['.zip', '.xlsx', '.csv']:
        if os.path.exists(taban_adi + uzanti):
            return taban_adi + uzanti
    return None

def en_guncel_belgeler(df, dosya_yolu=None):
    # --- STADIU DOSAR (dosyadurumu) İÇİN TARİH BULMA MANTIĞI ---
    if df.empty or 'Kaynak Belge' not in df.columns: 
        dt_str = "Bilinmiyor"
        tarih_bulundu = False
        
        # 1. Aşama: Orijinal isim tablonun içindeyse (başlık veya ilk satırlarda "LA DATA 09.09.2026" gibi)
        if not df.empty:
            ornek_metin = " ".join(df.columns.astype(str)).upper() + " " + " ".join(df.head(10).astype(str).values.flatten()).upper()
            
            # Öncelikle DATA, UPDATE veya STADIUL kelimelerinden sonraki tarihi (09.09.2026) bulmaya çalış
            m_icerik = re.search(r'(?:DATA|UPDATE|STADIUL).*?(\d{2}[\.\-\_]\d{2}[\.\-\_]202\d)', ornek_metin)
            if m_icerik:
                dt_str = m_icerik.group(1).replace('-', '.').replace('_', '.')
                tarih_bulundu = True
            else:
                # Sadece genel bir başlık tarihi varsa onu yakala
                m_herhangi = re.search(r'(\d{2}[\.\-\_]\d{2}[\.\-\_]202\d)', " ".join(df.columns.astype(str)))
                if m_herhangi:
                    dt_str = m_herhangi.group(1).replace('-', '.').replace('_', '.')
                    tarih_bulundu = True

        # 2. Aşama: Başlıklarda ANC'nin resmi tarihi yoksa, 'Başvuru Tarihi' sütunundaki EN BÜYÜK (maksimum) tarihi al
        if not tarih_bulundu and not df.empty:
            basvuru_sutun = next((col for col in df.columns if any(x in str(col).lower() for x in ['data înreg', 'data inreg', 'başvuru', 'basvuru'])), None)
            if basvuru_sutun:
                tarihler = pd.to_datetime(
                    df[basvuru_sutun].astype(str).str.extract(r'(\d{2}[\.\-\/]\d{2}[\.\-\/]\d{4})')[0].str.replace(r'[\-\/]', '.', regex=True), 
                    format='%d.%m.%Y', errors='coerce'
                )
                max_tarih = tarihler.max()
                if pd.notnull(max_tarih):
                    dt_str = max_tarih.strftime('%d.%m.%Y')
                    tarih_bulundu = True

        # 3. Aşama: Hiçbiri işe yaramazsa dosya değiştirilme saatini (mtime) kullan
        if not tarih_bulundu and dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            dt_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
            
        return ["Veri/Belge Yok"], dt_str

    # --- ORDIN DOSYALARI (Madde 10/11 Kararları) İÇİN SIRALAMA VE TARİH MANTIĞI ---
    tarih_kolonu = next((col for col in df.columns if any(k in str(col).lower() for k in ['tarih', 'data', 'date'])), None)
    
    unique_files = df[['Kaynak Belge']].dropna().drop_duplicates().copy()

    def dosya_skorunu_bul(dosya_adi):
        metin = str(dosya_adi)
        
        if tarih_kolonu:
            satir_tarihleri = df[df['Kaynak Belge'] == dosya_adi][tarih_kolonu].dropna()
            for t in satir_tarihleri:
                m = re.search(r'(\d{2})[\.\/\-](\d{2})[\.\/\-](\d{4})', str(t))
                if m:
                    return int(m.group(3)), pd.to_datetime(f"{m.group(1)}.{m.group(2)}.{m.group(3)}", format='%d.%m.%Y', errors='coerce')

        tm = re.search(r'(\d{2})[\.\-_](\d{2})[\.\-_](202\d)', metin)
        if tm:
            return int(tm.group(3)), pd.to_datetime(f"{tm.group(1)}.{tm.group(2)}.{tm.group(3)}", format='%d.%m.%Y', errors='coerce')
        
        ym = re.findall(r'\b(20[12]\d)\b', metin)
        if ym:
            son_yil = int(ym[-1])
            return son_yil, pd.to_datetime(f"01.01.{son_yil}", format='%d.%m.%Y', errors='coerce')
        
        return 2026, pd.to_datetime("01.01.2026", format='%d.%m.%Y', errors='coerce')

    def dosya_ordin_no_bul(dosya_adi):
        metin = str(dosya_adi)
        m = re.search(r'(?:ordin|op|nr)[^\d]*(\d{1,5})', metin, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m_fallback = re.search(r'(\d{1,5})', metin)
        return int(m_fallback.group(1)) if m_fallback else 0

    skorlar = unique_files['Kaynak Belge'].apply(dosya_skorunu_bul)
    unique_files['Yil'] = [s[0] for s in skorlar]
    unique_files['Parsed_Date'] = [s[1] for s in skorlar]
    unique_files['Ordin_No'] = unique_files['Kaynak Belge'].apply(dosya_ordin_no_bul)

    valid_files = unique_files.sort_values(by=['Yil', 'Ordin_No'], ascending=[False, False])
    
    if not valid_files.empty:
        latest_5_files = valid_files['Kaynak Belge'].head(5).tolist()
        
        max_date = unique_files['Parsed_Date'].dropna().max()
        if pd.notnull(max_date):
            max_date_str = max_date.strftime('%d.%m.%Y')
        elif dosya_yolu and os.path.exists(dosya_yolu):
            mtime = os.path.getmtime(dosya_yolu)
            max_date_str = datetime.datetime.fromtimestamp(mtime).strftime('%d.%m.%Y')
        else:
            max_date_str = "Bilinmiyor"
            
        return latest_5_files, max_date_str
        
    return unique_files['Kaynak Belge'].head(5).tolist(), "Bilinmiyor"
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

    arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if not df_dosya.empty and 'Dosya No' in df_dosya.columns else (df_dosya.iloc[:, 0].astype(str).str.strip() if not df_dosya.empty else pd.Series(dtype=str))
    ozel_bildirim_gecmisi = yeni_durum.get("ozel_bildirimler", [])
    
    # 📢 PAYLAŞ BUTONU HAZIRLIĞI
    bot_username = app_context.bot.username
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🇹🇩%20Romanya%20Vatandaslik%20Dosya%20Sorgulama%20ve%20Takip%20Botunu%20kesinlikle%20tavsiye%20ederim!"

    for kisi in bekleyenler:
        chat_id = kisi['chat_id']
        dosya_tam = kisi['dosya_no']
        
        kullanici_dili = hafiza['kullanici_dilleri'].get(chat_id, "tr")
        dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])
        
        # Dil bazlı buton metni ayarı
        buton_metni = "📢 Botu Arkadaşına Öner"
        if kullanici_dili == "ru": buton_metni = "📢 Порекомендуй бота другу"
        elif kullanici_dili == "ro": buton_metni = "📢 Recomandă botul unui prieten"
        
        oner_klavye = InlineKeyboardMarkup([[InlineKeyboardButton(buton_metni, url=share_url)]])
        
        if kisi.get('onaylandi', False):
            kalan_bekleyenler.append(kisi)
            continue
        
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
                            kalan_gun_mesaji = dil_paketi["gun_kaldi"].format(gun=kalan_gun)
                        elif kalan_gun == 0:
                            kalan_gun_mesaji = dil_paketi["bugun_doluyor"]
                        else:
                            kalan_gun_mesaji = dil_paketi["sure_doldu"].format(gun=gecen_gun)
                    except Exception:
                        pass

                    msg_ozel = dil_paketi["uyari_40_gun"].format(
                        tarih=ozel_tarih_str, isim=ozel_isim, not_=ozel_ek_bilgi, kalan_gun_msg=kalan_gun_mesaji
                    )
                    
                    try:
                        await app_context.bot.send_message(chat_id=chat_id, text=msg_ozel, parse_mode='HTML', disable_web_page_preview=True)
                        ozel_bildirim_gecmisi.append(bildirim_key)
                        await asyncio.sleep(1.5)
                    except Exception:
                        pass

        is_m10, is_m11, p_numarasi = False, True, None
        
        if not arama_sutunu.empty:
            arama_kriteri = f"^{ana_no}/.*{ana_yil}$"
            user_row = df_dosya[arama_sutunu.str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
            if not user_row.empty:
                satir_veri = user_row.iloc[0]
                kaynak_dosya_metni = sutun_degeri_al(satir_veri, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no', 'no:'])
                if re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE):
                    is_m10, is_m11 = True, False
                
                solutie_metni = sutun_degeri_al(satir_veri, ['SOLUTIE', 'Solutie', 'SOLUŢIE', 'Kurum Notu'])
                if solutie_metni:
                    p_match = re.search(r'(\d{1,6})\s*[/]?\s*P(?:\s*[/]?\s*(\d{4}))?', solutie_metni, re.IGNORECASE)
                    if p_match: 
                        u_no, u_yil = p_match.group(1), p_match.group(2)
                        p_numarasi = f"{u_no}/P/{u_yil}" if u_yil else f"{u_no}/P"

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
                kaynak_belge_adi = sutun_degeri_al(k_row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no', 'no:'])
                gosterilecek_karar = ""
                k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower() or 'no' in str(col).lower()]
                if k_ordin_cols: gosterilecek_karar = str(k_row[k_ordin_cols[0]]).strip()

                if not gosterilecek_karar or gosterilecek_karar.lower() in ['nan', 'none', '', 'belirtilmemiş']:
                    pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)\s*[/]?\s*([pP])?', kaynak_belge_adi, re.IGNORECASE)
                    if pdf_match: gosterilecek_karar = f"{pdf_match.group(1)}{'/P' if pdf_match.group(2) else ''}"

                if not gosterilecek_karar and p_numarasi: gosterilecek_karar = p_numarasi
                if gosterilecek_karar:
                    p_format_match = re.search(r'(\d+)\s*[/]?\s*P', str(gosterilecek_karar), re.IGNORECASE)
                    if p_format_match: gosterilecek_karar = f"{p_format_match.group(1)}/P"
                else:
                    gosterilecek_karar = "-"
                
                karar_tarihi = sutun_degeri_al(k_row, ['Tarih', 'Data', 'Karar Tarihi'])
                if not karar_tarihi or str(karar_tarihi).strip().lower() in ["nan", "none", ""]: 
                    date_match = re.search(r'(\d{2}[._\s]\d{2}[._\s]\d{4})', kaynak_belge_adi)
                    karar_tarihi = date_match.group(1).replace('_', '.').replace('-', '.') if date_match else "-"

                msg = dil_paketi["mujde_onay"].format(dosya=dosya_tam, karar=gosterilecek_karar, tarih=karar_tarihi, kaynak=kaynak_belge_adi)
                
                # ✅ MÜJDE MESAJINA BUTON EKLENDİ
                await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=oner_klavye)
                admin_onay_listesi.append(f"<code>{dosya_tam}</code> - 📄 <i>{kaynak_belge_adi}</i>") 
                
                kisi['onaylandi'] = True
                kalan_bekleyenler.append(kisi) 
                
                await asyncio.sleep(1.5)
                
            else:
                ilgili_ordin_eklendi_mi = (is_m10 and eklenen_m10) or (is_m11 and eklenen_m11)
                
                if not ilk_calistirma and (ilgili_ordin_eklendi_mi or dosya_tarih_degisti):
                    termen_degisti_mi, eski_termen_str, yeni_termen_str = False, "", ""
                    
                    if dosya_tarih_degisti:
                        if not user_row.empty:
                            y_sol = sutun_degeri_al(satir_veri, ['SOLUTIE', 'Solutie', 'SOLUŢIE', 'Kurum Notu'])
                            y_ter = sutun_degeri_al(satir_veri, ['TERMEN', 'Termen', 'Sonraki Aşama'])
                            y_sol_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', y_sol)
                            if y_sol_m and not re.search(r'\d+\s*/?\s*P', y_sol, re.IGNORECASE): y_ter = y_sol_m.group(1)
                            
                            if y_ter:
                                yt_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', y_ter)
                                yeni_termen_str = yt_m.group(1).replace('/', '.').replace('-', '.') if yt_m else str(y_ter).strip()

                        df_eski = hafiza.get('df_dosya_eski', pd.DataFrame())
                        if not df_eski.empty:
                            eski_dosya_col = next((col for col in df_eski.columns if any(x in str(col).lower() for x in ['dosya', 'nr'])), df_eski.columns[0])
                            eski_match = df_eski[df_eski[eski_dosya_col].astype(str).str.strip().str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
                            if not eski_match.empty:
                                e_satir = eski_match.iloc[0]
                                e_sol = sutun_degeri_al(e_satir, ['SOLUTIE', 'Solutie', 'SOLUŢIE', 'Kurum Notu'])
                                e_ter = sutun_degeri_al(e_satir, ['TERMEN', 'Termen', 'Sonraki Aşama'])
                                e_sol_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_sol)
                                if e_sol_m and not re.search(r'\d+\s*/?\s*P', e_sol, re.IGNORECASE): e_ter = e_sol_m.group(1)
                                if e_ter:
                                    et_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_ter)
                                    eski_termen_str = et_m.group(1).replace('/', '.').replace('-', '.') if et_m else str(e_ter).strip()
                    
                        if eski_termen_str and yeni_termen_str and eski_termen_str != yeni_termen_str:
                            termen_degisti_mi = True
                    
                    if ilgili_ordin_eklendi_mi:
                        # Hangi PDF'lerin eklendiğini bul ve listele
                        eklenen_pdf_listesi = []
                        if is_m10 and eklenen_m10:
                            eklenen_pdf_listesi.extend([f"🔹 Madde 10: <i>{pdf}</i>" for pdf in eklenen_m10])
                        if is_m11 and eklenen_m11:
                            eklenen_pdf_listesi.extend([f"🔹 Madde 11: <i>{pdf}</i>" for pdf in eklenen_m11])
                        eklenen_pdf_str = "\n".join(eklenen_pdf_listesi)
                        
                        msg = dil_paketi["guncelleme_sistem"].format(dosya=dosya_tam)
                        if termen_degisti_mi:
                            msg += f"\n\n" + dil_paketi["termen_degisti"].format(dosya=dosya_tam, eski=eski_termen_str, yeni=yeni_termen_str)
                    else:
                        if termen_degisti_mi:
                            msg = dil_paketi["termen_degisti"].format(dosya=dosya_tam, eski=eski_termen_str, yeni=yeni_termen_str)
                        else:
                            msg = dil_paketi["stadiu_guncellendi"].format(tarih=dosya_tarih)
                    
                    # ✅ SİSTEM GÜNCELLEME MESAJLARINA BUTON EKLENDİ
                    await app_context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML', reply_markup=oner_klavye)
                    
                    await asyncio.sleep(1.5)
                
                kalan_bekleyenler.append(kisi) 
        except Exception as e:
            kalan_bekleyenler.append(kisi)

        await asyncio.sleep(0)

    if admin_onay_listesi and ADMIN_CHAT_ID:
        admin_msg = "👑 <b>SİSTEM RAPORU - ONAY ALAN DOSYALAR</b>\n\n🎉 Yeni listelerde takipteki şu dosyaların kararı çıkmıştır:\n"
        for d in admin_onay_listesi: admin_msg += f"✅ {d}\n"
        try: await app_context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='HTML')
        except Exception: pass

    yeni_durum["ozel_bildirimler"] = ozel_bildirim_gecmisi
    hafiza['bekleyenler'] = kalan_bekleyenler
    hafiza['son_durum'] = yeni_durum
    set_bulut_verisi(kalan_bekleyenler, yeni_durum, hafiza['kullanici_dilleri'])
    print("✅ Hedefli bildirim dağıtımı tamamlandı, bulut durumu tam senkronize edildi.", flush=True)

# ==========================================
# 🔍 VERİTABANI KONTROL MERKEZİ
# ==========================================
def veritabanini_kontrol_et(app_context=None):
    if not hafiza['bulut_yuklendi']:
        bulut = get_bulut_verisi()
        if bulut is None:
            print("⚠️️ Bulut okunamadı, veritabanı kontrolü geçici olarak iptal edildi.", flush=True)
            return

        hafiza['bekleyenler'] = bulut.get("bekleyenler", [])
        hafiza['son_durum'] = bulut.get("son_durum", {})
        hafiza['kullanici_dilleri'] = bulut.get("kullanici_dilleri", {})
        hafiza['bulut_yuklendi'] = True

    dosyalar_kontrol = ["dosyadurumu.zip", "dosyadurumu.xlsx", "dosyadurumu.csv", "Dosya_Durumlari.xlsx", "Dosya_Durumlari.csv"]
    mevcut_saat = 0
    for d in dosyalar_kontrol:
        if os.path.exists(d):
            mevcut_saat = max(mevcut_saat, os.path.getmtime(d))
    
    if mevcut_saat > hafiza['son_guncelleme'] and mevcut_saat > 0:
        hafiza['df_dosya'] = veri_yukle_esnek("dosyadurumu")
        hafiza['df_dosya_eski'] = veri_yukle_esnek("dosyadurumu_eski")
        df_m10 = veri_yukle_esnek("Romanya_Vatandaslik_Tum_Veriler_Madde10")
        df_m11 = veri_yukle_esnek("Romanya_Vatandaslik_Tum_Veriler_Madde11")
        hafiza['df_ozel_durum'] = veri_yukle_esnek("Dosya_Durumlari") 
        
        hafiza['son_m10_belgeler'], _ = en_guncel_belgeler(df_m10, gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde10"))
        hafiza['son_m11_belgeler'], _ = en_guncel_belgeler(df_m11, gercek_dosya_yolu("Romanya_Vatandaslik_Tum_Veriler_Madde11"))
        hafiza['max_m10'] = max_ordin_hesapla_vektorel(df_m10)
        hafiza['max_m11'] = max_ordin_hesapla_vektorel(df_m11)
        
        yeni_m10_belgeler = tum_belgeler(df_m10)
        yeni_m11_belgeler = tum_belgeler(df_m11)
        
        karar_listesi = []
        if not df_m10.empty: karar_listesi.append(df_m10)
        if not df_m11.empty: karar_listesi.append(df_m11)
        hafiza['df_karar_birlesik'] = pd.concat(karar_listesi, ignore_index=True) if karar_listesi else pd.DataFrame()
        
        del df_m10, df_m11
        gc.collect() 
        hafiza['son_guncelleme'] = mevcut_saat
        
        if app_context:
            gercek_dosya = gercek_dosya_yolu("dosyadurumu")
            _, dosya_tarih = en_guncel_belgeler(hafiza['df_dosya'], gercek_dosya)
            
            eski_durum = hafiza['son_durum']
            eski_m10 = eski_durum.get("m10_belgeler", [])
            eski_m11 = eski_durum.get("m11_belgeler", [])
            eski_dosya_tarih = eski_durum.get("dosya_tarih", "")

            eklenen_m10 = list(set(yeni_m10_belgeler) - set(eski_m10))
            eklenen_m11 = list(set(yeni_m11_belgeler) - set(eski_m11))
            
            # 🛑 DÜZELTME: Eski tarih BOŞSA (ilk açılış/restart ise) asla "değişti" sayma!
            dosya_tarih_degisti = (
                bool(eski_dosya_tarih) and 
                (dosya_tarih != eski_dosya_tarih) and 
                (dosya_tarih not in ["Bilinmiyor", "Veri Yok", "Tarih Bulunamadı"])
            )

            yeni_durum = {
                "dosya_tarih": dosya_tarih, 
                "m10_belgeler": yeni_m10_belgeler, 
                "m11_belgeler": yeni_m11_belgeler,
                "ozel_bildirimler": eski_durum.get("ozel_bildirimler", [])
            }
            
            # İlk çalıştırma veya hafızanın ilk doluşu ise bildirim gitmesin
            ilk_calistirma = not bool(eski_durum) or not bool(eski_dosya_tarih)
            if len(eklenen_m10) > 15 or len(eklenen_m11) > 15: 
                ilk_calistirma = True
                
            app_context.create_task(bildirimleri_dagit(app_context, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum, ilk_calistirma))

# ==========================================
# 💬 TELEGRAM MESAJLAŞMA MANTIĞI
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context) 
    chat_id = str(update.message.chat_id)

    kullanici_dili = hafiza['kullanici_dilleri'].get(chat_id)
    if not kullanici_dili:
        klavye = [
            [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="dil_tr")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="dil_ru")],
            [InlineKeyboardButton("🇷🇴 Română", callback_data="dil_ro")]
        ]
        await update.message.reply_text(DIL_SOZLUGU["tr"]["secim"], reply_markup=InlineKeyboardMarkup(klavye))
        return

    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])
    gercek_dosya = gercek_dosya_yolu("dosyadurumu")
    _, dosya_guncelleme_tarihi = en_guncel_belgeler(hafiza['df_dosya'], gercek_dosya)
    
    m10_files = hafiza.get('son_m10_belgeler', ["Veri Yok"])
    m11_files = hafiza.get('son_m11_belgeler', ["Veri Yok"])

    m10_metin = "\n".join([f"🔸 {b}" for b in m10_files]) if m10_files and m10_files[0] != "Veri Yok" else "🔸 -"
    m11_metin = "\n".join([f"🔸 {b}" for b in m11_files]) if m11_files and m11_files[0] != "Veri Yok" else "🔸 -"

    user_takip_objeleri = [k for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
    reply_markup = None
    takip_metni = ""
    
    if user_takip_objeleri:
        dosyalar_alt_alta = ""
        for k in user_takip_objeleri:
            d_no = k.get('dosya_no')
            if k.get('onaylandi', False): dosyalar_alt_alta += f"🎉 <del>{d_no}</del>\n"
            else: dosyalar_alt_alta += f"⏳ <code>{d_no}</code>\n"
        
        takip_baslik = dil_paketi.get("takip_baslik", "🔔 <b>Takip Ettiğiniz Dosyalarınız:</b>")
        takip_metni = f"\n━━━━━━━━━━━━━━━━━━\n{takip_baslik}\n\n{dosyalar_alt_alta}\n"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(dil_paketi["buton_birak"], callback_data="menu_birak")]])

    mesaj = dil_paketi["karsilama"].format(
        tarih=dosya_guncelleme_tarihi,
        m10_liste=m10_metin,
        m11_liste=m11_metin,
        takip=takip_metni
    )
    await update.message.reply_text(mesaj, parse_mode='HTML', reply_markup=reply_markup)

async def dil_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    klavye = [
        [InlineKeyboardButton("🇹🇷 Türkçe", callback_data="dil_tr")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="dil_ru")],
        [InlineKeyboardButton("🇷🇴 Română", callback_data="dil_ro")],
        [InlineKeyboardButton("❌ Vazgeç / Отмена / Renunță", callback_data="dil_iptal")]
    ]
    await update.message.reply_text(
        "🌐 Lütfen yeni bir dil seçin / Пожалуйста, выберите язык / Vă rugăm să selectați limba:", 
        reply_markup=InlineKeyboardMarkup(klavye)
    )

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    veritabanini_kontrol_et(context)
    aranan_kelime = update.message.text.strip()
    chat_id = str(update.message.chat_id) 
    
    kullanici_dili = hafiza['kullanici_dilleri'].get(chat_id, "tr")
    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])

    df_dosya, df_karar, df_ozel = hafiza['df_dosya'], hafiza['df_karar_birlesik'], hafiza['df_ozel_durum'] 
    
    if df_dosya.empty:
        await update.message.reply_text(dil_paketi["bos"])
        return

    if not re.fullmatch(r'[0-9/]+', aranan_kelime) or aranan_kelime.count("/") != 1:
        await update.message.reply_text(dil_paketi["format"], parse_mode='HTML')
        return
        
    parcalar = aranan_kelime.split("/")
    ilk_numara, son_yil = parcalar[0], parcalar[1]
    if not ilk_numara.isdigit() or int(ilk_numara) == 0 or len(son_yil) != 4 or not (2017 <= int(son_yil) <= 2026):
        await update.message.reply_text(dil_paketi["gecersiz"])
        return

    arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
    df_gecici = df_dosya.copy()
    dosya_no_col = next((col for col in df_gecici.columns if 'dosya' in str(col).lower() or 'nr' in str(col).lower()), df_gecici.columns[0])
    df_gecici['Arama_Sutunu'] = df_gecici[dosya_no_col].astype(str).str.strip()
    sonuclar = df_gecici[df_gecici['Arama_Sutunu'].str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)].copy()

    if sonuclar.empty:
        await update.message.reply_text(dil_paketi["bulunamadi"], parse_mode='HTML')
        return

    sonuclar['Tekil_Anahtar'] = sonuclar['Arama_Sutunu'].apply(lambda x: f"{str(x).split('/')[0].strip()}_{str(x).split('/')[-1].strip()}")
    sonuclar = sonuclar.drop_duplicates(subset=['Tekil_Anahtar'])

    for index, row in sonuclar.iterrows():
        ana_no, ana_yil = str(row['Tekil_Anahtar']).split('_')[0], str(row['Tekil_Anahtar']).split('_')[-1]
        bulut_takip_formati = f"{ana_no}/{ana_yil}"
        
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
                    if kalan_gun > 0: kalan_gun_mesaji = dil_paketi["gun_kaldi"].format(gun=kalan_gun)
                    elif kalan_gun == 0: kalan_gun_mesaji = dil_paketi["bugun_doluyor"]
                    else: kalan_gun_mesaji = dil_paketi["sure_doldu"].format(gun=gecen_gun)
                except Exception:
                    pass

                ozel_mesaj_baslik = dil_paketi["uyari_40_gun"].format(
                    tarih=ozel_tarih_str, isim=ozel_isim, not_=ozel_ek_bilgi, kalan_gun_msg=kalan_gun_mesaji
                ) + "\n━━━━━━━━━━━━━━━━━━\n\n"

        karar_bulundu_mu, k_row = False, None
        solutie_metni = sutun_degeri_al(row, ['SOLUTIE', 'Solutie', 'SOLUŢIE', 'Kurum Notu'])
        termen_metni = sutun_degeri_al(row, ['TERMEN', 'Termen', 'Sonraki Aşama'])

        solutie_tarih_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', solutie_metni)
        if solutie_tarih_match and not re.search(r'\d+\s*/?\s*P', solutie_metni, re.IGNORECASE):
            termen_metni = solutie_tarih_match.group(1)
            solutie_metni = ""

        if termen_metni:
            termen_tarih_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', termen_metni)
            termen = termen_tarih_match.group(1).replace('/', '.').replace('-', '.') if termen_tarih_match else termen_metni
        else:
            termen = "-"

        eski_termen = ""
        df_eski = hafiza.get('df_dosya_eski', pd.DataFrame())
        if not df_eski.empty:
            eski_dosya_col = next((col for col in df_eski.columns if any(x in str(col).lower() for x in ['dosya', 'nr'])), df_eski.columns[0])
            eski_match = df_eski[df_eski[eski_dosya_col].astype(str).str.strip().str.contains(arama_kriteri, flags=re.IGNORECASE, regex=True)]
            if not eski_match.empty:
                e_satir = eski_match.iloc[0]
                e_sol = sutun_degeri_al(e_satir, ['SOLUTIE', 'Solutie', 'SOLUŢIE', 'Kurum Notu'])
                e_ter = sutun_degeri_al(e_satir, ['TERMEN', 'Termen', 'Sonraki Aşama'])
                e_sol_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_sol)
                if e_sol_m and not re.search(r'\d+\s*/?\s*P', e_sol, re.IGNORECASE): e_ter = e_sol_m.group(1)
                if e_ter:
                    et_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_ter)
                    eski_termen = et_m.group(1).replace('/', '.').replace('-', '.') if et_m else str(e_ter).strip()

        if eski_termen and eski_termen != termen: termen = f"{termen} <i>({eski_termen})</i> 🔄"

        p_numarasi = None
        if solutie_metni:
            p_match = re.search(r'(\d{1,6})\s*[/]?\s*P(?:\s*[/]?\s*(\d{4}))?', solutie_metni, re.IGNORECASE)
            if p_match: p_numarasi = f"{p_match.group(1)}/P/{p_match.group(2)}" if p_match.group(2) else f"{p_match.group(1)}/P"

        if not df_karar.empty:
            regex_find = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
            mask_initial = pd.Series(False, index=df_karar.index)
            for col in df_karar.columns:
                if col != 'Kaynak Belge':
                    temiz_sutun = df_karar[col].astype(str).str.replace(r'\s+', '', regex=True)
                    mask_initial |= temiz_sutun.str.contains(regex_find, case=False, regex=True)
            
            final_matches = df_karar[mask_initial]
            if not final_matches.empty:
                karar_bulundu_mu, k_row = True, final_matches.iloc[0]

        kaynak_dosya_metni = sutun_degeri_al(row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no', 'no:'])
        kurum_notu = solutie_metni if solutie_metni else "-"
        basvuru_tarihi = sutun_degeri_al(row, ['Başvuru Tarihi', 'DATA ÎNREGISTRĂRII', 'DATA INREGISTRARII', 'Tarih', 'Data'])
        if basvuru_tarihi:
            b_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', basvuru_tarihi)
            basvuru_tarihi = b_match.group(1).replace('/', '.').replace('-', '.') if b_match else basvuru_tarihi
        else: basvuru_tarihi = "-"

        yanit = ozel_mesaj_baslik + (
            f"{dil_paketi['dosya_baslik']}\n\n<b>No:</b> {row['Arama_Sutunu']}\n━━━━━━━━━━━━━━━━━━\n"
            f"📅 <b>{dil_paketi['basvuru']}:</b> {basvuru_tarihi}\n"
            f"⏳ <b>{dil_paketi['termen']}:</b> {termen}\n"
            f"📝 <b>{dil_paketi['solutie']}:</b> {kurum_notu}\n"
            f"📂 <b>{dil_paketi['kaynak']}:</b> {kaynak_dosya_metni}\n━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ <b>{dil_paketi['karar_baslik']}</b>\n\n"
        )

        buton_ekle, zaten_takipte = False, False

        if karar_bulundu_mu:
            kaynak_belge_adi = sutun_degeri_al(k_row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no', 'no:'])
            gosterilecek_karar = ""
            k_ordin_cols = [col for col in k_row.index if 'ordin' in str(col).lower() or 'karar' in str(col).lower() or 'no' in str(col).lower()]
            if k_ordin_cols: gosterilecek_karar = str(k_row[k_ordin_cols[0]]).strip()

            if not gosterilecek_karar or gosterilecek_karar.lower() in ['nan', 'none', '', 'belirtilmemiş']:
                pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)\s*[/]?\s*([pP])?', kaynak_belge_adi, re.IGNORECASE)
                if pdf_match: gosterilecek_karar = f"{pdf_match.group(1)}{'/P' if pdf_match.group(2) else ''}"

            if not gosterilecek_karar and p_numarasi: gosterilecek_karar = p_numarasi
            if gosterilecek_karar:
                p_format_match = re.search(r'(\d+)\s*[/]?\s*P', str(gosterilecek_karar), re.IGNORECASE)
                if p_format_match: gosterilecek_karar = f"{p_format_match.group(1)}/P"
                else: gosterilecek_karar = "-"
            else: gosterilecek_karar = "-"
            
            karar_tarihi = sutun_degeri_al(k_row, ['Tarih', 'Data', 'Karar Tarihi'])
            if not karar_tarihi or str(karar_tarihi).strip().lower() in ["nan", "none", ""]: 
                date_match = re.search(r'(\d{2}[._\s]\d{2}[._\s]\d{4})', kaynak_belge_adi)
                karar_tarihi = date_match.group(1).replace('_', '.').replace('-', '.') if date_match else "-"

            yanit += f"{dil_paketi['onay_var']}\n\n📜 <b>{dil_paketi['karar_no']}:</b> {gosterilecek_karar}\n📅 <b>{dil_paketi['tarih']}:</b> {karar_tarihi}\n📂 <b>{dil_paketi['kaynak']}:</b> {kaynak_belge_adi}"
        else:
            takip_listesi = hafiza['bekleyenler']
            if any(str(k.get('chat_id')) == str(chat_id) and str(k.get('dosya_no')) == str(bulut_takip_formati) for k in takip_listesi):
                zaten_takipte = True
            else:
                buton_ekle = True

            yanit += dil_paketi["henuz_yok"]
            if zaten_takipte: yanit += "\n━━━━━━━━━━━━━━━━━━\n" + dil_paketi["takipte"]

        # 📢 PAYLAŞ BUTONU HAZIRLIĞI
        bot_username = context.bot.username
        share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text=🇹🇩%20Romanya%20Vatandaslik%20Dosya%20Sorgulama%20ve%20Takip%20Botunu%20kesinlikle%20tavsiye%20ederim!"
        
        buton_metni = "📢 Botu Arkadaşına Öner"
        if kullanici_dili == "ru": buton_metni = "📢 Порекомендуй бота другу"
        elif kullanici_dili == "ro": buton_metni = "📢 Recomandă botul unui prieten"
        
        share_button = InlineKeyboardButton(buton_metni, url=share_url)

        # 🛠 KLAVYE OLUŞTURMA (Takip Et ve Paylaş Butonlarını Birlikte Sunar)
        klavye = []
        if buton_ekle:
            klavye.append([InlineKeyboardButton(dil_paketi["buton_takip"], callback_data=f"kvkk_{ana_no}_{ana_yil}")])
        
        klavye.append([share_button]) # Paylaş butonunu her halükarda en alta ekler
        reply_markup = InlineKeyboardMarkup(klavye)

        await update.message.reply_text(yanit, parse_mode='HTML', reply_markup=reply_markup, disable_web_page_preview=True)

# ==========================================
# 🔘 BUTON TIKLAMA VE KVKK SÜRECİ
# ==========================================
async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # --- YENİ EKLENEN DUYURU BUTONU KONTROLÜ ---
    if query.data == "duyuru_start":
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="🔎 <b>Sorgulama İşlemi</b>\n\nLütfen güncel durumunu öğrenmek istediğiniz dosya numarasını <code>1234/2023</code> formatında buraya yazarak bana gönderin.",
            parse_mode='HTML'
        )
        return
    chat_id = str(query.message.chat_id)
    
    if query.data == "dil_iptal":
        kullanici_dili = hafiza['kullanici_dilleri'].get(chat_id, "tr")
        dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])
        await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')
        return

    if query.data.startswith("dil_"):
        secilen_dil = query.data.split("_")[1] 
        hafiza['kullanici_dilleri'][chat_id] = secilen_dil
        set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum'], hafiza['kullanici_dilleri'])
        onay_mesaji = DIL_SOZLUGU.get(secilen_dil, DIL_SOZLUGU["tr"])["secildi"]
        await query.edit_message_text(text=onay_mesaji, parse_mode='HTML')
        return

    kullanici_dili = hafiza['kullanici_dilleri'].get(chat_id, "tr")
    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])
    
    if query.data.startswith("kvkk_"):
        _, ilk_no, son_yil = query.data.split('_')
        kvkk_metni = dil_paketi["kvkk"].format(dosya=f"{ilk_no}/{son_yil}")
        klavye = [
            [InlineKeyboardButton(dil_paketi["onay_evet"], callback_data=f"takip_{ilk_no}_{son_yil}")],
            [InlineKeyboardButton(dil_paketi["onay_hayir"], callback_data="iptal_takip")]
        ]
        await query.edit_message_text(text=kvkk_metni, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "iptal_takip":
        await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')
        return

    if query.data.startswith("takip_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no_temiz = f"{ilk_no}/{son_yil}"
        
        bulut_verisi = get_bulut_verisi()
        if bulut_verisi is None:
            await query.edit_message_text(text=dil_paketi["hata_bulut"])
            return
            
        hafiza['bekleyenler'] = bulut_verisi.get("bekleyenler", [])
        hafiza['son_durum'] = bulut_verisi.get("son_durum", {})

        if any(str(k.get('chat_id')) == chat_id and str(k.get('dosya_no')) == dosya_no_temiz for k in hafiza['bekleyenler']):
            await query.edit_message_text(text=dil_paketi["zaten_takip"].format(dosya=dosya_no_temiz))
            return
            
        hafiza['bekleyenler'].append({"chat_id": chat_id, "dosya_no": dosya_no_temiz})
        kayit_basarili = set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum'], hafiza['kullanici_dilleri']) 
        
        if kayit_basarili: await query.edit_message_text(text=dil_paketi["takip_basarili"].format(dosya=dosya_no_temiz), parse_mode='HTML')
        else:
            hafiza['bekleyenler'].pop() 
            await query.edit_message_text(text=dil_paketi["hata_bulut"], parse_mode='HTML')
        return

    if query.data == "menu_birak":
        user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        if not user_takip_listesi:
            await query.edit_message_text(text=dil_paketi["bos"], parse_mode='HTML')
            return
            
        if 'secilenler' not in context.user_data: context.user_data['secilenler'] = []
        context.user_data['secilenler'] = [d for d in context.user_data['secilenler'] if d in user_takip_listesi]
        secilenler = context.user_data['secilenler']
        
        klavye = []
        for d in user_takip_listesi:
            ilk_no, son_yil = d.split('/')
            klavye.append([InlineKeyboardButton(f"{'✅' if d in secilenler else '⬜'} {d}", callback_data=f"tsil_{ilk_no}_{son_yil}")])
            
        if secilenler: klavye.append([InlineKeyboardButton(dil_paketi["secilenleri_sil"].format(sayi=len(secilenler)), callback_data="toplusil_onay")])
        klavye.append([InlineKeyboardButton(dil_paketi["ana_menu_don"], callback_data="silvazgec")])
        
        await query.edit_message_text(text=dil_paketi["menu_sil_baslik"], parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data.startswith("tsil_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no_temiz = f"{ilk_no}/{son_yil}"
        if 'secilenler' not in context.user_data: context.user_data['secilenler'] = []
        if dosya_no_temiz in context.user_data['secilenler']: context.user_data['secilenler'].remove(dosya_no_temiz)
        else: context.user_data['secilenler'].append(dosya_no_temiz)
            
        user_takip_listesi = [k.get('dosya_no') for k in hafiza['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        secilenler = context.user_data['secilenler']
        
        klavye = []
        for d in user_takip_listesi:
            i_no, s_yil = d.split('/')
            klavye.append([InlineKeyboardButton(f"{'✅' if d in secilenler else '⬜'} {d}", callback_data=f"tsil_{i_no}_{s_yil}")])
            
        if secilenler: klavye.append([InlineKeyboardButton(dil_paketi["secilenleri_sil"].format(sayi=len(secilenler)), callback_data="toplusil_onay")])
        klavye.append([InlineKeyboardButton(dil_paketi["ana_menu_don"], callback_data="silvazgec")])
        
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_onay":
        secilenler = context.user_data.get('secilenler', [])
        dosyalar_raporu = "\n".join([f"❌ <code>{d}</code>" for d in secilenler])
        soru_metni = dil_paketi["sil_onay_soru"].format(liste=dosyalar_raporu)
        
        klavye = [
            [InlineKeyboardButton(dil_paketi["evet_sil"], callback_data="toplusil_confirm")],
            [InlineKeyboardButton(dil_paketi["hayir_don"], callback_data="menu_birak")]
        ]
        await query.edit_message_text(text=soru_metni, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_confirm":
        secilenler = context.user_data.get('secilenler', [])
        bulut_verisi = get_bulut_verisi()
        if bulut_verisi is None:
            await query.edit_message_text(text=dil_paketi["hata_bulut"])
            return
            
        hafiza['bekleyenler'] = bulut_verisi.get("bekleyenler", [])
        hafiza['son_durum'] = bulut_verisi.get("son_durum", {})
        eski_liste = list(hafiza['bekleyenler']) 
        
        hafiza['bekleyenler'] = [k for k in hafiza['bekleyenler'] if not (str(k.get('chat_id')) == chat_id and k.get('dosya_no') in secilenler)]
        kayit_basarili = set_bulut_verisi(hafiza['bekleyenler'], hafiza['son_durum'], hafiza['kullanici_dilleri'])
        
        if kayit_basarili:
            context.user_data['secilenler'] = []
            await query.edit_message_text(text=dil_paketi["sil_basarili"], parse_mode='HTML')
        else:
            hafiza['bekleyenler'] = eski_liste 
            await query.edit_message_text(text=dil_paketi["hata_bulut"], parse_mode='HTML')
        return

    if query.data == "silvazgec":
        context.user_data['secilenler'] = []
        await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')
        return

# ==========================================
# 📈 YÖNETİCİYE ÖZEL GÜNLÜK ÖZET RAPOR
# ==========================================
async def gunluk_otomatik_rapor(context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_CHAT_ID:
        bekleyenler = hafiza['bekleyenler']
        df_dosya = hafiza.get('df_dosya', pd.DataFrame())
        df_karar = hafiza.get('df_karar_birlesik', pd.DataFrame())
        
        # --- HIZLI ARAMA OPTİMİZASYONU ---
        hizli_kaynak_sozlugu = {}
        if not df_dosya.empty:
            arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if 'Dosya No' in df_dosya.columns else df_dosya.iloc[:, 0].astype(str).str.strip()
            kaynak_col = next((col for col in df_dosya.columns if 'kaynak' in str(col).lower() and 'dosya no' not in str(col).lower()), None)
            
            if kaynak_col:
                dosya_list = arama_sutunu.tolist()
                kaynak_list = df_dosya[kaynak_col].astype(str).tolist()
                for d_no, k_metin in zip(dosya_list, kaynak_list):
                    m = re.match(r'^(\d+)/.*?(\d{4})$', str(d_no).strip())
                    if m:
                        kilit = f"{m.group(1)}/{m.group(2)}"
                        hizli_kaynak_sozlugu[kilit] = k_metin

        # --- BEKLEYEN VE ONAYLANAN DOSYALARI AYRIŞTIR ---
        count_m10, count_m11 = 0, 0
        onaylanan_listesi = []

        for kisi in bekleyenler:
            dosya_tam = kisi['dosya_no']
            kaynak_dosya_metni = hizli_kaynak_sozlugu.get(dosya_tam, "")
            
            is_m10 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
            madde_etiketi = "Madde 10" if is_m10 else "Madde 11"
            
            if kisi.get('onaylandi', False):
                # Onaylanan dosyanın karar belgesini (PDF) bul
                karar_pdf = kisi.get('karar_belgesi', "")
                
                if not karar_pdf and not df_karar.empty:
                    try:
                        ana_no, ana_yil = dosya_tam.split('/')
                        regex_find = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
                        mask = pd.Series(False, index=df_karar.index)
                        for col in df_karar.columns:
                            if col != 'Kaynak Belge':
                                temiz_sutun = df_karar[col].astype(str).str.replace(r'\s+', '', regex=True)
                                mask |= temiz_sutun.str.contains(regex_find, case=False, regex=True)
                        eslesen = df_karar[mask]
                        if not eslesen.empty:
                            karar_pdf = str(eslesen.iloc[0].get('Kaynak Belge', ''))
                            kisi['karar_belgesi'] = karar_pdf  # Bir dahaki sefere hızlı bulması için hafızaya kaydet
                    except Exception:
                        pass
                
                ek_metin = f" - 📄 <i>{karar_pdf}</i>" if karar_pdf else ""
                onaylanan_listesi.append(f"▪️ <code>{dosya_tam}</code> ({madde_etiketi}){ek_metin}")
            else:
                if is_m10: count_m10 += 1
                else: count_m11 += 1

        aktif_bekleyen_sayisi = count_m10 + count_m11
        onaylanan_sayisi = len(onaylanan_listesi)

        tsi_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
        saat_metni = tsi_now.strftime("%H:%M")
        
        rapor_msg = (
            f"📊 <b>GÜNLÜK ÖZET SİSTEM RAPORU</b>\n\n"
            f"🕒 <b>Saat:</b> {saat_metni} (TSİ)\n\n"
            f"👥 Bot veritabanında anlık olarak takip edilen ve karar bekleyen <b>toplam dosya sayısı:</b> <code>{aktif_bekleyen_sayisi}</code>\n\n"
            f"🔸 <b>Madde 10 Dosya Sayısı:</b> <code>{count_m10}</code>\n\n"
            f"🔸 <b>Madde 11 Dosya Sayısı:</b> <code>{count_m11}</code>\n\n"
            f"✅ <b>Şu ana kadar onayı çıkan dosya sayısı:</b> <code>{onaylanan_sayisi}</code>\n"
        )
        
        if onaylanan_sayisi > 0:
            rapor_msg += f"\n<b>🏆 Onaylanan Dosyalar:</b>\n" + "\n".join(onaylanan_listesi) + "\n\n"
        else:
            rapor_msg += "\n"

        rapor_msg += f"<i>Sistem 7/24 ANC listelerini nöbette beklemeye devam ediyor. 🇹🇩</i>"
        
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=rapor_msg, parse_mode='HTML')
            print(f"✅ Günlük admin özet raporu ({saat_metni}) kırılımlarla birlikte başarıyla gönderildi.", flush=True)
        except Exception as e:
            print(f"Günlük rapor gönderilirken hata oluştu: {e}", flush=True)


# ==========================================
# 📊 YÖNETİCİYE ÖZEL MANUEL RAPOR KOMUTU (/rapor)
# ==========================================
async def rapor_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    if chat_id != str(ADMIN_CHAT_ID):
        return 
        
    bekleyenler = hafiza['bekleyenler']
    df_dosya = hafiza.get('df_dosya', pd.DataFrame())
    df_karar = hafiza.get('df_karar_birlesik', pd.DataFrame())
    
    # --- HIZLI ARAMA OPTİMİZASYONU ---
    hizli_kaynak_sozlugu = {}
    if not df_dosya.empty:
        arama_sutunu = df_dosya['Dosya No'].astype(str).str.strip() if 'Dosya No' in df_dosya.columns else df_dosya.iloc[:, 0].astype(str).str.strip()
        kaynak_col = next((col for col in df_dosya.columns if 'kaynak' in str(col).lower() and 'dosya no' not in str(col).lower()), None)
        
        if kaynak_col:
            dosya_list = arama_sutunu.tolist()
            kaynak_list = df_dosya[kaynak_col].astype(str).tolist()
            for d_no, k_metin in zip(dosya_list, kaynak_list):
                m = re.match(r'^(\d+)/.*?(\d{4})$', str(d_no).strip())
                if m:
                    kilit = f"{m.group(1)}/{m.group(2)}"
                    hizli_kaynak_sozlugu[kilit] = k_metin

    # --- BEKLEYEN VE ONAYLANAN DOSYALARI AYRIŞTIR ---
    count_m10, count_m11 = 0, 0
    onaylanan_listesi = []

    for kisi in bekleyenler:
        dosya_tam = kisi['dosya_no']
        kaynak_dosya_metni = hizli_kaynak_sozlugu.get(dosya_tam, "")
        
        is_m10 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
        madde_etiketi = "Madde 10" if is_m10 else "Madde 11"
        
        if kisi.get('onaylandi', False):
            # Onaylanan dosyanın karar belgesini (PDF) bul
            karar_pdf = kisi.get('karar_belgesi', "")
            
            if not karar_pdf and not df_karar.empty:
                try:
                    ana_no, ana_yil = dosya_tam.split('/')
                    regex_find = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
                    mask = pd.Series(False, index=df_karar.index)
                    for col in df_karar.columns:
                        if col != 'Kaynak Belge':
                            temiz_sutun = df_karar[col].astype(str).str.replace(r'\s+', '', regex=True)
                            mask |= temiz_sutun.str.contains(regex_find, case=False, regex=True)
                    eslesen = df_karar[mask]
                    if not eslesen.empty:
                        karar_pdf = str(eslesen.iloc[0].get('Kaynak Belge', ''))
                        kisi['karar_belgesi'] = karar_pdf  # Bir dahaki sefere hızlı bulması için hafızaya kaydet
                except Exception:
                    pass
            
            ek_metin = f" - 📄 <i>{karar_pdf}</i>" if karar_pdf else ""
            onaylanan_listesi.append(f"▪️ <code>{dosya_tam}</code> ({madde_etiketi}){ek_metin}")
        else:
            if is_m10: count_m10 += 1
            else: count_m11 += 1

    aktif_bekleyen_sayisi = count_m10 + count_m11
    onaylanan_sayisi = len(onaylanan_listesi)

    tsi_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    saat_metni = tsi_now.strftime("%H:%M")
    
    rapor_msg = (
        f"📊 <b>GÜNLÜK ÖZET SİSTEM RAPORU</b>\n\n"
        f"🕒 <b>Saat:</b> {saat_metni} (TSİ)\n\n"
        f"👥 Bot veritabanında anlık olarak takip edilen ve karar bekleyen <b>toplam dosya sayısı:</b> <code>{aktif_bekleyen_sayisi}</code>\n\n"
        f"🔸 <b>Madde 10 Dosya Sayısı:</b> <code>{count_m10}</code>\n\n"
        f"🔸 <b>Madde 11 Dosya Sayısı:</b> <code>{count_m11}</code>\n\n"
        f"✅ <b>Şu ana kadar onayı çıkan dosya sayısı:</b> <code>{onaylanan_sayisi}</code>\n"
    )
    
    if onaylanan_sayisi > 0:
        rapor_msg += f"\n<b>🏆 Onaylanan Dosyalar:</b>\n" + "\n".join(onaylanan_listesi) + "\n\n"
    else:
        rapor_msg += "\n"

    rapor_msg += f"<i>Sistem 7/24 ANC listelerini nöbette beklemeye devam ediyor. 🇹🇩</i>"
    
    try:
        await update.message.reply_text(rapor_msg, parse_mode='HTML')
    except Exception as e:
        print(f"Manuel rapor gönderilirken hata: {e}", flush=True)
        
# ==========================================
# 📢 YÖNETİCİ GENEL DUYURU (ÖZÜR) MOTORU
# ==========================================
async def duyuru_gonder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Bu komutu kullanma yetkiniz bulunmamaktadır.")
        return

    bekleyenler = hafiza.get('bekleyenler', [])
    if not bekleyenler:
        bulut = get_bulut_verisi()
        if bulut:
            bekleyenler = bulut.get("bekleyenler", [])
            hafiza['bekleyenler'] = bekleyenler

    hedef_chat_idleri = list(set([str(k['chat_id']) for k in bekleyenler if 'chat_id' in k]))

    if not hedef_chat_idleri:
        await update.message.reply_text("❌ Sistemde kayıtlı kullanıcı bulunamadı.")
        return

    # --- PROFESYONEL ÖZÜR METNİ ---
    duyuru_metni = (
        "📢 <b>Önemli Bilgilendirme ve Teknik Özür</b>\n\n"
        "Değerli Kullanıcılarımız,\n\n"
        "Sistemimizi geliştirmek ve sizlere çok daha hızlı hizmet sunabilmek adına bugün yaptığımız altyapı güncellemeleri sırasında, teknik bir aksaklık sebebiyle bazı kullanıcılarımıza <b>hatalı dosya güncelleme veya onay bildirimleri</b> iletilmiştir.\n\n"
        "Eğer bugün dosyanızla ilgili sistemimizden beklenmedik bir bildirim aldıysanız, lütfen bu mesajı dikkate almayınız. Dosyanızın gerçek ve en güncel durumunu teyit etmek için bota dosya numaranızı (Örn: 1234/2023) yazarak dilediğiniz zaman yeniden sorgulama yapabilirsiniz.\n\n"
        "Yaşanan bu kısa süreli teknik aksaklıktan dolayı özür diler, sistemimizin şu an sorunsuz ve aktif bir şekilde nöbetine devam ettiğini bildirmek isteriz. Anlayışınız için teşekkür ederiz. 🇹🇩"
    )
    
    # Kullanıcıyı manuel sorgulamaya teşvik eden buton
    klavye = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Dosyamın Gerçek Durumunu Sorgula", callback_data="duyuru_start")]
    ])

    gorsel_yolu = "duyuru.png"
    
    basarili = 0
    hatali = 0
    
    await update.message.reply_text(f"📢 Özür duyurusu {len(hedef_chat_idleri)} kayıtlı kullanıcıya iletilmeye başlanıyor. Lütfen bitene kadar bekleyin...")

    for hedef_id in hedef_chat_idleri:
        try:
            if os.path.exists(gorsel_yolu):
                with open(gorsel_yolu, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=hedef_id,
                        photo=photo,
                        caption=duyuru_metni,
                        parse_mode='HTML',
                        reply_markup=klavye
                    )
            else:
                await context.bot.send_message(
                    chat_id=hedef_id,
                    text=duyuru_metni,
                    parse_mode='HTML',
                    reply_markup=klavye
                )
            basarili += 1
        except Exception as e:
            hatali += 1
            print(f"Duyuru iletilemedi ({hedef_id}): {e}")

        # Telegram spam engeline (FloodWait) takılmamak için 0.5 saniye bekleme
        await asyncio.sleep(0.5)

    await update.message.reply_text(
        f"✅ <b>Duyuru Başarıyla Dağıtıldı!</b>\n\n"
        f"📤 Başarılı İletim: {basarili}\n"
        f"🚫 Ulaşılamayan/Botu Engelleyen: {hatali}",
        parse_mode='HTML'
    )

    
# ==========================================
# ⚙️ ANA ÇALIŞTIRMA VE ZAMANLAYICI (POLLING)
# ==========================================
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def post_init(application: Application):
        async def baslangic_taramasi(context: ContextTypes.DEFAULT_TYPE):
            veritabanini_kontrol_et(context.application)
        
        # Bot ayağa kalktıktan 2 sn sonra ilk kontrol
        application.job_queue.run_once(baslangic_taramasi, 2)
        
        # Her gün TSİ 20:00 (UTC 17:00) otomatik yönetici raporu
        hedef_zaman_utc = datetime.time(hour=17, minute=0, tzinfo=datetime.timezone.utc)
        application.job_queue.run_daily(gunluk_otomatik_rapor, time=hedef_zaman_utc)
        
    app.post_init = post_init
    app.add_handler(CommandHandler("start", start_command))    
    app.add_handler(CommandHandler("setlanguage", dil_komutu))
    app.add_handler(CommandHandler("rapor", rapor_komutu)) # <--- BU SATIRI EKLEYİN
    app.add_handler(CommandHandler("duyuru", duyuru_gonder))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    app.run_polling(drop_pending_updates=True)