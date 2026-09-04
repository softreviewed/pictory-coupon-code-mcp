"""Pictory MCP Server - Community Model Context Protocol Server for Pictory.ai."""

import logging
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP
from pictory_mcp.client import PictoryClient, PictoryAPIError

import sys
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)
logger = logging.getLogger("pictory_mcp.server")

# Initialize FastMCP Server
mcp = FastMCP(
    name="Pictory AI Video Studio",
    instructions="Universal MCP Server for Pictory.ai. Controls text-to-video storyboard rendering, long-video transcription into viral short clips, stock and AI asset discovery, template management, and cloud integrations.",
)


def _client() -> PictoryClient:
    """Instantiate Pictory API client."""
    return PictoryClient()


# =============================================================================
# Tool 1: pictory_video
# =============================================================================

@mcp.tool()
async def pictory_video(
    action: str,
    storyboard_payload: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
    project_id: Optional[str] = None,
    elements_payload: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Create, render, preview, and patch Pictory videos.

    Supported Actions:
      - 'render_storyboard': Render a full video from a storyboard or script payload (POST /v2/video/storyboard/render).
      - 'create_preview': Create a preview job to review storyboard scenes before spending render credits (POST /v2/video/storyboard).
      - 'render_from_preview': Render final video from an existing storyboard preview job (PUT /v2/video/render/{job_id}).
      - 'render_with_modifications': Render final video from modified storyboard preview elements (POST /v2/video/render).
      - 'update_elements': Surgically edit scenes, text, shapes, or visuals in an existing storyboard (PUT /v2/storyboard/{job_id}/elements).
      - 'render_project': Render a video directly from an existing saved Pictory project (POST /v2/projects/{project_id}/render).
      - 'poll_job': Check the status, progress percentage, error codes, and video download URL of a job (GET /v1/jobs/{job_id}).

    Args:
        action: The operation to execute ('render_storyboard', 'create_preview', 'render_from_preview', 'update_elements', 'render_project', 'poll_job').
        storyboard_payload: Complete storyboard JSON definition (videoName, aspectRatio, scenes, voiceOver, etc.).
        job_id: The job ID returned from preview, render, or transcription (required for poll_job, render_from_preview, update_elements).
        project_id: The saved Pictory project ID (required for render_project).
        elements_payload: Partial elements JSON for surgical storyboard updates.
        webhook_url: Optional webhook URL to receive callback notification on job completion.
    """
    client = _client()
    try:
        if action == "render_storyboard":
            if not storyboard_payload:
                return {"success": False, "error": "storyboard_payload is required for 'render_storyboard'"}
            res = await client.render_storyboard(storyboard_payload)
            return {"success": True, "data": res}

        elif action == "create_preview":
            if not storyboard_payload:
                return {"success": False, "error": "storyboard_payload is required for 'create_preview'"}
            res = await client.create_storyboard_preview(storyboard_payload)
            return {"success": True, "data": res}

        elif action == "render_from_preview":
            if not job_id:
                return {"success": False, "error": "job_id (storyboard preview job ID) is required for 'render_from_preview'"}
            res = await client.render_from_preview(job_id, webhook_url=webhook_url)
            return {"success": True, "data": res}

        elif action == "render_with_modifications":
            p = storyboard_payload or elements_payload
            if not p:
                return {"success": False, "error": "storyboard_payload or elements_payload (renderParams) is required for 'render_with_modifications'"}
            res = await client.render_video_with_modifications(p)
            return {"success": True, "data": res}

        elif action == "update_elements":
            if not job_id:
                return {"success": False, "error": "job_id (storyboard ID) is required for 'update_elements'"}
            if not elements_payload:
                return {"success": False, "error": "elements_payload is required for 'update_elements'"}
            res = await client.update_storyboard_elements(job_id, elements_payload)
            return {"success": True, "data": res}

        elif action == "render_project":
            if not project_id:
                return {"success": False, "error": "project_id is required for 'render_project'"}
            res = await client.render_project(project_id, webhook_url=webhook_url)
            return {"success": True, "data": res}

        elif action == "poll_job":
            if not job_id:
                return {"success": False, "error": "job_id is required for 'poll_job'"}
            res = await client.get_job_status(job_id)
            return {"success": True, "data": res}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: render_storyboard, create_preview, render_from_preview, render_with_modifications, update_elements, render_project, poll_job",
            }
    except PictoryAPIError as e:
        return {"success": False, "error": e.message, "status_code": e.status_code, "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error in pictory_video: %s", e)
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool 2: pictory_transcribe
# =============================================================================

@mcp.tool()
async def pictory_transcribe(
    action: str,
    video_url: Optional[str] = None,
    language: str = "en-US",
    job_id: Optional[str] = None,
    max_duration: int = 60,
    transcript_text: Optional[str] = None,
    highlight_settings: Optional[Dict[str, Any]] = None,
    webhook_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Transcribe long-form videos/podcasts and automatically extract viral short clips (Shorts/Reels/TikToks).

    Supported Actions:
      - 'create_transcription': Submit a video/audio URL for speech-to-text transcription (POST /v2/transcription).
      - 'get_transcription_job': Fetch the status, transcript, and word timestamps of a transcription job (GET /v1/jobs/{job_id}).
      - 'generate_highlights': Automatically generate engaging 30-60s short clips from a completed transcription (POST /v2/transcription/highlights).
      - 'generate_highlights_from_transcript': Generate viral highlights using custom user-supplied transcript text (POST /v2/transcription/highlights/custom).

    Args:
        action: 'create_transcription', 'get_transcription_job', 'generate_highlights', 'generate_highlights_from_transcript'.
        video_url: Public URL of the video or audio file to transcribe or clip.
        language: Speech language code (default: 'en-US').
        job_id: Transcription job ID (required for get_transcription_job and generate_highlights).
        max_duration: Maximum duration of generated highlight clips in seconds (default: 60).
        transcript_text: Custom transcript string (for generate_highlights_from_transcript).
        highlight_settings: Optional settings dictionary for highlight extraction.
        webhook_url: Optional webhook URL for completion callback.
    """
    client = _client()
    try:
        if action == "create_transcription":
            if not video_url:
                return {"success": False, "error": "video_url is required for 'create_transcription'"}
            res = await client.create_transcription(video_url=video_url, language=language, webhook=webhook_url)
            return {"success": True, "data": res}

        elif action == "get_transcription_job":
            if not job_id:
                return {"success": False, "error": "job_id is required for 'get_transcription_job'"}
            res = await client.get_job_status(job_id)
            return {"success": True, "data": res}

        elif action == "generate_highlights":
            if not job_id:
                return {"success": False, "error": "job_id is required for 'generate_highlights'"}
            res = await client.generate_highlights_from_job(
                job_id=job_id, max_duration=max_duration, settings=highlight_settings
            )
            return {"success": True, "data": res}

        elif action == "generate_highlights_from_transcript":
            if not transcript_text:
                return {"success": False, "error": "transcript_text is required for 'generate_highlights_from_transcript'"}
            if not video_url:
                return {"success": False, "error": "video_url is required for 'generate_highlights_from_transcript'"}
            res = await client.generate_highlights_from_transcript(
                transcript_text=transcript_text, video_url=video_url, max_duration=max_duration
            )
            return {"success": True, "data": res}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: create_transcription, get_transcription_job, generate_highlights, generate_highlights_from_transcript",
            }
    except PictoryAPIError as e:
        return {"success": False, "error": e.message, "status_code": e.status_code, "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error in pictory_transcribe: %s", e)
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool 3: pictory_assets
# =============================================================================

