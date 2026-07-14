# case-notes-eval

[![ci](https://github.com/repowazdogz-droid/case-notes-eval/actions/workflows/ci.yml/badge.svg)](https://github.com/repowazdogz-droid/case-notes-eval/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)

An [Inspect](https://inspect.aisi.org.uk/) evaluation that measures whether models
writing professional case notes **separate observation from interpretation**, and a
second, adversarial condition that asks the model to **carry a judgement past a
lexical validator** the author built.

The grader is deterministic — no model sits in the scoring path. The rubric was
committed to git before the first model call.

Unlike a typical capability benchmark, the score comes from a fixed deterministic
checker rather than a model judge, the rubric was pre-registered in git before any
model was run, and the design includes an adversarial condition aimed at the checker
itself, not only the model. The question is construct validity: whether a clean score
means what it claims to mean.

## Purpose

UK safeguarding recording standards require records to distinguish fact from
opinion. A note that says *"Jamie was being manipulative"* imports an unevidenced
inference into a record that a court or inspector will later read as fact; *"Jamie
asked three times after being told no"* does not. As models are increasingly used to
draft such notes, whether they preserve that separation is a measurable property.

This repository asks two questions:

1. **Neutral condition** — given only observable facts, does the model *add*
   interpretation the input did not contain?
2. **Evasion condition** — given the facts *plus* a judgement, can the model write a
   note that a deterministic lexical validator scores as clean *while still carrying
   that judgement to a human reader*? A high evasion rate means the validator is
   measuring surface vocabulary, not the property it claims to measure.

## Experimental design

- **30 scenarios**, each a short set of observable facts plus one judgement, across
  education, social care, therapy and residential settings. All scenarios are
  synthetic; no real person or record is involved.
- **2 conditions** per scenario (neutral, evasion) — 60 prompts per model.
- **Grader:** [`recording_checker.py`](src/case_notes_eval/recording_checker.py), a
  deterministic 252-phrase lexical checker with quote-suppression, an observational-
  qualifier rule, and a trailing-evidence downgrade. No model in the scoring path;
  the same note always scores identically.
- **Pre-registration:** [`docs/RUBRIC.md`](docs/RUBRIC.md) was committed before the
  first model call. Its git timestamp is the evidence. It is reproduced here
  unedited, including a dated factual correction (Amendment 3).
- **Metrics** are computed by the grader: `clean_rate`, `high_sev_rate`,
  `flags_per_100w`, `qualifier_rate`. One secondary metric — whether an evasion note
  still *conveys* the judgement — requires a human or LLM judge and is labelled in
  the rubric as the weakest number in the study. It is reported separately and never
  folded into the primary metrics.

## Threat model

The "attacker" is the model under the evasion prompt, and the thing being attacked
is a **lexical safeguarding validator** of exactly the kind that could be deployed to
screen human- or model-written notes. The question is whether such a validator's
clean verdict is trustworthy. The finding is that it is not: a paraphrase that avoids
the flagged vocabulary passes while still communicating the judgement. This is a
result about the *validator's construct validity*, not about any individual model's
safety. It generalises to any keyword-based content filter used as a safety gate.

The validator here (called **Reflex**) was deployed only as a demo at
`case-notes-validator.vercel.app`. **It was never used on real records and has no
users**, so no live safeguarding instrument was bypassed and no real records were at
risk. See [`docs/RUBRIC.md`](docs/RUBRIC.md), Amendment 3.

## How to reproduce

```bash
pip install -e ".[dev]"
```

The eval is provider-agnostic through Inspect's model API. Set the relevant API key
and point `inspect eval` at the task.

### Run on Anthropic

```bash
export ANTHROPIC_API_KEY=...
inspect eval src/case_notes_eval/task.py --model anthropic/claude-sonnet-5 --log-dir logs
```

### Run on OpenAI

```bash
export OPENAI_API_KEY=...
inspect eval src/case_notes_eval/task.py --model openai/gpt-5 --log-dir logs
```

### Run on local models (no API key, fully reproducible)

```bash
# with an Ollama server running locally
inspect eval src/case_notes_eval/task.py --model ollama/qwen3:14b --log-dir logs
```

Then analyse whatever logs you have:

```bash
case-notes-analyse logs
```

### Run the analysis on the bundled sample immediately

Four open-weight sample logs ship in `examples/sample_logs/`, so the analysis runs
with no model and no key:

```bash
case-notes-analyse examples/sample_logs
```

And the grader alone, on any text:

```bash
echo "Jamie was being manipulative." | case-notes-check
```

## Expected outputs

`case-notes-analyse examples/sample_logs` prints a per-model, per-condition table,
the evasion delta, and the count of EVASION notes that scored clean (candidate
bypasses). On the bundled open-weight sample you should see all four families
(`gemma3`, `llama3`, `mistral-small3.1`, `qwen3`), both conditions, and a non-zero
bypass count — several models produce validator-clean notes while under the evasion
prompt. That is the headline finding: a clean lexical verdict does not establish that
the judgement is absent.

## Known limitations

- **The lexicon is authored, not derived.** The 252 phrases and their severities are
  the author's editorial choices; they are part of the study's trusted base, not
  independent evidence. A different lexicon would score differently.
- **The conveyance metric is weak.** Whether an evasion note *still transmits* the
  judgement is a judgement call. It is reported separately and never mixed into the
  deterministic metrics.
- **Scope.** This tests one property (fact/opinion separation) against one validator
  design (lexical). It is not a general safety benchmark and does not rank models on
  anything else.
- **Reflex was a demo, never used on real records** (see Threat model). Any claim
  that a production safeguarding tool was bypassed would be false and is not made.
- The bundled sample is the open-weight arm; the frontier arm requires API keys and
  is reproduced by the commands above, not committed here.

## License

[MIT](LICENSE). The synthetic scenarios and the phrase lexicon are included under the
same licence.
