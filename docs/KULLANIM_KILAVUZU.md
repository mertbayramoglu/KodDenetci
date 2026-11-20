# Kod Denetçi (CodeAuditor) — Kullanım Kılavuzu

Kod Denetçi, seçtiğiniz proje klasöründeki kod dosyalarını bilgisayarınızda tarar, hataları dosya dosya listeler ve her dosya için bir yapay zekâ modeline (LLM) verebileceğiniz düzeltme prompt'u üretir. Tüm veriler yereldir; uygulama kendiliğinden internete bağlanmaz.

## 1. Hızlı başlangıç
- Üstteki 'Seç…' ile proje klasörünü seçin (veya yolunu yazıp Enter'a basın) ve 'Tara'ya tıklayın.
- Soldaki listeden bir dosya seçin; sağda 'Bulgular' sekmesinde o dosyanın sorunları görünür. Bir bulguya tıklayınca açıklama, kod satırı ve öneri altta çıkar.
- 'Prompt' sekmesinde o dosya için hazır prompt vardır. 'Panoya kopyala'yı kullanıp LLM sohbetine yapıştırın. Dosya büyükse birden çok parça üretilir; parçaları açılır listeden seçin.
- LLM'in verdiği ESKİ/YENİ düzeltmeleri kodunuza kendiniz uygulayın, sonra yeniden tarayın: 'Geçmiş' ve 'Özet' sekmeleri yeni ve giderilen bulguları gösterir.

## 2. K, H, U, B nedir? (Önem düzeyleri)
- K = Kritik: Güvenlik açığı veya veri kaybı riski (SQL injection, koda gömülü parola, WHERE'siz DELETE/UPDATE, kapatılmış TLS doğrulaması…). Önce bunları düzeltin.
- H = Hata: Çalışmayı bozabilecek veya hatayı gizleyen sorunlar (sözdizimi hatası, kapatılmamış parantez/string, boş catch, async void…).
- U = Uyarı: Riskli veya kötü pratik (zayıf özet algoritması, == kullanımı, debug kalıntısı…). Hemen bozmaz ama bakım/güvenlik maliyeti vardır.
- B = Bilgi: Düşük öncelikli notlar (TODO/FIXME, çok uzun satır/dosya, derin iç içe blok).

Dosya listesinde ve tablolarda bu harfler sayı olarak görünür (ör. K2 H5 = 2 kritik, 5 hata). İngilizce arayüzde karşılıkları C/E/W/I'dır (Critical/Error/Warning/Info). Satırdaki ★ işareti, önceki taramada olmayan YENİ bulgudur.

## 3. Token nedir?

LLM'ler metni 'token' denen parçalarla okur (kabaca bir kelime parçası; kodda bir sözcük, sayı veya işaret). Her modelin tek seferde alabileceği token sınırı vardır. Bu yüzden büyük dosyayı bütün olarak yapıştırmak çoğu zaman sığmaz veya kaliteyi düşürür.

Kod Denetçi her dosyanın yaklaşık token sayısını hesaplar ('Token' sütunu) ve prompt'ları 'Token bütçesi' ayarına göre böler: dosya sığıyorsa tamamı, sığmıyorsa yalnızca bulguların çevresindeki bölümler parçalara paketlenir. Sayılar tahminidir (±%15); modelden modele değişir.

## 4. Ayarlar (Ayarlar > Ayarlar…)
- Arayüz dili: Menü, liste ve kılavuz dili. 'Otomatik' Windows dilini izler. Değişiklik hemen uygulanır.
- Prompt / rapor dili: LLM'e verilecek prompt'ların ve raporların dili. 'Arayüzle aynı' ya da Türkçe/English. Kullandığınız model hangi dilde daha iyiyse onu seçin.
- Token bütçesi (varsayılan 6000): Bir prompt parçasının yaklaşık üst sınırı. Küçük model veya kısa bağlam penceresi için düşürün (ör. 3000), büyük bağlamlı modelde artırın.
- Bağlam satırı (varsayılan 6): Her bulgunun üstüne/altına eklenen kod satırı sayısı. Artarsa model çevreyi daha iyi görür ama token artar.
- Azami dosya boyutu KB (varsayılan 2048): Bundan büyük dosyalar atlanır (üretilmiş, minified, yedek dosyaları elemek için).
- Hariç tutulanlar: Virgülle ayrılmış klasör/dosya adları (node_modules, .git, bin, obj…). Proje köküne .kdignore dosyası koyarak desen bazlı (gitignore benzeri) dışlama da yapabilirsiniz.

## 5. Ekranlar ve alanlar
- Üst çubuk: Proje klasörü, Seç…, Tara, Durdur. İlerleme çubuğu taranan dosya sayısını gösterir.
- Sol liste: Dosyalar, dil, satır sayısı, token ve K/H/U/B sayıları. Üstteki filtre ve arama kutusu listeyi daraltır. Çift tık dosyayı açar (betik/HTML dosyaları çalıştırılmaz, Not Defteri'nde açılır). Sağ tık: klasörde göster, prompt kopyala.
- Bulgular sekmesi: Seçili dosyanın sorunları ve altta ayrıntı (kural kodu, satır/sütun, kod parçası, öneri).
- Kritik hatalar sekmesi: Tüm projedeki kritik (isteğe bağlı kritik+hata) bulguların tek listesi. Çift tıklayınca ilgili dosya ve bulguya gider; 'Listeyi kopyala' hepsini panoya alır.
- Prompt sekmesi: Seçili dosyanın prompt parçaları, token sayısı, kopyala ve kaydet düğmeleri.
- Özet sekmesi: Tarama sayıları, en sık kurallar, dillere göre dağılım ve Proje notu. Not, tüm prompt'lara bağlam olarak eklenir (ör. 'ASP.NET WebForms, SQL Server, .NET 4.8'). 'Proje özet prompt'u' en riskli dosyalar için genel bir düzeltme planı ister.
- Geçmiş sekmesi: Önceki taramalar; açma ve silme.
- Dosya menüsü: Raporu Markdown/HTML kaydet, tüm prompt'ları klasöre aktar, veri klasörünü aç.

## 6. Yanlış pozitifleri susturma
- Satır sonuna yorum olarak kd-ignore yazarsanız (ör. // kd-ignore gerekçe) o satırdaki bulgular gösterilmez.
- Dosya veya klasörü tümden atlamak için proje köküne .kdignore yazın (her satıra bir desen, # yorum).

Statik analiz kesin hüküm vermez: bulgu yanlış pozitif olabilir. Prompt'taki 1. adım LLM'den bulguyu doğrulamasını ister; düzeltmeyi uygulamadan önce siz de kontrol edin.

## 7. Gizlilik ve güvenlik
- Tarama, veritabanı (SQLite) ve raporlar yalnızca bilgisayarınızdaki 'veri' klasöründedir. Bu klasörü GitHub'a göndermeyin (.gitignore bunu engeller).
- Prompt'lar kodunuzun parçalarını içerir. Bir buluta/LLM'e yapıştırmadan önce parola, anahtar ve müşteri verisi olmadığından emin olun; şirket politikanıza uyun.
- Kod Denetçi taradığınız dosyaları çalıştırmaz ve değiştirmez.

## 8. Hata bildirme ve geri bildirim

Yardım > Hata bildir / Geri bildirim… penceresinden hata, öneri veya soru gönderebilirsiniz. Tür seçin, başlık ve açıklama yazın; hatalar için tekrar adımlarını ekleyin. İsteğe bağlı sistem bilgisi yalnızca sürüm, Python ve işletim sistemini içerir — kod veya dosya adı içermez. Alttaki önizleme, gönderilecek metnin aynısıdır.
- 'GitHub'da aç': Tarayıcıda hazır doldurulmuş bir kayıt (issue) sayfası açılır; siz kontrol edip gönderirsiniz. GitHub hesabı gerekir.
- 'Kopyala' / 'Dosyaya kaydet': GitHub kullanmadan e-posta veya başka kanaldan iletmek için.
- Güvenlik açığı bulduysanız herkese açık kayıt açmayın; SECURITY.md'deki özel bildirim yolunu kullanın.

## 9. Komut satırı ve ipuçları

```
KodDenetci.py --cli <klasör> [--prompts <çıktı klasörü>] [--lang tr|en]
```
- Arayüzsüz çalışır; CI veya toplu denetim için uygundur.
- Çalıştırmak için Calistir.bat'a çift tıklayın (Python 3.9+ ve tkinter gerekir).
- Önce Kritik hatalar sekmesini temizleyin, sonra Hata, sonra Uyarı.
- Çok büyük projede önce en riskli 10 dosyayla başlayın; 'Proje özet prompt'u' sırayı önerir.
