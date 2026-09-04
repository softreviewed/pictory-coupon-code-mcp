# 🎬 Pictory AI MCP Server (`pictory-mcp`)

[![MCP Protocol](https://img.shields.io/badge/MCP-Standard%202.0-blue.svg)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

A universal, community-grade **Model Context Protocol (MCP)** server for [Pictory.ai](https://pictory.ai). Connects AI assistants (**Claude Desktop, Cursor IDE, Windsurf, Antigravity, CrewAI, LangChain**) directly to the full Pictory video generation studio.

Transform scripts into rendered videos, repurpose long-form podcasts into viral short clips (Reels/Shorts/TikToks), search millions of stock b-roll assets, synchronize templates with your Pictory web dashboard, and publish directly to Vimeo and Amazon S3.

---

## 🌟 What This MCP Does (At a Glance)

```
                         ┌─────────────────────────────┐
                         │   Any AI Assistant / Agent  │
                         │  (Claude, Cursor, Windsurf) │
                         └──────────────┬──────────────┘
                                        │
                                        ▼ (JSON-RPC stdio)
                    ┌───────────────────────────────────────┐
                    │              pictory-mcp              │
                    │        FastMCP Universal Server       │
                    └───────────────────┬───────────────────┘
                                        │
     ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
     ▼                  ▼               ▼               ▼                  ▼
🎥 pictory_video  🎙️ pictory_    🖼️ pictory_    📁 pictory_       ☁️ pictory_
                  transcribe      assets          projects          integrations
- Script → Render - Long Video    - Stock Search  - Web Sync CRUD   - Vimeo Publish
- Storyboard Prev   → Transcript  - Music & Mood  - Master Brand    - AWS S3 Storage
- Scene Patching  - Viral AI      - 100+ AI Voices  Templates       - Quotas & Usage
- MP4 Polling       Short Clips   - AI Studio Gen - Scene Patches   - Job Cancelling
```

---

## ⚡ Quickstart (1-Minute Setup)

### 1. Get Your Pictory API Key
1. Log in to [Pictory.ai](https://app.pictory.ai).
2. Go to **Settings** ➔ **API Access** (or visit [https://app.pictory.ai/api-access](https://app.pictory.ai/api-access)).
3. Copy your API key (it starts with `pictai_`).

---

### 2. Connect to Your AI Client

#### 🤖 Option A: Claude Desktop
Add this to your `claude_desktop_config.json`:
* **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
* **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pictory": {
      "command": "uvx",
      "args": ["pictory-mcp"],
      "env": {
        "PICTORY_API_KEY": "pictai_your_api_key_here"
      }
    }
  }
}
```

#### 💻 Option B: Cursor IDE
In Cursor:
1. Open **Settings** ➔ **Features** ➔ **MCP Servers**.
2. Click **+ Add New MCP Server**.
3. Name: `pictory`
4. Type: `command`
5. Command: `uvx pictory-mcp`
6. Environment variable: `PICTORY_API_KEY=pictai_your_api_key_here`

#### 🏄 Option C: Windsurf IDE
Add to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "pictory": {
      "command": "uvx",
      "args": ["pictory-mcp"],
      "env": {
        "PICTORY_API_KEY": "pictai_your_api_key_here"
      }
    }
  }
}
```

#### 🐳 Option D: Docker MCP Gateway (`custom.yaml`)
```yaml
pictory-mcp:
  image: pictory-mcp:latest
  command:
    - python
    - -u
    - server.py
  env:
    - name: PICTORY_API_KEY
      value: "pictai_your_api_key_here"
  tools:
    - pictory_video
    - pictory_transcribe
    - pictory_assets
    - pictory_projects
    - pictory_integrations
```

#### 📦 Option E: Smithery CLI (1-Click)
```bash
npx -y @smithery/cli install pictory-mcp --client claude
```

---

## 🛠️ Complete MCP Tool Reference

The server consolidates all 45+ official Pictory endpoints into **5 intuitive, high-leverage tools**:

### 1. `pictory_video`
The core video engine. Create, preview, render, patch, and poll MP4 videos.

| Action | API Endpoint | Description |
| :--- | :--- | :--- |
| `render_storyboard` | `POST /v2/video/storyboard/render` | Render a video directly from script scenes. |
| `create_preview` | `POST /v2/video/storyboard` | Generate a preview to inspect scenes before spending credits. |
| `render_from_preview` | `PUT /v2/video/render/{job_id}` | Render the final MP4 from an approved preview. |
| `update_elements` | `PUT /v2/video/storyboard/{id}/elements` | Surgically patch single scene texts or visuals. |
| `render_project` | `POST /v2/projects/{id}/render` | Render directly from a saved project ID. |
| `poll_job` | `GET /v1/jobs/{job_id}` | Poll render progress percentage & download URL. |

---

### 2. `pictory_transcribe`
Video repurposing engine. Turn long videos/podcasts into viral short clips with auto-subtitles.

| Action | API Endpoint | Description |
| :--- | :--- | :--- |
| `create_transcription` | `POST /v2/transcription` | Transcribe speech with exact word timestamps. |
| `get_transcription_job` | `GET /v1/jobs/{job_id}` | Retrieve transcription status and text. |
| `generate_highlights` | `POST /v2/transcription/highlights` | Auto-extract 30–60s viral highlights from a job. |
| `generate_highlights_from_transcript` | `POST /v2/transcription/highlights/custom` | Extract clips using custom text script. |

---

### 3. `pictory_assets`
Stock b-roll, background music, voiceovers, avatars, and AI Studio generation.

| Action | API Endpoint | Description |
| :--- | :--- | :--- |
| `search_media` | `GET /v1/media/search` | Search Getty & Storyblocks stock b-roll and photos. |
| `generate_upload_url` | `POST /v1/media/generateurl` | Generate signed AWS S3 upload URL for user files. |
| `search_music` | `POST /v1/music/search` | Search music by query, mood, genre, and duration. |
| `get_music_filters` | `GET /v1/music/{filter}` | Discover moods, genres, groups, instruments, purposes. |
| `list_voices` | `GET /v1/voiceovers/tracks` | Browse 100+ AI voices (ElevenLabs, AWS, Google). |
| `list_avatars` | `GET /v1/avatars` | List realistic AI presenter avatars for video overlays. |
| `list_smart_layouts` | `GET /v1/smartlayouts` | Browse pre-built responsive layouts. |
| `list_text_styles` | `GET /v1/styles` | Browse subtitle styling presets. |
| `generate_ai_image` | `POST /v1/aistudio/images` | Generate AI images (Flux, Seedream, Nanobanana). |
| `generate_ai_video` | `POST /v1/aistudio/videos` | Generate AI videos (Veo 3.1, PixVerse 5.5). |
| `list_ai_assets` | `GET /v1/aistudio/...` | List previously generated AI images/videos. |

---

### 4. `pictory_projects`
Pictory web dashboard synchronization and reusable master video templates.

| Action | API Endpoint | Description |
| :--- | :--- | :--- |
| `list_projects` | `GET /v2/projects` | List all saved projects in your web account. |
| `get_project` | `GET /v2/projects/{id}` | Inspect full scene definitions of a project. |
| `update_project` | `PUT /v2/projects/{id}` | Update scenes, titles, and assets in a draft. |
| `delete_project` | `DELETE /v2/projects/{id}` | Delete a project from your account. |
| `list_templates` | `GET /v1/templates` | List saved brand video templates. |
| `create_template` | `POST /v1/templates` | Save a new reusable brand layout template. |
| `update_template` | `PUT /v1/templates/{id}` | Edit an existing master template. |
| `delete_template` | `DELETE /v1/templates/{id}` | Remove a template. |

---

### 5. `pictory_integrations`
Cloud publishing, AWS private storage, quotas, and job queue management.

| Action | API Endpoint | Description |
| :--- | :--- | :--- |
| `get_quota` | `GET /v1/quota` | Check remaining monthly render quota. |
| `get_credit_usage` | `GET /v1/aicredits/usage` | Check remaining AI image/video credits. |
| `list_jobs` | `GET /v1/jobs` | View active and recent jobs across the account. |
| `clean_job` | `DELETE /v1/jobs/{job_id}` | Cancel or delete a hung/failed render job. |
| `list_vimeo_connections` | `GET /v1/vimeo` | Manage authorized Vimeo publishing channels. |
| `create_vimeo_connection` | `POST /v1/vimeo` | Authorize a new Vimeo connection. |
| `list_aws_connections` | `GET /v1/aws` | View private AWS S3 bucket connections. |
| `create_aws_connection` | `POST /v1/aws` | Connect private AWS S3 assets with IAM keys. |

---

## 💬 Real-World Prompt Examples

Once installed, simply prompt your AI assistant naturally:

* 🎬 **Explainer Video:**  
  *"Render a 60-second 16:9 explainer video explaining quantum computing. Use upbeat background music, modern subtitles, and Brian's British voiceover."*

* 🎙️ **Podcast Repurposing:**  
  *"Transcribe this 30-minute webinar at https://example.com/recording.mp4 and generate 3 viral 9:16 vertical shorts with animated captions."*

* 🎵 **Asset Discovery:**  
  *"Search for upbeat cinematic background music under 90 seconds and find a female voiceover with an Australian accent."*

* ☁️ **Direct Publishing:**  
  *"Check my current Pictory quota and export my latest completed video straight to my connected Vimeo account."*

---

## 🔒 Security & Best Practices

* **Never commit API keys:** Always pass your key via the `PICTORY_API_KEY` environment variable.
* **No `Bearer` prefix:** Pictory accepts the raw API key directly. This server handles formatting automatically.
* **Non-destructive validation:** All payloads are pre-validated before hitting the API to save credits and prevent errors.

---

## 🧪 Development & Testing

```bash
# Clone repository
git clone https://github.com/jovin/pictory-mcp.git
cd pictory-mcp

# Install dependencies
pip install -r requirements.txt

# Run test suite
python tests/test_server.py

# Launch local interactive dev inspector
fastmcp dev server.py
```

---

## 📄 License
MIT License © 2026 Jovin. Free to use, modify, and distribute for personal and commercial applications.
