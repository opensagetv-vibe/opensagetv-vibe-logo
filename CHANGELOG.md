# Changelog

## Unreleased

- Migrated the complete generator into independent `opensagetv-vibe-logo`.
- Added deterministic generation, asset-contract validation, SHA-verified
  Android installation, unified Docker integration, and standard handoff files.
- Pinned all Python dependencies and corrected the documented generator version
  and actual 320x150 in-app logo size.
- Moved the former Android-only raster source into `reference/` for historical
  comparison, eliminating the competing branding source from the client.
- Moved the superseded host-Python and host-font Windows helpers under
  `reference/`; the supported root Windows workflow is now `dev.cmd` using the
  unified Docker image.

## Generator 1.6.4

- Added robust SVG style parsing and forced selected hidden groups and children
  visible for full renders.
- Added configurable `[full_render] force_visible` selectors.
- Made missing/unreadable configuration an explicit failure.
- Improved preview labels, dimensions, and render reports.

## Generator 1.6.2

- Fixed whole-group SVG filtering for the in-app logo.
- `TEXT` and `wave` now retain all authored child elements.
- Prevents the flower-only 256x89 output seen in v1.6.1.
- Retains CairoSVG-only Linux/Docker rendering.
- Retains project-local M_PLUS_Rounded_1c font loading.
- Retains transparent round icons.

## Generator 1.6.1

- Added Windows installed-font helper support.
