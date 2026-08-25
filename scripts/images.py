#!/usr/bin/env python3
"""Offload opted-in post images to S3-compatible object storage.

Posts opt in by setting `upload_images: true` in their YAML front matter.

When `image_host` in `_config.yml` is `local` (the default), images are served
directly from the repo by GitHub Pages and this script is never invoked. When
`image_host` is `s3`, the deploy workflow runs:

    python3 scripts/images.py upload    # before `jekyll build`
    python3 scripts/images.py rewrite   # after  `jekyll build`

`upload` copies every non-`.md` file in an opted-in post's directory to
`images/<slug>/<relative-path>` in the bucket. `rewrite` updates the built HTML
in `_site/` so image references point at `IMAGES_PUBLIC_URL`.

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


def find_media_files(slug):
    post_dir = PAGES_DIR / slug
    return [f for f in post_dir.rglob('*')
            if f.is_file() and f.suffix.lower() != '.md']


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

    total = 0
    errors = 0
    for slug in slugs:
        media = find_media_files(slug)
        if not media:
            print(f"  [{slug}] No media files found.")
            continue
        print(f"  [{slug}] {len(media)} file(s):")
        for f in media:
            rel_path = f.relative_to(PAGES_DIR / slug)
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
                        ExtraArgs={'ContentType': content_type})
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


def rewrite_html(html_path, slug, media_basenames, media_rel_paths, public_url):
    with open(html_path) as f:
        content = f.read()

    changed = False

    def replace(m):
        nonlocal changed
        attr, url = m.group(1), m.group(2)

        # Skip URLs that are already external.
        if url.startswith('http://') or url.startswith('https://'):
            return m.group(0)

        # Pattern A: absolute /pages/<slug>/<rest>
        prefix = f'/pages/{slug}/'
        idx = url.find(prefix)
        if idx != -1:
            rest = url[idx + len(prefix):]
            changed = True
            return f'{attr}="{public_url}/images/{slug}/{rest}"'

        # Pattern B: bare filename (relative, no directory components)
        if '/' not in url and '\\' not in url:
            if url in media_basenames:
                changed = True
                return f'{attr}="{public_url}/images/{slug}/{url}"'

        # Pattern C: relative path with subdirectories (e.g. ./images/photo.png)
        stripped = url[2:] if url.startswith('./') else url
        if stripped in media_rel_paths:
            changed = True
            return f'{attr}="{public_url}/images/{slug}/{stripped}"'

        return m.group(0)

    new_content = ATTR_RE.sub(replace, content)

    if changed:
        with open(html_path, 'w') as f:
            f.write(new_content)
        return True
    return False


def media_index(slug):
    post_dir = PAGES_DIR / slug
    names = set()
    rel_paths = set()
    for f in post_dir.rglob('*'):
        if f.is_file() and f.suffix.lower() != '.md':
            names.add(f.name)
            rel_paths.add(str(f.relative_to(post_dir)))
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
                content = f.read()
            rewrites = 0
            for _, url in ATTR_RE.findall(content):
                if url.startswith('http://') or url.startswith('https://'):
                    continue
                prefix = f'/pages/{slug}/'
                idx = url.find(prefix)
                if idx != -1:
                    rewrites += 1
                elif '/' not in url and '\\' not in url and url in media_basenames:
                    rewrites += 1
                else:
                    stripped = url[2:] if url.startswith('./') else url
                    if stripped in media_rel_paths:
                        rewrites += 1
            if rewrites:
                print(f"  [{slug}] {rewrites} URL(s) would be rewritten")
            else:
                print(f"  [{slug}] No URLs to rewrite")
        else:
            if rewrite_html(html_file, slug, media_basenames,
                            media_rel_paths, public_url):
                print(f"  [{slug}] Rewritten: {html_file}")
                total_rewritten += 1
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
