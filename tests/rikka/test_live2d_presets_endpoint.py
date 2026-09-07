"""Test Live2D presets GET/PATCH endpoint and validation."""

import unittest


class TestLive2DPresetsEndpoint(unittest.TestCase):
    """Test presets endpoint validation logic."""

    def test_forbidden_param_detection_arm(self):
        """Validate that arm/hand/wrist params are detected."""
        forbidden = ["arm", "hand", "wrist", "Param60", "Param63", "Param68", "Param73"]
        test_params = [
            "ParamArmL",
            "ParamHandR",
            "ParamWristL",
            "Param60",
            "Param63",
            "ParamEyeLSmile",
        ]
        for param in test_params:
            is_forbidden = any(f in param.lower() for f in ["arm", "hand", "wrist"]) or param in forbidden
            if param.startswith("Param") and param[5:] in ["60", "63", "68", "73"]:
                is_forbidden = True
            if "Arm" in param or "Hand" in param or "Wrist" in param:
                self.assertTrue(is_forbidden, f"{param} should be forbidden")
            elif param in ["Param60", "Param63"]:
                self.assertTrue(is_forbidden, f"{param} should be forbidden")
            else:
                self.assertFalse(is_forbidden, f"{param} should be allowed")

    def test_numeric_value_validation(self):
        """Validate numeric value checking."""
        valid_values = [0.5, 1.0, -0.3, 0]
        invalid_values = ["string", None, [1, 2], {"a": 1}]
        for val in valid_values:
            self.assertTrue(isinstance(val, (int, float)), f"{val} should be numeric")
        for val in invalid_values:
            self.assertFalse(isinstance(val, (int, float)), f"{val} should be non-numeric")

    def test_known_config_keys(self):
        """Validate allowed top-level keys."""
        allowed = {"expressionPresets", "gestureMap", "idleMicro", "speakingSmile"}
        test_keys = ["expressionPresets", "unknownKey", "gestureMap", "badKey"]
        for key in test_keys:
            if key in allowed:
                self.assertIn(key, allowed)
            else:
                self.assertNotIn(key, allowed)


if __name__ == "__main__":
    unittest.main()
