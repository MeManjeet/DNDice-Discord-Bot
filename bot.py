import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from dice import (
    roll_dice, roll_dmg, roll_with_advantage, roll_with_disadvantage,
    roll_character_stats, parse_roll_command, parse_char_command,
    RollResult, DmgResult
)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

# Multiple prefixes: ! - / \
bot = commands.Bot(command_prefix=['!', '-', '/', '\\'], intents=intents)


def format_roll_result(result: RollResult) -> str:
    return result.format()


def format_dmg_result(result: DmgResult) -> str:
    return result.format()


def add_chunked_fields(embed: discord.Embed, results: list, field_name: str = "") -> None:
    """Add results to embed, splitting across multiple fields if needed (1024 char limit)."""
    current_chunk = []
    current_length = 0
    field_count = 0
    
    for result in results:
        result_length = len(result) + 1  # +1 for newline
        
        if current_length + result_length > 1020:  # Leave some margin
            # Save current chunk and start new one
            if current_chunk:
                name = field_name if field_count == 0 else ""
                embed.add_field(name=name, value="\n".join(current_chunk), inline=False)
                field_count += 1
            current_chunk = [result]
            current_length = result_length
        else:
            current_chunk.append(result)
            current_length += result_length
    
    # Add remaining chunk
    if current_chunk:
        name = field_name if field_count == 0 else ""
        embed.add_field(name=name, value="\n".join(current_chunk), inline=False)


@bot.event
async def on_ready():
    print(f'{bot.user} connected to Discord!')
    await bot.change_presence(activity=discord.Game(name="!roll 1d20"))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing dice notation! Example: `!roll 1d20+3`")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"Error: {str(error)}")


