'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useCompletions, CompletionResponse } from '@/lib/hooks';
import { useAuth } from '@/lib/hooks';


interface FormattedCompletionResult {
  text: string;
  model: string;
  processingTime: number;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  finish_reason?: string;
}

export default function CompletionsPage() {
  const { isAuthenticated } = useAuth();
  const { createCompletion, isLoading: isCompletionLoading, result: completionResult, error: completionError } = useCompletions();
  const [prompt, setPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(256);
  const [model, setModel] = useState('gpt-3.5-turbo');
  const [topP, setTopP] = useState(1.0);
  const [frequencyPenalty, setFrequencyPenalty] = useState(0.0);
  const [presencePenalty, setPresencePenalty] = useState(0.0);
  const [stop, setStop] = useState('');
  const [formattedResult, setFormattedResult] = useState<FormattedCompletionResult | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  
  const isLoading = isCompletionLoading;
  
  // Update the formatted result when the hook result changes
  useEffect(() => {
    if (completionResult) {
      const endTime = performance.now();
      const processingTime = startTime ? (endTime - startTime) / 1000 : 0;
      
      // Check if the result has the expected format or the alternative format
      if (completionResult.choices && completionResult.choices.length > 0) {
        // Original format with choices
        setFormattedResult({
          text: completionResult.choices[0].text,
          model: completionResult.model,
          processingTime,
          usage: completionResult.usage,
          finish_reason: completionResult.choices[0].finish_reason
        });
      } else if (completionResult.text) {
        // Alternative format with text directly in the root object
        setFormattedResult({
          text: completionResult.text,
          model: completionResult.model,
          processingTime,
          usage: completionResult.usage,
          finish_reason: completionResult.finish_reason
        });
      }
    }
  }, [completionResult, startTime]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormattedResult(null);
    setStartTime(performance.now());

    try {
      await createCompletion({
        prompt,
        temperature,
        max_tokens: maxTokens,
        model,
        top_p: topP,
        frequency_penalty: frequencyPenalty,
        presence_penalty: presencePenalty,
        stop: stop ? [stop] : undefined
      });
      // The result is automatically updated through the hook
    } catch (err) {
      // The error is automatically handled in the hook
      console.error('Error:', err);
    }
  };

  // If not authenticated, show message
  if (!isAuthenticated) {
    return (
      <div className="p-6 w-full">
        <div className="flex items-center justify-center h-[60vh]">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-2">Invalid session</h2>
            <p className="text-muted-foreground mb-4">You must login to access this page</p>
            <Button onClick={() => window.location.href = '/login'}>Login</Button>
          </div>
        </div>
      </div>
    );
  }



  return (
    <div className="p-6 w-full">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Text generation</h1>
        <p className="text-muted-foreground">Create content with AI using different parameters</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Configuration</CardTitle>
            <CardDescription>Adjust the parameters for text generation</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="prompt" className="block text-sm font-medium mb-1">
                  Prompt
                </label>
                <textarea
                  id="prompt"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Write your prompt here..."
                  required
                />
              </div>
              
              <div>
                <label htmlFor="temperature" className="block text-sm font-medium mb-1">
                  Temperature: {temperature}
                </label>
                <input
                  type="range"
                  id="temperature"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>More deterministic</span>
                  <span>More creative</span>
                </div>
              </div>
              
              <div>
                <label htmlFor="maxTokens" className="block text-sm font-medium mb-1">
                  Maximum length: {maxTokens} tokens
                </label>
                <input
                  type="range"
                  id="maxTokens"
                  min="50"
                  max="1000"
                  step="50"
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                  className="w-full"
                />
              </div>
              
              <div>
                <label htmlFor="model" className="block text-sm font-medium mb-1">
                  Model
                </label>
                <select
                  id="model"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                </select>
              </div>
              
              <div className="mt-4">
                <button 
                  type="button" 
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="text-sm text-primary hover:text-primary/80"
                >
                  {showAdvanced ? 'Hide advanced options' : 'Show advanced options'}
                </button>
              </div>
              
              {showAdvanced && (
                <div className="space-y-4 mt-4 p-4 border border-border rounded-md bg-muted/50">
                  <div>
                    <label htmlFor="topP" className="block text-sm font-medium mb-1">
                      Top P: {topP}
                    </label>
                    <input
                      type="range"
                      id="topP"
                      min="0"
                      max="1"
                      step="0.05"
                      value={topP}
                      onChange={(e) => setTopP(parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="frequencyPenalty" className="block text-sm font-medium mb-1">
                      Frequency penalty: {frequencyPenalty}
                    </label>
                    <input
                      type="range"
                      id="frequencyPenalty"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={frequencyPenalty}
                      onChange={(e) => setFrequencyPenalty(parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="presencePenalty" className="block text-sm font-medium mb-1">
                      Presence penalty: {presencePenalty}
                    </label>
                    <input
                      type="range"
                      id="presencePenalty"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={presencePenalty}
                      onChange={(e) => setPresencePenalty(parseFloat(e.target.value))}
                      className="w-full"
                    />
                  </div>
                  
                  <div>
                    <label htmlFor="stop" className="block text-sm font-medium mb-1">
                      Stop sequence
                    </label>
                    <input
                      type="text"
                      id="stop"
                      value={stop}
                      onChange={(e) => setStop(e.target.value)}
                      placeholder="Example: ###"
                      className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>
              )}
              
              <Button 
                type="submit" 
                disabled={isLoading || !prompt.trim()} 
                className="w-full"
              >
                {isLoading ? 'Generating...' : 'Generate text'}
              </Button>
            </form>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>Text generated by the AI</CardDescription>
          </CardHeader>
          <CardContent>
            {completionError && (
              <div className="p-3 mb-3 text-sm bg-destructive/10 text-destructive rounded-md">
                {completionError.message || 'Error generating text. Please try again.'}
              </div>
            )}
            
            {isLoading && (
              <div className="text-center py-8">
                <div className="animate-pulse">Generating text...</div>
              </div>
            )}
            
            {formattedResult && !isLoading && (
              <div className="space-y-4">
                <div className="bg-card p-3 rounded border border-border">
                  <pre className="whitespace-pre-wrap text-sm">{formattedResult.text}</pre>
                </div>
                
                <div className="text-xs text-muted-foreground">
                  <p>Model: {formattedResult.model}</p>
                  <p>Processing time: {formattedResult.processingTime.toFixed(2)}s</p>
                  {formattedResult.usage && (
                    <p>Tokens: {formattedResult.usage.total_tokens} (prompt: {formattedResult.usage.prompt_tokens}, completion: {formattedResult.usage.completion_tokens})</p>
                  )}
                  {formattedResult.finish_reason && (
                    <p>Finish reason: {formattedResult.finish_reason}</p>
                  )}
                </div>
              </div>
            )}
            
            {!formattedResult && !isLoading && !completionError && (
              <div className="text-center py-8 text-muted-foreground">
                Complete the form and click "Generate text" to see the results here.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
