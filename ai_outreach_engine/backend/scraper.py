import requests
from bs4 import BeautifulSoup
import uuid
import re
import json as _json
from urllib.parse import quote_plus, unquote, unquote_plus, urljoin
from concurrent.futures import ThreadPoolExecutor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_legit_email(email: str, domain: str):
    email = email.lower().strip()
    junk = ['bootstrap', 'jquery', 'font-awesome', 'npm', '@1.', '@2.', '@3.',
            'example', 'format', 'template', 'svg', 'png', 'jpg', 'woff', 'ttf']
    if any(p in email for p in junk): return False
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email): return False
    if domain in email: return True
    business_prefixes = ['info@', 'sales@', 'contact@', 'support@', 'admin@',
                         'office@', 'hello@', 'team@', 'enquiry@', 'query@']
    return any(email.startswith(p) for p in business_prefixes)


def _clean_address(raw: str) -> str:
    """Normalize whitespace, commas, and truncate."""
    cleaned = re.sub(r'[\r\n\t]+', ', ', raw)
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip().strip(',').strip()
    return cleaned[:220]


# ---------------------------------------------------------------------------
# Phone extractor
# ---------------------------------------------------------------------------

def _extract_phone_from_soup(soup, raw_html: str) -> str | None:
    """
    Extract a phone number. Priority:
      1. <a href="tel:..."> links
      2. Regex for Indian mobiles / landlines in raw HTML
    Returns in +91XXXXXXXXXX format where possible.
    """
    # 1. tel: links
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.lower().startswith('tel:'):
            digits = re.sub(r'[^\d+]', '', href[4:])
            if len(digits) >= 10:
                return _normalise_phone(digits)

    # 2. Regex patterns (raw HTML avoids stripped whitespace issues)
    patterns = [
        r'\+91[\s\-]?[6-9]\d{2}[\s\-]?\d{3}[\s\-]?\d{4}',   # +91 mobile
        r'\b(?:0[1-9]\d{1,2}[\s\-]?\d{6,8})\b',               # landline with STD
        r'\b[6-9]\d{9}\b',                                      # plain 10-digit mobile
    ]
    for pat in patterns:
        m = re.search(pat, raw_html)
        if m:
            digits = re.sub(r'[^\d]', '', m.group(0))
            if len(digits) >= 10:
                return _normalise_phone(digits)
    return None


def _normalise_phone(digits: str) -> str:
    """Ensure +91 prefix for Indian numbers."""
    digits = re.sub(r'[^\d]', '', digits)
    if digits.startswith('91') and len(digits) == 12:
        return '+' + digits
    if len(digits) == 10 and digits[0] in '6789':
        return '+91' + digits
    return '+' + digits if not digits.startswith('+') else digits


# ---------------------------------------------------------------------------
# Address extractor  (9 strategies, richest-signal first)
# ---------------------------------------------------------------------------