@bot.command(name='roll', aliases=['r'])
async def roll_command(ctx, *, args: str = ""):
    """Roll with modifier applied to each die."""
    try:
        repeat_count, dice_expr = parse_roll_command(args)
        
        results = []
        for i in range(repeat_count):
            result = roll_dice(dice_expr)
            result_str = format_roll_result(result)
            
            if repeat_count == 1:
                results.append(f"**Result:** {result_str}")
            else:
                results.append(f"**Roll #{i+1}:**\n{result_str}")
        
        embed = discord.Embed(
            title=f"🎲 Rolling {dice_expr.upper()}" + (f" x{repeat_count}" if repeat_count > 1 else ""),
            color=0x5865F2
        )
        add_chunked_fields(embed, results)
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name='dmg', aliases=['damage', 'd'])
async def dmg_command(ctx, *, args: str = ""):
    """Roll damage - sum all dice, then add modifier."""
    try:
        repeat_count, dice_expr = parse_roll_command(args)
        
        results = []
        grand_total = 0
        for i in range(repeat_count):
            result = roll_dmg(dice_expr)
            result_str = format_dmg_result(result)
            grand_total += result.total
            
            if repeat_count == 1:
                results.append(f"**Result:** {result_str}")
            else:
                results.append(f"**Roll #{i+1}:**\n{result_str}")
        
        if repeat_count > 1:
            results.append(f"\n**Total Damage: {grand_total}**")
        
        embed = discord.Embed(
            title=f"⚔️ Damage: {dice_expr.upper()}" + (f" x{repeat_count}" if repeat_count > 1 else ""),
            color=0xFF4444
        )
        add_chunked_fields(embed, results)
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name='rolladv', aliases=['adv', 'ra'])
async def roll_advantage(ctx, *, args: str = ""):
    """Roll with advantage."""
    try:
        repeat_count, dice_expr = parse_roll_command(args)
        
        results = []
        for i in range(repeat_count):
            roll1, roll2, higher, higher_total = roll_with_advantage(dice_expr)
            
            if repeat_count == 1:
                results.append(f"Roll a: {roll1.format()}\nRoll b: {roll2.format()}\n**Result: {higher_total}** (higher)")
            else:
                results.append(f"**Roll #{i+1}:** {roll1.format()} | {roll2.format()} → {higher_total}")
        
        embed = discord.Embed(
            title=f"🍀 Advantage: {dice_expr.upper()}" + (f" x{repeat_count}" if repeat_count > 1 else ""),
            color=0x00FF00
        )
        add_chunked_fields(embed, results)
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name='rolldis', aliases=['dis', 'rd'])
async def roll_disadvantage(ctx, *, args: str = ""):
    """Roll with disadvantage."""
    try:
        repeat_count, dice_expr = parse_roll_command(args)
        
        results = []
        for i in range(repeat_count):
            roll1, roll2, lower, lower_total = roll_with_disadvantage(dice_expr)
            
            if repeat_count == 1:
                results.append(f"Roll a: {roll1.format()}\nRoll b: {roll2.format()}\n**Result: {lower_total}** (lower)")
            else:
                results.append(f"**Roll #{i+1}:** {roll1.format()} | {roll2.format()} → {lower_total}")
        
        embed = discord.Embed(
            title=f"💀 Disadvantage: {dice_expr.upper()}" + (f" x{repeat_count}" if repeat_count > 1 else ""),
            color=0xFF6600
        )
        add_chunked_fields(embed, results)
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name='char', aliases=['stats', 'character', 'c'])
async def roll_character_stats_command(ctx, *, args: str = ""):
    """Roll character stats (4d6 drop lowest)."""
    try:
        repeat_count = parse_char_command(args)
        
        all_blocks = []
        for block_num in range(repeat_count):
            stats = roll_character_stats()
            stat_lines = []
            grand_total = 0
            
            for i, (rolls, total) in enumerate(stats, 1):
                sorted_idx = sorted(range(4), key=lambda x: rolls[x])
                lowest = sorted_idx[0]
                
                rolls_display = []
                for j, roll in enumerate(rolls):
                    if j == lowest:
                        rolls_display.append(f"~~{roll}~~")
                    else:
                        rolls_display.append(str(roll))
                
                stat_lines.append(f"Stat #{i}: ({', '.join(rolls_display)}) = **{total}**")
                grand_total += total
            
            stat_lines.append(f"\n**Total: {grand_total}**")
            
            if repeat_count > 1:
                all_blocks.append(f"__Character #{block_num + 1}__\n" + "\n".join(stat_lines))
            else:
                all_blocks.append("\n".join(stat_lines))
        
        embed = discord.Embed(
            title="Character Stats (4d6 Drop Lowest)" + (f" x{repeat_count}" if repeat_count > 1 else ""),
            color=0x9B59B6
        )
        embed.add_field(name="Stats", value="\n\n".join(all_blocks), inline=False)
        embed.set_footer(text=f"Rolled by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"Error: {str(e)}")


@bot.command(name='help_dice', aliases=['dicehelp', 'commands'])
async def help_dice(ctx):
    embed = discord.Embed(title="🎲 D&D Dice Bot Commands", color=0x5865F2)
    
    embed.add_field(
        name="!roll / !r [n] [dice]",
        value="Default: `1d20`\n`!r` → 1d20\n`!r d20` → 1d20\n`!r +5` → 1d20+5\n`!r 10` → 10x 1d20\n`!r 5 +3` → 5x 1d20+3\n`!r 2d6+3` → per-die modifier",
        inline=False
    )
    embed.add_field(
        name="!dmg / !d [n] [dice]",
        value="Damage roll: sum all, then add modifier\n`!d 1d12+2d6+5`",
        inline=False
    )
    embed.add_field(
        name="!rolladv (!ra) / !rolldis (!rd)",
        value="Advantage/disadvantage (default: 1d20)\n`!ra` → advantage 1d20\n`!ra +5` → advantage 1d20+5",
        inline=False
    )
    embed.add_field(
        name="!char / !c [n]",
        value="Character stats (4d6 drop lowest)",
        inline=False
    )
    embed.add_field(
        name="Prefixes",
        value="`!` `-` `/` `\\`",
        inline=False
    )
    
    await ctx.send(embed=embed)


if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found!")
    else:
        bot.run(TOKEN)
