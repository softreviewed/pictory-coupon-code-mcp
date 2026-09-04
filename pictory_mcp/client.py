"""Pictory API Client - Async HTTP wrapper for 45+ Pictory.ai REST endpoints."""

import os
import logging
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("pictory_mcp.client")

DEFAULT_BASE_URL = "https://api.pictory.ai/pictoryapis"


class PictoryAPIError(Exception):
    """Exception raised when Pictory API returns an error."""

    def __init__(self, status_code: int, message: str, details: Optional[Any] = None):
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.message = message
        self.details = details


class PictoryClient:
    """Universal Async Client for all Pictory.ai v1 and v2 API endpoints."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("PICTORY_API_KEY", "").strip()
        self.base_url = (base_url or os.getenv("PICTORY_API_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise PictoryAPIError(
                status_code=401,
                message="PICTORY_API_KEY is not set. Please set the PICTORY_API_KEY environment variable or pass it in settings.",
            )
        # Note: Pictory uses raw API key in Authorization header WITHOUT 'Bearer' prefix
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "pictory-mcp/1.0.0",
        }

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Execute an HTTP request with error handling and response normalization."""
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers = self._headers()

        # Filter out None values in params
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
            except httpx.RequestError as exc:
                logger.error("HTTP network error reaching %s: %s", url, exc)
                raise PictoryAPIError(
                    status_code=503,
                    message=f"Network error communicating with Pictory API: {str(exc)}",
                ) from exc

            # Parse JSON body
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text}

            if not response.is_success:
                error_msg = (
                    data.get("message")
                    or data.get("error_message")
                    or data.get("error")
                    or f"Request failed with status code {response.status_code}"
                )
                fields = data.get("fields")
                logger.error("Pictory API error [%s]: %s (fields: %s)", response.status_code, error_msg, fields)
                raise PictoryAPIError(
                    status_code=response.status_code,
                    message=error_msg,
                    details=fields or data,
                )

            return data

    # -------------------------------------------------------------------------
    # 1. Videos & Storyboard Rendering
    # -------------------------------------------------------------------------

    async def render_storyboard(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v2/video/storyboard/render - Render video from storyboard."""
        return await self._request("POST", "/v2/video/storyboard/render", json_data=payload)

    async def create_storyboard_preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v2/video/storyboard - Create preview job to review scenes before rendering."""
        return await self._request("POST", "/v2/video/storyboard", json_data=payload)

    async def render_from_preview(self, storyboard_job_id: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """PUT /v2/video/render/{storyboardJobId} - Render final video from preview job."""
        body = {"webhook": webhook_url} if webhook_url else {}
        return await self._request("PUT", f"/v2/video/render/{storyboard_job_id}", json_data=body)

    async def update_storyboard_elements(self, storyboard_id: str, elements_payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v2/video/storyboard/{storyboardId}/elements - Surgically patch scenes/elements."""
        return await self._request("PUT", f"/v2/video/storyboard/{storyboard_id}/elements", json_data=elements_payload)

    async def render_project(self, project_id: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """POST /v2/projects/{projectId}/render - Render a saved project."""
        body = {"webhook": webhook_url} if webhook_url else {}
        return await self._request("POST", f"/v2/projects/{project_id}/render", json_data=body)

    # -------------------------------------------------------------------------
    # 2. Jobs & Polling
    # -------------------------------------------------------------------------

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """GET /v1/jobs/{jobId} - Poll job status (render, preview, transcription, AI gen)."""
        return await self._request("GET", f"/v1/jobs/{job_id}")

    async def list_jobs(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v1/jobs - List recent jobs."""
        return await self._request("GET", "/v1/jobs", params={"page": page, "pageSize": page_size})

    async def clean_job(self, job_id: str) -> Dict[str, Any]:
        """DELETE /v1/jobs/{jobId} - Cancel or clean a job."""
        return await self._request("DELETE", f"/v1/jobs/{job_id}")

    # -------------------------------------------------------------------------
    # 3. Video Transcription & Summarization (Shorts Generation)
    # -------------------------------------------------------------------------

    async def create_transcription(
        self,
        video_url: str,
        language: str = "en-US",
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v2/transcription - Transcribe long-form video or audio."""
        body: Dict[str, Any] = {"videoUrl": video_url, "language": language}
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", "/v2/transcription", json_data=body)

    async def generate_highlights_from_job(
        self,
        job_id: str,
        max_duration: int = 60,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """POST /v2/transcription/highlights - Extract viral short clips from completed transcription."""
        body: Dict[str, Any] = {"jobId": job_id, "maxDuration": max_duration}
        if settings:
            body.update(settings)
        return await self._request("POST", "/v2/transcription/highlights", json_data=body)

    async def generate_highlights_from_transcript(
        self,
        transcript_text: str,
        video_url: str,
        max_duration: int = 60,
    ) -> Dict[str, Any]:
        """POST /v2/transcription/highlights/custom - Extract highlights using custom text."""
        body = {
            "transcript": transcript_text,
            "videoUrl": video_url,
            "maxDuration": max_duration,
        }
        return await self._request("POST", "/v2/transcription/highlights/custom", json_data=body)

    # -------------------------------------------------------------------------
    # 4. Media Management & Stock Search
    # -------------------------------------------------------------------------

    async def search_media(
        self,
        query: str,
        media_type: str = "video",
        category: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """GET /v1/media/search - Search stock videos & images (Getty / Storyblocks)."""
        params = {
            "keyword": query,
            "mediaType": media_type,
            "language": language,
            "category": category,
        }
        return await self._request("GET", "/v1/media/search", params=params)

    async def generate_upload_url(self, file_name: str, file_type: str) -> Dict[str, Any]:
        """POST /v1/media/generateurl - Get signed AWS S3 URL for uploading custom media."""
        return await self._request(
            "POST",
            "/v1/media/generateurl",
            json_data={"fileName": file_name, "fileType": file_type},
        )

    # -------------------------------------------------------------------------
    # 5. Music Search & Filters
    # -------------------------------------------------------------------------

    async def search_music(
        self,
        query: Optional[str] = None,
        mood: Optional[List[str]] = None,
        genre: Optional[List[str]] = None,
        genre_group: Optional[List[str]] = None,
        instrument: Optional[List[str]] = None,
        purpose: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """POST /v1/music/search - Search music tracks with rich mood/genre filters."""
        body: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if query:
            body["query"] = query
        if mood:
            body["mood"] = mood
        if genre:
            body["genre"] = genre
        if genre_group:
            body["genreGroup"] = genre_group
        if instrument:
            body["instrument"] = instrument
        if purpose:
            body["purpose"] = purpose
        return await self._request("POST", "/v1/music/search", json_data=body)

    async def get_music_moods(self) -> Dict[str, Any]:
        """GET /v1/music/moods - List available music moods."""
        return await self._request("GET", "/v1/music/moods")

    async def get_music_genres(self) -> Dict[str, Any]:
        """GET /v1/music/genres - List available music genres."""
        return await self._request("GET", "/v1/music/genres")

    async def get_music_genre_groups(self) -> Dict[str, Any]:
        """GET /v1/music/genres/groups - List music genre groups."""
        return await self._request("GET", "/v1/music/genres/groups")

    async def get_music_instruments(self) -> Dict[str, Any]:
        """GET /v1/music/instruments - List music instruments."""
        return await self._request("GET", "/v1/music/instruments")

    async def get_music_purposes(self) -> Dict[str, Any]:
        """GET /v1/music/purposes - List music purposes."""
        return await self._request("GET", "/v1/music/purposes")

    # -------------------------------------------------------------------------
    # 6. Voices, Avatars, Layouts, & Styles
    # -------------------------------------------------------------------------

    async def list_voiceovers(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """GET /v1/voiceovers/tracks - List AI narrator voices."""
        params = {"language": language, "gender": gender, "service": service}
        return await self._request("GET", "/v1/voiceovers/tracks", params=params)

    async def list_avatars(self) -> Dict[str, Any]:
        """GET /v1/avatars - List available realistic AI presenter avatars."""
        return await self._request("GET", "/v1/avatars")

    async def list_smart_layouts(self) -> Dict[str, Any]:
        """GET /v1/smartlayouts - List smart responsive layout designs."""
        return await self._request("GET", "/v1/smartlayouts")

    async def list_text_styles(self) -> Dict[str, Any]:
        """GET /v1/styles - List subtitle text styling presets."""
        return await self._request("GET", "/v1/styles")

    async def list_video_brands(self) -> Dict[str, Any]:
        """GET /v1/brands/video - List saved video branding presets."""
        return await self._request("GET", "/v1/brands/video")

    async def list_fonts(self) -> Dict[str, Any]:
        """GET /v1/fonts - List available branding fonts."""
        return await self._request("GET", "/v1/fonts")

    # -------------------------------------------------------------------------
    # 7. AI Studio (Standalone Image & Video Generation)
    # -------------------------------------------------------------------------

    async def generate_ai_image(
        self,
        prompt: str,
        model: str = "seedream3.0",
        aspect_ratio: str = "16:9",
        style: Optional[str] = None,
        reference_image_url: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/aistudio/images - Generate AI image (seedream, flux-schnell, nanobanana)."""
        body: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "aspectRatio": aspect_ratio,
        }
        if style:
            body["style"] = style
        if reference_image_url:
            body["referenceImageUrl"] = reference_image_url
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", "/v1/aistudio/images", json_data=body)

    async def generate_ai_video(
        self,
        prompt: str,
        model: str = "pixverse5.5",
        aspect_ratio: str = "16:9",
        duration: int = 5,
        first_frame_image_url: Optional[str] = None,
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/aistudio/videos - Generate AI video (pixverse5.5, veo3.1)."""
        body: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "aspectRatio": aspect_ratio,
            "duration": duration,
        }
        if first_frame_image_url:
            body["firstFrameImageUrl"] = first_frame_image_url
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", "/v1/aistudio/videos", json_data=body)

    async def get_generated_images(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v1/aistudio/images - List past AI Studio images."""
        return await self._request("GET", "/v1/aistudio/images", params={"page": page, "pageSize": page_size})

    async def get_generated_videos(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v1/aistudio/videos - List past AI Studio videos."""
        return await self._request("GET", "/v1/aistudio/videos", params={"page": page, "pageSize": page_size})

    # -------------------------------------------------------------------------
    # 8. Projects CRUD (Web UI Synchronization)
    # -------------------------------------------------------------------------

    async def list_projects(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v2/projects - List saved projects in Pictory account."""
        return await self._request("GET", "/v2/projects", params={"page": page, "pageSize": page_size})

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """GET /v2/projects/{projectId} - Get project details by ID."""
        return await self._request("GET", f"/v2/projects/{project_id}")

    async def update_project(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v2/projects/{projectId} - Update project scenes and properties."""
        return await self._request("PUT", f"/v2/projects/{project_id}", json_data=payload)

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """DELETE /v2/projects/{projectId} - Delete project from account."""
        return await self._request("DELETE", f"/v2/projects/{project_id}")

    # -------------------------------------------------------------------------
    # 9. Video Templates CRUD
    # -------------------------------------------------------------------------

    async def list_templates(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v1/templates - List saved master video templates."""
        return await self._request("GET", "/v1/templates", params={"page": page, "pageSize": page_size})

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """GET /v1/templates/{templateId} - Get template configuration by ID."""
        return await self._request("GET", f"/v1/templates/{template_id}")

    async def create_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/templates - Create a new video template."""
        return await self._request("POST", "/v1/templates", json_data=payload)

    async def update_template(self, template_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v1/templates/{templateId} - Update an existing template."""
        return await self._request("PUT", f"/v1/templates/{template_id}", json_data=payload)

    async def delete_template(self, template_id: str) -> Dict[str, Any]:
        """DELETE /v1/templates/{templateId} - Delete template."""
        return await self._request("DELETE", f"/v1/templates/{template_id}")

    # -------------------------------------------------------------------------
    # 10. Third-Party Integrations (Vimeo & AWS Private S3)
    # -------------------------------------------------------------------------

    async def list_vimeo_connections(self) -> Dict[str, Any]:
        """GET /v1/vimeo - List Vimeo publishing connections."""
        return await self._request("GET", "/v1/vimeo")

    async def get_vimeo_connection(self, connection_id: str) -> Dict[str, Any]:
        """GET /v1/vimeo/{connectionId} - Get Vimeo connection details."""
        return await self._request("GET", f"/v1/vimeo/{connection_id}")

    async def create_vimeo_connection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/vimeo - Register a Vimeo connection."""
        return await self._request("POST", "/v1/vimeo", json_data=payload)

    async def update_vimeo_connection(self, connection_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v1/vimeo/{connectionId} - Update Vimeo connection."""
        return await self._request("PUT", f"/v1/vimeo/{connection_id}", json_data=payload)

    async def delete_vimeo_connection(self, connection_id: str) -> Dict[str, Any]:
        """DELETE /v1/vimeo/{connectionId} - Disconnect Vimeo."""
        return await self._request("DELETE", f"/v1/vimeo/{connection_id}")

    async def list_aws_connections(self) -> Dict[str, Any]:
        """GET /v1/aws - List private AWS S3 bucket connections."""
        return await self._request("GET", "/v1/aws")

    async def get_aws_connection(self, connection_id: str) -> Dict[str, Any]:
        """GET /v1/aws/{connectionId} - Get AWS private connection details."""
        return await self._request("GET", f"/v1/aws/{connection_id}")

    async def create_aws_connection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/aws - Connect private AWS S3 assets with IAM credentials."""
        return await self._request("POST", "/v1/aws", json_data=payload)

    async def update_aws_connection(self, connection_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v1/aws/{connectionId} - Update AWS connection."""
        return await self._request("PUT", f"/v1/aws/{connection_id}", json_data=payload)

    async def delete_aws_connection(self, connection_id: str) -> Dict[str, Any]:
        """DELETE /v1/aws/{connectionId} - Disconnect AWS S3."""
        return await self._request("DELETE", f"/v1/aws/{connection_id}")

    # -------------------------------------------------------------------------
    # 11. Account Quota & Usage
    # -------------------------------------------------------------------------

    async def get_quota(self) -> Dict[str, Any]:
        """GET /v1/quota - Get current video render quota and usage limits."""
        return await self._request("GET", "/v1/quota")

    async def get_aicredits_usage(self) -> Dict[str, Any]:
        """GET /v1/aicredits/usage - Get AI credits consumption details."""
        return await self._request("GET", "/v1/aicredits/usage")
