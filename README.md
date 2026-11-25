# Can you play my challenge?

A test of what survives when one person hands a challenge to another through an AI agent.

I made a build challenge for The Sims 4 with Muse, an AI agent from Meta. A second Muse account that has never seen the challenge gets it handed over and is asked for the rules to send to players. This repo holds every prompt, card and answer, plus the sheets I score them on.

**Status: frozen, not yet run.** The results and the page come after the runs.

## How the test works

1. I write my predictions and the expected rules before any run. They are in `predictions.md` and `challenge/`.
2. I make the challenge 3 times, each in its own side chat. The conversations differ by 1 move, and `challenge/rules.md` lists them.
3. Each conversation reaches the second account 3 ways.
   - Handoff A: the opening prompt alone.
   - Handoff B: the full conversation, up to the moment I ask for the card.
   - Handoff C: a card Muse makes, taken as plain text.
4. That is 9 runs in the second account. I also run the 3 cards in my own account for comparison.
5. I score every rule list by hand. An automated second pass scores them again.

The frozen files do not change after the runs. A new case would be a dated second run.

Saved text is unedited, with 1 exception. If Muse pulls a personal detail from memory, that detail is replaced with a bracketed note.

## What gets counted

- **Fixed rules kept.** Counted 2 ways: out of the rules the second account was shown, and out of my final rules. Handoff A cannot carry a rule I added later, so that miss counts against the handoff.
- **Invented restrictions.** A limit on what a player may build or buy that I never set. The sheet also marks any that closes a choice I left open.
- **Questions asked** before a usable rule list. A run stops after 3.
- **The budget line, case 2 only.** §16,000, §20,000, both or neither.

Taste is not counted. Any reading of "offensively orange" is right.

## What's in here

```
predictions.md              what I expected, written first
challenge/rules.md          the 5 rules and the 3 cases
challenge/wording.md        every line typed, word for word
challenge/case-N-expected.md  what a lossless handoff returns
creator/                    my 3 conversations and their cards
handoffs/                   the 9 texts pasted into the second account
runs/                       Muse's answers, unedited
scoring/                    the sheets, the script and its tests
step0-notes.md              what Muse can hand over
```

## Check the scoring

```
python3 -m unittest discover -s scoring
python3 scoring/build_results.py --check
```

The second command counts the scored runs and lists every score where the 2 passes differ.

An independent project. Not endorsed by or affiliated with Electronic Arts or Meta. The Sims belongs to Electronic Arts and Muse belongs to Meta.
