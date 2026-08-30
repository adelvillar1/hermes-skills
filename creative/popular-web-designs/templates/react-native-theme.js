/**
 * React Native Design System Template
 * 
 * Translates web design tokens from the popular-web-designs catalog into
 * React Native StyleSheet-compatible objects. Use this as a starting point
 * when redesigning an RN mobile app with a web design system as reference.
 * 
 * The mapping: CSS custom properties → RN StyleSheet objects
 *   --color-*    → colors object
 *   font-size/weight/line-height/letter-spacing → typography object
 *   padding/margin scale → spacing object (8px base unit)
 *   box-shadow   → shadows object (iOS shadowColor/Opacity/Offset/Radius + Android elevation)
 *   border-radius → radii object
 * 
 * Font substitution: Web fonts → system fonts or bundled Expo fonts
 *   - Inter → system default (already close)
 *   - DM Sans → 'DM Sans' (bundled with Expo)
 *   - Geist → 'Geist' (available in Expo)
 *   - Airbnb Cereal → 'DM Sans' (closest CDN substitute)
 */

export const colors = {
  canvas: '#FAFAF8',       // page background (warm off-white)
  surface: '#FFFFFF',       // cards, sheets
  textPrimary: '#1A1A1A',   // warm near-black (never #000)
  textSecondary: '#6B6B6B',
  textTertiary: '#999999',
  accent: '#D4553A',        // brand accent — pick from source design
  accentDark: '#B84430',    // pressed/hover variant
  accentLight: '#FDF0ED',   // selected state tint
  success: '#2D8A56',
  border: '#EBEBEB',
  inputBg: '#F2F2F0',       // warm grey for inputs, inactive pills
  white: '#FFFFFF',
};

export const typography = {
  headingLarge: { fontSize: 28, fontWeight: '700', letterSpacing: -0.5, lineHeight: 34 },
  headingMedium: { fontSize: 22, fontWeight: '600', letterSpacing: -0.3, lineHeight: 28 },
  headingSmall: { fontSize: 18, fontWeight: '600', lineHeight: 24 },
  body: { fontSize: 15, fontWeight: '400', lineHeight: 22 },
  bodyMedium: { fontSize: 15, fontWeight: '500', lineHeight: 22 },
  caption: { fontSize: 13, fontWeight: '400', lineHeight: 18 },
  label: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5, lineHeight: 14 },
};

export const spacing = {
  xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24, xxxl: 32, huge: 40, massive: 48,
};

export const shadows = {
  card: {
    shadowColor: '#000', shadowOpacity: 0.06, shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8, elevation: 2,
  },
  elevated: {
    shadowColor: '#000', shadowOpacity: 0.10, shadowOffset: { width: 0, height: 4 },
    shadowRadius: 12, elevation: 4,
  },
  pressed: {
    shadowColor: '#000', shadowOpacity: 0.14, shadowOffset: { width: 0, height: 6 },
    shadowRadius: 16, elevation: 6,
  },
};

export const radii = {
  sm: 8, md: 12, lg: 16, xl: 24, full: 999,
};

// Audit commands to verify no hardcoded values leaked into screens:
//   grep -rn '#[0-9a-fA-F]\{3,8\}' screens/ | grep -v theme.js | grep -v shadowColor
//   perl -CSD -ne 'print "$.: $_" if /[\x{1F300}-\x{1F9FF}\x{2600}-\x{26FF}]/' screens/*.js navigation.js