def _extract_address_from_soup(soup, text: str) -> str | None:
    """
    9-strategy address extractor:
      1. Google Maps iframe src  (q= or embed lat/lng text)
      2. JSON-LD schema.org PostalAddress
      3. HTML <address> tag
      4. itemprop="address" / itemprop="streetAddress"
      5. CSS class/id patterns  (address, location, office-addr …)
      6. Label-sibling: find 'Address:' text node → grab next sibling element
      7. Footer section → PIN code neighbourhood
      8. Page-wide PIN code neighbourhood scan
      9. Generic structured-address regex (street-type keyword)
    """

    # ── Strategy 1: Google Maps iframe ──────────────────────────────────────
    for iframe in soup.find_all('iframe'):
        src = (iframe.get('src') or iframe.get('data-src') or
               iframe.get('data-lazy-src') or '')
        if 'google.com/maps' in src or 'maps.google' in src:
            q_m = re.search(r'[?&]q=([^&]+)', src)
            if q_m:
                addr = unquote_plus(q_m.group(1)).replace('+', ' ').strip()
                if len(addr) > 8:
                    return _clean_address(addr)
            # Embedded URL sometimes hides address in !2s<encoded> segment
            pb_m = re.search(r'!2s([^!]+)', src)
            if pb_m:
                addr = unquote_plus(pb_m.group(1)).strip()
                if len(addr) > 8:
                    return _clean_address(addr)

    # ── Strategy 2: JSON-LD schema.org ──────────────────────────────────────
    for script in soup.find_all('script', {'type': 'application/ld+json'}):
        try:
            data = _json.loads(script.string or '')
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # support nested location.address
                addr_obj = (item.get('address') or
                            (item.get('location') or {}).get('address'))
                if isinstance(addr_obj, dict):
                    parts = [addr_obj.get('streetAddress'),
                             addr_obj.get('addressLocality'),
                             addr_obj.get('addressRegion'),
                             addr_obj.get('postalCode'),
                             addr_obj.get('addressCountry')]
                    candidate = ', '.join(p for p in parts if p)
                    if len(candidate) > 10:
                        return _clean_address(candidate)
                elif isinstance(addr_obj, str) and len(addr_obj) > 10:
                    return _clean_address(addr_obj)
        except Exception:
            pass

    # ── Strategy 3: <address> tag ────────────────────────────────────────────
    for addr_tag in soup.find_all('address'):
        candidate = addr_tag.get_text(separator=', ', strip=True)
        if 8 < len(candidate) < 400:
            return _clean_address(candidate)

    # ── Strategy 4: itemprop microdata ──────────────────────────────────────
    for attr_val in ('address', 'streetAddress'):
        tag = soup.find(True, {'itemprop': attr_val})
        if tag:
            candidate = tag.get_text(separator=', ', strip=True)
            if 8 < len(candidate) < 300:
                return _clean_address(candidate)

    # ── Strategy 5: CSS class / id patterns ─────────────────────────────────
    _cls = re.compile(
        r'\b(?:address|location|office[\-_]?addr|our[\-_]?office|'
        r'contact[\-_]?info|footer[\-_]?addr|reach[\-_]?us)\b', re.I)
    for attr in ('class', 'id'):
        for tag in soup.find_all(True, {attr: _cls}):
            candidate = tag.get_text(separator=', ', strip=True)
            # skip nav/menu-like elements
            if 8 < len(candidate) < 350 and candidate.count(',') < 15:
                return _clean_address(candidate)

    # ── Strategy 6: Label-sibling ("Address:" → next element) ───────────────
    _label_re = re.compile(
        r'^\s*(?:Address|Our Office(?:\s+Address)?|Office Address|'
        r'Location|Locate Us|Find Us|Visit Us|Reach Us|Where We Are)\s*:?\s*$', re.I)
    for node in soup.find_all(string=_label_re):
        parent = node.parent
        if not parent:
            continue
        # try following sibling tags
        for sib in parent.next_siblings:
            if hasattr(sib, 'get_text'):
                candidate = sib.get_text(separator=', ', strip=True)
                if 8 < len(candidate) < 300 and not _label_re.match(candidate):
                    return _clean_address(candidate)
                break
        # fallback: grandparent container minus the label text
        if parent.parent:
            full = parent.parent.get_text(separator=' ', strip=True)
            label_stripped = full.replace(node.strip().rstrip(':'), '', 1).strip().lstrip(':').strip()
            if 8 < len(label_stripped) < 300:
                return _clean_address(label_stripped[:250])

    # ── Strategy 7: Footer section → PIN code search ─────────────────────────
    _footer_sel = (soup.find('footer') or
                   soup.find(class_=re.compile(r'\bfooter\b', re.I)) or
                   soup.find(id=re.compile(r'\bfooter\b', re.I)))
    if _footer_sel:
        footer_text = _footer_sel.get_text(separator=' ', strip=True)
        pin_m = re.search(r'([A-Za-z0-9,.\-#\s/]{8,250}?\b\d{6}\b)', footer_text)
        if pin_m:
            candidate = pin_m.group(1)
            if re.search(r'[A-Za-z]{3,}', candidate):
                return _clean_address(candidate)

    # ── Strategy 8: Page-wide PIN code neighbourhood ─────────────────────────
    pin_m = re.search(r'([A-Za-z0-9,.\-#\s/]{8,250}?\b\d{6}\b)', text)
    if pin_m:
        candidate = pin_m.group(1)
        if re.search(r'[A-Za-z]{3,}', candidate):
            return _clean_address(candidate)

    # ── Strategy 9: Generic street-type regex  ───────────────────────────────
    generic = re.compile(
        r'\b(\d{1,5}[,\s]+[A-Z][a-zA-Z\s,.\-]{5,100}'
        r'(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Lane|Ln\.?|'
        r'Drive|Dr\.?|Court|Ct\.?|Floor|Fl\.?|Suite|Ste\.?|'
        r'Nagar|Colony|Marg|Chowk|Vihar|Enclave|Extension|Sector|Phase|'
        r'Building|Tower|Complex|Plaza|Park)'
        r'[,\s]+[A-Za-z\s]{2,40})',
        re.IGNORECASE
    )
    m = generic.search(text)
    if m:
        return _clean_address(m.group(1))

    return None


