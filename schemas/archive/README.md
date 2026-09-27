# Archived schema versions

`v0.1.0/` is a byte-identical, frozen copy of the schemas that dataset v0.1.0 (and evaluation
v0.1.0) were written against — the state of `schemas/` at commit `476d322`.

Records carry `schema_version`; `gjcore.schemas` validates each record against the schema set of
its own version (current version → `schemas/`, older versions → `schemas/archive/v<ver>/`), and the
semantic linter applies only the rules that existed at that version. Old releases therefore stay
reproducible and are never re-judged by rules written later.

Never edit files in this directory. A new schema version copies the current `schemas/*.json` here
before changing them.
