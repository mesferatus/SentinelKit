const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('sentinelConfig', Object.freeze({
  apiUrl: process.env.SENTINELKIT_API_URL,
  desktop: true,
}))
