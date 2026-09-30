module.exports = {
  apps: [
    {
      name: 'apex-speed-3d',
      script: './server.js',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '120M',
      env: {
        NODE_ENV: 'production',
        PORT: 5050,
        HOST: '0.0.0.0'
      }
    }
  ]
};
