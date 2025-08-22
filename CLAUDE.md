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

## Recent Work
- Added Scrivener plugin integration for tracking Scrivener project metadata
- Working on `scrivener_remake` branch for testing on multiple machines