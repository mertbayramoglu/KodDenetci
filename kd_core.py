# -*- coding: utf-8 -*-
"""
kd_core.py - Kod Denetçi çekirdeği
  * Tokenizer (dil ailesine göre sözcük çözümleyici)
  * Statik analiz kuralları (yerel, internetsiz)
  * SQLite veritabanı (yerel)
  * Token bütçeli prompt üretici
Yalnızca Python standart kütüphanesini kullanır.
"""
import os, re, sys, json, ast, time, hashlib, sqlite3, bisect, fnmatch

import kd_i18n as i18n
from xml.etree import ElementTree as ET

APP_NAME = "Kod Denetçi"          # İngilizce ad: CodeAuditor (bkz. kd_i18n.APP_NAME)
APP_VER = "1.2.0"
REPO_URL = "https://github.com/mertbayramoglu/KodDenetci"

SEV_ORDER = {"critical": 0, "error": 1, "warning": 2, "info": 3}
SEV_TR = {"critical": "Kritik", "error": "Hata", "warning": "Uyarı", "info": "Bilgi"}
SEV_W = {"critical": 10, "error": 5, "warning": 2, "info": 0.5}

LANG_LABEL = {
    "cs": "C#", "js": "JavaScript/TypeScript", "clike": "C-tabanlı", "php": "PHP",
    "python": "Python", "sql": "SQL", "vb": "VB/VBScript", "css": "CSS/SCSS",
    "markup": "HTML/ASPX/Razor", "json": "JSON", "xml": "XML/Config",
    "script": "Betik (ps1/sh/bat)", "config": "Yapılandırma (yml/ini/env)",
}

# --------------------------------------------------------------------------
# Yollar
# --------------------------------------------------------------------------
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Taşınabilir: uygulamanın yanındaki 'veri' klasörü; yazılamazsa LOCALAPPDATA."""
    base = os.path.join(app_dir(), "veri")
    try:
        os.makedirs(base, exist_ok=True)
        t = os.path.join(base, ".w")
        with open(t, "w") as f:
            f.write("1")
        os.remove(t)
        return base
    except OSError:
        alt = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "KodDenetci")
        os.makedirs(alt, exist_ok=True)
        return alt


def db_path():
    return os.path.join(data_dir(), "kod_denetci.db")


# --------------------------------------------------------------------------
# Veritabanı
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS projects(path TEXT PRIMARY KEY, note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS scans(
  id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, started REAL, finished REAL,
  n_files INTEGER DEFAULT 0, n_issues INTEGER DEFAULT 0, tokens INTEGER DEFAULT 0,
  crit INTEGER DEFAULT 0, err INTEGER DEFAULT 0, warn INTEGER DEFAULT 0, info INTEGER DEFAULT 0,
  new_issues INTEGER DEFAULT 0, fixed_issues INTEGER DEFAULT 0, skipped INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY AUTOINCREMENT, scan_id INTEGER, rel TEXT, lang TEXT,
  lines INTEGER, tokens INTEGER, size INTEGER, sha1 TEXT, risk REAL,
  c INTEGER, e INTEGER, w INTEGER, i INTEGER, enc TEXT);
CREATE TABLE IF NOT EXISTS issues(
  id INTEGER PRIMARY KEY AUTOINCREMENT, file_id INTEGER, scan_id INTEGER, line INTEGER,
  col INTEGER, severity TEXT, rule TEXT, message TEXT, fix TEXT, snippet TEXT,
  fp TEXT, isnew INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_issues_file ON issues(file_id);
CREATE INDEX IF NOT EXISTS ix_issues_scan ON issues(scan_id);
CREATE INDEX IF NOT EXISTS ix_files_scan ON files(scan_id);
"""

DEFAULT_SETTINGS = {
    "budget": "6000",          # prompt parçası başına token bütçesi
    "ctx": "6",                # bulgu çevresi bağlam satırı
    "max_kb": "2048",          # bundan büyük dosyalar atlanır
    "exclude": "node_modules,.git,.svn,.hg,bin,obj,packages,vendor,dist,build,.vs,__pycache__,.idea,.vscode,TestResults,.nuget,_ReSharper.Caches",
    "last_dir": "",
    "lang": "auto",            # arayüz dili: auto | tr | en
    "prompt_lang": "auto",     # prompt/rapor dili: auto (arayüzle aynı) | tr | en
}


def open_db(path=None):
    conn = sqlite3.connect(path or db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_settings(conn):
    s = dict(DEFAULT_SETTINGS)
    for r in conn.execute("SELECT key,value FROM settings"):
        s[r["key"]] = r["value"]
    return s


def set_setting(conn, key, value):
    conn.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, str(value)))
    conn.commit()


def get_note(conn, project):
    r = conn.execute("SELECT note FROM projects WHERE path=?", (project,)).fetchone()
    return r["note"] if r else ""


def set_note(conn, project, note):
    conn.execute("INSERT INTO projects(path,note) VALUES(?,?) ON CONFLICT(path) DO UPDATE SET note=excluded.note",
                 (project, note))
    conn.commit()


def delete_scan(conn, scan_id):
    conn.execute("DELETE FROM issues WHERE scan_id=?", (scan_id,))
    conn.execute("DELETE FROM files WHERE scan_id=?", (scan_id,))
    conn.execute("DELETE FROM scans WHERE id=?", (scan_id,))
    conn.commit()


# --------------------------------------------------------------------------
# Dil tablosu
# --------------------------------------------------------------------------
EXT_LANG = {
    ".cs": "cs", ".ashx": "cs",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js",
    ".java": "clike", ".kt": "clike", ".go": "clike", ".swift": "clike", ".c": "clike", ".cpp": "clike",
    ".cc": "clike", ".h": "clike", ".hpp": "clike", ".rs": "clike", ".scala": "clike", ".dart": "clike",
    ".php": "php", ".py": "python", ".sql": "sql",
    ".vb": "vb", ".vbs": "vb", ".bas": "vb", ".cls": "vb",
    ".css": "css", ".scss": "css", ".less": "css",
    ".html": "markup", ".htm": "markup", ".aspx": "markup", ".ascx": "markup", ".master": "markup",
    ".cshtml": "markup", ".vbhtml": "markup", ".razor": "markup", ".asax": "markup", ".asmx": "markup",
    ".asp": "markup",
    ".json": "json",
    ".xml": "xml", ".config": "xml", ".csproj": "xml", ".vbproj": "xml", ".resx": "xml", ".xaml": "xml",
    ".svg": "xml", ".props": "xml", ".targets": "xml", ".nuspec": "xml", ".sitemap": "xml",
    ".ps1": "script", ".sh": "script", ".bat": "script", ".cmd": "script",
    ".yml": "config", ".yaml": "config", ".ini": "config", ".toml": "config", ".env": "config",
    ".htaccess": "config",
}
VENDOR_RE = re.compile(r"^(jquery|bootstrap|angular|moment|modernizr|knockout|respond|popper|select2|"
                       r"datatables|fontawesome|font-awesome|ckeditor|tinymce|chart|lodash|underscore|"
                       r"react|vue|d3|three|highcharts)[\w.\-]*\.(js|css)$", re.I)


def lang_of(name):
    low = name.lower()
    if low.endswith((".min.js", ".min.css", ".bundle.js", ".map")):
        return None
    if VENDOR_RE.match(low):
        return None
    ext = os.path.splitext(low)[1]
    return EXT_LANG.get(ext) or EXT_LANG.get(low)


# --------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------
# Her dil ailesi için tek bir ana düzenli ifade kurulur; belirteç türleri:
# ws, comment, string, number, ident, br (parantez), op, html (PHP dışı metin), tag, server
_NUM = r"(?P<number>0[xX][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?[A-Za-z]*)"
_IDENT = r"(?P<ident>[$@]?[^\W\d]\w*)"
_BR = r"(?P<br>[{}()\[\]])"
_OP = r"(?P<op>[<>=!+\-*/&|^]=|&&|\|\||\+\+|--|=>|->|::|\?\?|\*\*|<<|>>|[^\w\s])"
_WS = r"(?P<ws>\s+)"
_CB = r"(?P<comment_b>/\*(?:.*?(?P<e_cb>\*/)|.*))"
_CL = r"(?P<comment_l>//[^\n]*)"
_CH = r"(?P<comment_h>\#[^\n]*)"
_DQ = r'(?P<str_dq>"(?:\\.|[^"\\\n])*(?P<e_dq>")?)'
_SQ = r"(?P<str_sq>'(?:\\.|[^'\\\n])*(?P<e_sq>')?)"
_DQML = r'(?P<str_dq>"(?:\\.|[^"\\])*(?P<e_dq>")?)'
_SQML = r"(?P<str_sq>'(?:\\.|[^'\\])*(?P<e_sq>')?)"
_BQ = r"(?P<str_bq>`(?:\\.|[^`\\])*(?P<e_bq>`)?)"
_VERB = r'(?P<str_vb>(?:\$@|@\$|@)"(?:""|[^"])*(?P<e_vb>")?)'
_TQ = r"""(?P<str_tq>(?P<tq>\"\"\"|''').*?(?:(?P=tq)(?P<e_tq>)|\Z))"""
_HD = r"""(?P<str_hd><<<[ \t]*(?P<hq>['"]?)(?P<hid>\w+)(?P=hq)\r?\n.*?\n[ \t]*(?P=hid)\b(?P<e_hd>))"""
_SQLSQ = r"(?P<str_sq>'(?:''|[^'])*(?P<e_sq>')?)"
_SQLDQ = r'(?P<str_dq>"(?:""|[^"])*(?P<e_dq>")?)'
_VBDQ = r'(?P<str_dq>"(?:""|[^"\n])*(?P<e_dq>")?)'
_SQLBR = r"(?P<ident_br>\[[^\]\n]*\])"
_URL = r"(?P<str_url>(?i:url)\((?!\s*[\"'])[^)\n]*\))"
_SQLC = r"(?P<comment_s>--[^\n]*)"
_VBC = r"(?P<comment_v>'[^\n]*|\bRem\b[^\n]*)"


