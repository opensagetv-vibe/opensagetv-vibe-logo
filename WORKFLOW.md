# Common project workflow

The only host prerequisite is Docker (plus Git for source management). Use
`dev.cmd` on Windows or `./dev.sh` on Linux/WSL with `test`, `validate`,
`build`, `install`, or `all`.

The commands use `opensagetv-vibe-build-env:u26-j11` and the single reusable
`opensagetv-vibe-dev` container. `build` regenerates all assets; `install`
copies and SHA-verifies them in the sibling Android client. Android test,
validate, build, bundle, and all commands synchronize the logo first.

Put update ZIPs in `artifacts/downloads`, run `update.cmd`/`update.sh`, and use
`create_ai_handoff_zip.cmd` for the standard verified handoff package.

