import pytest

from app.services.data_fetcher import DataFetcher


@pytest.mark.asyncio
async def test_get_multiple_assets_with_new_types():
    fetcher = DataFetcher()
    assets = [
        {"symbol": "NFT-TEST", "name": "Test NFT", "type": "nft"},
        {"symbol": "DEFI-TEST", "name": "Test DeFi", "type": "defi"},
        {"symbol": "INDEX-TEST", "name": "Test Index", "type": "index"},
        {"symbol": "BOND-TEST", "name": "Test Bond", "type": "bond"},
    ]
    results = await fetcher.get_multiple_assets(assets)
    assert len(results) == 4
    for asset, result in zip(assets, results, strict=False):
        assert result["symbol"] == asset["symbol"]
        assert result["type"] == asset["type"]
        assert result["name"] == asset["name"]
        assert "current_price" in result
        assert "chart_data" in result
