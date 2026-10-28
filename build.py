"""Generates the Make component files from the API contract (openapi.json).

openapi.json is backend/api/serp-api.yaml converted to JSON. Run: python3 build.py
"""

import json, pathlib, shutil

root = pathlib.Path(__file__).resolve().parent
spec = json.loads((root / "openapi.json").read_text())
schemas = spec["components"]["schemas"]

LIMIT_HELP = "Maximum number of results to return and work with during one execution cycle."
ERROR_MESSAGE = (
    "[{{statusCode}}{{if(body.error.code, ' / ', '')}}{{body.error.code}}] "
    "{{ifempty(body.error.message, 'The SerpKite API returned no error details.')}}"
)

# Full ISO 8601 values. Date-only fields (patent dates, start_date) stay text.
DATE_FIELDS = {"published_at", "cached_at"}
ABBREVIATIONS = {"url": "URL", "id": "ID", "pdf": "PDF", "cid": "CID", "fid": "FID", "oid": "OID", "html": "HTML", "iso": "ISO"}
PROPER = {"google": "Google", "maps": "Maps", "yandex": "Yandex"}
LABELS = {
    "q": "Query",
    "ms": "Duration (ms)",
    "latency_ms": "Latency (ms)",
    "rate_limit_rps": "Rate limit (RPS)",
    "credits_used_month": "Credits used this month",
    "next_day": "Closes next day",
    "image_links": "Image links",
    "resolved_urls": "Resolved URLs",
}
# Result fields that need request options these modules don't send
# (include_content, highlights, engine=consensus, /v1/place, engine=yandex).
OMIT = {"content", "highlights", "sources", "photos", "oid", "yandex_maps_url"}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def resolve(x):
    while "$ref" in x:
        ref, x = x["$ref"], spec
        for key in ref[2:].split("/"):
            x = x[key]
    return x


def label(name, overrides):
    if name in overrides:
        return overrides[name]
    if name in LABELS:
        return LABELS[name]
    words = name.split("_")
    out = []
    for i, w in enumerate(words):
        if w in ABBREVIATIONS:
            out.append(ABBREVIATIONS[w])
        elif w in PROPER and (i == 0 or words[0] in PROPER):
            out.append(PROPER[w])
        else:
            out.append(w.capitalize() if i == 0 else w)
    return " ".join(out)


def scalar(t):
    return {"integer": "number", "number": "number", "boolean": "boolean"}.get(t, "text")


def field(name, schema, overrides=None, only=None):
    overrides = overrides or {}
    s = resolve(schema)
    f = {"name": name, "label": label(name, overrides)}
    t = s.get("type")
    if isinstance(t, list):
        t = next(x for x in t if x != "null")
    if "oneOf" in s:
        t = "string"
    if t == "array":
        items = resolve(s["items"])
        if items.get("type") == "object":
            f.update(type="array", spec={"type": "collection", "spec": fields(items, overrides)})
        else:
            f.update(type="array", spec={"type": scalar(items.get("type"))})
    elif t == "object" and "properties" in s:
        f.update(type="collection", spec=fields(s, overrides, only))
    elif t == "object" and name == "opening_hours":
        f.update(type="collection", spec=[{"name": d.capitalize(), "label": d.capitalize(), "type": "text"} for d in WEEKDAYS])
    elif t == "object":
        f.update(type="collection")  # free-form keys, e.g. attributes
    elif name in DATE_FIELDS or s.get("format") == "date-time":
        f["type"] = "date"
    else:
        f["type"] = scalar(t)
    return f


def fields(schema, overrides=None, only=None):
    props = resolve(schema)["properties"]
    names = only or list(props)
    return [field(n, props[n], overrides) for n in names]


def result_schema(endpoint):
    op = spec["paths"][endpoint]["post"]
    resp = resolve(op["responses"]["200"])
    body = resolve(resp["content"]["application/json"]["schema"])
    return resolve(body["properties"]["results"]["items"])


