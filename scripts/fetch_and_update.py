import time
import logging
from read_emails import fetch_and_update

FETCH_INTERVAL_SECONDS = 600  # e.g. every 10 minutes

logging.basicConfig(level=logging.INFO)

def main_loop():
    while True:
        try:
            logging.info("Starting email fetch/update cycle...")
            fetch_and_update()
            logging.info("Cycle complete. Sleeping...")
        except Exception as e:
            logging.error(f"Error during fetch/update: {e}")
        time.sleep(FETCH_INTERVAL_SECONDS)

if __name__ == "__main__":
    main_loop()
