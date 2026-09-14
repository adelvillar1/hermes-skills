# Python Project Survey Patterns

Quick-reference commands and heuristics for surveying Python codebases (not JS/TS/web).

## Discovery Commands

```bash
# Total Python LOC and file count
find . -name "*.py" | xargs wc -l | tail -1
find . -name "*.py" | wc -l

# Largest files (monolith detection)
find . -name "*.py" -not -path "*/venv/*" -not -path "*/.git/*" | xargs wc -l | sort -rn | head -20

# Class inventory
grep -r "^class " src/ --include="*.py"

# Method/function inventory (top-level + methods)
grep -r "def " src/ --include="*.py" | wc -l

# Test classes and methods
grep -r "^class Test" tests/ --include="*.py"
grep -r "^def test_" tests/ --include="*.py"

# Assertion count (coverage signal)
grep -r "assert " tests/ --include="*.py" | wc -l

# Import graph (most-used modules)
grep -r "^import\|^from" src/ --include="*.py" | sort | uniq -c | sort -rn | head -20

# TODO/FIXME audit
grep -r "TODO\|FIXME\|XXX\|HACK" src/ --include="*.py" | wc -l
```

## Python-Specific Heuristics

| Signal | Command | Threshold | Meaning |
|--------|---------|-----------|---------|
| Test coverage | `pytest --tb=short -q` | 0 failures | Green suite |
| Test ratio | test LOC / src LOC | > 0.5 | Good coverage |
| Class count | `grep -c "^class "` | — | OOP density |
| Method count per class | `grep "def " file.py | wc -l` | > 15 | SRP violation |
| File size | `wc -l` | > 400 | Monolith risk |
| Docstring coverage | `grep -c '"""' file.py` | < 2 per class | Under-documented |

## Pyproject.toml Checklist

Read `pyproject.toml` for:
- `[project]` name, version, description
- `[project.dependencies]` — core libraries (FastAPI, Django, SQLAlchemy, Pydantic, etc.)
- `[project.optional-dependencies]` — dev/test/docs extras
- `[tool.pytest.ini_options]` — test configuration
- `[tool.mypy]` or `[tool.ruff]` — type/lint config
- `[build-system]` — setuptools, hatch, poetry, pdm

## Common Python Patterns to Note

- **Dataclasses vs Pydantic**: `@dataclass` = stdlib, lightweight; `BaseModel` = validation, serialization
- **Abstract base classes**: `ABC` + `@abstractmethod` for pluggable components
- **Factory pattern**: `get_*(...)` functions with registries (common for extractors, adapters)
- **Type hints**: `from __future__ import annotations` enables forward refs in Python < 3.10
- **pytest fixtures**: `@pytest.fixture` for reusable test data

## Test Structure Conventions

```
tests/
  test_<module>.py        # mirrors src/<module>.py
  conftest.py             # shared fixtures
  data/                   # test fixtures, sample files
```

Run tests:
```bash
pytest -v --tb=short      # verbose, short tracebacks
pytest -q                 # quiet, just dots
pytest --co -q            # collect only, count tests
```

## Documentation Patterns

Python projects often have:
- `README.md` — setup, quickstart
- `docs/` — Sphinx or MkDocs
- `SPEC.md` or `ARCHITECTURE.md` — design docs
- `CHANGELOG.md` — version history
- Docstrings in source (Google style, NumPy style, or Sphinx reST)

## Maintainability Assessment (Python)

| Grade | Criteria |
|-------|----------|
| A | Files < 300 lines, clear module boundaries, type hints everywhere, pytest fixtures, shared types in `models.py` or `schemas.py` |
| B | Some files 300-500 lines, minor duplication, mostly clean boundaries, some type hints |
| C | Several files 500-800 lines, noticeable duplication, fuzzy boundaries, inconsistent type hints |
| D | Multiple files > 800 lines, heavy duplication, no clear separation, untyped |
| F | Monolithic files > 1200 lines, everything coupled, changes require touching 4+ files, no tests |

## Git Repository State

For projects without an existing `.git` directory:
- Note "not a git repository" in the survey report
- Do NOT attempt to initialize git unless the user explicitly requests it
- The absence of version control is itself a signal (no commit history, no branch tracking, no rollback capability)
- If the user later provides a remote URL, use `git init` + `git remote add origin` + `git fetch` to establish the connection, then proceed with the survey
