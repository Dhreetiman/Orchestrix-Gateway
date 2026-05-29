"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api, ApiError } from "./api-client";
import type { LoginRequest, SignupRequest, User } from "./types";

export function useCurrentUser() {
  return useQuery<User | null>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await api.auth.me();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: (body: LoginRequest) => api.auth.login(body),
    onSuccess: (user) => {
      qc.setQueryData(["auth", "me"], user);
      router.push("/dashboard");
    },
  });
}

export function useSignup() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: (body: SignupRequest) => api.auth.signup(body),
    onSuccess: (resp) => {
      qc.setQueryData(["auth", "me"], resp.user);
      // signup response includes the freshly minted api key; stash it for the welcome screen
      sessionStorage.setItem("ogw_initial_key", resp.api_key);
      router.push("/dashboard?welcome=1");
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      qc.setQueryData(["auth", "me"], null);
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "auth" });
      router.push("/login");
    },
  });
}
