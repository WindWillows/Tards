# Agent Instructions for Tards Project

## Critical Rules

### 1. Do Not Interpret Game Terms Literally (不要望文生义)

All game-specific terms in this project have **explicit, defined meanings** in the rule system. **Never** assume the everyday meaning of a Chinese word applies to the game mechanic.

Examples of past mistakes to avoid:
- **视野 (Vision)**: Does NOT mean "can see through everything". It only allows attacking units in columns within range. It does NOT bypass **潜水 (Dive)** or **潜行 (Stealth)**.
- **潜水 (Dive)**: Makes a unit "unselectable" only during the **resolve phase**, NOT during the action phase. It can still be targeted when the player selects attack targets.
- **藤蔓 (Vine)**: An overlay that absorbs damage for its host. It is NOT a separate target on the board.
- **移动 (Move)**: An internal effect callback, NOT a player action type. It does NOT end the turn.
- **高频 (High Frequency)**: Grants multiple attack swings. It does NOT automatically require target selection unless combined with **视野 (Vision)**.

**When in doubt about a term's meaning:**
1. Check the codebase for its actual implementation.
2. Check the rule documents (`Tards规则书1.0.docx`, `rules_text.txt`).
3. Ask the user for clarification instead of guessing.

**Never** invent mechanics or behaviors based on the literal meaning of Chinese words.

### 2. Do Not Assume, Ask First (不要自作主张)

This game's design philosophy and mechanics differ significantly from conventional TCGs. **Never** apply knowledge from other card games (e.g., Hearthstone, Magic: The Gathering, Yu-Gi-Oh!) to infer how a mechanic should work.

**When in doubt:**
1. Check the codebase for existing implementations.
2. Check the rule documents (`Tards规则书1.0.docx`, `rules_text.txt`).
3. **Ask the user for clarification.** Do not guess, do not assume, do not "fill in the blanks" with general TCG knowledge.

**Never** alter card effects, resource mechanics, or game flow based on what "makes sense" in other games. The user's definition is the only authority.

### 3. No Hard-Coded Card Effects (禁止硬编码卡牌效果)

**Card effects must NEVER be implemented by hard-coding card names or special-case logic inside core game loops.**

The core game engine (`game.py`, `player.py`, `board.py`, `cards.py`) should only contain **generic mechanisms** (events, callbacks, state flags). Specific card behaviors must be implemented entirely within the card's own `effect_fn`, `special_fn`, `on_turn_start`, `on_turn_end`, or event listeners registered at deploy time.

Examples of violations to avoid:
- ❌ In `draw_phase`, checking `if m.name == "流浪商人": ...`
- ❌ In `develop_card`, checking `if player._enchanting_table_active: ...`
- ❌ In `_get_play_cost`, checking `if card.name == "耕殖": ...`
- ❌ Any `if` branch in core game logic that references a specific card name

**Correct approach:**
- ✅ Add a generic callback list (e.g., `Player._on_develop_callbacks`) and let the card append its own callback via `effect_fn`.
- ✅ Emit generic events (e.g., `EVENT_T_MAX_CHANGED`) and let the card register an EventBus listener via `special_fn`.
- ✅ Use generic state flags (e.g., `Player._skip_next_draw`) that any card can set, and let core logic check only the flag, never the card name.

When a card needs a mechanism that doesn't exist yet, **extend the generic mechanism** (add a new event type, a new callback list, or a new state flag) rather than hard-coding the card's behavior into the core loop.

### 4. Prefer Updating the Tool Library (优先更新工具库)

When implementing complex card effects, **if you find the existing APIs in `effect_utils.py` insufficient or awkward, prioritize extending the tool library** rather than writing one-off hacks or overly complex workarounds inside the card's effect function.

**Examples:**
- ❌ A card needs "two units fight each other" → do NOT write 50 lines of ad-hoc damage code in the card's `special_fn`.
- ✅ Instead, add a reusable `initiate_combat(a, b, game)` to `effect_utils.py`, then call it from the card.

**Rule of thumb:** If a pattern is needed by more than one card, or if the implementation feels "forced" with current tools, stop and ask: *"Should this be a generic utility?"*

The tool library (`effect_utils.py`, `targeting.py`, etc.) is the correct place for reusable combat, damage, movement, and state-tracking primitives. Keep card-specific files thin.

---

## Recent Architecture Changes (2026-04-19)

### Sacrifice Mechanism Refactored
- **Old model**: `game.py` temporarily injected blood, then rolled it back in `finally`. `cards.py` both killed sacrifices *and* modified `b_point`. This caused double-counting and rollback bugs when playing multiple B-cost minions.
- **New model**: `game.py` **permanently** adds blood to `active.b_point` before `card_can_play`. `cards.py` `MinionCard.effect()` **only kills sacrifices** (via `request_sacrifice` → `minion_death`). Blood deduction is handled uniformly by `Cost.pay()`.
- See `TARDS_GAME_REFERENCE.md` §3.2 / §6.4 for full flow.

### `card_can_play` Returns Detailed Reason
- `player.py` `card_can_play(serial, target)` now returns `tuple[bool, str]` instead of `bool`.
- `cost.py` added `can_afford_detail(player) -> tuple[bool, str]`.
- All callers updated: `game.py`, `gui_client.py`, `demo.py`, `demo_deckbuild.py`, `tards.py`, `tests/test_minecart.py`.
- **When writing new code that calls `card_can_play`, always unpack or index `[0]`.**

### Test Deck Mode
- `Deck.is_test_deck` flag bypasses all construction restrictions (40-card count, immersion points, pack limits, rarity limits).
- Test decks are only allowed in local play; the lobby blocks loading them.
- GUI deck builder has a checkbox; the flag is persisted in JSON save/load.
