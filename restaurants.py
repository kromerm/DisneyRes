"""
Disney World restaurant directory.

Maps common search names to WDW facility IDs used in the dining availability API.
IDs are the "facility entity IDs" used internally by Disney's booking system.

If a restaurant you want is missing, add it here:
  1. Find the restaurant on https://disneyworld.disney.go.com/dining/
  2. Open DevTools > Network, search for availability, and note the 'id' parameter
  3. Add an entry below with that ID
"""

# Each entry key is a lowercase search alias.
# Multiple aliases can point to the same restaurant record.
RESTAURANTS: dict[str, dict] = {

    # -------------------------------------------------------------------------
    # Magic Kingdom
    # -------------------------------------------------------------------------
    "be our guest": {
        "id": "90002822",
        "name": "Be Our Guest Restaurant",
        "park": "Magic Kingdom",
        "slug": "be-our-guest-restaurant",
    },
    "bog": {
        "id": "90002822",
        "name": "Be Our Guest Restaurant",
        "park": "Magic Kingdom",
        "slug": "be-our-guest-restaurant",
    },
    "cinderella's royal table": {
        "id": "90002780",
        "name": "Cinderella's Royal Table",
        "park": "Magic Kingdom",
        "slug": "cinderellas-royal-table",
    },
    "crt": {
        "id": "90002780",
        "name": "Cinderella's Royal Table",
        "park": "Magic Kingdom",
        "slug": "cinderellas-royal-table",
    },
    "crystal palace": {
        "id": "90002797",
        "name": "The Crystal Palace",
        "park": "Magic Kingdom",
        "slug": "the-crystal-palace",
    },
    "liberty tree tavern": {
        "id": "90002802",
        "name": "Liberty Tree Tavern",
        "park": "Magic Kingdom",
        "slug": "liberty-tree-tavern",
    },
    "skipper canteen": {
        "id": "18912380",
        "name": "Jungle Navigation Co. LTD Skipper Canteen",
        "park": "Magic Kingdom",
        "slug": "jungle-navigation-co-ltd-skipper-canteen",
    },
    "tony's town square": {
        "id": "90002864",
        "name": "Tony's Town Square Restaurant",
        "park": "Magic Kingdom",
        "slug": "tonys-town-square-restaurant",
    },

    # -------------------------------------------------------------------------
    # EPCOT
    # -------------------------------------------------------------------------
    "space 220": {
        "id": "18853891",
        "name": "Space 220 Restaurant",
        "park": "EPCOT",
    },
    "coral reef": {
        "id": "90002796",
        "name": "Coral Reef Restaurant",
        "park": "EPCOT",
    },
    "garden grill": {
        "id": "90002810",
        "name": "The Garden Grill Restaurant",
        "park": "EPCOT - The Land",
    },
    "akershus": {
        "id": "90002775",
        "name": "Akershus Royal Banquet Hall",
        "park": "EPCOT - Norway Pavilion",
    },
    "biergarten": {
        "id": "90002783",
        "name": "Biergarten Restaurant",
        "park": "EPCOT - Germany Pavilion",
    },
    "nine dragons": {
        "id": "90002848",
        "name": "Nine Dragons Restaurant",
        "park": "EPCOT - China Pavilion",
    },
    "san angel inn": {
        "id": "90002857",
        "name": "San Angel Inn Restaurante",
        "park": "EPCOT - Mexico Pavilion",
    },
    "la hacienda de san angel": {
        "id": "18004990",
        "name": "La Hacienda de San Angel",
        "park": "EPCOT - Mexico Pavilion",
    },
    "via napoli": {
        "id": "90002869",
        "name": "Via Napoli Ristorante e Pizzeria",
        "park": "EPCOT - Italy Pavilion",
    },
    "teppan edo": {
        "id": "90002861",
        "name": "Teppan Edo",
        "park": "EPCOT - Japan Pavilion",
    },
    "tokyo dining": {
        "id": "90002862",
        "name": "Tokyo Dining",
        "park": "EPCOT - Japan Pavilion",
    },
    "rose and crown": {
        "id": "90002856",
        "name": "Rose & Crown Pub & Dining Room",
        "park": "EPCOT - United Kingdom Pavilion",
    },
    "restaurant marrakesh": {
        "id": "90002854",
        "name": "Restaurant Marrakesh",
        "park": "EPCOT - Morocco Pavilion",
    },
    "spice road table": {
        "id": "18492882",
        "name": "Spice Road Table",
        "park": "EPCOT - Morocco Pavilion",
    },
    "chefs de france": {
        "id": "90002791",
        "name": "Chefs de France",
        "park": "EPCOT - France Pavilion",
    },
    "monsieur paul": {
        "id": "90002844",
        "name": "Monsieur Paul",
        "park": "EPCOT - France Pavilion",
    },
    "tutto italia": {
        "id": "90002866",
        "name": "Tutto Italia Ristorante",
        "park": "EPCOT - Italy Pavilion",
    },

    # -------------------------------------------------------------------------
    # Hollywood Studios
    # -------------------------------------------------------------------------
    "sci-fi dine-in": {
        "id": "90002858",
        "name": "Sci-Fi Dine-In Theater Restaurant",
        "park": "Hollywood Studios",
    },
    "sci fi": {
        "id": "90002858",
        "name": "Sci-Fi Dine-In Theater Restaurant",
        "park": "Hollywood Studios",
    },
    "hollywood brown derby": {
        "id": "90002820",
        "name": "The Hollywood Brown Derby",
        "park": "Hollywood Studios",
    },
    "brown derby": {
        "id": "90002820",
        "name": "The Hollywood Brown Derby",
        "park": "Hollywood Studios",
    },
    "oga's cantina": {
        "id": "90002876",
        "name": "Oga's Cantina",
        "park": "Hollywood Studios - Galaxy's Edge",
    },
    "ogas cantina": {
        "id": "90002876",
        "name": "Oga's Cantina",
        "park": "Hollywood Studios - Galaxy's Edge",
    },
    "50's prime time": {
        "id": "90002773",
        "name": "50's Prime Time Café",
        "park": "Hollywood Studios",
    },
    "prime time cafe": {
        "id": "90002773",
        "name": "50's Prime Time Café",
        "park": "Hollywood Studios",
    },
    "mama melrose's": {
        "id": "90002829",
        "name": "Mama Melrose's Ristorante Italiano",
        "park": "Hollywood Studios",
    },

    # -------------------------------------------------------------------------
    # Animal Kingdom
    # -------------------------------------------------------------------------
    "tiffins": {
        "id": "19240099",
        "name": "Tiffins Restaurant",
        "park": "Animal Kingdom",
    },
    "tusker house": {
        "id": "90002865",
        "name": "Tusker House Restaurant",
        "park": "Animal Kingdom",
    },
    "yak and yeti": {
        "id": "90002873",
        "name": "Yak & Yeti Restaurant",
        "park": "Animal Kingdom",
    },
    "yak & yeti": {
        "id": "90002873",
        "name": "Yak & Yeti Restaurant",
        "park": "Animal Kingdom",
    },

    # -------------------------------------------------------------------------
    # Walt Disney World Resorts
    # -------------------------------------------------------------------------
    # Contemporary
    "california grill": {
        "id": "90002784",
        "name": "California Grill",
        "park": "Contemporary Resort",
    },
    "chef mickey's": {
        "id": "90002792",
        "name": "Chef Mickey's",
        "park": "Contemporary Resort",
    },
    "steakhouse 71": {
        "id": "19634606",
        "name": "Steakhouse 71",
        "park": "Contemporary Resort",
    },
    # Grand Floridian
    "narcoossee's": {
        "id": "90002847",
        "name": "Narcoossee's",
        "park": "Grand Floridian Resort & Spa",
    },
    "grand floridian cafe": {
        "id": "90002811",
        "name": "Grand Floridian Café",
        "park": "Grand Floridian Resort & Spa",
    },
    "citricos": {
        "id": "90002795",
        "name": "Citrico's",
        "park": "Grand Floridian Resort & Spa",
    },
    "victoria and albert's": {
        "id": "90002870",
        "name": "Victoria & Albert's",
        "park": "Grand Floridian Resort & Spa",
    },
    # Polynesian
    "ohana": {
        "id": "90002851",
        "name": "'Ohana",
        "park": "Polynesian Village Resort",
    },
    "kona cafe": {
        "id": "90002800",
        "name": "Kona Café",
        "park": "Polynesian Village Resort",
    },
    # BoardWalk
    "flying fish": {
        "id": "90002807",
        "name": "Flying Fish",
        "park": "BoardWalk Inn",
    },
    "trattoria al forno": {
        "id": "18492866",
        "name": "Trattoria al Forno",
        "park": "BoardWalk Inn",
    },
    # Wilderness Lodge
    "storybook dining": {
        "id": "18623420",
        "name": "Storybook Dining at Artist Point",
        "park": "Wilderness Lodge",
    },
    "whispering canyon cafe": {
        "id": "90002871",
        "name": "Whispering Canyon Café",
        "park": "Wilderness Lodge",
    },
    # Beach/Yacht Club
    "cape may cafe": {
        "id": "90002787",
        "name": "Cape May Café",
        "park": "Beach Club Resort",
    },
    "yachtsman steakhouse": {
        "id": "90002872",
        "name": "Yachtsman Steakhouse",
        "park": "Yacht Club Resort",
    },
    # Animal Kingdom Lodge
    "sanaa": {
        "id": "90002855",
        "name": "Sanaa",
        "park": "Animal Kingdom Lodge - Kidani Village",
    },
    "jiko": {
        "id": "90002821",
        "name": "Jiko - The Cooking Place",
        "park": "Animal Kingdom Lodge - Jambo House",
    },
    "boma": {
        "id": "90002785",
        "name": "Boma - Flavors of Africa",
        "park": "Animal Kingdom Lodge - Jambo House",
    },
    # Riviera Resort
    "topolino's terrace": {
        "id": "19461956",
        "name": "Topolino's Terrace",
        "park": "Riviera Resort",
    },
    # Port Orleans
    "boatwright's dining hall": {
        "id": "90002786",
        "name": "Boatwright's Dining Hall",
        "park": "Port Orleans - Riverside",
    },
    # Fort Wilderness
    "trail's end": {
        "id": "90002863",
        "name": "Trail's End Restaurant",
        "park": "Fort Wilderness Resort",
    },
    # Swan and Dolphin
    "shula's steak house": {
        "id": "90002859",
        "name": "Shula's Steak House",
        "park": "Dolphin Hotel",
    },
    "il mulino": {
        "id": "90002817",
        "name": "Il Mulino New York Trattoria",
        "park": "Swan Hotel",
    },

    # -------------------------------------------------------------------------
    # Disney Springs
    # Note: numeric facility IDs below are not yet confirmed for these entries.
    # The Playwright checker only needs the slug to work.  To fill in the
    # correct numeric ID, open DevTools → Network while browsing the restaurant
    # on https://disneyworld.disney.go.com/dine-res/restaurant/{slug}/ and look
    # for a request containing "facilityId=" in the URL.
    # -------------------------------------------------------------------------
    "the boathouse": {
        "id": "",
        "name": "The BOATHOUSE",
        "park": "Disney Springs",
        "slug": "boathouse-restaurant",
    },
    "boathouse": {
        "id": "",
        "name": "The BOATHOUSE",
        "park": "Disney Springs",
        "slug": "boathouse-restaurant",
    },
    "homecomin": {
        "id": "",
        "name": "Chef Art Smith's Homecomin'",
        "park": "Disney Springs",
        "slug": "chef-art-smiths-homecomin",
    },
    "chef art smith": {
        "id": "",
        "name": "Chef Art Smith's Homecomin'",
        "park": "Disney Springs",
        "slug": "chef-art-smiths-homecomin",
    },
    "city works": {
        "id": "",
        "name": "City Works Eatery & Pour House",
        "park": "Disney Springs",
        "slug": "city-works",
    },
    "the edison": {
        "id": "",
        "name": "The Edison",
        "park": "Disney Springs",
        "slug": "edison",
    },
    "jaleo": {
        "id": "",
        "name": "Jaleo by José Andrés",
        "park": "Disney Springs",
        "slug": "jaleo",
    },
    "eet": {
        "id": "",
        "name": "Eet by Maneet Chauhan",
        "park": "Disney Springs",
        "slug": "eet-by-maneet-chauhan",
    },
    "eet by maneet": {
        "id": "",
        "name": "Eet by Maneet Chauhan",
        "park": "Disney Springs",
        "slug": "eet-by-maneet-chauhan",
    },
    "paddlefish": {
        "id": "",
        "name": "Paddlefish",
        "park": "Disney Springs",
        "slug": "paddlefish",
    },
    "stk": {
        "id": "",
        "name": "STK Orlando",
        "park": "Disney Springs",
        "slug": "stk-orlando",
    },
    "stk orlando": {
        "id": "",
        "name": "STK Orlando",
        "park": "Disney Springs",
        "slug": "stk-orlando",
    },
    "terralina": {
        "id": "",
        "name": "Terralina Crafted Italian",
        "park": "Disney Springs",
        "slug": "terralina-crafted-italian",
    },
    "terralina crafted italian": {
        "id": "",
        "name": "Terralina Crafted Italian",
        "park": "Disney Springs",
        "slug": "terralina-crafted-italian",
    },
    "wine bar george": {
        "id": "",
        "name": "Wine Bar George",
        "park": "Disney Springs",
        "slug": "wine-bar-george",
    },
    "frontera cocina": {
        "id": "",
        "name": "Frontera Cocina",
        "park": "Disney Springs",
        "slug": "frontera-cocina",
    },
    "frontera": {
        "id": "",
        "name": "Frontera Cocina",
        "park": "Disney Springs",
        "slug": "frontera-cocina",
    },
    "raglan road": {
        "id": "",
        "name": "Raglan Road Irish Pub & Restaurant",
        "park": "Disney Springs",
        "slug": "raglan-road",
    },
    "wolfgang puck": {
        "id": "",
        "name": "Wolfgang Puck Bar & Grill",
        "park": "Disney Springs",
        "slug": "wolfgang-puck-bar-and-grill",
    },
    "house of blues": {
        "id": "",
        "name": "House of Blues Restaurant & Bar",
        "park": "Disney Springs",
        "slug": "house-of-blues-restaurant",
    },
    "rainforest cafe disney springs": {
        "id": "",
        "name": "Rainforest Cafe at Disney Springs",
        "park": "Disney Springs",
        "slug": "rainforest-cafe-disney-springs",
    },
    "t-rex": {
        "id": "",
        "name": "T-REX",
        "park": "Disney Springs",
        "slug": "t-rex-a-prehistoric-family-adventure",
    },
    "trex": {
        "id": "",
        "name": "T-REX",
        "park": "Disney Springs",
        "slug": "t-rex-a-prehistoric-family-adventure",
    },
    "maria and enzos": {
        "id": "",
        "name": "Maria & Enzo's Ristorante",
        "park": "Disney Springs",
        "slug": "maria-and-enzos-ristorante",
    },
    "enzos hideaway": {
        "id": "",
        "name": "Enzo's Hideaway",
        "park": "Disney Springs",
        "slug": "enzos-hideaway",
    },
}