# Synthetic samples (example.com hosts and made-up values).
SAMPLES = {
    "searchSearch": {
        "position": 1,
        "title": "Example Domain: documentation and examples",
        "link": "https://www.example.com/docs",
        "domain": "example.com",
        "displayed_link": "https://www.example.com › docs",
        "snippet": "This domain is for use in documentation examples without needing permission.",
        "date": "3 days ago",
        "published_at": "2026-10-20",
        "sitelinks": [{"title": "Getting started", "link": "https://www.example.com/docs/start", "snippet": "Set up your first project."}],
        "attributes": {"Founded": "1992"},
        "rating": 4.6,
        "rating_count": 1280,
    },
    "searchNews": {
        "position": 1,
        "title": "Example City opens its new public library",
        "link": "https://news.example.com/2026/10/library-opens",
        "domain": "news.example.com",
        "snippet": "The library has 200,000 books and a rooftop reading room.",
        "date": "2 hours ago",
        "published_at": "2026-10-23T08:00:00Z",
        "source": "Example News",
        "image_url": "https://news.example.com/images/library.jpg",
    },
    "searchImages": {
        "position": 1,
        "title": "Red kite over a green field",
        "image_url": "https://images.example.com/kite.jpg",
        "image_width": 1600,
        "image_height": 1067,
        "thumbnail_url": "https://images.example.com/kite-thumb.jpg",
        "source": "Example Photos",
        "domain": "images.example.com",
        "link": "https://images.example.com/gallery/kite",
    },
    "searchVideos": {
        "position": 1,
        "title": "How to fly a kite in light wind",
        "link": "https://video.example.com/watch/abc123",
        "domain": "video.example.com",
        "snippet": "Five tips for launching a kite when the wind is under 10 km/h.",
        "image_url": "https://video.example.com/thumbs/abc123.jpg",
        "duration": "8:42",
        "source": "Example Video",
        "channel": "Kite School",
        "date": "Oct 1, 2026",
        "published_at": "2026-10-01",
    },
    "searchMaps": {
        "position": 1,
        "title": "Example Coffee Roasters",
        "address": "123 Main St, Austin, TX 78701",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "rating": 4.7,
        "rating_count": 532,
        "price_level": "$$",
        "type": "Coffee shop",
        "types": ["Coffee shop", "Cafe"],
        "website": "https://coffee.example.com",
        "phone_number": "(512) 555-0100",
        "international_phone_number": "+1 512-555-0100",
        "opening_hours": {"Monday": "7 am–6 pm", "Sunday": "Closed"},
        "weekly_hours": {"monday": [{"open": "07:00", "close": "18:00"}], "sunday": []},
        "country": "US",
        "timezone": "America/Chicago",
        "description": "Small-batch roaster with espresso drinks and pastries.",
        "google_maps_url": "https://www.google.com/maps/place/?q=place_id:ChIJexample0000",
        "thumbnail_url": "https://images.example.com/coffee.jpg",
        "place_id": "ChIJexample0000",
        "cid": "1234567890123456789",
        "fid": "0x0:0x112210f4e1b2c315",
    },
    "searchShopping": {
        "position": 1,
        "title": "Example Delta Kite, 150 cm",
        "source": "Example Store",
        "link": "https://store.example.com/products/delta-kite",
        "price": "$39.99",
        "price_value": 39.99,
        "currency": "USD",
        "delivery": "Free delivery",
        "image_url": "https://store.example.com/images/delta-kite.jpg",
        "rating": 4.5,
        "rating_count": 214,
        "offers": "3 stores",
        "product_id": "1234567890",
    },
    "searchScholar": {
        "position": 1,
        "title": "An example study of kite aerodynamics",
        "link": "https://journal.example.com/articles/kite-aerodynamics",
        "domain": "journal.example.com",
        "publication_info": "A Author, B Author - Journal of Examples, 2024 - journal.example.com",
        "snippet": "We measure lift and drag on delta kites in a wind tunnel.",
        "year": 2024,
        "cited_by": 42,
        "pdf_url": "https://journal.example.com/articles/kite-aerodynamics.pdf",
        "id": "AbCdEfGhIjKl",
    },
    "searchPatents": {
        "position": 1,
        "title": "Kite with a foldable frame",
        "snippet": "A kite frame that folds into a carrying tube without tools.",
        "link": "https://patents.example.com/patent/US1234567B2/en",
        "publication_number": "US1234567B2",
        "priority_date": "2022-03-01",
        "filing_date": "2023-02-28",
        "grant_date": "2024-03-01",
        "publication_date": "2024-03-01",
        "inventor": "Jane Example",
        "assignee": "Example Kites Inc.",
        "language": "en",
        "pdf_url": "https://patents.example.com/pdfs/US1234567B2.pdf",
        "thumbnail_url": "https://patents.example.com/thumbs/US1234567B2.png",
    },
    "searchAutocomplete": {"value": "kite festival 2026"},
    "getAccount": {
        "balance": 9876.5,
        "rate_limit_rps": 10,
        "plan": "paid",
        "key": {"id": "6f1c2d3e-0000-4000-8000-000000000000", "name": "Make", "credit_limit": 1000, "credits_used_month": 123.5},
        "monthly_spend_cap": None,
        "month": {"credits": 456.5, "requests": 420},
    },
    "fetchWebpage": {
        "request": {"endpoint": "webpage", "engine": "google", "url": "https://www.example.com/blog/kites", "country": "us"},
        "url": "https://www.example.com/blog/kites",
        "status_code": 200,
        "markdown": "# A short history of kites\n\nKites were first flown in China about 2,500 years ago.",
        "text": "A short history of kites\n\nKites were first flown in China about 2,500 years ago.",
        "metadata": {
            "title": "A short history of kites",
            "description": "From ancient China to modern kitesurfing.",
            "language": "en",
            "canonical": "https://www.example.com/blog/kites",
            "site_name": "Example Blog",
            "image": "https://www.example.com/images/kites.jpg",
            "published_time": "2026-09-15T10:00:00Z",
            "author": "Jane Example",
            "content_type": "text/html",
        },
        "meta": {
            "request_id": "01a1687d-0000-7000-8000-000000000000",
            "credits_used": 1,
            "engine": "webpage",
            "route": [{"provider": "webpage", "outcome": "ok", "ms": 1331}],
            "cached": False,
            "resolved_urls": True,
            "parse_quality": "ok",
            "latency_ms": 1362,
        },
    },
}

