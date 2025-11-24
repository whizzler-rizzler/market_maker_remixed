import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useExtendedWebSocket } from "@/hooks/useExtendedWebSocket";
import { FileText, Clock } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export const OrdersPanel = () => {
  const { extendedData } = useExtendedWebSocket();
  const orders = extendedData.orders || [];
  const lastUpdate = extendedData.lastUpdate.orders || new Date().toLocaleTimeString('pl-PL');

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('pl-PL');
  };

  const getSideBadgeVariant = (side: string) => {
    return side === 'BUY' ? 'default' : 'destructive';
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'PENDING':
        return 'secondary';
      case 'OPEN':
        return 'default';
      case 'FILLED':
        return 'outline';
      case 'CANCELLED':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  return (
    <Card className="bg-card border-primary/20">
      <CardHeader>
        <CardTitle className="text-primary flex items-center gap-2">
          <FileText className="w-5 h-5" />
          OTWARTE ZLECENIA
          <span className="ml-auto text-sm text-muted-foreground flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {lastUpdate}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {orders.length === 0 ? (
          <div className="text-center text-muted-foreground py-8">
            Brak otwartych zleceń
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rynek</TableHead>
                  <TableHead>Strona</TableHead>
                  <TableHead>Typ</TableHead>
                  <TableHead>Cena</TableHead>
                  <TableHead>Rozmiar</TableHead>
                  <TableHead>Wypełnione</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Utworzono</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((order: any) => (
                  <TableRow key={order.id}>
                    <TableCell className="font-medium">{order.market}</TableCell>
                    <TableCell>
                      <Badge variant={getSideBadgeVariant(order.side)}>
                        {order.side}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{order.orderType}</TableCell>
                    <TableCell className="font-mono">${parseFloat(order.price).toFixed(2)}</TableCell>
                    <TableCell className="font-mono">{parseFloat(order.size).toFixed(4)}</TableCell>
                    <TableCell className="font-mono">{parseFloat(order.filledSize || '0').toFixed(4)}</TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(order.status)}>
                        {order.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {formatTime(order.createdTime)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
