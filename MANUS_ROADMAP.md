# NextCNC → MANUSsim Seviyesi Özellik Yol Haritası

> Bu doküman; NextCNC'nin mevcut durumundan başlayarak MANUSsim ile
> aynı çözümleri sunabilmesi için eklenmesi gereken tüm özellikleri,
> öncelik sırasına ve geliştirme fazlarına göre listeler.

---

## Mevcut Durum (NextCNC v1 – Başlangıç)

| Özellik | Durum |
|--------|-------|
| G-code yükleme (Fanuc, temel) | Var |
| 3D toolpath görüntüleme | Var |
| G00/G01/G02/G03 parser | Var |
| PyQt6/PySide6 GUI | Var |
| Temel orbit kamera | Var |
| Çarpışma tespiti | **Yok** |
| Makine modeli / dijital ikiz | **Yok** |
| Stok / malzeme kaldırma | **Yok** |
| Gerçek kesim süresi hesabı | **Yok** |
| Air-cut tespiti ve optimizasyon | **Yok** |
| CAM entegrasyonu | **Yok** |
| Post processor | **Yok** |
| Çoklu lehçe (Siemens, Heidenhain) | **Yok** |
| Takım kütüphanesi | **Yok** |

---

## Geliştirme Fazları

---

## FAZ 1 — Güçlü Temel (0–3 Ay)
> Hedef: Yazılımı "ciddi araç" olarak konumlandır; ilk satışa hazır MVP.

### 1.1 Parser Güçlendirme

- [ ] **Çoklu lehçe desteği**
  - Siemens Sinumerik 840D sözdizimi
  - Heidenhain iTNC/TNC640 sözdizimi
  - Her lehçe için ayrı `dialect_fanuc.py`, `dialect_siemens.py`, `dialect_heidenhain.py` modülleri
- [ ] **Parametrik programlama**
  - Fanuc Macro B: `#1`, `#2`, aritmetik ifadeler `[#1 + SIN[#2]]`
  - Siemens R parametreleri: `R1=50`, `R2=R1+10`
  - Koşullu dallanma: `IF / THEN / ELSE / GOTO`
  - Döngüler: `WHILE / DO / END`
- [ ] **Alt program (Sub-program) desteği**
  - `M98 P / M99` (Fanuc)
  - `L` çağrısı (Siemens)
  - İç içe alt program (en az 5 seviye derinlik)
- [ ] **Sabit döngüler (Canned Cycles)**
  - `G81` Delme, `G83` Derin delik, `G84` Kılavuz
  - `G73`, `G76`, `G85`, `G86`, `G89`
- [ ] **Takım çapı / uzunluk tazminatı**
  - `G41`/`G42` (takım çapı tazminatı)
  - `G43`/`G44` (takım uzunluk tazminatı)
- [ ] **İş koordinat sistemleri (WCS)**
  - `G54`–`G59` desteği
  - `G52` lokal ofset

### 1.2 Arayüz İyileştirmeleri

- [ ] **Gelişmiş 3D görüntüleme**
  - Grid (taban ızgarası) ve eksen çizgileri
  - Rapid (G00) hareketleri farklı renk (kesik çizgi)
  - Kesim hareketleri (G01/G02/G03) farklı renk
  - Takım konumu göstergesi (gerçek zamanlı slider)
  - Koordinat göstergesi (X/Y/Z değerleri)
  - Ölçeklendirme (mm/inch)
- [ ] **G-code editörü**
  - Satır numaralı, sözdizimi renklendirmeli metin editörü
  - Editörde tıklayınca 3D'de ilgili harekete git
  - 3D'de hareket seçince editörde ilgili satır vurgula
- [ ] **Bilgi paneli**
  - Toplam blok sayısı
  - Tahmini mesafe (mm), takım yolu uzunluğu
  - Min/Max koordinatlar (X/Y/Z bounding box)
  - Hızlı/kesim hareket oranı (%)
