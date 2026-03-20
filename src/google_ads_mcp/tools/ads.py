"""Ad management tools — create RSA, display, video, demand gen ads; manage status."""

from __future__ import annotations

from mcp.server.fastmcp import Context

from google.protobuf import field_mask_pb2

from google_ads_mcp.annotations import CREATE, DESTRUCTIVE, READ_ONLY
from google_ads_mcp.helpers import (
    error_response,
    execute_query,
    extract_google_ads_error,
    success_response,
)
from google_ads_mcp.server import get_client, mcp


@mcp.tool(annotations=READ_ONLY)
def list_ads(
    customer_id: str,
    ad_group_id: str,
    ctx: Context,
    status_filter: str | None = None,
    limit: int = 50,
) -> dict:
    """List ads in an ad group with approval status.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID.
        status_filter: Optional -- 'ENABLED', 'PAUSED', or 'REMOVED'.
        limit: Max ads to return (default 50).
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        where_clauses = [f"ad_group.id = {ad_group_id}"]
        if status_filter:
            where_clauses.append(f"ad_group_ad.status = '{status_filter}'")
        else:
            where_clauses.append("ad_group_ad.status != 'REMOVED'")

        where = " AND ".join(where_clauses)
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.ad.name,
                ad_group_ad.status,
                ad_group_ad.ad.final_urls,
                ad_group_ad.policy_summary.approval_status,
                ad_group.id,
                ad_group.name
            FROM ad_group_ad
            WHERE {where}
            LIMIT {limit}
        """
        results = execute_query(client, cid, query)
        return success_response(
            data={"ads": results, "count": len(results)},
            message=f"Found {len(results)} ad(s)",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def create_responsive_search_ad(
    customer_id: str,
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    final_urls: list[str],
    ctx: Context,
    path1: str | None = None,
    path2: str | None = None,
    status: str = "ENABLED",
) -> dict:
    """Create a Responsive Search Ad (RSA) for Search campaigns.

    Google will automatically test combinations of headlines and descriptions.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID (must be in a Search campaign).
        headlines: 3-15 headline strings (max 30 chars each).
        descriptions: 2-4 description strings (max 90 chars each).
        final_urls: List of landing page URLs (at least one required).
        path1: Optional display URL path 1 (max 15 chars).
        path2: Optional display URL path 2 (max 15 chars, requires path1).
        status: Ad status -- 'ENABLED' (default) or 'PAUSED'.
    """
    if len(headlines) < 3:
        return error_response("RSA requires at least 3 headlines (max 15).")
    if len(headlines) > 15:
        return error_response("RSA allows at most 15 headlines.")
    if len(descriptions) < 2:
        return error_response("RSA requires at least 2 descriptions (max 4).")
    if len(descriptions) > 4:
        return error_response("RSA allows at most 4 descriptions.")
    if not final_urls:
        return error_response("At least one final URL is required.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_ad_service = client.get_service("AdGroupAdService")

        op = client.client.operation("create", "AdGroupAd")
        ad_group_ad = op.create
        ad_group_ad.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)

        status_enum = client.get_type("AdGroupAdStatusEnum").AdGroupAdStatus
        ad_group_ad.status = getattr(status_enum, status)

        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        for headline_text in headlines:
            headline = client.get_type("AdTextAsset")
            headline.text = headline_text
            ad.responsive_search_ad.headlines.append(headline)

        for desc_text in descriptions:
            desc = client.get_type("AdTextAsset")
            desc.text = desc_text
            ad.responsive_search_ad.descriptions.append(desc)

        if path1:
            ad.responsive_search_ad.path1 = path1
        if path2:
            ad.responsive_search_ad.path2 = path2

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"RSA created with {len(headlines)} headlines, {len(descriptions)} descriptions",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def create_responsive_display_ad(
    customer_id: str,
    ad_group_id: str,
    headlines: list[str],
    long_headline: str,
    descriptions: list[str],
    marketing_images: list[str],
    square_marketing_images: list[str],
    logo_images: list[str],
    business_name: str,
    final_urls: list[str],
    ctx: Context,
    call_to_action_text: str | None = None,
    status: str = "ENABLED",
) -> dict:
    """Create a Responsive Display Ad for Display campaigns.

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID (must be in a Display campaign).
        headlines: 1-5 short headlines (max 30 chars each).
        long_headline: Long headline (max 90 chars).
        descriptions: 1-5 descriptions (max 90 chars each).
        marketing_images: List of landscape image asset resource names (1200x628).
        square_marketing_images: List of square image asset resource names (1200x1200).
        logo_images: List of logo asset resource names.
        business_name: Business name (max 25 chars).
        final_urls: Landing page URLs.
        call_to_action_text: Optional CTA text.
        status: Ad status -- 'ENABLED' (default) or 'PAUSED'.
    """
    if not headlines:
        return error_response("At least 1 headline is required.")
    if not descriptions:
        return error_response("At least 1 description is required.")
    if not marketing_images:
        return error_response("At least 1 marketing image asset is required.")
    if not final_urls:
        return error_response("At least 1 final URL is required.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_ad_service = client.get_service("AdGroupAdService")

        op = client.client.operation("create", "AdGroupAd")
        ad_group_ad = op.create
        ad_group_ad.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)

        status_enum = client.get_type("AdGroupAdStatusEnum").AdGroupAdStatus
        ad_group_ad.status = getattr(status_enum, status)

        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        rda = ad.responsive_display_ad
        rda.business_name = business_name
        rda.long_headline.text = long_headline

        for h in headlines:
            asset = client.get_type("AdTextAsset")
            asset.text = h
            rda.headlines.append(asset)

        for d in descriptions:
            asset = client.get_type("AdTextAsset")
            asset.text = d
            rda.descriptions.append(asset)

        for img in marketing_images:
            image_asset = client.get_type("AdImageAsset")
            image_asset.asset = img
            rda.marketing_images.append(image_asset)

        for img in square_marketing_images:
            image_asset = client.get_type("AdImageAsset")
            image_asset.asset = img
            rda.square_marketing_images.append(image_asset)

        for img in logo_images:
            image_asset = client.get_type("AdImageAsset")
            image_asset.asset = img
            rda.logo_images.append(image_asset)

        if call_to_action_text:
            rda.call_to_action_text = call_to_action_text

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message="Responsive Display Ad created successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def create_video_ad(
    customer_id: str,
    ad_group_id: str,
    youtube_video_id: str,
    final_urls: list[str],
    ctx: Context,
    headline: str | None = None,
    description: str | None = None,
    call_to_action_text: str | None = None,
    ad_format: str = "IN_STREAM",
    companion_banner_asset: str | None = None,
    status: str = "ENABLED",
) -> dict:
    """Create a Video ad for Video campaigns (YouTube).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID (must be in a Video campaign).
        youtube_video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ').
        final_urls: Landing page URLs.
        headline: Optional headline for the ad.
        description: Optional description.
        call_to_action_text: CTA button text (e.g., 'Learn More', 'Shop Now').
        ad_format: Video ad format -- 'IN_STREAM' (skippable), 'BUMPER' (6-sec non-skip),
            'IN_FEED' (discovery/in-feed).
        companion_banner_asset: Optional companion banner image asset resource name.
        status: Ad status -- 'ENABLED' (default) or 'PAUSED'.
    """
    if not youtube_video_id:
        return error_response("youtube_video_id is required.")
    if not final_urls:
        return error_response("At least 1 final URL is required.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_ad_service = client.get_service("AdGroupAdService")

        op = client.client.operation("create", "AdGroupAd")
        ad_group_ad = op.create
        ad_group_ad.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)

        status_enum = client.get_type("AdGroupAdStatusEnum").AdGroupAdStatus
        ad_group_ad.status = getattr(status_enum, status)

        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        video_ad = ad.video_ad
        video_ad.video.asset = f"customers/{cid}/assets/{youtube_video_id}"

        if ad_format == "IN_STREAM":
            if headline:
                video_ad.in_stream.action_headline = headline
            if companion_banner_asset:
                video_ad.in_stream.companion_banner.asset = companion_banner_asset
        elif ad_format == "BUMPER":
            if companion_banner_asset:
                video_ad.bumper.companion_banner.asset = companion_banner_asset
        elif ad_format == "IN_FEED":
            if headline:
                video_ad.in_feed.headline = headline
            if description:
                video_ad.in_feed.description1 = description

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Video ad ({ad_format}) created successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=CREATE)
def create_demand_gen_ad(
    customer_id: str,
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    marketing_images: list[str],
    logo_images: list[str],
    final_urls: list[str],
    business_name: str,
    ctx: Context,
    call_to_action_text: str | None = None,
    status: str = "ENABLED",
) -> dict:
    """Create a Demand Gen ad (serves on YouTube, Gmail, Discover).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID (must be in a Demand Gen campaign).
        headlines: 1-5 headlines (max 40 chars each).
        descriptions: 1-5 descriptions (max 90 chars each).
        marketing_images: Landscape image asset resource names.
        logo_images: Logo asset resource names.
        final_urls: Landing page URLs.
        business_name: Business name.
        call_to_action_text: Optional CTA text.
        status: Ad status -- 'ENABLED' (default) or 'PAUSED'.
    """
    if not headlines:
        return error_response("At least 1 headline is required.")
    if not descriptions:
        return error_response("At least 1 description is required.")
    if not marketing_images:
        return error_response("At least 1 marketing image is required.")
    if not final_urls:
        return error_response("At least 1 final URL is required.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_service = client.get_service("AdGroupService")
        ad_group_ad_service = client.get_service("AdGroupAdService")

        op = client.client.operation("create", "AdGroupAd")
        ad_group_ad = op.create
        ad_group_ad.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)

        status_enum = client.get_type("AdGroupAdStatusEnum").AdGroupAdStatus
        ad_group_ad.status = getattr(status_enum, status)

        ad = ad_group_ad.ad
        ad.final_urls.extend(final_urls)

        demand_gen_ad = ad.demand_gen_multi_asset_ad
        demand_gen_ad.business_name = business_name

        for h in headlines:
            asset = client.get_type("AdTextAsset")
            asset.text = h
            demand_gen_ad.headlines.append(asset)

        for d in descriptions:
            asset = client.get_type("AdTextAsset")
            asset.text = d
            demand_gen_ad.descriptions.append(asset)

        for img in marketing_images:
            image_asset = client.get_type("AdImageAsset")
            image_asset.asset = img
            demand_gen_ad.marketing_images.append(image_asset)

        for img in logo_images:
            image_asset = client.get_type("AdImageAsset")
            image_asset.asset = img
            demand_gen_ad.logo_images.append(image_asset)

        if call_to_action_text:
            demand_gen_ad.call_to_action_text = call_to_action_text

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message="Demand Gen ad created successfully",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=DESTRUCTIVE)
def set_ad_status(
    customer_id: str,
    ad_group_id: str,
    ad_id: str,
    status: str,
    ctx: Context,
) -> dict:
    """Set an ad's status (enable, pause, or remove).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID containing the ad.
        ad_id: Ad ID.
        status: New status -- 'ENABLED', 'PAUSED', or 'REMOVED'.
    """
    if status not in ("ENABLED", "PAUSED", "REMOVED"):
        return error_response(f"Invalid status '{status}'. Must be ENABLED, PAUSED, or REMOVED.")

    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)

        ad_group_ad_service = client.get_service("AdGroupAdService")

        op = client.client.operation("update", "AdGroupAd")
        ad_group_ad = op.update
        ad_group_ad.resource_name = ad_group_ad_service.ad_group_ad_path(
            cid, ad_group_id, ad_id
        )
        status_enum = client.get_type("AdGroupAdStatusEnum").AdGroupAdStatus
        ad_group_ad.status = getattr(status_enum, status)

        op.update_mask.CopyFrom(
            field_mask_pb2.FieldMask(paths=["status"])
        )

        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=cid, operations=[op]
        )
        return success_response(
            data={"resource_name": response.results[0].resource_name},
            message=f"Ad {ad_id} status set to {status}",
        )
    except Exception as e:
        return error_response(extract_google_ads_error(e))


