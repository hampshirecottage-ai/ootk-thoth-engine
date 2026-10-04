"""Locks out a visitor who keeps getting APP_PASSWORD wrong, so it can't be guessed by brute force."""
import threading
import time

# Ten wrong passwords within 15 minutes lock that visitor out for 15 minutes.
LOCKOUT_ATTEMPTS = 10
LOCKOUT_WINDOW = 15 * 60
# Visitors tracked at once; past this the oldest are forgotten, so the table can't fill memory.
LOCKOUT_MAX_TRACKED = 10_000


class FailedLogins:
    """Wrong-password counts per visitor, kept in memory (one process; a restart clears them)."""

    def __init__(self, attempts=LOCKOUT_ATTEMPTS, window=LOCKOUT_WINDOW,
                 max_tracked=LOCKOUT_MAX_TRACKED, clock=time.monotonic):
        self.attempts, self.window, self.max_tracked, self.clock = attempts, window, max_tracked, clock
        self._failures = {}          # visitor -> times of wrong passwords within the window
        self._locked_until = {}      # visitor -> when the lockout ends
        self._lock = threading.Lock()

    def retry_after(self, visitor) -> int:
        """Seconds until `visitor` may try again; 0 when not locked out."""
        with self._lock:
            until = self._locked_until.get(visitor)
            if until is None:
                return 0
            left = until - self.clock()
            if left <= 0:
                del self._locked_until[visitor]
                return 0
            return max(1, int(left + 0.999))

    def failed(self, visitor) -> int:
        """Records a wrong password; returns the seconds of lockout it starts (0 if none yet)."""
        with self._lock:
            now = self.clock()
            recent = [t for t in self._failures.get(visitor, ()) if now - t < self.window]
            recent.append(now)
            if len(recent) >= self.attempts:
                self._failures.pop(visitor, None)
                self._locked_until[visitor] = now + self.window
                self._trim(self._locked_until)
                return self.window
            self._failures[visitor] = recent
            self._trim(self._failures)
            return 0

    def succeeded(self, visitor):
        with self._lock:
            self._failures.pop(visitor, None)

    def _trim(self, table):
        # Dicts keep insertion order, so the first keys are the longest-tracked visitors.
        while len(table) > self.max_tracked:
            del table[next(iter(table))]

    def clear(self):
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()
