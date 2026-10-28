"""Uploads the generated components to the Make app (us2). Token: ~/.serpkite/make-api-token.txt."""

import json, pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parent
APP, VERSION, CONN = "serpkite-krmli2", 1, "serpkite-krmli2"
API = "https://us2.make.com/api/v2/sdk/apps"
TOKEN = (pathlib.Path.home() / ".serpkite/make-api-token.txt").read_text().strip()


def call(method, path, data=None, jsonc=False, full=False):
    # curl, not urllib: python.org builds lack a CA bundle here.
    ctype = "application/jsonc" if jsonc else "application/json"
    args = ["curl", "-s", "-w", "\n%{http_code}", "-X", method, API + path, "-H", f"Authorization: Token {TOKEN}", "-H", f"Content-Type: {ctype}"]
    if data is not None:
        args += ["--data-binary", "@-"]
    out = subprocess.run(args, input=None if data is None else json.dumps(data), capture_output=True, text=True).stdout
    text, _, status = out.rpartition("\n")
    return int(status), text if full else text[:400]


def load(p):
    return json.loads((root / p).read_text())


results = []
def run(desc, *a, **k):
    status, text = call(*a, **k)
    results.append((desc, status))
    print(status, desc, "" if status < 300 else text)


manifest = load("app-components.json")
TYPES = {"action": 4, "search": 9, "universal": 12}
status, text = call("GET", f"/{APP}/{VERSION}/modules", full=True)
existing = {m["name"]: m for m in json.loads(text)["appModules"]}
for m in manifest["modules"]:
    if m["name"] not in existing:
        body = {"name": m["name"], "typeId": TYPES[m["type"]], "label": m["label"], "description": m["description"], "connection": CONN}
        if m["crud"]:
            body["crud"] = m["crud"]
        run(f"{m['name']} create", "POST", f"/{APP}/{VERSION}/modules", body)
run("common", "PUT", f"/{APP}/{VERSION}/common", load("common.json"))
run("base", "PUT", f"/{APP}/{VERSION}/base", load("base.json"), jsonc=True)
run("connection label", "PATCH", f"/connections/{CONN}", {"label": manifest["connection"]["label"]})
run("connection api", "PUT", f"/connections/{CONN}/api", load("connection/communication.json"), jsonc=True)
run("connection parameters", "PUT", f"/connections/{CONN}/parameters", load("connection/parameters.json"), jsonc=True)
sections = {"api": "communication", "expect": "parameters", "parameters": "static-parameters", "interface": "interface", "samples": "sample"}
for m in manifest["modules"]:
    meta = {"label": m["label"], "description": m["description"]}
    run(f"{m['name']} meta", "PATCH", f"/{APP}/{VERSION}/modules/{m['name']}", meta)
    if m["crud"]:
        run(f"{m['name']} crud", "PATCH", f"/{APP}/{VERSION}/modules/{m['name']}", {"crud": m["crud"]})
    for section, file in sections.items():
        run(f"{m['name']} {section}", "PUT", f"/{APP}/{VERSION}/modules/{m['name']}/{section}", load(f"modules/{m['folder']}/{file}.json"), jsonc=True)
for m in manifest["modules"]:
    if not existing.get(m["name"], {}).get("public"):
        run(f"{m['name']} public", "POST", f"/{APP}/{VERSION}/modules/{m['name']}/public")
run("groups", "PUT", f"/{APP}/{VERSION}/groups", load("groups.json"), jsonc=True)
failed = [d for d, s in results if s >= 300]
print("failed:", failed)
sys.exit(1 if failed else 0)
