import unittest
import numpy as np
from drx_core import read_xy, normalize, detect_peaks


class DRXTests(unittest.TestCase):
    def test_headerless_and_sorted(self):
        df, ignored, duplicates = read_xy(b"12 3\n10 1\n11 2")
        self.assertEqual(df.x.tolist(), [10, 11, 12])
        self.assertEqual(df.y.tolist(), [1, 2, 3])
        self.assertEqual((ignored, duplicates), ([], 0))

    def test_formats(self):
        for text, decimal in [
            ("10\t1\n11\t2\n12\t3", "."),
            ("10,1\n11,2\n12,3", "."),
            ("10,0;1,0\n11,0;2,0\n12,0;3,0", ","),
            ("10,0 1,0\n11,0 2,0\n12,0 3,0", ","),
            ("10 1D0\n11 2e0\n12 3E0", "."),
        ]:
            with self.subTest(text=text):
                df, _, _ = read_xy(text, decimal=decimal)
                self.assertEqual(df.y.tolist(), [1, 2, 3])

    def test_metadata_duplicates_and_invalid(self):
        df, ignored, duplicates = read_xy("# equipo\n2theta intensity\n10 1\n11 2\n11 4\n12 5\n13 nan\n180 1\n14 1 2")
        self.assertEqual(df.y.tolist(), [1, 3, 5])
        self.assertEqual(duplicates, 1)
        self.assertEqual(ignored, [2, 7, 8, 9])

    def test_reject_invalid(self):
        for text in ["", "texto", "1 2\n2 3", "10 1\n10 2\n10 3"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_xy(text)

    def test_skip_rows(self):
        df, _, _ = read_xy("20 999\n10 1\n11 2\n12 3", skip_rows=1)
        self.assertEqual(len(df), 3)

    def test_normalization(self):
        np.testing.assert_allclose(normalize([10, 20, 30]), [0, 50, 100])
        np.testing.assert_allclose(normalize([5, 5, 5]), [0, 0, 0])

    def test_maxima_and_bragg(self):
        peaks = detect_peaks([10, 20, 30, 40, 50], [0, 1, 10, 1, 0], wavelength=1.5406)
        self.assertEqual(peaks["2θ (°)"].tolist(), [30])
        self.assertAlmostEqual(peaks["d (Å)"].iloc[0], 2.976212, places=5)
        self.assertEqual(len(detect_peaks([10, 20, 30], [3, 3, 3])), 0)

    def test_irregular_angular_separation(self):
        peaks = detect_peaks([10, 10.01, 10.02, 10.04, 10.05, 20, 30],
                             [0, 5, 0, 10, 0, 4, 0], separation_deg=0.1)
        self.assertEqual(peaks["2θ (°)"].tolist(), [10.04, 20])


if __name__ == "__main__":
    unittest.main()
