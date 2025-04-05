import { useState } from 'react';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileText, Trash, Play, MoreHorizontal, Eye } from "lucide-react";
import { Document } from "@/lib/types/document-types";
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { useDocuments } from '@/lib/hooks/documents';
import { toast } from 'sonner';
import { PipelineProcessDialog } from '../../pipelines/execution';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface DocumentCardProps {
  document: Document;
  onDeleted?: () => void;
  onProcessed?: () => void;
}

export function DocumentCard({ document, onDeleted, onProcessed }: DocumentCardProps) {
  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const { downloadDocument, deleteDocument } = useDocuments();
  const [isDeleting, setIsDeleting] = useState(false);
  const router = useRouter();
  
  const handleViewDetails = () => {
    router.push(`/dashboard/documents/${document.id}`);
  };
  /*
  const handleDownload = async () => {
    try {
      const blob = await downloadDocument(document.id);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = document.title;
      window.document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success('Document downloaded successfully');
    } catch (error) {
      console.error('Error downloading document:', error);
      toast.error('Error downloading document');
    }
  };
*/
  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${document.title}"?`)) {
      return;
    }
    
    try {
      setIsDeleting(true);
      await deleteDocument(document.id);
      toast.success('Document deleted successfully');
      if (onDeleted) onDeleted();
    } catch (error) {
      console.error('Error deleting document:', error);
      toast.error('Error deleting document');
    } finally {
      setIsDeleting(false);
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
  };

  // Determine the background color of the file type tag
  const getFileTypeColor = (fileType?: string) => {
    if (!fileType) return "bg-secondary";
    
    const type = fileType.toLowerCase();
    switch(type) {
      case 'pdf': return "bg-red-500/15 text-red-600 dark:bg-red-900/30 dark:text-red-400";
      case 'doc':
      case 'docx': return "bg-blue-500/15 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400";
      case 'xls':
      case 'xlsx': return "bg-green-500/15 text-green-600 dark:bg-green-900/30 dark:text-green-400";
      case 'ppt':
      case 'pptx': return "bg-orange-500/15 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400";
      case 'txt': return "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300";
      case 'csv': return "bg-yellow-500/15 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400";
      default: return "bg-secondary text-secondary-foreground";
    }
  };

  return (
    <>
      <Card className="h-full flex flex-col transition-all duration-300 hover-scale card-shadow">
        <CardHeader className="pb-2">
          <div className="flex justify-between items-start">
            <CardTitle 
              className="text-md font-medium truncate cursor-pointer hover:text-primary transition-colors duration-200"
              onClick={handleViewDetails}
            >
              {document.title}
            </CardTitle>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 animate-fade-in">
                <DropdownMenuItem onClick={handleViewDetails} className="cursor-pointer">
                  <Eye className="mr-2 h-4 w-4" /> View document
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setShowDetailsDialog(true)} className="cursor-pointer">
                  <FileText className="mr-2 h-4 w-4" /> Information
                </DropdownMenuItem>
              {/*  <DropdownMenuItem onClick={handleDownload} className="cursor-pointer">
                  <Download className="mr-2 h-4 w-4" /> Download
                </DropdownMenuItem>*/}
                <DropdownMenuItem onClick={() => setShowProcessDialog(true)} className="cursor-pointer">
                  <Play className="mr-2 h-4 w-4" /> Process
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="text-destructive focus:text-destructive cursor-pointer"
                >
                  <Trash className="mr-2 h-4 w-4" /> Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <p className="text-xs text-muted-foreground">
            {formatDistanceToNow(new Date(document.created_at), { addSuffix: true, locale: es })}
          </p>
        </CardHeader>
        <CardContent className="flex-grow">
          <div className="text-xs flex gap-2 mb-2">
            <div className={cn(
              "px-2 py-1 rounded text-xs font-medium",
              getFileTypeColor(document.file_type)
            )}>
              {document.file_type?.toUpperCase() || 'DOC'}
            </div>
            {document.file_size && (
              <div className="bg-secondary/50 text-secondary-foreground px-2 py-1 rounded text-xs">
                {formatFileSize(document.file_size)}
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="pt-2 flex justify-between">
          <div className="flex gap-1">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleViewDetails}
              className="hover:bg-primary/10 hover:text-primary"
            >
              <Eye className="h-4 w-4" />
            </Button>
            {/*
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDownload}
              className="hover:bg-primary/10 hover:text-primary"
            >
              <Download className="h-4 w-4" />
            </Button>
            */}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => setShowProcessDialog(true)}
              className="hover:bg-primary/10 hover:text-primary"
            >
              <Play className="h-4 w-4" />
            </Button>
          </div>
          <Button 
            variant="destructive" 
            size="sm" 
            onClick={handleDelete}
            disabled={isDeleting}
            className="hover:bg-destructive/90"
          >
            <Trash className="h-4 w-4" />
          </Button>
        </CardFooter>
      </Card>

      {/* Dialog of details */}
      <Dialog 
        open={showDetailsDialog} 
        onOpenChange={setShowDetailsDialog}
      >
        <DialogContent className="sm:max-w-[425px] animate-fade-in">
          <DialogHeader>
            <DialogTitle>Document details</DialogTitle>
            <DialogDescription>
              Detailed information about the document
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 mt-4 divide-y divide-border/50">
            <div className="flex justify-between pb-2">
              <span className="text-sm font-medium">Name:</span>
              <span className="text-sm max-w-[220px] truncate text-right">{document.title}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-sm font-medium">Type:</span>
              <span className={cn(
                "text-sm px-2 py-0.5 rounded",
                getFileTypeColor(document.file_type)
              )}>
                {document.file_type?.toUpperCase() || 'Unknown'}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-sm font-medium">Size:</span>
              <span className="text-sm bg-secondary/50 px-2 py-0.5 rounded">
                {formatFileSize(document.file_size)}
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-sm font-medium">Created:</span>
              <span className="text-sm">{new Date(document.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="text-sm font-medium">ID:</span>
              <span className="text-sm opacity-75 font-mono text-xs">{document.id}</span>
            </div>
          </div>
          <DialogFooter className="flex justify-between gap-2 pt-4 flex-row-reverse sm:flex-row-reverse">
            <Button 
              onClick={handleViewDetails}
              className="gradient-bg hover:opacity-90"
            >
              <Eye className="mr-2 h-4 w-4" /> View document
            </Button>
            <Button variant="outline" onClick={() => setShowDetailsDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog of processing */}
      <PipelineProcessDialog
        isOpen={showProcessDialog}
        onClose={() => setShowProcessDialog(false)}
        documentId={document.id}
        documentName={document.title}
        onProcessed={() => {
          if (onProcessed) onProcessed();
        }}
      />
    </>
  );
} 