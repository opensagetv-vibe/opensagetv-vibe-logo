# OpenSageTV Vibe logo contributor rules

Read `README.md`, `HANDOFF.md`, `TASKS.md`, and `WORKFLOW.md` first. `TASKS.md`
is the sole local backlog. Record changes only in `CHANGELOG.md`; do not create
per-version, prompt, review, or validation notes.

The SVG, INI configuration, generator, and bundled OFL font are authoritative.
Never hand-edit generated Android PNG/XML resources. Generate and install them
through the unified build environment, validate every expected asset and size,
and preserve the M PLUS Rounded 1c license.


## Stock-server test-control policy

- For any new testing, commissioning, diagnostic, or automation control, first
  implement or extend the stock-compatible `opensagetv-vibe-core-MCP-Plugin`
  using supported `sage.SageTV.api`/`apiUI` calls and verify it against an
  unmodified stock SageTV server.
- Do not patch `Sage.jar`, add private MiniClient events, or change Core merely
  to make a test easier. Existing public APIs, the bounded MCP bridge, and
  external test tooling are the required first option.
- Change Core only when the required production runtime behavior cannot be
  expressed through the stock plugin/API boundary. Document the proven API
  gap, keep the extension optional and negotiated with a safe stock fallback,
  and verify older clients and installations remain unaffected.

