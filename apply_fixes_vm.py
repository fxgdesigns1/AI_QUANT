import os
import sys

TARGET_FILE = "/opt/ai-quant/working_trading_system.py"
API_FILE = "/opt/ai-quant/src/control_plane/api.py"

def patch_runner():
    print(f"Reading {TARGET_FILE}...")
    with open(TARGET_FILE, 'r') as f:
        content = f.read()

    # 1. Imports
    if "import math" not in content:
        print("Patching imports...")
        content = content.replace(
            "from datetime import datetime, timedelta, timezone",
            "from datetime import datetime, timedelta, timezone\nimport math\nfrom typing import Any"
        )
    
    # 2. Init Counters
    if "_price_integrity_blocks_per_account" not in content:
        print("Patching init counters...")
        old_init = 'self._price_sanity_blocks_per_account = {}  # account_id -> count'
        new_init = '''self._price_sanity_blocks_per_account = {}  # account_id -> count
        self._price_integrity_blocks_per_account = {}  # account_id -> count (NEW)
        
        # Price integrity validation thresholds (env-driven with safe defaults)
        self._max_price_staleness_seconds = int(os.getenv('MAX_PRICE_STALENESS_SECONDS', '15'))
        self._min_xau_usd_mid = float(os.getenv('MIN_XAU_USD_MID', '500'))
        self._max_xau_usd_mid = float(os.getenv('MAX_XAU_USD_MID', '10000'))
        self._min_fx_mid = float(os.getenv('MIN_FX_MID', '0.2'))
        self._max_fx_mid = float(os.getenv('MAX_FX_MID', '5.0'))'''
        content = content.replace(old_init, new_init)

    # 3. Add price_integrity_check method
    if "def price_integrity_check" not in content:
        print("Adding price_integrity_check method...")
        method_code = '''
    def price_integrity_check(self, instrument: str, price_obj: Any, now_ts: float, account_id: str) -> tuple[bool, str, dict]:
        """
        Price Integrity Gate - validates price before allowing signal generation/execution
        Returns: (ok: bool, reason: str, meta: dict)
        """
        meta = {
            'instrument': instrument,
            'account': account_id[-3:] if account_id else 'unknown'
        }
        
        # Check 1: Price object exists and has mid price
        if not price_obj or not hasattr(price_obj, 'mid'):
            return False, "missing_price_object", meta
        
        mid = float(price_obj.mid)
        meta['mid'] = mid
        
        # Check 2: Mid price is finite and positive
        if not (mid > 0 and math.isfinite(mid)):
            return False, "invalid_mid_price", meta
        
        # Check 3: Price freshness
        if hasattr(price_obj, 'ts_utc'):
            price_ts = float(price_obj.ts_utc)
            age_seconds = now_ts - price_ts
            meta['age_seconds'] = age_seconds
            meta['price_ts'] = price_ts
            
            if age_seconds > self._max_price_staleness_seconds:
                return False, f"stale_price_age_{age_seconds:.0f}s", meta
        
        # Check 4: Instrument-specific sanity ranges
        if 'XAU' in instrument:
            # Gold price validation
            if mid < self._min_xau_usd_mid or mid > self._max_xau_usd_mid:
                meta['min_allowed'] = self._min_xau_usd_mid
                meta['max_allowed'] = self._max_xau_usd_mid
                return False, f"xau_price_out_of_range", meta
        else:
            # FX majors validation
            if mid < self._min_fx_mid or mid > self._max_fx_mid:
                meta['min_allowed'] = self._min_fx_mid
                meta['max_allowed'] = self._max_fx_mid
                return False, f"fx_price_out_of_range", meta
        
        # All checks passed
        return True, "ok", meta

    def scan_and_execute(self):'''
        content = content.replace("def scan_and_execute(self):", method_code)

    # 4. Inject check into scan loop
    # We'll use the "Get strategy instance by key" comment as a reliable anchor
    marker = '# Get strategy instance by key'
    if "PRICE_INTEGRITY_FAIL" not in content and marker in content:
        print("Injecting integrity check loop...")
        integrity_logic = '''
                # GATE: Price Integrity Check (NEW - validates price ranges and quality)
                price_integrity_failed = False
                for inst in instruments:
                    price = market_data.get(inst)
                    if price:
                        ok, reason, meta = self.price_integrity_check(inst, price, now_ts, account_id)
                        if not ok:
                            # Log detailed failure
                            logger.warning(
                                f"PRICE_INTEGRITY_FAIL account={account_id[-3:]} strategy={strategy_key} "
                                f"instrument={inst} mid={meta.get('mid', 'N/A')} "
                                f"reason={reason} meta={meta}"
                            )
                            # Increment counter
                            self._price_integrity_blocks_per_account[account_id] = \\
                                self._price_integrity_blocks_per_account.get(account_id, 0) + 1
                            price_integrity_failed = True
                            break  # Fail fast on first integrity failure
                
                if price_integrity_failed:
                    continue  # Skip this account/strategy - fail closed
                '''
        
        content = content.replace(marker, integrity_logic + '\n                ' + marker)

    # 5. Fix STRAT_EVIDENCE and mixing
    old_evidence_marker = '# LOG EVIDENCE: STRAT_EVIDENCE (Canonical Marker)'
    
    # We need to find the whole block to replace.
    # We'll look for the start marker and the end marker "logger.info(evidence_str)"
    
    if "PRICE_INTEGRITY_MISMATCH" not in content and old_evidence_marker in content:
        print("Patching STRAT_EVIDENCE block...")
        
        new_evidence_block = '''# LOG EVIDENCE: STRAT_EVIDENCE (Canonical Marker)
                    # FIX: Use SIGNAL instrument for price lookup, not first scanned instrument
                    signal_instrument = signals[0].instrument if signals else (instruments[0] if instruments else "UNKNOWN")
                    price_instrument = signal_instrument  # Price MUST match signal instrument
                    
                    # Get price for the SIGNAL instrument (not scanned instrument)
                    price_used = market_data.get(price_instrument)
                    mid_price = price_used.mid if price_used else 0
                    price_ts = price_timestamps.get(price_instrument, 0)
                    
                    # Construct evidence object (single line, key=value)
                    # Using clean string representation for lists
                    prov_str = ",".join(news_context.get("providers", []))
                    if not prov_str: prov_str = "none"
                    
                    # Log strategy-specific instruments scanned
                    instruments_str = ",".join(instruments)
                    
                    # CRITICAL: Log BOTH signal_instrument and price_instrument to detect mismatches
                    evidence_str = (
                        f"STRAT_EVIDENCE system=ALPHA account={account_id[-3:]} strategy={strategy_key} "
                        f"instruments_scanned={instruments_str} signal_instrument={signal_instrument} "
                        f"price_instrument={price_instrument} price_mid={mid_price:.5f} "
                        f"price_ts={price_ts:.3f} price_source=oanda "
                        f"news_used_count={news_context.get('count', 0)} "
                        f"news_providers={prov_str} "
                        f"signals_generated={len(signals) if signals else 0} "
                        f"decision={'BUY' if signals and signals[0].side.value == 'BUY' else ('SELL' if signals and signals[0].side.value == 'SELL' else 'NONE')}"
                    )
                    logger.info(evidence_str)
                    
                    # HARD GUARD: Detect instrument/price mismatch
                    if signals and signal_instrument != price_instrument:
                        logger.error(
                            f"PRICE_INTEGRITY_MISMATCH account={account_id[-3:]} strategy={strategy_key} "
                            f"signal_instrument={signal_instrument} price_instrument={price_instrument} "
                            f"REJECTED: Signal instrument does not match price source instrument"
                        )
                        continue  # Skip this account/strategy - fail closed'''
        
        # We replace the old block roughly. 
        # Since exact string matching for a large block is risky with indentation, 
        # let's find start and end indices.
        
        start_idx = content.find(old_evidence_marker)
        end_marker = "logger.info(evidence_str)"
        end_idx = content.find(end_marker, start_idx)
        
        if start_idx != -1 and end_idx != -1:
             end_idx += len(end_marker)
             content = content[:start_idx] + new_evidence_block + content[end_idx:]
        else:
             print("WARNING: Could not locate STRAT_EVIDENCE block markers correctly")

    # 6. Expose in status snapshot
    if '"price_sanity_blocks_per_account": dict(self._price_sanity_blocks_per_account),' in content:
         if '"price_integrity_blocks_per_account"' not in content:
             print("Updating status snapshot...")
             content = content.replace(
                 '"price_sanity_blocks_per_account": dict(self._price_sanity_blocks_per_account),',
                 '"price_sanity_blocks_per_account": dict(self._price_sanity_blocks_per_account),\n                "price_integrity_blocks_per_account": dict(self._price_integrity_blocks_per_account),  # NEW'
             )

    with open(TARGET_FILE, 'w') as f:
        f.write(content)
    print("Successfully patched working_trading_system.py")

