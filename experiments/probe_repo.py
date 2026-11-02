"""probe_repo.py -- what does the Squares Project actually publish above n=324?"""
import json
import re
import urllib.request

API = "https://api.github.com/repos/jlevy/squares/git/trees/"


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=60))


main = get(API + "main")
packing = next(x["sha"] for x in main["tree"] if x["path"] == "packing")
sub = {x["path"]: x["sha"] for x in get(API + packing)["tree"]}

for name in ("atlas", "frontier", "cases"):
    try:
        top = get(API + sub[name])
    except KeyError:
        continue
    print(f"== {name}")
    for entry in top["tree"]:
        if entry["type"] != "tree":
            continue
        kids = [y["path"] for y in get(API + entry["sha"])["tree"]]
        nums = sorted(int(m.group(1)) for k in kids if (m := re.match(r"n-0*(\d+)\.", k)))
        rng = (min(nums), max(nums)) if nums else None
        above = [n for n in nums if n > 324]
        print(f"   {entry['path']:<14} {len(kids):>5} files  n-range={rng}  above324={len(above)}")
        if above[:5]:
            print(f"      e.g. {above[:8]}")