- [ ] **Simülasyon oynatma kontrolü**
  - Oynat / Durdur / Adım adım ileri-geri
  - Hız slider'ı (0.1x – 100x)
  - Belirli bloğa atla (N satırı)

### 1.3 Takım Kütüphanesi (Temel)

- [ ] **Takım tanımlama**
  - Parmak freze, matkap, kılavuz, boşaltma freze
  - Çap, uzunluk, köşe yarıçapı, flüt sayısı
  - Takım numarası – ofset eşleşmesi (T01, T02…)
- [ ] **SQLite veritabanı** (`tools.db`)
- [ ] **Takım kütüphanesi editörü** (ekle / düzenle / sil)
- [ ] **3D görünümde takım geometrisi** (silindir / koni gösterimi)

---

## FAZ 2 — Makine Modeli ve Çarpışma (3–7 Ay)
> Hedef: MANUSsim'in en kritik özelliği olan çarpışma tespitini ekle.

### 2.1 Makine Modeli (Dijital İkiz)

- [ ] **JSON tabanlı makine tanım dosyası**
  ```json
  {
    "name": "VMC 850",
    "type": "3-axis",
    "axes": {
      "X": { "min": -425, "max": 425, "rapid": 36000 },
      "Y": { "min": -510, "max": 510, "rapid": 30000 },
      "Z": { "min": -510, "max": 0,   "rapid": 30000 }
    },
    "components": [
      { "name": "table",    "mesh": "table.stl",    "parent": "Y" },
      { "name": "column",   "mesh": "column.stl",   "parent": "fixed" },
      { "name": "spindle",  "mesh": "spindle.stl",  "parent": "Z" }
    ]
  }
  ```
- [ ] **STL / OBJ formatında makine parçası yükleme**
- [ ] **Kinematik zincir** (hiyerarşik parent-child eksen bağlantısı)
- [ ] **3D görünümde makine animasyonu** (simülasyon sırasında eksenler hareket eder)
- [ ] **Başlangıç makine kütüphanesi**
  - Generic 3 eksen VMC
  - Generic 5 eksen (head-table)
  - Torna (2 eksen)

### 2.2 Eksen Limit Kontrolü

- [ ] Programdaki her hareket için eksen sınırlarını kontrol et
- [ ] Aşım noktalarını 3D'de kırmızı ile işaretle
- [ ] Raporda "blok X: Z ekseni limiti aşıldı" uyarısı

### 2.3 Çarpışma Tespiti

- [ ] **Geniş faz (Broad-phase): AABB**
  - Tüm makine bileşenleri için Axis-Aligned Bounding Box
  - Hızlı eliasyon: çakışmayan kutular için derin test yok
- [ ] **Dar faz (Narrow-phase): GJK/EPA**
  - AABB ihlali varsa tam geometri testi
  - Takım ↔ Bağlama aparatı (fixture)
  - Takım ↔ Ham parça (stok)
  - Tutucu (holder) ↔ Makine parçaları
  - Mil ↔ Mengene
- [ ] **Sürekli çarpışma tespiti (CCD)**
  - Rapid (G00) hareketi sırasında ara pozisyonlar kontrol
- [ ] **Çarpışma uyarısı**
  - 3D'de çarpışma noktası kırmızı ışık ile işaretle
  - Editörde ilgili satırı vurgula
  - Raporda blok numarası, çarpışan parça çifti, penetrasyon derinliği
- [ ] **Near-miss uyarısı** (yaklaşım eşiği, örn. 0.5 mm)

### 2.4 Bağlama Aparatı (Fixture/Mengene) Yönetimi

- [ ] STL olarak mengene / aparat yükleme
- [ ] 3D'de konumlandırma (X/Y/Z ofset, rotasyon)
- [ ] Çarpışma tespitine dahil etme

---

## FAZ 3 — Stok Simülasyonu ve Süre Hesabı (7–12 Ay)
> Hedef: "Parçanın nasıl çıkacağını gör" ve "ne kadar sürer" soruları.

