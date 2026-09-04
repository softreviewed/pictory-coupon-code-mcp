# 🎬 Pictory AI MCP Server (`pictory-mcp`)

[![MCP Protocol](https://img.shields.io/badge/MCP-Standard%202.0-blue.svg)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.x-green.svg)](https://github.com/jlowin/fastmcp)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

A universal, production-grade **Model Context Protocol (MCP)** server for [Pictory.ai](https://pictory.ai). Connects AI assistants (**Claude Desktop, Cursor IDE, Windsurf, Antigravity, CrewAI, LangChain**) directly to the complete Pictory video generation studio.

Transform scripts or articles into rendered videos, repurpose long-form podcasts into viral short clips (Reels/Shorts/TikToks), overlay realistic AI presenter avatars, search millions of stock B-roll assets, synchronize templates with your Pictory web dashboard, and publish directly to Vimeo and Amazon S3.

---

## ⚡ What This MCP Does (At a Glance)

```
                       ┌─────────────────────────┐
                       │ Any AI Assistant / Agent│
                       │(Claude, Cursor, Antigrav)│
                       └────────────┬────────────┘
                                    │ (JSON-RPC stdio)
                       ┌────────────▼────────────┐
                       │       pictory-mcp       │
                       │ FastMCP Universal Server│
                       └────────────┬────────────┘
                                    │
   ┌───────────────┬────────────────┼───────────────┬────────────────┐
   ▼               ▼                ▼               ▼                ▼
pictory_video  pictory_transcribe pictory_assets pictory_projects pictory_integrations
- Script/Render - Long Video Trans - Stock Search  - Web Sync CRUD  - Vimeo Publish
- Storyboard    - Viral AI Shorts  - Music & Mood  - Master Brand   - AWS S3 Storage
- Avatar Overlay- Timed Subtitles  - 300+ Voices     Templates      - Quotas & Usage
- Scene Patching- Highlight Clips  - AI Studio Gen - Scene Patches  - Job Cleanup
```

---

## 🚀 Quickstart (1-Minute Setup)

### 1. Get Your Pictory API Key
1. Log in to [Pictory.ai](https://app.pictory.ai).
2. Go to **Settings** → **API Access** (or visit [https://app.pictory.ai/api-access](https://app.pictory.ai/api-access)).
3. Copy your API key (`pictai_...`).

---

### 2. Connect to Your AI Client

#### 🟣 Option A: Claude Desktop
Add to your `claude_desktop_config.json`:
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

#### 🔵 Option B: Cursor IDE
1. Open **Settings** → **Features** → **MCP Servers**.
2. Click **+ Add New MCP Server**.
3. Name: `pictory`
4. Type: `command`
5. Command: `uvx pictory-mcp`
6. Environment variable: `PICTORY_API_KEY=pictai_your_api_key_here`

#### 🟢 Option C: Docker MCP Gateway
Add to `custom.yaml` or run directly:
```bash
docker mcp server enable pictory
```

---

## 🛠️ Master Tool Reference (5 Consolidated Tools)

| Tool | Category | Key Supported Actions |
| :--- | :--- | :--- |
| `pictory_video` | Video Rendering & Editing | `render_storyboard`, `create_preview`, `render_from_preview`, `render_with_modifications`, `update_elements`, `render_project`, `poll_job` |
| `pictory_transcribe` | Transcription & Viral Clips | `transcribe_video`, `poll_transcription`, `automatic_highlights`, `custom_highlights`, `get_subtitles` |
| `pictory_assets` | Stock & AI Asset Engine | `search_media`, `search_music`, `list_music_genres`, `list_music_moods`, `list_avatars`, `list_voiceovers`, `list_styles`, `list_fonts`, `generate_ai_image`, `generate_ai_video`, `get_signed_url` |
| `pictory_projects` | Project & Template Sync | `list_projects`, `get_project`, `update_project`, `delete_project`, `list_templates`, `get_template`, `create_template`, `update_template`, `delete_template`, `update_scene` |
| `pictory_integrations`| Cloud & Account Ops | `get_quota`, `get_aicredits_usage`, `list_vimeo_connections`, `create_vimeo_connection`, `list_aws_connections`, `create_aws_connection`, `clean_job` |

---

## 💡 Example: URL-to-Video with Talking-Head Avatar

Give Pictory a public URL and an avatar configuration — it will automatically scrape the content, generate scenes, match stock B-roll, and overlay a synchronized talking-head presenter:

```json
{
  "videoName": "Article_Showcase",
  "aspectRatio": "16:9",
  "avatar": {
    "avatarId": "Brandon_expressive2_public",
    "position": "bottom-right",
    "width": "25%",
    "borderRadius": "100"
  },
  "voiceOver": {
    "enabled": true,
    "aiVoices": [{"speaker": "Martin", "speed": 100, "volume": 100}]
  },
  "backgroundMusic": {
    "enabled": true,
    "autoMusic": true,
    "volume": 0.12
  },
  "scenes": [
    {
      "blogUrl": "https://softreviewed.com/openai-gpt6-astra-benchmarks/"
    }
  ]
}
```

---

## 🧪 Testing & Verification

Run the test suite locally:
```bash
pytest tests/
```
All 17 unit tests validate payload serialization, error handling, route matching, and header authentication.

---

## 📄 License
MIT License. Free for personal, commercial, and enterprise integration.
