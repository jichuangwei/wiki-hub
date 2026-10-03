"""Authenticated remote MCP tools for the scheduled report task."""
import os
import base64
import binascii
from pathlib import Path

import httpx
import jwt
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse

from publisher.service import GitHub, Publisher


class Verifier:
    def __init__(self, issuer, audience, jwks_url, subjects):
        self.issuer, self.audience, self.subjects = issuer, audience, subjects
        self.keys = jwt.PyJWKClient(jwks_url)

    async def verify_token(self, token):
        try:
            key = self.keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, key.key, algorithms=["RS256"], issuer=self.issuer,
                                audience=self.audience, options={"require": ["exp", "sub", "iss", "aud"]})
            scopes = claims.get("scope", "").split()
            if claims["sub"] not in self.subjects or "reports:publish" not in scopes:
                return None
            return AccessToken(token=token, client_id=claims.get("azp", claims["sub"]),
                               scopes=scopes, expires_at=claims["exp"], resource=self.audience)
        except (jwt.PyJWTError, ValueError, TypeError):
            return None


def load_private_key():
    """Read only runtime secrets: mounted file or Railway sealed base64 variable."""
    filename = os.environ.get("GITHUB_APP_PRIVATE_KEY_FILE")
    encoded = os.environ.get("GITHUB_APP_PRIVATE_KEY_BASE64")
    if bool(filename) == bool(encoded):
        raise ValueError("Configure exactly one private-key file or sealed base64 variable")
    if filename:
        return Path(filename).read_text()
    try:
        return base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Invalid sealed private-key encoding") from None


def create_server():
    # Required configuration: fail closed rather than start a public unauthenticated publisher.
    public_url = AnyHttpUrl(os.environ["PUBLISHER_URL"])
    issuer = AnyHttpUrl(os.environ["OAUTH_ISSUER"])
    jwks = os.environ["OAUTH_JWKS_URL"]
    if any(not str(url).startswith("https://") for url in (public_url, issuer, jwks)):
        raise ValueError("Public endpoint, issuer and JWKS must use HTTPS")
    if public_url.path != "/mcp" or public_url.port not in (None, 443) or public_url.query or public_url.fragment:
        raise ValueError("Public endpoint must use standard HTTPS port and /mcp path")
    subjects = {subject.strip() for subject in os.environ["OAUTH_ALLOWED_SUBJECTS"].split(",") if subject.strip()}
    if not subjects:
        raise ValueError("At least one authorized OAuth subject is required")
    client = httpx.Client(timeout=30, follow_redirects=True)
    github = GitHub(client, os.environ["GITHUB_APP_ID"], os.environ["GITHUB_INSTALLATION_ID"],
                    load_private_key())
    publisher = Publisher(github, client, Path(os.environ["PUBLISHER_DB"]))
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("Invalid service port")
    server = FastMCP("Wiki Hub weekly publisher", host="0.0.0.0", port=port,
        stateless_http=True, json_response=True,
        auth=AuthSettings(issuer_url=issuer, resource_server_url=public_url,
                          required_scopes=["reports:publish"], validate_token_resource=True),
        token_verifier=Verifier(str(issuer), str(public_url), jwks, subjects),
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
            allowed_hosts=[public_url.host, f"{public_url.host}:443", f"127.0.0.1:{port}"],
            allowed_origins=[f"https://{public_url.host}"]))

    @server.custom_route("/health", methods=["GET"])
    async def health(request):
        # Only liveness; this is not proof of GitHub or OAuth end-to-end connectivity.
        return JSONResponse({"status": "ok"})

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                             idempotentHint=True, openWorldHint=True))
    def publish_weekly_report(start: str, end: str, html: str) -> dict:
        """Publish validated HTML to wiki-hub/main through Actions. Return request_id, not deployment success.
        This tool changes the public website. Retry the same payload safely; query status after ambiguity.
        Dates must cover one Monday–Sunday week. Never pass credentials or email addresses in HTML.
        """
        return publisher.publish(start, end, html)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True))
    def get_publication_status(request_id: str) -> dict:
        """Read this publication's Action, verified archive commit and actual online content.
        Report success only for state=published; deployed_unverified still needs online verification.
        """
        return publisher.status(request_id)

    return server


if __name__ == "__main__":
    create_server().run(transport="streamable-http")