Q = {"name": "q", "label": "Query", "type": "text", "required": True, "help": "Search phrase, at most 2,048 characters."}
COUNTRY = {"name": "country", "label": "Country", "type": "text", "default": "us", "help": "Two-letter country code (ISO 3166-1 alpha-2), such as us, gb or de. The API uses us when this is empty."}
LANGUAGE = {"name": "language", "label": "Language", "type": "text", "default": "en", "help": "Interface language code, such as en, de or pt-br. The API uses en when this is empty."}
LOCATION = {"name": "location", "label": "Location", "type": "text", "help": "Free-text place to search around, such as Austin, Texas, United States. Local queries such as coffee need a location."}
LIMIT = {"name": "limit", "label": "Limit", "type": "uinteger", "default": 10, "help": LIMIT_HELP}

SEARCH = [
    # (live name, folder, endpoint, label, description, extra params, label overrides)
    ("searchSearch", "search-search", "/v1/search", "Search web results", "Returns Google web results for a query, one bundle per organic result.", [], {}),
    ("searchNews", "search-news", "/v1/news", "Search news articles", "Returns Google News articles for a query.", [], {}),
    ("searchImages", "search-images", "/v1/images", "Search images", "Returns Google Images results for a query.", [], {}),
    ("searchVideos", "search-videos", "/v1/videos", "Search videos", "Returns Google video results for a query.", [], {}),
    ("searchMaps", "search-maps", "/v1/maps", "Search Google Maps places", "Returns places from a Google Maps search, with address, coordinates, rating, opening hours and place IDs.", [LOCATION], {}),
    ("searchShopping", "search-shopping", "/v1/shopping", "Search products", "Returns Google Shopping product results for a query.", [], {}),
    ("searchScholar", "search-scholar", "/v1/scholar", "Search papers", "Returns Google Scholar results for a query.", [], {"id": "Paper ID"}),
    ("searchPatents", "search-patents", "/v1/patents", "Search patents", "Returns Google Patents results for a query.", [], {}),
    ("searchAutocomplete", "search-autocomplete", "/v1/autocomplete", "Get query suggestions", "Returns Google autocomplete suggestions for a query.", [], {}),
]


def write(folder, name, data):
    path = root / "modules" / folder / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


manifest_modules = []
for live, folder, endpoint, lbl, desc, extra, overrides in SEARCH:
    paged = endpoint != "/v1/autocomplete"
    params = [Q, COUNTRY, LANGUAGE, *extra]
    qs = {p["name"]: "{{parameters.%s}}" % p["name"] for p in params}
    comm = {
        "url": endpoint,
        "method": "GET",
        "qs": qs,
        "response": {"limit": "{{parameters.limit}}", "iterate": "{{body.results}}", "output": "{{item}}"},
    }
    if paged:
        # body.request.page echoes the page just fetched; the API accepts pages 1-10.
        comm["pagination"] = {"qs": {"page": "{{pagination.page}}"}, "condition": "{{length(body.results) > 0 && body.request.page < 10}}"}
        limit = LIMIT
    else:
        limit = {**LIMIT, "help": "Maximum number of suggestions to return. The module makes a single request; Google returns up to about 15 suggestions."}
    write(folder, "communication", comm)
    write(folder, "parameters", [*params, limit])
    write(folder, "static-parameters", [])
    item = result_schema(endpoint)
    write(folder, "interface", fields(item, overrides, [n for n in item["properties"] if n not in OMIT]))
    write(folder, "sample", SAMPLES[live])
    manifest_modules.append({"name": live, "folder": folder, "label": lbl, "type": "search", "crud": "read", "description": desc, "endpoint": endpoint})

