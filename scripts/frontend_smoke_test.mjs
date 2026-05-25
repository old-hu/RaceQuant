import { spawn } from "node:child_process";

const routes = ["/", "/data/sources", "/data/jobs", "/odds", "/model", "/backtests"];
const port = process.env.FRONTEND_SMOKE_PORT || "4173";
const baseUrl = `http://127.0.0.1:${port}`;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForServer() {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // Keep waiting while Vite preview starts.
    }
    await wait(500);
  }
  throw new Error(`Timed out waiting for ${baseUrl}`);
}

async function checkRoute(route) {
  const response = await fetch(`${baseUrl}${route}`);
  if (!response.ok) {
    throw new Error(`${route} returned ${response.status}`);
  }
  const html = await response.text();
  if (!html.includes('<div id="root"></div>')) {
    throw new Error(`${route} did not return the app shell`);
  }
}

const child = spawn("npm", ["run", "preview", "--", "--host", "127.0.0.1", "--port", port], {
  cwd: new URL("../frontend", import.meta.url),
  shell: process.platform === "win32",
  stdio: ["ignore", "pipe", "pipe"],
});

let output = "";
child.stdout.on("data", (chunk) => {
  output += chunk.toString();
});
child.stderr.on("data", (chunk) => {
  output += chunk.toString();
});

try {
  await waitForServer();
  for (const route of routes) {
    await checkRoute(route);
  }
  console.log(`Frontend smoke passed for ${routes.length} routes at ${baseUrl}`);
} finally {
  if (process.platform === "win32" && child.pid) {
    spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
  } else {
    child.kill("SIGTERM");
  }
}
process.exit(0);
