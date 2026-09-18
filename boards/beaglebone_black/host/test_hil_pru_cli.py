import unittest

from hil_pru_cli import percentile, summarize


class CliStatisticsTests(unittest.TestCase):
    def test_percentile_interpolates(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(percentile(values, 0.0), 1.0)
        self.assertEqual(percentile(values, 50.0), 3.0)
        self.assertEqual(percentile(values, 100.0), 5.0)

    def test_summary(self) -> None:
        result = summarize([1.0, 2.0, 3.0])
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["min"], 1.0)
        self.assertEqual(result["mean"], 2.0)
        self.assertEqual(result["p50"], 2.0)
        self.assertEqual(result["max"], 3.0)

    def test_empty_summary(self) -> None:
        self.assertEqual(summarize([]), {"count": 0})


if __name__ == "__main__":
    unittest.main()
