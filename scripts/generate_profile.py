"""Render dark and light GitHub profile cards from pixel art and live stats."""

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ART_PATH = ROOT / "pixel_art.json"
STATS_PATH = ROOT / "stats.json"
WIDTH = 1200
HEIGHT = 560
FONT = "ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,monospace"

THEMES = {
    "dark": {
        "background": "#0d1117",
        "border": "#30363d",
        "title": "#58a6ff",
        "label": "#f0883e",
        "value": "#c9d1d9",
        "muted": "#8b949e",
        "line": "#30363d",
        "accent": "#f85149",
    },
    "light": {
        "background": "#ffffff",
        "border": "#d0d7de",
        "title": "#0969da",
        "label": "#bc4c00",
        "value": "#24292f",
        "muted": "#57606a",
        "line": "#d8dee4",
        "accent": "#cf222e",
    },
}


def account_age(created_at: str) -> str:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    years = now.year - created.year
    months = now.month - created.month
    if now.day < created.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return f"{years}y {months}m"


def trim(value: object, limit: int = 42) -> str:
    text = str(value or "-")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def svg_text(x: int, y: int, text: str, color: str, *, weight: int = 400, size: int = 15) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="{weight}">{escape(text)}</text>'
    )


def pixel_paths(art: dict, theme: str) -> list[str]:
    paths: dict[int, list[str]] = {index: [] for index in range(len(art["palette"]))}
    for y, runs in enumerate(art["rows"]):
        for x, width, color_index in runs:
            paths[color_index].append(f"M{x} {y}h{width}v1h-{width}z")

    output = [
        '<g transform="translate(18 50) scale(4.7)" shape-rendering="crispEdges">'
    ]
    for color_index, commands in paths.items():
        if not commands:
            continue
        color = art["palette"][color_index]
        if theme == "light":
            red, green, blue = (int(color[i : i + 2], 16) for i in (1, 3, 5))
            if red + green + blue > 690:
                color = "#{:02x}{:02x}{:02x}".format(
                    int(red * 0.88), int(green * 0.88), int(blue * 0.88)
                )
        output.append(f'<path fill="{color}" d="{"".join(commands)}"/>')
    output.append("</g>")
    return output


def render(theme_name: str, art: dict, stats: dict) -> str:
    theme = THEMES[theme_name]
    login = stats["login"]
    top_languages = ", ".join(stats.get("top_languages", [])) or "No public language data"
    repo_scope = f'{stats["repos_total"]} total / {stats["repos_public"]} public'
    follower_scope = f'{stats["followers"]} followers / {stats["following"]} following'
    activity = f'{stats["contributions_365d"]:,} contributions / 365d'
    sync_time = datetime.fromisoformat(stats["generated_at"]).astimezone(timezone.utc)
    sync_label = sync_time.strftime("%Y-%m-%d %H:%M UTC")

    rows = [
        ("ACCOUNT", ""),
        ("Joined", account_age(stats["created_at"])),
        ("Repository", trim(stats.get("active_repository"), 32)),
        ("Languages", trim(top_languages, 38)),
        ("", ""),
        ("GITHUB STATS", ""),
        ("Repositories", repo_scope),
        ("Stars received", f'{stats["stars_received"]:,}'),
        ("Network", follower_scope),
        ("Activity", activity),
        ("Commits", f'{stats["commits_365d"]:,} / 365d'),
        ("Pull requests", f'{stats["pull_requests_365d"]:,} / 365d'),
        ("", ""),
        ("Last sync", sync_label),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title description">',
        f'<title id="title">{escape(login)} GitHub profile</title>',
        '<desc id="description">Vector pixel-art snow leopard with automatically updated GitHub statistics.</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" '
        f'fill="{theme["background"]}" stroke="{theme["border"]}"/>',
    ]
    parts.extend(pixel_paths(art, theme_name))

    panel_x = 520
    parts.append(svg_text(panel_x, 66, f"{login}@github", theme["title"], weight=700, size=18))
    parts.append(f'<line x1="{panel_x}" y1="82" x2="1150" y2="82" stroke="{theme["line"]}"/>')
    y = 118
    for label, value in rows:
        if not label:
            y += 14
            continue
        if not value:
            parts.append(svg_text(panel_x, y, label, theme["title"], weight=700, size=13))
            parts.append(f'<line x1="{panel_x + 118}" y1="{y - 5}" x2="1150" y2="{y - 5}" stroke="{theme["line"]}"/>')
        else:
            parts.append(svg_text(panel_x, y, f". {label}", theme["label"], weight=600, size=14))
            parts.append(svg_text(690, y, "·" * 20, theme["line"], size=14))
            parts.append(svg_text(865, y, value, theme["value"], size=14))
        y += 28

    parts.append(svg_text(36, 536, "SNOW LEOPARD // BUILDING IN PUBLIC", theme["muted"], weight=600, size=12))
    parts.append(svg_text(1138, 536, "●", theme["accent"], size=13))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    art = json.loads(ART_PATH.read_text())
    stats = json.loads(STATS_PATH.read_text())
    for theme in THEMES:
        output = ROOT / f"profile-{theme}.svg"
        output.write_text(render(theme, art, stats))
        print(f"saved {output}")


if __name__ == "__main__":
    main()
