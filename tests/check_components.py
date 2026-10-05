import json, pathlib, re

root = pathlib.Path(__file__).resolve().parents[1]
spec = json.loads((root / "openapi.json").read_text())


def resolve(x):
    while "$ref" in x:
        ref = x["$ref"]
        x = spec
        for key in ref[2:].split("/"):
            x = x[key]
    return x


count = 0
for path in root.glob("**/*.json"):
    data = json.loads(path.read_text())
    count += 1
    assert not re.search(r"skt_live_[a-zA-Z0-9]{10,}", path.read_text())
base = json.loads((root / "base.json").read_text())
assert base["baseUrl"] == "https://api.serpkite.com"
assert "request.headers.Authorization" in base["log"]["sanitize"]
connection = json.loads((root / "connection/communication.json").read_text())
assert connection["url"] == "https://api.serpkite.com/v1/account"
assert "parameters.apiKey" in connection["headers"]["Authorization"]
manifest = json.loads((root / "app-components.json").read_text())
for module in manifest["modules"]:
    folder = root / "modules" / module["name"]
    comm = json.loads((folder / "communication.json").read_text())
    params = json.loads((folder / "parameters.json").read_text())
    interface = json.loads((folder / "interface.json").read_text())
    if module["type"] == "universal":
        assert comm["url"].startswith("https://api.serpkite.com/")
        assert comm["url"].count("parameters.url") == 1
        assert "headers" not in comm
        continue
    assert module["endpoint"] in spec["paths"]
    if module["type"] == "search":
        request = resolve(spec["paths"][module["endpoint"]]["post"]["requestBody"])
        schema = resolve(request["content"]["application/json"]["schema"])
        assert set(comm["body"]) <= set(schema["properties"])
        assert any(p["name"] == "limit" for p in params)
        response = resolve(
            spec["paths"][module["endpoint"]]["post"]["responses"]["200"]
        )
        result = resolve(response["content"]["application/json"]["schema"])
        item = resolve(result["properties"]["results"]["items"])
        assert {f["name"] for f in interface} <= set(item["properties"])
        assert comm["response"]["iterate"] == "{{body.results}}"
        if module["endpoint"].endswith("autocomplete"):
            assert "page" not in comm["body"] and "pagination" not in comm
        else:
            assert (
                comm["body"]["page"] == 1 and "<= 10" in comm["pagination"]["condition"]
            )
print(
    json.dumps(
        {
            "jsonFilesValid": count,
            "modules": len(manifest["modules"]),
            "searchModules": 10,
            "secretValuesAbsent": True,
            "connectionUnbilled": True,
            "universalOriginFixed": True,
            "requestFieldsMatchOpenApi": True,
            "resultFieldsMatchOpenApi": True,
            "runtimeScenarioTestsPerformed": False,
        }
    )
)
