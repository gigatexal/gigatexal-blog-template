# Developer shortcuts for this blog. Nothing in here is host- or account-specific:
# the only values you ever supply are your own (see `make help`).
#
# `make` with no target builds the site.

.PHONY: all build check-pages clean help images-rewrite images-upload install serve venv

VENV   := .venv
PY     := $(VENV)/bin/python
BUNDLE := bundle

all: build

install:
	$(BUNDLE) install

build:
	$(BUNDLE) exec jekyll build

serve:
	$(BUNDLE) exec jekyll serve --livereload

clean:
	$(BUNDLE) exec jekyll clean
	@rm -rf __pycache__ scripts/__pycache__

# Jekyll only renders files with YAML front matter; a page without it is copied
# verbatim, so `page.html` 404s while `page.md` is served raw. Fails loudly when
# a page under pages/ is missing its `---` block.
check-pages:
	@missing=0; \
	for f in $$(find pages -name '*.md'); do \
		if [ "$$(head -1 $$f)" != "---" ]; then \
			echo "  MISSING FRONT MATTER: $$f"; \
			missing=1; \
		fi; \
	done; \
	if [ $$missing -eq 0 ]; then echo "all page markdown has front matter"; else exit 1; fi

# --- image pipeline (scripts/images.py) --------------------------------------
# Only relevant when `image_host: s3` in _config.yml. The deploy workflow runs
# these steps for you on every push; the targets below are for previewing
# locally and for uploading before a manual deploy.
#
#   make images-upload ARGS="--dry-run"
#   make images-rewrite IMAGES_PUBLIC_URL=https://cdn.example.com ARGS="--dry-run"
venv:
	@test -d $(VENV) || python3 -m venv $(VENV)
	@if [ ! -f $(VENV)/.requirements.stamp ] || [ scripts/requirements.txt -nt $(VENV)/.requirements.stamp ]; then \
		echo "installing scripts/requirements.txt into $(VENV)..."; \
		$(VENV)/bin/pip install -q -r scripts/requirements.txt && touch $(VENV)/.requirements.stamp; \
	fi
	@echo "venv ready: $(VENV)"

images-upload: venv
	@$(PY) scripts/images.py upload $(ARGS)

images-rewrite: venv
	@test -n "$(IMAGES_PUBLIC_URL)" || { \
		echo "usage: make images-rewrite IMAGES_PUBLIC_URL=https://cdn.example.com [ARGS=--dry-run]"; \
		exit 1; \
	}
	@IMAGES_PUBLIC_URL=$(IMAGES_PUBLIC_URL) $(PY) scripts/images.py rewrite $(ARGS)

help:
	@echo "make              - build the site into _site/ (same as 'make build')"
	@echo "make install      - bundle install"
	@echo "make build        - build the site into _site/"
	@echo "make serve        - dev server with livereload at :4000"
	@echo "make clean        - remove _site/, .jekyll-cache/ and Python caches"
	@echo "make check-pages  - verify every page under pages/ has front matter"
	@echo "make venv         - create .venv and install scripts/requirements.txt"
	@echo "make images-upload  - upload opted-in post images (ARGS=--dry-run to preview)"
	@echo "make images-rewrite - rewrite _site/ image URLs (needs IMAGES_PUBLIC_URL)"
