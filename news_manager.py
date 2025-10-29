#!/usr/bin/env python3
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class NewsEvent:
    def __init__(self, time_utc: datetime, country: str, title: str, impact: str, currency: str, forecast: Optional[float], actual: Optional[float]):
        self.time_utc = time_utc
        self.country = country
        self.title = title
        self.impact = impact  # e.g., high/medium/low
        self.currency = currency
        self.forecast = forecast
        self.actual = actual


class NewsManager:
    """
    Fetches economic calendars from TradingEconomics and Finnhub and provides
    a simple interface for event halts and surprise scoring.
    Only activates if API keys are available; otherwise, becomes a no-op.
    """

    def __init__(self) -> None:
        self.tradingeconomics_key = os.getenv("TRADINGECONOMICS_KEY", "")
        self.finnhub_key = os.getenv("FINNHUB_KEY", "")
        self.marketaux_key = os.getenv("MARKETAUX_KEY", "")  # reserved for sentiment (phase 2)
        self.newsapi_key = os.getenv("NEWSAPI_KEY", "")      # reserved for sentiment (phase 2)
        self.cached_events: List[NewsEvent] = []
        self.last_refresh: Optional[datetime] = None
        self.last_sentiment: Optional[Dict[str, Any]] = None
        self.last_sentiment_time: Optional[datetime] = None

    def is_enabled(self) -> bool:
        return bool(self.tradingeconomics_key or self.finnhub_key)

    def refresh_calendar(self) -> None:
        try:
            events: List[NewsEvent] = []
            now = datetime.utcnow()
            start = (now - timedelta(hours=1)).strftime('%Y-%m-%d')
            end = (now + timedelta(days=1)).strftime('%Y-%m-%d')

            # TradingEconomics
            if self.tradingeconomics_key:
                try:
                    te_url = f"https://api.tradingeconomics.com/calendar?d1={start}&d2={end}&format=json&c={self.tradingeconomics_key}"
                    r = requests.get(te_url, timeout=10)
                    if r.status_code == 200:
                        for e in r.json():
                            try:
                                t = datetime.strptime(e.get('Date', ''), '%Y-%m-%dT%H:%M:%S')
                                impact = (e.get('Importance', '') or '').lower()
                                events.append(
                                    NewsEvent(
                                        time_utc=t,
                                        country=e.get('Country', ''),
                                        title=e.get('Event', ''),
                                        impact=impact,
                                        currency=e.get('Currency', ''),
                                        forecast=self._to_float(e.get('Forecast')),
                                        actual=self._to_float(e.get('Actual')),
                                    )
                                )
                            except Exception:
                                continue
                except Exception as ex:
                    logger.warning(f"TradingEconomics calendar failed: {ex}")

            # Finnhub
            if self.finnhub_key:
                try:
                    fh_url = f"https://finnhub.io/api/v1/calendar/economic?from={start}&to={end}&token={self.finnhub_key}"
                    r = requests.get(fh_url, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        for e in data.get('economicCalendar', []):
                            try:
                                # Finnhub times are date strings with time; fallback noon UTC if missing
                                date_str = e.get('time', '') or f"{e.get('date','')} 12:00:00"
                                t = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                impact = (e.get('impact', '') or '').lower()
                                events.append(
                                    NewsEvent(
                                        time_utc=t,
                                        country=e.get('country', ''),
                                        title=e.get('event', ''),
                                        impact=impact,
                                        currency=e.get('currency', ''),
                                        forecast=self._to_float(e.get('estimate')),
                                        actual=self._to_float(e.get('actual')),
                                    )
                                )
                            except Exception:
                                continue
                except Exception as ex:
                    logger.warning(f"Finnhub calendar failed: {ex}")

            # Cache
            self.cached_events = sorted(events, key=lambda x: x.time_utc)
            self.last_refresh = datetime.utcnow()
        except Exception as e:
            logger.warning(f"Calendar refresh error: {e}")

    def get_upcoming_high_impact(self, within_minutes: int = 60) -> List[NewsEvent]:
        if not self.last_refresh or (datetime.utcnow() - self.last_refresh) > timedelta(minutes=10):
            self.refresh_calendar()
        now = datetime.utcnow()
        horizon = now + timedelta(minutes=within_minutes)
        return [e for e in self.cached_events if e.time_utc >= now and e.time_utc <= horizon and ('high' in e.impact or 'importance:high' in e.impact)]

    def surprise_score(self, event: NewsEvent) -> Optional[float]:
        if event.actual is None or event.forecast is None:
            return None
        try:
            # simple normalized surprise
            denom = max(1e-9, abs(event.forecast))
            return (event.actual - event.forecast) / denom
        except Exception:
            return None

    def fetch_sentiment(self, window_minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Aggregate sentiment over a short window using Marketaux and NewsAPI.
        Returns dict with avg_score, count, entity_hits per currency.
        """
        try:
            now = datetime.utcnow()
            if self.last_sentiment and self.last_sentiment_time and (now - self.last_sentiment_time) < timedelta(minutes=2):
                return self.last_sentiment

            since = (now - timedelta(minutes=window_minutes)).isoformat() + 'Z'
            total_score = 0.0
            total_count = 0
            entities: Dict[str, int] = { 'USD': 0, 'EUR': 0, 'GBP': 0, 'JPY': 0, 'XAU': 0 }

            # Marketaux
            if self.marketaux_key:
                try:
                    q = 'forex OR fx OR currency OR gold OR xau'
                    url = f"https://api.marketaux.com/v1/news/all?filter_entities=true&limit=25&published_after={since}&language=en&api_token={self.marketaux_key}&query={q}"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        for item in r.json().get('data', []):
                            s = item.get('sentiment_score')
                            if isinstance(s, (int, float)):
                                total_score += float(s)
                                total_count += 1
                            for ent in (item.get('entities') or []):
                                sym = (ent.get('symbol') or '').upper()
                                name = (ent.get('name') or '').upper()
                                text = f"{sym} {name}"
                                if 'USD' in text:
                                    entities['USD'] += 1
                                if 'EUR' in text:
                                    entities['EUR'] += 1
                                if 'GBP' in text:
                                    entities['GBP'] += 1
                                if 'JPY' in text:
                                    entities['JPY'] += 1
                                if 'GOLD' in text or 'XAU' in text:
                                    entities['XAU'] += 1
                except Exception as ex:
                    logger.warning(f"Marketaux sentiment failed: {ex}")

            # NewsAPI (headline only sentiment proxy via polarity words – minimal)
            if self.newsapi_key:
                try:
                    url = f"https://newsapi.org/v2/everything?q=forex%20OR%20currency%20OR%20gold&language=en&from={since}&pageSize=25&apiKey={self.newsapi_key}"
                    r = requests.get(url, timeout=10)
                    if r.status_code == 200:
                        for art in r.json().get('articles', []):
                            title = (art.get('title') or '') + ' ' + (art.get('description') or '')
                            title_u = title.upper()
                            # crude polarity proxy
                            neg = sum(1 for w in ['PLUNGE','SLUMP','SURGE IN CPI','HAWKISH','CUTS GROWTH'] if w in title_u)
                            pos = sum(1 for w in ['BEAT','COOLING','DOVISH','RISE IN JOBS','EXPANDS'] if w in title_u)
                            score = (pos - neg) * 0.1
                            if score != 0:
                                total_score += score
                                total_count += 1
                            if 'USD' in title_u:
                                entities['USD'] += 1
                            if 'EUR' in title_u:
                                entities['EUR'] += 1
                            if 'GBP' in title_u:
                                entities['GBP'] += 1
                            if 'JPY' in title_u:
                                entities['JPY'] += 1
                            if 'GOLD' in title_u or 'XAU' in title_u:
                                entities['XAU'] += 1
                except Exception as ex:
                    logger.warning(f"NewsAPI fetch failed: {ex}")

            avg = (total_score / max(1, total_count)) if total_count else 0.0
            out = { 'avg_score': avg, 'count': total_count, 'entities': entities }
            self.last_sentiment = out
            self.last_sentiment_time = now
            return out
        except Exception as e:
            logger.warning(f"fetch_sentiment error: {e}")
            return None

    @staticmethod
    def _to_float(val: Any) -> Optional[float]:
        try:
            if val is None:
                return None
            return float(str(val).replace('%',''))
        except Exception:
            return None

    @staticmethod
    def impacted_instruments(currency: str) -> List[str]:
        mapping = {
            'USD': ['EUR_USD', 'GBP_USD', 'XAU_USD', 'USD_JPY'],
            'EUR': ['EUR_USD'],
            'GBP': ['GBP_USD'],
            'JPY': ['USD_JPY'],
        }
        return mapping.get(currency.upper(), [])


