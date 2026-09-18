import os
import re
import certifi
import airportsdata
import pycountry
import requests
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
DEFAULT_ORIGIN_IATA = os.getenv("DEFAULT_ORIGIN_IATA", "DAC")
BASE_URL = "https://api.aviationstack.com/v1/flights"

AIRPORTS = airportsdata.load("IATA")

COUNTRY_ALIASES = {
    "USA": "US",
    "United States": "US",
    "UK": "GB",
    "United Kingdom": "GB",
    "UAE": "AE",
    "United Arab Emirates": "AE",
    "India": "IN",
    "Canada": "CA",
    "Australia": "AU",
    "New Zealand": "NZ",
    "Japan": "JP",
    "China": "CN",
    "South Korea": "KR",
    "Singapore": "SG",
    "Thailand": "TH",
    "Malaysia": "MY",
    "Indonesia": "ID",
    "Vietnam": "VN",
    "Philippines": "PH",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "Bangladesh": "BD",
    "Pakistan": "PK",
    "Saudi Arabia": "SA",
    "Qatar": "QA",
    "Oman": "OM",
    "Kuwait": "KW",
    "Bahrain": "BH",
    "Turkey": "TR",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Portugal": "PT",
    "Netherlands": "NL",
    "Switzerland": "CH",
    "Austria": "AT",
    "Belgium": "BE",
    "Greece": "GR",
    "Ireland": "IE",
    "Russia": "RU",
    "Ukraine": "UA",
    "Poland": "PL",
    "Norway": "NO",
    "Sweden": "SE",
    "Denmark": "DK",
    "Finland": "FI",
    "Iceland": "IS",
    "Brazil": "BR",
    "Argentina": "AR",
    "Mexico": "MX",
    "South Africa": "ZA",
    "Egypt": "EG",
    "Morocco": "MA",
    "Kenya": "KE",
    "Nigeria": "NG",
}

COUNTRY_MAIN_AIRPORT = {
    "AF": "KBL",  # Afghanistan
    "AL": "TIA",  # Albania
    "DZ": "ALG",  # Algeria
    "AD": "LEU",  # Andorra
    "AO": "LAD",  # Angola
    "AG": "ANU",  # Antigua and Barbuda
    "AR": "EZE",  # Argentina
    "AM": "EVN",  # Armenia
    "AU": "SYD",  # Australia
    "AT": "VIE",  # Austria
    "AZ": "GYD",  # Azerbaijan

    "BS": "NAS",  # Bahamas
    "BH": "BAH",  # Bahrain
    "BD": "DAC",  # Bangladesh
    "BB": "BGI",  # Barbados
    "BY": "MSQ",  # Belarus
    "BE": "BRU",  # Belgium
    "BZ": "BZE",  # Belize
    "BJ": "COO",  # Benin
    "BT": "PBH",  # Bhutan
    "BO": "VVI",  # Bolivia
    "BA": "SJJ",  # Bosnia and Herzegovina
    "BW": "GBE",  # Botswana
    "BR": "GRU",  # Brazil
    "BN": "BWN",  # Brunei
    "BG": "SOF",  # Bulgaria
    "BF": "OUA",  # Burkina Faso
    "BI": "BJM",  # Burundi

    "KH": "PNH",  # Cambodia
    "CM": "NSI",  # Cameroon
    "CA": "YYZ",  # Canada
    "CV": "RAI",  # Cape Verde
    "CF": "BGF",  # Central African Republic
    "TD": "NDJ",  # Chad
    "CL": "SCL",  # Chile
    "CN": "PEK",  # China
    "CO": "BOG",  # Colombia
    "KM": "HAH",  # Comoros
    "CG": "BZV",  # Congo
    "CD": "FIH",  # DR Congo
    "CR": "SJO",  # Costa Rica
    "CI": "ABJ",  # Ivory Coast
    "HR": "ZAG",  # Croatia
    "CU": "HAV",  # Cuba
    "CY": "LCA",  # Cyprus
    "CZ": "PRG",  # Czech Republic

    "DK": "CPH",  # Denmark
    "DJ": "JIB",  # Djibouti
    "DM": "DOM",  # Dominica
    "DO": "SDQ",  # Dominican Republic

    "EC": "UIO",  # Ecuador
    "EG": "CAI",  # Egypt
    "SV": "SAL",  # El Salvador
    "GQ": "SSG",  # Equatorial Guinea
    "ER": "ASM",  # Eritrea
    "EE": "TLL",  # Estonia
    "SZ": "SHO",  # Eswatini
    "ET": "ADD",  # Ethiopia

    "FJ": "NAN",  # Fiji
    "FI": "HEL",  # Finland
    "FR": "CDG",  # France

    "GA": "LBV",  # Gabon
    "GM": "BJL",  # Gambia
    "GE": "TBS",  # Georgia
    "DE": "FRA",  # Germany
    "GH": "ACC",  # Ghana
    "GR": "ATH",  # Greece
    "GD": "GND",  # Grenada
    "GT": "GUA",  # Guatemala
    "GN": "CKY",  # Guinea
    "GW": "OXB",  # Guinea-Bissau
    "GY": "GEO",  # Guyana

    "HT": "PAP",  # Haiti
    "HN": "SAP",  # Honduras
    "HU": "BUD",  # Hungary

    "IS": "KEF",  # Iceland
    "IN": "DEL",  # India
    "ID": "CGK",  # Indonesia
    "IR": "IKA",  # Iran
    "IQ": "BGW",  # Iraq
    "IE": "DUB",  # Ireland
    "IL": "TLV",  # Israel
    "IT": "FCO",  # Italy

    "JM": "KIN",  # Jamaica
    "JP": "HND",  # Japan
    "JO": "AMM",  # Jordan

    "KZ": "NQZ",  # Kazakhstan
    "KE": "NBO",  # Kenya
    "KI": "TRW",  # Kiribati
    "KP": "FNJ",  # North Korea
    "KR": "ICN",  # South Korea
    "KW": "KWI",  # Kuwait
    "KG": "FRU",  # Kyrgyzstan

    "LA": "VTE",  # Laos
    "LV": "RIX",  # Latvia
    "LB": "BEY",  # Lebanon
    "LS": "MSU",  # Lesotho
    "LR": "ROB",  # Liberia
    "LY": "TIP",  # Libya
    "LI": "ZRH",  # Liechtenstein
    "LT": "VNO",  # Lithuania
    "LU": "LUX",  # Luxembourg

    "MG": "TNR",  # Madagascar
    "MW": "LLW",  # Malawi
    "MY": "KUL",  # Malaysia
    "MV": "MLE",  # Maldives
    "ML": "BKO",  # Mali
    "MT": "MLA",  # Malta
    "MH": "MAJ",  # Marshall Islands
    "MR": "NKC",  # Mauritania
    "MU": "MRU",  # Mauritius
    "MX": "MEX",  # Mexico
    "FM": "PNI",  # Micronesia
    "MD": "KIV",  # Moldova
    "MC": "NCE",  # Monaco
    "MN": "UBN",  # Mongolia
    "ME": "TGD",  # Montenegro
    "MA": "CMN",  # Morocco
    "MZ": "MPM",  # Mozambique
    "MM": "RGN",  # Myanmar

    "NA": "WDH",  # Namibia
    "NR": "INU",  # Nauru
    "NP": "KTM",  # Nepal
    "NL": "AMS",  # Netherlands
    "NZ": "AKL",  # New Zealand
    "NI": "MGA",  # Nicaragua
    "NE": "NIM",  # Niger
    "NG": "LOS",  # Nigeria
    "MK": "SKP",  # North Macedonia
    "NO": "OSL",  # Norway

    "OM": "MCT",  # Oman

    "PK": "ISB",  # Pakistan
    "PW": "ROR",  # Palau
    "PA": "PTY",  # Panama
    "PG": "POM",  # Papua New Guinea
    "PY": "ASU",  # Paraguay
    "PE": "LIM",  # Peru
    "PH": "MNL",  # Philippines
    "PL": "WAW",  # Poland
    "PT": "LIS",  # Portugal

    "QA": "DOH",  # Qatar

    "RO": "OTP",  # Romania
    "RU": "SVO",  # Russia
    "RW": "KGL",  # Rwanda

    "KN": "SKB",  # Saint Kitts and Nevis
    "LC": "UVF",  # Saint Lucia
    "VC": "SVD",  # Saint Vincent and the Grenadines
    "WS": "APW",  # Samoa
    "SM": "RMI",  # San Marino
    "ST": "TMS",  # São Tomé and Príncipe
    "SA": "RUH",  # Saudi Arabia
    "SN": "DSS",  # Senegal
    "RS": "BEG",  # Serbia
    "SC": "SEZ",  # Seychelles
    "SL": "FNA",  # Sierra Leone
    "SG": "SIN",  # Singapore
    "SK": "BTS",  # Slovakia
    "SI": "LJU",  # Slovenia
    "SB": "HIR",  # Solomon Islands
    "SO": "MGQ",  # Somalia
    "ZA": "JNB",  # South Africa
    "SS": "JUB",  # South Sudan
    "ES": "MAD",  # Spain
    "LK": "CMB",  # Sri Lanka
    "SD": "KRT",  # Sudan
    "SR": "PBM",  # Suriname
    "SE": "ARN",  # Sweden
    "CH": "ZRH",  # Switzerland
    "SY": "DAM",  # Syria

    "TW": "TPE",  # Taiwan
    "TJ": "DYU",  # Tajikistan
    "TZ": "DAR",  # Tanzania
    "TH": "BKK",  # Thailand
    "TL": "DIL",  # Timor-Leste
    "TG": "LFW",  # Togo
    "TO": "TBU",  # Tonga
    "TT": "POS",  # Trinidad and Tobago
    "TN": "TUN",  # Tunisia
    "TR": "IST",  # Turkey
    "TM": "ASB",  # Turkmenistan
    "TV": "FUN",  # Tuvalu

    "UG": "EBB",  # Uganda
    "UA": "KBP",  # Ukraine
    "AE": "DXB",  # United Arab Emirates
    "GB": "LHR",  # United Kingdom
    "US": "ATL",  # United States
    "UY": "MVD",  # Uruguay
    "UZ": "TAS",  # Uzbekistan

    "VU": "VLI",  # Vanuatu
    "VA": "FCO",  # Vatican City
    "VE": "CCS",  # Venezuela
    "VN": "SGN",  # Vietnam

    "YE": "SAH",  # Yemen
    "ZM": "LUN",  # Zambia
    "ZW": "HRE",  # Zimbabwe
}

