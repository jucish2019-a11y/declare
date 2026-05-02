"""Fetch a free public-domain card-image pack to assets/cards/.

Source: deckofcardsapi.com (free API, standard 226x314 PNGs).
Each card is a PNG in the form '<rank>_of_<suit>.png'. We translate to our
internal naming convention 'A_spade.png', '10_heart.png', 'K_club.png', etc.

If the download fails (offline / firewall), card_render falls back to the
procedural painter automatically - game still works.

NOTE: The default deckofcardsapi images are 226x314 pixels. For crisp
rendering on high-DPI / retina displays, consider replacing them with
higher-resolution assets (e.g., 500x726px from an alternate source).
Larger source images allow smoothscale to produce sharper results.

Run:
    python download_cards.py
"""
import os
import sys
import ssl
import time
import urllib.request


BASE_URL = "https://deckofcardsapi.com/static/img"

RANK_FILE = {
    "A": "A", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7",
    "8": "8", "9": "9", "10": "0", "J": "J", "Q": "Q", "K": "K",
}
SUIT_FILE = {"spade": "S", "heart": "H", "diamond": "D", "club": "C"}


def assets_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "assets", "cards")


def _download(url, dest, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        data = r.read()
    if len(data) < 200:
        raise RuntimeError(f"suspiciously small payload from {url}")
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, dest)
    return len(data)


def download_all(verbose=True):
    out = assets_dir()
    os.makedirs(out, exist_ok=True)
    fetched = 0
    skipped = 0
    failed = []

    for rank, rank_code in RANK_FILE.items():
        for suit, suit_code in SUIT_FILE.items():
            local_name = f"{rank}_{suit}.png"
            local_path = os.path.join(out, local_name)
            if os.path.exists(local_path):
                skipped += 1
                continue
            url = f"{BASE_URL}/{rank_code}{suit_code}.png"
            try:
                _download(url, local_path)
                fetched += 1
                if verbose:
                    print(f"  fetched {local_name}", flush=True)
            except Exception as e:
                failed.append((local_name, str(e)))
                if verbose:
                    print(f"  FAIL {local_name}: {e}", flush=True)
            time.sleep(0.05)

    back_path = os.path.join(out, "back_red.png")
    if not os.path.exists(back_path):
        try:
            _download(f"{BASE_URL}/back.png", back_path)
            fetched += 1
            if verbose:
                print("  fetched back_red.png", flush=True)
        except Exception as e:
            failed.append(("back.png", str(e)))

    if verbose:
        print(f"\nFetched: {fetched}    Already had: {skipped}    Failed: {len(failed)}")
    return fetched, skipped, failed


def have_assets():
    out = assets_dir()
    if not os.path.isdir(out):
        return False
    return os.path.exists(os.path.join(out, "A_spade.png"))


if __name__ == "__main__":
    print(f"Downloading playing-cards pack to {assets_dir()}")
    fetched, skipped, failed = download_all(verbose=True)
    sys.exit(0 if not failed else 1)
