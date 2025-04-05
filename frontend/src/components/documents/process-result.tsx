import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ProcessResultProps {
  result: any;
}

export function ProcessResult({ result }: ProcessResultProps) {
  if (!result) return null;

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Processing results</CardTitle>
        <CardDescription>
          Document: {result.title}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {result.summary && (
            <div>
              <h3 className="font-medium text-sm mb-1">Summary</h3>
              <p className="text-sm bg-muted p-3 rounded">{result.summary}</p>
            </div>
          )}
          
          {result.keywords && result.keywords.length > 0 && (
            <div>
              <h3 className="font-medium text-sm mb-2">Keywords</h3>
              <div className="flex flex-wrap gap-1">
                {result.keywords.map((keyword: string, index: number) => (
                  <Badge key={index} variant="secondary">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          
          {result.tokens && (
            <div>
              <h3 className="font-medium text-sm mb-1">Statistics</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-muted p-2 rounded">
                  <span className="font-medium">Total tokens:</span> {result.tokens.length}
                </div>
                <div className="bg-muted p-2 rounded">
                  <span className="font-medium">Unique tokens:</span> {new Set(result.tokens).size}
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 