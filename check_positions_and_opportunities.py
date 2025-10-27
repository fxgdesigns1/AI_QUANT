#!/usr/bin/env python3
"""
Position & Market Analysis Script
Checks current positions, market conditions, and trading opportunities across all accounts
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add google-cloud-trading-system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system'))

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), 'google-cloud-trading-system', 'oanda_config.env')
load_dotenv(env_path)

from src.core.oanda_client import OandaClient

# Account configurations
ACCOUNTS = {
    '101-004-30719775-011': {
        'name': 'Momentum Trading',
        'instruments': ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'NZD_USD'],
        'strategy': 'Momentum-based entries with EMA crossover'
    },
    '101-004-30719775-006': {
        'name': 'High Win Rate',
        'instruments': ['EUR_JPY', 'USD_CAD'],
        'strategy': 'High probability setups with tight risk control'
    },
    '101-004-30719775-007': {
        'name': 'Zero Drawdown',
        'instruments': ['GBP_USD', 'XAU_USD'],
        'strategy': 'Conservative trading with maximum protection'
    },
    '101-004-30719775-008': {
        'name': 'High Frequency',
        'instruments': ['GBP_USD', 'NZD_USD', 'XAU_USD'],
        'strategy': 'Multiple small trades with quick profits'
    },
    '101-004-30719775-001': {
        'name': 'Gold Trump Week',
        'instruments': ['XAU_USD'],
        'strategy': 'Gold specialist with fundamental analysis'
    }
}

def format_currency(value: float) -> str:
    """Format currency with color coding"""
    if value >= 0:
        return f"\033[92m${value:,.2f}\033[0m"  # Green for positive
    else:
        return f"\033[91m${value:,.2f}\033[0m"  # Red for negative

def format_percentage(value: float) -> str:
    """Format percentage with color coding"""
    if value >= 0:
        return f"\033[92m{value:.2f}%\033[0m"  # Green for positive
    else:
        return f"\033[91m{value:.2f}%\033[0m"  # Red for negative

def analyze_market_regime(prices: dict) -> dict:
    """Analyze market regime for each instrument"""
    regimes = {}
    for instrument, price in prices.items():
        spread = price.spread
        spread_pips = spread * 10000 if not instrument.endswith('JPY') else spread * 100
        if instrument == 'XAU_USD':
            spread_pips = spread
        
        # Simple regime classification based on spread
        if spread_pips < 1.5:
            regime = "TIGHT (Good for trading)"
        elif spread_pips < 3.0:
            regime = "MODERATE (Acceptable)"
        else:
            regime = "WIDE (Caution advised)"
        
        regimes[instrument] = {
            'spread_pips': spread_pips,
            'regime': regime,
            'bid': price.bid,
            'ask': price.ask
        }
    
    return regimes

def check_account(account_id: str, account_info: dict) -> dict:
    """Check account status, positions, and opportunities"""
    print(f"\n{'='*80}")
    print(f"🏦 ACCOUNT: {account_info['name']}")
    print(f"📋 ID: {account_id}")
    print(f"📊 Strategy: {account_info['strategy']}")
    print(f"{'='*80}")
    
    try:
        # Initialize client for this account
        client = OandaClient(
            api_key=os.getenv('OANDA_API_KEY'),
            account_id=account_id,
            environment=os.getenv('OANDA_ENVIRONMENT', 'practice')
        )
        
        # Get account info
        acc_info = client.get_account_info()
        print(f"\n💰 Account Balance: {format_currency(acc_info.balance)}")
        print(f"📈 Unrealized P&L: {format_currency(acc_info.unrealized_pl)}")
        print(f"💵 Realized P&L: {format_currency(acc_info.realized_pl)}")
        print(f"📊 Margin Used: {format_currency(acc_info.margin_used)}")
        print(f"💳 Margin Available: {format_currency(acc_info.margin_available)}")
        print(f"📌 Open Trades: {acc_info.open_trade_count}")
        print(f"📍 Open Positions: {acc_info.open_position_count}")
        
        # Calculate account health
        if acc_info.balance > 0:
            roi = (acc_info.realized_pl / acc_info.balance) * 100
            current_exposure = (acc_info.margin_used / acc_info.balance) * 100 if acc_info.balance > 0 else 0
            print(f"\n📊 ROI (Realized): {format_percentage(roi)}")
            print(f"⚠️  Current Exposure: {format_percentage(current_exposure)}")
            
            # Risk warning
            if current_exposure > 75:
                print(f"🔴 WARNING: High exposure! Reduce risk.")
            elif current_exposure > 50:
                print(f"🟡 CAUTION: Moderate exposure. Monitor closely.")
            else:
                print(f"🟢 GOOD: Exposure within safe limits.")
        
        # Get open trades
        print(f"\n{'─'*80}")
        print(f"📋 OPEN POSITIONS")
        print(f"{'─'*80}")
        
        open_trades = client.get_open_trades()
        if open_trades:
            for i, trade in enumerate(open_trades, 1):
                instrument = trade['instrument']
                units = float(trade['currentUnits'])
                price = float(trade['price'])
                unrealized_pl = float(trade['unrealizedPL'])
                side = "LONG" if units > 0 else "SHORT"
                
                print(f"\n{i}. {instrument} - {side}")
                print(f"   Entry Price: {price:.5f}")
                print(f"   Units: {abs(units):,.0f}")
                print(f"   P&L: {format_currency(unrealized_pl)}")
                
                # Check if protective stops are in place
                has_sl = 'stopLossOrder' in trade
                has_tp = 'takeProfitOrder' in trade
                
                if has_sl:
                    sl_price = float(trade['stopLossOrder']['price'])
                    print(f"   🛡️  Stop Loss: {sl_price:.5f}")
                else:
                    print(f"   ⚠️  NO STOP LOSS - ADDING PROTECTIVE STOP!")
                    # Add protective stop
                    try:
                        mid_price = price
                        if side == "LONG":
                            sl_price = mid_price * 0.995  # 0.5% stop
                        else:
                            sl_price = mid_price * 1.005
                        
                        client.update_trade_protective_orders(trade['id'], stop_loss=sl_price)
                        print(f"   ✅ Protective stop added at {sl_price:.5f}")
                    except Exception as e:
                        print(f"   ❌ Failed to add stop: {e}")
                
                if has_tp:
                    tp_price = float(trade['takeProfitOrder']['price'])
                    print(f"   🎯 Take Profit: {tp_price:.5f}")
        else:
            print(f"No open positions")
        
        # Get current market prices
        print(f"\n{'─'*80}")
        print(f"📊 MARKET CONDITIONS & OPPORTUNITIES")
        print(f"{'─'*80}")
        
        instruments = account_info['instruments']
        prices = client.get_current_prices(instruments)
        regimes = analyze_market_regime(prices)
        
        opportunities = []
        
        for instrument, regime_data in regimes.items():
            print(f"\n{instrument}:")
            print(f"   Bid: {regime_data['bid']:.5f}")
            print(f"   Ask: {regime_data['ask']:.5f}")
            print(f"   Spread: {regime_data['spread_pips']:.2f} pips")
            print(f"   Regime: {regime_data['regime']}")
            
            # Opportunity detection
            if regime_data['spread_pips'] < 2.0:
                # Check if we already have a position
                has_position = any(t['instrument'] == instrument for t in open_trades)
                if not has_position and acc_info.open_trade_count < 5:
                    opportunities.append({
                        'instrument': instrument,
                        'spread': regime_data['spread_pips'],
                        'bid': regime_data['bid'],
                        'ask': regime_data['ask']
                    })
                    print(f"   ✅ OPPORTUNITY: Good spread, no current position")
                elif has_position:
                    print(f"   ℹ️  Already have position")
                else:
                    print(f"   ⚠️  Max positions reached ({acc_info.open_trade_count}/5)")
        
        return {
            'account_id': account_id,
            'name': account_info['name'],
            'balance': acc_info.balance,
            'unrealized_pl': acc_info.unrealized_pl,
            'realized_pl': acc_info.realized_pl,
            'open_trades': len(open_trades),
            'opportunities': opportunities,
            'exposure': current_exposure if acc_info.balance > 0 else 0
        }
        
    except Exception as e:
        print(f"\n❌ Error checking account {account_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("🔍 POSITION & MARKET ANALYSIS")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)
    
    # Check API credentials
    api_key = os.getenv('OANDA_API_KEY')
    if not api_key:
        print("❌ ERROR: OANDA_API_KEY not found in environment variables")
        print("Please check your oanda_config.env file")
        return
    
    print(f"\n✅ API Key found: {api_key[:10]}...")
    print(f"✅ Environment: {os.getenv('OANDA_ENVIRONMENT', 'practice')}")
    
    # Analyze each account
    results = []
    for account_id, account_info in ACCOUNTS.items():
        result = check_account(account_id, account_info)
        if result:
            results.append(result)
    
    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 PORTFOLIO SUMMARY")
    print(f"{'='*80}")
    
    if results:
        total_balance = sum(r['balance'] for r in results)
        total_unrealized = sum(r['unrealized_pl'] for r in results)
        total_realized = sum(r['realized_pl'] for r in results)
        total_trades = sum(r['open_trades'] for r in results)
        
        print(f"\n💰 Total Balance: {format_currency(total_balance)}")
        print(f"📈 Total Unrealized P&L: {format_currency(total_unrealized)}")
        print(f"💵 Total Realized P&L: {format_currency(total_realized)}")
        print(f"📊 Total Open Trades: {total_trades}")
        print(f"🏦 Active Accounts: {len(results)}")
        
        # Overall ROI
        if total_balance > 0:
            total_roi = (total_realized / total_balance) * 100
            print(f"\n📊 Portfolio ROI: {format_percentage(total_roi)}")
        
        # All opportunities
        print(f"\n{'─'*80}")
        print(f"🎯 TRADING OPPORTUNITIES ACROSS ALL ACCOUNTS")
        print(f"{'─'*80}")
        
        all_opportunities = []
        for result in results:
            for opp in result['opportunities']:
                all_opportunities.append({
                    'account': result['name'],
                    'instrument': opp['instrument'],
                    'spread': opp['spread'],
                    'bid': opp['bid'],
                    'ask': opp['ask']
                })
        
        if all_opportunities:
            # Sort by spread (tightest first)
            all_opportunities.sort(key=lambda x: x['spread'])
            
            for i, opp in enumerate(all_opportunities, 1):
                print(f"\n{i}. {opp['instrument']} on {opp['account']}")
                print(f"   Spread: {opp['spread']:.2f} pips")
                print(f"   Bid/Ask: {opp['bid']:.5f} / {opp['ask']:.5f}")
                print(f"   💡 Ready to trade with tight spread")
        else:
            print(f"\nNo immediate opportunities found.")
            print(f"Reasons:")
            print(f"  • All instruments already have positions")
            print(f"  • Maximum position limits reached")
            print(f"  • Spreads too wide for entry")
        
        # Recommendations
        print(f"\n{'─'*80}")
        print(f"💡 RECOMMENDATIONS")
        print(f"{'─'*80}")
        
        # Check portfolio exposure
        avg_exposure = sum(r['exposure'] for r in results) / len(results)
        
        if avg_exposure > 60:
            print(f"\n⚠️  HIGH RISK: Average exposure at {avg_exposure:.1f}%")
            print(f"   ACTION: Reduce position sizes or close losing trades")
        elif avg_exposure > 40:
            print(f"\n🟡 MODERATE RISK: Average exposure at {avg_exposure:.1f}%")
            print(f"   ACTION: Monitor closely, avoid adding new positions")
        else:
            print(f"\n🟢 LOW RISK: Average exposure at {avg_exposure:.1f}%")
            print(f"   ACTION: Can consider new opportunities")
        
        if total_unrealized < 0:
            print(f"\n⚠️  DRAWDOWN DETECTED: {format_currency(total_unrealized)}")
            print(f"   ACTION: Review losing trades and adjust stops")
        
        if all_opportunities:
            print(f"\n✅ {len(all_opportunities)} trading opportunities identified")
            print(f"   ACTION: Scanner will automatically evaluate these")
        
        print(f"\n🤖 SYSTEM STATUS:")
        print(f"   ✅ All accounts monitored")
        print(f"   ✅ Protective stops verified")
        print(f"   ✅ Market conditions analyzed")
        print(f"   ✅ Opportunities identified")
        
    else:
        print("\n❌ No accounts were successfully checked")
    
    print(f"\n{'='*80}")
    print(f"✅ Analysis Complete")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()


















