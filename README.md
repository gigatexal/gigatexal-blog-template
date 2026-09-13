# My Blog — a Jekyll template with tags

A minimal [Jekyll](https://jekyllrb.com) blog with a tag system, RSS, a sitemap,
and a clean reading theme. Fork it, change the title, delete the sample posts,
and start writing.

## Features

- **Tags** — every post declares `tags` in its front matter; the sidebar lists
  them all and clicking one filters the home page in the browser (no reload).
- **Posts grouped by month** on the home page.
- **RSS** (`/feed.xml`) and **sitemap** (`/sitemap.xml`) via `jekyll-seo-tag`
  and `jekyll-sitemap`.
- **Related posts** — a small script recommends posts with shared tags.
- **Responsive, dependency-free theme** — plain CSS inlined in the layouts, no
  frameworks.

## Requirements

- Ruby 3.1+
- [Bundler](https://bundler.io)

## Local development

```sh
bundle install
bundle exec jekyll serve
```

Open <http://localhost:4000>. Jekyll rebuilds the site as you edit files.

## Deploying to GitHub Pages

Deployment is **opt-in**. The workflow (`.github/workflows/pages.yml`) ships in
the repo but is gated behind the `pages_deploy` flag in `_config.yml` (default
`false`), so it does nothing until you switch it on.

1. In `_config.yml`, set `pages_deploy: true`.
2. Update `url` in `_config.yml` to your site URL:
   - user site (`username.github.io`): `https://username.github.io`
   - project site (`username.github.io/repo`): `https://username.github.io`
     (leave `baseurl` empty — the workflow sets it automatically).
3. Push the repo to GitHub.
4. Enable Pages with Actions as the source: **Settings → Pages →
   "Build and deployment" → Source → GitHub Actions**. See GitHub's guide,
   [Configuring a publishing source for your GitHub Pages
   site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
5. Push. The workflow builds and publishes on every push to `main`; watch
   progress under the repo's **Actions** tab.

> The workflow triggers on the `main` branch. If your default branch is
> `master`, change the `branches:` list in `.github/workflows/pages.yml`.

## Writing a post

The fastest way is to copy an existing post and rename it:

```sh
cp -r pages/getting-started pages/my-new-post
mv pages/my-new-post/getting-started.md pages/my-new-post/my-new-post.md
```

Each post is its own folder under `pages/`, with a Markdown file named after the
folder (`pages/<slug>/<slug>.md`):

```text
pages/
  my-new-post/
    my-new-post.md
```

Then edit the front matter:

```yaml
---
layout: default
title: My New Post
description: A one-line summary used for SEO and the feed.
type: post      # "post" shows it on the home page; "page" hides it
tags: [jekyll, tutorial]
date: 2026-01-15
---
```

- `type: post` includes the page in the home listing, tag sidebar, RSS feed, and
  `posts.json` — nothing else to register. The home page is rebuilt automatically
  on every deploy, so **there is no `index.md` to edit**.
- `type: page` keeps a page out of the listing (use it for an About page).
- `tags` is a YAML list of short, lowercase, hyphenated words.
- Optional: `upload_images: true` offloads this post's images to object storage
  (see [Hosting images](#hosting-images)).

## Hosting images

By default, images live next to their post (e.g. `pages/my-new-post/photo.png`)
and are served directly by GitHub Pages — no setup required. Reference them in
Markdown as `![alt text](/pages/my-new-post/photo.png)` or
`![alt text](./photo.png)`; both work with either backend.

To offload images to object storage, set `upload_images: true` on a post and
choose a backend with `image_host` in `_config.yml`:

| `image_host` | Behavior |
|---|---|
| `local` (default) | Images are served from the repo; `upload_images: true` is ignored. |
| `s3` | Posts with `upload_images: true` are uploaded to an S3-compatible bucket and their image URLs are rewritten to the bucket's public URL at build time. |

`image_host: s3` works with any S3-compatible store — AWS S3, Cloudflare R2,
MinIO, or Backblaze B2. Configure it with these **repository secrets**
(GitHub → **Settings → Secrets and variables → Actions**):

| Secret | Required | Purpose |
|---|---|---|
| `IMAGES_BUCKET` | yes | Bucket name |
| `IMAGES_ACCESS_KEY_ID` | yes | Access key id |
| `IMAGES_SECRET_ACCESS_KEY` | yes | Secret access key |
| `IMAGES_PUBLIC_URL` | yes | Public/CDN base URL images are served from |
| `IMAGES_ENDPOINT_URL` | for R2/MinIO/B2 | S3 endpoint; omit for AWS S3 |
| `IMAGES_REGION` | optional | AWS region (default `us-east-1`) |

The pipeline runs in `.github/workflows/pages.yml`: `scripts/images.py upload`
before `jekyll build` and `scripts/images.py rewrite` after. Both run only when
`image_host` is not `local`, and secrets are injected as environment variables —
never committed.

What the two steps do, precisely:

- **upload** copies every media file in the post's folder, recursively, to
  `images/<slug>/<relative-path>`. Markdown sources, hidden files and OS junk
  (`.DS_Store`, `Thumbs.db`, `desktop.ini`) are skipped, and each object is
  tagged with `Content-Type` and `Cache-Control`. Set `IMAGES_CACHE_CONTROL`
  (repository *variable* or secret) to change the header; the default is
  `public, max-age=86400`.
- **rewrite** only touches `src`/`href` values that resolve to a file actually
  present in that post's folder — links to pages (`/pages/<slug>/<slug>.html`),
  anchors, `data:` URIs, other posts and other sites are left alone, and
  `?query`/`#fragment` suffixes are preserved. Both steps can be previewed
  locally with `python3 scripts/images.py upload --dry-run` / `rewrite --dry-run`
  (dry runs of `rewrite` need `IMAGES_PUBLIC_URL` in the environment).
- Deleting an image from the repo does **not** delete it from your bucket: there
  is no prune step, so remove stale objects in your storage dashboard.
- Your Markdown keeps local paths; only the built `_site/` HTML points at
  `IMAGES_PUBLIC_URL`, so local `jekyll serve` still works without the bucket.

## How tags work

Tags are plain Liquid — no custom gem. Both layouts collect every post's `tags`,
deduplicate them, and render the sidebar. On the home page, `assets/js/tag-filter.js`
orders tags by frequency and filters the post list client-side; the current filter
is reflected in the URL (`/?tag=jekyll`). On a post page, the post's own tags are
highlighted in the sidebar.

## Configuration

Everything site-wide lives in `_config.yml`:

| Key | Meaning |
|---|---|
| `title` | Site title, shown in the header and `<title>` |
| `tagline` | Short line under the title |
| `description` | Used by SEO and the RSS feed |
| `url` | Absolute site URL (required for SEO/sitemap/feed) |
| `baseurl` | Sub-path for project sites; usually leave empty |
| `pages_deploy` | `true` enables the GitHub Pages deploy workflow (default `false`) |
| `image_host` | `local` (default) or `s3` — where `upload_images: true` posts' images go |
| `author.name` | Shown in the footer and RSS `<dc:creator>` |

## Customizing the theme

The CSS is inlined in `_layouts/home.html` and `_layouts/default.html`. The two
files share the same palette and typography — keep them in sync when you tweak
colors or spacing.

## Related posts

`assets/js/related-posts.js` fetches `/posts.json`, reads the tags of pages you
have visited (stored in `localStorage`), and lists up to five posts with shared
tags. Delete `_includes/related_posts.html`, `assets/js/related-posts.js`, and
`posts.json` if you don't want it.
