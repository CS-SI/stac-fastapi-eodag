
from typing import Annotated, Literal

import geojson
from pydantic import Field


async def test_basic_queryables(request_valid):
    """Response for /queryables request without filters must contain correct fields"""
    res = await request_valid(
        f"queryables", check_links=False
    )
    assert "properties" in res
    assert "collection" in res["properties"]
    assert len(res["properties"]) == 1
    assert "additionalProperties" in res and res["additionalProperties"]
    assert "description" in res and res["description"] == "Queryable names for the stac-fastapi."
    assert "title" in res and res["title"] == "Queryables for stac-fastapi."
    assert "type" in res and res["type"] == "object"

async def test_collection_queryables(mock_list_queryables, app_client):
    """Response for queryables of specific collection must contain values returned by eodag lib"""
    eodag_response = {
        "providerProductType": Annotated[Literal[tuple(sorted(["SAR", "GRD"]))], Field(default="SAR", **{"title": "Product type"})],
        "start": Annotated[str, Field(..., **{"title": "Start date"})],
        "end": Annotated[str, Field(..., **{"title": "End date"})]
    }
    mock_list_queryables.return_value = eodag_response
    response = await app_client.request(
        method="GET",
        url="/collections/ABC_SAR/queryables",
        follow_redirects=True,
    )
    result = geojson.loads(response.content.decode("utf-8"))
    assert "properties" in result
    assert len(result["properties"]) == 2
    assert "product:type" in result["properties"]
    assert result["properties"]["product:type"]["default"] == "SAR"
    assert result["properties"]["product:type"]["enum"] == ["GRD", "SAR"]
    assert "datetime" in result["properties"]