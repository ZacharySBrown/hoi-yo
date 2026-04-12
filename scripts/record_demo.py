"""Record a demo video of the hoi-yo dashboard using Playwright.

Waits for agent data to appear, then navigates through the dashboard
tabs and panels to showcase the UI. Outputs an MP4 and a GIF.

Usage:
    python scripts/record_demo.py [--turns N] [--output PATH]
"""

import asyncio
import sys
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright

DASHBOARD_URL = "http://localhost:8080/dashboard"
VIEWPORT = {"width": 1440, "height": 900}
TAGS = ["USA", "GER", "SOV", "ENG", "JAP", "ITA"]


async def wait_for_turn_data(page, min_turns: int = 2, timeout_minutes: int = 15):
    """Wait until the dashboard has processed at least min_turns."""
    print(f"Waiting for {min_turns} turn(s) of agent data (up to {timeout_minutes}m)...")
    deadline = asyncio.get_event_loop().time() + timeout_minutes * 60
    last_turn = 0
    while asyncio.get_event_loop().time() < deadline:
        turn_el = await page.query_selector("#turn-number")
        if turn_el:
            text = await turn_el.inner_text()
            try:
                turn = int(text.strip().replace("Turn ", "").replace("#", ""))
                if turn != last_turn:
                    print(f"  Turn {turn} processed...")
                    last_turn = turn
                if turn >= min_turns:
                    print(f"  Got {turn} turns. Starting recording.")
                    return turn
            except ValueError:
                pass
        await asyncio.sleep(5)
    print(f"  Timeout after {timeout_minutes}m with {last_turn} turns. Recording anyway.")
    return last_turn


async def record(min_turns: int = 2, output_dir: str = "."):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    video_path = output_path / "demo_raw"
    video_path.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=str(video_path),
            record_video_size=VIEWPORT,
        )
        page = await context.new_page()

        # Navigate to dashboard
        await page.goto(DASHBOARD_URL)
        await page.wait_for_load_state("networkidle")
        print("Dashboard loaded.")

        # Wait for real data
        turns = await wait_for_turn_data(page, min_turns=min_turns)
        if turns == 0:
            print("No turn data available. Make sure HOI4 is running and autosaving.")
            await browser.close()
            return None

        # Small pause to let the last turn's data fully render
        await asyncio.sleep(2)

        # ── Recording sequence ──────────────────────────────────────

        # 1. Overview shot - show the full dashboard
        print("Recording: Overview...")
        await asyncio.sleep(3)

        # 2. Hover over diplomatic web nodes
        print("Recording: Diplomatic web...")
        for tag in TAGS:
            node = await page.query_selector(f'.diplo-node[data-tag="{tag}"]')
            if node:
                await node.hover()
                await asyncio.sleep(1.2)

        # 3. Click through nation cards to expand them
        print("Recording: Nation cards...")
        for tag in TAGS[:3]:  # Show 3 expanded cards
            card = await page.query_selector(f'.nation-card[data-tag="{tag}"]')
            if card:
                await card.click()
                await asyncio.sleep(2.5)
                # Click again to collapse
                await card.click()
                await asyncio.sleep(0.5)

        # 4. Click through agent mind tabs - the star of the show
        print("Recording: Agent minds (inner monologues)...")
        for tag in TAGS:
            tab = await page.query_selector(f'.minds-tab[data-tag="{tag}"]')
            if tab:
                await tab.click()
                await asyncio.sleep(3)

                # Scroll the mind content to show strategies
                content = await page.query_selector("#minds-content")
                if content:
                    await content.evaluate("el => el.scrollTop = 0")
                    await asyncio.sleep(1)
                    await content.evaluate("el => el.scrollBy(0, 300)")
                    await asyncio.sleep(2)

        # 5. Final overview
        print("Recording: Final overview...")
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(3)

        # ── Save video ──────────────────────────────────────────────

        await context.close()
        await browser.close()

        # Find the recorded video file
        video_files = list(video_path.glob("*.webm"))
        if not video_files:
            print("Error: No video file generated.")
            return None

        raw_video = video_files[0]
        final_mp4 = output_path / "demo.mp4"
        final_gif = output_path / "demo.gif"

        # Convert to MP4 (smaller, better quality)
        print(f"Converting to MP4...")
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_video),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-vf", "fps=24",
            "-movflags", "+faststart",
            str(final_mp4),
        ], capture_output=True)

        # Convert to GIF (for README inline display, shorter/smaller)
        print(f"Converting to GIF (first 30s)...")
        subprocess.run([
            "ffmpeg", "-y", "-i", str(raw_video),
            "-t", "30",
            "-vf", "fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            str(final_gif),
        ], capture_output=True)

        # Cleanup raw
        raw_video.unlink(missing_ok=True)
        video_path.rmdir()

        mp4_size = final_mp4.stat().st_size / 1024 / 1024 if final_mp4.exists() else 0
        gif_size = final_gif.stat().st_size / 1024 / 1024 if final_gif.exists() else 0
        print(f"\nDone!")
        print(f"  MP4: {final_mp4} ({mp4_size:.1f} MB)")
        print(f"  GIF: {final_gif} ({gif_size:.1f} MB)")
        return final_mp4


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", type=int, default=2, help="Wait for N turns before recording")
    parser.add_argument("--output", default=".", help="Output directory")
    args = parser.parse_args()
    asyncio.run(record(min_turns=args.turns, output_dir=args.output))
