/**
 * Common types used throughout the application
 */

// Generic response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status?: number;
}

// Pagination types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Types for error handling
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, any>;
}

// Types for filters and sorting
export interface FilterParams {
  [key: string]: string | number | boolean | null;
}

export interface SortParams {
  field: string;
  direction: 'asc' | 'desc';
}

// Types for common callbacks
export type ProgressCallback = (progress: number) => void;
export type ErrorCallback = (error: ApiError) => void;
export type SuccessCallback<T> = (data: T) => void;
