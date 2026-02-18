# CNC Simülasyon Yazılımları: Derinlemesine Teknik Analiz

## Manus NC, Vericut & NCSIMUL Çalışma Prensipleri

---

## 1. G-Code Parsing: ISO 6983 Uyumlu Karmaşık Ayrıştırma

### 1.1 Problem Tanımı

ISO 6983 standardında G-kodları, basit satır-satır komutlardan çok daha karmaşık yapılar içerir: iç içe alt programlar (sub-programs), parametrik programlama (Fanuc Macro B, Siemens Cycles), koşullu dallanma, döngüler ve kullanıcı tanımlı değişkenler. Vericut ve NCSIMUL gibi yazılımların bu yapıları hatasız ayrıştırabilmesi, doğru bir AST (Abstract Syntax Tree) üretilmesine bağlıdır.

### 1.2 Önerilen Veri Yapıları

#### A) Lexer Katmanı — Token Akışı (Token Stream)

G-kodu önce bir lexer (sözcüksel çözümleyici) aşamasından geçirilir. Her satır, aşağıdaki token türlerine ayrıştırılır:

```
Token Türleri:
┌─────────────────────────────────────────────────────┐
│ BLOCK_NUMBER    : N100, N200, ...                   │
│ G_CODE          : G0, G1, G2, G3, G41, G43, ...     │
│ M_CODE          : M3, M5, M6, M30, ...              │
│ AXIS_WORD       : X, Y, Z, A, B, C + değer          │
│ FEED_RATE       : F (mm/min veya mm/rev)            │
│ SPINDLE_SPEED   : S (rpm)                           │
│ TOOL_CALL       : T + numara                        │
│ PARAMETER       : # (Fanuc), R (Siemens), @(Heidenhain)│
│ EXPRESSION      : Aritmetik ifadeler [#1+#2*SIN[#3]]│
│ COMMENT         : ( ... ) veya ; ...                │
│ SUB_CALL        : M98 P / CALL / L                  │
│ CONDITIONAL     : IF / THEN / ELSE / ENDIF / GOTO   │
│ LOOP            : WHILE / DO / END                   │
│ EOF             : Program sonu                      │
└─────────────────────────────────────────────────────┘
```

**En iyi veri yapısı:** Tokenler için bir `enum + tagged union` yapısı kullanılmalıdır:

```c
typedef enum {
    TOK_G_CODE, TOK_M_CODE, TOK_AXIS_WORD, TOK_PARAMETER,
    TOK_EXPRESSION, TOK_SUB_CALL, TOK_CONDITIONAL,
    TOK_LOOP, TOK_COMMENT, TOK_BLOCK_NUMBER, TOK_EOF
} TokenType;

typedef struct {
    TokenType type;
    int line_number;
    union {
        struct { int code; int subcode; } g_code;       // G43.1 → code=43, sub=1
        struct { char axis; double value; } axis_word;
        struct { int var_id; double value; } parameter;
        struct { ASTNode* root; } expression;            // İfade ağacı
        struct { int prog_number; int repeat; } sub_call;
    } data;
} Token;
```

#### B) Parser Katmanı — Abstract Syntax Tree (AST)

Tokenler, hiyerarşik bir AST'ye dönüştürülür. Bu ağaç, CNC programının semantik yapısını temsil eder:

```
                    Program
                    ├── Block (N100)
                    │   ├── GCode(G1)
                    │   ├── AxisWord(X, 50.0)
                    │   ├── AxisWord(Y, 30.0)
                    │   └── FeedRate(F, 500)
                    ├── Block (N200)
                    │   └── SubProgramCall(O9100, repeat=3)
                    │       └── [SubProgram O9100 AST referansı]
                    ├── ConditionalBlock
                    │   ├── Condition: IF [#1 GT 10]
                    │   ├── ThenBranch: [Block listesi]
                    │   └── ElseBranch: [Block listesi]
                    └── WhileLoop
                        ├── Condition: WHILE [#2 LT 100]
                        └── Body: [Block listesi]
```

**AST Node yapısı:**

```c
typedef enum {
    NODE_PROGRAM, NODE_BLOCK, NODE_GCODE, NODE_MCODE,
    NODE_AXIS_WORD, NODE_SUB_CALL, NODE_SUB_PROGRAM,
    NODE_IF_THEN_ELSE, NODE_WHILE_LOOP, NODE_GOTO,
    NODE_EXPRESSION, NODE_VARIABLE_ASSIGN
} NodeType;

typedef struct ASTNode {
    NodeType type;
    int line_number;
    struct ASTNode** children;
    int child_count;
    // Tip-spesifik veri:
    union {
        struct { int g_code; int g_subcode; ModalGroup group; } gcode_data;
        struct { int program_id; int repetition; struct ASTNode* target; } subcall_data;
        struct { struct ASTNode* condition; struct ASTNode* then_body; struct ASTNode* else_body; } if_data;
        struct { struct ASTNode* condition; struct ASTNode* body; } while_data;
        struct { int var_id; struct ASTNode* expr; } assign_data;
    } data;
} ASTNode;
```

#### C) Modal State Machine — Modal Durum Tablosu

G-kodları "modal" çalışır: bir G-kodu aktifleştirildiğinde, aynı gruptaki başka bir kod gelene kadar aktif kalır. Bu, en kritik parsing bileşenidir:

```
Modal Gruplar (ISO 6983):
┌─────────┬──────────────────────────────────────────────┐
│ Grup 01 │ G0, G1, G2, G3         (Hareket tipi)       │
│ Grup 02 │ G17, G18, G19          (Düzlem seçimi)      │
│ Grup 03 │ G90, G91               (Mutlak/Artımlı)     │
│ Grup 05 │ G93, G94, G95          (İlerleme modu)      │
│ Grup 06 │ G20, G21               (İnç/Metrik)         │
│ Grup 07 │ G40, G41, G42          (Takım yarıçap komp.)│
│ Grup 08 │ G43, G44, G49          (Takım boy komp.)    │
│ Grup 09 │ G73, G80, G81-G89      (Sabit döngüler)     │
│ Grup 10 │ G98, G99               (Dönüş düzlemi)      │
│ Grup 12 │ G54-G59, G54.1 Pxx     (İş koordinatları)   │
│ Grup 14 │ G96, G97               (Sabit yüzey hızı)   │
│ Grup 16 │ G68, G69               (Koordinat dönüşümü)  │
└─────────┴──────────────────────────────────────────────┘
```

