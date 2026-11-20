# CodeAuditor (Kod Denetçi) — User Guide

CodeAuditor scans the code files in a project folder on your computer, lists the problems file by file and builds a fix prompt for each file that you can give to an AI model (LLM). All data stays local; the app never connects to the internet by itself.

## 1. Quick start
- Click 'Browse…' to pick the project folder (or type the path and press Enter), then click 'Scan'.
- Select a file in the left list; its problems appear on the 'Findings' tab. Click a finding to see the description, code line and suggestion below.
- The 'Prompt' tab holds a ready prompt for that file. Use 'Copy to clipboard' and paste it into your LLM chat. Large files produce several parts; choose them in the drop-down.
- Apply the OLD/NEW fixes the LLM returns to your code yourself, then rescan: the 'History' and 'Summary' tabs show new and fixed findings.

## 2. What are C, E, W, I? (Severity levels; K, H, U, B in Turkish)
- C = Critical (K): Security hole or data-loss risk (SQL injection, hard-coded password, DELETE/UPDATE without WHERE, disabled TLS validation…). Fix these first.
- E = Error (H): Problems that can break execution or hide failures (syntax error, unterminated bracket/string, empty catch, async void…).
- W = Warning (U): Risky or poor practice (weak hash, ==, leftover debug code…). Not breaking now, but costs maintenance/security.
- I = Info (B): Low-priority notes (TODO/FIXME, very long line/file, deep nesting).

In the file list and tables these letters appear as counts (e.g. C2 E5 = 2 critical, 5 errors). The ★ mark on a row means a NEW finding that was not in the previous scan.

## 3. What is a token?

LLMs read text in pieces called 'tokens' (roughly a word fragment; in code a word, number or symbol). Every model can take only a limited number of tokens at once, so pasting a whole large file often does not fit or lowers quality.

CodeAuditor estimates each file's token count (the 'Tokens' column) and splits prompts by the 'Token budget' setting: the whole file if it fits, otherwise only the sections around findings are packed into parts. Numbers are estimates (±15%) and vary by model.

## 4. Settings (Settings > Settings…)
- Interface language: language of menus, lists and the guide. 'Automatic' follows the Windows language. Applied immediately.
- Prompt / report language: language of the prompts and reports you give to an LLM. 'Same as interface', Türkçe or English. Pick whichever your model handles best.
- Token budget (default 6000): approximate upper limit of one prompt part. Lower it for small models or short context windows (e.g. 3000); raise it for large-context models.
- Context lines (default 6): code lines added above/below each finding. More lines let the model see the surroundings but cost more tokens.
- Max file size KB (default 2048): larger files are skipped (to drop generated, minified and backup files).
- Excluded: comma-separated folder/file names (node_modules, .git, bin, obj…). For pattern-based (gitignore-like) exclusion put a .kdignore file in the project root.

## 5. Screens and fields
- Top bar: project folder, Browse…, Scan, Stop. The progress bar shows scanned files.
- Left list: files with language, line count, tokens and C/E/W/I counts. The filter and search box narrow the list. Double-click opens the file (scripts/HTML are not executed; they open in Notepad). Right-click: show in folder, copy prompt.
- Findings tab: the selected file's problems, with details below (rule code, line/column, code snippet, suggestion).
- Critical issues tab: one list of all critical (optionally critical+error) findings in the project. Double-click jumps to the file and finding; 'Copy list' puts them all on the clipboard.
- Prompt tab: the selected file's prompt parts, token count, copy and save buttons.
- Summary tab: scan counts, most frequent rules, language breakdown and the Project note. The note is added to every prompt as context (e.g. 'ASP.NET WebForms, SQL Server, .NET 4.8'). 'Project summary prompt' asks for an overall fix plan for the riskiest files.
- History tab: earlier scans; open and delete.
- File menu: save report as Markdown/HTML, export all prompts to a folder, open the data folder.

## 6. Silencing false positives
- Put kd-ignore in a comment at the end of a line (e.g. // kd-ignore reason) and findings on that line are hidden.
- To skip files or folders entirely, add a .kdignore file in the project root (one pattern per line, # for comments).

Static analysis is not a verdict: a finding can be a false positive. Step 1 of every prompt asks the LLM to verify the finding; please check fixes yourself before applying them.

## 7. Privacy and security
- Scans, the database (SQLite) and reports live only in the 'veri' folder on your computer. Do not push this folder to GitHub (.gitignore prevents it).
- Prompts contain pieces of your code. Before pasting into a cloud service/LLM make sure there are no passwords, keys or customer data, and follow your company policy.
- CodeAuditor never executes or modifies the files it scans.

## 8. Reporting problems and feedback

Use Help > Report a problem / Feedback… to send a bug, idea or question. Choose the type, write a title and description; for bugs add steps to reproduce. The optional system info contains only the version, Python and OS — no code or file names. The preview below is exactly the text that will be sent.
- 'Open on GitHub': opens a prefilled issue page in your browser; you review and submit it. A GitHub account is required.
- 'Copy' / 'Save to file': to send it by e-mail or another channel without GitHub.
- If you found a security vulnerability, do not open a public issue; use the private reporting route in SECURITY.md.

## 9. Command line and tips

```
KodDenetci.py --cli <folder> [--prompts <output folder>] [--lang tr|en]
```
- Runs without the GUI; good for CI or batch audits.
- Double-click Calistir.bat to start the app (needs Python 3.9+ with tkinter).
- Clear the Critical issues tab first, then Errors, then Warnings.
- In a very large project start with the 10 riskiest files; the 'Project summary prompt' suggests the order.