def _compile(*parts):
    return re.compile("|".join(parts), re.S)


MASTER = {
    "clike": _compile(_WS, _CB, _CL, _DQ, _SQ, _NUM, _IDENT, _BR, _OP),
    "cs": _compile(_WS, _CB, _CL, _VERB, _DQ, _SQ, _NUM, _IDENT, _BR, _OP),
    "js": _compile(_WS, _CB, _CL, _DQ, _SQ, _BQ, _NUM, _IDENT, _BR, _OP),
    "php": _compile(_WS, _CB, _CL, _CH, _HD, _DQML, _SQML, _NUM, _IDENT, _BR, _OP),
    "python": _compile(_WS, _CH, _TQ, _DQ, _SQ, _NUM, _IDENT, _BR, _OP),
    "sql": _compile(_WS, _SQLC, _CB, _SQLSQ, _SQLDQ, _SQLBR, _NUM, _IDENT, _BR, _OP),
    "vb": _compile(_WS, _VBC, _VBDQ, _NUM, _IDENT, _BR, _OP),
    "css": _compile(_WS, _CB, _URL, _DQ, _SQ, _NUM, _IDENT, _BR, _OP),
    "script": _compile(_WS, _CH, _DQML, _SQML, _NUM, _IDENT, _BR, _OP),
}
JS_REGEX = re.compile(r"/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[a-z]*")
_REGEX_PREV_OK = {"return", "typeof", "case", "in", "of", "delete", "void", "throw", "new", "yield", "await", "else", "do"}
_REGEX_PREV_OPS = set("([{,;:=!&|?+-*%<>~^")


def _lex_loop(text, pos, end, master, toks, lang, php_close=False):
    match = master.match
    prev = None  # son anlamlı belirtecin metni (JS regex ayrımı için)
    while pos < end:
        if php_close and text.startswith("?>", pos):
            toks.append(("op", pos, pos + 2, False))
            return pos + 2
        if lang == "js" and text[pos] == "/" and pos + 1 < end and text[pos + 1] not in "/*":
            if prev is None or prev in _REGEX_PREV_OPS or prev in _REGEX_PREV_OK:
                rm = JS_REGEX.match(text, pos, end)
                if rm:
                    toks.append(("string", pos, rm.end(), False))
                    prev = "x"
                    pos = rm.end()
                    continue
        m = match(text, pos, end)
        if not m:
            pos += 1
            continue
        g = m.lastgroup
        e = m.end()
        if e == pos:      # güvenlik: sonsuz döngüyü önle
            e = pos + 1
        if g == "ws":
            pos = e
            continue
        if g.startswith("comment"):
            bad = g == "comment_b" and not m.group("e_cb")
            toks.append(("comment", pos, e, bad))
        elif g.startswith("str"):
            eg = "e_" + g[4:]
            bad = eg in m.re.groupindex and m.group(eg) is None
            toks.append(("string", pos, e, bad))
            prev = "x"
        elif g in ("ident", "ident_br"):
            toks.append(("ident", pos, e, False))
            if lang == "js":
                prev = text[pos:e]
        elif g == "number":
            toks.append(("number", pos, e, False))
            prev = "x"
        else:
            toks.append((g, pos, e, False))
            if lang == "js":
                prev = text[pos:e] if g == "op" else (text[pos] if text[pos] in "([{" else "x")
        pos = e
    return pos


_PHP_OPEN = re.compile(r"<\?(?:php\b|=)?")
_MK_RE = re.compile(
    r"(?P<comment_h><!--(?:.*?(?P<e_h>-->)|.*))|(?P<comment_a><%--(?:.*?(?P<e_a>--%>)|.*))"
    r"|(?P<server><%(?:.*?(?P<e_s>%>)|.*))|(?P<tag><[A-Za-z/!][^<>]*>)|(?P<text>[^<]+|<)", re.S)


def tokenize(text, lang):
    toks = []
    n = len(text)
    if lang == "php":
        pos = 0
        while pos < n:
            m = _PHP_OPEN.search(text, pos)
            if not m:
                toks.append(("html", pos, n, False))
                break
            if m.start() > pos:
                toks.append(("html", pos, m.start(), False))
            toks.append(("op", m.start(), m.end(), False))
            pos = _lex_loop(text, m.end(), n, MASTER["php"], toks, "php", php_close=True)
    elif lang == "markup":
        for m in _MK_RE.finditer(text):
            g = m.lastgroup
            if g in ("comment_h", "comment_a"):
                eg = "e_h" if g == "comment_h" else "e_a"
                toks.append(("comment", m.start(), m.end(), m.group(eg) is None))
            elif g == "server":
                toks.append(("server", m.start(), m.end(), m.group("e_s") is None))
            else:
                toks.append((g, m.start(), m.end(), False))
    elif lang in MASTER:
        _lex_loop(text, 0, n, MASTER[lang], toks, lang)
    return toks


