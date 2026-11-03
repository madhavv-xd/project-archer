"""Self-serve routing eval — the shadow soak, minus the users.

Runs a labeled query set through BOTH routers locally and reports:
  - keyword accuracy vs the hand label
  - embedding accuracy vs the hand label (as it would actually route: embedding
    if similarity >= threshold, else keyword fallback)
  - agreement between the two, and every disagreement, so you can eyeball
    whether embedding was smarter on the cases keyword gets wrong.

Run: uv run python eval_routing.py   (needs EMBEDDING_API_KEY in .env)

The query set leans on KEYWORD-FREE paraphrases on purpose — those are the whole
reason 2B exists, so that's where embedding should earn its keep.

Two sets, reported separately:
  - CASES (36): the original set. Most are near-copies of routing_exemplars.py,
    so embedding scores here are inflated by memorization — kept for continuity.
  - DEV (150): for tuning (threshold, exemplars, embedding model). Disjoint
    from both exemplars and HELDOUT.
  - HELDOUT (210): written against the exemplars, no paraphrase of any of them.
    Never tuned on. THIS is the number to quote.
"""

import asyncio
from collections import Counter

from app.config import settings
from app.core.embeddings import embedding_route
from app.core.router import keyword_route
from app.core.routing_exemplars import EXEMPLARS

# keyword routing_reason -> domain (so both routers speak the same 6 buckets)
REASON_DOMAIN = {
    "coding_keywords": "coding",
    "math_keywords": "math",
    "writing_keywords": "writing",
    "simple_query": "simple",
    "analysis_keywords": "analysis",
    "default": "general",
}

# (query, expected_domain). Mix of keyword-free paraphrases (hard) and a few
# obvious ones. Edit freely — this is your eval set.
CASES = [
    # coding — mostly no whitelisted coding word
    ("my program keeps crashing on line 40", "coding"),
    ("the app freezes whenever I hit save", "coding"),
    ("how do I make this loop run faster", "coding"),
    ("why does my recursive call blow the stack", "coding"),
    ("connect my backend to a postgres database", "coding"),  # has 'database'
    ("help me debug this python function", "coding"),          # obvious
    ("tests pass locally but fail in the pipeline", "coding"),
    # math — no whitelisted math word in most
    ("if a train goes 60mph for two hours how far", "math"),
    ("whats the chance of rolling two sixes in a row", "math"),
    ("how many ways can I arrange five books", "math"),
    ("reduce this fraction to lowest terms", "math"),
    ("solve this integral step by step", "math"),              # obvious
    ("how much interest at 5 percent over 3 years", "math"),
    # writing
    ("help me put together a birthday message for my mom", "writing"),
    ("make this sound more professional", "writing"),
    ("give me a catchy tagline for my coffee shop", "writing"),
    ("turn these bullet points into a paragraph", "writing"),
    ("write a short poem about the ocean", "writing"),          # obvious
    ("craft a toast for my best friends wedding", "writing"),
    # simple
    ("hey there", "simple"),
    ("whats the capital of france", "simple"),
    ("who painted the mona lisa", "simple"),
    ("how tall is mount everest", "simple"),
    ("good morning", "simple"),
    ("how do you spell restaurant", "simple"),
    # analysis
    ("weigh the upsides and downsides of remote work", "analysis"),
    ("which of these three vendors should we pick and why", "analysis"),
    ("break down whats really driving our customer churn", "analysis"),
    ("compare these strategies across cost risk and timeline", "analysis"),  # obvious
    ("whats the long term consequence of raising prices", "analysis"),
    # general
    ("tell me something cool about deep sea creatures", "general"),
    ("what should I cook with chicken and rice", "general"),
    ("explain how airplanes stay in the air", "general"),
    ("how do bees make honey", "general"),
    ("recommend a beginner houseplant thats hard to kill", "general"),
    ("what causes the northern lights", "general"),
]

