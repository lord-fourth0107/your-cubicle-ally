/**
 * main/server-manager.ts
 * ----------------------
 * Spawns and manages the Python FastAPI backend as a child process.
 * Called from the Electron main process on app startup.
 *
 * Owner: Frontend / Electron team
 * Depends on: nothing (Node.js child_process)
 * Depended on by: main/index.ts
 */

import { ChildProcess, spawn } from "child_process";
import path from "path";

const BACKEND_PORT = 8000;
let serverProcess: ChildProcess | null = null;

export function startBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    // TODO: in production, point to the PyInstaller-bundled binary.
    // In dev, run `uvicorn api.main:app --port 8000` from the backend dir.
    const backendDir = path.join(__dirname, "../../../backend");

    serverProcess = spawn("uvicorn", ["api.main:app", "--port", String(BACKEND_PORT)], {
      cwd: backendDir,
      env: { ...process.env },
    });

    serverProcess.stdout?.on("data", (data) => {
      if (data.toString().includes("Application startup complete")) {
        resolve();
      }
    });

    serverProcess.stderr?.on("data", (data) => {
      console.error("[backend]", data.toString());
    });

    serverProcess.on("error", reject);
  });
}

export function stopBackend(): void {
  serverProcess?.kill();
  serverProcess = null;
}

export const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
