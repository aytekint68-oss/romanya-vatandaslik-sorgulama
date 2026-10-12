import os
import re
import asyncio
import datetime
import time
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import RetryAfter

# ==========================================
# 🌐 ÇOKLU DİL SÖZLÜĞÜ (i18n) - KORUNDU
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
            "Sistemde sunulan veriler tamamen bilgilendirme amaçlıdır ve hiçbir şekilde resmi tebligat, onay veya hukuki belge niteliği taşımaz. Veri senkronizasyonunda yaşanabilecek teknik gecikmelerden, hatalardan sau ANC listelerindeki tipografik yanlışlardan platform sorumlu tutulamaz. Nihai ve kesin teyit için her zaman resmi kurum kaynaklarını referans alınız.</i>"
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
        "guncelleme_1_karar_1_dosya": "🔔 <b>Sistem Güncellemesi:</b>\nANC sistemine yeni bir karar (ordin) yüklenmiştir:\n{yeni_dosyalar}\n\nMaalesef takip ettiğiniz şu dosya bu yeni listede görünmemiştir:\n{dosyalar}\n\nTakip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏",
        "guncelleme_1_karar_cok_dosya": "🔔 <b>Sistem Güncellemesi:</b>\nANC sistemine yeni bir karar (ordin) yüklenmiştir:\n{yeni_dosyalar}\n\nMaalesef takip ettiğiniz şu dosyalar bu yeni listede görünmemiştir:\n{dosyalar}\n\nTakip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏",
        "guncelleme_cok_karar_1_dosya": "🔔 <b>Sistem Güncellemesi:</b>\nANC sistemine yeni kararlar (ordin) yüklenmiştir:\n{yeni_dosyalar}\n\nMaalesef takip ettiğiniz şu dosya bu yeni listelerde görünmemiştir:\n{dosyalar}\n\nTakip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏",
        "guncelleme_cok_karar_cok_dosya": "🔔 <b>Sistem Güncellemesi:</b>\nANC sistemine yeni kararlar (ordin) yüklenmiştir:\n{yeni_dosyalar}\n\nMaalesef takip ettiğiniz şu dosyalar bu yeni listelerde görünmemiştir:\n{dosyalar}\n\nTakip etmeye devam ediyorum, lütfen umudunuzu kaybetmeyin! 🙏",
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
            "<i>Данная платформа представляет собой независимую автоматизированную систему. Наша платформа не имеет официальных связей или партнерских отношений с государством Румыния.</i>"
        ),
        "secildi": "🇷🇺 Язык установлен на русский.\nПожалуйста, отправьте номер вашего досье (Например: 1234/2023).",
        "bos": "❌ Нет данных в системе.",
        "format": "⚠ <b>Неверный формат:</b> Используйте только ОДИН знак '/'. Пример: 1234/2023",
        "gecersiz": "⚠ Системное предупреждение: Недопустимый номер досье или год.",
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
        "guncelleme_1_karar_1_dosya": "🔔 <b>Обновление системы:</b>\nВ систему ANC добавлен новый приказ (ordin):\n{yeni_dosyalar}\n\nК сожалению, отслеживаемое вами досье не найдено в этом новом списке:\n{dosyalar}\n\nПродолжаю отслеживание, не теряйте надежду! 🙏",
        "guncelleme_1_karar_cok_dosya": "🔔 <b>Обновление системы:</b>\nВ систему ANC добавлен новый приказ (ordin):\n{yeni_dosyalar}\n\nК сожалению, отслеживаемые вами досье не найдены в этом новом списке:\n{dosyalar}\n\nПродолжаю отслеживание, не теряйте надежду! 🙏",
        "guncelleme_cok_karar_1_dosya": "🔔 <b>Обновление системы:</b>\nВ систему ANC добавлены новые приказы (ordin):\n{yeni_dosyalar}\n\nК сожалению, отслеживаемое вами досье не найдено в этих новых списках:\n{dosyalar}\n\nПродолжаю отслеживание, не теряйте надежду! 🙏",
        "guncelleme_cok_karar_cok_dosya": "🔔 <b>Обновление системы:</b>\nВ систему ANC добавлены новые приказы (ordin):\n{yeni_dosyalar}\n\nК сожалению, отслеживаемые вами досье не найдены в этих новых списках:\n{dosyalar}\n\nПродолжаю отслеживание, не теряйте надежду! 🙏",
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
            "<i>Această platformă este un sistem automatizat independent, creat pentru a scana listele publice privind stadiul dosarelor. Nu are nicio legătură oficială cu statul român.</i>"
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
        "guncelleme_1_karar_1_dosya": "🔔 <b>Actualizare sistem:</b>\nA fost adăugat un nou ordin în sistemul ANC:\n{yeni_dosyalar}\n\nDin păcate, dosarul pe care îl urmăriți nu a apărut în această nouă listă:\n{dosyalar}\n\nUrmăresc în continuare, nu vă pierdeți speranța! 🙏",
        "guncelleme_1_karar_cok_dosya": "🔔 <b>Actualizare sistem:</b>\nA fost adăugat un nou ordin în sistemul ANC:\n{yeni_dosyalar}\n\nDin păcate, dosarele pe care le urmăriți nu au apărut în această nouă listă:\n{dosyalar}\n\nUrmăresc în continuare, nu vă pierdeți speranța! 🙏",
        "guncelleme_cok_karar_1_dosya": "🔔 <b>Actualizare sistem:</b>\nAu fost adăugate noi ordine în sistemul ANC:\n{yeni_dosyalar}\n\nDin păcate, dosarul pe care îl urmăriți nu a apărut în aceste noi liste:\n{dosyalar}\n\nUrmăresc în continuare, nu vă pierdeți speranța! 🙏",
        "guncelleme_cok_karar_cok_dosya": "🔔 <b>Actualizare sistem:</b>\nAu fost adăugate noi ordine în sistemul ANC:\n{yeni_dosyalar}\n\nDin păcate, dosarele pe care le urmăriți nu au apărut în aceste noi liste:\n{dosyalar}\n\nUrmăresc în continuare, nu vă pierdeți speranța! 🙏",
        "termen_degisti": "🔄 <b>IMPORTANT: Termenul a fost modificat!</b>\n\nDosar: <b>{dosya}</b>\nVechi: <del>{eski}</del>\nNou: {yeni}",
        "stadiu_guncellendi": "🔔 <b>Actualizare sistem:</b>\nListele Stadiu Dosar au fost actualizate ({tarih}).",
        "takip_baslik": "🔔 <b>Dosarele urmărite:</b>"
    }
}

