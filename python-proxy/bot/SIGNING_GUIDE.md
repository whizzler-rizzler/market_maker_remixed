# Starknet Order Signing Guide

## Problem z Previous Implementation

**Stary kod (NIEPRAWIDŁOWY):**
```python
from ecdsa import SigningKey, SECP256k1  # ❌ Wrong curve!
from starknet_py.hash.utils import pedersen_hash

# Wrong signing
signing_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
signature_bytes = signing_key.sign_digest(hash_bytes, sigencode=sigencode_string)
```

**Problem:**
- SECP256k1 to Bitcoin/Ethereum curve
- StarkEx używa **Stark curve** (nie SECP256k1!)
- `ecdsa` library nie obsługuje Stark curve
- Hash generation był uproszczony i nieprawidłowy

## Poprawna Implementation

**Nowy kod (PRAWIDŁOWY):**
```python
from starkware.crypto.signature.signature import sign, pedersen_hash

# Correct Starknet signing
private_key_int = int(self.starknet_private_key, 16)
r, s = sign(msg_hash=order_hash, priv_key=private_key_int)
```

**Dlaczego to działa:**
- ✅ `starkware.crypto.signature` używa właściwej Stark curve
- ✅ `sign()` function jest native dla StarkEx
- ✅ Generuje prawidłowe (r, s) signatures
- ✅ Compatible z Extended Exchange (StarkEx perpetual)

## Order Hash Generation

### StarkEx Message Format

Extended Exchange używa StarkEx perpetual trading format:

```python
# Pedersen hash chain (order matters!)
order_hash = pedersen_hash(market_id, side)
order_hash = pedersen_hash(order_hash, price_scaled)
order_hash = pedersen_hash(order_hash, size_scaled)
order_hash = pedersen_hash(order_hash, nonce)
order_hash = pedersen_hash(order_hash, time_in_force)
order_hash = pedersen_hash(order_hash, reduce_only)
```

### Parameters

1. **market_id**: Market as felt (0-2^251)
   ```python
   market_bytes = "BTC-USD".encode('utf-8')
   market_id = int.from_bytes(market_bytes[:31], byteorder='big') % (2**251)
   ```

2. **side**: 0 = BUY, 1 = SELL
   ```python
   side_int = 0 if side == "BUY" else 1
   ```

3. **price_scaled**: Price with 8 decimals
   ```python
   price_scaled = int(float("60000.0") * 10**8)  # 6000000000000
   ```

4. **size_scaled**: Size with 8 decimals
   ```python
   size_scaled = int(float("0.01") * 10**8)  # 1000000
   ```

5. **nonce**: Unix timestamp
   ```python
   nonce = int(time.time())
   ```

6. **time_in_force**: POST_ONLY=3, GTC=0, IOC=1, FOK=2
   ```python
   tif_map = {"POST_ONLY": 3, "GTC": 0, "IOC": 1, "FOK": 2}
   tif_int = tif_map.get(time_in_force, 0)
   ```

7. **reduce_only**: 0 or 1
   ```python
   reduce_only_int = 1 if reduce_only else 0
   ```

## Signature Verification Flow

```
1. Bot constructs order parameters
   ↓
2. generate_order_hash() creates Pedersen hash
   ↓
3. sign_order() signs hash with Starknet private key
   ↓
4. Order + signature sent to Extended API
   ↓
5. Extended verifies signature with public key
   ↓
6. If valid → order accepted
   If invalid → 401/403 error
```

## Testing Signatures

### Verify Signature Locally (Before Sending)
```python
from starkware.crypto.signature.signature import verify

# After signing
is_valid = verify(
    msg_hash=order_hash,
    r=r,
    s=s,
    public_key=int(self.starknet_public_key, 16)
)

if not is_valid:
    print("❌ Signature verification failed locally!")
else:
    print("✅ Signature valid, safe to send to Extended API")
```

### Debug Hash Components
```python
print(f"Hash inputs:")
print(f"  market_id: {market_id}")
print(f"  side: {side_int}")
print(f"  price: {price_scaled}")
print(f"  size: {size_scaled}")
print(f"  nonce: {nonce}")
print(f"  tif: {tif_int}")
print(f"  reduce_only: {reduce_only_int}")
print(f"Final hash: {hex(order_hash)}")
```

## Common Errors

### 1. "Invalid signature" from Extended API
**Cause:** Hash generation mismatch
**Solution:** Ensure hash components match Extended's exact format

### 2. "Unauthorized" 401 error
**Cause:** Wrong public key or signature format
**Solution:** Verify public key matches private key:
```python
from starkware.crypto.signature.signature import private_to_stark_key
expected_public = private_to_stark_key(int(private_key, 16))
assert expected_public == int(public_key, 16), "Public key mismatch!"
```

### 3. "Nonce already used"
**Cause:** Duplicate timestamp nonce
**Solution:** Use microseconds or add counter:
```python
nonce = int(time.time() * 1000)  # Milliseconds
```

## Dependencies

### Required Package
```bash
pip install cairo-lang==0.13.2
```

**NOT:**
- ~~starknet-py~~ (different library, ikke compatible)
- ~~ecdsa~~ (wrong curve)
- ~~eth-utils~~ (Ethereum, not Starknet)

### Import
```python
from starkware.crypto.signature.signature import (
    sign,
    verify,
    pedersen_hash,
    private_to_stark_key
)
```

## Extended API Response

### Success (200/201)
```json
{
  "id": "order_abc123",
  "market": "BTC-USD",
  "side": "BUY",
  "price": "60000.0",
  "size": "0.01",
  "status": "PENDING",
  "created_at": "2025-01-..."
}
```

### Failure (401/403)
```json
{
  "error": "Invalid signature",
  "code": 401,
  "message": "Signature verification failed"
}
```

## Next Steps

1. ✅ Install `cairo-lang==0.13.2`
2. ✅ Use `starkware.crypto.signature.sign()`
3. ✅ Implement proper hash chain
4. 🔄 Test with Extended API
5. 🔄 Add signature verification before sending
6. 🔄 Handle nonce collisions

## References

- [StarkEx Perpetual Documentation](https://docs.starkware.co/starkex/perpetual/)
- [cairo-lang Signature Module](https://github.com/starkware-libs/cairo-lang)
- [Pedersen Hash Explanation](https://docs.starkware.co/starkex/crypto/pedersen-hash-function.html)
