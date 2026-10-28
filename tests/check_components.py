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
assert base["timeout"] == "{{common.timeout}}"
assert 40000 < json.loads((root / "common.json").read_text())["timeout"] <= 300000
assert "request.headers.Authorization" in base["log"]["sanitize"]
connection = json.loads((root / "connection/communication.json").read_text())
assert connection["url"] == "https://api.serpkite.com/v1/account"
assert "parameters.apiKey" in connection["headers"]["Authorization"]
manifest = json.loads((root / "app-components.json").read_text())
groups = json.loads((root / "groups.json").read_text())
assert sorted(m for g in groups for m in g["modules"]) == sorted(m["name"] for m in manifest["modules"])
assert [g for g in groups if g["label"] == "Other"][0]["modules"] == ["makeAnApiCall"]
for module in manifest["modules"]:
    folder = root / "modules" / module["folder"]
    comm = json.loads((folder / "communication.json").read_text())
    params = json.loads((folder / "parameters.json").read_text())
    interface = json.loads((folder / "interface.json").read_text())
    sample = json.loads((folder / "sample.json").read_text())
    proper = ["Google Maps", "Google AI Mode", "API", "ChatGPT", "Gemini", "Copilot Search", "Brave AI", "URLs"]
    rest = module["label"][1:]
    for noun in proper:
        rest = rest.replace(noun, noun.lower())
    assert rest == rest.lower(), module["label"]
    if module["type"] == "universal":
        assert comm["url"] == "https://api.serpkite.com/{{parameters.url}}"
        assert [p["name"] for p in params] == ["url", "method", "headers", "qs", "body"]
        assert module["label"] == "Make an API call"
        continue
    path = module["endpoint"].replace("{{parameters.id}}", "{id}")
    assert path in spec["paths"], path
    assert set(sample) <= {f["name"] for f in interface}, module["name"]
    if comm["method"] == "POST":
        request = resolve(spec["paths"][path]["post"]["requestBody"])
        schema = resolve(request["content"]["application/json"]["schema"])
        props = dict(schema.get("properties", {}))
        for part in schema.get("allOf", []):
            props.update(resolve(part).get("properties", {}))
        assert set(comm["body"]) <= set(props), (module["name"], set(comm["body"]) - set(props))
        assert {p["name"] for p in params} - {"limit"} <= set(props) | {"limit"}
        assert "timeout" not in comm  # the base's common timeout applies
    if module["type"] == "search" and comm["method"] == "GET":
        op = spec["paths"][module["endpoint"]]["post"]
        request = resolve(op["requestBody"])
        schema = resolve(request["content"]["application/json"]["schema"])
        assert comm["method"] == "GET" and set(comm["qs"]) <= set(schema["properties"])
        assert [p["name"] for p in params if p.get("required")] == ["q"]
        limit = [p for p in params if p["name"] == "limit"][0]
        assert limit["type"] == "uinteger" and limit["default"] == 10 and not limit.get("required") and not limit.get("advanced")
        response = resolve(op["responses"]["200"])
        result = resolve(response["content"]["application/json"]["schema"])
        item = resolve(result["properties"]["results"]["items"])
        assert {f["name"] for f in interface} <= set(item["properties"])
        assert comm["response"] == {"limit": "{{parameters.limit}}", "iterate": "{{body.results}}", "output": "{{item}}"}
        if module["endpoint"].endswith("autocomplete"):
            assert "pagination" not in comm
        else:
            assert comm["pagination"]["qs"] == {"page": "{{pagination.page}}"} and set(comm["pagination"]) == {"qs", "condition"}
            assert "body.request.page < 10" in comm["pagination"]["condition"]
print(
    json.dumps(
        {
            "jsonFilesValid": count,
            "modules": len(manifest["modules"]),
            "searchModules": sum(m["type"] == "search" for m in manifest["modules"]),
            "secretValuesAbsent": True,
            "connectionUnbilled": True,
            "universalOriginFixed": True,
            "requestFieldsMatchOpenApi": True,
            "resultFieldsMatchOpenApi": True,
            "runtimeScenarioTestsPerformed": False,
        }
    )
)
