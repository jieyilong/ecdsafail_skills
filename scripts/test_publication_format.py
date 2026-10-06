import unittest
from build_skill_center_bundles import append_file
from normalize_patch import normalize


class PublicationFormatTest(unittest.TestCase):
    def test_unicode_script_preserves_exact_source_and_nested_fences(self):
        raw = '# α test\nprint("````")\n'.encode()
        bundle = append_file("scripts/example.py", raw)
        self.assertIn(raw.decode(), bundle)
        self.assertIn("`````python\n", bundle)

    def test_line_ending_noise_removed_but_semantic_change_retained(self):
        patch = ("diff --git a/a.rs b/a.rs\n--- a/a.rs\n+++ b/a.rs\n"
                 "@@ -1,2 +1,2 @@\n-old\r\n-x = 1;\r\n+old\n+x = 2;\n")
        compact = normalize(patch)
        self.assertNotIn("-old", compact)
        self.assertIn("-x = 1;", compact)
        self.assertIn("+x = 2;", compact)


if __name__ == "__main__":
    unittest.main()
