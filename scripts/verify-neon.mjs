/**
 * npm run build — verify Neon config + env wiring for this Python app.
 */
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { createJiti } from "jiti";
import { parseEnv } from "@neon/env";

const root = resolve(import.meta.dirname, "..");
const envPath = existsSync(resolve(root, ".env"))
  ? resolve(root, ".env")
  : resolve(root, ".env.local");

if (!existsSync(envPath)) {
  console.error(`Missing env file at ${envPath}. Run: neon deploy`);
  process.exit(1);
}

for (const line of readFileSync(envPath, "utf8").split(/\r?\n/)) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
  const eq = trimmed.indexOf("=");
  const key = trimmed.slice(0, eq).trim();
  let value = trimmed.slice(eq + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  if (process.env[key] === undefined) process.env[key] = value;
}

const jiti = createJiti(import.meta.url);
const config = jiti(resolve(root, "neon.ts"));
const { postgres } = parseEnv(config, ["DATABASE_URL", "DATABASE_URL_UNPOOLED"]);

if (!postgres.databaseUrl?.includes("neon.tech")) {
  console.error("DATABASE_URL does not look like a Neon host.");
  process.exit(1);
}
if (!postgres.databaseUrlUnpooled?.includes("neon.tech")) {
  console.error("DATABASE_URL_UNPOOLED does not look like a Neon host.");
  process.exit(1);
}

// Ensure package.json still declares Neon deps
const pkg = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));
const require = createRequire(import.meta.url);
require.resolve("@neon/config");
require.resolve("@neon/env");

console.log("Neon build check passed");
console.log("  neon.ts loaded");
console.log(`  env file: ${envPath}`);
console.log("  DATABASE_URL host ok (neon.tech)");
console.log("  DATABASE_URL_UNPOOLED host ok (neon.tech)");
console.log(`  deps: @neon/config@${pkg.dependencies["@neon/config"]}, @neon/env@${pkg.dependencies["@neon/env"]}`);
