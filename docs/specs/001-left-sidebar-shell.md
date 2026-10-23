# Spec 001: Left Sidebar Shell & Security Operations Console

**Status:** Proposed  
**Author:** Lead Engineer  
**Scope:** Milestone 1  
**Milestone 1 Theme:** Single-window SOC web console driven entirely by a persistent, accessible, role-aware left sidebar.

---

## 1. Goal

Provide a unified, dense, calm, and responsive security-operations web console where all navigation and platform capabilities originate from a persistent left sidebar. A SOC analyst or security administrator works entirely within this single web app: monitoring alerts, hunting in logs, inspecting indicators and watchlists, investigating incidents, managing cases and evidence, downloading compliance reports, tuning detection rules, and managing users and audit records without any secondary navigation bars or hidden menus.

---

## 2. Non-Goals

1. **No Backend API Changes in Milestone 1:** No modifications to FastAPI routes, database tables, SQLAlchemy models, Pydantic schemas, or Elasticsearch query engines. All new views and features will consume existing endpoints (`/api/v1/*`).
2. **No External UI Component Libraries:** No Tailwind, Material UI, Radix, Lucide, or Bootstrap. All layout, styling, and interactivity will adhere to the existing CSS variable system in `frontend/src/styles.css` with clean inline SVG icons.
3. **No Changes to Data Contract or Severities:** `docs/DATA_CONTRACT.md` remains strictly untouched. The severity hierarchy (`critical`, `high`, `medium`, `low`) and color mappings must not be altered.
4. **No Full In-App PDF Viewer:** PDF and Markdown reports are downloaded directly to the analyst's workstation using the existing download infrastructure.
5. **No Server-Side Audit Filtering in Milestone 1:** Server-side `?user=` and `?action=` query parameters are deferred to Milestone 2; Milestone 1 audit filtering operates client-side over the fetched recent $N$ entries ($N \in \{200, 500, 1000\}$).

---

## 3. User Roles & Permission Hierarchy

The platform defines a strict three-tier role hierarchy:
$$\text{viewer} < \text{analyst} < \text{admin}$$

| Role | Access Level | Permitted Navigation & Routes |
|---|---|---|
| `viewer` | Read-only observation | Monitor (`Overview`, `Alerts`, `Incidents`), Hunt (`Hunt`, `Indicators`, `Watchlist`), Investigate (`Cases`, `Reports`), Detect (`Detections`). |
| `analyst` | Triage, search, triage mutation, cases | All `viewer` pages + incident/case creation, evidence attachment, IOC lookup/refresh, watchlist addition/removal, manual detection runs. |
| `admin` | Full operational and governance access | All `analyst` pages + Admin group (`Users`, `Audit log`). |

*Security Architecture Note:* Route guards in the React client are UX-layer protections designed to prevent analyst confusion and clean navigation. The backend REST API strictly enforces role authorization at the endpoint level via `Depends(require_role(...))` dependencies, producing HTTP 403 Forbidden for unauthorized requests. Both layers must be validated by automated tests.

---

## 4. Functional Requirements (FR)

### FR-1: Single Source of Truth Navigation Schema (`frontend/src/nav.ts`)
- A single configuration array in `frontend/src/nav.ts` must define every top-level navigation item and its associated route.
- Each item must contain:
  - `id`: Unique string identifier (e.g., `"hunt"`, `"users"`).
  - `label`: Display text.
  - `path`: URL path.
  - `group`: Target navigation group (`"Monitor" | "Hunt" | "Investigate" | "Detect" | "Admin"`).
  - `icon`: Dedicated inline SVG component function.
  - `minRole`: Minimum user role required (`"viewer" | "analyst" | "admin"`).
  - `badgeKey`: Optional badge indicator key (`"openAlerts" | "openIncidents" | "openCases"`).
- Both the sidebar UI and React Router `<Routes>` must be generated directly from this definition. It must be impossible to define a sidebar link without a corresponding route, or a route without a nav definition (except for detail routes: `/cases/:id`, `/incidents/:id`, and the legacy `/rules` redirect).

