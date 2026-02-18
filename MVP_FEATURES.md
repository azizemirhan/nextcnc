# NextCNC - Faz 1 (MVP) Özellikleri

## 🎯 MVP Kapsamı

Bu sürüm, 3-eksenli CNC frezeleme için temel simülasyon ve doğrulama özelliklerini sağlar.

---

## ✅ Tamamlanan Özellikler

### 1. G-Code Parsing

#### Desteklenen G Kodları
| Kod | Açıklama |
|-----|----------|
| G00 | Hızlı pozisyonlama (Rapid) |
| G01 | Doğrusal interpolasyon |
| G02 | Saat yönünde dairesel (CW) |
| G03 | Saat yönünün tersine (CCW) |
| G17 | XY düzlemi |
| G18 | XZ düzlemi |
| G19 | YZ düzlemi |
| G20 | İnç birimi |
| G21 | Milimetre birimi |
| G54-G59 | İş koordinat sistemleri (WCS) |
| G90 | Mutlak pozisyonlama |
| G91 | Artımsal pozisyonlama |

#### Desteklenen M Kodları
| Kod | Açıklama |
|-----|----------|
| M02/M30 | Program sonu |
| M03/M04 | Spindle çalıştır |
| M05 | Spindle durdur |
| M06 | Takım değiştir |

#### Parser Özellikleri
- ✅ Yorum satırları `(yorum)` ve `; yorum`
- ✅ Blok atlama `/` karakteri
- ✅ Satır numaralandırma `N10`
- ✅ Program numarası `O1000`
- ✅ Parametre desteği `#1=100`

---

### 2. 3-Eksen Kinematik

#### Work Coordinate System (WCS)
```
G54 - 1. iş koordinat sistemi (varsayılan)
G55 - 2. iş koordinat sistemi
G56 - 3. iş koordinat sistemi
G57 - 4. iş koordinat sistemi
G58 - 5. iş koordinat sistemi
G59 - 6. iş koordinat sistemi
```

#### Eksen Limit Kontrolü
- X, Y, Z eksenleri için min/max limit tanımlama
- Limit aşımı durumunda uyarı
- JSON tabanlı makine konfigürasyonu

#### Örnek Makine Konfigürasyonu
```json
{
  "name": "DMG Mori DMU 60",
  "x_limits": {"min": -300, "max": 300},
  "y_limits": {"min": -200, "max": 200},
  "z_limits": {"min": -150, "max": 100},
  "max_rapid_feed": 15000,
  "max_cutting_feed": 8000
}
```

---

### 3. Malzeme Kaldırma Simülasyonu (Tri-Dexel)

#### Özellikler
- ✅ **Dexel Board**: 3 yönlü Z-buffer yapısı
- ✅ **Takım Tipleri**:
  - Düz uçlu (Flat Endmill)
  - Bilya uçlu (Ball Endmill)
  - Bullnose (Köşe yarıçaplı)
- ✅ **Hacim Hesaplama**: Kaldırılan malzeme hacmi (mm³)
- ✅ **Air-Cut Tespiti**: Bosta kesim algılama
- ✅ **Mesh Üretimi**: OpenGL render için üçgen mesh

#### Simülasyon İstatistikleri
- Toplam stok hacmi
- Kaldırılan hacim
- Kalan hacim
- Kaldırma yüzdesi
- Air-cut segment sayısı

---

### 4. 3D Görselleştirme

#### Gösterilebilir Objeler
1. **Takım Yolu (Toolpath)**
   - Rapid hareketler
   - Kesme hareketleri (cyan/mavi)
   - Line ve Arc desteği

2. **Stok (Stock)**
   - Wireframe gösterim
   - Gerçek zamanlı güncelleme
   - Malzeme kaldırma animasyonu

3. **Referans Eksenleri**
   - X ekseni (kırmızı)
   - Y ekseni (yeşil)
   - Z ekseni (mavi)

#### Kamera Kontrolleri
| İşlem | Fare/Tuş |
|-------|----------|
| Döndürme (Orbit) | Sol tık + sürükle |
| Kaydırma (Pan) | Sağ tık + sürükle |
| Yakınlaştırma (Zoom) | Tekerlek |
| Görünüm sıfırlama | Ctrl + R |

---

