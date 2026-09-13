#!/usr/bin/env python3
"""Offload opted-in post images to S3-compatible object storage.

Posts opt in by setting `upload_images: true` in their YAML front matter.

When `image_host` in `_config.yml` is `local` (the default), images are served
directly from the repo by GitHub Pages and this script is never invoked. When
`image_host` is `s3`, the deploy workflow runs:

    python3 scripts/images.py upload    # before `jekyll build`
    python3 scripts/images.py rewrite   # after  `jekyll build`

`upload` copies every media file in an opted-in post's directory (recursively;
`.md` sources, hidden files and OS junk such as `.DS_Store` are skipped) to
`images/<slug>/<relative-path>` in the bucket, tagging each object with a
`Cache-Control` header. `rewrite` updates the built HTML in `_site/` so image
references point at `IMAGES_PUBLIC_URL` — only references that resolve to a file
actually present in that post's directory are rewritten, so links to pages,
anchors, other posts and other sites are left alone.

Environment variables (injected as GitHub Actions secrets — never committed):

  required:
    IMAGES_BUCKET              bucket name
    IMAGES_ACCESS_KEY_ID       access key id
    IMAGES_SECRET_ACCESS_KEY   secret access key
    IMAGES_PUBLIC_URL          public/CDN base URL (rewrite only)
  optional:
    IMAGES_ENDPOINT_URL        S3 endpoint (R2/MinIO/B2); omit for AWS S3
    IMAGES_REGION              AWS region (default us-east-1); unused when
                               IMAGES_ENDPOINT_URL is set (R2 uses `auto`)
    IMAGES_CACHE_CONTROL       Cache-Control sent with uploaded objects
                               (default `public, max-age=86400`)
"""

import os
import sys
import argparse
import mimetypes
import re
from pathlib import Path

import yaml


PAGES_DIR = Path('pages')
SITE_DIR = Path('_site')

# Files that show up in post folders but are never real images.
SKIP_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

DEFAULT_CACHE_CONTROL = 'public, max-age=86400'


def parse_frontmatter(md_path):
    with open(md_path) as f:
        content = f.read()
    if not content.startswith('---'):
        return None
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


def find_opted_in_slugs():
    slugs = []
    for md_file in sorted(PAGES_DIR.glob('*/*.md')):
        fm = parse_frontmatter(md_file)
        if fm and fm.get('upload_images'):
            slugs.append(md_file.parent.name)
    return slugs


def is_media_file(path):
    """True for post files that belong in the bucket: not markdown, not junk."""
    name = path.name
    return (path.is_file()
            and path.suffix.lower() != '.md'
            and not name.startswith('.')
            and name not in SKIP_NAMES)


def find_media_files(slug):
    post_dir = PAGES_DIR / slug
    return sorted((f for f in post_dir.rglob('*') if is_media_file(f)),
                  key=lambda f: f.as_posix())


