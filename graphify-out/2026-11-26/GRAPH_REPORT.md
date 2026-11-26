# Graph Report - LichSuVietNam_App  (2026-11-26)

## Corpus Check
- 12 files · ~8,674 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 3, .example 1)

## Summary
- 143 nodes · 324 edges · 8 communities (7 shown, 1 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 28 edges (avg confidence: 0.95)
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
- backend_lichsu

## God Nodes (most connected - your core abstractions)
1. `SuKien` - 16 edges
2. `GiaiDoanLichSu` - 13 edges
3. `upsert_event_and_media()` - 11 edges
4. `Media` - 11 edges
5. `backend_lichsu` - 9 edges
6. `TienTrinhDoc` - 8 edges
7. `User` - 8 edges
8. `get_event_detail()` - 8 edges
9. `get_offline_sync_pack()` - 8 edges
10. `get_user_reading_summary()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `get_event_detail()` --uses--> `LienKetSuKien`  [INFERRED]
  be/main.py → be/database_config.py
- `get_offline_sync_pack()` --uses--> `LienKetSuKien`  [INFERRED]
  be/main.py → be/database_config.py
- `seed_giai_doan()` --calls--> `GiaiDoanLichSu`  [EXTRACTED]
  be/etl/seed_eras.py → be/database_config.py
- `run_youtube_crawler()` --uses--> `SuKien`  [INFERRED]
  be/etl/crawl_youtube.py → be/database_config.py
- `seed_users_and_progress()` --uses--> `SuKien`  [INFERRED]
  be/etl/seed_users.py → be/database_config.py

## Import Cycles
- None detected.

## Communities (8 total, 1 thin omitted)

### Community 0 - "crawl_wiki.py"
Cohesion: 0.15
Nodes (19): LienKetSuKien, build_event_Image_id(), extract_youtube_id(), slugify_vietnamese(), upload_wiki_image_to_cloud(), auto_detect_date(), crawl_category_recursive(), fetch_wiki_article_rich() (+11 more)

### Community 1 - "main.py"
Cohesion: 0.18
Nodes (15): GiaiDoanLichSu, SuKien, get_event_detail(), get_offline_sync_pack(), get_reading_progress(), get_thumbnail_subquery(), get_timeline_overview(), get_user_reading_summary() (+7 more)

### Community 2 - "db_lichsu"
Cohesion: 0.08
Nodes (23): container_name, environment, image, ports, restart, volumes, PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD (+15 more)

### Community 3 - "database_config.py"
Cohesion: 0.21
Nodes (6): Media, clean_event_keyword(), evaluate_video(), run_youtube_crawler(), search_youtube_videos(), seed_giai_doan()

### Community 4 - "seed_users.py"
Cohesion: 0.22
Nodes (7): hash_password(), verify_password(), TienTrinhDoc, User, seed_users_and_progress(), login(), register()

### Community 5 - "RegisterRequest"
Cohesion: 0.19
Nodes (6): GiaiDoanResponse, Config, LoginRequest, RegisterRequest, SuKienResponse, Config

### Community 6 - "backend_lichsu"
Cohesion: 0.17
Nodes (12): build, container_name, depends_on, env_file, environment, ports, restart, volumes (+4 more)

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RegisterRequest` connect `RegisterRequest` to `main.py`, `seed_users.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuKien` (e.g. with `run_youtube_crawler()` and `seed_users_and_progress()`) actually correct?**
  _`SuKien` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Should `crawl_wiki.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14516129032258066 - nodes in this community are weakly interconnected._
- **Why does `SuKien` connect `main.py` to `crawl_wiki.py`, `database_config.py`, `seed_users.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `GiaiDoanLichSu` (e.g. with `get_event_detail()` and `get_offline_sync_pack()`) actually correct?**
  _`GiaiDoanLichSu` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `db_lichsu` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Why does `services` connect `db_lichsu` to `backend_lichsu`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._