CITY_MAIN_AIRPORT = {
    # India
    "Hyderabad": "HYD",
    "Delhi": "DEL",
    "Mumbai": "BOM",
    "Bangalore": "BLR",
    "Chennai": "MAA",
    "Kolkata": "CCU",
    "Pune": "PNQ",
    "Ahmedabad": "AMD",
    "Goa": "GOI",
    "Jaipur": "JAI",
    "Kochi": "COK",
    "Lucknow": "LKO",
    "Visakhapatnam": "VTZ",
    "Bhubaneswar": "BBI",
    "Chandigarh": "IXC",
    "Indore": "IDR",
    "Varanasi": "VNS",
    "Amritsar": "ATQ",
    "Patna": "PAT",
    "Nagpur": "NAG",

    # USA
    "New York": "JFK",
    "Los Angeles": "LAX",
    "Chicago": "ORD",
    "San Francisco": "SFO",
    "Miami": "MIA",
    "Dallas": "DFW",
    "Houston": "IAH",
    "Atlanta": "ATL",
    "Boston": "BOS",
    "Seattle": "SEA",
    "Washington": "IAD",
    "Las Vegas": "LAS",
    "Orlando": "MCO",
    "Denver": "DEN",
    "Phoenix": "PHX",

    # UK
    "London": "LHR",
    "Manchester": "MAN",
    "Birmingham": "BHX",
    "Edinburgh": "EDI",
    "Glasgow": "GLA",
    "Liverpool": "LPL",

    # UAE
    "Dubai": "DXB",
    "Abu Dhabi": "AUH",
    "Sharjah": "SHJ",

    # Canada
    "Toronto": "YYZ",
    "Vancouver": "YVR",
    "Montreal": "YUL",
    "Calgary": "YYC",
    "Ottawa": "YOW",

    # Australia
    "Sydney": "SYD",
    "Melbourne": "MEL",
    "Brisbane": "BNE",
    "Perth": "PER",
    "Adelaide": "ADL",

    # Europe
    "Paris": "CDG",
    "London": "LHR",
    "Frankfurt": "FRA",
    "Berlin": "BER",
    "Munich": "MUC",
    "Rome": "FCO",
    "Milan": "MXP",
    "Madrid": "MAD",
    "Barcelona": "BCN",
    "Lisbon": "LIS",
    "Amsterdam": "AMS",
    "Brussels": "BRU",
    "Vienna": "VIE",
    "Zurich": "ZRH",
    "Athens": "ATH",
    "Dublin": "DUB",
    "Prague": "PRG",
    "Warsaw": "WAW",
    "Stockholm": "ARN",
    "Oslo": "OSL",
    "Copenhagen": "CPH",
    "Helsinki": "HEL",
    "Istanbul": "IST",
    "Moscow": "SVO",

    # Asia
    "Tokyo": "HND",
    "Osaka": "KIX",
    "Beijing": "PEK",
    "Shanghai": "PVG",
    "Seoul": "ICN",
    "Singapore": "SIN",
    "Bangkok": "BKK",
    "Kuala Lumpur": "KUL",
    "Jakarta": "CGK",
    "Bali": "DPS",
    "Manila": "MNL",
    "Ho Chi Minh City": "SGN",
    "Hanoi": "HAN",
    "Taipei": "TPE",
    "Hong Kong": "HKG",

    # Middle East
    "Doha": "DOH",
    "Riyadh": "RUH",
    "Jeddah": "JED",
    "Muscat": "MCT",
    "Kuwait City": "KWI",
    "Manama": "BAH",
    "Beirut": "BEY",
    "Amman": "AMM",
    "Cairo": "CAI",

    # South Asia
    "Dhaka": "DAC",
    "Kathmandu": "KTM",
    "Colombo": "CMB",
    "Islamabad": "ISB",
    "Karachi": "KHI",
    "Lahore": "LHE",
    "Male": "MLE",

    # Africa
    "Johannesburg": "JNB",
    "Cape Town": "CPT",
    "Nairobi": "NBO",
    "Lagos": "LOS",
    "Accra": "ACC",
    "Casablanca": "CMN",
    "Addis Ababa": "ADD",

    # South America
    "São Paulo": "GRU",
    "Rio de Janeiro": "GIG",
    "Buenos Aires": "EZE",
    "Lima": "LIM",
    "Bogotá": "BOG",
    "Santiago": "SCL",
    "Quito": "UIO",
    "Caracas": "CCS",

    # Mexico / Central America
    "Mexico City": "MEX",
    "Cancun": "CUN",
    "Panama City": "PTY",
    "San José": "SJO",

    # New Zealand
    "Auckland": "AKL",
    "Wellington": "WLG",
    "Christchurch": "CHC",
}