### FR-2: Sidebar Grouping, Ordering & Item Hierarchy
- The sidebar must render navigation items grouped in this exact sequential order:
  1. **Monitor**:
     - `Overview` (`/`)
     - `Alerts` (`/alerts`) [Badge: open alerts]
     - `Incidents` (`/incidents`) [Badge: open incidents]
  2. **Hunt**:
     - `Hunt` (`/hunt`)
     - `Indicators` (`/indicators`)
     - `Watchlist` (`/watchlist`)
  3. **Investigate**:
     - `Cases` (`/cases`) [Badge: open cases]
     - `Reports` (`/reports`)
  4. **Detect**:
     - `Detections` (`/detections`)
  5. **Admin** (*visible only to users with role `admin`*):
     - `Users` (`/users`)
     - `Audit log` (`/audit`)
- Group headers must be rendered in uppercase, muted typography. When the sidebar is collapsed to an icon rail, group headers are replaced with subtle horizontal separators.

### FR-3: Live Navigation Badges & Unified Poller Provider
- Badges must display counts for active workload items:
  - **Alerts Badge**: Count of open alerts = sum of `alerts_by_severity` (`critical` + `high` + `medium` + `low`) with status `open` or `investigating`.
  - **Incidents Badge**: Count of open incidents = `open_incidents` from `GET /stats/overview`.
  - **Cases Badge**: Count of active cases = cases where `status === "open" || status === "in_progress"`, computed client-side from `GET /cases`.
- **Unified Background Poller (`PollerProvider`):**
  - To prevent duplicated queries and avoid overwhelming the backend, `Overview.tsx` and the sidebar badges must share **one single background poller**.
  - Polls `/stats/overview` and `/cases` concurrently every 30 seconds.
  - Polling must automatically pause when the browser tab is hidden (`document.visibilityState === "hidden"`) and trigger an immediate refresh upon becoming visible again.
  - If a badge fetch fails (e.g., network drop, service restart), the badges must fail silently: hide the badge or show no count, and display **no error banner** in the sidebar.

### FR-4: Quick-Search Box with Deterministic IOC Heuristics
- The top of the sidebar (below the brand title) must feature a quick-search input with an inline search icon and placeholder `"Quick search or IOC..."`.
- Upon pressing `Enter`:
  - Input is trimmed and checked against the shared IOC vector heuristics (`docs/specs/ioc-vectors.json`).
  - If the input is classified as an IP (IPv4 or IPv6), domain, URL, or hash (MD5, SHA-1, SHA-256), the app navigates to `/hunt?pivot=<value>` (using the normalized/un-defanged string).
  - If the input is free text, log query syntax (e.g., `event.outcome:failure`), or unrecognized format, the app navigates to `/hunt?q=<value>`.
- Shared IOC classification vectors:
  - Both frontend (`frontend/src/ioc.ts`) and backend (`backend/tests/test_enrichment.py`) must validate against `docs/specs/ioc-vectors.json` to prevent classification drift.
  - Common defanged formats must be normalized: `evil[.]com` $\rightarrow$ `evil.com`, `hxxp://` $\rightarrow$ `http://`, `192.168.1[.]1` $\rightarrow$ `192.168.1.1`.

### FR-5: Desktop Sidebar Sizing, Icon Rail & Persistence
- On desktop screens ($\ge 800\text{ px}$):
  - **Expanded state**: Fixed width of $240\text{ px}$. Displays brand name, quick-search input, group headers, icon + label + badge, and user footer.
  - **Collapsed state**: Fixed width of $64\text{ px}$ icon rail. Displays compact brand logo/monogram, icon-only navigation with small badge dots, and icons for collapse toggle and sign out.
  - Hovering over an item in collapsed mode must render an accessible tooltip containing the full page title and current badge count.
  - A Collapse/Expand button must be located at the bottom of the sidebar.
  - The collapse state (`expanded` vs `collapsed`) must persist across page reloads and sessions via `localStorage` key `thp_sidebar_collapsed`.

