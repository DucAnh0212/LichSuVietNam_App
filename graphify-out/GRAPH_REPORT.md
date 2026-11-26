# Graph Report - LichSuVietNam_App  (2026-11-26)

## Corpus Check
- 12 files · ~9,148 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 4, .example 1)

## Summary
- 148 nodes · 316 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a24c0094`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- crawl_wiki.py
- main.py
- db_lichsu
- crawl_youtube.py
- database_config.py
- RegisterRequest
- backend_lichsu
- hash_password

## God Nodes (most connected - your core abstractions)
1. `upsert_event_and_media()` - 11 edges
2. `backend_lichsu` - 9 edges
3. `SuKien` - 8 edges
4. `register()` - 8 edges
5. `Media` - 7 edges
6. `run_full_crawler()` - 7 edges
7. `_check_rate_limit()` - 7 edges
8. `get_offline_sync_pack()` - 7 edges
9. `get_thumbnail_subquery()` - 7 edges
10. `login()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `upsert_event_and_media()` --calls--> `Media`  [EXTRACTED]
  be/etl/crawl_wiki.py → be/database_config.py
- `seed_giai_doan()` --calls--> `GiaiDoanLichSu`  [EXTRACTED]
  be/etl/seed_eras.py → be/database_config.py
- `run_full_crawler()` --calls--> `LienKetSuKien`  [EXTRACTED]
  be/etl/crawl_wiki.py → be/database_config.py
- `upsert_event_and_media()` --calls--> `SuKien`  [EXTRACTED]
  be/etl/crawl_wiki.py → be/database_config.py
- `seed_users_and_progress()` --uses--> `SuKien`  [INFERRED]
  be/etl/seed_users.py → be/database_config.py

## Import Cycles
- None detected.

## Communities (9 total, 2 thin omitted)

### Community 0 - "crawl_wiki.py"
Cohesion: 0.15
Nodes (17): build_event_Image_id(), extract_youtube_id(), slugify_vietnamese(), upload_wiki_image_to_cloud(), auto_detect_date(), crawl_category_recursive(), fetch_wiki_article_rich(), find_era_id() (+9 more)

### Community 1 - "main.py"
Cohesion: 0.12
Nodes (18): _check_rate_limit(), _get_client_ip(), get_event_detail(), get_offline_sync_pack(), get_reading_progress(), get_thumbnail_subquery(), get_timeline_overview(), get_user_reading_summary() (+10 more)

### Community 2 - "db_lichsu"
Cohesion: 0.08
Nodes (23): container_name, environment, image, ports, restart, volumes, PGADMIN_DEFAULT_EMAIL, PGADMIN_DEFAULT_PASSWORD (+15 more)

### Community 3 - "crawl_youtube.py"
Cohesion: 0.50
Nodes (5): Media, clean_event_keyword(), evaluate_video(), run_youtube_crawler(), search_youtube_videos()

### Community 4 - "database_config.py"
Cohesion: 0.28
Nodes (7): GiaiDoanLichSu, LienKetSuKien, SuKien, TienTrinhDoc, User, seed_giai_doan(), seed_users_and_progress()

### Community 5 - "RegisterRequest"
Cohesion: 0.19
Nodes (6): GiaiDoanResponse, Config, LoginRequest, RegisterRequest, SuKienResponse, Config

### Community 6 - "backend_lichsu"
Cohesion: 0.17
Nodes (12): build, container_name, depends_on, env_file, environment, ports, restart, volumes (+4 more)

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RegisterRequest` connect `RegisterRequest` to `main.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11561561561561562 - nodes in this community are weakly interconnected._
- **Why does `services` connect `db_lichsu` to `backend_lichsu`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Should `db_lichsu` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Why does `backend_lichsu` connect `backend_lichsu` to `db_lichsu`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._