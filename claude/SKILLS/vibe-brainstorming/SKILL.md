# Suggested Update to brainstorming/SKILL.md

Add this section at the end, before "Key Principles":

---

## After the Design

**Documentation:**
- Write the validated design to the vibe workspace:
  ```
  create_doc(project, "plans", "YYYY-MM-DD-<topic>-design", content=<design>)
  ```
- If vibeMCP is not available, write to `docs/plans/` locally

**Next step:**
- Suggest `task-breakdown` to turn the design into actionable tasks
- The task-breakdown skill will read the design doc from `plans/` automatically

---

This replaces the current "After the Design" section which references
git commits and other skills that may not exist (elements-of-style,
superpowers:using-git-worktrees, etc.)
