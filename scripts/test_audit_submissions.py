import unittest
from audit_submissions import frontier


def row(sid, q, t, status="rejected"):
    return {"id": sid, "officialMetrics": {"qubits": q, "toffoli": t}, "status": status}


class FrontierTest(unittest.TestCase):
    def test_tradeoffs_and_ties(self):
        rows = [row("a", 10, 20), row("tie", 10, 20), row("b", 9, 25),
                row("c", 11, 19), row("dominated", 11, 20), row("same_q", 10, 21)]
        self.assertEqual(set(frontier(rows)), {"a", "tie", "b", "c"})

    def test_failed_and_missing_metrics_do_not_define_frontier(self):
        rows = [row("clean", 10, 20), row("failed", 1, 1, "failed"),
                row("invalid", 0, 1), {"id": "missing", "status": "rejected"}]
        self.assertEqual(frontier(rows), ["clean"])


if __name__ == "__main__":
    unittest.main()
