# Graph Report - .  (2026-06-09)

## Corpus Check
- Corpus is ~17,286 words - fits in a single context window. You may not need a graph.

## Summary
- 253 nodes · 484 edges · 28 communities (20 shown, 8 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 16 edges (avg confidence: 0.83)
- Token cost: 31,000 input · 7,000 output

## Community Hubs (Navigation)
- [[_COMMUNITY_DB Operations & API Layer|DB Operations & API Layer]]
- [[_COMMUNITY_Message Filtering & Matching|Message Filtering & Matching]]
- [[_COMMUNITY_Group Discovery & Management|Group Discovery & Management]]
- [[_COMMUNITY_Infrastructure & Deployment|Infrastructure & Deployment]]
- [[_COMMUNITY_Parser Core & Client Connection|Parser Core & Client Connection]]
- [[_COMMUNITY_Auto-Join Flood Protection|Auto-Join Flood Protection]]
- [[_COMMUNITY_Notifications & XSS Safety|Notifications & XSS Safety]]
- [[_COMMUNITY_Dashboard Auth & Pages|Dashboard Auth & Pages]]
- [[_COMMUNITY_FastAPI App & Sanitization|FastAPI App & Sanitization]]
- [[_COMMUNITY_Keyword CRUD|Keyword CRUD]]
- [[_COMMUNITY_Route Management Tests|Route Management Tests]]
- [[_COMMUNITY_Auth Tests|Auth Tests]]
- [[_COMMUNITY_Hits Route Tests|Hits Route Tests]]
- [[_COMMUNITY_Binary Build & CICD|Binary Build & CI/CD]]
- [[_COMMUNITY_Claude Dev Settings|Claude Dev Settings]]
- [[_COMMUNITY_Index Route|Index Route]]
- [[_COMMUNITY_Base Nav Template|Base Nav Template]]
- [[_COMMUNITY_Toast UI Component|Toast UI Component]]
- [[_COMMUNITY_Time Format Utility|Time Format Utility]]
- [[_COMMUNITY_Stats & Editing Changelog|Stats & Editing Changelog]]
- [[_COMMUNITY_CI Test Job|CI Test Job]]
- [[_COMMUNITY_Gemini Spec Component D|Gemini Spec Component D]]

## God Nodes (most connected - your core abstractions)
1. `str` - 25 edges
2. `init_db()` - 16 edges
3. `on_new_message()` - 15 edges
4. `has_cyrillic()` - 14 edges
5. `build_notification_text()` - 14 edges
6. `int` - 14 edges
7. `list_keywords()` - 13 edges
8. `find_keyword_match()` - 11 edges
9. `build_profile_link()` - 11 edges
10. `is_russian_group()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `sanitize()` --implements--> `XSS Sanitization via html.escape + markdown strip`  [INFERRED]
  dashboard/sanitize.py → docs/superpowers/plans/2026-06-09-telelistener-ru.md
- `get_hits()` --implements--> `XSS Sanitization via html.escape + markdown strip`  [INFERRED]
  dashboard/routes/hits.py → docs/superpowers/plans/2026-06-09-telelistener-ru.md
- `Web Dashboard Component Spec` --references--> `sanitize()`  [EXTRACTED]
  gemini-code-1781011376559.md → dashboard/sanitize.py
- `TeleListener-RU Implementation Plan` --references--> `init_db()`  [EXTRACTED]
  docs/superpowers/plans/2026-06-09-telelistener-ru.md → db/init.py
- `SQLite WAL Mode Design` --rationale_for--> `Russian Compliance and Proxy Adaptability`  [INFERRED]
  db/init.py → gemini-code-1781011376559.md

## Hyperedges (group relationships)
- **Incoming Message Processing Pipeline** — parser_client_on_new_message, parser_handlers_has_cyrillic, parser_handlers_is_spam_link, parser_handlers_find_keyword_match [EXTRACTED 1.00]
- **Keyword Hit Notification Flow** — parser_client_on_new_message, parser_notifications_build_notification_text, parser_notifications_send_notification [EXTRACTED 1.00]
- **Auto-Discovery and Group Join Pipeline** — parser_main_run_auto_discovery, parser_auto_join_is_russian_group, parser_auto_join_join_groups_with_flood_protection [EXTRACTED 1.00]
- **Keyword CRUD Pipeline: Template → Route → DB** — templates_keywords_load_keywords, routes_keywords_get_keywords, db_operations_list_keywords [INFERRED 0.95]
- **Group Join/Leave Lifecycle: Template → Route → Telethon + DB** — templates_groups_join_group, routes_groups_join_group, db_operations_add_joined_group [EXTRACTED 1.00]
- **XSS Sanitization Chain: DB Hit → sanitize() → API Response** — db_operations_list_hits, routes_hits_get_hits, dashboard_sanitize_sanitize [EXTRACTED 1.00]

## Communities (28 total, 8 thin omitted)

### Community 0 - "DB Operations & API Layer"
Cohesion: 0.14
Nodes (40): v1.4 Auto-Discovery Feature, add_hit(), add_keyword(), add_monitored_group(), count_groups(), count_hits(), count_keywords(), delete_keyword() (+32 more)

### Community 1 - "Message Filtering & Matching"
Cohesion: 0.13
Nodes (27): build_profile_link(), find_keyword_match(), has_cyrillic(), is_spam_link(), bool, int, str, KEYWORDS config (+19 more)

### Community 2 - "Group Discovery & Management"
Cohesion: 0.10
Nodes (23): v1.3 Group Search and Join, BaseModel, int, str, list_joined_groups(), get_joined(), join_group(), JoinIn (+15 more)

### Community 3 - "Infrastructure & Deployment"
Cohesion: 0.11
Nodes (19): Docker Compose telelistener Service, Russian Compliance and Proxy Adaptability, Parser Component Spec, Database Component Spec, TeleListener-RU Implementation Plan, init_db(), _MIGRATIONS List, str (+11 more)

### Community 4 - "Parser Core & Client Connection"
Cohesion: 0.14
Nodes (19): Credential Retry Loop (credentials-absent-at-startup), add_joined_group(), create_client(), on_new_message(), Build TelegramClient, preferring DB-stored credentials over env vars., main(), Periodically search Telegram for Russian public groups matching configured keywo, Wait for credentials, then run the Telethon reconnect loop.      If credentials (+11 more)

### Community 5 - "Auto-Join Flood Protection"
Cohesion: 0.19
Nodes (17): Anti-Flood / Backoff Pattern, float, compute_backoff_delay(), is_russian_group(), join_groups_with_flood_protection(), bool, int, str (+9 more)

### Community 6 - "Notifications & XSS Safety"
Cohesion: 0.18
Nodes (16): XSS Sanitization via html.escape, build_notification_text(), int, str, send_notification(), test_build_profile_link_xss_username_is_escaped, test_notification_html_escapes_comment, test_notification_html_escapes_comment() (+8 more)

### Community 7 - "Dashboard Auth & Pages"
Cohesion: 0.21
Nodes (12): str, require_auth(), groups_page(), index(), keywords_page(), str, settings_page(), HTTPBasicCredentials (+4 more)

### Community 8 - "FastAPI App & Sanitization"
Cohesion: 0.17
Nodes (12): Web Dashboard Component Spec, XSS Sanitization via html.escape + markdown strip, FastAPI App Instance, int, str, sanitize(), get_groups(), get_hits() (+4 more)

### Community 9 - "Keyword CRUD"
Cohesion: 0.33
Nodes (8): int, update_keyword(), create_keyword(), edit_keyword(), KeywordIn, remove_keyword(), addKeywords() Bulk Add, saveEdit() Keyword Inline Edit

### Community 10 - "Route Management Tests"
Cohesion: 0.46
Nodes (7): _patched_auth(), test_add_keyword(), test_delete_keyword(), test_get_settings(), test_list_groups(), test_list_keywords(), test_update_settings()

### Community 11 - "Auth Tests"
Cohesion: 0.47
Nodes (4): auth_header(), str, test_correct_credentials_returns_200(), test_wrong_credentials_returns_401()

### Community 12 - "Hits Route Tests"
Cohesion: 0.60
Nodes (3): auth(), test_hits_api_returns_list(), test_hits_api_sanitizes_xss()

### Community 13 - "Binary Build & CI/CD"
Cohesion: 0.50
Nodes (4): v1.0 Combined PyInstaller Binary, GitHub Actions build Job (macOS+Windows), GitHub Actions release Job, PyInstaller Frozen Binary Path Resolution

## Knowledge Gaps
- **53 isolated node(s):** `str`, `allow`, `int`, `int`, `float` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `on_new_message()` connect `Parser Core & Client Connection` to `DB Operations & API Layer`, `Message Filtering & Matching`, `Notifications & XSS Safety`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Why does `init_db()` connect `Infrastructure & Deployment` to `Parser Core & Client Connection`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `list_keywords()` connect `DB Operations & API Layer` to `FastAPI App & Sanitization`, `Keyword CRUD`, `Parser Core & Client Connection`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **What connects `Combined entry point: runs the Telegram parser and web dashboard in one process.`, `str`, `allow` to the rest of the system?**
  _61 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `DB Operations & API Layer` be split into smaller, more focused modules?**
  _Cohesion score 0.1383838383838384 - nodes in this community are weakly interconnected._
- **Should `Message Filtering & Matching` be split into smaller, more focused modules?**
  _Cohesion score 0.1330049261083744 - nodes in this community are weakly interconnected._
- **Should `Group Discovery & Management` be split into smaller, more focused modules?**
  _Cohesion score 0.09782608695652174 - nodes in this community are weakly interconnected._