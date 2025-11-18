# Documentation Translation Guide

This guide explains how to translate the CryptoBot Python documentation into different languages.

## Overview

The documentation uses Sphinx's internationalization (i18n) support with `sphinx-intl` for managing translations. Translation files are stored in `.po` (Portable Object) format under `docs/locale/<language>/LC_MESSAGES/`.

## Available Languages

Currently supported languages:
- **English** (en) - Default
- **Spanish** (es) - Complete translation

## Prerequisites

Install documentation dependencies:

```bash
poetry install --extras docs
```

Or directly:

```bash
pip install sphinx sphinx-intl sphinx-rtd-theme myst-parser
```

## Quick Start: Adding a New Language

### 1. Generate Translation Templates

First, generate the `.pot` (Portable Object Template) files:

```bash
cd docs
make gettext
```

This creates template files in `_build/gettext/`.

### 2. Create Translation Catalog

Create `.po` files for your language (e.g., French):

```bash
cd docs
make update-po LANG=fr
```

This creates `locale/fr/LC_MESSAGES/*.po` files.

### 3. Translate Content

Edit the `.po` files in `locale/fr/LC_MESSAGES/` and fill in the `msgstr` fields:

```po
#: ../../index.md:1
msgid "Welcome to CryptoBot Python's documentation!"
msgstr "Bienvenue dans la documentation de CryptoBot Python!"
```

**Translation Guidelines:**
- Translate only the `msgstr` fields
- Keep code blocks, URLs, and technical identifiers unchanged
- Preserve markdown formatting
- Maintain consistent terminology

### 4. Build Translated Documentation

Build the documentation in your target language:

```bash
cd docs
make html-lang LANG=fr
```

The translated HTML will be in `_build/html/fr/`.

## Updating Existing Translations

When the English documentation changes, update translation files:

```bash
cd docs
make update-po LANG=es
```

This updates the `.po` files with new strings while preserving existing translations. Untranslated or updated strings will be marked as "fuzzy" and need review.

## Makefile Commands

The `docs/Makefile` provides several translation commands:

### `make gettext`
Generates `.pot` template files from source documentation.

```bash
cd docs
make gettext
```

### `make update-po LANG=<language>`
Updates or creates `.po` files for a specific language.

```bash
cd docs
make update-po LANG=es    # Update Spanish
make update-po LANG=fr    # Update French
```

### `make html-lang LANG=<language>`
Builds HTML documentation in a specific language.

```bash
cd docs
make html-lang LANG=es    # Build Spanish docs
make html-lang LANG=fr    # Build French docs
```

Output location: `_build/html/<language>/`

## File Structure

```
docs/
├── locale/                    # Translation catalogs
│   ├── es/                   # Spanish translations
│   │   └── LC_MESSAGES/
│   │       ├── index.po
│   │       ├── installation.po
│   │       ├── usage.po
│   │       └── ...
│   └── fr/                   # French translations (example)
│       └── LC_MESSAGES/
│           └── ...
├── _build/
│   ├── gettext/              # Generated .pot templates
│   └── html/
│       ├── en/               # English HTML (default)
│       ├── es/               # Spanish HTML
│       └── fr/               # French HTML (example)
├── conf.py                    # Sphinx configuration
└── Makefile                   # Build commands
```

## Translation Workflow

### For New Translators

1. **Fork the repository**
2. **Create translation files:**
   ```bash
   cd docs
   make update-po LANG=<your_language>
   ```

3. **Translate:**
   - Edit `.po` files in `locale/<your_language>/LC_MESSAGES/`
   - Use a `.po` editor like [Poedit](https://poedit.net/) or any text editor
   - Focus on `msgstr` fields

4. **Test your translation:**
   ```bash
   make html-lang LANG=<your_language>
   ```
   - Open `_build/html/<your_language>/index.html` in a browser

5. **Submit a pull request** with your translations

### For Maintainers

When documentation is updated:

1. **Regenerate templates:**
   ```bash
   cd docs
   make gettext
   ```

2. **Update all language catalogs:**
   ```bash
   make update-po LANG=es
   make update-po LANG=fr
   # ... for each language
   ```

3. **Review fuzzy translations:**
   - Search for `#, fuzzy` in `.po` files
   - Update or confirm these translations
   - Remove the `#, fuzzy` marker when done

4. **Build and verify all languages:**
   ```bash
   make html-lang LANG=es
   make html-lang LANG=fr
   ```

## Best Practices

### Translation Quality

- **Consistency:** Use consistent terminology throughout
- **Context:** Consider the technical context when translating
- **Natural language:** Translate meaning, not word-for-word
- **Code preservation:** Never translate:
  - Python code
  - Variable/function names
  - URLs
  - Command-line instructions
  - API endpoints

### Common Patterns

**Code comments in examples:**
```po
msgid "# Create a client"
msgstr "# Crear un cliente"
```

**Mixed content (keep code unchanged):**
```po
msgid "Call `client.create_invoice()` to create invoices"
msgstr "Llama a `client.create_invoice()` para crear facturas"
```

**URLs and links:**
```po
msgid "See [documentation](https://example.com) for details"
msgstr "Ver [documentación](https://example.com) para detalles"
```

## Tools

### Recommended .po Editors

- **[Poedit](https://poedit.net/)** - Cross-platform, user-friendly
- **[Lokalize](https://apps.kde.org/lokalize/)** - KDE translation tool
- **[GTranslator](https://wiki.gnome.org/Apps/Gtranslator)** - GNOME translation tool
- **Text editors** - VS Code, vim, emacs with syntax highlighting

### Validation

Check for errors in `.po` files:

```bash
msgfmt --check locale/es/LC_MESSAGES/index.po
```

## Read the Docs Integration

The project is configured to build multi-language documentation on Read the Docs:

- Configuration: `.readthedocs.yaml`
- Translation files are generated during the build process
- Spanish documentation is automatically built and published

## Contributing Translations

We welcome translations! Here's how to contribute:

1. Check [existing translations](locale/)
2. Create an issue announcing your translation
3. Follow the workflow above
4. Submit a pull request
5. Maintainers will review and merge

### Translation Checklist

- [ ] All `.po` files updated
- [ ] No `#, fuzzy` markers remain
- [ ] Documentation builds without errors
- [ ] Translated pages display correctly
- [ ] Code examples work as expected
- [ ] Links and references are functional

## Troubleshooting

### Build Errors

**Error: `unsupported locale setting`**
```bash
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
make html-lang LANG=es
```

**Error: `sphinx-intl` not found**
```bash
poetry install --extras docs
# or
pip install sphinx-intl
```

### Translation Not Appearing

1. Check `.mo` files were generated:
   ```bash
   ls locale/es/LC_MESSAGES/*.mo
   ```

2. Rebuild from scratch:
   ```bash
   make clean
   make html-lang LANG=es
   ```

3. Verify language code in `msgstr` header

## Resources

- [Sphinx Internationalization](https://www.sphinx-doc.org/en/master/usage/advanced/intl.html)
- [GNU gettext Manual](https://www.gnu.org/software/gettext/manual/)
- [sphinx-intl Documentation](https://sphinx-intl.readthedocs.io/)

## Questions?

For translation questions or issues:
- Open an issue on GitHub
- Contact the maintainers
- Check existing `.po` files for examples
