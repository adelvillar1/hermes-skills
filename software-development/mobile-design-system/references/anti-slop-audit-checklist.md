# Anti-Slop Audit Checklist for Mobile Design Systems

Run these commands from the mobile app source directory (e.g., `apps/mobile/src/`).

All commands should return CLEAN (no output) after migration is complete.

## 1. Hardcoded Colors

```bash
grep -rn '#[0-9a-fA-F]\{3,8\}' screens/ components/ navigation.js theme.js | grep -v 'theme.js:' | grep -v 'shadowColor'
```

**Exception:** `shadowColor: '#000'` in shadow definitions is allowed.
**Exception:** `'rgba(255,255,255,0.75)'` style opacity values are allowed on accent-colored surfaces.

**Fix:** Replace with a named color from `theme.js`.

## 2. Emoji

```bash
perl -CSD -ne 'print "$ARGV:$. $_" if /[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}\x{2700}-\x{27BF}]/' screens/*.js navigation.js
```

**Zero tolerance.** All emoji must be replaced with Ionicons or plain text.

## 3. Filler Copy

```bash
grep -rni 'revolutionizing\|unlock your\|next-generation\|seamlessly\|empower\|harness\|leverage\|cutting-edge\|thousands of\|10,000\|99.9%\|happy customer' screens/
```

**Fix:** Use real data or honest placeholder text.

## 4. Excessive Iconography

```bash
for f in screens/*.js; do echo "$(basename $f): $(grep -c '<Icon ' $f)"; done
```

**Flag if any screen >10 icons.** Check each is functional (navigation, action, semantic label) not decorative.

## 5. AI Card Smell

```bash
grep -rn 'borderLeft\|border-left\|borderLeftWidth' screens/ components/
```

**Zero tolerance.** The "rounded card with left border accent" is the signature AI-generated dashboard smell.

## 6. Purple / Gradient Check

```bash
grep -rni 'purple\|#6366f1\|#8b5cf6\|#a855f7\|#c084fc\|#7c3aed' screens/ theme.js components/
```

**Flag unless the brand explicitly uses purple.**

## Pass Criteria

- All 6 checks return CLEAN
- `theme.js` is the ONLY file containing hardcoded hex colors
- Every screen imports from `theme.js`
- Zero emoji in any screen, component, or navigation file
- No filler copy — every sentence says something specific or is cut
