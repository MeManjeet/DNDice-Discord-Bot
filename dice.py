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
    
    def _format_roll(self, base_roll: int, modified_roll: int, sides: int) -> str:
        """Format a single roll with special handling for d20 nat 1/20."""
        if sides == 20:
            if base_roll == 20:
                return f"**{modified_roll}**"  # Nat 20 - bold the result
            elif base_roll == 1:
                return "**Nat1**"  # Nat 1 - no modifier applied
        return str(modified_roll)
    
    def _get_sides(self, notation: str) -> int:
        """Extract die sides from notation like '1d20' or '2d6'."""
        import re
        match = re.search(r'd(\d+)', notation.lower())
        return int(match.group(1)) if match else 0
    
    def format(self) -> str:
        if self.modifier == 0:
            parts = []
            for notation, rolls in self.dice_pools:
                sides = self._get_sides(notation)
                formatted_rolls = []
                for r in rolls:
                    if sides == 20 and r == 20:
                        formatted_rolls.append("**20**")
                    elif sides == 20 and r == 1:
                        formatted_rolls.append("**Nat1**")
                    else:
                        formatted_rolls.append(str(r))
                rolls_str = ", ".join(formatted_rolls)
                parts.append(f"{notation.upper()} Result - ({rolls_str})")
            return "\n".join(parts)
        else:
            mod_sign = "+" if self.modifier > 0 else ""
            parts = []
            for idx, (notation, base_rolls) in enumerate(self.dice_pools):
                sides = self._get_sides(notation)
                modified = self.modified_rolls[idx]
                
                base_parts = []
                calc_parts = []
                result_parts = []
                
                for i, base_roll in enumerate(base_rolls):
                    if sides == 20 and base_roll == 20:
                        base_parts.append("**20**")
                        calc_parts.append(f"(**20**{mod_sign}{self.modifier})")
                        result_parts.append(f"**{modified[i]}**")
                    elif sides == 20 and base_roll == 1:
                        base_parts.append("**Nat1**")
                        calc_parts.append("(**Nat1**)")
                        result_parts.append("**Nat1**")
                    else:
                        base_parts.append(str(base_roll))
                        calc_parts.append(f"({base_roll}{mod_sign}{self.modifier})")
                        result_parts.append(str(modified[i]))
                
                base_str = ", ".join(base_parts)
                calc_str = " ".join(calc_parts)
                result_str = ", ".join(result_parts)
                parts.append(f"{notation.upper()} Result - ({base_str}) = {calc_str} = ({result_str})")
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
    """
    Parse repeat count and dice expression with smart defaults.
    
    Examples:
        "" or "d20"        -> (1, "1d20")
        "+3" or "+ 3"      -> (1, "1d20+3")
        "10"               -> (10, "1d20")
        "10 +2"            -> (10, "1d20+2")
        "2d6+3"            -> (1, "2d6+3")
        "5 2d6+3"          -> (5, "2d6+3")
    """
    args = args.strip()
    
    # Empty args -> default 1d20
    if not args:
        return 1, "1d20"
    
    # Normalize spaces around +/- but preserve them for detection
    # Check if starts with +/- (modifier only, no dice)
    normalized = args.replace(" ", "")
    
    # Case: just a modifier like "+3" or "-5" -> 1d20 with that modifier
    if re.match(r'^[+-]\d+$', normalized):
        return 1, f"1d20{normalized}"
    
    # Case: starts with +/- but has more (like "+ 3" with space)
    if args.lstrip().startswith('+') or args.lstrip().startswith('-'):
        # Extract the modifier part
        mod_match = re.match(r'^([+-])\s*(\d+)(.*)$', args.strip())
        if mod_match:
            sign, num, rest = mod_match.groups()
            rest = rest.strip()
            if not rest:
                # Just modifier: "+3" -> 1d20+3
                return 1, f"1d20{sign}{num}"
            elif 'd' in rest.lower():
                # Modifier then dice? Weird but handle: "+3 2d6" -> probably an error
                raise ValueError("Put dice notation before modifier: e.g., 2d6+3")
    
    tokens = args.split()
    first_token = tokens[0].strip()
    
    # Case: first token is just a number -> repeat count for 1d20
    if first_token.isdigit():
        repeat_count = int(first_token)
        if repeat_count < 1 or repeat_count > 20:
            raise ValueError("Repeat count must be 1-20")
        
        if len(tokens) == 1:
            # Just "10" -> 10x 1d20
            return repeat_count, "1d20"
        
        # Rest of tokens form the dice expression
        rest = "".join(tokens[1:]).replace(" ", "")
        
        # Check if rest is just a modifier
        if re.match(r'^[+-]\d+$', rest):
            # "10 +2" -> 10x 1d20+2
            return repeat_count, f"1d20{rest}"
        
        # Check if rest contains dice
        if 'd' in rest.lower():
            return repeat_count, rest
        
        raise ValueError(f"Invalid notation after count: {rest}")
    
    # Case: first token contains 'd' -> dice notation
    if 'd' in first_token.lower():
        dice_expr = normalized
        # Handle "d20" -> "1d20" (add implicit 1)
        dice_expr = re.sub(r'(?<![0-9])d', '1d', dice_expr, flags=re.IGNORECASE)
        return 1, dice_expr
    
    # Case: no 'd' at all, not a number - check if it's modifier-like
    raise ValueError(f"Invalid dice notation: {args}")


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
