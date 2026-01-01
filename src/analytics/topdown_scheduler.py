import logging
import schedule
import time
import threading
from datetime import datetime
from pytz import timezone

# Assuming these components exist based on the guide and previous context
from .topdown_analysis import get_topdown_analyzer
from ..core.telegram_notifier import get_telegram_notifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopDownScheduler:
    """
    Automated scheduler for the Top-Down Analysis Framework.
    Generates and sends reports via Telegram.
    """
    def __init__(self, analyzer, telegram_sender, london_tz):
        self.analyzer = analyzer
        self.telegram_sender = telegram_sender
        self.london_tz = london_tz
        self.setup_schedule()
        logger.info("✅ TopDownScheduler initialized.")

    def setup_schedule(self):
        """Sets up the schedule for automated report generation."""
        # Monthly Outlook: First Sunday of the month at 9:00 AM London time
        schedule.every().sunday.at("09:00").do(self._send_monthly_outlook_if_first_sunday)
        
        # Weekly Breakdown: Every Sunday at 8:00 AM London time
        schedule.every().sunday.at("08:00").do(self.send_weekly_breakdown)
        
        # Mid-Week Update: Every Wednesday at 7:00 AM London time
        schedule.every().wednesday.at("07:00").do(self.send_midweek_update)
        
        logger.info("✅ Top-Down Analysis schedule configured.")

    def _send_monthly_outlook_if_first_sunday(self):
        """Checks if it's the first Sunday of the month before sending."""
        now_london = datetime.now(self.london_tz)
        if 1 <= now_london.day <= 7:
            logger.info("🚀 Triggering Monthly Outlook (first Sunday of the month).")
            self.send_monthly_outlook()

    def send_report(self, timeframe: str):
        """Generates and sends a report for a given timeframe."""
        logger.info(f"📊 Generating {timeframe.upper()} report...")
        try:
            report_data = self.analyzer.generate_report(timeframe)
            if not report_data or "analysis" not in report_data or not report_data["analysis"]:
                logger.warning(f"⚠️ Report generation for {timeframe} yielded no data.")
                return
                
            message = self.analyzer.format_report_for_telegram(report_data)
            self.telegram_sender.send_message(message)
            logger.info(f"✅ {timeframe.upper()} report sent to Telegram.")
        except Exception as e:
            logger.error(f"❌ Failed to send {timeframe} report: {e}")

    def send_monthly_outlook(self):
        self.send_report("monthly")

    def send_weekly_breakdown(self):
        self.send_report("weekly")
        
    def send_midweek_update(self):
        # Mid-week is a lighter report, we can adjust the timeframe name if needed
        report_data = self.analyzer.generate_report("weekly") # re-use weekly for sentiment
        report_data["timeframe"] = "MID-WEEK"
        message = self.analyzer.format_report_for_telegram(report_data)
        self.telegram_sender.send_message(message)
        logger.info(f"✅ MID-WEEK report sent to Telegram.")

    def send_on_demand(self, period: str):
        """Sends a report on-demand based on a user command."""
        logger.info(f"📲 Received on-demand request for '{period}' analysis.")
        if period == "monthly":
            self.send_monthly_outlook()
        elif period == "weekly":
            self.send_weekly_breakdown()
        elif period == "midweek":
            self.send_midweek_update()
        else:
            self.telegram_sender.send_message(f"⚠️ Invalid analysis period: '{period}'. Use 'monthly', 'weekly', or 'midweek'.")

    def run_scheduler(self):
        """Runs the scheduler loop in a background thread."""
        logger.info("✅ Top-Down Scheduler is running in the background.")
        while True:
            schedule.run_pending()
            time.sleep(60) # Check every minute

def integrate_with_trading_system(trading_systems):
    """
    Factory function to create and integrate the scheduler with the main system.
    """
    from ..core.oanda_client import get_oanda_client
    
    # Dependencies
    oanda_client = get_oanda_client()
    analyzer = get_topdown_analyzer(oanda_client=oanda_client)
    telegram_sender = get_telegram_notifier()
    london_tz = timezone('Europe/London')

    # Create scheduler instance
    scheduler = TopDownScheduler(analyzer, telegram_sender, london_tz)

    # You could pass the scheduler to trading systems if they need to access it
    # for system in trading_systems:
    #     system.set_scheduler(scheduler)
        
    return scheduler