# ==========================================
# 🔐 GÜVENLİ AYARLAR
# ==========================================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not BOT_TOKEN or not MONGO_URI:
    print("❌ HATA: Çevre değişkenleri tanımlanmamış! (Render ayarlarınızı kontrol edin)", flush=True)

print("🤖 Akıllı Asistan (MongoDB Destekli) Başlatılıyor...", flush=True)

# ==========================================
# ☁️ MONGODB BAĞLANTILARI
# ==========================================
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # KULLANICI HAFIZASI İÇİN (Geçmişteki tüm abonelerin tutulduğu db)
    db_kullanici = client["VatandaslikBot"]
    koleksiyon_hafiza = db_kullanici["Hafiza"]
    
    # ANC VERİLERİ İÇİN (Yeni aktardığımız db)
    db_anc = client["anc_veritabani"]
    
    client.admin.command('ping')
    print("✅ MongoDB Atlas bağlantısı kusursuz kuruldu!", flush=True)
except Exception as e:
    print(f"❌ MongoDB Bağlantı Hatası: {e}", flush=True)

# ==========================================
# 🧠 KULLANICI HAFIZA YÖNETİMİ (Değişmedi)
# ==========================================
def get_bulut_verisi():
    try:
        veri = koleksiyon_hafiza.find_one({"_id": "bulut_hafiza"})
        if veri:
            return {
                "bekleyenler": veri.get("bekleyenler", []), 
                "son_durum": veri.get("son_durum", {}),
                "kullanici_dilleri": veri.get("kullanici_dilleri", {})
            }
        return {"bekleyenler": [], "son_durum": {}, "kullanici_dilleri": {}}
    except Exception as e:
        print(f"⚠️ Hafıza Okuma Hatası: {e}", flush=True)
        return None 

def set_bulut_verisi(bekleyenler, son_durum, kullanici_dilleri):
    try:
        koleksiyon_hafiza.update_one(
            {"_id": "bulut_hafiza"}, 
            {"$set": {"bekleyenler": bekleyenler, "son_durum": son_durum, "kullanici_dilleri": kullanici_dilleri}}, 
            upsert=True
        )
        return True
    except Exception as e:
        print(f"❌ Hafıza Kayıt Hatası: {e}", flush=True)
        return False

# ==========================================
# 🔍 VERİTABANI İSTATİSTİK YARDIMCILARI
# ==========================================
def sutun_degeri_al(row_dict, olasi_isimler, haric_kelimeler=None):
    if haric_kelimeler is None: haric_kelimeler = []
    for col in row_dict.keys():
        col_clean = str(col).strip().lower()
        if any(h.lower() in col_clean for h in haric_kelimeler): continue
        for hedef in olasi_isimler:
            if hedef.lower() in col_clean:
                val = str(row_dict[col]).strip()
                if val.lower() not in ['nan', 'none']: return val
    return ""

def pano_istatistiklerini_getir():
    """Bot başlangıcında gösterilecek pano verilerini hafifçe çeker"""
    d_tarih = "Bilinmiyor"
    
    stadiu_kaynaklar = db_anc.stadiu_dosar.distinct("Kaynak Belge")
    valid_dates = []
    for k in stadiu_kaynaklar:
        match = re.search(r'(\d{2}[\.\-\_]\d{2}[\.\-\_]\d{4})', str(k))
        if match:
            try:
                dt_str = match.group(1).replace('_', '.').replace('-', '.')
                valid_dates.append(datetime.datetime.strptime(dt_str, '%d.%m.%Y'))
            except: pass
    if valid_dates: d_tarih = max(valid_dates).strftime('%d.%m.%Y')

    def son_belgeler(koleksiyon_adi):
        sample = db_anc[koleksiyon_adi].find_one()
        if not sample: return ["Veri Yok"]
        ordin_col = next((col for col in sample.keys() if 'ordin' in str(col).lower() or 'karar' in str(col).lower()), None)
        proj = {"Kaynak Belge": 1, "_id": 0}
        if ordin_col: proj[ordin_col] = 1
        docs = list(db_anc[koleksiyon_adi].find({}, proj))
        unique_list = []
        for d in docs:
            kb = str(d.get("Kaynak Belge", "")).strip()
            if kb and kb.lower() not in ['nan', 'none'] and kb not in unique_list: unique_list.append(kb)
        return unique_list[:5] if unique_list else ["Veri Yok"]

    return d_tarih, son_belgeler("kararlar_m10"), son_belgeler("kararlar_m11")