**Veri yapısı:** HashMap/Dictionary tabanlı modal state:

```python
class ModalState:
    def __init__(self):
        self.groups = {
            1:  'G0',     # Motion mode
            2:  'G17',    # Plane selection
            3:  'G90',    # Distance mode
            5:  'G94',    # Feed mode
            6:  'G21',    # Units
            7:  'G40',    # Cutter comp
            8:  'G49',    # Tool length comp
            9:  'G80',    # Canned cycle
            12: 'G54',    # Work coordinate
        }
        self.position = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'A': 0.0, 'B': 0.0, 'C': 0.0}
        self.feed_rate = 0.0
        self.spindle_speed = 0
        self.active_tool = 0
        self.tool_length_offset = 0
        self.cutter_radius_offset = 0
        # Fanuc Macro B değişkenleri
        self.local_vars  = {}    # #1-#33  (lokal)
        self.common_vars = {}    # #100-#199, #500-#999 (ortak)
        self.system_vars = {}    # #1000+ (sistem)
```

#### D) Alt Program Yönetimi — Call Stack

Sub-program çağrıları (M98, CALL, L) bir call stack ile yönetilir:

```
Call Stack Yapısı:
┌──────────────────────────────────────────┐
│ Frame 3: O9200 (satır 5)  ← aktif       │
│ Frame 2: O9100 (satır 12, tekrar 2/3)   │
│ Frame 1: O9100 (satır 12, tekrar 1/3)   │
│ Frame 0: Ana Program (satır 45)          │
└──────────────────────────────────────────┘

struct CallFrame {
    int program_id;
    int return_line;
    int current_line;
    int repeat_count;
    int current_repeat;
    HashMap<int, double> local_variables;  // Lokal değişken kapsamı
};

// Stack derinliği: Tipik CNC kontrollerde 4-10 seviye
Stack<CallFrame> call_stack;  // max_depth = 10 (Fanuc), 16 (Siemens)
```

### 1.3 Kontrolcüye Özgü Dialect Yönetimi

Her CNC kontrolcüsünün kendine özgü G-kodu lehçesi vardır. Bu, bir "dialect registry" ile yönetilmelidir:

```
Kontrolcü Farklılıkları:
┌────────────┬───────────────────┬──────────────────┬──────────────────┐
│            │ Fanuc             │ Siemens          │ Heidenhain       │
├────────────┼───────────────────┼──────────────────┼──────────────────┤
│ Değişken   │ #1, #100          │ R1, R100         │ Q1, QL1          │
│ Alt Program│ M98 P9100         │ CALL "PROG1"     │ CALL PGM 9100    │
│ Döngü      │ WHILE[#1 LT 10]  │ WHILE R1<10      │ CYCL CALL        │
│ Koşul      │ IF[#1 EQ 1]GOTO  │ IF R1==1 GOTOF   │ FN 9: IF +Q1...  │
│ Yorum      │ ( yorum )        │ ; yorum          │ ; yorum          │
│ Makrolar   │ G65 P9100        │ CYCLE DEF         │ CYCL DEF         │
│ Koordinat  │ G54.1 P1-P48     │ G54-G599          │ DATUM (REF)      │
│ RTCP       │ G43.4/G43.5      │ TRAORI/TRAFOOF    │ M128/M129        │
└────────────┴───────────────────┴──────────────────┴──────────────────┘
```

### 1.4 Edge Cases ve Kritik Hatalar

```
⚠️ G-CODE PARSING EDGE CASES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. AYNI SATIRDA ÇELİŞEN MODAL KODLAR
   Örnek: "G0 G1 X100"  → G0 mu G1 mi aktif?
   Çözüm: Satırdaki SON modal kod geçerlidir (Fanuc davranışı).
          Siemens ise hata verir. Dialect-specific handling gerekir.

2. ÖRTÜK G-KODU (Implicit G-Code)
   Örnek: "X100 Y50" (G-kodu yok)
   Çözüm: Modal state'den aktif hareket kodu (G0/G1) kullanılır.
          HATA: Parser, modal state başlatılmadan çalışırsa
          makine davranışı belirsizdir.

3. ALT PROGRAM SONSUZ DÖNGÜSÜ
   Örnek: O9100 → M98 P9200 → M98 P9100 (karşılıklı çağrı)
   Çözüm: Call stack derinlik kontrolü + visited program tracking.
          Max depth aşılırsa → ALARM.

4. DEĞİŞKEN BAĞIMLI G-KODU
   Örnek: "G#100 X50" → #100 = 1 ise G1, = 0 ise G0
   Çözüm: İfade değerlendirmesi (expression evaluation) G-kodu
          çözümlenmeden ÖNCE yapılmalıdır.

5. SABIT DÖNGÜDE ARTIMLI/MUTLAK KARISIKLIĞI
   Örnek: G91 G81 X10 Y10 Z-20 R2 L5
   Çözüm: G91 modunda X ve Y artımlı ama Z ve R her zaman
          mutlak olarak yorumlanır (Fanuc). Siemens'te farklıdır.

6. TAKIMYOLU TELAFİSİ GİRİŞ/ÇIKIŞ
   Örnek: G41 D1 satırından sonra yetersiz hareket
   Çözüm: G41/G42 aktivasyonu en az 2 hareket bloğu gerektirir.
          İlk blok "ramp-on" hareketidir. Telafi vektörü hesabı
          lookahead buffer'da yapılır.

7. ONDALIK NOKTA OLMADAN DEĞER
   Örnek: "X1000" → 1000mm mi, 100.0mm mi, 1.000mm mi?
   Çözüm: Fanuc'ta ondalık nokta yoksa → tam sayı (1000mm).
          Bazı eski kontrollerde → son 3 hane ondalık (1.000mm).
          Dialect konfigürasyonu zorunludur.

8. BLOK SKIP (/) İŞARETİ
   Örnek: "/N100 G0 X50" → operatör panelinde block skip
          aktifse satır atlanır
   Çözüm: Simülasyon parametresi olarak block skip durumu
          kullanıcıdan alınmalıdır.

9. G68 KOORDİNAT DÖNÜŞÜMÜ İÇ İÇE ÇAĞRILARI
   Örnek: G68 X0 Y0 R45 → G68 X10 Y0 R30 (iç içe rotasyon)
   Çözüm: Dönüşüm matrisleri çarpılarak birikmeli (cumulative)
          olarak uygulanmalıdır. Stack-based transformation.

10. PROGRAM NUMARASI ÇAKIŞMASI
    Örnek: Aynı O-numarasına sahip iki alt program
    Çözüm: Program registry'de son yüklenen geçerlidir.
           Uyarı mekanizması gereklidir.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 2. Kinematik Zincirler ve RTCP Hesaplamaları

### 2.1 5-Eksenli Makine Konfigürasyonları

5-eksenli CNC tezgahları, iki döner eksenin konumuna göre üç ana topolojiye ayrılır:

```
KONFİGÜRASYON TİPLERİ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HEAD-HEAD (Çift Döner Kafa)
   Zincir: Zemin → X → Y → Z → A(kafa) → C(kafa) → Takım
   Örnek: DMG MORI DMU serisi, Mazak VARIAXIS (bazı modeller)

     ┌─────────┐    ┌─────────┐    ┌─────────┐
     │ X-Y-Z   │ →  │ A ekseni │ →  │ C ekseni │ → Takım
     │ lineer  │    │ (tilting)│    │ (spindle)│
     └─────────┘    └─────────┘    └─────────┘
                       ↕ pivot         ↻ rotation
                     noktası