### FR-6: Mobile Slide-in Drawer (< 800 px)
- On mobile/tablet viewports ($< 800\text{ px}$):
  - Sidebar is hidden off-screen by default (`transform: translateX(-100%)`).
  - A fixed top mobile bar displays a hamburger button ($\equiv$) and brand name.
  - Clicking the hamburger button slides the sidebar in as a drawer with a semi-transparent dark backdrop.
  - The drawer automatically closes when:
    - Any navigation link is clicked / route changes.
    - The `Escape` key is pressed.
    - The backdrop is clicked.
    - The mobile close button ($\times$) inside the drawer is clicked.
  - Focus is trapped within the open drawer and restored to the hamburger trigger upon closing.

### FR-7: Role-Aware Visibility & Route Guarding
- **Navigation Visibility:** Items with `minRole > currentUser.role` must be completely omitted from the DOM (not merely disabled).
- **Client-Side Route Guarding:**
  - Direct URL access to a page requiring higher privileges (e.g., a `viewer` navigating to `/users` or `/audit`) must not render the target component.
  - Instead, render a clean, standard `"Not Authorized"` view:
    - Headline: `403 - Not Authorized`
    - Subtitle: `Your account role (${currentUser.role}) cannot access this page. Required role: ${minRole}.`
    - Action: A button linking back to `Overview` (`/`).
- **Defense in Depth:** The backend endpoints already enforce authorization and return HTTP 403. The frontend guard provides a clean user experience and prevents unexpected failed API calls.

### FR-8: Detections Canonical Route & Legacy Redirect
- Canonical route for detection engineering is `/detections`.
- Navigating to legacy `/rules` must perform a permanent client-side replacement redirect (`<Navigate to="/detections" replace />`).