# ==========================================
# 💬 TELEGRAM ARAMA VE YANIT MANTIĞI
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat_id)
    bulut = get_bulut_verisi()
    
    kullanici_dili = bulut.get("kullanici_dilleri", {}).get(chat_id) if bulut else None
    if not kullanici_dili:
        klavye = [[InlineKeyboardButton("🇹🇷 Türkçe", callback_data="dil_tr")],
                  [InlineKeyboardButton("🇷🇺 Русский", callback_data="dil_ru")],
                  [InlineKeyboardButton("🇷🇴 Română", callback_data="dil_ro")]]
        await update.message.reply_text(DIL_SOZLUGU["tr"]["secim"], reply_markup=InlineKeyboardMarkup(klavye))
        return

    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])
    d_tarih, m10_files, m11_files = pano_istatistiklerini_getir()

    m10_metin = "\n".join([f"🔸 {b}" for b in m10_files]) if m10_files[0] != "Veri Yok" else "🔸 -"
    m11_metin = "\n".join([f"🔸 {b}" for b in m11_files]) if m11_files[0] != "Veri Yok" else "🔸 -"

    bekleyenler = bulut.get("bekleyenler", []) if bulut else []
    user_takip_objeleri = [k for k in bekleyenler if str(k.get('chat_id')) == chat_id]
    
    reply_markup, takip_metni = None, ""
    if user_takip_objeleri:
        dosyalar_alt_alta = "".join([f"🎉 <del>{k.get('dosya_no')}</del>\n" if k.get('onaylandi') else f"⏳ <code>{k.get('dosya_no')}</code>\n" for k in user_takip_objeleri])
        takip_metni = f"\n━━━━━━━━━━━━━━━━━━\n{dil_paketi.get('takip_baslik', '🔔')}\n\n{dosyalar_alt_alta}\n"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(dil_paketi["buton_birak"], callback_data="menu_birak")]])

    mesaj = dil_paketi["karsilama"].format(tarih=d_tarih, m10_liste=m10_metin, m11_liste=m11_metin, takip=takip_metni)
    await update.message.reply_text(mesaj, parse_mode='HTML', reply_markup=reply_markup)

async def dil_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    klavye = [[InlineKeyboardButton("🇹🇷 Türkçe", callback_data="dil_tr")],
              [InlineKeyboardButton("🇷🇺 Русский", callback_data="dil_ru")],
              [InlineKeyboardButton("🇷🇴 Română", callback_data="dil_ro")],
              [InlineKeyboardButton("❌ Vazgeç / Отмена", callback_data="dil_iptal")]]
    await update.message.reply_text("🌐 Lütfen yeni bir dil seçin / Выберите язык / Selectați limba:", reply_markup=InlineKeyboardMarkup(klavye))