2. TABLE-TABLE (Çift Döner Tabla)
   Zincir: Zemin → X → Y → Z → Takım
           Zemin → A(tabla) → C(tabla) → İş parçası
   Örnek: DMG MORI NMV serisi, Hermle C-serisi

     Takım ← Z-Y-X ← Zemin → A(tilt) → C(rot) → İş Parçası
                                  ↕           ↻

3. HEAD-TABLE (Karma / En Yaygın)
   Zincir: Zemin → X → Y → Z → B(kafa) → Takım
           Zemin → C(tabla) → İş parçası
   Örnek: DMG MORI DMU 50/80, Hermle C42, Mazak VARIAXIS i-series

     Takım ← B(kafa) ← Z-Y-X ← Zemin → C(tabla) → İş Parçası
               ↕ tilt                        ↻ rot
```

### 2.2 Homojen Dönüşüm Matrisleri (Denavit-Hartenberg)

Her eksen, 4×4 homojen dönüşüm matrisi ile temsil edilir. Genel form:

```
Lineer Eksen (X, Y veya Z yönünde d kadar öteleme):

        ┌ 1  0  0  dx ┐
T_lin = │ 0  1  0  dy │    (dx, dy, dz: eksen yönüne göre)
        │ 0  0  1  dz │
        └ 0  0  0   1 ┘

Döner A ekseni (X etrafında θ_A kadar dönme):

         ┌ 1    0        0      px ┐
T_A(θ) = │ 0  cos(θ)  -sin(θ)  py │    (px,py,pz: pivot noktası)
         │ 0  sin(θ)   cos(θ)  pz │
         └ 0    0        0      1  ┘

Döner B ekseni (Y etrafında θ_B kadar dönme):

         ┌  cos(θ)  0  sin(θ)  px ┐
T_B(θ) = │    0     1    0     py │
         │ -sin(θ)  0  cos(θ)  pz │
         └    0     0    0      1  ┘

Döner C ekseni (Z etrafında θ_C kadar dönme):

         ┌ cos(θ)  -sin(θ)  0  px ┐
T_C(θ) = │ sin(θ)   cos(θ)  0  py │
         │   0        0     1  pz │
         └   0        0     0   1  ┘
```

### 2.3 RTCP (Rotation Tool Center Point) Matematiksel Model

RTCP, döner eksenler hareket ettiğinde takım ucunun iş parçası üzerindeki konumunu sabit tutmak için lineer eksenlere telafi hareketi ekler. Bu, 5-eksenli işlemenin temelidir.

#### Head-Table Konfigürasyonu için RTCP (En yaygın):

```
Tanımlar:
  B  = Kafa döner ekseni açısı (Y ekseni etrafında)
  C  = Tabla döner ekseni açısı (Z ekseni etrafında)
  L  = Takım boyu (gauge length)
  Pp = Pivot noktası (B ekseni dönme merkezi) [Xp, Yp, Zp]

Takım ucu yön vektörü (Tool Axis Vector):
  ┌ tx ┐   ┌  sin(B)          ┐
  │ ty │ = │  -sin(C)·cos(B)  │
  └ tz ┘   └   cos(C)·cos(B)  ┘

  (B=0, C=0 → takım Z+ yönüne bakar: [0, 0, 1])

RTCP Telafi Hesabı:

  Programlanan konum (iş parçası koordinatları):
  P_prog = [Xp, Yp, Zp]   (CNC programındaki X, Y, Z değerleri)

  Takım ucu telafisi (pivot → takım ucu):
  ΔP = L · t̂ = L · [sin(B), -sin(C)·cos(B), cos(C)·cos(B)]

  Pivot noktası ofset telafisi:
  Tabla dönüşü nedeniyle pivot noktasının iş parçasına göre ofseti:

  ┌ΔXp┐   ┌ cos(C)  -sin(C)  0 ┐   ┌ Xp ┐   ┌ Xp ┐
  │ΔYp│ = │ sin(C)   cos(C)  0 │ · │ Yp │ - │ Yp │
  └ΔZp┘   └   0        0     1 ┘   └ Zp ┘   └ Zp ┘

  Makine eksen konumları (kontrol birimine gönderilen):
  X_machine = X_prog + L·sin(B) - Xp·(cos(C)-1) + Yp·sin(C)
  Y_machine = Y_prog - L·sin(C)·cos(B) - Xp·sin(C) - Yp·(cos(C)-1)
  Z_machine = Z_prog + L·cos(C)·cos(B) - L

  Basitleştirilmiş form (pivot orijinde: Xp=Yp=Zp=0):
  X_machine = X_prog + L·sin(B)
  Y_machine = Y_prog - L·sin(C)·cos(B)
  Z_machine = Z_prog + L·(cos(B)·cos(C) - 1)