# Get account balance
account = schemas["Account"]
write("get-account", "communication", {"url": "/v1/account", "method": "GET", "response": {"output": "{{body}}"}})
write("get-account", "parameters", [])
write("get-account", "static-parameters", [])
write("get-account", "interface", fields(account))
write("get-account", "sample", SAMPLES["getAccount"])
manifest_modules.append({"name": "getAccount", "folder": "get-account", "label": "Get account balance", "type": "action", "crud": "read", "description": "Returns the credit balance, rate limit, monthly usage and limits of the account and API key.", "endpoint": "/v1/account"})

# Fetch a webpage
page = resolve(schemas["WebpageResponse"])
page_interface = []
for n, s in page["properties"].items():
    if n == "request":
        page_interface.append(field(n, s, only=["endpoint", "engine", "url", "country"]))
    else:
        page_interface.append(field(n, s, {"url": "Final URL"} if n == "url" else None))
write("fetch-webpage", "communication", {
    "url": "/v1/webpage",
    "method": "POST",
    "type": "json",
    "body": {
        "url": "{{parameters.url}}",
        "include_html": "{{parameters.include_html}}",
        "include_links": "{{parameters.include_links}}",
        "include_images": "{{parameters.include_images}}",
        "country": "{{parameters.country}}",
    },
    "response": {"output": "{{body}}"},
})
write("fetch-webpage", "parameters", [
    {"name": "url", "label": "URL", "type": "url", "required": True, "help": "Public HTML page or PDF."},
    {"name": "include_html", "label": "Include HTML", "type": "boolean", "default": False, "help": "Also return the page's HTML in HTML."},
    {"name": "include_links", "label": "Include links", "type": "boolean", "default": False, "help": "Also return the page's outbound links in Links."},
    {"name": "include_images", "label": "Include image links", "type": "boolean", "default": False, "help": "Also return the page's image URLs in Image links."},
    {"name": "country", "label": "Country", "type": "text", "advanced": True, "help": "Fetch the page as seen from this country (two-letter code, such as gb), for pages that differ by location."},
])
write("fetch-webpage", "static-parameters", [])
write("fetch-webpage", "interface", page_interface)
write("fetch-webpage", "sample", SAMPLES["fetchWebpage"])
manifest_modules.append({"name": "fetchWebpage", "folder": "fetch-webpage", "label": "Fetch a webpage", "type": "action", "crud": "read", "description": "Returns a public web page or PDF as Markdown and plain text, with its metadata.", "endpoint": "/v1/webpage"})


PRICING = "Pricing: https://serpkite.com/pricing. Failed, refused and empty answers are not billed."


def body_module(live, folder, endpoint, lbl, desc, params, body, interface, sample, crud="read", output="{{body}}", group="Other", mtype="action", method="POST", extra_comm=None):
    comm = {"url": endpoint, "method": method, "response": {"output": output}}
    if method == "POST":
        comm.update(type="json", body=body)
    if extra_comm:
        comm.update(extra_comm)
    write(folder, "communication", comm)
    write(folder, "parameters", params)
    write(folder, "static-parameters", [])
    write(folder, "interface", interface)
    write(folder, "sample", sample)
    manifest_modules.append({"name": live, "folder": folder, "label": lbl, "type": mtype, "crud": crud, "description": desc, "endpoint": endpoint, "group": group})


