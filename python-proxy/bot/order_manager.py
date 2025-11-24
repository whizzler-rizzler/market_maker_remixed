"""
Extended Exchange Order Manager
Handles order creation, signing, and submission to Extended API
"""

import aiohttp
import os
import time
import json
from typing import Dict, Any, Optional, Literal
from starkware.crypto.signature.signature import sign, pedersen_hash, verify, private_to_stark_key

class OrderManager:
    def __init__(self):
        self.api_key = os.getenv("Extended_1_API_KEY")
        self.base_url = os.getenv("EXTENDED_API_BASE_URL", "https://api.starknet.extended.exchange/api/v1")
        self.base_url = self.base_url.rstrip("/")
        
        # Starknet credentials from environment
        self.starknet_public_key = os.getenv("Extended_1_Stark_Key_Public")
        self.starknet_private_key = os.getenv("Extended_1_Stark_Key_Private")
        self.client_id = os.getenv("Extended_1_Client_Id")
        self.vault_number = os.getenv("Extended_1_Vault_Number")
        
        if not all([self.api_key, self.starknet_public_key, self.starknet_private_key]):
            raise ValueError("Missing required Extended API credentials in environment variables")
        
        # Verify public key matches private key
        try:
            expected_public = private_to_stark_key(int(self.starknet_private_key, 16))
            actual_public = int(self.starknet_public_key, 16)
            if expected_public != actual_public:
                raise ValueError(f"Public key mismatch! Expected {hex(expected_public)}, got {hex(actual_public)}")
            print(f"✅ Key pair verified - public key matches private key")
        except Exception as e:
            print(f"⚠️ Could not verify key pair: {e}")
        
        print(f"✅ OrderManager initialized")
        print(f"   Client ID: {self.client_id}")
        print(f"   Vault: {self.vault_number}")
        print(f"   Public Key: {self.starknet_public_key[:10]}...")

    def generate_order_hash(self, order_params: Dict[str, Any]) -> int:
        """
        Generate order hash for Starknet signature using Pedersen hash
        Compatible with StarkEx perpetual exchange format
        """
        # Extract order parameters
        market = order_params["market"]
        side = order_params["side"]  # BUY or SELL
        price = order_params["price"]
        size = order_params["size"]
        time_in_force = order_params["timeInForce"]
        reduce_only = order_params["reduceOnly"]
        
        # Convert market to market ID (simplified - may need Extended's actual market IDs)
        market_bytes = market.encode('utf-8')
        market_id = int.from_bytes(market_bytes[:31], byteorder='big') % (2**251)
        
        # Convert side to integer (0 = BUY, 1 = SELL for StarkEx)
        side_int = 0 if side == "BUY" else 1
        
        # Price and size with 8 decimal precision
        price_scaled = int(float(price) * 10**8)
        size_scaled = int(float(size) * 10**8)
        
        # Nonce (timestamp in seconds)
        nonce = int(time.time())
        
        # Convert time_in_force to integer
        tif_map = {"POST_ONLY": 3, "GTC": 0, "IOC": 1, "FOK": 2}
        tif_int = tif_map.get(time_in_force, 0)
        
        # Reduce only flag
        reduce_only_int = 1 if reduce_only else 0
        
        # Build hash using Pedersen hash chain (StarkEx format)
        # Hash chain: market_id -> side -> price -> size -> nonce -> tif -> reduce_only
        order_hash = pedersen_hash(market_id, side_int)
        order_hash = pedersen_hash(order_hash, price_scaled)
        order_hash = pedersen_hash(order_hash, size_scaled)
        order_hash = pedersen_hash(order_hash, nonce)
        order_hash = pedersen_hash(order_hash, tif_int)
        order_hash = pedersen_hash(order_hash, reduce_only_int)
        
        print(f"   Hash components: market_id={market_id}, side={side_int}, price={price_scaled}, size={size_scaled}")
        
        return order_hash

    def sign_order(self, order_hash: int) -> tuple[int, int]:
        """
        Sign order hash with Starknet private key using starkware crypto
        Returns (r, s) signature components compatible with StarkEx
        """
        # Convert private key from hex string to integer
        private_key_int = int(self.starknet_private_key, 16)
        
        # Sign using starkware's sign function (returns r, s)
        r, s = sign(msg_hash=order_hash, priv_key=private_key_int)
        
        print(f"   Signature generated: r={hex(r)[:16]}..., s={hex(s)[:16]}...")
        
        # Verify signature locally before sending
        public_key_int = int(self.starknet_public_key, 16)
        is_valid = verify(msg_hash=order_hash, r=r, s=s, public_key=public_key_int)
        
        if is_valid:
            print(f"   ✅ Signature verified locally")
        else:
            print(f"   ❌ WARNING: Signature verification failed locally!")
            raise ValueError("Signature verification failed - will not send order")
        
        return (r, s)

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
                    # Check status first
                    if response.status not in [200, 201]:
                        response_text = await response.text()
                        print(f"❌ Order failed: HTTP {response.status}")
                        print(f"   Response: {response_text[:200]}")
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}: {response_text[:200]}",
                            "status": response.status
                        }
                    
                    # Try to parse JSON
                    try:
                        response_data = await response.json()
                    except Exception as json_err:
                        response_text = await response.text()
                        print(f"❌ Failed to parse JSON response: {json_err}")
                        print(f"   Response text: {response_text[:200]}")
                        return {
                            "success": False,
                            "error": f"Invalid JSON response: {response_text[:200]}",
                            "status": response.status
                        }
                    
                    print(f"✅ Order created successfully!")
                    print(f"   Order ID: {response_data.get('id', 'N/A')}")
                    return {
                        "success": True,
                        "data": response_data,
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
