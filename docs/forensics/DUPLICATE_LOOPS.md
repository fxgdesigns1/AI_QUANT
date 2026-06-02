./FINAL_SYSTEM_STATUS_OCT18.md:26:✅ APScheduler: RUNNING
./FINAL_SYSTEM_STATUS_OCT18.md:142:- APScheduler: Running jobs every 5/15 minutes
./simple_agent.py:41:        self._thread = threading.Thread(target=self._run_loop, daemon=True)
./IMPLEMENTATION_COMPLETE_OCT18.md:106:- ✅ APScheduler active
./IMPLEMENTATION_COMPLETE_OCT18.md:199:**IMPORTANT**: The trading systems, scanner, and APScheduler are all running correctly. Only the dashboard UI is affected. Trading operations continue unaffected.
./FINAL_BRUTAL_TRUTH_READY_FOR_WEEK_OCT19.md:72:- APScheduler operational
./WEEKLY_NAVIGATION_OCT19.md:162:- ✅ APScheduler: RUNNING
./EMERGENCY_FIX_OCT15_READONLY.md:49:   - APScheduler job ran but scanner was `None`
./EMERGENCY_FIX_OCT15_READONLY.md:121:- ✅ APScheduler runs scans every 5 minutes
./EMERGENCY_FIX_OCT15_READONLY.md:142:3. **Check APScheduler execution:**
./EMERGENCY_FIX_OCT15_READONLY.md:144:   gcloud app logs read --limit=100 | grep "APScheduler: Running scanner job"
./EMERGENCY_FIX_OCT15_READONLY.md:202:3. ⏳ First APScheduler scan runs (within 5 minutes)
./SYSTEM_VERIFICATION_OCT15_EVENING.md:12:2. **APScheduler:** ✅ RUNNING
./SYSTEM_VERIFICATION_OCT15_EVENING.md:96:| 7:20 PM | Verified: Scanner now working, APScheduler running |
./SYSTEM_VERIFICATION_OCT15_EVENING.md:111:3. ✅ APScheduler IS running scans
./SYSTEM_VERIFICATION_OCT15_EVENING.md:206:- APScheduler: ACTIVE
./working_trading_system.py:125:    while True:
./ERRORS_FIXED_OCT21.md:55:   - ✅ APScheduler configured (scanner every 5min, snapshots every 15min)
./WHY_NO_TRADES_TODAY.md:31:4. ❌ **Scanner NOT Executing**: APScheduler configured but not triggering
./WHY_NO_TRADES_TODAY.md:40:- APScheduler: ❌ NOT triggering the scanner job
./WHY_NO_TRADES_TODAY.md:46:"🔄 APScheduler: Running scanner job..."
./WHY_NO_TRADES_TODAY.md:55:### Problem 1: APScheduler Not Firing
./WHY_NO_TRADES_TODAY.md:120:2. ⏳ **Fix APScheduler** - why isn't it triggering?
./WHY_NO_TRADES_TODAY.md:146:- Why APScheduler isn't firing
./WHY_NO_TRADES_TODAY.md:170:1. **Investigate APScheduler** - Why no scanner job logs?
./DATA_CONSISTENCY_GUIDE.md:157:# (it will auto-restart via APScheduler)
./test_websocket_playwright.py:336:    asyncio.run(main())
./COMPREHENSIVE_DASHBOARD_FIX_FINAL_OCT18.md:268:**APScheduler:** ✅ RUNNING  
./COMPREHENSIVE_DASHBOARD_FIX_FINAL_OCT18.md:333:- ✅ APScheduler running (5-min scans)
./playwright_websocket_test.py:503:    asyncio.run(main())
./REAL_TRUTH_OCT15.md:21:- APScheduler: Running but **not placing trades**
./REAL_TRUTH_OCT15.md:31:3. Is APScheduler actually calling the scan function?
./REAL_TRUTH_OCT15.md:62:4. ⏳ Verify APScheduler is actually executing scans
./FINAL_HONEST_ASSESSMENT_OCT19.md:94:9. ✅ **APScheduler** - Jobs running on schedule
./enhanced_websocket_test.py:568:    asyncio.run(main())
./FIND_WHY_NO_SIGNALS.py:194:print("   - main.py must be running for APScheduler to work")
./COMPREHENSIVE_STRESS_TEST_REPORT_OCT19.md:137:- ✅ Scanner runs every 5 minutes via APScheduler
./COMPREHENSIVE_STRESS_TEST_REPORT_OCT19.md:144:**Test 5.2: APScheduler**
./COMPREHENSIVE_STRESS_TEST_REPORT_OCT19.md:271:7. ✅ **APScheduler** - Background jobs running on schedule
./STRATEGY_DASHBOARD_DEPLOYED.md:60:- Captures data every 15 minutes via APScheduler
./STRATEGY_DASHBOARD_DEPLOYED.md:127:### **APScheduler Job:**
./STRATEGY_DASHBOARD_DEPLOYED.md:182:1. **APScheduler** runs `capture_performance_snapshots()` every 15 minutes
./STRATEGY_DASHBOARD_DEPLOYED.md:220:- `main.py` (modified - added routes + APScheduler job)
./STRATEGY_DASHBOARD_DEPLOYED.md:315:- ✅ APScheduler - Background snapshot jobs
./docs/forensics/ENTRYPOINTS.md:20:./docs/forensics/DUPLICATE_LOOPS.md:93:./.venv/lib/python3.13/site-packages/charset_normalizer/cli/__main__.py:    while True:
