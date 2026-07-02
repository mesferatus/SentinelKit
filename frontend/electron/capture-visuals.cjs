const { app, BrowserWindow } = require('electron')
const fs = require('node:fs')
const http = require('node:http')
const path = require('node:path')

const dist = path.resolve(__dirname, '..', 'dist')
const output = path.resolve(__dirname, '..', '..', 'artifacts', 'screenshots')

function respondJson(response, payload, status = 200) {
  response.writeHead(status, {
    'Access-Control-Allow-Credentials': 'true',
    'Access-Control-Allow-Headers': 'authorization,content-type',
    'Access-Control-Allow-Origin': '*',
    'Content-Type': 'application/json',
  })
  response.end(JSON.stringify(payload))
}

function createServer() {
  return http.createServer((request, response) => {
    const url = new URL(request.url, 'http://127.0.0.1')
    if (url.pathname === '/auth/refresh') {
      return global.authenticated
        ? respondJson(response, { message: 'Sessao visual ativa', user: { name: 'Sofia', email: 'sofia@example.com' } })
        : respondJson(response, { detail: 'Sessão ausente' }, 401)
    }
    const acceptsJson = request.headers.accept?.includes('application/json')
    if (url.pathname === '/targets') return respondJson(response, [])
    if (url.pathname === '/siem/dashboard') return respondJson(response, { analyses: [], recent_activity: [] })
    if (url.pathname === '/audit-logs' && acceptsJson) return respondJson(response, { total: 0, page: 1, page_size: 20, items: [] })
    if (url.pathname === '/dashboard') return respondJson(response, {
      scans: 24,
      web_score: 82,
      alerts: 3,
      recent_activity: [
        { type: 'scan', title: 'Recon concluído', status: 'completed', timestamp: '2026-06-22T13:21:00Z' },
        { type: 'audit', title: 'Web Audit concluído', status: 'success', timestamp: '2026-06-22T12:47:00Z' },
        { type: 'siem', title: 'Alerta de SQL Injection', status: 'alert', timestamp: '2026-06-22T12:12:00Z' },
      ],
    })
    const relative = url.pathname === '/' ? 'index.html' : url.pathname.slice(1)
    let file = path.resolve(dist, relative)
    if (!file.startsWith(dist) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(dist, 'index.html')
    const types = { '.css': 'text/css', '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png' }
    response.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' })
    fs.createReadStream(file).pipe(response)
  })
}

async function capture(window, route, fileName) {
  await window.loadURL(`${global.origin}${route}`)
  await new Promise((resolve) => setTimeout(resolve, 1200))
  const image = await window.webContents.capturePage()
  fs.writeFileSync(path.join(output, fileName), image.toPNG())
}

app.whenReady().then(async () => {
  fs.mkdirSync(output, { recursive: true })
  const server = createServer()
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  global.origin = `http://127.0.0.1:${server.address().port}`
  process.env.SENTINELKIT_API_URL = global.origin
  const window = new BrowserWindow({ width: 1920, height: 1080, show: false, webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true } })
  global.authenticated = false
  await capture(window, '/login', 'sentinelkit-login-1920x1080.png')
  global.authenticated = true
  await capture(window, '/', 'sentinelkit-dashboard-1920x1080.png')
  await capture(window, '/profile', 'sentinelkit-profile-1920x1080.png')
  await capture(window, '/recon', 'sentinelkit-recon-empty-1920x1080.png')
  await capture(window, '/webaudit', 'sentinelkit-webaudit-empty-1920x1080.png')
  await capture(window, '/siem', 'sentinelkit-siem-empty-1920x1080.png')
  await capture(window, '/audit-logs', 'sentinelkit-audit-logs-empty-1920x1080.png')
  window.destroy()
  server.close()
  app.quit()
})