### 3.1 Ham Parça (Stok) Simülasyonu

- [ ] **Basit kutu stok tanımı** (X/Y/Z boyutları)
- [ ] **STL / STEP stok yükleme**
- [ ] **Malzeme kaldırma simülasyonu**
  - Voksel tabanlı (hız/basitlik için) veya Tri-Dexel (hassasiyet için)
  - Her G01/G02/G03 hareketinde takım süpürme hacmi stoktan çıkar
  - Gerçek zamanlı güncellenmiş stok mesh 3D'de görüntülenir
- [ ] **Parça hasarı (Gouge) tespiti**
  - Takım referans modeli (CAD / STL) ile karşılaştırma
  - Fazla kesilen bölgeler kırmızı ile göster
  - Yetersiz kesilen bölgeler sarı ile göster
- [ ] **Son parça dışa aktarma** (STL olarak kaydet)

### 3.2 Gerçek Kesim Süresi Hesabı

- [ ] **Temel süre hesabı**
  - Her segment için: `süre = mesafe / ilerleme_hızı`
  - G00 için: `süre = mesafe / rapid_hızı`
- [ ] **Gelişmiş süre hesabı (~%90–95 doğruluk)**
  - **İvme/yavaşlama profili:** Eksen hızlanma (mm/s²) parametresi
  - **Jerk kontrolü:** S-eğrisi profili (Siemens / Fanuc jerk değerleri)
  - **Ön okuma (Look-ahead):** Köşe hızı hesabı (küçük açılar = yavaşlama)
  - **Makine konfigürasyonundan** ivme/jerk değerleri al
- [ ] **Süre raporu**
  - Toplam süre (saat:dakika:saniye)
  - Kesim süresi / rapid (boş) süresi ayrımı
  - İşlem bazlı süre (her takım değişimi arası)
- [ ] **Süre karşılaştırma** (orijinal vs. optimize edilmiş program)

### 3.3 MRR (Material Removal Rate) Analizi

- [ ] Her blok için anlık MRR hesabı (mm³/dak)
- [ ] MRR grafiği (blok no – MRR çizgi grafiği)
- [ ] Aşırı yüklü kesim blokları uyarısı (renk ile işaret)

---

## FAZ 4 — Air-Cut ve Feed Optimizasyonu (10–15 Ay)
> Hedef: MANUSsim Optimize seviyesi – programı otomatik iyileştir.

### 4.1 Air-Cut Tespiti

- [ ] **Geometri tabanlı tespit**
  - Her hareket segmenti için takım ↔ stok kesişim testi
  - Takım hiç malzemeye temas etmiyorsa → Air-cut
- [ ] **Air-cut sınıflandırması**
  - `RAPID_AIR`: G00 ile havada
  - `FEED_AIR`: G01/G02/G03 ile havada (gereksiz ilerleme hızında)
  - `APPROACH`: Malzemeye yaklaşma (kısmi temas)
- [ ] **Görselleştirme:** Air-cut segmentleri farklı renk (turuncu)
- [ ] **Air-cut raporu:** Yüzde oranı, toplam süre kaybı

### 4.2 Otomatik Feed Optimizasyonu

- [ ] **Air-cut bloklarında G01 → G00'a otomatik dönüştür**
  - Güvenlik mesafesi kontrolü ile
- [ ] **Gereksiz ev pozisyonu (G28/G30) dönüşlerini minimize et**
- [ ] **MRR tabanlı feed rate optimizasyonu**
  - Düşük MRR bölgelerinde feed artır (zaman kazanımı)
  - Yüksek MRR bölgelerinde feed azalt (takım/parça koruması)
- [ ] **Optimize edilmiş NC programı dışa aktarma**
  - Yorum satırları ile değişiklikler işaretlenir
  - Orijinal ↔ optimize karşılaştırma tablosu