def require_env(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        print(f"Error: missing environment variable(s): {', '.join(missing)}")
        sys.exit(1)


def s3_client():
    # Imported lazily so `--dry-run` and `rewrite` work without boto3.
    import boto3
    from botocore.config import Config

    kwargs = dict(
        aws_access_key_id=os.environ['IMAGES_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['IMAGES_SECRET_ACCESS_KEY'],
    )
    endpoint = os.environ.get('IMAGES_ENDPOINT_URL')
    if endpoint:
        kwargs['endpoint_url'] = endpoint
        kwargs['config'] = Config(region_name=os.environ.get('IMAGES_REGION', 'auto'))
    else:
        kwargs['region_name'] = os.environ.get('IMAGES_REGION', 'us-east-1')
    return boto3.client('s3', **kwargs)


def cmd_upload(args):
    if not PAGES_DIR.is_dir():
        print("Error: 'pages/' directory not found. Run from the repo root.")
        sys.exit(1)

    slugs = find_opted_in_slugs()
    if not slugs:
        print("No posts with 'upload_images: true' found. Nothing to do.")
        return

    print(f"Found {len(slugs)} opted-in post(s): {', '.join(slugs)}")

    client = None
    bucket = None
    if not args.dry_run:
        require_env('IMAGES_BUCKET', 'IMAGES_ACCESS_KEY_ID', 'IMAGES_SECRET_ACCESS_KEY')
        client = s3_client()
        bucket = os.environ['IMAGES_BUCKET']

    cache_control = os.environ.get('IMAGES_CACHE_CONTROL') or DEFAULT_CACHE_CONTROL
    if not args.dry_run:
        print(f"Cache-Control: {cache_control}")

    total = 0
    errors = 0
    for slug in slugs:
        media = find_media_files(slug)
        if not media:
            print(f"  [{slug}] No media files found.")
            continue
        print(f"  [{slug}] {len(media)} file(s):")
        for f in media:
            rel_path = f.relative_to(PAGES_DIR / slug).as_posix()
            key = f"images/{slug}/{rel_path}"
            if args.dry_run:
                print(f"    [DRY RUN] {f} -> {key}")
            else:
                content_type, _ = mimetypes.guess_type(str(f))
                content_type = content_type or 'application/octet-stream'
                print(f"    {f} -> {key} ({content_type})")
                try:
                    client.upload_file(
                        str(f), bucket, key,
                        ExtraArgs={'ContentType': content_type,
                                   'CacheControl': cache_control})
                except Exception as e:
                    print(f"    ERROR uploading {f}: {e}")
                    errors += 1
            total += 1

    if errors:
        print(f"\nUpload completed with {errors} error(s).")
        sys.exit(1)
    if args.dry_run:
        print(f"\nDry run complete. {total} file(s) would be uploaded.")
    else:
        print(f"\nUpload complete. {total} file(s) uploaded.")


# Matches src="..." or href="..." attributes.
ATTR_RE = re.compile(r'(src|href)="([^"]*)"')


def resolve_media_url(url, slug, media_basenames, media_rel_paths):
    """Post-relative media path this URL points at, or None if it is not media.

    A URL only counts when it resolves to a file that is actually present in the
    post's directory, so `/pages/<slug>/<slug>.html` and other page links are
    never pointed at the bucket. Query strings and fragments are preserved.
    """
    if not url or url.startswith(('#', 'data:', '//')):
        return None
    if url.startswith('http://') or url.startswith('https://'):
        return None

    path, sep_q, query = url.partition('?')
    path, sep_f, fragment = path.partition('#')
    suffix = (sep_q + query) + (sep_f + fragment)

    # Pattern A: absolute /pages/<slug>/<rest>
    prefix = f'/pages/{slug}/'
    idx = path.find(prefix)
    if idx != -1:
        rest = path[idx + len(prefix):]
        return rest + suffix if rest in media_rel_paths else None

    # Pattern B: bare filename (relative, no directory components)
    if '/' not in path and '\\' not in path:
        return path + suffix if path in media_basenames else None

    # Pattern C: relative path with subdirectories (e.g. ./images/photo.png)
    stripped = path[2:] if path.startswith('./') else path
    return stripped + suffix if stripped in media_rel_paths else None


def map_urls(content, slug, media_basenames, media_rel_paths, public_url):
    """Return (rewritten HTML, [(old_url, new_url), ...])."""
    rewrites = []

    def replace(m):
        attr, url = m.group(1), m.group(2)
        target = resolve_media_url(url, slug, media_basenames, media_rel_paths)
        if target is None:
            return m.group(0)
        new_url = f'{public_url}/images/{slug}/{target}'
        rewrites.append((url, new_url))
        return f'{attr}="{new_url}"'

    return ATTR_RE.sub(replace, content), rewrites


def rewrite_html(html_path, slug, media_basenames, media_rel_paths, public_url):
    """Rewrite media URLs in place. Returns [(old_url, new_url), ...]."""
    with open(html_path) as f:
        content = f.read()

    new_content, rewrites = map_urls(content, slug, media_basenames,
                                     media_rel_paths, public_url)
    if rewrites:
        with open(html_path, 'w') as f:
            f.write(new_content)
    return rewrites


def media_index(slug):
    post_dir = PAGES_DIR / slug
    media = find_media_files(slug)
    names = {f.name for f in media}
    rel_paths = {f.relative_to(post_dir).as_posix() for f in media}
    return names, rel_paths


def cmd_rewrite(args):
    public_url = os.environ.get('IMAGES_PUBLIC_URL')

    if not SITE_DIR.is_dir():
        print("Error: '_site/' directory not found. Build the site first.")
        sys.exit(1)
    if not public_url:
        print("Error: IMAGES_PUBLIC_URL environment variable not set.")
        sys.exit(1)

    slugs = find_opted_in_slugs()
    if not slugs:
        print("No posts with 'upload_images: true' found. Nothing to do.")
        return

    print(f"Found {len(slugs)} opted-in post(s): {', '.join(slugs)}")

    total_rewritten = 0
    for slug in slugs:
        media_basenames, media_rel_paths = media_index(slug)
        html_file = SITE_DIR / 'pages' / slug / f'{slug}.html'

        if not html_file.exists():
            print(f"  [{slug}] No HTML output found at {html_file}")
            continue

        if args.dry_run:
            with open(html_file) as f:
                _, rewrites = map_urls(f.read(), slug, media_basenames,
                                       media_rel_paths, public_url)
        else:
            rewrites = rewrite_html(html_file, slug, media_basenames,
                                    media_rel_paths, public_url)
            if rewrites:
                total_rewritten += 1

        label = '[DRY RUN] ' if args.dry_run else ''
        for old, new in rewrites:
            print(f"    {label}{old} -> {new}")
        if rewrites:
            print(f"  [{slug}] {len(rewrites)} URL(s) "
                  f"{'would be rewritten' if args.dry_run else 'rewritten'}")
        else:
            print(f"  [{slug}] No URLs to rewrite in {html_file}")

    if args.dry_run:
        print("\nDry run complete.")
    else:
        print(f"\nRewrite complete. {total_rewritten} file(s) modified.")


def main():
    parser = argparse.ArgumentParser(
        description='Offload post images to S3-compatible object storage')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('upload', help='Upload opted-in images to the bucket')
    p.add_argument('--dry-run', action='store_true',
                   help='Preview without uploading')
    p.set_defaults(fn=cmd_upload)

    p = sub.add_parser('rewrite', help='Rewrite _site/ image URLs to the CDN')
    p.add_argument('--dry-run', action='store_true',
                   help='Preview without modifying files')
    p.set_defaults(fn=cmd_rewrite)

    args = parser.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
