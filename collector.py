import time
from database import get_connection
from trips import poll_trips, MACHINE
from alerts import poll_alerts
from weather import poll_weather

pollers = {"trips": poll_trips, "alerts": poll_alerts, "weather": poll_weather}
intervals = {"trips": 30, "alerts":300, "weather":600}

def log_failure(conn, source, error):
    conn.rollback()
    conn.execute(
        "INSERT INTO polls (source, fetched_ts, machine, error) VALUES (?, ?, ?, ?)",
        (source, int(time.time()), MACHINE, repr(error)))
    conn.commit()

def main():
    conn = get_connection()
    next_run = {source:0 for source in pollers}
    try:
        while True:
            for source, poller in pollers.items():
                now = time.time()
                if now >= next_run[source]:
                    next_run[source] = now + intervals[source]
                    try:
                        n = poller(conn)
                        print(time.strftime("%H:%M:%S"), source, n, "rows")
                    except Exception as e:
                        print(time.strftime("%H:%M:%S"), source, "FAILED:", e)
                        log_failure(conn, source, e)
            time.sleep(5)
    except KeyboardInterrupt:
        print('stopping')
    finally:
        conn.close()
    

if __name__ == "__main__":
    main()