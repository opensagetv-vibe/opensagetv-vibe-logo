# OpenSageTV Vibe Logo

This repository owns the canonical OpenSageTV Vibe SVG artwork and generates
all launcher, adaptive-icon, banner, and in-app resources required by
`opensagetv-vibe-android-client`.

It is the future `opensagetv-vibe/opensagetv-vibe-logo` subproject. Generated
files are reproducible build output, not editable source.

## Build and install

With Docker running and the sibling unified build-environment and Android
client projects checked out, run `dev.cmd all` on Windows or `./dev.sh all` on
Linux/WSL. The one shared development container regenerates and validates 25
Android resources, copies them to the correct Android resource directories,
and verifies every copied SHA-256. The normal Android build does this step
automatically.

Outputs include the 512x512 Play Store icon, five legacy and round launcher
densities, adaptive foreground/background layers and XML, the 320x180 TV
banner, and the 320x150 in-app logo.

## Editing and licensing

Edit `SageTV_VIBE_512_V3.svg` or `sagetv_logo.ini`, not generated PNG/XML.
The bundled M PLUS Rounded 1c font is loaded through a private Fontconfig setup,
so rendering does not depend on host fonts. Its SIL Open Font License is in
`M_PLUS_Rounded_1c/OFL.txt`. CairoSVG is an LGPL build tool and is not embedded
in the generated images.

`reference/SageTV-Vibe-legacy.png` is the former Android-only raster source,
retained solely for visual comparison. It is not a build input.
The superseded host-Python/font-install Windows helpers are similarly retained
under `reference/legacy-windows-host-workflow/`; supported Windows use is
`dev.cmd`, which keeps all renderer dependencies inside Docker.
