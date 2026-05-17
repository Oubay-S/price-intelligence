/**
 * Cross-cutting API shapes — error envelope + generic helpers.
 * Mirror of `backend/app/api_responses.py`.
 */

/** One field-level validation error inside the envelope's `details` list. */
export interface ErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ErrorBody {
  code: string;
  message: string;
  details?: ErrorDetail[] | null;
}

/** Every non-2xx backend response has this shape. */
export interface ErrorEnvelope {
  error: ErrorBody;
}

/** Normalised error the UI layer works with (see ApiService.handleError). */
export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: ErrorDetail[];
}
