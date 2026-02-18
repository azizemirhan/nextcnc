# Windows'ta SSL Hatası (DECRYPTION_FAILED_OR_BAD_RECORD_MAC)

`pip install` sırasında bu hata büyük paket (PySide6 / PyQt6) indirilirken oluşuyorsa aşağıdakileri deneyin.

## 1. Önbelleği temizleyip tekrar deneyin

```powershell
python -m pip cache purge
python -m pip install --no-cache-dir -r requirements.txt
```

Veya PyQt6 ile (daha küçük tek paket):

```powershell
python -m pip install --no-cache-dir -r requirements-pyqt6.txt
```

## 2. Farklı ağ kullanın

- VPN kapatıp açın veya kapatıp deneyin.
- Telefonunuzun internet paylaşımı (hotspot) ile bağlanıp aynı komutu çalıştırın.
- Kurumsal ağdaysanız ev ağında deneyin.

## 3. pip ve sertifikaları güncelleyin

```powershell
python -m pip install --upgrade pip
python -m pip install --upgrade certifi
```

## 4. Manuel kurulum (wheel indirip yükleme)

1. Tarayıcıdan PyPI’a gidin:
   - **PySide6:** https://pypi.org/project/PySide6/#files  
   - **PyQt6:** https://pypi.org/project/PyQt6/#files  

2. Python sürümünüze ve Windows 64-bit’e uygun `.whl` dosyasını indirin (örn. `cp312`, `win_amd64`).

3. **PySide6** için şu paketlerin hepsini indirip sırayla kurun:
   - `shiboken6-...-win_amd64.whl`
   - `PySide6_Essentials-...-win_amd64.whl`
   - `PySide6_Addons-...-win_amd64.whl`
   - `PySide6-...-win_amd64.whl`

   ```powershell
   cd indirilenlerin_klasoru
   python -m pip install shiboken6-....whl
   python -m pip install PySide6_Essentials-....whl
   python -m pip install PySide6_Addons-....whl
   python -m pip install PySide6-....whl
   python -m pip install PyOpenGL numpy
   ```

4. **PyQt6** kullanacaksanız yalnızca tek bir wheel indirip:

   ```powershell
   python -m pip install PyQt6-....whl
   python -m pip install PyOpenGL numpy
   ```

Kurulum bitince proje klasöründe:

```powershell
python main.py
```

## 5. Antivirus / güvenlik duvarı

Bazı antivirus veya kurumsal güvenlik yazılımları SSL trafiğini kesip bu hataya yol açar. Geçici olarak kapatıp (veya pip’i istisnaya alıp) tekrar `pip install` deneyin.
