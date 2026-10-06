import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "ecdsafail-circuit-optimization/scripts/score_gate.py"
spec = importlib.util.spec_from_file_location("score_gate", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScoreGateTest(unittest.TestCase):
    def test_latest_width_submission_boundary(self):
        self.assertEqual(module.max_rounded_t(1107975918, 1172), 945371)

    def test_closing_width_submission_boundary(self):
        maximum = module.max_rounded_t(1107932620, 1171)
        self.assertEqual(maximum, 946142)
        self.assertEqual(1107932620 - 1171 * 946021, 142029)

    def test_equality_is_not_a_strict_win(self):
        self.assertEqual(module.max_rounded_t(100, 10), 9)

    def test_next_integer_always_loses(self):
        for score, width in [(101, 10), (1107932620, 1171), (1, 1)]:
            maximum = module.max_rounded_t(score, width)
            self.assertLess(maximum * width, score)
            self.assertGreaterEqual((maximum + 1) * width, score)


if __name__ == "__main__":
    unittest.main()
