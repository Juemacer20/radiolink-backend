module.exports = {
  apps: [{
    name: 'radiolink-backend',
    script: '/home/juan/radiolink-backend/venv/bin/uvicorn',
    args: 'main:app --host 0.0.0.0 --port 8000',
    cwd: '/home/juan/radiolink-backend',
    interpreter: 'none',
    restart_delay: 3000,
    max_restarts: 10,
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
}
