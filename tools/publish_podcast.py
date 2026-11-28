#!/usr/bin/env python3
"""Publish Market Briefing audio episodes to the GitHub Pages podcast feed.

Usage:
    python3 tools/publish_podcast.py <repo_dir> <audio.m4a> [<audio.m4a> ...]

Each audio file must be named "Market Briefing YYYY.MM.DD (Audio).m4a".
Copies new episodes into episodes/ as YYYY-MM-DD.m4a, keeps only the KEEP
most recent, rewrites feed.xml and index.html. Committing is done by the
caller (orphan single commit + force push keeps the repo small).
"""
import datetime as dt
import email.utils
import html
import json
import os
import re
import shutil
import subprocess
import sys

KEEP = 10
BASE = "https://mortagonus.github.io/briefing-podcast"
TITLE = "Market Briefing (Audio)"
AUTHOR = "Eric Areiter"
DESC = ("Eric's daily Market Briefing as a two-host audio deep dive: the session, "
        "movers, earnings, research and sections. Private feed.")
NAME_RE = re.compile(r"Market Briefing (\d{4})\.(\d{2})\.(\d{2}) \(Audio\)\.m4a$")


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return int(float(json.loads(out)["format"]["duration"]))


def hms(sec):
    return f"{sec // 3600:d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def main():
    repo, files = sys.argv[1], sys.argv[2:]
    ep_dir = os.path.join(repo, "episodes")
    os.makedirs(ep_dir, exist_ok=True)
    for f in files:
        m = NAME_RE.search(os.path.basename(f))
        if not m:
            sys.exit(f"bad name: {f}")
        shutil.copyfile(f, os.path.join(ep_dir, f"{m[1]}-{m[2]}-{m[3]}.m4a"))

    eps = sorted(e for e in os.listdir(ep_dir) if re.match(r"\d{4}-\d{2}-\d{2}\.m4a$", e))
    for old in eps[:-KEEP]:
        os.remove(os.path.join(ep_dir, old))
    eps = eps[-KEEP:]

    items, rows = [], []
    for e in reversed(eps):
        p = os.path.join(ep_dir, e)
        d = dt.date.fromisoformat(e[:10])
        # publish time: 4:30 PM Pacific on the edition date (stable, ordered)
        pub = dt.datetime(d.year, d.month, d.day, 16, 30,
                          tzinfo=dt.timezone(dt.timedelta(hours=-8)))
        title = f"Market Briefing — {d.strftime('%a %b')} {d.day}, {d.year}"
        url = f"{BASE}/episodes/{e}"
        secs = duration(p)
        items.append(f"""    <item>
      <title>{html.escape(title)}</title>
      <description>{html.escape('Audio edition of the ' + d.strftime('%Y.%m.%d') + ' Market Briefing.')}</description>
      <enclosure url="{url}" length="{os.path.getsize(p)}" type="audio/x-m4a"/>
      <guid isPermaLink="false">market-briefing-{e[:10]}</guid>
      <pubDate>{email.utils.format_datetime(pub)}</pubDate>
      <itunes:duration>{hms(secs)}</itunes:duration>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
    </item>""")
        rows.append(f'<li><a href="episodes/{e}">{html.escape(title)}</a> · {hms(secs)}</li>')

    now = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{TITLE}</title>
    <link>{BASE}/</link>
    <atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>en-us</language>
    <description>{html.escape(DESC)}</description>
    <lastBuildDate>{now}</lastBuildDate>
    <itunes:author>{AUTHOR}</itunes:author>
    <itunes:summary>{html.escape(DESC)}</itunes:summary>
    <itunes:image href="{BASE}/cover.jpg"/>
    <itunes:category text="Business"><itunes:category text="Investing"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:block>Yes</itunes:block>
    <itunes:owner><itunes:name>{AUTHOR}</itunes:name></itunes:owner>
{chr(10).join(items)}
  </channel>
</rss>
"""
    with open(os.path.join(repo, "feed.xml"), "w") as fh:
        fh.write(feed)
    with open(os.path.join(repo, "index.html"), "w") as fh:
        fh.write(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow"><title>{TITLE}</title></head>
<body style="font-family:system-ui;max-width:640px;margin:40px auto">
<h1>{TITLE}</h1><p>Feed: <a href="feed.xml">{BASE}/feed.xml</a></p>
<ul>{''.join(rows)}</ul></body></html>
""")
    with open(os.path.join(repo, "robots.txt"), "w") as fh:
        fh.write("User-agent: *\nDisallow: /\n")
    open(os.path.join(repo, ".nojekyll"), "w").close()
    print("episodes:", ", ".join(eps))


if __name__ == "__main__":
    main()