# ---------------------------------------------------------------------------
# Main intel extractor  (called per page)
# ---------------------------------------------------------------------------

def extract_intel_from_text(raw_html: str):
    """Extracts address, phone, leadership, and LinkedIn from a page."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    # Remove noise BUT keep JSON-LD scripts
    for tag in soup(['script', 'style', 'noscript', 'svg']):
        if tag.name == 'script' and tag.get('type') == 'application/ld+json':
            continue
        tag.decompose()

    text = soup.get_text(separator=' ', strip=True)
    intel = {'address': None, 'phone': None, 'founder': None, 'linkedin': None}

    # 1. Address
    intel['address'] = _extract_address_from_soup(soup, text)
    # Safety: wipe if leaked HTML tags survived
    if intel['address'] and '<' in intel['address']:
        intel['address'] = None

    # 2. Phone
    intel['phone'] = _extract_phone_from_soup(soup, raw_html)

    # 3. LinkedIn
    li_m = re.search(
        r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+', raw_html)
    if li_m:
        intel['linkedin'] = li_m.group(0)

    # 4. Founder / CEO / Director
    exec_m = re.search(
        r'(?:Founder|Co[-\s]?Founder|CEO|Chief Executive|Director|'
        r'Principal|CMD|Managing Director|MD|President)'
        r':?\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})',
        text)
    if exec_m:
        intel['founder'] = exec_m.group(1)

    return intel


# ---------------------------------------------------------------------------
# Per-agency scraper
# ---------------------------------------------------------------------------

def get_agency_detailed_info(url: str, domain: str):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
               'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    data = {'emails': [], 'phone': None,
            'intel': {'address': None, 'phone': None, 'founder': None, 'linkedin': None}}
    try:
        resp = requests.get(url, headers=headers, timeout=6)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # ── Emails ────────────────────────────────────────────────────────
        emails = []
        for a in soup.find_all('a', href=True):
            if a['href'].lower().startswith('mailto:'):
                em = a['href'].lower().replace('mailto:', '').split('?')[0].strip()
                if is_legit_email(em, domain):
                    emails.append(em)
        email_regex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        for e in re.findall(email_regex, resp.text):
            if is_legit_email(e.lower(), domain):
                emails.append(e.lower())
        data['emails'] = list(dict.fromkeys(emails))

        # ── Intel from homepage ───────────────────────────────────────────
        data['intel'] = extract_intel_from_text(resp.text)

        # ── Sub-page crawl (contact > about > team > location) ───────────
        sub_keywords = ['contact', 'about', 'team', 'reach', 'location', 'find-us']
        visited = {url}
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href'].lower()
            if not any(k in href for k in sub_keywords):
                continue
            full_url = urljoin(url, link_tag['href'])
            if full_url in visited:
                continue
            visited.add(full_url)
            try:
                cr = requests.get(full_url, headers=headers, timeout=5)
                # Emails
                for e in re.findall(email_regex, cr.text):
                    if is_legit_email(e.lower(), domain):
                        data['emails'].append(e.lower())
                # Intel – prefer sub-page for address & phone (contact page is best)
                sub = extract_intel_from_text(cr.text)
                if sub['address']:
                    data['intel']['address'] = sub['address']
                if sub['phone']:
                    data['intel']['phone'] = sub['phone']
                if sub['founder']:
                    data['intel']['founder'] = sub['founder']
                if sub['linkedin']:
                    data['intel']['linkedin'] = sub['linkedin']
                # Stop once we have both address and phone
                if data['intel']['address'] and data['intel']['phone']:
                    break
            except Exception:
                continue

        data['emails'] = list(dict.fromkeys(data['emails']))
        # Surface phone to top-level for easy access
        data['phone'] = data['intel'].get('phone')
        return data
    except Exception:
        return data


# ---------------------------------------------------------------------------
# Listicle helpers
# ---------------------------------------------------------------------------

def is_listicle(title: str, link: str):
    patterns = ['top 10', 'top 5', 'best real estate', 'list of', '/blog/',
                '/blogs/', 'article', 'ranking', 'news/', '/public/']
    return any(p in f'{title} {link}'.lower() for p in patterns)


def extract_agencies_from_listicle(url: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    extracted = []
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for h in soup.find_all(['h2', 'h3', 'h4']):
            text = h.text.strip()
            if 3 < len(text) < 50 and not any(
                    x in text.lower() for x in ['top', 'best', 'agent']):
                nxt = h.find_next('a', href=True)
                if nxt and nxt['href'].startswith('http'):
                    link = nxt['href']
                    dm = re.search(r'https?://(?:www\.)?([^/]+)', link)
                    if dm:
                        domain = dm.group(1).split('/')[0].lower()
                        if ('.' in domain and not any(
                                x in domain for x in
                                ['facebook', 'linkedin', 'google', 'propertykumbh'])):
                            extracted.append(
                                {'name': text, 'link': link, 'domain': domain})
    except Exception:
        pass
    return extracted[:10]


def clean_name_ai(title: str, link: str):
    name = title.split('www.')[0].split('http')[0].split('|')[0].split('—')[0].strip()
    # Only split on hyphen if remaining part is meaningful
    parts = name.split('-')
    if len(parts[0].strip()) > 3:
        name = parts[0].strip()
    dm = re.search(r'https?://(?:www\.)?([^/.]+)', link)
    if dm:
        brand = dm.group(1).capitalize()
        if len(name) > 30 or any(x in name.lower() for x in ['best', 'top', 'list', 'news']):
            name = brand
    return name.replace('.com', '').replace('.in', '').strip()


# ---------------------------------------------------------------------------
# Worker + relevance
# ---------------------------------------------------------------------------

def process_worker(candidate):
    domain = candidate['domain']
    result = get_agency_detailed_info(candidate['website'], domain)

    candidate['intel'] = result['intel']
    candidate['phone'] = result.get('phone')          # surface phone to lead

    if result['emails']:
        candidate['email'] = result['emails'][0]
        candidate['status'] = 'Verified Agency'
    else:
        candidate['email'] = f"info@{domain}"
        candidate['status'] = 'Identified'
    return candidate


def is_relevant_agency(text: str):
    keywords = ['real estate', 'property', 'properties', 'realty', 'estates',
                'homes', 'builders', 'developers', 'consultants', 'agency',
                'realtor', 'holdings', 'living', 'constructions', 'infra']
    return any(k in text.lower() for k in keywords)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def trigger_scraping_job(query: str, city: str, db: dict):
    try:
        print(f'🚀 HYPER-NOVA RADAR: Hunt for "{query}" in {city}')
        db['leads'] = []
        seen_domains = set()
        candidates = []

        blacklist = [
            'yahoo', 'google', 'blog', 'news', 'fb.me', 'indiaproperty',
            'justdial', 'magicbricks', 'housing.com', '99acres', 'realtor.com',
            'zillow', 'linkedin', 'facebook', 'youtube', '8kun', 'qresearch',
            'wikipedia', 'business-standard', 'economictimes', 'moneycontrol',
            'commonfloor', 'nobroker', 'sulekha', 'yellowpages', 'indiamart'
        ]

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        search_queries = [
            f'"{city}" real estate agencies',
            f'top real estate companies in {city}',
            f'"{city}" property consultants site contact',
        ]

        for q in search_queries:
            print(f'📡 Scanning: {q}')
            for page in range(3):
                start = page * 10 + 1
                url = f'https://search.yahoo.com/search?p={quote_plus(q)}&b={start}'
                try:
                    resp = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    for item in soup.select('.algo, .algo-sr'):
                        a = item.find('a')
                        if not a:
                            continue
                        link = a['href']
                        title = a.text
                        if '/RU=' in link:
                            try:
                                link = unquote(re.search(r'RU=([^/&]*)', link).group(1))
                            except Exception:
                                pass

                        dm = re.search(r'https?://(?:www\.)?([^/]+)', link)
                        if not dm:
                            continue
                        domain = dm.group(1).split('/')[0].lower()

                        if any(b in domain for b in blacklist) or domain in seen_domains:
                            continue
                        if not is_relevant_agency(title + ' ' + link):
                            continue

                        if is_listicle(title, link):
                            for bl in extract_agencies_from_listicle(link):
                                if (bl['domain'] not in seen_domains and
                                        not any(b in bl['domain'] for b in blacklist)):
                                    candidates.append({
                                        'id': str(uuid.uuid4()),
                                        'company_name': bl['name'],
                                        'website': bl['link'],
                                        'domain': bl['domain'],
                                        'city': city,
                                        'phone': None,
                                        'drafted_email': None,
                                    })
                                    seen_domains.add(bl['domain'])
                            continue

                        candidates.append({
                            'id': str(uuid.uuid4()),
                            'company_name': clean_name_ai(title, link),
                            'website': link,
                            'domain': domain,
                            'city': city,
                            'phone': None,
                            'drafted_email': None,
                        })
                        seen_domains.add(domain)
                        if len(candidates) >= 45:
                            break
                except Exception:
                    continue
            if len(candidates) >= 45:
                break

        print(f'🔥 Harvesting intel for {len(candidates)} candidates...')
        with ThreadPoolExecutor(max_workers=8) as ex:
            leads_processed = list(ex.map(process_worker, candidates))

        # Basic relevance filter
        leads_processed = [l for l in leads_processed if is_relevant_agency(l['company_name'])]

        # City relevance: clear addresses that don't mention the searched city
        city_lower = city.lower()
        for lead in leads_processed:
            addr = (lead.get('intel') or {}).get('address')
            if addr and city_lower not in addr.lower():
                print(f'🗑️  Address mismatch for {lead["company_name"]}: dropping "{addr[:50]}"')
                lead['intel']['address'] = None

        # Completeness scoring
        def score(lead):
            s = 0
            intel = lead.get('intel') or {}
            if lead.get('status') == 'Verified Agency':       s += 2000
            addr = intel.get('address')
            if addr and city_lower in addr.lower():            s += 1500
            if lead.get('phone'):                              s += 1000
            founder = intel.get('founder')
            if founder and founder not in ('Analyzing...', '', None): s += 600
            if intel.get('linkedin'):                          s += 400
            return s

        leads_processed.sort(key=score, reverse=True)
        db['leads'] = leads_processed

    finally:
        db['is_hunting'] = False
        print(f'✅ HARVEST COMPLETE: {len(db["leads"])} agencies identified.')
