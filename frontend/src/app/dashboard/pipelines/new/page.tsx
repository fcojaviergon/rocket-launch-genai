'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
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
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { PipelineStepsEditor } from '@/components/pipelines/pipeline-steps-editor'

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
    })
  ).min(1, { message: 'You must add at least one step to the pipeline' }),
})

type FormValues = z.infer<typeof formSchema>

export default function NewPipelinePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: '',
      description: '',
      type: 'document_processing',
      steps: [],
    },
    mode: 'onChange',
  })

  async function onSubmit(data: FormValues) {
    try {
      setIsSubmitting(true)
      
      const response = await fetch('/api/pipelines/configs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        throw new Error('Error creating the pipeline')
      }

      const result = await response.json()
      
      toast.success('Pipeline created correctly')
      
      router.push('/dashboard/pipelines')
    } catch (error) {
      console.error('Error creating pipeline:', error)
      toast.error('Could not create the pipeline')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <DashboardShell>
      <DashboardHeader heading="Create Pipeline" text="Create a new pipeline to process documents.">
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
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Ej: Invoice processing" {...field} />
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
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Describe the purpose and operation of this pipeline..."
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
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Type (optional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Ej: document_processing" {...field} />
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
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Pipeline steps</FormLabel>
                    <FormControl>
                      <PipelineStepsEditor
                        value={field.value}
                        onChange={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Pipeline'}
            </Button>
          </form>
        </Form>
      </div>
    </DashboardShell>
  )
} 