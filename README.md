# SerpKite custom app components for Make

Source of the SerpKite custom app on Make (`serpkite-krmli2`, us2, published, review requested 2026-10-09). `build.py` generates every component file from `openapi.json` (backend/api/serp-api.yaml as JSON); `push.py` uploads them through Make's SDK API with the token in `~/.serpkite/make-api-token.txt`. Edit `build.py`, then run `python3 build.py && python3 tests/check_components.py && python3 push.py`.

## Components

- API-key connection: validates credentials through unbilled `GET /v1/account`.
- Base: fixed API domain, Bearer authorization, JSON content type, error message with a fallback when the body has no `error` object, only the Authorization header sanitized. Common data sets `timeout` to 120000 ms (Make's default is 40 s; AI assistant answers take up to about 45 s, and the API's own budget is 90 s); the base reads it as `{{common.timeout}}`.
- Nine search modules (group Search): web, news, images, videos, Google Maps, shopping, scholar, patents and autocomplete. `GET` with query strings; output is the API's result object as is (`{{item}}`), interfaces list every documented field except ones that need options the modules don't send. Limit is optional (default 10). Paged verticals send only `page` in the pagination block and stop when the echoed `body.request.page` reaches 10 (the API accepts 1-10). Autocomplete makes one request.
- AI assistants (group AI assistants, Read): Ask ChatGPT, Ask Gemini, Ask Copilot Search, Ask Google AI Mode, Ask Brave AI. One POST each to `/v1/<assistant>` with prompt, country, language (ChatGPT: web search instead), and Track (brands/domains → `mentions`). Output is the whole response (`{{body}}`); `html` is left out of the interface (only with include_html, which the modules don't send).
- Get a cited answer (group AI answers): `POST /v1/answer`, depth fast or standard.
- Places: Get place details (`POST /v1/place`, output `{{first(body.results)}}`) and List place reviews (search module over `POST /v1/reviews`, paginated with `next_page_token`; Google offers other orders only to signed-in visitors, so there is no sort option).
- Webpages: Fetch a webpage (include HTML/links/images and an advanced country), List site URLs (search module over `POST /v1/map`), Extract webpages (`POST /v1/extract`, up to 20 URLs, query highlights, AI summary), Start a crawl (`POST /v1/crawl`, optional webhook) and Get a crawl (`GET /v1/crawl/{id}`).
- Get account balance (group Account, Read).
- Research (`/v1/research`, 30+ credits a run) has no module; Make an API call reaches it and every other endpoint.
- Make an API call (group Other): Make's REST universal template with Headers and Query string, fixed `api.serpkite.com` origin.
- Search Places was removed (same results as `/v1/maps`). Make can't delete a module from a public app, so `searchPlaces` is private instead.

`published_at` and `meta.cached_at` are `date` fields; date-only values (patent dates) stay text. All samples are synthetic examples.

## Install using an existing Make account

1. Open https://developers.make.com/ and create a private Custom App named `serpkite`, labeled **SerpKite**.
2. Copy `base.json` into the Base component and `common.json` into Common data.
3. Create the connection described by `app-components.json`. Copy `connection/parameters.json` and `connection/communication.json` into their editor tabs.
4. Create the modules with the name, label and type in `app-components.json`.
5. For each module, copy its `communication.json`, `parameters.json`, `static-parameters.json`, `interface.json` and synthetic `sample.json` into the matching editor tabs. Select the API-key connection.
6. Upload SerpKite's logo and configure website `https://serpkite.com` and support `support@serpkite.com`.
7. In the Scenario Builder, use your own dedicated SerpKite key. Do not export or share it. Test every module and error handling before publication.

This folder contains component-tab source files, not a fictional one-click import bundle. Make's editor/SDK must create its own app identifier and local workspace metadata.

## Required scenario testing

Use each module in at least one test scenario. Put search modules (they return one bundle per result) last, or later modules run once per bundle. Test authentication success and failure, empty results, country/language values, pagination up to the configured limit, and page fetching. Search calls consume credits. Keep queries non-sensitive and do not send customer data. Keep credentials and private responses out of public source and exports.

For pagination, verify that `page` is incremented from 1 and stops at page 10 or the requested limit. SerpKite rejects `page > 10` and rejects autocomplete pagination. Test scenarios: https://us2.make.com/3148775/scenarios/6575764/edit (original modules; web search Limit 100 ran exactly 10 pages on 2026-10-23), /6575784/edit (API error), /6818390/edit (assistants, answer, site URLs, extract, place; 2026-10-28) and /6818475/edit (reviews, crawl start/get; 2026-10-28). Run them from the API with `POST /scenarios/{id}/start`, `/run`, then `/stop`.

## Request public review

Make's current process is through the Custom App editor: **Publish → Review → Request review**. It requires recent successful scenario logs and links for all modules, plus API documentation.

The follow-up partnership form includes trademark, external-service terms and indemnification attestations. The account owner must review those legal statements; this preparation does not sign them. Make publication cannot be undone. Submit the app only after validation and owner review of those statements.

Developer relationship: maintained by the SerpKite team.
Website/API documentation: https://serpkite.com and https://serpkite.com/docs.
API contract: https://serpkite.com/openapi/serp-api.yaml.
Partnership/support contact: support@serpkite.com.
Suggested category: developer tools / search / data extraction.

## Validation and sources

Local checks validate component JSON, endpoint coverage, request fields, typed result field references, relative universal URL construction, empty-secret source and log sanitization. They do not replace execution inside Make's IML runtime or Scenario Builder.

- https://developers.make.com/custom-apps-documentation/create-your-first-app/apps-environment/base
- https://developers.make.com/custom-apps-documentation/create-your-first-app/apps-environment/connection
- https://developers.make.com/custom-apps-documentation/app-components/modules/search
- https://developers.make.com/custom-apps-documentation/app-components/modules/universal-module/rest
- https://developers.make.com/custom-apps-documentation/app-review/prerequisites
- https://developers.make.com/custom-apps-documentation/app-review/request-app-review

Google is a trademark of Google LLC; SerpKite is not affiliated with Google.
