"""Fixed-destination TCP relay using the bundled Xray, not a shared proxy account.

Uses the pinned bundled core through an independent process. Control-channel
authorization is handled by the caller; this module has no app/database imports.
"""
import ipaddress
import json
import os
import re
import subprocess
import threading
import time
from collections import deque

import psutil


def clean_address(value):
    value = (value or "").strip()
    if not value or len(value) > 253:
        raise ValueError("A direct IP or DNS-only hostname is required")
    try:
        ip = ipaddress.ip_address(value)
        if ip.is_unspecified or ip.is_loopback or ip.is_multicast or ip.is_link_local:
            raise ValueError("Loopback, unspecified and link-local addresses are not allowed")
        return str(ip)
    except ValueError as exc:
        if ":" in value or re.fullmatch(r"[\d.]+", value):
            raise ValueError("Invalid relay address") from exc
    # Hostnames only: no URLs, credentials, path, template variables or lists.
    value = value.rstrip(".").encode("idna").decode("ascii").lower()
    if len(value) > 253 or value == "localhost" or value.endswith(".localhost") or not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value
    ) or any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in value.split(".")):
        raise ValueError("Use an IP or hostname without a scheme, path or port")
    return value


def business_inbounds(config):
    """First release supports the existing VLESS TCP/RAW REALITY inbounds."""
    return {tag: item for tag, item in config.inbounds_by_tag.items()
            if item.get("protocol") == "vless" and item.get("network") in ("tcp", "raw")
            and item.get("tls") == "reality" and not item.get("is_fallback")
            and type(item.get("port")) is int and 1 <= item["port"] <= 65535}


def config_ports(config):
    ports = set()
    for inbound in config.get("inbounds", []):
        for segment in str(inbound.get("port", "")).split(","):
            parts = segment.strip().split("-")
            if len(parts) <= 2 and all(part.isdigit() for part in parts):
                start, end = int(parts[0]), int(parts[-1])
                if 1 <= start <= end <= 65535:
                    ports.update(range(start, end + 1))
    return ports


def choose_port(requested, current, reserved, allocated, occupied):
    blocked = set(reserved) | set(allocated) | set(occupied)
    if requested is not None:
        if type(requested) is not int or not 1024 <= requested <= 65535 or requested in blocked:
            raise ValueError("Relay port is invalid, reserved or already in use")
        return requested
    if type(current) is int and 1024 <= current <= 65535 and current not in blocked:
        return current
    for port in range(18443, 65536):
        if port not in blocked:
            return port
    raise ValueError("No available relay port")


def make_config(profiles, listen="0.0.0.0"):
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": f"managed-node-relay-{item['node_id']}", "listen": listen,
            "port": item["listen_port"], "protocol": "dokodemo-door",
            "settings": {"address": item["target_address"], "port": item["target_port"],
                         "network": "tcp", "followRedirect": False},
            "sniffing": {"enabled": False},
        } for item in profiles],
        "outbounds": [{"tag": "relay-direct", "protocol": "freedom", "settings": {}}],
    }


def host_target(host, default_port):
    """Match original Hosts without DNS lookups or guessing by display name.

    A mixed-address load-balancing host cannot safely acquire one relay port.
    Templates and alternate business domains are not guessed as a Node identity.
    """
    addresses = host.get("address") or []
    if not isinstance(addresses, (list, tuple)) or not addresses:
        return None
    try:
        normalized = {clean_address(address) for address in addresses}
    except (ValueError, TypeError, AttributeError):
        return None
    if len(normalized) != 1:
        return None
    return (normalized.pop(), host.get("port") or default_port)


