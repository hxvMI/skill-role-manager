# Skill and Role Manager

**Version 0.1.0 — preview**

Validate local skill packages, review their permissions, and register them in a marketplace that supported ChatGPT desktop clients can use. Keep previous registrations recoverable when updating or removing a package.

The repository includes two separately installable plugins:

| Plugin | What it provides |
|---|---|
| **Skill and Role Manager** (`skill-role-manager`) | A management skill and a Python tool for validation, planning, registration and recovery. |
| **Building Practices** (`building-practices`) | Eight candidate development skills and four single-session role definitions. Optional; install it only if you want those procedures. |

## Understand the three steps

1. **Add a marketplace:** tell the host where a catalog of available plugins lives.
2. **Install a plugin:** select a catalog entry in the host's Plugins interface.
3. **Use a skill:** select the installed plugin in a supported chat and request a task.

These are separate actions. A successful package validation or marketplace registration does not prove the plugin is installed or that a skill was used.

The bundled manager prepares local registrations. The host's Plugins interface performs actual native installation. An “agent role” is a set of instructions for the current conversation; this project does not launch independent or autonomous agents.

## Requirements

- A desktop ChatGPT/Codex surface that supports local plugin marketplaces. Availability depends on the application version and workspace policy.
- The Codex CLI, with `codex plugin marketplace` commands available, for the setup route shown below.
- Python **3.10 or newer** to run the management tool.
- Local filesystem access to extracted packages and the selected target folder.

The tool uses Python's standard library. It needs no API key, hosted server, telemetry service or third-party Python package. Host subscriptions, feature access and external CLI setup are separate prerequisites.

Check your commands in a local terminal:

```powershell
python --version
codex --version
codex plugin marketplace --help
```

