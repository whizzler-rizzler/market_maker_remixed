import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Trade {
  id: string;
  accountId: number;
  market: string;
  orderId: string;
  side: string;
  price: string;
  qty: string;
  value: string;
  fee: string;
  tradeType: string;
  createdTime: number;
  isTaker: boolean;
}

interface TradeHistoryProps {
  trades: Trade[];
}

export const TradeHistory = ({ trades }: TradeHistoryProps) => {
  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('pl-PL');
  };

  const formatPrice = (price: string) => {
    return parseFloat(price).toFixed(2);
  };

  return (
    <Card className="border-primary/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-bold text-primary flex items-center gap-2">
          📊 Historia Transakcji
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="trades" className="border-border/50">
            <AccordionTrigger className="text-sm py-2 hover:no-underline">
              <div className="flex items-center gap-2">
                <span>Wszystkie transakcje ({trades.length})</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <ScrollArea className="h-[400px] pr-2">
                <div className="space-y-1">
                  {trades.length > 0 ? (
                    trades.map((trade) => {
                      return (
                        <div 
                          key={trade.id}
                          className="grid grid-cols-7 gap-2 p-2 bg-card/50 rounded border border-border/50 hover:bg-card/80 transition-colors text-xs"
                        >
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Rynek</span>
                            <span className="font-medium text-foreground">{trade.market}</span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Strona</span>
                            <span className={`font-medium ${trade.side === 'BUY' ? 'text-success' : 'text-destructive'}`}>
                              {trade.side}
                            </span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Rozmiar</span>
                            <span className="font-mono text-foreground">{parseFloat(trade.qty).toFixed(4)}</span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Cena</span>
                            <span className="font-mono text-foreground">${formatPrice(trade.price)}</span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Wartość</span>
                            <span className="font-mono text-foreground">${formatPrice(trade.value)}</span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Fee</span>
                            <span className="font-mono text-muted-foreground">${formatPrice(trade.fee)}</span>
                          </div>
                          
                          <div className="flex flex-col">
                            <span className="text-muted-foreground text-[10px]">Czas</span>
                            <span className="text-muted-foreground text-[10px]">{formatDate(trade.createdTime)}</span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-center py-3 text-muted-foreground text-sm">
                      Brak historii transakcji
                    </div>
                  )}
                </div>
              </ScrollArea>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  );
};
