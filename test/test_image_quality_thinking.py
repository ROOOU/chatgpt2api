from __future__ import annotations

import unittest
from unittest.mock import patch

from services.openai_backend_api import ChatRequirements, OpenAIBackendAPI
from services.protocol import openai_v1_image_edit, openai_v1_image_generations


class ImageQualityThinkingTests(unittest.TestCase):
    def test_quality_maps_to_chatgpt_thinking_effort(self):
        backend = OpenAIBackendAPI(access_token="test-token")
        model_slug = "gpt-5-5-thinking"

        self.assertEqual(backend._image_thinking_effort(model_slug, "low"), "")
        self.assertEqual(backend._image_thinking_effort(model_slug, "medium"), "standard")
        self.assertEqual(backend._image_thinking_effort(model_slug, "high"), "extended")

    def test_non_thinking_model_ignores_quality_effort(self):
        backend = OpenAIBackendAPI(access_token="test-token")

        self.assertEqual(backend._image_thinking_effort("auto", "medium"), "")

    def test_medium_quality_is_sent_as_standard_effort(self):
        backend = OpenAIBackendAPI(access_token="test-token")
        captured = {}

        class DummySession:
            headers = {}

            def post(self, _url, **kwargs):
                captured["json"] = kwargs["json"]

                class DummyResponse:
                    status_code = 200
                    text = "{}"

                    def json(self):
                        return {"conduit_token": "test-conduit-token"}

                return DummyResponse()

        backend.session = DummySession()
        backend._prepare_image_conversation(
            "test",
            ChatRequirements(token="test-requirements-token"),
            "gpt-image-2",
            "medium",
        )

        self.assertEqual(captured["json"]["thinking_effort"], "standard")

    def test_generation_request_preserves_quality(self):
        captured = {}

        def fake_outputs(request):
            captured["quality"] = request.quality
            return iter(())

        with patch.object(openai_v1_image_generations, "stream_image_outputs_with_pool", fake_outputs):
            openai_v1_image_generations.handle({
                "prompt": "test",
                "model": "gpt-image-2",
                "quality": "medium",
            })

        self.assertEqual(captured["quality"], "medium")

    def test_edit_request_preserves_quality(self):
        captured = {}

        def fake_outputs(request):
            captured["quality"] = request.quality
            return iter(())

        with patch.object(openai_v1_image_edit, "stream_image_outputs_with_pool", fake_outputs):
            openai_v1_image_edit.handle({
                "prompt": "test",
                "images": [(b"png", "input.png", "image/png")],
                "model": "gpt-image-2",
                "quality": "medium",
            })

        self.assertEqual(captured["quality"], "medium")


if __name__ == "__main__":
    unittest.main()
