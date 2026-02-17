# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = uv run python3 -msphinx
SPHINXINTL    = uv run sphinx-intl
SPHINXPROJ    = cryptobot_python
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile gettext

# Generate gettext .pot files
gettext:
	@$(SPHINXBUILD) -b gettext "$(SOURCEDIR)" "$(BUILDDIR)/gettext" $(SPHINXOPTS)
	@echo "Build finished. The gettext catalog files are in $(BUILDDIR)/gettext."

# Update translation catalogs (.po files) for a specific language
# Usage: make update-po LANG=es
update-po: gettext
	@$(SPHINXINTL) update -p "$(BUILDDIR)/gettext" -l $(LANG)
	@echo "Translation catalogs updated for language: $(LANG)"

# Build HTML documentation in a specific language
# Usage: make html-lang LANG=es
html-lang:
	@$(SPHINXBUILD) -b html -D language=$(LANG) "$(SOURCEDIR)" "$(BUILDDIR)/html/$(LANG)" $(SPHINXOPTS)
	@echo "Build finished. The HTML pages for $(LANG) are in $(BUILDDIR)/html/$(LANG)."

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
