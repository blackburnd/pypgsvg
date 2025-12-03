const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Pick a port
const PORT = process.env.TEST_HTTP_PORT || 8123;
const DOC_ROOT = path.resolve(__dirname, '../../');
let serverProcess;

/**
 * Check if a command is available on the system
 */
function checkPrerequisite(command, installInstructions) {
  try {
    execSync(`command -v ${command}`, { stdio: 'ignore' });
    return true;
  } catch (error) {
    console.error(`\n❌ ERROR: Required prerequisite '${command}' is not installed.\n`);
    console.error('Installation instructions:');
    console.error(installInstructions);
    console.error('\nPlease install the missing prerequisite and try again.\n');
    return false;
  }
}

module.exports = async () => {
  // Check prerequisites before running tests
  console.log('Checking prerequisites...');

  const prerequisites = [
    {
      command: 'dot',
      name: 'Graphviz',
      instructions: `
  macOS:       brew install graphviz
  Ubuntu:      sudo apt-get install graphviz
  CentOS/RHEL: sudo yum install graphviz
  Windows:     Download from https://graphviz.org/download/
      `.trim()
    },
    {
      command: 'npm',
      name: 'Node.js/npm',
      instructions: `
  macOS:       brew install node
  Ubuntu:      sudo apt-get install nodejs npm
  CentOS/RHEL: sudo yum install nodejs npm
  Windows:     Download from https://nodejs.org/

  Note: npm is only required for running browser tests (development/testing).
        End users of pypgsvg do not need npm.
      `.trim()
    }
  ];

  for (const prereq of prerequisites) {
    if (!checkPrerequisite(prereq.command, prereq.instructions)) {
      throw new Error(`Missing prerequisite: ${prereq.name}`);
    }
  }

  console.log('✓ All prerequisites installed\n');


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