def _est(kind, length):
    if kind in ("ident", "number"):
        return max(1, -(-length // 5))
    if kind in ("string", "comment", "html", "text", "tag", "server"):
        return max(1, -(-length // 4))
    return 1


def line_token_counts(toks, line_starts, nlines, text, lang):
    """Satır başına tahmini LLM token sayısı (belirteçlerden)."""
    lt = [1] * (nlines + 2)
    if not toks:       # sözcük çözümlenmeyen diller: karakter tahmini
        ls = text.split("\n")
        for i, l in enumerate(ls[:nlines + 1]):
            lt[i] = 1 + -(-len(l) // 4)
        return lt
    ln = 0
    for k, s, e, _ in toks:
        while ln + 1 < len(line_starts) and line_starts[ln + 1] <= s:
            ln += 1
        if k in ("string", "comment", "html", "text", "server") and e - s > 200:
            # çok satırlı büyük belirteç: satırlara dağıt
            chunk = text[s:e].split("\n")
            for j, c in enumerate(chunk):
                if ln + j < len(lt):
                    lt[ln + j] += _est(k, len(c))
        elif ln < len(lt):
            lt[ln] += _est(k, e - s)
    return lt


TOKEN_PIECE = re.compile(r"\w+|[^\w\s]", re.U)


def est_text(s):
    """Serbest metin için tahmini token sayısı."""
    n = 0
    for p in TOKEN_PIECE.findall(s):
        n += 1 if len(p) <= 6 else -(-len(p) // 4)
    return n


# --------------------------------------------------------------------------
# Kurallar
# --------------------------------------------------------------------------
CODE_LANGS = {"cs", "js", "clike", "php", "python", "vb"}
ALLTXT = CODE_LANGS | {"sql", "markup", "xml", "json", "config", "script", "css"}
RULES = []


def R(rid, sev, langs, target, pat, msg, fix, flags=re.I, cap=25):
    RULES.append(dict(id=rid, sev=sev, langs=set(langs), target=target,
                      rx=re.compile(pat, flags | re.M), msg=msg, fix=fix, cap=cap))


_SQLSTART = r"\b(?:select\b[^\n]*?\bfrom\b|insert\s+into\b|update\s+[\w\[\].]+\s+set\b|delete\s+from\b)"
_DQ_SQL = r'"[^"\n]*?' + _SQLSTART + r'[^"\n]*"'
_SQ_SQL = r"'[^'\n]*?" + _SQLSTART + r"[^'\n]*'"
SQLI_MSG = "SQL sorgusu metin birleştirme/enterpolasyonla kuruluyor (SQL injection riski)."
SQLI_FIX = "Parametreli sorgu kullan (SqlParameter / PDO prepared statement / ? parametreleri). Kullanıcı girdisini asla sorgu metnine ekleme."

R("SQL001", "critical", {"cs", "vb", "js", "clike", "python", "markup"}, "nocomment",
  "(?:" + _DQ_SQL + "|" + _SQ_SQL + r")\s*[+&]\s*[\w$@(]", SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"php"}, "nocomment",
  "(?:" + _DQ_SQL + "|" + _SQ_SQL + r")\s*\.\s*\$", SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"php"}, "nocomment",
  r'"[^"\n]*?' + _SQLSTART + r'[^"\n]*\$\w+', SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"cs", "markup"}, "nocomment",
  r'(?:\$@?|@\$)"[^"\n]*?' + _SQLSTART + r'[^"\n]*\{', SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"cs"}, "nocomment",
  r'\bstring\.Format\s*\(\s*@?"[^"\n]*?' + _SQLSTART + r'[^"\n]*\{\d', SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"python"}, "nocomment",
  r'\bf(?:"[^"\n]*?' + _SQLSTART + r'[^"\n]*\{|\'[^\'\n]*?' + _SQLSTART + r'[^\'\n]*\{)', SQLI_MSG, SQLI_FIX)
R("SQL001", "critical", {"js"}, "nocomment",
  r"`[^`]*?" + _SQLSTART + r"[^`]*\$\{", SQLI_MSG, SQLI_FIX)

R("SEC001", "critical", ALLTXT - {"css"}, "nocomment",
  r"\b\w*(?:password|passwd|pwd|secret|apikey|api_key|access_token|auth_token|private_key|client_secret)\w*[\"']?\s*(?:=|:|=>)\s*@?[\"'](?![^\"'\n]*(?:\{\{|\$\{|%s|%\(|\{0\}))[^\"'\n]{3,}[\"']",
  "Koda gömülü parola/gizli anahtar bulundu.",
  "Gizli bilgiyi koddan çıkar: ortam değişkeni, kullanıcı gizli deposu (secrets), şifreli yapılandırma bölümü veya anahtar kasası kullan. Sızmış olabileceği için parolayı değiştir.")
R("SEC001", "critical", CODE_LANGS | {"sql"}, "nocomment",
  r"[\"';](?:password|pwd)=[^;\"'\s{}$@%<][^;\"']*",
  "Bağlantı metninde açık parola var.", "Bağlantı bilgisini yapılandırma/gizli depoya taşı; Integrated Security veya şifreli connectionStrings kullan.")
R("SEC001", "critical", {"xml", "json", "config", "markup"}, "nocomment",
  r"\b(?:password|pwd)=[^;\"'\s{}$@%<&][^;\"'<]*",
  "Yapılandırmada/bağlantı metninde açık parola var.", "Parolayı yapılandırma şifreleme (aspnet_regiis) veya ortam değişkeni/gizli depo ile sakla.")
R("SEC001", "critical", {"xml"}, "nocomment",
  r"key\s*=\s*\"[^\"]*(?:password|pwd|secret|apikey)[^\"]*\"\s+value\s*=\s*\"[^\"]{3,}\"",
  "appSettings içinde açık gizli değer var.", "Değeri şifrele veya gizli depoya taşı.")
R("SEC002", "critical", ALLTXT, "raw",
  r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bxox[baprs]-[A-Za-z0-9-]{10,}|\bAIza[0-9A-Za-z\-_]{35}\b",
  "Özel anahtar / bulut-API token'ı dosyada açıkta.", "Anahtarı hemen iptal et/yenile ve depodan temizle (geçmişi de).", flags=0)
R("SEC003", "critical", {"php"}, "nocomment",
  r"\b(?:include|require)(?:_once)?\b[^;\n]*\$_(?:GET|POST|REQUEST|COOKIE)\b",
  "Kullanıcı girdisiyle dosya dahil etme (LFI/RFI).", "Dahil edilecek dosyayı beyaz listeden seç; girdiyi doğrudan yola koyma.")
R("SEC004", "critical", {"php"}, "nocomment",
  r"\b(?:mysqli?_query|pg_query|sqlsrv_query|->query|->exec|->prepare)\s*\([^;\n]*\$_(?:GET|POST|REQUEST|COOKIE)\b",
  "İstek verisi doğrudan sorguya giriyor.", "PDO/mysqli prepared statement + bind kullan.")
R("SEC004", "critical", {"php"}, "code", r"\bextract\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)",
  "extract() ile istek değişkenleri üzerine yazılabilir.", "extract() kullanma; alanları tek tek ve doğrulayarak al.")
R("XSS001", "error", {"php"}, "nocomment",
  r"\b(?:echo|print)\b(?![^;\n]*(?:htmlspecialchars|htmlentities|intval|\(int\)|esc_))[^;\n]*\$_(?:GET|POST|REQUEST|COOKIE)\b",
  "İstek verisi kodlanmadan çıktıya yazılıyor (XSS).", "htmlspecialchars($x, ENT_QUOTES, 'UTF-8') ile kodla.")
R("XSS001", "error", {"cs", "vb", "markup"}, "nocomment", r"\bResponse\.Write\s*\(\s*Request(?:\.|\[|\()",
  "İstek verisi kodlanmadan Response.Write ile yazılıyor (XSS).", "Server.HtmlEncode / HttpUtility.HtmlEncode veya <%: %> kullan.")
R("XSS001", "error", {"markup"}, "nocomment", r"<%=\s*Request\b",
  "İstek verisi <%= %> ile kodlanmadan basılıyor (XSS).", "<%: ... %> (kodlamalı) veya HtmlEncode kullan.")
R("XSS002", "warning", {"js"}, "code", r"\.innerHTML\s*\+?=|\bdocument\.write(?:ln)?\s*\(|\bdangerouslySetInnerHTML\b|\.insertAdjacentHTML\s*\(",
  "Ham HTML ekleme (XSS riski).", "textContent kullan veya girdiyi DOMPurify gibi bir araçla temizle.")
R("XSS002", "warning", {"js"}, "nocomment", r"\bset(?:Timeout|Interval)\s*\(\s*[\"']",
  "setTimeout/setInterval içine metin verilmiş (örtük eval).", "Metin yerine fonksiyon geçir.")
R("EVAL01", "error", {"js", "php"}, "code", r"\beval\s*\(|\bnew\s+Function\s*\(",
  "eval/Function ile dinamik kod çalıştırma.", "Dinamik kod çalıştırmayı kaldır; JSON.parse / veri tabanlı yaklaşım kullan.")
R("EVAL01", "error", {"python"}, "code", r"\b(?:eval|exec)\s*\(",
  "eval/exec ile dinamik kod çalıştırma.", "ast.literal_eval veya açık bir ayrıştırıcı kullan.")
R("CRY001", "warning", {"cs"}, "code",
  r"\b(?:MD5|SHA1)(?:CryptoServiceProvider|Managed|Cng)\b|\b(?:MD5|SHA1)\.Create\b",
  "Zayıf özet algoritması (MD5/SHA1).", "Parola için bcrypt/Argon2/PBKDF2; bütünlük için SHA-256+.")
R("CRY001", "warning", {"php"}, "code", r"\b(?:md5|sha1)\s*\(", "Zayıf özet algoritması (md5/sha1).",
  "Parola için password_hash()/password_verify() kullan.")
R("CRY001", "warning", {"python"}, "code", r"\bhashlib\.(?:md5|sha1)\b(?!\s*\([^)]*usedforsecurity\s*=\s*False)", "Zayıf özet algoritması.", "SHA-256+ ya da parola için bcrypt/argon2.")
R("CRY001", "warning", {"js"}, "nocomment", r"createHash\s*\(\s*[\"'](?:md5|sha1)[\"']", "Zayıf özet algoritması.", "SHA-256+ kullan.")
R("TLS001", "error", {"cs"}, "code",
  r"ServerCertificateValidationCallback\s*\+?=\s*(?:\([^)]*\)\s*=>\s*true|delegate\s*\([^)]*\)\s*\{\s*return\s+true)",
  "TLS sertifika doğrulaması kapatılmış.", "Doğrulamayı geri aç; geçerli sertifika kur.")
R("TLS001", "error", {"php"}, "code", r"CURLOPT_SSL_VERIFY(?:PEER|HOST)\s*,\s*(?:false|0)\b",
  "TLS doğrulaması kapatılmış.", "CURLOPT_SSL_VERIFYPEER=true, VERIFYHOST=2.")
R("TLS001", "error", {"python"}, "code", r"\bverify\s*=\s*False\b", "TLS doğrulaması kapatılmış.", "verify=True (veya CA yolu ver).")
R("TLS001", "error", {"js"}, "code", r"\brejectUnauthorized\s*:\s*false\b", "TLS doğrulaması kapatılmış.", "rejectUnauthorized: true.")
R("CFG001", "warning", {"xml"}, "nocomment", r"customErrors\s+mode\s*=\s*\"Off\"",
  "customErrors kapalı: hata ayrıntıları kullanıcıya sızar.", "mode=\"RemoteOnly\" veya \"On\" yap.")
R("CFG001", "warning", {"xml"}, "nocomment", r"<compilation\b[^>]*\bdebug\s*=\s*\"true\"",
  "Üretimde debug=\"true\" performans/güvenlik sorunudur.", "Yayında debug=\"false\" yap.")
R("CFG001", "error", {"xml", "markup"}, "nocomment", r"\bvalidateRequest\s*=\s*\"false\"|requestValidationMode\s*=\s*\"2\.0\"",
  "İstek doğrulaması (XSS koruması) kapatılmış.", "ValidateRequest'i açık tut; gereken alanı ayrıca doğrula/kodla.")
R("CFG001", "critical", {"xml", "markup"}, "nocomment", r"\benableViewStateMac\s*=\s*\"false\"",
  "ViewState MAC kapalı.", "enableViewStateMac=\"true\".")
R("CFG001", "warning", {"xml"}, "nocomment", r"<trust\s+level\s*=\s*\"Full\"", "Tam güven düzeyi.", "Gerekmiyorsa daha düşük güven düzeyi kullan.")
R("CFG001", "info", {"xml"}, "nocomment", r"\brequireSSL\s*=\s*\"false\"", "Çerez/form için SSL zorunlu değil.", "requireSSL=\"true\".")
R("CORS01", "warning", ALLTXT, "nocomment", r"Access-Control-Allow-Origin[\"']?\s*[:,=]\s*[\"']?\*|\bAllowAnyOrigin\s*\(",
  "CORS tüm kaynaklara açık.", "İzin verilen kaynakları açıkça listele.")
R("PHP001", "error", {"php"}, "code",
  r"\bmysql_(?:query|connect|pconnect|fetch_\w+|escape_string|real_escape_string|num_rows|select_db|result|close|error|insert_id)\s*\(",
  "Kaldırılmış mysql_* işlevleri kullanılıyor.", "PDO veya mysqli + prepared statement'a geç.")
R("PHP002", "warning", {"php"}, "code", r"\b(?:shell_exec|passthru|system|popen|proc_open|exec|pcntl_exec)\s*\(|\bunserialize\s*\(",
  "Komut çalıştırma / güvensiz deserialization.", "Girdiyi doğrula, escapeshellarg kullan; unserialize yerine json_decode.")
R("PHP002", "warning", {"php"}, "nocomment", r"ini_set\s*\(\s*['\"]display_errors['\"]\s*,\s*['\"]?(?:1|on|true)",
  "display_errors açık: hata ayrıntıları sızar.", "Üretimde kapat, hataları log'a yaz.")
R("PHP003", "info", {"php"}, "code", r"\bmove_uploaded_file\s*\(",
  "Dosya yükleme noktası.", "Uzantı/MIME/boyut doğrula, rastgele ad kullan, yükleme klasöründe betik çalıştırmayı kapat.")
R("CS001", "warning", {"cs"}, "code", r"\bthrow\s+(?:ex|e|exception|err)\s*;",
  "'throw ex;' yığın izini siler.", "'throw;' kullan.")
R("CS002", "warning", {"cs"}, "code", r"\basync\s+void\s+\w+\s*\((?![^)]*\bsender\b)",
  "async void: hatalar yakalanamaz.", "async Task döndür (yalnızca olay işleyicilerde async void).")
R("CS002", "warning", {"cs"}, "code", r"\.GetAwaiter\(\)\s*\.GetResult\(\)|\.Wait\s*\(\s*\)",
  "Eşzamanlı bekleme: deadlock riski.", "async/await'i baştan sona kullan.")
R("CS003", "warning", {"cs", "vb"}, "code",
  r"^(?!.*\busing\b).*\b(?P<hit>new\s+(?:SqlConnection|OleDbConnection|OdbcConnection|MySqlConnection|SqlCommand|StreamReader|StreamWriter|FileStream)\s*\()",
  "IDisposable nesne using ile sarılmamış olabilir.", "using (...) { } ile sar; bağlantı sızıntısını önle.")
R("CS004", "warning", {"cs", "vb"}, "code", r"(?:Int32\.Parse|Int64\.Parse|Convert\.ToInt\d*|Convert\.ToDecimal)\s*\(\s*Request[.\[]",
  "İstek verisi doğrulamasız dönüştürülüyor (hata/istisna).", "TryParse kullan, hatalı girdiyi yönet.")
R("CS005", "info", {"cs"}, "code", r"\bProcess\.Start\s*\(", "Dış süreç başlatma.", "Argümanlara kullanıcı girdisi karıştırma.")
R("VB001", "warning", {"vb"}, "code", r"\bOn\s+Error\s+Resume\s+Next\b",
  "Hatalar sessizce yutuluyor.", "Try/Catch (VB.NET) veya hedefli On Error GoTo kullan.")
R("QLT001", "warning", {"cs", "js", "clike", "php"}, "code", r"\bcatch\b\s*(?:\([^)]*\))?\s*\{\s*\}",
  "Boş catch bloğu: hata sessizce yutuluyor.", "En azından logla; beklenen istisnayı daralt, gerisini yeniden fırlat.")
R("QLT001", "warning", {"python"}, "code", r"\bexcept\s*:|\bexcept\s+(?:Base)?Exception(?:\s+as\s+\w+)?\s*:\s*\n\s*pass\b",
  "Boş/çıplak except.", "Belirli istisnayı yakala ve logla.")
R("QLT001", "warning", {"vb"}, "code", r"\bCatch\b[^\n]*\n\s*End\s+Try\b", "Boş Catch bloğu.", "Hatayı logla veya yönet.")
R("QLT002", "info", {"js"}, "code", r"\bconsole\.(?:log|debug)\s*\(|\bdebugger\b", "Hata ayıklama kalıntısı.", "Yayından önce kaldır.")
R("QLT002", "info", {"php"}, "code", r"\b(?:var_dump|print_r|var_export)\s*\(", "Hata ayıklama kalıntısı.", "Yayından önce kaldır.")
R("QLT002", "info", {"cs"}, "code", r"\bConsole\.WriteLine\s*\(|\bDebug\.WriteLine\s*\(", "Hata ayıklama kalıntısı olabilir.", "Loglama altyapısına geç veya kaldır.")
R("QLT003", "info", {"js"}, "code", r"(?<![=!<>+\-*/%&|^])==(?!=)|!=(?!=)", "Gevşek eşitlik (==/!=).", "=== / !== kullan.", cap=10)
R("QLT004", "warning", {"python"}, "code", r"\bdef\s+\w+\s*\([^)]*=\s*(?:\[\s*\]|\{\s*\}|dict\(\)|list\(\))",
  "Değiştirilebilir varsayılan argüman.", "None ver, işlev içinde oluştur.")
R("QLT004", "warning", {"python"}, "code", r"\bsubprocess\.\w+\([^)]*shell\s*=\s*True|\bos\.system\s*\(",
  "Kabuk üzerinden komut çalıştırma.", "Argüman listesi ver, shell=False kullan.")
R("QLT004", "warning", {"python"}, "code", r"\bpickle\.loads?\s*\(|\byaml\.load\s*\((?![^)]*Loader)",
  "Güvensiz deserialization.", "yaml.safe_load / güvenilir veri kullan.")
R("QLT004", "warning", {"python"}, "code", r"\.run\s*\([^)]*debug\s*=\s*True", "Debug modu açık.", "Üretimde kapat.")
R("QLT005", "warning", {"js"}, "nocomment", r"\b(?:local|session)Storage\.setItem\s*\(\s*[\"'][^\"']*(?:token|password|secret)",
  "Hassas veri tarayıcı depolamasında.", "HttpOnly çerez kullan.")
R("QLT006", "info", {"markup"}, "nocomment", r"target\s*=\s*\"_blank\"(?![^>]*noopener)",
  "target=_blank rel=noopener olmadan.", "rel=\"noopener noreferrer\" ekle.")
R("QLT006", "info", {"markup"}, "nocomment", r"<script[^>]+src\s*=\s*[\"']http://", "Karışık içerik (http betik).", "https kullan.")
R("SQLX01", "warning", {"sql"}, "nocomment",
  r"\bdelete\s+from\s+[\w\[\]\.#@]+\s*(?=;|\bgo\b|\Z)",
  "WHERE'siz DELETE: tüm kayıtlar silinir.", "WHERE koşulu ekle veya bilinçliyse yorumla belirt.", flags=re.I | re.S)
R("SQLX01", "warning", {"sql"}, "nocomment",
  r"\bupdate\s+[\w\[\]\.#@]+\s+set\b(?:(?!\bwhere\b|;|\bgo\b).)*(?=;|\bgo\b|\Z)",
  "WHERE'siz UPDATE: tüm kayıtlar güncellenir.", "WHERE koşulu ekle.", flags=re.I | re.S)
R("SQLX02", "error", {"sql"}, "nocomment", r"\bxp_cmdshell\b", "xp_cmdshell kullanımı.", "Kapat; alternatif tasarım kullan.")
R("SQLX02", "warning", {"sql"}, "nocomment", r"\bexec(?:ute)?\s*\(\s*@|\bdrop\s+(?:table|database)\b",
  "Dinamik SQL / yıkıcı komut.", "sp_executesql + parametre kullan; DROP'u onay/yedekle.")
R("SQLX03", "info", {"sql"}, "nocomment", r"\bselect\s+\*|\bwith\s*\(\s*nolock\s*\)",
  "SELECT * veya NOLOCK.", "Gerekli sütunları yaz; NOLOCK kirli okumaya yol açar.", cap=10)
R("SCR001", "warning", {"script"}, "nocomment",
  r"\bInvoke-Expression\b|\biex\b\s|ConvertTo-SecureString\s+[^|\n]*-AsPlainText|curl[^\n]*\|\s*(?:sh|bash)\b|\bchmod\s+777\b",
  "Riskli komut kalıbı.", "Uzaktan gelen veriyi çalıştırma; izinleri daralt.")
R("CFG002", "critical", {"config"}, "nocomment",
  r"^\s*[\w.\-]*(?:password|passwd|pwd|secret|api[_-]?key|token|private[_-]?key)[\w.\-]*\s*[:=]\s*(?!\s*$)(?![\"']?\s*(?:\$\{|%|<|\{\{|changeme))[\"']?[^\s\"'#]{3,}",
  "Yapılandırma dosyasında açık gizli değer.", "Gizli depo/ortam değişkeni kullan.")
R("ENC001", "warning", ALLTXT, "raw", r"Ã[¼§¶œ‡–]|Ä[±°Ÿ]|Å[Ÿž]|Ã\x9c|Ã\x87|Ã\x96|Ä\x9f|Ä\x9e|Ä±|Å\x9f",  # kd-ignore (kuralın kendi deseni)
  "Bozuk Türkçe karakter (çift kodlama/mojibake) belirtisi.", "Dosyayı doğru kodlamada aç, UTF-8 olarak yeniden kaydet.", flags=0, cap=5)

KD_IGNORE = "kd-ignore"


# --------------------------------------------------------------------------
# Analiz
# --------------------------------------------------------------------------
def _blank(text, ranges):
    """Verilen aralıkları boşlukla değiştirir (satır sonlarını korur)."""
    if not ranges:
        return text
    out, last = [], 0
    for s, e in ranges:
        out.append(text[last:s])
        out.append(re.sub(r"[^\r\n]", " ", text[s:e]))
        last = e
    out.append(text[last:])
    return "".join(out)


_XML_COMMENT = re.compile(r"<!--.*?-->", re.S)


def build_views(text, toks, lang):
    if lang in ("xml",):
        rng = [(m.start(), m.end()) for m in _XML_COMMENT.finditer(text)]
        v = _blank(text, rng)
        return {"raw": text, "nocomment": v, "code": v}
    if lang in ("json", "config"):
        return {"raw": text, "nocomment": text, "code": text}
    if lang == "markup":
        rng = [(s, e) for k, s, e, _ in toks if k == "comment"]
        v = _blank(text, rng)
        return {"raw": text, "nocomment": v, "code": v}
    com = [(s, e) for k, s, e, _ in toks if k == "comment"]
    cs = [(s, e) for k, s, e, _ in toks if k in ("comment", "string", "html")]
    return {"raw": text, "nocomment": _blank(text, [(s, e) for k, s, e, _ in toks if k in ("comment", "html")]),
            "code": _blank(text, cs)}


_PAIR = {")": "(", "]": "[", "}": "{"}


def check_brackets(text, toks, line_of, parens_only=False):
    """(sorunlar, azami_süslü_parantez_derinliği, satırı)"""
    stack, out, bd, maxd, maxl = [], [], 0, 0, 0
    for k, s, e, _ in toks:
        if k != "br":
            continue
        ch = text[s]
        if ch in "([{":
            if parens_only and ch != "(":
                continue
            stack.append((ch, s))
            if ch == "{":
                bd += 1
                if bd > maxd:
                    maxd, maxl = bd, line_of(s)
        else:
            if parens_only and ch != ")":
                continue
            if not stack:
                out.append((s, f"Fazladan kapatma işareti '{ch}'."))
                return out, maxd, maxl
            if stack[-1][0] != _PAIR[ch]:
                o, os_ = stack[-1]
                out.append((s, f"'{ch}' kapanışı, satır {line_of(os_)} içinde açılan '{o}' ile eşleşmiyor."))
                return out, maxd, maxl
            if stack.pop()[0] == "{":
                bd = max(0, bd - 1)
    for o, os_ in list(reversed(stack))[:3]:
        out.append((os_, f"Kapatılmamış '{o}' (satır {line_of(os_)}'de açıldı)."))
    return out, maxd, maxl


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):      # SSMS vb. UTF-16 BOM'lu dosyalar
        try:
            return raw.decode("utf-16"), "utf-16", raw
        except UnicodeDecodeError:
            return None, None, raw
    if b"\x00" in raw[:8000]:
        return None, None, raw
    for enc, label in (("utf-8-sig", "utf-8"), ("cp1254", "cp1254")):
        try:
            return raw.decode(enc), label, raw
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1", raw


