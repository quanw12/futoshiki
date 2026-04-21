const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const API_PORT = 8000;
const API_HEALTH_URL = `http://127.0.0.1:${API_PORT}/api/health`;

let backendProcess = null;

function detectPythonCommand() {
  return process.platform === "win32" ? "python" : "python3";
}

function waitForApiReady(timeoutMs = 15000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get(API_HEALTH_URL, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          resolve();
        } else if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`API health check returned ${res.statusCode}`));
        } else {
          setTimeout(check, 350);
        }
      });
      req.on("error", () => {
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error("Timed out waiting for Python API server."));
        } else {
          setTimeout(check, 350);
        }
      });
    };
    check();
  });
}

function stopBackend() {
  if (!backendProcess) return;
  backendProcess.kill();
  backendProcess = null;
}

async function startBackend(repoRoot) {
  if (backendProcess) return;
  const pythonCmd = detectPythonCommand();
  backendProcess = spawn(
    pythonCmd,
    ["-m", "uvicorn", "source.api_server:app", "--host", "127.0.0.1", "--port", `${API_PORT}`],
    { cwd: repoRoot, stdio: "pipe" }
  );

  backendProcess.stdout.on("data", (d) => process.stdout.write(`[py] ${d}`));
  backendProcess.stderr.on("data", (d) => process.stderr.write(`[py] ${d}`));
  backendProcess.on("exit", (code) => {
    console.log(`Python backend exited with code ${code}`);
    backendProcess = null;
  });
}

async function createWindow() {
  const uiRoot = path.resolve(__dirname, "..");
  const repoRoot = path.resolve(uiRoot, "..", "..");
  const distIndex = path.resolve(uiRoot, "dist", "index.html");

  await startBackend(repoRoot);
  await waitForApiReady();

  const win = new BrowserWindow({
    width: 1360,
    height: 880,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: "#070d18",
    title: "Futoshiki Liquid App",
    webPreferences: {
      contextIsolation: true,
      sandbox: true
    }
  });

  await win.loadFile(distIndex);
}

app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopBackend();
});

app.whenReady().then(async () => {
  try {
    await createWindow();
  } catch (error) {
    console.error(error);
    dialog.showErrorBox(
      "Desktop startup failed",
      `Could not start desktop app.\n\n${error.message}\n\nMake sure Python and requirements are installed.`
    );
    app.quit();
  }
});
