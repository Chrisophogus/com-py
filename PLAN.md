# Plan

## 2026-03-24 README maintenance

Trade-off considered:

- A broader documentation rewrite could cover every workflow and generated file in depth.
- A smaller sync update keeps the README aligned with the current scripts without adding extra maintenance burden.

Chosen approach:

- Use the smaller sync update. It is the simplest maintainable option and keeps the documentation accurate without introducing a new structure or extra process.

## 2026-07-19 repository review and checks

Trade-offs considered:

- `pytest` would provide richer fixtures, but the standard-library `unittest` runner covers the current functional surface without adding a development dependency.
- Separate lint, data and media tools would provide more specialised reports, but one small repository checker is easier to run locally and can validate Python syntax, JSON/JSONL and image integrity with the project's existing dependencies.
- Cached render intermediates save some processing time, but validating or rebuilding inexpensive derived files is safer than silently reusing output produced with different quality settings.
- Removing generated images from Git would substantially reduce the repository size, but it would also remove the examples currently used by the README and require another history rewrite. That should be handled as a separate repository-policy change.

Chosen approach:

- Add a `unittest` suite covering every active module, using small temporary images and mocked network/process boundaries.
- Add a repository checker and document the separate commands for checks and tests so each failure remains easy to diagnose.
- Fix confirmed defects in partial extraction reuse, cache reuse, strip ordering, shot merging, metadata refresh fallback, output theme selection and vertical render coverage without restructuring the working pipeline.
- Clarify dependencies, checks and local-file exclusions in the README and `.gitignore` while preserving the existing layout and the user's current MemPalace ignore entries.

## 2026-07-26 repository branch instructions

Trade-off considered:

- Keeping branch guidance only in local tooling would avoid another tracked file, but collaborators and fresh clones would not receive the same safeguards.
- A tracked root `AGENTS.md` makes the branch workflow explicit and portable without adding tooling or maintenance overhead.

Chosen approach:

- Track the requested root `AGENTS.md` so development consistently starts away from the protected production branch.
