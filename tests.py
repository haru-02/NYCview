import unittest
from unittest.mock import patch
from core.brain import AgentBrain
from core.state import AgentState

class TestAgent(unittest.TestCase):
    @patch('core.brain.AgentBrain.decide_next_action')
    def test_decision_logic(self, mock_decide):
        # Mock the SLM to return 'finalize' immediately
        mock_decide.return_value = "finalize"
        
        state = AgentState(poi_name="Test", target_lat=0, target_lng=0)
        action = AgentBrain.decide_next_action(state)
        
        self.assertEqual(action, "finalize")

if __name__ == '__main__':
    unittest.main()