# Held-out set: none of these paraphrase an exemplar. ~1/3 contain a whitelisted
# keyword (realistic traffic), the rest are keyword-free.
HELDOUT = [
    # coding
    ("my react component re-renders every time I type in the input", "coding"),
    ("the docker container exits immediately after starting", "coding"),
    ("how do I reverse a linked list in place", "coding"),
    ("git says I have merge conflicts, how do I resolve them", "coding"),
    ("my flexbox items wont center vertically", "coding"),
    ("getting a null pointer exception when I read the config file", "coding"),
    ("how do I parse a json file and pull out one field", "coding"),
    ("set up a cron job that runs a script every night at midnight", "coding"),
    ("my website loads slowly on mobile, how do I profile it", "coding"),
    ("whats the difference between a process and a thread", "coding"),
    ("regex to match an email address", "coding"),
    ("npm install fails with a peer dependency conflict", "coding"),
    ("how do I paginate results from a rest endpoint", "coding"),
    ("my query takes 30 seconds on a table with a million rows", "coding"),
    ("explain big o notation with an example of quadratic time", "coding"),
    ("how do I mock an http call in my unit tests", "coding"),
    ("write a bash script that renames every file in a folder", "coding"),
    ("my kubernetes pod is stuck in crashloopbackoff", "coding"),
    ("how should I structure folders in a large flask project", "coding"),
    ("convert this callback based code to async await", "coding"),
    ("what does a segmentation fault mean in c", "coding"),
    ("how do I undo my last commit without losing changes", "coding"),
    ("the button click handler fires twice", "coding"),
    ("implement a binary search tree with insert and delete", "coding"),
    ("fix this sql query that returns duplicate rows", "coding"),
    ("my python script runs out of memory reading a big csv", "coding"),
    ("how do I deploy a node server to a vps", "coding"),
    ("why is my variable undefined inside the arrow function", "coding"),
    ("add type hints to this module so mypy stops complaining", "coding"),
    ("my webhook endpoint keeps returning 403", "coding"),
    ("how do I cache responses in a single page app", "coding"),
    ("the borrow checker says cannot borrow as mutable more than once", "coding"),
    ("create a dockerfile for a django app", "coding"),
    ("how do I read environment variables in go", "coding"),
    ("my android app crashes when the screen rotates", "coding"),
    # math
    ("what is 15 percent of 240", "math"),
    ("a recipe needs 3 cups for 4 people, how much for 10", "math"),
    ("if I invest 1000 dollars at 7 percent compounded yearly what will I have in 10 years", "math"),
    ("find x if 3x plus 7 equals 22", "math"),
    ("whats the area of a circle with radius 4", "math"),
    ("how many diagonals does a hexagon have", "math"),
    ("whats the least common multiple of 12 and 18", "math"),
    ("is 221 a prime number", "math"),
    ("differentiate x cubed times sine x", "math"),
    ("whats the volume of a cone with height 9 and radius 3", "math"),
    ("how likely is it that two people in a room of 23 share a birthday", "math"),
    ("find the inverse of this 2x2 matrix", "math"),
    ("if I drive 240 miles on 8 gallons whats my mileage", "math"),
    ("how long to pay off a 5000 loan at 200 a month with 18 percent apr", "math"),
    ("whats the median of 3 8 1 9 4 7", "math"),
    ("show that the sum of two odd numbers is always even", "math"),
    ("how many handshakes if 12 people all greet each other once", "math"),
    ("whats the next number in 2 6 12 20 30", "math"),
    ("simplify the square root of 72", "math"),
    ("whats the angle between the hour and minute hands at 3:15", "math"),
    ("how many grams of salt for a 2 percent brine with 1 liter of water", "math"),
    ("solve the system 2x plus y equals 5 and x minus y equals 1", "math"),
    ("whats the limit of sine x over x as x goes to zero", "math"),
    ("if a population doubles every 3 years how long until its 10 times bigger", "math"),
    ("factor x squared minus 9", "math"),
    ("whats 2 to the power of 20", "math"),
    ("how much paint for a room 12 by 14 feet with 8 foot ceilings", "math"),
    ("whats the variance of 2 4 4 4 5 5 7 9", "math"),
    ("a shirt is 40 percent off then another 20 percent off, whats the total discount", "math"),
    ("how many different 4 digit pin codes are possible", "math"),
    ("integrate e to the 2x", "math"),
    ("whats the hypotenuse of a right triangle with legs 5 and 12", "math"),
    ("convert 0.375 to a fraction", "math"),
    ("find the eigenvalues of this 2x2 matrix", "math"),
    ("whats the probability of drawing two aces from a deck without replacement", "math"),
    # writing
    ("help me reply to a customer whos upset about a late delivery", "writing"),
    ("polish my linkedin summary so it sounds confident", "writing"),
    ("give me three name ideas for a bakery", "writing"),
    ("rewrite this paragraph so a ten year old could understand it", "writing"),
    ("draft a resignation letter that stays on good terms", "writing"),
    ("make my wedding vows funnier without losing the sweetness", "writing"),
    ("punch up the opening of my short story", "writing"),
    ("tighten this abstract to under 150 words", "writing"),
    ("come up with a haiku about autumn rain", "writing"),
    ("help me say no to a coworker who keeps asking for favors", "writing"),
    ("turn my meeting notes into a clear summary email", "writing"),
    ("give my product description a more playful tone", "writing"),
    ("write lyrics for a lullaby", "writing"),
    ("craft a thank you note to my kids teacher", "writing"),
    ("fix the grammar and flow in my personal statement", "writing"),
    ("suggest a title for my essay on climate migration", "writing"),
    ("write a limerick about a cat who hates mondays", "writing"),
    ("help me announce our new office location to the team", "writing"),
    ("make this apology sound sincere rather than defensive", "writing"),
    ("create a slogan for a recycling campaign", "writing"),
    ("pen a short eulogy for my grandfather who loved fishing", "writing"),
    ("convert this formal press release into a friendly blog post", "writing"),
    ("draft a dating profile bio thats witty but not try hard", "writing"),
    ("help me describe a sunset in a more evocative way", "writing"),
    ("give me an outline for a mystery novel set in a lighthouse", "writing"),
    ("shorten this speech so it fits in two minutes", "writing"),
    ("rephrase this complaint to my landlord so its firm but polite", "writing"),
    ("write the opening scene of a sci-fi screenplay", "writing"),
    ("help me caption a photo of my dog at the beach", "writing"),
    ("make this job posting sound more inclusive", "writing"),
    ("come up with a rhyming invitation for a kids party", "writing"),
    ("give feedback on the tone of my cover letter", "writing"),
    ("help me sign a farewell card for a retiring colleague", "writing"),
    ("turn this dry instruction manual section into friendly copy", "writing"),
    ("edit this email so it gets to the point faster", "writing"),
    # simple
    ("hello!", "simple"),
    ("thank you so much", "simple"),
    ("whats the capital of australia", "simple"),
    ("who wrote pride and prejudice", "simple"),
    ("how many legs does a spider have", "simple"),
    ("what year did world war two end", "simple"),
    ("whats the boiling point of water", "simple"),
    ("is a tomato a fruit", "simple"),
    ("how many days are in a leap year", "simple"),
    ("who founded microsoft", "simple"),
    ("whats the largest ocean", "simple"),
    ("good night", "simple"),
    ("what does asap stand for", "simple"),
    ("how many continents are there", "simple"),
    ("yes please", "simple"),
    ("what color do you get mixing blue and yellow", "simple"),
    ("whats the chemical symbol for gold", "simple"),
    ("nice, thanks!", "simple"),
    ("how many ounces in a pound", "simple"),
    ("who was the first person on the moon", "simple"),
    ("what language do they speak in brazil", "simple"),
    ("whats the tallest animal", "simple"),
    ("how many players on a soccer team", "simple"),
    ("whats the opposite of ancient", "simple"),
    ("when is christmas", "simple"),
    ("how far is the moon from earth", "simple"),
    ("who discovered penicillin", "simple"),
    ("whats the currency of japan", "simple"),
    ("are you there?", "simple"),
    ("whats the plural of cactus", "simple"),
    ("whats the speed of light", "simple"),
    ("sup", "simple"),
    ("which planet is closest to the sun", "simple"),
    ("how old is the universe", "simple"),
    ("ok got it", "simple"),
    # analysis
    ("should we build our own auth system or buy one, given a team of four", "analysis"),
    ("is it smarter to pay off my student loans early or invest the money", "analysis"),
    ("what are the risks of expanding into europe next year", "analysis"),
    ("assess how this merger could affect smaller competitors", "analysis"),
    ("which pricing tier structure would maximize revenue for a niche saas", "analysis"),
    ("why might our apps retention drop after the first week", "analysis"),
    ("contrast nuclear and solar as long term energy bets for a mid size country", "analysis"),
    ("what are the strengths and weaknesses of this hiring plan", "analysis"),
    ("help me decide between two job offers, one pays more and the other has better growth", "analysis"),
    ("critique the methodology of this survey study", "analysis"),
    ("what could go wrong if we migrate all our servers in one weekend", "analysis"),
    ("is a four day work week realistic for a customer support team", "analysis"),
    ("how would a recession likely affect a luxury goods brand", "analysis"),
    ("rank these five marketing channels by expected return for a b2b startup", "analysis"),
    ("what factors explain why some cities gentrify faster than others", "analysis"),
    ("evaluate whether our onboarding flow is causing drop off", "analysis"),
    ("should a small bakery open a second location or improve the first", "analysis"),
    ("what are the hidden costs of switching cloud providers", "analysis"),
    ("look at both sides of banning phones in schools", "analysis"),
    ("diagnose why our ad spend went up but conversions stayed flat", "analysis"),
    ("what would happen to our margins if shipping costs rose 20 percent", "analysis"),
    ("is leasing or buying a car better for someone who drives 20k miles a year", "analysis"),
    ("compare a monolith versus microservices for a team of three", "analysis"),
    ("weigh centralizing versus decentralizing decisions in a growing company", "analysis"),
    ("how might remote hiring reshape our company culture over five years", "analysis"),
    ("is our dependence on one big client a serious risk", "analysis"),
    ("judge which of these three apartment options is the best value", "analysis"),
    ("why did the product launch underperform compared to forecasts", "analysis"),
    ("analyze the competitive landscape for meal kit delivery", "analysis"),
    ("what are the pros and cons of an index fund versus picking stocks", "analysis"),
    ("scrutinize this contract for clauses that could hurt us", "analysis"),
    ("would raising the minimum order size hurt or help us", "analysis"),
    ("examine how interest rate changes affect housing affordability", "analysis"),
    ("think through whether franchising makes sense for our brand", "analysis"),
    ("which is the stronger thesis in these two research proposals and why", "analysis"),
    # general
    ("how do vaccines train the immune system", "general"),
    ("whats a good way to start running as a beginner", "general"),
    ("why is the sky blue", "general"),
    ("give me some ideas for a first date", "general"),
    ("how do I get rid of fruit flies in my kitchen", "general"),
    ("whats the history behind halloween", "general"),
    ("how do noise cancelling headphones work", "general"),
    ("suggest some books like the hobbit", "general"),
    ("how can I keep my basil plant alive", "general"),
    ("why do cats purr", "general"),
    ("what are some fun things to do in lisbon", "general"),
    ("how do I remove a red wine stain from carpet", "general"),
    ("explain how a bill becomes a law", "general"),
    ("whats the difference between a crocodile and an alligator", "general"),
    ("tips for staying focused while working from home", "general"),
    ("how does gps know where I am", "general"),
    ("what should I pack for a week in iceland", "general"),
    ("how did the ancient egyptians build the pyramids", "general"),
    ("recommend a board game for six people", "general"),
    ("why do we dream", "general"),
    ("how do I make my sourdough rise better", "general"),
    ("whats a good stretch routine for lower back pain", "general"),
    ("how does a credit score work", "general"),
    ("tell me a fun fact about the roman empire", "general"),
    ("how do solar panels turn sunlight into electricity", "general"),
    ("what are good gifts for someone who loves gardening", "general"),
    ("how do I teach my dog to stop pulling on the leash", "general"),
    ("why do leaves change color in the fall", "general"),
    ("whats the best way to learn a new language as an adult", "general"),
    ("how do tides work", "general"),
    ("give me an easy weekly meal prep plan", "general"),
    ("how do I choose a good watermelon", "general"),
    ("what happened during the french revolution", "general"),
    ("how can I save money on groceries", "general"),
    ("why do onions make you cry", "general"),
]