```

#### Head-Head Konfigürasyonu için RTCP:

```
Tanımlar:
  A  = Birinci döner eksen açısı (X ekseni etrafında tilting)
  C  = İkinci döner eksen açısı (Z ekseni etrafında rotation)
  L  = Takım boyu
  P1 = A ekseni pivot noktası
  P2 = C ekseni pivot noktası (A'ya göre ofset: d)

Takım yön vektörü:
  ┌ tx ┐   ┌          sin(C)·sin(A)           ┐
  │ ty │ = │         -cos(C)·sin(A)            │
  └ tz ┘   └            cos(A)                 ┘

  (NOT: Eksen sırası önemlidir: Önce A, sonra C uygulanır)

RTCP Telafisi:
  X_machine = X_prog + L·sin(C)·sin(A) + d·(sin(C)·sin(A))
  Y_machine = Y_prog - L·cos(C)·sin(A) - d·(cos(C)·sin(A))
  Z_machine = Z_prog + L·(cos(A) - 1) + d·(cos(A) - 1)

  Burada d = P2-P1 (iki pivot arası mesafe)
```

#### Table-Table Konfigürasyonu için RTCP:

```
Tanımlar:
  A  = Birinci tabla döner ekseni (X etrafında, tilting cradle)
  C  = İkinci tabla döner ekseni (Z etrafında, rotary table)
  L  = Takım boyu (BU KONFİGÜRASYONDA SABİT KALIR)

Kritik fark: Takım sabit, iş parçası döner.
  → Takım ucuna telafi GEREKMEZ (takım yönü değişmez)
  → Bunun yerine iş parçası koordinatları dönüştürülür.

İş parçası dönüşüm matrisi:
  T_workpiece = T_C(θC) · T_A(θA)

  P_machine = T_C · T_A · P_prog

  Açık form:
  X_machine = X_prog·cos(C) - Y_prog·sin(C)·... [tam matris çarpımı]

  Table-Table'da RTCP yoktur; bunun yerine "düzlem eğme"
  (tilted working plane / CYCLE800) kullanılır.
```

### 2.4 İleri ve Ters Kinematik

```
İLERİ KİNEMATİK (Forward Kinematics):
  Makine eksen değerleri → Takım ucu dünya konumu
  P_tool_tip = T_base · T_X(x) · T_Y(y) · T_Z(z) · T_B(b) · T_tool(L) · P_0

TERS KİNEMATİK (Inverse Kinematics):
  İstenen takım ucu konumu + yönü → Makine eksen değerleri
  Girdi:  [Px, Py, Pz, Tx, Ty, Tz]  (konum + takım ekseni vektörü)
  Çıktı:  [X, Y, Z, B, C]            (makine eksenleri)

  Head-Table için analitik çözüm:
  B = arctan2(Tx, Tz)                          (veya asin(Tx))
  C = arctan2(-Ty/cos(B), Tz/cos(B))           (veya atan2(-Ty, Tz/cos(B)))

  ⚠️ Singülarite: cos(B) = 0 ise (B = ±90°) → C belirsiz (gimbal lock)
  Çözüm: Bu noktada C serbest seçilir, genellikle C = C_önceki

  B'nin iki çözümü vardır:
    Çözüm 1: B₁ = asin(Tx)
    Çözüm 2: B₂ = π - asin(Tx)
  → En kısa yolu seçen veya eksen limitlerini aşmayan çözüm tercih edilir.
```

### 2.5 Kinematik Edge Cases

```
⚠️ KİNEMATİK EDGE CASES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. GIMBAL LOCK (Tekil Nokta / Singülarite)
   Durum: B = ±90° (Head-Table) veya A = 0° (Head-Head)
   Etki: Bir döner eksen kaybedilir, sonsuz çözüm vardır.
   Sonuç: Makine eksenleri çılgınca dönebilir (360° C dönüşü).
   Çözüm: Singülarite bölgesinde yol bölümleme (path splitting)
          ve açısal hız sınırlaması.

2. PİVOT NOKTASI KALIBRASYON HATASI
   Durum: Gerçek pivot noktası ile tanımlanan arasında 0.01mm fark
   Etki: Her açıda farklı yüzey hatası, yarıçap büyüdükçe artar
   Formül: Hata ≈ Δpivot × sin(θ)
   Sonuç: 0.05mm pivot hatası, 30° açıda ~0.025mm yüzey hatası.

3. TAKIMALTI BOY ÖLÇÜM HATASI
   Durum: L (gauge length) 0.1mm yanlış
   Etki: RTCP telafisi yanlış hesaplanır
   Formül: Hata_X = 0.1 × sin(B), Hata_Z = 0.1 × (cos(B) - 1)
   Sonuç: B=45°'de X'te 0.07mm, Z'de 0.03mm hata.

4. EKSEN LİMİTLERİ GEÇİŞİ
   Durum: B ekseni -10° ile +110° arasında sınırlı
   Etki: Ters kinematik çözümlerden biri geçersiz
   Çözüm: Her iki çözüm kontrol edilir, geçerli olan seçilir.
          Her ikisi de geçersizse → iş parçası yeniden konumlandırılır.

5. 180° C DÖNÜŞÜ SORUNU (Roll-over)
   Durum: C ekseni 179° → -179° geçişi (aslında 2° hareket)
   Etki: Kontrol birimi 358° ters yönde dönebilir.
   Çözüm: Angular unwrapping: Δθ = atan2(sin(Δ), cos(Δ))
          ile en kısa yol hesaplanır.

6. İLERLEME HIZI DOĞRULAMASIZLIĞI
   Durum: Programlanan F=1000 mm/dk → TCP'de 1000 mm/dk
   Etki: Döner eksenler hızlı dönüyorsa, lineer eksenler
         çok yüksek hızlara çıkmak zorunda kalabilir.
   Çözüm: RTCP modunda gerçek TCP hızı hesaplanır:
          V_tcp = √(Vx² + Vy² + Vz²)
          Makine limitleri aşılıyorsa F otomatik düşürülür.

7. TABLA AĞIRLIĞINA BAĞLI DİNAMİK SAPMA
   Durum: Ağır iş parçası tabla dönerken merkezkaç kuvveti
   Etki: Simülasyonda olmayan mekanik sapmalar
   Sonuç: Simülasyon vs. gerçek kesim farkı (FEM entegrasyonu
          gerekir, bu Vericut'un kapsamı dışındadır).

8. ÇİFT ÇÖZÜMLÜ TERS KİNEMATİK GEÇİŞİ
   Durum: Yol boyunca B₁ çözümünden B₂ çözümüne geçiş
   Etki: Eksenlerde süreksizlik (sıçrama)
   Çözüm: Tüm yol boyunca aynı çözüm ailesi kullanılır.
          Geçiş gerekiyorsa retract → reposition → approach.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 3. Çarpışma Algılama (Collision Detection)

### 3.1 Genel Mimari — İki Aşamalı Yaklaşım

Gerçek zamanlı CNC simülasyonunda çarpışma algılama, iki aşamalı bir pipeline kullanır:

```
ÇARPIŞMA ALGILAMA MİMARİSİ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                   Tüm Nesne Çiftleri
                   (N nesne → N(N-1)/2 çift)
                          │
                          ▼
            ┌──────────────────────────┐
            │   BROAD PHASE            │
            │   (Kaba Eleme)           │
            │                          │
            │   ● AABB (Axis-Aligned   │
            │     Bounding Box)        │
            │   ● BVH (Bounding Volume │
            │     Hierarchy)           │
            │   ● Sweep and Prune      │
            │                          │
            │   Sonuç: Aday çiftler    │
            │   O(N log N)             │
            └────────────┬─────────────┘
                         │ (genellikle %95+ elenir)
                         ▼
            ┌──────────────────────────┐
            │   NARROW PHASE           │
            │   (Hassas Test)          │
            │                          │
            │   ● GJK Algoritması      │
            │   ● EPA (Penetrasyon)    │
            │   ● Triangle-Triangle    │
            │   ● Signed Distance      │
            │                          │
            │   Sonuç: Kesin çarpışma  │
            │   bilgisi + penetrasyon  │
            │   derinliği + temas      │
            │   noktaları              │
            └──────────────────────────┘
```

### 3.2 Broad Phase: BVH (Bounding Volume Hierarchy)

BVH, CNC simülasyonunda en performanslı broad-phase yapısıdır çünkü geometriler frame-to-frame küçük değişiklikler gösterir (incremental updates).

```
BVH AĞACI YAPISI (AABB tabanlı):

                    ┌─────────────────┐
                    │  Root AABB      │
                    │  (Tüm sahne)    │
                    └────────┬────────┘
                       ┌─────┴─────┐
                 ┌─────┴───┐ ┌─────┴───┐
                 │ Makine   │ │ İş      │
                 │ gövdesi  │ │ parçası │
                 └────┬─────┘ └────┬────┘
                ┌─────┴──┐     ┌───┴────┐
           ┌────┴───┐ ┌──┴──┐ │ Stock  │
           │Spindle │ │Table│ │ mesh   │
           └───┬────┘ └─────┘ └────────┘
          ┌────┴────┐
     ┌────┴──┐  ┌───┴────┐
     │Holder │  │ Tool   │
     └───────┘  │ (Cutter)│
                └─────────┘

BVH Node yapısı:
struct BVHNode {
    AABB bounding_box;        // Min-max köşe noktaları
    BVHNode* left;
    BVHNode* right;
    Mesh* geometry;           // Yaprak node'da gerçek geometri
    int object_type;          // SPINDLE, HOLDER, TOOL, TABLE, etc.
    bool is_moving;           // Her frame güncellenmeli mi?
    Matrix4x4 transform;     // Dünya dönüşümü
};

AABB Güncelleme (her simülasyon adımında):
  ● Sadece HAREKET EDEN nesnelerin AABB'leri güncellenir
  ● Bottom-up refit: yaprak → kök yönünde
  ● Karmaşıklık: O(k · log N), k = değişen yaprak sayısı
```

**AABB Kesişim Testi:**

```
İki AABB'nin kesişimi (en hızlı red testi):

bool AABB_Intersect(AABB a, AABB b) {
    return (a.min.x <= b.max.x && a.max.x >= b.min.x) &&
           (a.min.y <= b.max.y && a.max.y >= b.min.y) &&
           (a.min.z <= b.max.z && a.max.z >= b.min.z);
}

Performans: 6 karşılaştırma, erken çıkış ile ortalama ~3
```

### 3.3 Narrow Phase: GJK Algoritması

GJK (Gilbert-Johnson-Keerthi), iki konveks şeklin kesişimini Minkowski farkı üzerinden test eder. CNC simülasyonunda konveks hull'lara ayrıştırılmış parçalar için idealdir.

```
GJK ALGORİTMASI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Temel fikir:
  İki konveks şeklin kesişimi ⟺ Minkowski farkının orijini içermesi

  Minkowski Farkı: A ⊖ B = { a - b : a ∈ A, b ∈ B }

Support fonksiyonu (her yön için en uç nokta):
  Support_A(d) = argmax { p · d : p ∈ A }
  Support_B(d) = argmax { p · (-d) : p ∈ B }
  Support(d) = Support_A(d) - Support_B(-d)

GJK İterasyon:
  1. Başlangıç yönü d seçilir (genellikle A_center - B_center)
  2. p = Support(d) hesaplanır
  3. Eğer p · d < 0 → KESİŞİM YOK (erken çıkış)
  4. p, simplex'e eklenir
  5. Simplex güncellenir (en yakın özellik bulunur)
  6. Yeni d = orijin yönüne işaret eden vektör
  7. Simplex orijini içerene kadar tekrarla (2-4 iterasyon)

Simplex evrimi (2D görselleştirme):
  İterasyon 1: Nokta  →  d = orijin yönü
  İterasyon 2: Çizgi  →  d = çizgiye dik, orijin tarafı
  İterasyon 3: Üçgen  →  d = üçgen normalı, orijin tarafı
  İterasyon 4: Tetrahedron → orijin içeride mi kontrol et

Karmaşıklık: O(k · n), k = iterasyon (~4-20), n = vertex sayısı
CNC kullanımı: Konveks alt-parçalar için idealdir.
```

### 3.4 EPA (Expanding Polytope Algorithm) — Penetrasyon Derinliği

GJK kesişim tespit ettikten sonra, EPA penetrasyon derinliğini ve yönünü hesaplar:

```
EPA ALGORİTMASI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Girdi: GJK'nın son simplex'i (orijini içeren tetrahedron)
Çıktı: Penetrasyon derinliği (d) ve penetrasyon yönü (n̂)

  1. GJK simplex'ini başlangıç polytope'u yap
  2. Orijine en yakın yüzeyi bul
  3. Bu yüzey normalinde yeni Support noktası hesapla
  4. Polytope'u genişlet (yeni nokta ekle, yüzeyler güncelle)
  5. Orijine en yakın yüzey artık değişmiyorsa → SONUÇ:
     ● Penetrasyon derinliği = en yakın yüzey-orijin mesafesi
     ● Penetrasyon yönü = yüzey normali

CNC Uygulaması:
  ● Takım tutucu - iş parçası arasındaki penetrasyon miktarı
  ● "Near miss" uyarısı: penetrasyon < güvenlik mesafesi
  ● Minimum mesafe hesabı (clearance check)
```

### 3.5 Mesh-to-Mesh Triangle Testi

Konveks olmayan (non-convex) geometriler için doğrudan üçgen-üçgen testi gerekir:

```
MÖLLER-TRUMBORE ÜÇGEN-ÜÇGEN KESİŞİM TESTİ:

Her üçgen çifti (T1, T2) için:
  1. T1'in düzlemini hesapla: n₁ = (v1-v0) × (v2-v0)
  2. T2'nin köşelerinin T1 düzlemine mesafelerini hesapla
  3. Tüm mesafeler aynı işaretliyse → KESİŞMEZ
  4. Kesişim doğrusunu hesapla (iki düzlemin kesişimi)
  5. Her üçgenin kesişim doğrusu üzerindeki aralığını bul
  6. Aralıklar örtüşüyorsa → KESİŞİR

Optimizasyon: BVH ile elenmiş çiftlerde yapılır.
Karmaşıklık: O(1) per pair, toplam O(k²) aday çift için.
```

### 3.6 CNC-Spesifik Çarpışma Çiftleri

```
KONTROL EDİLMESİ GEREKEN ÇİFTLER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Yüksek Öncelik (her adımda):
  ┌─────────────────────────────────────────────────┐
  │  Takım  ↔  İş Parçası  (İşleme simülasyonu)    │
  │  Holder ↔  İş Parçası  (EN SIK ÇARPIŞMA!)      │
  │  Holder ↔  Bağlama      (Mengene, fixture)      │
  │  Spindle ↔ İş Parçası                           │
  │  Spindle ↔ Bağlama                              │
  └─────────────────────────────────────────────────┘

  Orta Öncelik (rapid hareketlerde):
  ┌─────────────────────────────────────────────────┐
  │  Takım  ↔  Bağlama                              │
  │  Tabla  ↔  Spindle                               │
  │  Kablo Zinciri ↔ Diğer parçalar (opsiyonel)     │
  └─────────────────────────────────────────────────┘

  Düşük Öncelik (yol planlama):
  ┌─────────────────────────────────────────────────┐
  │  Herhangi bir parça ↔ Makine gövdesi            │
  │  Eksenlerin hareket limitleri (soft limits)      │
  └─────────────────────────────────────────────────┘
```

### 3.7 Çarpışma Algılama Edge Cases

```
⚠️ ÇARPIŞMA ALGILAMA EDGE CASES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. TUNNELING (Tünelleme)
   Durum: Rapid (G0) hareket çok hızlı, çarpışma iki frame
          arasında atlanır (ince duvar / uzun mesafe)
   Çözüm: Swept volume testi veya CCD (Continuous Collision
          Detection). Her G0 hareketini lineer interpolasyon
          ile ara noktalara böl: dt = min_feature_size / V_rapid

2. YÜZEY-YÜZEY TEMASI (Grazing Contact)
   Durum: Takım tutucu, iş parçasına sadece teğet geçiyor
   Etki: GJK penetrasyon = 0, EPA belirsiz sonuç
   Çözüm: Güvenlik mesafesi (clearance) parametresi:
          if (distance < safety_margin) → UYARI

3. İNCE GEOMETRİ (Thin Features)
   Durum: 0.5mm kalınlığında nervür veya ince cidar
   Etki: BVH'deki AABB'ler neredeyse düzlemsel, çok sayıda
         false positive
   Çözüm: OBB (Oriented Bounding Box) kullanımı veya
          BVH yaprak boyutunun min thickness'tan büyük olması.

4. DEĞİŞEN GEOMETRİ (Evolving Stock)
   Durum: İşleme ilerledikçe iş parçası şekli değişir
   Etki: BVH sürekli rebuild edilmeli
   Çözüm: CSG (Constructive Solid Geometry) veya
          Dexel/Z-buffer tabanlı stock modeli + incremental
          BVH update. Vericut bu yaklaşımı kullanır.

5. KONVEKS OLMAYAN GEOMETRİ
   Durum: Karmaşık bağlama ekipmanları, T-slot plakalar
   Etki: GJK doğrudan çalışmaz (konveks geometri gerektirir)
   Çözüm: Konveks ayrıştırma (convex decomposition):
          V-HACD algoritması ile ~20-50 konveks hull'a ayırma.

6. NUMERIK HASSASIYET
   Durum: İki yüzey tam olarak aynı düzlemde (coplanar)
   Etki: Üçgen-üçgen testinde 0/0 veya NaN
   Çözüm: Epsilon-tabanlı karşılaştırmalar:
          |n·d| < ε ise → coplanar kabul et (ε ≈ 1e-10)

7. BÜYÜK ÖLÇEK FARKI
   Durum: Ø0.5mm matkap + 2000mm makine gövdesi
   Etki: Floating point hassasiyet kaybı, AABB çok gevşek
   Çözüm: Çok seviyeli BVH + lokal koordinat sistemleri.
          Makine parçaları dünya koordinatında, takım/parça
          bölgesi lokal koordinatta hesaplanır.

8. TAKIMALTI DEĞİŞİMİ SIRASI
   Durum: M6 sırasında eski takım çıkıyor, yeni giriyor
   Etki: ATC (Automatic Tool Changer) kolu animasyonu
         sırasında çarpışma kontrolü atlanabilir
   Çözüm: Takım değişim döngüsü ayrı bir kinematik
          zincir olarak modellenmeli ve her adımı kontrol
          edilmelidir.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 4. Optimizasyon: Air-Cut Tespiti

### 4.1 Air-Cut Tanımı ve Maliyeti

```
AIR-CUT (Boşta Kesim):
  Tanım: Takımın programlanmış ilerleme hızında (G1/G2/G3)
         hareket ettiği fakat malzemeyle temas etmediği durumlar.

  Maliyet Etkisi:
  ● Tipik bir CNC programında %15-40 air-cut bulunabilir
  ● CAM yazılımları güvenlik için fazla approach/retract ekler
  ● Roughing operasyonlarında önceki pasoların kaldırdığı
    malzeme üzerinden tekrar geçiş
  ● Her dakika boşta kesim = kayıp üretim kapasitesi
```

### 4.2 Geometrik Kesişim Testleri

#### A) Dexel Board Modeli (Vericut yaklaşımı)

```
DEXEL (Discrete Element) MODELİ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  XY düzleminde düzgün ızgara, her hücrede Z-yönünde dexel'ler:

  Üstten görünüm (XY ızgarası):
  ┌───┬───┬───┬───┬───┬───┐
  │   │ ║ │ ║ │ ║ │   │   │
  ├───┼─║─┼─║─┼─║─┼───┼───┤
  │   │ ║ │ ║ │ ║ │ ║ │   │  ║ = malzeme var
  ├───┼─║─┼─║─┼─║─┼─║─┼───┤
  │   │ ║ │ ║ │ ║ │ ║ │   │
  ├───┼───┼─║─┼─║─┼───┼───┤
  │   │   │ ║ │   │   │   │
  └───┴───┴───┴───┴───┴───┘

  Yandan görünüm (tek dexel kolonu):
       ┌─────┐ z_top_1
       │█████│
       │█████│ z_bottom_1
       └─────┘
                            ← boşluk (önceki işleme)
       ┌─────┐ z_top_2
       │█████│
       │█████│ z_bottom_2
       └─────┘

  Her dexel: (z_bottom, z_top) çiftlerinin sıralı listesi
  Multi-dexel: Bir kolonda birden fazla segment (delikler, cep-ler)

Veri yapısı:
struct Dexel {
    float z_bottom;
    float z_top;
};

struct DexelColumn {
    std::vector<Dexel> segments;    // Sıralı, örtüşmeyen
};

struct DexelBoard {
    float x_min, y_min;
    float x_max, y_max;
    float resolution;                // Tipik: 0.1-0.5mm
    int nx, ny;                      // Izgara boyutları
    DexelColumn** grid;              // 2D dizi
};
```

#### B) Air-Cut Tespiti Algoritması

```
AIR-CUT TESPİT ALGORİTMASI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Her G1/G2/G3 hareketi için:

  1. TAKIM SWEPT VOLUME HESABI:
     ● Takım başlangıç ve bitiş pozisyonu arasında
       swept cylinder/cone oluştur
     ● Swept volume AABB'sini hesapla

  2. DEXEL BOARD KESİŞİM TESTİ:
     ● Swept volume AABB'si içindeki dexel kolonlarını bul
     ● Her kolon için:
       a) Takımın o kolondaki Z aralığını hesapla
       b) Dexel segmentleriyle kesişim kontrolü

     Pseudocode:
     is_air_cut = true
     for each dexel_column in swept_AABB:
         tool_z_range = compute_tool_z_at(column.x, column.y)
         for each segment in column.segments:
             if overlaps(tool_z_range, segment):
                 is_air_cut = false
                 remove_material(segment, tool_z_range)
                 break

  3. SONUÇ:
     ● Tüm dexel kolonlarında kesişim yoksa → AIR-CUT
     ● Kısmi kesişim → PARTIAL CUT (optimizasyon fırsatı)
     ● Tam kesişim → NORMAL CUT

  Karmaşıklık: O(k), k = swept volume'un kapsadığı dexel sayısı
  Tipik: 100-1000 dexel per move
