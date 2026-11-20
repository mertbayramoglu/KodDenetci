# Güvenlik politikası

## Güvenlik açığı bildirimi
Bir güvenlik sorunu bulursanız lütfen herkese açık issue **açmayın**; GitHub'da deponun
**Security → Report a vulnerability** (özel bildirim) bölümünü kullanın veya depo sahibine doğrudan yazın.

## Tasarım ilkeleri
- Uygulama **ağ bağlantısı kurmaz**; kod ve veriler yerel kalır (`veri/` klasörü, SQLite).
- Taranan projedeki dosyalar **çalıştırılmaz**. Arayüzde bir dosyayı açarken betik/HTML türleri
  (`.bat`, `.vbs`, `.js`, `.ps1`, `.html` vb.) varsayılan uygulama yerine metin düzenleyicide açılır.
- Veritabanı sorguları parametreli; HTML rapor çıktısı kaçışlanır.
- Araç statik bir desen tarayıcısıdır: yanlış pozitif/negatif olabilir, güvenlik denetiminin yerine geçmez.
