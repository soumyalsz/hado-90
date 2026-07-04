import unittest

from runner.mutator import ensure_distinct_mutation


class EnsureDistinctMutationTests(unittest.TestCase):
    def test_rewrites_prompt_when_it_matches_previous_attempt(self):
        result = ensure_distinct_mutation(
            original_prompt="same prompt",
            prior_prompt="same prompt",
        )

        self.assertNotEqual(result, "same prompt")
        self.assertIn("different framing", result.lower())

    def test_keeps_model_output_when_it_is_already_distinct(self):
        result = ensure_distinct_mutation(
            original_prompt="original prompt",
            prior_prompt="older prompt",
            candidate="new framing prompt",
        )

        self.assertEqual(result, "new framing prompt")


if __name__ == "__main__":
    unittest.main()
