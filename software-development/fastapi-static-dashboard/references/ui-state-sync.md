# UI State Sync — Persisted Selectors in Vanilla JS Dashboards

Pattern for keeping UI selector state (risk profile, league, team filters) in sync with `localStorage` and re-rendering correctly.

## The Bug

A selector (e.g., risk profile pills: Conservative / Balanced / Aggressive) changes the view when clicked, but the button highlight stays on the default value after re-render.

**Root cause:** The render function hardcodes the default button style instead of reading from the current state variable.

**Before (broken):**
```javascript
async function renderUpcoming(container) {
  container.innerHTML = `
    <div>
      <button id="risk-conservative" style="background: transparent;">Conservative</button>
      <button id="risk-balanced" style="background: var(--accent); color: white;">Balanced</button>
      <button id="risk-aggressive" style="background: transparent;">Aggressive</button>
    </div>
  `;
  // ... fetch and render games
}

function setRiskProfile(profile) {
  riskProfile = profile;
  localStorage.setItem('riskProfile', profile);
  // Update button styles
  document.querySelectorAll('.risk-btn').forEach(btn => {
    btn.style.background = 'transparent';
    btn.style.color = 'var(--text-muted)';
  });
  document.getElementById(`risk-${profile}`).style.background = 'var(--accent)';
  document.getElementById(`risk-${profile}`).style.color = 'white';
  // Re-render
  renderUpcoming(document.getElementById('content'));
}
```

When `setRiskProfile('aggressive')` runs:
1. It updates the buttons to show Aggressive as active
2. It calls `renderUpcoming()`
3. `renderUpcoming()` rebuilds the HTML with hardcoded "Balanced" as active
4. The UI snaps back to Balanced

**After (fixed):**
```javascript
let riskProfile = localStorage.getItem('riskProfile') || 'balanced';

async function renderUpcoming(container) {
  container.innerHTML = `
    <div>
      <button id="risk-conservative" 
        style="background: ${riskProfile === 'conservative' ? 'var(--accent)' : 'transparent'};
               color: ${riskProfile === 'conservative' ? 'white' : 'var(--text-muted)'};">
        Conservative
      </button>
      <button id="risk-balanced"
        style="background: ${riskProfile === 'balanced' ? 'var(--accent)' : 'transparent'};
               color: ${riskProfile === 'balanced' ? 'white' : 'var(--text-muted)'};">
        Balanced
      </button>
      <button id="risk-aggressive"
        style="background: ${riskProfile === 'aggressive' ? 'var(--accent)' : 'transparent'};
               color: ${riskProfile === 'aggressive' ? 'white' : 'var(--text-muted)'};">
        Aggressive
      </button>
    </div>
  `;
  // ... fetch and render games
}
```

Now the render function reads from `riskProfile` state, so re-rendering preserves the user's selection.

## General Pattern

For any persisted selector in a vanilla JS dashboard:

1. **Initialize from `localStorage`:**
   ```javascript
   let myFilter = localStorage.getItem('myFilter') || 'default';
   ```

2. **Render with template literal interpolation:**
   ```javascript
   `<button style="background: ${myFilter === 'value' ? 'active' : 'inactive'}">`
   ```

3. **Update handler:**
   ```javascript
   function setMyFilter(value) {
     myFilter = value;
     localStorage.setItem('myFilter', value);
     renderView();  // Re-render reads from updated myFilter
   }
   ```

4. **Never hardcode active state in the template.** Always interpolate from the state variable.

## Applies To

- Risk profile selectors (conservative / balanced / aggressive)
- League/sport selectors
- Team filters
- Date range pickers
- View mode toggles (list / grid / chart)
- Any UI state that persists across re-renders

## Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Hardcoded default in template | Selector snaps back to default on re-render | Interpolate from state variable |
| Missing `localStorage` init | Selection lost on page refresh | Read from `localStorage` on script load |
| State variable not updated before render | Old value shown after click | Update state variable BEFORE calling render |
| Multiple state sources | `riskProfile` variable vs `localStorage` out of sync | Single source of truth: variable reads from `localStorage` on init, writes on change |
