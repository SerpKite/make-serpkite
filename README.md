# SerpKite custom app components for Make

Prepared by the SerpKite team for Make's Custom Apps editor. These components are not deployed to Make, scenario-tested, published or approved yet.

## Components

- API-key connection: validates credentials through unbilled `GET /v1/account`.
- Base: fixed API domain, Bearer authorization, JSON content type, structured error handling, authorization/query sanitization.
- Ten search modules: web, news, images, videos, maps, places, shopping, scholar, patents and autocomplete. Results become individual bundles with explicit output interfaces. Search modules have a limit; paged verticals request ten results per page and stop by page ten. Autocomplete is not paginated.
- Fetch a Webpage action and Get Account Balance action.
- Make an API Call universal module: fixed `api.serpkite.com` origin, relative path input, inherited authentication, query strings and JSON body. Users cannot direct the connection's API key to another host.

Search output interfaces select useful non-temporal result fields. Date-only and mixed date/date-time fields are omitted from those curated bundles. Use the universal module to access the complete REST response when needed. All samples are synthetic examples.

## Install using an existing Make account

1. Open https://developers.make.com/ and create a private Custom App named `serpkite`, labeled **SerpKite**.
2. Copy `base.json` into the Base component.
3. Create the connection described by `app-components.json`. Copy `connection/parameters.json` and `connection/communication.json` into their editor tabs.
4. Create the thirteen modules with the name, label and type in `app-components.json`.
5. For each module, copy its `communication.json`, `parameters.json`, `static-parameters.json`, `interface.json` and synthetic `sample.json` into the matching editor tabs. Select the API-key connection.
6. Upload SerpKite's logo and configure website `https://serpkite.com` and support `support@serpkite.com`.
7. In the Scenario Builder, use your own dedicated SerpKite key. Do not export or share it. Test every module and error handling before publication.

This folder contains component-tab source files, not a fictional one-click import bundle. Make's editor/SDK must create its own app identifier and local workspace metadata.

## Required scenario testing

Use each module in at least one test scenario. Test authentication success and failure, empty results, country/language values, pagination up to the configured limit, and page fetching. Search calls consume credits. Keep queries non-sensitive and do not send customer data. Keep credentials and private responses out of public source and exports.

For pagination, verify that `page` is incremented from 1 and stops at page 10 or the requested limit. SerpKite rejects `page > 10` and rejects autocomplete pagination. No real Make scenario execution has been claimed here.

## Request public review

Make's current process is through the Custom App editor: **Publish → Review → Request review**. It requires recent successful scenario logs and links for all modules, plus API documentation.

The follow-up partnership form includes trademark, external-service terms and indemnification attestations. The account owner must review those legal statements; this preparation does not sign them. Make publication cannot be undone. Submit the app only after validation and owner review of those statements.

Developer relationship: maintained by the SerpKite team.
Website/API documentation: https://serpkite.com and https://serpkite.com/docs.
API contract: https://serpkite.com/openapi.json.
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

Local check: `python3 tests/check_components.py`. Configuration source is MIT licensed. The hosted API implementation is proprietary.
