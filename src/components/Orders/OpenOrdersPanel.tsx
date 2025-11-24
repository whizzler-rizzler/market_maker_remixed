import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, FileText } from "lucide-react";
import { useOpenOrders } from "@/hooks/useOpenOrders";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const OpenOrdersPanel = () => {
  const { orders, lastUpdate } = useOpenOrders();

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('pl-PL', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatPrice = (price: string) => {
    return parseFloat(price).toLocaleString('pl-PL', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  };

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Otwarte Zlecenia
          </CardTitle>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            {lastUpdate.toLocaleTimeString('pl-PL')}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {orders.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            Brak otwartych zleceń
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Wszystkie zlecenia ({orders.length})
            </div>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rynek</TableHead>
                    <TableHead>Strona</TableHead>
                    <TableHead>Typ</TableHead>
                    <TableHead className="text-right">Cena</TableHead>
                    <TableHead className="text-right">Ilość</TableHead>
                    <TableHead className="text-right">Wypełnione</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Czas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orders.map((order: any) => (
                    <TableRow key={order.id}>
                      <TableCell className="font-medium">{order.market}</TableCell>
                      <TableCell>
                        <Badge variant={order.side === 'BUY' ? 'default' : 'destructive'}>
                          {order.side}
                        </Badge>
                      </TableCell>
                      <TableCell>{order.orderType}</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatPrice(order.price)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {order.size}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {order.filledSize || '0'}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{order.status}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatTime(order.createdTime)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
