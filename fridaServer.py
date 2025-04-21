import asyncio
import frida
import json
import re
import ast

current_turn = {}
game_origin = {}
current_match_id = 0
is_new_match = True


def select(message, _):
    payload = message.get("payload")
    if payload and payload.get("content"):
        try:
            content = (
                json.loads(payload.get("content"))
                if isinstance(payload.get("content"), str)
                else payload.get("content")
            )
        except json.JSONDecodeError:
            try:
                content = (
                    ast.literal_eval(payload.get("content"))
                    if isinstance(payload.get("content"), str)
                    else payload.get("content")
                )
            except (ValueError, SyntaxError):
                content = payload.get("content")
    else:
        content = None

    if payload and payload.get("type") == "getHints" and content and content != "{ }":
        possible_actions = content.get("selfActionHints")
        possible_actions = [
            action for action in possible_actions if action.get("canPlay")
        ]
        current_turn["possibleActions"] = possible_actions

    if payload and payload.get("type") == "gameRecord":
        game_origin["origin"] = content.get("game").get("origin")

    match = {"turns": [current_turn.copy()], "game": game_origin.copy()}
    with open("match.json", "w") as f:
        json.dump(match, f, indent=2)


def append(message, _):
    global is_new_match
    payload = message.get("payload")
    if payload and payload.get("content"):
        try:
            content = (
                json.loads(payload.get("content"))
                if isinstance(payload.get("content"), str)
                else payload.get("content")
            )
        except json.JSONDecodeError:
            try:
                content = (
                    ast.literal_eval(payload.get("content"))
                    if isinstance(payload.get("content"), str)
                    else payload.get("content")
                )
            except (ValueError, SyntaxError):
                content = payload.get("content")
    else:
        content = None

    if payload and payload.get("type") == "getHints" and content and content != "{ }":
        # print("possibleActions", content.get("selfActionHints"))
        possible_actions = content.get("selfActionHints")
        possible_actions = [
            action for action in possible_actions if action.get("canPlay")
        ]
        current_turn["possibleActions"] = possible_actions

    if payload and payload.get("type") == "gameRecord":
        # print("gameRecord", content)
        # current_turn["gameRecord"] = content.get("game").get("store")
        game_origin["origin"] = content.get("game").get("origin")

    if payload and payload.get("type") == "actionTaken":
        # Remove Pokemons field when it contains unparsed System.Collections.Generic.List
        s_fixed = re.sub(
            r"(,\s*)?Pokemons:\s*System\.Collections\.Generic\.List`1\[[^\]]+\](,\s*)?",
            lambda m: (
                ""
                if m.group(1) and m.group(2)
                else m.group(2) if m.group(1) else m.group(1) if m.group(2) else ""
            ),
            content,
        )

        # Fix JSON formatting
        for pattern, repl in [
            (r"([{,]\s*)(\w+)\s*:", r'\1"\2":'),  # Add quotes to keys
            (r":\s*([A-Za-z0-9_.]+)", r': "\1"'),  # Add quotes to simple values
            (r',\s*"([^"]+)"\s*:\s*}\s*', "}"),  # Remove empty values at end
            (r',\s*"([^"]+)"\s*:\s*$', ""),  # Remove trailing empty values
            (r",\s*}$", "}"),  # Remove trailing commas
        ]:
            s_fixed = re.sub(pattern, repl, s_fixed)

        print(s_fixed)
        current_turn["actionTaken"] = json.loads(s_fixed)

        # Check if this is a new match beginning
        if "PrepareActiveField" in content:
            is_new_match = True

        update_turns()


def update_turns():
    global current_match_id, is_new_match

    try:
        with open("train.json", "r") as f:
            data = json.load(f)
            matches = data.get("matches", [])
    except (FileNotFoundError, json.JSONDecodeError):
        matches = []

    # If we need to start a new match
    if is_new_match:
        current_match_id = len(matches)
        new_match = {
            "id": current_match_id,
            "turns": [current_turn.copy()],
            "game": game_origin.copy(),
        }
        matches.append(new_match)
        is_new_match = False
    else:
        # Add to the current match if it exists
        if 0 <= current_match_id < len(matches):
            matches[current_match_id]["turns"].append(current_turn.copy())
        else:
            # Fallback if match doesn't exist
            new_match = {
                "id": len(matches),
                "turns": [current_turn.copy()],
                "game": game_origin.copy(),
            }
            matches.append(new_match)
            current_match_id = len(matches) - 1

    data = {"matches": matches}
    with open("train.json", "w") as f:
        json.dump(data, f, indent=2)


async def main(append_data=True):
    device = frida.get_usb_device()
    application = device.get_frontmost_application()
    session = device.attach(application.pid, realm="emulated")

    with open("fridaAgent.js", "r", encoding="utf-8") as f:
        js = f.read()

    script = session.create_script(js)
    script.on("message", append if append_data else select)
    script.load()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main(append_data=False))
