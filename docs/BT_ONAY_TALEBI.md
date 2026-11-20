# Yazılım Onay Talebi Şablonu (kurumsal bilgisayarlar için)

Kurumunuzun güvenlik yazılımı (EDR/antivirüs) bu aracı engellerse BT/güvenlik ekibine aşağıdaki bilgilerle başvurun.
Güvenlik kontrolünü atlatmaya çalışmayın; onay ancak güvenlik ekibinden gelmelidir.

## Ne yapar?
- Kullanıcının seçtiği proje klasöründeki kod dosyalarını **yalnızca okur**; hiçbirini değiştirmez/silmez.
- Sonuçları uygulamanın yanındaki `veri\` klasörüne yerel SQLite dosyası ve rapor dosyaları olarak yazar.
- Python 3 + tkinter (standart kütüphane); üçüncü taraf paket yoktur.

## Ne yapmaz? (kaynak kodda doğrulanabilir)
- Ağ bağlantısı kurmaz (socket, urllib, http, requests kullanılmaz); veri dışarı gönderilmez.
- Kayıt defterine yazmaz, servis/zamanlanmış görev oluşturmaz, yönetici yetkisi istemez.
- Kendini gizlemez, başka işleme kod enjekte etmez, kalıcılık sağlamaz.
- Taranan projedeki dosyaları çalıştırmaz; betik/HTML dosyalarını metin düzenleyicide açar.
- Alt süreç kullanımı yalnızca kullanıcı isterse: dosyayı açma, "Klasörde göster" ve Notepad.

## Bütünlük
Sürüm: GitHub sürüm etiketi veya `git rev-parse HEAD`. Dosya özeti: `certutil -hashfile KodDenetci.py SHA256`.
Uygulama imzasız `.exe` içermez; `Calistir.bat` ile Python üzerinden çalışır.

## Talep
1. Kaynak kodun güvenlik ekibince incelenmesi.
2. Uygun bulunursa çalıştırma izni / istisna tanımlanması.
