from fastapi.testclient import TestClient

from src.rag import server


class DummyClient:
    def chat_completion(self, messages, model, temperature=0.2, **kwargs):
        return "This is a stubbed LLM answer."


def test_llm_answer_success(monkeypatch):
    monkeypatch.setattr("src.llm.client.get_llm_client", lambda: DummyClient())
    client = TestClient(server.app)

    resp = client.post("/llm/answer", json={"prompt": "What is HUST?"})
    assert resp.status_code == 200
    assert "answer" in resp.json()
    assert resp.json()["answer"] == "This is a stubbed LLM answer."


def test_llm_answer_validation():
    client = TestClient(server.app)
    resp = client.post("/llm/answer", json={"prompt": "   "})
    assert resp.status_code == 400
