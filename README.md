# Astro-Dev Game

**Laporan Teknis dan Pedoman Penggunaan**

| **Nama** | Devi Putri Sekar Arum |
| **NRP** | 5024241049 |
| **Kelas** | Semester Genap 2025/2026 |
| **Mata Kuliah** | Pengolahan Citra dan Video |

---

## Daftar Isi

1. [Deskripsi Game](#1-deskripsi-game)
2. [Fitur Game](#2-fitur-game)
3. [Tools yang Digunakan](#3-tools-yang-digunakan)
4. [Alur Program](#4-alur-program)
5. [Implementasi Teknis](#5-implementasi-teknis)
6. [Cara Menjalankan](#6-cara-menjalankan)
7. [Dokumentasi Aset](#7-dokumentasi-aset)
8. [Demo Video](#8-demo-video)
9. [Struktur Direktori](#9-struktur-direktori)

---

## 1. Deskripsi Game

**Astro-Dev** adalah game aksi berbasis Python yang dikendalikan sepenuhnya melalui gestur tangan menggunakan webcam, tanpa keyboard maupun mouse sebagai input permainan. Pemain berperan sebagai AstroDev, seorang astronot perempuan yang menjaga planetnya bersama **5 kucing penjaga berbaju antariksa** dari serangan dua ancaman: planet-planet asing yang berjatuhan dari luar angkasa, dan alien kucing hijau bernama *Glorb* yang mengendarai piring terbang. Setiap objek yang lolos menyentuh tanah akan mengurangi satu nyawa dari total 5 nyawa yang diwakili oleh indikator lingkaran merah di sudut kiri atas layar.

Kontrol game sepenuhnya bergantung pada teknik **HSV-based skin color segmentation** dan **Convexity Defects finger counting** yang diimplementasikan menggunakan OpenCV. Tangan kiri mengontrol arah gerak horizontal karakter, sementara tangan kanan mengontrol ketinggian lompatan. Tidak ada library deteksi pose (seperti MediaPipe) yang digunakan; semua pipeline deteksi tangan dibangun dari primitif OpenCV dan NumPy.

---

## 2. Fitur Game

**Kontrol berbasis gestur tangan real-time**
Deteksi dilakukan pada setiap frame kamera (~30 fps) tanpa buffering atau delay tambahan. Karakter merespons perubahan jumlah jari yang ditampilkan secara langsung.

**Dua jenis musuh dengan perilaku berbeda**
Planet jatuh secara vertikal lurus dengan kecepatan acak antara 2 sampai 5 piksel per frame. Alien bergerak secara sinusoidal pada sumbu horizontal sambil turun, sehingga lintasannya tidak dapat diprediksi secara linier.

**Sistem lompatan bertingkat tiga level**
Ketinggian lompatan ditentukan oleh jumlah jari yang ditampilkan tangan kanan. Satu jari menghasilkan lompatan dengan kecepatan awal vertikal -22 piksel/frame, dua jari -44 piksel/frame, dan tiga jari -66 piksel/frame. Gravitasi konstan 2 piksel/frame^2 diterapkan setiap frame.

**Sistem skor berbasis nilai objek**
Planet bernilai 1 poin, alien bernilai 2 poin. Teks skor mengambang (+1 atau +2) muncul di posisi objek yang dihancurkan lalu memudar dalam 30 frame.

**Tampilan debug tiga panel simultan**
Jendela game menampilkan frame permainan (800x800), feed kamera langsung (640x240), dan visualisasi mask HSV (640x240) secara bersamaan dalam satu jendela OpenCV berukuran 1440x800.

**Morfologi manual tanpa cv2.morphologyEx**
Fungsi erode dan dilate diimplementasikan dari nol menggunakan Python loop dan operasi array NumPy, bukan memanggil fungsi morfologi bawaan OpenCV.

---

## 3. Tools yang Digunakan

| Komponen | Versi | Peran dalam Proyek |
|---|---|---|
| Python | 3.13 | Runtime utama |
| opencv-python | 4.13.0.92 | Akuisisi kamera, konversi ruang warna, deteksi kontur, rendering teks dan bentuk geometri, penampilanframe |
| numpy | 2.4.6 | Representasi array gambar, operasi mask HSV berbasis boolean, kalkulasi vektor untuk penghitungan jari, padding morfologi manual |
| math (stdlib) | bawaan | Fungsi `sin()` untuk gerak sinusoidal alien, `pi` untuk inisialisasi offset drift acak |
| random (stdlib) | bawaan | Randomisasi posisi spawn, kecepatan objek, interval spawn, dan indeks planet dari spritesheet |
| winsound (stdlib) | bawaan Windows | Pemutaran efek suara `.wav` secara asinkron saat game dimulai (hanya Windows) |

**Alasan tidak menggunakan MediaPipe atau library deteksi pose lain:**
Proyek ini sengaja membangun pipeline deteksi tangan dari primitif pengolahan citra sebagai implementasi kompetensi mata kuliah Pengolahan Citra dan Video. Seluruh proses dari segmentasi warna, morfologi, pencarian kontur, hingga analisis geometri convex hull dilakukan secara eksplisit.

---

## 4. Alur Program

```
INISIALISASI
  Muat semua aset (gambar, background, spritesheet)
  Buka kamera (cv2.VideoCapture(0))
  Buat objek GameState
  Tampilkan layar welcome

LOOP UTAMA (per frame)
  |
  +-- Baca frame kamera
  |     cap.read() -> ret, frame
  |
  +-- PRE-PROCESSING FRAME
  |     flip horizontal (mirroring agar tidak terbalik)
  |     resize ke 640x480
  |
  +-- PIPELINE DETEKSI TANGAN
  |     get_hand_mask(frame)
  |       - potong ROI: 35% bawah frame (y >= 168px dari atas)
  |       - GaussianBlur 5x5
  |       - BGR -> HSV
  |       - buat mask1: H[0,20], S[30,255], V[60,255]
  |       - buat mask2: H[160,179], S[30,255], V[60,255]
  |       - gabung: combined = mask1 OR mask2
  |       - morfologi: dilate(5) -> erode(5) -> erode(5) -> dilate(5)
  |       - kembalikan full_mask dan roi_y
  |
  +-- SEGMENTASI ZONA
  |     zona kiri  : x = [0, 320)
  |     zona kanan : x = [320, 640)
  |     get_largest_contour_in_region() untuk masing-masing zona
  |
  +-- PENGHITUNGAN JARI
  |     count_fingers(contour)
  |       - konveks hull (returnPoints=False)
  |       - convexityDefects
  |       - filter defect: sudut < 90 derajat DAN kedalaman > 10000
  |       - return min(jumlah_defect + 1, 5)
  |
  +-- UPDATE LOGIKA GAME
  |     GameState.update(left_fingers, right_fingers)
  |       - gerak horizontal karakter
  |       - fisika lompatan (vy += GRAVITY)
  |       - spawn planet dan alien berdasarkan timer
  |       - update posisi semua objek
  |       - check_collisions()
  |       - hapus objek mati
  |
  +-- RENDER
  |     GameState.draw() -> game_frame (800x800)
  |     anotasi cam_view dan mask_bgr
  |     build_combined_display() -> gabungkan tiga panel
  |     cv2.imshow()
  |
  +-- INPUT KEYBOARD
        'q' -> keluar
        'd' -> mulai game (dari layar welcome)
        'r' -> restart (saat game over)
```

---

## 5. Implementasi Teknis

### 5.1 Deteksi Warna Kulit (HSV Skin Segmentation)

Fungsi `get_hand_mask()` pada baris 87 hingga 113.

Deteksi tangan menggunakan pendekatan segmentasi warna di ruang warna HSV. Ruang warna HSV dipilih karena komponen Hue memisahkan informasi warna dari intensitas cahaya, sehingga lebih tahan terhadap variasi pencahayaan dibanding segmentasi langsung di ruang BGR.

**Region of Interest (ROI):**
Deteksi hanya dilakukan pada 65% bawah frame kamera (dari `y = frame_height * 0.35` ke bawah). Pembatasan ROI ini menghilangkan gangguan dari wajah dan latar belakang atas, sekaligus mengurangi beban komputasi morfologi manual yang mahal.

**Range warna kulit yang digunakan:**

```python
# Range 1: warna kulit normal (oranye ke kuning)
mask1 = (H >= 0) & (H <= 20) & (S >= 30) & (S <= 255) & (V >= 60) & (V <= 255)

# Range 2: warna kulit dengan hue melingkar di ujung spektrum (merah tua)
mask2 = (H >= 160) & (H <= 179) & (S >= 30) & (S <= 255) & (V >= 60) & (V <= 255)

combined_mask = (mask1 | mask2).astype(np.uint8) * 255
```

Batas bawah saturasi (S >= 30) dan value (V >= 60) mencegah piksel putih, abu-abu, dan hitam ikut terdeteksi sebagai kulit.

**Preprocessing sebelum thresholding:**
Frame ROI di-blur menggunakan Gaussian Blur kernel 5x5 sebelum konversi ke HSV. Ini menghaluskan transisi warna pada tepi kulit sehingga mask yang dihasilkan lebih solid dan tidak berlubang-lubang.

### 5.2 Morfologi Manual

Fungsi `manual_erode()` dan `manual_dilate()` pada baris 68 hingga 85.

Kedua fungsi ini diimplementasikan dari nol tanpa memanggil `cv2.erode()`, `cv2.dilate()`, atau `cv2.morphologyEx()`. Implementasi menggunakan sliding window dengan `np.pad` dan perulangan piksel:

**Erosi:**
```python
def manual_erode(binary_img, kernel_size=5):
    pad = kernel_size // 2
    padded = np.pad(binary_img, pad, mode='constant', constant_values=0)
    output = np.zeros_like(binary_img)
    for y in range(binary_img.shape[0]):
        for x in range(binary_img.shape[1]):
            roi = padded[y:y+kernel_size, x:x+kernel_size]
            if np.all(roi == 255):   # piksel dipertahankan hanya jika seluruh kernel putih
                output[y, x] = 255
    return output
```

**Dilasi:**
```python
def manual_dilate(binary_img, kernel_size=5):
    pad = kernel_size // 2
    padded = np.pad(binary_img, pad, mode='constant', constant_values=0)
    output = np.zeros_like(binary_img)
    for y in range(binary_img.shape[0]):
        for x in range(binary_img.shape[1]):
            roi = padded[y:y+kernel_size, x:x+kernel_size]
            if np.any(roi == 255):   # piksel diset putih jika ada satu saja piksel putih di kernel
                output[y, x] = 255
    return output
```

**Urutan operasi morfologi yang diterapkan:**
```
dilate(5) -> erode(5)    = closing: menutup lubang kecil dalam mask kulit
erode(5)  -> dilate(5)   = opening: menghilangkan noise kecil di luar kontur tangan
```

Empat tahap ini setara dengan `morphologicalClose` diikuti `morphologicalOpen`. Hasilnya adalah mask tangan yang lebih solid dan bersih dari artefak kecil.

**Catatan performa:** Implementasi Python loop berjalan lambat pada resolusi penuh. Pada resolusi 640x480 dengan kernel 5x5, satu operasi morfologi memproses sekitar 307.000 piksel dalam nested loop. Ini merupakan trade-off yang disengaja untuk tujuan pembelajaran; pada aplikasi produksi digunakan `cv2.morphologyEx`.

### 5.3 Penghitungan Jari via Convexity Defects

Fungsi `count_fingers()` pada baris 122 hingga 145.

Penghitungan jari menggunakan analisis geometri **Convex Hull** dan **Convexity Defects**. Convex hull adalah poligon terkecil yang membungkus seluruh kontur tangan. Titik-titik di kontur tangan yang berada di dalam hull (terutama di celah antar jari) disebut defect point.

**Algoritma:**

```
1. Hitung convex hull dari kontur tangan (returnPoints=False -> kembalikan indeks)
2. Hitung convexity defects dari kontur dan hull
3. Untuk setiap defect (start, end, far, depth):
   - start: titik ujung jari pertama
   - end  : titik ujung jari berikutnya
   - far  : titik terdalam di celah antar dua jari tersebut
   - depth: kedalaman defect dalam piksel^2 (nilai mentah / 256 = piksel)

4. Hitung panjang sisi segitiga (start-far-end):
   a = jarak(end, start)
   b = jarak(far, start)
   c = jarak(end, far)

5. Hitung sudut di titik far menggunakan hukum kosinus:
   cos(angle) = (b^2 + c^2 - a^2) / (2 * b * c)

6. Defect dihitung sebagai celah jari jika:
   - angle < 90 derajat (sudut lancip = celah jari yang valid)
   - depth > 10000 (untuk menghilangkan defect kecil dari noise)

7. Jumlah jari = jumlah defect valid + 1
   (karena n celah antar jari = n+1 jari)
   Maksimum dikembalikan 5.
```

**Threshold yang digunakan:**
Nilai `angle < 90` dipilih karena celah antar jari yang benar-benar terbuka membentuk sudut lancip. Jari yang merapat atau setengah terbuka menghasilkan sudut tumpul dan tidak ikut dihitung. Nilai `depth > 10000` (setara sekitar 100 piksel) memfilter defect yang sangat dangkal akibat ketidaksempurnaan kontur.

### 5.4 Segmentasi Zona Tangan Kiri/Kanan

Fungsi `get_largest_contour_in_region()` pada baris 116 hingga 120.

Frame kamera dibagi menjadi dua zona vertikal: zona kiri (`x < 320`) dan zona kanan (`x >= 320`). Untuk setiap zona, dicari kontur dengan luas terbesar yang centroid-nya (`M10/M00`) berada di dalam batas zona dan luasnya melebihi `MIN_HAND_AREA = 5000` piksel persegi. Filter luas minimum ini mencegah kontur kecil dari noise atau pantulan cahaya ikut terdeteksi sebagai tangan.

### 5.5 Fisika Karakter

Fungsi `GameState.update()` mulai baris 213.

Karakter menggunakan model fisika kinematika sederhana berbasis frame:

```
Setiap frame:
  vy += GRAVITY          # GRAVITY = 2 piksel/frame^2
  y  += vy

Saat melompat (trigger dari tangan kanan):
  vy = JUMP_FORCE * right_fingers   # JUMP_FORCE = -22

Kondisi landing:
  if y >= GROUND_Y - char_height:
    y  = GROUND_Y - char_height
    vy = 0
    is_jumping = False
```

Kecepatan awal lompatan negatif (ke atas dalam koordinat layar). Gravitasi positif menarik karakter kembali ke bawah. Karakter hanya bisa melompat kembali setelah `is_jumping == False`, yaitu setelah menyentuh lantai.

**Ketinggian lompatan berdasarkan jumlah jari:**

| Jari Kanan | vy Awal | Ketinggian Maksimum |
|---|---|---|
| 1 | -22 piksel/frame | ~121 piksel di atas lantai |
| 2 | -44 piksel/frame | ~484 piksel di atas lantai |
| 3 | -66 piksel/frame | ~1089 piksel (melewati batas layar atas) |

Ketinggian teoritis dihitung dari `h = vy^2 / (2 * GRAVITY)`.

### 5.6 Deteksi Tabrakan (AABB Collision Detection)

Fungsi `check_collision()` baris 148 dan `GameState.check_collisions()` baris 270.

Tabrakan menggunakan metode **Axis-Aligned Bounding Box (AABB)**:

```python
def check_collision(ax, ay, aw, ah, bx, by, bw, bh):
    return (ax < bx + bw and ax + aw > bx and
            ay < by + bh and ay + ah > by)
```

Dua kondisi diperiksa secara berurutan untuk setiap objek aktif:

1. **Objek menyentuh lantai:** `obj.y + obj.h >= GROUND_Y` -> kurangi nyawa, set `obj.dead = True`
2. **Karakter menyentuh objek sambil melompat:** `is_jumping == True` AND `check_collision(...)` -> tambah skor, panggil `obj.hit()`, set `vy = -8` (bouncing kecil)

Pengecekan tabrakan dengan injakan hanya valid saat `is_jumping == True`. Ini berarti karakter yang menyentuh objek dari samping atau saat berdiri di tanah tidak mengaktifkan penghancuran objek.

### 5.7 Sistem Spawn Objek

Planet di-spawn oleh `spawn_timer` dengan interval awal 90 frame, diacak ±30 frame setelah setiap spawn. Alien di-spawn oleh `alien_timer` dengan interval acak antara 150 dan 200 frame. Batas maksimum objek aktif pada layar: 4 planet (`MAX_PLANETS`) dan 2 alien (`MAX_ALIENS`).

**Gerak sinusoidal alien:**
```python
self.x += math.sin(self.frame_count * 0.05 + self.drift_offset) * 2
```
Parameter `0.05` menentukan frekuensi osilasi (satu siklus penuh setiap ~126 frame). Amplitudo 2 piksel per frame menghasilkan pergeseran horizontal maksimum sekitar ±40 piksel dari posisi spawn. `drift_offset` yang diacak antara 0 dan 2*pi memastikan setiap alien memiliki fase awal yang berbeda, sehingga tidak semua alien bergerak ke arah yang sama secara bersamaan.

### 5.8 Rendering Sprite dengan Alpha Blending

Fungsi `overlay_sprite()` baris 56 hingga 71.

Semua aset dimuat dengan channel alpha (BGRA). Rendering menggunakan alpha compositing manual:

```python
alpha   = sp_crop[:, :, 3:4].astype(np.float32) / 255.0
fg      = sp_crop[:, :, :3].astype(np.float32)
bg      = fr_crop.astype(np.float32)
blended = (alpha * fg + (1 - alpha) * bg).astype(np.uint8)
```

Formula ini adalah **Porter-Duff "over" compositing**. Piksel transparan (alpha=0) menghasilkan latar belakang murni, piksel opak (alpha=255) menghasilkan sprite murni, dan piksel semi-transparan menghasilkan campuran proporsional. Ini memungkinkan sprite dengan bentuk tidak persegi (seperti alien dan ledakan) ditampilkan tanpa kotak putih di sekelilingnya.

Fungsi juga menangani kasus **clipping** di tepi layar: jika sprite sebagian keluar batas frame, hanya bagian yang tumpang tindih dengan frame yang dihitung dan di-render.

### 5.9 Slicing Spritesheet Planet

Fungsi `slice_planet_spritesheet()` baris 42 hingga 54.

File `planet.png` berisi 9 varian planet dalam grid 3 kolom x 3 baris. Fungsi membagi gambar menjadi 9 sel berdasarkan pembagian dimensi, lalu me-resize setiap sel ke `PLANET_SIZE = 80x80` piksel. Hasilnya adalah list 9 sprite yang diakses secara acak saat setiap planet baru di-spawn.

---

## 6. Cara Menjalankan

### Prasyarat

- Python 3.10 atau lebih baru
- Webcam aktif
- Sistem operasi Windows, Linux, atau macOS (fitur suara hanya aktif di Windows)
- Latar belakang polos (disarankan putih atau abu-abu gelap) untuk akurasi deteksi kulit

### Instalasi

```bash
# Clone atau ekstrak repositori
git clone https://github.com/deviputridev/AstroDev-Game.git
cd "AstroDev-Game"

# Buat dan aktifkan virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# Install dependencies
pip install opencv-python numpy

# Jalankan game
python game.py
```

**Penting:** Perintah `python game.py` harus dijalankan dari dalam direktori `Astro-Dev Game/` agar path relatif `assets/` terbaca dengan benar.

### Kontrol

| Tangan | Jumlah Jari | Aksi |
|---|---|---|
| Kiri | 1 jari | Berjalan ke kanan |
| Kiri | 2 jari | Berjalan ke kiri |
| Kiri | 0 atau 5 jari | Berhenti (diam) |
| Kanan | 1 jari | Lompat kecil |
| Kanan | 2 jari | Lompat sedang |
| Kanan | 3 jari | Lompat tinggi |
| Kanan | 0 atau 5 jari | Tidak melompat |
| Keyboard D | - | Mulai game dari layar welcome |
| Keyboard R | - | Restart (saat game over) |
| Keyboard Q | - | Keluar game |

### Mekanisme Skor dan Nyawa

- Melompat dan menginjak planet: **+1 poin**
- Melompat dan menginjak alien: **+2 poin**
- Planet atau alien lolos menyentuh lantai: **-1 nyawa**
- Total nyawa: 5 (ditampilkan sebagai 5 lingkaran merah di pojok kiri atas)
- Nyawa habis: game over, tekan R untuk main lagi

### Tips Bermain

Posisikan tangan 35 cm atau lebih dari kamera di bagian bawah frame. Gunakan cahaya yang merata pada kedua telapak tangan. Hindari pakaian berwarna oranye atau merah muda yang dapat terdeteksi sebagai kulit. Gunakan tangan kiri untuk navigasi horizontal dan tangan kanan untuk melompat secara bersamaan agar bisa mengintersep objek jatuh dari berbagai posisi.

---

## 7. Dokumentasi Aset

Seluruh aset visual dirancang sendiri dengan gaya pixel art dan memiliki filosofi desain yang konsisten: astronot perempuan dengan kucing penjaga sebagai tema utama, palet warna pastel dan cosmic, serta estetika retro pixel art.

---

### 7.1 Layar Welcome (`welcome.png`)

![Welcome Screen](assets/welcome.png)

Layar pembuka game berukuran 1080x1080 piksel yang digabungkan dengan background dalam kode (`cv2.resize(welcome_img, (800, 800))`). Komposisi layar menampilkan AstroDev berdiri di padang bunga lavender bersama keempat kucing penjaga, dengan latar langit pixel art berwarna biru-ungu dan awan oranye-pink. Teks "WELCOME! ASTRO-DEV" menggunakan font pixel bitmap berwarna putih dan biru, tagline berbunyi *"The galaxy won't save itself. Suit up, jump higher, survive the void!"*, dan instruksi "PRESS D TO BEGIN" di tengah layar. Layar welcome merupakan komposit antara background environment yang sama digunakan saat gameplay dengan overlay karakter dalam posisi idle.

---

### 7.2 Background Lingkungan (`background.png`)

![Background](assets/background.png)

Background berukuran asli besar yang di-resize ke 800x800 piksel saat runtime. Menggambarkan lingkungan fantasi berbasis pixel art: padang rumput hijau dengan bunga lavender di foreground, pohon-pohon pinus bergaya pixel art berwarna ungu di midground, pegunungan putih di background, dan langit biru-ungu dengan awan berwarna oranye-pink serta efek aurora borealis dan bintang-bintang bersinar. Palet warna didominasi pastel dingin (ungu, biru, pink) dengan aksen hijau dari vegetasi. Gaya artistik memadukan pixel art presisi untuk elemen dekat dengan lukisan digital yang lebih halus untuk langit, menciptakan kedalaman perspektif yang kuat.

---

### 7.3 Karakter AstroDev: Idle (`dev-stay.png`)

![AstroDev Stay](assets/dev-stay.png)

Sprite idle karakter utama yang ditampilkan saat karakter berdiri diam. AstroDev digambarkan sebagai perempuan berambut hitam panjang mengenakan setelan astronot putih dengan badge label "dev" dan lencana hijau di dada. Ia memegang helm bulat di tangan kiri dan memegang kucing kecil berhelmet di tangan kanan. Di kakinya berdiri **4 kucing penjaga** berhelmet astronot dalam berbagai warna bulu: abu-abu gelap dengan ekspresi tenang, putih dengan bintik hijau, cokelat belang dengan mata biru, dan hitam pekat. Kelima kucing (termasuk satu yang dipegang) bersama AstroDev membentuk unit tim yang merepresentasikan 5 nyawa dalam game.

Di dalam kode, sprite ini dimuat sebagai:
```python
sprites["stay"] = load_sprite("assets/dev-stay.png", width=CHAR_SCALE)  # CHAR_SCALE = 200
```

---

### 7.4 Karakter AstroDev: Bergerak Kanan (`dev-right.png`)

![AstroDev Right](assets/dev-right.png)

Sprite yang aktif saat `left_fingers == 1`. AstroDev ditampilkan dalam pose melayang/berlari dengan badan condong ke depan, kaki terangkat, dan tangan terentang. Keempat kucing penjaga mengambang bebas di sekitarnya: abu-abu (kiri atas), oranye belang (kanan atas), cokelat belang bermata biru (kiri bawah), hitam (kanan bawah). Komposisi ini menggambarkan tim yang bergerak bersama dalam gravitasi mikro. Pose melayang dipilih karena dalam konteks game berlatar luar angkasa, gerak horizontal lebih tepat digambarkan sebagai melayang daripada berlari di tanah.

---

### 7.5 Karakter AstroDev: Bergerak Kiri (`dev-left.png`)

![AstroDev Left](assets/dev-left.png)

Sprite yang aktif saat `left_fingers == 2`. Komposisi hampir identik dengan `dev-right.png` namun karakter menghadap ke kiri. Posisi dan distribusi kucing penjaga di sekitar karakter juga sedikit berbeda, bukan sekadar mirror horizontal, menunjukkan bahwa sprite kiri dan kanan dibuat secara terpisah untuk memberikan nuansa visual yang berbeda. Oranye belang kini di kanan atas, abu-abu di kiri atas, sedangkan formasi bawah mempertahankan cokelat belang dan hitam. Ketiga sprite karakter (stay, left, right) di-swap secara langsung di `GameState.draw()` berdasarkan nilai `self.direction`.

---

### 7.6 Spritesheet Planet (`planet.png`)

![Planet Spritesheet](assets/planet.png)

Spritesheet berisi 9 varian planet/asteroid dalam grid 3x3 yang di-slice secara otomatis oleh fungsi `slice_planet_spritesheet()`:

| Posisi | Deskripsi |
|---|---|
| Baris 1, Col 1 | Komet es biru dengan ekor kristal |
| Baris 1, Col 2 | Planet hijau tua dengan kawah berapi |
| Baris 1, Col 3 | Asteroid merah muda berbentuk tidak beraturan |
| Baris 2, Col 1 | Planet ungu bercincin merah muda |
| Baris 2, Col 2 | Bumi (hijau-biru dengan awan putih) |
| Baris 2, Col 3 | Asteroid merah karang berlekuk |
| Baris 3, Col 1 | Planet kuning-hijau berteknik dengan cincin |
| Baris 3, Col 2 | Bulan abu-biru dengan kawah |
| Baris 3, Col 3 | Lubang hitam dengan piringan kuning emas |

Setiap sel di-resize ke `80x80` piksel. Saat planet baru di-spawn, `self.sprite_idx = random.randint(0, 8)` memilih salah satu dari 9 varian secara acak sehingga pemain melihat variasi visual yang terus berganti.

---

### 7.7 Musuh Alien: Glorb (`alien.png`)

![Alien](assets/alien.png)

Sprite musuh alien berukuran asli besar yang di-resize ke `width=80` piksel saat runtime, dengan tinggi menyesuaikan aspek rasio. Menggambarkan kucing hijau neon dengan antena dan telinga runcing, duduk di dalam piring terbang berbentuk datar. Piring terbang berwarna hijau-abu dengan stiker-stiker kecil: lencana alien, teks "glorb", dan label "CA-TT" (singkat dari cat/kucing dalam bahasa Inggris yang dimodifikasi). Nama karakter alien adalah **Glorb**. Desain ini mempertahankan tema kucing dari karakter utama namun dengan identitas musuh: warna hijau neon menggambarkan alien, piring terbang menggambarkan teknologi extraterrestrial, dan ekspresi mata sipit Glorb memberi kesan antagonis ringan namun tetap menggemaskan.

Di dalam kode, alien bergerak secara sinusoidal:
```python
self.x += math.sin(self.frame_count * 0.05 + self.drift_offset) * 2
```
Nilai musuh ini 2x lebih tinggi dari planet (skor +2) karena lintasan sinusoidal membuatnya lebih sulit untuk diinjak.

---

### 7.8 Efek Ledakan (`explode.png`)

![Explode](assets/explode.png)

Sprite ledakan tunggal berukuran asli yang di-resize ke `110x110` piksel untuk planet dan ke lebar alien untuk Glorb. Menggambarkan ledakan pixel art klasik: inti putih di tengah, cincin oranye, dan percikan merah-kuning yang menyebar ke segala arah. Gaya pixel art yang eksplisit (kotak-kotak piksel terlihat jelas) kontras dengan kehalusan sprite karakter dan alien, sengaja dipilih untuk memberikan feedback visual yang kuat saat objek dihancurkan.

Saat `obj.hit()` dipanggil, `obj.exploding = True` dan sprite ledakan menggantikan sprite objek selama `EXPLODE_DURATION = 20` frame (sekitar 0,67 detik pada 30 fps). Offset posisi diterapkan agar ledakan terpusat pada posisi planet:
```python
offset = (EXPLODE_SIZE - PLANET_SIZE) // 2   # = (110 - 80) // 2 = 15
overlay_sprite(frame, self.explode_sprite, int(self.x) - offset, int(self.y) - offset)
```

---

## 8. Demo Video

> Ganti tautan berikut dengan URL video demonstrasi yang telah diunggah ke YouTube atau platform lain.

[Tonton Video Demonstrasi](https://youtu.be/LINK_VIDEO_DISINI)

Video demonstrasi sebaiknya mencakup:
- Tampilan keseluruhan jendela game (tiga panel: game, kamera, mask)
- Demonstrasi kontrol tangan kiri (1 jari kanan, 2 jari kiri)
- Demonstrasi tiga level lompatan tangan kanan
- Penghancuran planet (skor +1) dan alien Glorb (skor +2)
- Kondisi game over saat nyawa habis
- Restart dengan tombol R

---

## 9. Struktur Direktori

```
Astro-Dev Game/
├── game.py                      # Satu-satunya file kode sumber (580+ baris)
├── README.md                    # Dokumen ini
├── assets/
│   ├── welcome.png              # Layar welcome (1080x1080, pixel art + latar belakang)
│   ├── background.png           # Latar belakang gameplay (pixel art landscape)
│   ├── dev-stay.png             # Sprite karakter: idle + 4 kucing di kaki
│   ├── dev-right.png            # Sprite karakter: bergerak kanan + 4 kucing melayang
│   ├── dev-left.png             # Sprite karakter: bergerak kiri + 4 kucing melayang
│   ├── planet.png               # Spritesheet 3x3: 9 varian planet/asteroid
│   ├── alien.png                # Sprite musuh Glorb si alien kucing hijau
│   ├── explode.png              # Sprite efek ledakan pixel art
│   └── not-ok.wav               # Efek suara (diputar saat game dimulai, Windows only)
└── venv/
    └── Lib/site-packages/
        ├── cv2/                 # OpenCV 4.13.0.92
        └── numpy/               # NumPy 2.4.6
```

**Ringkasan ukuran aset:**

| File | Ukuran |
|---|---|
| not-ok.wav | 36 MB (audio WAV tidak terkompresi) |
| background.png | 4,9 MB |
| dev-right.png | 2,1 MB |
| dev-left.png | 2,0 MB |
| dev-stay.png | 2,1 MB |
| welcome.png | 2,5 MB |
| alien.png | 1,4 MB |
| planet.png | 1,3 MB |
| explode.png | 180 KB |

---

## Lisensi

Proyek ini dibuat untuk keperluan akademis mata kuliah Pengolahan Citra dan Video, Institut Teknologi Sepuluh Nopember (ITS) Surabaya. Seluruh aset visual dirancang sendiri oleh pembuat.