#!/usr/bin/env python3
"""
keyword_forecast.py — Get forward-looking keyword forecast metrics via Google Ads API.

Usage:
  keyword_forecast.py --keywords "term1,term2" [--max-cpc-micros 2000000]
"""
import argparse, json, sys
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient

SKILL_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_DIR / "google-ads.yaml"


def main():
    ap = argparse.ArgumentParser(description="Get keyword forecast metrics via Google Ads API")
    ap.add_argument("--keywords", required=True, help="Comma-separated keywords")
    ap.add_argument("--max-cpc-micros", type=int, default=1_000_000, help="Max CPC in micros (default: 1000000 = $1)")
    ap.add_argument("--customer-id", help="Override customer ID")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--config", default=str(CONFIG_PATH))
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        sys.exit("Error: no keywords provided")

    client = GoogleAdsClient.load_from_storage(path=args.config, version="v23")
    kw_plan_idea_service = client.get_service("KeywordPlanIdeaService")

    import yaml
    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    customer_id = args.customer_id or str(cfg.get("login_customer_id", ""))

    request = client.get_type("GenerateKeywordForecastMetricsRequest")
    request.customer_id = customer_id

    campaign = request.campaign
    campaign.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    # Default: next 7 days forecast

    ad_group = client.get_type("ForecastAdGroup")
    for kw in keywords:
        biddable_kw = client.get_type("BiddableKeyword")
        biddable_kw.keyword.text = kw
        biddable_kw.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        biddable_kw.max_cpc_bid_micros = args.max_cpc_micros
        ad_group.biddable_keywords.append(biddable_kw)
    campaign.ad_groups.append(ad_group)

    try:
        response = kw_plan_idea_service.generate_keyword_forecast_metrics(request=request)
    except Exception as e:
        sys.exit(f"API error: {e}")

    metrics = response.campaign_forecast_metrics
    result = {
        "impressions": metrics.impressions if metrics.impressions else 0,
        "clicks": metrics.clicks if metrics.clicks else 0,
        "cost_micros": metrics.cost_micros if metrics.cost_micros else 0,
        "ctr": metrics.ctr if metrics.ctr else 0,
        "avg_cpc_micros": metrics.average_cpc_micros if metrics.average_cpc_micros else 0,
        "conversions": metrics.conversions if metrics.conversions else 0,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Forecast for: {', '.join(keywords)}")
        print(f"  Impressions:  {result['impressions']:,.0f}")
        print(f"  Clicks:       {result['clicks']:,.0f}")
        print(f"  Cost:         ${result['cost_micros']/1_000_000:,.2f}")
        print(f"  CTR:          {result['ctr']:.2%}")
        print(f"  Avg CPC:      ${result['avg_cpc_micros']/1_000_000:.2f}")
        print(f"  Conversions:  {result['conversions']:,.1f}")


if __name__ == "__main__":
    main()
