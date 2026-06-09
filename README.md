# Astro-Dev Game

**Laporan Teknis dan Pedoman Penggunaan**

| | |
|---|---|
| **Nama** | Devi Putri Sekar Arum |
| **NRP** | 5024241049 |
| **Mata Kuliah** | Pengolahan Citra dan Video (A) |

---

## Deskripsi

Astro-Dev Game adalah game berbasis Python yang dikendalikan sepenuhnya menggunakan gestur tangan melalui webcam. Pemain menggunakan tangan kiri untuk menggerakkan karakter ke kiri/kanan, dan tangan kanan untuk melompat. Karakter harus melompat dan menghancurkan planet serta alien yang jatuh dari atas layar sebelum mereka menyentuh tanah. Game menggunakan teknik pengolahan citra (OpenCV) untuk deteksi dan penghitungan jari secara real-time tanpa library deteksi pose eksternal.

---

## Struktur Repositori

```
Astro-Dev Game/
├── game.py                  # Kode sumber utama (satu file)
├── assets/
│   ├── background.png       # Latar belakang game (langit/ruang angkasa)
│   ├── welcome.png          # Layar selamat datang
│   ├── dev-stay.png         # Sprite karakter diam
│   ├── dev-right.png        # Sprite karakter berjalan ke kanan
│   ├── dev-left.png         # Sprite karakter berjalan ke kiri
│   ├── planet.png           # Spritesheet planet (3x3 grid, 9 varian)
│   ├── alien.png            # Sprite alien
│   ├── explode.png          # Sprite ledakan
│   └── not-ok.wav           # Efek suara
├── venv/                    # Virtual environment Python
│   └── Lib/site-packages/
│       ├── cv2/             # OpenCV 4.13.0.92
│       └── numpy/           # NumPy 2.4.6
└── README.md
```

---

## Tangkapan Layar

> Letakkan tangkapan layar game di direktori `screenshots/` dan referensikan di sini.

```
screenshots/
├── welcome_screen.png
├── gameplay.png
└── game_over.png
```

Contoh:
```markdown
![Welcome Screen](screenshots/welcome_screen.png)
![Gameplay](screenshots/gameplay.png)
![Game Over](screenshots/game_over.png)
```

---

## Tautan Video Demonstrasi


