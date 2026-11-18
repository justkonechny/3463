import re, html, time
from google.transit import gtfs_realtime_pb2
from database import get_connection
from trips import fetch_feed, MACHINE

ALERTS_URL = f"https://data.calgary.ca/download/jhgn-ynqj/application%2Foctet-stream"

Effect = gtfs_realtime_pb2.Alert.Effect

update_alert = """
INSERT INTO alerts (alert_id, routes, effect, active_start, active_end,
                    description, first_seen, last_seen)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (alert_id) DO UPDATE SET
    routes       = excluded.routes,
    effect       = excluded.effect,
    active_start = excluded.active_start,
    active_end   = excluded.active_end,
    description  = excluded.description,
    last_seen    = excluded.last_seen
"""

update_poll = """
INSERT INTO polls (source, fetched_ts, machine, http_status, feed_ts,
                   entity_count, rows_written, error)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def get_text(translated):
    for t in translated.translation:
        if t.language in ("en", "en-CA", ""):
            return t.text
    return translated.translation[0].text if translated.translation else ""


def clean_html(raw):
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def get_effect(alert, raw_description):
    match = re.search(r'data-effect="(\w+)"', raw_description)
    if match:
        return match.group(1)
    name = Effect.Name(alert.effect)
    return None if name == "UNKNOWN_EFFECT" else name


def poll_alerts(conn):
    r, feed = fetch_feed(ALERTS_URL)
    feed_ts = feed.header.timestamp
    fetched_ts = int(time.time())

    rows = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        a = entity.alert

        routes = sorted({ie.route_id for ie in a.informed_entity if ie.route_id})

        starts = [p.start for p in a.active_period if p.start]
        ends = [p.end for p in a.active_period if p.end]

        raw_description = get_text(a.description_text)

        rows.append((
            entity.id,
            ",".join(routes),
            get_effect(a, raw_description),
            min(starts) if starts else None,
            max(ends) if ends else None,
            clean_html(raw_description),
            fetched_ts,
            fetched_ts,  
        ))

    conn.executemany(update_alert, rows)
    conn.execute(update_poll, ("alerts", fetched_ts, MACHINE, r.status_code,
                               feed_ts, len(feed.entity), len(rows), None))
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    conn = get_connection()
    print(poll_alerts(conn), "alerts written")
    conn.close()
