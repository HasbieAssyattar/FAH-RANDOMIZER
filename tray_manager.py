# ============================================================================
# tray_manager.py — FAHH Randomizer Engine: Manajer System Tray
# ============================================================================
# Modul ini ngurusin icon di system tray Windows pake pystray + PIL.
# Jadi pas aplikasi di-minimize dia masuk ke tray, ga ilang.
# Klik kanan icon tray bisa "Open Controls" atau "Exit Application".
# ============================================================================

import sys                      #buat sys.exit
import threading                #buat jalanin tray di thread terpisah
from typing import Callable, Optional   #buat type hint

from PIL import Image, ImageDraw        #buat bikin gambar icon
import pystray                          #library system tray


# ============================================   KELAS TRAY MANAGER   ============================================
class TrayManager:
    """
    Ngurusin icon di Windows System Tray.
    
    Pas di-init dia butuh 2 callback:
    - on_open : dipanggil waktu user klik "Open Controls" di tray
    - on_exit : dipanggil waktu user klik "Exit Application" di tray
    """

    def __init__(self, on_open: Callable, on_exit: Callable) -> None:
        self._on_open = on_open         #simpen callback buat buka GUI
        self._on_exit = on_exit         #simpen callback buat exit aplikasi
        self._icon: Optional[pystray.Icon] = None       #icon tray (belum dibuat)
        self._thread: Optional[threading.Thread] = None #thread tray (belum jalan)

    # ============================================   PROSEDUR BIKIN ICON   ============================================
    @staticmethod
    def _create_icon_image() -> Image.Image:
        """Bikin icon 64x64 pixel: lingkaran merah di background gelap dengan huruf F."""
        size = 64                                       #ukuran icon 64x64
        img = Image.new("RGBA", (size, size), (20, 20, 30, 255))    #background gelap
        draw = ImageDraw.Draw(img)                      #siap-siap gambar

        #gambar lingkaran merah — biar keliatan jelas di tray
        margin = 8                                      #jarak dari pinggir
        draw.ellipse(                                   #bikin lingkaran
            [margin, margin, size - margin, size - margin],
            fill=(220, 40, 40, 255),                    #warna merah
        )

        #gambar huruf "F" di tengah pake kotak-kotak kecil (ga perlu font file)
        draw.rectangle([24, 20, 40, 24], fill=(255, 255, 255, 255))  #garis atas
        draw.rectangle([24, 20, 28, 44], fill=(255, 255, 255, 255))  #garis vertikal
        draw.rectangle([24, 30, 36, 34], fill=(255, 255, 255, 255))  #garis tengah
        return img                                      #balikin gambar iconnya

    # ============================================   PROSEDUR START TRAY   ============================================
    def start(self) -> None:
        """Bikin icon tray dan jalanin di daemon thread (jalan di background)."""
        menu = pystray.Menu(                            #bikin menu klik kanan
            pystray.MenuItem("Open Controls", self._handle_open),    #opsi buka GUI
            pystray.MenuItem("Exit Application", self._handle_exit), #opsi keluar
        )
        self._icon = pystray.Icon(                      #bikin icon tray
            name="FAHH Randomizer",                     #nama internal
            icon=self._create_icon_image(),             #gambar iconnya
            title="FAHH Randomizer Engine",             #tooltip pas hover
            menu=menu,                                  #menu klik kanan
        )
        self._thread = threading.Thread(target=self._icon.run, daemon=True) #bikin thread
        self._thread.start()                            #jalanin thread tray

    # ============================================   PROSEDUR STOP TRAY   ============================================
    def stop(self) -> None:
        """Hapus icon tray dan bersihin resource."""
        if self._icon is not None:                      #kalo icon ada
            self._icon.stop()                           #stop dan hapus dari tray

    # ============================================   HANDLER INTERNAL   ============================================
    def _handle_open(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Dipanggil waktu user klik 'Open Controls' di tray."""
        self._on_open()                                 #panggil callback buka GUI

    def _handle_exit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        """Dipanggil waktu user klik 'Exit Application' di tray."""
        self._on_exit()                                 #panggil callback exit
