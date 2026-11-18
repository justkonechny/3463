import time
import requests
from google.transit import gtfs_realtime_pb2
from database import get_connection

ROUTES = {'306'}
MACHINE = 'justin-mac'

TRIPS_URL = f"https://data.calgary.ca/download/gs4m-mdc2/application%2Foctet-stream"

Status = gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship

update_trip = """
INSERT INTO trips (start_date, trip_id, stop_sequence, route_id, stop_id, predicted_ts, trip_status, feed_ts, fetched_ts)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (start_date, trip_id, stop_sequence) DO UPDATE SET
    predicted_ts = excluded.predicted_ts,
    trip_status = excluded.trip_status,
    feed_ts = excluded.feed_ts,
    fetched_ts = excluded.fetched_ts
"""

update_poll = """
INSERT INTO polls (source, fetched_ts, machine, http_status, feed_ts,
                   entity_count, rows_written, error)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

def poll_trips(conn):
    fetched_ts = int(time.time())
    service_date = time.strftime("%Y%m%d", time.localtime(fetched_ts - 4 * 3600))
    r = requests.get(TRIPS_URL, timeout=30)
    r.raise_for_status()
    
    feed = gtfs_realtime_pb2.FeedMessage() 
    feed.ParseFromString(r.content)
    feed_ts = feed.header.timestamp

    rows = []
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue

        tu = entity.trip_update

        if tu.trip.route_id not in ROUTES:
            continue
    
        status = Status.Name(tu.trip.schedule_relationship)


        for stu in tu.stop_time_update:
            predicted = stu.arrival.time if stu.arrival.time > 0 else stu.departure.time
            start_date = tu.trip.start_date or service_date
            if predicted <= 0:
                continue
            rows.append((
                start_date,
                tu.trip.trip_id,
                stu.stop_sequence,
                tu.trip.route_id,
                stu.stop_id,
                predicted,
                status,
                feed_ts,
                fetched_ts
            ))
    conn.executemany(update_trip, rows)
    conn.execute(update_poll, ("trips", fetched_ts, MACHINE, r.status_code, feed_ts, len(feed.entity), len(rows), None))
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    conn = get_connection()
    print(poll_trips(conn), "rows written")
    conn.close()