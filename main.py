# ============================================================================
# main.py — FAHH Randomizer Engine v1.6
# ============================================================================
#
# Aplikasi jumpscare stealth yang jalan di Windows System Tray.
# Fitur-fiturnya:
#   - GUI dark mode pake customtkinter (keren kayak Bloomberg terminal)
#   - Random interval audio blast pake file fah.mp3
#   - Volume boost sampe 200% (multi-channel layering biar pecah)
#   - System tray integration (pake pystray, jalan di background)
#   - Multi-threaded RNG countdown engine (GUI ga nge-freeze)
#   - Checkbox buat nampilin countdown timer di GUI
#
# ── CARA COMPILE KE .EXE ────────────────────────────────────────────────────
#
#  1. Install dulu semua library yang dibutuhin:
#       pip install customtkinter pygame-ce pystray Pillow
#
#  2. Compile pake PyInstaller (console hidden, satu file):
#       pyinstaller --noconsole --onefile --add-data "fah.mp3;." main.py
#
#     Hasilnya ada di folder dist/
#     File fah.mp3 udah ke-bundle di dalem .exe nya
#
#  3. Jalanin dist/main.exe — aplikasi muncul dengan GUI.
#     Kalo di-close / minimize, dia masuk ke System Tray.
#     Klik kanan icon tray → "Open Controls" / "Exit Application".
#
# ============================================================================

import os                       #buat akses file system
import sys                      #buat sys.exit
import random                   #buat generate angka random (RNG)
import threading                #buat bikin thread terpisah (biar GUI ga freeze)
import time                     #buat sleep / delay
from typing import Optional     #buat type hint

import customtkinter as ctk     #library GUI dark mode

# ============================================   IMPORT MODUL LOKAL   ============================================
#import dari file yang ada di folder yang sama
from audio_handler import play_sound, stop_audio, init_audio    #fungsi-fungsi audio
from tray_manager import TrayManager                            #kelas system tray


# ============================================   PENGATURAN TAMPILAN   ============================================
ctk.set_appearance_mode("dark")         #set tema gelap biar keren
ctk.set_default_color_theme("dark-blue")#set warna tema biru gelap

# ============================================   KONSTANTA PROGRAM   ============================================
MAX_DELAY_SECONDS = 600         #delay maksimal 10 menit (600 detik)
WINDOW_WIDTH = 420              #lebar jendela GUI
WINDOW_HEIGHT = 420             #tinggi jendela GUI (ditambahin buat checkbox baru)
SLIDER_SENSITIVITY_MIN = 1     #sensitivity paling rendah (jarang bunyi)
SLIDER_SENSITIVITY_MAX = 10    #sensitivity paling tinggi (sering bunyi)
VOLUME_MIN = 0                  #volume minimum 0%
VOLUME_MAX = 200                #volume maximum 200% (boost mode)


