# Değişiklik günlüğü

## 1.2.0
- Bilingual (Türkçe / English) interface, findings, prompts, reports and CLI (`--lang`); English name: CodeAuditor
- Help > User guide (F1): usage, settings, K/H/U/B (C/E/W/I) levels, tokens
- Help > Report a problem / Feedback: prefilled GitHub issue, copy or save; optional system info without code
- Settings: interface language and prompt/report language
- Rules and messages in docs/RULES.md (bilingual)

## 1.1.0 — 2026-11-20
- **Kritik hatalar** sekmesi: tüm projedeki kritik (isteğe bağlı kritik + hata) bulgular tek listede; çift tıklayınca dosyaya gider, listeyi kopyalama.
- `.kdignore` desteği (gitignore benzeri klasör/dosya hariç tutma); durum çubuğunda atlanan sayısı.
- CLI mantığı `kd_core.cli_main`'e taşındı; testler alt süreç başlatmıyor (kurumsal PC'lerde engellenebiliyor).
- Depo kendi kendini taramada sıfır bulgu verir (test olarak doğrulanır).
- GitHub hazırlığı: `.gitattributes`, `.editorconfig`, `SECURITY.md`, `tools/github_hazirla.bat`, sadeleştirilmiş belgeler.

## 1.0.1 — 2026-11-20 (kendi kendini denetim)
- **Güvenlik:** taranan projedeki `.bat/.vbs/.js/.ps1/.html` gibi dosyalar çift tıklamayla artık çalıştırılmaz/tarayıcıda açılmaz, Notepad ile açılır.
- **Hata:** Ayarlar'da ondalıklı token bütçesi (örn. 6000.5) girilince oluşan çökme giderildi (tam sayı doğrulaması).
- **Hata:** XML'de `encoding="windows-1254"` bildirimi olan dosyalar yanlışlıkla geçersiz sayılabiliyordu; düzeltildi.
- UTF-16 BOM'lu `.sql` dosyaları (SSMS çıktısı) artık okunuyor; eskiden ikili sanılıp atlanıyordu.
- Durdurulan taramada "giderilen" sayısı yanıltıcı hesaplanmıyor; durum çubuğunda "kısmi sonuç" yazıyor.
- Kural iyileştirmeleri: `hashlib.sha1(..., usedforsecurity=False)` ve `except <belirli hata>: pass` artık uyarı üretmiyor.

## 1.0.0 — 2026-11-20
- İlk sürüm: sözcük çözümleyici (tokenizer) tabanlı yerel statik denetim, dosya dosya bulgu listesi.
- Token bütçeli düzeltme prompt'u üretimi, SQLite geçmişi, önceki taramayla karşılaştırma.
- Markdown/HTML rapor, tüm prompt'ları dışa aktarma, `--cli` kipi.
