const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Add any IPC methods here when you need backend communication
});
