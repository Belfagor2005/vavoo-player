#!/usr/bin/env python3
import gzip
import requests
import xml.etree.ElementTree as ET
from io import BytesIO
import sys


def download_and_parse(url):
    """Download gzipped XML, decompress and parse."""
    print(f"Downloading {url}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        raise
    with gzip.open(BytesIO(resp.content), 'rt', encoding='utf-8') as f:
        return ET.parse(f)

def merge_xml_files(urls, output_xml, output_gz):
    """Merge multiple XMLTV files, deduplicate channels by id."""
    tv = ET.Element('tv')
    channels_dict = {}   # id -> element
    programmes = []

    for url in urls:
        tree = download_and_parse(url)
        root = tree.getroot()
        # Keep first occurrence of each channel
        for ch in root.findall('channel'):
            ch_id = ch.get('id')
            if ch_id and ch_id not in channels_dict:
                channels_dict[ch_id] = ch
        programmes.extend(root.findall('programme'))

    # Add channels to tv element
    for ch in channels_dict.values():
        tv.append(ch)
    for prog in programmes:
        tv.append(prog)

    # Convert the whole tree to a bytes string
    xml_bytes = ET.tostring(tv, encoding='utf-8', xml_declaration=True)

    # Write uncompressed file
    with open(output_xml, 'wb') as f:
        f.write(xml_bytes)
    print(f"Saved merged XML to {output_xml}")

    # Write compressed file
    with gzip.open(output_gz, 'wb') as f:
        f.write(xml_bytes)
    print(f"Saved compressed GZ to {output_gz}")


if __name__ == '__main__':
    urls = [
        "https://epgshare01.online/epgshare01/epg_ripper_BA1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_HR1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_RS1.xml.gz"
    ]
    merge_xml_files(urls, 'epg_bk.xml', 'epg_bk.xml.gz')

if __name__ == '__main__':
    urls = [
        "https://epgshare01.online/epgshare01/epg_ripper_BA1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_HR1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_RS1.xml.gz"
    ]
    merge_xml_files(urls, 'epg_bk.xml', 'epg_bk.xml.gz')
