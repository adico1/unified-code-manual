"""Publish one verified words-to-publication bundle through one operation."""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "docs" / "ARTICLE.md"
PACKAGE = ROOT / "docs" / "PUBLICATION.md"
DEFAULT_SITE = "https://adico.tech"


def run(arguments, capture=False):
    return subprocess.run(
        arguments,
        cwd=ROOT,
        check=True,
        capture_output=capture,
        text=True,
    )


def frontmatter(source):
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", source, re.DOTALL)
    if match is None:
        raise ValueError("article-frontmatter")
    metadata = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError("article-frontmatter-line")
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, match.group(2).strip() + "\n"


def inline(source):
    escaped = html.escape(source, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )


def markdown_html(source):
    output = []
    paragraph = []
    listing = False
    code = False
    code_lines = []

    def flush_paragraph():
        if paragraph:
            output.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def close_list():
        nonlocal listing
        if listing:
            output.append("</ul>")
            listing = False

    for line in source.splitlines():
        if line.startswith("```"):
            flush_paragraph()
            close_list()
            if code:
                output.append(
                    "<pre><code>"
                    + html.escape("\n".join(code_lines))
                    + "</code></pre>"
                )
                code_lines.clear()
            code = not code
            continue
        if code:
            code_lines.append(line)
            continue
        heading = re.match(r"^(#{1,6}) (.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(
                f"<h{level}>{inline(heading.group(2))}</h{level}>"
            )
            continue
        if line.startswith("- "):
            flush_paragraph()
            if not listing:
                output.append("<ul>")
                listing = True
            output.append("<li>" + inline(line[2:]) + "</li>")
            continue
        if line.startswith("> "):
            flush_paragraph()
            close_list()
            output.append("<blockquote><p>" + inline(line[2:]) + "</p></blockquote>")
            continue
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        paragraph.append(line.strip())
    flush_paragraph()
    close_list()
    if code:
        raise ValueError("article-code-fence")
    return "\n".join(output) + "\n"


def request(url, authorization=None, method="GET", payload=None):
    headers = {"Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json; charset=utf-8"
    operation = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(operation, timeout=30) as response:
        return json.loads(response.read())


def wordpress_authority():
    user = os.environ.get("ADICO_WORDPRESS_USER")
    password = os.environ.get("ADICO_WORDPRESS_APP_PASSWORD")
    if not user or not password:
        raise ValueError(
            "wordpress-authority:"
            "ADICO_WORDPRESS_USER+ADICO_WORDPRESS_APP_PASSWORD"
        )
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def verify(query):
    if not query.strip():
        raise ValueError("empty-publication-query")
    metadata, article = frontmatter(ARTICLE.read_text(encoding="utf-8"))
    if metadata.get("status") != "ready":
        raise ValueError("article-not-ready")
    proof = run(
        [sys.executable, "tools/verify_all.py", "--generate-only"],
        capture=True,
    )
    run([sys.executable, "tools/modify_seeds.py", "--check"], capture=True)
    run(["git", "diff", "--check"], capture=True)
    if run(["git", "status", "--porcelain"], capture=True).stdout:
        raise ValueError("publication-worktree-not-clean")
    run(["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"])
    match = re.search(r"complete-tree=([0-9a-f]{64})", proof.stdout)
    if match is None or match.group(1) not in PACKAGE.read_text(encoding="utf-8"):
        raise ValueError("publication-evidence-mismatch")
    return {
        "query": query,
        "metadata": metadata,
        "article": article,
        "html": markdown_html(article),
        "tree_sha256": match.group(1),
        "head": run(["git", "rev-parse", "HEAD"], capture=True).stdout.strip(),
    }


def publish_wordpress(bundle, site, authorization):
    base = site.rstrip("/")
    request(
        base + "/wp-json/wp/v2/users/me?context=edit",
        authorization,
    )
    slug = bundle["metadata"]["slug"]
    existing = request(
        base
        + "/wp-json/wp/v2/posts?"
        + urllib.parse.urlencode({"slug": slug, "status": "any"}),
        authorization,
    )
    payload = {
        "title": bundle["metadata"]["title"],
        "slug": slug,
        "content": bundle["html"],
        "status": "publish",
    }
    endpoint = (
        base + f"/wp-json/wp/v2/posts/{existing[0]['id']}"
        if existing
        else base + "/wp-json/wp/v2/posts"
    )
    result = request(endpoint, authorization, "POST", payload)
    return {
        "id": result["id"],
        "link": result["link"],
        "status": result["status"],
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--site",
        default=os.environ.get("ADICO_WORDPRESS_URL", DEFAULT_SITE),
    )
    arguments = parser.parse_args(argv)
    bundle = verify(arguments.query)
    result = {
        "event": "publication.dry-run",
        "query": bundle["query"],
        "head": bundle["head"],
        "tree_sha256": bundle["tree_sha256"],
        "targets": ["github", "wordpress"],
        "linkedin_copy": "docs/PUBLICATION.md",
    }
    if arguments.execute:
        authorization = wordpress_authority()
        request(
            arguments.site.rstrip("/")
            + "/wp-json/wp/v2/users/me?context=edit",
            authorization,
        )
        run(["git", "push", "origin", "HEAD:main"])
        result.update(
            {
                "event": "publication.completed",
                "github": "https://github.com/adico1/unified-code-manual",
                "wordpress": publish_wordpress(
                    bundle,
                    arguments.site,
                    authorization,
                ),
            }
        )
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
