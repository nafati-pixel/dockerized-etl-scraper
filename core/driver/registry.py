"""Factory registry for dynamic provisioning of parsing strategies."""

from scraper.driver.platforms.mytek import MyTekAPIParser

from .interface import RetailerParsingStrategy

# Statically mapped registry of available domain strategies
_STRATEGY_REGISTRY: dict[str, type[RetailerParsingStrategy]] = {
    "mytek": MyTekAPIParser,
}


def provision_parsing_strategy(retailer_name: str) -> RetailerParsingStrategy:
    """
    Factory mechanism to instantiate a specific parsing strategy.
    
    Raises:
        ValueError: If the requested retailer strategy does not exist in the registry.
    """
    normalized_name = retailer_name.lower().strip()
    strategy_class = _STRATEGY_REGISTRY.get(normalized_name)
    
    if strategy_class is None:
        available_strategies = sorted(_STRATEGY_REGISTRY.keys())
        raise ValueError(
            f"Extraction strategy for '{normalized_name}' is not registered. "
            f"Available providers: {available_strategies}"
        )
        
    return strategy_class()
