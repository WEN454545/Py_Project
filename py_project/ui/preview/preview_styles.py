"""Preview stylesheet generator with theme support (light/dark)."""

from __future__ import annotations


def get_theme(name: str = "dark") -> dict:
    """Return a color palette for the given theme name."""
    themes = {
        "dark": {
            "bg": "#1e1e2e",
            "surface": "#181825",
            "text": "#cdd6f4",
            "subtext": "#a6adc8",
            "accent": "#89b4fa",
            "border": "#313244",
            "code_bg": "#11111b",
            "code_text": "#fab387",
            "link": "#89b4fa",
            "wikilink": "#cba6f7",
            "blockref": "#f9e2af",
            "math": "#74c7ec",
            "heading": "#ffffff",
            "blockquote_bg": "#181825",
        },
        "light": {
            "bg": "#fafafa",
            "surface": "#f0f0f0",
            "text": "#333333",
            "subtext": "#666666",
            "accent": "#2962ff",
            "border": "#e0e0e0",
            "code_bg": "#f5f5f5",
            "code_text": "#c62828",
            "link": "#2962ff",
            "wikilink": "#6a1b9a",
            "blockref": "#f57f17",
            "math": "#00695c",
            "heading": "#111111",
            "blockquote_bg": "#f5f5f5",
        },
    }
    return themes.get(name, themes["dark"])


def generate_css(theme_name: str = "dark") -> str:
    """Generate the full preview CSS for a given theme."""
    t = get_theme(theme_name)
    return f"""
    :root {{
        --bg: {t["bg"]};
        --surface: {t["surface"]};
        --text: {t["text"]};
        --subtext: {t["subtext"]};
        --accent: {t["accent"]};
        --border: {t["border"]};
        --code-bg: {t["code_bg"]};
        --code-text: {t["code_text"]};
        --link: {t["link"]};
        --wikilink: {t["wikilink"]};
        --blockref: {t["blockref"]};
        --math: {t["math"]};
        --heading: {t["heading"]};
        --bq-bg: {t["blockquote_bg"]};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        background-color: var(--bg);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 15px;
        line-height: 1.7;
        padding: 24px 32px;
        max-width: 800px;
        margin: 0 auto;
    }}
    h1 {{ font-size: 1.8em; margin: 0.8em 0 0.4em; color: var(--heading);
          border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.5em; margin: 0.7em 0 0.3em; color: var(--heading); }}
    h3 {{ font-size: 1.25em; margin: 0.6em 0 0.2em; color: var(--heading); }}
    h4, h5, h6 {{ font-size: 1.1em; margin: 0.5em 0 0.15em; color: var(--subtext); }}
    p {{ margin: 0.5em 0; }}
    strong {{ color: var(--heading); }}
    em {{ color: var(--subtext); }}
    code {{
        background-color: var(--code-bg); color: var(--code-text);
        padding: 2px 6px; border-radius: 4px;
        font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
        font-size: 0.9em;
    }}
    pre {{
        background-color: var(--code-bg); border: 1px solid var(--border);
        border-radius: 8px; padding: 16px; overflow-x: auto; margin: 1em 0;
    }}
    pre code {{ background: none; padding: 0; color: var(--text); }}
    blockquote {{
        border-left: 3px solid var(--accent); padding: 0.5em 1em;
        margin: 1em 0; background-color: var(--bq-bg);
        border-radius: 0 8px 8px 0; color: var(--subtext);
    }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
    th, td {{ border: 1px solid var(--border); padding: 8px 12px; text-align: left; }}
    th {{ background-color: var(--surface); font-weight: 600; }}
    ul, ol {{ padding-left: 2em; margin: 0.5em 0; }}
    li {{ margin: 0.15em 0; }}
    hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }}
    a {{ color: var(--link); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    a.wikilink {{ color: var(--wikilink); font-weight: 500; }}
    a.blockref {{ color: var(--blockref); font-family: monospace; font-size: 0.85em; }}
    .math-block, .math-inline {{ color: var(--math); }}
    img {{ max-width: 100%; border-radius: 8px; margin: 0.5em 0; }}
    """
