# Handoff

This repository is the canonical source for OpenSageTV Vibe product artwork.
It was migrated intact from the workspace-level `SageTV_Android_Logo_Generator`
directory, which no longer serves as a build input. Generator source version
is 1.8.0; repository workflow version is in `release.properties`.

Authoritative inputs are `SageTV_VIBE_512_V3.svg`, `sagetv_logo.ini`,
`sagetv_logo_generator.py`, and `M_PLUS_Rounded_1c/`. Output under `generated/`
is disposable. The pipeline installs 29 validated resources into the Android
client and writes `config/logo-assets.sha256` there for provenance. The single
Android client APK owns its launcher resources; the failed companion-launcher
experiment was removed.
The former Android `branding/SageTV-Vibe.png` is preserved only as
`reference/SageTV-Vibe-legacy.png` and is not authoritative.
Adaptive icons use visible foreground artwork over an opaque dark-blue
background. The pipeline rejects a fully transparent foreground; this protects
launchers that resolve or cache only the adaptive foreground layer.
Legacy/Fire TV square icons use an 80-percent inset and adaptive foregrounds
use a 60-percent inset. These values keep the full SageTV Vibe wordmark inside
the API-30 Fire OS rounded mask rather than clipping its left/right edges.

The unified image owns Python, CairoSVG, Pillow, libcairo, fontconfig, and all
validation dependencies. No old workspace path or host Python is required.
The TV cover must remain an opaque RGB PNG at
`android-tv/src/main/res/drawable/banner_v2.png`. To match the working client,
the TV module must not own duplicate `mipmap-*` launcher icons: its standard
launcher inherits the shared icon and its Leanback activity explicitly uses
the TV banner. Sharpness comes from the 2048px vector supersample and one
reduction. Required Amazon 114x114/512x512 tablet icons, the opaque 1280x720
Fire TV app icon with critical artwork inside its 882x448 safe area, and the
title-free opaque 1920x1080 Fire TV background are generated under
`source/dev/android-tv/store-assets/`. They must be uploaded with an
eventual Amazon Appstore submission and are not APK resources. The remaining
store-art gate is three to ten reviewed, genuine 1920x1080 app screenshots.
Fire OS launcher validation must use a clean Dev-package install because
update installs retain stale icon resources. The application and standard
launcher use the shared square/adaptive icon; the Leanback activity uses the
320x180 resource as icon, banner, and logo, matching the known-good APK.
The intended remote is `https://github.com/opensagetv-vibe/opensagetv-vibe-logo`.
