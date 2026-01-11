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


class TestAskAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)
        self._orig_components = server._get_components
        self._orig_generate = server.generate_answer

    def tearDown(self):
        server._get_components = self._orig_components
        server.generate_answer = self._orig_generate

    def test_ask_respects_top_k(self):
        cfg = {"retrieval": SimpleNamespace(top_k=2), "model": {}}
        server._get_components = lambda: (cfg, DummyRetriever())
        server.generate_answer = lambda q, docs, model: "answer"

        # explicit top_k in payload
        resp = self.client.post("/ask", json={"question": "q", "top_k": 3})
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(resp.json()["contexts"]), 3)

        # fallback to config.top_k when not provided
        resp2 = self.client.post("/ask", json={"question": "q"})
        self.assertEqual(resp2.status_code, 200)
        self.assertLessEqual(len(resp2.json()["contexts"]), 2)


if __name__ == "__main__":
    unittest.main()
