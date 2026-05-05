# Kilo Agent Configuration - Python SpaceMonger Clone

## Project Overview
This project is a Python-based disk space visualization tool inspired by SpaceMonger. It uses a treemap layout to represent directory contents interactively.

**Main File:** `main.py` (310 lines, single-file application)

## Architecture Summary

### Core Components
1. **Node Class** (`main.py:10-16`) — Tree node for filesystem representation
2. **human_size()** (`main.py:19-28`) — Human-readable byte formatting
3. **scan_path()** (`main.py:31-57`) — Recursive directory scanner
4. **treemap()** (`main.py:60-82`) — Slice-and-dice treemap layout algorithm
5. **SpaceMongerClone** (`main.py:85-306`) — Tkinter GUI application

## Development Workflow

### For Code Analysis
When analyzing this codebase:
- Start with `main.py` — it's the only source file
- Focus on the `SpaceMongerClone` class for GUI logic
- Understand the treemap algorithm for visualization
- Note the threading pattern for background scanning

### For Code Changes
1. **Always read the full file first** using the `read` tool
2. **Make targeted edits** using the `edit` tool with exact string matching
3. **Run lint/type checks** after changes (if available)
4. **Do not commit** without explicit user request

### Testing This Project
No formal test suite exists. Manual testing includes:
```bash
python main.py
# Then interact with the GUI:
# - Open a folder
# - Click/double-click rectangles
# - Test zoom out (Backspace)
# - Try open/delete operations
```

## Kilo Tool Usage Guidelines

### When to Use Which Tool

| Task | Recommended Tool |
|------|-----------------|
| Find all Python files | `glob` with `*.py` pattern |
| Search for specific code patterns | `grep` with regex |
| Read existing code | `read` (always before editing) |
| Make code changes | `edit` (after reading) |
| Run shell commands | `bash` (for tests, lint, etc.) |
| Complex multi-step tasks | `task` with subagent |
| Web searches for info | `websearch` or `codesearch` |

### Project-Specific Patterns

#### Editing main.py
Always preserve:
- The exact indentation (the file uses 4 spaces)
- Tkinter main loop at the end (lines 308-310)
- Threading pattern for background work
- Error handling approach (graceful degradation)

#### Search Patterns
Common interesting patterns to grep:
- `class ` — finds class definitions
- `def ` — finds function definitions  
- `tk\.` or `ttk\.` — finds Tkinter widget usage
- `threading` — finds concurrent code
- `lambda` — finds inline functions

## Common Development Tasks

### Task: Add a New Feature
1. Use `read` to understand relevant sections
2. Identify the modification point
3. Use `edit` to make the change
4. Test manually by running the application
5. Document the change in appropriate files

### Task: Fix a Bug
1. Use `grep` to locate related code
2. Use `read` to examine the context
3. Identify the root cause
4. Use `edit` to apply the fix
5. Verify the fix manually

### Task: Refactor Code
1. Use `read` to understand the full scope
2. Create a todo list with `todowrite` for multi-step changes
3. Make incremental edits with `edit`
4. Ensure functionality is preserved
5. Update documentation if needed

## Configuration Files

- **`.kilo/command/*.md`** — Custom command documentation
- **`.kilo/agent/*.md`** — Agent behavior specifications
- **`kilo.json`** — Project-specific Kilo settings
- **`AGENTS.md`** — This file (agent configuration guide)

## Notes for AI Agents

### Key Behaviors
- **Single-file project**: All logic is in `main.py`
- **No external dependencies**: Uses only Python stdlib
- **GUI application**: Requires manual testing
- **Threading present**: Background scanning pattern
- **Recursive algorithms**: scan_path and treemap

### Important Constraints
- Do not add comments unless explicitly requested
- Keep code changes minimal and focused
- Maintain the existing UI/UX patterns
- Preserve cross-platform compatibility
- Do not commit without user approval

### Style Consistency
When making changes:
- Use 4-space indentation (as in existing code)
- Snake case for functions/variables
- PascalCase for classes
- Max line length ~79 chars (but not strictly enforced)
- No trailing whitespace
- Descriptive names over short names

## Integration Points

The application could be extended with:
- File system watchers for auto-refresh
- Export functionality (images, reports)
- Database for scan history
- Network scanning capabilities
- Plugin system for custom renderers

## Troubleshooting

If the application has issues:
1. Check Python version (`python --version`)
2. Verify write permissions in working directory
3. Ensure Tkinter is available (usually included with Python)
4. Look for error dialogs from failed operations
5. Check console for error messages

## Resources

- **Kilo Documentation**: https://kilo.ai/docs
- **Tkinter Reference**: Standard Python library docs
- **Treemap Algorithms**: Academic literature on visualization
- **SpaceMonger**: Original application (historical reference)

## Maintenance

### Regular Tasks
- No scheduled maintenance (self-contained application)
- Dependencies are from Python stdlib (no version conflicts)
- Code updates should focus on features, not infrastructure

### Version Control
- Git-friendly (text-based, single file)
- Small diffs for most changes
- Easy to review and merge

---

*This configuration helps Kilo agents understand the project structure, workflows, and best practices for working with this codebase.*
