# FAHH Randomizer Engine

Aplikasi desktop Windows untuk memutar audio fah.mp3 secara acak di latar belakang (System Tray). Saat pertama kali dijalankan, aplikasi akan langsung memutar suara jumpscare sekali dan langsung bersembunyi ke System Tray, kemudian memutar kembali suara secara acak berdasarkan interval waktu yang ditentukan.

## Cara Clone
```bash
git clone https://github.com/HasbieAssyattar/FAH-RANDOMIZER.git
cd FAH-RANDOMIZER
```

## Persyaratan & Instalasi
Instal dependensi yang diperlukan:
```bash
pip install customtkinter pygame-ce pystray Pillow pyinstaller
```

## Cara Menjadikan Aplikasi (.exe)
Untuk membuat file executable (.exe), jalankan perintah berikut:
```bash
pyinstaller --noconsole --onefile --add-data "fah.mp3;." --name "FAHH_Randomizer" --clean -y main.py
```
File hasil compile akan berada di folder dist/.
