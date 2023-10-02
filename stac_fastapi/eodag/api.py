import attr
from fastapi.responses import StreamingResponse
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.api.models import ItemUri

from stac_fastapi.eodag.core import EodagCoreClient

@attr.s
class EeodagStacApi(StacApi):
    client: EodagCoreClient = attr.ib()

    def register_download_item(self):
        """Register download item endpoint (GET /collections/{collection_id}/items/{item_id}/download).

        Returns:
            None
        """
        self.router.add_api_route(
            name="Download Item",
            path="/collections/{collection_id}/items/{item_id}/download",
            response_class=StreamingResponse,
            methods=["GET"],
            endpoint=create_async_endpoint(
                self.client.download_item, ItemUri, StreamingResponse
            ),
        )

    def register_core(self):
        super().register_core()
        self.register_download_item()
