# Deployment Required

**Date**: 2026-01-13  
**Status**: Code fixes exist but NOT deployed

---

## ✅ Code Fixes Exist (Local Files)

1. **Active Trades Fix** (Line 1113 in `templates/forensic_command.html`):
   ```javascript
   const unrealizedPL = Number(trade.unrealizedPL) || 0;
   ${unrealizedPL.toFixed(2)}
   ```
   ✅ Fix is in code file

2. **News Filtering Fix** (Line 1910 in `src/control_plane/api.py`):
   ```python
   if not filtered_items and news_items:
       filtered_items = news_items[:10]
   ```
   ✅ Fix is in code file

3. **Loading State Fix** (Line 1279 in `templates/forensic_command.html`):
   ```javascript
   show(loading); hide(disabled); hide(content); hide(errorBox);
   ```
   ✅ Fix is in code file

---

## ❌ Deployed Code is OLD

**Evidence**: Browser shows error:
```
Failed to load active trades: (trade.unrealizedPL || 0).toFixed is not a function
```

This error shows OLD code that calls `.toFixed()` directly on `(trade.unrealizedPL || 0)` without converting to Number first.

**Current code file**: Already has `Number()` conversion before `.toFixed()`

**Conclusion**: Local code files have fixes, but VM is running OLD code.

---

## 🚀 Next Step: Deploy Code to VM

All fixes are in local files but need to be deployed to the VM for them to take effect.

**Deployment needed**:
1. Deploy `templates/forensic_command.html` to VM
2. Deploy `src/control_plane/api.py` to VM
3. Restart control plane service
4. Clear browser cache
5. Test in browser

---

## 📝 Summary

- ✅ **Code fixes**: All fixes exist in local files
- ❌ **Deployed code**: VM is running old code without fixes
- 🚀 **Action required**: Deploy code to VM
