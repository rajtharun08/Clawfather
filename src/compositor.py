import os
import sys
import argparse
import random
from PIL import Image, ImageEnhance

# Ensure src/ is importable
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SRC_DIR)
ASSETS_DIR = os.path.join(REPO_DIR, "assets")
OUTPUT_DIR = os.path.join(REPO_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Add SRC_DIR to path for sibling imports
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

from github_client import (
    fetch_github_metrics,
    map_streak_to_cat_rank,
    map_volume_to_loot_tier
)

def get_cat_dimensions(rank: int, canvas_height: int, raw_size: tuple[int, int]) -> tuple[int, int]:
    """
    Computes proportional width and height preserving nearest-neighbor pixel grids:
      Rank 0 (Stray): Small curled-up kitten (18% canvas height)
      Ranks 1–3 (Standing cats): Authentic upright height (35% canvas height)
      Rank 4 (Armchair Don): Broad armchair stature (44% canvas height)
    """
    raw_w, raw_h = raw_size
    if rank == 0:
        cat_h = int(canvas_height * 0.18)
    elif rank in (1, 2, 3):
        cat_h = int(canvas_height * 0.35)
    else:
        cat_h = int(canvas_height * 0.44)

    cat_w = int(cat_h * (raw_w / raw_h))
    return cat_w, cat_h

def get_prop_dimensions(tier: int, canvas_width: int, raw_size: tuple[int, int]) -> tuple[int, int]:
    """
    Computes small, grounded floor item dimensions:
      Tier 0 (Sardine tin): 8% canvas width (~110px)
      Tier 1 (Cash & watch): 10% canvas width (~137px)
      Tier 2 (Syndicate crate): 13% canvas width (~178px)
    """
    raw_w, raw_h = raw_size
    if tier == 0:
        prop_w = int(canvas_width * 0.08)
    elif tier == 1:
        prop_w = int(canvas_width * 0.10)
    else:
        prop_w = int(canvas_width * 0.13)

    prop_h = int(prop_w * (raw_h / raw_w))
    return prop_w, prop_h

def build_profile_tracker_gif(
    cat_rank: int,
    loot_tier: int,
    output_path: str = os.path.join(OUTPUT_DIR, "profile_tracker.gif"),
    num_frames: int = 8,
    frame_duration_ms: int = 220
) -> str:
    """
    Renders an infinite-loop, atmospheric film-noir GIF:
      1. Ground-Plane Alignment (baseline_y = h * 0.84)
      2. Idle Cat Breathing Cycle (vertical translation [0, -1, -2, -1, 0, 1, 2, 1] px)
      3. Streetlamp Flicker (irregular brightness modulation)
      4. Procedural Film-Noir Grain Matrix
    """
    bg_path = os.path.join(ASSETS_DIR, "background.png")
    cat_path = os.path.join(ASSETS_DIR, f"cat_tier_{cat_rank}.png")
    prop_path = os.path.join(ASSETS_DIR, f"prop_tier_{loot_tier}.png")

    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Missing background asset at {bg_path}")
    if not os.path.exists(cat_path):
        raise FileNotFoundError(f"Missing cat sprite at {cat_path}")
    if not os.path.exists(prop_path):
        raise FileNotFoundError(f"Missing prop sprite at {prop_path}")

    bg_raw = Image.open(bg_path).convert("RGBA")
    w, h = bg_raw.size

    # 1. Ground Plane Alignment Baseline (84% of canvas height)
    baseline_y = int(h * 0.84) # 645 px

    # 2. Prepare Cat Sprite
    cat_raw = Image.open(cat_path).convert("RGBA")
    cat_w, cat_h = get_cat_dimensions(cat_rank, h, cat_raw.size)
    cat_sprite = cat_raw.resize((cat_w, cat_h), Image.Resampling.NEAREST)

    # 3. Prepare Loot Prop Sprite
    prop_raw = Image.open(prop_path).convert("RGBA")
    prop_w, prop_h = get_prop_dimensions(loot_tier, w, prop_raw.size)
    prop_sprite = prop_raw.resize((prop_w, prop_h), Image.Resampling.NEAREST)

    # 4. Horizontal Spacing & Centered Alignment
    # Cat centered in the middle of the alley (X ~ 53%)
    cat_center_x = int(w * 0.53)
    cat_x = cat_center_x - cat_w // 2
    cat_base_y = baseline_y - cat_h

    # Loot placed on the sidewalk to the cat's left with a natural 34px safety gap
    gap = int(w * 0.025)
    prop_x = cat_x - prop_w - gap
    prop_y = baseline_y - prop_h

    # 5. Atmospheric Micro-Animation Parameters
    breath_offsets = [0, -1, -2, -1, 0, 1, 2, 1]
    flicker_factors = [1.00, 0.96, 1.03, 0.94, 1.01, 0.97, 1.04, 0.98]

    frames = []
    for i in range(num_frames):
        # Base canvas frame
        frame = bg_raw.copy()

        # Streetlamp voltage flicker
        enhancer = ImageEnhance.Brightness(frame)
        frame = enhancer.enhance(flicker_factors[i % len(flicker_factors)])

        # Paste Anchored Loot (firmly grounded on pavement, 0px translation)
        frame.paste(prop_sprite, (prop_x, prop_y), prop_sprite)

        # Paste Breathing Cat (subtle vertical translation)
        offset_y = breath_offsets[i % len(breath_offsets)]
        frame.paste(cat_sprite, (cat_x, cat_base_y + offset_y), cat_sprite)

        # Film-Noir procedural grain matrix (vintage 1940s projector texture)
        noise = Image.effect_noise((w // 4, h // 4), sigma=12).resize((w, h), Image.Resampling.NEAREST).convert("RGBA")
        noise.putalpha(14)
        frame = Image.alpha_composite(frame, noise)

        # Quantize to high-fidelity 128-color palette for compact GIF size
        frame_p = frame.convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        frames.append(frame_p)

    # Save animated GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True
    )
    size_kb = os.path.getsize(output_path) / 1024
    print(f"[The Clawfather Compositor] Successfully generated {output_path} ({num_frames} frames, {size_kb:.1f} KB)")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="The Clawfather (The Cat Syndicate Activity Engine) Compositor")
    parser.add_argument("--streak", type=int, default=None, help="Consecutive commit streak in days")
    parser.add_argument("--commits", type=int, default=None, help="Commits in the last 24 hours / today")
    parser.add_argument("--username", type=str, default=None, help="GitHub username to query")
    parser.add_argument("--output", type=str, default=os.path.join(OUTPUT_DIR, "profile_tracker.gif"), help="Output path")
    args = parser.parse_args()

    # Determine streak and commits
    if args.streak is not None and args.commits is not None:
        streak_days = args.streak
        commits_today = args.commits
        cat_rank = map_streak_to_cat_rank(streak_days)
        loot_tier = map_volume_to_loot_tier(commits_today)
    else:
        streak_days, commits_today, cat_rank, loot_tier = fetch_github_metrics(username=args.username)

    rank_names = [
        "Rank 0: The Scavenger (Shivering Stray)",
        "Rank 1: The Street Runner (Newsie Cat)",
        "Rank 2: The Alley Enforcer (Vest & Cigar)",
        "Rank 3: The Made Cat (Flat Cap & Cigar)",
        "Rank 4: The Clawfather (Don in Armchair)"
    ]
    loot_names = [
        "Tier 0: The Scraps (Sardine Tin)",
        "Tier 1: The Cut (Cash & Pocket Watch)",
        "Tier 2: The Vault (Open Syndicate Crate)"
    ]

    print(f"[The Clawfather] Streak: {streak_days} days -> {rank_names[cat_rank]}")
    print(f"[The Clawfather] Commits Today: {commits_today} -> {loot_names[loot_tier]}")

    build_profile_tracker_gif(cat_rank=cat_rank, loot_tier=loot_tier, output_path=args.output)

if __name__ == "__main__":
    main()
