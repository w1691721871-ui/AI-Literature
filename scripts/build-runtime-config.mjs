import { writeFileSync } from "node:fs";

const configuredUrl = (process.env.RESEARCHOS_API_URL || "").trim().replace(/\/$/, "");
const isPrivateDevelopmentHost = (hostname) => (
  hostname === "localhost"
  || hostname === "127.0.0.1"
  || /^10\./.test(hostname)
  || /^192\.168\./.test(hostname)
  || /^172\.(1[6-9]|2\d|3[01])\./.test(hostname)
);
if (configuredUrl) {
  const parsedUrl = new URL(configuredUrl);
  const allowsHttpForPrivateDevelopment = parsedUrl.protocol === "http:" && isPrivateDevelopmentHost(parsedUrl.hostname);
  if (parsedUrl.protocol !== "https:" && !allowsHttpForPrivateDevelopment) {
    throw new Error("RESEARCHOS_API_URL must use HTTPS, except for localhost or a private-network development host.");
  }
}

const source = [
  "/* Generated during deployment. This file must never contain a secret. */",
  `window.RESEARCHOS_API_URL = ${JSON.stringify(configuredUrl)};`,
  "",
].join("\n");
writeFileSync("frontend/runtime-config.js", source, "utf8");
