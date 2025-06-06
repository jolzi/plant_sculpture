"""Platform-agnostic system notification wrapper."""
import sys
import platform
from loguru import logger

class SystemNotifier:
    def __init__(self):
        self.platform = platform.system().lower()
        self._setup_notifier()

    def _setup_notifier(self):
        """Set up the appropriate notifier based on platform."""
        if self.platform == 'linux':
            try:
                import systemd.daemon
                self._notify = systemd.daemon.notify
                logger.info("Using systemd notifications")
            except ImportError:
                logger.warning("systemd not available, using mock notifications")
                self._notify = self._mock_notify
        else:
            logger.info(f"Platform {self.platform} detected, using mock notifications")
            self._notify = self._mock_notify

    def _mock_notify(self, status):
        """Mock notification for non-Linux platforms."""
        logger.debug(f"Mock system notification: {status}")
        return True

    def notify(self, status):
        """Send notification to the system."""
        return self._notify(status)