[Tonton Video Demonstrasi](https://youtu.be/LINK_VIDEO_DISINI)

---

## Dependencies

| Library | Versi | Kegunaan |
|---|---|---|
| Python | 3.13 | Runtime bahasa pemrograman |
| opencv-python | 4.13.0.92 | Pembacaan kamera, pengolahan citra, rendering game |
| numpy | 2.4.6 | Operasi array, kalkulasi mask HSV, geometri vektor |
| winsound | bawaan Python (Windows) | Pemutaran efek suara `.wav` (opsional) |
| math | bawaan Python | Kalkulasi trigonometri untuk gerak sinusoidal alien |
| random | bawaan Python | Randomisasi posisi dan kecepatan objek |

---

## Cara Instalasi dan Menjalankan

### Prasyarat

- Python 3.10 atau lebih baru
- Webcam yang terpasang dan berfungsi
- Sistem operasi Windows (untuk fitur suara `winsound`; Linux/Mac tetap bisa dijalankan tanpa suara)

### Langkah Instalasi

**1. Clone atau ekstrak repositori**

```bash
git clone https://github.com/deviputridev/AstroDev-Game.git
cd "astro-dev-game/Astro-Dev Game"
```

**2. Buat virtual environment**

```bash
python -m venv venv
```

**3. Aktifkan virtual environment**

Windows:
```bash
venv\Scripts\activate
```

Linux/macOS:
```bash
source venv/bin/activate
```

**4. Install dependencies**

```bash
pip install opencv-python numpy
```

**5. Jalankan game**

```bash
python game.py
```

Pastikan perintah dijalankan dari dalam direktori `Astro-Dev Game/` agar path aset relatif (`assets/`) terbaca dengan benar.

---

## Cara Kerja

### 1. Alur Program Utama

```
Inisialisasi kamera
      |
Baca frame kamera (30 fps)
      |
Flip horizontal (mirroring)
      |
Ekstrak ROI tangan (35% bawah frame)
      |
Konversi BGR ke HSV
      |
Buat mask warna kulit (HSV range 0-20 dan 160-179)
      |
Morfologi manual: dilate -> erode -> erode -> dilate
      |
Bagi frame menjadi dua zona: KIRI dan KANAN
      |
Temukan kontur terbesar di masing-masing zona
      |
Hitung jari dengan Convex Hull + Convexity Defects
      |
Kirim nilai jari ke GameState.update()
      |
Render game frame + camera panel + mask panel
      |
Tampilkan gabungan ke jendela OpenCV
```

### 2. Deteksi Tangan (HSV Skin Detection)

File `game.py`, fungsi `get_hand_mask()`.

- Frame kamera di-blur dengan Gaussian Blur 5x5 untuk mengurangi noise.
- Dikonversi dari BGR ke ruang warna HSV.
- Dua range warna kulit digunakan: `H:[0,20]` (oranye-merah) dan `H:[160,179]` (merah-magenta), dengan saturasi minimal 30 dan value minimal 60.
- Kedua mask digabungkan menggunakan operasi OR bitwise.
- Diproses dengan morphological operation untuk menutup lubang dan menghilangkan noise.

### 3. Morfologi Manual (Tanpa cv2.morphologyEx)

Fungsi `manual_erode()` dan `manual_dilate()` diimplementasikan secara manual menggunakan perulangan piksel dan `np.pad`, tanpa memanggil `cv2.erode()` atau `cv2.dilate()`. Ini merupakan implementasi dari scratch untuk memenuhi tujuan pembelajaran pengolahan citra.

- **Erode:** piksel bernilai 255 hanya jika seluruh kernel berisi 255 (`np.all`).
- **Dilate:** piksel bernilai 255 jika ada satu saja piksel 255 dalam kernel (`np.any`).
- Urutan operasi: dilate(5) -> erode(5) -> erode(5) -> dilate(5), setara dengan closing lalu opening.

### 4. Penghitungan Jari (Convexity Defects)

Fungsi `count_fingers()`.

- Kontur tangan dianalisis menggunakan `cv2.convexHull()` untuk mendapatkan indeks titik hull.
- `cv2.convexityDefects()` mengembalikan celah antara kontur asli dan hull (defect points).
- Untuk setiap defect, dihitung sudut antara dua sisi jari menggunakan hukum kosinus:

```
cos(angle) = (b^2 + c^2 - a^2) / (2 * b * c)
```

- Defect dihitung sebagai sela jari jika sudut < 90 derajat dan kedalaman defect > 10.000 piksel kuadrat.
- Jumlah sela jari + 1 = jumlah jari (maksimum 5).

### 5. Logika Kontrol Karakter

Fungsi `GameState.update()`.

| Tangan | Jari | Aksi |
|---|---|---|
| Kiri | 1 | Berjalan ke kanan (+5 px/frame) |
| Kiri | 2 | Berjalan ke kiri (-5 px/frame) |
| Kiri | 0 atau 5 | Diam |
| Kanan | 1 | Lompat kecil (`vy = -22`) |
| Kanan | 2 | Lompat sedang (`vy = -44`) |
| Kanan | 3 | Lompat tinggi (`vy = -66`) |
| Kanan | 0 atau 5 | Tidak lompat |

Gravitasi diterapkan setiap frame (`vy += 2`). Karakter berhenti jatuh saat mencapai `GROUND_Y - tinggi_karakter`.

### 6. Sistem Tabrakan (Collision)

Fungsi `check_collision()` dan `GameState.check_collisions()`.

Deteksi tabrakan menggunakan AABB (Axis-Aligned Bounding Box):

```python
ax < bx + bw  AND  ax + aw > bx  AND  ay < by + bh  AND  ay + ah > by
```

- Planet yang diinjak saat karakter melompat: skor +1.
- Alien yang diinjak saat karakter melompat: skor +2.
- Planet/alien yang mencapai `GROUND_Y` tanpa diinjak: nyawa berkurang 1.
- Saat nyawa habis (0 dari 5), game berakhir.

### 7. Sistem Spawn Objek

- Planet muncul setiap ~90 frame (dengan variasi acak +-30 frame), maksimum 4 planet sekaligus.
- Alien muncul setiap 150-200 frame, maksimum 2 alien sekaligus.
- Alien bergerak sinusoidal secara horizontal: `x += sin(frame * 0.05 + offset) * 2`.
- Planet diambil secara acak dari spritesheet 3x3 (9 varian planet berbeda).

### 8. Tampilan Gabungan

Jendela game menampilkan tiga panel secara bersamaan:

```
[ Game Frame 800x800 ] [ Camera Feed 640x240 ]
                        [  HSV Mask   640x240 ]
```

Panel kanan menampilkan feed kamera dan mask HSV dalam ukuran setengah-setengah. Garis horizontal menunjukkan batas ROI tangan. Garis vertikal memisahkan zona kiri dan kanan.

---

## Cara Main

### Layar Selamat Datang

- Tekan **D** untuk memulai permainan.

### Selama Permainan

Letakkan kedua tangan di depan kamera pada bagian bawah frame (zona "HAND ZONE").

| Aksi | Gestur |
|---|---|
| Jalan ke kanan | Tangan KIRI tunjuk 1 jari |
| Jalan ke kiri | Tangan KIRI tunjuk 2 jari |
| Lompat kecil | Tangan KANAN tunjuk 1 jari |
| Lompat sedang | Tangan KANAN tunjuk 2 jari |
| Lompat tinggi | Tangan KANAN tunjuk 3 jari |
| Berhenti/diam | Kepal tangan atau buka penuh (0/5 jari) |
| Keluar game | Tekan tombol **Q** |

### Saat Game Over

- Tekan **R** untuk mengulang permainan dari awal.

### Mekanisme Skor

- Melompat dan menginjak **planet**: +1 poin.
- Melompat dan menginjak **alien**: +2 poin.
- Planet atau alien yang lolos menyentuh tanah: nyawa berkurang 1.
- Total nyawa: 5 (ditampilkan sebagai lingkaran merah di pojok kiri atas).

### Tips

- Gunakan latar belakang polos (dinding putih/gelap) agar deteksi kulit lebih akurat.
- Pastikan pencahayaan cukup dan merata pada tangan.
- Hindari memakai baju berwarna oranye/merah muda agar tidak terbaca sebagai kulit.
- Jauhkan tangan dari muka saat bermain karena deteksi hanya aktif di 65% bawah frame.

---

## Catatan Teknis

- Morfologi manual (`manual_erode`, `manual_dilate`) berjalan lambat pada resolusi penuh karena menggunakan Python loop. Ini disengaja untuk tujuan pembelajaran; pada penggunaan produksi disarankan menggunakan `cv2.morphologyEx`.
- Fitur suara (`winsound`) hanya berfungsi di Windows dan akan diabaikan di sistem lain.
- Game diuji pada Python 3.13, OpenCV 4.13.0.92, NumPy 2.4.6.
- Karakter dapat berpindah melewati batas layar kiri/kanan (wrapping).
