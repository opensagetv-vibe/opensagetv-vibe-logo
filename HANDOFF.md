# Handoff

This repository is the canonical source for OpenSageTV Vibe product artwork.
It was migrated intact from the workspace-level `SageTV_Android_Logo_Generator`
directory, which no longer serves as a build input. Generator source version
is 1.6.4; repository workflow version is in `release.properties`.

Authoritative inputs are `SageTV_VIBE_512_V3.svg`, `sagetv_logo.ini`,
`sagetv_logo_generator.py`, and `M_PLUS_Rounded_1c/`. Output under `generated/`
is disposable. The pipeline installs 25 validated resources into the Android
client and writes `config/logo-assets.sha256` there for provenance.
The former Android `branding/SageTV-Vibe.png` is preserved only as
`reference/SageTV-Vibe-legacy.png` and is not authoritative.

The unified image owns Python, CairoSVG, Pillow, libcairo, fontconfig, and all
validation dependencies. No old workspace path or host Python is required.
The intended remote is `https://github.com/opensagetv-vibe/opensagetv-vibe-logo`.
