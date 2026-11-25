# Contributing

Keep changes scoped and establish observable requirements/scenarios before implementation. Run the regression suite and CLI demo in disposable directories. Preserve failing observations and label simulated versus real integration checks. Document changes to manifest schema, permissions and rollback compatibility before implementation.

Do not commit credentials, local state/history, user project records, trial captures or machine-specific paths. Do not add automatic execution of imported package code or lifecycle hooks to the existing permission model. Those features require a separate threat model and owner-reviewed scope. Unknown schema versions must fail closed until an explicit migration is implemented and tested.

Use semantic versions for package changes; schema versions are separate. Native plugin source availability is not discovery/invocation evidence. Actual supported-host integration must be tested before advertising that support as verified. No GitHub repository, issue endpoint or maintainer identity is assumed in this source candidate.
