import socket
import json
import re
import ssl
import tempfile
import threading
import time
from collections import deque
from contextlib import contextmanager
from typing import List

import grpc
import requests
import rpyc
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from websocket import WebSocketConnectionClosedException, WebSocketTimeoutException, create_connection

from app.xray.config import XRayConfig
from xray_api import XRay as XRayAPI

NODE_CONNECT_TIMEOUT = 15
NODE_CONTROL_TIMEOUT = (10, 10)  # TCP/TLS connection, then response read
NODE_API_READY_TIMEOUT = 10
NODE_READ_ONLY_PATHS = frozenset(("/", "/ping", "/health", "/device-activity"))


def string_to_temp_file(content: str):
    file = tempfile.NamedTemporaryFile(mode='w+t')
    file.write(content)
    file.flush()
    return file


class SANIgnoringAdaptor(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       assert_hostname=False)


class NodeAPIError(Exception):
    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail


class ReSTXRayNode:
    def __init__(self,
                 address: str,
                 port: int,
                 api_port: int,
                 ssl_key: str,
                 ssl_cert: str,
                 usage_coefficient: float = 1):

        self.address = address
        self.port = port
        self.api_port = api_port
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.usage_coefficient = usage_coefficient

        self._keyfile = string_to_temp_file(ssl_key)
        self._certfile = string_to_temp_file(ssl_cert)

        self.session = requests.Session()
        self.session.mount('https://', SANIgnoringAdaptor())
        self.session.cert = (self._certfile.name, self._keyfile.name)

        self._session_id = None
        self._rest_api_url = f"https://{self.address.strip('/')}:{self.port}"

        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE
        self._ssl_context.load_cert_chain(certfile=self.session.cert[0], keyfile=self.session.cert[1])
        self._logs_ws_url = f"wss://{self.address.strip('/')}:{self.port}/logs"
        self._logs_queues = []
        self._logs_bg_thread = threading.Thread(target=self._bg_fetch_logs, daemon=True)

        self._api = None
        self._started = False

    def _prepare_config(self, config: XRayConfig):
        for inbound in config.get("inbounds", []):
            streamSettings = inbound.get("streamSettings") or {}
            tlsSettings = streamSettings.get("tlsSettings") or {}
            certificates = tlsSettings.get("certificates") or []
            for certificate in certificates:
                if certificate.get("certificateFile"):
                    with open(certificate['certificateFile']) as file:
                        certificate['certificate'] = [
                            line.strip() for line in file.readlines()
                        ]
                        del certificate['certificateFile']

                if certificate.get("keyFile"):
                    with open(certificate['keyFile']) as file:
                        certificate['key'] = [
                            line.strip() for line in file.readlines()
                        ]
                        del certificate['keyFile']

        return config

    def make_request(self, path: str, timeout=NODE_CONTROL_TIMEOUT, **params):
        # These POST routes are read-only in both old and new Nodes. Never
        # replay /connect, /start, /restart or policy writes after an ambiguous
        # response timeout: the remote mutation may already have succeeded.
        attempts = 2 if path in NODE_READ_ONLY_PATHS else 1
        for attempt in range(attempts):
            try:
                res = self.session.post(self._rest_api_url + path, timeout=timeout,
                                        json={"session_id": self._session_id, **params})
                data = res.json()
                break
            except requests.exceptions.SSLError as exc:
                raise NodeAPIError(0, f"{path} TLS verification/transport: {exc}") from exc
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                if attempt + 1 < attempts:
                    continue
                raise NodeAPIError(0, f"{path} control request: {exc}") from exc
            except Exception as exc:
                raise NodeAPIError(0, f"{path} invalid control response: {exc}") from exc

        if res.status_code == 200:
            return data
        else:
            exc = NodeAPIError(res.status_code, data.get('detail', f'HTTP {res.status_code}'))
            raise exc

    def _check_session(self):
        if not self._session_id:
            return False
        try:
            self.make_request("/ping")
            return True
        except NodeAPIError as exc:
            if exc.status_code == 403 and exc.detail == "Session ID mismatch.":
                self._session_id = None
                self._api = None
                self._started = False
                return False
            # A timeout is not evidence that the authenticated session expired.
            raise

    @property
    def connected(self):
        try:
            return self._check_session()
        except NodeAPIError:
            return False

    @property
    def started(self):
        res = self.make_request("/")
        return res.get('started', False)

    @property
    def api(self):
        if not self._session_id:
            raise ConnectionError("Node is not connected")

        if not self._api:
            if self._started is True:
                self._api = XRayAPI(
                    address=self.address,
                    port=self.api_port,
                    ssl_cert=self._node_cert.encode(),
                    ssl_target_name="Gozargah"
                )
            else:
                raise ConnectionError("Node is not started")

        return self._api

    def connect(self):
        if self._session_id:
            # /connect on an already connected Node stops its running core.
            # Reuse a valid session; propagate transient errors without takeover.
            if self._check_session():
                return
        self._node_cert = ssl.get_server_certificate((self.address, self.port), timeout=NODE_CONNECT_TIMEOUT)
        self._node_certfile = string_to_temp_file(self._node_cert)
        self.session.verify = self._node_certfile.name

        res = self.make_request("/connect")
        self._session_id = res['session_id']

    def disconnect(self):
        self.make_request("/disconnect")
        self._session_id = None

    def get_version(self):
        res = self.make_request("/")
        return res.get('core_version')

    def get_health(self):
        if not self._session_id:
            raise ConnectionError("Node is not connected")
        try:
            return self.make_request("/health")
        except NodeAPIError as exc:
            if exc.status_code == 404:
                raise NotImplementedError("Node does not support health metrics") from exc
            raise

    def get_device_activity(self):
        """Return the optional activity contract, or ``None`` for old Nodes."""
        if not self._session_id:
            raise ConnectionError("Node is not connected")
        try:
            return self.make_request("/device-activity")
        except NodeAPIError as exc:
            if exc.status_code in (404, 405, 501):
                return None
            raise

    def set_device_policies(self, policies):
        """Send a complete policy snapshot when supported by the Node."""
        if not self._session_id:
            raise ConnectionError("Node is not connected")
        try:
            return self.make_request("/device-policies", policies=policies)
        except NodeAPIError as exc:
            if exc.status_code in (404, 405, 501):
                return None
            raise

    def start(self, config: XRayConfig):
        if not self.connected:
            self.connect()

        config = self._prepare_config(config)
        json_config = config.to_json()

        try:
            res = self.make_request("/start", timeout=10, config=json_config)
        except NodeAPIError as exc:
            if exc.detail == 'Xray is started already':
                # This also recovers a successful /start whose response was
                # lost. An explicit configuration restart uses /restart.
                res = {"started": True}
            else:
                raise exc

        self._started = True

        self._api = XRayAPI(
            address=self.address,
            port=self.api_port,
            ssl_cert=self._node_cert.encode(),
            ssl_target_name="Gozargah"
        )

        try:
            grpc.channel_ready_future(self._api._channel).result(timeout=NODE_API_READY_TIMEOUT)
        except grpc.FutureTimeoutError:
            raise ConnectionError(f"Node Xray API port {self.api_port} not ready after {NODE_API_READY_TIMEOUT}s; check its listener and firewall")

        return res

    def stop(self):
        if not self.connected:
            self.connect()

        self.make_request('/stop')
        self._api = None
        self._started = False

    def restart(self, config: XRayConfig):
        if not self.connected:
            self.connect()

        config = self._prepare_config(config)
        json_config = config.to_json()

        res = self.make_request("/restart", timeout=10, config=json_config)

        self._started = True

        self._api = XRayAPI(
            address=self.address,
            port=self.api_port,
            ssl_cert=self._node_cert.encode(),
            ssl_target_name="Gozargah"
        )

        try:
            grpc.channel_ready_future(self._api._channel).result(timeout=NODE_API_READY_TIMEOUT)
        except grpc.FutureTimeoutError:
            raise ConnectionError(f"Node Xray API port {self.api_port} not ready after {NODE_API_READY_TIMEOUT}s; check its listener and firewall")

        return res

    def _bg_fetch_logs(self):
        while self._logs_queues:
            try:
                websocket_url = f"{self._logs_ws_url}?session_id={self._session_id}&interval=0.7"
                self._ssl_context.load_verify_locations(self.session.verify)
                ws = create_connection(websocket_url, sslopt={"context": self._ssl_context}, timeout=2)
                while self._logs_queues:
                    try:
                        logs = ws.recv()
                        for buf in self._logs_queues:
                            buf.append(logs)
                    except WebSocketConnectionClosedException:
                        break
                    except WebSocketTimeoutException:
                        pass
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(2)

    @contextmanager
    def get_logs(self):
        try:
            buf = deque(maxlen=100)
            self._logs_queues.append(buf)

            if not self._logs_bg_thread.is_alive():
                try:
                    self._logs_bg_thread.start()
                except RuntimeError:
                    self._logs_bg_thread = threading.Thread(target=self._bg_fetch_logs, daemon=True)
                    self._logs_bg_thread.start()

            yield buf

        finally:
            try:
                self._logs_queues.remove(buf)
            except ValueError:
                pass
            del buf