def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    stop_words = [
        "flight", "flights", "ticket", "tickets", "trip", "travel", 
        "plan", "complete", "days", "day", "including", "hotel", "hotels", 
        "sightseeing", "under", "budget", "info", "information"
    ]

    words = [w for w in text.split() if w not in stop_words]
    return " ".join(words).strip()

def country_name_to_code(text: str):
    text = clean_text(text)

    if text in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[text]

    try:
        country = pycountry.countries.lookup(text)
        return country.alpha_2
    except LookupError:
        pass

    # Detect country name inside longer text
    for country in pycountry.countries:
        country_name = country.name.lower()
        if country_name in text:
            return country.alpha_2

    for alias, code in COUNTRY_ALIASES.items():
        if alias in text:
            return code

    return None

def airport_country_matches(airport: dict, country_code: str) -> bool:
    airport_country = str(airport.get(alpha_2=country_code)).upper().strip()

    if airport_country == country_code:
        return True

    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country and airport_country.lower() == country.name.lower():
            return True
    except Exception:
        pass

    return False


def get_best_airport_for_country(country_code: str):
    preferred = COUNTRY_MAIN_AIRPORT.get(country_code)

    if preferred and preferred in AIRPORTS:
        return preferred

    candidates = []

    for iata, airport in AIRPORTS.items():
        if not iata:
            continue

        if airport_country_matches(airport, country_code):
            name = str(airport.get("name", "")).lower()
            city = str(airport.get("city", "")).lower()

            score = 0

            if "international" in name:
                score += 50
            if "intl" in name:
                score += 40
            if "capital" in name:
                score += 20
            if city:
                score += 5

            candidates.append((score, iata))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][1]

