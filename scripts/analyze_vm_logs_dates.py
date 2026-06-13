import json
from datetime import datetime, timedelta

def analyze_vm_logs():
    try:
        with open('data/processed/vm_trades_flat.json', 'r') as f:
            data = json.load(f)
            
        trades = data.get('trades', [])
        
        print(f"Total trades in log: {len(trades)}")
        
        accounts_of_interest = ['001', '002', '003']
        recent_cutoff = datetime.now() - timedelta(days=7)
        
        for acc in accounts_of_interest:
            acc_trades = [t for t in trades if t.get('account_suffix') == acc]
            print(f"\nAccount {acc}:")
            if not acc_trades:
                print("  No trades found.")
                continue
                
            # Sort by date
            acc_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            latest = acc_trades[0].get('timestamp')
            count_recent = sum(1 for t in acc_trades if datetime.fromisoformat(t.get('timestamp').replace('Z', '+00:00')).replace(tzinfo=None) > recent_cutoff)
            
            print(f"  Total Trades: {len(acc_trades)}")
            print(f"  Latest Trade: {latest}")
            print(f"  Trades in last 7 days: {count_recent}")
            
            if acc_trades:
                print(f"  Most recent trade details: {json.dumps(acc_trades[0], indent=2)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_vm_logs()
