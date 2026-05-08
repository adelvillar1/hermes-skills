# Backend Storage Evaluation: SQLite vs FalkorDB

When designing the cross-project knowledge graph, two storage backends were evaluated. This note captures the tradeoffs for future reference.

## Evaluation Context

- **Requirement**: Queryable store for ~2000 document chunks from ~150 skills + 8 projects' recaps/plans/architecture docs
- **Constraints**: Zero infrastructure tax, sub-second queries, must work at session warmup
- **Our experience**: Deep FalkorDB expertise from Cruising Intelligence (57 clan nodes, 1K+ CABIN_FIT edges, 9-pass Cypher projections)

## SQLite (Chosen)

**Setup**: `import sqlite3` — stdlib, always available
**Memory**: File on disk, ~5MB for the full corpus
**Startup**: Instant
**Query**: Simhash distance + TF-IDF ranking — approximate semantic search
**Portability**: Any machine with Python 3.9+
**Durability**: ACID, survives crashes

**The tradeoff**: No graph traversal. "Show me the dependency chain from concept X" requires multiple queries and client-side join logic. Simhash is less accurate than embeddings for paraphrased queries.

## FalkorDB

**Setup**: `docker run falkordb/falkordb` + Python client
**Memory**: ~1GB RSS for the server process
**Startup**: ~3s for container + graph load from RDB file
**Query**: Cypher `MATCH (p:Pattern)-[:SOLVES]->(c:Concept) RETURN p` — native graph traversal
**Portability**: Requires Docker running. Not available on Railway workers or machines without Docker.
**Durability**: Requires RDB persistence strategy (SAVE/BGSAVE, SHUTDOWN NOSAVE pattern we already know from CI)

**The advantage**: Multi-hop queries are trivial. "Which recaps reference the FalkorDB replication fix AND were written in the same week as a scraper fix?" is one Cypher query. In SQLite, it's a join across two query result sets.

## Decision

SQLite for v1. The 90% use case is "find me everything about concept X" — a ranked flat list. Graph traversal is <10% of queries and can be approximated with multi-step SQLite queries. FalkorDB should be added as a v2 enrichment layer when the multi-hop query pattern becomes frequent enough to warrant the Docker dependency.

## Migration Path to FalkorDB v2

When adding FalkorDB:
1. The indexer already has all data in a structured format — just write nodes + edges to both stores
2. Node types: `Document`, `Chunk`, `Project`, `Pattern`
3. Edge types: `APPEARS_IN` (chunk → document), `PART_OF` (chunk → project), `RELATES_TO` (chunk → chunk via fingerprint similarity), `SOLVES` (pattern → concept)
4. Keep SQLite as the default for warmup (fast, no Docker). FalkorDB runs on demand when user explicitly asks for a graph-traversal query
5. Use the same RDB persistence pattern from CI: BGSAVE → copy dump.rdb → SHUTDOWN NOSAVE → restart
