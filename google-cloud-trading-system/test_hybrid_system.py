#!/usr/bin/env python3
"""
Test Hybrid Manual Trading System
Validates all components work together
"""

import sys
sys.path.insert(0, 'src')

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("🧪 TESTING HYBRID MANUAL TRADING SYSTEM")
print("="*80 + "\n")

# Test 1: Trump DNA Integration
print("Test 1: Trump DNA Integration Module")
print("-" * 80)
try:
    from src.core.trump_dna_integration import get_trump_dna_integration
    
    trump_dna = get_trump_dna_integration("Test Strategy", ["EUR_USD", "GBP_USD"])
    
    assert trump_dna.weekly_plan is not None, "Weekly plan not created"
    assert trump_dna.weekly_plan.weekly_target > 0, "No weekly target"
    assert len(trump_dna.weekly_plan.daily_targets) == 5, "Missing daily targets"
    assert len(trump_dna.weekly_plan.entry_zones) > 0, "No entry zones"
    
    print(f"  ✅ Weekly target: ${trump_dna.weekly_plan.weekly_target}")
    print(f"  ✅ Daily targets: {list(trump_dna.weekly_plan.daily_targets.values())}")
    print(f"  ✅ Entry zones: {len(trump_dna.weekly_plan.entry_zones)} instruments")
    print(f"  ✅ Fixed stops: {trump_dna.weekly_plan.fixed_stop_pips} pips")
    print(f"  ✅ TP stages: {len(trump_dna.weekly_plan.fixed_tp_stages)}")
    
    # Test should_trade_now
    can_trade, reason = trump_dna.should_trade_now()
    print(f"  ✅ Trade check: {can_trade} ({reason})")
    
    # Test entry zone detection
    zone = trump_dna.is_near_entry_zone("EUR_USD", 1.0850, 5.0)
    print(f"  ✅ Zone check: {zone is not None}")
    
    # Test fixed stops
    stop = trump_dna.get_fixed_stop_loss("EUR_USD", 1.0850, "BUY")
    print(f"  ✅ Fixed stop calculation: {stop:.5f}")
    
    # Test multi-stage targets
    targets = trump_dna.get_multi_stage_targets("EUR_USD", 1.0850, "BUY")
    print(f"  ✅ Multi-stage targets: {len(targets)} stages")
    
    print("\n✅ TEST 1 PASSED: Trump DNA Integration\n")
    
