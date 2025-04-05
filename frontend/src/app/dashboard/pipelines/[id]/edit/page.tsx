'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { DashboardHeader } from '@/components'
import { DashboardShell } from '@/components'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { toast } from '@/components/ui/use-toast'
import { ArrowLeft, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { PipelineStepsEditor } from '@/components/pipelines/pipeline-steps-editor'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const formSchema = z.object({
  name: z.string().min(2, {
    message: 'The name must be at least 2 characters',
  }),
  description: z.string().min(10, {
    message: 'The description must be at least 10 characters',
  }),
  type: z.string().optional(),
  steps: z.array(
    z.object({
      name: z.string().min(1, { message: 'The name is required' }),
      type: z.string().min(1, { message: 'The type is required' }),
      config: z.record(z.any()),
      description: z.string().optional(),
      id: z.string().optional(),
    })
  ).min(1, { message: 'You must add at least one step to the pipeline' }),
})

type FormValues = z.infer<typeof formSchema>

export default function EditPipelinePage() {
  const params = useParams()
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      description: '',
      type: '',
      steps: [],
    },
    mode: 'onChange',
  })

  useEffect(() => {
    const fetchPipeline = async () => {
      try {
        setIsLoading(true)
        console.log('Fetching pipeline with ID:', params.id)
        
        const response = await fetch(`/api/pipelines/configs/${params.id}`, {
          credentials: 'include' // Ensure cookies are sent with the request
        })
        
        console.log('Pipeline fetch response status:', response.status)
        
        if (!response.ok) {
          const errorText = await response.text()
          console.error('Pipeline fetch error response:', errorText)
          throw new Error(`Error loading the pipeline: ${response.statusText}`)
        }
        
        const data = await response.json()
        console.log('Pipeline data loaded successfully')
        
        form.reset({
          name: data.name,
          description: data.description || '',
          type: data.type || '',
          steps: data.steps || [],
        })
      } catch (err) {
        console.error('Error fetching pipeline:', err)
        setError('Could not load the pipeline to edit')
      } finally {
        setIsLoading(false)
      }
    }

    fetchPipeline()
  }, [params.id, form])

  // Function to ensure no undefined objects in nested data
  function cleanNestedObjects(obj: any): any {
    // Handle null/undefined
    if (obj === null || obj === undefined) {
      return {};
    }
    
    // Handle arrays
    if (Array.isArray(obj)) {
      return obj.map(item => cleanNestedObjects(item));
    }
    
    // Handle objects
    if (typeof obj === 'object') {
      const cleaned: Record<string, any> = {};
      
      for (const [key, value] of Object.entries(obj)) {
        if (value === undefined) {
          // Skip undefined values
          continue;
        } else if (value === null) {
          // Replace null with empty object or appropriate default
          cleaned[key] = typeof value === 'object' ? {} : '';
        } else if (typeof value === 'object') {
          // Recursively clean nested objects
          cleaned[key] = cleanNestedObjects(value);
        } else {
          // Keep primitive values as is
          cleaned[key] = value;
        }
      }
      
      return cleaned;
    }
    
    // Return primitives as is
    return obj;
  }

  async function onSubmit(data: FormValues) {
    console.log('Form submission started with data:', data);
    console.log('Form validation state:', form.formState.errors);
    
    try {
      setIsSubmitting(true);
      
      // Clean all nested data to remove any undefined values
      const fullyCleanedData = cleanNestedObjects(data);
      
      // Don't perform extra validation here - rely on zod schema
      // The form won't submit if validation fails
      
      // Create clean data structure for API
      const cleanedData = {
        name: fullyCleanedData.name,
        description: fullyCleanedData.description || '',
        type: fullyCleanedData.type || '',
        steps: fullyCleanedData.steps.map((step: any) => ({
          id: step.id || `step-${Math.random().toString(36).substring(2, 9)}`,
          name: step.name,
          type: step.type,
          config: step.config || {},
          description: step.description || null
        }))
      };
      
      console.log('Submitting pipeline data:', JSON.stringify(cleanedData));
      
      const response = await fetch(`/api/pipelines/configs/${params.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(cleanedData),
      });
      
      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorData = await response.text();
        console.error('API error response:', errorData);
        throw new Error(`Error updating pipeline: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      console.log('Update successful, result:', result);
      
      toast({
        title: 'Pipeline updated',
        description: 'The pipeline has been updated successfully',
      });
      
      // Redirect immediately
      router.push('/dashboard/pipelines');
    } catch (error) {
      console.error('Error updating pipeline:', error);
      toast({
        title: 'Update Failed',
        description: error instanceof Error ? error.message : 'Could not update the pipeline',
        variant: 'destructive',
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Edit Pipeline" text="Loading pipeline data...">
          <Link href="/dashboard/pipelines">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </DashboardHeader>
        <div className="flex justify-center items-center h-96">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </DashboardShell>
    )
  }

  if (error) {
    return (
      <DashboardShell>
        <DashboardHeader heading="Edit Pipeline" text="There was an error loading the data">
          <Link href="/dashboard/pipelines">
            <Button variant="outline">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
          </Link>
        </DashboardHeader>
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </DashboardShell>
    )
  }

  return (
    <DashboardShell>
      {/* Hide any "undefined" text that might appear */}
      <style jsx global>{`
        body:after { content: none !important; }
        undefined { display: none !important; }
      `}</style>
      
      <DashboardHeader heading="Edit Pipeline" text="Modify the pipeline configuration.">
        <Link href="/dashboard/pipelines">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </DashboardHeader>

      <div className="grid gap-8">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            {/* Show form-level errors */}
            {Object.keys(form.formState.errors).length > 0 && (
              <Alert variant="destructive" className="mb-4">
                <AlertTitle>Validation Errors</AlertTitle>
                <AlertDescription>
                  Please fix the highlighted errors before submitting
                </AlertDescription>
              </Alert>
            )}
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }: { field: any }) => (
                  <FormItem>
                    <FormLabel htmlFor="pipeline-name">Name</FormLabel>
                    <FormControl>
                      <Input 
                        id="pipeline-name" 
                        placeholder="Ej: Invoice processing" 
                        autoComplete="off"
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Descriptive name to identify the pipeline.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }: { field: any }) => (
                  <FormItem>
                    <FormLabel htmlFor="pipeline-description">Description</FormLabel>
                    <FormControl>
                      <Textarea
                        id="pipeline-description"
                        placeholder="Describe the purpose and operation of this pipeline..."
                        autoComplete="off"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      Detailed description of the pipeline and its purpose.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="type"
                render={({ field }: { field: any }) => (
                  <FormItem>
                    <FormLabel htmlFor="pipeline-type">Type (optional)</FormLabel>
                    <FormControl>
                      <Input 
                        id="pipeline-type" 
                        placeholder="Ej: document_processing" 
                        autoComplete="off"
                        {...field} 
                      />
                    </FormControl>
                    <FormDescription>
                      Category or type of pipeline.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="steps"
                render={({ field }: { field: any }) => (
                  <FormItem>
                    <FormLabel htmlFor="pipeline-steps">Pipeline steps</FormLabel>
                    <FormControl>
                      <div id="pipeline-steps">
                        <PipelineStepsEditor
                          value={field.value || []}
                          onChange={field.onChange}
                        />
                      </div>
                    </FormControl>
                    <FormDescription>
                      Add at least one step to your pipeline. Each step needs a name and type.
                    </FormDescription>
                    <FormMessage className="text-red-500 mt-2 font-semibold" />
                  </FormItem>
                )}
              />
            </div>

            <div>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save changes'
                )}
              </Button>
            </div>
          </form>
        </Form>
        {form.formState?.errors && <span style={{ display: 'none' }}>{JSON.stringify(form.formState.errors)}</span>}
      </div>
    </DashboardShell>
  )
} 