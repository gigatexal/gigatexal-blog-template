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

Each post is its own folder under `pages/`, with a Markdown file named after the
folder:

```text
pages/
  my-post/
    my-post.md
```

Front matter:

```yaml
---
layout: default
title: My Post
description: A one-line summary used for SEO and the feed.
type: post      # "post" shows it on the home page; "page" hides it
tags: [jekyll, tutorial]
date: 2026-01-15
---
```

- `type: post` includes the page in the home listing and the tag sidebar.
- `type: page` keeps a page out of the listing (use it for an About page).
- `tags` is a YAML list of short, lowercase, hyphenated words.

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