On Windows, `py -3` may be available instead of `python`. If you substitute it, do so consistently. If `codex` is not recognized, install/configure the official CLI before continuing. See the [official Codex CLI guide](https://developers.openai.com/codex/cli).

This preview does not manage browser-only ChatGPT files, upload sources to ChatGPT Projects, edit project instructions, install packages through an undocumented account API, or manage hosted agent runtimes.

## Quick start: install the included plugins

All paths below are fictional examples. Replace them with your actual extracted folder. Do not include a trailing backslash after a closing quote.

### 1. Download and extract

Download the repository ZIP using GitHub's **Code → Download ZIP**, or use a release ZIP if one is provided. Extract the entire archive to a stable folder, for example:

```text
D:\AI-Tools\Skill-Role-Manager\
├── README.md
├── LICENSE
├── .agents\
│   └── plugins\
│       └── marketplace.json
├── plugins\
│   ├── skill-role-manager\
│   │   ├── plugin.json
│   │   ├── manager.json
│   │   ├── .codex-plugin\plugin.json
│   │   └── skills\manage-skills\...
│   └── building-practices\...
├── tests\
└── tools\
```

Keep hidden folders such as `.agents` and `.codex-plugin`. Select the folder that directly contains `README.md`, `plugins` and `.agents`, not an extra outer extraction folder. Keep that folder in place while using it as a local marketplace source.

### 2. Add the marketplace

Open **PowerShell on your computer** and run:

```powershell
codex plugin marketplace add "D:\AI-Tools\Skill-Role-Manager"
```

The command is **`plugin`**, not `plug`. A successful response should identify the `skill-role-tools` marketplace and its local root. Confirm the source is listed:

```powershell
codex plugin marketplace list
```

This adds a catalog; it does not install either plugin. The setup uses the host's documented [local marketplace mechanism](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

### 3. Install through the plugin interface

Restart the desktop app when convenient if required for the new source to appear. Open **Plugins**, find the **Skill and Role Tools (Preview)** local source, and install:

- **Skill and Role Manager** for package management.
- **Building Practices**, optionally, for the eight included procedures.

The interface may show technical names such as `skill-role-manager`. Labels and source visibility can vary by host version. If the source is unavailable, check platform/workspace support; do not assume repeated file copying will activate it.

### 4. Verify the manager with a read-only request

Start a fresh supported chat and explicitly select the installed manager plugin using the host's plugin selector. Ask:

> Use manage-skills to validate `D:\AI-Tools\Skill-Role-Manager\plugins\building-practices`. Run only the bundled manager.py validate command. Report the actual output. Do not register, install, update, reseal, modify files or use --apply. If local execution is unavailable, say so.

Successful validation reports:

```json
{
  "id": "building-practices",
  "version": "0.1.0",
  "permissions": [],
  "dependencies": {},
  "digest": "<SHA-256 digest of the actual package>"
}
```

The exact digest depends on the downloaded revision. Exit code `0` means validation succeeded; the tool returns `2` for handled errors. Require actual command output, not just a proposed plan.

If the chat cannot execute local Python, run the command yourself:

```powershell
Set-Location "D:\AI-Tools\Skill-Role-Manager"
python -B plugins/skill-role-manager/skills/manage-skills/scripts/manager.py validate --source plugins/building-practices
```

### 5. Try an included skill

If you installed Building Practices, select it in a fresh supported chat and ask:

> Use Session Handoff to draft a handoff for a fictional unfinished task. Include one failed check and one pending decision. Return it in chat only; do not modify files. Clearly label all fictional results as simulated.

Inspect the answer: it should retain the unresolved failure and decision without claiming real tests, edits or saves. A plausible answer alone does not prove native routing; check the host's skill-selection evidence when available. This is a smoke test, not certification of effectiveness.

## Manage a new package: complete fictional example

Suppose someone gives you an extracted, reviewed package:

```text
D:\Reviewed-Packages\research-helper\
├── plugin.json
├── manager.json
├── ROLES.md
└── skills\source-checker\SKILL.md
```

`source-checker` is a skill. `ROLES.md` describes a Research Reviewer role that uses it. Neither file launches an independent agent.

The package must meet the manager's supported format; an arbitrary folder containing only Markdown is not sufficient. See “Package authors” below.

### 1. Choose a separate managed target

Use an existing folder you control. For this example, create a fresh dedicated folder:

```powershell
New-Item -ItemType Directory -Path "D:\Managed-AI-Plugins"
```

If it already exists, inspect it instead of replacing or clearing it. **Do not use the downloaded repository's own marketplace as the managed target.** Its bundled entries are bootstrap sources, not registrations owned by this tool.

Prepare convenient PowerShell variables:

```powershell
$managerScript = "D:\AI-Tools\Skill-Role-Manager\plugins\skill-role-manager\skills\manage-skills\scripts\manager.py"
$sourcePackage = "D:\Reviewed-Packages\research-helper"
$managedTarget = "D:\Managed-AI-Plugins"
```

### 2. Validate, then plan

```powershell
python -B "$managerScript" validate --source "$sourcePackage"
python -B "$managerScript" plan --source "$sourcePackage" --target "$managedTarget"
```

These commands do not write to the target. Review the returned package identity/version, `source_digest`, target, permissions, dependencies, `catalog_after` and `plan_digest`.

If permissions are required, stop and decide whether you actually authorize them. For example, a package declaring `local-code` requires that grant on both planning and applying:

```powershell
python -B "$managerScript" plan --source "$sourcePackage" --target "$managedTarget" --grant local-code
```

Use every required grant consistently on both commands. Grants are acknowledgements, not a sandbox. The manager copies imported code but never executes it. Later host actions remain subject to the host's permissions and the user's authorization.

### 3. Apply only the reviewed plan

Replace the placeholder with the actual `plan_digest` from your reviewed output:

```powershell
python -B "$managerScript" register --source "$sourcePackage" --target "$managedTarget" --apply --plan-digest "PASTE_REVIEWED_PLAN_DIGEST"
```

Add the same approved `--grant` options if needed. Do not copy `source_digest` into `--plan-digest`; they are different values. If the source or catalog changed, the old plan is refused. Review a fresh plan rather than bypassing the error.

A successful registration returns a transaction ID. Keep it for rollback. The target now contains a native marketplace entry, immutable source revision and local transaction history.

### 4. Add the new target to the host and install

For the first package in this separate managed target:

```powershell
codex plugin marketplace add "D:\Managed-AI-Plugins"
```

Find that source in the host's Plugins interface, install `research-helper`, and test Source Checker in a fresh chat. A newly created managed catalog defaults to the technical name `skill-role-local`; if you manage an existing catalog, its name is preserved.

Example request after actual installation:

> Act as Research Reviewer and use Source Checker to assess these three claims. Return evidence and uncertainty in chat. Do not edit files or contact anyone.

This completes the intended workflow: **validate → review plan → register → host install → verify use**. Role names still describe conversation responsibilities.

## Common operations

The variables in these examples are from the fictional example above.

### List registered entries

```powershell
python -B "$managerScript" list --target "$managedTarget"
```

This lists catalog entries, not the host's installed-plugin state. Use the host UI to check installation/enablement.

### Update a package

Obtain a reviewed new version, for example `research-helper` `0.2.0`. Validate and plan that new source, then apply its reviewed digest using the same `register` workflow. Required dependencies must already be registered at the exact declared versions. The tool will not download or install them for you.

Identical content is a no-op. Changed content under the same version is refused; the package author must increment the version and regenerate reviewed integrity metadata. Modified managed copies are refused instead of overwritten. Updates that would break registered dependents are also refused.

After registration changes, refresh/restart and update the native installation using the supported host workflow. A changed source catalog does not prove the installed host copy has refreshed.

### Remove a registration

First obtain and review a removal plan:

```powershell
python -B "$managerScript" unregister --id research-helper --target "$managedTarget"
```

Then apply its exact returned digest:

```powershell
python -B "$managerScript" unregister --id research-helper --target "$managedTarget" --apply --plan-digest "PASTE_REMOVAL_PLAN_DIGEST"
```

This removes the managed catalog entry only. Historical source folders remain, and installed host copies/caches are unchanged. Use the host's own disable/uninstall controls to stop or remove an already installed plugin. A registered dependent prevents removal.

### Roll back a transaction

Use the transaction ID returned by a successful registration/removal:

```powershell
python -B "$managerScript" rollback --target "$managedTarget" --transaction "PASTE_TRANSACTION_ID" --apply
```

Rollback restores the previous exact catalog snapshot and retains source history. Later catalog edits can block rollback to protect newer work. It does not roll back the host's cache or installed state; reconcile those through the host UI separately.

### Recover an interrupted operation

If the manager reports a pending transaction, stop new changes. Once any active writer has stopped, review recovery scope and run:

```powershell
python -B "$managerScript" recover --target "$managedTarget" --apply
```

Recovery restores the pre-transaction catalog only when its current bytes match the recorded before/after state. Unexpected later edits cause a refusal. A stale writer lock may require manual attention, but **do not delete a lock while a writer may still be active**. See [SECURITY.md](SECURITY.md) before intervening.

## What about ordinary ChatGPT Projects?

Native plugins and uploaded project sources are different mechanisms.

| Destination | Current workflow |
|---|---|
| Supported desktop native plugins | Add marketplace, install in host UI, then verify skill use. |
| ChatGPT Project uploaded sources/instructions | Manually upload selected reference files and edit project instructions. This tool does not automate those steps. |
| Independent/autonomous agent runtime | Not supplied by this project. Roles are instructions within a conversation. |

For a reference-only project, upload the relevant skill and role Markdown, or a combined reference document, and explicitly request that the assistant follow it. Keep existing project rules. Do not upload manifests expecting them to install plugins or copy the whole repository into project instructions.

## Package authors: supported format

The manager accepts a deliberately limited subset of native skill-based plugins:

- Native root `plugin.json` using the documented portable schema, stable kebab-case name, semantic version and description.
- At least one `skills/SKILL-NAME/SKILL.md` with matching `name` and a nonempty `description` in frontmatter.
- Optional compatible `.codex-plugin/plugin.json` overlay.
- Separate **schema 1** `manager.json` with matching identity/version, explicit permissions, exact-version dependencies and a SHA-256 inventory of every other package file.
- No symlinks/junctions, escaping paths, ambiguous case collisions, oversized packages or unsupported active integrations.

Hooks, MCP server/app wiring and plugin extensions are refused by this preview manager. It does not implement the entire upstream plugin specification. Only local extracted directories are accepted; remote downloads and automatic archive extraction are not implemented.

For a package you author inside this repository's `plugins` directory, the authoring sequence is:

1. Review its actual contents and permissions.
2. Set matching native/compatibility manifest versions.
3. Add an empty or appropriate permissions/dependency declaration through the sealing workflow. The current sealing helper is tailored to this repository's built-in packages: it assigns the manager's two permissions by name and empty permissions/dependencies to other packages. **For custom executable or dependent packages, author/review manager.json explicitly; do not rely on that helper to infer permissions or dependencies.**
4. Seal reviewed built-in packages with `python -B tools/seal_packages.py`, or generate the exact file hashes for your custom manager.json using your own reviewed authoring process.
5. Run `validate` on the resulting package before sharing.

Inspect the included `manager.json` files for the exact format. They are manager-specific metadata, not the upstream native manifest. Never reseal unknown or unexpectedly modified content merely to clear a hash error. Hash consistency proves integrity against that inventory, not authenticity, security or useful behavior.

## Troubleshooting

| Symptom | What to do |
|---|---|
| `codex` or `python` is not recognized | Check installation and PATH in a local terminal. A chat execution-helper failure is not proof the command or package is broken. |
| Source folder not found | Confirm you extracted the ZIP and selected the correct root. Quote paths containing spaces. |
| Marketplace added, no plugin installed | Open Plugins and install the desired entry; registration alone is insufficient. |
| Source not visible in Plugins | Confirm `codex plugin marketplace list`, host support and workspace policy; restart when appropriate. |
| Chat returns another plan instead of validation output | Explicitly request only `manager.py validate`; require an actual exit code/output or a disclosed inability to execute. |
| Missing grant/dependency | Review and authorize only necessary permissions; separately register exact required dependencies. No automatic downloads. |
| Plan changed | Review a fresh plan; don't substitute a digest or force an overwrite. |
| Hash mismatch/managed content modified | Preserve edits, compare to the intended source and stop. Do not reseal to hide unexplained changes. |
| Pending transaction or writer lock | Stop concurrent work, inspect state and follow the recovery guidance. |
| No effect on ChatGPT Project sources | Expected: uploads and project instructions are outside this native manager's scope. |

## Validation status and limitations

Local regression suite: **18 tests, 17 passed and 1 skipped**. The real symlink-creation test was skipped because that development environment did not permit it; a simulated guard check is not a substitute. Real CLI demonstration and isolated ZIP-extraction retest also passed. See [VALIDATION.md](VALIDATION.md) for scope, failures corrected and remaining limits.

A user-reported Windows smoke test subsequently confirmed marketplace addition and execution of the installed manager's read-only validation command. A fictional handoff response was also supplied, but response text alone does not establish native selection of the handoff skill. These observations are not independent validation or proof of broad host compatibility.

No independent security audit, general effectiveness claim, automatic agent execution, Linux/macOS runtime certification or unattended production readiness is claimed. The manager uses owner-controlled local folders and is not a sandbox against malicious packages or hostile concurrent filesystem changes. Keep backups and review imported instructions/code before host installation.

## Tests and license

From the repository root:

```powershell
python -B -m unittest discover -s tests -v
python -B tools/demo.py
```

Tests and the demo use disposable directories. They do not install native plugins or modify your live host configuration.

Source is provided under the [MIT License](LICENSE). Read [SECURITY.md](SECURITY.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before extending the permission model. Public GitHub availability does not mean inclusion in OpenAI's public plugin directory; those are separate distribution routes.
