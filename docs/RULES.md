# Rules / Kurallar

| ID | Severity / Önem | Languages / Diller | English | Türkçe |
|---|---|---|---|---|
| SQL001 | critical | markup,python,js,cs,vb,clike | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | php | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | php | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | markup,cs | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | cs | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | python | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SQL001 | critical | js | SQL query is built with string concatenation/interpolation (SQL injection risk). | SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski). |
| SEC001 | critical | xml,config,vb,php,markup,sql,python,json,js,script,cs,clike | Hard-coded password/secret found in code. | Koda gömülü parola/gizli anahtar bulundu. |
| SEC001 | critical | sql,python,js,cs,vb,php,clike | Plain-text password in a connection string. | Bağlantı metninde açık parola var. |
| SEC001 | critical | markup,xml,json,config | Plain-text password in configuration/connection string. | Yapılandırmada/bağlantı metninde açık parola var. |
| SEC001 | critical | xml | Plain-text secret value in appSettings. | appSettings içinde açık gizli değer var. |
| SEC002 | critical | xml,config,vb,php,markup,sql,python,json,js,script,css,cs,clike | Private key / cloud API token exposed in the file. | Özel anahtar / bulut-API token'ı dosyada açıkta. |
| SEC003 | critical | php | File inclusion driven by user input (LFI/RFI). | Kullanıcı girdisiyle dosya dahil etme (LFI/RFI). |
| SEC004 | critical | php | Request data goes straight into the query. | İstek verisi doğrudan sorguya giriyor. |
| SEC004 | critical | php | extract() can overwrite variables with request data. | extract() ile istek değişkenleri üzerine yazılabilir. |
| XSS001 | error | php | Request data is written to the output without encoding (XSS). | İstek verisi kodlanmadan çıktıya yazılıyor (XSS). |
| XSS001 | error | vb,markup,cs | Request data is written with Response.Write without encoding (XSS). | İstek verisi kodlanmadan Response.Write ile yazılıyor (XSS). |
| XSS001 | error | markup | Request data is printed with <%= %> without encoding (XSS). | İstek verisi <%= %> ile kodlanmadan basılıyor (XSS). |
| XSS002 | warning | js | Raw HTML insertion (XSS risk). | Ham HTML ekleme (XSS riski). |
| XSS002 | warning | js | A string is passed to setTimeout/setInterval (implicit eval). | setTimeout/setInterval içine metin verilmiş (örtük eval). |
| EVAL01 | error | php,js | Dynamic code execution with eval/Function. | eval/Function ile dinamik kod çalıştırma. |
| EVAL01 | error | python | Dynamic code execution with eval/exec. | eval/exec ile dinamik kod çalıştırma. |
| CRY001 | warning | cs | Weak hash algorithm (MD5/SHA1). | Zayıf özet algoritması (MD5/SHA1). |
| CRY001 | warning | php | Weak hash algorithm (md5/sha1). | Zayıf özet algoritması (md5/sha1). |
| CRY001 | warning | python | Weak hash algorithm. | Zayıf özet algoritması. |
| CRY001 | warning | js | Weak hash algorithm. | Zayıf özet algoritması. |
| TLS001 | error | cs | TLS certificate validation is disabled. | TLS sertifika doğrulaması kapatılmış. |
| TLS001 | error | php | TLS verification is disabled. | TLS doğrulaması kapatılmış. |
| TLS001 | error | python | TLS verification is disabled. | TLS doğrulaması kapatılmış. |
| TLS001 | error | js | TLS verification is disabled. | TLS doğrulaması kapatılmış. |
| CFG001 | warning | xml | customErrors is off: error details leak to users. | customErrors kapalı: hata ayrıntıları kullanıcıya sızar. |
| CFG001 | warning | xml | debug="true" in production hurts performance and security. | Üretimde debug="true" performans/güvenlik sorunudur. |
| CFG001 | error | markup,xml | Request validation (XSS protection) is disabled. | İstek doğrulaması (XSS koruması) kapatılmış. |
| CFG001 | critical | markup,xml | ViewState MAC is disabled. | ViewState MAC kapalı. |
| CFG001 | warning | xml | Full trust level. | Tam güven düzeyi. |
| CFG001 | info | xml | SSL is not required for cookies/forms. | Çerez/form için SSL zorunlu değil. |
| CORS01 | warning | xml,config,vb,php,markup,sql,python,json,js,script,css,cs,clike | CORS is open to all origins. | CORS tüm kaynaklara açık. |
| PHP001 | error | php | Removed mysql_* functions are in use. | Kaldırılmış mysql_* işlevleri kullanılıyor. |
| PHP002 | warning | php | Command execution / unsafe deserialization. | Komut çalıştırma / güvensiz deserialization. |
| PHP002 | warning | php | display_errors is on: error details leak. | display_errors açık: hata ayrıntıları sızar. |
| PHP003 | info | php | File upload point. | Dosya yükleme noktası. |
| CS001 | warning | cs | 'throw ex;' resets the stack trace. | 'throw ex;' yığın izini siler. |
| CS002 | warning | cs | async void: exceptions cannot be caught. | async void: hatalar yakalanamaz. |
| CS002 | warning | cs | Synchronous waiting: deadlock risk. | Eşzamanlı bekleme: deadlock riski. |
| CS003 | warning | vb,cs | IDisposable object may not be wrapped in using. | IDisposable nesne using ile sarılmamış olabilir. |
| CS004 | warning | vb,cs | Request data is converted without validation (exceptions). | İstek verisi doğrulamasız dönüştürülüyor (hata/istisna). |
| CS005 | info | cs | External process launch. | Dış süreç başlatma. |
| VB001 | warning | vb | Errors are silently swallowed. | Hatalar sessizce yutuluyor. |
| QLT001 | warning | php,clike,js,cs | Empty catch block: the error is silently swallowed. | Boş catch bloğu: hata sessizce yutuluyor. |
| QLT001 | warning | python | Empty/bare except. | Boş/çıplak except. |
| QLT001 | warning | vb | Empty Catch block. | Boş Catch bloğu. |
| QLT002 | info | js | Leftover debugging code. | Hata ayıklama kalıntısı. |
| QLT002 | info | php | Leftover debugging code. | Hata ayıklama kalıntısı. |
| QLT002 | info | cs | Possible leftover debugging code. | Hata ayıklama kalıntısı olabilir. |
| QLT003 | info | js | Loose equality (==/!=). | Gevşek eşitlik (==/!=). |
| QLT004 | warning | python | Mutable default argument. | Değiştirilebilir varsayılan argüman. |
| QLT004 | warning | python | Command execution through a shell. | Kabuk üzerinden komut çalıştırma. |
| QLT004 | warning | python | Unsafe deserialization. | Güvensiz deserialization. |
| QLT004 | warning | python | Debug mode is on. | Debug modu açık. |
| QLT005 | warning | js | Sensitive data in browser storage. | Hassas veri tarayıcı depolamasında. |
| QLT006 | info | markup | target=_blank without rel=noopener. | target=_blank rel=noopener olmadan. |
| QLT006 | info | markup | Mixed content (http script). | Karışık içerik (http betik). |
| SQLX01 | warning | sql | DELETE without WHERE: all rows are deleted. | WHERE'siz DELETE: tüm kayıtlar silinir. |
| SQLX01 | warning | sql | UPDATE without WHERE: all rows are updated. | WHERE'siz UPDATE: tüm kayıtlar güncellenir. |
| SQLX02 | error | sql | xp_cmdshell usage. | xp_cmdshell kullanımı. |
| SQLX02 | warning | sql | Dynamic SQL / destructive command. | Dinamik SQL / yıkıcı komut. |
| SQLX03 | info | sql | SELECT * or NOLOCK. | SELECT * veya NOLOCK. |
| SCR001 | warning | script | Risky command pattern. | Riskli komut kalıbı. |
| CFG002 | critical | config | Plain-text secret in a configuration file. | Yapılandırma dosyasında açık gizli değer. |
| ENC001 | warning | xml,config,vb,php,markup,sql,python,json,js,script,css,cs,clike | Sign of corrupted Turkish characters (double encoding/mojibake). | Bozuk Türkçe karakter (çift kodlama/mojibake) belirtisi. |
