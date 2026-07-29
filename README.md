# Batarya Sıcaklık İzleme Sistemi - 18 Kanal

STM32F4 Discovery tabanlı, 9 batarya modülünün her birinden 2'şer NTC sensörü ile toplam 18 kanaldan sıcaklık okuyan sistem.

## Donanım

- **Mikrodenetleyici:** STM32F4 Discovery (STM32F407VGT6)
- **Analog mux:** CD74HC4067, 16 kanal analog/dijital çoklayıcı
- **Sıcaklık sensörü:** 10K NTC termistör (B katsayısı 3950), su geçirmez, 18 adet
- **Gerilim bölücü direnci:** 10K, %1 tolerans, 18 adet
- **USB-Seri köprü:** CP2102 (PC arayüzü için)

## Pin haritası

### Mux bağlantıları

| Mux pini | STM32 pini |
|---|---|
| S0 | PE2 |
| S1 | PE4 |
| S2 | PE5 |
| S3 | PE6 |
| SIG | PA1 (ADC1_IN1) |
| EN | GND |
| VCC | 3.3V |
| GND | GND |

### CP2102 (UART) bağlantıları

| CP2102 pini | STM32 pini |
|---|---|
| TXD | PD9 (USART3_RX) |
| RXD | PD8 (USART3_TX) |
| GND | GND |

## Gerilim bölücü devresi (her kanal için)

```
3.3V -- NTC -- [ölçüm noktası] -- 10K direnç -- GND
```

Ölçüm noktası, mux'un ilgili C0-C17 pinine bağlanır.

## Kurulum

1. Bu depoyu klonlayın:
   ```
   git clone https://github.com/tatabey/sicaklik-izleme-stm32.git
   ```
2. STM32CubeIDE'yi açın.
3. **File → Open Projects from File System...** ile klonlanan klasörü seçin.
4. Projeye sağ tıklayıp **Build Project** deyin.
5. STM32'yi USB ile bağlayıp **Run** (Debug değil) ile karta yükleyin.

## PC arayüzü

Sensör verilerini görsel olarak izlemek için `sicaklik_arayuz.py` (Python + Tkinter) kullanılır.

```
pip install pyserial
python sicaklik_arayuz.py
```

CP2102'nin bağlı olduğu COM portunu seçip "Bağlan" butonuna basmanız yeterli. Arayüz, 18 sensörü 9 modül halinde gruplandırıp gösterir ve en yüksek sıcaklığa sahip sensörü otomatik vurgular.

## Notlar

- ADC örnekleme süresi 480 cycle olarak ayarlıdır (yüksek empedanslı NTC bölücüsü için önerilen değer).
- Mux kanal değiştirme sonrası 10ms bekleme (settling time) uygulanır.
- Isıl eşikler: 45°C üzeri uyarı, 60°C üzeri kritik olarak arayüzde renklendirilir.
