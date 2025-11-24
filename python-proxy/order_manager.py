"""
Extended Exchange Order Manager
Handles order creation, signing, and submission to Extended API
"""

import aiohttp
import os
import time
import json
from typing import Dict, Any, Optional, Literal
from starknet_py.hash.utils import pedersen_hash
from starknet_py.net.signer.key_pair import KeyPair
from eth_utils import to_checksum_address

class OrderManager:
    def __init__(self):
        self.api_key = os.getenv("EXTENDED_API_KEY")
        self.base_url = os.getenv("EXTENDED_API_BASE_URL", "https://api.starknet.extended.exchange/api/v1")
        self.base_url = self.base_url.rstrip("/")
        
        # Starknet credentials from environment
        self.starknet_public_key = os.getenv("Extended_2_D61658C_STARKNET_PUBLIC")
        self.starknet_private_key = os.getenv("Extended_2_D61658C_STARKNET_PRIVATE")
        self.client_id = os.getenv("Extended_2_D61658C_CLIENT_ID")
        self.vault_number = os.getenv("Extended_2_D61658C_VAULT_NUMBER")
        
        if not all([self.api_key, self.starknet_public_key, self.starknet_private_key]):
            raise ValueError("Missing required Extended API credentials in environment variables")
        
        print(f"✅ OrderManager initialized")
        print(f"   Client ID: {self.client_id}")
        print(f"   Vault: {self.vault_number}")
        print(f"   Public Key: {self.starknet_public_key[:10]}...")

    def generate_order_hash(self, order_params: Dict[str, Any]) -> int:
        """
        Generate order hash for Starknet signature
        Based on Extended's order structure
        """
        # Extract order parameters
        market = order_params["market"]
        side = order_params["side"]  # BUY or SELL
        order_type = order_params["type"]  # LIMIT
        price = order_params["price"]
        size = order_params["size"]
        
        # Convert to Starknet format
        # This is a simplified hash - need to match Extended's exact format
        elements = [
            int(self.starknet_public_key, 16),
            int(market.encode().hex(), 16) % (2**251),  # market as felt
            1 if side == "BUY" else 2,  # side as felt
            int(float(price) * 10**8),  # price with 8 decimals
            int(float(size) * 10**8),  # size with 8 decimals
            int(time.time()),  # timestamp
        ]
        
        # Pedersen hash chain
        order_hash = elements[0]
        for element in elements[1:]:
            order_hash = pedersen_hash(order_hash, element)
        
        return order_hash

    def sign_order(self, order_hash: int) -> tuple[int, int]:
        """
        Sign order hash with Starknet private key
        Returns (r, s) signature components
        """
        # Create KeyPair from private key
        key_pair = KeyPair.from_private_key(int(self.starknet_private_key, 16))
        # Sign the hash
        signature = key_pair.sign_hash(order_hash)
        # Return (r, s) components
        return (signature[0], signature[1])

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
        Create and submit an order to Extended Exchange
        
        Args:
            market: Market symbol (e.g., "BTC-PERP")
            side: Order side ("BUY" or "SELL")
            price: Order price as string
            size: Order size as string
            order_type: Order type (default: "LIMIT")
            time_in_force: Time in force (default: "POST_ONLY")
            reduce_only: If True, order can only reduce position size
        
        Returns:
            API response with order details
        """
        print(f"\n📝 Creating {time_in_force} {side} order:")
        print(f"   Market: {market}")
        print(f"   Price: {price}")
        print(f"   Size: {size}")
        print(f"   Reduce Only: {reduce_only}")
        
        # Prepare order parameters
        order_params = {
            "market": market,
            "side": side,
            "type": order_type,
            "price": price,
            "size": size,
            "timeInForce": time_in_force,
            "reduceOnly": reduce_only,
            "clientId": self.client_id,
            "starknetPublicKey": self.starknet_public_key,
        }
        
        # Generate and sign order hash
        order_hash = self.generate_order_hash(order_params)
        print(f"   Order Hash: {hex(order_hash)}")
        
        signature = self.sign_order(order_hash)
        order_params["signature"] = {
            "r": hex(signature[0]),
            "s": hex(signature[1])
        }
        
        print(f"   Signature: r={hex(signature[0])[:10]}..., s={hex(signature[1])[:10]}...")
        
        # Submit order to Extended API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/orders",
                    headers={
                        "X-Api-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=order_params,
                    timeout=aiohttp.ClientTimeout(total=10.0)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status in [200, 201]:
                        print(f"✅ Order created successfully!")
                        print(f"   Order ID: {response_data.get('id', 'N/A')}")
                        return {
                            "success": True,
                            "data": response_data,
                            "status": response.status
                        }
                    else:
                        print(f"❌ Order failed: HTTP {response.status}")
                        print(f"   Response: {response_data}")
                        return {
                            "success": False,
                            "error": response_data,
                            "status": response.status
                        }
        except Exception as e:
            print(f"❌ Error creating order: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": 500
            }

    async def get_open_orders(self, market: Optional[str] = None) -> Dict[str, Any]:
        """
        Get open orders from Extended API
        
        Args:
            market: Optional market filter
        
        Returns:
            List of open orders
        """
        try:
            params = {}
            if market:
                params["market"] = market
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/orders",
                    headers={
                        "X-Api-Key": self.api_key,
                    },
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "data": data
                        }
                    else:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "error": error_data,
                            "status": response.status
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": 500
            }

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order by ID
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Cancellation result
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.base_url}/orders/{order_id}",
                    headers={
                        "X-Api-Key": self.api_key,
                    },
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as response:
                    if response.status in [200, 204]:
                        print(f"✅ Order {order_id} cancelled")
                        return {
                            "success": True,
                            "message": f"Order {order_id} cancelled"
                        }
                    else:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "error": error_data,
                            "status": response.status
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status": 500
            }

# Global instance
order_manager: Optional[OrderManager] = None

def get_order_manager() -> OrderManager:
    """Get or create OrderManager singleton"""
    global order_manager
    if order_manager is None:
        order_manager = OrderManager()
    return order_manager
