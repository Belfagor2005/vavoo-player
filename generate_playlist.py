import os
import sys
import logging
import argparse

# Add the root directory to sys.path to allow imports from src
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.playlist_generator import PlaylistGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate Vavoo IPTV Playlist")
    parser.add_argument("--output", default="playlist.m3u8", help="Output path for the playlist")
    parser.add_argument("--epg-output", default=None, help="Output path for merged EPG (e.g. epg.xml)")
    parser.add_argument("--groups", nargs="+", default=["Italy"], help="Groups to include")
    
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

    success = True

    # Generate playlist
    logging.info(f"Starting playlist generation for groups: {args.groups}")
    gen = PlaylistGenerator()
    
    if not gen.generate_m3u8(args.output, groups=args.groups):
        logging.error("Failed to generate playlist.")
        success = False

    # Generate merged EPG
    if args.epg_output:
        logging.info(f"Starting EPG merge...")
        from src.epg_merger import merge_epg
        if not merge_epg(args.epg_output):
            logging.error("Failed to merge EPG.")
            success = False

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
