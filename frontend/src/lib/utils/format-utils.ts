/**
 * Formatting utilities
 */

import { format, formatDistance, formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

/**
 * Formats a date in Spanish format
 */
export function formatDate(date: Date | string, formatStr: string = 'dd/MM/yyyy HH:mm'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return format(dateObj, formatStr);
}

/**
 * Formats a date as relative time
 */
export function formatRelativeTime(date: Date | string): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(dateObj, { addSuffix: true, locale: es });
}

/**
 * Formats a number with thousand separators
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('es-ES').format(num);
}

/**
 * Formats a JSON object as a string with indentation
 */
export function formatJSON(obj: any): string {
  return JSON.stringify(obj, null, 2);
} 