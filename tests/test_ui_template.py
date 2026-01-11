import unittest
from fastapi.testclient import TestClient
from src.rag import server


class TestUITemplate(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)

    def test_ui_index_renders(self):
        resp = self.client.get('/ui/')
        self.assertEqual(resp.status_code, 200)
        body = resp.text
        self.assertIn('HUST Unified Chatbot', body)


if __name__ == '__main__':
    unittest.main()
