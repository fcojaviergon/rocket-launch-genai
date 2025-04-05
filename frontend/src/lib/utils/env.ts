/**
 * Validates that all required environment variables are present
 * @throws {Error} If any required environment variable is missing
 */
export function validateEnv(): void {
  const requiredEnvs = [
    'NEXT_PUBLIC_BACKEND_URL',
    'NEXTAUTH_URL',
    'NEXTAUTH_SECRET'
  ];
  
  const missingEnvs = requiredEnvs.filter(env => !process.env[env]);
  
  if (missingEnvs.length > 0) {
    throw new Error(`Missing required environment variables: ${missingEnvs.join(', ')}`);
  }
}

/**
 * Gets an environment variable with validation
 * @param key The environment variable key
 * @param defaultValue Optional default value if not found
 * @param required Whether the environment variable is required
 */
export function getEnv(
  key: string, 
  defaultValue?: string, 
  required = false
): string {
  const value = process.env[key] || defaultValue;
  
  if (required && !value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  
  return value || '';
}

/**
 * Gets a public environment variable (NEXT_PUBLIC_*)
 * @param key The environment variable key without the NEXT_PUBLIC_ prefix
 * @param defaultValue Optional default value if not found
 */
export function getPublicEnv(
  key: string,
  defaultValue?: string
): string {
  const fullKey = `NEXT_PUBLIC_${key}`;
  return getEnv(fullKey, defaultValue);
}

/**
 * Gets the backend URL from environment variables
 */
export function getBackendUrl(): string {
  return getEnv('NEXT_PUBLIC_BACKEND_URL', 'http://localhost:8000', true);
} 