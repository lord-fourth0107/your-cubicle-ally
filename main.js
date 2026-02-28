const { app, BrowserWindow, ipcMain } = require('electron');
const fs = require('fs/promises');
const path = require('path');

function getWorldCacheDir() {
  return path.join(app.getPath('userData'), 'world-cache');
}

function sanitizeScenarioId(scenarioId) {
  const raw = String(scenarioId || '').trim();
  const cleaned = raw.replace(/[^a-zA-Z0-9._-]/g, '_');
  return cleaned || 'unknown-scenario';
}

function getWorldCachePath(scenarioId) {
  return path.join(getWorldCacheDir(), `${sanitizeScenarioId(scenarioId)}.json`);
}

async function readWorldCache(scenarioId) {
  if (!scenarioId) return null;
  const filePath = getWorldCachePath(scenarioId);
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function writeWorldCache(scenarioId, worldData) {
  if (!scenarioId || !worldData) return false;
  const filePath = getWorldCachePath(scenarioId);
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, JSON.stringify(worldData), 'utf8');
  return true;
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: 'hiddenInset', // macOS style
    backgroundColor: '#FAFBFC',
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });
}

ipcMain.handle('world-cache:get', async (_event, scenarioId) => readWorldCache(scenarioId));
ipcMain.handle('world-cache:set', async (_event, payload) => {
  const scenarioId = payload?.scenarioId;
  const worldData = payload?.worldData;
  return writeWorldCache(scenarioId, worldData);
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