class RPyCXRayNode:
    def __init__(self,
                 address: str,
                 port: int,
                 api_port: int,
                 ssl_key: str,
                 ssl_cert: str,
                 usage_coefficient: float = 1):

        class Service(rpyc.Service):
            def __init__(self,
                         on_start_funcs: List[callable] = [],
                         on_stop_funcs: List[callable] = []):
                self.on_start_funcs = on_start_funcs
                self.on_stop_funcs = on_stop_funcs

            def exposed_on_start(self):
                for func in self.on_start_funcs:
                    threading.Thread(target=func).start()

            def exposed_on_stop(self):
                for func in self.on_stop_funcs:
                    threading.Thread(target=func).start()

            def add_startup_func(self, func):
                self.on_start_funcs.append(func)

            def add_shutdown_func(self, func):
                self.on_stop_funcs.append(func)

            def on_connect(self, conn):
                pass

            def on_disconnect(self, conn):
                pass

        self.address = address
        self.port = port
        self.api_port = api_port
        self.ssl_key = ssl_key
        self.ssl_cert = ssl_cert
        self.usage_coefficient = usage_coefficient

        self.started = False

        self._keyfile = string_to_temp_file(ssl_key)
        self._certfile = string_to_temp_file(ssl_cert)

        self._service = Service()
        self._api = None

    def disconnect(self):
        try:
            self.connection.close()
            del self.connection
        except AttributeError:
            pass

    def connect(self):
        self.disconnect()

        tries = 0
        while True:
            tries += 1
            self._node_cert = ssl.get_server_certificate((self.address, self.port), timeout=NODE_CONNECT_TIMEOUT)
            self._node_certfile = string_to_temp_file(self._node_cert)
            conn = self._connect_transport()
            try:
                conn.ping()
                self.connection = conn
                break
            except EOFError as exc:
                conn.close()
                if tries <= 3:
                    continue
                raise exc
            except Exception:
                conn.close()
                raise

    def _connect_transport(self):
        # RPyC's ssl_connect does not expose a TLS handshake deadline. Keep
        # mutual TLS and the existing pinned Node certificate, but bound the
        # socket/handshake before handing the blocking stream to RPyC.
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.load_verify_locations(cafile=self._node_certfile.name)
        context.load_cert_chain(self._certfile.name, self._keyfile.name)
        sock = socket.create_connection((self.address, self.port), timeout=NODE_CONNECT_TIMEOUT)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            sock = context.wrap_socket(sock, server_hostname=self.address)
            sock.settimeout(None)
            return rpyc.utils.factory.connect_stream(
                rpyc.core.stream.SocketStream(sock), service=self._service,
                config={"sync_request_timeout": 10})
        except Exception:
            sock.close()
            raise

    @property
    def connected(self):
        try:
            self.connection.ping()
            return (not self.connection.closed)
        except (AttributeError, EOFError):
            self.disconnect()
            return False

    @property
    def remote(self):
        if not self.connected:
            self.connect()
        return self.connection.root

    @property
    def api(self):
        if not self.connected:
            raise ConnectionError("Node is not connected")

        if not self.started:
            raise ConnectionError("Node is not started")

        return self._api

    def get_version(self):
        return self.remote.fetch_xray_version()

    def get_health(self):
        if not self.connected:
            raise ConnectionError("Node is not connected")
        result = rpyc.async_(self.connection.root.fetch_health)()
        result.set_expiry(3)
        result.wait()
        if not result.ready:
            raise TimeoutError("Node health request timed out")
        return {key: result.value[key] for key in result.value}

    def get_device_activity(self):
        """Return the optional activity contract, or ``None`` for old Nodes."""
        if not self.connected:
            raise ConnectionError("Node is not connected")
        fetch = getattr(self.connection.root, "fetch_device_activity", None)
        if fetch is None:
            return None
        result = rpyc.async_(fetch)()
        result.set_expiry(3)
        result.wait()
        if not result.ready:
            raise TimeoutError("Node activity request timed out")
        return {key: result.value[key] for key in result.value}

    def set_device_policies(self, policies):
        """Send a complete policy snapshot when supported by the Node."""
        if not self.connected:
            raise ConnectionError("Node is not connected")
        setter = getattr(self.connection.root, "set_device_policies", None)
        if setter is None:
            return None
        result = rpyc.async_(setter)(json.dumps(policies))
        result.set_expiry(5)
        result.wait()
        if not result.ready:
            raise TimeoutError("Node policy update timed out")
        return {key: result.value[key] for key in result.value}

    def _prepare_config(self, config: XRayConfig):
        for inbound in config.get("inbounds", []):
            streamSettings = inbound.get("streamSettings") or {}
            tlsSettings = streamSettings.get("tlsSettings") or {}
            certificates = tlsSettings.get("certificates") or []
            for certificate in certificates:
                if certificate.get("certificateFile"):
                    with open(certificate['certificateFile']) as file:
                        certificate['certificate'] = [
                            line.strip() for line in file.readlines()
                        ]
                        del certificate['certificateFile']

                if certificate.get("keyFile"):
                    with open(certificate['keyFile']) as file:
                        certificate['key'] = [
                            line.strip() for line in file.readlines()
                        ]
                        del certificate['keyFile']

        return config

    def start(self, config: XRayConfig):
        config = self._prepare_config(config)
        json_config = config.to_json()
        self.remote.start(json_config)
        self.started = True

        # connect to API
        self._api = XRayAPI(
            address=self.address,
            port=self.api_port,
            ssl_cert=self._node_cert.encode(),
            ssl_target_name="Gozargah"
        )
        try:
            grpc.channel_ready_future(self._api._channel).result(timeout=5)
        except grpc.FutureTimeoutError:

            start_time = time.time()
            end_time = start_time + 3  # check logs for 3 seconds
            last_log = ''
            with self.get_logs() as logs:
                while time.time() < end_time:
                    if logs:
                        last_log = logs[-1].strip().split('\n')[-1]
                    time.sleep(0.1)

            self.disconnect()

            if re.search(r'[Ff]ailed', last_log):
                raise RuntimeError(last_log)

            raise ConnectionError('Failed to connect to node\'s API')

    def stop(self):
        self.remote.stop()
        self.started = False
        self._api = None

    def restart(self, config: XRayConfig):
        self.started = False
        config = self._prepare_config(config)
        json_config = config.to_json()
        self.remote.restart(json_config)
        self.started = True

    @contextmanager
    def get_logs(self):
        if not self.connected:
            raise ConnectionError("Node is not connected")

        try:
            self.__curr_logs
        except AttributeError:
            self.__curr_logs = 0

        try:
            buf = deque(maxlen=100)

            if self.__curr_logs <= 0:
                self.__curr_logs = 1
                self.__bgsrv = rpyc.BgServingThread(self.connection)
            else:
                if not self.__bgsrv._active:
                    self.__bgsrv = rpyc.BgServingThread(self.connection)
                self.__curr_logs += 1

            logs = self.remote.fetch_logs(buf.append)
            yield buf

        finally:
            if self.__curr_logs <= 1:
                self.__curr_logs = 0
                self.__bgsrv.stop()
            else:
                if not self.__bgsrv._active:
                    self.__bgsrv = rpyc.BgServingThread(self.connection)
                self.__curr_logs -= 1

            if logs:
                logs.stop()

    def on_start(self, func: callable):
        self._service.add_startup_func(func)
        return func

    def on_stop(self, func: callable):
        self._service.add_shutdown_func(func)
        return func


class XRayNode:
    def __new__(self,
                address: str,
                port: int,
                api_port: int,
                ssl_key: str,
                ssl_cert: str,
                usage_coefficient: float = 1):

        # trying to detect what's the server of node
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((address, port))
                s.send(b'HEAD / HTTP/1.0\r\n\r\n')
                s.recv(1024)
            # it might be uvicorn
            return ReSTXRayNode(
                address=address,
                port=port,
                api_port=api_port,
                ssl_key=ssl_key,
                ssl_cert=ssl_cert,
                usage_coefficient=usage_coefficient
            )
        except Exception:
            # if might be rpyc
            return RPyCXRayNode(
                address=address,
                port=port,
                api_port=api_port,
                ssl_key=ssl_key,
                ssl_cert=ssl_cert,
                usage_coefficient=usage_coefficient
            )
