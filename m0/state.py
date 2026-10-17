"""Story state (§4): apply an episode's state_diff, then generate the next episode from a player choice.

    python3 m0/state.py --prev out/dev/storyboard_ep1.json --choice 0 --out out/dev/storyboard_ep2.json
    python3 m0/state.py --prev ... --free "Vesna schová dopis a jde za Strážci krystalů" --out ...
"""

import argparse
import copy

import storyboard
from common import DATA, load_json, save_json


def empty_state(world):
    first = world["permissions"].get("allowed_locations", [world["locations"][0]["id"]])[0]
    return {"characters": {c["id"]: {"alive": True, "location": first, "status": "", "relations": {}, "inventory": []}
                           for c in world["characters"] if c["role"] != "npc"},
            "current_location": first, "open_threads": [], "timeline": [], "facts": [], "mood": ""}


def apply_diff(state, diff, episode_index):
    s = copy.deepcopy(state)
    if diff.get("current_location"):
        s["current_location"] = diff["current_location"]
        for ch in s["characters"].values():
            ch["location"] = diff["current_location"]
    s["open_threads"] = [t for t in s["open_threads"] if t not in diff.get("open_threads_remove", [])]
    s["open_threads"] += [t for t in diff.get("open_threads_add", []) if t not in s["open_threads"]]
    s["facts"] += [f for f in diff.get("facts_add", []) if f not in s["facts"]]
    if diff.get("timeline_add"):
        s["timeline"].append({"episode": episode_index, "event": diff["timeline_add"]})
    if diff.get("mood"):
        s["mood"] = diff["mood"]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=str(DATA / "world_m0.json"))
    ap.add_argument("--prev", required=True, help="previous episode storyboard (may carry _campaign)")
    ap.add_argument("--choice", type=int)
    ap.add_argument("--free")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    world = load_json(args.world)
    prev = load_json(args.prev)
    camp = prev.get("_campaign") or {"episode_index": 1, "state": empty_state(world), "canon_progress": []}
    state = apply_diff(camp["state"], prev.get("state_diff", {}), camp["episode_index"])
    canon = sorted(set(camp["canon_progress"]) | set(prev.get("canon_nodes_reached", [])))
    if args.free:
        chosen = args.free
    else:
        closed = [c for c in prev["choices"] if c["kind"] == "closed"]
        chosen = closed[args.choice]["text"]

    last = prev["panels"][-1]
    premise = (f"Previous episode: \"{prev['title']}\". It ended with: "
               f"{[b['text'] for b in last.get('bubbles', [])]} at {last.get('location_id')}.\n"
               f"The player chose: \"{chosen}\". Continue directly from that moment.")
    nxt_campaign = {"episode_index": camp["episode_index"] + 1, "state": state, "canon_progress": canon}
    sb = storyboard.generate(world, premise, nxt_campaign)
    sb["_campaign"] = nxt_campaign
    sb["_chosen"] = chosen
    save_json(args.out, sb)
    print(f"ep{nxt_campaign['episode_index']} '{sb['title']}' after choice: {chosen}")
    print(f"state: location={state['current_location']} threads={state['open_threads']} canon={canon}")
    for i, p in enumerate(sb["panels"]):
        print(f"  {i} {p['shot']:<13} {p['location_id']:<9} {[b['text'] for b in p.get('bubbles', [])]}")
    print("choices:", [c["text"] for c in sb["choices"]])


if __name__ == "__main__":
    main()