async def mesaj_isleyici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    aranan_kelime = update.message.text.strip().replace(" ", "")
    chat_id = str(update.message.chat_id) 
    
    bulut = get_bulut_verisi() or {"bekleyenler": [], "kullanici_dilleri": {}}
    kullanici_dili = bulut.get("kullanici_dilleri", {}).get(chat_id, "tr")
    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])

    if not re.fullmatch(r'[a-zA-Z0-9/]+', aranan_kelime) or aranan_kelime.count("/") != 1:
        await update.message.reply_text(dil_paketi["format"], parse_mode='HTML')
        return
        
    parcalar = aranan_kelime.split("/")
    ilk_numara = "".join(filter(str.isdigit, parcalar[0]))
    son_yil = "".join(filter(str.isdigit, parcalar[-1]))
    
    if len(ilk_numara) == 0 or int(ilk_numara) == 0 or len(son_yil) != 4:
        await update.message.reply_text(dil_paketi["gecersiz"])
        return

    arama_kriteri = f"^{ilk_numara}/.*{son_yil}$"
    
    # 1. MongoDB - Stadiu Dosar Araması
    sample_dosya = db_anc.stadiu_dosar.find_one()
    if not sample_dosya:
        await update.message.reply_text(dil_paketi["bos"])
        return
        
    dosya_no_col = next((col for col in sample_dosya.keys() if any(x in str(col).lower() for x in ['dosya', 'nr'])), list(sample_dosya.keys())[0])
    sonuclar = list(db_anc.stadiu_dosar.find({dosya_no_col: {"$regex": arama_kriteri, "$options": "i"}}))

    if not sonuclar:
        await update.message.reply_text(dil_paketi["bulunamadi"], parse_mode='HTML')
        return

    row = sonuclar[0] # İlk sonucu al
    ana_no, ana_yil = str(row.get(dosya_no_col, "")).strip().split('/')[0].strip(), str(row.get(dosya_no_col, "")).strip().split('/')[-1].strip()
    bulut_takip_formati = f"{ana_no}/{ana_yil}"
    
    # 2. MongoDB - Özel Durum Kontrolü (40 Gün)
    ozel_mesaj_baslik = ""
    sample_ozel = db_anc.ozel_durumlar.find_one()
    if sample_ozel:
        or_cond = [{k: {"$regex": arama_kriteri, "$options": "i"}} for k in sample_ozel.keys() if k != "_id"]
        ozel_doc = db_anc.ozel_durumlar.find_one({"$or": or_cond})
        if ozel_doc:
            vals = [v for k, v in ozel_doc.items() if k != "_id"]
            ozel_tarih_str, ozel_isim, ozel_ek_bilgi = str(vals[0]) if len(vals)>0 else "-", str(vals[1]) if len(vals)>1 else "-", str(vals[3]) if len(vals)>3 else "-"
            kalan_gun_mesaji = ""
            try:
                gecen_gun = (datetime.datetime.now() - datetime.datetime.strptime(ozel_tarih_str, '%d.%m.%Y')).days
                kalan_gun = 40 - gecen_gun
                if kalan_gun > 0: kalan_gun_mesaji = dil_paketi["gun_kaldi"].format(gun=kalan_gun)
                elif kalan_gun == 0: kalan_gun_mesaji = dil_paketi["bugun_doluyor"]
                else: kalan_gun_mesaji = dil_paketi["sure_doldu"].format(gun=gecen_gun)
            except: pass
            ozel_mesaj_baslik = dil_paketi["uyari_40_gun"].format(tarih=ozel_tarih_str, isim=ozel_isim, not_=ozel_ek_bilgi, kalan_gun_msg=kalan_gun_mesaji) + "\n━━━━━━━━━━━━━━━━━━\n\n"

    # 3. MongoDB - Karar Listeleri Araması
    karar_bulundu_mu, k_row = False, None
    karar_icin_regex = rf"\b{ana_no}\b.*?\b{ana_yil}\b"
    
    # Önce Madde 11'de ara (daha yaygın), yoksa Madde 10'da ara
    for col_name in ["kararlar_m11", "kararlar_m10"]:
        sample_k = db_anc[col_name].find_one()
        if sample_k:
            k_sutun = next((col for col in sample_k.keys() if 'dosya' in str(col).lower() or 'nr' in str(col).lower()), None)
            if k_sutun:
                match_k = db_anc[col_name].find_one({k_sutun: {"$regex": karar_icin_regex, "$options": "i"}})
                if match_k:
                    karar_bulundu_mu, k_row = True, match_k
                    break

    # Değerleri Parse Etme
    solutie_metni = sutun_degeri_al(row, ['SOLUTIE', 'Solutie', 'Kurum Notu'])
    termen_metni = sutun_degeri_al(row, ['TERMEN', 'Termen', 'Sonraki Aşama'])
    
    sol_tarih_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', solutie_metni)
    if sol_tarih_match and not re.search(r'\d+\s*/?\s*P', solutie_metni, re.IGNORECASE):
        termen_metni, solutie_metni = sol_tarih_match.group(1), ""

    termen = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', termen_metni).group(1).replace('/', '.').replace('-', '.') if re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', termen_metni) else (termen_metni if termen_metni else "-")

    # MongoDB - Eski Termen Araması
    eski_termen = ""
    sample_eski = db_anc.stadiu_dosar_eski.find_one()
    if sample_eski:
        eski_dosya_col = next((col for col in sample_eski.keys() if any(x in str(col).lower() for x in ['dosya', 'nr'])), None)
        if eski_dosya_col:
            eski_match = db_anc.stadiu_dosar_eski.find_one({eski_dosya_col: {"$regex": arama_kriteri, "$options": "i"}})
            if eski_match:
                e_ter = sutun_degeri_al(eski_match, ['TERMEN', 'Termen'])
                et_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_ter)
                eski_termen = et_m.group(1).replace('/', '.').replace('-', '.') if et_m else str(e_ter).strip()

    if eski_termen and eski_termen != termen and eski_termen.lower() not in ['nan', 'none']: termen = f"{termen} <i>({eski_termen})</i> 🔄"

    kaynak_dosya_metni = sutun_degeri_al(row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no'])
    kurum_notu = solutie_metni if solutie_metni else "-"
    basvuru_tarihi = sutun_degeri_al(row, ['Başvuru Tarihi', 'DATA ÎNREGISTRĂRII', 'Tarih'])
    b_match = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', basvuru_tarihi)
    basvuru_tarihi = b_match.group(1).replace('/', '.').replace('-', '.') if b_match else (basvuru_tarihi if basvuru_tarihi else "-")

    yanit = ozel_mesaj_baslik + (
        f"{dil_paketi['dosya_baslik']}\n\n<b>No:</b> {row.get(dosya_no_col, bulut_takip_formati)}\n━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>{dil_paketi['basvuru']}:</b> {basvuru_tarihi}\n"
        f"⏳ <b>{dil_paketi['termen']}:</b> {termen}\n"
        f"📝 <b>{dil_paketi['solutie']}:</b> {kurum_notu}\n"
        f"📂 <b>{dil_paketi['kaynak']}:</b> {kaynak_dosya_metni}\n━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ <b>{dil_paketi['karar_baslik']}</b>\n\n"
    )

    buton_ekle, zaten_takipte = False, False
    if karar_bulundu_mu:
        kaynak_belge_adi = sutun_degeri_al(k_row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no'])
        gosterilecek_karar = next((str(k_row[col]).strip() for col in k_row.keys() if 'ordin' in col.lower() or 'karar' in col.lower()), "")
        if not gosterilecek_karar or gosterilecek_karar.lower() in ['nan', 'none', '']:
            pdf_match = re.search(r'(?:ordin|nr)[^\d]*(\d+)\s*[/]?\s*([pP])?', kaynak_belge_adi, re.IGNORECASE)
            gosterilecek_karar = f"{pdf_match.group(1)}{'/P' if pdf_match.group(2) else ''}" if pdf_match else "-"
        
        p_format_match = re.search(r'(\d+)\s*[/]?\s*P', str(gosterilecek_karar), re.IGNORECASE)
        gosterilecek_karar = f"{p_format_match.group(1)}/P" if p_format_match else gosterilecek_karar
        
        karar_tarihi = sutun_degeri_al(k_row, ['Tarih', 'Data'])
        if not karar_tarihi or str(karar_tarihi).strip().lower() in ["nan", "none"]: 
            d_match = re.search(r'(\d{2}[._\s]\d{2}[._\s]\d{4})', kaynak_belge_adi)
            karar_tarihi = d_match.group(1).replace('_', '.').replace('-', '.') if d_match else "-"

        yanit += f"{dil_paketi['onay_var']}\n\n📜 <b>{dil_paketi['karar_no']}:</b> {gosterilecek_karar}\n📅 <b>{dil_paketi['tarih']}:</b> {karar_tarihi}\n📂 <b>{dil_paketi['kaynak']}:</b> {kaynak_belge_adi}"
    else:
        takip_listesi = bulut.get('bekleyenler', [])
        zaten_takipte = any(str(k.get('chat_id')) == str(chat_id) and str(k.get('dosya_no')) == str(bulut_takip_formati) for k in takip_listesi)
        buton_ekle = not zaten_takipte
        yanit += dil_paketi["henuz_yok"] + ("\n━━━━━━━━━━━━━━━━━━\n" + dil_paketi["takipte"] if zaten_takipte else "")

    share_button = InlineKeyboardButton("📢 Botu Öner" if kullanici_dili=="tr" else "📢 Recommend", url=f"https://t.me/share/url?url=https://t.me/{context.bot.username}")
    klavye = [[InlineKeyboardButton(dil_paketi["buton_takip"], callback_data=f"kvkk_{ana_no}_{ana_yil}")]] if buton_ekle else []
    klavye.append([share_button])
    
    await update.message.reply_text(yanit, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye), disable_web_page_preview=True)

# ==========================================
# 🔘 BUTON TIKLAMA VE KVKK (Değişmedi, MongoDB Entegreli)
# ==========================================
async def buton_tiklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    bulut = get_bulut_verisi() or {"bekleyenler": [], "son_durum": {}, "kullanici_dilleri": {}}
    kullanici_dili = bulut.get("kullanici_dilleri", {}).get(chat_id, "tr")
    dil_paketi = DIL_SOZLUGU.get(kullanici_dili, DIL_SOZLUGU["tr"])

    if query.data.startswith("dil_"):
        if query.data == "dil_iptal":
            await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')
            return
        secilen_dil = query.data.split("_")[1] 
        bulut['kullanici_dilleri'][chat_id] = secilen_dil
        set_bulut_verisi(bulut['bekleyenler'], bulut['son_durum'], bulut['kullanici_dilleri'])
        await query.edit_message_text(text=DIL_SOZLUGU[secilen_dil]["secildi"], parse_mode='HTML')
        return

    if query.data.startswith("kvkk_"):
        _, ilk_no, son_yil = query.data.split('_')
        kvkk_metni = dil_paketi["kvkk"].format(dosya=f"{ilk_no}/{son_yil}")
        klavye = [[InlineKeyboardButton(dil_paketi["onay_evet"], callback_data=f"takip_{ilk_no}_{son_yil}")],
                  [InlineKeyboardButton(dil_paketi["onay_hayir"], callback_data="iptal_takip")]]
        await query.edit_message_text(text=kvkk_metni, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "iptal_takip":
        await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')
        return

    if query.data.startswith("takip_"):
        _, ilk_no, son_yil = query.data.split('_')
        dosya_no_temiz = f"{ilk_no}/{son_yil}"
        if any(str(k.get('chat_id')) == chat_id and str(k.get('dosya_no')) == dosya_no_temiz for k in bulut['bekleyenler']):
            await query.edit_message_text(text=dil_paketi["zaten_takip"].format(dosya=dosya_no_temiz))
            return
        bulut['bekleyenler'].append({"chat_id": chat_id, "dosya_no": dosya_no_temiz})
        set_bulut_verisi(bulut['bekleyenler'], bulut['son_durum'], bulut['kullanici_dilleri']) 
        await query.edit_message_text(text=dil_paketi["takip_basarili"].format(dosya=dosya_no_temiz), parse_mode='HTML')
        return

    if query.data == "menu_birak":
        user_takip_listesi = [k.get('dosya_no') for k in bulut['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        if not user_takip_listesi: return await query.edit_message_text(text=dil_paketi["bos"], parse_mode='HTML')
        context.user_data['secilenler'] = []
        klavye = [[InlineKeyboardButton(f"⬜ {d}", callback_data=f"tsil_{d.replace('/', '_')}")] for d in user_takip_listesi]
        klavye.append([InlineKeyboardButton(dil_paketi["ana_menu_don"], callback_data="silvazgec")])
        await query.edit_message_text(text=dil_paketi["menu_sil_baslik"], parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data.startswith("tsil_"):
        dosya_no_temiz = query.data.replace("tsil_", "").replace("_", "/")
        if dosya_no_temiz in context.user_data.get('secilenler', []): context.user_data['secilenler'].remove(dosya_no_temiz)
        else: context.user_data.setdefault('secilenler', []).append(dosya_no_temiz)
        secilenler = context.user_data['secilenler']
        user_takip_listesi = [k.get('dosya_no') for k in bulut['bekleyenler'] if str(k.get('chat_id')) == chat_id]
        klavye = [[InlineKeyboardButton(f"{'✅' if d in secilenler else '⬜'} {d}", callback_data=f"tsil_{d.replace('/', '_')}")] for d in user_takip_listesi]
        if secilenler: klavye.append([InlineKeyboardButton(dil_paketi["secilenleri_sil"].format(sayi=len(secilenler)), callback_data="toplusil_onay")])
        klavye.append([InlineKeyboardButton(dil_paketi["ana_menu_don"], callback_data="silvazgec")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_onay":
        secilenler = context.user_data.get('secilenler', [])
        dosyalar_raporu = "\n".join([f"❌ <code>{d}</code>" for d in secilenler])
        klavye = [[InlineKeyboardButton(dil_paketi["evet_sil"], callback_data="toplusil_confirm")], [InlineKeyboardButton(dil_paketi["hayir_don"], callback_data="menu_birak")]]
        await query.edit_message_text(text=dil_paketi["sil_onay_soru"].format(liste=dosyalar_raporu), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(klavye))
        return

    if query.data == "toplusil_confirm":
        secilenler = context.user_data.get('secilenler', [])
        bulut['bekleyenler'] = [k for k in bulut['bekleyenler'] if not (str(k.get('chat_id')) == chat_id and k.get('dosya_no') in secilenler)]
        set_bulut_verisi(bulut['bekleyenler'], bulut['son_durum'], bulut['kullanici_dilleri'])
        context.user_data['secilenler'] = []
        await query.edit_message_text(text=dil_paketi["sil_basarili"], parse_mode='HTML')
        return

    if query.data == "silvazgec":
        context.user_data['secilenler'] = []
        await query.edit_message_text(text=dil_paketi["iptal"], parse_mode='HTML')

# ==========================================
# 🚀 ARKA PLAN KONTROL MERKEZİ (POLLING)
# ==========================================
async def veritabanini_kontrol_et(context: ContextTypes.DEFAULT_TYPE):
    """MongoDB'de değişiklik var mı diye saniyeler içinde tarar."""
    bulut = get_bulut_verisi()
    if not bulut: return
    
    eski_durum = bulut.get("son_durum", {})
    eski_m10, eski_m11, eski_dosya_tarih = eski_durum.get("m10_belgeler", []), eski_durum.get("m11_belgeler", []), eski_durum.get("dosya_tarih", "")
    
    # Güncel MongoDB durumunu çek (Çok hafif sorgu)
    d_tarih, yeni_m10, yeni_m11 = pano_istatistiklerini_getir()
    
    # Sadece ilk 5 belgeye bakmak yerine, veritabanındaki TÜM unique kaynak belgeleri çekip kıyaslar (M10/M11 için)
    tum_yeni_m10 = db_anc.kararlar_m10.distinct("Kaynak Belge") if db_anc.kararlar_m10.count_documents({}) > 0 else []
    tum_yeni_m11 = db_anc.kararlar_m11.distinct("Kaynak Belge") if db_anc.kararlar_m11.count_documents({}) > 0 else []
    
    eklenen_m10 = list(set(tum_yeni_m10) - set(eski_m10)) if eski_m10 else []
    eklenen_m11 = list(set(tum_yeni_m11) - set(eski_m11)) if eski_m11 else []
    
    dosya_tarih_degisti = bool(eski_dosya_tarih) and (d_tarih != eski_dosya_tarih) and (d_tarih not in ["Bilinmiyor", "Veri Yok"])
    ilk_calistirma = not bool(eski_durum) or not bool(eski_dosya_tarih)
    
    if ilk_calistirma or len(eklenen_m10) > 15 or len(eklenen_m11) > 15:
        ilk_calistirma = True # Çok fazla yeni dosya varsa toplu eklemedir, bildirim atma sus.

    yeni_durum = {
        "dosya_tarih": d_tarih, 
        "m10_belgeler": tum_yeni_m10, 
        "m11_belgeler": tum_yeni_m11,
        "ozel_bildirimler": eski_durum.get("ozel_bildirimler", [])
    }

    if (eklenen_m10 or eklenen_m11 or dosya_tarih_degisti) or ilk_calistirma:
        set_bulut_verisi(bulut['bekleyenler'], yeni_durum, bulut['kullanici_dilleri'])
        if not ilk_calistirma:
            context.application.create_task(bildirimleri_dagit(context.application, bulut['bekleyenler'], eklenen_m10, eklenen_m11, dosya_tarih_degisti, d_tarih, yeni_durum, bulut['kullanici_dilleri']))

async def bildirimleri_dagit(app_context, bekleyenler, eklenen_m10, eklenen_m11, dosya_tarih_degisti, dosya_tarih, yeni_durum, diller):
    async def guvenli_mesaj_gonder(g_chat_id, g_text, g_klavye=None):
        try: await app_context.bot.send_message(chat_id=g_chat_id, text=g_text, parse_mode='HTML', reply_markup=g_klavye, disable_web_page_preview=True)
        except: pass

    ozel_bildirim_gecmisi = yeni_durum.get("ozel_bildirimler", [])
    toplu_mesajlar, kalan_bekleyenler, admin_onay_listesi = {}, [], []

    for kisi in bekleyenler:
        chat_id, dosya_tam = kisi['chat_id'], kisi['dosya_no']
        k_dili = diller.get(chat_id, "tr")
        dil_pak = DIL_SOZLUGU.get(k_dili, DIL_SOZLUGU["tr"])
        
        if chat_id not in toplu_mesajlar: toplu_mesajlar[chat_id] = {"bulunamayanlar": [], "termen_degisenler": [], "stadiu_guncellendi": False, "eklenen_pdfler": set(), "dil": k_dili}
        if kisi.get('onaylandi', False): kalan_bekleyenler.append(kisi); continue
        
        ana_no, ana_yil = dosya_tam.split('/')
        arama_kriteri, karar_icin_regex = f"^{ana_no}/.*{ana_yil}$", rf"\b{ana_no}\b.*?\b{ana_yil}\b"

        # 40 GÜN KONTROLÜ
        sample_ozel = db_anc.ozel_durumlar.find_one()
        if sample_ozel:
            or_cond = [{k: {"$regex": arama_kriteri, "$options": "i"}} for k in sample_ozel.keys() if k != "_id"]
            ozel_doc = db_anc.ozel_durumlar.find_one({"$or": or_cond})
            if ozel_doc and f"{chat_id}_{dosya_tam}_40gun" not in ozel_bildirim_gecmisi:
                vals = [v for k, v in ozel_doc.items() if k != "_id"]
                ozel_tarih_str, ozel_isim, ozel_ek_bilgi = str(vals[0]) if len(vals)>0 else "-", str(vals[1]) if len(vals)>1 else "-", str(vals[3]) if len(vals)>3 else "-"
                kalan_gun_msg = "Lütfen kurumla iletişime geçin."
                try:
                    gecen_gun = (datetime.datetime.now() - datetime.datetime.strptime(ozel_tarih_str, '%d.%m.%Y')).days
                    if (40 - gecen_gun) > 0: kalan_gun_msg = dil_pak["gun_kaldi"].format(gun=40 - gecen_gun)
                    elif (40 - gecen_gun) == 0: kalan_gun_msg = dil_pak["bugun_doluyor"]
                    else: kalan_gun_msg = dil_pak["sure_doldu"].format(gun=gecen_gun)
                except: pass
                await guvenli_mesaj_gonder(chat_id, dil_pak["uyari_40_gun"].format(tarih=ozel_tarih_str, isim=ozel_isim, not_=ozel_ek_bilgi, kalan_gun_msg=kalan_gun_msg))
                ozel_bildirim_gecmisi.append(f"{chat_id}_{dosya_tam}_40gun")

        # KARAR KONTROLÜ (MongoDB)
        karar_bulundu_mu, k_row = False, None
        for col_name in ["kararlar_m11", "kararlar_m10"]:
            sample_k = db_anc[col_name].find_one()
            if sample_k:
                k_sutun = next((col for col in sample_k.keys() if 'dosya' in str(col).lower() or 'nr' in str(col).lower()), None)
                if k_sutun:
                    match_k = db_anc[col_name].find_one({k_sutun: {"$regex": karar_icin_regex, "$options": "i"}})
                    if match_k: karar_bulundu_mu, k_row = True, match_k; break

        if karar_bulundu_mu:
            kaynak_belge_adi = sutun_degeri_al(k_row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no'])
            g_karar = next((str(k_row[col]).strip() for col in k_row.keys() if 'ordin' in col.lower() or 'karar' in col.lower()), "")
            if not g_karar: g_karar = f"{re.search(r'(?:ordin|nr)[^\d]*(\d+)', kaynak_belge_adi, re.IGNORECASE).group(1)}/P" if re.search(r'(?:ordin|nr)[^\d]*(\d+)', kaynak_belge_adi, re.IGNORECASE) else "-"
            k_tarih = sutun_degeri_al(k_row, ['Tarih', 'Data']) or "-"
            
            await guvenli_mesaj_gonder(chat_id, dil_pak["mujde_onay"].format(dosya=dosya_tam, karar=g_karar, tarih=k_tarih, kaynak=kaynak_belge_adi))
            admin_onay_listesi.append(f"<code>{dosya_tam}</code> - 📄 <i>{kaynak_belge_adi}</i>") 
            kisi['onaylandi'] = True
            
        else:
            sample_dosya = db_anc.stadiu_dosar.find_one()
            if sample_dosya:
                dosya_no_col = next((col for col in sample_dosya.keys() if any(x in str(col).lower() for x in ['dosya', 'nr'])), list(sample_dosya.keys())[0])
                user_row = db_anc.stadiu_dosar.find_one({dosya_no_col: {"$regex": arama_kriteri, "$options": "i"}})
                
                if user_row:
                    kaynak_dosya_metni = sutun_degeri_al(user_row, ['Kaynak Belge', 'Kaynak'], haric_kelimeler=['dosya no'])
                    is_m10, is_m11 = bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE)), not bool(re.search(r'art[- ]?10', kaynak_dosya_metni, re.IGNORECASE))
                    ilgili_ordin_eklendi_mi = (is_m10 and eklenen_m10) or (is_m11 and eklenen_m11)

                    if ilgili_ordin_eklendi_mi or dosya_tarih_degisti:
                        termen_degisti_mi, eski_termen_str, yeni_termen_str = False, "", ""
                        if dosya_tarih_degisti:
                            y_sol = sutun_degeri_al(user_row, ['SOLUTIE', 'Solutie', 'Kurum Notu'])
                            y_ter = sutun_degeri_al(user_row, ['TERMEN', 'Termen'])
                            y_sol_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', y_sol)
                            if y_sol_m and not re.search(r'\d+\s*/?\s*P', y_sol, re.IGNORECASE): y_ter = y_sol_m.group(1)
                            yeni_termen_str = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', y_ter).group(1).replace('/', '.').replace('-', '.') if re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', y_ter) else str(y_ter).strip()

                            eski_match = db_anc.stadiu_dosar_eski.find_one({dosya_no_col: {"$regex": arama_kriteri, "$options": "i"}}) if db_anc.stadiu_dosar_eski.count_documents({}) > 0 else None
                            if eski_match:
                                e_sol = sutun_degeri_al(eski_match, ['SOLUTIE', 'Solutie', 'Kurum Notu'])
                                e_ter = sutun_degeri_al(eski_match, ['TERMEN', 'Termen'])
                                e_sol_m = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_sol)
                                if e_sol_m and not re.search(r'\d+\s*/?\s*P', e_sol, re.IGNORECASE): e_ter = e_sol_m.group(1)
                                eski_termen_str = re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_ter).group(1).replace('/', '.').replace('-', '.') if re.search(r'(\d{2}[\.\/\-]\d{2}[\.\/\-]\d{4})', e_ter) else str(e_ter).strip()

                            if eski_termen_str and yeni_termen_str and eski_termen_str != yeni_termen_str: termen_degisti_mi = True
                        
                        if termen_degisti_mi: toplu_mesajlar[chat_id]["termen_degisenler"].append(dil_pak["termen_degisti"].format(dosya=dosya_tam, eski=eski_termen_str, yeni=yeni_termen_str))
                        if ilgili_ordin_eklendi_mi:
                            for pdf in (eklenen_m10 if is_m10 else eklenen_m11): toplu_mesajlar[chat_id]["eklenen_pdfler"].add(f"🔹 Madde {'10' if is_m10 else '11'}: <i>{pdf}</i>")
                            toplu_mesajlar[chat_id]["bulunamayanlar"].append(f"🔸 <code>{dosya_tam}</code>")
                        elif dosya_tarih_degisti and not termen_degisti_mi:
                            toplu_mesajlar[chat_id]["stadiu_guncellendi"] = True

        kalan_bekleyenler.append(kisi)

    # TOPLU MESAJLARI DAĞIT
    for ch_id, data in toplu_mesajlar.items():
        dil_pak = DIL_SOZLUGU.get(data["dil"], DIL_SOZLUGU["tr"])
        msg_parcalari = []
        if data["bulunamayanlar"]:
            m_key = "guncelleme_1_karar_1_dosya" if len(data["eklenen_pdfler"]) == 1 and len(data["bulunamayanlar"]) == 1 else ("guncelleme_1_karar_cok_dosya" if len(data["eklenen_pdfler"]) == 1 else ("guncelleme_cok_karar_1_dosya" if len(data["bulunamayanlar"]) == 1 else "guncelleme_cok_karar_cok_dosya"))
            msg_parcalari.append(dil_pak[m_key].format(dosyalar="\n".join(data["bulunamayanlar"]), yeni_dosyalar="\n".join(sorted(list(data["eklenen_pdfler"])))))
        if data["termen_degisenler"]: msg_parcalari.extend(data["termen_degisenler"])
        if data["stadiu_guncellendi"] and not data["bulunamayanlar"] and not data["termen_degisenler"]: msg_parcalari.append(dil_pak["stadiu_guncellendi"].format(tarih=dosya_tarih))
        
        if msg_parcalari: await guvenli_mesaj_gonder(ch_id, "\n\n━━━━━━━━━━━━━━━━━━\n\n".join(msg_parcalari))

    if admin_onay_listesi and ADMIN_CHAT_ID: await guvenli_mesaj_gonder(ADMIN_CHAT_ID, "👑 <b>SİSTEM RAPORU - ONAY ALAN DOSYALAR</b>\n\n" + "\n".join([f"✅ {d}" for d in admin_onay_listesi]))
    
    yeni_durum["ozel_bildirimler"] = ozel_bildirim_gecmisi
    set_bulut_verisi(kalan_bekleyenler, yeni_durum, diller)
    # EKLENEN LOG SATIRI:
    print("✅ Hedefli bildirim dağıtımı (Jet Hızında ve Gramer Uyumlu) tamamlandı.", flush=True)

async def rapor_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(ADMIN_CHAT_ID): return 
    bulut = get_bulut_verisi()
    b_len = len(bulut.get("bekleyenler", [])) if bulut else 0
    await update.message.reply_text(f"📊 <b>GÜNLÜK ÖZET SİSTEM RAPORU</b>\n\n👥 Bot veritabanında anlık olarak takip edilen <b>toplam dosya sayısı:</b> <code>{b_len}</code>\n\n<i>Sistem 7/24 ANC listelerini nöbette beklemeye devam ediyor. 🇹🇩</i>", parse_mode='HTML')

# ==========================================
# ⚙️ ANA ÇALIŞTIRMA (POLLING)
# ==========================================
if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    
    async def post_init(application: Application):
        async def baslangic_taramasi(context: ContextTypes.DEFAULT_TYPE): await veritabanini_kontrol_et(context)
        application.job_queue.run_repeating(baslangic_taramasi, interval=3600, first=2) # Her 1 saatte bir DB'yi sessizce kontrol eder
        
    app.post_init = post_init
    app.add_handler(CommandHandler("start", start_command))    
    app.add_handler(CommandHandler("setlanguage", dil_komutu))
    app.add_handler(CommandHandler("rapor", rapor_komutu)) 
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_isleyici))
    app.add_handler(CallbackQueryHandler(buton_tiklama))
    app.run_polling(drop_pending_updates=True)