import { writeFileSync } from "node:fs";

const configuredUrl = (process.env.RESEARCHOS_API_URL || "").trim().replace(/\/$/, "");
if (configuredUrl && !/^https:\/\/[^\s]+$/i.test(configuredUrl)) {
  throw new Error("RESEARCHOS_API_URL must be an https URL when configured.");
}

const source = [
  "/* Generated during deployment. This file must never contain a secret. */",
  `window.RESEARCHOS_API_URL = ${JSON.stringify(configuredUrl)};`,
  "",
].join("\n");
writeFileSync("frontend/runtime-config.js", source, "utf8");
