# -*- coding: utf-8 -*-
import os, sys, shutil, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import kd_core as core


def rules(text, lang):
    iss, _ = core.analyze_text(text, lang)
    return {i["rule"] for i in iss}, iss


class AnalyzerTests(unittest.TestCase):
    def test_csharp_sql_concat_and_secret(self):
        r, _ = rules('string p = "Sup3rSecret!"; var s = "SELECT * FROM U WHERE n=\'" + u + "\'";', "cs")  # kd-ignore (bilerek hatalı test girdisi)
        self.assertIn("SQL001", r)
        r2, _ = rules('string password = "Sup3rSecret!";', "cs")  # kd-ignore (bilerek hatalı test girdisi)
        self.assertIn("SEC001", r2)

    def test_parameterized_query_is_clean(self):
        r, _ = rules('var c = new SqlCommand("SELECT * FROM U WHERE n=@n", cn);', "cs")
        self.assertNotIn("SQL001", r)

    def test_comments_and_strings_do_not_trigger_code_rules(self):
        r, _ = rules('// eval("x")\nvar s = "eval(1)";\n', "js")
        self.assertNotIn("EVAL01", r)

    def test_bracket_mismatch(self):
        r, iss = rules("function a(x) {\n  foo(1\n}\n", "js")
        self.assertIn("SYN003", r)
        self.assertEqual([i for i in iss if i["rule"] == "SYN003"][0]["line"], 3)

    def test_unterminated_block(self):
        r, _ = rules("class A { }\n", "cs")
        self.assertNotIn("SYN003", r)
        r2, _ = rules("class A {\n", "cs")
        self.assertIn("SYN003", r2)

    def test_js_regex_literal_not_bracket_error(self):
        r, _ = rules("var re = /[(]+/g;\nif (a) { b(); }\n", "js")
        self.assertNotIn("SYN003", r)

    def test_python_syntax_error_line(self):
        _, iss = rules("def f():\n    return (1\n", "python")
        syn = [i for i in iss if i["rule"] == "SYN005"]
        self.assertTrue(syn)

    def test_json_error(self):
        r, _ = rules('{"a": 1,}', "json")
        self.assertIn("SYN006", r)

    def test_php_rules(self):
        src = '<?php\n$r = mysql_query("SELECT * FROM t WHERE id=$id");\ninclude($_GET["p"]);\n?>\n<p>Don\'t</p>'
        r, _ = rules(src, "php")
        self.assertTrue({"PHP001", "SQL001", "SEC003"} <= r)
        self.assertNotIn("SYN002", r)     # HTML'deki kesme işareti hata sayılmamalı

    def test_aspx_commented_code_ignored(self):
        r, _ = rules('<%-- <%= Request["x"] %> --%>\n<div>ok</div>', "markup")
        self.assertNotIn("XSS001", r)
        r2, _ = rules('<div><%= Request["x"] %></div>', "markup")
        self.assertIn("XSS001", r2)

    def test_webconfig(self):
        r, _ = rules('<configuration><system.web><compilation debug="true"/></system.web></configuration>', "xml")
        self.assertIn("CFG001", r)
        r2, _ = rules('<configuration><!-- <compilation debug="true"/> --></configuration>', "xml")
        self.assertNotIn("CFG001", r2)

    def test_sql_delete_without_where(self):
        r, iss = rules("DELETE FROM Users;\nDELETE FROM T WHERE id=1;", "sql")
        self.assertEqual(len([i for i in iss if i["rule"] == "SQLX01"]), 1)

    def test_kd_ignore(self):
        r, _ = rules('string password = "abcdef"; // kd-ignore', "cs")
        self.assertNotIn("SEC001", r)


class PromptTests(unittest.TestCase):
    def _big(self):
        L = ["        int v%d = Compute(%d);" % (i, i) for i in range(3000)]
        for ln in (100, 1500, 2900):
            L[ln] = '        string q = "SELECT * FROM T WHERE a=\'" + x + "\'";'  # kd-ignore (bilerek hatalı test girdisi)
        return "namespace A {\nclass B {\n" + "\n".join(L) + "\n}\n}\n"

    def test_small_file_single_part(self):
        text = 'string q = "SELECT * FROM T WHERE a=\'" + x + "\'";\n'  # kd-ignore (bilerek hatalı test girdisi)
        iss, _ = core.analyze_text(text, "cs")
        parts = core.build_prompts("P", "a.cs", "cs", text, iss)
        self.assertEqual(len(parts), 1)
        self.assertIn("SQL001", parts[0]["text"])

    def test_budget_respected_and_split(self):
        text = self._big()
        iss, _ = core.analyze_text(text, "cs")
        parts = core.build_prompts("P", "Big.cs", "cs", text, iss, budget=1200, ctx=15)
        self.assertGreater(len(parts), 1)
        for p in parts:
            self.assertLessEqual(p["tokens"], 1400)