- [ ] **Tasarruf raporu**
  - Kazanılan süre (dakika + yüzde)
  - Air-cut azaltma (%)
  - Feed optimizasyonu katkısı

### 4.3 Kesim Kuvveti ve Torku (İleri Seviye)

- [ ] **Empirik kesim kuvveti modeli**
  - MRR, takım geometrisi, malzeme → kuvvet tahmini
- [ ] **Tork ve güç hesabı**
  - Mil torku sınırı aşımı uyarısı
- [ ] **Kesim kuvveti – blok grafiği**

---

## FAZ 5 — CAM Entegrasyonu ve Post Processor (15–20 Ay)
> Hedef: CAM çıktısını doğrudan simüle et ve post processor üret.

### 5.1 CAM Entegrasyonu

- [ ] **Desteklenecek CAM formatları**
  - Fusion 360 (`.nc`)
  - Mastercam (`.nc`, `.nci`)
  - SolidCAM (`.nc`)
  - HyperMill (`.nc`)
  - FreeCAD Path (`.gcode`)
- [ ] **Makine bağlantısı (DNC)**
  - RS-232 / Ethernet üzerinden NC programı makineye gönderme
  - Makine durumu okuma (opsiyonel, protokol bağımlı)

### 5.2 Post Processor Desteği (Temel)

- [ ] **Post processor şablon sistemi**
  - JSON/YAML tabanlı şablon tanımlama
  - Fanuc, Siemens, Heidenhain çıktı formatı
- [ ] **Post processor düzenleyici (GUI)**
  - Başlık / bitiş bloğu
  - Takım değişimi formatı
  - Koordinat formatı (dönüşüm)
  - M/G kodu eşleşmeleri

### 5.3 Rapor Üretimi

- [ ] **PDF / HTML rapor**
  - Takım yolu özeti
  - Çarpışma listesi
  - Air-cut analizi
  - Süre tahmini
  - Ekran görüntüsü
- [ ] **Excel / CSV dışa aktarma** (blok bazlı detay)

---

## FAZ 6 — 5 Eksen ve RTCP (18–24 Ay)
> Hedef: Havacılık ve kalıpçılık sektörüne açıl.

### 6.1 5 Eksen Kinematik

- [ ] **Makine tipleri**
  - Head-Head (çift döner mil)
  - Head-Table (döner mil + döner tabla)
  - Table-Table (çift döner tabla)
- [ ] **Denavit-Hartenberg (DH) parametreleri** ile kinematik zincir
- [ ] **İleri kinematik:** Eksen değerleri → TCP konumu ve yönü
- [ ] **Ters kinematik:** TCP → eksen değerleri
- [ ] **Tekillik (Singularity) tespiti ve uyarısı**

### 6.2 RTCP (Rotating Tool Center Point)

- [ ] **RTCP/TCPM hesabı**
  - `G43.4` (Fanuc RTCP)
  - `CYCLE800` / `TRAORI` (Siemens)
  - `M128` (Heidenhain)
- [ ] **TCP hız hesabı** (gerçek kesim hızı, eksen kombinasyonunda)
- [ ] **RTCP modu simülasyonu**

### 6.3 5 Eksen Çarpışma

- [ ] Döner eksenlerle oluşan harekette çarpışma tespiti
- [ ] Makine açı limitleri (A/B/C eksen aralıkları)

---

## FAZ 7 — Bulut ve Lisans (Paralel Geliştirme)
> Hedef: Ticari ürün altyapısı.

### 7.1 Lisans Sistemi

- [ ] **Lisans doğrulama** (çevrimiçi veya çevrimdışı)
  - Makine ID tabanlı lisans
  - Zaman sınırlı deneme (30 gün)
- [ ] **Lisans seviyeleri**
  - **Starter:** 3 eksen, görüntüleme, temel çarpışma
  - **Professional:** Stok simülasyonu, süre hesabı, air-cut
  - **Enterprise:** 5 eksen, RTCP, post processor, CAM entegrasyonu

