import time
from src.core.candle_based_scanner import get_candle_scanner
from src.core.optimized_telegram import get_optimized_telegram

scanner = get_candle_scanner()
notif = get_optimized_telegram()

scanner.start_scanning()
print("Scanner started. Press Ctrl+C to stop.")
try:
    while True:
        time.sleep(5)
except KeyboardInterrupt:
    pass
