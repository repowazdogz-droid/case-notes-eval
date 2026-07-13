# Assurance boundary

What this evaluation's numbers do and do not establish.

## What the deterministic metrics establish

`clean_rate`, `high_sev_rate`, `flags_per_100w` and `qualifier_rate` are computed by
a deterministic grader with no model in the scoring path. Given the same note, they
are exactly reproducible. They are **facts about the grader applied to the notes** —
not, on their own, facts about the world.

Specifically: a low neutral `clean_rate` means the model wrote language *this lexicon*
flags. A high evasion `clean_rate` means the model avoided *this lexicon's* vocabulary.
Both are only as meaningful as the lexicon, which is authored (see below).

## The trusted base

- **The lexicon is authored, not derived.** The 252 phrases, their categories and
  their severities are the author's editorial choices. They are an unverified premise
  the numbers inherit, not independent evidence. A different lexicon yields different
  numbers.
- **The scenarios are authored.** 30 synthetic vignettes chosen by the author. They
  are not a random sample of real case notes and carry the author's view of what a
  hard case looks like.
- **The conveyance judgement is a judgement.** Whether an evasion note still transmits
  the stated view is assessed by a human or an LLM judge. It is the one number with a
  model (or author) in the loop, is reported separately, and is labelled in the rubric
  as the weakest number in the study.

## What a "candidate bypass" is, and is not

An EVASION note that scores clean is a *candidate* validator bypass: it passed the
lexical check. Whether it *also* still conveys the judgement — which is what would make
it a true bypass rather than a genuinely neutral rewrite — is the weak conveyance
judgement above. The primary metric counts the clean notes; it does not, by itself,
prove conveyance. The rubric requires every clean evasion note's transcript to be
published so a reader can judge conveyance independently.

## What is explicitly not claimed

- That any production safeguarding tool was bypassed. Reflex was a demo with no users
  and no real records (rubric, Amendment 3).
- That one model is safer than another in general. This tests one narrow property.
- That passing this validator means a note is good, or failing it means a note is bad.
  The validator's blindness is the finding, not a certification.
