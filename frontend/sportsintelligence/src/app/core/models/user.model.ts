/**
 * User / auth DTOs — mirror of `backend/app/models/user.py`.
 */

export type UserRole = 'user' | 'admin';

// --- Inbound (request bodies) ---

export interface UserRegister {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface ResendVerificationRequest {
  email: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

// --- Outbound (responses) ---

export interface MessageResponse {
  message: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  /** Seconds until the access token expires. */
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name?: string | null;
  role: UserRole;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at?: string | null;
  last_login_at?: string | null;
}
