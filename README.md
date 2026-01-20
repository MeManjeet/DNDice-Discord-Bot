# D&D Dice Bot for Discord

A Discord bot for rolling dice in D&D sessions.

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!roll [n] <dice>` | Per-die modifier (each die gets +mod) | `!roll 3d6+2` → each die +2 |
| `!dmg [n] <dice>` | Damage (sum all, then add mod) | `!dmg 1d12+2d6+5` |
| `!rolladv [n] <dice>` | Roll with advantage | `!rolladv 1d20+5` |
| `!rolldis [n] <dice>` | Roll with disadvantage | `!rolldis 1d20` |
| `!char [n]` | Character stats (4d6 drop lowest) | `!char 3` |

**Prefixes:** `!` `-` `/` `\`

## Roll vs Dmg

```
!roll 3d6+2  → (4+2), (2+2), (3+2) = (6, 4, 5)
!dmg 3d6+2   → (4, 2, 3) + [+2] = 11
```

## Setup

1. Get bot token from [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **Message Content Intent** in Bot settings
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add token
5. Run: `python bot.py`

## Local Testing

```bash
python test_local.py
```
