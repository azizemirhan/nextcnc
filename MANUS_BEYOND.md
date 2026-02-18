# MANUS Seviyesini Geçmek İçin Gerekenler

> Roadmap tamamlandığında MANUS ile **aynı seviyede** olunur.
> Bu doküman, **MANUS'u geçmek** (farklılaşmak ve daha iyi konumlanmak) için
> eklenmesi gereken strateji, özellik ve altyapıyı listeler.

---

## 1. MANUS'un Zayıf / Eksik Kaldığı Alanlar (Fırsatlar)

| Alan | MANUS'ta durum | Geçmek için yapılacak |
|------|----------------|------------------------|
| **Fiyat** | Kurumsal / KOBİ odaklı, yüksek lisans maliyeti | Daha uygun fiyat (tek seferlik veya düşük abonelik), hobi / küçük atölye paketi |
| **Kullanım kolaylığı** | Güçlü ama karmaşık, eğitim gerektirir | Sade arayüz, sihirbazlar, “5 dakikada ilk simülasyon” deneyimi |
| **Türkçe / yerel dil** | Kısıtlı veya İngilizce ağırlıklı | Tam Türkçe arayüz, Türkçe raporlar, yerel destek |
| **Hız / performans** | İyi ama ağır kurulum olabilir | Hafif kurulum, hızlı açılış, büyük dosyalarda 60 FPS hedefi |
| **Açık format / API** | Kapalı kutu | Açık makine/stok formatları (JSON), plugin API, script (Python) ile otomasyon |
| **Bulut / erişim** | Kısmen | Tarayıcıdan demo veya hafif simülasyon, paylaşılabilir rapor linki |
| **Eğitim / öğrenme** | Doküman + destek | Uygulama içi rehber, örnek projeler, ücretsiz video eğitim seti |

Bu alanlarda **bilinçli olarak daha iyi olmak**, “aynı seviye”den “geçmek” anlamına gelir.

---

## 2. Özellik Bazında MANUS'u Geçmek

### 2.1 Teknik / Özellik Üstünlüğü

- **Daha hızlı simülasyon**
  - GPU kullanımı (CUDA/OpenCL) ile stok/voxel güncelleme
  - Çok çekirdekli paralel çarpışma testi
  - Hedef: Aynı programda MANUS’tan %20–30 daha hızlı tamamlama
- **Daha doğru süre hesabı**
  - Makine spesifik ivme/jerk eğrileri (gerçek kontrolcü verisi)
  - Look-ahead ve köşe yavaşlatma modeli
  - Hedef: %95+ doğruluk, mümkünse Vericut / gerçek makine ile kıyaslama
- **Daha fazla makine / kontrolcü**
  - Hazır makine kütüphanesi (3/4/5 eksen): en az 50–100 model
  - Mitsubishi, Mazak, Okuma, Haas, Fagor vb. post/lehçe desteği
  - Kullanıcının kendi makinesini eklemesi için kolay şablon
- **Daha derin CAM entegrasyonu**
  - MANUS’ta olan CAM’lara ek: FreeCAD Path, Kiri:Moto, Carbide Create
  - CAM eklentisi (Fusion 360 / NX / SolidWorks’ten “Simüle et” butonu)
- **Yapay zeka / otomatik öneri (uzun vadeli)**
  - Takım seçimi önerisi
  - “Bu blokta çarpışma riski yüksek” özeti
  - Air-cut’ları otomatik gruplayıp “bu bölgeyi G00 yap” önerisi

### 2.2 Kullanıcı Deneyimi (UX) ile Geçmek

- **İlk 5 dakika**
  - “Örnek G-code aç” ile tek tıkla demo
  - Varsayılan makine ile anında 3D görüntü
  - Hiç ayar yapmadan süre + çarpışma uyarısı
- **Akıllı varsayılanlar**
  - Dosya uzantısına göre lehçe tahmini (.mpf → Siemens, .h → Heidenhain)
  - Makine seçilince uygun takım listesi önerisi
- **Görsel geri bildirim**
  - Çarpışma anında kısa animasyon
  - Riskli bloklar için renk skalası (yeşil → sarı → kırmızı)
  - Raporlarda grafik ve mini görseller
- **Erişilebilirlik**
  - Klavye ile tam kullanım
  - Yüksek kontrast / büyük font seçeneği
  - Türkçe dahil çoklu dil

