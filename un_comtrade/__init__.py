"""UN Comtrade Python SDK.

A production-quality Python SDK for the UN Comtrade (UNSD) trade
statistics API.

The single public entry point is :class:`un_comtrade.client.ComtradeClient`,
re-exported here as :data:`ComtradeClient` for convenience::

    from un_comtrade import ComtradeClient

    client = ComtradeClient()  # reads UN_COMTRADE_KEY from env
    countries = client.metadata.get_countries()
    exports = client.trade.get_exports(699, "2022")

The full public surface is documented in `docs/007_SDK_SPECIFICATION.md`.
"""

from un_comtrade.__version__ import __version__
from un_comtrade.client import ComtradeClient

__all__ = ["ComtradeClient", "__version__"]