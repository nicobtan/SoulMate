import unittest
from unittest.mock import MagicMock
import json
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.active_engine import ActiveEngine

class TestDifyIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_ai_engine = MagicMock()
        self.mock_callback = MagicMock()
        self.mock_bubble_service = MagicMock()
        self.mock_bubble_service._active_bubbles = {}
        
        self.active_engine = ActiveEngine(self.mock_ai_engine, self.mock_callback, bubble_service=self.mock_bubble_service)
        
        # Mock Dify Client
        self.active_engine.dify_client = MagicMock()
        
    def test_dify_workflow_triggers_bubble(self):
        # Setup Dify Mock Response
        self.active_engine.dify_client.fetch_note_article.return_value = {
            "message": "Test Article",
            "url": "http://example.com"
        }
        
        # Execute
        self.active_engine._run_dify_workflow("TestTag")
        
        # Assert 1: Bubble Registered in Service
        self.assertTrue(len(self.mock_bubble_service._active_bubbles) > 0)
        action_id = list(self.mock_bubble_service._active_bubbles.keys())[0]
        self.assertTrue(action_id.startswith("DIFY_"))
        
        packet = self.mock_bubble_service._active_bubbles[action_id]
        self.assertEqual(packet['metadata']['url'], "http://example.com")
        self.assertIn("Test Article", packet['text'])
        
        # Assert 2: UI Callback Triggered
        self.mock_callback.assert_called_once()
        args = self.mock_callback.call_args[0][0] # First arg of first call
        payload = json.loads(args)
        
        self.assertEqual(payload['type'], 'bubble')
        self.assertEqual(payload['action_id'], action_id)
        self.assertEqual(payload['metadata']['url'], "http://example.com")
        
        print(f"Verified Packet: {packet}")
        print(f"Verified UI Payload: {payload}")

if __name__ == '__main__':
    unittest.main()