@mcp.tool()
async def pictory_assets(
    action: str,
    query: Optional[str] = None,
    media_type: str = "video",
    category: Optional[str] = None,
    filter_type: Optional[str] = None,
    prompt: Optional[str] = None,
    ai_model: Optional[str] = None,
    aspect_ratio: str = "16:9",
    duration: Any = 5,
    style: Optional[str] = None,
    reference_image_url: Optional[str] = None,
    file_name: Optional[str] = None,
    file_type: Optional[str] = None,
    language: Optional[str] = None,
    gender: Optional[str] = None,
    service: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Search stock b-roll, background music, voices, avatars, layouts, and generate AI Studio images & videos.

    Supported Actions:
      - 'search_media': Search Getty / Storyblocks stock videos and images (GET /v1/media/search).
      - 'generate_upload_url': Generate signed AWS S3 upload URL for user files (POST /v1/media/generateurl).
      - 'search_music': Search background music tracks by query and filters (POST /v1/music/search).
      - 'get_music_filters': Get available values for a music filter ('moods', 'genres', 'groups', 'instruments', 'purposes').
      - 'list_voices': List available AI narrator voices with provider, gender, and language filters (GET /v1/voiceovers/tracks).
      - 'list_avatars': List realistic AI presenter avatars for video overlays (GET /v1/avatars).
      - 'list_smart_layouts': List pre-built responsive visual layouts (GET /v1/smartlayouts).
      - 'list_text_styles': List subtitle styling templates (GET /v1/styles).
      - 'list_brands': List saved video brand presets (GET /v1/brands/video).
      - 'list_fonts': List branding fonts (GET /v1/video/storyboard/fonts).
      - 'generate_ai_image': Generate standalone image via AI Studio (POST /v1/aistudio/images). Models: 'seedream3.0', 'flux-schnell', 'nanobanana'.
      - 'generate_ai_video': Generate standalone video via AI Studio (POST /v1/aistudio/videos). Models: 'pixverse5.5', 'veo3.1', 'veo3.1_fast'.
      - 'list_ai_assets': List past generated AI Studio images and videos.
    """
    client = _client()
    try:
        if action == "search_media":
            if not query:
                return {"success": False, "error": "query is required for 'search_media'"}
            res = await client.search_media(query=query, media_type=media_type, category=category)
            return {"success": True, "data": res}

        elif action == "generate_upload_url":
            if not file_name or not file_type:
                return {"success": False, "error": "file_name and file_type are required for 'generate_upload_url'"}
            res = await client.generate_upload_url(file_name=file_name, file_type=file_type)
            return {"success": True, "data": res}

        elif action == "search_music":
            res = await client.search_music(query=query, page=page, page_size=page_size)
            return {"success": True, "data": res}

        elif action == "get_music_filters":
            f_type = (filter_type or "moods").lower()
            if f_type == "moods":
                res = await client.get_music_moods()
            elif f_type == "genres":
                res = await client.get_music_genres()
            elif f_type in ("groups", "genre_groups"):
                res = await client.get_music_genre_groups()
            elif f_type == "instruments":
                res = await client.get_music_instruments()
            elif f_type == "purposes":
                res = await client.get_music_purposes()
            else:
                return {"success": False, "error": f"Unknown filter_type '{filter_type}'. Valid: moods, genres, groups, instruments, purposes"}
            return {"success": True, "filter_type": f_type, "data": res}

        elif action == "list_voices":
            res = await client.list_voiceovers(language=language, gender=gender, service=service)
            return {"success": True, "data": res}

        elif action == "list_avatars":
            res = await client.list_avatars()
            return {"success": True, "data": res}

        elif action == "list_smart_layouts":
            res = await client.list_smart_layouts()
            return {"success": True, "data": res}

        elif action == "list_text_styles":
            res = await client.list_text_styles()
            return {"success": True, "data": res}

        elif action == "list_brands":
            res = await client.list_video_brands()
            return {"success": True, "data": res}

        elif action == "list_fonts":
            res = await client.list_fonts()
            return {"success": True, "data": res}

        elif action == "generate_ai_image":
            if not prompt:
                return {"success": False, "error": "prompt is required for 'generate_ai_image'"}
            m = ai_model or "seedream3.0"
            res = await client.generate_ai_image(
                prompt=prompt,
                model=m,
                aspect_ratio=aspect_ratio,
                style=style,
                reference_image_url=reference_image_url,
            )
            return {"success": True, "data": res}

        elif action == "generate_ai_video":
            if not prompt:
                return {"success": False, "error": "prompt is required for 'generate_ai_video'"}
            m = ai_model or "pixverse5.5"
            res = await client.generate_ai_video(
                prompt=prompt,
                model=m,
                aspect_ratio=aspect_ratio,
                duration=duration,
                first_frame_image_url=reference_image_url,
            )
            return {"success": True, "data": res}

        elif action == "list_ai_assets":
            if media_type == "image":
                res = await client.get_generated_images(page=page, page_size=page_size)
            else:
                res = await client.get_generated_videos(page=page, page_size=page_size)
            return {"success": True, "media_type": media_type, "data": res}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: search_media, generate_upload_url, search_music, get_music_filters, list_voices, list_avatars, list_smart_layouts, list_text_styles, list_brands, list_fonts, generate_ai_image, generate_ai_video, list_ai_assets",
            }
    except PictoryAPIError as e:
        return {"success": False, "error": e.message, "status_code": e.status_code, "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error in pictory_assets: %s", e)
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool 4: pictory_projects
# =============================================================================

@mcp.tool()
async def pictory_projects(
    action: str,
    project_id: Optional[str] = None,
    template_id: Optional[str] = None,
    file_path: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    scene_number: Optional[int] = None,
    media_url: Optional[str] = None,
    thumbnail_url: Optional[str] = None,
    duration: Optional[float] = None,
    text: Optional[str] = None,
    asset_id: Optional[str] = None,
    library: str = "getty",
    description: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Manage Pictory projects and master video templates (full web UI synchronization).

    Supported Actions:
      - 'list_projects': List all saved projects in your Pictory web dashboard (GET /v2/projects).
      - 'get_project': Get complete scene data for a specific project ID (GET /v2/projects/{project_id}).
      - 'update_project': Update an existing project's scenes, text, or settings (PUT /v2/projects/{project_id}).
      - 'update_scene': Surgically update a single scene's footage, thumbnail, duration, or text with auto-concurrency retry and schema protection.
      - 'delete_project': Delete a project from your account (DELETE /v2/projects/{project_id}).
      - 'list_templates': List saved master video templates (GET /v1/templates).
      - 'get_template': Get template configuration by ID (GET /v1/templates/{template_id}).
      - 'create_template': Create a new reusable brand video template (POST /v1/templates).
      - 'update_template': Update an existing video template (PUT /v1/templates/{template_id}).
      - 'delete_template': Delete a video template (DELETE /v1/templates/{template_id}).
    """
    client = _client()
    try:
        if action == "list_projects":
            res = await client.list_projects(page=page, page_size=page_size)
            return {"success": True, "data": res}

        elif action == "get_project":
            if not project_id:
                return {"success": False, "error": "project_id is required for 'get_project'"}
            res = await client.get_project(project_id)
            return {"success": True, "data": res}

        elif action == "update_project":
            if not project_id:
                return {"success": False, "error": "project_id is required for 'update_project'"}
            if not payload:
                return {"success": False, "error": "payload is required for 'update_project'"}
            res = await client.update_project(project_id, payload)
            return {"success": True, "data": res}

        elif action == "update_scene":
            if not project_id:
                return {"success": False, "error": "project_id is required for 'update_scene'"}
            p = payload or {}
            s_num = scene_number if scene_number is not None else p.get("scene_number")
            if s_num is None:
                return {"success": False, "error": "scene_number is required for 'update_scene' (1-indexed integer, at top-level or inside payload)"}
            res = await client.update_scene(
                project_id=project_id,
                scene_number=int(s_num),
                media_url=media_url or p.get("media_url"),
                thumbnail_url=thumbnail_url or p.get("thumbnail_url"),
                duration=duration if duration is not None else p.get("duration"),
                text=text or p.get("text"),
                asset_id=str(asset_id) if asset_id else (str(p.get("asset_id")) if p.get("asset_id") else None),
                library=p.get("library", library or "getty"),
                description=description or p.get("description"),
            )
            return {"success": True, "data": res}

        elif action == "delete_project":
            if not project_id:
                return {"success": False, "error": "project_id is required for 'delete_project'"}
            res = await client.delete_project(project_id)
            return {"success": True, "data": res}

        elif action == "list_templates":
            res = await client.list_templates(page=page, page_size=page_size)
            return {"success": True, "data": res}

        elif action == "get_template":
            if not template_id:
                return {"success": False, "error": "template_id is required for 'get_template'"}
            res = await client.get_template(template_id)
            return {"success": True, "data": res}

        elif action == "create_template":
            target = file_path or payload
            if not target:
                return {"success": False, "error": "file_path (to .pictai file) or payload is required for 'create_template'"}
            res = await client.create_template(target)
            return {"success": True, "data": res}

        elif action == "update_template":
            if not template_id:
                return {"success": False, "error": "template_id is required for 'update_template'"}
            if not payload:
                return {"success": False, "error": "payload is required for 'update_template'"}
            res = await client.update_template(template_id, payload)
            return {"success": True, "data": res}

        elif action == "delete_template":
            if not template_id:
                return {"success": False, "error": "template_id is required for 'delete_template'"}
            res = await client.delete_template(template_id)
            return {"success": True, "data": res}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: list_projects, get_project, update_project, update_scene, delete_project, list_templates, get_template, create_template, update_template, delete_template",
            }
    except PictoryAPIError as e:
        return {"success": False, "error": e.message, "status_code": e.status_code, "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error in pictory_projects: %s", e)
        return {"success": False, "error": str(e)}


