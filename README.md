# OpenSageTV Vibe Logo

This repository owns the canonical OpenSageTV Vibe SVG artwork and generates
all launcher, adaptive-icon, banner, and in-app resources required by
`opensagetv-vibe-android-client`.

It is the `opensagetv-vibe/opensagetv-vibe-logo` subproject. Generated files are
reproducible build output, not editable source.

## Build and install

With Docker running and the sibling unified build-environment and Android
client projects checked out, run `dev.cmd all` on Windows or `./dev.sh all` on
Linux/WSL. The one shared development container regenerates and validates 29
Android resources, copies them to the correct Android resource directories,
and verifies every copied SHA-256. The normal Android build does this step
automatically.

Outputs include the 512x512 Play Store icon, five legacy and round launcher
densities, adaptive foreground/background layers and XML, the 320x180 TV
banner, the 114x114 and 512x512 Amazon tablet icons, the safe-area-compliant
1280x720 Amazon Fire TV app icon, a title-free 1920x1080 Amazon Fire TV
background, and the 320x150 in-app logo. Amazon submission images are installed
under `source/dev/android-tv/store-assets/`; they are deliberately not
packaged as Android resources.

The Android client is the only APK. The superseded companion-launcher module is
not generated or installed. The TV banner and Amazon catalog artwork are deliberately encoded as opaque
RGB PNGs. A newly sideloaded Fire TV package is represented with its square
APK icon; Amazon supplies the full-width tile from its catalog after store
publication. Legacy square artwork is inset to 80 percent and the
adaptive foreground to 60 percent so the full wordmark survives circular and
rounded-square masks. The generated preview shows those contexts separately
from the full-width banner and catalog art.

The standard Android launcher inherits the shared square application icon.
The Leanback activity assigns the 320x180 resource as icon, banner, and logo,
matching the known-good APK resource topology. Fire OS can retain stale art
across update installs, so physical artwork checks require a clean install.

Amazon also requires three to ten genuine 1920x1080 application screenshots.
Those are intentionally not synthesized by this logo generator: capture them
from a release-candidate build using non-private fixture data, convert them to
opaque 24-bit PNG or JPEG, and review them before submission.

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
