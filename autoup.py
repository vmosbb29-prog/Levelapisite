import requests

# Fallback values if auto-update API is unavailable
_FALLBACK_URL     = "https://clientbp.ggpolarbear.com/"
_FALLBACK_OB      = "OB48"
_FALLBACK_VERSION = "1.106.1"


def AuToUpDaTE():
    """
    Fetches latest Free Fire server URL, OB version, and Play Store version.
    Returns fallback values instead of crashing if the API is unreachable.
    """
    api_url = "https://auto-update-devil.vercel.app/"
    try:
        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        server_url = data["server_url"]
        ob_version = data["latest_release_version"]
        version    = data["play_version"]
        print(f"[AutoUpdate] OK — server={server_url}  ob={ob_version}  ver={version}")
        return server_url, ob_version, version
    except Exception as e:
        print(f"[AutoUpdate] WARNING: API unavailable ({e}). Using fallback values.")
        return _FALLBACK_URL, _FALLBACK_OB, _FALLBACK_VERSION
