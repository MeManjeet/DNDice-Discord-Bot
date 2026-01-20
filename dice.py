import secrets
import re
from dataclasses import dataclass
from typing import List, Tuple


def roll_single_die(sides: int) -> int:
    """Roll a single die with cryptographically secure randomness."""
    return 1 + secrets.randbelow(sides)


@dataclass
class RollResult:
    """Result of roll command - modifier applied per die across all dice pools."""
    expression: str
    dice_pools: List[Tuple[str, List[int]]]  # (notation, base_rolls)
    modifier: int
    modified_rolls: List[List[int]]  # Each pool's modified rolls
    
    def format(self) -> str:
        if self.modifier == 0:
            parts = []
            for notation, rolls in self.dice_pools:
                rolls_str = ", ".join(str(r) for r in rolls)
                parts.append(f"{notation.upper()} Result - ({rolls_str})")
            return "\n".join(parts)
        else:
            mod_sign = "+" if self.modifier > 0 else ""
            parts = []
            for idx, (notation, base_rolls) in enumerate(self.dice_pools):
                modified = self.modified_rolls[idx]
                base_str = ", ".join(str(r) for r in base_rolls)
                calc_parts = [f"({r}{mod_sign}{self.modifier})" for r in base_rolls]
                result_str = ", ".join(str(r) for r in modified)
                parts.append(f"{notation.upper()} Result - ({base_str}) = {' '.join(calc_parts)} = ({result_str})")
            return "\n".join(parts)



@dataclass
class DmgResult:
    """Result of damage roll - all dice summed per pool, then modifier added."""
    expression: str
    components: List[Tuple[str, List[int], int]]  # (notation, rolls, subtotal)
    modifier: int
    total: int
    
    def format(self) -> str:
        parts = []
        for notation, rolls, subtotal in self.components:
            rolls_str = ", ".join(str(r) for r in rolls)
            parts.append(f"({rolls_str})")
        
        if self.modifier != 0:
            parts.append(f"[{self.modifier:+d}]")
        
        return " + ".join(parts) + f" = {self.total}"


def parse_dice_only(notation: str) -> Tuple[int, int]:
    """Parse dice notation without modifier (e.g., '2d6')."""
    notation = notation.lower().strip()
    pattern = r'^(\d*)d(\d+)$'
    match = re.match(pattern, notation)
    
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")
    
    count_str, sides_str = match.groups()
    dice_count = int(count_str) if count_str else 1
    dice_sides = int(sides_str)
    
    if dice_count < 1 or dice_count > 100:
        raise ValueError("Dice count must be 1-100")
    if dice_sides < 1 or dice_sides > 1000:
        raise ValueError("Dice sides must be 1-1000")
    
    return dice_count, dice_sides


def roll_dice(expression: str) -> RollResult:
    """
    Roll with modifier applied to EACH die across ALL dice pools.
    Example: 3d8 + 2d6 + 5 -> each die in 3d8 and 2d6 gets +5
    """
    expression = expression.replace(" ", "")
    
    # Parse into tokens
    expr = re.sub(r'([+-])', r' \1 ', expression)
    tokens = expr.split()
    
    dice_pools = []
    modifier = 0
    current_sign = 1
    
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        
        if token == '+':
            current_sign = 1
        elif token == '-':
            current_sign = -1
        elif 'd' in token.lower():
            count, sides = parse_dice_only(token)
            rolls = [roll_single_die(sides) for _ in range(count)]
            dice_pools.append((token, rolls))
            current_sign = 1
        else:
            try:
                value = int(token)
                modifier += current_sign * value
                current_sign = 1
            except ValueError:
                raise ValueError(f"Invalid token: {token}")
    
    # Apply modifier to each die in each pool
    modified_rolls = []
    for notation, rolls in dice_pools:
        modified_rolls.append([r + modifier for r in rolls])
    
    return RollResult(
        expression=expression,
        dice_pools=dice_pools,
        modifier=modifier,
        modified_rolls=modified_rolls
    )


def roll_dmg(expression: str) -> DmgResult:
    """
    Roll damage - each dice pool summed separately, then flat modifier added.
    Example: 3d4 + 4d6 + 4 -> sum(3d4) + sum(4d6) + 4
    """
    expression = expression.replace(" ", "")
    
    expr = re.sub(r'([+-])', r' \1 ', expression)
    tokens = expr.split()
    
    components = []
    modifier = 0
    total = 0
    current_sign = 1
    
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        
        if token == '+':
            current_sign = 1
        elif token == '-':
            current_sign = -1
        elif 'd' in token.lower():
            count, sides = parse_dice_only(token)
            rolls = [roll_single_die(sides) for _ in range(count)]
            subtotal = sum(rolls)
            components.append((token, rolls, subtotal))
            total += current_sign * subtotal
            current_sign = 1
        else:
            try:
                value = int(token)
                modifier += current_sign * value
                total += current_sign * value
                current_sign = 1
            except ValueError:
                raise ValueError(f"Invalid token: {token}")
    
    return DmgResult(
        expression=expression,
        components=components,
        modifier=modifier,
        total=total
    )


def roll_with_advantage(expression: str) -> Tuple:
    """Roll twice, take higher."""
    roll1 = roll_dice(expression)
    roll2 = roll_dice(expression)
    
    total1 = sum(sum(pool) for pool in roll1.modified_rolls)
    total2 = sum(sum(pool) for pool in roll2.modified_rolls)
    
    higher = roll1 if total1 >= total2 else roll2
    return roll1, roll2, higher, max(total1, total2)


def roll_with_disadvantage(expression: str) -> Tuple:
    """Roll twice, take lower."""
    roll1 = roll_dice(expression)
    roll2 = roll_dice(expression)
    
    total1 = sum(sum(pool) for pool in roll1.modified_rolls)
    total2 = sum(sum(pool) for pool in roll2.modified_rolls)
    
    lower = roll1 if total1 <= total2 else roll2
    return roll1, roll2, lower, min(total1, total2)


def roll_character_stats() -> List[Tuple[List[int], int]]:
    """Roll 4d6 drop lowest, 6 times."""
    stats = []
    for _ in range(6):
        rolls = [roll_single_die(6) for _ in range(4)]
        sorted_rolls = sorted(rolls)
        stat_total = sum(sorted_rolls[1:])
        stats.append((rolls, stat_total))
    return stats


def parse_roll_command(args: str) -> Tuple[int, str]:
    """Parse repeat count and dice expression."""
    args = args.strip()
    
    if not args:
        raise ValueError("Missing dice notation! Usage: !roll [count] <dice>")
    
    tokens = args.split()
    first_token = tokens[0].lower()
    
    if first_token.isdigit():
        if len(tokens) < 2:
            raise ValueError("Missing dice after count!")
        
        repeat_count = int(first_token)
        dice_expr = "".join(tokens[1:]).replace(" ", "")
        
        if 'd' not in dice_expr.lower():
            raise ValueError("Invalid dice notation!")
        
        return repeat_count, dice_expr
    else:
        dice_expr = args.replace(" ", "")
        if 'd' not in dice_expr.lower():
            raise ValueError("Invalid dice notation!")
        return 1, dice_expr


def parse_char_command(args: str) -> int:
    """Parse character stats repeat count."""
    args = args.strip()
    if not args:
        return 1
    try:
        count = int(args)
        if count < 1 or count > 20:
            raise ValueError("Count must be 1-20")
        return count
    except ValueError:
        raise ValueError(f"Invalid count: {args}")