### FR-9: Dedicated Watchlist Page (`/watchlist`)
- Move the Watchlist card and table completely out of [`Indicators.tsx`](file:///C:/dev/threat-hunting-platform/frontend/src/pages/Indicators.tsx) into a dedicated page component `frontend/src/pages/Watchlist.tsx`.
- Displays active and historical watchlist entries (`GET /watchlist`).
- Provides an analyst form to add an indicator (`value`, `source`, `note`) with automatic IOC validation (`POST /watchlist`).
- Provides soft-delete button for analysts (`DELETE /watchlist/{id}`).
- `Indicators.tsx` retains indicator lookup, threat-intel provider cards, and quick link to watchlist.

### FR-10: Case Reports Management Page (`/reports`)
- Create `frontend/src/pages/Reports.tsx` accessible to all roles (`viewer`+).
- Lists cases fetched from `GET /cases` with columns: ID, Title, Severity (with severity badge), Status, Created date, Updated date.
- For each case, provides two instant download action buttons:
  - **Download PDF**: Triggers `download("/cases/{id}/report?format=pdf", "case-{id}-report.pdf")`.
  - **Download Markdown**: Triggers `download("/cases/{id}/report?format=md", "case-{id}-report.md")`.
- Disables buttons with loading spinner during report compilation.

### FR-11: Admin User Management Page (`/users`)
- Create `frontend/src/pages/Users.tsx` restricted to role `admin`.
- Lists existing platform accounts (`GET /auth/users`): Username, Role badge (`admin`, `analyst`, `viewer`), Active status, Created timestamp.
- Includes a create-user modal or top form (`POST /auth/users`):
  - Username (required)
  - Password (required, minimum 8 characters)
  - Role dropdown selector: `viewer`, `analyst`, `admin`
- Form validation and error banner for 409 Conflict (username already taken).

### FR-12: Admin Audit Log Viewer (`/audit`)
- Create `frontend/src/pages/AuditLog.tsx` restricted to role `admin`.
- Fetches recent events from `GET /api/v1/audit?limit={N}` with user-selectable $N \in [200, 500, 1000]$ (defaults to 200).
- Displays clear, honest header notice:
  > *"Displaying the most recent {N} platform audit events. Filters apply client-side to this fetched dataset."*
- Client-side interactive filters:
  - User filter (case-insensitive substring or dropdown of distinct users in dataset).
  - Action filter (e.g., `login`, `login_failed`, `search`, `case_created`, `user_created`, `watchlist_add`, etc.).
- Table displays: Timestamp (UTC formatted), User, Action, Object Type, Object ID, and formatted Detail JSON summary.

### FR-13: Accessibility (a11y) & Design System Conformance
- Nav landmark must have an accessible label: `<nav aria-label="Main Navigation">`.
- Active link must be marked with `aria-current="page"` (provided natively by React Router `NavLink`).
- A hidden `"Skip to main content"` link must be the first focusable element on the page, jumping to `#main-content` on focus/activation.
- All interactive controls (links, buttons, inputs) must display visible focus rings conforming to `:focus-visible` (`outline: 2px solid var(--teal); outline-offset: 2px`).
- Transitions for sidebar collapse rail and mobile slide-in drawer must be wrapped in `@media (prefers-reduced-motion: reduce)` to disable animations for users who request reduced motion.
- All colors must maintain WCAG 2.1 AA contrast ratios ($\ge 4.5:1$ for normal text, $\ge 3:1$ for UI components and badges) against the dark palette.

### FR-14: Public Threat-Hunting Showcase Landing Page & Navigation Header (Group-IB Style)
- When a user is unauthenticated (`!user`), visiting the application root (`/`) must render a high-impact, modern cybersecurity showcase landing page inspired by top-tier threat intelligence platforms (Group-IB aesthetic):
  - **Top Navigation Bar:**
    - **Branding (Left):** Modern emblem/monogram logo + text `THREAT HUNTING PLATFORM`.
    - **Navigation Links (Center):** Security platform options:
      - `Capabilities` (Log search, indicator pivot, watchlist tracking)
      - `Detection Rules` (10 built-in YAML rules, MITRE ATT&CK matrix)
      - `Threat Intelligence` (VirusTotal, AbuseIPDB, AlienVault OTX integration)
      - `Architecture` (Filebeat -> Ingest Pipeline -> Elasticsearch -> FastAPI)
      - `Resources & Docs`
      - `Company & About Us`
    - **Action Controls (Right):**
      - `Report an incident` (Quick action link)
      - `Contact Team / Support`
      - Prominent **`Sign In` / `Get Started`** button (navigates to `/login` or activates the login modal).
  - **Hero Section:**
    - Kicker / Category tag: `CYBERSECURITY OPERATIONS & THREAT HUNTING`
    - Hero Headline: `Fight against cybercrime` (with high-contrast typography)
    - Subhead: `Our intelligence-driven detection and response platform correlates multi-stage attacks in real time, investigates indicators across Elasticsearch, and empowers analysts with tamper-proof evidence management.`
    - Call to Action (CTA) Buttons:
      - Primary CTA: **`Get Started` / `Find your product`** $\rightarrow$ opens the analyst login dialog.
      - Secondary CTA: **`Explore Detections` / `Talk to sales`** $\rightarrow$ displays platform detection rule coverage and lab walkthrough.
    - Hero Graphic (Right):
      - High-performance, pure CSS/SVG cybernetic visual featuring glowing interconnected nodes, laser beams, and a dark geometric core reflecting the Group-IB visual aesthetic.
  - **Authenticated Transition:**
    - Upon successful login (as `admin`, `analyst`, or `viewer`), the public landing view unmounts and the full **SOC Operations Console** (FR-1 through FR-13) with the persistent 240px Left Sidebar Shell is displayed.


---

## 5. Non-Functional Requirements (NFR)

1. **Performance & Polling Hygiene:**
   - Polling frequency capped at 30 seconds.
   - Poller must be dormant when tab is backgrounded.
   - Zero memory leaks: all event listeners (`keydown`, `visibilitychange`, `resize`) must be cleaned up on component unmount.
2. **Bundle Size & Dependencies:**
   - Zero new external UI libraries or heavy icon packs.
   - All icons are compact functional SVG components (< 1 KB each).
3. **Cross-Platform Scripting:**
   - Verification and testing scripts must run seamlessly on both Linux/macOS (`verify.sh`, `integration.sh`) and Windows PowerShell (`verify.ps1`, `integration.ps1`).
   - Git repository must enforce LF line endings for shell scripts via `.gitattributes`.
4. **State Persistence:**
   - Collapsed rail preference must persist in `localStorage` without flickering during initial page hydration.

---

## 6. ASCII Wireframes

### Public Showcase Landing Page (Unauthenticated - Group-IB Style)
```text
+----------------------------------------------------------------------------------------------------------------------+
| [O] THREAT HUNTING  Capabilities  Detection Rules  Threat Intel  Architecture  Docs  Company    Report Incident  [Sign In]|
+----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                      |
|  CYBERSECURITY OPERATIONS & THREAT HUNTING                                             / \                           |
|                                                                                       /   \     * [Alert: Red]       |
|  Fight against                                                                     ======[#]======                   |
|  cybercrime                                                                      //   *     *   \\                   |
|                                                                                 //  [Node] [Node] \\  * [Laser Beam] |
|  Our intelligence-driven detection and response platform                       ||     *   |   *    ||                |
|  correlates multi-stage attacks in real time, investigates                     ||     [Cyber Core] ||==============> |
|  indicators across Elasticsearch, and empowers analysts                         \\    *   |   *    //                |
|  with tamper-proof evidence management.                                          \\ [Node] [Node] //                 |
|                                                                                    ======[#]======                   |
|  +--------------------+  +----------------------+                                     \   /                          |
|  | Find your product  |  | Talk to sales / Docs |                                      \ /   * [IOC Verified]        |
|  +--------------------+  +----------------------+                                                                    |
|                                                                                                                      |
+----------------------------------------------------------------------------------------------------------------------+
```

### Desktop Expanded ($240\text{ px}$)
```text
+------------------------+-------------------------------------------------------------+
| Threat Hunting         | [Skip to main content]                                      |
| Platform               |                                                             |
| [Quick search or IOC..]| # Overview                                                  |
+------------------------+                                                             |
| MONITOR                | +---------------------------------------------------------+ |
| [o] Overview           | | Open Incidents: 2    Critical: 1   High: 3              | |
| [!] Alerts         (4) | +---------------------------------------------------------+ |
| [/] Incidents      (2) |                                                             |
|                        | +----------------------------+ +--------------------------+ |
| HUNT                   | | Events per hour            | | Top Sources              | |
| [?] Hunt               | | ~~~~~~~~~~~~~~~~~~~~~~~~~~ | | 192.168.1.50   1,240     | |
| [*] Indicators         | +----------------------------+ +--------------------------+ |
| [=] Watchlist          |                                                             |
|                        |                                                             |
| INVESTIGATE            |                                                             |
| [#] Cases          (1) |                                                             |
| [%] Reports            |                                                             |
|                        |                                                             |
| DETECT                 |                                                             |
| [>] Detections         |                                                             |
|                        |                                                             |
| ADMIN                  |                                                             |
| [@] Users              |                                                             |
| [&] Audit log          |                                                             |
+------------------------+                                                             |
| analayst1 (analyst)    |                                                             |
| [<-] Collapse  Sign out|                                                             |
+------------------------+-------------------------------------------------------------+
```

### Desktop Collapsed ($64\text{ px}$ Icon Rail)
```text
+------+-------------------------------------------------------------------------------+
| [THP]| # Overview                                                                    |
+------+                                                                               |
| [o]  | Tooltip on hover:                                                             |
| [!]4 | +--------------------+                                                        |
| [/]2 | | Alerts (4 open)    |                                                        |
| ---- | +--------------------+                                                        |
| [?]  |                                                                               |
| [*]  |                                                                               |
| [=]  |                                                                               |
| ---- |                                                                               |
| [#]1 |                                                                               |
| [%]  |                                                                               |
| ---- |                                                                               |
| [>]  |                                                                               |
| ---- |                                                                               |
| [@]  |                                                                               |
| [&]  |                                                                               |
+------+                                                                               |
| [->] |                                                                               |
| [x]  |                                                                               |
+------+-------------------------------------------------------------------------------+
```

### Mobile Drawer ($< 800\text{ px}$, Open State)
```text
+----------------------------+-----------------------------------+
| Threat Hunting Platform [X]| (Darkened / Dimmed Backdrop)      |
| [Quick search or IOC...]   |                                   |
| -------------------------- |                                   |
| MONITOR                    | Click backdrop or press Escape    |
| [o] Overview               | to close drawer                   |
| [!] Alerts             (4) |                                   |
| [/] Incidents          (2) |                                   |
|                            |                                   |
| HUNT                       |                                   |
| [?] Hunt                   |                                   |
| [*] Indicators             |                                   |
| [=] Watchlist              |                                   |
|                            |                                   |
| INVESTIGATE                |                                   |
| [#] Cases              (1) |                                   |
| [%] Reports                |                                   |
|                            |                                   |
| DETECT                     |                                   |
| [>] Detections             |                                   |
|                            |                                   |
| ADMIN                      |                                   |
| [@] Users                  |                                   |
| [&] Audit log              |                                   |
| -------------------------- |                                   |
| admin (admin)              |                                   |
| Sign out                   |                                   |
+----------------------------+-----------------------------------+
```

---

## 7. Acceptance Criteria (Given / When / Then)

### AC-1: Navigation Source of Truth & Gating (FR-1, FR-7)
- **Scenario 1.1: Analyst navigation visibility**
  - **Given** an authenticated user with role `analyst`
  - **When** the sidebar renders
  - **Then** all items in Monitor, Hunt, Investigate, and Detect are visible
  - **And** items in Admin (`Users`, `Audit log`) are not present in the DOM.
- **Scenario 1.2: Direct unauthorized URL access**
  - **Given** an authenticated user with role `viewer`
  - **When** the user directly navigates to `/users` or `/audit`
  - **Then** the page renders the `Not Authorized` component stating their role cannot access the page
  - **And** no request is dispatched to `/api/v1/auth/users` or `/api/v1/audit`.

### AC-2: Live Badges & Background Polling (FR-3)
- **Scenario 2.1: Live badge count aggregation**
  - **Given** `/stats/overview` returns `open_incidents: 3` and alerts with `critical: 1, high: 2, medium: 1, low: 0`
  - **And** `/cases` returns 2 open cases and 1 in-progress case
  - **When** the poller completes its cycle
  - **Then** the Incidents badge displays `3`
  - **And** the Alerts badge displays `4` ($1 + 2 + 1 + 0$)
  - **And** the Cases badge displays `3` ($2 + 1$).
- **Scenario 2.2: Silent badge degradation on error**
  - **Given** `/cases` returns HTTP 500 or network failure
  - **When** the badge poller runs
  - **Then** the Cases badge is hidden or empty
  - **And** no global error banner is displayed in the sidebar.
- **Scenario 2.3: Background tab pause**
  - **Given** the application tab is active and polling every 30 seconds
  - **When** the user switches tabs (`document.visibilityState === "hidden"`)
  - **Then** timer intervals are suspended and no network calls are dispatched
  - **When** the user switches back to the tab (`visibilitychange` to `"visible"`)
  - **Then** an immediate refresh query is dispatched.

### AC-3: Quick Search IOC Routing (FR-4)
- **Scenario 3.1: IOC pivot input**
  - **Given** the user enters `evil[.]com` or `192.168.1.1` into the quick-search input
  - **When** the user presses `Enter`
  - **Then** the application navigates to `/hunt?pivot=evil.com` or `/hunt?pivot=192.168.1.1`.
- **Scenario 3.2: General search query input**
  - **Given** the user enters `event.action:ssh_login` or `failed root login`
  - **When** the user presses `Enter`
  - **Then** the application navigates to `/hunt?q=event.action%3Assh_login` or `/hunt?q=failed%20root%20login`.

### AC-4: Desktop Collapsible Rail (FR-5)
- **Scenario 4.1: Toggle collapse**
  - **Given** the sidebar is expanded at $240\text{ px}$
  - **When** the user clicks the Collapse toggle button
  - **Then** the sidebar width transitions to $64\text{ px}$
  - **And** labels and group headers are hidden
  - **And** `localStorage.getItem("thp_sidebar_collapsed")` equals `"true"`.
- **Scenario 4.2: Tooltips in collapsed state**
  - **Given** the sidebar is collapsed
  - **When** the user hovers over the Alerts icon
  - **Then** an accessible tooltip displays `"Alerts"` along with the active badge count.

### AC-5: Mobile Responsive Drawer (FR-6)
- **Scenario 5.1: Drawer interaction**
  - **Given** viewport width is $768\text{ px}$
  - **When** the user taps the hamburger button
  - **Then** the sidebar slides in over the content and the backdrop appears
  - **When** the user presses `Escape` or taps a navigation link
  - **Then** the sidebar closes and focus returns to the hamburger button.

### AC-6: Detections Canonical Route (FR-8)
- **Scenario 6.1: Legacy redirect**
  - **Given** a user navigates to `/rules`
  - **When** the router resolves the URL
  - **Then** the browser URL updates to `/detections` with replace history
  - **And** the Detections page component is rendered.

### AC-7: Reports Page Export (FR-10)
- **Scenario 7.1: Download report**
  - **Given** an analyst on `/reports`
  - **When** the analyst clicks `"Download PDF"` for Case 12
  - **Then** the client requests `/api/v1/cases/12/report?format=pdf`
  - **And** a browser download is initiated for `case-12-report.pdf`.

### AC-8: Audit Log Page & Filtering (FR-12)
- **Scenario 8.1: Limit and Client Filtering**
  - **Given** an admin on `/audit`
  - **When** the admin selects limit `500`
  - **Then** `GET /api/v1/audit?limit=500` is requested
  - **When** the admin types `admin1` into the User filter
  - **Then** only log entries where `user` matches `admin1` are displayed in the table.

### AC-9: Public Showcase Landing Page & Sign-In Transition (FR-14)
- **Scenario 9.1: Unauthenticated root access**
  - **Given** a user is not authenticated (`user === null`)
  - **When** the user opens `http://localhost:5173/`
  - **Then** the Group-IB style public landing page is rendered with top navigation header
  - **And** the hero section displays "Fight against cybercrime" and primary CTA buttons.
- **Scenario 9.2: Sign In navigation**
  - **Given** an unauthenticated visitor on the landing page
  - **When** the user clicks the top-right `"Sign In"` button or `"Find your product"` CTA
  - **Then** the login dialog / page is displayed
  - **When** valid credentials (e.g., `admin` / `admin`) are submitted
  - **Then** the landing view unmounts and the authenticated SOC console with the persistent left sidebar is displayed.

---

## 8. Traceability Matrix (Requirement $\rightarrow$ Task $\rightarrow$ Verification Test)

| FR ID | Description | Planned Task | Automated / Verification Test |
|---|---|---|---|
| **FR-0** | Windows Tooling & LF Enforcement | Task 0 | `scripts/verify.ps1`, `scripts/integration.ps1`, `.gitattributes` |
| **FR-1** | Navigation Schema (`nav.ts`) | Task 1 | `frontend/src/nav.test.ts`: verify all routes mapped, icons present, roles valid |
| **FR-2** | Sidebar Grouping & Ordering | Task 2 | `frontend/src/Sidebar.test.tsx`: assert group ordering and DOM structure |
| **FR-3** | Live Badges & Shared Poller | Task 3 | `frontend/src/poller.test.tsx`: test count calculation, tab visibility pause, silent error |
| **FR-4** | Quick Search & IOC Vectors | Task 4 | `frontend/src/ioc.test.ts` & `backend/tests/test_ioc_vectors.py` against `ioc-vectors.json` |
| **FR-5** | Desktop Collapsible Rail & Storage | Task 5 | `frontend/src/Sidebar.test.tsx`: toggle collapse, verify CSS class and `localStorage` |
| **FR-6** | Mobile Drawer & Keyboard Escape | Task 6 | `frontend/src/Sidebar.test.tsx`: open drawer, simulate `Escape`, check backdrop click |
| **FR-7** | Role Guarding & Visibility | Task 7 | `frontend/src/guard.test.tsx`: test viewer vs admin routes and "Not Authorized" view |
| **FR-8** | Detections Route & Legacy Redirect | Task 8 | `frontend/src/App.test.tsx`: navigate `/rules` $\rightarrow$ redirects to `/detections` |
| **FR-9** | Dedicated Watchlist Page | Task 9 | `frontend/src/pages/Watchlist.test.tsx`: render list, submit new entry, remove entry |
| **FR-10**| Reports Management Page | Task 10 | `frontend/src/pages/Reports.test.tsx`: list cases, trigger PDF/MD download calls |
| **FR-11**| Admin User Management Page | Task 11 | `frontend/src/pages/Users.test.tsx`: list users, submit create user form, error handling |
| **FR-12**| Admin Audit Log Page | Task 12 | `frontend/src/pages/AuditLog.test.tsx`: selector 200/500/1000, client filtering test |
| **FR-13**| a11y, Focus Rings, Reduced Motion | Task 13 | Axe / DOM a11y check: skip link, `aria-current`, `aria-label`, reduced-motion CSS |
| **FR-14**| Public Landing Showcase (Group-IB Style) | Task 14 | `frontend/src/Landing.test.tsx`: verify top bar, hero visual, and Sign In action |

---

## 9. Milestone 2 Backlog (Deferred Items)

1. **DB-Only `/stats/badges` Endpoint**: Implement an optimized database-only endpoint in FastAPI that queries PostgreSQL directly for badge counts without executing Elasticsearch aggregation queries on every 30s tick.
2. **Server-Side Audit Query Filters**: Add `?user=` and `?action=` query parameters and SQL `WHERE` clauses to `GET /api/v1/audit` in the backend.

---

## 10. Open Questions for Approval

1. **Quick-Search Route Behavior for Un-defanged Input:** When an analyst enters defanged input like `evil[.]com` or `hxxp://test`, should the URL parameter in `/hunt?pivot=<value>` contain the cleaned/normalized form (`evil.com`) or the literal raw input? *(Proposed: Cleaned/normalized form `evil.com`, matching backend `detect_ioc_type` output).*
2. **Watchlist Navigation from Indicators Lookup:** Currently, when an IOC lookup succeeds in `Indicators.tsx`, there is an "Add to watchlist" button. Should that button stay in `Indicators.tsx` as a convenience action, while the main list moves to `/watchlist`? *(Proposed: Yes, keep "Add to watchlist" action in Indicators for workflow velocity, but link to `/watchlist` for management).*
3. **Admin User Password Reset:** The backend currently provides `POST /auth/users` (create user) and `GET /auth/users` (list users), but no password update or delete endpoint. Should the `/users` UI in Milestone 1 strictly support listing and creation? *(Proposed: Yes, strictly list and create to honor the "no backend changes" rule).*
4. **Detail Views Sidebar Highlighting:** When an analyst views `/cases/42` or `/incidents/7`, should the parent navigation item (`Cases` or `Incidents`) remain visually active in the sidebar? *(Proposed: Yes, match route prefixes `/cases/*` to activate Cases and `/incidents/*` to activate Incidents).*
5. **Initial Collapsed State on Medium Screens:** Should desktop screens between 800 px and 1024 px default to expanded ($240\text{ px}$) or collapsed ($64\text{ px}$)? *(Proposed: Default to expanded $240\text{ px}$, allowing analyst manual toggle to $64\text{ px}$ which persists in `localStorage`).*
