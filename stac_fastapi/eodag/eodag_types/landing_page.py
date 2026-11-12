"""EODAG-specific STAC landing page model."""

from typing import Any

from stac_fastapi.types import stac


class EodagLandingPage(stac.LandingPage):
    """STAC landing page with EODAG federation information."""

    federation: dict[str, Any]
