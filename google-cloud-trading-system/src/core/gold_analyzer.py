#!/usr/bin/env python3
"""
Gold Analyzer Module
Dedicated analysis module for Gold (XAU_USD) trading
Provides comprehensive Gold-specific insights and recommendations
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class GoldAnalyzer:
    """Dedicated Gold analysis and insights"""
    
    def __init__(self, data_feed=None, news_integration=None):
        self.data_feed = data_feed
        self.news_integration = news_integration
        self.gold_history = []
        self.support_resistance_levels = {}
        
    def get_comprehensive_gold_analysis(self, accounts: List[str]) -> Dict[str, Any]:
        """Get comprehensive Gold analysis"""
        try:
            analysis = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'current_data': self._get_current_gold_data(accounts),
                'technical_analysis': self._get_technical_analysis(accounts),
                'session_analysis': self._get_session_analysis(),
                'news_impact': self._get_news_impact(),
                'trading_recommendations': self._get_trading_recommendations(accounts),
                'risk_assessment': self._get_risk_assessment(accounts),
                'support_resistance': self._get_support_resistance_levels(accounts),
                'volatility_analysis': self._get_volatility_analysis(accounts),
                'momentum_indicators': self._get_momentum_indicators(accounts)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in comprehensive Gold analysis: {e}")
            return {'error': str(e)}
    
    def _get_current_gold_data(self, accounts: List[str]) -> Dict[str, Any]:
        """Get current Gold price data"""
        try:
            gold_data = {}
            
            if self.data_feed and accounts:
                for account_id in accounts:
                    try:
                        market_data = self.data_feed.get_market_data(account_id)
                        if market_data and 'XAU_USD' in market_data:
                            xau_data = market_data['XAU_USD']
                            gold_data = {
                                'current_price': (xau_data.bid + xau_data.ask) / 2,
                                'bid': xau_data.bid,
                                'ask': xau_data.ask,
                                'spread': xau_data.spread,
                                'timestamp': xau_data.timestamp,
                                'is_live': xau_data.is_live,
                                'volatility_score': getattr(xau_data, 'volatility_score', None)
                            }
                            break
                    except Exception:
                        continue
            
            return gold_data
            
        except Exception as e:
            logger.error(f"Error getting current Gold data: {e}")
            return {}
    
    def _get_technical_analysis(self, accounts: List[str]) -> Dict[str, Any]:
        """Get technical analysis for Gold"""
        try:
            current_data = self._get_current_gold_data(accounts)
            current_price = current_data.get('current_price', 0)
            
            if current_price == 0:
                return {'error': 'No Gold price data available'}
            
            # Simplified technical analysis (in practice, use proper indicators)
            analysis = {
                'trend': self._analyze_trend(current_price),
                'momentum': self._analyze_momentum(current_price),
                'support_levels': self._calculate_support_levels(current_price),
                'resistance_levels': self._calculate_resistance_levels(current_price),
                'fibonacci_levels': self._calculate_fibonacci_levels(current_price),
                'moving_averages': self._calculate_moving_averages(current_price),
                'rsi': self._calculate_rsi(current_price),  # Simplified
                'macd': self._calculate_macd(current_price)  # Simplified
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in technical analysis: {e}")
            return {'error': str(e)}
    
    def _get_session_analysis(self) -> Dict[str, Any]:
        """Analyze Gold trading session characteristics"""
        try:
            now_utc = datetime.now(timezone.utc)
            hour = now_utc.hour
            
            sessions = {
                'Asian': {'start': 0, 'end': 8, 'volatility': 0.6, 'liquidity': 'low'},
                'London': {'start': 8, 'end': 17, 'volatility': 1.2, 'liquidity': 'high'},
                'New York': {'start': 13, 'end': 22, 'volatility': 1.0, 'liquidity': 'high'},
                'Overlap': {'start': 13, 'end': 17, 'volatility': 1.5, 'liquidity': 'very_high'}
            }
            
            current_session = None
            for session_name, config in sessions.items():
                if config['start'] <= hour < config['end']:
                    current_session = session_name
                    break
            
            if not current_session:
                current_session = 'Closed'
            
            # Get session characteristics
            session_config = sessions.get(current_session, {})
            
            analysis = {
                'current_session': current_session,
                'volatility_multiplier': session_config.get('volatility', 1.0),
                'liquidity_level': session_config.get('liquidity', 'medium'),
                'trading_recommendation': self._get_session_recommendation(current_session),
                'next_session': self._get_next_session(hour),
                'session_transitions': self._get_session_transitions(hour)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in session analysis: {e}")
            return {'error': str(e)}
    
    def _get_news_impact(self) -> Dict[str, Any]:
        """Get Gold-specific news impact analysis"""
        try:
            if self.news_integration:
                # Get Gold-specific news
                gold_news = self.news_integration.get_gold_news()
                return self._analyze_news_impact(gold_news)
            else:
                # Fallback analysis
                return {
                    'overall_impact': 'neutral',
                    'key_factors': [
                        'USD strength/weakness',
                        'Inflation expectations',
                        'Fed monetary policy',
                        'Geopolitical tensions',
                        'Central bank gold purchases'
                    ],
                    'sentiment_score': 0.5,
                    'volatility_forecast': 'medium',
                    'key_events_today': [
                        'CPI data release',
                        'Fed official speech',
                        'Economic indicators'
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting news impact: {e}")
            return {'error': str(e)}
    
    def _get_trading_recommendations(self, accounts: List[str]) -> Dict[str, Any]:
        """Get Gold trading recommendations"""
        try:
            current_data = self._get_current_gold_data(accounts)
            technical_analysis = self._get_technical_analysis(accounts)
            session_analysis = self._get_session_analysis()
            news_impact = self._get_news_impact()
            
            # Combine all factors for recommendation
            recommendation = self._generate_trading_recommendation(
                current_data, technical_analysis, session_analysis, news_impact
            )
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting trading recommendations: {e}")
            return {'error': str(e)}
    
    def _get_risk_assessment(self, accounts: List[str]) -> Dict[str, Any]:
        """Get Gold-specific risk assessment"""
        try:
            current_data = self._get_current_gold_data(accounts)
            volatility = current_data.get('volatility_score', 0.5)
            spread = current_data.get('spread', 0)
            
            risk_factors = []
            risk_level = 'medium'
            
            # Volatility risk
            if volatility > 0.8:
                risk_factors.append('High volatility detected')
                risk_level = 'high'
            elif volatility < 0.3:
                risk_factors.append('Low volatility - limited opportunities')
                risk_level = 'low'
            
            # Spread risk
            if spread > 0.5:  # 50 cents spread
                risk_factors.append('Wide spread - reduced profitability')
                risk_level = 'high' if risk_level == 'medium' else risk_level
            
            # Session risk
            session_analysis = self._get_session_analysis()
            if session_analysis.get('liquidity_level') == 'low':
                risk_factors.append('Low liquidity session')
                risk_level = 'high' if risk_level == 'medium' else risk_level
            
            # News risk
            news_impact = self._get_news_impact()
            if news_impact.get('volatility_forecast') == 'high':
                risk_factors.append('High news volatility expected')
                risk_level = 'high' if risk_level == 'medium' else risk_level
            
            return {
                'overall_risk': risk_level,
                'risk_factors': risk_factors,
                'recommended_position_size': self._get_recommended_position_size(risk_level),
                'stop_loss_suggestion': self._get_stop_loss_suggestion(volatility),
                'take_profit_suggestion': self._get_take_profit_suggestion(volatility)
            }
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            return {'error': str(e)}
    
    def _get_support_resistance_levels(self, accounts: List[str]) -> Dict[str, Any]:
        """Get support and resistance levels for Gold"""
        try:
            current_data = self._get_current_gold_data(accounts)
            current_price = current_data.get('current_price', 0)
            
            if current_price == 0:
                return {'error': 'No price data available'}
            
            # Calculate key levels
            levels = {
                'current_price': current_price,
                'support_levels': self._calculate_support_levels(current_price),
                'resistance_levels': self._calculate_resistance_levels(current_price),
                'psychological_levels': self._get_psychological_levels(current_price),
                'fibonacci_levels': self._calculate_fibonacci_levels(current_price),
                'pivot_points': self._calculate_pivot_points(current_price)
            }
            
            return levels
            
        except Exception as e:
            logger.error(f"Error getting support/resistance levels: {e}")
            return {'error': str(e)}
    
    def _get_volatility_analysis(self, accounts: List[str]) -> Dict[str, Any]:
        """Get Gold volatility analysis"""
        try:
            current_data = self._get_current_gold_data(accounts)
            volatility = current_data.get('volatility_score', 0.5)
            
            analysis = {
                'current_volatility': volatility,
                'volatility_level': self._classify_volatility(volatility),
                'volatility_trend': 'stable',  # Would need historical data
                'expected_range': self._calculate_expected_range(current_data.get('current_price', 0), volatility),
                'volatility_forecast': self._forecast_volatility(),
                'trading_implications': self._get_volatility_implications(volatility)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in volatility analysis: {e}")
            return {'error': str(e)}
    
    def _get_momentum_indicators(self, accounts: List[str]) -> Dict[str, Any]:
        """Get momentum indicators for Gold"""
        try:
            current_data = self._get_current_gold_data(accounts)
            current_price = current_data.get('current_price', 0)
            
            if current_price == 0:
                return {'error': 'No price data available'}
            
            indicators = {
                'rsi': self._calculate_rsi(current_price),
                'macd': self._calculate_macd(current_price),
                'stochastic': self._calculate_stochastic(current_price),
                'momentum': self._calculate_momentum(current_price),
                'rate_of_change': self._calculate_rate_of_change(current_price),
                'trend_strength': self._calculate_trend_strength(current_price)
            }
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error getting momentum indicators: {e}")
            return {'error': str(e)}
    
    # Helper methods for technical analysis
    def _analyze_trend(self, price: float) -> str:
        """Analyze Gold trend (simplified)"""
        # In practice, this would use moving averages, trend lines, etc.
        return 'neutral'
    
    def _analyze_momentum(self, price: float) -> str:
        """Analyze Gold momentum"""
        # In practice, this would use momentum indicators
        return 'neutral'
    
    def _calculate_support_levels(self, price: float) -> List[float]:
        """Calculate support levels"""
        return [
            price * 0.995,  # 0.5% below
            price * 0.990,  # 1% below
            price * 0.985,  # 1.5% below
            price * 0.980   # 2% below
        ]
    
    def _calculate_resistance_levels(self, price: float) -> List[float]:
        """Calculate resistance levels"""
        return [
            price * 1.005,  # 0.5% above
            price * 1.010,  # 1% above
            price * 1.015,  # 1.5% above
            price * 1.020   # 2% above
        ]
    
    def _calculate_fibonacci_levels(self, price: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        return {
            '23.6%': price * 0.764,
            '38.2%': price * 0.618,
            '50%': price * 0.5,
            '61.8%': price * 0.382,
            '78.6%': price * 0.214
        }
    
    def _calculate_moving_averages(self, price: float) -> Dict[str, float]:
        """Calculate moving averages (simplified)"""
        return {
            'SMA_20': price * 0.998,  # Simplified
            'SMA_50': price * 0.995,
            'SMA_200': price * 0.990
        }
    
    def _calculate_rsi(self, price: float) -> float:
        """Calculate RSI (simplified)"""
        # In practice, this would use actual RSI calculation
        return 50.0  # Neutral RSI
    
    def _calculate_macd(self, price: float) -> Dict[str, float]:
        """Calculate MACD (simplified)"""
        return {
            'macd_line': 0.0,
            'signal_line': 0.0,
            'histogram': 0.0
        }
    
    def _get_session_recommendation(self, session: str) -> str:
        """Get trading recommendation based on session"""
        recommendations = {
            'Asian': 'Low activity - monitor for breakouts',
            'London': 'High activity - best trading opportunities',
            'New York': 'Good liquidity - trend continuation likely',
            'Overlap': 'Maximum volatility - high opportunity, high risk',
            'Closed': 'Market closed - prepare for next session'
        }
        return recommendations.get(session, 'Monitor market conditions')
    
    def _get_next_session(self, current_hour: int) -> str:
        """Get next trading session"""
        if current_hour < 8:
            return 'London (8:00 UTC)'
        elif current_hour < 13:
            return 'New York (13:00 UTC)'
        else:
            return 'London (Tomorrow 8:00 UTC)'
    
    def _get_session_transitions(self, current_hour: int) -> List[Dict[str, Any]]:
        """Get upcoming session transitions"""
        transitions = []
        
        if current_hour < 8:
            transitions.append({
                'session': 'London',
                'time': '8:00 UTC',
                'impact': 'high',
                'description': 'London session opens - increased volatility expected'
            })
        
        if current_hour < 13:
            transitions.append({
                'session': 'New York',
                'time': '13:00 UTC',
                'impact': 'medium',
                'description': 'New York session opens - good liquidity'
            })
        
        return transitions
    
    def _analyze_news_impact(self, news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze news impact on Gold"""
        # Simplified news impact analysis
        return {
            'overall_impact': 'neutral',
            'sentiment_score': 0.5,
            'key_factors': ['USD strength', 'Inflation data'],
            'volatility_forecast': 'medium'
        }
    
    def _generate_trading_recommendation(self, current_data: Dict, technical: Dict, 
                                       session: Dict, news: Dict) -> Dict[str, Any]:
        """Generate comprehensive trading recommendation"""
        try:
            recommendation = {
                'overall_signal': 'neutral',
                'confidence': 0.5,
                'entry_strategy': 'wait',
                'risk_level': 'medium',
                'timeframe': '1-4 hours',
                'reasoning': [],
                'key_levels': {
                    'entry': current_data.get('current_price', 0),
                    'stop_loss': 0,
                    'take_profit': 0
                }
            }
            
            # Combine all factors
            factors = []
            
            # Technical factors
            if technical.get('trend') == 'bullish':
                factors.append('Technical trend is bullish')
                recommendation['confidence'] += 0.1
            
            # Session factors
            if session.get('liquidity_level') == 'high':
                factors.append('High liquidity session')
                recommendation['confidence'] += 0.1
            
            # News factors
            if news.get('sentiment_score', 0.5) > 0.6:
                factors.append('Positive news sentiment')
                recommendation['confidence'] += 0.1
            
            recommendation['reasoning'] = factors
            recommendation['confidence'] = min(recommendation['confidence'], 1.0)
            
            # Determine overall signal
            if recommendation['confidence'] > 0.7:
                recommendation['overall_signal'] = 'strong_buy'
            elif recommendation['confidence'] > 0.6:
                recommendation['overall_signal'] = 'buy'
            elif recommendation['confidence'] < 0.3:
                recommendation['overall_signal'] = 'sell'
            else:
                recommendation['overall_signal'] = 'neutral'
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating trading recommendation: {e}")
            return {'error': str(e)}
    
    def _get_recommended_position_size(self, risk_level: str) -> str:
        """Get recommended position size based on risk level"""
        sizes = {
            'low': 'Standard position size',
            'medium': 'Reduced position size',
            'high': 'Minimal position size or avoid'
        }
        return sizes.get(risk_level, 'Standard position size')
    
    def _get_stop_loss_suggestion(self, volatility: float) -> str:
        """Get stop loss suggestion based on volatility"""
        if volatility > 0.8:
            return 'Wider stop loss (15-20 pips) due to high volatility'
        elif volatility < 0.3:
            return 'Tighter stop loss (8-12 pips) due to low volatility'
        else:
            return 'Standard stop loss (10-15 pips)'
    
    def _get_take_profit_suggestion(self, volatility: float) -> str:
        """Get take profit suggestion based on volatility"""
        if volatility > 0.8:
            return 'Higher take profit targets (20-30 pips) due to high volatility'
        elif volatility < 0.3:
            return 'Lower take profit targets (8-15 pips) due to low volatility'
        else:
            return 'Standard take profit targets (15-20 pips)'
    
    def _get_psychological_levels(self, price: float) -> List[float]:
        """Get psychological price levels"""
        # Round numbers that traders watch
        base = int(price)
        return [
            base,
            base + 10,
            base + 20,
            base + 50,
            base + 100
        ]
    
    def _calculate_pivot_points(self, price: float) -> Dict[str, float]:
        """Calculate pivot points"""
        # Simplified pivot point calculation
        return {
            'pivot': price,
            'r1': price * 1.01,
            'r2': price * 1.02,
            's1': price * 0.99,
            's2': price * 0.98
        }
    
    def _classify_volatility(self, volatility: float) -> str:
        """Classify volatility level"""
        if volatility > 0.8:
            return 'high'
        elif volatility > 0.5:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_expected_range(self, price: float, volatility: float) -> Dict[str, float]:
        """Calculate expected price range"""
        range_multiplier = volatility * 0.02  # 2% base range
        return {
            'upper': price * (1 + range_multiplier),
            'lower': price * (1 - range_multiplier),
            'range': price * range_multiplier * 2
        }
    
    def _forecast_volatility(self) -> str:
        """Forecast volatility (simplified)"""
        return 'medium'
    
    def _get_volatility_implications(self, volatility: float) -> List[str]:
        """Get trading implications of volatility"""
        implications = []
        
        if volatility > 0.8:
            implications.extend([
                'High volatility - use wider stops',
                'Higher profit potential but higher risk',
                'Consider shorter timeframes'
            ])
        elif volatility < 0.3:
            implications.extend([
                'Low volatility - limited opportunities',
                'May need to wait for breakout',
                'Consider longer timeframes'
            ])
        else:
            implications.extend([
                'Normal volatility - standard approach',
                'Good balance of risk and opportunity'
            ])
        
        return implications
    
    def _calculate_stochastic(self, price: float) -> Dict[str, float]:
        """Calculate stochastic oscillator (simplified)"""
        return {
            'k_percent': 50.0,
            'd_percent': 50.0
        }
    
    def _calculate_momentum(self, price: float) -> float:
        """Calculate momentum (simplified)"""
        return 0.0
    
    def _calculate_rate_of_change(self, price: float) -> float:
        """Calculate rate of change (simplified)"""
        return 0.0
    
    def _calculate_trend_strength(self, price: float) -> str:
        """Calculate trend strength (simplified)"""
        return 'neutral'