### 5. Çarpışma Algılama

#### Tespit Edilen Çarpışma Tipleri
| Tip | Açıklama | Risk Seviyesi |
|-----|----------|---------------|
| TOOL_STOCK | Takım stoka değiyor | ✅ Normal (kesme) |
| TOOL_HOLDER_STOCK | Takım tutucu stoka değiyor | ❌ KRİTİK |
| TOOL_FIXTURE | Takım fikstüre değiyor | ❌ KRİTİK |

#### Algoritma
- **Broad-Phase**: AABB Tree (hızlı filtreleme)
- **Narrow-Phase**: AABB-AABB kesişim testi
- **CCD**: Sürekli çarpışma kontrolü (rapid hareketler için)

---

### 6. Kullanıcı Arayüzü

#### Ana Pencere
- **Menü Çubuğu**: Dosya, Görünüm, Ayarlar
- **3D Viewport**: OpenGL render alanı
- **Durum Çubuğu**: Bilgi ve hata mesajları

#### Dock Panel (Sağ Taraf)
- Stok simülasyonu istatistikleri
- "Simülasyonu Başlat" butonu
- "Stock'u Sıfırla" butonu

---

## 📊 Örnek Kullanım Senaryoları

### Senaryo 1: Basit Cep İşleme
```gcode
O1000 (CEP ORNEGI)
G21 G54 G90
T1 M6 (D10 FREZE)
S3000 M3
G0 X0 Y0 Z50
G1 Z-5 F500 (Cep tabanına in)
X50 F1000 (Cep tabanı)
Y50
X0
Y0
G0 Z50 (Güvenli yükseklik)
M30
```

**Yapılabilecekler:**
1. G-Code'u yükle ve parse et
2. 3D takım yolunu görüntüle
3. Stok simülasyonu çalıştır
4. Kaldırılan hacmi gör
5. Eksen limit kontrolü yap

### Senaryo 2: Çarpışma Tespiti
```gcode
G0 X0 Y0 Z100 (Güvenli)
G1 Z-50 F500 (Derin kesim - holder çarpar!)
```

**Yapılabilecekler:**
- Takım tutucunun stoka çarptığını tespit et
- Hangi satırda (block numarası) çarpışma olduğunu gör
- Çarpışma derinliğini hesapla

### Senaryo 3: WCS Değişimi
```gcode
G54 (1. parça)
G0 X50 Y50
G55 (2. parça - farklı offset)
G0 X50 Y50
```

**Yapılabilecekler:**
- Her iki WCS için farklı makine koordinatlarını gör
- WCS offsetlerini JSON'dan yükle
- Parça sıfır noktasını görselleştir

---

## ⚠️ MVP Sınırlamaları (Bilinmeyenler)

### Henüz Desteklenmeyenler
- ❌ 5-eksen (A, B, C eksenleri)
- ❌ Dairesel enterpolasyon düzlemleri (tam G18/G19 testi)
- ❌ Değişkenler ve matematiksel ifadeler (#1+#2)
- ❌ Alt programlar (M98/M99)
- ❌ Döngüler (FOR, WHILE)
- ❌ Sabit döngüler (G81-G89 delme döngüleri)
- ❌ Takım telafisi (G41/G42)
- ❌ Takım uzunluk telafisi (G43/G44)
- ❌ STL yükleme/ihraç
- ❌ Gerçek kesme kuvvetleri/ısı

### Bilinen Sınırlamalar
- Stok simülasyonu: Kareli pikselleşme (dexel çözünürlüğüne bağlı)
- Çarpışma: AABB yaklaşımı (kesin değil ama hızlı)
- Performans: >100k blokta yavaşlayabilir

---

## 🎯 Kullanıcı Profili

Bu MVP şu kullanıcılar için uygundur:
- ✅ CNC operatörleri (G-Code doğrulama)
- ✅ CAM programcıları (takım yolu kontrolü)
- ✅ Eğitim amaçlı (CNC simülasyon öğrenimi)
- ✅ Basit 3-eksen freze programları

Bu MVP şu kullanıcılar için henüz uygun değildir:
- ❌ 5-eksen işleme merkezleri
- ❌ Karmaşık torna (lathe) operasyonları
- ❌ Endüstriyel üretim (tam doğrulama gerekir)
