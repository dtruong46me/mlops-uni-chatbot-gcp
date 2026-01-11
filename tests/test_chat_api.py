import unittest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from src.rag import server


class DummyDoc:
    def __init__(self, text, metadata=None):
        self.text = text
        self.metadata = metadata or {}


class DummyRetriever:
    def retrieve(self, q, top_k=None):
        docs = [DummyDoc(f"doc{i}", metadata={"id": i}) for i in range(1, 6)]
        if top_k:
            docs = docs[:top_k]
        return [(d, 1.0) for d in docs]


class DummyLLM:
    def chat_completion(self, messages, model, temperature=0.2, **kwargs):
        # echo the model and message so tests can assert it was used
        return f"[model={model}] {messages[-1]['content']}"


class ChatAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        self._orig_components = server._get_components

    def tearDown(self):
        server._get_components = self._orig_components

    def test_chat_rag_mode(self):
        cfg = {"retrieval": SimpleNamespace(top_k=2), "model": {}}
        server._get_components = lambda: (cfg, DummyRetriever())
        # stub generate_answer to avoid depending on model config internals
        orig_generate = server.generate_answer
        server.generate_answer = lambda q, docs, model: "answer"
        try:
            resp = self.client.post("/chat", json={"message": "hi", "use_rag": True, "top_k": 3})
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body.get("source"), "rag")
            self.assertIn("answer", body)
            self.assertLessEqual(len(body.get("contexts", [])), 3)

            # also test that providing a string model override doesn't crash
            resp2 = self.client.post("/chat", json={"message": "hi", "use_rag": True, "model": "gpt-4o-mini"})
            self.assertEqual(resp2.status_code, 200)
        finally:
            server.generate_answer = orig_generate

    def test_chat_llm_mode(self):
        # monkeypatch LLM client
        import src.llm.client as llm_client_module
        orig = llm_client_module.get_llm_client
        llm_client_module.get_llm_client = lambda: DummyLLM()

        try:
            resp = self.client.post("/chat", json={"message": "hi", "use_rag": False, "model": "my-model"})
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertEqual(body.get("source"), "llm")
            self.assertTrue(body.get("answer").startswith("[model=my-model]"))
        finally:
            llm_client_module.get_llm_client = orig


if __name__ == "__main__":
    unittest.main()
