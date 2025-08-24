# Flashbake Project Notes

## About This Project
Flashbake is a tool for writers that automates Git version control with metadata from their lifelog (social media, music, weather, location, etc.). It helps archive the evolution of writing work by automatically committing changes along with contextual information about the writer's environment and activities.

## Git Configuration
- **Authentication**: Uses HTTPS with stored GitHub token (SSH keys not configured)
- **Main branch**: `master` (not `main` - this is an older repo)
- **Remotes**: 
  - `origin`: ianpaul/flashbake (your fork)
  - `upstream`: cmdln/flashbake (original repo)
- **Current branch**: `scrivener_remake` (contains new Scrivener plugin)
- **Push command**: `git push origin <branch>` (not `git push master`)

## Project Structure
```
src/flashbake/
├── Core modules: commit.py, control.py, git.py, context.py
├── plugins/ - Various lifelog data sources
│   ├── scrivener.py (newly added)
│   ├── weather.py, location.py, music.py
│   ├── social: twitter.py, mastodon.py
│   └── other: lastfm.py, itunes.py, feed.py, etc.
└── Console interface: console.py
```

## Development Notes
- Plugin-based architecture for extending metadata sources
- Python project with setup.py for installation
- Test suite available in `/test/` directory
- Uses setuptools for packaging
- GPL v3 licensed

## Useful Commands
- Install: `pip install .` or `python setup.py install`
- Test: `python -m pytest test/` (check for test runner first)
- Entry points: `flashbake` and `flashbakeall` console commands

## Known Issues & Fixes
- **Scrivener Plugin**: Message plugins don't receive `hot_files` parameter, only `config`. Fixed by using shared property mechanism to pass `project_dir` between file and message plugins.
- **Scrivener Word Count**: Legacy Scrivener projects can have stale XML word count caches that don't reflect actual RTF content. Fixed by implementing hybrid validation that compares XML vs manual RTF parsing, with automatic fallback when XML seems unreliable.
- **Installation Warnings**: `setup.py install` is deprecated (deadline Oct 2025). Modern alternative: `pip install .`
- **Regex Warnings**: Invalid escape sequences in commit.py and __init__.py need fixing (e.g., `\s` → `\\s`)

## Testing Notes
- Always test plugin changes on multiple platforms - WSL vs macOS can behave differently
- Use `git status` before commits to avoid contaminating repo with build artifacts (egg-info, etc.)
- Test Scrivener plugin with both fresh projects (accurate XML) and legacy projects (potentially stale XML)

## Installation Troubleshooting
- **Setuptools caching**: If plugin changes don't take effect after reinstall, clean build artifacts: `rm -rf build/ dist/ src/flashbake.egg-info/` then reinstall
- **Multiple install locations**: Check install location with `python3 -c "import flashbake.plugins.scrivener; print(flashbake.plugins.scrivener.__file__)"` 
- **User vs system install**: May need to `pip3 uninstall flashbake` before `sudo python3 setup.py install` to avoid conflicts

## Recent Work
- Added Scrivener plugin integration for tracking Scrivener project metadata
- Working on `scrivener_remake` branch for testing on multiple machines
- Fixed `hot_files` access error in scrivener plugin (worked on WSL, failed on macOS)
- Implemented hybrid word count validation for Scrivener plugin to handle legacy projects with stale XML caches
- Enhanced git-based word count change tracking with proper error handling and fallback mechanisms