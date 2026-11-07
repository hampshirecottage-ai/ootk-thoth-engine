"""ootk.busy: reading the container's CPU and turning a sustained high average into one alert."""
import asyncio
import http.server
import threading

import pytest

from ootk import busy


def test_cpu_allowance_from_cgroup_v2(tmp_path):
    (tmp_path / "cpu.max").write_text("10000 100000\n")
    assert busy.cpu_allowance(tmp_path) == pytest.approx(0.1)


def test_cpu_allowance_from_cgroup_v1(tmp_path):
    (tmp_path / "cpu").mkdir()
    (tmp_path / "cpu" / "cpu.cfs_quota_us").write_text("50000")
    (tmp_path / "cpu" / "cpu.cfs_period_us").write_text("100000")
    assert busy.cpu_allowance(tmp_path) == pytest.approx(0.5)


def test_cpu_allowance_without_a_quota_counts_cpus(tmp_path):
    (tmp_path / "cpu.max").write_text("max 100000")
    assert busy.cpu_allowance(tmp_path) >= 1


def test_cpu_seconds(tmp_path):
    (tmp_path / "cpu.stat").write_text("usage_usec 2500000\nuser_usec 2000000\n")
    assert busy.cpu_seconds(tmp_path) == pytest.approx(2.5)
    v1 = tmp_path / "v1"
    (v1 / "cpuacct").mkdir(parents=True)
    (v1 / "cpuacct" / "cpuacct.usage").write_text("3000000000")
    assert busy.cpu_seconds(v1) == pytest.approx(3.0)
    assert busy.cpu_seconds(tmp_path / "missing") >= 0   # falls back to this process's CPU time


def run(watch, percents, start=0.0, used=0.0, step=30):
    """Feed one 30-second sample per percentage (of 0.1 CPU); returns the events sent."""
    events = []
    now = start
    watch.feed(now, used)
    for percent in percents:
        now += step
        used += step * watch.cores * percent / 100
        event, average = watch.feed(now, used)
        if event:
            events.append((event, round(average)))
    return events, now, used


def test_sustained_load_sends_one_busy_then_one_calm():
    watch = busy.BusyWatch(cores=0.1, percent=70, minutes=5)
    events, _, _ = run(watch, [80] * 20 + [20] * 10)
    assert events == [("busy", 80), ("calm", 68)]


def test_short_spike_sends_nothing():
    watch = busy.BusyWatch(cores=0.1, percent=70, minutes=5)
    events, _, _ = run(watch, [10] * 10 + [100] * 3 + [10] * 10)
    assert events == []


def test_no_alert_before_a_whole_window():
    watch = busy.BusyWatch(cores=0.1, percent=70, minutes=5)
    events, _, _ = run(watch, [100] * 9)
    assert events == []
    events, _, _ = run(watch, [100], 270.0, 27.0)
    assert events == [("busy", 100)]


def test_cooldown_holds_a_second_busy_spell_and_its_calm():
    watch = busy.BusyWatch(cores=0.1, percent=70, minutes=5, cooldown_minutes=60)
    events, now, used = run(watch, [90] * 12 + [5] * 12)
    assert [e for e, _ in events] == ["busy", "calm"]
    # 20 minutes later, still inside the hour: no messages at all.
    events, now, used = run(watch, [90] * 12 + [5] * 12, now, used)
    assert events == []
    # After the hour has passed, the next spell alerts again.
    events, _, _ = run(watch, [5] * 80 + [90] * 12, now, used)
    assert [e for e, _ in events] == ["busy"]


def test_a_spell_that_outlasts_the_cooldown_alerts_once_it_has_passed():
    watch = busy.BusyWatch(cores=0.1, percent=70, minutes=5, cooldown_minutes=60)
    events, now, used = run(watch, [90] * 12 + [5] * 12)
    assert [e for e, _ in events] == ["busy", "calm"]
    events, _, _ = run(watch, [90] * 150, now, used)   # 75 busy minutes, starting 12 minutes on
    assert [e for e, _ in events] == ["busy"]


def test_start_is_off_without_a_topic(monkeypatch):
    monkeypatch.delenv("BUSY_ALERT_NTFY_TOPIC", raising=False)
    assert asyncio.run(_start()) is None


async def _start():
    return busy.start()


def test_send_ntfy_posts_title_and_message():
    received = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received["path"] = self.path
            received["title"] = self.headers["Title"]
            received["tags"] = self.headers["Tags"]
            received["body"] = self.rfile.read(int(self.headers["Content-Length"])).decode()
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()
    title, message, tags = busy.alert_text("busy", 83.4, 70, 5)
    busy.send_ntfy(f"http://127.0.0.1:{server.server_port}/", "my-topic", title, message, tags)
    thread.join(5)
    server.server_close()
    assert received == {"path": "/my-topic", "title": "Server busy", "tags": "warning",
                        "body": "CPU has averaged 83% (alert at 70%) for the last 5 minutes."}


def test_watch_keeps_going_when_a_send_fails(monkeypatch):
    sent = []
    clock = iter(range(0, 100000, 30))
    used = iter(x * 0.1 * 0.9 for x in range(0, 100000, 30))   # 90% of 0.1 CPU throughout

    def fail(*args):
        sent.append(args)
        raise OSError("no network")

    async def no_wait(_):
        if len(sent) >= 1:
            raise asyncio.CancelledError

    monkeypatch.setattr(busy, "cpu_allowance", lambda: 0.1)
    monkeypatch.setattr(busy, "cpu_seconds", lambda: next(used))
    monkeypatch.setattr(busy.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(busy, "send_ntfy", fail)
    monkeypatch.setattr(busy.asyncio, "sleep", no_wait)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(busy.watch("topic", "https://ntfy.sh", 70, 5, 60))
    assert sent and sent[0][2] == "Server busy"


def _ntfy_server(statuses):
    """A local ntfy stand-in answering each POST with the next status; returns (server, seen)."""
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            seen.append(self.headers.get("Authorization"))
            status = statuses[len(seen) - 1]
            body = b'{"code":42901,"error":"limit reached: too many requests"}' if status == 429 else b""
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen


def test_send_ntfy_sends_the_token_and_retries_a_429_once(monkeypatch):
    monkeypatch.setenv("NTFY_TOKEN", " tk_abc ")
    server, seen = _ntfy_server([429, 200])
    waits = []
    try:
        busy.send_ntfy(f"http://127.0.0.1:{server.server_port}", "t", "T", "m", "x", sleep=waits.append)
    finally:
        server.shutdown()
        server.server_close()
    assert seen == ["Bearer tk_abc", "Bearer tk_abc"] and waits == [busy.RETRY_SECONDS]


def test_send_ntfy_gives_up_after_a_second_429_and_never_retries_other_errors(monkeypatch):
    import urllib.error
    monkeypatch.delenv("NTFY_TOKEN", raising=False)
    for statuses, posts in (([429, 429], 2), ([500], 1)):
        server, seen = _ntfy_server(statuses)
        try:
            with pytest.raises(urllib.error.HTTPError) as caught:
                busy.send_ntfy(f"http://127.0.0.1:{server.server_port}", "t", "T", "m", "x", sleep=lambda s: None)
        finally:
            server.shutdown()
            server.server_close()
        assert seen == [None] * posts                          # no token: no Authorization header
        if statuses[0] == 429:                                 # ntfy's own reason reaches the log
            assert "limit reached: too many requests" in str(caught.value)
