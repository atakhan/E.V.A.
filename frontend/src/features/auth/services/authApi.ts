import { apiRequest } from "@/shared/api/http";

export type AuthUser = {
  id: string;
  email: string;
};

export type AuthCredentials = {
  email: string;
  password: string;
};

export function fetchMe(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me");
}

export function login(credentials: AuthCredentials): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function register(credentials: AuthCredentials): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}
