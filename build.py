"""
超軽量Markdown→HTMLビルドスクリプト。
外部ライブラリ不要(python標準ライブラリのみ)。
content/published/*.md と legal/*.md をHTMLに変換して site/ 以下に出力する。

想定しているMarkdown記法(このプロジェクトのプロンプトが生成する範囲のみ対応):
- frontmatter (--- key: value ---)
- # ## ### 見出し
- **太字**
- テーブル(| a | b |)
- 箇条書き(- item)
- > 引用(開示文言用)
- 通常の段落
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

TEMPLATE = """<meta charset="UTF-8">
<title>{title} | ASM Lab</title>
<link rel="stylesheet" href="{css_path}styles.css">
<header>
  <div class="inner">
    <a class="brand" href="{css_path}index.html">ASM Lab</a>
    <div class="tagline">Daily Goods, Compared.</div>
  </div>
</header>
<main>
{body}
</main>
<footer>
  <div>
    <a href="{css_path}privacy.html">プライバシーポリシー</a>
  </div>
  <div>&copy; ASM</div>
</footer>
"""


def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            block = text[3:end].strip()
            for line in block.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            text = text[end + 3:]
    return meta, text.strip()


def inline(text):
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Only treat [x](y) as a real link when y looks like a URL/path/anchor.
    # Content uses bare [商品A]-style bracket placeholders that are often
    # immediately followed by an unrelated "(...)" aside in the same sentence
    # (e.g. "[商品A]か[商品E](計量不要)"), which must NOT become a link.
    text = re.sub(r"\[(.+?)\]\((https?://[^)]+|/[^)]*|#[^)]*)\)", r'<a href="\2">\1</a>', text)
    return text


ORDERED_ITEM = re.compile(r"^\d+\.\s+(.*)")


def md_to_html(text):
    lines = text.splitlines()
    html = []
    i = 0
    list_type = None  # None, "ul", or "ol"

    def close_list():
        nonlocal list_type
        if list_type:
            html.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            close_list()
            i += 1
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            if len(rows) >= 2:
                header = [c.strip() for c in rows[0].strip("|").split("|")]
                body_rows = rows[2:] if re.match(r"^\|[-\s|]+\|$", rows[1]) else rows[1:]
                html.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in header) + "</tr></thead><tbody>")
                for r in body_rows:
                    cells = [c.strip() for c in r.strip("|").split("|")]
                    html.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                html.append("</tbody></table></div>")
            continue

        if stripped.startswith("### "):
            html.append(f"<h3>{inline(stripped[4:])}</h3>")
            i += 1
            continue
        if stripped.startswith("## "):
            html.append(f"<h2>{inline(stripped[3:])}</h2>")
            i += 1
            continue
        if stripped.startswith("# "):
            html.append(f"<h1>{inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("> "):
            html.append(f'<div class="disclosure">{inline(stripped[2:])}</div>')
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if list_type != "ul":
                close_list()
                html.append("<ul>")
                list_type = "ul"
            html.append(f"<li>{inline(stripped[2:])}</li>")
            i += 1
            continue

        ordered_match = ORDERED_ITEM.match(stripped)
        if ordered_match:
            if list_type != "ol":
                close_list()
                html.append("<ol>")
                list_type = "ol"
            html.append(f"<li>{inline(ordered_match.group(1))}</li>")
            i += 1
            continue

        close_list()

        if stripped == "---":
            html.append("<hr>")
            i += 1
            continue

        html.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_list()
    return "\n".join(html)


def build_file(src: Path, dest: Path, css_path: str):
    meta, body_md = parse_frontmatter(src.read_text(encoding="utf-8"))
    title = meta.get("title", src.stem)
    body_html = md_to_html(body_md)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(TEMPLATE.format(title=title, body=body_html, css_path=css_path), encoding="utf-8")
    print(f"built: {dest.relative_to(ROOT)}")


def main():
    articles_dir = SITE / "articles"
    for md_file in (ROOT / "content" / "published").glob("*.md"):
        build_file(md_file, articles_dir / (md_file.stem + ".html"), "../")

    preview_dir = SITE / "articles-preview"
    for md_file in (ROOT / "content" / "drafts").glob("*.md"):
        build_file(md_file, preview_dir / (md_file.stem + ".html"), "../")

    legal_map = {
        "privacy_policy.md": "privacy.html",
    }
    for src_name, dest_name in legal_map.items():
        src = ROOT / "legal" / src_name
        if src.exists():
            build_file(src, SITE / dest_name, "")

    build_index()


INDEX_TEMPLATE = """<meta charset="UTF-8">
<title>ASM Lab</title>
<link rel="stylesheet" href="styles.css">
<header>
  <div class="inner">
    <a class="brand" href="index.html">ASM Lab</a>
    <div class="tagline">Daily Goods, Compared.</div>
  </div>
</header>
<main>
  <p class="lede">毎日使う消耗品・日用品を、実際の使用感をもとに比較する記録。</p>
  <ul class="index-list">
{items}
  </ul>
</main>
<footer>
  <div>
    <a href="privacy.html">プライバシーポリシー</a>
  </div>
  <div>&copy; ASM</div>
</footer>
"""


def build_index():
    """content/published/*.md から site/index.html を再生成する。0件の場合は既存のindex.htmlをそのまま残す。"""
    published = sorted((ROOT / "content" / "published").glob("*.md"))
    if not published:
        print("skip index rebuild: content/published is empty")
        return

    items = []
    for n, md_file in enumerate(reversed(published), start=1):
        meta, _ = parse_frontmatter(md_file.read_text(encoding="utf-8"))
        title = meta.get("title", md_file.stem)
        items.append(
            f'    <li><a href="articles/{md_file.stem}.html">'
            f'<span class="index-num mono">{n:02d}</span>'
            f'<span class="index-title">{inline(title)}</span>'
            f'<span class="index-meta">{md_file.stem[:8]}</span>'
            f"</a></li>"
        )
    (SITE / "index.html").write_text(INDEX_TEMPLATE.format(items="\n".join(items)), encoding="utf-8")
    print("built: site/index.html")


if __name__ == "__main__":
    main()