### 7.2 Kurulum ve Dağıtım

- [ ] **PyInstaller** ile tek `.exe` kurulum paketi (Windows)
- [ ] **Otomatik güncelleme** mekanizması
- [ ] **Windows installer** (NSIS veya Inno Setup)
- [ ] macOS `.app` ve Linux AppImage

### 7.3 Bulut Özellikleri (Opsiyonel)

- [ ] Bulut tabanlı lisans yönetimi
- [ ] Rapor paylaşma (link ile)
- [ ] Makine kütüphanesi güncelleme (sunucudan)

---

## Öncelik Özeti

| Öncelik | Özellik | Faz | Neden Önemli |
|---------|---------|-----|--------------|
| 🔴 Kritik | Çarpışma tespiti | 2 | MANUSsim'in temel satış argümanı |
| 🔴 Kritik | Gerçek süre hesabı | 3 | Teklif ve planlama için şart |
| 🔴 Kritik | Stok simülasyonu | 3 | "Parça nasıl çıkacak" sorusu |
| 🟠 Yüksek | Air-cut tespiti | 4 | %20+ zaman tasarrufu = somut değer |
| 🟠 Yüksek | Çoklu lehçe (Siemens) | 1 | Pazar genişliği |
| 🟠 Yüksek | Makine modeli | 2 | Çarpışma için temel |
| 🟡 Orta | Süre optimizasyonu | 4 | MANUSsim Optimize seviyesi |
| 🟡 Orta | Post processor | 5 | Ek gelir kapısı |
| 🟢 Düşük | 5 eksen / RTCP | 6 | İleri seviye, dar hedef kitle |
| 🟢 Düşük | CAM entegrasyonu | 5 | Ekosisteme bağlanma |

---

## Teknoloji Kararları

| Bileşen | Mevcut | Öneri |
|--------|--------|-------|
| Arayüz | PyQt6/PySide6 | PyQt6/PySide6 (devam) |
| 3D | PyOpenGL | PyOpenGL + Modern GL (VAO/VBO) |
| Çarpışma | Yok | python-fcl veya saf NumPy AABB+GJK |
| Stok simülasyonu | Yok | Voksel (NumPy 3D array) veya Tri-Dexel |
| Veritabanı | Yok | SQLite (takım, makine kütüphanesi) |
| Süre hesabı | Yok | NumPy tabanlı kinematik model |
| Dağıtım | Python script | PyInstaller → `.exe` |
| Lisans | Yok | Cryptography + makine ID |

---

## Tahmini Geliştirme Süresi

| Faz | Kapsam | Tahmini Süre |
|-----|--------|--------------|
| Faz 1 | Parser, GUI, takım kütüphanesi | 3 ay |
| Faz 2 | Makine modeli, çarpışma | 4 ay |
| Faz 3 | Stok sim., süre hesabı | 5 ay |
| Faz 4 | Air-cut, optimizasyon | 3 ay |
| Faz 5 | CAM entegrasyonu, post processor | 5 ay |
| Faz 6 | 5 eksen, RTCP | 6 ay |
| Faz 7 | Lisans, dağıtım | 2 ay (paralel) |
| **Toplam** | **MANUSsim seviyesi** | **~18–24 ay** |

---

## Kısa Vadeli Hedef (3 Ay – Satışa Hazır MVP)

Sadece Faz 1 tamamlanırsa bile şunlar sunulabilir:

1. Çoklu lehçe G-code okuma
2. Gelişmiş 3D görüntüleme (renk, grid, slider)
3. G-code editörü (satır-3D bağlantısı)
4. Takım kütüphanesi
5. Temel blok bilgileri ve rapor
6. Tek `.exe` kurulum paketi

Bu seviye bile **hobi CNC, küçük atölye ve eğitim** pazarına satılabilir.

---

*Son güncelleme: Şubat 2026 — NextCNC v1 → MANUSsim Seviyesi Yol Haritası*
