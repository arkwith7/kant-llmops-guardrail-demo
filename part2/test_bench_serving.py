import io
import unittest
from unittest.mock import patch

import bench_serving


class BenchmarkTests(unittest.TestCase):
    def test_stream_counts_usage_not_chunks(self):
        response = io.BytesIO(
            b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            b'data: {"choices":[],"usage":{"completion_tokens":3}}\n\n'
            b'data: [DONE]\n\n'
        )
        with patch.object(bench_serving.urllib.request, "urlopen", return_value=response):
            result = bench_serving.one_request("http://localhost/v1", "test", 10)
        self.assertEqual(result["tokens"], 3)
        self.assertEqual(result["chunks"], 1)
        self.assertEqual(result["response"], "hello")

    def test_partial_failure_and_missing_usage(self):
        response = {"ok": True, "ttft": 0.1, "total": 0.3, "tokens": None,
                    "chunks": 2, "response": "hello"}
        with patch.object(bench_serving, "one_request", side_effect=[response, RuntimeError("failed")]):
            result = bench_serving.run_level("http://localhost/v1", "test", 1, 10, repeats=2)
        self.assertEqual((result["succeeded"], result["failed"]), (1, 1))
        self.assertIsNone(result["throughput"])
        self.assertEqual(result["ttft_p95"], 0.1)

    def test_percentile_nearest_rank(self):
        self.assertEqual(bench_serving.percentile(list(range(1, 21)), 0.95), 19)
        self.assertIsNone(bench_serving.percentile([], 0.95))


if __name__ == "__main__":
    unittest.main()