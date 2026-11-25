# Validation and release status — 0.1.0 preview

2026-11-25. Windows, Python 3.14; implementation requires Python 3.10+. Author performed review and tests in the originating session; no independent security/effectiveness review performed. Official host documentation consulted: https://developers.openai.com/plugins/build/plugins and https://developers.openai.com/plugins/build/skills. These sources establish package/marketplace design, not successful installation on the user's account.

## Executed

- Standard-library regression suite: **18 tests, 17 passed, 1 skipped**, exit 0. Covers N1–N7: read-only plans, digest consent, explicit grants, exact dependencies, reverse dependency update/unregister protection, preserve unrelated catalog fields, immutable versions, original-state rollback, stale catalog/dirty source refusals, invalid hashes/schema/paths/versions/size/JSON, unsupported integrations, writer locking, injected process interruption before/after catalog commit and explicit recovery.
- Real OS symlink creation was unavailable, so that test is **skipped**, not passed. A separate simulated link-guard test passes; it does not replace a real platform integration test. Denied-write case uses an injected PermissionError, not actual OS access denial.
- Real CLI subprocess demo passes: validate -> read-only plan -> register -> list -> no-op -> unregister -> rollback -> original absent catalog restored. Disposable target only; no user config modified.
- Both built-in packages validate against the manager's documented narrow subset, with exact file inventories and hashes. This is not a claim of full upstream JSON-schema conformance.
- Standard skill metadata validator passes for manager procedure; existing eight skill sources also passed during prior candidate development. Host activation still untested.
- Final source preservation comparison: 168 protected reference/baseline/recovery files unchanged; nested baseline repository clean.

## Failures retained and corrected

Initial regression run failed valid Windows-created SKILL.md fixtures because byte decoding retained CRLF while frontmatter detection required LF. Corrected parsing to accept CRLF/UTF-8 BOM without altering source hashes or acceptance expectations. Full suite rerun passed (14 pass/1 skip initially), then expanded security/recovery checks passed (17 pass/1 skip). One implementation correction cycle; no weakened assertions.

Standard metadata validator initially failed under Windows default cp1252 decoding on a typographic character. Reran with Python UTF-8 mode; passed without changing candidate text or validator. This was a validation-runtime prerequisite correction, not a skill-behavior success by assumption.

## Not verified

H1 native ChatGPT desktop discovery/install/invocation is **not run**. No app restart, global marketplace registration, plugin cache write, account change or public publishing was performed. A compatible local surface and user-controlled installation step are still required. Browser-only remote file management, Linux/macOS runtime, real link/junction abuse, hostile concurrent filesystem mutation, disk/power-loss recovery, independent review and publisher authenticity are not verified. No claim of autonomous agents or measured productivity benefit.

Local candidate acceptance N1–N4/N6–N8 is supported by regression/demo/packaging checks. N5 has passing structural/path/hash checks with real symlink coverage limited as above. Do not mark full host readiness or broad security certification complete. Release remains **preview for final owner review**, not a production-certified native installer.

## Repeat

```text
python -B -m unittest discover -s tests -v
python -B tools/demo.py
```

Do not reseal changed packages just to pass validation. Review actual differences first. After authorizing the native host test, use README steps and record source visibility, install status and a real invocation separately. Stop and report exact error if unavailable; preserve the existing app configuration.