def _mk(sev, rule, msg, fix, line, col, snippet):
    return dict(severity=sev, rule=rule, message=msg, fix=fix, line=line, col=col, snippet=snippet)


def analyze_text(text, lang, enc="utf-8"):
    """Metni çözümler; (issues, metrics) döndürür. Dosya erişimi yok (test edilebilir)."""
    issues = []
    lines = text.split("\n")
    nl = len(lines)
    line_starts = [0]
    for m in re.finditer("\n", text):
        line_starts.append(m.end())

    def line_of(off):
        return bisect.bisect_right(line_starts, off)

    def snip(ln):
        if 1 <= ln <= nl:
            return lines[ln - 1].strip()[:220]
        return ""

    def col_of(off):
        return off - line_starts[line_of(off) - 1] + 1

    toks = tokenize(text, lang)
    strict = True

    # --- sözdizimi ----------------------------------------------------
    if lang in ("cs", "js", "clike", "php", "css", "sql", "vb"):
        for k, s, e, bad in toks:
            if not bad:
                continue
            if k == "comment":
                issues.append(_mk("error", "SYN001", "Kapatılmamış blok yorumu.", "Yorumu '*/' ile kapat.", line_of(s), col_of(s), snip(line_of(s))))
            elif k == "string":
                q = text[s]
                if q == '"' or lang in ("js", "php", "python", "sql"):
                    issues.append(_mk("error", "SYN002", "Kapatılmamış metin (string) sabiti.", "Eksik tırnağı ekle.", line_of(s), col_of(s), snip(line_of(s))))
        if lang in ("cs", "js", "clike", "php", "css", "sql", "vb"):
            br, maxd, maxl = check_brackets(text, toks, line_of, parens_only=lang in ("sql", "vb"))
            sev = "error"
            for off, msg in br:
                issues.append(_mk(sev, "SYN003", msg, "Parantez/süslü parantez eşleşmesini düzelt.", line_of(off), col_of(off), snip(line_of(off))))
            if maxd > 8:
                issues.append(_mk("warning", "QLT007", f"Çok derin iç içe blok (derinlik {maxd}).", "Erken dönüş/yardımcı işlevlerle sadeleştir.", maxl, 1, snip(maxl)))
    if lang == "markup":
        for k, s, e, bad in toks:
            if bad and k in ("server", "comment"):
                issues.append(_mk("error", "SYN004", "Kapatılmamış sunucu bloğu/yorum ('<%' veya '<!--').", "Kapanış '%>' / '-->' ekle.", line_of(s), col_of(s), snip(line_of(s))))
    if lang == "python":
        try:
            ast.parse(text)
        except SyntaxError as ex:
            ln = ex.lineno or 1
            issues.append(_mk("error", "SYN005", f"Python sözdizimi hatası: {ex.msg} (Python 3 kuralları).", "Söz dizimini düzelt.", ln, ex.offset or 1, snip(ln)))
        except (ValueError, RecursionError) as ex:
            issues.append(_mk("warning", "SYN005", f"Python çözümlenemedi: {ex}", "Dosyayı kontrol et.", 1, 1, ""))
    if lang == "json":
        try:
            json.loads(text)
        except ValueError as ex:
            ln = getattr(ex, "lineno", 1)
            issues.append(_mk("error", "SYN006", f"Geçersiz JSON: {getattr(ex, 'msg', ex)}", "JSON biçimini düzelt (virgül/tırnak).", ln, getattr(ex, "colno", 1), snip(ln)))
    if lang == "xml":
        try:
            ET.fromstring(text)
        except ET.ParseError as ex:
            ln, col = ex.position if hasattr(ex, "position") else (1, 0)
            issues.append(_mk("error", "SYN007", f"Geçersiz XML: {ex}", "Etiket kapanışlarını/özel karakterleri düzelt.", ln, col + 1, snip(ln)))
        except ValueError:      # ör. çözümlenemeyen kodlama bildirimi: sözdizimi hatası sayma
            pass

    if enc not in ("utf-8", None):
        issues.append(_mk("info", "ENC002", f"Dosya UTF-8 değil ({enc} olarak okundu).", "UTF-8 olarak yeniden kaydet.", 0, 0, ""))

    # --- kural taraması -------------------------------------------------
    views = build_views(text, toks, lang)
    counts = {}
    for r in RULES:
        if lang not in r["langs"]:
            continue
        v = views[r["target"]]
        for m in r["rx"].finditer(v):
            off = m.start("hit") if "hit" in r["rx"].groupindex and m.group("hit") else m.start()
            ln = line_of(off)
            key = (r["id"], r["msg"])
            counts[key] = counts.get(key, 0) + 1
            if counts[key] > r["cap"]:
                continue
            issues.append(_mk(r["sev"], r["id"], r["msg"], r["fix"], ln, col_of(off), snip(ln)))
        if counts.get((r["id"], r["msg"]), 0) > r["cap"]:
            n = counts[(r["id"], r["msg"])]
            issues.append(_mk("info", r["id"], f"{r['msg']} (+{n - r['cap']} yer daha, gösterilmedi)", r["fix"], 0, 0, ""))

    # --- yorumlardaki görev etiketleri ---------------------------------------
    todo = re.compile(r"\b(TODO|FIXME|HACK|XXX|BUG)\b")
    tcount = 0
    for k, s, e, _ in toks:
        if k == "comment":
            mm = todo.search(text, s, e)
            if mm:
                tcount += 1
                if tcount <= 15:
                    ln = line_of(mm.start())
                    issues.append(_mk("info", "TODO01", f"Yorumda {mm.group(1)} notu.", "Bitir, sorun aç veya kaldır.", ln, col_of(mm.start()), snip(ln)))

    # --- uzunluk ölçütleri --------------------------------------------
    if lang not in ("json", "xml", "markup", "config"):
        longl = [i + 1 for i, l in enumerate(lines) if len(l) > 500]
        if longl:
            issues.append(_mk("info", "QLT008", f"{len(longl)} satır 500 karakterden uzun (ilki satır {longl[0]}).", "Satırı böl / minified dosya mı kontrol et.", longl[0], 1, snip(longl[0])[:120]))
    if nl > 1500:
        issues.append(_mk("info", "QLT009", f"Dosya çok uzun ({nl} satır).", "Sorumluluklara göre dosyalara böl.", 0, 0, ""))

    # --- kd-ignore bastırma + tekilleştirme ----------------------------
    clean, seen = [], set()
    for it in issues:
        ln = it["line"]
        if 1 <= ln <= nl and KD_IGNORE in lines[ln - 1]:
            continue
        key = (it["rule"], it["line"], it["message"])
        if key in seen:
            continue
        seen.add(key)
        clean.append(it)
    clean.sort(key=lambda x: (x["line"] == 0, x["line"], SEV_ORDER[x["severity"]]))
    clean = clean[:300]

    lt = line_token_counts(toks, line_starts, nl, text, lang)
    metrics = dict(lines=nl, tokens=sum(lt), line_tokens=lt, ntoks=len(toks))
    return clean, metrics


