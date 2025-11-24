"""
Extended Exchange Order Manager
Uses x10-python-trading-starknet SDK for automatic order signing and submission
"""
import os
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Literal

# x10 SDK - handles signing automatically
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.configuration import EndpointConfig
from x10.perpetual.trading_client import PerpetualTradingClient
from x10.perpetual.orders import OrderSide, OrderType

# Mainnet configuration
STARKEX_MAINNET_CONFIG = EndpointConfig(
    chain_rpc_url="https://cloudflare-eth.com",
    api_base_url="https://api.extended.exchange/api/v1",
    stream_url="wss://api.extended.exchange/stream.extended.exchange/v1",
    onboarding_url="https://api.extended.exchange",
    signing_domain="extended.exchange",
    starknet_domain="extended.exchange",
    collateral_asset_contract="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    asset_operations_contract="0x1cE5D7f52A8aBd23551e91248151CA5A13353C65",
    collateral_asset_on_chain_id="0x2893294412a4c8f915f75892b395ebbf6859ec246ec365c3b1f56f47c3a0a5d",
    collateral_asset_id="0x2893294412a4c8f915f75892b395ebbf6859ec246ec365c3b1f56f47c3a0a5d",
    collateral_decimals=6,
)


class OrderManager:
    """
    Manages Extended Exchange orders using x10 SDK
    SDK automatically handles Starknet signing - no manual crypto needed!
    """
    
    def __init__(self):
        """Initialize OrderManager with x10 SDK client"""
        # Load credentials from environment
        self.api_key = os.getenv("EXTENDED_API_KEY") or os.getenv("Extended_1_API_KEY")
        self.public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY") or os.getenv("Extended_1_Stark_Key_Public")
        self.private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY") or os.getenv("Extended_1_Stark_Key_Private")
        self.vault = int(os.getenv("EXTENDED_VAULT_NUMBER") or os.getenv("Extended_1_Vault_Number", "0"))
        
        if not all([self.api_key, self.public_key, self.private_key]):
            raise ValueError(
                "Missing Extended API credentials. Required: "
                "EXTENDED_API_KEY (or Extended_1_API_KEY), "
                "EXTENDED_STARK_PUBLIC_KEY (or Extended_1_Stark_Key_Public), "
                "EXTENDED_STARK_PRIVATE_KEY (or Extended_1_Stark_Key_Private)"
            )
        
        # Create StarkPerpetualAccount (handles signing automatically!)
        self.account = StarkPerpetualAccount(
            vault=self.vault,
            private_key=self.private_key,
            public_key=self.public_key,
            api_key=self.api_key
        )
        
        # Create trading client with Starknet mainnet config
        self.client = PerpetualTradingClient.create(
            STARKEX_MAINNET_CONFIG,
            self.account
        )
        
        print(f"✅ OrderManager initialized with x10 SDK")
        print(f"   Vault: {self.vault}")
        print(f"   Public Key: {self.public_key[:10]}...")
    
    async def create_order(
        self,
        market: str,
        side: Literal["BUY", "SELL"],
        price: str,
        size: str,
        order_type: Literal["LIMIT"] = "LIMIT",
        time_in_force: Literal["POST_ONLY", "GTC", "IOC", "FOK"] = "POST_ONLY",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Create and submit order using x10 SDK
        SDK automatically handles Starknet signing!
        
        Args:
            market: Market symbol (e.g., "BTC-USD")
            side: "BUY" or "SELL"
            price: Order price as string
            size: Order size as string
            order_type: Order type (currently only LIMIT supported)
            time_in_force: Time in force (POST_ONLY, GTC, IOC, FOK)
            reduce_only: Whether order can only reduce position
            
        Returns:
            Dict with success, data, and status
        """
        print(f"\n📝 Creating {time_in_force} {side} order:")
        print(f"   Market: {market}")
        print(f"   Price: {price}")
        print(f"   Size: {size}")
        print(f"   Reduce Only: {reduce_only}")
        
        try:
            # Convert side to SDK enum
            order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
            
            # Map time_in_force to SDK parameters
            post_only = False
            if time_in_force == "POST_ONLY":
                sdk_order_type = OrderType.LIMIT
                post_only = True
            elif time_in_force == "IOC":
                sdk_order_type = OrderType.LIMIT
                # IOC is handled by short expiration
            elif time_in_force == "FOK":
                sdk_order_type = OrderType.LIMIT
                # FOK is handled by SDK
            else:  # GTC
                sdk_order_type = OrderType.LIMIT
            
            # Set expiration (required for Starknet)
            # Default 1 hour, shorter for IOC
            expiration_hours = 0.01 if time_in_force == "IOC" else 1
            expiration = int((datetime.now() + timedelta(hours=expiration_hours)).timestamp() * 1000)
            
            # Convert price and size to Decimal
            price_decimal = Decimal(price)
            size_decimal = Decimal(size)
            
            print(f"🔐 SDK will automatically sign order...")
            
            # Place order - SDK handles signing automatically!
            order = await self.client.orders.place_order(
                market_name=market,
                side=order_side,
                order_type=sdk_order_type,
                size=size_decimal,
                price=price_decimal,
                expiration=expiration,
                reduce_only=reduce_only,
                post_only=post_only
            )
            
            print(f"✅ Order created successfully!")
            print(f"   Order ID: {order.id}")
            print(f"   Status: {order.status}")
            
            return {
                "success": True,
                "data": {
                    "id": order.id,
                    "order_id": order.id,  # Backwards compatibility
                    "market": market,
                    "side": side,
                    "price": price,
                    "size": size,
                    "status": order.status,
                    "created_at": datetime.now().isoformat()
                },
                "status": 200
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error creating order: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status": 500
            }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order by ID
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Dict with success status
        """
        print(f"\n🗑️ Cancelling order: {order_id}")
        
        try:
            await self.client.orders.cancel_order(order_id)
            print(f"✅ Order {order_id} cancelled")
            
            return {
                "success": True,
                "message": f"Order {order_id} cancelled",
                "status": 200
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error cancelling order: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status": 500
            }
    
    async def get_open_orders(self, market: Optional[str] = None) -> Dict[str, Any]:
        """
        Get open orders, optionally filtered by market
        
        Args:
            market: Optional market filter
            
        Returns:
            Dict with success and orders data
        """
        print(f"\n📋 Fetching open orders{f' for {market}' if market else ''}...")
        
        try:
            # Get orders with OPEN/PENDING status
            orders = await self.client.account.get_orders_history(
                market_names=[market] if market else None,
                order_statuses=["OPEN", "PENDING"]
            )
            
            print(f"✅ Found {len(orders)} open orders")
            
            return {
                "success": True,
                "data": orders,
                "status": 200
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error fetching orders: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status": 500
            }
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information (balances, positions, etc.)
        
        Returns:
            Dict with success and account data
        """
        print(f"\n👤 Fetching account info...")
        
        try:
            account_info = await self.client.account.get_account()
            print(f"✅ Account info fetched")
            
            return {
                "success": True,
                "data": account_info,
                "status": 200
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error fetching account info: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "status": 500
            }


# Global singleton instance
order_manager: Optional[OrderManager] = None


def get_order_manager() -> OrderManager:
    """
    Get or create OrderManager singleton instance
    
    Returns:
        OrderManager instance
    """
    global order_manager
    if order_manager is None:
        order_manager = OrderManager()
    return order_manager
