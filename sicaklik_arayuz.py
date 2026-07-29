"""
Batarya Modulu Sicaklik Izleme Arayuzu
18 kanalli NTC sensor verisini seri port (UART) uzerinden okur ve gosterir.

Gereksinimler:
    pip install pyserial

Kullanim:
    python sicaklik_arayuz.py
"""

import re
import threading
import queue
import sys
import ctypes
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

TOPLAM_KANAL = 18
BAUD_RATE = 115200
UYARI_ESIGI = 45.0
KRITIK_ESIK = 60.0

SATIR_DESENI = re.compile(r"C(\d+)\s*->\s*V:\s*([\d.]+)\s*V\s*\|\s*T:\s*(-?[\d.]+)\s*C")


class SicaklikArayuzu:
    def __init__(self, root):
        self.root = root
        self.root.title("Batarya Sicaklik Izleme - 18 Kanal")
        self.root.configure(bg="#1e1e1e")
        self.root.geometry("980x600")
        self.root.resizable(True, True)

        self.seri_port = None
        self.okuma_kuyrugu = queue.Queue()
        self.calisiyor = False
        self.sicakliklar = {i: None for i in range(TOPLAM_KANAL)}
        self.son_gosterilen = {}
        self.kart_widgetlari = {}

        self._ust_panel_olustur()
        self._kart_izgarasi_olustur()
        self._durum_cubugu_olustur()

        self.root.after(250, self._kuyruk_kontrol)

    def _ust_panel_olustur(self):
        panel = tk.Frame(self.root, bg="#1e1e1e", pady=12)
        panel.pack(fill="x", padx=16)

        tk.Label(panel, text="Port:", bg="#1e1e1e", fg="#cccccc",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))

        self.port_secim = ttk.Combobox(panel, width=12, state="readonly")
        self.port_secim.pack(side="left", padx=(0, 8))
        self._portlari_yenile()

        yenile_btn = tk.Button(panel, text="Yenile", command=self._portlari_yenile,
                                bg="#333333", fg="white", relief="flat", padx=10)
        yenile_btn.pack(side="left", padx=(0, 16))

        self.baglan_btn = tk.Button(panel, text="Bağlan", command=self._baglanti_toggle,
                                     bg="#0f6e56", fg="white", relief="flat",
                                     padx=16, pady=4, font=("Segoe UI", 10, "bold"))
        self.baglan_btn.pack(side="left")

        self.max_etiket = tk.Label(panel, text=self._max_metin_olustur(None, None),
                                    bg="#1e1e1e", fg="#f2a623",
                                    font=("Consolas", 12, "bold"), anchor="e", width=32)
        self.max_etiket.pack(side="right")

    def _portlari_yenile(self):
        portlar = [p.device for p in serial.tools.list_ports.comports()]
        self.port_secim["values"] = portlar
        if portlar:
            self.port_secim.current(0)

    def _kart_izgarasi_olustur(self):
        kart_g, kart_y = 140, 100
        cift_ici_bosluk = 10
        modul_arasi_bosluk = 38
        baslik_yuksekligi = 24
        sutun_sayisi = 6
        satir_sayisi = 3
        sol_bosluk, ust_bosluk = 24, 14
        satir_araligi = baslik_yuksekligi + kart_y + 26

        x_konumlari = []
        cur = sol_bosluk
        for c in range(sutun_sayisi):
            x_konumlari.append(cur)
            cur += kart_g + (cift_ici_bosluk if c % 2 == 0 else modul_arasi_bosluk)

        genislik = x_konumlari[-1] + kart_g + sol_bosluk
        yukseklik = ust_bosluk + satir_sayisi * satir_araligi

        self.canvas = tk.Canvas(self.root, bg="#1e1e1e", width=genislik, height=yukseklik,
                                 highlightthickness=0)
        self.canvas.pack(padx=16, pady=8)

        for m in range(TOPLAM_KANAL // 2):
            satir, grup = divmod(m, sutun_sayisi // 2)
            c1, c2 = grup * 2, grup * 2 + 1
            x1, x2 = x_konumlari[c1], x_konumlari[c2]
            y_baslik = ust_bosluk + satir * satir_araligi
            y_orta = y_baslik + baslik_yuksekligi / 2
            x_merkez = (x1 + kart_g / 2 + x2 + kart_g / 2) / 2

            self.canvas.create_text(x_merkez, y_orta, text=f"MODÜL {m + 1}",
                                     fill="#888888", font=("Segoe UI", 10, "bold"),
                                     anchor="center")
            self.canvas.create_line(x1 + 6, y_orta, x_merkez - 36, y_orta,
                                     fill="#444444", width=1)
            self.canvas.create_line(x_merkez + 36, y_orta, x2 + kart_g - 6, y_orta,
                                     fill="#444444", width=1)

            for j, c in enumerate((c1, c2)):
                kanal = m * 2 + j
                x = x_konumlari[c]
                y = y_baslik + baslik_yuksekligi

                rect_id = self.canvas.create_rectangle(
                    x, y, x + kart_g, y + kart_y,
                    fill="#2a2a2a", outline="#3a3a3a", width=2)
                baslik_id = self.canvas.create_text(
                    x + kart_g / 2, y + 26, text=f"Sensör {j + 1}",
                    fill="#999999", font=("Segoe UI", 10), anchor="center")
                deger_id = self.canvas.create_text(
                    x + kart_g / 2, y + 62, text=self._sabit_genislik_metin(None) + "°C",
                    fill="#e0e0e0", font=("Consolas", 18, "bold"), anchor="center")

                self.kart_widgetlari[kanal] = {"rect": rect_id, "baslik": baslik_id, "deger": deger_id}

    def _durum_cubugu_olustur(self):
        self.durum_etiketi = tk.Label(self.root, text="Bağlı değil",
                                       bg="#141414", fg="#888888",
                                       font=("Segoe UI", 9), anchor="w", padx=12)
        self.durum_etiketi.pack(fill="x", side="bottom")

    def _baglanti_toggle(self):
        if self.calisiyor:
            self._baglantiyi_kes()
        else:
            self._baglan()

    def _baglan(self):
        port = self.port_secim.get()
        if not port:
            self.durum_etiketi.config(text="Port seçilmedi")
            return
        try:
            self.seri_port = serial.Serial(port, BAUD_RATE, timeout=1)
        except Exception as e:
            self.durum_etiketi.config(text=f"Bağlantı hatası: {e}")
            return

        self.calisiyor = True
        self.baglan_btn.config(text="Kes", bg="#993c1d")
        self.durum_etiketi.config(text=f"{port} - {BAUD_RATE} baud - bağlı")

        self.okuma_thread = threading.Thread(target=self._seri_okuma_dongusu, daemon=True)
        self.okuma_thread.start()

    def _baglantiyi_kes(self):
        self.calisiyor = False
        if self.seri_port and self.seri_port.is_open:
            self.seri_port.close()
        self.baglan_btn.config(text="Bağlan", bg="#0f6e56")
        self.durum_etiketi.config(text="Bağlı değil")

    def _seri_okuma_dongusu(self):
        while self.calisiyor:
            try:
                satir = self.seri_port.readline().decode("utf-8", errors="ignore").strip()
            except Exception:
                break
            if not satir:
                continue
            eslesme = SATIR_DESENI.search(satir)
            if eslesme:
                kanal = int(eslesme.group(1))
                sicaklik = float(eslesme.group(3))
                if 0 <= kanal < TOPLAM_KANAL:
                    self.okuma_kuyrugu.put((kanal, sicaklik))

    def _kuyruk_kontrol(self):
        guncellenen = False
        while not self.okuma_kuyrugu.empty():
            kanal, sicaklik = self.okuma_kuyrugu.get()
            self.sicakliklar[kanal] = sicaklik
            guncellenen = True

        if guncellenen:
            self._kartlari_yenile()

        self.root.after(250, self._kuyruk_kontrol)

    @staticmethod
    def _max_metin_olustur(sensor_no, sicaklik):
        if sensor_no is None:
            no_str = "--"
            deger_str = " --.-"
        else:
            no_str = f"{sensor_no:2d}"
            deger_str = f"{sicaklik:5.1f}"
        return f"En yüksek: Sensör {no_str} - {deger_str}°C"

    @staticmethod
    def _sabit_genislik_metin(sicaklik):
        if sicaklik is None:
            return "  --.-"
        return f"{sicaklik:6.1f}"

    def _renk_belirle(self, sicaklik):
        if sicaklik is None:
            return "#e0e0e0", "#2a2a2a", "#3a3a3a"
        if sicaklik >= KRITIK_ESIK:
            return "#f7c1c1", "#3a1f1f", "#a32d2d"
        if sicaklik >= UYARI_ESIGI:
            return "#fac775", "#3a2f14", "#854f0b"
        return "#9fe1cb", "#1f2e2a", "#0f6e56"

    def _kartlari_yenile(self):
        gecerli_degerler = {k: v for k, v in self.sicakliklar.items() if v is not None}
        max_kanal = None
        if gecerli_degerler:
            max_kanal = max(gecerli_degerler, key=gecerli_degerler.get)
            self.max_etiket.config(
                text=self._max_metin_olustur(max_kanal + 1, gecerli_degerler[max_kanal]))
        else:
            self.max_etiket.config(text=self._max_metin_olustur(None, None))

        for i in range(TOPLAM_KANAL):
            sicaklik = self.sicakliklar[i]
            onceki = self.son_gosterilen.get(i)
            vurgulu = (i == max_kanal)

            if onceki is not None and onceki == (sicaklik, vurgulu):
                continue

            fg, bg, border = self._renk_belirle(sicaklik)
            w = self.kart_widgetlari[i]
            metin = self._sabit_genislik_metin(sicaklik) + "°C"

            if vurgulu:
                border = "#f2a623"

            self.canvas.itemconfig(w["rect"], fill=bg, outline=border)
            self.canvas.itemconfig(w["deger"], text=metin, fill=fg)

            self.son_gosterilen[i] = (sicaklik, vurgulu)


if __name__ == "__main__":
    kok = tk.Tk()
    uygulama = SicaklikArayuzu(kok)
    kok.mainloop()