def rewrite_hosts(hosts, profiles, default_port):
    """Switch original entries internally; never append or rename a Host.

    Preserve per-host SNI/fingerprint/transport overrides and all user credentials.
    Copy address/port only, leaving persisted Hosts and other Node entries intact.
    Ambiguous destinations fail closed to the original direct configuration.
    """
    from collections import defaultdict
    destinations = defaultdict(list)
    for profile in profiles:
        destinations[(profile["target_address"], profile["target_port"])].append(profile)
    result = []
    for host in hosts:
        matches = destinations.get(host_target(host, default_port), [])
        if len(matches) == 1:
            profile = matches[0]
            result.append({**host, "address": [profile["entry_address"]], "port": profile["listen_port"]})
        else:
            result.append(host)
    return result


class RelayProcess:
    """One independent Xray process for all managed relay listeners.

    Reconfiguration may interrupt relay sessions, but never touches main/Node
    cores. Syntax is checked before stopping an old process; failed start restores
    the last configuration. Publication requires verified local listener ownership.
    """
    def __init__(self, executable, assets, listen="0.0.0.0"):
        self.executable, self.assets, self.listen = executable, assets, listen
        self.process = None
        self.profiles = []
        self.last_error = None
        self.logs = deque(maxlen=50)
        self.lock = threading.RLock()

    @property
    def running(self):
        return self.process is not None and self.process.poll() is None

    def occupied_ports(self):
        own_pid = self.process.pid if self.running else None
        return {connection.laddr.port for connection in psutil.net_connections(kind="tcp")
                if connection.status == psutil.CONN_LISTEN
                and not (own_pid is not None and connection.pid == own_pid)}

    def _env(self):
        return {**os.environ, "XRAY_LOCATION_ASSET": self.assets}

    def validate(self, profiles):
        if not profiles:
            return
        result = subprocess.run([self.executable, "run", "-test", "-config", "stdin:"],
                                input=json.dumps(make_config(profiles, self.listen)),
                                capture_output=True, text=True, timeout=15, env=self._env())
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout)[-2000:] or "Xray relay validation failed")

    def _stop(self):
        process, self.process = self.process, None
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()

    def _start(self, profiles):
        self.logs.clear()
        process = subprocess.Popen([self.executable, "run", "-config", "stdin:"],
                                   env=self._env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        self.process = process
        def capture():
            try:
                for line in process.stdout:
                    self.logs.append(line.rstrip()[-2000:])
            except (ValueError, OSError):
                pass
        threading.Thread(target=capture, daemon=True).start()
        process.stdin.write(json.dumps(make_config(profiles, self.listen)))
        process.stdin.close()
        expected = {item["listen_port"] for item in profiles}
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Xray relay exited: " + " / ".join(self.logs)[-1500:])
            ports = {conn.laddr.port for conn in psutil.net_connections(kind="tcp")
                     if conn.pid == process.pid and conn.status == psutil.CONN_LISTEN}
            if expected <= ports:
                return
            time.sleep(0.05)
        raise RuntimeError("Relay listener readiness timed out")

    def apply(self, profiles):
        profiles = sorted([dict(item) for item in profiles], key=lambda item: item["node_id"])
        with self.lock:
            if make_config(profiles, self.listen) == make_config(self.profiles, self.listen) and (not profiles or self.running):
                self.profiles = profiles
                return
            previous = [dict(item) for item in self.profiles]
            try:
                self.validate(profiles)
            except Exception as exc:
                self.last_error = str(exc)[:2000]
                raise RuntimeError(self.last_error) from exc
            self._stop()
            try:
                if profiles:
                    self._start(profiles)
                self.profiles = profiles
                self.last_error = None
            except Exception as exc:
                self._stop()
                self.last_error = str(exc)[:2000]
                try:
                    if previous:
                        self._start(previous)
                except Exception as restore_error:
                    self.last_error += "; rollback failed: " + str(restore_error)[:1000]
                raise RuntimeError(self.last_error) from exc

    def stop(self):
        with self.lock:
            self._stop()
            self.profiles = []

    def snapshot(self):
        with self.lock:
            return [dict(item) for item in self.profiles] if self.running else []