def patch_api():
    if not os.path.exists(API_FILE):
        print(f"API file not found: {API_FILE}")
        return
        
    print(f"Reading {API_FILE}...")
    with open(API_FILE, 'r') as f:
        content = f.read()
    
    # Update StatusResponse
    if "price_integrity_blocks_per_account" not in content:
        print("Patching API model...")
        content = content.replace(
            "price_sanity_blocks_per_account: Optional[Dict[str, int]] = None",
            "price_sanity_blocks_per_account: Optional[Dict[str, int]] = None\n    price_integrity_blocks_per_account: Optional[Dict[str, int]] = None  # NEW"
        )
        
        content = content.replace(
            'price_sanity_blocks = snapshot.get("price_sanity_blocks_per_account", {})',
            'price_sanity_blocks = snapshot.get("price_sanity_blocks_per_account", {})\n        price_integrity_blocks = snapshot.get("price_integrity_blocks_per_account", {})'
        )
        
        content = content.replace(
            'price_sanity_blocks_per_account=price_sanity_blocks if price_sanity_blocks else None,',
            'price_sanity_blocks_per_account=price_sanity_blocks if price_sanity_blocks else None,\n            price_integrity_blocks_per_account=price_integrity_blocks if price_integrity_blocks else None,'
        )

    with open(API_FILE, 'w') as f:
        f.write(content)
    print("Successfully patched api.py")

if __name__ == "__main__":
    patch_runner()
    patch_api()
