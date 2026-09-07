import unittest

from open_llm_vtuber.rikka.presentation import rikka_response_to_actions
from open_llm_vtuber.rikka.schemas import RikkaResponse


class DummyLive2DModel:
    def __init__(self, emo_map, model_info=None):
        self.emo_map = emo_map
        self.model_info = model_info or {}


RIKKA_PRESET_MODEL_INFO = {
    "expressionPresets": {
        "neutral": {"label": "平静", "parameters": {}, "fade_ms": 300},
        "soft_smile": {
            "label": "浅笑",
            "parameters": {
                "ParamEyeLSmile": 0.35,
                "ParamEyeRSmile": 0.35,
                "ParamMouthForm": 0.15,
                "ParamBadValue": "oops",
            },
            "fade_ms": 400,
            "hold_after_speech_ms": 2500,
        },
    },
    "gestureMap": {
        "nod": {
            "kind": "nod",
            "amplitude": 1.0,
            "duration_ms": 900,
            "cooldown_ms": 1800,
        },
        "small_wave": {"kind": "greeting_bob", "amplitude": 0.8},
        "look_away": {"kind": "look_away", "enabled": False},
    },
}


def make_response(
    emotion: str,
    motion: str = "idle",
    gaze: str = "camera",
) -> RikkaResponse:
    return RikkaResponse(
        spoken_text="收到。",
        subtitle_text="收到。",
        emotion=emotion,
        motion=motion,
        gaze=gaze,
        priority="normal",
        interruptible=True,
        reason_code="reply_chat",
    )


class RikkaPresentationActionTests(unittest.TestCase):
    def test_rikka_response_emits_legacy_expression_actions_by_default(self):
        live2d_model = DummyLive2DModel({"soft_smile": 7, "neutral": 0})
        actions = rikka_response_to_actions(
            make_response("soft_smile"),
            live2d_model,
        )

        self.assertEqual(actions.to_dict()["expressions"], [7])

    def test_rikka_response_can_opt_out_of_expression_actions(self):
        live2d_model = DummyLive2DModel({"soft_smile": 7, "neutral": 0})
        actions = rikka_response_to_actions(
            make_response("soft_smile"),
            live2d_model,
            enable_expression_actions=False,
        )

        self.assertEqual(actions.to_dict(), {})

    def test_rikka_response_maps_motion_and_gaze_without_expression(self):
        live2d_model = DummyLive2DModel(
            {"soft_smile": 7, "neutral": 0},
            model_info={
                "motionMap": {
                    "nod": {
                        "group": "",
                        "index": 16,
                        "priority": "normal",
                    },
                },
                "gazeMap": {
                    "chat": {
                        "parameters": {
                            "ParamAngleX": -5,
                            "ParamEyeBallX": -0.25,
                        },
                        "hold_ms": 1200,
                    },
                },
            },
        )
        actions = rikka_response_to_actions(
            make_response("soft_smile", motion="nod", gaze="chat"),
            live2d_model,
            enable_expression_actions=False,
        ).to_dict()

        self.assertNotIn("expressions", actions)
        self.assertEqual(actions["motions"][0]["name"], "nod")
        self.assertEqual(actions["motions"][0]["index"], 16)
        self.assertEqual(actions["gaze"]["name"], "chat")
        self.assertEqual(actions["gaze"]["parameters"]["ParamEyeBallX"], -0.25)

    def test_rikka_response_keeps_legacy_emotion_maps_usable(self):
        live2d_model = DummyLive2DModel({"joy": 3, "neutral": 0})
        actions = rikka_response_to_actions(
            make_response("happy"),
            live2d_model,
            enable_expression_actions=True,
        )

        self.assertEqual(actions.to_dict()["expressions"], [3])

    def test_rikka_response_omits_actions_when_no_expression_exists(self):
        live2d_model = DummyLive2DModel({})
        actions = rikka_response_to_actions(make_response("quiet"), live2d_model)

        self.assertEqual(actions.to_dict(), {})

    def test_configured_preset_is_inlined_in_expression_payload(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("soft_smile"),
            live2d_model,
        ).to_dict()

        expression = actions["expressions"][0]
        self.assertEqual(expression["name"], "soft_smile")
        self.assertEqual(expression["preset"]["label"], "浅笑")
        self.assertEqual(expression["preset"]["fade_ms"], 400)
        self.assertEqual(expression["preset"]["hold_after_speech_ms"], 2500)
        self.assertEqual(
            expression["preset"]["parameters"],
            {
                "ParamEyeLSmile": 0.35,
                "ParamEyeRSmile": 0.35,
                "ParamMouthForm": 0.15,
            },
        )

    def test_unknown_emotion_falls_back_to_neutral_preset(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("starry_eyes"),
            live2d_model,
        ).to_dict()

        expression = actions["expressions"][0]
        self.assertEqual(expression["name"], "neutral")
        self.assertEqual(expression["preset"]["parameters"], {})
        self.assertEqual(expression["preset"]["fade_ms"], 300)
        self.assertEqual(expression["preset"]["hold_after_speech_ms"], 2000)

    def test_unknown_emotion_without_neutral_preset_omits_expressions(self):
        live2d_model = DummyLive2DModel(
            {},
            model_info={
                "expressionPresets": {
                    "soft_smile": {"parameters": {"ParamMouthForm": 0.15}},
                },
            },
        )
        actions = rikka_response_to_actions(
            make_response("starry_eyes"),
            live2d_model,
        ).to_dict()

        self.assertNotIn("expressions", actions)

    def test_gesture_map_produces_envelope_payload(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("neutral", motion="nod"),
            live2d_model,
        ).to_dict()

        motion = actions["motions"][0]
        self.assertEqual(
            motion,
            {
                "name": "nod",
                "kind": "nod",
                "amplitude": 1.0,
                "duration_ms": 900,
                "cooldown_ms": 1800,
            },
        )
        self.assertNotIn("group", motion)
        self.assertNotIn("index", motion)

    def test_gesture_map_fills_missing_fields_with_defaults(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("neutral", motion="small_wave"),
            live2d_model,
        ).to_dict()

        motion = actions["motions"][0]
        self.assertEqual(motion["kind"], "greeting_bob")
        self.assertEqual(motion["amplitude"], 0.8)
        self.assertEqual(motion["duration_ms"], 1000)
        self.assertEqual(motion["cooldown_ms"], 1200)

    def test_disabled_gesture_entry_emits_no_motion(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("neutral", motion="look_away"),
            live2d_model,
        ).to_dict()

        self.assertNotIn("motions", actions)

    def test_unmapped_gesture_emits_no_motion(self):
        live2d_model = DummyLive2DModel({}, model_info=RIKKA_PRESET_MODEL_INFO)
        actions = rikka_response_to_actions(
            make_response("neutral", motion="thinking"),
            live2d_model,
        ).to_dict()

        self.assertNotIn("motions", actions)


if __name__ == "__main__":
    unittest.main()
