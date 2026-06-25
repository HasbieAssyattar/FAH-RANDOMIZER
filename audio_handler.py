# ============================================================================
# audio_handler.py — FAHH Randomizer Engine: Modul Pemutaran Audio
# ============================================================================
# Modul ini ngurusin pemutaran file fah.mp3 dengan volume sampe 200%.
#
# Cara kerjanya:
#   - Pake pygame.mixer.music buat muter MP3 (ini yang paling reliable)
#   - Kalo volume di atas 100%, dia nge-layer beberapa Sound object
#     bareng-bareng biar suaranya pecah kayak "ear-rape"
#   - File MP3 di-cache jadi WAV waktu init biar layering boost nya jalan
# ============================================================================

import io                       #buat handle byte stream
import os                       #buat akses file system
import threading                #buat thread-safe init

import pygame                   #library audio utama


# ============================================   KONFIGURASI PATH   ============================================
#ambil path folder tempat script ini berada
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILE = os.path.join(_SCRIPT_DIR, "fah.mp3")  #path ke file suara fahh

# ============================================   KONFIGURASI BOOST   ============================================
_MAX_LAYERS = 4                 #maksimal 4 layer suara bareng buat boost mode (200%)

# ============================================   CACHE VARIABEL   ============================================
_cached_sound: pygame.mixer.Sound | None = None     #cache Sound object biar ga load ulang terus
_init_lock = threading.Lock()   #lock biar init ga tabrakan antar thread


# ============================================   PROSEDUR INIT AUDIO   ============================================
def init_audio() -> None:
    """Inisialisasi mixer pygame satu kali doang, terus cache suaranya."""
    global _cached_sound

    with _init_lock:                    #pake lock biar thread-safe
        if not pygame.mixer.get_init(): #kalo belum di-init
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024) #init mixer
            pygame.mixer.set_num_channels(_MAX_LAYERS + 2)  #set jumlah channel buat layering

        #pre-convert MP3 ke Sound object buat boost mode
        if _cached_sound is None and os.path.isfile(AUDIO_FILE):    #kalo belum di-cache dan file ada
            try:
                _cached_sound = _load_as_sound(AUDIO_FILE)          #coba load dan cache
            except Exception as exc:                                #kalo gagal ya udah
                print(f"[AUDIO WARN] Gagal cache WAV buat boost mode: {exc}")
                _cached_sound = None


# ============================================   FUNGSI LOAD SOUND   ============================================
def _load_as_sound(filepath: str) -> pygame.mixer.Sound:
    """
    Load file MP3 jadi Sound object buat bisa di-layer.
    Pertama coba langsung load, kalo gagal pake fallback byte stream.
    """
    #coba load langsung — pygame-ce (SDL_mixer 2.x) kadang bisa load MP3 ke Sound
    try:
        snd = pygame.mixer.Sound(filepath)          #coba load langsung
        if snd.get_length() > 0.05:                 #cek apakah beneran ke-load (bukan kosong)
            return snd                              #kalo oke langsung return
    except Exception:                               #kalo gagal ya lanjut ke fallback
        pass

    #fallback: load file sebagai raw bytes terus masukin ke Sound
    with open(filepath, "rb") as f:                 #buka file sebagai binary
        raw = f.read()                              #baca semua isinya
    snd = pygame.mixer.Sound(buffer=io.BytesIO(raw).read())  #masukin ke Sound dari bytes
    return snd                                      #balikin Sound objectnya


# ============================================   PROSEDUR PLAY SOUND   ============================================
def play_sound(volume_pct: float) -> None:
    """
    Muter fah.mp3 sesuai volume yang diset (0-200%).
    
    Cara kerjanya:
    - 0-100%  : pake mixer.music biasa, volume linear 0.0 - 1.0
    - 101-200% : music di volume full + layer Sound object di atasnya
                 biar suaranya pecah dan blown-out (boost mode)
    """
    init_audio()                                    #pastiin mixer udah ready

    if not os.path.isfile(AUDIO_FILE):              #cek file ada ga
        print(f"[AUDIO ERROR] File ga ketemu: {AUDIO_FILE}")
        return

    volume_pct = max(0.0, min(200.0, volume_pct))   #clamp ke 0-200 biar aman

    if volume_pct <= 100.0:
        # ── Mode Normal — pake mixer.music (paling reliable buat MP3) ──
        try:
            pygame.mixer.music.load(AUDIO_FILE)             #load file MP3
            pygame.mixer.music.set_volume(volume_pct / 100.0)  #set volume 0.0-1.0
            pygame.mixer.music.play()                       #muter suaranya
        except Exception as exc:                            #kalo gagal print error
            print(f"[AUDIO ERROR] music.play gagal: {exc}")
    else:
        # ── BOOST MODE — layer banyak suara biar pecah ──
        #layer pertama: music channel di volume full
        try:
            pygame.mixer.music.load(AUDIO_FILE)             #load file MP3
            pygame.mixer.music.set_volume(1.0)              #volume mentok
            pygame.mixer.music.play()                       #muter
        except Exception as exc:
            print(f"[AUDIO ERROR] music.play gagal: {exc}")

        #layer tambahan: overlay Sound object biar makin kenceng dan pecah
        if _cached_sound is not None:                       #kalo ada cache Sound
            extra_ratio = (volume_pct - 100.0) / 100.0      #hitung rasio boost (0.0 - 1.0)
            num_layers = 1 + int(extra_ratio * (_MAX_LAYERS - 1))  #hitung jumlah layer (1-4)
            num_layers = min(num_layers, _MAX_LAYERS)       #batasin biar ga kebanyakan

            for i in range(num_layers):                     #loop per layer
                try:
                    channel = pygame.mixer.Channel(i)       #ambil channel ke-i
                    _cached_sound.set_volume(1.0)           #volume full tiap layer
                    channel.play(_cached_sound)             #muter di channel itu
                except Exception:                           #kalo gagal ya skip aja
                    pass


# ============================================   PROSEDUR STOP AUDIO   ============================================
def stop_audio() -> None:
    """Berenti muterr semua suara dan matiin mixer."""
    if pygame.mixer.get_init():                     #kalo mixer lagi aktif
        pygame.mixer.music.stop()                   #stop music channel
        pygame.mixer.stop()                         #stop semua Sound channel
        pygame.mixer.quit()                         #matiin mixer sepenuhnya
