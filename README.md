# Hermes Skills — by Alejandro Del Villar

A collection of Hermes Agent skills for cross-project knowledge management, automation, and developer productivity.

## Skills

### Project Knowledge Graph

> A local FalkorDB-backed semantic index over all your project artifacts. Query by concept across every project you've ever worked on.

**What it does:**

Hermes already has persistent memory, but it's per-session — it remembers facts about you and preferences across conversations. The Project Knowledge Graph goes further: it indexes the *content* of every project you've built — session recaps, implementation plans, CLAUDE.md conventions, architecture docs, feature specs, and all your Hermes skills — into a local FalkorDB graph database running in Docker.

When you search across projects during a session, instead of hoping the right context is in memory, the graph returns ranked results by concept, with project name, file path, heading, and a snippet — regardless of which project the knowledge came from.

**Indexed document types:**
| Type | What's included |
|------|----------------|
| `recap` | Session recaps and daily recaps |
| `plan` | Implementation plans |
| `claude` | Project memory files (CLAUDE.md, etc.) |
| `architecture` | Architecture docs, feature docs, operations docs, pipeline docs, technical/functional specifications |
| `skill` | Every SKILL.md across all installed Hermes skills |

**Key capabilities:**
- Two-stage ranking: Cypher CONTAINS (fast primary filter) → TF-IDF re-ranking (relevance scoring)
- Incremental indexing: content hashing means unchanged documents are skipped in <1s
- Cross-project: one query searches all configured projects simultaneously
- Zero API calls: no LLM embeddings, no external services — runs entirely locally
- Smart scoping: targeted glob patterns (not rglob) avoid node_modules and build artifacts
- Auto-projection: integrates with session-wrapup to index new knowledge at session end

**Architecture:**
```
knowledge index
    │
    ▼
Scans project directories for .md artifacts
    ├── docs/recaps/, docs/daily-recaps/
    ├── docs/plans/
    ├── project memory file
    ├── docs/architecture/, docs/features/, docs/operations/, docs/pipeline/
    ├── TECHNICAL-DOCUMENTATION.md, FUNCTIONAL-SPECIFICATIONS.md
    └── **/SKILL.md (Hermes skills)
    │
    ▼
Chunks by heading-2 boundaries + paragraphs (max 2000 chars)
    │
    ▼
MERGE into FalkorDB graph as :Chunk nodes
    │
    ▼
knowledge query "concept"
    │
    ▼
Stage 1: Cypher CONTAINS (fast primary filter)
Stage 2: TF-IDF re-ranking
    │
    ▼
Ranked results with project, file, heading, snippet
```

**Setup (one-time):**
```bash
docker run -d \
  --restart=unless-stopped \
  -p 16379:6379 \
  -v knowledge-graph-data:/data \
  --name knowledge-graph \
  falkordb/falkordb:latest

pip install falkordb==1.6.1
```

> **⚠️ Before your first real index**, run the dry-run first to preview which files will be read:
> ```bash
> python3 ~/.hermes/scripts/project-knowledge-index.py index --dry-run
> ```

**Data retention & purge:**

Indexed content persists in the Docker volume until explicitly removed:

```bash
# Stop the service (keep data)
docker stop knowledge-graph

# Clear all indexed data (stop + purge)
docker stop knowledge-graph && docker rm knowledge-graph && docker volume rm knowledge-graph-data
```

**Usage:**
```bash
# Index all projects
python3 ~/.hermes/scripts/project-knowledge-index.py index

# Query by concept
python3 ~/.hermes/scripts/project-knowledge-index.py query "FalkorDB replication"

# Filter by project or doc type
python3 ~/.hermes/scripts/project-knowledge-index.py query "batch writes" --project CI
python3 ~/.hermes/scripts/project-knowledge-index.py query "soft delete" --type skill

# Health check
python3 ~/.hermes/scripts/project-knowledge-index.py doctor
```

**Why FalkorDB over alternatives:**
- **Cypher CONTAINS** (exact match) as primary filter — faster and more predictable than fuzzy simhash
- **Native graph model** — cross-project queries are `MATCH (c:Chunk {project:'CI'}) RETURN c`, no JOINs needed
- **Schema-free** — add new node types and edges on the fly without migrations
- **Sub-200MB idle** — runs in a single Docker container with `--restart=unless-stopped`
- **Full purge** — `docker stop && docker rm && docker volume rm` erases all indexed data

**Install via Hermes:**
```bash
hermes skills install https://raw.githubusercontent.com/adelvillar1/hermes-skills/main/devops/project-knowledge-graph/SKILL.md --name project-knowledge-graph
```

---

## About the author

**Alejandro Del Villar** — B2B SaaS founder and Hermes Agent power user. Building cruiseintelligence.com and other products. Most Hermes skills here were extracted from real production workflows, solving actual problems across multiple projects.
