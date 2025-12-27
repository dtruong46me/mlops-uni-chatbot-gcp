import unittest
from fastapi.testclient import TestClient
import src.llm.client as llm_client_module
from src.rag import server


class DummyClient:
    def chat_completion(self, messages, model, temperature=0.2, **kwargs):
        return "This is a stubbed LLM answer."


class TestLLMApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        self._orig = llm_client_module.get_llm_client

    def tearDown(self):
        llm_client_module.get_llm_client = self._orig

    def test_llm_answer_success(self):
        llm_client_module.get_llm_client = lambda: DummyClient()
        resp = self.client.post("/llm/answer", json={"prompt": "What is HUST?"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("answer", resp.json())
        self.assertEqual(resp.json()["answer"], "This is a stubbed LLM answer.")

    def test_llm_answer_validation(self):
        resp = self.client.post("/llm/answer", json={"prompt": "   "})
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