# Tuning set: change the threshold / exemplars / embedding model by DEV score
# only, then read HELDOUT once. Tuning on HELDOUT turns its number into fiction.
DEV = [(q, d) for d, qs in {
    "coding": [
        "my flask route returns a 500 but theres nothing in the logs",
        "how do I write a generator that yields chunks of a list",
        "the linter complains about unused imports everywhere",
        "how do I sort a list of dicts by a nested key",
        "memory keeps climbing in my long running worker process",
        "websocket connection drops after exactly sixty seconds",
        "how do I hash passwords safely before storing them",
        "the page shows a cors error when calling my backend",
        "whats the cleanest way to handle retries with exponential backoff",
        "my terraform plan wants to destroy and recreate the bucket",
        "how do I stop my threads from deadlocking",
        "the form submits but the state doesnt update until I refresh",
        "how do I spin up a local redis for integration tests",
        "my ios build fails with a provisioning profile error",
        "swap two variables without a temp",
        "whats a good way to version a public rest interface",
        "my pandas merge is producing way more rows than expected",
        "the ssl handshake fails when my client calls the internal server",
        "how do I lazy load images on a long page",
        "my github action cant find the secret I added",
        "turn this nested loop into a list comprehension",
        "find the hot path in this slow data pipeline",
        "my vim config breaks syntax highlighting",
        "how do I make a dropdown accessible to screen readers",
        "the migration fails because the column already exists",
    ],
    "math": [
        "whats 18 percent tip on 64 dollars",
        "how many seconds are in a week",
        "if 5 workers build a wall in 8 days how long for 10 workers",
        "whats the sum of interior angles of an octagon",
        "solve for t in 4t minus 9 equals 3t plus 2",
        "how many combinations of 3 toppings from 10",
        "whats the derivative of ln of x squared",
        "area of a trapezoid with bases 6 and 10 and height 4",
        "if I get a 6 percent raise on 52000 whats my new salary",
        "expected number of flips to get heads twice in a row",
        "whats the gcd of 84 and 126",
        "convert 3/8 to a percentage",
        "how fast must I drive to cover 300 km in 2.5 hours",
        "what is 7 factorial",
        "whats the surface area of a sphere with radius 6",
        "is the series 1 over n squared convergent",
        "split a 230 dollar bill four ways with 15 percent tip",
        "whats the log base 2 of 1024",
        "how many triangles can you form from 8 points no three collinear",
        "find the mean of 12 15 18 22 and 33",
        "whats the determinant of a 3x3 identity",
        "if a car depreciates 15 percent a year whats it worth after 4 years",
        "round pi to 4 decimal places and multiply by 9",
        "whats the dot product of 1 2 3 and 4 5 6",
        "chances of getting at least one six in four rolls",
    ],
    "writing": [
        "help me write a heartfelt sympathy card",
        "make this text to my ex sound less bitter",
        "give me five catchy names for a podcast about gardening",
        "rework this intro paragraph so it hooks the reader",
        "help me phrase a raise request to my manager",
        "compose a short sonnet about city lights",
        "turn this rambling voicemail transcript into a tidy message",
        "suggest a headline for my article about urban beekeeping",
        "make my instagram bio more fun",
        "help me respond graciously to a negative review",
        "draft an out of office reply for my vacation",
        "punch up these product bullet points for the landing page",
        "write a bedtime rhyme about a sleepy dragon",
        "give my thesis acknowledgments a warmer tone",
        "help me word a reminder about an unpaid invoice",
        "rewrite this cover blurb for my fantasy novel",
        "create a short welcome speech for new interns",
        "make this paragraph flow better",
        "craft a memorable opening line for my memoir",
        "turn these facts about our company into an about us page",
        "help me write a polite follow up after a job interview",
        "tone down this angry message to my roommate",
        "give me a clever pun for my lemonade stand sign",
        "help me retell this family legend for my kids",
        "condense this report into a three sentence executive summary",
    ],
    "simple": [
        "hi there",
        "cheers",
        "whats the capital of canada",
        "who sang thriller",
        "how many hours in a day",
        "what is the freezing point of water",
        "what day comes after tuesday",
        "who invented the telephone",
        "is pluto a planet",
        "how many teeth do adults have",
        "whats the biggest country by area",
        "okay cool",
        "whats h2o",
        "who is the author of harry potter",
        "bye for now",
        "how many sides does a pentagon have",
        "whats the national animal of scotland",
        "when did the titanic sink",
        "whats the longest river in africa",
        "no thanks",
        "whats the capital of kenya",
        "hows it going",
        "who directed jaws",
        "whats the main ingredient in guacamole",
        "hey, quick question",
    ],
    "analysis": [
        "should our startup raise a seed round now or bootstrap another year",
        "what are the risks of relying on a single supplier overseas",
        "why are our support tickets spiking on mondays",
        "is it worth renovating my kitchen before selling the house",
        "weigh hiring a senior engineer against two juniors",
        "whats driving the gap between our signups and paid conversions",
        "assess the long term viability of this franchise model",
        "which of these two cities is a better place to open a gym",
        "what are the downsides of offering unlimited vacation",
        "is it smarter to rent equipment or buy it for a six month project",
        "how might new tariffs reshape our sourcing strategy",
        "critically review this go to market plan",
        "what would a 10 percent price cut do to demand and profit",
        "should we sunset our legacy product or keep maintaining it",
        "evaluate the trade offs of a four tier versus three tier pricing page",
        "why do some teams ship faster than others with similar headcount",
        "interpret what these survey results say about customer loyalty",
        "what are the biggest threats to our market share next year",
        "decide between expanding online or opening a physical store",
        "break down the cost structure of running a food truck",
        "what explains the drop in our newsletter open rates",
        "is it better to consolidate our tools or keep best of breed",
        "how robust is this financial forecast to a slower sales quarter",
        "what are the ethical implications of using customer data for pricing",
        "appraise whether this acquisition target is overvalued",
    ],
    "general": [
        "how does a refrigerator keep things cold",
        "what are some good podcasts for a long drive",
        "why do we get goosebumps",
        "how should I care for a cast iron pan",
        "whats the story behind the olympic rings",
        "how do hurricanes form",
        "tips for making new friends in a new city",
        "how do I get my toddler to eat vegetables",
        "whats the difference between baking soda and baking powder",
        "how did people navigate before compasses",
        "what are some easy hobbies to pick up this winter",
        "why do some people get motion sickness",
        "how does a microwave heat food",
        "what should I know before adopting a cat",
        "how do I keep my car battery healthy in cold weather",
        "why is the ocean salty",
        "explain how a mortgage works",
        "what are fun indoor activities for kids",
        "how do bats find their way in the dark",
        "recommend a few classic movies from the 80s",
        "how do I fold a fitted sheet",
        "whats the origin of thanksgiving",
        "how do plants know which way is up",
        "ways to reduce stress before an exam",
        "how does recycling actually get processed",
    ],
}.items() for q in qs]

