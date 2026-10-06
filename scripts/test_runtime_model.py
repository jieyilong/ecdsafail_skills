import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "ecdsafail-island-hunting/scripts/island_runtime_model.py"
spec = importlib.util.spec_from_file_location("runtime_model", PATH)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


class RuntimeModelTest(unittest.TestCase):
    def test_conditional_fit_does_not_pool_correlated_phase_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = Path(folder) / "panel.txt"
            panel.write_text("0 0 0\n" * 6 + "1 1 0\n" * 6)
            q, stats = model.funnel_from_counts(panel)
        self.assertEqual(stats["pha"]["n"], 6)
        self.assertEqual(stats["pha"]["mu"], 0)
        self.assertEqual(stats["anc"]["model"], "observed-all-zero")
        self.assertAlmostEqual(q, stats["cls"]["p0"])

    def test_small_conditioning_subset_uses_explicit_marginals(self):
        with tempfile.TemporaryDirectory() as folder:
            panel = Path(folder) / "panel.txt"
            panel.write_text("1 0 1\n1 2 0\n1 1 2\n")
            _, stats = model.funnel_from_counts(panel)
        self.assertEqual(stats["anc"]["n"], 3)
        self.assertEqual(stats["pha"]["n"], 3)
        self.assertIn("assumes", stats["anc_mode"])
        self.assertIn("assumes", stats["pha_mode"])

    def test_calibration_scales_candidate_count_and_evaluation_work(self):
        run = subprocess.run([sys.executable, str(PATH), "--density", ".01", "--q", ".5",
                              "--rate", "100", "--t-eval", "3", "--k", "2"],
                             capture_output=True, text=True, check=True)
        count = re.search(r"Stage-1 passes to eval\s+N\*d\s+=\s+(\S+)", run.stdout)
        self.assertAlmostEqual(float(count[1]), 4)
        self.assertIn("12.0 s", run.stdout)

    def test_invalid_density_is_a_domain_error_not_a_traceback(self):
        run = subprocess.run([sys.executable, str(PATH), "--density", "0", "--q", ".5",
                              "--rate", "100"], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertNotIn("Traceback", run.stderr)


if __name__ == "__main__":
    unittest.main()
