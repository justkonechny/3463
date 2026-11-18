import calendar, time
import requests
import feedparser
from database import get_connection
from trips import MACHINE

WEATHER_URL = "https://weather.gc.ca/rss/battleboard/ab12_e.xml"   # City of Calgary

update_weather = """
INSERT INTO weather (entry_id, title, warning_type, published, updated,
                     first_seen, last_seen)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (entry_id) DO UPDATE SET
    title        = excluded.title,
    warning_type = excluded.warning_type,
    updated      = excluded.updated,
    last_seen    = excluded.last_seen
"""

update_poll = """
INSERT INTO polls (source, fetched_ts, machine, http_status, feed_ts,
                   entity_count, rows_written, error)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def to_unix(parsed_time):
    """feedparser gives times as UTC struct_time; convert to Unix seconds."""
    return calendar.timegm(parsed_time) if parsed_time else None


def poll_weather(conn):
    r = requests.get(WEATHER_URL, timeout=30)
    r.raise_for_status()
    fetched_ts = int(time.time())

    feed = feedparser.parse(r.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"could not parse weather feed: {feed.bozo_exception}")

    feed_ts = to_unix(feed.feed.get("updated_parsed"))

    rows = []
    for entry in feed.entries:
        title = entry.get("title", "")

        # When nothing is active the feed has a placeholder entry such as
        # "No watches or warnings in effect, City of Calgary". Skip it; the
        # poll is still logged, which records that no warning was active.
        if title.lower().startswith("no "):
            continue

        # "YELLOW WARNING - SNOWFALL, City of Calgary" -> "YELLOW WARNING - SNOWFALL"
        warning_type = title.split(",")[0].strip()

        rows.append((
            entry.get("id", title),
            title,
            warning_type,
            to_unix(entry.get("published_parsed")),
            to_unix(entry.get("updated_parsed")),
            fetched_ts,   # first_seen
            fetched_ts,   # last_seen
        ))

    conn.executemany(update_weather, rows)
    conn.execute(update_poll, ("weather", fetched_ts, MACHINE, r.status_code,
                               feed_ts, len(feed.entries), len(rows), None))
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    conn = get_connection()
    print(poll_weather(conn), "warnings written")
    conn.close()
