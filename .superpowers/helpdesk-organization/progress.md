# Helpdesk organization - user-approved in-chat plan

1. Add package compatibility and admin access regression checks.
2. Split models/forms and staff views, preserving existing edits.
3. Expand README with complete file guide and diagrams.
4. Run suite, migration checks, preservation checks, and independent review.

Working directly in the existing codex/helpdesk-mvp checkout to preserve the user-approved local edits. No commits, new checkout, or dependencies are required by the approved plan. Source snapshots and file hashes are kept here for comparison.

Pre-flight: models package must preserve migration callback imports; forms package exports are used by portal, staff views, and tests. Admin URL wrappers stay in admin.py. Templates and CSS are outside the edit scope.

Package test failed before the split on the missing package boundary; admin access characterization passed. Moved existing definitions without rewriting their bodies, apart from the planned cross-module string relationships. Existing exports and migration callback aliases retained.

Implementation complete: helpdesk suite 21/21 passed; migration dry run detected no changes. README covers all 43 files and local links resolve. Source/data preservation hashes and AST body comparisons passed. Live IDE workspace.xml changed externally; excluded from source preservation assertions. Independent review and fresh file-backed migration smoke check pending.

Fresh file-backed SQLite smoke migration passed with three categories, three types, nine fields, and zero users/tickets/comments/attachments; system check clean. Form style and factory constants are AST-identical to the working-copy originals.

Final review complete: independent reviewer found no actionable issues. Reviewed moved bodies/constants, model discovery, package exports, migration callbacks, admin wrappers, GET-only tests, README descriptions, and protected-file hashes. Browser rendering and prior MVP/production/SSO behavior were outside this behavior-preserving refactor; existing UI files were unchanged and covered by source preservation checks. Verification complete: 21 tests passed, no migration changes, clean system check and fresh SQLite migration, complete guide coverage, and clean git diff --check. All four plan steps complete; no production behavior deviations, commits, or dependency changes.