class ScanTests(unittest.TestCase):
    def test_scan_excludes_and_diffs(self):
        tmp = tempfile.mkdtemp()
        try:
            proj = os.path.join(tmp, "proj")
            shutil.copytree(os.path.join(HERE, "fixtures"), proj)
            os.makedirs(os.path.join(proj, "node_modules", "x"))
            with open(os.path.join(proj, "node_modules", "x", "skip.js"), "w") as f:
                f.write('eval("1")')
            conn = core.open_db(os.path.join(tmp, "t.db"))
            st = core.get_settings(conn)
            r1 = core.scan_project(proj, conn, st)
            self.assertEqual(r1["files"], 8)   # node_modules atlandı
            self.assertGreater(r1["c"], 0)
            os.remove(os.path.join(proj, "api", "svc.py"))
            r2 = core.scan_project(proj, conn, st)
            self.assertGreater(r2["fixed"], 0)
            self.assertEqual(r2["new"], 0)
            md = core.report_markdown(conn, r2["scan_id"])
            self.assertIn("Login.cs", md)
            n = core.export_prompts(conn, r2["scan_id"], os.path.join(tmp, "p"), "proj", proj, st)
            self.assertGreater(n, 0)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CliTests(unittest.TestCase):
    """Alt süreç başlatmaz (kurumsal bilgisayarlarda engellenebilir); CLI mantığı aynı süreçte çalıştırılır."""

    def test_cli(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = core.cli_main(["KodDenetci.py", "--cli", os.path.join(HERE, "fixtures"), "--lang", "tr"])
        self.assertIn("Kritik", buf.getvalue())
        self.assertGreater(r["c"], 0)

    def test_gui_module_compiles(self):
        path = os.path.join(ROOT, "KodDenetci.py")
        with open(path, encoding="utf-8") as f:
            compile(f.read(), path, "exec")      # sözdizimi denetimi; tkinter içe aktarılmaz


class RegressionTests(unittest.TestCase):
    """Kendi kendini denetimde bulunan sorunların regresyon testleri."""

    def test_risky_files_not_opened_with_default_app(self):
        for n in ("a.bat", "x.VBS", "s.js", "p.ps1", "i.html", "u.exe"):
            self.assertTrue(core.is_risky_to_open(n), n)
        for n in ("a.cs", "b.php", "c.sql", "d.config", "e.py"):
            self.assertFalse(core.is_risky_to_open(n), n)

    def test_utf16_sql_is_read(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "a.sql")
            with open(p, "wb") as f:
                f.write("DELETE FROM Users;\n".encode("utf-16"))
            text, enc, _ = core.read_text(p)
            self.assertEqual(enc, "utf-16")
            r, _ = rules(text, "sql")
            self.assertIn("SQLX01", r)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_xml_with_encoding_declaration(self):
        xml = '<?xml version="1.0" encoding="windows-1254"?>\n<a><b>ğüşiöç</b></a>'
        r, _ = rules(xml, "xml")
        self.assertNotIn("SYN007", r)
        r2, _ = rules('<?xml version="1.0"?><a><b></a>', "xml")
        self.assertIn("SYN007", r2)

    def test_hash_not_for_security_is_exempt(self):
        r, _ = rules('import hashlib\nh = hashlib.sha1(b"x", usedforsecurity=False)\n', "python")
        self.assertNotIn("CRY001", r)
        r2, _ = rules('import hashlib\nh = hashlib.sha1(b"x")\n', "python")
        self.assertIn("CRY001", r2)

    def test_specific_except_pass_not_flagged(self):
        r, _ = rules("try:\n    x()\nexcept queue.Empty:\n    pass\n", "python")
        self.assertNotIn("QLT001", r)
        r2, _ = rules("try:\n    x()\nexcept Exception:\n    pass\n", "python")
        self.assertIn("QLT001", r2)

    def test_cancelled_scan_reports_flag(self):
        import threading
        tmp = tempfile.mkdtemp()
        try:
            proj = os.path.join(tmp, "p")
            shutil.copytree(os.path.join(HERE, "fixtures"), proj)
            conn = core.open_db(os.path.join(tmp, "t.db"))
            ev = threading.Event()
            ev.set()
            r = core.scan_project(proj, conn, core.get_settings(conn), cancel=ev)
            self.assertTrue(r["cancelled"])
            self.assertEqual(r["fixed"], 0)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class IgnoreFileTests(unittest.TestCase):
    def test_kdignore_patterns(self):
        tmp = tempfile.mkdtemp()
        try:
            def w(rel, txt):
                path = os.path.join(tmp, *rel.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
            bad = 'string password = "abcdef123";\n'  # kd-ignore (bilerek hatalı test girdisi)
            w("src/ok.cs", "class A { }\n")
            w("src/Gen.generated.cs", bad)
            w("samples/deep/x.cs", bad)
            w("other/samples/y.cs", bad)
            w("keep/z.cs", bad)
            w(".kdignore", "# yorum\nsamples/\n*.generated.cs\nother/samples/\n")
            conn = core.open_db(os.path.join(tmp, "t.db"))
            r = core.scan_project(tmp, conn, core.get_settings(conn))
            rels = {x["rel"].replace(os.sep, "/") for x in conn.execute("SELECT rel FROM files")}
            self.assertEqual(rels, {"src/ok.cs", "keep/z.cs"})
            self.assertGreaterEqual(r["ignored"], 3)
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_repo_itself_is_clean(self):
        """Depo kökü (fixtures hariç) sıfır bulgu vermeli: kendi kendini denetim."""
        tmp = tempfile.mkdtemp()
        try:
            conn = core.open_db(os.path.join(tmp, "t.db"))
            r = core.scan_project(ROOT, conn, core.get_settings(conn))
            self.assertEqual(r["issues"], 0, [dict(x) for x in conn.execute("SELECT rule,line,message FROM issues")])
            conn.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
