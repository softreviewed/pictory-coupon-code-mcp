"""Unit test suite for Pictory MCP Server."""

import sys
import os
import unittest
from unittest.mock import AsyncMock, patch

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pictory_mcp.server import (
    mcp,
    pictory_video,
    pictory_transcribe,
    pictory_assets,
    pictory_projects,
    pictory_integrations,
)
from pictory_mcp.client import PictoryClient, PictoryAPIError


def _fn(tool):
    """Helper to get callable function whether direct or wrapped in FunctionTool."""
    return getattr(tool, "fn", tool)


class TestPictoryMCPServer(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying all tools, validation paths, and mocked client responses."""

    def test_tools_registered(self):
        """Verify all 5 tools are registered on FastMCP server."""
        tools = mcp._tool_manager._tools
        expected_tools = [
            "pictory_video",
            "pictory_transcribe",
            "pictory_assets",
            "pictory_projects",
            "pictory_integrations",
        ]
        for t in expected_tools:
            self.assertIn(t, tools, f"Tool {t} should be registered in FastMCP")

    async def test_pictory_video_unknown_action(self):
        """Verify unknown action returns structured error."""
        res = await _fn(pictory_video)(action="invalid_action")
        self.assertFalse(res["success"])
        self.assertIn("Unknown action", res["error"])

    async def test_pictory_video_validation(self):
        """Verify parameter validation for render_storyboard and poll_job."""
        res1 = await _fn(pictory_video)(action="render_storyboard")
        self.assertFalse(res1["success"])
        self.assertIn("storyboard_payload is required", res1["error"])

        res2 = await _fn(pictory_video)(action="poll_job")
        self.assertFalse(res2["success"])
        self.assertIn("job_id is required", res2["error"])

    @patch.object(PictoryClient, "render_storyboard", new_callable=AsyncMock)
    async def test_pictory_video_render_success(self, mock_render):
        """Verify successful storyboard rendering with mocked API."""
        mock_render.return_value = {"jobId": "job-12345", "status": "queued"}
        res = await _fn(pictory_video)(
            action="render_storyboard",
            storyboard_payload={"videoName": "test", "scenes": [{"story": "Hello"}]},
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["jobId"], "job-12345")

    async def test_pictory_transcribe_validation(self):
        """Verify transcribe parameter requirements."""
        res = await _fn(pictory_transcribe)(action="create_transcription")
        self.assertFalse(res["success"])
        self.assertIn("video_url is required", res["error"])

    @patch.object(PictoryClient, "create_transcription", new_callable=AsyncMock)
    async def test_pictory_transcribe_success(self, mock_transcribe):
        """Verify transcription trigger with mocked client."""
        mock_transcribe.return_value = {"jobId": "tx-999", "status": "processing"}
        res = await _fn(pictory_transcribe)(
            action="create_transcription",
            video_url="https://example.com/podcast.mp4",
            language="en-US",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["jobId"], "tx-999")

    @patch.object(PictoryClient, "search_media", new_callable=AsyncMock)
    async def test_pictory_assets_search(self, mock_search):
        """Verify media search tool with mocked client."""
        mock_search.return_value = {"items": [{"assetId": "ast_1", "mediaType": "video"}]}
        res = await _fn(pictory_assets)(action="search_media", query="nature")
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]["items"]), 1)

    @patch.object(PictoryClient, "get_music_moods", new_callable=AsyncMock)
    async def test_pictory_assets_music_filters(self, mock_moods):
        """Verify music filter discovery."""
        mock_moods.return_value = ["Happy", "Inspiring", "Cinematic"]
        res = await _fn(pictory_assets)(action="get_music_filters", filter_type="moods")
        self.assertTrue(res["success"])
        self.assertEqual(res["filter_type"], "moods")

    @patch.object(PictoryClient, "list_projects", new_callable=AsyncMock)
    async def test_pictory_projects_list(self, mock_list):
        """Verify listing projects."""
        mock_list.return_value = {"projects": [{"id": "proj_1", "name": "Demo"}]}
        res = await _fn(pictory_projects)(action="list_projects")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["projects"][0]["name"], "Demo")

    @patch.object(PictoryClient, "get_quota", new_callable=AsyncMock)
    @patch.object(PictoryClient, "get_aicredits_usage", new_callable=AsyncMock)
    async def test_pictory_integrations_quota(self, mock_credits, mock_quota):
        """Verify quota and credits retrieval."""
        mock_quota.return_value = {"rendersRemaining": 50, "quotaLimit": 100}
        mock_credits.return_value = {"creditsRemaining": 250}

        res_q = await _fn(pictory_integrations)(action="get_quota")
        self.assertTrue(res_q["success"])
        self.assertEqual(res_q["data"]["rendersRemaining"], 50)

        res_c = await _fn(pictory_integrations)(action="get_credit_usage")
        self.assertTrue(res_c["success"])
        self.assertEqual(res_c["data"]["creditsRemaining"], 250)


    async def test_pictory_projects_update_scene_validation(self):
        """Verify update_scene parameter validation."""
        res1 = await _fn(pictory_projects)(action="update_scene")
        self.assertFalse(res1["success"])
        self.assertIn("project_id is required", res1["error"])

        res2 = await _fn(pictory_projects)(action="update_scene", project_id="proj_1")
        self.assertFalse(res2["success"])
        self.assertIn("scene_number is required", res2["error"])

    @patch.object(PictoryClient, "update_scene", new_callable=AsyncMock)
    async def test_pictory_projects_update_scene_success(self, mock_update_scene):
        """Verify update_scene tool dispatch to PictoryClient."""
        mock_update_scene.return_value = {
            "success": True,
            "project_id": "proj_1",
            "scene_number": 2,
            "updated_image": "https://example.com/lion.mp4",
            "version_id": "v_test_99",
            "total_scenes": 5,
        }
        res = await _fn(pictory_projects)(
            action="update_scene",
            project_id="proj_1",
            scene_number=2,
            media_url="https://example.com/lion.mp4",
            duration=10.0,
            text="A majestic African lion.",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["scene_number"], 2)
        self.assertEqual(res["data"]["version_id"], "v_test_99")

    @patch.object(PictoryClient, "get_project", new_callable=AsyncMock)
    @patch.object(PictoryClient, "update_project", new_callable=AsyncMock)
    async def test_client_update_scene_logic_and_healing(self, mock_update, mock_get):
        """Verify client.update_scene logic: scene isolation, subtitle sync, and imageMetadata healing."""
        mock_get.return_value = {
            "versionId": "v1",
            "scenes": [
                {
                    "subSceneId": 1,
                    "image": "https://example.com/scene1.mp4",
                    "sentence": "Scene 1 intact",
                    "imageMetadata": '{"duration": 5.0, "library": "getty"}',
                },
                {
                    "subSceneId": 2,
                    "image": "https://example.com/old_lion.mp4",
                    "sentence": "Old lion text",
                    "lines": [{"text": "Old lion text", "html": "Old lion text"}],
                    "imageMetadata": '{"duration": 8.0, "library": "storyblocks"}',
                },
                {
                    "subSceneId": 3,
                    "image": "https://example.com/scene3.mp4",
                    "sentence": "Corrupted metadata scene",
                    "imageMetadata": '{\\"duration\\": 6.0}',  # Corrupted quotes
                },
            ],
        }
        mock_update.return_value = {"status": "ok", "versionId": "v2"}

        client = PictoryClient(api_key="test")
        res = await client.update_scene(
            project_id="proj_test",
            scene_number=2,
            media_url="https://example.com/new_lion.mp4",
            thumbnail_url="https://example.com/new_lion.jpg",
            duration=12.5,
            text="Brand new lion subtitle text",
            asset_id="lion_999",
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["version_id"], "v2")

        # Verify update_project payload
        mock_update.assert_called_once()
        sent_project = mock_update.call_args[0][1]
        sent_scenes = sent_project["scenes"]

        # Scene 1 must remain intact
        self.assertEqual(sent_scenes[0]["image"], "https://example.com/scene1.mp4")

        # Scene 2 must be updated with synchronized subtitles
        self.assertEqual(sent_scenes[1]["image"], "https://example.com/new_lion.mp4")
        self.assertEqual(sent_scenes[1]["sentence"], "Brand new lion subtitle text")
        self.assertEqual(sent_scenes[1]["lines"][0]["text"], "Brand new lion subtitle text")

        # Scene 3 corrupted metadata must be healed
        import json
        repaired_meta = json.loads(sent_scenes[2]["imageMetadata"])
        self.assertIsInstance(repaired_meta, dict)


    @patch.object(PictoryClient, "render_video_with_modifications", new_callable=AsyncMock)
    async def test_pictory_video_render_with_modifications(self, mock_render_mod):
        """Verify render_with_modifications action passes renderParams to client."""
        mock_render_mod.return_value = {"jobId": "job_mod_123", "status": "queued"}
        res = await _fn(pictory_video)(
            action="render_with_modifications",
            storyboard_payload={"renderParams": {"scenes": []}},
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["jobId"], "job_mod_123")
        mock_render_mod.assert_called_once_with({"renderParams": {"scenes": []}})

    @patch.object(PictoryClient, "update_storyboard_elements", new_callable=AsyncMock)
    async def test_pictory_video_update_elements(self, mock_update_elem):
        """Verify update_elements action in pictory_video."""
        mock_update_elem.return_value = {"status": "ok"}
        res = await _fn(pictory_video)(
            action="update_elements",
            job_id="job_preview_456",
            elements_payload={"elements": [{"id": "elem_1", "type": "text"}]},
        )
        self.assertTrue(res["success"])
        mock_update_elem.assert_called_once_with("job_preview_456", {"elements": [{"id": "elem_1", "type": "text"}]})

    @patch.object(PictoryClient, "create_template", new_callable=AsyncMock)
    async def test_pictory_projects_create_template(self, mock_create_tmpl):
        """Verify create_template handles file_path parameter."""
        mock_create_tmpl.return_value = {"templateId": "tmpl_999", "name": "Brand Template"}
        res = await _fn(pictory_projects)(
            action="create_template",
            file_path="C:/fake/path/template.pictai",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["templateId"], "tmpl_999")
        mock_create_tmpl.assert_called_once_with("C:/fake/path/template.pictai")

    @patch.object(PictoryClient, "update_vimeo_connection", new_callable=AsyncMock)
    @patch.object(PictoryClient, "update_aws_connection", new_callable=AsyncMock)
    @patch.object(PictoryClient, "clean_job", new_callable=AsyncMock)
    async def test_pictory_integrations_updates_and_clean(self, mock_clean, mock_aws, mock_vimeo):
        """Verify update_vimeo_connection, update_aws_connection, and clean_job in pictory_integrations."""
        mock_vimeo.return_value = {"success": True}
        mock_aws.return_value = {"success": True}
        mock_clean.return_value = {"success": True, "job_id": "job_to_clean"}

        # Vimeo update
        rv = await _fn(pictory_integrations)(
            action="update_vimeo_connection",
            connection_id="vimeo_conn_1",
            connection_payload={"enabled": True},
        )
        self.assertTrue(rv["success"])
        mock_vimeo.assert_called_once_with("vimeo_conn_1", {"enabled": True})

        # AWS update
        ra = await _fn(pictory_integrations)(
            action="update_aws_connection",
            connection_id="aws_conn_1",
            connection_payload={"enabled": True},
        )
        self.assertTrue(ra["success"])
        mock_aws.assert_called_once_with("aws_conn_1", {"enabled": True})

        # Clean job
        rc = await _fn(pictory_integrations)(
            action="clean_job",
            job_id="job_to_clean",
        )
        self.assertTrue(rc["success"])
        mock_clean.assert_called_once_with("job_to_clean")


if __name__ == "__main__":
    unittest.main()
