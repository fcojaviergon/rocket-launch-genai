'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Upload, Loader2 } from 'lucide-react';
import { useDocuments } from '@/lib/hooks/documents';
import { Document as ServiceDocument } from '@/lib/services/documents';
import { toast } from 'sonner';

interface UploadDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete: (document: ServiceDocument) => void;
}

export function UploadDialog({ isOpen, onClose, onUploadComplete }: UploadDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { uploadDocument, isLoading: isUploading } = useDocuments();
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    try {
      // Start upload process
      setUploadProgress(0);
      setError(null);
      
      console.log(`Uploading file: ${file.name}, size: ${file.size} bytes, type: ${file.type}`);
      
      // Upload the file using DocumentService
      const uploadedDoc = await uploadDocument(file, (progress) => {
        setUploadProgress(progress);
      });
      
      console.log("Document uploaded successfully:", uploadedDoc);
      
      // Notify parent component
      onUploadComplete(uploadedDoc as ServiceDocument);
      
      // Show success toast
      toast.success(`${file.name} uploaded successfully`);
      
      // Close dialog
      onClose();
      
      // Reset state
      setFile(null);
      setUploadProgress(0);
      
    } catch (error: any) {
      console.error("Error uploading document:", error);
      setError(error.message || "Error uploading document");
      
      // Show error details if available
      const detailedMessage = error.data ? JSON.stringify(error.data) : error.message;
      console.error("Detailed error message:", detailedMessage);
      
      toast.error(`Upload failed: ${error.message || "Unknown error"}`);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md bg-white dark:bg-gray-800">
        <DialogHeader>
          <DialogTitle>Upload document</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file">Select a file</Label>
            <Input
              id="file"
              type="file"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          {file && (
            <div className="text-sm">
              <p className="font-medium">{file.name}</p>
              <p className="text-muted-foreground">{(file.size / 1024).toFixed(2)} KB</p>
            </div>
          )}

          {isUploading && uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary transition-all duration-300 ease-in-out" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-center text-muted-foreground">
                {uploadProgress.toFixed(0)}% completed
              </p>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button 
            onClick={handleUpload} 
            disabled={!file || isUploading}
            className="flex items-center gap-2"
          >
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4" />
                Upload
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 