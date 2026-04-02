# 🌐 Web MCP

The ultimate web-access MCP server. Combines extended Playwright browser automation with stealth capabilities, free web search, and dual-mode HTML-to-Markdown conversion.

## Features

- **Browser automation** with three engines: vanilla [Playwright](https://playwright.dev/), 
[Camoufox](https://camoufox.com/) (Firefox stealth), and [CloakBrowser](https://cloakbrowser.dev/) (Chromium stealth)
- **Free web search** via [DDGS](https://github.com/deedy5/ddgs) (multi-backend: Bing, Brave, DuckDuckGo, Google, Yahoo, Wikipedia)
- **HTML-to-Markdown** in two modes: as-is structural conversion 
([markdownify](https://github.com/matthewwithanm/python-markdownify)) and article extraction ([Trafilatura](https://trafilatura.readthedocs.io/))

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Setup

```bash
uv sync
uv run playwright install
```

## Usage

### Run MCP server over stdio

```bash
uv run python -m web_mcp
```

### Run MCP server over HTTP 

1. Start Web MCP in HTTP mode:

```bash
uv run python -m web_mcp --http
```

By default, MCP server will run at:
```text
http://127.0.0.1:9000/mcp
```

- `--host` — bind address; default `127.0.0.1`, or set `WEB_MCP_HOST`.
- `--port` — bind port; default `9000`, or set `WEB_MCP_PORT`.
- `--path` — MCP URL path; default `/mcp`, or set `WEB_MCP_PATH`.

### Add to MCP configuration (stdio-based)

```json
{
  "mcpServers": {
    "web-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/web-mcp", "python", "-m", "web_mcp"]
    }
  }
}
```

## Tools

### Browser Tools

| Tool | Description |
|------|-------------|
| `browser_configure` | Set engine (playwright/camoufox/cloakbrowser), stealth options, proxy, viewport |
| `browser_navigate` | Navigate to URL |
| `browser_navigate_back` | Go back in history |
| `browser_snapshot` | Get accessibility tree with numbered element refs |
| `browser_take_screenshot` | Capture page or element screenshot |
| `browser_click` | Click an element by ref |
| `browser_type` | Type text into an element |
| `browser_fill_form` | Fill multiple form fields at once |
| `browser_select_option` | Select dropdown option(s) |
| `browser_hover` | Hover over an element |
| `browser_drag` | Drag and drop between elements |
| `browser_press_key` | Press a keyboard key |
| `browser_evaluate` | Execute JavaScript on the page |
| `browser_wait_for` | Wait for time, text, or selector |
| `browser_tabs` | List, create, close, or switch tabs |
| `browser_resize` | Resize viewport |
| `browser_file_upload` | Upload file(s) to a file input |
| `browser_handle_dialog` | Handle alert/confirm/prompt dialogs |
| `browser_console_messages` | Get console output |
| `browser_network_requests` | Get network request log |
| `browser_get_html` | Get page HTML source |
| `browser_close` | Close the browser |

### Search Tools

| Tool | Description |
|------|-------------|
| `web_search` | Text search with configurable backend |
| `news_search` | News search |
| `image_search` | Image search |

### Content Tools

| Tool | Description |
|------|-------------|
| `html_to_markdown` | Convert HTML to Markdown as-is (full structure) |
| `extract_article` | Extract article from HTML via Trafilatura |
| `fetch_page` | HTTP-fetch a URL, return raw HTML |
| `fetch_as_markdown` | HTTP-fetch + convert to Markdown |
| `fetch_article` | HTTP-fetch + extract article |
