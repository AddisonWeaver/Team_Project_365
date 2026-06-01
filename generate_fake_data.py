"""
Generates ~1 million rows of realistic fake data for the Team_Project_365 movie-review service.

Target row counts (totals ~1,035,000):
  users           10,000
  movies          50,000   (40,000 movies + 10,000 TV series)
  genres              25   (lookup table)
  actors          20,000
  movie_genres   100,000   (2 genres per movie on average)
  movie_actors   200,000   (4 actors per movie on average)
  ratings        400,000   (average 8 ratings per movie, skewed toward popular titles)
  reviews        130,000   (~1 review per 3 ratings; users who rate often also review)
  watch_history  125,000   (users mark watched without necessarily rating/reviewing)

Grand total ≈ 1,035,025 rows
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO

import psycopg2
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

# ─── Config ────────────────────────────────────────────────────────────────────
NUM_USERS = 10_000
NUM_MOVIES = 40_000
NUM_TV = 10_000
NUM_ACTORS = 20_000
NUM_GENRES = 25
AVG_GENRES_PER_MOVIE = 2  # → ~100,000 movie_genres rows
AVG_ACTORS_PER_MOVIE = 4  # → ~200,000 movie_actors rows
NUM_RATINGS = 400_000
NUM_REVIEWS = 130_000
NUM_WATCH_HISTORY = 125_000

BATCH = 5_000  # rows per COPY batch

GENRES = [
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Horror",
    "Musical",
    "Mystery",
    "Romance",
    "Science Fiction",
    "Thriller",
    "Western",
    "Biography",
    "Family",
    "History",
    "Sport",
    "War",
    "Noir",
    "Superhero",
    "Anime",
    "Reality",
    "Talk Show",
]
assert len(GENRES) == NUM_GENRES

# ─── Real-ish seed data ────────────────────────────────────────────────────────
# 200 real movie titles — the script will combine, remix, and suffix these
# to generate 40,000 unique movie titles that still look plausible.
REAL_MOVIE_TITLES = [
    "The Godfather",
    "Pulp Fiction",
    "The Dark Knight",
    "Schindler's List",
    "The Shawshank Redemption",
    "Forrest Gump",
    "Inception",
    "The Matrix",
    "Goodfellas",
    "Fight Club",
    "Interstellar",
    "The Silence of the Lambs",
    "Saving Private Ryan",
    "Gladiator",
    "The Lion King",
    "Titanic",
    "Jurassic Park",
    "Back to the Future",
    "The Avengers",
    "Avatar",
    "Parasite",
    "Spirited Away",
    "Eternal Sunshine of the Spotless Mind",
    "No Country for Old Men",
    "There Will Be Blood",
    "Whiplash",
    "La La Land",
    "Mad Max: Fury Road",
    "Get Out",
    "Hereditary",
    "Moonlight",
    "Roma",
    "The Grand Budapest Hotel",
    "Birdman",
    "12 Years a Slave",
    "Gravity",
    "Her",
    "Django Unchained",
    "The Wolf of Wall Street",
    "American Hustle",
    "Gone Girl",
    "The Revenant",
    "Spotlight",
    "The Martian",
    "Ex Machina",
    "Arrival",
    "Dunkirk",
    "Blade Runner 2049",
    "Three Billboards",
    "A Quiet Place",
    "Hereditary",
    "Midsommar",
    "1917",
    "Joker",
    "Once Upon a Time in Hollywood",
    "Knives Out",
    "Tenet",
    "Soul",
    "Nomadland",
    "The Father",
    "Promising Young Woman",
    "Minari",
    "Sound of Metal",
    "The Trial of the Chicago 7",
    "Ma Rainey's Black Bottom",
    "Judas and the Black Messiah",
    "Borat Subsequent Moviefilm",
    "News of the World",
    "The United States vs. Billie Holiday",
    "Malcolm & Marie",
    "Pieces of a Woman",
    "The Dig",
    "The White Tiger",
    "Quo Vadis, Aida?",
    "Another Round",
    "Collective",
    "Quo Vadis",
    "Drive My Car",
    "The Power of the Dog",
    "West Side Story",
    "Belfast",
    "CODA",
    "King Richard",
    "Licorice Pizza",
    "Spencer",
    "Tick, Tick... Boom!",
    "The Lost Daughter",
    "C'mon C'mon",
    "The Tragedy of Macbeth",
    "After Yang",
    "Nope",
    "Everything Everywhere All at Once",
    "The Banshees of Inisherin",
    "Tar",
    "The Fabelmans",
    "All Quiet on the Western Front",
    "Argentina, 1985",
    "Decision to Leave",
    "Women Talking",
    "The Son",
    "Aftersun",
    "Triangle of Sadness",
    "Bardo",
    "Close",
    "EO",
    "Living",
    "Corsage",
    "The Whale",
    "Babylon",
    "Elvis",
    "Glass Onion",
    "Avatar: The Way of Water",
    "Top Gun: Maverick",
    "Black Panther: Wakanda Forever",
    "Doctor Strange in the Multiverse of Madness",
    "Thor: Love and Thunder",
    "The Batman",
    "Uncharted",
    "Bullet Train",
    "Prey",
    "Barbarian",
    "Pearl",
    "Halloween Ends",
    "Scream",
    "The Menu",
    "Smile",
    "RRR",
    "KGF Chapter 2",
    "Brahmastra",
    "Vikram",
    "Jawan",
    "Pathaan",
    "Animal",
    "Dunki",
    "Past Lives",
    "Oppenheimer",
    "Barbie",
    "Killers of the Flower Moon",
    "Poor Things",
    "Anatomy of a Fall",
    "The Zone of Interest",
    "American Fiction",
    "Maestro",
    "Ferrari",
    "Napoleon",
    "Society of the Snow",
    "The Holdovers",
    "Saltburn",
    "Priscilla",
    "Dream Scenario",
    "May December",
    "Rustin",
    "Nyad",
    "Radical",
    "Cabrini",
    "Origin",
    "Civil War",
    "Furiosa",
    "Inside Out 2",
    "Alien: Romulus",
    "Longlegs",
    "Trap",
    "The Substance",
    "Conclave",
    "Emilia Pérez",
    "The Brutalist",
    "Nickel Boys",
    "September 5",
    "Queer",
    "A Complete Unknown",
    "Wicked",
    "Gladiator II",
    "Dune: Part Two",
    "Monkey Man",
    "Immaculate",
    "I Saw the TV Glow",
    "Love Lies Bleeding",
    "Janet Planet",
    "In a Violent Nature",
    "Hundreds of Beavers",
    "Strange Darling",
    "Heretic",
    "Christmas Eve in Miller's Point",
    "Wallace & Gromit: Vengeance Most Fowl",
    "Flow",
    "The Wild Robot",
    "Memoir of a Snail",
    "Robot Dreams",
    "El Conde",
    "Tótem",
    "20 Days in Mariupol",
    "Four Daughters",
    "To Kill a Tiger",
    "Bobi Wine: The People's President",
    "The Eternal Memory",
    "American Symphony",
    "Little Richard: I Am Everything",
    "Still: A Michael J. Fox Movie",
    "32 Sounds",
    "All the Beauty and the Bloodshed",
    "Fire of Love",
    "All That Breathes",
    "My Imaginary Country",
    "Navalny",
    "The Longest Goodbye",
    "Retrograde",
    "Roadrunner: A Film About Anthony Bourdain",
    "Flee",
    "Summer of Soul",
    "Procession",
    "Attica",
    "Faya Dayi",
    "Writing with Fire",
    "Ascension",
    "The Rescue",
]

# 150 real TV show titles
REAL_TV_TITLES = [
    "Breaking Bad",
    "The Wire",
    "The Sopranos",
    "Game of Thrones",
    "Succession",
    "The Crown",
    "Chernobyl",
    "Fleabag",
    "Atlanta",
    "Better Call Saul",
    "Mindhunter",
    "Ozark",
    "Stranger Things",
    "The Bear",
    "Severance",
    "The Last of Us",
    "House of the Dragon",
    "Andor",
    "Abbott Elementary",
    "Ted Lasso",
    "White Lotus",
    "Only Murders in the Building",
    "Yellowstone",
    "The Mandalorian",
    "Euphoria",
    "Mare of Easttown",
    "Squid Game",
    "Lupin",
    "Money Heist",
    "Dark",
    "Narcos",
    "Peaky Blinders",
    "Downton Abbey",
    "Sherlock",
    "Black Mirror",
    "Westworld",
    "True Detective",
    "Fargo",
    "Silicon Valley",
    "Veep",
    "Barry",
    "Curb Your Enthusiasm",
    "It's Always Sunny in Philadelphia",
    "Arrested Development",
    "Twin Peaks",
    "The X-Files",
    "The Americans",
    "Homeland",
    "24",
    "Lost",
    "The Office",
    "Parks and Recreation",
    "Community",
    "30 Rock",
    "Brooklyn Nine-Nine",
    "Schitt's Creek",
    "Bojack Horseman",
    "BoJack Horseman",
    "Arrested Development",
    "The Good Place",
    "What We Do in the Shadows",
    "Reservation Dogs",
    "Ramy",
    "Insecure",
    "Pose",
    "Transparent",
    "The Handmaid's Tale",
    "Orange Is the New Black",
    "GLOW",
    "Big Little Lies",
    "Sharp Objects",
    "Little Fires Everywhere",
    "Normal People",
    "Conversations with Friends",
    "Daisy Jones & the Six",
    "The Bear",
    "The Diplomat",
    "Beef",
    "Poker Face",
    "The Gentlemen",
    "Ripley",
    "Shogun",
    "3 Body Problem",
    "Fallout",
    "X-Men '97",
    "Baby Reindeer",
    "Bodkin",
    "Eric",
    "Presumed Innocent",
    "The Penguin",
    "Disclaimer",
    "Agatha All Along",
    "English Teacher",
    "The Day of the Jackal",
    "Dune: Prophecy",
    "Tulsa King",
    "Lioness",
    "1923",
    "The Rings of Power",
    "House of the Dragon",
    "Andor",
    "Moon Knight",
    "Ms. Marvel",
    "She-Hulk",
    "Hawkeye",
    "WandaVision",
    "Loki",
    "The Falcon and the Winter Soldier",
    "What If...?",
    "Secret Invasion",
    "Echo",
    "Agatha All Along",
    "Foundation",
    "For All Mankind",
    "Severance",
    "Ted",
    "Slow Horses",
    "The Capture",
    "Anatomy of a Scandal",
    "Inventing Anna",
    "The Dropout",
    "WeCrashed",
    "Super Pumped",
    "The Watcher",
    "Dahmer",
    "Monster",
    "American Horror Story",
    "The Act",
    "Dirty John",
    "Dr. Death",
    "Impeachment",
    "Pam & Tommy",
    "The Offer",
    "The Staircase",
    "Under the Banner of Heaven",
    "Candy",
    "The Thing About Pam",
    "Reasonable Doubt",
    "Tell Me Lies",
    "Dead to Me",
    "Never Have I Ever",
    "Ginny & Georgia",
    "Emily in Paris",
    "Bridgerton",
    "Queen Charlotte",
    "Outer Banks",
    "You",
    "Clickbait",
    "The Haunting of Hill House",
    "Midnight Mass",
    "The Fall of the House of Usher",
]

# 300 real actor/actress names
REAL_ACTOR_NAMES = [
    "Meryl Streep",
    "Cate Blanchett",
    "Viola Davis",
    "Natalie Portman",
    "Charlize Theron",
    "Nicole Kidman",
    "Julianne Moore",
    "Olivia Colman",
    "Jessica Lange",
    "Glenn Close",
    "Frances McDormand",
    "Emma Thompson",
    "Sandra Bullock",
    "Jennifer Lawrence",
    "Brie Larson",
    "Saoirse Ronan",
    "Margot Robbie",
    "Florence Pugh",
    "Zendaya",
    "Ana de Armas",
    "Carey Mulligan",
    "Lupita Nyong'o",
    "Awkwafina",
    "Constance Wu",
    "Sandra Oh",
    "Kerry Washington",
    "Taraji P. Henson",
    "Angela Bassett",
    "Halle Berry",
    "Whoopi Goldberg",
    "Denzel Washington",
    "Morgan Freeman",
    "Will Smith",
    "Idris Elba",
    "Mahershala Ali",
    "Daniel Kaluuya",
    "Chadwick Boseman",
    "Michael B. Jordan",
    "John Boyega",
    "Aldis Hodge",
    "Tom Hanks",
    "Tom Cruise",
    "Brad Pitt",
    "Leonardo DiCaprio",
    "Ryan Gosling",
    "Chris Hemsworth",
    "Chris Evans",
    "Robert Downey Jr.",
    "Mark Ruffalo",
    "Jeremy Renner",
    "Paul Rudd",
    "Benedict Cumberbatch",
    "Tom Holland",
    "Timothée Chalamet",
    "Austin Butler",
    "Jacob Elordi",
    "Barry Keoghan",
    "Paul Mescal",
    "Andrew Scott",
    "Jonathan Bailey",
    "Pedro Pascal",
    "Oscar Isaac",
    "Anthony Mackie",
    "Simu Liu",
    "Ke Huy Quan",
    "Steven Yeun",
    "John Cho",
    "Daniel Dae Kim",
    "Jared Leto",
    "Adam Driver",
    "Joaquin Phoenix",
    "Rami Malek",
    "Christian Bale",
    "Matt Damon",
    "Ben Affleck",
    "Jake Gyllenhaal",
    "Ethan Hawke",
    "Viggo Mortensen",
    "Willem Dafoe",
    "Gary Oldman",
    "Anthony Hopkins",
    "Ian McKellen",
    "Judi Dench",
    "Helen Mirren",
    "Tilda Swinton",
    "Sigourney Weaver",
    "Jamie Lee Curtis",
    "Michelle Pfeiffer",
    "Michelle Yeoh",
    "Gemma Chan",
    "Awkwafina",
    "Stephanie Hsu",
    "Rebecca Ferguson",
    "Zoe Saldana",
    "Lupita Nyong'o",
    "Danai Gurira",
    "Elizabeth Olsen",
    "Scarlett Johansson",
    "Gal Gadot",
    "Brie Larson",
    "Anya Taylor-Joy",
    "Emma Stone",
    "Rachel Weisz",
    "Amy Adams",
    "Jennifer Aniston",
    "Reese Witherspoon",
    "Hilary Swank",
    "Kate Winslet",
    "Cate Blanchett",
    "Marion Cotillard",
    "Penélope Cruz",
    "Javier Bardem",
    "Antonio Banderas",
    "Benicio del Toro",
    "Gael García Bernal",
    "Diego Luna",
    "Salma Hayek",
    "Eva Longoria",
    "Sofia Vergara",
    "Zoe Saldana",
    "Lana Condor",
    "Michelle Rodriguez",
    "Jennifer Lopez",
    "Rita Moreno",
    "Ali Wong",
    "Mindy Kaling",
    "Priyanka Chopra",
    "Deepika Padukone",
    "Ranveer Singh",
    "Shah Rukh Khan",
    "Aamir Khan",
    "Hrithik Roshan",
    "Aishwarya Rai",
    "Katrina Kaif",
    "Kareena Kapoor",
    "Alia Bhatt",
    "Ranbir Kapoor",
    "Yalitza Aparicio",
    "María de Tavira",
    "Adriana Paz",
    "Song Kang-ho",
    "Lee Byung-hun",
    "Ma Dong-seok",
    "Jung Ho-yeon",
    "Lee Jung-jae",
    "Park Seo-joon",
    "Choi Woo-shik",
    "Park So-dam",
    "Masahiro Motoki",
    "Rinko Kikuchi",
    "Ken Watanabe",
    "Hiroyuki Sanada",
    "Mads Mikkelsen",
    "Nikolaj Coster-Waldau",
    "Stellan Skarsgård",
    "Alexander Skarsgård",
    "Bill Skarsgård",
    "Rebecca Ferguson",
    "Noomi Rapace",
    "Alicia Vikander",
    "Ingrid Bergman",
    "Björn Andrésen",
    "Christoph Waltz",
    "Michael Fassbender",
    "Daniel Brühl",
    "Diane Kruger",
    "Franka Potente",
    "Fatih Akin",
    "Alexandra Maria Lara",
    "Moritz Bleibtreu",
    "Vincent Cassel",
    "Léa Seydoux",
    "Marion Cotillard",
    "Omar Sy",
    "Tahar Rahim",
    "Adèle Exarchopoulos",
    "Adèle Haenel",
    "Youssef Hajdi",
    "Lubna Azabal",
    "Tahar Rahim",
    "Hafsia Herzi",
    "Leïla Bekhti",
    "Asghar Farhadi",
    "Golshifteh Farahani",
    "Shahab Hosseini",
    "Navid Mohammadzadeh",
    "Payman Maadi",
    "Hana Kamkar",
    "Javier Bardem",
    "Belén Rueda",
    "Maribel Verdú",
    "Óscar Martínez",
    "Ricardo Darín",
    "Martina Gusmán",
    "Leonardo Sbaraglia",
    "Dolores Fonzi",
    "Diego Peretti",
    "Graciela Borges",
    "Ethan Hawke",
    "Uma Thurman",
    "Harvey Keitel",
    "Tim Roth",
    "Samuel L. Jackson",
    "John Travolta",
    "Bruce Willis",
    "Ving Rhames",
    "Steve Buscemi",
    "Michael Madsen",
    "Chris Penn",
    "Kirk Baltz",
    "Forest Whitaker",
    "Cuba Gooding Jr.",
    "Cuba Gooding Jr.",
    "Jamie Foxx",
    "Don Cheadle",
    "Terrence Howard",
    "Chiwetel Ejiofor",
    "David Oyelowo",
    "Nate Parker",
    "Michael B. Jordan",
    "Tessa Thompson",
    "Ruth Negga",
    "Joel Edgerton",
    "Lucas Hedges",
    "Kelvin Harrison Jr.",
    "Taylor Russell",
    "Daveed Diggs",
    "Lakeith Stanfield",
    "Atlanta cast",
    "Zazie Beetz",
    "Brian Tyree Henry",
    "Stephan James",
    "Ali Hassan",
    "Khris Davis",
    "Regina King",
    "Aldis Hodge",
    "Yahya Abdul-Mateen II",
    "Jovan Adepo",
    "Jonathan Majors",
    "Damson Idris",
    "Caleb McLaughlin",
    "Asante Blackk",
    "Mia Goth",
    "Thomasin McKenzie",
    "Jessie Buckley",
    "Morfydd Clark",
    "Ellie Bamber",
    "Sophia Lillis",
    "Sadie Sink",
    "Millie Bobby Brown",
    "Finn Wolfhard",
    "Noah Schnapp",
    "Caleb McLaughlin",
    "Gaten Matarazzo",
    "Natalia Dyer",
    "Charlie Heaton",
    "Joe Keery",
    "Maya Hawke",
    "Priah Ferguson",
    "Brett Gelman",
    "Cara Buono",
    "Matthew Modine",
    "Paul Reiser",
    "Sean Astin",
    "Winona Ryder",
    "David Harbour",
]

# Word banks for generating unique titles by combining seeds with modifiers
TITLE_PREFIXES = [
    "The",
    "A",
    "Last",
    "Dark",
    "Silent",
    "Broken",
    "Lost",
    "Hidden",
    "Eternal",
    "Forgotten",
    "Rising",
    "Falling",
    "Final",
    "Secret",
    "Midnight",
    "Hollow",
    "Crimson",
    "Scarlet",
    "Golden",
    "Iron",
    "Burning",
    "Fading",
    "Endless",
    "Savage",
    "Bitter",
    "Sweet",
    "Ancient",
    "New",
    "Dead",
    "Living",
]
TITLE_SUFFIXES = [
    "Chronicles",
    "Legacy",
    "Rising",
    "Reborn",
    "Awakening",
    "Reckoning",
    "Redemption",
    "Requiem",
    "Descent",
    "Ascent",
    "Chapter Two",
    "Part II",
    "Part III",
    "Returns",
    "Resurrected",
    "Unleashed",
    "Unbound",
    "Untold",
    "Origins",
    "Begins",
    "Strikes Back",
    "Forever",
    "Infinity",
    "Beyond",
    "Within",
    "Without",
    "Reloaded",
    "Revolution",
    "Resurrection",
    "Revelation",
]


def ts(start: datetime, end: datetime) -> str:
    """Random UTC timestamp between start and end as ISO string."""
    delta = end - start
    secs = random.randint(0, int(delta.total_seconds()))
    dt = start + timedelta(seconds=secs)
    return dt.isoformat()


NOW = datetime.now(timezone.utc)
START = NOW - timedelta(days=5 * 365)  # 5 years of history


def copy_rows(cur, table: str, columns: list, rows: list[tuple]):
    """Bulk-load rows into table via COPY."""
    buf = StringIO()
    for row in rows:
        line = "\t".join(
            (
                "\\N"
                if v is None
                else str(v).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")
            )
            for v in row
        )
        buf.write(line + "\n")
    buf.seek(0)
    cur.copy_from(buf, table, columns=columns, null="\\N")


def run(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    print("Truncating existing data …")
    cur.execute("""
        TRUNCATE watch_history, reviews, ratings,
                 movie_actors, movie_genres,
                 actors, genres, movies, users
        RESTART IDENTITY CASCADE;
    """)
    conn.commit()

    # 1. Users
    print(f"Inserting {NUM_USERS:,} users …")
    seen_names, seen_emails = set(), set()
    batch = []
    for i in range(1, NUM_USERS + 1):
        while True:
            username = fake.user_name() + str(random.randint(0, 9999))
            if username not in seen_names:
                seen_names.add(username)
                break
        while True:
            email = fake.unique.email()
            if email not in seen_emails:
                seen_emails.add(email)
                break
        created = ts(START, NOW)
        batch.append((username, email, created))
        if len(batch) == BATCH:
            copy_rows(cur, "users", ["username", "email", "created_at"], batch)
            batch = []
    if batch:
        copy_rows(cur, "users", ["username", "email", "created_at"], batch)
    conn.commit()
    print(f"  ✓ users done")

    # 2. Genres
    print(f"Inserting {NUM_GENRES} genres …")
    copy_rows(cur, "genres", ["name"], [(g,) for g in GENRES])
    conn.commit()
    print(f"  ✓ genres done")

    # 3. Actors
    # Start with real actor names, then fill remaining slots with fake names
    print(f"Inserting {NUM_ACTORS:,} actors …")
    seen_actors = set()
    batch = []
    # First: insert all real actor names (deduplicated)
    for name in REAL_ACTOR_NAMES:
        if name not in seen_actors:
            seen_actors.add(name)
            batch.append((name,))
    # Fill rest with faker names
    while len(seen_actors) < NUM_ACTORS:
        name = fake.name()
        if name not in seen_actors:
            seen_actors.add(name)
            batch.append((name,))
        if len(batch) == BATCH:
            copy_rows(cur, "actors", ["name"], batch)
            batch = []
    if batch:
        copy_rows(cur, "actors", ["name"], batch)
    conn.commit()
    print(f"  ✓ actors done")

    # 4. Movies
    total_media = NUM_MOVIES + NUM_TV
    print(f"Inserting {total_media:,} movies/TV …")

    # Build a large unique title pool:
    # 1. Real titles as-is
    # 2. "The Dark Knight Returns", "Pulp Fiction: Reloaded", etc.
    # 3. Prefix + real word combos
    # 4. Fill remainder with faker words (as before)
    all_real = REAL_MOVIE_TITLES + REAL_TV_TITLES
    title_pool = set(all_real)

    # Generate variants until we have enough
    while len(title_pool) < total_media + 5000:
        base = random.choice(all_real)
        mode = random.randint(0, 3)
        if mode == 0:
            candidate = f"{random.choice(TITLE_PREFIXES)} {base}"
        elif mode == 1:
            candidate = f"{base}: {random.choice(TITLE_SUFFIXES)}"
        elif mode == 2:
            candidate = f"{base} {random.choice(TITLE_SUFFIXES)}"
        else:
            # prefix word + base word
            words = base.split()
            candidate = f"{random.choice(TITLE_PREFIXES)} {random.choice(words)} {random.choice(TITLE_SUFFIXES)}"
        title_pool.add(candidate)

    title_list = list(title_pool)
    random.shuffle(title_list)
    # Trim to exactly what we need
    movie_titles = title_list[:NUM_MOVIES]
    tv_titles = title_list[NUM_MOVIES : NUM_MOVIES + NUM_TV]

    movie_ids = list(range(1, total_media + 1))

    batch = []
    for i, title in enumerate(movie_titles + tv_titles, start=1):
        media_type = "movie" if i <= NUM_MOVIES else "tv"
        release_year = random.choices(
            range(1980, 2026),
            weights=[max(1, (y - 1979) ** 1.5) for y in range(1980, 2026)],
        )[0]
        created = ts(START, NOW)
        batch.append((title, media_type, release_year, created))
        if len(batch) == BATCH:
            copy_rows(
                cur,
                "movies",
                ["title", "media_type", "release_year", "created_at"],
                batch,
            )
            batch = []
    if batch:
        copy_rows(
            cur, "movies", ["title", "media_type", "release_year", "created_at"], batch
        )
    conn.commit()
    print(f"  ✓ movies done")

    # 5. movie_genres
    print("Inserting movie_genres …")
    genre_ids = list(range(1, NUM_GENRES + 1))
    batch = []
    seen_mg = set()
    for movie_id in movie_ids:
        n = random.choices([1, 2, 3, 4], weights=[20, 50, 25, 5])[0]
        chosen = random.sample(genre_ids, min(n, NUM_GENRES))
        for gid in chosen:
            key = (movie_id, gid)
            if key not in seen_mg:
                seen_mg.add(key)
                batch.append(key)
        if len(batch) >= BATCH:
            copy_rows(cur, "movie_genres", ["movie_id", "genre_id"], batch)
            batch = []
    if batch:
        copy_rows(cur, "movie_genres", ["movie_id", "genre_id"], batch)
    conn.commit()
    print(f"  ✓ movie_genres done ({len(seen_mg):,} rows)")

    # 6. movie_actors
    print("Inserting movie_actors …")
    actor_ids = list(range(1, NUM_ACTORS + 1))
    batch = []
    seen_ma = set()
    for movie_id in movie_ids:
        n = random.choices([1, 2, 3, 4, 5, 6], weights=[5, 15, 30, 30, 15, 5])[0]
        chosen = random.sample(actor_ids, min(n, NUM_ACTORS))
        for aid in chosen:
            key = (movie_id, aid)
            if key not in seen_ma:
                seen_ma.add(key)
                batch.append(key)
        if len(batch) >= BATCH:
            copy_rows(cur, "movie_actors", ["movie_id", "actor_id"], batch)
            batch = []
    if batch:
        copy_rows(cur, "movie_actors", ["movie_id", "actor_id"], batch)
    conn.commit()
    print(f"  ✓ movie_actors done ({len(seen_ma):,} rows)")

    #  7. Ratings
    # Popularity tier: top 10% of movies get 60% of ratings (long tail)
    print(f"Inserting {NUM_RATINGS:,} ratings …")

    popular_cutoff = int(total_media * 0.10)
    popular_movie_ids = movie_ids[:popular_cutoff]
    other_movie_ids = movie_ids[popular_cutoff:]

    def pick_movie_for_rating():
        if random.random() < 0.60:
            return random.choice(popular_movie_ids)
        return random.choice(other_movie_ids)

    seen_ratings = set()
    batch = []
    inserted_ratings = 0
    attempts = 0
    while inserted_ratings < NUM_RATINGS:
        attempts += 1
        if attempts > NUM_RATINGS * 5:
            print("  Warning: could not fill all ratings without duplicates")
            break
        uid = random.randint(1, NUM_USERS)
        mid = pick_movie_for_rating()
        key = (uid, mid)
        if key in seen_ratings:
            continue
        seen_ratings.add(key)
        # Ratings skewed toward 3-5 (most people rate things they liked)
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        created = ts(START, NOW)
        batch.append((mid, uid, rating, created))
        inserted_ratings += 1
        if len(batch) == BATCH:
            copy_rows(
                cur, "ratings", ["movie_id", "user_id", "rating", "created_at"], batch
            )
            batch = []
    if batch:
        copy_rows(
            cur, "ratings", ["movie_id", "user_id", "rating", "created_at"], batch
        )
    conn.commit()
    print(f"  ✓ ratings done ({inserted_ratings:,} rows)")

    # 8. Reviews
    # Reviews only from (user, movie) pairs that already have a rating
    print(f"Inserting {NUM_REVIEWS:,} reviews …")
    rating_pairs = list(seen_ratings)
    random.shuffle(rating_pairs)
    review_pairs = rating_pairs[:NUM_REVIEWS]

    SAMPLE_REVIEWS = [
        "Absolutely loved it! The cinematography was stunning.",
        "A solid watch, though the pacing felt a bit off in the second act.",
        "Not my cup of tea, but I can see why others enjoy it.",
        "Incredible performances all around. Would recommend.",
        "Overrated in my opinion. Expected much more.",
        "A hidden gem. Surprised by how much I enjoyed this.",
        "The plot twists kept me on the edge of my seat!",
        "Great for a lazy Sunday afternoon watch.",
        "The dialogue felt unnatural at times, but the story was compelling.",
        "One of the best I've seen this year. Instant classic.",
        "Decent enough, nothing groundbreaking.",
        "The ending was a letdown after such a strong start.",
        "Visually breathtaking, emotionally resonant.",
        "I laughed, I cried, I watched it twice.",
        "A bit slow but the payoff was worth it.",
    ]

    batch = []
    for uid, mid in review_pairs:
        text_base = random.choice(SAMPLE_REVIEWS)
        # pad to make each review unique-ish and realistic length
        extra = fake.sentence(nb_words=random.randint(5, 25))
        review_text = f"{text_base} {extra}"[:2000]
        contains_spoilers = random.random() < 0.15
        created = ts(START, NOW)
        batch.append((mid, uid, review_text, contains_spoilers, created))
        if len(batch) == BATCH:
            copy_rows(
                cur,
                "reviews",
                [
                    "movie_id",
                    "user_id",
                    "review_text",
                    "contains_spoilers",
                    "created_at",
                ],
                batch,
            )
            batch = []
    if batch:
        copy_rows(
            cur,
            "reviews",
            ["movie_id", "user_id", "review_text", "contains_spoilers", "created_at"],
            batch,
        )
    conn.commit()
    print(f"  ✓ reviews done ({len(review_pairs):,} rows)")

    # 9. Watch History
    # Union of all (user, movie) from ratings + extra casual watchers
    print(f"Inserting {NUM_WATCH_HISTORY:,} watch_history rows …")
    wh_pairs = set(rating_pairs[: NUM_WATCH_HISTORY // 2])
    while len(wh_pairs) < NUM_WATCH_HISTORY:
        uid = random.randint(1, NUM_USERS)
        mid = random.choice(movie_ids)
        wh_pairs.add((uid, mid))

    batch = []
    for uid, mid in wh_pairs:
        date_watched = ts(START, NOW)
        created = ts(START, NOW)
        batch.append((uid, mid, date_watched, created))
        if len(batch) == BATCH:
            copy_rows(
                cur,
                "watch_history",
                ["user_id", "movie_id", "date_watched", "created_at"],
                batch,
            )
            batch = []
    if batch:
        copy_rows(
            cur,
            "watch_history",
            ["user_id", "movie_id", "date_watched", "created_at"],
            batch,
        )
    conn.commit()
    print(f"  ✓ watch_history done ({len(wh_pairs):,} rows)")

    # Summary
    cur.execute("""
        SELECT
          (SELECT COUNT(*) FROM users)         AS users,
          (SELECT COUNT(*) FROM movies)        AS movies,
          (SELECT COUNT(*) FROM genres)        AS genres,
          (SELECT COUNT(*) FROM actors)        AS actors,
          (SELECT COUNT(*) FROM movie_genres)  AS movie_genres,
          (SELECT COUNT(*) FROM movie_actors)  AS movie_actors,
          (SELECT COUNT(*) FROM ratings)       AS ratings,
          (SELECT COUNT(*) FROM reviews)       AS reviews,
          (SELECT COUNT(*) FROM watch_history) AS watch_history;
    """)
    row = cur.fetchone()
    labels = [
        "users",
        "movies",
        "genres",
        "actors",
        "movie_genres",
        "movie_actors",
        "ratings",
        "reviews",
        "watch_history",
    ]
    total = sum(row)
    print("\n── Final row counts ─────────────────────────────────")
    for label, count in zip(labels, row):
        print(f"  {label:<20} {count:>10,}")
    print(f"  {'TOTAL':<20} {total:>10,}")
    print("────────────────────────────────────────────────────")

    cur.close()
    conn.close()
    print("\nDone! 🎉")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate fake data for Team_Project_365"
    )
    parser.add_argument(
        "--dsn",
        default="postgresql://postgres:password@localhost:5432/movies365",
        help="PostgreSQL DSN",
    )
    args = parser.parse_args()
    run(args.dsn)