```

#### C) Tri-Dexel Model (Gelişmiş)

```
TRI-DEXEL (3 Yönlü Dexel):
  ● X, Y ve Z yönlerinde ayrı dexel board'ları
  ● Daha doğru geometri temsili (tek dexel → aliasing)
  ● Undercut ve negatif draft açılarını yakalayabilir

  Üç board:
  Board_XY: Z yönünde dexel'ler (üstten bakış)
  Board_XZ: Y yönünde dexel'ler (önden bakış)
  Board_YZ: X yönünde dexel'ler (yandan bakış)

  Kesişim: Üç board'un OR'lanması → daha doğru sonuç
  Maliyet: 3× bellek, ~2× hesaplama süresi
```

### 4.3 Optimizasyon Stratejileri

```
OPTİMİZASYON KATMANLARI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A) RAPID OVERRIDE:
   Tespit: G0 hareketi sırasında iş parçasıyla mesafe hesabı
   Aksiyon: Air-cut G1 bloklarını G0'a dönüştür
   Kazanç: %50-80 hız artışı (rapid vs. feed rate)

   Kural:
   IF (block is G1 AND material_removed == 0)
       AND (min_distance_to_stock > safety_margin):
       REPLACE with G0

B) FEED RATE OPTİMİZASYONU:
   Tespit: Kesim derinliği (ae, ap) ve malzeme kaldırma hacmi
   Aksiyon: Düşük yüklü bölgelerde F artır, yüksek yüklü
            bölgelerde F azalt
   Formül:
     F_optimal = F_ref × (MRR_ref / MRR_actual)^n
     MRR = Material Removal Rate (mm³/dk)
     n = 0.3-0.7 (malzeme bağımlı)

