#!/usr/bin/env python3
"""
ICT OTE Strategy Optimization Runner
Simple script to run the comprehensive ICT OTE optimization
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add the current directory to the path
sys.path.append(os.path.dirname(__file__))

from ict_ote_comprehensive_optimizer import ICTOTEComprehensiveOptimizer, ComprehensiveConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run ICT OTE strategy optimization"""
    print("🚀 ICT OTE Strategy Comprehensive Optimization")
    print("=" * 60)
    
    # Configuration
    config = ComprehensiveConfig(
        instruments=['XAU_USD', 'EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD'],
        start_date=datetime.now() - timedelta(days=90),  # Last 90 days
        end_date=datetime.now(),
        initial_balance=10000.0,
        n_optimization_combinations=50,  # Number of parameter combinations to test
        n_monte_carlo_simulations=1000,  # Number of Monte Carlo simulations
        max_trades_per_day=20,
        max_positions=3,
        risk_per_trade=0.02  # 2% risk per trade
    )
    
    print(f"📊 Instruments: {', '.join(config.instruments)}")
    print(f"📅 Period: {config.start_date.strftime('%Y-%m-%d')} to {config.end_date.strftime('%Y-%m-%d')}")
    print(f"💰 Initial Balance: ${config.initial_balance:,.2f}")
    print(f"🔧 Optimization Combinations: {config.n_optimization_combinations}")
    print(f"🎲 Monte Carlo Simulations: {config.n_monte_carlo_simulations}")
    print()
    
    # Create optimizer
    optimizer = ICTOTEComprehensiveOptimizer(config)
    
    try:
        # Run optimization
        print("🚀 Starting optimization process...")
        results = optimizer.run_comprehensive_optimization()
        
        if results:
            print("\n" + "="*80)
            print("✅ OPTIMIZATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            
            # Display key results
            print(f"🎯 Final Score: {results.final_score:.1f}/100")
            print(f"📈 Best Return: {results.backtest_results['total_return']:.2f}%")
            print(f"📉 Max Drawdown: {results.backtest_results['max_drawdown']:.2f}%")
            print(f"📊 Win Rate: {results.backtest_results['win_rate']:.1f}%")
            print(f"🎲 Profit Probability: {results.monte_carlo_results['probability_of_profit']:.1f}%")
            print(f"⚠️ Risk Level: {results.risk_assessment['overall_risk_level'].upper()}")
            
            print("\n🔧 OPTIMIZED PARAMETERS:")
            for param, value in results.best_parameters.items():
                print(f"   {param}: {value}")
            
            print("\n📋 TOP RECOMMENDATIONS:")
            for i, rec in enumerate(results.recommendations[:5], 1):
                print(f"   {i}. {rec}")
            
            # Save results
            filename = optimizer.save_comprehensive_results()
            print(f"\n💾 Complete results saved to: {filename}")
            
            # Generate visualizations
            try:
                os.makedirs('ict_ote_plots', exist_ok=True)
                plot_paths = optimizer.monte_carlo.generate_visualizations('ict_ote_plots')
                print(f"📊 Visualizations saved to: ict_ote_plots/")
            except Exception as e:
                print(f"⚠️ Could not generate visualizations: {e}")
            
            print("\n" + "="*80)
            print("🎉 OPTIMIZATION COMPLETE!")
            print("="*80)
            
        else:
            print("\n❌ OPTIMIZATION FAILED!")
            print("Please check the logs for error details.")
            
    except KeyboardInterrupt:
        print("\n⏹️ Optimization interrupted by user.")
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        logger.error(f"Optimization error: {e}")

if __name__ == "__main__":
    main()