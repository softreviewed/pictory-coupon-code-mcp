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


if __name__ == "__main__":
    unittest.main()
