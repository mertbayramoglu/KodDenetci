**[English](README.md)** · Türkçe

# Kod Denetçi

[![CI](https://github.com/mertbayramoglu/KodDenetci/actions/workflows/ci.yml/badge.svg)](https://github.com/mertbayramoglu/KodDenetci/actions/workflows/ci.yml)

Yazılım projelerinizin kodlarını **yerelde** okuyup dosya dosya hataları ve güvenlik açıklarını listeleyen,
her dosya için Claude/ChatGPT gibi bir LLM'e yapıştırılacak **düzeltme prompt'u** üreten Windows masaüstü uygulaması.

- İnternet ve bulut gerekmez; kod ve veritabanı bilgisayardan çıkmaz.
- Yalnızca Python standart kütüphanesi (tkinter + sqlite3). `pip install` yok.
- **Tokenizer yaklaşımı:** kod önce sözcüklere ayrılır; yorum/string içindeki metin kod sanılmaz, token maliyeti tahmin edilir,
  büyük dosyalar token bütçesine göre prompt parçalarına bölünür.

## Hızlı başlangıç
Gereksinim: Windows, Python 3.9+ (tcl/tk seçeneği açık kurulum).

```bat
git clone https://github.com/mertbayramoglu/KodDenetci.git
cd KodDenetci
Calistir.bat
```
Proje klasörünü seçin; tarama otomatik başlar. Soldaki liste risk sırasına göre dosyalardır
(K=Kritik, H=Hata, U=Uyarı, B=Bilgi). Dosyaya tıklayınca bulgular ve hazır prompt görünür.
**Kritik hatalar** sekmesi tüm projedeki kritik bulguları tek listede toplar (çift tıklayınca ilgili dosyaya gider).

Simgeli kısayol: `Calistir.bat` → Kısayol oluştur → Özellikler → Simgeyi değiştir → `kd.ico`.

## Neler bulur?
Sözdizimi (eşleşmeyen parantez, kapanmayan string/yorum, geçersiz JSON/XML, Python sözdizimi), SQL injection, XSS,
koda gömülü parola/anahtar, zayıf hash, kapalı TLS doğrulaması, riskli `web.config` ayarları, boş `catch`, `throw ex;`,
kapatılmamış bağlantılar, PHP `mysql_*`/LFI, Türkçe karakter/kodlama sorunları ve daha fazlası.
Tam liste: [docs/KURALLAR.md](docs/KURALLAR.md).
Diller: C#, VB, JS/TS, PHP, Python, SQL (UTF-16 dahil), HTML/ASPX/Razor, CSS, JSON, XML/config, PowerShell/sh/bat, YAML/INI/env, Java/Go/C/C++ vb.

## Özellikler
- Dosya dosya bulgu listesi (satır, önem, kural, öneri, kod satırı) ve **tüm kritik hatalar** görünümü
- Token bütçeli, çok parçalı düzeltme prompt'u + proje notu (teknoloji bilgisi her prompt'a eklenir)
- Tarama geçmişi; önceki taramaya göre **yeni / giderilen** bulgu sayısı
- Rapor: Markdown, HTML; tüm prompt'ları klasöre dışa aktarma
- Satır bastırma: satıra yorum olarak `kd-ignore` yazın
- Klasör/dosya hariç tutma: proje köküne `.kdignore` koyun (gitignore benzeri; örnek: bu deponun `.kdignore` dosyası)

## Komut satırı
```bat
python KodDenetci.py --cli C:\Projeler\Portal --prompts C:\Temp\promptlar
```

## Veri ve gizlilik
Veriler uygulamanın yanındaki `veri\` klasöründe (SQLite) tutulur; yazılamazsa `%LOCALAPPDATA%\KodDenetci`.
Bu klasör `.gitignore` ile depo dışındadır. Uygulama ağ bağlantısı kurmaz; taranan dosyaları çalıştırmaz ([SECURITY.md](SECURITY.md)).

## Sınırlar
Statik desen/sözdizimi tarayıcısıdır; derleme yapmaz ve yanlış pozitif verebilir (prompt bu yüzden "önce doğrula" der).
Token sayıları tahminidir. Alınan düzeltmeleri her zaman gözden geçirip test edin.

## Geliştirme
```bat
python -m unittest discover -s tests -v
```
Testler arasında deponun kendi kendini taraması da vardır: kaynak kod **sıfır bulgu** vermelidir
(bilerek hatalı örnekler `tests/fixtures/` altındadır ve `.kdignore` ile taramadan çıkarılmıştır).
Katkı: [CONTRIBUTING.md](CONTRIBUTING.md) · Yayın: [docs/GITHUB_YUKLEME.md](docs/GITHUB_YUKLEME.md) ·
Kurumsal onay şablonu: [docs/BT_ONAY_TALEBI.md](docs/BT_ONAY_TALEBI.md)

## Lisans
MIT — Mert Bayramoğlu, Yazılım Geliştirici