# AI assistants: one POST each, answered inline (the base timeout covers the slowest).
assistant_iface = fields(schemas["AssistantResponse"], {"position": "Position"}, [n for n in schemas["AssistantResponse"]["properties"] if n != "html"])
PROMPT = {"name": "prompt", "label": "Prompt", "type": "text", "required": True, "help": "The question to ask, at most 4,000 characters. " + PRICING}
TRACK = {"name": "track", "label": "Track", "type": "array", "spec": {"type": "text", "label": "Brand or domain"}, "help": "Up to 20 brands or domains (such as Pipedrive or hubspot.com). Mentions then says whether the answer names each one and whether a cited source is on it."}
ASSISTANTS = [
    # (live, folder, endpoint, label, product, latency, description tail, extra params)
    ("askChatgpt", "ask-chatgpt", "/v1/chatgpt", "Ask ChatGPT", "ChatGPT", "10–30 s", "with the sources it cited, the products and places it showed and the model it used", [
        {"name": "web_search", "label": "Search the web", "type": "boolean", "default": True, "help": "Let ChatGPT search the web before answering, as it does by default for logged-out visitors."},
        {"name": "country", "label": "Country", "type": "text", "help": "Ask from this country (two-letter code, such as gb), so the answer is localized like a visitor's there."},
    ]),
    ("askGemini", "ask-gemini", "/v1/gemini", "Ask Gemini", "Google Gemini", "5–30 s", "with the sources it grounded on", None),
    ("askCopilot", "ask-copilot", "/v1/copilot", "Ask Copilot Search", "Microsoft Copilot Search", "15–40 s", "with its cited sources and the products shown beside it", None),
    ("askAiMode", "ask-ai-mode", "/v1/ai_mode", "Ask Google AI Mode", "Google AI Mode", "5–45 s", "with the sources it cited", None),
    ("askBraveAi", "ask-brave-ai", "/v1/brave_ai", "Ask Brave AI", "Brave Search's AI answer", "1–10 s", "with its cited sources, the searches it ran and the products it showed", None),
]
for live, folder, endpoint, lbl, product, latency, tail, extra in ASSISTANTS:
    params = [PROMPT, *(extra or [COUNTRY, LANGUAGE]), TRACK]
    params = [{**x, "default": None} if x["name"] in ("country", "language") and x.get("default") else x for x in params]
    params = [{k: v for k, v in x.items() if not (k == "default" and v is None)} for x in params]
    body = {x["name"]: "{{parameters.%s}}" % x["name"] for x in params}
    sample = {
        "request": {"endpoint": endpoint.rsplit("/", 1)[1], "prompt": "What are the best CRMs for a 10-person startup?", "country": "us"},
        "text": "For a 10-person startup, HubSpot CRM and Pipedrive are the most common picks [1][2].",
        "markdown": "For a 10-person startup, **HubSpot CRM** and **Pipedrive** are the most common picks [1](https://www.example.com/crm-guide)[2](https://reviews.example.com/crm).",
        "model": "example-model",
        "sources": [{"position": 1, "title": "The best CRMs for startups", "link": "https://www.example.com/crm-guide", "domain": "example.com", "cited": True}],
        "search_queries": ["best crm for small startup"],
        "products": [],
        "related_questions": ["Is HubSpot CRM free?"],
        "mentions": [{"term": "Pipedrive", "mentioned": True, "cited": False}],
        "meta": {"request_id": "01a1687d-0000-7000-8000-000000000000", "credits_used": 2, "cached": False, "latency_ms": 8200},
    }
    desc = f"Asks {product} as a logged-out visitor and returns its answer {tail}. Takes {latency}."
    body_module(live, folder, endpoint, lbl, desc, params, body, assistant_iface, sample, group="AI assistants")

# Places: one place's listing and its reviews.
PLACE_ID = {"name": "place_id", "label": "Place ID", "type": "text", "help": "Google place ID (ChIJ…) from Search Google Maps places. Or fill in CID or FID instead."}
PLACE_CID = {"name": "cid", "label": "CID", "type": "text", "advanced": True, "help": "Decimal customer ID from a Maps result, instead of Place ID."}
PLACE_FID = {"name": "fid", "label": "FID", "type": "text", "advanced": True, "help": "Feature ID (0x…:0x…) from a Maps result, instead of Place ID."}
place_item = resolve(schemas["PlaceResult"])
place_params = [PLACE_ID, PLACE_CID, PLACE_FID, {**COUNTRY, "default": None}, {**LANGUAGE, "default": None}]
place_params = [{k: v for k, v in x.items() if not (k == "default" and v is None)} for x in place_params]
body_module("getPlace", "get-place", "/v1/place", "Get place details", "Returns one Google Maps place's full listing: address, coordinates, categories, opening hours per weekday, website, phone, rating, description and photos.",
    place_params, {x["name"]: "{{parameters.%s}}" % x["name"] for x in place_params},
    fields(place_item, None, [n for n in place_item["properties"] if n not in ("oid", "yandex_maps_url")]),
    {**SAMPLES["searchMaps"], "photos": [{"image_url": "https://images.example.com/coffee-1.jpg", "thumbnail_url": "https://images.example.com/coffee-1-thumb.jpg"}]},
    output="{{first(body.results)}}", group="Places")

review_item = resolve(schemas["ReviewResult"])
review_params = [PLACE_ID, PLACE_CID, PLACE_FID,
    {**LANGUAGE, "default": None}]
