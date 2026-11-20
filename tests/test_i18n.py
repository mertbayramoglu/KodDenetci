# -*- coding: utf-8 -*-
import os, re, sys, tempfile, unittest, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import kd_core as core
import kd_i18n as i18n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class I18nTests(unittest.TestCase):
    def test_every_rule_text_has_english(self):
        for r in core.RULES:
            for k in ("msg", "fix"):
                self.assertIn(r[k], i18n.MSG_EN, r["id"])

    def test_dynamic_messages(self):
        self.assertEqual(i18n.tx("Kapatılmamış '{' (satır 3'de açıldı).", "en"), "Unclosed '{' (opened on line 3).")
        self.assertEqual(i18n.tx("Yorumda TODO notu. (+4 yer daha, gösterilmedi)", "en"), "TODO note in a comment. (+4 more, not shown)")
        self.assertEqual(i18n.tx("Bilinmeyen", "en"), "Bilinmeyen")
        self.assertEqual(i18n.tx("Kapatılmamış blok yorumu.", "tr"), "Kapatılmamış blok yorumu.")

    def test_ui_and_guide_parity(self):
        self.assertEqual(set(i18n.UI["tr"]), set(i18n.UI["en"]))
        self.assertEqual([k for k, _ in i18n.GUIDE["tr"]], [k for k, _ in i18n.GUIDE["en"]])
        with open(os.path.join(ROOT, "KodDenetci.py"), encoding="utf-8") as fh:
            src = fh.read()
        for k in set(re.findall(r'self\.t\(\s*"([a-z_0-9]+)"', src)):
            self.assertIn(k, i18n.UI["tr"], k)

    def test_prompt_languages(self):
        iss = [dict(rule="SEC001", severity="critical", line=2, col=1, message=core.RULES[0]["msg"], fix=core.RULES[0]["fix"], snippet="x")]
        tr = core.build_prompts("P", "a.cs", "cs", "a\nb\nc", iss, ui="tr")[0]["text"]
        en = core.build_prompts("P", "a.cs", "cs", "a\nb\nc", iss, ui="en")[0]["text"]
        self.assertIn("Görev", tr)
        self.assertIn("## Task", en)
        self.assertNotIn("Görev", en)

    def test_cli_lang(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "a.php"), "w", encoding="utf-8") as f:
            f.write("<?php\n$x = md5($p);\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            core.cli_main(["x", "--cli", d, "--lang", "en"])
        self.assertIn("Files:", buf.getvalue())

    def test_feedback(self):
        t, b = core.feedback_text("bug", "Crash", "desc", "1. open", True, "en")
        self.assertTrue(t.startswith("[Bug]"))
        self.assertNotIn(os.sep + "Users", b)
        url, trunc = core.feedback_url("bug", t, b, "en")
        self.assertTrue(url.startswith(core.REPO_URL + "/issues/new?"))
        self.assertFalse(trunc)
        url2, trunc2 = core.feedback_url("bug", t, "x" * 5000, "en")
        self.assertTrue(trunc2)
        self.assertLessEqual(len(url2), 1900)

    def test_t_accepts_lang_kwarg(self):
        self.assertIn("C#", i18n.t("file_hdr", "en", rel="a", lang="C#", lines=1, tok=2, enc="u"))
        self.assertIn("x", i18n.t("s_lang_line", "tr", lang="x", n=1, t="2"))

    def test_resolve(self):
        self.assertEqual(i18n.resolve("tr"), "tr")
        self.assertEqual(i18n.resolve("en"), "en")
        self.assertIn(i18n.resolve("auto"), ("tr", "en"))


if __name__ == "__main__":
    unittest.main()
