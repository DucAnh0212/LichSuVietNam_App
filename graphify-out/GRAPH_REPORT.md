# Graph Report - LichSuVietNam_App  (2026-11-26)

## Corpus Check
- 12 files · ~8,629 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .example 1)

## Summary
- 143 nodes · 301 edges · 8 communities (7 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3ad44be9`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- crawl_wiki.py
- main.py
- db_lichsu
- database_config.py
- seed_users.py
- RegisterRequest
- db_lichsu

## God Nodes (most connected - your core abstractions)
1. `upsert_event_and_media()` - 11 edges
2. `SuKien` - 9 edges
3. `backend_lichsu` - 9 edges
4. `get_thumbnail_subquery()` - 7 edges
5. `Media` - 7 edges
6. `run_full_crawler()` - 7 edges
7. `hash_password()` - 7 edges
8. `db_lichsu` - 7 edges
9. `pgadmin_lichsu` - 7 edges
10. `RegisterRequest` - 6 edges

## Surprising Connections (you probably didn't know these)
- `register()` --calls--> `User`  [EXTRACTED]
  be/main.py → be/database_config.py
- `seed_giai_doan()` --calls--> `GiaiDoanLichSu`  [EXTRACTED]
  be/etl/seed_eras.py → be/database_config.py
- `upsert_event_and_media()` --calls--> `SuKien`  [EXTRACTED]
  be/etl/crawl_wiki.py → be/database_config.py
- `run_youtube_crawler()` --uses--> `SuKien`  [INFERRED]
  be/etl/crawl_youtube.py → be/database_config.py
- `seed_users_and_progress()` --uses--> `SuKien`  [INFERRED]
  be/etl/seed_users.py → be/database_config.py

## Import Cycles
- None detected.

## Communities (8 total, 1 thin omitted)

### Community 0 - "crawl_wiki.py"
Cohesion: 0.13
Nodes (19): LienKetSuKien, build_event_Image_id(), extract_youtube_id(), slugify_vietnamese(), upload_wiki_image_to_cloud(), auto_detect_date(), crawl_category_recursive(), fetch_wiki_article_rich() (+11 more)

### Community 1 - "main.py"
Cohesion: 0.17
Nodes (13): get_event_detail(), get_offline_sync_pack(), get_reading_progress(), get_thumbnail_subquery(), get_timeline_overview(), get_user_reading_summary(), get_year_month_breakdown(), ProgressUpdateRequest (+5 more)

### Community 2 - "db_lichsu"
Cohesion: 0.08
Nodes (25): build, container_name, depends_on, env_file, environment, ports, restart, volumes (+17 more)

### Community 3 - "database_config.py"
Cohesion: 0.18
Nodes (11): GiaiDoanLichSu, Media, SuKien, TienTrinhDoc, User, clean_event_keyword(), evaluate_video(), run_youtube_crawler() (+3 more)

### Community 4 - "seed_users.py"
Cohesion: 0.31
Nodes (4): hash_password(), verify_password(), login(), register()

### Community 5 - "RegisterRequest"
Cohesion: 0.19
Nodes (6): GiaiDoanResponse, Config, LoginRequest, RegisterRequest, SuKienResponse, Config

### Community 6 - "db_lichsu"
Cohesion: 0.20
Nodes (10): container_name, environment, image, ports, restart, volumes, POSTGRES_DB, POSTGRES_PASSWORD (+2 more)

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RegisterRequest` connect `RegisterRequest` to `main.py`, `seed_users.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `SuKien` (e.g. with `run_youtube_crawler()` and `seed_users_and_progress()`) actually correct?**
  _`SuKien` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `crawl_wiki.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13368983957219252 - nodes in this community are weakly interconnected._
- **Why does `services` connect `db_lichsu` to `db_lichsu`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Should `db_lichsu` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._