RISKY_OPEN_EXT = {".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh", ".hta", ".ps1", ".psm1", ".msi",
                  ".exe", ".com", ".scr", ".jar", ".lnk", ".reg", ".sh", ".html", ".htm", ".svg"}


def is_risky_to_open(path):
    """Çift tıklamayla çalıştırılabilecek/tarayıcıda betik yürütebilecek dosya mı?
    Taranan (güvenilmeyen) projeden gelen bu dosyalar varsayılan uygulamayla değil metin düzenleyiciyle açılmalı."""
    return os.path.splitext(path)[1].lower() in RISKY_OPEN_EXT


def sha1_of(raw):
    return hashlib.sha1(raw, usedforsecurity=False).hexdigest()


def fingerprint(rel, it):
    norm = re.sub(r"\s+", " ", it["snippet"])
    data = f"{rel}|{it['rule']}|{it['message']}|{norm}".encode("utf-8", "replace")
    return hashlib.sha1(data, usedforsecurity=False).hexdigest()[:16]


def load_ignore(root):
    """Proje kökündeki .kdignore dosyasını okur (gitignore benzeri, basit):
    'klasor/' -> klasör (yol içeriyorsa köke göre, içermiyorsa her derinlikte ad eşleşmesi),
    '*.generated.cs' / 'yol/dosya.cs' -> dosya deseni, '#' yorum satırı."""
    pats = []
    try:
        with open(os.path.join(root, ".kdignore"), encoding="utf-8-sig") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    pats.append(line.replace("\\", "/").lower())
    except OSError:
        pass
    return pats


