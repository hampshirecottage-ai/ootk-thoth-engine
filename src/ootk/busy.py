"""Busy-server alert: a push to the owner's phone when the server's CPU stays high.

Render's free plan sends no CPU alerts, so the web app watches itself. Every SAMPLE_SECONDS it
reads how much CPU the container has used, as a share of the CPU it is allowed (the free plan
allows a tenth of one), and when the average over BUSY_ALERT_MINUTES reaches BUSY_ALERT_PERCENT
it posts one message to an ntfy topic (https://ntfy.sh, a free push app with no account). A
second message follows once the average drops back below the threshold. Busy alerts are at least
BUSY_ALERT_COOLDOWN_MINUTES apart. The message carries the CPU figure only, never anything from
a reading.

It is off unless BUSY_ALERT_NTFY_TOPIC is set. Anyone who knows an ntfy topic's name can read
it, so the name should be long and random, and kept with the other secrets.
"""
import asyncio
import logging
import os
import time
import urllib.request
from collections import deque
from pathlib import Path

from ootk.db import env_int

log = logging.getLogger("ootk.busy")

SAMPLE_SECONDS = 30
SEND_TIMEOUT = 10
CGROUP = Path("/sys/fs/cgroup")


def _read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def cpu_allowance(root=CGROUP):
    """How many CPUs the container may use: the cgroup quota (cgroup v2 cpu.max, or v1
    cfs_quota_us / cfs_period_us), else the CPUs this process may run on."""
    v2 = _read(root / "cpu.max")
    if v2:
        quota, _, period = v2.partition(" ")
        if quota != "max" and period:
            return int(quota) / int(period)
    for folder in ("cpu", "cpu,cpuacct"):
        quota, period = _read(root / folder / "cpu.cfs_quota_us"), _read(root / folder / "cpu.cfs_period_us")
        if quota and period and int(quota) > 0:
            return int(quota) / int(period)
    try:
        return float(len(os.sched_getaffinity(0)))
    except AttributeError:
        return float(os.cpu_count() or 1)


def cpu_seconds(root=CGROUP):
    """CPU seconds the container has used so far (cgroup v2 cpu.stat or v1 cpuacct.usage), or
    this process's own CPU time when neither is readable."""
    stat = _read(root / "cpu.stat")
    if stat:
        for line in stat.splitlines():
            key, _, value = line.partition(" ")
            if key == "usage_usec":
                return int(value) / 1e6
    for folder in ("cpuacct", "cpu,cpuacct"):
        usage = _read(root / folder / "cpuacct.usage")
        if usage:
            return int(usage) / 1e9
    return time.process_time()


class BusyWatch:
    """Turns CPU readings into 'busy' and 'calm' events. `feed` takes the time and the CPU
    seconds used so far and returns the event to send, if any, with the window's average."""

    def __init__(self, cores, percent=70, minutes=5, cooldown_minutes=60):
        self.cores = cores
        self.percent = percent
        self.window = minutes * 60
        self.cooldown = cooldown_minutes * 60
        self.samples = deque()
        self.busy = False
        self.alerted = False  # whether this busy spell's alert was sent (not held by the cooldown)
        self.last_alert = None

    def average(self):
        """Average CPU use over the samples kept, as a percentage of the allowance."""
        (t0, used0), (t1, used1) = self.samples[0], self.samples[-1]
        return 100 * (used1 - used0) / ((t1 - t0) * self.cores)

    def feed(self, now, used):
        self.samples.append((now, used))
        # Keep just enough samples to span the window: the oldest kept is the last one at or
        # before its start.
        while len(self.samples) > 2 and self.samples[1][0] <= now - self.window:
            self.samples.popleft()
        if now - self.samples[0][0] < self.window:
            return None, None
        average = self.average()
        if average >= self.percent:
            self.busy = True
            # One alert per busy spell; a spell that starts inside the cooldown alerts once the
            # cooldown has passed, if it is still going.
            if not self.alerted and (self.last_alert is None or now - self.last_alert >= self.cooldown):
                self.alerted = True
                self.last_alert = now
                return "busy", average
        elif self.busy:
            self.busy = False
            # A calm message only follows a busy one that was sent.
            if self.alerted:
                self.alerted = False
                return "calm", average
        return None, average


def send_ntfy(server, topic, title, message, tags):
    request = urllib.request.Request(
        f"{server.rstrip('/')}/{topic}", data=message.encode(), method="POST",
        headers={"Title": title, "Tags": tags})
    with urllib.request.urlopen(request, timeout=SEND_TIMEOUT):
        pass


def alert_text(event, average, percent, minutes):
    if event == "busy":
        return ("Server busy", f"CPU has averaged {average:.0f}% (alert at {percent}%) "
                f"for the last {minutes} minutes.", "warning")
    return "Server back to normal", f"CPU is down to {average:.0f}% over the last {minutes} minutes.", "white_check_mark"


async def watch(topic, server, percent, minutes, cooldown_minutes):
    cores = cpu_allowance()
    watcher = BusyWatch(cores, percent, minutes, cooldown_minutes)
    log.warning("Busy alert on: %s%% of %.2g CPU for %s minutes", percent, cores, minutes)
    while True:
        event, average = watcher.feed(time.monotonic(), cpu_seconds())
        if event:
            title, message, tags = alert_text(event, average, percent, minutes)
            log.warning("%s: %s", title, message)
            try:
                await asyncio.to_thread(send_ntfy, server, topic, title, message, tags)
            except Exception as error:  # an alert that can't be sent must not stop the watch
                log.warning("Busy alert not sent: %s", error)
        await asyncio.sleep(SAMPLE_SECONDS)


def start():
    """Start the watch as a background task if BUSY_ALERT_NTFY_TOPIC is set; returns the task."""
    topic = (os.getenv("BUSY_ALERT_NTFY_TOPIC") or "").strip()
    if not topic:
        return None
    server = (os.getenv("BUSY_ALERT_NTFY_SERVER") or "").strip() or "https://ntfy.sh"
    percent = env_int("BUSY_ALERT_PERCENT", 70, maximum=100)
    minutes = env_int("BUSY_ALERT_MINUTES", 5)
    cooldown = env_int("BUSY_ALERT_COOLDOWN_MINUTES", 60)
    return asyncio.get_running_loop().create_task(watch(topic, server, percent, minutes, cooldown))
