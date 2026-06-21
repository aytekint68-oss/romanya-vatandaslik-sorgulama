# Romanya Vatandaşlık Dosya (Stadiu Dosar) ve Karar (Ordin) Sorgulama Sistemi

Bu proje, Romanya Adalet Bakanlığı - Ulusal Vatandaşlık Kurumu (ANC) tarafından yayımlanan **Madde 10 ve Madde 11** kapsamındaki vatandaşlık başvuru dosyalarının durumunu ve Karar (Ordin) sonuçlarını **tek bir ekranda birleştirerek** sunan akıllı bir sorgulama motorudur. 

Yüzlerce sayfalık karmaşık PDF listeleri arasında kaybolmayı önler ve kullanıcılara saniyeler içinde net bilgiler sunar.

---

## ✨ Öne Çıkan Özellikler

* **Entegre Çift Yönlü Sorgulama:** Kullanıcı dosya numarasını girdiğinde, sistem önce "Dosya Durumu" (Stadiu Dosar) listesini tarar. Eğer dosyada bir karar/onay kodu (Örn: `2040/P/2023`) tespit ederse, otomatik olarak "Karar (Ordine)" listelerine bağlanır ve dosyanın resmi olarak yayımlanıp yayımlanmadığını kontrol eder.
* **Akıllı Hata Ayıklama (Gelişmiş İstisna Yönetimi):** Eğer dosya "P (Onay)" numarası almış ancak henüz resmi karar listesinde yayımlanmamışsa, sistem kullanıcıya *"Dosyanız olumlu çözümlenmiş ancak henüz resmi listeye eklenmemiş"* şeklinde özel bir uyarı verir.
* **Esnek ve Tam Eşleşme (Exact Match):** `1234/2017` yazıldığında aradaki harfleri (Örn: `1234/RD/2017`) otomatik tolere eder. Ayrıca `1234` arandığında `12340` gibi sahte eşleşmeleri filtreleyerek tam on ikiden vurur.
* **Dinamik Güncelleme Takibi:** Sistem, veritabanını oluşturan PDF dosyalarının isimlerindeki tarihleri (Örn: `Update-10.06.2026`) okuyarak ziyaretçilere verilerin ne kadar güncel olduğunu şeffaf bir şekilde sunar.

---

## 📂 Sistem Mimarisi ve Veritabanı Yapısı

Sistemin arka planda kusursuz çalışması için aşağıdaki 3 ana Excel dosyası ile beslenmesi gerekir:

1. `dosyadurumu.zip` -> Tüm başvuruların genel durumunu (TERMEN ve SOLUTIE) barındırır.
2. `Romanya_Vatandaslik_Tum_Veriler_Madde10.csv` -> Madde 10 kapsamındaki onaylanmış karar (Ordine) listesi.
3. `Romanya_Vatandaslik_Tum_Veriler_Madde11.csv` -> Madde 11 kapsamındaki onaylanmış karar (Ordine) listesi.

*(Bu Excel dosyaları, sisteme entegre edilen özel bir PyMuPDF botu ile resmi PDF'lerden çekilerek oluşturulmaktadır.)*

---

## 🛠️ Kullanılan Teknolojiler

* **Python 3.12+**
* **Streamlit:** Web arayüzü ve sunucu altyapısı.
* **Pandas:** Çoklu Excel veritabanlarının birleştirilmesi ve hızlı manipülasyonu.
* **Regex (Re):** Akıllı arama ve metin ayıklama işlemleri.

