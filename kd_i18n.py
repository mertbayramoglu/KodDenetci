# -*- coding: utf-8 -*-
"""
kd_i18n.py - Türkçe / English metinler (Kod Denetçi / CodeAuditor)

  * detect_lang / resolve      : dil seçimi
  * tx()                       : bulgu mesajı ve önerilerini çevirir (veritabanında Türkçe kaynak metin saklanır)
  * PROMPT / REPORT            : prompt ve rapor şablonları
  * UI / t()                   : arayüz metinleri
  * GUIDE                      : kullanım kılavuzu (uygulama + docs üretimi)
Yalnızca standart kütüphane kullanır.
"""
import os
import re
import sys

LANGS = ("tr", "en")
APP_NAME = {"tr": "Kod Denetçi", "en": "CodeAuditor"}
APP_TAGLINE = {"tr": "Yerel statik kod denetimi  ·  düzeltme prompt'u üretici",
               "en": "Local static code audit  ·  LLM fix-prompt generator"}
SEV = {"tr": {"critical": "Kritik", "error": "Hata", "warning": "Uyarı", "info": "Bilgi"},
       "en": {"critical": "Critical", "error": "Error", "warning": "Warning", "info": "Info"}}
# Sütun kısaltmaları: TR K/H/U/B  ·  EN C/E/W/I
SEV_ABBR = {"tr": {"critical": "K", "error": "H", "warning": "U", "info": "B"},
            "en": {"critical": "C", "error": "E", "warning": "W", "info": "I"}}
LANG_LABEL = {
    "tr": {"cs": "C#", "js": "JavaScript/TypeScript", "clike": "C-tabanlı", "php": "PHP", "python": "Python",
           "sql": "SQL", "vb": "VB/VBScript", "css": "CSS/SCSS", "markup": "HTML/ASPX/Razor", "json": "JSON",
           "xml": "XML/Config", "script": "Betik (ps1/sh/bat)", "config": "Yapılandırma (yml/ini/env)"},
    "en": {"cs": "C#", "js": "JavaScript/TypeScript", "clike": "C-like", "php": "PHP", "python": "Python",
           "sql": "SQL", "vb": "VB/VBScript", "css": "CSS/SCSS", "markup": "HTML/ASPX/Razor", "json": "JSON",
           "xml": "XML/Config", "script": "Script (ps1/sh/bat)", "config": "Config (yml/ini/env)"},
}