def derive_slug(restaurant: dict) -> str:
    """
    Return the URL slug used by Disney's dine-res SPA for *restaurant*.

    Uses the explicit ``"slug"`` field when present; otherwise derives one
    from the restaurant name.  The derived slug may not always match Disney's
    exact URL — if the browser navigates to a 404, the user will see an error
    and should add the correct ``"slug"`` field to the ``RESTAURANTS`` dict.
    """
    if restaurant.get("slug"):
        return restaurant["slug"]

    import re
    name = restaurant["name"]
    s = name.lower()
    s = re.sub(r"[''\u2019]", "", s)
    s = re.sub(r"&", "and", s)
    s = re.sub(r"[^a-z0-9 \-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s


def search(query: str) -> list[dict]:
    """
    Return all unique restaurants matching the search query.

    Matches against alias keys, full restaurant name, and park name.
    """
    q = query.lower().strip()
    seen_ids: set[str] = set()
    results: list[dict] = []

    for key, restaurant in RESTAURANTS.items():
        if (
            q in key
            or q in restaurant["name"].lower()
            or q in restaurant["park"].lower()
        ):
            rid = restaurant.get("id") or restaurant.get("slug") or restaurant["name"]
            if rid not in seen_ids:
                seen_ids.add(rid)
                results.append(restaurant)

    return results


def all_unique() -> list[dict]:
    """Return every restaurant exactly once, sorted by park then name."""
    seen_ids: set[str] = set()
    unique: list[dict] = []
    for r in RESTAURANTS.values():
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            unique.append(r)
    return sorted(unique, key=lambda r: (r["park"], r["name"]))