C) SPATIAL HASHING (Hızlı konum sorgusu):
   ● 3D uzayı sabit boyutlu hücrelere böl
   ● Her hücrede: o bölgedeki dexel referansları
   ● Takım hareketi → sadece ilgili hücreler sorgulanır

   struct SpatialHash {
       float cell_size;         // Takım çapından biraz büyük
       HashMap<(ix,iy,iz), vector<DexelRef>> cells;
   };

D) INCREMENTAL GÜNCELLEME:
   ● Her kesimden sonra sadece değişen dexel'leri güncelle
   ● BVH refit: sadece etkilenen dal
   ● Karmaşıklık: O(m), m = değişen dexel sayısı (genellikle << N)

E) PARALEL HESAPLAMA:
   ● Dexel board doğal olarak paralelleştirilebilir
   ● Her dexel kolonu bağımsız işlenebilir
   ● GPU compute (CUDA/OpenCL):
     - Dexel board → GPU texture
     - Swept volume → GPU shader
     - Kesişim testi → fragment shader
   ● Speedup: 10-50× (GPU vs single-thread CPU)

F) LOD (Level of Detail):
   ● Kaba simülasyon: Düşük çözünürlük dexel (1mm)
   ● İnce simülasyon: Yüksek çözünürlük (0.05mm)
   ● Adaptif: Takım yakınında yüksek, uzakta düşük çözünürlük
