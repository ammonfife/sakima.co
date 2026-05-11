# AGENTS.md — sakima.co

**Coin dealer storefront.** Subproject of `ammonfife/lkup.info`. Marketing/storefront site for Sakima LC.

## Boot sequence

```bash
git checkout main && git pull origin main
# No knowledge snapshot — read lkup.info for backend context
cat README.md
```

## Relationship to lkup.info

- `sakima.co` = public dealer storefront (Astro/static site)
- `lkup.info` = backend platform (Supabase, Edge Functions, React SPA)
- GA4 dual tracking: both sites send to G-Z5C47SKHDD + their own property ID
- Whatnot shows data flows from lkup.info → sakima.co overlay

## Branch policy

Work on `main`. Push frequently. No long-lived feature branches.

## Key files

- `README.md` — site overview
- GA4 tracking config — dual measurement IDs on all pages

## Related

- Backend: `~/github/ammonfife/lkup.info` (canonical)
- AGENTS.md in lkup.info has the full execution policy
