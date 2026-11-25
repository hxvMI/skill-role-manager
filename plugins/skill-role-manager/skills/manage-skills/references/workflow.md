# Local package workflow

Python 3.10+ required. Run the bundled script directly, substituting actual paths. Target must be an existing owner-controlled directory. This version supports skill-only plugins, optionally with acknowledged local code; no hooks, MCP integrations, downloads or archive extraction. Extract trusted review packages yourself before validation. Hashes detect corruption/changes, not publisher authenticity.

```text
python manager.py validate --source PACKAGE
python manager.py plan --source PACKAGE --target TARGET
python manager.py register --source PACKAGE --target TARGET --apply --plan-digest REVIEWED_DIGEST
python manager.py list --target TARGET
python manager.py unregister --id PACKAGE_ID --target TARGET
python manager.py unregister --id PACKAGE_ID --target TARGET --apply --plan-digest REVIEWED_DIGEST
python manager.py rollback --target TARGET --transaction TRANSACTION_ID --apply
python manager.py recover --target TARGET --apply
```

Repeat --grant PERMISSION on plan and apply for each permission the owner actually authorizes. Package code requires the local-code grant; it is copied but never executed by the manager. A skills-only instruction pack normally declares no new executable permissions, although instructions themselves can request work subject to the host's existing authorization.

manager.json is schema 1, separate from native plugin.json. It contains exact identity/version, permissions, exact-version dependencies and SHA-256 file inventory (excluding manager.json itself). Unknown schemas/fields and unsupported host components fail closed. Use tools/seal_packages.py in the source repository to seal reviewed built-in packages; never reseal untrusted changes merely to bypass a failed hash. No semantic-version ranges or automatic dependencies in v0.1.

Dry runs make no target writes. Apply checks the exact source and catalog state again; changed plans require renewed review. Same-version changed content is refused; use a new version. Managed source modifications are refused rather than overwritten. Existing unrelated marketplace entries/fields are retained. Concurrent writers are locked; concurrent hostile filesystem modification is outside this owner-controlled local tool's threat model.

Immutable revisions are stored under TARGET/plugins/ID/VERSION/DIGEST. Transaction journals and historical catalog snapshots are under TARGET/.skill-role-manager. A failure before catalog replacement leaves the old registration; a failure after commit leaves a pending journal. New writes stop until explicit recovery. Recover restores the pre-transaction catalog only if current state is exactly its before/after snapshot. Rollback likewise refuses later catalog drift. This is a local process interruption recovery model, not a guarantee against hardware/filesystem loss; keep external backups.

Unregister removes only the managed catalog entry and checks reverse dependencies. Historical sources remain; actual host-installed copies and caches are unchanged. To stop an already installed plugin, use the host's own disable/uninstall controls. Do not call unregister native uninstallation. Old folders are intentionally not automatically deleted.

After registration: use the supported desktop local/repo marketplace flow to discover the catalog, restart only when ready, then install the desired plugin in the plugin interface and test in a new chat. Exact visibility depends on surface/version/workspace policy. Do not claim native activation until it is observed. Public web hosting, remote MCP, autonomous agents and ChatGPT Project file editing are not provided.

Official host contract reviewed during development: https://developers.openai.com/plugins/build/plugins and https://developers.openai.com/plugins/build/skills. Package management code enforces this deliberately smaller subset, not the full upstream plugin schema.
