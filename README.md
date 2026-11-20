**English** · [Türkçe](README.tr.md)

# CodeAuditor (Kod Denetçi)

[![CI](https://github.com/mertbayramoglu/KodDenetci/actions/workflows/ci.yml/badge.svg)](https://github.com/mertbayramoglu/KodDenetci/actions)

A local, offline **static code audit** desktop tool for Windows (Python + tkinter + SQLite, standard library only).
It scans a project folder with a tokenizer-based analyzer, lists the problems **file by file** and builds
**token-budgeted fix prompts** you can paste into any LLM. The interface, prompts and reports are available in **English and Turkish**.

- Tokenizer-based rules for C#, JavaScript/TypeScript, PHP, Python, SQL, VB, HTML/ASPX/Razor, CSS, JSON, XML, config and scripts
- Severity levels: Critical / Error / Warning / Info (C/E/W/I; K/H/U/B in Turkish)
- "Critical issues" tab with every critical finding of the project at once
- Prompts split by a token budget; project summary prompt; Markdown/HTML reports; scan history with new/fixed diff
- Built-in **User guide** (Help > User guide, F1) and **Report a problem / Feedback** form
- No network access by itself; all data stays in the local `veri\` folder

## Run

Requires Python 3.9+ with tkinter. Double-click `Calistir.bat`, or:

```
python KodDenetci.py
python KodDenetci.py --cli <folder> [--prompts <out folder>] [--lang en|tr]
```

## Documentation

- [User guide](docs/USER_GUIDE.md) · [Kullanım kılavuzu](docs/KULLANIM_KILAVUZU.md)
- [Rules / Kurallar](docs/RULES.md)
- [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Feedback

Use Help > Report a problem / Feedback in the app, or open an issue: https://github.com/mertbayramoglu/KodDenetci/issues

Developer: Mert Bayramoğlu - Software Developer · License: MIT
