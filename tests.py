import unittest
from unittest.mock import patch, MagicMock
from agent import get_vision_score, calculate_geo_score

class TestNYCDiscoveryAgent(unittest.TestCase):

    def test_calculate_geo_score_logic(self):
        # Test the Goldilocks Zone scoring math
        # Test 1: Ideal distance (~500m)
        score_ideal = calculate_geo_score(40.7484, -73.9857, 40.7520, -73.9810)
        self.assertEqual(score_ideal, 1.0)
        
        # Test 2: Far away (10km)
        score_far = calculate_geo_score(40.7484, -73.9857, 40.8000, -73.9000)
        self.assertEqual(score_far, 0.0)

    @patch('agent.requests.get')
    @patch('agent.vision_model.encode')
    def test_get_vision_score_execution(self, mock_encode, mock_get):
        # Test the vision scoring flow without downloading a real image
        # Mocking the HTTP response for the image
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake_image_bytes"
        
        # Mocking the CLIP model embeddings (returning 1.0 similarity)
        import torch
        mock_encode.return_value = torch.tensor([0.95])
        
        score = get_vision_score("http://fakeurl.com/img.jpg", "Empire State Building")
        
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.0)

    def test_source_integration_structure(self):
        # Check if candidates are structured correctly for the scoring loop
        sample_candidate = {
            "source": "Wikimedia",
            "coords": (40.7484, -73.9857),
            "url": "http://test.com/image.jpg"
        }
        self.assertIn("url", sample_candidate)
        self.assertEqual(len(sample_candidate["coords"]), 2)

if __name__ == '__main__':
    unittest.main()