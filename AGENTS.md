Codex Repository Instructions

Git Branch Workflow

Before starting substantial new work:

1. Check the current Git branch.
2. If currently on main, do not make changes. Tell me that main is the protected production branch.
3. If currently on dev, determine whether the requested work is a distinct feature, project, experiment, refactor, or significant change.
4. For distinct new work, suggest creating a feature branch before modifying files.
5. Suggest a concise branch name using:
   feature/
6. Do not create or switch branches until I approve, unless I explicitly instructed you to create the branch as part of the request.
7. Small fixes, documentation updates, and minor adjustments may be made directly on dev when appropriate.
8. Before making changes, state which branch is currently checked out.
9. When in doubt, prefer suggesting a feature branch.

Branch Roles

- main is the protected production branch.
- dev is the persistent development/staging branch.
- feature/* branches are for isolated development work.

Normal promotion path:

feature/* → dev → main
