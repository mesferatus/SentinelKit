const test = require('node:test')
const assert = require('node:assert/strict')

const {
  buildBackendEnvironment,
  ensureDesktopSecrets,
  probeRuntimeHealth,
  startBackendWithRetry,
  selectBackendCommand,
} = require('./runtime.cjs')

test('desktop backend receives local-only eager configuration', () => {
  const secrets = {
    jwtSecret: 'a'.repeat(96),
    jwtRefreshSecret: 'b'.repeat(96),
  }
  const environment = buildBackendEnvironment({
    userDataPath: 'C:\\Users\\Demo\\SentinelKit',
    apiPort: 43123,
    frontendOrigin: 'http://127.0.0.1:43124',
    baseEnvironment: {},
    secrets,
    runtimeNonce: 'runtime-nonce',
  })

  assert.equal(environment.API_HOST, '127.0.0.1')
  assert.equal(environment.API_PORT, '43123')
  assert.equal(environment.CELERY_TASK_ALWAYS_EAGER, 'true')
  assert.equal(environment.FRONTEND_ORIGIN, 'http://127.0.0.1:43124')
  assert.match(environment.DATABASE_URL, /sentinelkit\.db$/)
  assert.equal(environment.JWT_SECRET, secrets.jwtSecret)
  assert.equal(environment.JWT_REFRESH_SECRET, secrets.jwtRefreshSecret)
  assert.equal(environment.DESKTOP_RUNTIME_NONCE, 'runtime-nonce')
})

test('desktop secrets are strong, distinct and stable across launches', () => {
  const fs = require('node:fs')
  const os = require('node:os')
  const path = require('node:path')
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'sentinelkit-secrets-'))

  const first = ensureDesktopSecrets(directory)
  const second = ensureDesktopSecrets(directory)

  assert.deepEqual(second, first)
  assert.notEqual(first.jwtSecret, first.jwtRefreshSecret)
  assert.ok(first.jwtSecret.length >= 64)
  assert.ok(first.jwtRefreshSecret.length >= 64)
  assert.doesNotThrow(() =>
    JSON.parse(fs.readFileSync(path.join(directory, 'desktop-secrets.json'), 'utf8')),
  )
})

test('runtime health rejects wrong processes and wrong nonces', async () => {
  const wrongMarker = await probeRuntimeHealth({
    apiUrl: 'http://127.0.0.1:43123',
    runtimeNonce: 'nonce',
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ marker: 'other-service', nonce_hash: 'x' }),
    }),
  })
  const wrongNonce = await probeRuntimeHealth({
    apiUrl: 'http://127.0.0.1:43123',
    runtimeNonce: 'nonce',
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({
        marker: 'sentinelkit-desktop',
        nonce_hash: 'not-the-right-hash',
      }),
    }),
  })

  assert.equal(wrongMarker, false)
  assert.equal(wrongNonce, false)
})

test('backend startup kills impersonator and retries another port', async () => {
  const killed = []
  const ports = [43123, 43124]
  const result = await startBackendWithRetry({
    maxAttempts: 2,
    getPort: async () => ports.shift(),
    spawnBackend: ({ apiPort }) => ({
      apiPort,
      killed: false,
      kill() {
        this.killed = true
        killed.push(apiPort)
      },
    }),
    probe: async ({ apiUrl }) => apiUrl.endsWith(':43124'),
  })

  assert.equal(result.apiPort, 43124)
  assert.deepEqual(killed, [43123])
})

test('packaged app selects bundled backend executable', () => {
  const command = selectBackendCommand({
    isPackaged: true,
    resourcesPath: 'C:\\SentinelKit\\resources',
    projectRoot: 'C:\\src\\SentinelKit',
  })

  assert.equal(
    command.executable,
    'C:\\SentinelKit\\resources\\backend\\sentinelkit-api.exe',
  )
  assert.deepEqual(command.args, [])
})

test('development selects the project virtualenv Python entrypoint', () => {
  const command = selectBackendCommand({
    isPackaged: false,
    resourcesPath: '',
    projectRoot: 'C:\\src\\SentinelKit',
  })

  assert.equal(
    command.executable,
    'C:\\src\\SentinelKit\\.venv\\Scripts\\python.exe',
  )
  assert.deepEqual(command.args, ['-m', 'app.desktop'])
})
