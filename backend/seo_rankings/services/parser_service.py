"""
SERP parsing service.
Ported from Rankmax: parser.py + parser_json.py
Parses ScrapingDog JSON responses to extract rank position and SERP features.
"""
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def extract_domain(url, remove_http=True):
    """
    Extract domain name from URL.
    Ported from Rankmax parser.py → extract_domain()
    """
    if not url:
        return ''
    uri = urlparse(url)
    if remove_http:
        if uri.netloc:
            domain_name = f"{uri.netloc}".replace("www.", "")
        else:
            domain_division = f"{uri.path}".replace("www.", "").split('/')
            domain_name = domain_division[0] if len(domain_division) > 0 else ''
    else:
        domain_name = f"{uri.netloc}".replace("www.", "")
    return domain_name


def exact_url_scheme(url):
    """Remove scheme from URL for exact comparison."""
    if not url:
        return ''
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1).rstrip("/")


def parse_json_serp_response(json_data, target_url, exact_domain=False):
    """
    Parse ScrapingDog JSON response to find target domain rank.
    Ported from Rankmax parser_json.py → engineParseData()

    Args:
        json_data: ScrapingDog JSON response (merged across pages)
        target_url: The target URL/domain to find rank for
        exact_domain: If True, match exact URL instead of domain

    Returns:
        dict with keys: rank, url, featured_snippet, ads, knowledge_panel,
                       review, total_rating, total_review, snippets_details,
                       competitors, cannibalisation, search_results, today_snippet
    """
    result = {
        'rank': 0,
        'url': target_url,
        'featured_snippet': False,
        'ads': False,
        'knowledge_panel': False,
        'review': False,
        'total_rating': '-',
        'total_review': '-',
        'snippets_details': {},
        'competitors': {'tp': [], 'bf': [], 'ar': []},
        'cannibalisation': [],
        'search_results': '-',
        'today_snippet': {},
    }

    if not json_data or not isinstance(json_data, dict):
        return result

    target_domain = extract_domain(target_url)
    if not target_domain:
        return result

    # Search results count
    search_info = json_data.get('search_information', {})
    if search_info:
        result['search_results'] = str(search_info.get('total_results', '-'))

    # Featured snippet
    featured = json_data.get('featured_snippet', {})
    if featured:
        result['snippets_details']['featured_box'] = {
            'status': 'yes' if featured.get('link', '').find(target_domain) > -1 else 'no',
            'link': featured.get('link', ''),
            'title': featured.get('title', ''),
            'desc': featured.get('description', ''),
        }
        if featured.get('link', '').find(target_domain) > -1:
            result['featured_snippet'] = True

    # Knowledge panel
    knowledge = json_data.get('knowledge_graph', {})
    if knowledge:
        result['snippets_details']['knowledge_box'] = {'present': 'yes'}
        result['knowledge_panel'] = True

    # Ads (top)
    top_ads_data = json_data.get('ads', [])
    if top_ads_data:
        ads_top_list = []
        ad_present = False
        for ad in top_ads_data:
            ad_link = ad.get('link', '')
            ads_top_list.append({
                'link': ad_link,
                'title': ad.get('title', ''),
            })
            if ad_link.find(target_domain) > -1:
                ad_present = True

        if ads_top_list:
            result['snippets_details']['ads'] = {
                'top_result': ads_top_list,
                'bottom_result': [],
                'status': 'yes' if ad_present else 'no',
                'top_count': len(ads_top_list),
                'bottom_count': 0,
                'present': 'top' if ad_present else '',
            }
            result['ads'] = True

    # People Also Ask
    paa = json_data.get('related_questions', [])
    if paa:
        result['snippets_details']['rqrs'] = 'yes'

    # Organic results — find target rank
    organic = json_data.get('organic_results', [])
    domains = []
    cannib = []
    rank_found = 0
    target_max = 10

    for item in organic:
        if not isinstance(item, dict):
            continue

        link = item.get('link', '')
        item_domain = extract_domain(link)
        item_rank = item.get('rank', item.get('position', 0))

        if not item_rank:
            continue

        # Check if this result matches our target
        if rank_found == 0 and link and item_domain:
            matched = False
            if exact_domain:
                if exact_url_scheme(link) == exact_url_scheme(target_url):
                    matched = True
            else:
                if item_domain == target_domain:
                    matched = True

            if matched:
                rank_found = int(item_rank)
                result['rank'] = rank_found
                result['url'] = link

                # Extract rating from snippet
                rating_text = item.get('rich_snippet', {}).get('top', {}).get('extensions', [])
                if rating_text:
                    for ext in rating_text:
                        rating_match = re.search(r'([\d,.]+)', str(ext))
                        if rating_match:
                            try:
                                rating_val = float(rating_match.group(1).replace(',', '.'))
                                if 0 < rating_val <= 5:
                                    result['total_rating'] = str(rating_val)
                                    result['review'] = True
                                    break
                            except (ValueError, TypeError):
                                pass

                # Today's snippet
                result['today_snippet'] = {
                    'lk': link,
                    'tt': item.get('title', ''),
                    'ds': item.get('snippet', ''),
                    'mt': item_domain,
                    'rt': result['total_rating'],
                    'rv': result['total_review'],
                }

        # Track cannibalisation (same domain appearing multiple times)
        if item_domain == target_domain and rank_found > 0:
            if link != result['url']:
                cannib.append(link)

        # Build competitor list
        if link:
            domains.append({
                'rn': str(item_rank),
                'dn': item_domain,
                'lk': link,
            })

        # Once we found the rank and have enough competitors, break
        if rank_found > 0 and int(item_rank) >= rank_found + target_max:
            break

    result['cannibalisation'] = cannib if len(cannib) > 1 else []

    # Build competitor segments
    if domains:
        top = domains[:target_max]
        before = []
        after = []

        if rank_found > 0:
            kw_rank_idx = rank_found - 1
            domain_key_min = max(0, kw_rank_idx - target_max + 1)
            before = domains[domain_key_min:kw_rank_idx]
            after = domains[kw_rank_idx:(kw_rank_idx + target_max)]

        result['competitors'] = {
            'tp': top,
            'bf': before,
            'ar': after,
        }

    return result