def _ignored(rel, pats, is_dir):
    rel = rel.lower()
    base = rel.rsplit("/", 1)[-1]
    for p in pats:
        if p.endswith("/"):
            d = p.rstrip("/").lstrip("/")
            if "/" in d:
                if rel == d or rel.startswith(d + "/"):
                    return True
            elif is_dir and fnmatch.fnmatchcase(base, d):
                return True
        else:
            q = p.lstrip("/")
            if fnmatch.fnmatchcase(rel, q) or ("/" not in q and fnmatch.fnmatchcase(base, q)):
                return True
    return False


def collect_files(root, settings):
    excl = {x.strip().lower() for x in settings.get("exclude", "").split(",") if x.strip()}
    max_b = int(float(settings.get("max_kb", "2048")) * 1024)
    pats = load_ignore(root)
    found, skipped, ignored = [], 0, 0
    for d, dirs, files in os.walk(root):
        reld = os.path.relpath(d, root).replace(os.sep, "/")
        keep = []
        for x in dirs:
            if x.lower() in excl:
                continue
            if pats and _ignored(x if reld == "." else reld + "/" + x, pats, True):
                ignored += 1
                continue
            keep.append(x)
        dirs[:] = keep
        for f in files:
            lang = lang_of(f)
            if not lang:
                continue
            if pats and _ignored(f if reld == "." else reld + "/" + f, pats, False):
                ignored += 1
                continue
            full = os.path.join(d, f)
            try:
                if os.path.getsize(full) > max_b:
                    skipped += 1
                    continue
            except OSError:
                continue
            found.append((full, os.path.relpath(full, root), lang))
    found.sort(key=lambda x: x[1].lower())
    return found, skipped, ignored


def scan_project(root, conn, settings, progress=None, cancel=None):
    """Projeyi tarar, sonuçları veritabanına yazar. Özet sözlüğü döndürür."""
    files, skipped, ignored = collect_files(root, settings)
    prev = conn.execute("SELECT id FROM scans WHERE project=? ORDER BY id DESC LIMIT 1", (root,)).fetchone()
    prev_fps = set()
    if prev:
        prev_fps = {r[0] for r in conn.execute("SELECT fp FROM issues WHERE scan_id=?", (prev["id"],))}
    cur = conn.execute("INSERT INTO scans(project,started) VALUES(?,?)", (root, time.time()))
    sid = cur.lastrowid
    tot = dict(c=0, e=0, w=0, i=0, tokens=0, issues=0, new=0)
    cur_fps = set()
    for idx, (full, rel, lang) in enumerate(files):
        if cancel is not None and cancel.is_set():
            break
        if progress:
            progress(idx + 1, len(files), rel)
        try:
            text, enc, raw = read_text(full)
        except OSError:
            skipped += 1
            continue
        if text is None:
            skipped += 1
            continue
        try:
            iss, met = analyze_text(text, lang, enc)
        except Exception as ex:   # tek dosya taramayı durdurmasın
            iss = [_mk("warning", "ERR000", f"Analiz hatası: {ex}", "Dosyayı elle incele.", 0, 0, "")]
            met = dict(lines=text.count("\n") + 1, tokens=est_text(text))
        cnt = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        for it in iss:
            cnt[it["severity"]] += 1
        risk = sum(SEV_W[it["severity"]] for it in iss)
        fc = conn.execute(
            "INSERT INTO files(scan_id,rel,lang,lines,tokens,size,sha1,risk,c,e,w,i,enc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, rel, lang, met["lines"], met["tokens"], len(raw), sha1_of(raw), risk,
             cnt["critical"], cnt["error"], cnt["warning"], cnt["info"], enc))
        fid = fc.lastrowid
        rows = []
        for it in iss:
            fp = fingerprint(rel, it)
            cur_fps.add(fp)
            isnew = 1 if (prev and fp not in prev_fps) else 0
            tot["new"] += isnew
            rows.append((fid, sid, it["line"], it["col"], it["severity"], it["rule"], it["message"], it["fix"], it["snippet"], fp, isnew))
        conn.executemany("INSERT INTO issues(file_id,scan_id,line,col,severity,rule,message,fix,snippet,fp,isnew) VALUES(?,?,?,?,?,?,?,?,?,?,?)", rows)
        tot["c"] += cnt["critical"]; tot["e"] += cnt["error"]; tot["w"] += cnt["warning"]; tot["i"] += cnt["info"]
        tot["tokens"] += met["tokens"]; tot["issues"] += len(iss)
    cancelled = cancel is not None and cancel.is_set()
    fixed = len(prev_fps - cur_fps) if (prev and not cancelled) else 0   # kısmi taramada "giderilen" hesaplanmaz
    nfiles = conn.execute("SELECT COUNT(*) FROM files WHERE scan_id=?", (sid,)).fetchone()[0]
    conn.execute("UPDATE scans SET finished=?,n_files=?,n_issues=?,tokens=?,crit=?,err=?,warn=?,info=?,new_issues=?,fixed_issues=?,skipped=? WHERE id=?",
                 (time.time(), nfiles, tot["issues"], tot["tokens"], tot["c"], tot["e"], tot["w"], tot["i"],
                  tot["new"], fixed, skipped, sid))
    conn.commit()
    return dict(scan_id=sid, files=nfiles, skipped=skipped, ignored=ignored, fixed=fixed, cancelled=cancelled, **tot)


# --------------------------------------------------------------------------
# Prompt üretici (token bütçeli)
# --------------------------------------------------------------------------
def _sevmin(iss):
    return min(SEV_ORDER[i["severity"]] for i in iss)