# ============================================   KELAS UTAMA APLIKASI   ============================================
class FAHHApp:
    """
    Kelas utama FAHH Randomizer Engine.
    Ngurusin GUI, RNG countdown, dan koneksi ke system tray.
    Intinya ini otak dari seluruh program.
    """

    def __init__(self) -> None:
        # ── Variabel State ──
        self._random_enabled = False    #status random mode (aktif/tidak)
        self._show_countdown = True     #status checkbox countdown (nampilin/engga)
        self._sensitivity: float = 5.0  #nilai sensitivity slider (default 5)
        self._volume_pct: float = 100.0 #nilai volume slider (default 100%)
        self._rng_thread: Optional[threading.Thread] = None     #thread RNG (belum jalan)
        self._stop_event = threading.Event()    #event buat stop thread RNG
        self._running = True            #flag master — kalo False semua berhenti

        # ── Inisialisasi Audio ──
        init_audio()                    #nyalain mixer pygame

        # ── Bangun GUI ──
        self._build_window()            #bikin semua widget di jendela

        # ── System Tray ──
        self._tray = TrayManager(       #bikin manajer tray
            on_open=self._tray_open,    #callback pas klik "Open Controls"
            on_exit=self._tray_exit,    #callback pas klik "Exit Application"
        )
        self._tray.start()              #jalanin tray di background thread

        # ── Auto-Start: setel sekali dulu, baru mulai RNG dan sembunyi ke tray ──
        self._random_var.set(True)      #centang checkbox random otomatis
        self._random_enabled = True     #set state random ke aktif
        play_sound(self._volume_pct)    #SETEL DULU SEKALI langsung pas buka — biar tau udah jalan
        self._start_rng_loop()          #abis itu baru jalanin RNG countdown
        self._set_status("▶  Armed — Countdown berjalan …")
        self.root.after(500, self.root.withdraw)  #sembunyi ke tray setelah 500ms (biar GUI sempet ke-init)

    # ============================================   PROSEDUR BANGUN GUI   ============================================
    def _build_window(self) -> None:
        """Bikin jendela utama dan semua widget di dalamnya."""
        self.root = ctk.CTk()                                   #bikin jendela utama
        self.root.title("FAHH Randomizer Engine")               #judul jendela
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")   #ukuran jendela
        self.root.resizable(False, False)                        #ga bisa di-resize
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)  #override tombol X

        #coba hapus icon default Windows (ga penting kalo gagal)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # ── Frame kontainer utama dengan padding ──
        frame = ctk.CTkFrame(self.root, corner_radius=12)       #bikin frame rounded
        frame.pack(padx=16, pady=16, fill="both", expand=True)  #taro di tengah

        # ── Judul ──
        title = ctk.CTkLabel(                                   #label judul besar
            frame,
            text="FAHH Randomizer Controls",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
        )
        title.pack(pady=(18, 10))                               #spacing atas bawah

        # ── Checkbox Random Mode ──
        self._random_var = ctk.BooleanVar(value=False)          #variabel boolean buat checkbox
        self._chk_random = ctk.CTkCheckBox(                     #bikin checkbox
            frame,
            text="Enable Random Interval",                      #label checkbox
            variable=self._random_var,                          #terhubung ke variabel
            onvalue=True,                                       #kalo dicentang = True
            offvalue=False,                                     #kalo ga dicentang = False
            command=self._toggle_random,                        #fungsi yang dipanggil pas diklik
            font=ctk.CTkFont(size=14),
            corner_radius=6,
        )
        self._chk_random.pack(pady=(6, 6))                      #taro di GUI

        # ── Checkbox Show Countdown ──
        self._countdown_var = ctk.BooleanVar(value=True)        #default nyala (nampilin countdown)
        self._chk_countdown = ctk.CTkCheckBox(                  #bikin checkbox kedua
            frame,
            text="Tampilkan Countdown",                         #label dalam bahasa Indonesia
            variable=self._countdown_var,                       #terhubung ke variabel
            onvalue=True,                                       #kalo dicentang = nampilin
            offvalue=False,                                     #kalo ga dicentang = sembunyiin
            command=self._toggle_countdown,                     #fungsi yang dipanggil pas diklik
            font=ctk.CTkFont(size=14),
            corner_radius=6,
        )
        self._chk_countdown.pack(pady=(2, 14))                  #taro di bawah checkbox random

        # ── Slider Sensitivity (Kecepatan Interval) ──
        lbl_sens = ctk.CTkLabel(                                #label penjelasan slider
            frame,
            text="Interval Speed (1 = Jarang ↔ 10 = Sering)",
            font=ctk.CTkFont(size=12),
        )
        lbl_sens.pack()

        self._slider_sens = ctk.CTkSlider(                      #bikin slider sensitivity
            frame,
            from_=SLIDER_SENSITIVITY_MIN,                        #nilai minimum
            to=SLIDER_SENSITIVITY_MAX,                           #nilai maximum
            number_of_steps=9,                                   #9 langkah (1 sampe 10)
            command=self._on_sensitivity_change,                 #callback pas digeser
            width=300,
        )
        self._slider_sens.set(self._sensitivity)                 #set ke default (5)
        self._slider_sens.pack(pady=(2, 4))

        self._lbl_sens_val = ctk.CTkLabel(                       #label nilai sensitivity
            frame, text=f"Sensitivity: {int(self._sensitivity)}", font=ctk.CTkFont(size=11)
        )
        self._lbl_sens_val.pack(pady=(0, 12))

        # ── Slider Volume Boost ──
        lbl_vol = ctk.CTkLabel(                                  #label penjelasan slider volume
            frame,
            text="Volume Level (0 % – 200 %)",
            font=ctk.CTkFont(size=12),
        )
        lbl_vol.pack()

        self._slider_vol = ctk.CTkSlider(                        #bikin slider volume
            frame,
            from_=VOLUME_MIN,                                    #minimum 0
            to=VOLUME_MAX,                                       #maximum 200
            number_of_steps=40,                                  #40 langkah (tiap 5%)
            command=self._on_volume_change,                      #callback pas digeser
            width=300,
        )
        self._slider_vol.set(self._volume_pct)                   #set ke default (100%)
        self._slider_vol.pack(pady=(2, 4))

        self._lbl_vol_val = ctk.CTkLabel(                        #label nilai volume
            frame, text=f"Volume: {int(self._volume_pct)} %", font=ctk.CTkFont(size=11)
        )
        self._lbl_vol_val.pack(pady=(0, 6))

        # ── Tombol Test Sound ──
        self._btn_test = ctk.CTkButton(                          #tombol merah buat test suara
            frame,
            text="🔊  Test Sound",
            command=self._test_sound,                            #langsung muter suara pas diklik
            font=ctk.CTkFont(size=13, weight="bold"),
            height=32,
            width=180,
            corner_radius=8,
            fg_color="#c0392b",                                  #warna merah
            hover_color="#e74c3c",                                #warna merah terang pas hover
        )
        self._btn_test.pack(pady=(6, 8))

        # ── Label Status / Countdown ──
        self._lbl_status = ctk.CTkLabel(                         #label status di bawah
            frame,
            text="⏸  Idle — Random mode MATI",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#888888",                                #warna abu-abu
        )
        self._lbl_status.pack(pady=(4, 8))                       #taro di paling bawah

    # ============================================   CALLBACK SLIDER   ============================================
    def _on_sensitivity_change(self, value: float) -> None:
        """Dipanggil tiap kali slider sensitivity digeser."""
        self._sensitivity = value                                #update nilai sensitivity
        self._lbl_sens_val.configure(text=f"Sensitivity: {int(value)}")  #update label

    def _on_volume_change(self, value: float) -> None:
        """Dipanggil tiap kali slider volume digeser."""
        self._volume_pct = value                                 #update nilai volume
        self._lbl_vol_val.configure(text=f"Volume: {int(value)} %")     #update label

    # ============================================   PROSEDUR TEST SOUND   ============================================
    def _test_sound(self) -> None:
        """Langsung muter suara sekarang juga buat ngetes (ga perlu nunggu RNG)."""
        self._set_status("🔊  FAHH! Testing sekarang …")        #update status
        threading.Thread(                                        #jalanin di thread biar GUI ga freeze
            target=play_sound, args=(self._volume_pct,), daemon=True
        ).start()

    # ============================================   TOGGLE RANDOM MODE   ============================================
    def _toggle_random(self) -> None:
        """Dipanggil pas checkbox random mode diklik."""
        self._random_enabled = self._random_var.get()            #ambil nilai checkbox
        if self._random_enabled:                                 #kalo dicentang
            self._start_rng_loop()                               #mulai loop RNG
            self._set_status("▶  Armed — Countdown berjalan …")
        else:                                                    #kalo ga dicentang
            self._stop_rng_loop()                                #stop loop RNG
            self._set_status("⏸  Idle — Random mode MATI")

    # ============================================   TOGGLE COUNTDOWN   ============================================
    def _toggle_countdown(self) -> None:
        """Dipanggil pas checkbox countdown diklik."""
        self._show_countdown = self._countdown_var.get()         #ambil nilai checkbox

        if not self._show_countdown:                             #kalo ga dicentang
            #sembunyiin countdown — ganti status jadi teks biasa
            if self._random_enabled:                             #kalo random mode aktif
                self._set_status("▶  Armed — Countdown disembunyikan") 
            else:
                self._set_status("⏸  Idle — Random mode MATI")

    def _set_status(self, text: str) -> None:
        """Update label status (thread-safe, bisa dipanggil dari thread mana aja)."""
        try:
            self._lbl_status.configure(text=text)                #ganti teks label
        except Exception:                                        #kalo widget udah di-destroy ya udah
            pass

    # ============================================   PROSEDUR START RNG   ============================================
    def _start_rng_loop(self) -> None:
        """Mulai background thread buat RNG countdown."""
        self._stop_rng_loop()                   #matiin thread lama kalo ada
        self._stop_event.clear()                #reset event stop
        self._rng_thread = threading.Thread(target=self._rng_worker, daemon=True)    #bikin thread baru
        self._rng_thread.start()                #jalanin thread

    def _stop_rng_loop(self) -> None:
        """Stop background thread RNG."""
        self._stop_event.set()                  #kasih sinyal stop ke thread
        if self._rng_thread is not None:        #kalo ada thread yang jalan
            self._rng_thread.join(timeout=2.0)  #tunggu max 2 detik biar selesai
            self._rng_thread = None             #bersihin referensi

    # ============================================   WORKER RNG (BACKGROUND THREAD)   ============================================
    def _rng_worker(self) -> None:
        """
        Worker yang jalan di background thread.
        Dia ngitung mundur terus muter suara pas countdown habis.
        
        Rumus delay: random.randint(0, int(600 / sensitivity))
        Makin tinggi sensitivity → delay makin pendek → makin sering bunyi.
        """
        while not self._stop_event.is_set() and self._running:  #selama belum di-stop
            sensitivity = max(1.0, self._sensitivity)            #ambil sensitivity (minimal 1)
            max_delay = int(MAX_DELAY_SECONDS / sensitivity)     #hitung delay maksimal
            delay = random.randint(0, max(0, max_delay))         #random delay dari 0 sampe max

            # ── Countdown Loop ──
            #loop countdown per 0.5 detik (interruptible — bisa di-stop kapan aja)
            remaining = delay                                    #sisa waktu countdown
            while remaining > 0 and not self._stop_event.is_set():
                #update status countdown kalo checkbox dicentang
                if self._show_countdown:                         #kalo user mau liat countdown
                    menit = int(remaining) // 60                 #hitung menit
                    detik = int(remaining) % 60                  #hitung detik
                    countdown_text = f"⏳  Countdown: {menit:02d}:{detik:02d}"  #format MM:SS
                    try:
                        self.root.after(0, self._set_status, countdown_text) #update GUI dari thread
                    except Exception:
                        pass
                else:                                            #kalo ga mau liat countdown
                    try:
                        self.root.after(0, self._set_status, "▶  Armed — Countdown disembunyikan")
                    except Exception:
                        pass

                time.sleep(0.5)                                  #tidur 0.5 detik
                remaining -= 0.5                                 #kurangin sisa waktu

            if self._stop_event.is_set():                        #kalo di-stop di tengah countdown
                break                                            #keluar dari loop utama

            # ── BUNYI! FAHH! ──
            try:
                self.root.after(0, self._set_status, "🔊  FAHH! Bunyi sekarang …")
            except Exception:
                pass

            play_sound(self._volume_pct)                         #muter suara fahh

            time.sleep(1.0)                                      #cooldown 1 detik sebelum cycle berikutnya

    # ============================================   PROSEDUR WINDOW HIDE / TRAY   ============================================
    def _on_close(self) -> None:
        """Dipanggil pas user klik X atau Alt-F4 — sembunyiin ke tray, jangan quit."""
        self.root.withdraw()                    #sembunyiin jendela (masih jalan di background)

    def _tray_open(self) -> None:
        """Balikin GUI dari tray (dipanggil dari thread tray)."""
        self.root.after(0, self.root.deiconify) #tampilin ulang jendela dari main thread

    def _tray_exit(self) -> None:
        """Full shutdown — dipanggil dari menu tray "Exit Application"."""
        self._running = False                   #set flag master ke False
        self._stop_rng_loop()                   #stop thread RNG
        stop_audio()                            #stop semua suara
        self._tray.stop()                       #hapus icon tray
        self.root.after(0, self._destroy)       #destroy GUI dari main thread

    def _destroy(self) -> None:
        """Hancurin jendela dan keluar dari program."""
        try:
            self.root.destroy()                 #hancurin jendela tkinter
        except Exception:
            pass
        sys.exit(0)                             #keluar dari program sepenuhnya

    # ============================================   MAIN LOOP   ============================================
    def run(self) -> None:
        """Jalanin main loop GUI — program jalan sampe user exit."""
        self.root.mainloop()                    #ini blocking sampe jendela di-destroy


# ============================================   INTI PROGRAM   ============================================
if __name__ == "__main__":
    app = FAHHApp()     #bikin instance aplikasi
    app.run()           #jalanin — program mulai dari sini
# ============================================   INTI PROGRAM   ============================================
