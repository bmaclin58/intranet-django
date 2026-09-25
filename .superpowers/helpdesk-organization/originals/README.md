# SCI IT Helpdesk

Server-rendered Django + iommi employee forms and Unfold administration. The existing dependency versions are retained: 
Django 6.1.1, iommi 7.32.2, django-unfold 0.107.0. No new Python or frontend dependencies.

## Run locally

The initial migrations have been applied to the workspace SQLite database.
It contains the three starter request forms, **no users and no tickets**.

Select `C:\Programing Projects\djangoIntranet\.venv\Scripts\python.exe` in PyCharm and run `intranet/run_helpdesk.py` 
with no arguments. The host and port are editable constants at the top. Open:

- Employee portal: <http://127.0.0.1:8000/helpdesk/>
- Administration: <http://127.0.0.1:8000/admin/>
- Reports: <http://127.0.0.1:8000/admin/helpdesk/ticket/reports/>

Create the first administrator interactively in PyCharm's terminal; no default password is installed:

Open **View → Tool Windows → Terminal** (Alt+F12), using PowerShell. The ordinary Run console can lack the interactive TTY Django needs, causing account creation to be skipped. Run the command below from the repository root, then enter your username, email, and password at the prompts. Password entry does not echo characters.

```powershell
& '.\.venv\Scripts\python.exe' intranet/manage.py createsuperuser
```

For a fresh checkout, apply migrations first:

```powershell
& '.\.venv\Scripts\python.exe' intranet/manage.py migrate
```

This is the existing project's local-development configuration. Before deployment, configure a private production
SECRET_KEY, DEBUG=False, allowed hosts, HTTPS/session security, static serving, and private upload backups. 
Do not publish the development server. Keep the private upload folder outside every public web-server/static/media
mapping, and configure the reverse proxy's request limit to accommodate at most five 10 MB files plus multipart overhead.
File checks are basic type validation, not malware scanning.

## Accounts and permissions

Use Django admin Users and Groups. Employees need an active account; 
they do not need `is_staff` or helpdesk model permissions. They can submit requests and view/reply/download only 
within their own tickets.

Create an **IT agents** group with these helpdesk permissions, and give its members Staff status:

- Ticket: **view**, **change**.
- Ticket comment: **view**, **add**. Existing comments are read-only.
- Ticket attachment: **view**, **add**. Add public files through the ticket's **Open public conversation / attach files** link.
- **Can view helpdesk reports**, when reports are needed.

Form administrators additionally need **view/add/change/delete** for Category, Ticket type, and Ticket field. 
Give account-management permissions only to people who should manage users and privilege assignments. Superusers already have all permissions. Staff status alone grants no ticket access; no group memberships are assigned automatically.

Unfold is kept in the approved light theme, including browsers that previously remembered auto/dark. Logout is POST-only.
Accounts/passwords are managed by administrators; password-reset email delivery is outside this MVP.

## Create and change request forms

1. Under **Categories**, create a category with its name, description, position, and Active flag.
2. Under **Ticket types**, add a type in that category and save it.
3. Add **Ticket fields** inline: label, field type, required, help text, choices, position, and Active.
4. Enter dropdown/multiple-choice options one per line. Options must be unique; there may be 1–100 options of up to 200 characters. A required checkbox must be checked.
5. Save, then select **Preview saved form**. Preview does not submit tickets and also works for inactive definitions.
6. Activate the category/type when ready. Employees choose a request under **New ticket**.

Core fields (subject, description, priority, attachments) are shared by all forms. Dynamic fields support short/long text, 
email, integer, decimal, date, checkbox, dropdown, and multiple choice. Position orders fields; ties use creation order. 
Required dropdowns begin with an empty prompt rather than silently selecting the first answer. There are no conditional
rules or arbitrary executable validators.

Starter forms: Hardware → Computer problem, Software → Software issue, Access → Access request. The generic
On-site/Remote/Other location choices are editable. Access requests only create tickets; they do not provision permissions.

Edits apply to new submissions. Existing tickets retain original category/type labels and a snapshot of each submitted 
custom field's label, type, choices, and answer. Ticket answers are read-only in both interfaces. If a form changes 
while someone is filling it in, submission is rejected with an explanation; review the updated fields and re-select
attachments before retrying. Deactivate used categories/types instead of deleting them. Ticket history and related user 
records are protected from cascading deletion.

## Work tickets

