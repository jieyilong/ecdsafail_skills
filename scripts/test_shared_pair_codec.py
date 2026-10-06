"""Exhaustive support/phase check of the Q1172 shared-pair equations.

Scope: two trits in HL encoding {(0,0),(0,1),(1,0)} and a supplied product
p=a*(1-c)*(1-d). This verifies the algebraic support obligation, not the full
point-add implementation or the actual carry's lifetime/source binding.
"""
import itertools
import unittest

TRITS = [(0, 0), (0, 1), (1, 0)]


def ordinary_pair(a, b, c, d):
    c ^= a
    anc = a & c
    if anc:
        b, d = d, b
    d ^= anc
    a ^= anc
    return a, b, c, d


def shared_pair(a, b, c, d, p):
    h = a & c
    b ^= p ^ a ^ h
    c ^= a
    d ^= p
    return h, b, c, d


def unpack(h1, l1, h2, l2):
    anc = h2 & l2
    h1 ^= anc
    l2 ^= anc
    if anc:
        l1, l2 = l2, l1
    h2 ^= h1
    return h1, l1, h2, l2


class SharedPairTest(unittest.TestCase):
    def test_nine_legal_pairs_and_all_measurement_outcomes(self):
        for (a, b), (c, d) in itertools.product(TRITS, repeat=2):
            p = a & (1 ^ c) & (1 ^ d)
            packed = shared_pair(a, b, c, d, p)
            self.assertEqual(packed, ordinary_pair(a, b, c, d))
            self.assertEqual(unpack(*packed), (a, b, c, d))
            h, bp, cp, dp = packed
            # HMR(a) phase is repaired immediately by Z(h) and CZ(cp,dp).
            a_repair = h ^ (cp & dp)
            # HMR(p) phase is repaired at unpack using its already computed AND.
            p_repair = (cp & dp) ^ (cp & dp & bp)
            self.assertEqual(a, a_repair)
            self.assertEqual(p, p_repair)
            for m_a, m_p in itertools.product((0, 1), repeat=2):
                residual_phase = (m_a & (a ^ a_repair)) ^ (m_p & (p ^ p_repair))
                self.assertEqual(residual_phase, 0)

    def test_product_precondition_is_necessary(self):
        self.assertNotEqual(shared_pair(1, 0, 0, 0, 0), ordinary_pair(1, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