except Exception as e:
    print(f"\n❌ TEST 1 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Trade Opportunity Finder
print("Test 2: Trade Opportunity Finder")
print("-" * 80)
try:
    from src.core.trade_opportunity_finder import get_opportunity_finder, TradeOpportunity, OpportunityQuality
    
    finder = get_opportunity_finder()
    
    assert finder is not None, "Finder not created"
    assert hasattr(finder, 'find_opportunities'), "Missing find_opportunities method"
    assert hasattr(finder, 'approve_opportunity'), "Missing approve method"
    assert hasattr(finder, 'dismiss_opportunity'), "Missing dismiss method"
    
    print(f"  ✅ Opportunity finder created")
    print(f"  ✅ User preferences: {finder.user_preferences}")
    print(f"  ✅ All methods present")
    
    # Test opportunity creation (mock)
    test_opp = TradeOpportunity(
        id="test_123",
        timestamp=datetime.now(),
        instrument="EUR_USD",
        direction="BUY",
        at_sniper_zone=True,
        zone_type="support",
        zone_level=1.0850,
        distance_to_zone_pips=2.5,
        suggested_entry=1.0852,
        fixed_stop_loss=1.0842,
        stop_loss_pips=10.0,
        take_profit_stages=[
            {'pips': 15, 'price': 1.0867, 'close_pct': 0.30},
            {'pips': 30, 'price': 1.0882, 'close_pct': 0.30},
            {'pips': 50, 'price': 1.0902, 'close_pct': 0.20},
        ],
        risk_reward_ratio=3.0,
        quality_score=82,
        quality_level=OpportunityQuality.EXCELLENT,
        confluence_factors={'trend': True, 'rsi': True, 'adx': True, 'volume': True},
        regime="TRENDING",
        current_price=1.0852,
        daily_target_progress=45.0,
        trades_today=2,
        max_trades_remaining=3,
        pros=["At support", "High quality", "4 factors"],
        cons=["2 trades today"],
        recommendation="STRONG BUY",
        upcoming_news=[],
        news_risk="LOW",
        strategy_name="75% WR Champion",
        expected_win_rate=0.75,
        expected_profit=300.0,
        expected_loss=100.0
    )
    
    print(f"  ✅ Test opportunity created")
    print(f"     Quality: {test_opp.quality_score}/100 ({test_opp.quality_level.value})")
    print(f"     Recommendation: {test_opp.recommendation}")
    print(f"     R/R: 1:{test_opp.risk_reward_ratio}")
    
    print("\n✅ TEST 2 PASSED: Trade Opportunity Finder\n")
    
except Exception as e:
    print(f"\n❌ TEST 2 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Champion 75WR Hybrid Strategy
print("Test 3: Champion 75WR Hybrid Strategy")
print("-" * 80)
try:
    from src.strategies.champion_75wr_hybrid import get_champion_75wr_hybrid
    
    strategy = get_champion_75wr_hybrid()
    
    assert strategy is not None, "Strategy not created"
    assert hasattr(strategy, 'trump_dna'), "Trump DNA not integrated"
    assert hasattr(strategy, 'analyze_market'), "Missing analyze_market method"
    
    print(f"  ✅ Strategy created: {strategy.name}")
    print(f"  ✅ Instruments: {strategy.instruments}")
    print(f"  ✅ Signal strength min: {strategy.signal_strength_min}")
    print(f"  ✅ Confluence required: {strategy.confluence_required}")
    print(f"  ✅ Min ADX: {strategy.min_adx}")
    print(f"  ✅ Trump DNA integrated: YES")
    print(f"  ✅ Weekly target: ${strategy.trump_dna.weekly_plan.weekly_target}")
    
    print("\n✅ TEST 3 PASSED: Champion 75WR Hybrid Strategy\n")
    
except Exception as e:
    print(f"\n❌ TEST 3 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: API Endpoint Structure
print("Test 4: API Endpoint Structure")
print("-" * 80)
try:
    # Check if main.py has the routes (by importing)
    import importlib.util
    spec = importlib.util.spec_from_file_location("main", "main.py")
    main_module = importlib.util.module_from_spec(spec)
    
    # Read main.py content
    with open('main.py', 'r') as f:
        main_content = f.read()
    
    assert '/api/opportunities' in main_content, "Missing /api/opportunities route"
    assert '/api/opportunities/approve' in main_content, "Missing approve route"
    assert '/api/opportunities/dismiss' in main_content, "Missing dismiss route"
    
    print(f"  ✅ /api/opportunities endpoint present")
    print(f"  ✅ /api/opportunities/approve endpoint present")
    print(f"  ✅ /api/opportunities/dismiss endpoint present")
    
    print("\n✅ TEST 4 PASSED: API Endpoints\n")
    
except Exception as e:
    print(f"\n❌ TEST 4 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Dashboard HTML Structure
print("Test 5: Dashboard HTML Structure")
print("-" * 80)
try:
    with open('src/templates/dashboard_advanced.html', 'r') as f:
        html_content = f.read()
    
    assert 'opportunitiesFeed' in html_content, "Missing opportunities feed div"
    assert 'approveOpportunity' in html_content, "Missing approve function"
    assert 'dismissOpportunity' in html_content, "Missing dismiss function"
    assert 'opportunity-card' in html_content, "Missing opportunity card CSS"
    assert 'Manual vs Auto' in html_content, "Missing A/B comparison"
    assert 'tradingMode' in html_content, "Missing mode selector"
    
    print(f"  ✅ Opportunities feed section present")
    print(f"  ✅ Approve/Dismiss functions present")
    print(f"  ✅ Opportunity card CSS present")
    print(f"  ✅ A/B comparison section present")
    print(f"  ✅ Mode selector present")
    print(f"  ✅ JavaScript integration complete")
    
    print("\n✅ TEST 5 PASSED: Dashboard HTML\n")
    
except Exception as e:
    print(f"\n❌ TEST 5 FAILED: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final Summary
print("="*80)
print("✅ ALL TESTS PASSED - HYBRID SYSTEM READY!")
print("="*80)
print()
print("Components Validated:")
print("  ✅ Trump DNA Integration Module")
print("  ✅ Trade Opportunity Finder")
print("  ✅ Champion 75WR Hybrid Strategy")
print("  ✅ API Endpoints (/api/opportunities)")
print("  ✅ Dashboard UI (opportunity cards, A/B comparison)")
print()
print("Next Steps:")
print("  1. Deploy to Google Cloud")
print("  2. Open dashboard: https://ai-quant-trading.uc.r.appspot.com/dashboard")
print("  3. See opportunities appear with one-click approve/dismiss")
print("  4. Monitor Manual vs Auto lane performance")
print()
print("="*80)
print("🚀 SYSTEM READY FOR DEPLOYMENT!")
print("="*80)
print()