review_params = [{k: v for k, v in x.items() if not (k == "default" and v is None)} for x in review_params]
body_module("listReviews", "list-reviews", "/v1/reviews", "List place reviews", "Returns a Google Maps place's most relevant reviews with rating, date, text, reviewer and the owner's response.",
    [*review_params, {**LIMIT, "help": LIMIT_HELP + " Reviews come 10 per request."}],
    {x["name"]: "{{parameters.%s}}" % x["name"] for x in review_params},
    fields(review_item),
    {"rating": 5, "date": "2 weeks ago", "iso_date": "2026-10-10T00:00:00Z", "snippet": "Great espresso and friendly staff.", "likes": 3, "user": {"name": "Alex Example", "link": "https://www.example.com/u/alex", "reviews": 12}, "response": {"date": "1 week ago", "snippet": "Thanks, Alex!"}},
    output="{{item}}", group="Places", mtype="search",
    extra_comm={"response": {"limit": "{{parameters.limit}}", "iterate": "{{body.results}}", "output": "{{item}}"},
                "pagination": {"body": {"page_token": "{{body.next_page_token}}"}, "condition": "{{body.next_page_token}}"}})

# Sites: map, extract, crawl.
map_item = resolve(schemas["MapURL"])
map_params = [
    {"name": "url", "label": "Site URL", "type": "url", "required": True, "help": "The site or section to list, such as https://example.com/docs."},
    {"name": "search", "label": "Search", "type": "text", "help": "Rank the URLs by relevance to this phrase."},
    {"name": "include_subdomains", "label": "Include subdomains", "type": "boolean", "default": False},
]
body_module("listSiteUrls", "list-site-urls", "/v1/map", "List site URLs", "Returns the URLs of a site from its sitemaps and start page, optionally ranked by a search phrase.",
    [*map_params, {**LIMIT, "default": 100, "help": "Maximum number of URLs to return (up to 5,000)."}],
    {**{x["name"]: "{{parameters.%s}}" % x["name"] for x in map_params}, "limit": "{{parameters.limit}}"},
    fields(map_item),
    {"url": "https://www.example.com/docs/start", "title": "Getting started", "lastmod": "2026-10-01T00:00:00Z", "source": "sitemap"},
    output="{{item}}", group="Webpages", mtype="search",
    extra_comm={"response": {"limit": "{{parameters.limit}}", "iterate": "{{body.results}}", "output": "{{item}}"}})

extract_params = [
    {"name": "urls", "label": "URLs", "type": "array", "required": True, "spec": {"type": "url", "label": "URL"}, "help": "Up to 20 public pages or PDFs."},
    {"name": "query", "label": "Query", "type": "text", "help": "Rank each page's passages by this phrase and return the best as Highlights."},
    {"name": "summary", "label": "Summarize", "type": "boolean", "default": False, "help": "Add an AI summary of each page. " + "Pricing: https://serpkite.com/pricing."},
    {"name": "prompt", "label": "Summary instructions", "type": "text", "help": "What the summary should focus on, such as \"pricing and plans\". Used with Summarize."},
    {"name": "include_links", "label": "Include links", "type": "boolean", "default": False},
    {"name": "country", "label": "Country", "type": "text", "advanced": True, "help": "Fetch the pages as seen from this country (two-letter code, such as gb)."},
]
extract_iface = fields(schemas["ExtractResponse"], None, ["request", "results", "failed", "meta"])
body_module("extractWebpages", "extract-webpages", "/v1/extract", "Extract webpages", "Returns up to 20 pages or PDFs as Markdown with metadata, optionally with passages ranked by a query and an AI summary per page.",
    extract_params, {x["name"]: "{{parameters.%s}}" % x["name"] for x in extract_params},
    extract_iface,
    {"request": {"urls": ["https://www.example.com/blog/kites"]}, "results": [{"url": "https://www.example.com/blog/kites", "status_code": 200, "title": "A short history of kites", "markdown": "# A short history of kites\n\nKites were first flown in China about 2,500 years ago.", "summary": "Kites began in China about 2,500 years ago."}], "failed": [], "meta": {"request_id": "01a1687d-0000-7000-8000-000000000000", "credits_used": 1}},
    group="Webpages")

