const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getWorldCache: (scenarioId) => ipcRenderer.invoke('world-cache:get', scenarioId),
  setWorldCache: (scenarioId, worldData) =>
    ipcRenderer.invoke('world-cache:set', { scenarioId, worldData }),
});