```

### 4.4 Air-Cut Edge Cases

```
⚠️ AIR-CUT TESPİTİ EDGE CASES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. MİKRO-KESİM (SIFILANMA HATASI)
   Durum: Takım yüzeyi 0.001mm derinlikte "çiziyor"
   Etki: Dexel çözünürlüğü yetersizse air-cut olarak algılanır
   Çözüm: Dexel çözünürlüğü < minimum kesim derinliği olmalı.
          Alternatif: Analitik kesişim hesabı (dexel-free).

2. HELİKAL İNTERPOLASYON (G2/G3 + Z hareketi)
   Durum: Helikal dalma sırasında swept volume hesabı
   Etki: Basit silindir süpürme yanlış sonuç verir
   Çözüm: Helikal yolu düz segmentlere böl (chord error < tol).
          Her segment için ayrı swept volume testi.

3. TAKIMYOLU TELAFİSİ (G41/G42) SONRASI
   Durum: Telafi hesabı sonrası gerçek yol, programlanandan
          farklı olabilir (özellikle iç köşelerde)
   Etki: Air-cut tespiti telafi ÖNCESİ değil SONRASI yapılmalı
   Çözüm: Telafi hesaplanmış yol üzerinden analiz yapılır.

4. TALAŞ HACMI = 0 AMA TEMAS VAR
   Durum: Finishing pasosunda yüzey temizleme
          (spring pass / spark-out)
   Etki: Malzeme kaldırılmıyor ama temas var → air-cut DEĞİL
   Çözüm: Air-cut tanımı: temas yok AND malzeme kaldırılmıyor.
          Temas varsa, MRR=0 olsa bile air-cut sayılmaz.