crawl_params = [
    {"name": "url", "label": "Start URL", "type": "url", "required": True, "help": "The site or section to crawl, such as https://example.com/docs."},
    {"name": "limit", "label": "Page limit", "type": "uinteger", "default": 10, "help": "Maximum pages to read (1–1,000). Credits for this many pages are held when the crawl starts, and the pages not read are refunded. Pricing: https://serpkite.com/pricing."},
    {"name": "max_depth", "label": "Maximum depth", "type": "uinteger", "help": "Link hops from the start URL."},
    {"name": "include_paths", "label": "Include paths", "type": "array", "spec": {"type": "text", "label": "Path pattern"}, "help": "Only crawl paths matching these patterns, such as /docs/*."},
    {"name": "exclude_paths", "label": "Exclude paths", "type": "array", "spec": {"type": "text", "label": "Path pattern"}},
    {"name": "query", "label": "Query", "type": "text", "help": "Read the pages most relevant to this phrase first."},
    {"name": "webhook_url", "label": "Webhook URL", "type": "url", "help": "Receives the result when the crawl ends, for example a Make custom webhook."},
]
task_iface = fields(schemas["CrawlTask"])
body_module("startCrawl", "start-crawl", "/v1/crawl", "Start a crawl", "Starts reading a site in the background. Get the pages with Get a crawl, or receive them on a webhook.",
    crawl_params, {x["name"]: "{{parameters.%s}}" % x["name"] for x in crawl_params},
    [field(n, t) for n, t in [("id", {"type": "string"}), ("kind", {"type": "string"}), ("status", {"type": "string"}), ("created_at", {"type": "string", "format": "date-time"}), ("poll_url", {"type": "string"}), ("credits_reserved", {"type": "number"}), ("webhook_url", {"type": "string"})]],
    {"id": "01926a3e-7b2c-7c4e-9f1a-2b3c4d5e6f70", "kind": "crawl", "status": "queued", "created_at": "2026-10-29T12:00:00Z", "poll_url": "https://api.serpkite.com/v1/crawl/01926a3e-7b2c-7c4e-9f1a-2b3c4d5e6f70", "credits_reserved": 10, "webhook_url": None},
    crud="create", group="Webpages")
crawl_result = fields(schemas["CrawlResult"])
get_crawl_iface = [f if f["name"] != "result" else {"name": "result", "label": "Result", "type": "collection", "spec": crawl_result} for f in fields(schemas["CrawlTask"])]
body_module("getCrawl", "get-crawl", "/v1/crawl/{{parameters.id}}", "Get a crawl", "Returns a crawl's status, progress and, once it has completed, its pages as Markdown. Crawls are kept for 24 hours.",
    [{"name": "id", "label": "Crawl ID", "type": "text", "required": True, "help": "The ID returned by Start a crawl."}], None,
    get_crawl_iface,
    {"id": "01926a3e-7b2c-7c4e-9f1a-2b3c4d5e6f70", "kind": "crawl", "status": "completed", "created_at": "2026-10-29T12:00:00Z", "completed_at": "2026-10-29T12:00:40Z", "credits_reserved": 10, "credits_used": 2, "result": {"pages": [{"url": "https://www.example.com/docs", "title": "Docs", "markdown": "# Docs"}]}},
    method="GET", group="Webpages")

# Answers: a cited answer from live Google results.
answer_params = [
    {"name": "q", "label": "Question", "type": "text", "required": True, "help": "The question to answer from live Google results. " + "Pricing: https://serpkite.com/pricing; a failed answer is not billed."},
    {"name": "depth", "label": "Depth", "type": "select", "default": "fast", "options": [{"label": "Fast (from search snippets)", "value": "fast"}, {"label": "Standard (reads the top pages)", "value": "standard"}]},
    {**COUNTRY, "default": None}, {**LANGUAGE, "default": None}, LOCATION,
    {"name": "time", "label": "Time", "type": "select", "options": [{"label": l.capitalize(), "value": l} for l in ["hour", "day", "week", "month", "year"]], "help": "Only use results from this recent period."},
]
answer_params = [{k: v for k, v in x.items() if not (k == "default" and v is None)} for x in answer_params]
body_module("getAnswer", "get-answer", "/v1/answer", "Get a cited answer", "Answers a question from live Google results and returns the answer with numbered citations and the results it used.",
    answer_params, {x["name"]: "{{parameters.%s}}" % x["name"] for x in answer_params},
    fields(schemas["AnswerResponse"], None, ["request", "answer", "citations", "results", "meta"]),
    {"request": {"q": "when was the first kite flown"}, "answer": "Kites were first flown in China about 2,500 years ago [1].", "citations": [{"index": 1, "title": "A short history of kites", "link": "https://www.example.com/blog/kites", "domain": "example.com"}], "results": [{"index": 1, "title": "A short history of kites", "link": "https://www.example.com/blog/kites", "domain": "example.com"}], "meta": {"request_id": "01a1687d-0000-7000-8000-000000000000", "credits_used": 3}},
    group="AI answers")

