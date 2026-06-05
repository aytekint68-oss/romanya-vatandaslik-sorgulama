# Romanya Vatandaşlık Karar Sorgulama - Madde 10/11

Bu proje, Romanya Adalet Bakanlığı (ANC) tarafından yayımlanan vatandaşlık onay kararlarını (Ordin - Articolul 10) onlarca PDF dosyası arasında tek tek aramak yerine, saniyeler içinde kolayca sorgulayabilmeniz için geliştirilmiş açık kaynaklı bir web uygulamasıdır.

## 🌟 Özellikler

* **Hızlı Sorgulama:** Dosya numaranızı (Örn: 7026/2023) yazarak kararın çıkıp çıkmadığını anında öğrenebilirsiniz.
* **Tam Eşleşme Mantığı:** Sadece birebir eşleşen dosya numaralarını getirerek hatalı sonuçların önüne geçer.
* **Son Karar Panosu:** Sisteme eklenen en güncel kararnamenin tarihini ve adını ana sayfada gösterir.
* **Resmi Kaynağa Yönlendirme:** Bulunan kararı teyit edebilmeniz için tek tıkla doğrudan orijinal devlet sitesine yönlendirir.
* **Mobil Uyumlu:** Streamlit altyapısı sayesinde telefondan veya bilgisayardan kusursuz görünür.

## 🛠️ Nasıl Çalışıyor?

Sistem, Python kullanılarak geliştirilmiş iki aşamalı bir mimariye sahiptir:

1. **Veri Çıkarma (Backend):** Resmi siteden indirilen PDF dosyaları `PyMuPDF (fitz)` ve `Regex` kullanılarak taranır. İçlerindeki dosya numaraları, tarih ve karar (Ordin) bilgileri ayıklanarak Pandas aracılığıyla tek bir merkezi Excel veritabanına (`Romanya_Vatandaslik_Tum_Veriler.xlsx`) dönüştürülür.
2. **Web Arayüzü (Frontend):** Oluşturulan bu veritabanı, `Streamlit` kütüphanesi kullanılarak kullanıcı dostu ve interaktif bir web sitesi üzerinden genel erişime açılır.

## ⚠️ Yasal Uyarı

Bu proje tamamen açık kaynaklı ve sivil bir girişim olup, verileri kolayca taramak amacıyla oluşturulmuş gayriresmi bir arama motorudur. Sonuçlar hiçbir hukuki bağlayıcılık taşımaz. Resmi ve kesin kararlar her zaman sadece [cetatenie.just.ro](https://cetatenie.just.ro/ordine-articolul-10/) adresinden teyit edilmelidir.
