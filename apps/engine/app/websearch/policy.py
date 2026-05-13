from __future__ import annotations

from urllib.parse import urlparse


OFFICIAL_DOMAINS = (
    "knowledge.broadcom.com",
    "techdocs.broadcom.com",
    "docs.vmware.com",
    "compatibilityguide.broadcom.com",
    "developer.broadcom.com",
    "developer.vmware.com",
    "blogs.vmware.com",
)
COMMUNITY_DOMAINS = (
    "williamlam.com",
    "virten.net",
    "yellow-bricks.com",
    "vstellar.com",
    "communities.vmware.com",
)


def domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host.removeprefix("www.")


def source_type_for_url(url: str) -> str:
    domain = domain_from_url(url)
    if domain == "knowledge.broadcom.com":
        return "official_kb"
    if domain in {"techdocs.broadcom.com", "docs.vmware.com"}:
        return "official_docs"
    if domain == "compatibilityguide.broadcom.com":
        return "compatibility_guide"
    if domain in {"developer.broadcom.com", "developer.vmware.com"}:
        return "developer_docs"
    if domain == "blogs.vmware.com":
        return "official_blog"
    if domain in COMMUNITY_DOMAINS:
        return "community_reference"
    return "unknown"


def is_official_source(source_type: str) -> bool:
    return source_type.startswith("official") or source_type in {"compatibility_guide", "developer_docs"}
