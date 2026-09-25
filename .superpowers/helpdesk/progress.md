# SCI Helpdesk implementation — approved conversation plan

Ruling: Work in the requested checkout on codex/helpdesk-mvp. Repository is unborn and all app files are untracked; an isolated worktree would omit them. Preserve the user's existing index.
Preflight: dynamic definitions feed iommi forms, immutable snapshots feed ticket display; ticket queryset permissions also govern comments/downloads; one filtered queryset feeds all report sections.
Tests written first: initial 10 integration tests fail because the helpdesk models do not yet exist.
Tasks: models/uploads; forms/routes/admin; styles/templates; migrations/tests; browser QA; fresh review and documentation.

Completed: models, allowlisted iommi forms, protected uploads, portal, Unfold configuration/tickets/reports, auth seam, starter migrations, run script and README.
Validation: 19 focused tests pass (6.575s final run); Django check clean; makemigrations --check --dry-run clean; fresh file-backed SQLite migrated with Category3/Type3/User0/Ticket0/Attachment0.
Independent review found partial-storage cleanup and test storage isolation defects; both fixed and review follow-up passed. Browser found required=False rendering as an HTML attribute; fixed shared field style and added rendered-HTML regression.
Browser proof: saved admin field definition -> preview -> employee request with diagnostic.txt -> IT assignment/In progress + public reply + internal note -> employee sees only public reply and sends text-only reply without status change. Reports total1/open1/unassigned0/finished0; Resolved filter all zeros.
Fidelity ledger: official SCI artwork replaces generated approximation; local Lato/red/white preserved; portal two-column form with guide and steps matches concept structure; native file chooser/dropdown prompt retained for accessibility/configurability; Unfold sidebar/account controls retained; reports keep filtered metrics/two breakdowns/matching table. Desktop1536x1024 and mobile390x844 inspected, mobile scrollWidth375 within390; keyboard focus outline and native validation checked; console warnings/errors empty. Mobile stacks fields and report counters. Screenshot capture fullPage is unreliable in this browser (oversized duplicate canvas), so evidence uses viewport captures; desktop may need a short vertical scroll to footer.
Evidence: C:/Users/bmacl/.codex/visualizations/2026/09/23/01a0cbad-d5fb-7253-83a6-7db30d7f55fe/helpdesk-{form,reports}-desktop.jpg and helpdesk-{form,reports,ticket}-mobile.jpg.
