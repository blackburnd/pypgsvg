const fs = require('fs');
const path = require('path');

module.exports = async () => {
  const pidFile = path.join(__dirname, 'httpd.pid');
  if (fs.existsSync(pidFile)) {
    const pid = Number(fs.readFileSync(pidFile, 'utf8'));
    try {
      process.kill(pid);
    } catch (e) {
      // Ignore if already killed
    }
    fs.unlinkSync(pidFile);
  }
};
