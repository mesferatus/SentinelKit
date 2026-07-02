const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')

function ensureDesktopSecrets(userDataPath) {
  fs.mkdirSync(userDataPath, { recursive: true })
  const target = path.join(userDataPath, 'desktop-secrets.json')
  if (fs.existsSync(target)) return JSON.parse(fs.readFileSync(target, 'utf8'))
  const value = {
    jwtSecret: crypto.randomBytes(48).toString('hex'),
    jwtRefreshSecret: crypto.randomBytes(48).toString('hex'),
  }
  const temporary = `${target}.${process.pid}.${crypto.randomBytes(6).toString('hex')}.tmp`
  fs.writeFileSync(temporary, JSON.stringify(value), { encoding: 'utf8', mode: 0o600 })
  try {
    fs.renameSync(temporary, target)
  } catch (error) {
    fs.rmSync(temporary, { force: true })
    if (!fs.existsSync(target)) throw error
  }
  try { fs.chmodSync(target, 0o600) } catch {}
  return JSON.parse(fs.readFileSync(target, 'utf8'))
}

function buildBackendEnvironment({
  userDataPath,
  apiPort,
  frontendOrigin,
  secrets,
  runtimeNonce,
  baseEnvironment = process.env,
}) {
  const databasePath = path.join(userDataPath, 'sentinelkit.db').replaceAll('\\', '/')
  return {
    ...baseEnvironment,
    DATABASE_URL: `sqlite+pysqlite:///${databasePath}`,
    CELERY_TASK_ALWAYS_EAGER: 'true',
    API_HOST: '127.0.0.1',
    API_PORT: String(apiPort),
    FRONTEND_ORIGIN: frontendOrigin,
    COOKIE_SECURE: 'false',
    COOKIE_SAMESITE: 'strict',
    JWT_SECRET: secrets.jwtSecret,
    JWT_REFRESH_SECRET: secrets.jwtRefreshSecret,
    DESKTOP_RUNTIME_NONCE: runtimeNonce,
    ALLOWED_SCAN_TARGETS:
      baseEnvironment.ALLOWED_SCAN_TARGETS ||
      JSON.stringify(['localhost', '127.0.0.1', '::1']),
  }
}

async function probeRuntimeHealth({ apiUrl, runtimeNonce, fetchImpl = fetch }) {
  try {
    const response = await fetchImpl(`${apiUrl}/health/runtime`, {
      headers: { 'X-Sentinel-Runtime': runtimeNonce },
    })
    if (!response.ok) return false
    const body = await response.json()
    const expected = crypto.createHash('sha256').update(runtimeNonce).digest('hex')
    return body.marker === 'sentinelkit-desktop' && body.nonce_hash === expected
  } catch {
    return false
  }
}

async function startBackendWithRetry({
  maxAttempts = 4,
  getPort,
  spawnBackend,
  probe,
}) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const apiPort = await getPort()
    const handle = await spawnBackend({ apiPort })
    const apiUrl = `http://127.0.0.1:${apiPort}`
    if (await probe({ apiUrl, processHandle: handle })) {
      return { ...handle, apiPort, apiUrl }
    }
    handle.kill()
  }
  throw new Error('Não foi possível iniciar o serviço local com identidade válida.')
}

function selectBackendCommand({ isPackaged, resourcesPath, projectRoot }) {
  if (isPackaged) {
    return {
      executable: path.win32.join(resourcesPath, 'backend', 'sentinelkit-api.exe'),
      args: [],
    }
  }
  return {
    executable: path.win32.join(projectRoot, '.venv', 'Scripts', 'python.exe'),
    args: ['-m', 'app.desktop'],
  }
}

module.exports = {
  buildBackendEnvironment,
  ensureDesktopSecrets,
  probeRuntimeHealth,
  selectBackendCommand,
  startBackendWithRetry,
}