def build_prompts(project_name, rel, lang, text, issues, budget=6000, ctx=6, note="", ui="tr"):
    """Dosya için bir veya daha fazla prompt parçası döndürür (ui: prompt dili 'tr'|'en').
    Her parça yaklaşık 'budget' tokenı aşmaz; bulgu çevresindeki pencereler öncelik sırasıyla paketlenir."""
    P = i18n.PROMPT[ui]
    toks = tokenize(text, lang)
    lines = text.split("\n")
    n = len(lines)
    line_starts = [0]
    for m in re.finditer("\n", text):
        line_starts.append(m.end())
    lt = line_token_counts(toks, line_starts, n, text, lang)

    def cost(a, b):
        return sum(lt[a - 1:b]) + 2 * (b - a + 1)

    head = 520 + est_text(note) + est_text(rel)
    iss = sorted(issues, key=lambda x: (SEV_ORDER[x["severity"]], x["line"]))
    avail = max(900, budget - head - 45 * min(len(iss), 25))
    lang_tag = {"cs": "csharp", "js": "javascript", "php": "php", "python": "python", "sql": "sql", "vb": "vbnet",
                "markup": "html", "json": "json", "xml": "xml", "css": "css", "script": "powershell",
                "clike": "", "config": ""}.get(lang, "")
    sev_names = i18n.SEV[ui]
    lang_label = i18n.LANG_LABEL[ui].get(lang, lang)

    def render(part_no, total, windows, part_issues, whole):
        out = [P["role"]]
        out.append(P["intro"].format(project=project_name, rel=rel, lang=lang_label)
                   + (P["part"].format(i=part_no, n=total) if total > 1 else ""))
        if note.strip():
            out += ["", P["context"].format(note=note.strip())]
        out += ["", P["task"], P["t1"], P["t2"], P["t3"], P["t4"], P["t5"], P["t6"], "", P["findings"]]
        for i, it in enumerate(part_issues, 1):
            where = P["line"].format(n=it["line"]) if it["line"] else P["general"]
            out.append(f"{i}. [{sev_names[it['severity']]}] {where} — {it['rule']}: {i18n.tx(it['message'], ui)}")
            if it.get("fix"):
                out.append(f"   {P['advice']} {i18n.tx(it['fix'], ui)}")
        out.append("")
        a0 = windows[0][0] if windows else 1
        b0 = windows[-1][1] if windows else 1
        out.append(P["code_all"] if whole else P["code_part"].format(a=a0, b=b0))
        out.append("```" + lang_tag)
        prev_end = 0
        w = len(str(n))
        for a, b in windows:
            if prev_end and a > prev_end + 1:
                out.append(f"{' ' * w}| " + P["skipped"].format(a=prev_end + 1, b=a - 1))
            for ln in range(a, b + 1):
                out.append(f"{str(ln).rjust(w)}| {lines[ln - 1].rstrip()}")
            prev_end = b
        out.append("```")
        return "\n".join(out)

    # tüm dosya sığıyor mu?
    if cost(1, n) <= avail:
        txt = render(1, 1, [(1, n)], iss, True)
        return [dict(title=P["title_all"], text=txt, tokens=est_text(txt), lines=(1, n))]

    # pencereler
    wins = []
    for it in iss:
        if it["line"] <= 0:
            continue
        a, b = max(1, it["line"] - ctx), min(n, it["line"] + ctx)
        wins.append([a, b, [it]])
    wins.sort(key=lambda w: w[0])
    merged = []
    for a, b, its in wins:
        if merged and a <= merged[-1][1] + 2:
            merged[-1][1] = max(merged[-1][1], b)
            merged[-1][2].extend(its)
        else:
            merged.append([a, b, list(its)])
    for w in merged:      # tek pencere bütçeyi aşıyorsa ilk bulgu çevresinde daralt
        if cost(w[0], w[1]) > avail:
            c = w[2][0]["line"]
            a, b = c, c
            while True:
                grew = False
                if a > w[0] and cost(a - 1, b) <= avail:
                    a -= 1
                    grew = True
                if b < w[1] and cost(a, b + 1) <= avail:
                    b += 1
                    grew = True
                if not grew:
                    break
            w[0], w[1] = a, b
            w[2] = [i for i in w[2] if a <= i["line"] <= b] or w[2][:1]
    merged.sort(key=lambda w: (_sevmin(w[2]), w[0]))
    parts, cur, cc = [], [], 0
    for w in merged:
        c = cost(w[0], w[1])
        if cur and cc + c > avail:
            parts.append(cur)
            cur, cc = [], 0
        cur.append(w)
        cc += c
    if cur:
        parts.append(cur)
    general = [i for i in iss if i["line"] <= 0]
    if not parts:
        txt = render(1, 1, [], general, False)
        return [dict(title=P["title_general"], text=txt, tokens=est_text(txt), lines=(0, 0))]
    res = []
    for pi, part in enumerate(parts, 1):
        part.sort(key=lambda w: w[0])
        pis = [i for w in part for i in w[2]]
        if pi == 1:
            pis = general + pis
        pis.sort(key=lambda x: (SEV_ORDER[x["severity"]], x["line"]))
        txt = render(pi, len(parts), [(w[0], w[1]) for w in part], pis, False)
        res.append(dict(title=P["title_part"].format(i=pi, n=len(parts), a=part[0][0], b=part[-1][1]), text=txt,
                        tokens=est_text(txt), lines=(part[0][0], part[-1][1])))
    return res


