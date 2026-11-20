# Katkı rehberi

- Bağımlılık eklemeyin: proje yalnızca Python standart kütüphanesini kullanır (tkinter, sqlite3).
- Yeni kural: `kd_core.py` içinde `R("KOD001", "warning", {"cs"}, "code", r"...", "mesaj", "öneri")`.
  `target`: `code` (yorum+string boş), `nocomment` (yalnızca yorum boş), `raw` (ham metin).
- Her yeni kural için `tests/test_core.py` içine hem tetikleyen hem tetiklememesi gereken bir test ekleyin.
- Çalıştırma: `python -m unittest discover -s tests -v`
- Yanlış pozitif bildirirken ilgili kod satırını (hassas veri içermeden) ekleyin.