5. TERS TALAŞ (Climb vs Conventional Algılama)
   Durum: Takımın ters yönden geçişi temas oluşturabilir
          ama kesim yapmaz (deflection riski)
   Çözüm: Takım dönüş yönü ve ilerleme yönü birlikte
          değerlendirilir. Ters talaş uyarısı verilir.

6. SICAKLIK ETKİSİ (Termal Genleşme)
   Durum: Uzun işlemelerde malzeme genleşmesi
   Etki: Simülasyonda air-cut, gerçekte temas (veya tersi)
   Çözüm: Bu, simülasyon kapsamı dışındadır.
          Vericut ve NCSIMUL bunu modellemez.

7. STOK MODEL HATA BİRİKİMİ
   Durum: Binlerce kesim sonrası dexel segmentlerinde
          sayısal hata birikimi
   Etki: Küçük artık malzeme parçaları "hayalet" olarak kalır
   Çözüm: Periyodik dexel temizliği:
          if segment.height < epsilon → kaldır

8. ÇOK-TAKIMLI SETUP
   Durum: Birden fazla takım aynı anda çalışıyor (twin-spindle)
   Etki: Her takım diğerinin kaldırdığı malzemeyi görmeli
   Çözüm: Paylaşılan (shared) dexel board + senkronizasyon.
          Race condition'a dikkat (mutex/lock-free update).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 5. Yazılım Karşılaştırması

```
VERICUT vs NCSIMUL vs MANUS NC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                  VERICUT          NCSIMUL          MANUS NC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stock Model      Tri-dexel        Tri-dexel +      Dexel
                                  Octree hybrid
Collision        BVH + OBB        BVH + AABB       AABB basit
Kinematic        Tam zincir       Tam zincir       Sınırlı
RTCP             Tam destek       Tam destek       Kısıtlı
G-code Parser    Multi-dialect    Multi-dialect    Fanuc ağırlıklı
GPU Acceleration Kısmi            Var (OpenGL)     Sınırlı
Air-cut Detect   OptiPath modülü  AUTO-DIFF        Manuel analiz
Feed Optimize    OptiPath         Var              Yok
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. Özet: Kritik Tasarım Kararları

```
EN ÖNEMLİ TASARIM KARARLARI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Parser'da AST + Modal State Machine ZORUNLUDUR
   → Satır-satır parsing yetersizdir

2. Kinematik model PARAMETRIK olmalıdır
   → Her makine için ayrı kod yazmak sürdürülemez
   → XML/JSON tabanlı kinematik tanım dosyaları

3. Çarpışma algılamada iki-aşamalı pipeline ZORUNLUDUR
   → Sadece narrow phase → performans felaket
   → Sadece broad phase → false positive çığı

4. Stock model için Tri-Dexel en iyi denge noktasıdır
   → Octree: daha doğru ama yavaş
   → Tek dexel: hızlı ama aliasing sorunlu
   → B-Rep: en doğru ama gerçek zamanlı değil

5. CCD (Continuous Collision Detection) ZORUNLUDUR
   → Rapid hareketlerde tunneling kaçınılmazdır

6. GPU hesaplama ÖNEMLİDİR ama ZORUNLU DEĞİLDİR
   → Dexel board paralelleşmesi doğal
   → Ancak CPU multithreading de yeterli olabilir
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```