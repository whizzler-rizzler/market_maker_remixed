import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAccountRestAPI } from "@/hooks/useAccountRestAPI";
import { Activity } from "lucide-react";

export const RestAPIDebugPanel = () => {
  const { balance, positions, lastUpdate, error } = useAccountRestAPI();

  return (
    <Card className="bg-card border-destructive/50">
      <CardHeader>
        <CardTitle className="text-destructive flex items-center gap-2">
          <Activity className="w-5 h-5" />
          REST API DEBUG PANEL
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Connection Status */}
        <div className="space-y-2">
          <h3 className="font-semibold text-sm text-muted-foreground">Connection Status</h3>
          <div className="font-mono text-sm space-y-1">
            <div>
              <span className="text-muted-foreground">Status: </span>
              <span className={error ? "text-destructive" : "text-success"}>
                {error ? "ERROR" : "OK"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Last Update: </span>
              <span className="text-foreground">{lastUpdate.toLocaleTimeString('pl-PL')}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Endpoint: </span>
              <span className="text-foreground">https://extended-account-stream.onrender.com/api/account</span>
            </div>
            <div>
              <span className="text-muted-foreground">Polling Rate: </span>
              <span className="text-foreground">4x/sec (250ms)</span>
            </div>
            {error && (
              <div className="mt-2 p-2 bg-destructive/10 rounded border border-destructive/30">
                <span className="text-destructive font-semibold">Error: </span>
                <span className="text-destructive">{error}</span>
              </div>
            )}
          </div>
        </div>

        {/* Balance Data */}
        {balance && (
          <div className="space-y-2">
            <h3 className="font-semibold text-sm text-muted-foreground">Balance Data</h3>
            <div className="font-mono text-xs bg-muted/50 p-3 rounded-lg border border-border overflow-x-auto">
              <pre className="whitespace-pre-wrap break-words">
                {JSON.stringify(balance, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Positions Data */}
        {positions.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-semibold text-sm text-muted-foreground">
              Positions Data ({positions.length} positions)
            </h3>
            <div className="font-mono text-xs bg-muted/50 p-3 rounded-lg border border-border overflow-x-auto max-h-96 overflow-y-auto">
              <pre className="whitespace-pre-wrap break-words">
                {JSON.stringify(positions, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* No Data */}
        {!balance && positions.length === 0 && !error && (
          <div className="text-center text-muted-foreground py-8">
            Waiting for REST API data...
          </div>
        )}
      </CardContent>
    </Card>
  );
};