# Guard the held-out claim: no case may be an exemplar verbatim.
_EX = {e.lower().replace("'", "") for es in EXEMPLARS.values() for e in es}
assert not [q for q, _ in HELDOUT + DEV if q.lower().replace("'", "") in _EX], "eval set leaks an exemplar"


async def evaluate(name: str, cases: list[tuple[str, str]], thr: float) -> tuple[int, int, int]:
    print(f"\n### {name}  cases={len(cases)}\n")
    kw_correct = emb_correct = agree = failed = 0
    per_domain: Counter = Counter()
    per_domain_ok: Counter = Counter()
    disagreements = []
    print(f"{'expected':9} {'keyword':9} {'embedding':16} query")
    print("-" * 80)
    for query, expected in cases:
        kw_domain = REASON_DOMAIN[keyword_route(query)[1]]
        domain, sim = await embedding_route(query)
        failed += sim == -1.0  # embedding_route's failure sentinel — silently degrades to keyword
        # As deployed: embedding decides only above threshold, else keyword.
        emb_domain = domain if sim >= thr else kw_domain
        emb_label = f"{emb_domain}({sim:.2f})" if sim >= thr else f"kw:{kw_domain}({sim:.2f})"

        kw_correct += kw_domain == expected
        emb_correct += emb_domain == expected
        agree += kw_domain == emb_domain
        per_domain[expected] += 1
        per_domain_ok[expected] += emb_domain == expected
        if kw_domain != emb_domain:
            disagreements.append((query, expected, kw_domain, emb_domain, sim))

        flag = "" if emb_domain == expected else "  <-- embedding miss"
        print(f"{expected:9} {kw_domain:9} {emb_label:16} {query}{flag}")

    n = len(cases)
    print("\n" + "=" * 80)
    print(f"keyword   accuracy vs label: {kw_correct}/{n}  ({kw_correct/n*100:.0f}%)")
    print(f"embedding accuracy vs label: {emb_correct}/{n}  ({emb_correct/n*100:.0f}%)")
    print(f"agreement (same pick):       {agree}/{n}  ({agree/n*100:.0f}%)")
    print(f"embedding call failures:     {failed}/{n}" + ("  <-- RESULTS INVALID" if failed else ""))
    print("embedding accuracy by domain: " + "  ".join(
        f"{d} {per_domain_ok[d]}/{per_domain[d]}" for d in sorted(per_domain)))
    print(f"\ndisagreements ({len(disagreements)}) — who was right?")
    for query, expected, kw, emb, sim in disagreements:
        kw_ok = "OK" if kw == expected else "X"
        emb_ok = "OK" if emb == expected else "X"
        print(f"  expected={expected:9} keyword={kw:9}[{kw_ok}] embedding={emb:9}[{emb_ok}] sim={sim:.2f}  {query}")
    return kw_correct, emb_correct, n


async def main() -> None:
    thr = settings.EMBEDDING_SIMILARITY_THRESHOLD
    assert settings.EMBEDDING_API_KEY, "set EMBEDDING_API_KEY in .env first"
    print(f"threshold={thr}")
    a = await evaluate("ORIGINAL (overlaps exemplars)", CASES, thr)
    d = await evaluate("DEV (tuning)", DEV, thr)
    b = await evaluate("HELD-OUT", HELDOUT, thr)
    kw, emb, n = (x + y for x, y in zip(a, b))
    print(f"\n### SUMMARY  threshold={thr}")
    print(f"original  ({a[2]:3}): keyword {a[0]/a[2]*100:.0f}%  embedding {a[1]/a[2]*100:.0f}%")
    print(f"dev       ({d[2]:3}): keyword {d[0]/d[2]*100:.0f}%  embedding {d[1]/d[2]*100:.0f}%")
    print(f"held-out  ({b[2]:3}): keyword {b[0]/b[2]*100:.0f}%  embedding {b[1]/b[2]*100:.0f}%")
    print(f"combined  ({n:3}): keyword {kw/n*100:.0f}%  embedding {emb/n*100:.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
