const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Pick a port
const PORT = process.env.TEST_HTTP_PORT || 8123;
const DOC_ROOT = path.resolve(__dirname, '../../');
let serverProcess;

module.exports = async () => {
  // Try to use npx http-server if available, else fallback to Python
  let command, args;
  if (fs.existsSync(path.join(DOC_ROOT, 'node_modules/.bin/http-server'))) {
    command = 'npx';
    args = ['http-server', DOC_ROOT, '-p', PORT, '--silent'];
  } else {
    command = 'python3';
    args = ['-m', 'http.server', PORT, '--directory', DOC_ROOT];
  }
  serverProcess = spawn(command, args, { stdio: 'ignore', detached: true });
  // Wait a moment for server to start
  await new Promise(res => setTimeout(res, 1500));
  // Save PID for teardown
  fs.writeFileSync(path.join(__dirname, 'httpd.pid'), String(serverProcess.pid));
  process.env.TEST_HTTP_PORT = PORT;
};
