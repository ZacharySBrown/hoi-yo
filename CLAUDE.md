# HOI-YO Project

## What This Is
A live multi-agent system where Claude-powered AI personas play Hearts of Iron IV.
See SPEC.md for the complete implementation specification.

## Tech Stack
- Python 3.11+, asyncio
- anthropic SDK for Claude API calls
- FastAPI + WebSocket for dashboard
- Jinja2 for Clausewitz template generation
- Click for CLI
- watchdog for file system monitoring
- pytest for testing

## Key Conventions
- All Clausewitz .txt output: UTF-8 WITHOUT BOM
- All localisation .yml output: UTF-8 WITH BOM
- Persona definitions live in personas/{country}/SOUL.md + config.toml
- Generated mod files go to build/hoi_yo_mod/
- Agent decision logs go to logs/ (gitignored)
- Use structured JSON output (output_config) for all Claude API calls
- Cache shared board state across parallel agent calls

## Running
- `hoi-yo run --local` for local development (manual HOI4)
- `hoi-yo run --headless` for headless server deployment
- `hoi-yo dashboard` to start dashboard only
- `pytest` for tests

## Environment
- ANTHROPIC_API_KEY in .env
- config.toml for paths and game settings
