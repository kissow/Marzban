"""Build a node-only Xray extension without mutating the panel core config."""

from copy import deepcopy
from ipaddress import ip_address


def _validate_server(server):
    if not isinstance(server, str) or not server or len(server) > 253:
        raise ValueError("Invalid proxy server")
    if any(character.isspace() for character in server) or "/" in server or "@" in server:
        raise ValueError("Invalid proxy server")
    try:
        ip_address(server)
        return server
    except ValueError:
        pass
    if not all(part and len(part) <= 63 and part.replace("-", "a").isalnum()
               and not part.startswith("-") and not part.endswith("-") for part in server.split(".")):
        raise ValueError("Invalid proxy server")
    return server


def validate_egress(profile):
    """Validate one HTTP/SOCKS upstream for one Node."""
    if not isinstance(profile, dict):
        raise ValueError("Proxy settings must be an object")
    protocol = profile.get("protocol")
    if protocol not in ("http", "socks"):
        raise ValueError("Only HTTP and SOCKS proxy outbounds are supported")
    server = _validate_server(profile.get("server"))
    port = profile.get("port")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Proxy port must be between 1 and 65535")
    username, password = profile.get("username"), profile.get("password")
    if (username is None) != (password is None):
        raise ValueError("Proxy username and password must be provided together")
    if username is not None and (not isinstance(username, str) or not isinstance(password, str)
                                 or not username or not password or len(username) > 256 or len(password) > 256):
        raise ValueError("Invalid proxy credentials")
    return {
        "tag": "managed-residential-egress",
        "protocol": protocol,
        "server": server,
        "port": port,
        "username": username,
        "password": password,
    }


def supports_egress(health):
    """Only a paired custom Node may receive the managed extension."""
    if not isinstance(health, dict) or health.get("source") != "node-runtime":
        return False
    capabilities = health.get("capabilities")
    return isinstance(capabilities, list) and "managed-outbounds-v1" in capabilities


def for_node(config, profile):
    """Copy the config and add an extension understood only by the custom Node.

    The original XRayConfig is never touched. Rejection by old Nodes is safer
    than silently dropping an intended upstream proxy.
    """
    if profile is None:
        return config
    outbound = validate_egress(profile)
    result = deepcopy(config)
    if "marzban_node_extensions" in result:
        raise ValueError("Xray config already contains a Node extension")
    existing_tags = {item.get("tag") for item in result.get("outbounds", []) if isinstance(item, dict)}
    if outbound["tag"] in existing_tags:
        raise ValueError(f"Reserved outbound tag already exists: {outbound['tag']}")
    result["marzban_node_extensions"] = {
        "outbounds": [
            {key: outbound[key] for key in ("protocol", "server", "port", "username", "password")
             if outbound[key] is not None} | {"tag": outbound["tag"]}
        ],
        "default_outbound_tag": outbound["tag"],
    }
    return result
