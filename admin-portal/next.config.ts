import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Allow reading markdown vault outside admin-portal/
  experimental: {
    externalDir: true,
  },
  // Server can resolve monorepo vault via OHCC_VAULT
  env: {
    OHCC_VAULT: process.env.OHCC_VAULT || path.join(process.cwd(), "..", "vault"),
  },
};

export default nextConfig;
