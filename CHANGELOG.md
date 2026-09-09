# Changelog

- Updated repository CI to Ubuntu 24.04 and the current Node 24-based
  `actions/checkout@v7` and `actions/setup-python@v7` releases.

- Prepared the generator for public GitHub development with source-only checks,
  contribution/security guidance, and the shared Vibe workflow contract.

- Restored the Android resource layout used by the working client. Removed the
  five `android-tv` module square-icon overrides; standard launcher icons now
  come only from `android-shared`, while the TV module owns only the 320x180
  Leanback banner and non-APK store artwork. The pipeline now validates and
  installs 29 Android assets and deletes obsolete overrides during install.
- Added mask-safe launcher composition after the Fire TV Pro/API-30 tile
  visibly clipped the full-canvas wordmark. Legacy and Fire TV square icons are
  now inset to 80 percent, adaptive foregrounds to 60 percent, and the
  generated preview exposes both results before APK packaging.
- Removed the unsuccessful separate Fire TV companion-launcher output. The
  Android client is again the only APK, and optional Amazon catalog artwork now
  installs under `android-tv/store-assets` without becoming a launchable app.
- Fixed blank adaptive launcher icons by moving the vector-rendered Vibe
  artwork to the adaptive foreground over an opaque dark-blue background. The
  asset validator now fails if any generated adaptive foreground is fully
  transparent, preventing a build from silently producing an icon that Fire OS
  and Android launchers can resolve but cannot draw.

## Unreleased

- Recorded the physical Fire OS result for the forced-banner workaround. A
  rectangular `android:icon` and the single-activity dual-launcher-category
  variant were both omitted from Apps & Channels after clean installs and
  reboots on AFTMM/API 25. The supported sideload path keeps the square icon
  and uses the 320x180 artwork only as banner/logo.
- Corrected the Fire TV compatibility launcher to use its generated square
  icon for the application and standard `LAUNCHER` entry while reserving the
  16:9 banner for `LEANBACK_LAUNCHER`, matching Fire OS sideload fallback
  behavior. Added the required 114x114 and 512x512 Amazon tablet icons, an
  opaque 1280x720 Fire TV app icon whose critical art fits the documented
  882x448 safe area, and a separate title-free opaque 1920x1080 Fire TV
  background. Included both Fire TV images in the generated preview.
- Restored the unqualified banner resource placement proven visible on the
  AFTMM Fire OS 7 launcher. The separate TV-density square icon remains, so a
  sideloaded tile uses a sharper source without depending on banner behavior.
- Added TV-specific 80/120/160/240/320px square launcher rasters. Stock Fire TV
  deliberately displays this square icon for sideloaded packages, so it now
  uses a sharp 160px xhdpi source rather than enlarging the phone 96px asset.
  The independent 320x180 xhdpi banner remains available to Android TV and app
  store delivery, matching the published Android TV asset contract.
- Fixed the Fire TV cover at the resource-contract level: it is emitted as the
  physically proven unqualified `drawable` 320x180 opaque RGB resource,
  rendered from a 2048px vector supersample and reduced exactly once for
  cleaner edges. Fire OS 7's Apps Grid displayed the xhdpi-qualified experiment
  as blank even though PackageManager resolved it, so installation removes it.
- Fixed Fire OS 7 launcher compatibility by encoding the Android TV/Fire TV
  320x180 cover as opaque RGB instead of RGBA. Expanded the generated preview
  to show square, round, adaptive-composite, TV-cover, and in-app contexts with
  exact dimensions and image modes.
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

## Generator 1.6.9

- Kept the high-resolution TV square icon and restored the physically proven
  Fire OS 7 banner resource placement.

## Generator 1.6.8

- Added distinct TV square-icon and 16:9-banner outputs for sideloaded Fire TV
  and normal Android TV/app-store launcher behavior.

## Generator 1.6.7

- Restored the physically proven unqualified Fire TV banner placement while
  retaining the supersampled sharp render; removes stale xhdpi experiments.

## Generator 1.6.6

- Added the density-qualified, supersampled Android TV/Fire TV cover contract.

## Generator 1.6.5

- Emits an opaque RGB Android TV/Fire TV cover and a context-aware preview.

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
