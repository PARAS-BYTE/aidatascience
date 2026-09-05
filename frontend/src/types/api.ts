export interface HealthResponse {
  status: string;
  service: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: string;
  };
}
