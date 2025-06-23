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

if __name__ == "__main__":
    unittest.main()