@mcp.tool(annotations=READ_ONLY)
def get_ad_details(
    customer_id: str,
    ad_group_id: str,
    ad_id: str,
    ctx: Context,
) -> dict:
    """Get full details of an ad (headlines, descriptions, URLs, assets).

    Args:
        customer_id: Google Ads customer ID.
        ad_group_id: Ad group ID containing the ad.
        ad_id: Ad ID.
    """
    try:
        client = get_client(ctx)
        cid = client.resolve_customer_id(customer_id)
        query = f"""
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.ad.name,
                ad_group_ad.status,
                ad_group_ad.ad.final_urls,
                ad_group_ad.ad.final_mobile_urls,
                ad_group_ad.ad.tracking_url_template,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions,
                ad_group_ad.ad.responsive_search_ad.path1,
                ad_group_ad.ad.responsive_search_ad.path2,
                ad_group_ad.ad_strength,
                ad_group_ad.policy_summary.approval_status,
                ad_group_ad.policy_summary.review_status,
                ad_group.id,
                ad_group.name,
                campaign.id,
                campaign.name
            FROM ad_group_ad
            WHERE ad_group.id = {ad_group_id}
                AND ad_group_ad.ad.id = {ad_id}
        """
        results = execute_query(client, cid, query)
        if not results:
            return error_response(f"Ad {ad_id} not found in ad group {ad_group_id}")
        return success_response(data=results[0])
    except Exception as e:
        return error_response(extract_google_ads_error(e))
