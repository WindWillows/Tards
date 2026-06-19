# Agent Instructions

This is the root instruction file for AI agents working on the Tards project.

For detailed rules, conventions, and domain-specific guidance, see:

- `docs/AGENTS.md` — full agent instructions (critical rules, architecture, test framework)
- `docs/ARCHITECTURE.md` — system architecture
- `docs/TARDS_GAME_REFERENCE.md` — game mechanics reference

## Quick Reference

- **Source root**: `TARDS(demo)/`
- **Entry point**: `TARDS(demo)/Gamestart.py`
- **Tests**: `python tests/run.py`
- **Package/EXE**: `cd TARDS(demo) && pyinstaller --noconfirm Tards.spec`
- **Dependencies**: `pip install -r TARDS(demo)/requirements.txt`

## Directory Layout

- `TARDS(demo)/tards/` — game engine
  - `cards/` — card type hierarchy
  - `core/` — board, player, cost, targeting, auras, etc.
  - `data/` — card database, deck builder, deck IO
  - `game/` — Game controller mixins
  - `net/` — network duel and protocol
- `TARDS(demo)/card_pools/` — card packs and effects
- `TARDS(demo)/gui/` — tkinter UI
- `tests/` — regression tests using the built-in zero-dependency runner
- `pygame_client/` — experimental Pygame client, not wired into the main game
- `agent_team/`, `config/`, `.agents/` — AI development tooling, not part of the game

## Critical Reminders

1. Never hard-code card-specific logic in the core engine.
2. Never interpret Chinese game terms by their everyday meaning; check the codebase or rule docs.
3. When in doubt about mechanics, ask the user instead of guessing.
4. Prefer adding reusable utilities in `effect_utils.py` over one-off hacks.
5. Run `python tests/run.py` after non-trivial changes.
