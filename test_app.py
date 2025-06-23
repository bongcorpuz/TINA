import unittest
from unittest.mock import patch
from app import handle_ask

class TestHandleAsk(unittest.TestCase):
    def test_handle_ask_with_fallback(self):
        dummy_query = "What is VAT?"
        fallback_response = "[Fallback] This is a fallback answer."

        with patch("app.semantic_search", side_effect=Exception("Index error")):
            with patch("app.fallback_to_chatgpt", return_value=fallback_response) as mock_fallback:
                result = handle_ask(dummy_query)
                self.assertIn(fallback_response, result)
                mock_fallback.assert_called_once_with(dummy_query)

    def test_handle_ask_success(self):
        dummy_query = "What is income tax?"
        mock_result = ["Answer 1", "Answer 2"]

        with patch("app.semantic_search", return_value=mock_result):
            result = handle_ask(dummy_query)
            expected = "\n\n---\n\n".join(mock_result)
            self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()