def resolve_location_to_iata(location: str):
    """
    Converts country/city/airport/IATA into IATA code.

    Examples:
    Bangladesh -> DAC
    Japan -> NRT
    Dhaka -> DAC
    Tokyo -> NRT
    DAC -> DAC
    """

    if not location:
        return None

    raw_location = location.strip()

    # Direct IATA code
    if re.fullmatch(r"[A-Za-z]{3}", raw_location):
        code = raw_location.upper()
        if code in AIRPORTS:
            return code

    location_clean = clean_text(raw_location)

    if not location_clean:
        return None

    # City preferred airport
    if location_clean in CITY_MAIN_AIRPORT:
        return CITY_MAIN_AIRPORT[location_clean]

    # Country preferred airport
    country_code = country_name_to_code(location_clean)
    if country_code:
        airport = get_best_airport_for_country(country_code)
        if airport:
            return airport

    # Exact city match from airport database
    city_matches = []

    for iata, airport in AIRPORTS.items():
        city = str(airport.get("city", "")).lower().strip()
        name = str(airport.get("name", "")).lower().strip()

        score = 0

        if city == location_clean:
            score += 100
        elif location_clean in city:
            score += 70

        if location_clean in name:
            score += 50

        if "international" in name:
            score += 10

        if score > 0:
            city_matches.append((score, iata))

    if city_matches:
        city_matches.sort(reverse=True)
        return city_matches[0][1]

    return None

def find_location_mentions(query: str):
    """
    Finds country or city names inside a natural language query.
    """

    q = query.lower()
    mentions = []

    # Country aliases
    for alias in COUNTRY_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", q):
            mentions.append(alias)

    # Country names from pycountry
    for country in pycountry.countries:
        name = country.name.lower()
        if len(name) >= 4 and re.search(rf"\b{re.escape(name)}\b", q):
            mentions.append(name)

    # City names from our preferred city map
    for city in CITY_MAIN_AIRPORT:
        if re.search(rf"\b{re.escape(city)}\b", q):
            mentions.append(city)

    # Remove duplicate while keeping order
    unique_mentions = []
    for item in mentions:
        if item not in unique_mentions:
            unique_mentions.append(item)

    return unique_mentions


def parse_route(query: str):
    """
    Returns:
    dep_iata, arr_iata

    Can return:
    None, None  -> gloabal live flights
    DAC, NRT    -> filtered route
    DAC, None   -> all flights: from DAC
    None, NRT   -> all flights to NRT
    """

    q = query.strip()
    q_lower = q.lower()

    # Global / all-country query
    global_keywords = [
        "all country",
        "all countries",
        "global flight",
        "global flights",
        "all flight",
        "all flights",
        "worldwide flight",
        "worldwide flights",
    ]

    if any(keyword in q_lower for keyword in global_keywords):
        return None, None

    # # Direct IATA code route DAC to NRT
    # codes = re.findall(r"\b[A-Z]{3}\b")

    # if len(codes) >= 2:
    #     dep = codes[0].upper()
    #     arr = codes[1].upper()
    #     return dep, arr

    # # Pattern: from X to Y
    # match = re.search(
    #     r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
    #     q_lower,
    # )


    # Direct IATA code route DAC to NRT
    codes = re.findall(r"\b[A-Z]{3}\b", q)

    if len(codes) >= 2:
        dep = codes[0].upper()
        arr = codes[1].upper()
        return dep, arr

    # Pattern: from X to Y
    match = re.search(
        r"\bfrom\s+(.+?)\s+\bto\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower,
    )




    if match:
        origin_text = match.group(1)
        dest_text = match.group(2)

        dep_iata = resolve_location_to_iata(origin_text)
        arr_iata = resolve_location_to_iata(dest_text)

        return dest_text, arr_iata

    # Pattern: to Y from X
    match = re.search(
        r"\bto\s+(.+?)\s+\bfrom\s+(.+?)(?:\s+(?:on|for|under|including|with|in|at)\b|[.!?]|$)",
        q_lower
    )

    if match:
        origin_text = match.group(1)
        dep_iata = resolve_location_to_iata(origin_text)
        return dep_iata, None


    # Pattern: flights to X
    match = re.search(r"\bto\s+(.+?)(?:[.!?]|$)", q_lower)

    if match:
        dest_text = match.group(1)
        arr_iata = resolve_location_to_iata(dep_iata)
        return None, arr_iata

    # Fallback: find country/city mentions
    mentions = find_location_mentions(q)


    if len(mentions) >= 2:
        dep_iata = resolve_location_to_iata(mentions[0])
        arr_iata = resolve_location_to_iata(mentions[1])
        return dep_iata, arr_iata

    if len(mentions) == 1:
        arr_iata = resolve_location_to_iata(mentions[0])
        return DEFAULT_ORIGIN_IATA, arr_iata

    return None, None

