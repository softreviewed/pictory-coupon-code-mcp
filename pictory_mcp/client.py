"""Pictory API Client - Async HTTP wrapper for 45+ Pictory.ai REST endpoints."""

import os
import logging
import json
from typing import Any, Dict, List, Optional, Union
import httpx
from dotenv import load_dotenv

def _normalize_payload(payload: Any) -> Dict[str, Any]:
    """Helper to support dict payloads, file path, or object with file_path."""
    if isinstance(payload, dict) and "file_path" in payload:
        payload = payload["file_path"]
    if isinstance(payload, str):
        if os.path.exists(payload):
            with open(payload, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            return json.loads(payload)
        except Exception:
            pass
    return payload if isinstance(payload, dict) else {}

_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(_env_path)
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
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.exists(env_file):
                load_dotenv(env_file, override=True)
            self.api_key = os.getenv("PICTORY_API_KEY", "").strip()
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
        json_data: Optional[Any] = None,
        content: Optional[bytes] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Execute an HTTP request with error handling and response normalization."""
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        headers = self._headers()
        if custom_headers:
            headers.update(custom_headers)

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
                    json=json_data if content is None else None,
                    content=content,
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
        payload = _normalize_payload(payload)
        return await self._request("POST", "/v2/video/storyboard/render", json_data=payload)

    async def create_storyboard_preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v2/video/storyboard - Create preview job to review scenes before rendering."""
        payload = _normalize_payload(payload)
        return await self._request("POST", "/v2/video/storyboard", json_data=payload)

    async def render_from_preview(self, storyboard_job_id: str, webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """PUT /v2/video/render/{storyboardJobId} - Render final video from preview job."""
        body = {"webhook": webhook_url} if webhook_url else {}
        return await self._request("PUT", f"/v2/video/render/{storyboard_job_id}", json_data=body)

    async def render_video_with_modifications(self, render_params: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v2/video/render - Render final video from modified storyboard elements."""
        return await self._request("POST", "/v2/video/render", json_data=render_params)

    async def update_storyboard_elements(self, storyboard_id: str, elements_payload: Any) -> Dict[str, Any]:
        """PUT /v2/storyboard/{storyboardId}/elements - Surgically patch scenes/elements."""
        # Unpack if nested under 'elements'
        if isinstance(elements_payload, dict) and "elements" in elements_payload:
            elements_payload = elements_payload["elements"]
        return await self._request("PUT", f"/v2/storyboard/{storyboard_id}/elements", json_data=elements_payload)

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
        """DELETE /v1/jobs/{jobId}/clean - Remove job data and associated resources."""
        return await self._request("DELETE", f"/v1/jobs/{job_id}/clean")

    # -------------------------------------------------------------------------
    # 3. Video Transcription & Summarization (Shorts Generation)
    # -------------------------------------------------------------------------

    async def create_transcription(
        self,
        video_url: str,
        media_type: str = "video",
        language: str = "en-US",
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v2/transcription - Transcribe long-form video or audio."""
        body: Dict[str, Any] = {
            "fileUrl": video_url,
            "mediaType": media_type,
            "language": language,
        }
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", "/v2/transcription", json_data=body)

    async def generate_highlights_from_job(
        self,
        job_id: str,
        highlight_duration: int = 60,
        language: str = "en",
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v2/transcription/{jobId}/highlights - Extract viral short clips from completed transcription."""
        body: Dict[str, Any] = {
            "highlight_duration": highlight_duration,
            "language": language,
        }
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", f"/v2/transcription/{job_id}/highlights", json_data=body)

    async def generate_highlights_from_transcript(
        self,
        transcript: Union[List[Dict[str, Any]], str],
        highlight_duration: int = 60,
        duration: Optional[float] = None,
        language: str = "en",
        webhook: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v2/transcription/highlights - Extract AI highlights using custom/edited transcript."""
        body: Dict[str, Any] = {
            "transcript": transcript,
            "highlight_duration": highlight_duration,
            "language": language,
        }
        if duration is not None:
            body["duration"] = duration
        if webhook:
            body["webhook"] = webhook
        return await self._request("POST", "/v2/transcription/highlights", json_data=body)

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
            json_data={"fileName": file_name, "contentType": file_type},
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
        safe_size = max(20, page_size)
        body: Dict[str, Any] = {"page": page, "pageSize": safe_size}
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

    list_brands = None  # defined below
    async def list_video_brands(self) -> Dict[str, Any]:
        """GET /v1/brands/video - List saved video branding presets."""
        return await self._request("GET", "/v1/brands/video")

    list_brands = list_video_brands

    async def list_fonts(self) -> Dict[str, Any]:
        """GET /v1/video/storyboard/fonts - List available branding fonts."""
        return await self._request("GET", "/v1/video/storyboard/fonts")

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
        # Auto-normalize duration (e.g. 5 -> '5s', '8' -> '8s', '10s' -> '10s')
        dur_str = str(duration).strip().lower()
        if not dur_str.endswith("s"):
            dur_str = f"{dur_str}s"

        body: Dict[str, Any] = {
            "prompt": prompt,
            "model": model,
            "aspectRatio": aspect_ratio,
            "duration": dur_str,
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
        payload = _normalize_payload(payload)
        return await self._request("PUT", f"/v2/projects/{project_id}", json_data=payload)

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """DELETE /v2/projects/{projectId} - Delete project from account."""
        return await self._request("DELETE", f"/v2/projects/{project_id}")

    async def update_scene(
        self,
        project_id: str,
        scene_number: int,
        media_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        duration: Optional[float] = None,
        text: Optional[str] = None,
        asset_id: Optional[str] = None,
        library: str = "getty",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Surgically update a single scene's footage, thumbnail, duration, or text.

        Guarantees:
          - Auto-fetches latest project and concurrency versionId.
          - Validates scene_number (1-indexed).
          - Isolates and modifies ONLY the target scene.
          - Generates complete, valid imageMetadata (preventing web UI null pointer errors).
          - Synchronizes sentence and subtitle lines[0].text.
          - Automatically repairs / preserves all other scenes against string corruption.
          - Retries on optimistic concurrency lock (Invalid_Version).
        """
        for attempt in range(2):
            project = await self.get_project(project_id)
            if not project or "scenes" not in project:
                raise PictoryAPIError(404, f"Project '{project_id}' not found or invalid format")

            scenes = project.get("scenes", [])
            if not (1 <= scene_number <= len(scenes)):
                raise PictoryAPIError(400, f"scene_number {scene_number} is out of range. Project has {len(scenes)} scenes (1 to {len(scenes)}).")

            target = scenes[scene_number - 1]

            # 1. Update Media / Footage if provided
            if media_url:
                target["image"] = media_url
                meta_duration = float(duration) if duration is not None else 10.0
                preview_thumb = thumbnail_url or media_url.replace(".mp4", ".jpg")
                metadata_obj = {
                    "aspect_ratio": "16:9",
                    "caption": description or f"Scene {scene_number} footage",
                    "description": description or f"Scene {scene_number} footage",
                    "duration": meta_duration,
                    "id": str(asset_id) if asset_id else str(scene_number),
                    "keyword": "video",
                    "large": None,
                    "library": library,
                    "license_model": "royaltyfree",
                    "media_type": "video",
                    "orientation": "Horizontal",
                    "preview": media_url,
                    "preview_jpg": preview_thumb,
                    "thumb": media_url,
                    "thumb_jpg": preview_thumb,
                }
                target["imageMetadata"] = json.dumps(metadata_obj)

            # 2. Update Subtitle Text if provided
            if text:
                clean_text = text.strip()
                target["sentence"] = clean_text
                if target.get("lines") and len(target["lines"]) > 0:
                    target["lines"][0]["text"] = clean_text
                    target["lines"][0]["html"] = clean_text
                else:
                    target["lines"] = [{
                        "subSceneId": 1,
                        "time": int(target.get("time", 8)),
                        "text": clean_text,
                        "html": clean_text,
                        "format": {
                            "fontName": "Lato",
                            "fontSize": 24,
                            "fontColor": "rgb(255,255,255)",
                            "textAlign": "center",
                            "preset": "bottom-center"
                        },
                        "uuid": f"line_{scene_number}"
                    }]

            # 3. Clean root properties
            if "file_path" in project:
                del project["file_path"]

            # 4. Clean & validate all scenes' imageMetadata to prevent string corruption
            for idx, s in enumerate(scenes):
                meta = s.get("imageMetadata")
                if isinstance(meta, str):
                    try:
                        json.loads(meta)
                    except Exception:
                        try:
                            repaired = meta.replace('\\"', '"').replace('\"', '"')
                            json.loads(repaired)
                            s["imageMetadata"] = repaired
                        except Exception:
                            s["imageMetadata"] = json.dumps({
                                "duration": 5.0,
                                "library": "story_blocks",
                                "media_type": "video",
                                "preview": s.get("image", ""),
                                "preview_jpg": s.get("image", "")
                            })

            # 5. Push update
            res = await self.update_project(project_id, project)
            if isinstance(res, dict) and res.get("status") == "error" and res.get("errorCode") == "Invalid_Version":
                if attempt < 1:
                    logger.info("Retrying update_scene for %s due to version lock", project_id)
                    continue
                raise PictoryAPIError(409, "Concurrent edit conflict on project. Please try again.", res)

            return {
                "success": True,
                "project_id": project_id,
                "scene_number": scene_number,
                "updated_image": target.get("image"),
                "updated_text": target.get("sentence"),
                "version_id": res.get("versionId"),
                "total_scenes": len(scenes),
            }


    # -------------------------------------------------------------------------
    # 9. Video Templates CRUD
    # -------------------------------------------------------------------------

    async def list_templates(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """GET /v1/templates - List saved master video templates."""
        return await self._request("GET", "/v1/templates", params={"page": page, "pageSize": page_size})

    async def get_template(self, template_id: str) -> Dict[str, Any]:
        """GET /v1/templates/{templateId} - Get template configuration by ID."""
        return await self._request("GET", f"/v1/templates/{template_id}")

    async def create_template(
        self,
        template_file_or_payload: Union[str, bytes, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """POST /v1/templates - Upload a .pictai project file to create a reusable template."""
        if isinstance(template_file_or_payload, str):
            if os.path.exists(template_file_or_payload):
                with open(template_file_or_payload, "rb") as f:
                    file_bytes = f.read()
                return await self._request(
                    "POST",
                    "/v1/templates",
                    content=file_bytes,
                    custom_headers={"Content-Type": "application/octet-stream"},
                )
            else:
                raise ValueError(f"Template file not found at path: {template_file_or_payload}")
        elif isinstance(template_file_or_payload, (bytes, bytearray)):
            return await self._request(
                "POST",
                "/v1/templates",
                content=bytes(template_file_or_payload),
                custom_headers={"Content-Type": "application/octet-stream"},
            )
        elif isinstance(template_file_or_payload, dict):
            file_path = template_file_or_payload.get("file_path") or template_file_or_payload.get("filePath")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                return await self._request(
                    "POST",
                    "/v1/templates",
                    content=file_bytes,
                    custom_headers={"Content-Type": "application/octet-stream"},
                )
            return await self._request("POST", "/v1/templates", json_data=template_file_or_payload)
        else:
            raise TypeError("template_file_or_payload must be a file path, bytes, or payload dict")

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
        """GET /v1/vimeo-connections - List Vimeo publishing connections."""
        return await self._request("GET", "/v1/vimeo-connections")

    async def get_vimeo_connection(self, connection_id: str) -> Dict[str, Any]:
        """GET /v1/vimeo-connections/{connectionId} - Get Vimeo connection details."""
        return await self._request("GET", f"/v1/vimeo-connections/{connection_id}")

    async def create_vimeo_connection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/vimeo-connections - Register a Vimeo connection."""
        return await self._request("POST", "/v1/vimeo-connections", json_data=payload)

    async def update_vimeo_connection(self, connection_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v1/vimeo-connections/{connectionId} - Update Vimeo connection."""
        return await self._request("PUT", f"/v1/vimeo-connections/{connection_id}", json_data=payload)

    async def delete_vimeo_connection(self, connection_id: str) -> Dict[str, Any]:
        """DELETE /v1/vimeo-connections/{connectionId} - Disconnect Vimeo."""
        return await self._request("DELETE", f"/v1/vimeo-connections/{connection_id}")

    async def list_aws_connections(self) -> Dict[str, Any]:
        """GET /v1/awsconnections - List private AWS S3 bucket connections."""
        return await self._request("GET", "/v1/awsconnections")

    async def get_aws_connection(self, connection_id: str) -> Dict[str, Any]:
        """GET /v1/awsconnections/{connectionId} - Get AWS private connection details."""
        return await self._request("GET", f"/v1/awsconnections/{connection_id}")

    async def create_aws_connection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /v1/awsconnections - Connect private AWS S3 assets with IAM credentials."""
        return await self._request("POST", "/v1/awsconnections", json_data=payload)

    async def update_aws_connection(self, connection_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PUT /v1/awsconnections/{connectionId} - Update AWS connection."""
        return await self._request("PUT", f"/v1/awsconnections/{connection_id}", json_data=payload)

    async def delete_aws_connection(self, connection_id: str) -> Dict[str, Any]:
        """DELETE /v1/awsconnections/{connectionId} - Disconnect AWS S3."""
        return await self._request("DELETE", f"/v1/awsconnections/{connection_id}")

    # -------------------------------------------------------------------------
    # 11. Account Quota & Usage
    # -------------------------------------------------------------------------

    async def get_quota(self) -> Dict[str, Any]:
        """GET /v1/quota - Get current video render quota and usage limits."""
        return await self._request("GET", "/v1/quota")

    async def get_aicredits_usage(self) -> Dict[str, Any]:
        """GET /v1/aicredits/usage - Get AI credits consumption details."""
        return await self._request("GET", "/v1/aicredits/usage")



