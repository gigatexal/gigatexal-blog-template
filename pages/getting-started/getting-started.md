---
layout: default
title: Welcome to Your New Blog
description: A quick tour of how posts, tags, and the layout work together.
type: post
tags: [getting-started, jekyll, tutorial]
date: 2026-08-20
---

# Welcome to Your New Blog

This is a minimal Jekyll blog with tag filtering. It ships with three sample
posts so you can see how everything fits together before you start writing.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

## How posts work

Every post lives in its own folder under `pages/` and carries YAML front
matter:

```yaml
---
layout: default
title: Welcome to Your New Blog
description: A quick tour of how posts, tags, and the layout work together.
type: post
tags: [getting-started, jekyll, tutorial]
date: 2026-08-20
---
```

The `type: post` field is what makes a page show up in the home listing and in
the tag sidebar. Pages you want to keep out of the listing (an about page, for
example) use `type: page` instead.

## The layout

The theme is deliberately plain: a sticky tag sidebar on the left, posts on the
right, and a small footer. It collapses to a single column on narrow screens.

- Posts are grouped by month on the home page.
- The sidebar lists every tag, ordered by how often it appears.
- Clicking a tag filters the list in the browser — no page reload.

> Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore
> eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
> in culpa qui officia deserunt mollit anim id est laborum.