def format_flight(flight: dict):
    airline = flight.get("airline", {}).get("name") or "Unknown airline"
    flight_number = flight.get("flight", {}).get("iata") or "Unknown flight number"
    status = flight.get("flight_status") or "Unknown"

    dep = flight.get("departure", {}) or {}
    arr = flight.get("arrival", {}) or {}

    dep_airport = dep.get("airport") or "Unknown departure airport"
    dep_iata = dep.get("iara") or "Unknown"
    dep_terminal = dep.get("terminal") or "N/A"
    dep_gate = dep.get("gate") or "N/A"
    dep_scheduled = dep.get("scheduled") or "Unknown"
    dep_delay = dep.get("delay")
    dep_delay_text = f"{dep_delay} minutes" if dep_delay is not None else "N/A"

    arr_airport = arr.get("airport") or "Unknown arrival airport"
    arr_iata = arr.get("iata") or "Unknown"
    arr_terminal = arr.get("terminal") or "N/A"
    arr_gate = arr.get("gate") or "N/A"
    arr_scheduled = arr.get("scheduled") or "Unknown"
    arr_delay = arr.get("delay")
    arr_delay_text = f"{arr_delay} minutes" if arr_delay is not None else "N/A"

    return f"""
Airline: {airline}
Flight: {flight_number}
Status: {status}

Departure:
- Airport: {dep_airport}
- IATA: {dep_iata}
- Terminal: {dep_terminal}
- Gate: {dep_gate}
- Scheduled: {dep_scheduled}
- Delay: {dep_delay_text}

Arrival:
- Airport: {arr_airport}
- IATA: {arr_iata}
- Gate: {arr_gate}
- Scheduled: {arr_scheduled}
- Delay: {arr_delay_text}
""".strip()


def search_flights(query: str, limit: int = 10):
    if not API_KEY:
        return (
            "Flight API error: AVIATIONSTACK_API_KEY is missing.\n"
            "Please add this in your .env file:\n"
            "AVIATIONSTACK_API_KEY=your_api_key_here"
        )

    dep_iata, arr_iata = parse_route(query)

    params = {
        "access_key": API_KEY,
        "limit": min(limit, 100)
    }

    if dep_iata:
        params["dep_iata"] = dep_iata

    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"Flight API request failed: {e}"
    except ValueError:
        return "Flight API returned invalid JSON."

    if "error" in data:
        error = data["error"]
        return (
            "flight API error:\n"
            f"code: {error.get('code', 'Unknown')}\n"
            f"Message: {error.get('message', 'Unknown error')}"
        )

    flight_data = data.get("data", [])

    if not flight_data:
        route_text = ""

        if dep_iata and arr_iata:
            route_text = f" for route {dep_iata} to {arr_iata}"
        elif dep_iata:
            route_text = f" from {dep_iata}"
        elif arr_iata:
            route_text = f" to {arr_iata}"

        return (
            f"No live flight data found{route_text}.\n\n"
            "Note: AviationStack provides live/status flight data, not ticket prices."
            "For actual fare prices, use a flight-pricing API such as Amadeus."
        )

    route_info = "Global live flights"

    if dep_iata and arr_iata:
        route_info = f"Live flights from {dep_iata} to {arr_iata}"
    elif dep_iata:
        route_info = f"Live flights from {dep_iata}"
    elif arr_iata:
        route_info = f"Live flights to {arr_iata}"

    formatted_flights = [format_flight(flight) for flight in flight_data[:limit]]

    return f"{route_info}\n\n" + "\n\n--\n\n".join(formatted_flights)

if __name__ == "__main__":
    print(search_flights("Plan a 7 days Japan trip from Bangladesh"))
    print("\n" + "=" * 80 + "\n")
    print(search_flights("all country flight info"))
