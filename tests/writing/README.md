# Writing-quality fixtures

The positive sources combine correct reader-visible prose with deliberately
invalid tokens inside code, math, citations, URLs, attributes, raw backend
markup, shortcodes, and front-matter keys. They also exercise shared and
per-book terminology plus every supported source-local override.

Negative sources put unique misspellings immediately beside excluded syntax,
inside reader-facing front-matter values, and in visible semantic-icon wording.
Separate cases prove book dictionary scope, shared and per-book rejected terms,
and the nonblocking severity of subjective repetition findings.

`tests/integration/test-writing-quality.py` stages these files under canonical `book/`
and `docs/` paths in temporary repositories, runs the override validator, and
then invokes the pinned CSpell and Vale tools in rootless offline containers.
Cases are batched into five container runs and each checker has a 20-second
limit so a pathological pattern fails rather than consuming CPU indefinitely.