# Make an API call (Make's REST universal module template)
write("make-an-api-call", "communication", {
    "url": "https://api.serpkite.com/{{parameters.url}}",
    "method": "{{parameters.method}}",
    "headers": {"{{...}}": "{{toCollection(parameters.headers, 'key', 'value')}}"},
    "qs": {"{{...}}": "{{toCollection(parameters.qs, 'key', 'value')}}"},
    "body": "{{parameters.body}}",
    "type": "text",
    "response": {"output": {"body": "{{body}}", "headers": "{{headers}}", "statusCode": "{{statusCode}}"}},
    "log": {"sanitize": ["request.headers.Authorization", "request.qs.api_key", "request.qs.key"]},
})
kv = [{"name": "key", "label": "Key", "type": "text"}, {"name": "value", "label": "Value", "type": "text"}]
write("make-an-api-call", "parameters", [
    {"name": "url", "label": "URL", "type": "text", "required": True, "help": "Enter a path relative to `https://api.serpkite.com`. For example: `/v1/account`"},
    {"name": "method", "label": "Method", "type": "select", "required": True, "default": "GET", "options": [{"label": m, "value": m} for m in ["GET", "POST", "PATCH", "DELETE"]]},
    {"name": "headers", "label": "Headers", "type": "array", "spec": kv, "default": [{"key": "Content-Type", "value": "application/json"}], "help": "You don't have to add authorization headers; we already did that for you."},
    {"name": "qs", "label": "Query string", "type": "array", "spec": kv},
    {"name": "body", "label": "Body", "type": "any", "help": "JSON request body, for example for POST /v1/batches."},
])
write("make-an-api-call", "static-parameters", [])
write("make-an-api-call", "interface", [
    {"name": "body", "label": "Body", "type": "any"},
    {"name": "headers", "label": "Headers", "type": "collection"},
    {"name": "statusCode", "label": "Status code", "type": "number"},
])
write("make-an-api-call", "sample", {})
manifest_modules.append({"name": "makeAnApiCall", "folder": "make-an-api-call", "label": "Make an API call", "type": "universal", "crud": None, "description": "Performs an arbitrary authorized API call.", "endpoint": "relative path on api.serpkite.com"})

base = {
    "baseUrl": "https://api.serpkite.com",
    "timeout": "{{common.timeout}}",
    "headers": {"Authorization": "Bearer {{connection.apiKey}}", "Content-Type": "application/json"},
    "response": {"error": {"message": ERROR_MESSAGE}},
    "log": {"sanitize": ["request.headers.Authorization"]},
}
(root / "base.json").write_text(json.dumps(base, indent=2) + "\n")
(root / "connection/communication.json").write_text(json.dumps({
    "url": "https://api.serpkite.com/v1/account",
    "method": "GET",
    "headers": {"Authorization": "Bearer {{parameters.apiKey}}"},
    "response": {"error": {"message": ERROR_MESSAGE}},
    "log": {"sanitize": ["request.headers.Authorization"]},
}, indent=2) + "\n")
(root / "connection/parameters.json").write_text(json.dumps([{
    "name": "apiKey",
    "label": "API key",
    "type": "password",
    "required": True,
    "editable": True,
    "help": "Create a key at https://app.serpkite.com. Use a dedicated key with a monthly credit limit.",
}], indent=2) + "\n")

# AI answers can take up to 90 s (the API's own budget), past Make's 40 s default.
(root / "common.json").write_text(json.dumps({"timeout": 120000}, indent=2) + "\n")
GROUPS = ["Search", "AI assistants", "AI answers", "Places", "Webpages", "Account", "Other"]
group_of = {"fetchWebpage": "Webpages", "getAccount": "Account", "makeAnApiCall": "Other"}
groups = [
    {"label": g, "modules": [m["name"] for m in manifest_modules if m.get("group", group_of.get(m["name"], "Search")) == g]}
    for g in GROUPS
]
(root / "groups.json").write_text(json.dumps(groups, indent=2) + "\n")

manifest = json.loads((root / "app-components.json").read_text())
manifest["connection"]["label"] = "SerpKite API key"
manifest["modules"] = manifest_modules
(root / "app-components.json").write_text(json.dumps(manifest, indent=2) + "\n")

old = root / "modules" / "search-places"
if old.exists():
    shutil.move(str(old), str(root / "removed-search-places"))
print(f"{len(manifest_modules)} modules, {len(groups)} groups")
