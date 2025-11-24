"""
Bot Configuration
Simple configuration class for market making bot parameters
"""

class BotConfig:
    """Configuration for the market making bot"""
    
    # Trading parameters
    market: str = "BTC-USD"
    spread_percentage: float = 0.001  # 0.1% spread
    order_size: str = "0.01"
    
    # Execution parameters
    refresh_interval: int = 5  # seconds
    price_move_threshold: float = 0.002  # 0.2% price change triggers refresh
    
    # Control
    enabled: bool = False

# Global config instance
config = BotConfig()
