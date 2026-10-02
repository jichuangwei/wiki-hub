"""Run with publisher/requirements.lock installed (separate from stdlib-only Action tests)."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import jwt
from starlette.testclient import TestClient

from publisher.server import create_server


class RemoteServerTests(unittest.TestCase):
    def test_oauth_blocks_anonymous_and_other_users_and_exposes_only_two_tools(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test-key.pem"
            path.write_bytes(pem)
            settings = {"PUBLISHER_URL": "https://publisher.example.com/mcp",
                "OAUTH_ISSUER": "https://auth.example.com/", "OAUTH_JWKS_URL": "https://auth.example.com/jwks",
                "OAUTH_ALLOWED_SUBJECTS": "owner", "GITHUB_APP_ID": "123", "GITHUB_INSTALLATION_ID": "456",
                "GITHUB_APP_PRIVATE_KEY_FILE": str(path), "PUBLISHER_DB": str(Path(directory) / "db")}
            with patch.dict(os.environ, settings), patch("publisher.server.jwt.PyJWKClient") as jwks:
                jwks.return_value.get_signing_key_from_jwt.return_value = Mock(key=key.public_key())
                server = create_server()
                with TestClient(server.streamable_http_app(), base_url="https://publisher.example.com") as client:
                    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
                    headers = {"Accept": "application/json, text/event-stream"}
                    self.assertEqual(client.post("/mcp", json=request, headers=headers).status_code, 401)
                    for sub, audience, scope, expiry in (("other", settings["PUBLISHER_URL"], "reports:publish", 60),
                            ("owner", "wrong-audience", "reports:publish", 60),
                            ("owner", settings["PUBLISHER_URL"], "read", 60),
                            ("owner", settings["PUBLISHER_URL"], "reports:publish", -60)):
                        token = jwt.encode({"iss": settings["OAUTH_ISSUER"], "aud": audience,
                            "sub": sub, "scope": scope, "exp": int(time.time()) + expiry}, key, algorithm="RS256")
                        response = client.post("/mcp", json=request, headers={**headers, "Authorization": f"Bearer {token}"})
                        self.assertIn(response.status_code, (401, 403))
                    token = jwt.encode({"iss": settings["OAUTH_ISSUER"], "aud": settings["PUBLISHER_URL"],
                        "sub": "owner", "scope": "reports:publish", "exp": int(time.time()) + 60}, key, algorithm="RS256")
                    response = client.post("/mcp", json=request, headers={**headers, "Authorization": f"Bearer {token}"})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual({tool["name"] for tool in response.json()["result"]["tools"]},
                                     {"publish_weekly_report", "get_publication_status"})


if __name__ == "__main__":
    unittest.main()
