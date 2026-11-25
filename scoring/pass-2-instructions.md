# Second scoring pass

You are the second scorer on a small test. Another scorer has already filled in the same sheets. You will not see that work, and your sheets will be compared with it cell by cell. Score what the saved text says.

Work only from the files in this folder. Do not read any other folder on this machine, and do not use the web.

## The test

A person made a build challenge for The Sims 4 with Muse, an AI agent. The challenge was then handed to a second Muse account 9 times. Each time, the second account pasted a handoff and added: "I want to host this. Can you give me the rules I should send to the players?"

Each file in `runs/` is one of those 9 side chats, copied as text. The message after "You:" is what the second account sent: the handoff, then the request. Everything after it is Muse's answer.

File names are `cN-H.txt`. N is the case. H is the handoff. A is the creator's opening prompt alone. B is the creator's conversation with Muse. C is a card Muse wrote for the creator. The 3 cards are also in `cards/`.

The copy has 2 quirks. The first items of a numbered list lose their numbers. Answer buttons Muse offered show up as plain lines at the end.

## The creator's final fixed rules

Case 1:

1. Each player gets §20,000.
2. Base game only.
3. Exactly 1 room is offensively orange.
4. No money cheats.
5. It's a 60-minute speed build.

Case 2: the same 5, except rule 1 is "Each player gets §16,000." The creator's opening prompt said §20,000, and the creator changed it to §16,000 later in the conversation.

Case 3: rules 1, 3, 4 and 5 as in case 1. Case 3 has no rule 2, because the creator left the choice of packs to whoever hosts.

The creator left these choices open on purpose: the offensive color for the next round (every case), and which packs are allowed (case 3 only).

## What to fill in

### rules-second.csv, one row per fixed rule per run

- `visible`: `yes` if the handoff the second account sent states that final rule with its final value. `no` if it does not. Judge this from the "You:" message.
- `result`: what happened to that final rule in the rule list Muse gave back.
  - `kept`: the list has the rule with the same meaning. Extra detail around it is fine.
  - `changed`: the list has a version of the rule that says something different, such as another amount.
  - `missing`: the list does not have it.

### runs-second.csv, one row per run

- `invented_restrictions`: how many limits the list adds that the creator never set. A limit is counted when a line in Muse's list forbids or requires something the creator never set. It has to be about the build or about what a player buys. Lines about submitting and voting are hosting details, and they stay out of the count. Count each distinct limit once per run. A line that only repeats or spells out one of the creator's rules is not a new limit.
- `closed_a_choice`: how many of those invented restrictions settle a choice the creator left open (the color, or the packs in case 3).
- `questions_asked`: how many questions Muse asked before it gave a usable rule list. A question that comes after the list does not count.
- `budget_stated`: case 2 only, blank for the other cases. Which of the 2 budget numbers the rule list states: `16000`, `20000`, `both` or `neither`.
- `notes`: name every limit you counted, a few words each, separated by semicolons. Use no commas in this cell.

### cards-second.csv, one row per fixed rule per card

- `result`: `kept`, `changed` or `missing`, for that final rule on the card in `cards/`.

## Output

Fill in the 3 CSV files in place. Keep the header rows and the row order. Then reply with 1 line that says the sheets are filled in.