The IT ticket list supports search, category/type/status/priority/assignee filters, and date navigation. On a ticket,
set status, priority, and assignee; add a conversation inline with Internal unchecked for an employee-visible reply or
checked for a staff-only note. Only active staff with ticket-change permissions appear as assignees. Existing conversation 
entries cannot be edited or deleted in this interface.

Employees see current status, original answers, attachments, and public replies. They can reply with text, files, or both.
Replies update the activity timestamp without overwriting concurrent status or assignment changes. Replies never reopen or
otherwise change status automatically. Admin status changes are recorded in Django's history. Resolved/closed timestamps 
reflect the current resolution cycle and clear when reopened.

Uploads accept PNG, JPG/JPEG, PDF, UTF-8 TXT, DOCX, and XLSX, up to five files per submission/reply and 10 MB per 
nonempty file. Macro-enabled Office containers are rejected. Files use generated names under `intranet/private_uploads/`; 
original display names are retained separately. Downloads require authorization and use attachment disposition, 
octet-stream content type, no-store, and nosniff. There is no public media route. Failed saves remove newly written files, 
including interrupted partial writes. Back up SQLite and the private file directory together.

## Reports

The dedicated report permission and ticket-view permission are both required. Filters use **ticket creation date**, 
inclusive in America/New_York, plus category and status. Every counter, breakdown, and table uses the same filtered tickets:

- Total tickets: all matching tickets.
- Open tickets: New, In progress, or Waiting.
- Unassigned open: matching open tickets with no assignee.
- Resolved or closed: matching tickets in either terminal status.

Breakdowns group by category and current status. The matching-ticket list has 25 rows per page. 
Invalid filters display errors and no results. This foundation has no SLA, trend, historical-status, or time-to-resolution 
claims. Renamed categories use current names in report groupings; individual tickets retain submission labels.

## Microsoft Entra SSO seam

Django accounts are the sole enabled identity provider. Ticket relationships use `settings.AUTH_USER_MODEL`, 
user lookups use `get_user_model()`, and application access is tied to authenticated users and Django permissions rather
than an email domain or provider.

For the future integration: choose a supported Entra/OIDC Django authentication package, register the application and 
callback URI in the intended tenant, configure issuer/client/secret outside source control, and add the provider at the
centralized account routes/authentication backend settings. Validate tenant, issuer, audience, nonce, and state with the 
provider library. Map a verified stable identity (issuer/subject or tenant/object ID) to an existing local user through
an explicit verified linking process; never auto-link by a matching email address alone. Define provisioning, 
deprovisioning, group-to-permission mapping, and break-glass local-admin policies before enabling SSO. No dormant 
callbacks, secrets, provider package, or Microsoft button are included.

## Verification

Validated: 19 Django tests pass; Django checks are clean; no missing migrations. A fresh file-backed SQLite database 
migrates successfully and contains only three starter categories/types, with zero users, tickets, or attachments.

Browser checks covered configuration and preview, employee submission with a file, IT assignment/status/public 
reply/internal note, employee tracking and text-only reply, and populated/empty reports. Desktop (1536�1024) and mobile (390�844) layouts were inspected; native required validation, visible keyboard focus, associated labels, and server error messages were checked. No browser console warnings/errors were captured. Browser testing used an isolated disposable database, never the workspace data.

Run from the repository root:

```powershell
& '.\.venv\Scripts\python.exe' intranet/manage.py test helpdesk
& '.\.venv\Scripts\python.exe' intranet/manage.py check
& '.\.venv\Scripts\python.exe' intranet/manage.py makemigrations --check --dry-run
```

Tests use a separate database and patch the model's actual file storage to a temporary directory. They cover field parsing, 
required inputs, forged values, stale definitions, historical snapshots, ownership, internal notes, staff permissions,
CSRF/logout, valid and invalid files, partial writes, rollback cleanup, admin changes, concurrent replies, and 
report filters/counts/local dates.

Brand assets: SCI's public SVG from `https://standardcal.com/cdn/shop/files/SCI-favicon.svg` (viewBox tightened around 
the existing artwork; paths unchanged). Lato Regular/Bold/Black from Google Fonts, bundled locally under the included 
SIL Open Font License. The mockup's approximate SCI mark is deliberately replaced by the official artwork, and native 
Unfold controls remain in administration.

Deferred: Microsoft SSO activation, conditional forms, automated approvals, email notifications, SLAs, advanced reporting, 
and production hosting.
