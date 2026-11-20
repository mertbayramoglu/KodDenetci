# Kural listesi

Bu dosya `kd_core.RULES` içinden otomatik üretilmiştir. Yeni kural eklemek için `kd_core.py` içindeki `R(...)` çağrılarına bakın.

| Kural | Önem | Diller | Açıklama |
|---|---|---|---|
| `CFG001` | Kritik | markup, xml | ViewState MAC kapalı. |
| `CFG002` | Kritik | config | Yapılandırma dosyasında açık gizli değer. |
| `SEC001` | Kritik | clike, config, cs, js, json, markup, php, python, script, sql, vb, xml | Koda gömülü parola/gizli anahtar bulundu. |
| `SEC001` | Kritik | clike, cs, js, php, python, sql, vb | Bağlantı metninde açık parola var. |
| `SEC001` | Kritik | config, json, markup, xml | Yapılandırmada/bağlantı metninde açık parola var. |
| `SEC001` | Kritik | xml | appSettings içinde açık gizli değer var. |
| `SEC002` | Kritik | clike, config, cs, css, js, json, markup, php, python, script, sql, vb, xml | Özel anahtar / bulut-API token'ı dosyada açıkta. |
| `SEC003` | Kritik | php | Kullanıcı girdisiyle dosya dahil etme (LFI/RFI). |
| `SEC004` | Kritik | php | İstek verisi doğrudan sorguya giriyor. |
| `SEC004` | Kritik | php | extract() ile istek değişkenleri üzerine yazılabilir. |
| `SQL001` | Kritik | clike, cs, js, markup, php, python, vb | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| `CFG001` | Hata | markup, xml | İstek doğrulaması (XSS koruması) kapatılmış. |
| `EVAL01` | Hata | js, php | eval/Function ile dinamik kod çalıştırma. |
| `EVAL01` | Hata | python | eval/exec ile dinamik kod çalıştırma. |
| `PHP001` | Hata | php | Kaldırılmış mysql_* işlevleri kullanılıyor. |
| `SQLX02` | Hata | sql | xp_cmdshell kullanımı. |
| `TLS001` | Hata | cs | TLS sertifika doğrulaması kapatılmış. |
| `TLS001` | Hata | js, php, python | TLS doğrulaması kapatılmış. |
| `XSS001` | Hata | php | İstek verisi kodlanmadan çıktıya yazılıyor (XSS). |
| `XSS001` | Hata | cs, markup, vb | İstek verisi kodlanmadan Response.Write ile yazılıyor (XSS). |
| `XSS001` | Hata | markup | İstek verisi <%= %> ile kodlanmadan basılıyor (XSS). |
| `CFG001` | Uyarı | xml | customErrors kapalı: hata ayrıntıları kullanıcıya sızar. |
| `CFG001` | Uyarı | xml | Üretimde debug="true" performans/güvenlik sorunudur. |
| `CFG001` | Uyarı | xml | Tam güven düzeyi. |
| `CORS01` | Uyarı | clike, config, cs, css, js, json, markup, php, python, script, sql, vb, xml | CORS tüm kaynaklara açık. |
| `CRY001` | Uyarı | cs | Zayıf özet algoritması (MD5/SHA1). |
| `CRY001` | Uyarı | php | Zayıf özet algoritması (md5/sha1). |
| `CRY001` | Uyarı | js, python | Zayıf özet algoritması. |
| `CS001` | Uyarı | cs | 'throw ex;' yığın izini siler. |
| `CS002` | Uyarı | cs | async void: hatalar yakalanamaz. |
| `CS002` | Uyarı | cs | Eşzamanlı bekleme: deadlock riski. |
| `CS003` | Uyarı | cs, vb | IDisposable nesne using ile sarılmamış olabilir. |
| `CS004` | Uyarı | cs, vb | İstek verisi doğrulamasız dönüştürülüyor (hata/istisna). |
| `ENC001` | Uyarı | clike, config, cs, css, js, json, markup, php, python, script, sql, vb, xml | Bozuk Türkçe karakter (çift kodlama/mojibake) belirtisi. |
| `PHP002` | Uyarı | php | Komut çalıştırma / güvensiz deserialization. |
| `PHP002` | Uyarı | php | display_errors açık: hata ayrıntıları sızar. |
| `QLT001` | Uyarı | clike, cs, js, php | Boş catch bloğu: hata sessizce yutuluyor. |
| `QLT001` | Uyarı | python | Boş/çıplak except. |
| `QLT001` | Uyarı | vb | Boş Catch bloğu. |
| `QLT004` | Uyarı | python | Değiştirilebilir varsayılan argüman. |
| `QLT004` | Uyarı | python | Kabuk üzerinden komut çalıştırma. |
| `QLT004` | Uyarı | python | Güvensiz deserialization. |
| `QLT004` | Uyarı | python | Debug modu açık. |
| `QLT005` | Uyarı | js | Hassas veri tarayıcı depolamasında. |
| `SCR001` | Uyarı | script | Riskli komut kalıbı. |
| `SQLX01` | Uyarı | sql | WHERE'siz DELETE: tüm kayıtlar silinir. |
| `SQLX01` | Uyarı | sql | WHERE'siz UPDATE: tüm kayıtlar güncellenir. |
| `SQLX02` | Uyarı | sql | Dinamik SQL / yıkıcı komut. |
| `VB001` | Uyarı | vb | Hatalar sessizce yutuluyor. |
| `XSS002` | Uyarı | js | Ham HTML ekleme (XSS riski). |
| `XSS002` | Uyarı | js | setTimeout/setInterval içine metin verilmiş (örtük eval). |
| `CFG001` | Bilgi | xml | Çerez/form için SSL zorunlu değil. |
| `CS005` | Bilgi | cs | Dış süreç başlatma. |
| `PHP003` | Bilgi | php | Dosya yükleme noktası. |
| `QLT002` | Bilgi | js, php | Hata ayıklama kalıntısı. |
| `QLT002` | Bilgi | cs | Hata ayıklama kalıntısı olabilir. |
| `QLT003` | Bilgi | js | Gevşek eşitlik (==/!=). |
| `QLT006` | Bilgi | markup | target=_blank rel=noopener olmadan. |
| `QLT006` | Bilgi | markup | Karışık içerik (http betik). |
| `SQLX03` | Bilgi | sql | SELECT * veya NOLOCK. |

Sözdizimi kuralları (`SYN001`–`SYN007`), TODO notları (`TODO01`), uzunluk/derinlik (`QLT007`–`QLT009`) ve kodlama (`ENC002`) analizörde koddan üretilir.
