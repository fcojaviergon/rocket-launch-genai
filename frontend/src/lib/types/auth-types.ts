/**
 * Types related to authentication and users
 */

// Basic user
export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  role?: string;
}

// Login credentials
export interface LoginCredentials {
  email: string;
  password: string;
}

// Register data
export interface RegisterData {
  email: string;
  password: string;
  name: string;
}

// Authentication response
export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// Refresh token response
export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}

// User update data
export interface UserUpdateData {
  name?: string;
  email?: string;
  password?: string;
  is_active?: boolean;
}

// Decoded token
export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
  role?: string;
}
