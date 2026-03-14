"""
Data Manager - Handles channel data and EPG integration.

This module provides backward-compatible interface while using
the optimized EPGManager for EPG operations.
"""

import os
import re
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# Import optimized EPG manager
from src.epg_manager import EPGManager, EPGSource, load_epg_data


class DataManager:
    """
    Manages channel data, EPG information, and logo mappings.
    
    Provides backward-compatible interface for existing code while
    using the optimized EPGManager internally.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl_hours: int = 12):
        self.channels: List[Dict[str, Any]] = []
        self.user_agent = "VAVOO/2.6"
        self.logos_map: Dict[str, str] = {}
        self._logos_keys_sorted: List[str] = []  # Sorted keys for faster partial matching
        
        # Initialize optimized EPG manager
        self._epg_manager: Optional[EPGManager] = None
        self._cache_dir = cache_dir
        self._cache_ttl = cache_ttl_hours
        
        # Legacy compatibility attributes
        self.epg_data: Dict[str, List[Dict]] = {}
        self.epg_channels: Dict[str, str] = {}
        self.epg_names: Dict[str, str] = {}
        self.epg_icons: Dict[str, str] = {}
        
        # Name normalization cache
        self._normalize_cache: Dict[str, str] = {}
        
        self._load_local_logos()

    def _load_local_logos(self):
        """Scans the logos directory and builds a map."""
        logos_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logos")
        if not os.path.exists(logos_dir):
            return
        
        for filename in os.listdir(logos_dir):
            if filename.endswith(('.png', '.svg', '.jpg')):
                base = os.path.splitext(filename)[0]
                norm_base = re.sub(r'[^A-Z0-9]', '', base.upper())
                norm_base = re.sub(r'IT$', '', norm_base)
                self.logos_map[norm_base] = os.path.join(logos_dir, filename)
        
        # Pre-sort keys by length (longer first) for better partial matching
        self._logos_keys_sorted = sorted(self.logos_map.keys(), key=len, reverse=True)

    def find_logo(self, norm_name: str) -> Optional[str]:
        """Attempts to find a matching logo path (optimized with sorted keys)."""
        if not norm_name:
            return None
        
        snorm = re.sub(r'[^A-Z0-9]', '', norm_name)
        if snorm in self.logos_map:
            return self.logos_map[snorm]
        
        # Try partial matches using pre-sorted keys (longer first for better matches)
        for key in self._logos_keys_sorted:
            if key in snorm or snorm in key:
                return self.logos_map[key]
        return None

    def get_clean_epg_name(self, epg_id: str) -> Optional[str]:
        """Returns the display name from EPG, stripping 'IT - ' prefix."""
        if not epg_id:
            return None
        
        raw_name = self.epg_names.get(epg_id)
        if not raw_name:
            return None
        
        # Remove "IT - " or "CH - " prefix if present
        clean_name = re.sub(r'^(IT|CH)\s*-\s*', '', raw_name, flags=re.IGNORECASE)
        return clean_name.strip()

    def normalize_name(self, name: str) -> str:
        """Normalizes channel name for better EPG matching (cached)."""
        if not name:
            return ""
        
        # Check cache first
        if name in self._normalize_cache:
            return self._normalize_cache[name]
        
        n = name.upper().strip()
        
        # Remove explicit country codes or extensions
        n = re.sub(r'\s+\.[A-Z]{1,3}$', '', n)
        
        # Remove Vavoo specific suffixes
        n = re.sub(r'\s+[CST]$', '', n)
        
        # Remove parentheses/brackets
        n = re.sub(r'\[.*?\]', '', n)
        n = re.sub(r'\(.*?\)', '', n)
        
        # Remove quality suffixes
        n = re.sub(r'\s+(HD|FHD|SD|HEVC|H265).*', '', n)
        
        # Remove special chars AND spaces
        n = re.sub(r'[^A-Z0-9]', '', n)
        
        result = n.strip()
        self._normalize_cache[name] = result
        return result

    def load_all_epgs(self, force_refresh: bool = False) -> bool:
        """Loads EPG data from multiple sources with caching.
        
        Args:
            force_refresh: If True, ignore cache and download fresh.
        """
        try:
            # Initialize EPG manager if not already done
            if self._epg_manager is None:
                self._epg_manager = EPGManager(
                    cache_dir=self._cache_dir,
                    cache_ttl_hours=self._cache_ttl,
                    user_agent=self.user_agent
                )
            
            # Load all EPG sources
            success = self._epg_manager.load_all(force_refresh)
            
            if success:
                # Sync to legacy format for backward compatibility
                self._sync_to_legacy_format()
                self._apply_epg_to_channels()
            
            return success
            
        except Exception as e:
            logging.error(f"Failed to load EPG: {e}")
            return False

    def _sync_to_legacy_format(self):
        """Sync EPGManager data to legacy format for backward compatibility."""
        if not self._epg_manager:
            return
        
        # Clear existing data
        self.epg_data = {}
        self.epg_channels = {}
        self.epg_names = {}
        self.epg_icons = {}
        
        # Convert channels
        for ch_id, info in self._epg_manager.channels.items():
            self.epg_channels[ch_id] = info.display_name
            self.epg_names[ch_id] = info.display_name
            if info.icon:
                self.epg_icons[ch_id] = info.icon
            
            # Also map normalized name to ID
            self.epg_channels[info.normalized_name] = ch_id
        
        # Convert programs
        for ch_id, programs in self._epg_manager.programs.items():
            self.epg_data[ch_id] = [
                {
                    'start': p.start.strftime("%Y%m%d%H%M%S %z"),
                    'stop': p.stop.strftime("%Y%m%d%H%M%S %z"),
                    'title': p.title,
                    'desc': p.desc
                }
                for p in programs
            ]

    def _apply_epg_to_channels(self):
        """Updates channel names based on loaded EPG data."""
        matches = 0
        for ch in self.channels:
            norm = ch.get('norm_name')
            epg_id = self.epg_channels.get(norm)
            
            if epg_id:
                real_name = self.epg_names.get(epg_id)
                if real_name:
                    ch['name'] = real_name
                    matches += 1
                
                epg_icon = self.epg_icons.get(epg_id)
                if epg_icon:
                    ch['logo'] = epg_icon
        
        logging.info(f"Updated {matches} channel names from all EPGs.")

    def load_epg(self, url: str):
        """Legacy method for backward compatibility."""
        logging.warning("load_epg(url) is deprecated, use load_all_epgs() instead")
        self.load_all_epgs()

    @staticmethod
    def get_current_time_cest() -> datetime:
        """Returns current time in Europe/Rome timezone (CET/CEST)."""
        return datetime.now(ZoneInfo("Europe/Rome"))

    def get_current_program(self, channel_id: str, 
                            norm_name: str = None) -> Tuple[Optional[str], Optional[str], Optional[datetime], Optional[datetime]]:
        """Finds the current running program using ID or normalized name.
        
        Returns: (title, desc, start_dt, stop_dt)
        """
        # Use optimized EPG manager if available
        if self._epg_manager:
            return self._epg_manager.get_current_program(channel_id, norm_name)
        
        # Fallback to legacy implementation
        now = datetime.now(timezone.utc)
        target_id = channel_id
        
        if target_id not in self.epg_data and norm_name:
            target_id = self.epg_channels.get(norm_name)
        
        if not target_id or target_id not in self.epg_data:
            return None, None, None, None
        
        for prog in self.epg_data[target_id]:
            try:
                start_dt = self._parse_xmltv_date(prog['start'])
                stop_dt = self._parse_xmltv_date(prog['stop'])
                
                if start_dt and stop_dt and start_dt <= now <= stop_dt:
                    return prog['title'], prog['desc'], start_dt, stop_dt
            except:
                continue
        
        return "No Info Available", "", None, None

    def _parse_xmltv_date(self, date_str: str) -> Optional[datetime]:
        """Parse XMLTV date format."""
        try:
            return datetime.strptime(date_str, "%Y%m%d%H%M%S %z")
        except:
            return None

    def clear_epg_cache(self):
        """Clear the EPG cache."""
        if self._epg_manager:
            self._epg_manager.clear_cache()
            logging.info("EPG cache cleared")

    def get_epg_stats(self) -> Dict[str, int]:
        """Get EPG statistics."""
        return {
            'channels': len(self.epg_channels),
            'programs': sum(len(p) for p in self.epg_data.values()),
            'logos': len(self.logos_map)
        }