def build_project_prompt(project_name, files, note="", budget=6000, top=25, ui="tr"):
    """Projenin genel düzeltme planı için özet prompt."""
    P = i18n.PROMPT[ui]
    out = [P["proj_role"], P["proj_intro"].format(project=project_name)]
    if note.strip():
        out += ["", P["context"].format(note=note.strip())]
    out += ["", P["task"], P["proj_t1"], P["proj_t2"], P["proj_t3"], "", P["proj_files"], P["proj_head"], "|---|---|---|---|---|---|---|"]
    for f in files[:top]:
        out.append(f"| {f['rel']} | {i18n.LANG_LABEL[ui].get(f['lang'], f['lang'])} | {f['c']} | {f['e']} | {f['w']} | {f['i']} | {f['tokens']} |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Rapor
# --------------------------------------------------------------------------
def fmt_time(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(ts)) if ts else "-"


def _where(R, it):
    return R["line"].format(n=it["line"]) if it["line"] else R["general"]


def report_markdown(conn, scan_id, ui="tr"):
    R = i18n.REPORT[ui]
    sev = i18n.SEV[ui]
    sc = conn.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
    files = conn.execute("SELECT * FROM files WHERE scan_id=? ORDER BY risk DESC, rel", (scan_id,)).fetchall()
    L = [f"# {R['title']}", "", f"- {R['project']}: `{sc['project']}`", f"- {R['date']}: {fmt_time(sc['finished'])}",
         "- " + R["scanned"].format(n=sc["n_files"], s=sc["skipped"], t=f"{sc['tokens']:,}"),
         "- " + R["counts"].format(c=sc["crit"], e=sc["err"], w=sc["warn"], i=sc["info"]),
         "- " + R["delta"].format(n=sc["new_issues"], f=sc["fixed_issues"]), ""]
    for f in files:
        if not (f["c"] or f["e"] or f["w"] or f["i"]):
            continue
        L.append(f"## {f['rel']}")
        L.append("_" + R["fileline"].format(lang=i18n.LANG_LABEL[ui].get(f["lang"], f["lang"]), lines=f["lines"], tok=f["tokens"],
                                            c=f["c"], e=f["e"], w=f["w"], i=f["i"]) + "_")
        L.append("")
        for it in conn.execute("SELECT * FROM issues WHERE file_id=? ORDER BY line", (f["id"],)):
            new = f" **[{R['new']}]**" if it["isnew"] else ""
            L.append(f"- **{sev[it['severity']]}** · {_where(R, it)} · `{it['rule']}`{new}: {i18n.tx(it['message'], ui)}")
            if it["snippet"]:
                L.append(f"  - {R['code']}: `{it['snippet'].replace('`', chr(39))}`")
            if it["fix"]:
                L.append(f"  - {R['advice']}: {i18n.tx(it['fix'], ui)}")
        L.append("")
    return "\n".join(L)


def report_html(conn, scan_id, ui="tr"):
    import html as _h
    R = i18n.REPORT[ui]
    sev = i18n.SEV[ui]
    sc = conn.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
    files = conn.execute("SELECT * FROM files WHERE scan_id=? ORDER BY risk DESC, rel", (scan_id,)).fetchall()
    e = _h.escape
    col = {"critical": "#b91c1c", "error": "#c2410c", "warning": "#a16207", "info": "#475569"}
    P = [f"<!doctype html><html lang='{ui}'><meta charset='utf-8'><title>{e(R['title'])}</title>",
         "<style>body{font:14px Segoe UI,Arial;margin:24px;color:#1e293b}h2{margin-top:28px;border-bottom:1px solid #cbd5e1}"
         "code{background:#f1f5f9;padding:1px 4px;border-radius:3px}.s{font-weight:600}.n{background:#dcfce7;padding:0 4px}"
         "li{margin:4px 0}</style>", f"<h1>{e(R['title'])}</h1>",
         f"<p><b>{e(R['project'])}:</b> {e(sc['project'])}<br><b>{e(R['date'])}:</b> {fmt_time(sc['finished'])}<br>"
         f"{e(R['scanned'].format(n=sc['n_files'], s=sc['skipped'], t=format(sc['tokens'], ',')))}<br>"
         f"{e(R['counts'].format(c=sc['crit'], e=sc['err'], w=sc['warn'], i=sc['info']))}<br>"
         f"{e(R['delta'].format(n=sc['new_issues'], f=sc['fixed_issues']))}</p>"]
    for f in files:
        if not (f["c"] or f["e"] or f["w"] or f["i"]):
            continue
        meta = R["fileline"].format(lang=i18n.LANG_LABEL[ui].get(f["lang"], f["lang"]), lines=f["lines"], tok=f["tokens"],
                                    c=f["c"], e=f["e"], w=f["w"], i=f["i"])
        P.append(f"<h2>{e(f['rel'])}</h2><small>{e(meta)}</small><ul>")
        for it in conn.execute("SELECT * FROM issues WHERE file_id=? ORDER BY line", (f["id"],)):
            new = f" <span class='n'>{e(R['new'])}</span>" if it["isnew"] else ""
            P.append(f"<li><span class='s' style='color:{col[it['severity']]}'>{e(sev[it['severity']])}</span> · {e(_where(R, it))} · "
                     f"<code>{e(it['rule'])}</code>{new} {e(i18n.tx(it['message'], ui))}")
            if it["snippet"]:
                P.append(f"<br><code>{e(it['snippet'])}</code>")
            if it["fix"]:
                P.append(f"<br><i>{e(R['advice'])}: {e(i18n.tx(it['fix'], ui))}</i>")
            P.append("</li>")
        P.append("</ul>")
    return "\n".join(P)


def safe_name(rel):
    return re.sub(r"[^\w.\-]+", "_", rel)[:120]


def export_prompts(conn, scan_id, out_dir, project_name, root, settings, note="", ui="tr"):
    """Bulgusu olan her dosya için prompt dosyaları yazar; yazılan sayıyı döndürür."""
    R = i18n.REPORT[ui]
    os.makedirs(out_dir, exist_ok=True)
    files = conn.execute("SELECT * FROM files WHERE scan_id=? AND (c+e+w)>0 ORDER BY risk DESC", (scan_id,)).fetchall()
    idx = [f"# {R['index']}", ""]
    n = 0
    for f in files:
        full = os.path.join(root, f["rel"])
        try:
            text, _, _ = read_text(full)
        except OSError:
            continue
        if text is None:
            continue
        iss = [dict(r) for r in conn.execute("SELECT * FROM issues WHERE file_id=?", (f["id"],))]
        parts = build_prompts(project_name, f["rel"], f["lang"], text, iss, int(settings["budget"]), int(settings["ctx"]), note, ui)
        for i, p in enumerate(parts, 1):
            fn = f"{safe_name(f['rel'])}__p{i}.md"
            with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(p["text"])
            idx.append(f"- [{R['idx_item'].format(rel=f['rel'], title=p['title'], tok=p['tokens'])}]({fn})")
            n += 1
    with open(os.path.join(out_dir, "00_INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(idx))
    return n


# --------------------------------------------------------------------------
# Geri bildirim / hata bildirimi (ağ bağlantısını uygulama değil, tarayıcı kurar)
# --------------------------------------------------------------------------
FEEDBACK_KINDS = ("bug", "idea", "question")
_FB_LABEL = {"bug": "bug", "idea": "enhancement", "question": "question"}
_FB_PREFIX = {"bug": "[Bug]", "idea": "[Idea]", "question": "[Question]"}
_FB = {
    "tr": {"desc": "Açıklama", "steps": "Tekrar adımları", "diag": "Sistem bilgisi", "none": "(boş)",
           "scan": "Son tarama: {n} dosya · Kritik {c}, Hata {e}, Uyarı {w}, Bilgi {i} (dosya adı/kod içermez)",
           "paste": "(Rapor metni panoya kopyalandı; lütfen buraya yapıştırın.)"},
    "en": {"desc": "Description", "steps": "Steps to reproduce", "diag": "System info", "none": "(empty)",
           "scan": "Last scan: {n} files · Critical {c}, Error {e}, Warning {w}, Info {i} (no file names/code included)",
           "paste": "(The report text was copied to the clipboard; please paste it here.)"},
}


def diagnostics(ui="en", scan=None):
    """Hata bildirimine eklenebilecek, kod/dosya yolu içermeyen sistem bilgisi."""
    import platform
    F = _FB[ui]
    L = [f"{i18n.APP_NAME['en']} {APP_VER}", f"Python {platform.python_version()}", f"OS: {platform.platform()}", f"UI language: {ui}"]
    if scan:
        L.append(F["scan"].format(n=scan["n_files"], c=scan["crit"], e=scan["err"], w=scan["warn"], i=scan["info"]))
    return "\n".join(L)


def feedback_text(kind, title, description, steps="", include_diag=True, ui="en", scan=None):
    """(başlık, gövde) döndürür."""
    F = _FB[ui]
    t = f"{_FB_PREFIX.get(kind, '')} {title.strip()}".strip()
    body = [f"### {F['desc']}", description.strip() or F["none"]]
    if kind == "bug":
        body += ["", f"### {F['steps']}", steps.strip() or F["none"]]
    if include_diag:
        body += ["", f"### {F['diag']}", "```", diagnostics(ui, scan), "```"]
    return t, "\n".join(body)


def feedback_url(kind, title, body, ui="en", max_len=1900):
    """GitHub 'yeni issue' adresi. Adres çok uzunsa gövde kısaltılır ve truncated=True döner
    (arayüz tam metni panoya koyar). Dönüş: (url, truncated)."""
    from urllib.parse import quote

    def build(b):
        return (f"{REPO_URL}/issues/new?title={quote(title, safe='')}&body={quote(b, safe='')}"
                f"&labels={quote(_FB_LABEL.get(kind, ''), safe='')}")

    url = build(body)
    if len(url) <= max_len:
        return url, False
    return build(_FB[ui]["paste"]), True


# --------------------------------------------------------------------------
# Komut satırı kipi (arayüzsüz; tkinter gerekmez)
# --------------------------------------------------------------------------
_CLI = {"tr": {"ign": ".kdignore ile atlanan klasör/dosya: {n}",
               "sum": "Dosya: {f}  Kritik: {c}  Hata: {e}  Uyarı: {w}  Bilgi: {i}  ~Token: {t}",
               "line": "   satır {n:>5}  {sev:<8} {rule}: {msg}", "wrote": "{n} prompt dosyası yazıldı: {out}"},
        "en": {"ign": "Folders/files skipped by .kdignore: {n}",
               "sum": "Files: {f}  Critical: {c}  Error: {e}  Warning: {w}  Info: {i}  ~Tokens: {t}",
               "line": "   line {n:>5}  {sev:<8} {rule}: {msg}", "wrote": "{n} prompt files written: {out}"}}


def cli_main(argv):
    """python KodDenetci.py --cli <klasör> [--prompts <çıktı klasörü>] [--lang tr|en]"""
    import tempfile
    for stream in (sys.stdout, sys.stderr):      # cp1252/cp437 konsolda Türkçe karakter çökmesin
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):  # kd-ignore (yönlendirilmiş/StringIO akışı)
            pass
    root = argv[argv.index("--cli") + 1]
    out = argv[argv.index("--prompts") + 1] if "--prompts" in argv else None
    ui = i18n.resolve(argv[argv.index("--lang") + 1] if "--lang" in argv else "auto")
    C = _CLI[ui]
    conn = open_db(os.path.join(tempfile.mkdtemp(), "cli.db"))
    st = get_settings(conn)
    r = scan_project(root, conn, st)
    if r["ignored"]:
        print(C["ign"].format(n=r["ignored"]))
    print(C["sum"].format(f=r["files"], c=r["c"], e=r["e"], w=r["w"], i=r["i"], t=r["tokens"]))
    for f in conn.execute("SELECT * FROM files WHERE (c+e+w+i)>0 ORDER BY risk DESC"):
        ab = i18n.SEV_ABBR[ui]
        print(f"\n{f['rel']}  [{f['lang']}]  {ab['critical']}{f['c']} {ab['error']}{f['e']} {ab['warning']}{f['w']} {ab['info']}{f['i']}")
        for i in conn.execute("SELECT * FROM issues WHERE file_id=? ORDER BY line", (f["id"],)):
            print(C["line"].format(n=i["line"], sev=i18n.SEV[ui][i["severity"]], rule=i["rule"], msg=i18n.tx(i["message"], ui)))
    if out:
        n = export_prompts(conn, r["scan_id"], out, os.path.basename(os.path.abspath(root)), root, st, ui=ui)
        print("\n" + C["wrote"].format(n=n, out=out))
    conn.close()
    return r
