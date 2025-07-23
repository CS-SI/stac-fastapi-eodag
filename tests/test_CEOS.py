# -*- coding: utf-8 -*-
# Copyright 2025, CS GROUP - France, https://www.cs-soprasteria.com
#
# This file is part of stac-fastapi-eodag project
#     https://www.github.com/CS-SI/stac-fastapi-eodag
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""CEOS tests."""

import logging
from urllib.parse import urlparse

import requests
from jsonschema import validate

logger = logging.getLogger(__name__)


def is_absolute(url):
    """Check if the url is absolute"""
    return bool(urlparse(url).netloc)


# Flag to set if test that cannot be tested should fail. False means fail.
CANT_TEST = False


async def test_CEOS_STAC_PER_3210(request_valid_raw):
    """
    CEOS-STAC-PER-3210 - API Feature paths [Permission]

    A CEOS STAC catalog implementation is not required to use fixed paths to navigate from resource to resource.
    It shall support discovering the path via the proper relation (rel="xyz") in the corresponding resource's
    representation.
    """
    errors = []

    data = (await request_valid_raw("/")).json()

    for link in data["links"]:
        if "href" not in link:
            errors.append(f"href not found in link: {link['title']}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_PER_3220(request_valid_raw):
    """
    CEOS-STAC-PER-3220 - API Feature relations [Permission]

    A CEOS STAC catalog implementation is not required to:

        Support the /api path or provide an OpenAPI description of its interface
        Support the rel="service-desc" from its landing page (root catalog)
        Support the /conformance path
        Support the rel="conformance" from its landing page (root catalog)
    """
    errors = []

    data = (await request_valid_raw("/")).json()
    service_desc = False
    conformance = False
    for link in data["links"]:
        if link["rel"] == "service-desc":
            service_desc = True
        elif link["rel"] == "conformance":
            conformance = True

    try:
        assert service_desc
    except Exception:
        errors.append("Root catalog does not have rel=service-desc")

    try:
        assert conformance
    except Exception:
        errors.append("Root catalog does not have rel=conformance")

    try:
        await request_valid_raw("/api")
    except Exception:
        errors.append("Could not get /api endpoint")

    try:
        await request_valid_raw("/conformance")
    except Exception:
        errors.append("Could not get /conformance endpoint")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_CREQ_3230(request_valid_raw):
    """
    CEOS-STAC-CREQ-3230 - Additional search parameters [Conditional]

    A CEOS STAC collection/granule catalog supporting additional search parameters shall implement
    the "STAC API Filter Extension" [AD06], i.e.:

        Advertise the additional filter parameters via the corresponding Queryables responses (JSON Schema),
        Use the additional filter parameters inside the filter expression passed via the filter (HTTP) query parameter.
    """

    errors = []

    try:
        await request_valid_raw("/queryables")
    except Exception:
        errors.append("Could not get /queryables endpoint")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_3235(request_valid_raw):
    """
    CEOS-STAC-REQ-3235 - Parameter Descriptions [Requirement]

    The GET response for the rel=queryables endpoint in application/schema+json representation shall provide additional
    information about search parameters including:

        type of the parameter (e.g. array, string, integer, number, ...)
        title of the parameter providing a human readable title.
        format of the string parameter (e.g. "uri", "date-time")
        enum to enumerate valid (string) values
        minItems, maxItems to constrain the size of arrays
        minimum, maximum to constrain the range of a numerical parameter
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_CREQ_3240(request_valid_raw):
    """
    CEOS-STAC-CREQ-3240 - Additional search parameters [Conditional]

    A CEOS STAC collection/granule catalog supporting additional search parameters via a filter expression shall support
    the following additional query parameters and advertise the corresponding conformance classes in the landing page
    (See also "STAC API Filter Extension" [AD06]:

        filter
        filter-lang
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    if "filter" not in [x["name"] for x in data["paths"]["/search"]["get"]["parameters"]]:
        errors.append("filter parameter not advertised in /search endpoint")

    if "filter-lang" not in [x["name"] for x in data["paths"]["/search"]["get"]["parameters"]]:
        errors.append("filter-lang parameter not advertised in /search endpoint")

    data = (await request_valid_raw("/")).json()

    for conformance in ["http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/filter"]:
        if conformance not in data["conformsTo"]:
            errors.append(f"Conformance not found in landing page: {conformance}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_CREQ_3250(request_valid_raw):
    """
    CEOS-STAC-CREQ-3250 - CQL subset [Conditional]

    A CEOS STAC collection/granule catalog supporting additional search parameters via a filter expression shall support
    at least the following conformance classes of CQL2 (See also "STAC API Filter Extension" [AD06] and
    "OGC21-065, Common Query Language (CQL2)" [AD10]:

        CQL2 Text
        Basic CQL2
    """

    errors = []
    data = (await request_valid_raw("/")).json()

    for conformance in [
        "http://www.opengis.net/spec/cql2/1.0/conf/basic-cql2",
        "http://www.opengis.net/spec/cql2/1.0/conf/cql2-text",
    ]:
        if conformance not in data["conformsTo"]:
            errors.append(f"Conformance not found in landing page: {conformance}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REC_3255(request_valid_raw, open_search_eo_json):
    """
    CEOS-STAC-REC-3255 - Additional search parameter names [Recommendation]

    A CEOS STAC collection/granule catalog supporting additional search parameters for collection search
    (e.g. search by platform, instrument, organisation) or granule search
    (e.g. by polarisation mode, orbit direction, orbit number, cloud cover, etc.) should, by preference,
    use names consistent with the names defined in the OpenSearch extension for Earth Observation OGC 13-026r9 [RD04].
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3260(request_valid_raw):
    """
    CEOS-STAC-REC-3260 - Standalone JSON Schema [Recommendation]

    CEOS STAC catalog server /queryables responses should contain a stand-alone JSON schema without $ref.
    """

    errors = []

    try:
        data = (await request_valid_raw("/queryables")).json()
    except Exception:
        errors.append("Could not get /queryables endpoint")

    if "$ref" in data.keys():
        errors.append("/queryables response contains $ref")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_3265(app_client):
    """
    CEOS-STAC-REQ-3265 - numberMatched [Requirement]

    A CEOS STAC catalog search response shall include the numberMatched property providing the number of items meeting
    the selection parameters, possibly estimated.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3270(app_client):
    """
    CEOS-STAC-REC-3270 - numberReturned [Recommendation]

    A CEOS STAC catalog search response should include the numberReturned property.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_3280(app_client):
    """
    CEOS-STAC-REQ-3280 - Result set navigation [Requirement]

    The $.links array in a search response shall include Link objects for navigating the search result set when the
    result set is too large to fit a single response using hyperlinks rel='next'.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3290(app_client):
    """
    CEOS-STAC-REC-3290 - Result set navigation [Recommendation]

    The $.links array in a search response should include Link objects for navigating the search result set when the
    result set is too large to fit a single response using hyperlinks rel='self', rel='prev', rel='first', rel='last'.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3295(app_client):
    """
    CEOS-STAC-REC-3295 - Result set navigation [Recommendation]

    Implementations may decide to only implement forward traversal via navigation/paging links. The $.links array in a
    search response should include Link objects for navigating the search result set when the result set is too large
    to fit a single response using hyperlinks rel='self', rel='prev', rel='next', rel='first', rel='last' per result
    page as shown below.
    """

    assert CANT_TEST, "TBD: Depends on test_CEOS_STAC_REC_3290"


async def test_CEOS_STAC_REC_3297(app_client):
    """
    CEOS-STAC-REC-3297 - Exceptions [Recommendation]

    A CEOS STAC catalog search response in case of exception shall return the applicable HTTP status code and a JSON
    response with the following members:
        code
        description
    """

    errors = []
    method = "GET"
    url = "/raise_exception"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Server error")
    for p in ["code", "description"]:
        if p not in data.keys():
            errors.append(f"Property not found on server exception: {p}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REC_3299():
    """
    CEOS-STAC-REC-3299 - Alternative response formats [Recommendation]

    A CEOS STAC catalog supporting alternative response formats shall allow this via content negotiation and use common
    media types also used for assets and links as referenced in the current Best Practices document
    (See Link and Asset type).
    """

    # Server only supports json
    assert True


async def test_CEOS_STAC_REC_3305(app_client):
    """
    CEOS-STAC-REC-3305 - Common metadata [Recommendation]

    CEOS implementations should encode the following STAC common metadata properties in granule or collection
    representations with a name corresponding to the preferred label defined in the corresponding GCMD keyword scheme:
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3308(app_client):
    """
    CEOS-STAC-REC-3308 - Controlled keywords [Recommendation]

    CEOS implementations should encode controlled keywords in granule or collection representations using the STAC
    Themes Extension Specification [AD29].
    """

    errors = []
    method = "GET"
    url = "/"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Could not get /search endpoint")

    if "https://stac-extensions.github.io/themes/v1.0.0/schema.json" not in data["conformsTo"]:
        errors.append("Server does not conform to STAC Themes Extension Specification")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_3310(app_client):
    """
    CEOS-STAC-REQ-3310 - Resource associations [Requirement]

    If a resource association can be encoded as Assets (e.g. role="metadata") or Link (e.g. rel="icon", rel="alternate")
    , STAC implementations shall give precedence to the encoding as Asset.
    """

    assert CANT_TEST, "Cant test"


async def test_CEOS_STAC_REQ_3320(app_client):
    """
    CEOS-STAC-REQ-3320 - Metadata assets [Requirement]

    CEOS STAC implementations shall provide a URL of the collection or granule metadata encoding in a particular
    standard representation (if available), via an Asset object with role=metadata.
    """

    assert CANT_TEST, "Cant test"


async def test_CEOS_STAC_REQ_3325(app_client):
    """
    CEOS-STAC-REQ-3325 - Link and Asset type attributes [Requirement]

    CEOS STAC implementations shall specify the media (MIME) type of the artifact associated with a resource by
    specifying the "type" attribute of the Link object or Asset object. The media types (type) from the table below
    shall be used for assets/links to the corresponding resources.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3330(app_client):
    """
    CEOS-STAC-REC-3330 - Asset roles [Recommendation]

    If additional asset roles are required (e.g. for cloud masks, snow masks etc), preference shall be given to the
    asset role names of the general Asset Roles Best Practices.
    """

    assert CANT_TEST, "Cant test"


async def test_CEOS_STAC_REC_3350(app_client):
    """
    CEOS-STAC-REC-3350 - Reference to metadata [Recommendation]

    Implementations should use Link objects with rel="alternate" or rel=”via” for referencing detailed representation
    of the metadata for a collection or granule. (The “via” relation should be preferred to convey the authoritative
    resource or the source of the information from where the Collection/Item is made.)
    """

    assert CANT_TEST, "Cant test"


async def test_CEOS_STAC_REC_3360(app_client):
    """
    CEOS-STAC-REC-3360 - Reference to documentation [Recommendation]

    Implementations should use a Link object with rel="describedby" to reference from a collection or granule to its
    documentation.
    """

    assert CANT_TEST, "Cant test"


async def test_CEOS_STAC_REQ_3410(app_client):
    """
    CEOS-STAC-REQ-3410 - Absolute links [Requirement]

    "href" attributes in links or assets shall use absolute paths and not relative paths in CEOS STAC collection or
    granule metadata records.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3420(app_client):
    """
    CEOS-STAC-REC-3420 - Root relation [Recommendation]

    Implementations should not use the rel="root" relation in STAC collection and item encodings as the original
    catalog/collections may be referenced or included in a federated catalog with a different root.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_3430(app_client):
    """
    CEOS-STAC-REC-3430 - Collection identifier [Recommendation]

    Implementations should carefully choose the "identifier" used for a STAC collection /collections/{identifier}
    to minimize the risk of duplicate collection identifiers when federated with catalogs and collections
    from other providers.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_4310(app_client):
    """
    CEOS-STAC-REQ-4310 - Granule search endpoints [Requirement]

    CEOS STAC granule catalogs shall advertise and provide the endpoints for granule search per individual collection
    in the STAC Collection representation as a Link object with rel="items" and type="application/geo+json".
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Could not get /collections endpoint")

    for col in data["collections"]:
        if "links" in col.keys():
            if len([x for x in col["links"] if x["rel"] == "items" and "href" in x.keys()]) == 0:
                errors.append(f"Collection {col['id']} doest not have Link to rel=items or its missing href field")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_PER_4320(app_client):
    """
    CEOS-STAC-PER-4320 - Cross-collection granule search endpoint [Permission]

    CEOS STAC granule catalogs may or may not advertise and provide a cross-collection endpoint for granule search,
    valid for all the collections in the STAC Catalog (typically the Landing Page)
    with rel="search" and type="application/geo+json" and may instead only provide individual granule search endpoints
    per collection via rel="items" in the collection representation.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_4330(app_client):
    """
    CEOS-STAC-REQ-4330 - Cross-collection granule search method [Requirement]

    CEOS STAC granule catalogs with cross-collection granule search endpoint shall support searches at the endpoint
    (rel="search") using the HTTP GET method.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_4340(request_valid_raw):
    """
    CEOS-STAC-REQ-4340 - Supported granule search parameters [Requirement]

    The STAC-API and OGC API-Features specifications define a list of fundamental search parameters.
    From these specifications, a CEOS STAC granule catalog shall support the following minimum set of search parameters
    for “granule” search at the rel="items" endpoint:
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    for path in ["/search", "/collections/{collection_id}/items"]:
        for param in ["limit", "bbox", "datetime"]:
            if param not in [x["name"] for x in data["paths"][path]["get"]["parameters"]]:
                errors.append(f"{param} parameter not advertised in {path} endpoint")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_4350(request_valid_raw):
    """
    CEOS-STAC-REQ-4350 - Additional granule search queryables [Requirement]

    A CEOS STAC granule catalog supporting additional queryables for a collection shall return the link to the
     Queryables object with the list of queryables that can be used in a filter expression for that collection
     via a link object in the collection representation (metadata) with
     rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" and type="application/schema+json" (typically,
     but not necessarily, at '/collections/{collectionId}/queryables').
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    if r"/collections/\{collection_id\}/queryables" not in data["paths"].keys():
        errors.append(r"/collections/\{collection_id\}/queryables not found in api")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_4630(request_valid_raw):
    """
    CEOS-STAC-REQ-4630 - Item search response representation [Requirement]

    A granule search response shall be represented as a GeoJSON FeatureCollection according to version v1.0.0 of
    the "STAC API ItemCollection Specification".
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    for path in ["/search", r"/collections/\{collection_id\}/items"]:
        try:
            data["paths"][path]["get"]["responses"]["200"]["content"]["application/geo+json"]
        except KeyError:
            errors.append(f"Path {path} does not respond with application/geo+json")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_4635(app_client):
    """
    CEOS-STAC-REQ-4635 - Item search numberMatched [Requirement]

    Granule search responses shall use the properties $.numberMatched and $.numberReturned as per version v1.0.0 of the
    "STAC API ItemCollection Specification" instead of using the deprecated "STAC API - Context Extension Specification"
    to communicate the number of results.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_4640(app_client):
    """
    CEOS-STAC-REQ-4640 - Allow for granule search-by-id [Requirement]

    The $.features[].id property in a granule search response shall allow navigation to a single granule using the id as
    a path parameter appended to the granule search endpoint (rel='items') e.g. /collections/{collection-id}/items/{id}.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_4645():
    """
    CEOS-STAC-REQ-4645 - Item search response representation [Requirement]

    Granules included in a granule search response shall be conformant with "CEOS STAC Granule Metadata Best Practices".
    """

    # Will be tested in a different block
    assert True


async def test_CEOS_STAC_REQ_5210(app_client):
    """
    CEOS-STAC-REQ-5210 - Collection access [Requirement]

    A CEOS STAC catalog shall support access to collection metadata from the catalog landing page using the rel="child"
    or rel="data" approach depicted above or both approaches combined.
    """

    errors = []
    method = "GET"
    url = "/"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Could not get / endpoint")

    if len([x for x in data["links"] if x["rel"] == "data"]) == 0:
        errors.append("No rel=data in landing page")

    if len([x for x in data["links"] if x["rel"] == "child"]) == 0:
        errors.append("No rel=data in landing page")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_CREQ_5320(app_client):
    """
    CEOS-STAC-CREQ-5320 - Collections endpoint [Conditional]

    A CEOS STAC catalog supporting collection search shall advertise the search endpoint for collections in the landing
    page with rel="data" (most often /collections), type="application/json" and declare the corresponding collection
    search conformance classes in the landing page. See "STAC API Collection Search" [AD07].
    """

    errors = []
    method = "GET"
    url = "/"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Could not get / endpoint")

    for c in [x for x in data["links"] if x["rel"] == "data"]:
        if c["type"] != "application/json":
            errors.append("rel=data type is not application/json")

    for conformance in [
        "https://api.stacspec.org/v1.0.0-rc.1/core",
        "https://api.stacspec.org/v1.0.0-rc.1/collection-search",
        "http://www.opengis.net/spec/ogcapi-common-2/1.0/conf/simple-query",
        "https://api.stacspec.org/v1.0.0/collections",
    ]:
        if conformance not in data["conformsTo"]:
            errors.append(f"Missing spec conformance {conformance}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5330(app_client):
    """
    CEOS-STAC-REQ-5330 - Collection search method [Requirement]

    A CEOS STAC collection catalog shall support collection searches at the collections endpoint (rel="data") using
    the HTTP GET method.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        response.json()
    except Exception:
        errors.append("Could not get /collections endpoint using GET")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5335(app_client):
    """
    CEOS-STAC-REC-5335 - Collection search endpoint [Recommendation]

    A CEOS STAC collection catalog should make its collections endpoint (rel="data") available at '/collections'.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        response.json()
    except Exception:
        errors.append("Could not get /collections endpoint using GET")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5340(request_valid_raw):
    """
    CEOS-STAC-REQ-5340 - Supported search parameters [Requirement]

    The STAC-API and OGC API-Features specifications define a list of fundamental search parameters.
    From these specifications, a CEOS STAC collection catalog shall support the following minimum set of search
    parameters for “collection” search at the collections endpoint:
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    for path in ["/collections"]:
        for param in ["limit", "bbox", "datetime"]:
            if param not in [x["name"] for x in data["paths"][path]["get"]["parameters"]]:
                errors.append(f"{param} parameter not advertised in {path} endpoint")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5360(request_valid_raw):
    """
    CEOS-STAC-REQ-5360 - Free text search [Requirement]

    For supporting free text searches, a CEOS STAC collection catalog shall advertise support for the HTTP query
    parameter q as in "STAC API Collection Search" [AD07].
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    for path in ["/collections"]:
        for param in ["q"]:
            if param not in [x["name"] for x in data["paths"][path]["get"]["parameters"]]:
                errors.append(f"{param} parameter not advertised in {path} endpoint")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_CREQ_5370(app_client):
    """
    CEOS-STAC-CREQ-5370 - Collection queryables [Conditional]

    A CEOS STAC collection catalog supporting additional queryables for collection search shall return the link to
    the Queryables object with the list of queryables that can be used in a filter expression via a link object in
    the collection search response with rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" and
    type="application/schema+json" (See also "STAC API Collection Search" [AD07].
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_5372(request_valid_raw):
    """
    CEOS-STAC-REQ-5372 - Collection search response representation [Requirement]

    A collection search response shall be represented as a JSON object according to the
    "STAC API - Collection Search" [AD07].
    """

    errors = []

    data = (await request_valid_raw("/api")).json()

    for path in ["/collections"]:
        try:
            data["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]
        except KeyError:
            errors.append(f"Path {path} does not respond with application/json")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5373(app_client):
    """
    CEOS-STAC-REQ-5373 - Allow for collection search-by-id [Requirement]

    The $.collections[].id property in a collection search response shall allow to navigate to a single collection using
    the id as a path parameter appended to the collection search endpoint (rel='data') e.g. /collections/{id}.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_5374(app_client):
    """
    CEOS-STAC-REQ-5374 - Collection search response representation [Requirement]

    Collections included in a collection search response shall be represented according to
    the "CEOS STAC Collection Metadata Best Practices".

    """

    # Will be tested in a different bloc
    assert True


async def test_CEOS_STAC_REQ_5390(app_client):
    """
    CEOS-STAC-REQ-5390 - Support for granule search [Requirement]

    Collections supporting two-step search shall contain a link with rel="items" and type="application/geo+json"
    in the STAC collection representation returned by the collection search.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url}endpoint using GET")

    for col in data["collections"]:
        items = [x for x in col["links"] if x["rel"] == "items"]
        if not items:
            errors.append(f"Collection {col['id']} does not have a rel=items link")
        for i in items:
            if i["type"] != "application/geo+json":
                errors.append(f"Collection {col['id']} does not have a rel=items link with type application/geo+json")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5392(app_client):
    """
    CEOS-STAC-REC-5392 - Support for granule search [Recommendation]

    Collections supporting granule search should contain a link with
    rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" and type="application/schema+json" in the
    STAC collection representation returned by the collection search.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url}endpoint using GET")

    for col in data["collections"]:
        items = [x for x in col["links"] if x["rel"] == "http://www.opengis.net/def/rel/ogc/1.0/queryables"]
        if not items:
            errors.append(
                f'Collection {col["id"]} does not have a rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" link'
            )

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5393(app_client):
    """
    CEOS-STAC-REQ-5393 - Support for granule search [Requirement]

    STAC Granule Catalogs shall advertise all "additional" collection specific search/filter parameters applicable for
    a granule search within a collection (if any) in the corresponding queryables object for that collection and not
    rely on a global set of queryables applicable to all collections made available via a link with
    rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" from the landing page
    (typically "/collections/{collectionId}/queryables" instead of "/queryables"),
    to be combined with a collection-specific set (which may be empty).
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        id = col["id"]

        url = f"/collection/{id}/queryables"

        try:
            response = await app_client.request(method, url, follow_redirects=True)
            data = response.json()
        except Exception:
            errors.append(f"Could not get {url}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_5395(app_client):
    """
    CEOS-STAC-REQ-5395 - Support for granule search [Requirement]

    Collections not supporting granule search shall not contain a link rel="items" and type="application/geo+json"
    in the STAC collection representation returned by the collection search.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_6210(app_client):
    """
    CEOS-STAC-REQ-6210 - Granule representation [Requirement]

    A(n EO) Granule metadata record shall be represented as a STAC Item according to version v1.0.0 of
    the "STAC Item Specification" [AD03].
    """

    # Covered by further tests
    assert True


async def test_CEOS_STAC_REQ_6220(app_client):
    """
    CEOS-STAC-REC-6220 - Temporal extents [Recommendation]

    STAC implementations should represent temporal extents in Items with the start_datetime and end_datetime
    properties and include the value for start_datetime also as datetime property.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_6230(app_client):
    """
    CEOS-STAC-REQ-6230 - Geographical extents [Requirement]

    STAC implementations shall represent geographical extents of Items with the geometry property
    (GeoJSON Geometry object or null if not available).
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_6235(app_client):
    """
    CEOS-STAC-REQ-6235 - Polygon geometry [Requirement]

    The geographical extent of an Item represented as polygon shall follow the right-hand rule with respect to the area
    it bounds and in case of a polygon with more than one ring, the first shall be the exterior ring and the others
    shall be interior rings as required by the GeoJSON specification.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_6240(app_client):
    """
    CEOS-STAC-REQ-6240 - Minimum-bounding rectangle [Requirement]

    CEOS implementations should render spatial extents using a minimum-bounding rectangle (MBR) with a GeoJSON bbox
    property RFC7946 in addition to the native more accurate representation of that extent with the geometry property.
    The value of the bbox element must be an array of length 4 (two long/lat pairs), with the southwesterly point
    followed by the northeasterly point.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_6250(app_client):
    """
    CEOS-STAC-REQ-6250 - Granule representation extension [Recommendation]

    A(n EO) Granule metadata record represented as a STAC Item should use applicable properties defined by
    the following STAC extensions:
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_PER_6255(app_client):
    """
    CEOS-STAC-PER-6255 - Granule representation extension validation [Permission]

    A CEOS STAC implementation may include a subset of properties in the item encoding defined by any of the above STAC
    extensions, even though the STAC extension may require additional properties to be included to pass the
    corresponding STAC extension JSON schema validation.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_6310(app_client):
    """
    CEOS-STAC-REC-6310 - Browse image [Recommendation]

    STAC implementations should provide a URL to the granule’s browse image when available, via an Asset object
    with role=overview.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_6320(app_client):
    """
    CEOS-STAC-REC-6320 - Thumbnail image [Recommendation]

    STAC implementations should provide a URL to the granule’s thumbnail image (smaller than the browse image) when
    available, via an Asset object with role=thumbnail.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_6330(app_client):
    """
    CEOS-STAC-REC-6330 - Data access [Recommendation]

    STAC implementations should provide the data access URL for the granule via an Asset object with role=data.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_6340(app_client):
    """
    CEOS-STAC-REC-6340 - Data access to multiple files [Recommendation]

    When data access to a granule in a granule search response is to be provided in multiple physical files, each file
    should be linked to via a separate Asset object with role=data.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_6360(app_client):
    """
    CEOS-STAC-REC-6360 - Alternate locations [Recommendation]

    When the same assets are available at multiple locations or via multiple protocols, they should be encoded as
     alternate asset as defined in the "STAC Alternate Assets Extension Specification" [AD24].
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_6410(app_client):
    """
    CEOS-STAC-REC-6410 - WMS Offering [Recommendation]

    STAC implementations should indicate available data access via WMS using a STAC Web Map Link as defined in [AD26].
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_6510(app_client):
    """
    CEOS-STAC-REQ-6510 - Absolute links [Requirement]

    "href" attributes in links or assets shall use absolute paths and not relative paths in CEOS STAC granule metadata
    records.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REQ_7210(app_client):
    """
    CEOS-STAC-REQ-7210 - Collection representation [Requirement]

    A(n EO) Collection metadata record shall be represented as a STAC Collection according to version v1.0.0 of the
    "STAC Collection Specification" [AD02].
    """

    # Covered by further tests
    assert True


async def test_CEOS_STAC_REC_7215(app_client):
    """
    CEOS-STAC-REC-7215 - Collection metadata dates [Recommendation]

    A(n EO) Collection metadata record should encode metadata dates using the $.created, $.updated and $.published
    properties according to the "STAC Timestamps Extension Specification" [AD20].
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        if "stac_extensions" in col.keys():
            for extension in col["stac_extensions"]:
                schema = requests.get(extension).json()
                try:
                    validate(instance=col, schema=schema)
                except Exception:
                    errors.append(f"Collection {col['id']} does not comply with extension: {extension}")
        else:
            errors.append(f"Collection {col['id']} metadata does not define any stac extensions")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7220(app_client):
    """
    CEOS-STAC-REQ-7220 - Platform information [Requirement]

    A(n EO) Collection metadata record shall encode the platform name(s) as $.summaries.platform property and use the
    platform name corresponding to the GCMD platforms preferred label.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        if "summaries" not in col.keys():
            errors.append(f"Summaries property not available on {col['id']}")

        if "summaries" in col.keys() and "platforms" not in col["summaries"].keys():
            errors.append(f"Summaries.platforms property not available on {col['id']}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7230(app_client):
    """
    CEOS-STAC-REQ-7230 - Instrument information [Requirement]

    A(n EO) Collection metadata record shall encode the instrument name(s) as $.summaries.instruments property and use
    the instrument names corresponding to the GCMD instruments preferred label.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        if "summaries" not in col.keys():
            errors.append(f"Summaries property not available on {col['id']}")

        if "summaries" in col.keys() and "instruments" not in col["summaries"].keys():
            errors.append(f"Summaries.instruments property not available on {col['id']}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7240(app_client):
    """
    CEOS-STAC-REQ-7240 - Science keywords [Requirement]

    A(n EO) Collection metadata record shall encode related science keywords as $.keywords property and use the science
    keywords corresponding to the GCMD Earth Science) preferred label.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        if "keywords" not in col.keys():
            errors.append(f"keywords property not available on {col['id']}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7250(app_client):
    """
    CEOS-STAC-REQ-7250 - DOI [Requirement]

    The DOI of a collection, if available, shall be encoded according to the Scientific Citation Extension Specification
    i.e. using the $.sci:doi property and a link object with rel="cite-as" [AD13].
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_7260(app_client):
    """
    CEOS-STAC-REQ-7260 - Provider names [Requirement]

    A(n EO) Collection metadata record shall encode provider information as $.providers[*] and use the GCMD Providers
    preferred label (skos:prefLabel) as $.providers[*].name.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        if "providers" not in col.keys():
            errors.append(f"Providers property not available on {col['id']}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7310(app_client):
    """
    CEOS-STAC-REQ-7310 - Item assets [Recommendation]

    In the case where all granules of a collection contain the same asset types, these assets should be provided in the
    collection encoding as Item asset as defined in the "STAC Item Assets Definition Extension Specification" [AD25].
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_7410(app_client):
    """
    CEOS-STAC-REQ-7410 - Support for granule search [Requirement]

    Collections supporting granule search shall contain a link with rel="items" and type="application/geo+json" in the
    STAC collection representation.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append("Could not get /collections endpoint")

    for col in data["collections"]:
        if "links" in col.keys():
            if len([x for x in col["links"] if x["rel"] == "items" and "href" in x.keys()]) == 0:
                errors.append(f"Collection {col['id']} doest not have Link to rel=items or its missing href field")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REC_7420(app_client):
    """
    CEOS-STAC-REC-7420 - Support for granule search [Recommendation]

    Collections supporting granule search should contain a link with
    rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" and type="application/schema+json" in the STAC collection
    representation.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url}endpoint using GET")

    for col in data["collections"]:
        items = [x for x in col["links"] if x["rel"] == "http://www.opengis.net/def/rel/ogc/1.0/queryables"]
        if not items:
            errors.append(
                f'Collection {col["id"]} does not have a rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" link'
            )

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7430(app_client):
    """
    CEOS-STAC-REQ-7430 - Support for granule search [Requirement]

    STAC Granule Catalogs shall advertise all "additional" collection specific search/filter parameters applicable for a
    granule search within a collection in the corresponding queryables object for that collection and not rely on a
    global set of queryables applicable to all collections made available via a link with
    rel="http://www.opengis.net/def/rel/ogc/1.0/queryables" from the landing page
    (typically "/collections/{collectionId}/queryables" instead of "/queryables"), to be combined with a
    collection-specific set (which may be empty).
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url} endpoint using GET")

    for col in data["collections"]:
        id = col["id"]

        url = f"/collection/{id}/queryables"

        try:
            response = await app_client.request(method, url, follow_redirects=True)
            data = response.json()
        except Exception:
            errors.append(f"Could not get {url}")

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7440(app_client):
    """
    CEOS-STAC-REQ-7440 - Support for granule search [Requirement]

    Collections not supporting granule search shall not contain a link rel="items" and type="application/geo+json" in
    the STAC collection representation.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_7450(app_client):
    """
    CEOS-STAC-REC-7450 - Reference to license [Recommendation]

    CEOS STAC collection metadata should include a Link object with rel="license" to reference an external file
    describing the license information for the collection, unless the license property has a specific SPDX license
    identifier.
    """

    errors = []
    method = "GET"
    url = "/collections"

    try:
        response = await app_client.request(method, url, follow_redirects=True)
        data = response.json()
    except Exception:
        errors.append(f"Could not get {url}endpoint using GET")

    for col in data["collections"]:
        items = [x for x in col["links"] if x["rel"] == "license"]
        if not items:
            errors.append(f'Collection {col["id"]} does not have a rel="license" link')

    [logger.error(e) for e in errors]
    assert len(errors) == 0


async def test_CEOS_STAC_REQ_7510(app_client):
    """
    CEOS-STAC-REQ-7510 - Absolute links [Requirement]

    "href" attributes in links or assets shall use absolute paths and not relative paths in CEOS STAC collection
    metadata records.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_7520(app_client):
    """
    CEOS-STAC-REC-7520 - Parent relation [Recommendation]

    Implementations should not use the rel="parent" relation in STAC collection encodings as the original collection may
    be referenced or included in a federated catalog below a different parent.
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_7530(app_client):
    """
    CEOS-STAC-REC-7530 - Keywords [Requirement]

    CEOS STAC collection metadata shall contain at least one platform keyword, one corresponding instrument keyword and
    one science keyword encoded according to CEOS-STAC-REQ-7220, CEOS-STAC-REQ-7230 and CEOS-STAC-REQ-7240.
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REQ_8510(app_client):
    """
    CEOS-STAC-REQ-8510 - No authentication for discovery [Requirement]

    STAC implementations shall not require authentication for collection and granule discovery and provide access to the
    following resources (if available) without requiring authentication:
    """

    assert CANT_TEST, "Requires socket"


async def test_CEOS_STAC_REC_8520(app_client):
    """
    CEOS-STAC-REC-8520 - Advertising authentication interface [Recommendation]

    STAC implementations requiring authentication for asset download should advertise this using the STAC Authentication
    Extension [AD32].
    """

    assert CANT_TEST, "Cant Test"


async def test_CEOS_STAC_REC_8530(app_client):
    """
    CEOS-STAC-REC-8530 - Advertising OpenID Connect authentication interface in granule metadata [Recommendation]

    STAC implementations requiring authentication via OpenID Connect for asset download (e.g. data download) should
    indicate this in the granule metadata using the STAC Authentication Extension [AD32] and refer to the metadata of
    the OpenID server.
    """

    assert CANT_TEST, "Cant Test"