### 2.3 Fiyat ve Lisans Modeli ile Geçmek

- **Katmanlı paketler**
  - **Ücretsiz:** Sadece görüntüleme + süre (reklam veya watermark ile)
  - **Starter:** Çarpışma + stok (düşük fiyat)
  - **Pro:** Optimizasyon + post + 5 eksen
  - **Enterprise:** Sınırsız makine, API, kurumsal destek
- **Tek seferlik ödeme seçeneği**
  - MANUS ağırlıklı abonelik ise; siz “ömür boyu lisans” sunarak farklılaşma
- **Eğitim / hobi indirimi**
  - Öğrenci ve atölye kursları için özel fiyat

---

## 3. Altyapı ve İş Modeli

### 3.1 Güvenilirlik ve Doğruluk

- **Referans test seti**
  - 100+ gerçek NC programı (Fanuc, Siemens, Heidenhain)
  - Her biri için “beklenen süre”, “çarpışma var/yok”, “son stok” referansı
  - Her sürümde bu sette regresyon testi
- **Üçüncü parti kıyaslama**
  - Vericut / NCSIMUL / gerçek makine ile aynı programda süre ve sonuç karşılaştırması
  - Sonuçları web sitesinde “Doğruluk raporu” olarak yayımlama
- **Sertifikasyon**
  - Belirli CNC kontrolcü / CAM firmalarıyla “test edilmiş / uyumlu” logosu

### 3.2 Topluluk ve Ekosistem

- **Ücretsiz makine / takım paylaşımı**
  - Kullanıcıların makine tanımı (JSON + STL) yükleyip indirebileceği kütüphane
  - “Bu makine için test edildi” etiketi
- **Plugin / script mağazası**
  - Python API ile özel rapor, özel optimizasyon kuralı
  - Hazır plugin’ler: Excel’e aktar, özel post formatı
- **Forum / destek**
  - Türkçe forum, sık sorulan sorular, video çözümler
  - Hata raporlama ve özellik isteği için public roadmap

### 3.3 Dağıtım ve Görünürlük

- **Hafif “online demo”**
  - Tarayıcıda sınırlı demo (küçük G-code, sadece görüntüleme + süre)
  - Kayıt veya e-posta ile tam sürüm denemesi
- **YouTube / eğitim**
  - “MANUS alternatifi”, “Türkçe CNC simülasyon” içerikleri
  - Kısa “1 dakikada simülasyon” videoları
- **CAM / makine satıcıları ile iş birliği**
  - “Bu makineyi aldığınızda 1 yıl simülasyon dahil”
  - Entegrasyon: CAM’dan “NextCNC’de aç” butonu

---

## 4. Özet: “Geçmek” İçin Checklist

| Başlık | Yapılacak |
|--------|-----------|
| **Fiyat** | Daha uygun katman + tek seferlik lisans + eğitim indirimi |
| **Kolay kullanım** | 5 dk’da ilk simülasyon, sihirbazlar, akıllı varsayılanlar |
| **Dil** | Tam Türkçe arayüz ve raporlar |
| **Performans** | GPU / çok çekirdek, 60 FPS, hızlı açılış |
| **Doğruluk** | %95+ süre, referans test seti, Vericut/makine kıyaslaması |
| **Makine kütüphanesi** | 50–100 hazır makine + kullanıcı paylaşımı |
| **Açıklık** | Açık format, plugin API, script ile otomasyon |
| **Eğitim** | İç rehber, örnekler, ücretsiz videolar |
| **Güven** | Regresyon testi, doğruluk raporu, sertifikasyon |
| **Pazarlama** | Online demo, YouTube, CAM/makine iş birlikleri |

---

## 5. Sonuç

- **Aynı seviyeye gelmek:** Tüm roadmap fazlarının tamamlanması (MANUS_ROADMAP.md).
- **MANUS’u geçmek:** Yukarıdaki fırsat alanlarında **bilinçli olarak daha iyi** olmak:
  - Daha uygun fiyat ve lisans,
  - Daha kolay ve hızlı kullanım,
  - Tam Türkçe ve yerel destek,
  - Daha hızlı / doğru simülasyon,
  - Açık format ve topluluk,
  - Güvenilirlik (test seti, kıyaslama, sertifikasyon).

Önce roadmap ile **aynı seviye**, sonra bu maddelerle **geçmek** hedeflenebilir.