# =============================================================================
# Tool 5: pictory_integrations
# =============================================================================

@mcp.tool()
async def pictory_integrations(
    action: str,
    connection_id: Optional[str] = None,
    job_id: Optional[str] = None,
    connection_payload: Optional[Dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Manage third-party cloud integrations (Vimeo & AWS S3), account quotas, AI credits, and job cleanup.

    Supported Actions:
      - 'get_quota': Check current API video render quota and usage limits (GET /v1/quota).
      - 'get_credit_usage': Check remaining AI generation credits and breakdown (GET /v1/aicredits/usage).
      - 'list_jobs': List recent and running render jobs across your account (GET /v1/jobs).
      - 'clean_job': Cancel or delete a stuck/failed job (DELETE /v1/jobs/{job_id}/clean).
      - 'list_vimeo_connections': List connected Vimeo accounts for direct video publishing (GET /v1/vimeo-connections).
      - 'get_vimeo_connection': Get details for a Vimeo connection (GET /v1/vimeo-connections/{id}).
      - 'create_vimeo_connection': Authorize a new Vimeo connection (POST /v1/vimeo-connections).
      - 'update_vimeo_connection': Update an existing Vimeo connection (PUT /v1/vimeo-connections/{id}).
      - 'delete_vimeo_connection': Disconnect a Vimeo account (DELETE /v1/vimeo-connections/{id}).
      - 'list_aws_connections': List private AWS S3 bucket connections (GET /v1/awsconnections).
      - 'get_aws_connection': Get details for an AWS private S3 connection (GET /v1/awsconnections/{id}).
      - 'create_aws_connection': Connect a private AWS S3 bucket using IAM keys (POST /v1/awsconnections).
      - 'update_aws_connection': Update an AWS private S3 connection (PUT /v1/awsconnections/{id}).
      - 'delete_aws_connection': Remove an AWS connection (DELETE /v1/awsconnections/{id}).
    """
    client = _client()
    try:
        if action == "get_quota":
            res = await client.get_quota()
            return {"success": True, "data": res}

        elif action == "get_credit_usage":
            res = await client.get_aicredits_usage()
            return {"success": True, "data": res}

        elif action == "list_jobs":
            res = await client.list_jobs(page=page, page_size=page_size)
            return {"success": True, "data": res}

        elif action == "clean_job":
            if not job_id:
                return {"success": False, "error": "job_id is required for 'clean_job'"}
            res = await client.clean_job(job_id)
            return {"success": True, "data": res}

        elif action == "list_vimeo_connections":
            res = await client.list_vimeo_connections()
            return {"success": True, "data": res}

        elif action == "get_vimeo_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'get_vimeo_connection'"}
            res = await client.get_vimeo_connection(connection_id)
            return {"success": True, "data": res}

        elif action == "create_vimeo_connection":
            if not connection_payload:
                return {"success": False, "error": "connection_payload is required for 'create_vimeo_connection'"}
            res = await client.create_vimeo_connection(connection_payload)
            return {"success": True, "data": res}

        elif action == "update_vimeo_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'update_vimeo_connection'"}
            if not connection_payload:
                return {"success": False, "error": "connection_payload is required for 'update_vimeo_connection'"}
            res = await client.update_vimeo_connection(connection_id, connection_payload)
            return {"success": True, "data": res}

        elif action == "delete_vimeo_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'delete_vimeo_connection'"}
            res = await client.delete_vimeo_connection(connection_id)
            return {"success": True, "data": res}

        elif action == "list_aws_connections":
            res = await client.list_aws_connections()
            return {"success": True, "data": res}

        elif action == "get_aws_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'get_aws_connection'"}
            res = await client.get_aws_connection(connection_id)
            return {"success": True, "data": res}

        elif action == "create_aws_connection":
            if not connection_payload:
                return {"success": False, "error": "connection_payload is required for 'create_aws_connection'"}
            res = await client.create_aws_connection(connection_payload)
            return {"success": True, "data": res}

        elif action == "update_aws_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'update_aws_connection'"}
            if not connection_payload:
                return {"success": False, "error": "connection_payload is required for 'update_aws_connection'"}
            res = await client.update_aws_connection(connection_id, connection_payload)
            return {"success": True, "data": res}

        elif action == "delete_aws_connection":
            if not connection_id:
                return {"success": False, "error": "connection_id is required for 'delete_aws_connection'"}
            res = await client.delete_aws_connection(connection_id)
            return {"success": True, "data": res}

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}'. Valid actions: get_quota, get_credit_usage, list_jobs, clean_job, list_vimeo_connections, get_vimeo_connection, create_vimeo_connection, update_vimeo_connection, delete_vimeo_connection, list_aws_connections, get_aws_connection, create_aws_connection, update_aws_connection, delete_aws_connection",
            }
    except PictoryAPIError as e:
        return {"success": False, "error": e.message, "status_code": e.status_code, "details": e.details}
    except Exception as e:
        logger.exception("Unexpected error in pictory_integrations: %s", e)
        return {"success": False, "error": str(e)}


def main():
    """Main entrypoint for running the Pictory FastMCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
