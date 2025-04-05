/**
 * Validates if an email is valid
 * @param email Email to validate
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validates if a password meets the minimum requirements
 * @param password Password to validate
 * @param minLength Minimum length (default: 8)
 */
export function isValidPassword(password: string, minLength = 8): boolean {
  if (!password || password.length < minLength) return false;
  
  // Must contain at least one number
  const hasNumber = /\d/.test(password);
  
  // Must contain at least one uppercase letter
  const hasUpperCase = /[A-Z]/.test(password);
  
  // Must contain at least one lowercase letter
  const hasLowerCase = /[a-z]/.test(password);
  
  return hasNumber && hasUpperCase && hasLowerCase;
}

/**
 * Validates if a file is of an allowed type
 * @param file File to validate
 * @param allowedTypes Allowed types
 */
export function isValidFileType(file: File, allowedTypes: string[]): boolean {
  if (!file) return false;
  
  // Get the file extension
  const fileExt = file.name.split('.').pop()?.toLowerCase() || '';
  
  // Check if the extension is in the allowed types
  return allowedTypes.includes(fileExt);
}

/**
 * Validates if a file does not exceed the maximum size
 * @param file File to validate
 * @param maxSizeInMB Maximum size in MB
 */
export function isValidFileSize(file: File, maxSizeInMB: number): boolean {
  if (!file) return false;
  
  // Convert MB to bytes
  const maxSizeInBytes = maxSizeInMB * 1024 * 1024;
  
  return file.size <= maxSizeInBytes;
}

/**
 * Validates if a URL is valid
 * @param url URL to validate
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Validates if a value is a valid number
 * @param value Value to validate
 */
export function isValidNumber(value: any): boolean {
  if (value === null || value === undefined || value === '') return false;
  
  return !isNaN(Number(value));
}

/**
 * Validates if a value is in a specific range
 * @param value Value to validate
 * @param min Minimum value
 * @param max Maximum value
 */
export function isInRange(value: number, min: number, max: number): boolean {
  return value >= min && value <= max;
}
