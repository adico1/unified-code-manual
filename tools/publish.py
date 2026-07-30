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
import time
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
        return None
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return "Basic " + token


def apple_script(source):
    return subprocess.run(
        ["osascript", "-e", source],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def browser_javascript(source):
    return apple_script(
        "tell application \"Brave Browser\" to execute active tab of "
        "front window javascript "
        + json.dumps(source)
    )


def browser_wordpress_preflight(site):
    admin = site.rstrip("/") + "/wp-admin/edit.php"
    apple_script(
        "tell application \"Brave Browser\"\n"
        "activate\n"
        f"make new tab at end of tabs of front window with properties "
        f"{{URL:{json.dumps(admin)}}}\n"
        "end tell"
    )
    status = None
    for _ in range(30):
        time.sleep(0.25)
        raw = browser_javascript(
            "(()=>{const s=Array.from(document.scripts).map(x=>x.textContent)"
            ".find(t=>t.includes('var wpApiSettings'));"
            "const m=s&&s.match(/var wpApiSettings = (\\{.*?\\});/s);"
            "return JSON.stringify({url:location.href,"
            "ready:document.readyState,nonce:Boolean(m&&JSON.parse(m[1]).nonce)})"
            "})()"
        )
        status = json.loads(raw) if raw else {}
        if "wp-login" in status.get("url", ""):
            raise ValueError("wordpress-browser-not-authenticated")
        if status.get("ready") == "complete" and status.get("nonce"):
            return {"mode": "logged-in-browser", "admin": admin}
    raise ValueError("wordpress-browser-boundary:" + repr(status))


def publish_wordpress_browser(bundle, site):
    encoded = base64.b64encode(
        json.dumps(
            {
                "title": bundle["metadata"]["title"],
                "slug": bundle["metadata"]["slug"],
                "content": bundle["html"],
            },
            ensure_ascii=False,
        ).encode()
    ).decode()
    javascript = (
        "(()=>{"
        f"const p=JSON.parse(atob('{encoded}'));"
        "const s=Array.from(document.scripts).map(x=>x.textContent)"
        ".find(t=>t.includes('var wpApiSettings'));"
        "const m=s&&s.match(/var wpApiSettings = (\\{.*?\\});/s);"
        "if(!m)throw new Error('wordpress-rest-bootstrap');"
        "const n=JSON.parse(m[1]).nonce;"
        "const q=(m,u,b)=>{const x=new XMLHttpRequest();"
        "x.open(m,u,false);x.setRequestHeader('X-WP-Nonce',n);"
        "if(b)x.setRequestHeader('Content-Type','application/json');"
        "x.send(b?JSON.stringify(b):null);"
        "if(x.status<200||x.status>=300)throw new Error(x.status+':'+x.responseText);"
        "return JSON.parse(x.responseText)};"
        "const base=location.origin+'/wp-json/wp/v2/posts';"
        "const found=q('GET',base+'?context=edit&status=any&slug='"
        "+encodeURIComponent(p.slug));"
        "const body={title:p.title,slug:p.slug,content:p.content,status:'publish'};"
        "const out=q('POST',found.length?base+'/'+found[0].id:base,body);"
        "return JSON.stringify({id:out.id,link:out.link,status:out.status})"
        "})()"
    )
    return json.loads(browser_javascript(javascript))


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
        browser = None
        if authorization:
            request(
                arguments.site.rstrip("/")
                + "/wp-json/wp/v2/users/me?context=edit",
                authorization,
            )
        else:
            browser = browser_wordpress_preflight(arguments.site)
        run(["git", "push", "origin", "HEAD:main"])
        wordpress = (
            publish_wordpress(
                bundle,
                arguments.site,
                authorization,
            )
            if authorization
            else publish_wordpress_browser(
                bundle,
                arguments.site,
            )
        )
        result.update(
            {
                "event": "publication.completed",
                "github": "https://github.com/adico1/unified-code-manual",
                "wordpress_authority": (
                    {"mode": "official-rest-api"}
                    if authorization
                    else browser
                ),
                "wordpress": wordpress,
            }
        )
    sys.stdout.write(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