def detect_lang():
    """İşletim sistemi arayüz dili Türkçe ise 'tr', değilse 'en'."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "tr" if (lid & 0xFF) == 0x1F else "en"
    except Exception:  # kd-ignore (Windows dışı / ctypes yok)
        pass
    for k in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(k, "")
        if v:
            return "tr" if v.lower().startswith("tr") else "en"
    return "en"


def resolve(setting):
    """'tr' | 'en' | 'auto' (veya boş) -> 'tr' | 'en'."""
    s = (setting or "").strip().lower()
    return s if s in LANGS else detect_lang()


# --------------------------------------------------------------------------
# Bulgu mesajları / öneriler (kaynak: Türkçe) -> İngilizce
# --------------------------------------------------------------------------
_PAIRS = [
    ("SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski).",
     "SQL query is built with string concatenation/interpolation (SQL injection risk)."),
    ("Parametreli sorgu kullan (SqlParameter / PDO prepared statement / ? parametreleri). Kullanıcı girdisini asla sorgu metnine ekleme.",
     "Use parameterized queries (SqlParameter / PDO prepared statements / ? placeholders). Never put user input into the query text."),
    ("Koda gömülü parola/gizli anahtar bulundu.", "Hard-coded password/secret found in code."),
    ("Gizli bilgiyi koddan çıkar: ortam değişkeni, kullanıcı gizli deposu (secrets), şifreli yapılandırma bölümü veya anahtar kasası kullan. Sızmış olabileceği için parolayı değiştir.",
     "Remove the secret from code: use an environment variable, a secrets store, an encrypted config section or a key vault. Rotate the password, it may already be exposed."),
    ("Bağlantı metninde açık parola var.", "Plain-text password in a connection string."),
    ("Bağlantı bilgisini yapılandırma/gizli depoya taşı; Integrated Security veya şifreli connectionStrings kullan.",
     "Move the connection info to configuration/a secrets store; use Integrated Security or encrypted connectionStrings."),
    ("Yapılandırmada/bağlantı metninde açık parola var.", "Plain-text password in configuration/connection string."),
    ("Parolayı yapılandırma şifreleme (aspnet_regiis) veya ortam değişkeni/gizli depo ile sakla.",
     "Store the password with configuration encryption (aspnet_regiis) or an environment variable/secrets store."),
    ("appSettings içinde açık gizli değer var.", "Plain-text secret value in appSettings."),
    ("Değeri şifrele veya gizli depoya taşı.", "Encrypt the value or move it to a secrets store."),
    ("Özel anahtar / bulut-API token'ı dosyada açıkta.", "Private key / cloud API token exposed in the file."),
    ("Anahtarı hemen iptal et/yenile ve depodan temizle (geçmişi de).",
     "Revoke/rotate the key immediately and purge it from the repository (including history)."),
    ("Kullanıcı girdisiyle dosya dahil etme (LFI/RFI).", "File inclusion driven by user input (LFI/RFI)."),
    ("Dahil edilecek dosyayı beyaz listeden seç; girdiyi doğrudan yola koyma.",
     "Pick the file to include from an allow-list; never put input directly into the path."),
    ("İstek verisi doğrudan sorguya giriyor.", "Request data goes straight into the query."),
    ("PDO/mysqli prepared statement + bind kullan.", "Use PDO/mysqli prepared statements with bound parameters."),
    ("extract() ile istek değişkenleri üzerine yazılabilir.", "extract() can overwrite variables with request data."),
    ("extract() kullanma; alanları tek tek ve doğrulayarak al.", "Do not use extract(); read fields one by one with validation."),
    ("İstek verisi kodlanmadan çıktıya yazılıyor (XSS).", "Request data is written to the output without encoding (XSS)."),
    ("htmlspecialchars($x, ENT_QUOTES, 'UTF-8') ile kodla.", "Encode with htmlspecialchars($x, ENT_QUOTES, 'UTF-8')."),
    ("İstek verisi kodlanmadan Response.Write ile yazılıyor (XSS).", "Request data is written with Response.Write without encoding (XSS)."),
    ("Server.HtmlEncode / HttpUtility.HtmlEncode veya <%: %> kullan.", "Use Server.HtmlEncode / HttpUtility.HtmlEncode or <%: %>."),
    ("İstek verisi <%= %> ile kodlanmadan basılıyor (XSS).", "Request data is printed with <%= %> without encoding (XSS)."),
    ("<%: ... %> (kodlamalı) veya HtmlEncode kullan.", "Use <%: ... %> (encoding) or HtmlEncode."),
    ("Ham HTML ekleme (XSS riski).", "Raw HTML insertion (XSS risk)."),
    ("textContent kullan veya girdiyi DOMPurify gibi bir araçla temizle.", "Use textContent or sanitize the input with a tool like DOMPurify."),
    ("setTimeout/setInterval içine metin verilmiş (örtük eval).", "A string is passed to setTimeout/setInterval (implicit eval)."),
    ("Metin yerine fonksiyon geçir.", "Pass a function instead of a string."),
    ("eval/Function ile dinamik kod çalıştırma.", "Dynamic code execution with eval/Function."),
    ("Dinamik kod çalıştırmayı kaldır; JSON.parse / veri tabanlı yaklaşım kullan.", "Remove dynamic code execution; use JSON.parse / a data-driven approach."),
    ("eval/exec ile dinamik kod çalıştırma.", "Dynamic code execution with eval/exec."),
    ("ast.literal_eval veya açık bir ayrıştırıcı kullan.", "Use ast.literal_eval or an explicit parser."),
    ("Zayıf özet algoritması (MD5/SHA1).", "Weak hash algorithm (MD5/SHA1)."),
    ("Parola için bcrypt/Argon2/PBKDF2; bütünlük için SHA-256+.", "Use bcrypt/Argon2/PBKDF2 for passwords; SHA-256+ for integrity."),
    ("Zayıf özet algoritması (md5/sha1).", "Weak hash algorithm (md5/sha1)."),
    ("Parola için password_hash()/password_verify() kullan.", "Use password_hash()/password_verify() for passwords."),
    ("Zayıf özet algoritması.", "Weak hash algorithm."),
    ("SHA-256+ ya da parola için bcrypt/argon2.", "Use SHA-256+, or bcrypt/argon2 for passwords."),
    ("SHA-256+ kullan.", "Use SHA-256+."),
    ("TLS sertifika doğrulaması kapatılmış.", "TLS certificate validation is disabled."),
    ("Doğrulamayı geri aç; geçerli sertifika kur.", "Re-enable validation; install a valid certificate."),
    ("TLS doğrulaması kapatılmış.", "TLS verification is disabled."),
    ("CURLOPT_SSL_VERIFYPEER=true, VERIFYHOST=2.", "Set CURLOPT_SSL_VERIFYPEER=true and VERIFYHOST=2."),
    ("verify=True (veya CA yolu ver).", "Use verify=True (or pass a CA bundle path)."),
    ("rejectUnauthorized: true.", "Use rejectUnauthorized: true."),
    ("customErrors kapalı: hata ayrıntıları kullanıcıya sızar.", "customErrors is off: error details leak to users."),
    ('mode="RemoteOnly" veya "On" yap.', 'Set mode="RemoteOnly" or "On".'),
    ('Üretimde debug="true" performans/güvenlik sorunudur.', 'debug="true" in production hurts performance and security.'),
    ('Yayında debug="false" yap.', 'Use debug="false" in production.'),
    ("İstek doğrulaması (XSS koruması) kapatılmış.", "Request validation (XSS protection) is disabled."),
    ("ValidateRequest'i açık tut; gereken alanı ayrıca doğrula/kodla.", "Keep ValidateRequest on; validate/encode the specific field separately."),
    ("ViewState MAC kapalı.", "ViewState MAC is disabled."),
    ('enableViewStateMac="true".', 'Use enableViewStateMac="true".'),
    ("Tam güven düzeyi.", "Full trust level."),
    ("Gerekmiyorsa daha düşük güven düzeyi kullan.", "Use a lower trust level if full trust is not required."),
    ("Çerez/form için SSL zorunlu değil.", "SSL is not required for cookies/forms."),
    ('requireSSL="true".', 'Use requireSSL="true".'),
    ("CORS tüm kaynaklara açık.", "CORS is open to all origins."),
    ("İzin verilen kaynakları açıkça listele.", "List the allowed origins explicitly."),
    ("Kaldırılmış mysql_* işlevleri kullanılıyor.", "Removed mysql_* functions are in use."),
    ("PDO veya mysqli + prepared statement'a geç.", "Switch to PDO or mysqli with prepared statements."),
    ("Komut çalıştırma / güvensiz deserialization.", "Command execution / unsafe deserialization."),
    ("Girdiyi doğrula, escapeshellarg kullan; unserialize yerine json_decode.", "Validate input, use escapeshellarg; prefer json_decode over unserialize."),
    ("display_errors açık: hata ayrıntıları sızar.", "display_errors is on: error details leak."),
    ("Üretimde kapat, hataları log'a yaz.", "Turn it off in production and log errors instead."),
    ("Dosya yükleme noktası.", "File upload point."),
    ("Uzantı/MIME/boyut doğrula, rastgele ad kullan, yükleme klasöründe betik çalıştırmayı kapat.",
     "Validate extension/MIME/size, use a random file name, and disable script execution in the upload folder."),
    ("'throw ex;' yığın izini siler.", "'throw ex;' resets the stack trace."),
    ("'throw;' kullan.", "Use 'throw;'."),
    ("async void: hatalar yakalanamaz.", "async void: exceptions cannot be caught."),
    ("async Task döndür (yalnızca olay işleyicilerde async void).", "Return async Task (async void only for event handlers)."),
    ("Eşzamanlı bekleme: deadlock riski.", "Synchronous waiting: deadlock risk."),
    ("async/await'i baştan sona kullan.", "Use async/await all the way through."),
    ("IDisposable nesne using ile sarılmamış olabilir.", "IDisposable object may not be wrapped in using."),
    ("using (...) { } ile sar; bağlantı sızıntısını önle.", "Wrap it in using (...) { } to prevent connection leaks."),
    ("İstek verisi doğrulamasız dönüştürülüyor (hata/istisna).", "Request data is converted without validation (exceptions)."),
    ("TryParse kullan, hatalı girdiyi yönet.", "Use TryParse and handle invalid input."),
    ("Dış süreç başlatma.", "External process launch."),
    ("Argümanlara kullanıcı girdisi karıştırma.", "Do not mix user input into the arguments."),
    ("Hatalar sessizce yutuluyor.", "Errors are silently swallowed."),
    ("Try/Catch (VB.NET) veya hedefli On Error GoTo kullan.", "Use Try/Catch (VB.NET) or a targeted On Error GoTo."),
    ("Boş catch bloğu: hata sessizce yutuluyor.", "Empty catch block: the error is silently swallowed."),
    ("En azından logla; beklenen istisnayı daralt, gerisini yeniden fırlat.", "At least log it; narrow the expected exception and rethrow the rest."),
    ("Boş/çıplak except.", "Empty/bare except."),
    ("Belirli istisnayı yakala ve logla.", "Catch the specific exception and log it."),
    ("Boş Catch bloğu.", "Empty Catch block."),
    ("Hatayı logla veya yönet.", "Log or handle the error."),
    ("Hata ayıklama kalıntısı.", "Leftover debugging code."),
    ("Yayından önce kaldır.", "Remove before release."),
    ("Hata ayıklama kalıntısı olabilir.", "Possible leftover debugging code."),
    ("Loglama altyapısına geç veya kaldır.", "Switch to a logging framework or remove it."),
    ("Gevşek eşitlik (==/!=).", "Loose equality (==/!=)."),
    ("=== / !== kullan.", "Use === / !==."),
    ("Değiştirilebilir varsayılan argüman.", "Mutable default argument."),
    ("None ver, işlev içinde oluştur.", "Default to None and create it inside the function."),
    ("Kabuk üzerinden komut çalıştırma.", "Command execution through a shell."),
    ("Argüman listesi ver, shell=False kullan.", "Pass an argument list and use shell=False."),
    ("Güvensiz deserialization.", "Unsafe deserialization."),
    ("yaml.safe_load / güvenilir veri kullan.", "Use yaml.safe_load / trusted data."),
    ("Debug modu açık.", "Debug mode is on."),
    ("Üretimde kapat.", "Turn it off in production."),
    ("Hassas veri tarayıcı depolamasında.", "Sensitive data in browser storage."),
    ("HttpOnly çerez kullan.", "Use an HttpOnly cookie."),
    ("target=_blank rel=noopener olmadan.", "target=_blank without rel=noopener."),
    ('rel="noopener noreferrer" ekle.', 'Add rel="noopener noreferrer".'),
    ("Karışık içerik (http betik).", "Mixed content (http script)."),
    ("https kullan.", "Use https."),
    ("WHERE'siz DELETE: tüm kayıtlar silinir.", "DELETE without WHERE: all rows are deleted."),
    ("WHERE koşulu ekle veya bilinçliyse yorumla belirt.", "Add a WHERE clause, or comment it if intentional."),
    ("WHERE'siz UPDATE: tüm kayıtlar güncellenir.", "UPDATE without WHERE: all rows are updated."),
    ("WHERE koşulu ekle.", "Add a WHERE clause."),
    ("xp_cmdshell kullanımı.", "xp_cmdshell usage."),
    ("Kapat; alternatif tasarım kullan.", "Disable it; use an alternative design."),
    ("Dinamik SQL / yıkıcı komut.", "Dynamic SQL / destructive command."),
    ("sp_executesql + parametre kullan; DROP'u onay/yedekle.", "Use sp_executesql with parameters; require approval/backup for DROP."),
    ("SELECT * veya NOLOCK.", "SELECT * or NOLOCK."),
    ("Gerekli sütunları yaz; NOLOCK kirli okumaya yol açar.", "List only the needed columns; NOLOCK allows dirty reads."),
    ("Riskli komut kalıbı.", "Risky command pattern."),
    ("Uzaktan gelen veriyi çalıştırma; izinleri daralt.", "Do not execute remote data; tighten permissions."),
    ("Yapılandırma dosyasında açık gizli değer.", "Plain-text secret in a configuration file."),
    ("Gizli depo/ortam değişkeni kullan.", "Use a secrets store/environment variable."),
    ("Bozuk Türkçe karakter (çift kodlama/mojibake) belirtisi.", "Sign of corrupted Turkish characters (double encoding/mojibake)."),
    ("Dosyayı doğru kodlamada aç, UTF-8 olarak yeniden kaydet.", "Open the file in the correct encoding and re-save it as UTF-8."),
    # analizörün sabit mesajları
    ("Kapatılmamış blok yorumu.", "Unterminated block comment."),
    ("Yorumu '*/' ile kapat.", "Close the comment with '*/'."),
    ("Kapatılmamış metin (string) sabiti.", "Unterminated string literal."),
    ("Eksik tırnağı ekle.", "Add the missing quote."),
    ("Parantez/süslü parantez eşleşmesini düzelt.", "Fix the bracket/brace matching."),
    ("Erken dönüş/yardımcı işlevlerle sadeleştir.", "Simplify with early returns/helper functions."),
    ("Kapatılmamış sunucu bloğu/yorum ('<%' veya '<!--').", "Unterminated server block/comment ('<%' or '<!--')."),
    ("Kapanış '%>' / '-->' ekle.", "Add the closing '%>' / '-->'."),
    ("Söz dizimini düzelt.", "Fix the syntax."),
    ("Dosyayı kontrol et.", "Check the file."),
    ("JSON biçimini düzelt (virgül/tırnak).", "Fix the JSON format (commas/quotes)."),
    ("Etiket kapanışlarını/özel karakterleri düzelt.", "Fix tag closings/special characters."),
    ("UTF-8 olarak yeniden kaydet.", "Re-save the file as UTF-8."),
    ("Bitir, sorun aç veya kaldır.", "Finish it, open an issue, or remove it."),
    ("Satırı böl / minified dosya mı kontrol et.", "Split the line / check whether this is a minified file."),
    ("Sorumluluklara göre dosyalara böl.", "Split into files by responsibility."),
    ("Dosyayı elle incele.", "Inspect the file manually."),
]
MSG_EN = dict(_PAIRS)

_DYN = [
    (r"^Fazladan kapatma işareti '(.)'\.$", "Unexpected closing '{0}'."),
    (r"^'(.)' kapanışı, satır (\d+) içinde açılan '(.)' ile eşleşmiyor\.$", "'{0}' does not match the '{2}' opened on line {1}."),
    (r"^Kapatılmamış '(.)' \(satır (\d+)'de açıldı\)\.$", "Unclosed '{0}' (opened on line {1})."),
    (r"^Çok derin iç içe blok \(derinlik (\d+)\)\.$", "Deeply nested block (depth {0})."),
    (r"^Python sözdizimi hatası: (.*) \(Python 3 kuralları\)\.$", "Python syntax error: {0} (Python 3 rules)."),
    (r"^Python çözümlenemedi: (.*)$", "Python could not be parsed: {0}"),
    (r"^Geçersiz JSON: (.*)$", "Invalid JSON: {0}"),
    (r"^Geçersiz XML: (.*)$", "Invalid XML: {0}"),
    (r"^Dosya UTF-8 değil \((.*) olarak okundu\)\.$", "File is not UTF-8 (read as {0})."),
    (r"^Yorumda (\w+) notu\.$", "{0} note in a comment."),
    (r"^(\d+) satır 500 karakterden uzun \(ilki satır (\d+)\)\.$", "{0} lines are longer than 500 characters (first at line {1})."),
    (r"^Dosya çok uzun \((\d+) satır\)\.$", "File is very long ({0} lines)."),
    (r"^Analiz hatası: (.*)$", "Analysis error: {0}"),
]
_DYN = [(re.compile(p, re.S), t) for p, t in _DYN]
_MORE = re.compile(r"^(.*) \(\+(\d+) yer daha, gösterilmedi\)$", re.S)


def tx(text, lang):
    """Veritabanındaki (Türkçe kaynak) bulgu metnini hedef dile çevirir; bilinmeyen metni olduğu gibi döndürür."""
    if lang != "en" or not text:
        return text
    if text in MSG_EN:
        return MSG_EN[text]
    m = _MORE.match(text)
    if m:
        return f"{tx(m.group(1), 'en')} (+{m.group(2)} more, not shown)"
    for rx, tpl in _DYN:
        m = rx.match(text)
        if m:
            return tpl.format(*m.groups())
    return text


# --------------------------------------------------------------------------
# Prompt şablonları
# --------------------------------------------------------------------------
PROMPT = {
    "tr": {
        "role": "Sen deneyimli bir kıdemli yazılım geliştirici ve kod güvenliği denetçisisin.",
        "intro": "Aşağıda \"{project}\" projesine ait `{rel}` dosyasında ({lang}) otomatik statik analizle bulunan sorunlar ve ilgili kod parçaları var.",
        "part": " (Parça {i}/{n})",
        "context": "Proje bağlamı: {note}",
        "task": "## Görev",
        "t1": "1. Her bulguyu koda bakarak doğrula. Yanlış pozitifse nedenini bir cümleyle yaz.",
        "t2": "2. Gerçek sorunlar için davranışı bozmayan, en küçük düzeltmeyi yap.",
        "t3": "3. Dosyayı baştan yazma. Her düzeltme için şu biçimi kullan: satır aralığı, ESKİ kod, YENİ kod, tek cümlelik gerekçe.",
        "t4": "4. Güvenlik düzeltmelerinde standart yöntemleri kullan (parametreli sorgu, çıktı kodlaması, gizli bilgiyi yapılandırmadan okuma).",
        "t5": "5. Burada görünmeyen kodu varsayma; gerekiyorsa hangi dosya/parçaya ihtiyacın olduğunu belirt.",
        "t6": "6. Sol taraftaki `NN|` ön ekleri satır numarasıdır; kodun parçası değildir, ESKİ/YENİ bloklarına yazma.",
        "findings": "## Bulgular",
        "line": "Satır {n}", "general": "Dosya geneli", "advice": "Öneri:",
        "code_all": "## Kod (dosyanın tamamı)",
        "code_part": "## Kod (satır {a}–{b} arası seçili bölümler)",
        "skipped": "... (satır {a}–{b} atlandı)",
        "title_all": "Parça 1/1 (tüm dosya)",
        "title_general": "Parça 1/1 (dosya geneli bulgular)",
        "title_part": "Parça {i}/{n} (satır {a}–{b})",
        "proj_role": "Sen deneyimli bir kıdemli yazılım mimarı ve güvenlik denetçisisin.",
        "proj_intro": "\"{project}\" projesinde otomatik statik analiz yapıldı. Aşağıda en riskli dosyalar ve bulgu sayıları var.",
        "proj_t1": "1. Bulgu dağılımına bakarak düzeltme önceliklerini belirle (önce kritik güvenlik, sonra hata, sonra kalite).",
        "proj_t2": "2. Bana hangi sırayla hangi dosyaları göndermem gerektiğini söyle; her dosya için kısa bir plan yaz.",
        "proj_t3": "3. Birden fazla dosyayı etkileyen ortak kök nedenleri (ör. tekrar eden SQL birleştirme deseni) tespit et ve merkezi çözüm öner.",
        "proj_files": "## En riskli dosyalar",
        "proj_head": "| Dosya | Dil | Kritik | Hata | Uyarı | Bilgi | ~Token |",
        "stale": "# UYARI: Dosya taramadan sonra değişmiş; satır numaraları kayabilir. Yeniden tarayın.",
    },
    "en": {
        "role": "You are an experienced senior software engineer and code security reviewer.",
        "intro": "Below are issues found by automated static analysis in the file `{rel}` ({lang}) of the project \"{project}\", together with the relevant code.",
        "part": " (Part {i}/{n})",
        "context": "Project context: {note}",
        "task": "## Task",
        "t1": "1. Verify each finding against the code. If it is a false positive, explain why in one sentence.",
        "t2": "2. For real issues, make the smallest fix that does not change behavior.",
        "t3": "3. Do not rewrite the whole file. For every fix use this format: line range, OLD code, NEW code, one-sentence rationale.",
        "t4": "4. For security fixes use standard techniques (parameterized queries, output encoding, reading secrets from configuration).",
        "t5": "5. Do not assume code you cannot see; if you need another file/part, say which one.",
        "t6": "6. The `NN|` prefixes on the left are line numbers, not part of the code; do not put them in the OLD/NEW blocks.",
        "findings": "## Findings",
        "line": "Line {n}", "general": "File-level", "advice": "Suggestion:",
        "code_all": "## Code (entire file)",
        "code_part": "## Code (selected sections between lines {a}–{b})",
        "skipped": "... (lines {a}–{b} skipped)",
        "title_all": "Part 1/1 (entire file)",
        "title_general": "Part 1/1 (file-level findings)",
        "title_part": "Part {i}/{n} (lines {a}–{b})",
        "proj_role": "You are an experienced senior software architect and security reviewer.",
        "proj_intro": "Automated static analysis was run on the project \"{project}\". Below are the riskiest files and their finding counts.",
        "proj_t1": "1. Using the distribution of findings, set fix priorities (critical security first, then errors, then quality).",
        "proj_t2": "2. Tell me which files I should send you and in which order; write a short plan for each file.",
        "proj_t3": "3. Identify root causes shared by several files (e.g. a repeated SQL concatenation pattern) and propose a central fix.",
        "proj_files": "## Riskiest files",
        "proj_head": "| File | Language | Critical | Error | Warning | Info | ~Tokens |",
        "stale": "# WARNING: The file changed after the scan; line numbers may be off. Please rescan.",
    },
}

REPORT = {
    "tr": {"title": "Kod Denetim Raporu", "project": "Proje", "date": "Tarih",
           "scanned": "Taranan dosya: {n} (atlanan: {s}) — tahmini token: {t}",
           "counts": "Bulgular: Kritik {c} · Hata {e} · Uyarı {w} · Bilgi {i}",
           "delta": "Önceki taramaya göre: yeni {n}, giderilen {f}",
           "fileline": "{lang} · {lines} satır · ~{tok} token · K{c} H{e} U{w} B{i}",
           "line": "satır {n}", "general": "dosya geneli", "new": "YENİ", "code": "Kod", "advice": "Öneri",
           "tokens": "Token (~)", "files": "Dosya", "index": "Prompt dizini", "idx_item": "{rel} — {title} · ~{tok} token"},
    "en": {"title": "Code Audit Report", "project": "Project", "date": "Date",
           "scanned": "Files scanned: {n} (skipped: {s}) — estimated tokens: {t}",
           "counts": "Findings: Critical {c} · Error {e} · Warning {w} · Info {i}",
           "delta": "Compared with the previous scan: {n} new, {f} fixed",
           "fileline": "{lang} · {lines} lines · ~{tok} tokens · C{c} E{e} W{w} I{i}",
           "line": "line {n}", "general": "file-level", "new": "NEW", "code": "Code", "advice": "Suggestion",
           "tokens": "Tokens (~)", "files": "Files", "index": "Prompt index", "idx_item": "{rel} — {title} · ~{tok} tokens"},
}


# --------------------------------------------------------------------------
# Arayüz metinleri
# --------------------------------------------------------------------------
_UI_TR = {
    "m_file": "Dosya", "m_pick": "Proje klasörü seç…", "m_rep_md": "Raporu kaydet (Markdown)…", "m_rep_html": "Raporu kaydet (HTML)…",
    "m_prompts": "Tüm prompt'ları dışa aktar…", "m_datadir": "Veri klasörünü aç", "m_exit": "Çıkış",
    "m_settings": "Ayarlar", "m_settings_item": "Ayarlar…", "opt_auto": "Otomatik (sistem dili)", "opt_same": "Arayüzle aynı",
    "m_help": "Yardım", "m_guide": "Kullanım kılavuzu", "m_feedback": "Hata bildir / Geri bildirim…", "m_site": "GitHub sayfası", "m_about": "Hakkında",
    "lbl_dir": "Proje klasörü:", "b_pick": "Seç…", "b_scan": "Tara", "b_stop": "Durdur",
    "f_all": "Tüm dosyalar", "f_with": "Bulgusu olanlar", "f_crit_err": "Kritik + Hata", "f_crit": "Yalnız kritik",
    "col_file": "Dosya", "col_file_short": "Dosya", "col_lang": "Dil", "col_lines": "Satır", "col_tok": "Token",
    "legend": "K = Kritik · H = Hata · U = Uyarı · B = Bilgi. Token ≈ dosyanın yaklaşık LLM token sayısı.",
    "ctx_open": "Dosyayı aç", "ctx_reveal": "Klasörde göster", "ctx_copy": "Prompt'u kopyala",
    "tab_findings": "Bulgular", "tab_crit": "Kritik hatalar", "tab_crit_n": "Kritik hatalar ({n})", "tab_prompt": "Prompt",
    "tab_summary": "Özet", "tab_history": "Geçmiş", "pick_file": "Soldan bir dosya seçin.",
    "col_sev": "Önem", "col_line": "Satır", "col_rule": "Kural", "col_desc": "Açıklama", "col_code": "Kod",
    "c_mode_crit": "Yalnız kritik", "c_mode_both": "Kritik + Hata", "c_copy": "Listeyi kopyala",
    "c_hint": "Satıra çift tıklayın: dosyası ve bulgusu açılır.", "c_count": "{n} bulgu · {f} dosya", "c_none": "Kritik bulgu yok.",
    "c_copied": "{n} bulgu panoya kopyalandı.",
    "p_copy": "Panoya kopyala", "p_save": "Kaydet…", "p_unreadable": "Dosya okunamadı: {err}",
    "p_nofind": "Bu dosyada bulgu yok; prompt gerekmiyor.", "p_tokens": "~{n} token (bütçe {b})", "p_copied": "Prompt panoya kopyalandı.",
    "ft_text": "Metin", "proj_win": "Proje düzeltme planı prompt'u", "proj_copied": "Proje prompt'u kopyalandı.",
    "note_title": "Proje notu (prompt'lara bağlam olarak eklenir)", "note_save": "Notu kaydet", "proj_prompt": "Proje özet prompt'u…",
    "note_saved": "Not kaydedildi.",
    "h_date": "Tarih", "h_files": "Dosya", "h_new": "Yeni", "h_fixed": "Giderilen", "h_open": "Taramayı aç", "h_delete": "Sil",
    "h_del_title": "Silme", "h_del_q": "Seçili tarama kaydı silinsin mi?",
    "st_ready": "Hazır.", "st_listing": "Dosyalar listeleniyor…", "st_scanning": "Taranıyor {i}/{n}: {rel}",
    "st_done": "Tarama bitti: {f} dosya, {i} bulgu (yeni {new}, giderilen {fixed}), ~{t} token.",
    "st_cancelled": "Tarama durduruldu: {f} dosya, {i} bulgu, ~{t} token.", "st_ignored": " · .kdignore ile atlanan: {n}",
    "err_scan_title": "Tarama hatası", "busy_title": "Tarama sürüyor", "busy_msg": "Dil değiştirmek için taramanın bitmesini bekleyin.",
    "dlg_pick_dir": "Proje klasörünü seçin", "no_dir_title": "Klasör yok", "no_dir_msg": "Geçerli bir proje klasörü seçin veya yazın.",
    "file_hdr": "{rel} · {lang} · {lines} satır · ~{tok} token · kodlama: {enc}",
    "d_head": "[{sev}] {rule} · satır {line}, sütun {col}", "d_new": "★ YENİ", "d_code": "Kod:", "d_fix": "Öneri:",
    "s_project": "Proje", "s_date": "Tarih", "s_files": "Taranan dosya: {n} (atlanan: {s}) · ~{t} token",
    "s_counts": "Kritik {c} · Hata {e} · Uyarı {w} · Bilgi {i}", "s_delta": "Önceki taramaya göre: yeni {n}, giderilen {f}",
    "s_rules": "En sık kurallar:", "s_langs": "Dillere göre:", "s_lang_line": "{lang}: {n} dosya, ~{t} token",
    "no_scan_title": "Tarama yok", "no_scan_msg": "Önce bir proje klasörünü tarayın.", "rep_file": "kod-denetim-raporu",
    "rep_saved": "Rapor kaydedildi: {p}", "dlg_prompts_dir": "Prompt dosyalarının yazılacağı klasör", "done_title": "Tamam",
    "prompts_done": "{n} prompt dosyası yazıldı.",
    "set_title": "Ayarlar", "set_lang": "Arayüz dili", "set_lang_h": "Menüler, listeler ve kılavuz bu dilde görünür. 'Otomatik' Windows dilini izler.",
    "set_plang": "Prompt / rapor dili", "set_plang_h": "LLM'e verilecek prompt'ların ve raporların dili. Modelin Türkçe/İngilizce başarımına göre seçin.",
    "set_budget": "Token bütçesi", "set_budget_h": "Tek bir prompt parçasının yaklaşık üst sınırı (varsayılan 6000). Küçük model/kısa bağlam için düşürün; dosya sığmazsa bulgu çevresindeki bölümler parçalara ayrılır.",
    "set_ctx": "Bağlam satırı", "set_ctx_h": "Her bulgunun üstüne ve altına eklenecek satır sayısı (varsayılan 6). Artarsa model daha çok çevre görür, token artar.",
    "set_max_kb": "Azami dosya boyutu (KB)", "set_max_kb_h": "Bundan büyük dosyalar taranmaz (üretilmiş/minified dosyaları elemek için). Varsayılan 2048.",
    "set_exclude": "Hariç tutulanlar", "set_exclude_h": "Virgülle ayrılmış klasör/dosya adları (ör. node_modules,.git,bin,obj). Proje içine .kdignore dosyası da koyabilirsiniz.",
    "bad_value_title": "Geçersiz değer", "bad_value_msg": "Bütçe ve bağlam pozitif tam sayı, boyut pozitif sayı olmalı.", "cancel": "İptal", "save": "Kaydet",
    "g_view": "Dil:", "g_title": "Kullanım kılavuzu", "g_close": "Kapat",
    "fb_title": "Hata bildir / Geri bildirim", "fb_kind": "Tür", "fb_k_bug": "Hata", "fb_k_idea": "Öneri / geliştirme", "fb_k_question": "Soru",
    "fb_subject": "Başlık", "fb_desc": "Açıklama", "fb_steps": "Tekrar adımları", "fb_diag": "Sistem bilgisini ekle (sürüm, Python, işletim sistemi; kod/dosya adı içermez)",
    "fb_preview": "Gönderilecek metin (önizleme)",
    "fb_privacy": "Gizlilik: Uygulama kendiliğinden internete bağlanmaz. 'GitHub'da aç' tarayıcınızda hazır bir kayıt sayfası açar; göndermeden önce metni siz görür ve düzenlersiniz. Gizli kod, parola veya müşteri verisi yapıştırmayın.",
    "fb_empty": "Başlık ve açıklama boş olamaz.", "fb_long": "Metin çok uzun; tam metin panoya kopyalandı. Açılan sayfaya yapıştırın.",
    "fb_copied": "Geri bildirim metni kopyalandı.", "fb_saved": "Kaydedildi: {p}", "fb_save": "Dosyaya kaydet…", "fb_copy": "Kopyala", "fb_open": "GitHub'da aç",
    "about_body": "{name} {ver}\n\nProje klasörlerindeki kodu yerelde tarar, hataları dosya dosya listeler ve LLM için token bütçeli düzeltme prompt'ları üretir.\n\nGeliştirici: Mert Bayramoğlu - Yazılım Geliştirici\nVeri klasörü: {data}\nGitHub: {url}\nLisans: MIT",
}
_UI_EN = {
    "m_file": "File", "m_pick": "Choose project folder…", "m_rep_md": "Save report (Markdown)…", "m_rep_html": "Save report (HTML)…",
    "m_prompts": "Export all prompts…", "m_datadir": "Open data folder", "m_exit": "Exit",
    "m_settings": "Settings", "m_settings_item": "Settings…", "opt_auto": "Automatic (system language)", "opt_same": "Same as interface",
    "m_help": "Help", "m_guide": "User guide", "m_feedback": "Report a problem / Feedback…", "m_site": "GitHub page", "m_about": "About",
    "lbl_dir": "Project folder:", "b_pick": "Browse…", "b_scan": "Scan", "b_stop": "Stop",
    "f_all": "All files", "f_with": "With findings", "f_crit_err": "Critical + Error", "f_crit": "Critical only",
    "col_file": "File", "col_file_short": "File", "col_lang": "Lang", "col_lines": "Lines", "col_tok": "Tokens",
    "legend": "C = Critical · E = Error · W = Warning · I = Info. Tokens ≈ approximate LLM token count of the file.",
    "ctx_open": "Open file", "ctx_reveal": "Show in folder", "ctx_copy": "Copy prompt",
    "tab_findings": "Findings", "tab_crit": "Critical issues", "tab_crit_n": "Critical issues ({n})", "tab_prompt": "Prompt",
    "tab_summary": "Summary", "tab_history": "History", "pick_file": "Select a file on the left.",
    "col_sev": "Severity", "col_line": "Line", "col_rule": "Rule", "col_desc": "Description", "col_code": "Code",
    "c_mode_crit": "Critical only", "c_mode_both": "Critical + Error", "c_copy": "Copy list",
    "c_hint": "Double-click a row to open its file and finding.", "c_count": "{n} findings · {f} files", "c_none": "No critical findings.",
    "c_copied": "{n} findings copied to the clipboard.",
    "p_copy": "Copy to clipboard", "p_save": "Save…", "p_unreadable": "Could not read file: {err}",
    "p_nofind": "No findings in this file; no prompt needed.", "p_tokens": "~{n} tokens (budget {b})", "p_copied": "Prompt copied to the clipboard.",
    "ft_text": "Text", "proj_win": "Project fix-plan prompt", "proj_copied": "Project prompt copied.",
    "note_title": "Project note (added to prompts as context)", "note_save": "Save note", "proj_prompt": "Project summary prompt…",
    "note_saved": "Note saved.",
    "h_date": "Date", "h_files": "Files", "h_new": "New", "h_fixed": "Fixed", "h_open": "Open scan", "h_delete": "Delete",
    "h_del_title": "Delete", "h_del_q": "Delete the selected scan record?",
    "st_ready": "Ready.", "st_listing": "Listing files…", "st_scanning": "Scanning {i}/{n}: {rel}",
    "st_done": "Scan finished: {f} files, {i} findings ({new} new, {fixed} fixed), ~{t} tokens.",
    "st_cancelled": "Scan stopped: {f} files, {i} findings, ~{t} tokens.", "st_ignored": " · skipped by .kdignore: {n}",
    "err_scan_title": "Scan error", "busy_title": "Scan in progress", "busy_msg": "Wait for the scan to finish before changing the language.",
    "dlg_pick_dir": "Choose the project folder", "no_dir_title": "No folder", "no_dir_msg": "Choose or type a valid project folder.",
    "file_hdr": "{rel} · {lang} · {lines} lines · ~{tok} tokens · encoding: {enc}",
    "d_head": "[{sev}] {rule} · line {line}, column {col}", "d_new": "★ NEW", "d_code": "Code:", "d_fix": "Suggestion:",
    "s_project": "Project", "s_date": "Date", "s_files": "Files scanned: {n} (skipped: {s}) · ~{t} tokens",
    "s_counts": "Critical {c} · Error {e} · Warning {w} · Info {i}", "s_delta": "Compared with the previous scan: {n} new, {f} fixed",
    "s_rules": "Most frequent rules:", "s_langs": "By language:", "s_lang_line": "{lang}: {n} files, ~{t} tokens",
    "no_scan_title": "No scan", "no_scan_msg": "Scan a project folder first.", "rep_file": "code-audit-report",
    "rep_saved": "Report saved: {p}", "dlg_prompts_dir": "Folder for the prompt files", "done_title": "Done",
    "prompts_done": "{n} prompt files written.",
    "set_title": "Settings", "set_lang": "Interface language", "set_lang_h": "Menus, lists and the guide use this language. 'Automatic' follows the Windows language.",
    "set_plang": "Prompt / report language", "set_plang_h": "Language of the prompts and reports you give to an LLM. Pick whichever your model handles best.",
    "set_budget": "Token budget", "set_budget_h": "Approximate upper limit of one prompt part (default 6000). Lower it for small models/short context; if a file does not fit, sections around findings are split into parts.",
    "set_ctx": "Context lines", "set_ctx_h": "Lines added above and below each finding (default 6). More lines give the model more surroundings but cost more tokens.",
    "set_max_kb": "Max file size (KB)", "set_max_kb_h": "Larger files are not scanned (to skip generated/minified files). Default 2048.",
    "set_exclude": "Excluded", "set_exclude_h": "Comma-separated folder/file names (e.g. node_modules,.git,bin,obj). You can also put a .kdignore file in the project.",
    "bad_value_title": "Invalid value", "bad_value_msg": "Budget and context must be positive integers, size a positive number.", "cancel": "Cancel", "save": "Save",
    "g_view": "Language:", "g_title": "User guide", "g_close": "Close",
    "fb_title": "Report a problem / Feedback", "fb_kind": "Type", "fb_k_bug": "Bug", "fb_k_idea": "Idea / enhancement", "fb_k_question": "Question",
    "fb_subject": "Title", "fb_desc": "Description", "fb_steps": "Steps to reproduce", "fb_diag": "Include system info (version, Python, OS; no code or file names)",
    "fb_preview": "Text to be sent (preview)",
    "fb_privacy": "Privacy: the app never connects to the internet by itself. 'Open on GitHub' opens a prefilled issue page in your browser; you see and can edit the text before sending. Do not paste confidential code, passwords or customer data.",
    "fb_empty": "Title and description are required.", "fb_long": "The text is too long for a link; the full text was copied to the clipboard. Paste it into the page that opens.",
    "fb_copied": "Feedback text copied.", "fb_saved": "Saved: {p}", "fb_save": "Save to file…", "fb_copy": "Copy", "fb_open": "Open on GitHub",
    "about_body": "{name} {ver}\n\nScans code in your project folders locally, lists problems file by file and builds token-budgeted fix prompts for LLMs.\n\nDeveloper: Mert Bayramoğlu - Software Developer\nData folder: {data}\nGitHub: {url}\nLicense: MIT",
}
UI = {"tr": _UI_TR, "en": _UI_EN}


def t(key, _lang, /, **kw):
    """Arayüz metni. _lang yalnızca konumsal: format alanlarında 'lang'/'key' adları kullanılabilsin."""
    s = UI.get(_lang, UI["en"]).get(key)
    if s is None:
        s = UI["en"].get(key, key)
    try:
        return s.format(**kw) if kw else s
    except (KeyError, IndexError):
        return s


# --------------------------------------------------------------------------
# Kullanım kılavuzu (uygulamada Yardım > Kullanım kılavuzu, F1)
# Her öğe: (tür, metin) — tür: h1 | h2 | p | li | code. TR ve EN aynı yapıda olmalı.
# --------------------------------------------------------------------------
GUIDE = {
    "tr": [
        ("h1", "Kod Denetçi (CodeAuditor) — Kullanım Kılavuzu"),
        ("p", "Kod Denetçi, seçtiğiniz proje klasöründeki kod dosyalarını bilgisayarınızda tarar, hataları dosya dosya listeler ve her dosya için bir yapay zekâ modeline (LLM) verebileceğiniz düzeltme prompt'u üretir. Tüm veriler yereldir; uygulama kendiliğinden internete bağlanmaz."),
        ("h2", "1. Hızlı başlangıç"),
        ("li", "Üstteki 'Seç…' ile proje klasörünü seçin (veya yolunu yazıp Enter'a basın) ve 'Tara'ya tıklayın."),
        ("li", "Soldaki listeden bir dosya seçin; sağda 'Bulgular' sekmesinde o dosyanın sorunları görünür. Bir bulguya tıklayınca açıklama, kod satırı ve öneri altta çıkar."),
        ("li", "'Prompt' sekmesinde o dosya için hazır prompt vardır. 'Panoya kopyala'yı kullanıp LLM sohbetine yapıştırın. Dosya büyükse birden çok parça üretilir; parçaları açılır listeden seçin."),
        ("li", "LLM'in verdiği ESKİ/YENİ düzeltmeleri kodunuza kendiniz uygulayın, sonra yeniden tarayın: 'Geçmiş' ve 'Özet' sekmeleri yeni ve giderilen bulguları gösterir."),
        ("h2", "2. K, H, U, B nedir? (Önem düzeyleri)"),
        ("li", "K = Kritik: Güvenlik açığı veya veri kaybı riski (SQL injection, koda gömülü parola, WHERE'siz DELETE/UPDATE, kapatılmış TLS doğrulaması…). Önce bunları düzeltin."),
        ("li", "H = Hata: Çalışmayı bozabilecek veya hatayı gizleyen sorunlar (sözdizimi hatası, kapatılmamış parantez/string, boş catch, async void…)."),
        ("li", "U = Uyarı: Riskli veya kötü pratik (zayıf özet algoritması, == kullanımı, debug kalıntısı…). Hemen bozmaz ama bakım/güvenlik maliyeti vardır."),
        ("li", "B = Bilgi: Düşük öncelikli notlar (TODO/FIXME, çok uzun satır/dosya, derin iç içe blok)."),
        ("p", "Dosya listesinde ve tablolarda bu harfler sayı olarak görünür (ör. K2 H5 = 2 kritik, 5 hata). İngilizce arayüzde karşılıkları C/E/W/I'dır (Critical/Error/Warning/Info). Satırdaki ★ işareti, önceki taramada olmayan YENİ bulgudur."),
        ("h2", "3. Token nedir?"),
        ("p", "LLM'ler metni 'token' denen parçalarla okur (kabaca bir kelime parçası; kodda bir sözcük, sayı veya işaret). Her modelin tek seferde alabileceği token sınırı vardır. Bu yüzden büyük dosyayı bütün olarak yapıştırmak çoğu zaman sığmaz veya kaliteyi düşürür."),
        ("p", "Kod Denetçi her dosyanın yaklaşık token sayısını hesaplar ('Token' sütunu) ve prompt'ları 'Token bütçesi' ayarına göre böler: dosya sığıyorsa tamamı, sığmıyorsa yalnızca bulguların çevresindeki bölümler parçalara paketlenir. Sayılar tahminidir (±%15); modelden modele değişir."),
        ("h2", "4. Ayarlar (Ayarlar > Ayarlar…)"),
        ("li", "Arayüz dili: Menü, liste ve kılavuz dili. 'Otomatik' Windows dilini izler. Değişiklik hemen uygulanır."),
        ("li", "Prompt / rapor dili: LLM'e verilecek prompt'ların ve raporların dili. 'Arayüzle aynı' ya da Türkçe/English. Kullandığınız model hangi dilde daha iyiyse onu seçin."),
        ("li", "Token bütçesi (varsayılan 6000): Bir prompt parçasının yaklaşık üst sınırı. Küçük model veya kısa bağlam penceresi için düşürün (ör. 3000), büyük bağlamlı modelde artırın."),
        ("li", "Bağlam satırı (varsayılan 6): Her bulgunun üstüne/altına eklenen kod satırı sayısı. Artarsa model çevreyi daha iyi görür ama token artar."),
        ("li", "Azami dosya boyutu KB (varsayılan 2048): Bundan büyük dosyalar atlanır (üretilmiş, minified, yedek dosyaları elemek için)."),
        ("li", "Hariç tutulanlar: Virgülle ayrılmış klasör/dosya adları (node_modules, .git, bin, obj…). Proje köküne .kdignore dosyası koyarak desen bazlı (gitignore benzeri) dışlama da yapabilirsiniz."),
        ("h2", "5. Ekranlar ve alanlar"),
        ("li", "Üst çubuk: Proje klasörü, Seç…, Tara, Durdur. İlerleme çubuğu taranan dosya sayısını gösterir."),
        ("li", "Sol liste: Dosyalar, dil, satır sayısı, token ve K/H/U/B sayıları. Üstteki filtre ve arama kutusu listeyi daraltır. Çift tık dosyayı açar (betik/HTML dosyaları çalıştırılmaz, Not Defteri'nde açılır). Sağ tık: klasörde göster, prompt kopyala."),
        ("li", "Bulgular sekmesi: Seçili dosyanın sorunları ve altta ayrıntı (kural kodu, satır/sütun, kod parçası, öneri)."),
        ("li", "Kritik hatalar sekmesi: Tüm projedeki kritik (isteğe bağlı kritik+hata) bulguların tek listesi. Çift tıklayınca ilgili dosya ve bulguya gider; 'Listeyi kopyala' hepsini panoya alır."),
        ("li", "Prompt sekmesi: Seçili dosyanın prompt parçaları, token sayısı, kopyala ve kaydet düğmeleri."),
        ("li", "Özet sekmesi: Tarama sayıları, en sık kurallar, dillere göre dağılım ve Proje notu. Not, tüm prompt'lara bağlam olarak eklenir (ör. 'ASP.NET WebForms, SQL Server, .NET 4.8'). 'Proje özet prompt'u' en riskli dosyalar için genel bir düzeltme planı ister."),
        ("li", "Geçmiş sekmesi: Önceki taramalar; açma ve silme."),
        ("li", "Dosya menüsü: Raporu Markdown/HTML kaydet, tüm prompt'ları klasöre aktar, veri klasörünü aç."),
        ("h2", "6. Yanlış pozitifleri susturma"),
        ("li", "Satır sonuna yorum olarak kd-ignore yazarsanız (ör. // kd-ignore gerekçe) o satırdaki bulgular gösterilmez."),
        ("li", "Dosya veya klasörü tümden atlamak için proje köküne .kdignore yazın (her satıra bir desen, # yorum)."),
        ("p", "Statik analiz kesin hüküm vermez: bulgu yanlış pozitif olabilir. Prompt'taki 1. adım LLM'den bulguyu doğrulamasını ister; düzeltmeyi uygulamadan önce siz de kontrol edin."),
        ("h2", "7. Gizlilik ve güvenlik"),
        ("li", "Tarama, veritabanı (SQLite) ve raporlar yalnızca bilgisayarınızdaki 'veri' klasöründedir. Bu klasörü GitHub'a göndermeyin (.gitignore bunu engeller)."),
        ("li", "Prompt'lar kodunuzun parçalarını içerir. Bir buluta/LLM'e yapıştırmadan önce parola, anahtar ve müşteri verisi olmadığından emin olun; şirket politikanıza uyun."),
        ("li", "Kod Denetçi taradığınız dosyaları çalıştırmaz ve değiştirmez."),
        ("h2", "8. Hata bildirme ve geri bildirim"),
        ("p", "Yardım > Hata bildir / Geri bildirim… penceresinden hata, öneri veya soru gönderebilirsiniz. Tür seçin, başlık ve açıklama yazın; hatalar için tekrar adımlarını ekleyin. İsteğe bağlı sistem bilgisi yalnızca sürüm, Python ve işletim sistemini içerir — kod veya dosya adı içermez. Alttaki önizleme, gönderilecek metnin aynısıdır."),
        ("li", "'GitHub'da aç': Tarayıcıda hazır doldurulmuş bir kayıt (issue) sayfası açılır; siz kontrol edip gönderirsiniz. GitHub hesabı gerekir."),
        ("li", "'Kopyala' / 'Dosyaya kaydet': GitHub kullanmadan e-posta veya başka kanaldan iletmek için."),
        ("li", "Güvenlik açığı bulduysanız herkese açık kayıt açmayın; SECURITY.md'deki özel bildirim yolunu kullanın."),
        ("h2", "9. Komut satırı ve ipuçları"),
        ("code", "KodDenetci.py --cli <klasör> [--prompts <çıktı klasörü>] [--lang tr|en]"),
        ("li", "Arayüzsüz çalışır; CI veya toplu denetim için uygundur."),
        ("li", "Çalıştırmak için Calistir.bat'a çift tıklayın (Python 3.9+ ve tkinter gerekir)."),
        ("li", "Önce Kritik hatalar sekmesini temizleyin, sonra Hata, sonra Uyarı."),
        ("li", "Çok büyük projede önce en riskli 10 dosyayla başlayın; 'Proje özet prompt'u' sırayı önerir."),
    ],
    "en": [
        ("h1", "CodeAuditor (Kod Denetçi) — User Guide"),
        ("p", "CodeAuditor scans the code files in a project folder on your computer, lists the problems file by file and builds a fix prompt for each file that you can give to an AI model (LLM). All data stays local; the app never connects to the internet by itself."),
        ("h2", "1. Quick start"),
        ("li", "Click 'Browse…' to pick the project folder (or type the path and press Enter), then click 'Scan'."),
        ("li", "Select a file in the left list; its problems appear on the 'Findings' tab. Click a finding to see the description, code line and suggestion below."),
        ("li", "The 'Prompt' tab holds a ready prompt for that file. Use 'Copy to clipboard' and paste it into your LLM chat. Large files produce several parts; choose them in the drop-down."),
        ("li", "Apply the OLD/NEW fixes the LLM returns to your code yourself, then rescan: the 'History' and 'Summary' tabs show new and fixed findings."),
        ("h2", "2. What are C, E, W, I? (Severity levels; K, H, U, B in Turkish)"),
        ("li", "C = Critical (K): Security hole or data-loss risk (SQL injection, hard-coded password, DELETE/UPDATE without WHERE, disabled TLS validation…). Fix these first."),
        ("li", "E = Error (H): Problems that can break execution or hide failures (syntax error, unterminated bracket/string, empty catch, async void…)."),
        ("li", "W = Warning (U): Risky or poor practice (weak hash, ==, leftover debug code…). Not breaking now, but costs maintenance/security."),
        ("li", "I = Info (B): Low-priority notes (TODO/FIXME, very long line/file, deep nesting)."),
        ("p", "In the file list and tables these letters appear as counts (e.g. C2 E5 = 2 critical, 5 errors). The ★ mark on a row means a NEW finding that was not in the previous scan."),
        ("h2", "3. What is a token?"),
        ("p", "LLMs read text in pieces called 'tokens' (roughly a word fragment; in code a word, number or symbol). Every model can take only a limited number of tokens at once, so pasting a whole large file often does not fit or lowers quality."),
        ("p", "CodeAuditor estimates each file's token count (the 'Tokens' column) and splits prompts by the 'Token budget' setting: the whole file if it fits, otherwise only the sections around findings are packed into parts. Numbers are estimates (±15%) and vary by model."),
        ("h2", "4. Settings (Settings > Settings…)"),
        ("li", "Interface language: language of menus, lists and the guide. 'Automatic' follows the Windows language. Applied immediately."),
        ("li", "Prompt / report language: language of the prompts and reports you give to an LLM. 'Same as interface', Türkçe or English. Pick whichever your model handles best."),
        ("li", "Token budget (default 6000): approximate upper limit of one prompt part. Lower it for small models or short context windows (e.g. 3000); raise it for large-context models."),
        ("li", "Context lines (default 6): code lines added above/below each finding. More lines let the model see the surroundings but cost more tokens."),
        ("li", "Max file size KB (default 2048): larger files are skipped (to drop generated, minified and backup files)."),
        ("li", "Excluded: comma-separated folder/file names (node_modules, .git, bin, obj…). For pattern-based (gitignore-like) exclusion put a .kdignore file in the project root."),
        ("h2", "5. Screens and fields"),
        ("li", "Top bar: project folder, Browse…, Scan, Stop. The progress bar shows scanned files."),
        ("li", "Left list: files with language, line count, tokens and C/E/W/I counts. The filter and search box narrow the list. Double-click opens the file (scripts/HTML are not executed; they open in Notepad). Right-click: show in folder, copy prompt."),
        ("li", "Findings tab: the selected file's problems, with details below (rule code, line/column, code snippet, suggestion)."),
        ("li", "Critical issues tab: one list of all critical (optionally critical+error) findings in the project. Double-click jumps to the file and finding; 'Copy list' puts them all on the clipboard."),
        ("li", "Prompt tab: the selected file's prompt parts, token count, copy and save buttons."),
        ("li", "Summary tab: scan counts, most frequent rules, language breakdown and the Project note. The note is added to every prompt as context (e.g. 'ASP.NET WebForms, SQL Server, .NET 4.8'). 'Project summary prompt' asks for an overall fix plan for the riskiest files."),
        ("li", "History tab: earlier scans; open and delete."),
        ("li", "File menu: save report as Markdown/HTML, export all prompts to a folder, open the data folder."),
        ("h2", "6. Silencing false positives"),
        ("li", "Put kd-ignore in a comment at the end of a line (e.g. // kd-ignore reason) and findings on that line are hidden."),
        ("li", "To skip files or folders entirely, add a .kdignore file in the project root (one pattern per line, # for comments)."),
        ("p", "Static analysis is not a verdict: a finding can be a false positive. Step 1 of every prompt asks the LLM to verify the finding; please check fixes yourself before applying them."),
        ("h2", "7. Privacy and security"),
        ("li", "Scans, the database (SQLite) and reports live only in the 'veri' folder on your computer. Do not push this folder to GitHub (.gitignore prevents it)."),
        ("li", "Prompts contain pieces of your code. Before pasting into a cloud service/LLM make sure there are no passwords, keys or customer data, and follow your company policy."),
        ("li", "CodeAuditor never executes or modifies the files it scans."),
        ("h2", "8. Reporting problems and feedback"),
        ("p", "Use Help > Report a problem / Feedback… to send a bug, idea or question. Choose the type, write a title and description; for bugs add steps to reproduce. The optional system info contains only the version, Python and OS — no code or file names. The preview below is exactly the text that will be sent."),
        ("li", "'Open on GitHub': opens a prefilled issue page in your browser; you review and submit it. A GitHub account is required."),
        ("li", "'Copy' / 'Save to file': to send it by e-mail or another channel without GitHub."),
        ("li", "If you found a security vulnerability, do not open a public issue; use the private reporting route in SECURITY.md."),
        ("h2", "9. Command line and tips"),
        ("code", "KodDenetci.py --cli <folder> [--prompts <output folder>] [--lang tr|en]"),
        ("li", "Runs without the GUI; good for CI or batch audits."),
        ("li", "Double-click Calistir.bat to start the app (needs Python 3.9+ with tkinter)."),
        ("li", "Clear the Critical issues tab first, then Errors, then Warnings."),
        ("li", "In a very large project start with the 10 riskiest files; the 'Project summary prompt' suggests the order."),
    ],
}
