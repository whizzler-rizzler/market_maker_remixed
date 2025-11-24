import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Loader2 } from 'lucide-react';

const PYTHON_PROXY_URL = import.meta.env.VITE_PYTHON_PROXY_URL || 'https://extended-account-stream.onrender.com';

export const OrderPanel = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  
  // Order form state
  const [market, setMarket] = useState('BTC-PERP');
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [price, setPrice] = useState('');
  const [size, setSize] = useState('');
  const [timeInForce, setTimeInForce] = useState<'POST_ONLY' | 'GTC' | 'IOC' | 'FOK'>('POST_ONLY');
  const [reduceOnly, setReduceOnly] = useState(false);

  const handleSubmitOrder = async () => {
    if (!price || !size) {
      toast({
        title: 'Validation Error',
        description: 'Price and size are required',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${PYTHON_PROXY_URL}/api/orders/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          market,
          side,
          price,
          size,
          timeInForce,
          reduceOnly,
        }),
      });

      const result = await response.json();

      if (response.ok && result.success) {
        toast({
          title: 'Order Created',
          description: `${side} ${size} @ ${price} on ${market}`,
        });
        
        // Clear form
        setPrice('');
        setSize('');
      } else {
        throw new Error(result.error || 'Order creation failed');
      }
    } catch (error) {
      console.error('Order error:', error);
      toast({
        title: 'Order Failed',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Market Making Bot - Order Panel</CardTitle>
        <CardDescription>
          Place POST_ONLY orders on Extended Exchange
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="market">Market</Label>
            <Input
              id="market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
              placeholder="BTC-PERP"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="side">Side</Label>
            <Select value={side} onValueChange={(v) => setSide(v as 'BUY' | 'SELL')}>
              <SelectTrigger id="side">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BUY">BUY</SelectItem>
                <SelectItem value="SELL">SELL</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="price">Price</Label>
            <Input
              id="price"
              type="number"
              step="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0.00"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="size">Size</Label>
            <Input
              id="size"
              type="number"
              step="0.001"
              value={size}
              onChange={(e) => setSize(e.target.value)}
              placeholder="0.000"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="timeInForce">Time In Force</Label>
          <Select 
            value={timeInForce} 
            onValueChange={(v) => setTimeInForce(v as typeof timeInForce)}
          >
            <SelectTrigger id="timeInForce">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="POST_ONLY">POST ONLY (Market Making)</SelectItem>
              <SelectItem value="GTC">GTC (Good Till Cancel)</SelectItem>
              <SelectItem value="IOC">IOC (Immediate or Cancel)</SelectItem>
              <SelectItem value="FOK">FOK (Fill or Kill)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center space-x-2">
          <Switch
            id="reduceOnly"
            checked={reduceOnly}
            onCheckedChange={setReduceOnly}
          />
          <Label htmlFor="reduceOnly">
            Reduce Only (can only decrease position)
          </Label>
        </div>

        <Button 
          onClick={handleSubmitOrder} 
          disabled={loading}
          className="w-full"
          variant={side === 'BUY' ? 'default' : 'destructive'}
        >
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {loading ? 'Placing Order...' : `Place ${side} Order`}
        </Button>

        <div className="pt-4 border-t">
          <p className="text-sm text-muted-foreground">
            <strong>POST ONLY:</strong> Order will only execute if it adds liquidity (rests on the order book).
            If it would execute immediately, the order is cancelled.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            <strong>REDUCE ONLY:</strong> Order can only reduce your existing position size, not increase it.
          </p>
        </div>
      </CardContent>
    </Card>
  );
};
