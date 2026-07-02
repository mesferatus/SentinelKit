const { app, BrowserWindow, dialog, Menu } = require('electron')
const { spawn } = require('node:child_process')
const fs = require('node:fs')
const http = require('node:http')
const path = require('node:path')
const net = require('node:net')
const { randomBytes } = require('node:crypto')
const {
  buildBackendEnvironment,
  ensureDesktopSecrets,
  probeRuntimeHealth,
  selectBackendCommand,
  startBackendWithRetry,
} = require('./runtime.cjs')

let backendProcess
let frontendServer

const projectRoot = path.resolve(__dirname, '..', '..')
const frontendRoot = path.resolve(__dirname, '..', 'dist')

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => resolve(port))
    })
  })
}

function contentType(filePath) {
  const extension = path.extname(filePath)
  return {
    '.css': 'text/css; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
  }[extension] || 'application/octet-stream'
}

function startFrontendServer() {
  return new Promise((resolve, reject) => {
    frontendServer = http.createServer((request, response) => {
      const requestPath = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
      const relativePath = requestPath === '/' ? 'index.html' : requestPath.slice(1)
      let filePath = path.resolve(frontendRoot, relativePath)
      if (!filePath.startsWith(frontendRoot) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(frontendRoot, 'index.html')
      }
      response.setHeader(
        'Content-Security-Policy',
        "default-src 'self'; connect-src 'self' http://127.0.0.1:*; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'",
      )
      response.setHeader('Content-Type', contentType(filePath))
      fs.createReadStream(filePath).pipe(response)
    })
    frontendServer.on('error', reject)
    frontendServer.listen(0, '127.0.0.1', () => {
      resolve(`http://127.0.0.1:${frontendServer.address().port}`)
    })
  })
}

async function waitForHealth(apiUrl, runtimeNonce, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      if (await probeRuntimeHealth({ apiUrl, runtimeNonce })) return true
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  return false
}

async function createWindow() {
  const frontendOrigin = await startFrontendServer()
  const secrets = ensureDesktopSecrets(app.getPath('userData'))
  const command = selectBackendCommand({
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    projectRoot,
  })
  const backendLogPath = path.join(app.getPath('userData'), 'backend.log')
  fs.writeFileSync(backendLogPath, '', 'utf8')
  const started = await startBackendWithRetry({
    getPort: freePort,
    spawnBackend: async ({ apiPort }) => {
      const runtimeNonce = randomBytes(48).toString('hex')
      const environment = buildBackendEnvironment({
        userDataPath: app.getPath('userData'),
        apiPort,
        frontendOrigin,
        secrets,
        runtimeNonce,
      })
      const child = spawn(command.executable, command.args, {
        cwd: app.isPackaged ? path.dirname(command.executable) : path.join(projectRoot, 'api'),
        env: environment,
        windowsHide: true,
        stdio: app.isPackaged ? ['ignore', 'pipe', 'pipe'] : 'inherit',
      })
      if (app.isPackaged) {
        const log = fs.createWriteStream(backendLogPath, { flags: 'a' })
        child.stdout.pipe(log, { end: false })
        child.stderr.pipe(log, { end: false })
        child.once('close', () => log.end())
      }
      return { child, runtimeNonce, kill: () => child.kill() }
    },
    probe: ({ apiUrl, processHandle }) =>
      waitForHealth(apiUrl, processHandle.runtimeNonce),
  })
  backendProcess = started.child
  const apiUrl = started.apiUrl
  backendProcess.on('exit', (code) => {
    if (!app.isQuitting && code !== 0) {
      dialog.showErrorBox('SentinelKit', 'O serviço local foi encerrado inesperadamente.')
    }
  })

  process.env.SENTINELKIT_API_URL = apiUrl
  const window = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 900,
    minHeight: 620,
    show: true,
    backgroundColor: '#edf3ff',
    icon: path.join(__dirname, '..', 'build', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  window.maximize()
  window.show()
  await window.loadURL(frontendOrigin)
}

function shutdown() {
  app.isQuitting = true
  frontendServer?.close()
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
}

const hasLock = app.requestSingleInstanceLock()
if (!hasLock) app.quit()
else {
  Menu.setApplicationMenu(null)
  app.on('second-instance', () => {
    const window = BrowserWindow.getAllWindows()[0]
    if (window) {
      if (window.isMinimized()) window.restore()
      window.focus()
    }
  })
  app.whenReady().then(createWindow).catch((error) => {
    dialog.showErrorBox('SentinelKit', error.message)
    shutdown()
    app.quit()
  })
  app.on('before-quit', shutdown)
  app.on('window-all-closed', () => app.quit())
}
