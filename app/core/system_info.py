import datetime
import httpx
import logging
import asyncio
import platform
import psutil
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Cache location data to avoid rate limits
_LOCATION_CACHE: Optional[Dict[str, str]] = None
_LAST_LOCATION_FETCH: float = 0
LOCATION_CACHE_DURATION = 3600  # 1 hour

def get_os_info() -> Dict[str, str]:
    """Returns OS and hardware information."""
    try:
        # Basic OS stuff
        uname = platform.uname()
        os_info = {
            "system": uname.system,  # Windows, Linux, Darwin
            "release": uname.release, # 10, 11, etc.
            "version": uname.version,
            "machine": uname.machine, # AMD64, etc.
            "processor": uname.processor
        }
        
        # Memory Info
        vm = psutil.virtual_memory()
        total_gb = round(vm.total / (1024**3), 1)
        avail_gb = round(vm.available / (1024**3), 1)
        os_info["ram_total"] = f"{total_gb} GB"
        os_info["ram_available"] = f"{avail_gb} GB"
        
        return os_info
    except Exception as e:
        logger.warning(f"Failed to fetch OS info: {e}")
        return {}

async def get_public_ip_info() -> Dict[str, str]:
    """
    Fetches public IP and location info using ip-api.com (free, no key).
    """
    global _LOCATION_CACHE, _LAST_LOCATION_FETCH
    
    current_time = datetime.datetime.now().timestamp()
    if _LOCATION_CACHE and (current_time - _LAST_LOCATION_FETCH < LOCATION_CACHE_DURATION):
        return _LOCATION_CACHE

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://ip-api.com/json/")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    info = {
                        "ip": data.get("query", "Unknown"),
                        "city": data.get("city", "Unknown"),
                        "region": data.get("regionName", "Unknown"),
                        "country": data.get("country", "Unknown"),
                        "timezone": data.get("timezone", "UTC"),
                        "isp": data.get("isp", "Unknown")
                    }
                    _LOCATION_CACHE = info
                    _LAST_LOCATION_FETCH = current_time
                    return info
    except Exception as e:
        logger.warning(f"Failed to fetch ID/Location info: {e}")
    
    # Fallback return (don't cache failure forever)
    return {
        "ip": "Unknown", 
        "city": "Unknown", 
        "region": "Unknown", 
        "country": "Unknown", 
        "timezone": "UTC"
    }

def get_formatted_time(timezone_str: str = "UTC") -> str:
    """Returns current time formatted for the prompt."""
    now = datetime.datetime.now()
    # Simple formatting, ideally we would use 'pytz' or 'zoneinfo' if installed to respect the fetched timezone
    # For now, we rely on system local time but report the fetched timezone name
    return now.strftime("%Y-%m-%d %H:%M:%S %A")

async def get_system_context_string() -> str:
    """
    Constructs the standard system context block for Agents/Heartbeat.
    Fetches location asynchronously if needed.
    """
    loc = await get_public_ip_info()
    time_str = get_formatted_time(loc.get("timezone", "UTC"))
    os_info = get_os_info()
    
    return f"""### CURRENT SYSTEM STATUS
- **Date/Time**: {time_str}
- **Location**: {loc['city']}, {loc['region']}, {loc['country']}
- **Timezone**: {loc['timezone']}
- **Connection**: {loc.get('isp', 'Unknown')}
- **Operating System**: {os_info.get('system', 'Unknown')} {os_info.get('release', '')} ({os_info.get('machine', '')})
- **Hardware**: {os_info.get('processor', 'Unknown Processor')} | RAM: {os_info.get('ram_available', '?')} / {os_info.get('ram_total', '?')}
"""
